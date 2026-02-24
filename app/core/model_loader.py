"""
model_loader.py — Carga robusta de modelos Keras y clases.
Valida coherencia entre el .keras y el archivo classes.json.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import tensorflow as tf
from tensorflow.keras.models import load_model


@dataclass(frozen=True)
class LoadedModel:
    model: tf.keras.Model
    classes: List[str]           # p.ej. ["-5","-4","-3","-2"]
    class_to_idx: Dict[str, int] # {"-5":0,...}
    idx_to_class: Dict[int, str] # {0:"-5",...}
    path: str                    # ruta del .keras
    classes_path: str            # ruta del classes.json


def _load_classes_json(path: Path) -> List[str]:
    if not path.is_file():
        raise FileNotFoundError(f"No existe classes.json en: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    # formatos admitidos:
    # 1) {"classes": ["-5","-4",...]}
    # 2) {"class_to_idx": {"-5":0,"-4":1,...}}
    if "classes" in data and isinstance(data["classes"], list):
        return [str(x) for x in data["classes"]]

    if "class_to_idx" in data and isinstance(data["class_to_idx"], dict):
        sorted_by_idx = sorted(((int(v), str(k)) for k, v in data["class_to_idx"].items()),
                               key=lambda t: t[0])
        return [name for _, name in sorted_by_idx]

    raise ValueError("classes.json inválido: se esperaba 'classes' o 'class_to_idx'")


def load_keras_model(model_path: str, classes_json_path: str) -> LoadedModel:
    mp = Path(model_path).resolve()
    cp = Path(classes_json_path).resolve()

    if not mp.is_file():
        raise FileNotFoundError(f"Modelo .keras no encontrado: {mp}")

    classes = _load_classes_json(cp)
    model = load_model(mp, compile=False)

    # Validación básica del número de salidas
    out = model.outputs[0]
    num_outputs = int(out.shape[-1])
    if num_outputs != len(classes):
        raise ValueError(
            f"Incompatibilidad modelo↔clases: salidas={num_outputs} vs clases={len(classes)}"
        )

    class_to_idx = {c: i for i, c in enumerate(classes)}
    idx_to_class = {i: c for c, i in class_to_idx.items()}

    return LoadedModel(
        model=model,
        classes=classes,
        class_to_idx=class_to_idx,
        idx_to_class=idx_to_class,
        path=str(mp),
        classes_path=str(cp),
    )