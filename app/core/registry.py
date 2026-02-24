"""
registry.py — Carga el catálogo de especies y modelos desde registry.yaml.
Soporta ejecución 'dev' y 'frozen' (PyInstaller).
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import sys
import yaml

def _bases_to_search() -> list[Path]:
    bases: list[Path] = []

    # 1) Carpeta del ejecutable (ONEDIR): dist\IRFLies-App\
    if getattr(sys, "frozen", False):
        bases.append(Path(sys.executable).parent)

    # 2) Carpeta temporal descomprimida (ONEFILE)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bases.append(Path(meipass))

    # 3) CWD (por si tu lanzador cambia el directorio de trabajo)
    try:
        bases.append(Path.cwd())
    except Exception:
        pass

    # 4) Raíz del repo en dev (…/app/core/ -> subir 2 niveles)
    bases.append(Path(__file__).resolve().parents[2])

    return bases

def default_registry_path() -> Path:
    """
    Busca en cada base:
      base/registry.yaml
      base/app/config/registry.yaml
    """
    preferred = None
    for base in _bases_to_search():
        cand1 = base / "registry.yaml"
        cand2 = base / "app" / "config" / "registry.yaml"
        if preferred is None:
            preferred = cand1
        if cand1.is_file():
            return cand1
        if cand2.is_file():
            return cand2
    # Para el mensaje de error
    return preferred if preferred else Path("registry.yaml")


@dataclass(frozen=True)
class ModelEntry:
    key: str
    name: str
    path: str
    classes_path: str
    description: str | None = None


@dataclass(frozen=True)
class SpeciesEntry:
    key: str
    display_name: str
    models: Dict[str, ModelEntry]


class Registry:
    def __init__(self, yaml_path: str | Path | None = None):
        # Si no te pasan ruta, usa el detector anterior
        self.yaml_path = Path(yaml_path) if yaml_path else default_registry_path()
        self._species: Dict[str, SpeciesEntry] = {}
        self._load()

    def _load(self) -> None:
        path = self.yaml_path
        if not path.is_file():
            raise FileNotFoundError(f"No se encontró registry.yaml en: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        species_data = data.get("species", {})
        if not isinstance(species_data, dict) or not species_data:
            raise ValueError("registry.yaml: campo 'species' vacío o inválido")

        # 👇 Base para resolver rutas RELATIVAS dentro del YAML
        base_for_rel = path.parent

        result: Dict[str, SpeciesEntry] = {}
        for skey, sval in species_data.items():
            disp = sval.get("display_name", skey)
            models = sval.get("models", {})
            if not models:
                raise ValueError(f"registry.yaml: especie '{skey}' no define 'models'")

            model_entries: Dict[str, ModelEntry] = {}
            for mkey, mval in models.items():
                # Rutas seguras: si vienen absolutas, se respetan; si son relativas, se resuelven contra el YAML
                m_path = Path(mval["path"])
                c_path = Path(mval["classes"])
                if not m_path.is_absolute():
                    m_path = (base_for_rel / m_path)
                if not c_path.is_absolute():
                    c_path = (base_for_rel / c_path)

                model_entries[mkey] = ModelEntry(
                    key=mkey,
                    name=mval.get("name", mkey),
                    path=str(m_path),            # 👈 NO forzamos .resolve() para no “encementar” tu PC
                    classes_path=str(c_path),
                    description=mval.get("description"),
                )

            result[skey] = SpeciesEntry(key=skey, display_name=disp, models=model_entries)

        self._species = result

    # ===== API pública =====
    @property
    def species_keys(self) -> List[str]:
        return list(self._species.keys())

    def get_species(self, key: str) -> SpeciesEntry:
        if key not in self._species:
            raise KeyError(f"Especie no registrada: {key}")
        return self._species[key]

    def get_model(self, species_key: str, model_key: str) -> ModelEntry:
        sp = self.get_species(species_key)
        if model_key not in sp.models:
            raise KeyError(f"Modelo '{model_key}' no existe para especie '{species_key}'")
        return sp.models[model_key]