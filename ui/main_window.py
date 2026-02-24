# app/ui/main_window.py

from __future__ import annotations
from pathlib import Path
from typing import Optional
import sys
import os

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QStackedWidget
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QStandardPaths

from core.config import load_app_config, AppConfig
from core.registry import Registry
from core.model_loader import LoadedModel
from core.predictor import predict_files
from core.storage import append_to_global_csv, export_run_csv
from core.utils import iter_images_in_paths, file_sha1

from core.model_manager import ModelManager

from .views.HomeView import HomeView
from .views.BatchView import BatchView
from .views.MetricsView import MetricsView
from .views.CropView import CropView


def resource_path(*parts: str) -> Path:
    """
    Devuelve una ruta válida tanto en dev como en frozen (PyInstaller).
    - ONEDIR: sys.executable -> dist/IRFLies-App/IRFLies-App.exe
    - ONEFILE: sys._MEIPASS apunta a la carpeta temporal
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        # En dev es más seguro usar el directorio del archivo (no el cwd)
        base = Path(__file__).resolve().parent
    return base.joinpath(*parts)


class MainWindow(QMainWindow):
    sig_predict_many = Signal(list)   # lista de rutas

    def __init__(self, registry: Optional[Registry] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Estado básico / config
        self.cfg: AppConfig = load_app_config()

        # >>> Importante: NO pisar el Registry autodetectado
        # Usa el que te pasan o crea uno que autodetecta registry.yaml (works en dev y frozen)
        self.registry = registry or Registry()

        self.selected_species_key: Optional[str] = None
        self.selected_model_key: Optional[str] = None
        self.loaded: Optional[LoadedModel] = None
        self.model_hash: str = ""

        # Ventana
        self.setWindowTitle("IRFLies - Age Classifier")
        # Icono que funciona en dev y en el .exe
        icon_file = resource_path("app", "assets", "icons", "app_icon.png")
        if icon_file.is_file():
            self.setWindowIcon(QIcon(str(icon_file)))
        self.setGeometry(120, 80, 1200, 750)

        # Manager asíncrono
        self.model_manager = ModelManager()
        self.model_manager.sig_loaded.connect(self._on_model_loaded)
        self.model_manager.sig_error.connect(self._on_model_error)

        # UI
        self._build_topbar()
        self._build_stack()

        # señales
        self.sig_predict_many.connect(self._on_predict_many)

    # ---------- UI scaffolding ----------
    def _build_topbar(self):
        top = QWidget()
        lay = QHBoxLayout(top)
        lay.setContentsMargins(12, 8, 12, 8)

        self.lbl_status = QLabel("Listo")

        self.btn_metrics = QPushButton("Métricas")
        self.btn_metrics.clicked.connect(self._open_metrics)
        self.btn_metrics.setEnabled(False)

        self.btn_open = QPushButton("Abrir imágenes…")
        self.btn_open.clicked.connect(self._open_files)

        self.btn_export = QPushButton("Exportar último lote")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_last_batch)

        lay.addWidget(self.lbl_status, 1, alignment=Qt.AlignLeft)
        lay.addWidget(self.btn_metrics, 0, alignment=Qt.AlignRight)
        lay.addWidget(self.btn_open, 0, alignment=Qt.AlignRight)
        lay.addWidget(self.btn_export, 0, alignment=Qt.AlignRight)

        wrapper = QWidget()
        v = QVBoxLayout(wrapper)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(top)

        self.setMenuWidget(wrapper)

    def _build_stack(self):
        self.stack = QStackedWidget()
        self.home = HomeView(self.registry, self.cfg)
        self.batch = BatchView(self.cfg)
        self.metrics = MetricsView(self.registry)
        self.crop = CropView(self.cfg)  # <--- NUEVO

        self.stack.addWidget(self.home)    # index 0
        self.stack.addWidget(self.batch)   # index 1
        self.stack.addWidget(self.metrics) # index 2
        self.stack.addWidget(self.crop)    # index 3  (o en otro orden si prefieres)

        self.setCentralWidget(self.stack)

        # HomeView
        self.home.sig_species_model_changed.connect(self._load_species_model)
        # En vez de predecir directo, vamos al recortador:
        self.home.sig_predict_one.connect(self._open_cropper_single)  # <--- CAMBIO
        self.home.sig_predict_many.connect(self._open_cropper_many)   # <--- CAMBIO

        # BatchView
        self.batch.sig_back.connect(lambda: self.stack.setCurrentWidget(self.home))
        self.batch.sig_run_batch.connect(lambda paths: self.sig_predict_many.emit(paths))
        self.batch.sig_results_ready.connect(lambda: self.btn_export.setEnabled(True)) 

        # MetricsView
        self.metrics.sig_back.connect(lambda: self.stack.setCurrentWidget(self.home))

        # CropView
        self.crop.sig_cancel.connect(lambda: self.stack.setCurrentWidget(self.home))
        self.crop.sig_crops_ready.connect(self._on_crops_ready)  # <--- NUEVO

        
    # ---------- Actions ----------
    @Slot(str, str)
    def _load_species_model(self, species_key: str, model_key: str):
        try:
            sp = self.registry.get_species(species_key)
            me = sp.models[model_key]
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.selected_species_key = species_key
        self.selected_model_key = model_key

        self._set_busy(True, f"Cargando modelo {model_key}…")
        self.model_manager.load_async(model_key, me)

    @Slot(str, object)
    def _on_model_loaded(self, model_key: str, lm: LoadedModel):
        if model_key != (self.selected_model_key or ""):
            return

        try:
            entry = self.registry.get_model(self.selected_species_key or "", self.selected_model_key or "")
        except Exception:
            self._set_busy(False)
            return

        if Path(lm.path).resolve() != Path(entry.path).resolve():
            self.model_manager.load_async(self.selected_model_key or "", entry)
            return

        self.loaded = lm
        self.model_hash = file_sha1(lm.path)

        self.lbl_status.setText(
            f"Especie: {self.selected_species_key} | Modelo: {self.selected_model_key} | Clases: {', '.join(lm.classes)}"
        )
        self.home.set_loaded_model(lm, self.selected_species_key or "", self.selected_model_key or "")
        self.btn_metrics.setEnabled(True)
        self.metrics.set_active(self.selected_species_key or "", self.selected_model_key or "")

        self._set_busy(False)

    @Slot(str, str)
    def _on_model_error(self, model_key: str, err: str):
        if model_key != (self.selected_model_key or ""):
            return
        self._set_busy(False)
        QMessageBox.critical(self, "Error cargando modelo", err)

    def _predict_one_from_home(self, file_path: str):
        if not self.loaded:
            QMessageBox.warning(self, "Sin modelo", "Selecciona especie y modelo primero.")
            return
        self.home.show_busy("Clasificando…")
        try:
            preds = predict_files(self.loaded, self.cfg, [file_path])
        except Exception as e:
            self.home.hide_busy()
            QMessageBox.critical(self, "Error en inferencia", str(e))
            return
        self.home.hide_busy()

        self.home.show_prediction(preds[0])
        append_to_global_csv(
            self.cfg,
            self.selected_species_key or "",
            self.selected_model_key or "",
            self.model_hash,
            preds
        )
        self.btn_export.setEnabled(True)

    def _open_files(self):
        if not self.loaded:
            QMessageBox.information(self, "Selecciona primero", "Elige modelo antes de abrir imágenes.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Selecciona imágenes", str(Path.home()),
            "Imágenes (*.jpg *.jpeg *.png *.bmp)"
        )
        if not files:
            return
        paths = iter_images_in_paths(files)
        # Ir a recortar (1 o varias)
        self.crop.load_images(paths)
        self.stack.setCurrentWidget(self.crop)

    @Slot(list)
    def _on_predict_many(self, paths: list[str]):
        if not self.loaded:
            QMessageBox.warning(self, "Sin modelo", "Selecciona especie y modelo primero.")
            return
        self.stack.setCurrentWidget(self.batch)
        self.batch.run_batch(
            self.loaded,
            self.selected_species_key or "",
            self.selected_model_key or "",
            self.model_hash,
            paths
        )
        if self.batch.has_results():
            self.btn_export.setEnabled(True)

    def _export_last_batch(self):
        if not self.batch.has_results():
            QMessageBox.information(self, "Sin resultados", "Aún no hay lote para exportar.")
            return

        # 1) Carpeta sugerida = Documentos
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) or str(Path.home())

        # 2) Pide al usuario la carpeta de destino
        dest_dir = QFileDialog.getExistingDirectory(
            self,
            "Selecciona la carpeta destino",
            docs
        )
        if not dest_dir:
            return

        try:
            # 3) Exporta directamente a esa carpeta (storage.export_run_csv ahora lo soporta)
            out_path = export_run_csv(
                self.cfg,
                self.selected_species_key or "",
                self.selected_model_key or "",
                self.model_hash,
                self.batch.get_results(),
                dest_dir=dest_dir,  # <- clave
            )
            QMessageBox.information(self, "Exportado", f"Archivo guardado:\n{out_path}")

        except PermissionError as e:
            QMessageBox.critical(self, "Permisos insuficientes",
                                 "No se pudo escribir en la carpeta seleccionada.\n"
                                 "Elige Documentos o Escritorio e intenta de nuevo.\n\n"
                                 f"Detalle: {e}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Carpeta no encontrada",
                                 "La carpeta de destino no existe o fue removida.\n\n"
                                 f"Detalle: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar",
                                 f"No se pudo exportar el CSV:\n{e}")
    def _open_metrics(self):
        if not (self.selected_species_key and self.selected_model_key):
            QMessageBox.information(self, "Sin selección", "Selecciona especie y modelo para ver métricas.")
            return
        self.metrics.set_active(self.selected_species_key, self.selected_model_key)
        self.stack.setCurrentWidget(self.metrics)

    # Helper de “ocupado”
    def _set_busy(self, busy: bool, msg: str = ""):
        if busy:
            self.lbl_status.setText(msg or "Procesando…")
            self.setCursor(Qt.WaitCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            if self.selected_species_key and self.selected_model_key and self.loaded:
                self.lbl_status.setText(
                    f"Especie: {self.selected_species_key} | Modelo: {self.selected_model_key}"
                )
            else:
                self.lbl_status.setText("Listo")
        self.btn_metrics.setEnabled(not busy and bool(self.loaded))
        self.btn_open.setEnabled(not busy)
        self.btn_export.setEnabled(not busy and self.btn_export.isEnabled())
        
    def _open_cropper_single(self, path: str):
        if not self.loaded:
            QMessageBox.warning(self, "Sin modelo", "Selecciona modelo primero.")
            return
        self.crop.load_images([path])
        self.stack.setCurrentWidget(self.crop)

    def _open_cropper_many(self, paths: list[str]):
        if not self.loaded:
            QMessageBox.warning(self, "Sin modelo", "Selecciona modelo primero.")
            return
        self.crop.load_images(paths)
        self.stack.setCurrentWidget(self.crop)

    def _on_crops_ready(self, crop_paths: list[str]):
        # Reutilizamos tu flujo batch sin tocar predictor
        if not self.loaded:
            QMessageBox.warning(self, "Sin modelo", "Selecciona modelo primero.")
            return
        self.stack.setCurrentWidget(self.batch)
        self.batch.run_batch(
            self.loaded,
            self.selected_species_key or "",
            self.selected_model_key or "",
            self.model_hash,
            crop_paths
        )
        if self.batch.has_results():
            self.btn_export.setEnabled(True)

