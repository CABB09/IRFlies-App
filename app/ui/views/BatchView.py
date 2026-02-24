# app/ui/views/BatchView.py

from __future__ import annotations
from typing import List

from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar

from core.config import AppConfig
from core.model_loader import LoadedModel
from core.predictor import predict_files, Prediction

from ..widgets.BatchTable import BatchTable


class Worker(QObject):
    sig_progress = Signal(int, int)           # done, total
    sig_results = Signal(list)                # List[Prediction]

    def __init__(self, lm: LoadedModel, cfg: AppConfig, paths: List[str]):
        super().__init__()
        self.lm = lm
        self.cfg = cfg
        self.paths = paths
        self._stop = False

    def stop(self):  # opcional
        self._stop = True

    def run(self):
        # Simple: una sola pasada (si necesitas chunks, puedes trocear aquí)
        preds = predict_files(self.lm, self.cfg, self.paths)
        self.sig_results.emit(preds)


class BatchView(QWidget):
    sig_back = Signal()
    sig_run_batch = Signal(list)
    sig_results_ready = Signal()

    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg
        self._results: List[Prediction] = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        self.btn_back = QPushButton("← Volver")
        self.btn_back.clicked.connect(self.sig_back.emit)
        self.lbl_info = QLabel("Arrastra imágenes en Home o usa 'Abrir imágenes…' en la barra superior.")
        top.addWidget(self.btn_back, 0)
        top.addWidget(self.lbl_info, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.table = BatchTable()

        lay.addLayout(top)
        lay.addWidget(self.progress)
        lay.addWidget(self.table)

    # ---------- External API ----------
    def run_batch(self, lm: LoadedModel, species: str, model_key: str, model_hash: str, paths: List[str]):
        self._results = []
        self.table.clear_rows()
        self.progress.setVisible(True)

        self.thread = QThread(self)
        self.worker = Worker(lm, self.cfg, paths)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.sig_results.connect(lambda preds: self._on_results(preds, species, model_key, model_hash))
        self.worker.sig_results.connect(self.thread.quit)
        self.worker.sig_results.connect(self.worker.deleteLater)
        self.thread.finished.connect(lambda: self.progress.setVisible(False))
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _on_results(self, preds: List[Prediction], species: str, model_key: str, model_hash: str):
        self._results = preds
        self.table.populate(preds, species, model_key, model_hash)
        self.progress.setVisible(False)
        self.sig_results_ready.emit() 

    def has_results(self) -> bool:
        return len(self._results) > 0

    def get_results(self) -> List[Prediction]:
        return list(self._results)

    def clear(self):
        self._results = []
        self.table.clear_rows()