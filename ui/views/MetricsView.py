# app/ui/views/MetricsView.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSizePolicy,
    QMessageBox, QPushButton, QScrollArea, QFrame
)

from core.registry import Registry, ModelEntry


class MetricsView(QWidget):
    sig_back = Signal()  # botón volver

    def __init__(self, registry: Registry):
        super().__init__()
        self.registry = registry
        self._species_key: Optional[str] = None
        self._model_key: Optional[str] = None

        self._pixmap_orig: Optional[QPixmap] = None
        self._available_imgs: Dict[str, Path] = {}  # {"Externa": Path(...), "Interna": Path(...), "Otras: <nombre>": Path(...)}

        self._build()
        self._populate_species()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # ---- Barra superior
        top = QHBoxLayout()
        self.btn_back = QPushButton("← Volver")
        self.btn_back.clicked.connect(lambda: self.sig_back.emit())

        self.box_species = QComboBox()
        self.box_models = QComboBox()
        self.box_species.currentIndexChanged.connect(self._on_species_changed)
        self.box_models.currentIndexChanged.connect(self._on_model_changed)

        # NUEVO: selector de fuente (Interna / Externa / Otras…)
        self.box_source = QComboBox()
        self.box_source.currentIndexChanged.connect(self._on_source_changed)

        top.addWidget(self.btn_back, 0, alignment=Qt.AlignLeft)
        top.addSpacing(12)
        top.addWidget(QLabel("Especie:"))
        top.addWidget(self.box_species, 2)
        top.addWidget(QLabel("Modelo:"))
        top.addWidget(self.box_models, 2)
        top.addWidget(QLabel("Métrica:"))
        top.addWidget(self.box_source, 2)
        top.addStretch(1)

        # ---- Centro: imagen (scroll) + info
        mid = QHBoxLayout()

        self.lbl_img = QLabel("Sin imagen de matriz de confusión")
        self.lbl_img.setAlignment(Qt.AlignCenter)
        # anti-zoom loop:
        self.lbl_img.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.lbl_img.setScaledContents(True)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.lbl_img)
        self.scroll.setFrameShape(QFrame.NoFrame)


        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setMinimumWidth(280)
        self.lbl_info.setStyleSheet("color:#555;")
        self.lbl_info.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        mid.addWidget(self.scroll, 3)
        mid.addWidget(self.lbl_info, 1)

        root.addLayout(top)
        root.addLayout(mid)

    # ---------- Populate ----------
    def _populate_species(self):
        self.box_species.clear()
        for sk in self.registry.species_keys:
            sp = self.registry.get_species(sk)
            self.box_species.addItem(sp.display_name, userData=sk)
        if self.box_species.count() > 0:
            self.box_species.setCurrentIndex(0)

    def _populate_models(self, species_key: str):
        self.box_models.clear()
        sp = self.registry.get_species(species_key)
        for mkey, entry in sp.models.items():
            self.box_models.addItem(f"{entry.name} ({mkey})", userData=mkey)
        if self.box_models.count() > 0:
            self.box_models.setCurrentIndex(0)

    def _populate_sources(self, found: Dict[str, Path]):
        self.box_source.blockSignals(True)
        self.box_source.clear()

        # orden fijo y corto
        for label in ["Interna", "Externa"]:
            if label in found:
                self.box_source.addItem(label, userData=label)

        self.box_source.blockSignals(False)

        if self.box_source.count() > 0:
            self.box_source.setCurrentIndex(0)

    # ---------- Events ----------
    def _on_species_changed(self, _idx: int):
        skey = self.box_species.currentData()
        if not skey:
            return
        self._species_key = skey
        self._populate_models(skey)

    def _on_model_changed(self, _idx: int):
        mkey = self.box_models.currentData()
        if not (self._species_key and mkey):
            return
        self._model_key = mkey
        sp = self.registry.get_species(self._species_key)
        me = sp.models[mkey]
        self._load_metrics_for_model(me)

    def _on_source_changed(self, _idx: int):
        if not self._available_imgs:
            return
        key = self.box_source.currentData()
        if not key:
            return
        path = self._available_imgs.get(key)
        if not path:
            return
        self._load_image(path)

    # ---------- Public API ----------
    def set_active(self, species_key: str, model_key: str):
        sp_idx = max(0, self.box_species.findData(species_key))
        self.box_species.setCurrentIndex(sp_idx)
        md_idx = max(0, self.box_models.findData(model_key))
        self.box_models.setCurrentIndex(md_idx)

    # ---------- Internals ----------
    def _load_metrics_for_model(self, me: ModelEntry):
        # Info textual
        parent_dir = Path(me.path).resolve().parent
        classes_dir = Path(me.classes_path).resolve().parent
        info = [
            f"<b>{me.name}</b>",
            f"<i>{me.description or ''}</i>",
            f"<br><b>Ruta modelo:</b> {me.path}",
            f"<b>Clases:</b> {me.classes_path}",
        ]
        self.lbl_info.setText("<br>".join(info))

        # Buscar múltiples imágenes
        found = self._find_confusion_images([parent_dir, classes_dir])
        self._available_imgs = found
        self._populate_sources(found)
        
        if self.box_source.count() > 0:
            self._on_source_changed(self.box_source.currentIndex())
        else:
            self._pixmap_orig = None
            self.lbl_img.setText("No se encontraron matrices de confusión (cm_val.png / cm_test.png).")


        # Cargar la primera seleccionada en el combo
        key = self.box_source.currentData()
        path = found.get(key) if key else next(iter(found.values()))
        self._load_image(path)

    def _load_image(self, path: Path):
        pm = QPixmap(str(path))
        if pm.isNull():
            QMessageBox.warning(self, "Imagen inválida", f"No se pudo abrir:\n{path}")
            self._pixmap_orig = None
            self.lbl_img.setText("Imagen inválida.")
            #self.lbl_img.clear()
            return
        self._pixmap_orig = pm
        self._apply_fit()

    def _find_confusion_images(self, dirs: List[Path]) -> Dict[str, Path]:
        """
        Busca únicamente:
        - Interna  -> cm_val.png
        - Externa  -> cm_test.png
        Prioridad: carpeta del modelo (parent_dir) sobre la de classes.
        Evita duplicados si aparecen en ambas carpetas.
        """
        # nombres fijos (¡listas, no strings!)
        internal_names = ["cm_val.png"]
        external_names = ["cm_test.png"]

        result: Dict[str, Path] = {}
        seen: set[str] = set()  # rutas absolutas vistas (para evitar duplicados)

        def search_one(label: str, names: List[str]) -> Optional[Path]:
            # prioriza orden de dirs recibido (primero parent_dir, luego classes_dir)
            for d in dirs:
                for n in names:
                    p = (d / n).resolve()
                    if p.is_file():
                        ap = str(p)
                        if ap in seen:
                            continue
                        seen.add(ap)
                        result[label] = p
                        return p
            return None

        # Primero Interna, luego Externa (o cambia el orden si prefieres)
        search_one("Interna", internal_names)
        search_one("Externa", external_names)

        return result


    def resizeEvent(self, _e):
        self._apply_fit()

    def _apply_fit(self):
        if not self._pixmap_orig:
            return
        avail_w = max(1, self.scroll.viewport().width())
        avail_h = max(1, self.scroll.viewport().height())
        scaled = self._pixmap_orig.scaled(avail_w, avail_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_img.setPixmap(scaled)