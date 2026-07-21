import html, time
from PySide6.QtCore import Qt, QRect, QPoint, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QKeySequence, QPainter, QPen, QShortcut, QTextCursor
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame,QLabel,QPushButton,
    QTextEdit,QLineEdit,QScrollArea)
from dialogs.message_dialog import MessageDialog
from services.chat_matching import match_score, clean
from services.ocr_process import OCRProcess
from services.ocr_pack import installed as ocr_installed
from styles import Style
from utils import s
from widgets.slider import DiscordSlider
from widgets.ui_primitives import ToggleButton

DEFAULT_TRIGGERS=['монарх','м1','м2','м3','м1к','м2к','м3к','m1k','m2k','m3k','m1 k','m2 k','m3 k','дерево']

class RegionSelector(QWidget):
    selected=Signal(dict); cancelled=Signal()
    def __init__(self):
        super().__init__(None,Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool); self.setAttribute(Qt.WA_TranslucentBackground); self.setCursor(Qt.CrossCursor)
        geo=QGuiApplication.primaryScreen().virtualGeometry()
        for screen in QGuiApplication.screens()[1:]: geo=geo.united(screen.geometry())
        self.setGeometry(geo); self.origin=QPoint(); self.current=QPoint(); self.drag=False
        QShortcut(QKeySequence(Qt.Key_Escape),self,activated=self.cancel)
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton:self.origin=e.position().toPoint();self.current=self.origin;self.drag=True;self.update()
    def mouseMoveEvent(self,e):
        if self.drag:self.current=e.position().toPoint();self.update()
    def mouseReleaseEvent(self,e):
        if not self.drag or e.button()!=Qt.LeftButton:return
        self.current=e.position().toPoint(); rect=QRect(self.origin,self.current).normalized(); self.drag=False
        if rect.width()<80 or rect.height()<40:return
        top=self.mapToGlobal(rect.topLeft()); center=self.mapToGlobal(rect.center()); screen=QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
        screens=QGuiApplication.screens(); idx=screens.index(screen) if screen in screens else 0; scale=float(screen.devicePixelRatio()); logical=screen.geometry()
        physical_left=round(logical.left()*scale);physical_top=round(logical.top()*scale)
        self.selected.emit({'left':round(physical_left+(top.x()-logical.left())*scale),'top':round(physical_top+(top.y()-logical.top())*scale),
            'width':round(rect.width()*scale),'height':round(rect.height()*scale),'coordinate_space':'physical','dpi_scale':scale}); self.close()
    def cancel(self):self.cancelled.emit();self.close()
    def paintEvent(self,_):
        p=QPainter(self);p.fillRect(self.rect(),QColor(0,0,0,120));p.setPen(Qt.white);p.drawText(24,38,'Выделите игровой чат • Esc — отмена')
        if self.drag:
            r=QRect(self.origin,self.current).normalized();p.setCompositionMode(QPainter.CompositionMode_Clear);p.fillRect(r,Qt.transparent)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver);p.setPen(QPen(QColor(88,101,242),4));p.drawRect(r)

class TriggersDialog(QDialog):
    def __init__(self,parent,triggers):
        super().__init__(parent);self.setWindowTitle('Триггеры');self.resize(470,600);self.rows=[]
        root=QVBoxLayout(self);self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.body=QWidget();self.box=QVBoxLayout(self.body);self.scroll.setWidget(self.body);root.addWidget(self.scroll)
        controls=QHBoxLayout();add=QPushButton('+ Добавить');add.setObjectName('Primary');add.clicked.connect(lambda:self.add_row(''));reset=QPushButton('Сбросить');reset.setObjectName('Ghost');reset.clicked.connect(self.reset)
        save=QPushButton('Готово');save.setObjectName('Success');save.clicked.connect(self.accept);controls.addWidget(add);controls.addWidget(reset);controls.addStretch();controls.addWidget(save);root.addLayout(controls)
        for value in triggers:self.add_row(value)
    def add_row(self,value):
        row=QFrame();lay=QHBoxLayout(row);edit=QLineEdit(value);delete=QPushButton('×');delete.setObjectName('Danger');delete.setFixedWidth(38)
        lay.addWidget(edit);lay.addWidget(delete);self.box.addWidget(row);self.rows.append((row,edit));delete.clicked.connect(lambda:self.remove_row(row))
    def remove_row(self,row):
        self.rows=[x for x in self.rows if x[0] is not row];row.deleteLater()
    def reset(self):
        for row,_ in self.rows:row.deleteLater()
        self.rows=[]
        for value in DEFAULT_TRIGGERS:self.add_row(value)
    def values(self):return list(dict.fromkeys(e.text().strip() for _,e in self.rows if e.text().strip()))[:100]

class ChatTrackerDialog(QDialog):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.settings=app.settings;self.worker=None;self.selector=None;self.line_history=[];self.cooldown_until=0;self.drag_pos=None
        self.setWindowTitle('Сканер чата');self.setObjectName('ChatTrackerDialog');self.setWindowFlags(Qt.FramelessWindowHint|Qt.Dialog)
        screen=self.screen().availableGeometry();self.resize(min(screen.width()-32,s(930,self.settings.app_scale)),min(screen.height()-32,s(610,self.settings.app_scale)));self.setStyleSheet(Style.main(self.settings.app_scale));self.build();self.refresh_region()
    def build(self):
        root=QVBoxLayout(self);top=QFrame();top.setObjectName('TopBar');top_row=QHBoxLayout(top);top_row.setContentsMargins(0,0,0,0)
        title=QLabel('Сканер чата');title.setObjectName('SectionTitle');close=QPushButton('×');close.setObjectName('Close');close.setFixedSize(s(38,self.settings.app_scale),s(34,self.settings.app_scale));close.clicked.connect(self.close)
        top_row.addWidget(title);top_row.addStretch();top_row.addWidget(close);root.addWidget(top)
        top.mousePressEvent=self.mousePressEvent;top.mouseMoveEvent=self.mouseMoveEvent;top.mouseReleaseEvent=self.mouseReleaseEvent
        region=QHBoxLayout();self.region_btn=QPushButton();self.region_btn.setObjectName('Primary');self.region_btn.clicked.connect(self.region_action);self.coords=QLabel();self.coords.setObjectName('FormLabel');region.addWidget(self.region_btn);region.addWidget(self.coords);region.addStretch();root.addLayout(region)
        controls=QHBoxLayout();controls.setSpacing(s(14,self.settings.app_scale));triggers=QPushButton('Триггеры');triggers.setObjectName('Ghost');triggers.clicked.connect(self.edit_triggers);controls.addWidget(triggers)
        self.contrast=ToggleButton('Усилить контраст');self.contrast.setChecked(self.settings.chat_contrast);controls.addWidget(self.contrast);controls.addStretch();root.addLayout(controls)
        thresholds=QGridLayout();thresholds.setHorizontalSpacing(s(12,self.settings.app_scale));thresholds.setVerticalSpacing(s(5,self.settings.app_scale))
        self.similarity=DiscordSlider(self.settings.app_scale);self.similarity.setRange(0,100);self.similarity.setValue(self.settings.chat_similarity)
        self.similarity_value=QLabel(f'{self.similarity.value()}%');self.similarity_value.setFixedWidth(s(46,self.settings.app_scale));self.similarity.valueChanged.connect(lambda v:self.similarity_value.setText(f'{v}%'))
        self.confidence=DiscordSlider(self.settings.app_scale);self.confidence.setRange(0,100);self.confidence.setValue(self.settings.chat_ocr_confidence)
        self.confidence_value=QLabel(f'{self.confidence.value()}%');self.confidence_value.setFixedWidth(s(46,self.settings.app_scale));self.confidence.valueChanged.connect(lambda v:self.confidence_value.setText(f'{v}%'))
        thresholds.addWidget(QLabel('Сходство фразы'),0,0);thresholds.addWidget(self.similarity,0,1);thresholds.addWidget(self.similarity_value,0,2)
        thresholds.addWidget(QLabel('Уверенность сканера'),1,0);thresholds.addWidget(self.confidence,1,1);thresholds.addWidget(self.confidence_value,1,2);root.addLayout(thresholds)
        self.log=QTextEdit();self.log.setReadOnly(True);self.log.document().setMaximumBlockCount(100);root.addWidget(self.log,1)
        bottom=QHBoxLayout();reset=QPushButton('Сбросить настройки');reset.setObjectName('Danger');reset.clicked.connect(self.reset_defaults);clear=QPushButton('Очистить журнал');clear.setObjectName('Ghost');clear.clicked.connect(self.clear_log);self.start=QPushButton('Старт');self.start.setObjectName('Success');self.start.clicked.connect(self.start_tracking);self.stop=QPushButton('Стоп');self.stop.setObjectName('Danger');self.stop.clicked.connect(self.stop_tracking);self.stop.setEnabled(False)
        bottom.addWidget(reset);bottom.addWidget(clear);bottom.addStretch();bottom.addWidget(self.start);bottom.addWidget(self.stop);root.addLayout(bottom)
    def region_action(self):
        if self.worker:return
        if self.settings.chat_region:
            self.settings.chat_region={};self.settings.save();self.refresh_region();return
        self.hide();self.selector=RegionSelector();self.selector.selected.connect(self.region_selected);self.selector.cancelled.connect(self.show);self.selector.show()
    def region_selected(self,r):self.settings.chat_region=r;self.settings.save();self.show();self.raise_();self.refresh_region()
    def refresh_region(self):
        r=self.settings.chat_region;self.region_btn.setText('Сбросить' if r else 'Выбрать область чата')
        self.coords.setText(f"X {r['left']} · Y {r['top']} · {r['width']} × {r['height']} px" if r else '')
    def edit_triggers(self):
        d=TriggersDialog(self,self.settings.chat_triggers)
        if d.exec()==QDialog.Accepted:self.settings.chat_triggers=d.values();self.settings.save()
    def save_options(self):
        self.settings.chat_similarity=self.similarity.value();self.settings.chat_ocr_confidence=self.confidence.value();self.settings.chat_contrast=self.contrast.isChecked();self.settings.save()
    def start_tracking(self):
        if not ocr_installed():return MessageDialog(self,'Сканер чата','Компоненты сканера чата не установлены.').exec()
        if not self.settings.chat_region:return MessageDialog(self,'Сканер чата','Сначала выберите область чата.').exec()
        if not self.settings.chat_triggers:return MessageDialog(self,'Сканер чата','Добавьте хотя бы один триггер.').exec()
        self.save_options();self.worker=OCRProcess(self.settings.chat_region,self.confidence.value(),self.contrast.isChecked(),self);self.worker.ready.connect(self.on_ready);self.worker.scan.connect(self.on_scan);self.worker.error.connect(self.on_error);self.worker.stopped.connect(self.on_stopped);self.worker.start();self.start.setEnabled(False);self.stop.setEnabled(True);self.region_btn.setEnabled(False)
    def stop_tracking(self):
        if self.app.cancel_local_chat_alert_effect():
            self.cooldown_until=0
        if self.worker:self.worker.stop();self.stop.setEnabled(False)

    def on_stopped(self):
        worker=self.worker;self.worker=None
        if worker:worker.deleteLater()
        self.start.setEnabled(True);self.stop.setEnabled(False);self.region_btn.setEnabled(True);self.append_html('<span style="color:#949ba4">Сканирование остановлено</span>')
    def on_ready(self):self.append_html('<span style="color:#23a559">Сканирование запущено</span>')
    def on_error(self,text):self.append_html(f'<span style="color:#f23f43">Ошибка сканера чата: {html.escape(text[-800:])}</span>')
    def on_scan(self,lines,elapsed):
        if time.monotonic()<self.cooldown_until:return
        self.append_html(f'<span style="color:#949ba4">Сканирование кадра · {elapsed:.1f} сек</span>')
        found=None
        for item in lines:
            text=item['text'];trigger=None;score=0
            for phrase in self.settings.chat_triggers:
                value=match_score(phrase,text)
                if value>score:score=value;trigger=phrase
            hot=score>=self.similarity.value();color='#f23f43' if hot else '#dbdee1';self.append_html(f'<span style="color:{color}">{item["confidence"]:.1f}%&nbsp;&nbsp;{html.escape(text)}</span>')
            if hot and found is None:found=(trigger,text,score)
        if found:self.triggered(*found)
    def _display_html(self,value):self.log.moveCursor(QTextCursor.End);self.log.insertHtml(value);self.log.insertPlainText('\n');self.log.moveCursor(QTextCursor.End)
    def append_html(self,value):self._display_html(value)
    def clear_log(self):self.log.clear()
    def reset_defaults(self):
        if not MessageDialog(self,'Сброс сканера','Сбросить область чата, триггеры и параметры сканера чата?',ok_text='Сбросить',cancel_text='Отмена').exec_result():return
        if self.worker:self.worker.stop()
        self.settings.chat_region={};self.settings.chat_triggers=list(DEFAULT_TRIGGERS);self.settings.chat_similarity=82;self.settings.chat_ocr_confidence=45;self.settings.chat_contrast=False
        self.similarity.setValue(82);self.confidence.setValue(45);self.contrast.setChecked(False);self.cooldown_until=0;self.settings.save();self.refresh_region();self.clear_log()
    def triggered(self,trigger,text,score):
        if not self.app.on_local_chat_detection(trigger,text):
            return
        self.cooldown_until=time.monotonic()+30
        if self.worker:self.worker.pause(30)
        self.append_html(f'<b style="color:#f23f43">ТРИГГЕР: {html.escape(trigger)} ({score}%)</b>')
        self.app.sound_controller.stop('local_ocr')
        self.app.sound_controller.play('local_ocr')
    def closeEvent(self,e):
        self.save_options()
        if self.worker:self.worker.stop()
        if self.worker:self.worker.wait(5000)
        self.worker=None
        self.app.chat_tracker_dialog=None;e.accept()
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton:self.drag_pos=e.globalPosition().toPoint()-self.frameGeometry().topLeft();e.accept()
    def mouseMoveEvent(self,e):
        if self.drag_pos is not None:self.move(e.globalPosition().toPoint()-self.drag_pos);e.accept()
    def mouseReleaseEvent(self,e):self.drag_pos=None;e.accept()
