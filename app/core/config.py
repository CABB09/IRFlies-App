"""
config.py — Carga y valida la configuración de la aplicación.

Prioridad de carga (de menor a mayor):
  1) DEFAULTS (abajo)
  2) config/app_config.json (si existe)
  3) Variables de entorno (prefijo IRFL_)
"""

from __future__ import annotations
import json, os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict


APP_ROOT = Path(__file__).resolve().parents[1]   # .../app
PROJECT_ROOT = APP_ROOT.parent                   # raíz del repo


@dataclass
class AppConfig:
    # Rutas
    registry_path: str = str(PROJECT_ROOT / "registry.yaml")
    runs_dir: str = str(APP_ROOT / "runs_app")
    models_dir: str = str(APP_ROOT / "models")
    assets_dir: str = str(APP_ROOT / "assets")
    config_dir: str = str(APP_ROOT / "config")

    # Inferencia
    image_size: int = 224
    confidence_threshold: float = 0.60
    top2_margin_pp: float = 0.05  # margen en puntos porcentuales (0.05 = 5pp)
    batch_size: int = 16

    # TensorFlow
    tf_allow_memory_growth: bool = True
    tf_warmup_on_start: bool = True
    tf_num_threads: int | None = None  # None = auto

    # Exportación
    export_full_prob_vector: bool = True  # guardar vector de probabilidades por imagen

    # UI (opcional)
    theme: str = "auto"  # "auto" | "light" | "dark"


def _merge_dict(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(dst)
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _load_json_if_exists(path: Path) -> Dict[str, Any]:
    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _env_overrides() -> Dict[str, Any]:
    """Lee variables de entorno que empiecen con IRFL_ y hagan match con campos del dataclass."""
    prefix = "IRFL_"
    out: Dict[str, Any] = {}
    for field in AppConfig.__dataclass_fields__.keys():  # type: ignore[attr-defined]
        env_name = prefix + field.upper()
        if env_name in os.environ:
            raw = os.environ[env_name]
            # intento de casting sencillo
            if raw.lower() in {"true", "false"}:
                out[field] = raw.lower() == "true"
            else:
                try:
                    if "." in raw:
                        out[field] = float(raw)
                    else:
                        out[field] = int(raw)
                except ValueError:
                    out[field] = raw
    return out


def load_app_config() -> AppConfig:
    defaults = asdict(AppConfig())

    cfg_dir = Path(defaults["config_dir"])
    cfg_dir.mkdir(parents=True, exist_ok=True)
    json_path = cfg_dir / "app_config.json"

    merged = defaults
    merged = _merge_dict(merged, _load_json_if_exists(json_path))
    merged = _merge_dict(merged, _env_overrides())

    # normalización de rutas
    for key in ("runs_dir", "models_dir", "assets_dir", "config_dir"):
        merged[key] = str(Path(merged[key]).resolve())

    # crea carpetas clave
    Path(merged["runs_dir"]).mkdir(parents=True, exist_ok=True)

    return AppConfig(**merged)


def save_app_config(cfg: AppConfig) -> None:
    path = Path(cfg.config_dir) / "app_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)