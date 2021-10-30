import textwrap
import typing
from PySide2 import QtWidgets, QtCore, QtGui
from utils.widgets import HBoxFrame, UpdatingLineEdit, ColorSelectWidget, BaseFormDialog, DeleteAction, HiddenLineEdit, ImageBackgroundDialog
from utils import style_selector_widgets as styles
import json
import datetime
from project_sqlalchemy_globals import Session
from .models import TodoListModel, TodoCardModel, TodoLabelModel
import asyncio
from settings.models import Setting
from utils.field_widgets import ColorSelectField, LineEditField

# TODO: Re-organize. Place each model and its widget in its own file, including dialogues and other necessary objects. Then, combine the object and widget classes into one class, and do everything through that.


class TodoListWidget(styles.PrimaryColorWidget):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.holder = None
        self.card_widgets = []
        self.new_card_index = len(self.model.cards)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.title_label = UpdatingLineEdit(lambda w: self.set_title(w.text()), self.model.title)
        self.title_label.setFrame(False)
        self.layout().addWidget(self.title_label)

        self.setFrameStyle(1)
        # b = QtWidgets.QGraphicsDropShadowEffect()
        # self.setGraphicsEffect(b)
        print(self.graphicsEffect())
        self.setFixedWidth(225)
        self.setAcceptDrops(True)

        for card in sorted(self.model.cards, key=lambda c: c.position):
            card = TodoCardWidget(card)
            self.card_widgets.append(card)
            self.layout().addWidget(card)

        self.layout().addWidget(AddCardWidget(self))
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)  # fit-contents

        self.empty_card = QtWidgets.QFrame()
        self.empty_card.setFixedWidth(205)
        self.empty_card.setFixedHeight(50)

    def set_title(self, title: str):
        self.model.title = title
        self.model.save()

    def add_card(self, card_widget, index=None):
        if index is None:
            index = len(self.model.cards) + 1

        card_widget.model.position = index
        card_widget.model.save()

        for widget in self.card_widgets:
            if widget.model.position >= card_widget.model.position:
                widget.model.position += 1
                widget.model.save()

        self.model.add_card(card_widget.model)
        self.layout().insertWidget(index, card_widget)
        self.card_widgets.append(card_widget)
        self.holder.cards[card_widget.model.id] = card_widget

    def remove_card(self, card_widget, delete_model=True):
        self.layout().removeWidget(card_widget)
        self.card_widgets.remove(card_widget)
        self.model.remove_card(card_widget.model)

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/json"):
            event.acceptProposedAction()
            data = json.loads(event.mimeData().data("application/json").data().decode())
            card = Session.query(TodoCardModel).filter(TodoCardModel.id == data["card_id"]).first()
            self.holder.lists[data["og_list_id"]].remove_card(self.holder.cards[card.id])
            print("+"*100)
            print(card.title)
            self.add_card(self.holder.cards[card.id], self.new_card_index)
            self.layout().removeWidget(self.empty_card)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/json"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        self.new_card_index = self.get_drag_event_card_index(event)
        self.layout().insertWidget(self.new_card_index, self.empty_card)

    def get_drag_event_card_index(self, event):
        y = event.answerRect().y() - 35  # get y pos of widget (-35 accounts for the list title)
        i = 0
        # subtract card heights until you reach <= 0, that card is where to place the empty card
        for height in [widget.height() for widget in self.card_widgets] + [35]:  # 35 accounts for the "add card" widget
            i += 1
            y -= height
            if y <= 0:
                break
        return i

    def dragLeaveEvent(self, event):
        self.layout().removeWidget(self.empty_card)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        a = DeleteAction(self)
        menu.addAction(a)
        menu.exec_(event.globalPos())
        if a.widget_deleted:
            for l in ("Assignments List", "materials List"):
                s = Setting.get(l)
                if s is not None and s.value == self.model.title:
                    s.set_value(None)


class TodoCardWidget(styles.AccentColorWidget):
    class LabelContainer(QtWidgets.QFrame):
        def __init__(self, labels, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.setLayout(QtWidgets.QVBoxLayout())
            self.layout().setContentsMargins(0, 0, 0, 0)

            # print(len(labels), list(range(0, len(labels))), list(range(5, len(labels), 5)))
            last = 0
            for i in range(5, len(labels), 5):
                a = QtWidgets.QFrame()
                a.setLayout(QtWidgets.QHBoxLayout())
                a.layout().setContentsMargins(0, 0, 0, 0)

                for label in labels[last:i]:
                    a.layout().addWidget(self.CardLabelWidget(label))
                    # a.layout().addWidget(QtWidgets.QLabel(label.name))
                last = i
                self.layout().addWidget(a)

            a = QtWidgets.QFrame()
            a.setLayout(QtWidgets.QHBoxLayout())
            a.layout().setContentsMargins(0, 0, 0, 0)
            for label in labels[last:len(labels)]:
                a.layout().addWidget(self.CardLabelWidget(label))

            while a.layout().count() != 5:
                a.layout().addWidget(self.CardLabelSpacer())
            self.layout().addWidget(a)

        class CardLabelWidget(QtWidgets.QFrame):
            def __init__(self, label, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.setStyleSheet(f"background-color: {label.color}; border-radius: 4px;")
                self.setFixedWidth(32)
                self.setFixedHeight(8)

        class CardLabelSpacer(QtWidgets.QFrame):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.setStyleSheet(f"background-color: rgba(0, 0, 0, 0)")
                self.setFixedWidth(32)
                self.setFixedHeight(8)

    class DueDateDisplay(QtWidgets.QFrame):
        def __init__(self, date_time, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.date_time = date_time

            self.setFrameStyle(1)
            self.setStyleSheet("border-width: 5px")
            self.setFixedSize(50, 25)

            self.setLayout(QtWidgets.QHBoxLayout())
            self.layout().setContentsMargins(7, 0, 0, 0)

            self.layout().addWidget(QtWidgets.QLabel(date_time.strftime("%b %d")))

            asyncio.get_running_loop().create_task(self.check_date())

        async def check_date(self):
            while True:
                if (self.date_time - datetime.datetime.now()) <= datetime.timedelta(days=0):
                    self.setStyleSheet("background-color: rgba(120, 0, 0, 90)")
                elif (self.date_time - datetime.datetime.now()) <= datetime.timedelta(days=1):
                    self.setStyleSheet("background-color: rgba(250, 220, 120, 90)")
                await asyncio.sleep(5000)

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

        self.setFrameStyle(1)
        self.ui_refresh(init=True)

    def ui_refresh(self, init=False):
        if not init:
            for w in self.findChildren(QtWidgets.QWidget):
                w.deleteLater()

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.setFixedWidth(225)

        if len(self.model.labels) > 0:
            self.layout().addWidget(self.LabelContainer(self.model.labels))

        title_qlabel = HiddenLineEdit(self.model.title if len(self.model.title) < 34 else f"{self.model.title[:33]}...")
        title_qlabel.setFrame(False)
        title_qlabel.setFixedWidth(200)
        self.layout().addWidget(title_qlabel)

        if self.model.due_date is not None:
            self.layout().addWidget(self.DueDateDisplay(self.model.due_date))

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            a = CardDialog(self.model, widget=self)
            a.exec_()

    def mouseMoveEvent(self, event):
        drag = QtGui.QDrag(self)
        mimeData = QtCore.QMimeData()
        mimeData.setData("application/json", QtCore.QByteArray(json.dumps({"og_list_id": self.model.list.id, "card_id": self.model.id}).encode()))
        drag.setMimeData(mimeData)

        drag.exec_()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        a = DeleteAction(self)
        menu.addAction(a)
        menu.addSeparator()
        menu.exec_(event.globalPos())
        if a.widget_deleted:
            print("widget_deleted")
            self.parentWidget().remove_card(self, delete_model=False)  # model is already deleted by the action.


class AddCardWidget(QtWidgets.QFrame):
    def __init__(self, parent_list_widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_list_widget = parent_list_widget
        self.setFrameStyle(1)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(QtWidgets.QLabel("+    Add Card"))
        self.setFixedWidth(221)
        self.setFixedHeight(35)

    def mousePressEvent(self, event):
        a = CardDialog(TodoCardModel, parent_list=self.parent_list_widget)
        a.exec_()


class CreateListWidget(styles.PrimaryColorWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFrameStyle(1)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(QtWidgets.QLabel("+    Create List"))
        self.setFixedWidth(255)
        self.setFixedHeight(40)

    def mousePressEvent(self, event):
        a = ListDialog(self.parent().parent())
        a.exec_()


class CardDialog(BaseFormDialog):
    """
    card needs to be an instance or type
    """

    class DueDateWidget(QtWidgets.QFrame):
        def __init__(self, qdatetime=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setLayout(QtWidgets.QHBoxLayout())
            self.has_datetime = qdatetime is not None

            self.datetime_edit = QtWidgets.QDateTimeEdit(qdatetime)
            self.datetime_edit.setCalendarPopup(True)
            self.datetime_edit.setDisplayFormat("MM/dd/yyyy h:mm ap")

            self.add_due_date_button = QtWidgets.QPushButton("Add Due Date")
            self.add_due_date_button.pressed.connect(self.add_due_date)

            self.remove_due_date_button = QtWidgets.QPushButton("Remove Due Date")
            self.remove_due_date_button.pressed.connect(self.remove_due_date)

            if not self.has_datetime:
                self.layout().addWidget(self.add_due_date_button)
            else:
                self.layout().addWidget(self.datetime_edit)
                self.layout().addWidget(self.remove_due_date_button)

        def remove_due_date(self):
            print("em")
            self.has_datetime = False
            self.layout().removeWidget(self.datetime_edit)
            self.datetime_edit.hide()

            self.layout().removeWidget(self.remove_due_date_button)
            self.remove_due_date_button.hide()

            self.layout().addWidget(self.add_due_date_button)
            self.add_due_date_button.show()

        def add_due_date(self):
            print("ad")
            self.has_datetime = True
            # have to re-create because for some reason setDateTime() doesn't work, but this does..
            self.datetime_edit = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
            print(self.datetime_edit.dateTime())

            self.layout().addWidget(self.datetime_edit)
            self.datetime_edit.show()

            self.layout().addWidget(self.remove_due_date_button)
            self.remove_due_date_button.show()

            self.layout().removeWidget(self.add_due_date_button)
            self.add_due_date_button.hide()

            self.update()

        def dateTime(self):
            if self.has_datetime:
                return self.datetime_edit.dateTime()

    def __init__(self, card: typing.Union[type, TodoCardModel], widget=None, parent_list=None, *args, **kwargs):
        self.parent_list_widget = parent_list
        self.widget = widget

        if isinstance(card, TodoCardModel):
            if card.due_date is not None:
                b = card.due_date.strftime("%m/%d/%Y %H:%M %p")
                a = QtCore.QDateTime.fromString(b, "MM/dd/yyyy HH:mm ap")
                print(b, "|", a)
                # https://doc.qt.io/qt-5/qdatetime.html#fromString

                due_date_widget = self.DueDateWidget(a)
            else:
                due_date_widget = self.DueDateWidget()

            super().__init__(card, {"title": (QtWidgets.QLineEdit(card.title), "text()"),
                                    "description": (QtWidgets.QTextEdit(card.description), "document().toPlainText()"),
                                    "labels": (LabelSelectWidget(card.labels), "selected_labels"),
                                    "due_date": (due_date_widget, "dateTime()")},
                             image_fp=Setting.get("Background Image").value, *args, **kwargs)

        else:
            super().__init__(card, {"title": (QtWidgets.QLineEdit(), "text()"),
                                    "description": (QtWidgets.QTextEdit(), "document().toPlainText()"),
                                    "labels": (LabelSelectWidget(), "selected_labels"),
                                    "due_date": (self.DueDateWidget(), "dateTime()")},
                             image_fp=Setting.get("Background Image").value, *args, **kwargs)

    def save(self):  # noqa
        model_attrs = self.generate_attrs_dict()
        if model_attrs["due_date"] is not None:
            model_attrs["due_date"] = model_attrs["due_date"].toPython()

        if isinstance(self.model, type):
            model_attrs["position"] = len(self.parent_list_widget.model.cards) + 1

        model_attrs["parent_list"] = None
        print(model_attrs)
        model = super().save(model_attrs, accept=False)
        if self.parent_list_widget is not None:
            self.parent_list_widget.add_card(TodoCardWidget(model))

        if self.widget is not None:
            self.widget.ui_refresh()  # refresh card

        self.accept()


class LabelWidget(QtWidgets.QFrame):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

        self.setLayout(QtWidgets.QHBoxLayout())
        self.name_label = QtWidgets.QLabel(self.model.name)
        self.layout().addWidget(self.name_label)

        self.setStyleSheet(f"background-color: {self.model.color}; border-radius: 5px;")
        self.setFixedWidth(125)
        self.setFixedHeight(30)
        self.setFrameStyle(1)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        a = DeleteAction(self)
        menu.addAction(a)
        menu.addSeparator()
        menu.exec_(event.globalPos())


class LabelSelectOption(LabelWidget):
    def __init__(self, parent_select, model, *args, **kwargs):
        super().__init__(model, *args, **kwargs)
        self.parent_select = parent_select
        self.name_label.setText(f"✓     {self.model.name}" if self.model in self.parent_select.selected_labels else self.model.name)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.model in self.parent_select.selected_labels:
                self.parent_select.selected_labels.remove(self.model)
                self.name_label.setText(self.model.name)

            else:
                self.parent_select.selected_labels.append(self.model)
                self.name_label.setText(f"✓     {self.model.name}")

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        del_ac = DeleteAction(self)
        menu.addAction(del_ac)

        edit_ac = QtWidgets.QAction("Edit")
        edit_ac.triggered.connect(lambda: LabelDialog(self.model).exec_())
        menu.addAction(edit_ac)

        menu.exec_(event.globalPos())
        if del_ac.widget_deleted:
            self.parent_select.selected_labels.remove(self.model)


class LabelSelectWidget(styles.PrimaryColorWidget):
    def __init__(self, selected_labels=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_labels = [] if selected_labels is None else selected_labels

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)  # fit-contents
        self.layout().addWidget(QtWidgets.QLabel("Select a label:"))

        self.setFixedWidth(205)
        self.setFrameStyle(1)
        for label in Session.query(TodoLabelModel).all():
            self.layout().addWidget(LabelSelectOption(self, label))

        self.layout().addWidget(CreateLabelWidget(self))


class CreateLabelWidget(QtWidgets.QFrame):
    def __init__(self, parent_select, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_select = parent_select
        self.setFrameStyle(1)
        self.setFixedWidth(125)
        self.setFixedHeight(30)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(QtWidgets.QLabel("+  Create Label"))

    def mouseReleaseEvent(self, event):
        dialog = LabelDialog()
        dialog.exec_()
        self.parent_select.layout().insertWidget(self.parent_select.layout().count() - 1,
                                                 LabelSelectOption(self.parent_select, dialog.created))


class LabelDialog(BaseFormDialog):
    def __init__(self, model=TodoLabelModel, *args, **kwargs):
        if isinstance(model, type):
            super().__init__(model, {"name": (LineEditField(), "data()"),
                                     "color": (ColorSelectField(), "data()")},
                             image_fp=Setting.get("Background Image").value, *args, **kwargs)
        else:
            super().__init__(model, {"name": (LineEditField(model.name), "data()"),
                                     "color": (ColorSelectField(model.color), "data()")},
                             image_fp=Setting.get("Background Image").value, *args, **kwargs)

    def save(self):  # noqa
        self.created = super().save(accept=False)
        self.accept()


class ListDialog(BaseFormDialog):
    def __init__(self, parent_holder_widget, *args, **kwargs):
        self.parent_holder_widget = parent_holder_widget
        super().__init__(TodoListModel, {"title": (QtWidgets.QLineEdit(), "text()")},
                         image_fp=Setting.get("Background Image").value, *args, **kwargs)

    def generate_attrs_dict(self):
        ret = super().generate_attrs_dict()
        title = ret["title"]
        assert Session.query(TodoListModel).filter(TodoListModel.title == title).one_or_none() is None
        return ret


    def save(self):  # noqa
        try:
            model = super().save(accept=False)
            self.parent_holder_widget.add_list(TodoListWidget(model))
            self.accept()
        except AssertionError:
            e = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Invalid list name",
                                      "A list with this name already exists. Please select another.")
            e.exec_()


class TodoMainScroll(QtWidgets.QScrollArea):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWidget(MainTodoWidget())
        self.setWidgetResizable(True)
        self.bg = QtGui.QPixmap(Setting.get_or_create("Background Image", "bg.jpg").value)
        self.bg = self.bg.scaled(self.width(), self.height(), QtCore.Qt.KeepAspectRatioByExpanding)
        print(self.viewport())

    def paintEvent(self, arg__1: QtGui.QPaintEvent):  # Special Case since its a scrollarea.
        super().paintEvent(arg__1)
        painter = QtGui.QPainter(self.viewport())
        painter.drawPixmap(0, 0, self.bg)

    def resizeEvent(self, event) -> None:
        self.bg = QtGui.QPixmap(Setting.get("Background Image").value)
        self.bg = self.bg.scaled(event.size().width(), event.size().height(), QtCore.Qt.KeepAspectRatioByExpanding)


class MainTodoWidget(styles.InvisibleBackgroundWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lists = {}
        self.cards = {}

        self.hbox = HBoxFrame()
        self.hbox.setLayout(QtWidgets.QHBoxLayout())

        for list_widget in self.lists:
            self.hbox.layout().addWidget(list_widget, alignment=QtCore.Qt.AlignTop)  # Noqa

        self.hbox.layout().addWidget(CreateListWidget(), alignment=QtCore.Qt.AlignTop)  # Noqa
        self.hbox.layout().addStretch()

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.hbox, alignment=QtCore.Qt.AlignTop)  # Noqa

        list_models = Session.query(TodoListModel).all()
        # print(list_models, len(list_models))
        if len(list_models) == 0:
            list_models = [TodoListModel("To-Do"),
                           TodoListModel("Doing"),
                           TodoListModel("Done")]
            for todo_list in list_models:
                Session.add(todo_list)
                Session.commit()
                self.add_list(TodoListWidget(todo_list))
        else:
            for todo_list in list_models:
                self.add_list(TodoListWidget(todo_list))

        # print([a.position for a in Session.query(TodoCardModel).order_by(TodoCardModel.position).all()])

    def add_list(self, list_widget):
        self.lists[list_widget.model.id] = list_widget
        list_widget.holder = self
        self.hbox.layout().insertWidget(len(self.lists) - 1, list_widget, alignment=QtCore.Qt.AlignTop)
        for card_widget in list_widget.card_widgets:
            self.cards[card_widget.model.id] = card_widget
