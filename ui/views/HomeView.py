# app/ui/views/HomeView.py
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from core.config import AppConfig
from core.registry import Registry
from core.model_loader import LoadedModel
from core.predictor import Prediction

from ..widgets.SpeciesSelector import SpeciesSelector
from ..widgets.ModelVariantPicker import ModelVariantPicker
from ..widgets.DropZone import DropZone
from ..widgets.ResultCard import ResultCard
from ..widgets.BusyOverlay import BusyOverlay
from ..widgets.FitImageView import FitImageView


class HomeView(QWidget):
    sig_species_model_changed = Signal(str, str)  # species_key, model_key
    sig_predict_one = Signal(str)                 # file
    sig_predict_many = Signal(list)               # files

    def __init__(self, registry: Registry, cfg: AppConfig):
        super().__init__()
        self.registry = registry
        self.cfg = cfg
        self.loaded: Optional[LoadedModel] = None
        self.species_key: Optional[str] = None
        self.model_key: Optional[str] = None

        self._build()
        
        # Preseleccionar si solo hay una especie en el registry
        keys = self.registry.species_keys
        if len(keys) == 1:
            self._on_species_changed(keys[0])   # pobla modelos
            self.species.setEnabled(False)      # bloquea combo de especie


    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        # Top controls
        top = QHBoxLayout()
        self.species = SpeciesSelector(self.registry.species_keys)
        self.models = ModelVariantPicker()
        self.models.setEnabled(False)

        self.species.sig_changed.connect(self._on_species_changed)
        self.models.sig_changed.connect(self._on_model_changed)

        top.addWidget(QLabel("Especie:"))
        top.addWidget(self.species, 2)
        top.addWidget(QLabel("Modelo:"))
        top.addWidget(self.models, 2)
        top.addStretch(1)

        # Centro: DropZone + Visor de Imagen (FitImageView) + Resultado
        mid = QHBoxLayout()
        self.drop = DropZone()
        self.drop.setEnabled(False)

        # Visor que evita loops de zoom (fit-to-view dentro de QScrollArea)
        self.image_view = FitImageView()

        # Resultado
        self.result = ResultCard()

        # Conexiones DropZone
        # Una imagen: mostrar en visor y pedir predicción
        self.drop.sig_file.connect(self._on_single_file)
        # Varias: mandar al flujo batch
        self.drop.sig_many.connect(lambda L: self.sig_predict_many.emit(L))

        # Distribución (ajusta proporciones si quieres)
        mid.addWidget(self.drop, 2)
        mid.addWidget(self.image_view, 6)
        mid.addWidget(self.result, 2)

        root.addLayout(top)
        root.addLayout(mid)

        # Overlay de ocupado (para predicción individual)
        self.overlay = BusyOverlay(self)

    # ---------- API para MainWindow ----------
    def set_loaded_model(self, lm: LoadedModel, species_key: str, model_key: str):
        self.loaded = lm
        self.species_key = species_key
        self.model_key = model_key
        self.result.set_classes(lm.classes)
        self.drop.setEnabled(True)

    def show_prediction(self, pred: Prediction):
        self.result.set_prediction(pred)

    def show_busy(self, text: str = "Clasificando…"):
        self.overlay.show_busy(text)

    def hide_busy(self):
        self.overlay.hide_busy()

    # ---------- Internos ----------
    def _on_single_file(self, path: str):
        # Mostrar inmediatamente la imagen en el visor
        pm = QPixmap(path)
        self.image_view.set_pixmap(pm)
        # Disparar predicción
        self.sig_predict_one.emit(path)

    # ---------- Events ----------
    def _on_species_changed(self, key: str):
        self.species_key = key
        # Poblar combo de modelos desde registry
        self.models.populate_from_registry_species(key, self.registry)
        self.models.setEnabled(True)

    def _on_model_changed(self, model_key: str):
        self.model_key = model_key
        if self.species_key and self.model_key:
            self.sig_species_model_changed.emit(self.species_key, self.model_key)
