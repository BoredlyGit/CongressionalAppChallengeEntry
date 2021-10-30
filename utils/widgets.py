from PySide2 import QtWidgets, QtCore, QtGui
from project_sqlalchemy_globals import Session


class HBoxFrame(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())


class VBoxFrame(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLayout(QtWidgets.QVBoxLayout())


def UpdatingWidget(widget):
    class _UpdatingWidget(widget):
        def __init__(self, on_update, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
            self.on_update = on_update

        def focusOutEvent(self, event):
            super().focusOutEvent(event)
            self.on_update(self)
    return _UpdatingWidget


class UpdatingLineEdit(UpdatingWidget(QtWidgets.QLineEdit)):
    pass


class HiddenLineEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setFrame(False)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)


class ColorSelectWidget(QtWidgets.QFrame):
    def __init__(self, default="#FFFFF", *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("defauld: ", default)
        self.color_dialog = QtWidgets.QColorDialog()
        self.selected_color = default
        self.setStyleSheet(f"background-color: {default}")
        self.setFrameStyle(1)
        self.setFixedWidth(75)
        self.setFixedHeight(20)

    def mouseReleaseEvent(self, event):
        color = self.color_dialog.getColor()
        self.selected_color = color.name()
        self.setStyleSheet(f"background-color: {self.selected_color}")


class DeleteAction(QtWidgets.QAction):
    def __init__(self, widget, *args, **kwargs):
        super().__init__("Delete", *args, **kwargs)
        self.widget = widget
        self.widget_deleted = False
        self.triggered.connect(lambda: self.delete_widget())

    def delete_widget(self):
        try:
            Session.delete(Session.query(type(self.widget.model)).filter(type(self.widget.model).id == self.widget.model.id).first())
            Session.commit()
            print("wasd", Session.query(type(self.widget.model)).filter(type(self.widget.model).id == self.widget.model.id).first())
        except AttributeError:
            print("atterr")
        self.widget.deleteLater()
        self.widget_deleted = True


class ImageBackgroundWidget(QtWidgets.QFrame):
    def __init__(self, image_fp, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_fp = image_fp
        self.bg = QtGui.QPixmap(image_fp)
        self.bg = self.bg.scaled(self.width(), self.height(), QtCore.Qt.KeepAspectRatioByExpanding)

    def paintEvent(self, event: QtGui.QPaintEvent):  # Special Case since its a scrollarea.
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, 0, self.bg)

    def resizeEvent(self, event) -> None:
        self.bg = QtGui.QPixmap(self.bg_fp)
        self.bg = self.bg.scaled(event.size().width(), event.size().height(), QtCore.Qt.KeepAspectRatioByExpanding)


class ImageBackgroundDialog(QtWidgets.QDialog):
    def __init__(self, image_fp, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_fp = image_fp
        self.bg = QtGui.QPixmap(image_fp)
        self.bg = self.bg.scaled(self.width(), self.height(), QtCore.Qt.KeepAspectRatioByExpanding)

    def paintEvent(self, event: QtGui.QPaintEvent):  # Special Case since its a scrollarea.
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, 0, self.bg)

    def resizeEvent(self, event) -> None:
        self.bg = QtGui.QPixmap(self.bg_fp)
        self.bg = self.bg.scaled(event.size().width(), event.size().height(), QtCore.Qt.KeepAspectRatioByExpanding)


class BaseFormDialog(ImageBackgroundDialog):
    def __init__(self, model, fields, *args, **kwargs):
        """
        The fields dict should be ordered like this: {"{attribute}": (Widget(), "{python.path.to.data.attribute()}")}
        Ex:
            {"description": (QtWidgets.QTextEdit(), "document().toPlainText()")}
        """
        super().__init__(*args, **kwargs)
        self.model = model
        self.fields = fields

        self.setLayout(QtWidgets.QFormLayout())
        for attribute, widget in fields.items():
            self.layout().addRow(f"{attribute.replace('_', ' ').capitalize()}:", widget[0])

        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.clicked.connect(self.save)
        self.layout().addWidget(self.save_button)

    def generate_attrs_dict(self):
        return {attr: eval(f"widget[0].{widget[1]}") for attr, widget in self.fields.items()}

    def save(self, attrs=None, accept=True):
        model_attrs = self.generate_attrs_dict() if attrs is None else attrs
        if isinstance(self.model, type):
            self.model = self.model(**model_attrs)
        else:
            for attr, value in model_attrs.items():
                setattr(self.model, attr, value)
            self.model.save()  # save is implicit on model creation

        if accept:
            self.accept()
        else:
            return self.model