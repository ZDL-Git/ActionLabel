from typing import List, Dict

from PyQt5 import uic
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QCloseEvent, QColor
from PyQt5.QtWidgets import QMainWindow, QGridLayout, QTextBrowser, QDialog, QMessageBox, QGraphicsDropShadowEffect, \
    QHeaderView, QFileDialog

import global_
import xml_
from action import Action, ActionLabel
from utils.utils import Log
from video import Video

Ui_MainWindow, QtBaseClass = uic.loadUiType("qt_gui/mainwindow.ui")


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        QMainWindow.__init__(self, flags=Qt.Window)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        self.combo_speed.addItems(['0.25', '0.5', '0.75', '1', '1.25', '1.5', '1.75'])
        self.combo_speed.setCurrentIndex(3)
        self.combo_sortby.addItems(['timestamp', 'filename'])
        self.combo_sortby.setCurrentIndex(1)
        # self.line_xml_file_parttern.setText('action_{begin index}-{end index}.xml')

        self.spin_interval.textChanged.connect(self.slot_interval_changed)
        self.combo_speed.currentTextChanged.connect(self.slot_speed_changed)
        self.input_jumpto.textChanged.connect(self.slot_input_jumpto_changed)
        self.label_show.installEventFilter(self)

        def init_buttons():
            self.btn_open_video.setFocus()
            self.btn_open_video.clicked.connect(self.slot_open_file)
            self.btn_play.clicked.connect(global_.mySignals.video_pause_or_resume.emit)
            self.btn_to_head.clicked.connect(self.to_head)
            self.btn_to_tail.clicked.connect(self.to_tail)
            self.btn_eval.clicked.connect(self.slot_eval)
            self.btn_new_action.clicked.connect(self.table_action.slot_action_add)
            self.btn_del_action.clicked.connect(self.table_action.slot_del_selected_actions)

        def init_settings():
            global_.Settings.v_interval = int(self.spin_interval.text())
            # global_.Settings.v_speed = float(self.combo_speed.currentText())

        def prettify():
            shadowEffect = QGraphicsDropShadowEffect()
            shadowEffect.setColor(QColor(0, 0, 0, 255 * 0.9))
            shadowEffect.setOffset(0)
            shadowEffect.setBlurRadius(8)
            self.label_show.setGraphicsEffect(shadowEffect)
            self.label_note.setGraphicsEffect(shadowEffect)

            vheader = self.table_timeline.verticalHeader()
            vheader.setDefaultSectionSize(5)
            vheader.sectionResizeMode(QHeaderView.Fixed)

        init_buttons()
        init_settings()
        prettify()

        self.table_timeline.__init_later__()
        self.table_labeled.__init_later__()
        self.table_action.__init_later__()
        self.table_xml_setting.__init_later__(self.table_action.model())

        self._holder1 = XmlSettingUnit(self)

        global_.g_status_prompt = self.label_note.setText
        global_.mySignals.follow_to.connect(self.slot_follow_to)

    def common_slot(self, *arg):
        Log.debug(f'common slot print:', arg)

    def slot_open_file(self):
        # TODO: remove native directory
        got = QFileDialog.getOpenFileName(self, "Open Image", "/Users/zdl/Downloads/下载-视频",
                                          "Media Files (*.mp4 *.jpg *.bmp)", options=QFileDialog.ReadOnly)
        # got = ['/Users/zdl/Downloads/下载-视频/金鞭溪-张家界.mp4']
        Log.info(got)
        fname = got[0]
        if fname:
            video = Video(fname)
            self.table_timeline.set_column_count(video.get_info()['frame_c'])
            self.label_show.set_video(video)
            global_.mySignals.timer_start(1000 / video.get_info()['fps'] / float(self.combo_speed.currentText()))
            global_.mySignals.video_start.emit()

    def to_head(self):
        pass

    def to_tail(self):
        pass

    def slot_interval_changed(self):
        global_.Settings.v_interval = int(self.spin_interval.text() or 1)

    def slot_speed_changed(self):
        Log.debug('')
        new_speed = 1000 / self.label_show.video_obj.get_info()['fps'] / float(self.combo_speed.currentText())
        global_.mySignals.timer_video.setInterval(new_speed)

    def slot_input_jumpto_changed(self, text):
        try:
            jumpto = int(text)
            global_.mySignals.schedule.emit(jumpto, -1, -1, global_.Emitter.INPUT_JUMPTO)
        except Exception:
            Log.warn('Only int number supported!')

    def slot_follow_to(self, emitter, to):
        global_.g_status_prompt(f'Frame {to}')

    def eventFilter(self, source, event):
        if event.type() == 12:
            return False

        return super(QMainWindow, self).eventFilter(source, event)

    def closeEvent(self, e: QCloseEvent):
        Log.debug('Main window closed.')
        if QMessageBox.Ok != QMessageBox.information(self, 'ActionLabel',
                                                     "Are you sure to quit, the unsaved labels will be lost?",
                                                     QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel):
            e.ignore()

    # def resizeEvent(self, e):
    #     pass
    #     Log.warn(self.table_timeline.width())
    #     super(MyApp, self).resizeEvent(e)

    def slot_eval(self):
        eval_content = self.ptext_eval_in.toPlainText()
        Log.info(eval_content)
        try:
            resp = eval(eval_content)
        except Exception as e:
            resp = e.__str__()
        self.textb_eval_out.setText(str(resp))


class XmlSettingUnit:
    def __init__(self, mwindow):
        Log.debug('')
        self.mw = mwindow
        # Log.debug(self.parent())
        self.mw.btn_export_xml.clicked.connect(self.slot_export_xml)
        self.mw.btn_xml_template.clicked.connect(self.slot_xml_template)

    def slot_export_xml(self):
        Log.debug('')
        labels = global_.g_all_labels()  # type:List[ActionLabel]
        labels.sort(key=lambda l: l.begin)
        actions = global_.g_all_actions()  # type:List[Action]
        id_action_dict = {a.id: a for a in actions}  # type:Dict[int,Action]
        framespan = int(self.mw.line_framespan.text())
        overlap = int(self.mw.line_overlap.text())
        Log.debug(framespan, overlap, labels)

        anno = xml_.AnnotationXml()
        file_num = 0
        abandoned = []
        while labels:
            trans = overlap * (0 if file_num == 0 else -1)
            range_ = (file_num * framespan + trans + 1, (file_num + 1) * framespan + trans)
            anno.new_file(f'runtime/xmldemo_{range_}.xml')
            anno.set_tag('folder', 'runtime')
            anno.set_tag('filename', f'runtime/xmldemo_{range_}.png')
            anno.set_tag('width', framespan)
            anno.set_tag('height', 200)
            anno.set_tag('depth', 100)
            cursor = 0
            while labels:
                if labels[cursor].begin >= range_[0] and labels[cursor].end <= range_[1]:
                    label = labels.pop(cursor)
                    action = id_action_dict[label.action_id]
                    anno.append_action(label.action, label.begin, label.end, action.xml_ymin, action.xml_ymax)
                elif labels[cursor].begin < range_[0]:
                    abandoned.append(labels.pop(cursor))
                elif labels[cursor].begin > range_[1]:
                    break
                else:
                    cursor += 1
            anno.dump()
            file_num += 1
        Log.info('labels abandoned:', abandoned)

    def slot_xml_template(self):
        Log.debug('')
        layout = QGridLayout()
        layout.addWidget(QTextBrowser())
        layout.setContentsMargins(2, 2, 2, 2)
        dialog = QDialog(self.mw, flags=Qt.Dialog)
        dialog.setFixedSize(QSize(400, 300))
        dialog.setLayout(layout)
        dialog.setContentsMargins(2, 2, 2, 2)
        dialog.exec_()