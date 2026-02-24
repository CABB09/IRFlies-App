"""
tf_session.py — Inicialización segura de TensorFlow para inferencia.
Configura memory growth en GPU, threads y warm-up opcional.
"""

from __future__ import annotations
from typing import Optional
from .config import AppConfig

import tensorflow as tf


def _enable_memory_growth() -> None:
    gpus = tf.config.list_physical_devices("GPU")
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except Exception:  # pragma: no cover
            pass


def _set_intra_inter_threads(num_threads: Optional[int]) -> None:
    if num_threads is None:
        return
    try:
        tf.config.threading.set_inter_op_parallelism_threads(num_threads)
        tf.config.threading.set_intra_op_parallelism_threads(num_threads)
    except Exception:
        # No crítico en inferencia si no aplica
        pass


def _warmup_dummy(image_size: int) -> None:
    # crea un batch 1 de zeros con shape esperado por EfficientNetV2
    dummy = tf.zeros((1, image_size, image_size, 3), dtype=tf.float32)
    # op tonto: +0 para forzar grafo y kernels
    _ = dummy + 0.0


def init_tf_session(cfg: AppConfig) -> None:
    if cfg.tf_allow_memory_growth:
        _enable_memory_growth()
    _set_intra_inter_threads(cfg.tf_num_threads)
    if cfg.tf_warmup_on_start:
        _warmup_dummy(cfg.image_size)