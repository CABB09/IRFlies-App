"""
utils.py — utilidades varias sin dependencias de UI.
"""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Iterable


IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".JPG", ".JPEG", ".PNG", ".BMP")


def is_image(path: str) -> bool:
    return Path(path).suffix in IMG_EXTS


def iter_images_in_paths(paths: Iterable[str]) -> list[str]:
    """
    Accepta archivos sueltos o carpetas y devuelve una lista plana de imágenes válidas.
    """
    out: list[str] = []
    for p in map(Path, paths):
        if p.is_file() and is_image(str(p)):
            out.append(str(p.resolve()))
        elif p.is_dir():
            for sub in p.rglob("*"):
                if sub.is_file() and is_image(str(sub)):
                    out.append(str(sub.resolve()))
    # único, orden estable
    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def file_sha1(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()[:10]