# app/ui/views/CropView.py
from __future__ import annotations
import os, tempfile, time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QMessageBox
)

from PIL import Image
from ..widgets.CropGraphicsView import CropGraphicsView
from core.eyes_detector import default_eyes_detector, EyesDetector

@dataclass
class _ImgState:
    path: str
    rois: List[Tuple[int,int,int,int]]  # (x,y,w,h)

class CropView(QWidget):
    """
    Permite recortar 1..N ROIs por imagen (con zoom/pan) y emite rutas de recortes listos para predecir.
    """
    sig_cancel = Signal()
    sig_crops_ready = Signal(list)  # list[str] rutas de recortes

    def __init__(self, cfg=None):
        super().__init__()
        self.cfg = cfg
        self._images: List[_ImgState] = []
        self._idx: int = -1
        self._out_dir = ""  # carpeta temporal para los recortes
        self._eyes_detector: EyesDetector | None = None  # <<< NUEVO
        self._build()

    # -------- UI --------
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        # Top bar
        top = QHBoxLayout()
        self.btn_back = QPushButton("← Volver")
        self.btn_back.clicked.connect(self.sig_cancel.emit)
        self.lbl_title = QLabel("Recortar imágenes")
        self.lbl_title.setStyleSheet("font-weight:600;")
        top.addWidget(self.btn_back, 0)
        top.addWidget(self.lbl_title, 1, alignment=Qt.AlignLeft)

        # Center
        center = QHBoxLayout()
        self.view = CropGraphicsView()
        self.view.setMinimumSize(640, 480)
        self.view.sig_rois_changed.connect(self._on_view_rois_changed)

        right = QVBoxLayout()
        self.lbl_file = QLabel("—")
        self.list_rois = QListWidget()
        self.btn_auto = QPushButton("Cortes automáticos (YOLO)")
        self.btn_auto.clicked.connect(self._auto_detect_rois)
        self.btn_remove_last = QPushButton("Eliminar último ROI")
        self.btn_clear = QPushButton("Limpiar ROIs")

        self.btn_remove_last.clicked.connect(self._remove_last)
        self.btn_clear.clicked.connect(self._clear_rois)

        right.addWidget(QLabel("Archivo:"))
        right.addWidget(self.lbl_file)
        right.addWidget(QLabel("ROIs (x,y,w,h):"))
        right.addWidget(self.list_rois, 1)
        right.addWidget(self.btn_auto)
        right.addWidget(self.btn_remove_last)
        right.addWidget(self.btn_clear)

        center.addWidget(self.view, 4)
        center.addLayout(right, 2)

        # Bottom
        bottom = QHBoxLayout()
        self.btn_prev = QPushButton("← Anterior")
        self.btn_next = QPushButton("Siguiente →")
        self.btn_accept = QPushButton("Aceptar y predecir")
        self.btn_cancel = QPushButton("Cancelar")

        self.btn_prev.clicked.connect(self._prev)
        self.btn_next.clicked.connect(self._next)
        self.btn_accept.clicked.connect(self._accept)
        self.btn_cancel.clicked.connect(self.sig_cancel.emit)

        bottom.addWidget(self.btn_prev)
        bottom.addWidget(self.btn_next)
        bottom.addStretch(1)
        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.btn_accept)

        root.addLayout(top)
        root.addLayout(center, 1)
        root.addLayout(bottom)

    # -------- API externa --------
    def load_images(self, paths: List[str]):
        """Cargar 1..N imágenes; se reinicia el estado."""
        self._images = [_ImgState(path=p, rois=[]) for p in paths]
        self._idx = 0 if self._images else -1
        self._out_dir = ""
        self._refresh_view()

    # -------- Internos --------
    def _refresh_view(self):
        self.list_rois.clear()
        if self._idx < 0 or self._idx >= len(self._images):
            self.view.set_image(QPixmap())
            self.lbl_file.setText("—")
            self.lbl_title.setText("Recortar imágenes")
            return

        st = self._images[self._idx]
        pm = QPixmap(st.path)
        if pm.isNull():
            QMessageBox.warning(self, "Imagen inválida", f"No se pudo abrir:\n{st.path}")
            return
        self.view.set_image(pm)
        self.lbl_file.setText(Path(st.path).name)
        self.lbl_title.setText(f"Imagen {self._idx+1} / {len(self._images)}")

        # Re-dibujar ROIs ya guardados en este índice
        if st.rois:
            self.view.set_rois(st.rois)
            self._update_rois_listwidget(st.rois)

    def _capture_rois_from_view(self):
        """Leer ROIs del view y guardarlos en el estado actual."""
        if self._idx < 0: 
            return
        st = self._images[self._idx]
        st.rois = self.view.rois()
        self._update_rois_listwidget(st.rois)

    def _on_view_rois_changed(self, rois: List[Tuple[int,int,int,int]]):
        if 0 <= self._idx < len(self._images):
            self._images[self._idx].rois = list(rois)
        self._update_rois_listwidget(rois)
        
    def _update_rois_listwidget(self, rois):
        self.list_rois.clear()
        for i, r in enumerate(rois, start=1):
            x, y, w, h = r
            QListWidgetItem(f"ROI {i}: x={x}, y={y}, w={w}, h={h}", self.list_rois)

    def _remove_last(self):
        self.view.remove_last_roi()

    def _clear_rois(self):
        self.view.clear_rois()

    def _prev(self):
        self._capture_rois_from_view()
        if self._idx > 0:
            self._idx -= 1
            self._refresh_view()

    def _next(self):
        self._capture_rois_from_view()
        if self._idx + 1 < len(self._images):
            self._idx += 1
            self._refresh_view()

    def _accept(self):
        # Asegurar que el último estado esté sincronizado
        self._capture_rois_from_view()

        # Verificar que haya al menos un ROI total
        num_total = sum(len(s.rois) for s in self._images)
        if num_total == 0:
            QMessageBox.information(self, "Sin ROIs", "Dibuja al menos un recorte antes de continuar.")
            return

        # Carpeta temporal para esta sesión
        if not self._out_dir:
            base = Path(tempfile.gettempdir()) / "IRFLies" / "crops"
            base.mkdir(parents=True, exist_ok=True)
            self._out_dir = str(base / time.strftime("%Y%m%d_%H%M%S"))
            Path(self._out_dir).mkdir(parents=True, exist_ok=True)

        out_paths: List[str] = []
        for s in self._images:
            if not s.rois:
                continue
            try:
                with Image.open(s.path) as im:
                    w0, h0 = im.size
                    for i, (x,y,w,h) in enumerate(s.rois, start=1):
                        # Limitar por seguridad
                        x2 = max(0, min(x, w0-1))
                        y2 = max(0, min(y, h0-1))
                        w2 = max(1, min(w, w0 - x2))
                        h2 = max(1, min(h, h0 - y2))
                        crop = im.crop((x2, y2, x2+w2, y2+h2))
                        name = f"{Path(s.path).stem}__roi{i}_x{x2}_y{y2}_w{w2}_h{h2}.jpg"
                        out = str(Path(self._out_dir) / name)
                        crop.save(out, quality=95)
                        out_paths.append(out)
            except Exception as e:
                QMessageBox.critical(self, "Error recortando", f"{s.path}\n\n{e}")
                return

        if not out_paths:
            QMessageBox.information(self, "Sin recortes válidos", "No se generaron recortes.")
            return

        self.sig_crops_ready.emit(out_paths)
        
    def _get_eyes_detector(self) -> EyesDetector:
        if self._eyes_detector is None:
            self._eyes_detector = default_eyes_detector()
        return self._eyes_detector
    
    def _auto_detect_rois(self):
        """Usa el modelo YOLO para detectar la ROI de ojos en la imagen actual."""
        if self._idx < 0 or self._idx >= len(self._images):
            return

        st = self._images[self._idx]
        img_path = st.path

        try:
            det = self._get_eyes_detector()
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Modelo no encontrado", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error cargando modelo YOLO", str(e))
            return

        try:
            rois = det.detect(img_path, conf=0.25)
        except Exception as e:
            QMessageBox.critical(self, "Error en detección", f"{img_path}\n\n{e}")
            return

        if not rois:
            QMessageBox.information(self, "Sin detecciones", "No se detectaron ojos en esta imagen.")
            return

        # Esto dibuja los rectángulos + números y dispara sig_rois_changed,
        # que a su vez actualiza self._images[_idx].rois y la lista de la derecha.
        self.view.set_rois(rois)

