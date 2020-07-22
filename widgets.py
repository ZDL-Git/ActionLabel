import collections
from random import random

import cv2
import typing
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import global_
from action import ActionLabel
from utils import *
from typing import List


class TableDecorators:
    @classmethod
    def dissort(cls, func):
        def func_wrapper(*arg):
            arg[0].setSortingEnabled(False)
            func(*arg)
            arg[0].setSortingEnabled(True)

        return func_wrapper

    @classmethod
    def block_signals(cls, func):
        def func_wrapper(*arg):
            arg[0].blockSignals(True)
            func(*arg)
            arg[0].blockSignals(False)

        return func_wrapper


class TimeLineTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self)

        # myQAbstractItemModel = MyQAbstractItemModel(self)
        # proxyModel = QAbstractProxyModel(self)
        # proxyModel.setSourceModel(myQAbstractItemModel)
        # self.setModel(proxyModel)

        self.key_control_pressing = False
        self.mouse_pressing_hscrollbar = False
        self.mouse_pressing_item = False
        self.entry_cell_pos = None
        self.label_clicked = None
        self.hcenter_before_wheeling = None

        self.cellPressed.connect(self.slot_cellPressed)
        self.cellClicked.connect(self.slot_cellClicked)
        self.cellDoubleClicked.connect(self.slot_cellDoubleClicked)
        self.cellActivated.connect(self.slot_cellActivated)
        # self.itemSelectionChanged.connect(self.slot_itemSelectionChanged)

        # global_.mySignals.jump_to.connect(self.slot_jump_to)
        global_.mySignals.follow_to.connect(self.slot_follow_to)
        global_.mySignals.labeled_selected.connect(self.slot_labeled_selected)
        # global_.mySignals.labeled_update.connect(self.slot_labeled_update)
        global_.mySignals.labeled_delete.connect(self.slot_labeled_delete)

    # FIXME
    def __init_later__(self):
        self.setHorizontalHeaderLabels([str(i) for i in range(self.columnCount())])

        header = self.horizontalHeader()
        header.sectionPressed.disconnect()
        header.sectionClicked.connect(self.slot_horizontalHeaderClicked)

        self.horizontalScrollBar().installEventFilter(self)
        self.horizontalScrollBar().sliderMoved.connect(self.slot_sliderMoved)
        # self.installEventFilter(self)

    def eventFilter(self, source, event):
        # Log.debug('here', source, event)
        if source == self.horizontalScrollBar():
            if event.type() == QEvent.MouseButtonPress:
                self.mouse_pressing_hscrollbar = True
                # global_.mySignals.video_pause.emit()
            elif event.type() == QEvent.MouseButtonRelease:
                self.mouse_pressing_hscrollbar = False
            # elif event.type() == QScrollBar.sliderPressed:
            #     Log.error('here')
            else:
                pass
                # Log.error(event.type())
        return False

    def keyPressEvent(self, e: QKeyEvent) -> None:
        Log.debug(f'mytable {e} {e.key()} {e.type()}')
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
            cells_deleted = self._del_selected_label_cells()
            global_.mySignals.label_cells_delete.emit(cells_deleted, global_.Emitter.T_LABEL)
        elif e.key() == Qt.Key_R:
            if self.label_clicked is not None:
                self._emit_video_play(self.label_clicked.begin, self.label_clicked.end)

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
            global_.mySignals.schedule.emit(-1, bias, -1, global_.Emitter.T_WHEEL)

    def mousePressEvent(self, e):
        Log.debug('here')
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        Log.debug('here')
        super().mouseReleaseEvent(e)
        if not self.entry_cell_pos:
            return
        rect = self.selectedRanges() and self.selectedRanges()[-1]
        if not rect:
            return
        l, r, t, b = rect.leftColumn(), rect.rightColumn(), rect.topRow(), rect.bottomRow()
        Log.debug('l r t b', l, r, t, b)
        if l == r and t == b or b - t == self.rowCount() - 1:
            return
        entry_item = self.item(*self.entry_cell_pos)
        if entry_item.background() == Qt.white:
            name, color = g_get_action()
            if name is None:
                return
        else:
            name, color = entry_item.toolTip(), entry_item.background()
        changed = False
        for c in range(l, r + 1):
            item = self.item(self.entry_cell_pos[0], c)
            if item:
                if item.background() != color:
                    changed = True
                    item.setBackground(color)
                    item.setToolTip(name)
            else:
                changed = True
                item = QTableWidgetItem('')
                item.setBackground(color)
                item.setToolTip(name)
                self.setItem(self.entry_cell_pos[0], c, item)
        if changed:
            found_label = self._detect_label(*self.entry_cell_pos)  # redetect after update, for sections connection
            if found_label is not None:
                global_.mySignals.label_created.emit(found_label, global_.Emitter.T_LABEL)

    # def horizontalScrollbarValueChanged(self, p_int):
    #     Log.debug('here', p_int)
    #     if self.mouse_pressing_hscrollbar:
    #         global_.mySignals.jump_to.emit(p_int, None, global_.Emitter.T_HSCROLL)

    def slot_labeled_delete(self, action_labels: List[ActionLabel], emitter):
        Log.debug(action_labels, emitter)
        self._unselect_all()
        for label in action_labels:
            self._del_label(label)

    @TableDecorators.block_signals
    def slot_labeled_selected(self, action_label: ActionLabel, emitter):
        Log.debug(action_label, emitter)
        self._unselect_all()
        self._select_label(action_label)
        self._emit_video_play(action_label.begin, action_label.end)

    # @TableDecorators.block_signals
    # def slot_labeled_update(self, action_label: ActionLabel, emitter):
    #     Log.debug(action_label, emitter)
    #     self._update_label(action_label)

    def slot_common_test(self, *arg):
        Log.debug(*arg)

    def slot_sliderMoved(self, pos):
        Log.debug(pos)
        # col_c = self.columnCount()
        # hscrollbar = self.horizontalScrollBar()
        index = (self.columnCount() - 1) * pos / self.horizontalScrollBar().maximum()

        global_.mySignals.schedule.emit(index, -1, -1, global_.Emitter.T_HSCROLL)
        # self.selectColumn(index)  # crash bug

    def slot_cellDoubleClicked(self, r, c):
        label = self._detect_label(r, c)  # type:ActionLabel
        if label is not None:
            self._emit_video_play(label.begin, label.end)

    def _emit_video_play(self, start_at, stop_at=-1):
        global_.mySignals.schedule.emit(start_at, -1, stop_at, global_.Emitter.T_LABEL)
        global_.mySignals.video_start.emit()

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
        label = self._detect_label(r, c)
        if label is None:
            self.label_clicked = None
        else:
            self.label_clicked = label
            self._select_label(label)
            global_.mySignals.label_selected.emit(label, global_.Emitter.T_LABEL)

    def slot_cellPressed(self, r, c):
        Log.info('here', r, c, self.item(r, c))
        global_.mySignals.video_pause.emit()
        if not self.item(r, c):
            item = QTableWidgetItem('')
            item.setBackground(Qt.white)
            self.setItem(r, c, item)
        self.mouse_pressing_item = True
        self.entry_cell_pos = (r, c)
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

    def slot_horizontalHeaderClicked(self, i):
        Log.info('index', i)
        global_.mySignals.schedule.emit(i, -1, -1, global_.Emitter.T_HHEADER)

    def slot_follow_to(self, emitter, index):
        if emitter == global_.Emitter.T_HSCROLL:
            return
        self._col_to_center(index)

    def _center_col(self):  # only supports static case
        t_width = self.width()  # no vertical header
        return self.columnAt(int(t_width / 2))

    def _col_to_center(self, index):
        hscrollbar = self.horizontalScrollBar()
        # bias_to_center = self.width() / 2 / self.columnWidth(0)
        bias_to_center = hscrollbar.pageStep() / 2
        to = index - bias_to_center
        hscrollbar.setSliderPosition(max(0, to))

    def _col_scroll(self, bias):
        hscrollbar = self.horizontalScrollBar()
        pos = hscrollbar.sliderPosition() + bias
        hscrollbar.setSliderPosition(pos)

    def set_column_count(self, c):

        self.setColumnCount(c)
        # FIXME: Set all labels is too slow, but implements view is too expensive
        self.setHorizontalHeaderLabels([str(i) for i in range(c)])
        # self.horizontalHeader().moveSection(c - 1, 0)
        # self.setHorizontalHeaderItem(c - 1, QTableWidgetItem('0'))

    # def headerData(self, col, orientation, role):
    #     Log.warn('here')
    #     if orientation == Qt.Horizontal and role == Qt.DisplayRole:
    #         return col - 1
    #     return QVariant()

    def _detect_label(self, row, col):
        item = self.item(row, col)
        if not item or item.background() == Qt.white:
            return None

        color = item.background()
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
        return ActionLabel(item.toolTip(), l, r, row)

    def _select_label(self, label: ActionLabel):
        self.setRangeSelected(
            QTableWidgetSelectionRange(label.timeline_row, label.begin, label.timeline_row, label.end), True)

    def _unselect_label(self, label: ActionLabel):
        self.setRangeSelected(
            QTableWidgetSelectionRange(label.timeline_row, label.begin, label.timeline_row, label.end), False)

    def _unselect_all(self):
        rowc = self.rowCount()
        colc = self.columnCount()
        if rowc > 0 and colc > 0:
            self.setRangeSelected(QTableWidgetSelectionRange(0, 0, rowc - 1, colc - 1), False)

    # def _update_label(self, label: ActionLabel):
    #     old_color = self.item(label.timeline_row, label.begin)
    #     if old_color == Qt.white:
    #         old_color = self.item(label.timeline_row, label.end)

    def _del_label(self, label: ActionLabel):
        for c in range(label.begin, label.end + 1):
            self.item(label.timeline_row, c).setBackground(Qt.white)

    def _del_selected_label_cells(self):
        Log.info('here')
        label_cells = {}  # key:row,value:cols list
        for item in self.selectedItems():
            if item.background() != Qt.white:
                item.setBackground(Qt.white)
                item_row = item.row()
                if item_row in label_cells:
                    label_cells[item_row].append(item.column())
                else:
                    label_cells[item_row] = [item.column()]
        for range_ in self.selectedRanges():
            self.setRangeSelected(range_, False)
        return label_cells


class LabeledTableWidget(QTableWidget):
    def __init__(self, parent):
        QTableWidget.__init__(self)

        self.cellDoubleClicked.connect(self.slot_cellDoubleClicked)
        self.itemSelectionChanged.connect(self.slot_itemSelectionChanged)
        # self.cellChanged.connect(self.slot_cellChanged)

        global_.mySignals.label_created.connect(self.slot_label_created)
        global_.mySignals.label_selected.connect(self.slot_label_selected)
        global_.mySignals.label_delete.connect(self.slot_label_delete)
        global_.mySignals.label_cells_delete.connect(self.slot_label_cells_delete)

    def __init_later__(self):
        self.setColumnHidden(3, True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    @TableDecorators.dissort
    @TableDecorators.block_signals
    def slot_label_created(self, action_label: ActionLabel, emitter):
        Log.debug(action_label, emitter)
        self._label_cells_delete({action_label.timeline_row: list(range(action_label.begin, action_label.end + 1))})
        row_i = self._add_label(action_label)
        self._select_row(row_i)

    @TableDecorators.dissort
    @TableDecorators.block_signals
    def slot_label_selected(self, action_label, emitter):
        Log.debug(action_label, emitter)
        label_row = self._get_label_row(action_label)
        if label_row is not None:
            self.selectRow(label_row)

    @TableDecorators.dissort
    @TableDecorators.block_signals
    def slot_label_delete(self, action_label, emitter):
        Log.debug(action_label, emitter)
        row_i = self._get_label_row(action_label)
        if row_i is not None:
            self._delete_rows(row_i)

    @TableDecorators.dissort
    @TableDecorators.block_signals
    def slot_label_cells_delete(self, label_cells, emitter):
        Log.debug(label_cells, emitter)
        self._label_cells_delete(label_cells)

    # def slot_cellChanged(self, r, c):
    #     Log.debug(r, c)

    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        Log.debug('here', e.key())
        if e.key() in [Qt.Key_Backspace, Qt.Key_D]:
            rows, labels = self._labels_selected()
            global_.mySignals.labeled_delete.emit(labels, global_.Emitter.T_LABELED)
            self._delete_rows(rows)
        elif e.key() == Qt.Key_R:
            if self.label_clicked is not None:
                self._slot_video_play(self.label_clicked.begin, self.label_clicked.end)

    def slot_itemSelectionChanged(self):
        Log.debug('here')

    def slot_cellDoubleClicked(self, r, c):
        Log.debug(r, c)
        label = self._label_at(r)
        global_.mySignals.labeled_selected.emit(label, global_.Emitter.T_LABELED)

    def _label_at(self, r):
        return ActionLabel(self.item(r, 0).text(), int(self.item(r, 1).text()), int(self.item(r, 2).text()),
                           int(self.item(r, 3).text()))

    def _labels_selected(self) -> (set, List[ActionLabel]):
        rows = set()
        for index in self.selectedIndexes():
            rows.add(index.row())
        labels = []
        for r in rows:
            labels.append(self._label_at(r))
        return rows, labels

    def _label_cells_delete(self, label_cells):
        for k in label_cells:
            label_cells[k].sort()
        rows_delete_later = set()
        labels_add_later = []
        for t_r in range(self.rowCount()):
            label_row = int(self.item(t_r, 3).text())
            if label_row not in label_cells:
                continue
            label_begin = int(self.item(t_r, 1).text())
            label_end = int(self.item(t_r, 2).text())
            if label_cells[label_row][0] > label_end or label_cells[label_row][-1] < label_begin:
                continue
            elif label_cells[label_row][0] <= label_begin:
                self.item(t_r, 1).setData(Qt.DisplayRole, label_cells[label_row][-1] + 1)
            elif label_cells[label_row][-1] >= label_end:
                self.item(t_r, 2).setData(Qt.DisplayRole, label_cells[label_row][0] - 1)
            else:
                self.item(t_r, 2).setData(Qt.DisplayRole, label_cells[label_row][0] - 1)
                labels_add_later.append(
                    ActionLabel(self.item(t_r, 0).text(), label_cells[label_row][-1] + 1, label_end, label_row))

            if int(self.item(t_r, 1).text()) > int(self.item(t_r, 2).text()):
                rows_delete_later.add(t_r)

        self._delete_rows(rows_delete_later)

        for l_add in labels_add_later:
            self._add_label(l_add)

    def _get_label_row(self, action_label: ActionLabel):
        rows = self.rowCount()
        for r in range(rows):
            if self.item(r, 1) and self.item(r, 1).text() == str(action_label.begin):
                if self.item(r, 2) and self.item(r, 2).text() == str(action_label.end):
                    if self.item(r, 3) and self.item(r, 3).text() == str(action_label.timeline_row):
                        return r
        return None

    def _add_label(self, action_label: ActionLabel):
        action = QTableWidgetItem(action_label.action)
        # action.setFlags(action.flags() & ~Qt.ItemIsEditable)
        begin = QTableWidgetItem()
        begin.setData(Qt.DisplayRole, action_label.begin)
        end = QTableWidgetItem()
        end.setData(Qt.DisplayRole, action_label.end)
        timeline_row = QTableWidgetItem()
        timeline_row.setData(Qt.DisplayRole, action_label.timeline_row)
        new_row_i = self.rowCount()
        self.insertRow(new_row_i)
        self.setItem(new_row_i, 0, action)
        self.setItem(new_row_i, 1, begin)
        self.setItem(new_row_i, 2, end)
        self.setItem(new_row_i, 3, timeline_row)
        return new_row_i

    def _delete_rows(self, rows):
        for r_d in sorted(rows, reverse=True):
            self.removeRow(r_d)

    def _select_row(self, row):
        self.selectRow(row)


class LabelTempTableWidget(QTableWidget):
    def __init__(self, parent):
        QTableWidget.__init__(self)

        # self.cellDoubleClicked.connect(self.slot_cellDoubleClicked)
        # self.itemSelectionChanged.connect(self.slot_itemSelectionChanged)
        self.cellChanged.connect(self.slot_cellChanged)
        self.cellDoubleClicked.connect(self.slot_cellDoubleClicked)

        # global_.mySignals.label_created.connect(self.slot_label_created)
        # global_.mySignals.action_add.connect(self.slot_action_add)

    def __init_later__(self):
        # self.setColumnHidden(3, True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for i in range(2):
            self._new_action(f"action{i + 1}", QColor('#fe8a71') if i == 0 else QColor('#0e9aa7'),
                             Qt.Checked if i == 0 else Qt.Unchecked)

        global g_get_action
        g_get_action = self.get_default_action

    def slot_cellChanged(self, r, c):
        Log.debug(r, c)
        if self.item(r, c).checkState() == Qt.Checked:
            self._unselect_others(except_=r)
        elif self.item(r, c).checkState() == 0:
            pass

    def slot_cellDoubleClicked(self, r, c):
        Log.debug(r, c)
        if c == 1:
            item = self.item(r, c)
            color = QColorDialog.getColor(initial=item.background().color())  # type:QColor
            if color.isValid():
                item.setBackground(color)

    def slot_action_add(self):
        Log.debug('here')
        self._new_action('', QColor(QRandomGenerator().global_().generate()), False)
        self.editItem(self.item(self.rowCount() - 1, 0))

    def slot_del_selected_action(self):
        Log.debug('here')
        if QMessageBox.Cancel == QMessageBox.warning(self, 'ActionLabel Warning',
                                                     "All you sure to delete action template?",
                                                     QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel):
            return
        rows = set()
        for index in self.selectedIndexes():
            rows.add(index.row())
        for r in sorted(rows, reverse=True):
            self.removeRow(r)

    def get_default_action(self):
        rows = self.rowCount()
        if rows == 0:
            QMessageBox.information(self, 'ActionLabel',
                                    "Please add action first!",
                                    QMessageBox.Ok, QMessageBox.Ok)
            return None, None

        actions = {}
        for r in range(rows):
            actions[self.item(r, 0).text()] = self.item(r, 1).background()
            if self.item(r, 2).checkState() == Qt.Checked:
                if not self.item(r, 0).text():
                    QMessageBox.information(self, 'ActionLabel',
                                            "Please complete action name first!",
                                            QMessageBox.Ok, QMessageBox.Ok)
                return self.item(r, 0).text(), self.item(r, 1).background()
        action, ok_pressed = QInputDialog.getItem(self, "ActionLabel", "Actions:", list(actions.keys()), 0, False)
        if ok_pressed and action:
            return action, actions[action]

        return None, None

    def _new_action(self, name, qcolor, checked):
        action = QTableWidgetItem(name)
        color = QTableWidgetItem()
        color.setFlags(Qt.ItemIsEnabled)
        color.setBackground(qcolor)
        default = QTableWidgetItem()
        default.setCheckState(checked)
        r = self.rowCount()
        self.insertRow(r)
        self.setItem(r, 0, action)
        self.setItem(r, 1, color)
        self.setItem(r, 2, default)

    def _del_action(self, r):
        self.removeRow(r)

    def _unselect_others(self, except_):
        for r in range(self.rowCount()):
            if r == except_:
                continue
            self.item(r, 2).setCheckState(Qt.Unchecked)

    def slot_test(self, *arg):
        Log.debug(*arg)

    # TODO
    class ActionSelectDialog(QDialog):
        def __init__(self, parent=None):
            QDialog.__init__(self)


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
        global_.mySignals.schedule.connect(self.slot_schedule)
        global_.mySignals.timer_video.timeout.connect(self.timer_flush_frame)
        global_.mySignals.video_pause_or_resume.connect(self.pause_or_resume)
        global_.mySignals.video_start.connect(self.slot_start)
        global_.mySignals.video_pause.connect(self.slot_pause)

    def set_video(self, video):
        self.video_obj = video

    def slot_schedule(self, jump_to, bias, stop_at, emitter):
        # index: related signal defined to receive int parameters, None will be cast to large number 146624904,
        #        hence replace None with -1
        if jump_to != -1:
            bias = None
        Log.info('here', jump_to, bias)

        if self.video_obj:
            self.video_obj.schedule(jump_to, bias, stop_at, emitter)

    def mousePressEvent(self, e):
        self.pause_or_resume()

    def pause_or_resume(self):
        if self.video_playing:
            self.slot_pause()
        else:
            self.slot_start()

    def slot_pause(self):
        Log.info('here')
        self.video_playing = False

    def slot_start(self):
        # self.timer_video.start()
        if not self.video_obj:
            return
        self.video_playing = True

    def timer_flush_frame(self):
        if self.video_obj is None:
            return
        if not self.video_playing and not self.video_obj.scheduled:
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

# class MyQAbstractItemModel(QAbstractItemModel):
#     def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> typing.Any:
#         if orientation == Qt.Horizontal and role == Qt.DisplayRole:
#             return str(section - 1)
#         return QVariant()
