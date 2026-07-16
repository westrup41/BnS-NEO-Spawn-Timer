import os, re, sys, threading, time, traceback, unicodedata
from pathlib import Path
import cv2, mss, numpy as np
from rapidfuzz import fuzz
from PySide6.QtCore import QObject, Signal, Slot

os.environ.setdefault('FLAGS_use_mkldnn', '0')
os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')

MODEL_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1])) / 'models'
LOOKALIKE = str.maketrans({'а':'a','в':'b','с':'c','е':'e','н':'h','к':'k','м':'m','о':'o','р':'p','т':'t','х':'x','у':'y'})

def clean(value):
    value = unicodedata.normalize('NFKC', str(value)).casefold().replace('ё','е')
    return re.sub(r'\s+', ' ', re.sub(r'[^0-9a-zа-я]+', ' ', value)).strip()

def variants(value):
    base = clean(value)
    # Keep digits intact: turning "1" into a letter made a single OCR symbol
    # look like a complete short trigger (for example, "м1").
    return list(dict.fromkeys((base, base.translate(LOOKALIKE)))) if base else []

def match_score(phrase, text):
    best = 0
    for p in variants(phrase):
        for t in variants(text):
            if not p or not t:
                continue
            # Exact trigger must be bounded by non-alphanumeric characters.
            # Thus "м1" matches a chat word, but never a lone "1" or "м10".
            if re.search(rf'(?<![0-9a-zа-я]){re.escape(p)}(?![0-9a-zа-я])', t):
                return 100
            # Short codes are too ambiguous for fuzzy matching. They must be
            # recognized in full; fuzziness is reserved for normal words.
            if len(p.replace(' ', '')) < 4:
                continue
            word_count = max(1, len(p.split()))
            words = t.split()
            candidates = [' '.join(words[i:i + word_count]) for i in range(len(words))]
            for candidate in candidates:
                if not candidate:
                    continue
                length_ratio = min(len(p), len(candidate)) / max(len(p), len(candidate))
                if length_ratio < 0.70:
                    continue
                best = max(best, int(round(fuzz.ratio(p, candidate))))
    return best

def create_engine():
    from paddleocr import PaddleOCR
    det, rec = MODEL_ROOT/'PP-OCRv5_mobile_det', MODEL_ROOT/'eslav_PP-OCRv5_mobile_rec'
    if not det.exists() or not rec.exists(): raise FileNotFoundError('Не найдены OCR-модели')
    return PaddleOCR(text_detection_model_name='PP-OCRv5_mobile_det', text_detection_model_dir=str(det),
        text_recognition_model_name='eslav_PP-OCRv5_mobile_rec', text_recognition_model_dir=str(rec),
        use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False,
        enable_mkldnn=False, cpu_threads=max(2,min(8,os.cpu_count() or 4)))

class ChatOCRWorker(QObject):
    ready = Signal(); scan = Signal(list, float); error = Signal(str); stopped = Signal()
    def __init__(self, region, confidence, contrast):
        super().__init__(); self.region={k:int(region[k]) for k in ('left','top','width','height')}
        self.confidence=confidence/100; self.contrast=contrast; self.stop_event=threading.Event(); self.pause_until=0
    def stop(self): self.stop_event.set()
    def pause(self, seconds=30): self.pause_until=max(self.pause_until,time.monotonic()+seconds)
    @Slot()
    def run(self):
        try:
            ocr=create_engine(); self.ready.emit()
            with mss.mss() as grabber:
                while not self.stop_event.is_set():
                    wait=self.pause_until-time.monotonic()
                    if wait>0: self.stop_event.wait(min(wait,.5)); continue
                    started=time.perf_counter(); shot=np.asarray(grabber.grab(self.region)); frame=cv2.cvtColor(shot,cv2.COLOR_BGRA2BGR)
                    if self.contrast:
                        lab=cv2.cvtColor(frame,cv2.COLOR_BGR2LAB); l,a,b=cv2.split(lab)
                        frame=cv2.cvtColor(cv2.merge((cv2.createCLAHE(2.2,(8,8)).apply(l),a,b)),cv2.COLOR_LAB2BGR)
                    result=list(ocr.predict(frame)); rows=[]
                    if result:
                        data=result[0].json.get('res',{}); boxes=data.get('rec_boxes',[])
                        for i,(text,score) in enumerate(zip(data.get('rec_texts',[]),data.get('rec_scores',[]))):
                            if str(text).strip() and float(score)>=self.confidence:
                                box=boxes[i] if i<len(boxes) else [0,i,0,0]; rows.append((float(box[1]),float(box[0]),str(text).strip(),round(float(score)*100,1)))
                    rows.sort(); self.scan.emit([{'text':r[2],'confidence':r[3]} for r in rows],time.perf_counter()-started)
                    self.stop_event.wait(.35)
        except Exception: self.error.emit(traceback.format_exc())
        finally: self.stopped.emit()
