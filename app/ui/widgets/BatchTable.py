from __future__ import annotations
from typing import List

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QSizePolicy
from core.predictor import Prediction


class BatchTable(QWidget):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Archivo", "Edad", "%", "Edad 2ª", "% 2ª", "Gap pp", "Confianza", "Especie/Modelo", "Probs"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.table)

    def clear_rows(self):
        self.table.setRowCount(0)

    def populate(self, preds: List[Prediction], species: str, model_key: str, model_hash: str):
        self.table.setRowCount(len(preds))
        for r, p in enumerate(preds):
            probs_txt = "; ".join(f"{k}:{v:.2f}" for k, v in p.full_probs.items())
            vals = [
                p.file,
                p.top1_class, f"{p.top1_prob*100:.1f}",
                (p.top2_class or ""), (f"{(p.top2_prob or 0.0)*100:.1f}"),
                f"{p.gap_pp*100:.1f}", p.confidence,
                f"{species}/{model_key} ({model_hash})",
                probs_txt
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c in (2, 4, 5):
                    item.setTextAlignment(0x0004 | 0x0080)  # AlignRight|AlignVCenter
                self.table.setItem(r, c, item)