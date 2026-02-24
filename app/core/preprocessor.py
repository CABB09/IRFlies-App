"""
preprocessor.py — Carga/decodifica imágenes y aplica el mismo preprocesamiento
que en el entrenamiento: EXIF transpose, RGB, resize 224, float32 [0..255],
y preprocess_enetv2.
"""

from __future__ import annotations
from pathlib import Path
from typing import Iterable, List

import numpy as np
from PIL import Image, ImageOps
import tensorflow as tf
from tensorflow.keras.applications.efficientnet_v2 import preprocess_input as preprocess_enetv2


IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".JPG", ".JPEG", ".PNG", ".BMP")


def load_and_preprocess(path: str, image_size: int) -> np.ndarray:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Imagen no encontrada: {p}")

    img = Image.open(p)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = img.resize((image_size, image_size), Image.Resampling.BILINEAR)
    arr = np.asarray(img, dtype=np.float32)  # [H,W,3] en [0..255]
    arr = preprocess_enetv2(arr)             # EfficientNetV2 espera float [0..255] luego normaliza
    return arr  # shape (H,W,3), float32


def batch_from_paths(paths: Iterable[str], image_size: int) -> np.ndarray:
    arrays: List[np.ndarray] = [load_and_preprocess(p, image_size) for p in paths]
    if not arrays:
        raise ValueError("Lista de paths vacía")
    batch = np.stack(arrays, axis=0)  # [N,H,W,3]
    return batch.astype(np.float32)