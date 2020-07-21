from enum import Enum

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from action import ActionLabel
from utils import *


class MySignals(QObject):
    jump_to = pyqtSignal(int, int, Enum)  # index,bias,emitter
    follow_to = pyqtSignal(Enum, int)  # emitter,index
    video_pause_or_resume = pyqtSignal()
    video_pause = pyqtSignal()
    video_start = pyqtSignal(int)  # stopAt

    label_selected = pyqtSignal(ActionLabel, Enum)
    label_created = pyqtSignal(ActionLabel, Enum)
    label_delete = pyqtSignal(ActionLabel, Enum)
    label_cells_delete = pyqtSignal(dict, Enum)
    labeled_selected = pyqtSignal(ActionLabel, Enum)
    # labeled_update = pyqtSignal(ActionLabel, Enum)
    labeled_delete = pyqtSignal(list, Enum)
    action_add = pyqtSignal(Enum)

    timer_video = QTimer()

    @classmethod
    def timer_start(cls, Tms=50):
        cls.timer_video.start(Tms)

    def slot_toTest(self):
        Log.info('here')


class Settings:
    pass
    v_interval = None


class Emitter(Enum):
    TIMER = 1
    T_HHEADER = 2
    T_HSCROLL = 3
    T_WHEEL = 4
    T_LABEL = 5
    T_LABELED = 6
    T_TEMP = 7
    INPUT_JUMPTO = 10


mySignals = MySignals()
g_get_action = lambda: (_ for _ in ()).throw(NotImplementedError('Please override this!'))
