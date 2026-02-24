# app/core/eyes_detector.py
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional
import sys

import torch  # <<< seguimos usando torch para el parche

# --- Parche para PyTorch 2.6+ ---
_orig_torch_load = torch.load

def _torch_load_ultralytics(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_torch_load(*args, **kwargs)

torch.load = _torch_load_ultralytics
# --- fin del parche ---

from ultralytics import YOLO


MODEL_FILENAME = "eyes_yolov8n_best.pt"


def _resolve_weights_path() -> Path:
    """
    Intenta encontrar el .pt en varias rutas razonables,
    tanto en desarrollo como dentro del .exe de PyInstaller.
    """
    here = Path(__file__).resolve()

    candidates = []

    # ----- Entorno de desarrollo -----
    # Proyecto típico: <root>/app/core/eyes_detector.py
    # 1) <root>/app/models/eyes_yolov8n_best.pt
    candidates.append(here.parent.parent / "models" / MODEL_FILENAME)
    # 2) por si core y models fueran hermanos
    candidates.append(here.parent / "models" / MODEL_FILENAME)

    # ----- Entorno congelado (PyInstaller) -----
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        exe_dir = Path(sys.executable).parent

        # 3) models directamente dentro de _MEIPASS
        candidates.append(meipass / "models" / MODEL_FILENAME)
        # 4) app/models dentro de _MEIPASS (otra estructura típica)
        candidates.append(meipass / "app" / "models" / MODEL_FILENAME)
        # 5) models junto al .exe (útil si distribuyes el .pt como archivo externo)
        candidates.append(exe_dir / "models" / MODEL_FILENAME)

    for c in candidates:
        if c.is_file():
            return c

    msg = "No se encontró el modelo de ojos. Se probaron estas rutas:\n" + \
          "\n".join(str(p) for p in candidates)
    raise FileNotFoundError(msg)


class EyesDetector:
    """
    Wrapper sobre YOLOv8 para detectar la región de ojos.
    Devuelve [(x, y, w, h), ...] en píxeles.
    """

    def __init__(self, weights_path: str | Path):
        self.weights_path = str(weights_path)
        self._model: Optional[YOLO] = None

    def _lazy_model(self) -> YOLO:
        if self._model is None:
            self._model = YOLO(self.weights_path)
        return self._model

    def detect(self, img_path: str, conf: float = 0.25) -> List[Tuple[int, int, int, int]]:
        model = self._lazy_model()
        res = model.predict(source=img_path, conf=conf, verbose=False)[0]

        rois: List[Tuple[int, int, int, int]] = []
        for box in res.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            x = max(0, int(round(x1)))
            y = max(0, int(round(y1)))
            w = max(1, int(round(x2 - x1)))
            h = max(1, int(round(y2 - y1)))
            rois.append((x, y, w, h))
        return rois


def default_eyes_detector() -> EyesDetector:
    """
    Crea el detector usando el archivo eyes_yolov8n_best.pt
    ubicado en alguna de las rutas soportadas por _resolve_weights_path().
    """
    weights = _resolve_weights_path()
    return EyesDetector(weights)