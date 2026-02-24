# app/ui/widgets/ModelVariantPicker.py
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QComboBox, QHBoxLayout
from core.registry import Registry


class ModelVariantPicker(QWidget):
    sig_changed = Signal(str)  # model_key

    def __init__(self):
        super().__init__()
        self.box = QComboBox()
        self.box.currentIndexChanged.connect(self._emit)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.box)

    def populate_from_registry_species(self, species_key: str, registry: Registry):
        self.box.clear()
        sp = registry.get_species(species_key)
        for mkey, entry in sp.models.items():
            self.box.addItem(f"{entry.name} ({mkey})", userData=mkey)
        if self.box.count() > 0:
            self.box.setCurrentIndex(0)
            #self._emit()

    def _emit(self):
        if self.box.count() == 0:
            return
        key = self.box.currentData()
        if key:
            self.sig_changed.emit(key)