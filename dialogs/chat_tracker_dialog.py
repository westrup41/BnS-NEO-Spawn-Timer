import html, time, json
import cv2, mss, numpy as np
from PySide6.QtCore import Qt, QRect, QPoint, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut, QTextCursor
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QFrame,QLabel,QPushButton,QSpinBox,QCheckBox,
    QTextEdit,QLineEdit,QScrollArea,QMessageBox)
from services.chat_ocr import ChatOCRWorker, match_score, clean
from services.audio import play_alert, stop_alert_sound
from styles import Style
from utils import s
from paths import CHAT_PREVIEW_PATH, CHAT_LOG_PATH

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
        with mss.mss() as g: monitors=g.monitors[1:]; physical=monitors[min(idx,len(monitors)-1)] if monitors else g.monitors[0]
        self.selected.emit({'left':round(physical['left']+(top.x()-logical.left())*scale),'top':round(physical['top']+(top.y()-logical.top())*scale),
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
        super().__init__(app);self.app=app;self.settings=app.settings;self.thread=None;self.worker=None;self.selector=None;self.line_history=[];self.cooldown_until=0;self.drag_pos=None;self.alert_sound_timers=[]
        self.log_timer=QTimer(self);self.log_timer.setSingleShot(True);self.log_timer.timeout.connect(self.persist_log)
        self.setWindowTitle('Трекер чата — BETA');self.setObjectName('ChatTrackerDialog');self.setWindowFlags(Qt.FramelessWindowHint|Qt.Dialog)
        self.resize(s(930,self.settings.app_scale),s(760,self.settings.app_scale));self.setStyleSheet(Style.main(self.settings.app_scale));self.build();self.load_log();self.refresh_region();self.refresh_preview()
    def build(self):
        root=QVBoxLayout(self);top=QFrame();top.setObjectName('TopBar');top_row=QHBoxLayout(top);top_row.setContentsMargins(0,0,0,0)
        title=QLabel('Трекер чата');title.setObjectName('SectionTitle');close=QPushButton('×');close.setObjectName('Close');close.setFixedSize(s(38,self.settings.app_scale),s(34,self.settings.app_scale));close.clicked.connect(self.close)
        top_row.addWidget(title);top_row.addStretch();top_row.addWidget(close);root.addWidget(top)
        top.mousePressEvent=self.mousePressEvent;top.mouseMoveEvent=self.mouseMoveEvent;top.mouseReleaseEvent=self.mouseReleaseEvent
        region=QHBoxLayout();self.region_btn=QPushButton();self.region_btn.setObjectName('Primary');self.region_btn.clicked.connect(self.region_action);self.coords=QLabel();self.coords.setObjectName('FormLabel');region.addWidget(self.region_btn);region.addWidget(self.coords);region.addStretch();root.addLayout(region)
        self.preview=QLabel('Область не выбрана');self.preview.setAlignment(Qt.AlignCenter);self.preview.setFixedHeight(150);self.preview.setObjectName('TrackerPreview');root.addWidget(self.preview)
        controls=QHBoxLayout();triggers=QPushButton('Триггеры');triggers.setObjectName('Ghost');triggers.clicked.connect(self.edit_triggers);controls.addWidget(triggers)
        controls.addWidget(QLabel('Порог совпадения с триггером'));self.similarity=QSpinBox();self.similarity.setRange(50,100);self.similarity.setSuffix(' %');self.similarity.setValue(self.settings.chat_similarity);controls.addWidget(self.similarity)
        controls.addWidget(QLabel('Мин. уверенность распознавания'));self.confidence=QSpinBox();self.confidence.setRange(10,95);self.confidence.setSuffix(' %');self.confidence.setValue(self.settings.chat_ocr_confidence);controls.addWidget(self.confidence)
        self.contrast=QCheckBox('Усилить читаемость текста (контраст)');self.contrast.setChecked(self.settings.chat_contrast);controls.addWidget(self.contrast);root.addLayout(controls)
        self.similarity.setToolTip('Насколько распознанный текст должен быть похож на триггер. Ниже — больше допуск к ошибкам OCR.')
        self.confidence.setToolTip('Строки с меньшей уверенностью распознавателя отбрасываются как шум.')
        self.contrast.setToolTip('Локально усиливает светлые и цветные буквы на прозрачном игровом фоне.')
        self.log=QTextEdit();self.log.setReadOnly(True);self.log.document().setMaximumBlockCount(100);root.addWidget(self.log,1)
        bottom=QHBoxLayout();clear=QPushButton('Очистить журнал');clear.setObjectName('Ghost');clear.clicked.connect(self.clear_log);self.status=QLabel('Остановлено');self.start=QPushButton('Старт');self.start.setObjectName('Success');self.start.clicked.connect(self.start_tracking);self.stop=QPushButton('Стоп');self.stop.setObjectName('Danger');self.stop.clicked.connect(self.stop_tracking);self.stop.setEnabled(False)
        bottom.addWidget(clear);bottom.addStretch();bottom.addWidget(self.status);bottom.addWidget(self.start);bottom.addWidget(self.stop);root.addLayout(bottom)
    def region_action(self):
        if self.thread:return
        if self.settings.chat_region:
            self.settings.chat_region={};self.settings.save();CHAT_PREVIEW_PATH.unlink(missing_ok=True);self.refresh_region();self.refresh_preview();return
        self.hide();self.selector=RegionSelector();self.selector.selected.connect(self.region_selected);self.selector.cancelled.connect(self.show);self.selector.show()
    def region_selected(self,r):self.settings.chat_region=r;self.settings.save();self.show();self.raise_();self.refresh_region();QTimer.singleShot(150,lambda:self.refresh_preview(True))
    def refresh_region(self):
        r=self.settings.chat_region;self.region_btn.setText('Сбросить' if r else 'Выбрать область чата')
        self.coords.setText(f"X {r['left']} · Y {r['top']} · {r['width']} × {r['height']} px" if r else '')
    def refresh_preview(self,capture=False):
        r=self.settings.chat_region
        if not r:self.preview.setPixmap(QPixmap());self.preview.setText('Область не выбрана');return
        if CHAT_PREVIEW_PATH.exists() and not capture:
            pixmap=QPixmap(str(CHAT_PREVIEW_PATH))
            if not pixmap.isNull():self.preview.setText('');self.preview.setPixmap(pixmap.scaled(self.preview.width()-8,self.preview.height()-8,Qt.KeepAspectRatio,Qt.SmoothTransformation));return
        try:
            mon={k:int(r[k]) for k in ('left','top','width','height')}
            with mss.mss() as g:shot=np.asarray(g.grab(mon))
            cv2.imencode('.png',shot)[1].tofile(str(CHAT_PREVIEW_PATH))
            rgb=cv2.cvtColor(shot,cv2.COLOR_BGRA2RGB);h,w,c=rgb.shape;image=QImage(rgb.data,w,h,c*w,QImage.Format_RGB888).copy()
            self.preview.setText('');self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.width()-8,self.preview.height()-8,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        except Exception as e:self.preview.setText(str(e))
    def edit_triggers(self):
        d=TriggersDialog(self,self.settings.chat_triggers)
        if d.exec()==QDialog.Accepted:self.settings.chat_triggers=d.values();self.settings.save()
    def save_options(self):
        self.settings.chat_similarity=self.similarity.value();self.settings.chat_ocr_confidence=self.confidence.value();self.settings.chat_contrast=self.contrast.isChecked();self.settings.save()
    def start_tracking(self):
        if not self.settings.chat_region:return QMessageBox.warning(self,'Трекер чата','Сначала выберите область чата.')
        if not self.settings.chat_triggers:return QMessageBox.warning(self,'Трекер чата','Добавьте хотя бы один триггер.')
        self.save_options();self.thread=QThread(self);self.worker=ChatOCRWorker(self.settings.chat_region,self.confidence.value(),self.contrast.isChecked());self.worker.moveToThread(self.thread);self.thread.started.connect(self.worker.run);self.worker.ready.connect(lambda:self.status.setText('Отслеживание включено'));self.worker.scan.connect(self.on_scan);self.worker.error.connect(self.on_error);self.worker.stopped.connect(self.on_stopped);self.thread.start();self.start.setEnabled(False);self.stop.setEnabled(True);self.region_btn.setEnabled(False);self.status.setText('Загрузка OCR…')
    def stop_tracking(self):
        if self.app.cancel_local_chat_alert_effect():
            self.cancel_local_alert_sounds()
            self.cooldown_until=0
        if self.worker:self.worker.stop();self.stop.setEnabled(False);self.status.setText('Остановка…')

    def cancel_local_alert_sounds(self):
        for timer in self.alert_sound_timers:
            timer.stop();timer.deleteLater()
        self.alert_sound_timers.clear()
        stop_alert_sound()
    def on_stopped(self):
        t=self.thread
        if t:t.quit();t.wait(3000);t.deleteLater()
        self.thread=None;self.worker=None;self.start.setEnabled(True);self.stop.setEnabled(False);self.region_btn.setEnabled(True);self.status.setText('Остановлено')
    def on_error(self,text):self.append_html(f'<span style="color:#f23f43">Ошибка OCR: {html.escape(text[-800:])}</span>')
    def on_scan(self,lines,elapsed):
        if time.monotonic()<self.cooldown_until:return
        found=None
        for item in lines:
            text=item['text'];trigger=None;score=0
            for phrase in self.settings.chat_triggers:
                value=match_score(phrase,text)
                if value>score:score=value;trigger=phrase
            hot=score>=self.similarity.value();color='#f23f43' if hot else '#dbdee1';self.append_html(f'<span style="color:{color}">{item["confidence"]:.1f}%&nbsp;&nbsp;{html.escape(text)}</span>')
            if hot and found is None:found=(trigger,text,score)
        if found:self.triggered(*found)
    def load_log(self):
        try:self.saved_log=json.loads(CHAT_LOG_PATH.read_text(encoding='utf-8'))[-100:]
        except Exception:self.saved_log=[]
        for value in self.saved_log:self._display_html(str(value))
    def _display_html(self,value):self.log.moveCursor(QTextCursor.End);self.log.insertHtml(value);self.log.insertPlainText('\n');self.log.moveCursor(QTextCursor.End)
    def append_html(self,value):
        self._display_html(value);self.saved_log=(getattr(self,'saved_log',[])+[value])[-100:]
        self.log_timer.start(150)
    def persist_log(self):
        try:CHAT_LOG_PATH.write_text(json.dumps(self.saved_log,ensure_ascii=False),encoding='utf-8')
        except OSError:pass
    def clear_log(self):self.log.clear();self.saved_log=[];self.persist_log()
    def triggered(self,trigger,text,score):
        if not self.app.on_local_chat_detection(trigger,text):
            return
        self.cooldown_until=time.monotonic()+30
        if self.worker:self.worker.pause(30)
        self.status.setText(f'Пауза 30 сек: {trigger}');self.append_html(f'<b style="color:#f23f43">ТРИГГЕР: {html.escape(trigger)} ({score}%)</b>')
        self.cancel_local_alert_sounds()
        play_alert(self.settings.sound_enabled,self.settings.custom_sound_path,self.settings.sound_volume)
        for delay in (5000,10000,15000,20000):
            timer=QTimer(self);timer.setSingleShot(True)
            timer.timeout.connect(lambda:play_alert(self.settings.sound_enabled,self.settings.custom_sound_path,self.settings.sound_volume))
            timer.start(delay);self.alert_sound_timers.append(timer)
        QTimer.singleShot(30000,lambda:self.status.setText('Отслеживание включено') if self.worker else None)
    def closeEvent(self,e):
        self.save_options()
        if self.worker:self.worker.stop()
        if self.thread:
            self.thread.quit();self.thread.wait(15000)
        self.thread=None;self.worker=None
        self.app.chat_tracker_dialog=None;e.accept()
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton:self.drag_pos=e.globalPosition().toPoint()-self.frameGeometry().topLeft();e.accept()
    def mouseMoveEvent(self,e):
        if self.drag_pos is not None:self.move(e.globalPosition().toPoint()-self.drag_pos);e.accept()
    def mouseReleaseEvent(self,e):self.drag_pos=None;e.accept()
