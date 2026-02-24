from pathlib import Path
import textwrap, tempfile

from core.registry import Registry

MINIMAL_REGISTRY = textwrap.dedent("""
species:
  Ludens:
    display_name: "Anastrepha ludens"
    models:
      final:
        name: "final"
        path: "D:/dummy/final_model.keras"
        classes: "D:/dummy/classes.json"
  Ceratitis:
    display_name: "Ceratitis capitata"
    models:
      final:
        name: "final"
        path: "D:/dummy/final_model.keras"
        classes: "D:/dummy/classes.json"
""").strip()

def test_registry_load_minimal():
    with tempfile.TemporaryDirectory() as td:
        reg_path = Path(td) / "registry.yaml"
        reg_path.write_text(MINIMAL_REGISTRY, encoding="utf-8")

        reg = Registry(str(reg_path))
        keys = set(reg.species_keys)
        assert {"Ludens", "Ceratitis"}.issubset(keys)
        assert "final" in reg.get_species("Ludens").models
        assert "final" in reg.get_species("Ceratitis").models