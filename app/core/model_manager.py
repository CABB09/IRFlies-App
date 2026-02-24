# app/core/model_manager.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QThreadPool

from .registry import ModelEntry
from . import model_loader
from core.config import load_app_config


@dataclass
class CachedModel:
    loaded: model_loader.LoadedModel


class _LoadTask(QRunnable):
    def __init__(self, entry: ModelEntry, on_ok: Callable[[model_loader.LoadedModel], None],
                 on_err: Callable[[str], None], do_warmup: bool, warmup_size: int):
        super().__init__()
        self.entry = entry
        self.on_ok = on_ok
        self.on_err = on_err
        self.do_warmup = do_warmup
        self.warmup_size = warmup_size

    @Slot()
    def run(self):
        try:
            lm = model_loader.load_keras_model(self.entry.path, self.entry.classes_path)
            if self.do_warmup:
                import tensorflow as tf
                dummy = tf.zeros((1, self.warmup_size, self.warmup_size, 3), dtype=tf.float32)
                _ = lm.model(dummy, training=False)
            self.on_ok(lm)
        except Exception as e:
            self.on_err(str(e))


class ModelManager(QObject):
    # mantenemos la señal con model_key para no romper MainWindow
    sig_loaded = Signal(str, object)   # model_key, LoadedModel
    sig_error  = Signal(str, str)      # model_key, error

    def __init__(self):
        super().__init__()
        # cache por ruta absoluta del .keras
        self._cache: Dict[str, CachedModel] = {}
        self._pool = QThreadPool.globalInstance()
        self._cfg = load_app_config()

    def _cache_key_for(self, entry: ModelEntry) -> str:
        return str(Path(entry.path).resolve())

    def get_cached(self, entry: ModelEntry) -> Optional[model_loader.LoadedModel]:
        key = self._cache_key_for(entry)
        c = self._cache.get(key)
        return c.loaded if c else None

    def load_async(self, model_key: str, entry: ModelEntry):
        # usa caché por ruta: si la ruta es la misma, reutiliza; si es distinta, recarga
        cached = self.get_cached(entry)
        if cached is not None:
            self.sig_loaded.emit(model_key, cached)
            return

        def _ok(lm: model_loader.LoadedModel):
            key = self._cache_key_for(entry)
            self._cache[key] = CachedModel(loaded=lm)
            self.sig_loaded.emit(model_key, lm)

        def _err(msg: str):
            self.sig_error.emit(model_key, msg)

        task = _LoadTask(
            entry=entry,
            on_ok=_ok,
            on_err=_err,
            do_warmup=bool(self._cfg.tf_warmup_on_start),
            warmup_size=int(self._cfg.image_size),
        )
        self._pool.start(task)