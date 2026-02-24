"""
storage.py — Persistencia de resultados: CSV acumulado y export por corrida.
"""

from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from .config import AppConfig
from .predictor import Prediction


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- Helpers de ruta segura ----------

def _safe_runs_dir(runs_dir: str) -> Path:
    """
    Normaliza runs_dir para que sea absoluta y escribible por el usuario.
    - Expande ~
    - Si es relativa, la reubica bajo HOME/Documents/IRFLies (o HOME/.irflies si no hay Documents)
    """
    p = Path(runs_dir).expanduser()
    if not p.is_absolute():
        docs = Path.home() / "Documents"
        base = docs if docs.exists() else Path.home() / ".irflies"
        p = (base / "IRFLies" / runs_dir).resolve()
    return p


def ensure_runs_dirs(cfg: AppConfig) -> None:
    base = _safe_runs_dir(cfg.runs_dir)
    (base / "logs").mkdir(parents=True, exist_ok=True)
    (base / "exports").mkdir(parents=True, exist_ok=True)


# ---------- Escritura de CSV global acumulado ----------

def append_to_global_csv(
    cfg: AppConfig,
    species: str,
    model_key: str,
    model_hash: str,
    preds: Iterable[Prediction],
) -> None:
    ensure_runs_dirs(cfg)
    base = _safe_runs_dir(cfg.runs_dir)
    path = base / "predictions.csv"
    new_file = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow([
                "timestamp", "species", "model_key", "model_hash",
                "file", "top1_class", "top1_prob", "top2_class", "top2_prob", "gap_pp",
                "confidence", "full_probs_json"
            ])
        for p in preds:
            full_json = ";".join(f"{k}:{v:.6f}" for k, v in p.full_probs.items())
            w.writerow([
                _timestamp(), species, model_key, model_hash,
                p.file, p.top1_class, f"{p.top1_prob:.6f}",
                p.top2_class or "", f"{(p.top2_prob or 0.0):.6f}",
                f"{p.gap_pp:.6f}", p.confidence, full_json
            ])


# ---------- Exportación por corrida (a carpeta elegida por el usuario) ----------

def export_run_csv(
    cfg: AppConfig,
    species: str,
    model_key: str,
    model_hash: str,
    preds: Iterable[Prediction],
    dest_dir: Optional[str] = None,  # <- NUEVO: carpeta de destino opcional
) -> str:
    """
    Exporta un CSV con los resultados de una corrida.
    - Si dest_dir es None, exporta en <runs_dir>/exports/.
    - Si dest_dir tiene valor, exporta ahí directamente (crea la carpeta si hace falta).

    Devuelve la ruta absoluta del archivo creado.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if dest_dir:
        base = Path(dest_dir).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
    else:
        ensure_runs_dirs(cfg)
        base = _safe_runs_dir(cfg.runs_dir) / "exports"

    path = base / f"{species}_{model_key}_{ts}.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "timestamp", "species", "model_key", "model_hash",
            "file", "top1_class", "top1_prob", "top2_class", "top2_prob", "gap_pp",
            "confidence", "full_probs_json"
        ])
        for p in preds:
            full_json = ";".join(f"{k}:{v:.6f}" for k, v in p.full_probs.items())
            w.writerow([
                _timestamp(), species, model_key, model_hash,
                p.file, p.top1_class, f"{p.top1_prob:.6f}",
                p.top2_class or "", f"{(p.top2_prob or 0.0):.6f}",
                f"{p.gap_pp:.6f}", p.confidence, full_json
            ])

    return str(path.resolve())