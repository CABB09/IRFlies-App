"""
predictor.py — Inferencia sin dependencias de UI.
Expone funciones para predecir una o muchas imágenes y devolver probabilidades,
Top-1/Top-2, y métricas auxiliares.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Iterable
import numpy as np
import tensorflow as tf

from .preprocessor import batch_from_paths
from .model_loader import LoadedModel
from .config import AppConfig


@dataclass(frozen=True)
class Prediction:
    file: str
    top1_class: str
    top1_prob: float
    top2_class: str | None
    top2_prob: float | None
    full_probs: Dict[str, float]  # clase -> prob
    confidence: str               # "high" | "ambiguous" | "low"
    gap_pp: float                 # diferencia top1-top2 en puntos porcentuales (0..1)


def _softmax(x: np.ndarray) -> np.ndarray:
    # Por si el modelo ya devuelve probs, lo dejamos idempotente
    x = x - np.max(x, axis=-1, keepdims=True)
    ex = np.exp(x)
    return ex / np.sum(ex, axis=-1, keepdims=True)


def _confidence_label(p1: float, p2: float, cfg: AppConfig) -> str:
    gap = p1 - p2
    if p1 >= cfg.confidence_threshold and gap >= cfg.top2_margin_pp:
        return "high"
    if gap < cfg.top2_margin_pp:
        return "ambiguous"
    return "low"


def predict_files(
    lm: LoadedModel,
    cfg: AppConfig,
    files: Iterable[str],
) -> List[Prediction]:
    paths = list(files)
    if not paths:
        return []

    # lote en memoria (si necesitas chunking, puedes dividir aquí)
    batch = batch_from_paths(paths, cfg.image_size)

    # inferencia
    logits_or_probs: np.ndarray = lm.model(batch, training=False).numpy()  # [N,C]
    # forzamos softmax por robustez
    probs = _softmax(logits_or_probs)

    preds: List[Prediction] = []
    for i, path in enumerate(paths):
        pv = probs[i]
        order = np.argsort(-pv)  # desc
        t1, t2 = order[0], (order[1] if pv.shape[0] > 1 else None)

        top1_c = lm.idx_to_class[int(t1)]
        top1_p = float(pv[int(t1)])
        top2_c = (lm.idx_to_class[int(t2)] if t2 is not None else None)
        top2_p = (float(pv[int(t2)]) if t2 is not None else None)

        conf = _confidence_label(top1_p, top2_p or 0.0, cfg)
        gap_pp = top1_p - (top2_p or 0.0)

        full = {lm.idx_to_class[j]: float(pv[j]) for j in range(len(pv))}

        preds.append(
            Prediction(
                file=path,
                top1_class=top1_c,
                top1_prob=top1_p,
                top2_class=top2_c,
                top2_prob=top2_p,
                full_probs=full if cfg.export_full_prob_vector else {},
                confidence=conf,
                gap_pp=gap_pp,
            )
        )
    return preds