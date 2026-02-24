from __future__ import annotations
from pathlib import Path
import hashlib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST_CER = ROOT / "app" / "models" / "ceratitis"
DEST_EYES = ROOT / "app" / "models"

# Cambia el TAG y los SHA256 por los reales
TAG = "models-v1"
ASSETS = [
    {
        "dest": DEST_CER / "refit_model.keras",
        "url": f"https://github.com/CABB09/IRFlies-App/releases/download/{TAG}/refit_model.keras",
        "sha256": "PON_AQUI_SHA256",
    },
    {
        "dest": DEST_CER / "finetune_short.keras",
        "url": f"https://github.com/CABB09/IRFlies-App/releases/download/{TAG}/finetune_short.keras",
        "sha256": "PON_AQUI_SHA256",
    },
    {
        "dest": DEST_EYES / "eyes_yolov8n_best.pt",
        "url": f"https://github.com/CABB09/IRFlies-App/releases/download/{TAG}/eyes_yolov8n_best.pt",
        "sha256": "PON_AQUI_SHA256",
    },
]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(dest)

def main():
    for a in ASSETS:
        dest = a["dest"]
        url = a["url"]
        expected = a["sha256"]

        if dest.exists() and expected != "PON_AQUI_SHA256":
            if sha256_file(dest) == expected:
                print(f"[OK] {dest}")
                continue
            else:
                print(f"[WARN] SHA256 distinto, re-descargando: {dest}")
                dest.unlink()

        if not dest.exists():
            print(f"[DL] {url} -> {dest}")
            download(url, dest)

        if expected != "PON_AQUI_SHA256":
            got = sha256_file(dest)
            if got != expected:
                raise RuntimeError(f"SHA256 no coincide en {dest}\nEsperado: {expected}\nObtenido: {got}")

    print("Listo. Modelos colocados en app/models/...")

if __name__ == "__main__":
    main()