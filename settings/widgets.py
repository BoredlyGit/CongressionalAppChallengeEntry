import json
from PySide2 import QtWidgets, QtCore, QtGui
from .models import Setting
from todo_lists.models import TodoListModel
from utils.field_widgets import LineEditField, SliderField, ComboBoxField, ColorSelectField, TimeField, FilePathField, PasswordField, BooleanField
from utils.widgets import ImageBackgroundWidget
from project_sqlalchemy_globals import Session
from collections import OrderedDict
from datetime import datetime


class SettingsWidget(ImageBackgroundWidget):  # just hardcode it, i give up
    updated = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(image_fp=Setting.get("Background Image").value, *args, **kwargs)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.fields = OrderedDict({
            "Todo Lists": (
                # (name, setting_model, widget, data location)
                ("Automatically create to-do cards\n from Google Classroom emails", Setting.get_or_create("gc_email_cards", "False"), BooleanField(Setting.get("gc_email_cards").value)),
                ("Notify me if I'm offline", Setting.get_or_create("Offline Notification", "True"), BooleanField(Setting.get("Offline Notification").value)),
                ("Email IMAP URL", Setting.get_or_create("Email IMAP URL"), LineEditField(Setting.get("Email IMAP URL").value)),
                ("Email Address", Setting.get_or_create("Email Address"), LineEditField(Setting.get("Email Address").value)),
                ("Email Password", Setting.get_or_create("Email Password"), PasswordField(Setting.get("Email Password").value)),
                ("Assignments List", Setting.get_or_create("Assignments List"), ComboBoxField([l.title for l in Session.query(TodoListModel).all()])),
                ("Materials List", Setting.get_or_create("Materials List"), ComboBoxField([l.title for l in Session.query(TodoListModel).all()])),
            ),
            "Break and Study Timer": (
                ("Break Time", Setting.get_or_create("Break Time", "0:5:0"), TimeField(*Setting.get("Break Time").value.split(":"))),
                ("Study Time", Setting.get_or_create("Study Time", "0:25:0"), TimeField(*Setting.get("Study Time").value.split(":")))
            ),
            "Appearance": (
                ("Primary Color", Setting.get_or_create("Primary Color", "#FFFFFF"), ColorSelectField(Setting.get("Primary Color").value)),
                ("Accent Color", Setting.get_or_create("Accent Color", "#000000"), ColorSelectField(Setting.get("Accent Color").value)),
                ("Opacity", Setting.get_or_create("Opacity", 100), SliderField(Setting.get("Opacity").value, (0, 255), QtCore.Qt.Horizontal)),
                ("Background Image", Setting.get_or_create("Background Image", "bg.jpg"), FilePathField(Setting.get("Background Image").value)),
            ),
        })

        for category in self.fields:
            box = QtWidgets.QGroupBox(category)
            box.setLayout(QtWidgets.QFormLayout())
            for row in self.fields[category]:
                box.layout().addRow(row[0], row[2])
            self.layout().addWidget(box)

        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.clicked.connect(self.save)
        self.layout().addWidget(self.save_button)

        print(f"eee {self.fields}")

    def save(self):
        def hex_to_rgb(hex_val):
            hex_val = f"#{hex_val}" if not hex_val.startswith("#") else hex_val
            qcolor = QtGui.QColor(hex_val)
            return f"{qcolor.red()}, {qcolor.green()}, {qcolor.blue()}"

        for category, rows in self.fields.items():
            for row in rows:
                print(f"saving: {row[0]} | {row[2].data()}")
                row[1].set_value(row[2].data())  # This works only since all fields use utils.field_widgets widgets.

        with open("qss_vars.json", "r") as vars_file:
            qss_vars = json.load(vars_file)

        with open("qss_vars.json", "w") as vars_file:
            qss_vars["primary_color"] = hex_to_rgb(Setting.get("Primary Color").value)
            qss_vars["accent_color"] = hex_to_rgb(Setting.get("Accent Color").value)
            qss_vars["opacity"] = str(Setting.get("Opacity").value)
            json.dump(qss_vars, vars_file, indent=4)

        self.updated.emit()
