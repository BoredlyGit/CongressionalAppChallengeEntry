# Created by Nickolas Koe for the 2021 Congressional App Challenge
# NOTE: Currently does not work with python 3.10 - pip has no available binaries for PySide2 for 3.10

import asyncio
import imaplib
import random
import socket
from PySide2 import QtWidgets, QtCore, QtGui
from project_sqlalchemy_globals import Session, Base, engine
import qasync
import json
import os

if os.name == 'nt':
    # https://stackoverflow.com/questions/1551605/how-to-set-applications-taskbar-icon-in-windows-7/1552105#1552105
    import ctypes
    myappid = 'StudyCoordinator'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)  # ensures qt icon is used and not the python one

app = QtWidgets.QApplication([])
asyncio.set_event_loop(qasync.QEventLoop(QtCore.QCoreApplication.instance()))  # expose qt event loop as a PEP 3156 one

# these imports here in case any rely on the event loop
from settings.widgets import SettingsWidget
from settings.models import Setting
from break_timer.widgets import MainBreakTimerWidget
from todo_lists import TodoLabelModel, TodoCardWidget, TodoMainScroll, TodoListModel, TodoCardModel, email_checking

Base.metadata.create_all(engine)


def apply_stylesheet(qapp, qss_fp, vars_fp):
    try:
        with open(vars_fp, "r") as vars_file:
            stylesheet_vars = json.load(vars_file)
    except FileNotFoundError:
        with open(vars_fp, "a+") as vars_file:
            stylesheet_vars = {
                "primary_color": "255, 255, 255",
                "accent_color": "0, 0, 0",
                "opacity": "123",
            }
            json.dump(stylesheet_vars, vars_file, indent=4)

    with open(qss_fp, "r") as stylesheet:
        stylesheet_str = stylesheet.read()
        for var, value in stylesheet_vars.items():
            stylesheet_str = stylesheet_str.replace(f"@{var}", value)
        qapp.setStyleSheet(stylesheet_str)


class AppMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCentralWidget(MainTabWidget())
        self.setWindowTitle("StudyCoordinator")
        self.icon = QtGui.QIcon()
        for size in (2**n for n in range(4, 9)):
            print(size)
            self.icon.addFile(f"icon_{size}", QtCore.QSize(size, size))
        self.setWindowIcon(self.icon)

    def reload(self):
        for task in asyncio.all_tasks():
            task.cancel()
        try:
            self.centralWidget().email_checker.stop()
        except AttributeError:
            pass
        self.centralWidget().deleteLater()
        self.setCentralWidget(MainTabWidget())
        self.centralWidget().setCurrentWidget(self.centralWidget().settings_widget)
        apply_stylesheet(app, "styles.qss", "qss_vars.json")


class MainTabWidget(QtWidgets.QTabWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.todo_widget = TodoMainScroll()
        self.addTab(self.todo_widget, "To-do list")
        self.todo_widget = self.todo_widget.widget()

        self.break_timer_widget = MainBreakTimerWidget()
        self.addTab(self.break_timer_widget, "Break and Study Timer")

        self.settings_widget = SettingsWidget()
        self.settings_widget.updated.connect(lambda: self.parent().reload())
        self.addTab(self.settings_widget, "Settings")
        self.setAcceptDrops(True)

        try:
            if Setting.get_or_create("gc_email_cards", "False").value == "True":
                print("STARTING GC EMAILS")
                self.email_checker = self.TodoCardEmailChecker(self)
                self.email_checker.start()
            else:
                print("NOT STARTING GC EMAILS")
        except socket.gaierror:
            if Setting.get_or_create("Offline Notification", "True") == "True":
                mb = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Offline",
                                           "Unable to connect to the internet. Some features, such as auto-generated "
                                           "to-do cards from Google Classroom emails, may be unavailable. This message"
                                           " can be disabled in the settings menu.")
                mb.exec_()

        except imaplib.IMAP4.error as e:
            if str(e) == "b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)'":
                mb = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Invalid Email Credentials",
                                           "Your email login information is incorrect. Auto-generated to-do cards "
                                           "from Google Classroom emails will be unavailable. You can disable "
                                           "Google Classroom emails in settings.")
                mb.exec_()
            else:
                raise

        except ConnectionRefusedError as e:
            mb = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Invalid IMAP URL",
                                       "The IMAP url provided in settings is invalid. Auto-generated to-do cards "
                                       "from Google Classroom emails will be unavailable. You can disable "
                                       "Google Classroom emails in settings.")
            mb.exec_()

    class TodoCardEmailChecker(email_checking.EmailChecker):
        def __init__(self, main_tab_widget):
            self.upper = main_tab_widget
            super().__init__()

        def on_new_assignment(self, title, subject, date, description, **kwargs):
            list_name = Session.query(Setting).filter(Setting.name == "Assignments List").first().value
            list_model = Session.query(TodoListModel).filter(TodoListModel.title == list_name).first()
            try:
                print(self.upper.todo_widget.lists)
                list_widget = self.upper.todo_widget.lists[list_model.id]
                model = TodoCardModel(list_model, title, description, date, labels=[TodoLabelModel.get_or_create(subject, color=f'#{"".join((random.choice(list("0123456789ABCDEF")) for i in range(6)))}')])
                list_widget.add_card(TodoCardWidget(model))
            except KeyError:
                box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, "Invalid List",
                                            f'Invalid list "{list_name.title}" selected as Assignments List. Please '
                                            f"select another in settings. You can also disable google classroom emails "
                                            f"integration there")
                box.exec_()
                raise self.ExitError("Invalid list")
            print("DONE")

        def on_new_material(self, title, subject, description, **kwargs):
            list_name = Session.query(Setting).filter(Setting.name == "Materials List").first().value
            list_model = Session.query(TodoListModel).filter(TodoListModel.title == list_name).first()
            try:
                list_widget = self.upper.todo_widget.lists[list_model.id]
                model = TodoCardModel(list_model, title, description, None, labels=[TodoLabelModel.get_or_create(subject, color=f'#{"".join((random.choice("0123456789ABCDEF") for _ in range(6)))}')])
                list_widget.add_card(TodoCardWidget(model))
            except KeyError:
                box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, "Invalid List",
                                            f'Invalid list "{list_name.title}" selected as Materials List. Please '
                                            f"select another in settings. You can also disable google classroom emails "
                                            f"integration there")
                box.exec_()
                raise self.ExitError("Invalid list")


apply_stylesheet(app, "styles.qss", "qss_vars.json")

root = AppMainWindow()
root.show()
app.exec_()
