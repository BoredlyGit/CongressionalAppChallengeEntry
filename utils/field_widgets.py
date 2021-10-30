"""
Provides Widgets to be used in dialogues and settings, with a standardized function to return the data
"""
from PySide2 import QtWidgets, QtCore
from .widgets import ColorSelectWidget
from utils import style_selector_widgets as styles


class BaseFieldWidget():
    def data(self):
        pass


class LineEditField(QtWidgets.QLineEdit, BaseFieldWidget):
    def data(self):
        return self.text()


class TextEditField(QtWidgets.QTextEdit, BaseFieldWidget):
    def data(self):
        return self.document().toPlainText()


class ComboBoxField(QtWidgets.QComboBox, BaseFieldWidget):
    def __init__(self, options=(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addItems(options)

    def data(self):
        return self.currentText()


class ColorSelectField(ColorSelectWidget, BaseFieldWidget):
    def data(self):
        return self.selected_color


class SelectMultipleField():
    pass  # SUggestion: move labelselect to this sort of thing?


class PasswordField(LineEditField, BaseFieldWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEchoMode(QtWidgets.QLineEdit.Password)


class TimeField(QtWidgets.QFrame, BaseFieldWidget):
    def __init__(self, hours=0, minutes=0, seconds=0):
        super().__init__()
        self.setLayout(QtWidgets.QHBoxLayout())

        self.hours_select = QtWidgets.QDoubleSpinBox()
        self.hours_select.setValue(float(hours))
        self.hours_select.setDecimals(0)
        self.layout().addWidget(self.hours_select, alignment=QtCore.Qt.AlignLeft)
        self.layout().addWidget(QtWidgets.QLabel(":"))

        self.minutes_select = QtWidgets.QDoubleSpinBox()
        self.minutes_select.setValue(float(minutes))
        self.minutes_select.setDecimals(0)
        self.layout().addWidget(self.minutes_select, alignment=QtCore.Qt.AlignLeft)
        self.layout().addWidget(QtWidgets.QLabel(":"))

        self.seconds_select = QtWidgets.QDoubleSpinBox()
        self.seconds_select.setValue(float(seconds))
        self.seconds_select.setDecimals(0)
        self.layout().addWidget(self.seconds_select, alignment=QtCore.Qt.AlignLeft)
        self.layout().addWidget(QtWidgets.QLabel("hh:mm:ss"))

        self.setFixedWidth(220)

    def data(self):
        return f"{int(self.hours_select.value())}:{int(self.minutes_select.value())}:{int(self.seconds_select.value())}"


class FilePathField(styles.PrimaryColorWidget, BaseFieldWidget):
    def __init__(self, file_path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_path = file_path
        self.file_label = QtWidgets.QLabel("Select a File" if file_path is None else file_path)

        self.file_dialog = QtWidgets.QFileDialog()
        self.file_dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.file_dialog.currentChanged.connect(lambda path: self.file_label.setText(path))

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.file_label)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.file_dialog.exec_()

    def data(self):
        if len(self.file_dialog.selectedFiles()) != 0:
            print(self.file_dialog.selectedFiles()[0])
            return self.file_dialog.selectedFiles()[0]
        else:
            return self.file_path


class SliderField(QtWidgets.QFrame, BaseFieldWidget):
    def __init__(self, init_value=0, _range=(0, 100), *sliders_args, **slider_kwargs):
        super().__init__()
        self.slider = QtWidgets.QSlider(*sliders_args, **slider_kwargs)
        self.slider.setRange(*_range)
        self.slider.setValue(int(init_value))

        self.label = QtWidgets.QLabel(f"{self.slider.value()}/{self.slider.maximum()}")
        self.slider.valueChanged.connect(lambda new: self.label.setText(f"{new}/{self.slider.maximum()}"))

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.slider)

    def data(self):
        return self.slider.value()


class BooleanField(QtWidgets.QCheckBox, BaseFieldWidget):
    def __init__(self, is_checked=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(is_checked, str):
            is_checked = False if is_checked == "False" else True
        self.setChecked(is_checked)

    def data(self):
        return str(self.isChecked())
