import collections
from random import random

import cv2
import typing
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import global_
from utils import *


class MyTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self)

        # myQAbstractItemModel = MyQAbstractItemModel(self)
        # proxyModel = QAbstractProxyModel(self)
        # proxyModel.setSourceModel(myQAbstractItemModel)
        # self.setModel(proxyModel)

        self.key_control_pressing = False
        self.mouse_pressing_hscrollbar = False
        self.hcenter_before_wheeling = None
        self.pressed_cell_pos = None
        self.entry_row_index = None
        self.cellClicked.connect(self.slot_cellClicked)
        self.cellDoubleClicked.connect(self.slot_cellDoubleClicked)
        self.cellActivated.connect(self.slot_cellActivated)
        self.itemSelectionChanged.connect(self.slot_itemSelectionChanged)
        self.cellPressed.connect(self.slot_cellPressed)

        # global_.mySignals.jump_to.connect(self.slot_jump_to)
        global_.mySignals.follow_to.connect(self.slot_follow_to)

    # FIXME
    def __init_later__(self):
        self.setHorizontalHeaderLabels([str(i) for i in range(self.columnCount())])

        header = self.horizontalHeader()
        header.sectionPressed.disconnect()
        header.sectionClicked.connect(self.slot_horizontalHeaderClicked)

        # self.horizontalScrollBar().mousePressEvent = self.slot_common_test # wrong
        self.horizontalScrollBar().installEventFilter(self)
        # self.horizontalScrollBar().sliderPressed.connect(lambda: print('slider pressed!'))
        self.horizontalScrollBar().sliderMoved.connect(self.slot_sliderMoved)

    def eventFilter(self, source, event):
        Log.debug('here', source, event)
        if source == self.horizontalScrollBar():
            if event.type() == QEvent.MouseButtonPress:
                self.mouse_pressing_hscrollbar = True
                global_.mySignals.video_pause.emit()
            elif event.type() == QEvent.MouseButtonRelease:
                self.mouse_pressing_hscrollbar = False
            # elif event.type() == QScrollBar.sliderPressed:
            #     Log.error('here')
            else:
                Log.error(event.type())
        return False

    def keyPressEvent(self, e: QKeyEvent) -> None:
        print(f'mytable {e} {e.key()} {e.type()}')
        if e.key() == Qt.Key_Control:
            self.key_control_pressing = True
            self.hcenter_before_wheeling = self._center_col()
        # elif e.key() == Qt.Key_Control:
        #     pass

    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        Log.debug('here', e.key())
        if e.key() == Qt.Key_Control:
            self.key_control_pressing = False
        elif e.key() in [Qt.Key_Backspace, Qt.Key_D]:
            self._del_selected_label()

    def wheelEvent(self, e: QWheelEvent) -> None:
        print(f'wheel{e.angleDelta()}')
        idler_forward = e.angleDelta().y() > 0
        if self.key_control_pressing:
            col_width = self.columnWidth(0)
            col_width += 3 if idler_forward else -3
            t_width = self.width()  # no vertical header
            cols = self.horizontalHeader().count()
            col_width_to = max(col_width, int(t_width / cols))

            Log.warn(self.hcenter_before_wheeling)
            self.horizontalHeader().setDefaultSectionSize(col_width_to)
            self._col_to_center(self.hcenter_before_wheeling)
        else:
            bias = 2 if idler_forward else -2
            # self._col_scroll(bias) # conflicts with follow_to
            global_.mySignals.jump_to.emit(-1, bias, global_.Emitter.T_WHEEL)

    def mousePressEvent(self, e):
        Log.debug('here')
        super().mousePressEvent(e)

    # def horizontalScrollbarValueChanged(self, p_int):
    #     Log.debug('here', p_int)
    #     if self.mouse_pressing_hscrollbar:
    #         global_.mySignals.jump_to.emit(p_int, None, global_.Emitter.T_HSCROLL)

    def slot_common_test(self, *arg):
        Log.debug(*arg)

    def slot_sliderMoved(self, p_int):
        Log.debug(p_int)
        index = self.columnCount() * self.horizontalScrollBar().sliderPosition() / self.horizontalScrollBar().maximum()

        global_.mySignals.jump_to.emit(index, None, global_.Emitter.T_HSCROLL)

    def slot_cellDoubleClicked(self, r, c):
        selection_range = self._select_label(r, c)
        if not selection_range:
            return
        start_at = selection_range.leftColumn()
        stop_at = selection_range.rightColumn()
        global_.mySignals.jump_to.emit(start_at, None, global_.Emitter.T_LABEL)
        global_.mySignals.video_start.emit(stop_at)

    def _cell_label(self) -> QTableWidgetSelectionRange:
        pass

    def _selected_colors(self):
        pass

    def _neighbor_color(self, r, c):
        if c - 1 >= 0 and self.item(r, c - 1) and self.item(r, c - 1).background() != Qt.white:
            return self.item(r, c - 1).background()
        elif c + 1 < self.columnCount() and self.item(r, c + 1) and self.item(r, c + 1).background() != Qt.white:
            return self.item(r, c + 1).background()
        else:
            return None

    def _refer_color(self, rect: QTableWidgetSelectionRange):
        l, r, t, b = rect.leftColumn(), rect.rightColumn(), rect.topRow(), rect.bottomRow()
        colors = set()
        for r in range(t, b + 1):
            for c in range(l, r + 1):
                if self.item(r, c) and self.item(r, c).background():
                    pass

    def slot_cellClicked(self, r, c):
        Log.debug(r, c)
        self._select_label(r, c)
        # if self.item(r, c).background() != Qt.white:
        #     Log.debug('clear color')
        #     self.item(r, c).setBackground(Qt.white)
        # else:
        #     n_color = self._neighbor_color(r, c)
        #     if n_color:
        #         self.item(r, c).setBackground(n_color)

    def slot_cellPressed(self, r, c):
        Log.info('here', r, c, self.item(r, c))
        self.pressed_cell_pos = (r, c)
        global_.mySignals.video_pause.emit()
        if not self.item(r, c):
            self.setItem(r, c, QTableWidgetItem(''))
            self.item(r, c).setBackground(Qt.white)
            # Log.warn(self.item(r, c).background() == Qt.white)
            # self.item(r, c).setText('10')
        # if self.item(r, c).background() != Qt.white:
        #     Log.debug('clear color')
        #     self.item(r, c).setBackground(Qt.white)
        # elif self.item(r, c - 1) and self.item(r, c - 1).background() != Qt.white:
        #     Log.debug('follow left neighbour color')
        #     self.item(r, c).setBackground(self.item(r, c - 1).background())
        # else:
        #     Log.debug('fill random color')
        #     self.item(r, c).setBackground(QColor(QRandomGenerator().global_().generate()))

    def slot_cellActivated(self, r, c):
        pass

    def slot_itemSelectionChanged(self):
        Log.info('here')
        rect = self.selectedRanges() and self.selectedRanges()[0]
        if not rect:
            return
        l, r, t, b = rect.leftColumn(), rect.rightColumn(), rect.topRow(), rect.bottomRow()
        Log.debug('l r t b', l, r, t, b)
        if l != r or t != b:
            if self.item(*self.pressed_cell_pos) and self.item(*self.pressed_cell_pos).background() != Qt.white:
                color = self.item(*self.pressed_cell_pos).background()
            else:
                color = QColor(QRandomGenerator().global_().generate())
            for c in range(l, r + 1):
                self.setItem(self.pressed_cell_pos[0], c, QTableWidgetItem(''))
                self.item(self.pressed_cell_pos[0], c).setBackground(color)

    def slot_horizontalHeaderClicked(self, i):
        Log.info('index', i)
        global_.mySignals.jump_to.emit(i, None, global_.Emitter.T_HHEADER)

    def slot_follow_to(self, emitter, index):
        if emitter == global_.Emitter.T_HSCROLL:
            return
        Log.error(emitter)
        self._col_to_center(index)

    def _center_col(self):  # only supports static case
        t_width = self.width()  # no vertical header
        return self.columnAt(t_width / 2)

    def _col_to_center(self, index):
        hscrollbar = self.horizontalScrollBar()
        # bias_to_center = self.width() / 2 / self.columnWidth(0)
        bias_to_center = hscrollbar.pageStep() / 2
        to = index - bias_to_center
        Log.debug(index, to)
        hscrollbar.setSliderPosition(max(0, to))

    def _col_scroll(self, bias):
        hscrollbar = self.horizontalScrollBar()
        pos = hscrollbar.sliderPosition() + bias
        hscrollbar.setSliderPosition(pos)

    def set_column_count(self, c):
        self.setColumnCount(c)
        self.setHorizontalHeaderLabels([str(i) for i in range(c)])
        # self.insertColumn(0)

    # def headerData(self, col, orientation, role):
    #     Log.warn('here')
    #     if orientation == Qt.Horizontal and role == Qt.DisplayRole:
    #         return col - 1
    #     return QVariant()

    def _select_label(self, row, col):
        if not self.item(row, col) or self.item(row, col).background() == Qt.white:
            return None
        color = self.item(row, col).background()
        l = r = col
        for ci in range(col - 1, -1, -1):
            if self.item(row, ci) and self.item(row, ci).background() == color:
                l = ci
            else:
                break
        for ci in range(col + 1, self.columnCount()):
            if self.item(row, ci) and self.item(row, ci).background() == color:
                r = ci
            else:
                break
        selection_range = QTableWidgetSelectionRange(row, l, row, r)
        self.setRangeSelected(selection_range, True)
        return selection_range

    def _del_selected_label(self):
        Log.error('here')
        for iterm in self.selectedItems():
            iterm.setBackground(Qt.white)
        self.setRangeSelected(self.selectedRanges()[0], False)


class MyVideoLabelWidget(QLabel):

    def __init__(self, parent):
        QLabel.__init__(self)
        self.entry_row_index = None
        self.video_obj = None
        self.video_playing = False
        # self.v_buffer = collections.deque(maxlen=100)

        # self.cellClicked.connect(self.slot_cellClicked)
        # self.cellActivated.connect(self.slot_cellActivated)
        # self.itemSelectionChanged.connect(self.slot_itemSelectionChanged)
        # self.cellPressed.connect(self.slot_cellPressed)
        global_.mySignals.jump_to.connect(self.slot_jump_to)
        global_.mySignals.timer_video.timeout.connect(self.timer_flush_frame)
        global_.mySignals.video_pause_or_resume.connect(self.pause_or_resume)
        global_.mySignals.video_start.connect(self.slot_start)
        global_.mySignals.video_pause.connect(self.pause)

    def set_video(self, video):
        self.video_obj = video

    def slot_jump_to(self, index, bias, emitter):
        # index: related signal defined to receive int parameters, None will be cast to large number 146624904,
        #        hence replace None with -1
        if index != -1:
            bias = None
        Log.info('here', index, bias)

        if self.video_obj:
            self.video_obj.schedule(index, bias, emitter)

    def mousePressEvent(self, e):
        self.pause_or_resume()

    def pause_or_resume(self):
        if self.video_playing:
            self.pause()
        else:
            self.slot_start(stop_at=-1)

    def pause(self):
        # self.timer_video.stop()
        self.video_playing = False

    def slot_start(self, stop_at):
        # self.timer_video.start()
        if not self.video_obj:
            return
        self.video_playing = True
        if stop_at != -1:
            self.video_obj.stop_at = stop_at

    def timer_flush_frame(self):
        if self.video_obj is None:
            return
        if not self.video_playing and self.video_obj.scheduled is None:
            return

        emitter, i, frame = self.video_obj.read()
        if frame is None:
            self.video_playing = False
            return
        global_.mySignals.follow_to.emit(emitter, i)

        height, width, bytesPerComponent = frame.shape
        bytesPerLine = bytesPerComponent * width
        q_image = QImage(frame.data, width, height, bytesPerLine,
                         QImage.Format_RGB888).scaled(self.width(), self.height(),
                                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
        q_pixmap = QPixmap.fromImage(q_image)
        self.setPixmap(q_pixmap)

        # self.label_note.setText(f'frame:{self.cur_index}')

        # elif not ret:
        #     self.cap.release()
        #     # self.timer_video.stop()
        #     # self.statusBar.showMessage('播放结束！')
        # else:
        #     self.flush_frame()


class MyQAbstractItemModel(QAbstractItemModel):
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> typing.Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(section - 1)
        return QVariant()
