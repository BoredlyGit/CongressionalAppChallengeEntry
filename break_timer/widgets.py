from PySide2 import QtWidgets, QtCore, QtGui
from project_sqlalchemy_globals import Session
from settings.models import Setting
import qasync
import asyncio
from utils import style_selector_widgets as styles
from utils.widgets import HBoxFrame, ImageBackgroundWidget


class BreakTimerWidget(styles.PrimaryColorWidget):
    def __init__(self, *args, **kwargs):
        self.paused = False
        self.break_time = [int(value) for value in Setting.get_or_create("Break Time", "0:5:0").value.split(":")]
        self.study_time = [int(value) for value in Setting.get_or_create("Study Time", "0:25:0").value.split(":")]
        self.mode = "study"
        self.current_time = getattr(self, f"{self.mode}_time")

        super().__init__(*args, **kwargs)
        self.setFrameStyle(2)
        self.setFixedHeight(300)
        self.setFixedWidth(600)
        self.setLayout(QtWidgets.QVBoxLayout())

        self.mode_label = QtWidgets.QLabel(self.mode.capitalize())
        self.mode_label.setStyleSheet("font-size: 35px")
        self.layout().addWidget(self.mode_label, alignment=QtCore.Qt.AlignCenter)  # noqa

        self.time_label = QtWidgets.QLabel(":".join(str(value).zfill(2) for value in self.current_time))
        self.time_label.setStyleSheet("font-size: 50px")
        self.layout().addWidget(self.time_label, alignment=QtCore.Qt.AlignCenter)  # noqa

        self.buttons = HBoxFrame()

        self.switch_button = QtWidgets.QPushButton("Switch to Break")
        self.switch_button.pressed.connect(lambda: self.set_mode("study" if self.mode == "break" else "break"))
        self.switch_button.setFixedWidth(125)
        self.buttons.layout().addWidget(self.switch_button, alignment=QtCore.Qt.AlignCenter)  # noqa

        self.pause_button = QtWidgets.QPushButton("Start")
        self.pause_button.pressed.connect(self.toggle_pause)
        self.buttons.layout().addWidget(self.pause_button, alignment=QtCore.Qt.AlignCenter)  # noqa

        self.layout().addWidget(self.buttons, alignment=QtCore.Qt.AlignCenter)  # noqa

        self.task = None

    def set_mode(self, mode):
        self.mode = mode
        self.current_time = getattr(self, f"{self.mode}_time")
        self.time_label.setText(":".join(str(value).zfill(2) for value in self.current_time))
        self.mode_label.setText(self.mode.capitalize())
        self.switch_button.setText(f'Switch to {"Study" if self.mode == "break" else "Break"}')

        if self.task is not None:
            self.task.cancel()
            self.task = asyncio.get_running_loop().create_task(self.start())

    def change_time(self, increment):
        time = [int(value) for value in self.time_label.text().split(":")]
        time[2] += increment
        for i in reversed(range(0, 3)):
            if time[i] > 60:
                time[i - 1] += time[i] // 60
                time[i] = time[i] % 60

            if time[i] < 0:  # -1
                time[i - 1] += time[i] // 60  # idk why but -1//60 = -1 instead of 0 so no need to subtract 1.
                time[i] = time[i] % 60  # idk why but -1 % 60 = 59, so no need to add 60.

        if sum(time) < 0:
            raise ArithmeticError("Time cannot be negative!")

        self.time_label.setText(":".join(str(value).zfill(2) for value in time))

    async def start(self):
        time_in_seconds = 3600 * self.current_time[0] + 60 * self.current_time[1] + self.current_time[2]
        for sec in range(time_in_seconds):
            for centisec in range(100):
                while self.paused:
                    await asyncio.sleep(0.01)
                await asyncio.sleep(0.01)

            self.change_time(-1)
        await asyncio.sleep(1)
        mb = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Break timer",
                                   f"Time {'for a break' if self.mode == 'study' else 'to study'}!")
        mb.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        mb.exec_()
        print("f")
        self.set_mode("study" if self.mode == "break" else "break")

    def toggle_pause(self):
        if self.task is None:
            self.task = asyncio.get_running_loop().create_task(self.start())
            self.pause_button.setText("Pause")
            return

        self.paused = not self.paused
        if self.paused:
            self.pause_button.setText("Start")
        else:
            self.pause_button.setText("Pause")


class MainBreakTimerWidget(ImageBackgroundWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(image_fp=Setting.get("Background Image").value, *args, *kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(BreakTimerWidget(), alignment=QtCore.Qt.AlignCenter)  # noqa
