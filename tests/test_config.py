from pathlib import Path
import json
from core.config import load_app_config, save_app_config

def test_load_save_config():
    # Carga configuración real del proyecto
    cfg = load_app_config()
    cfg_path = Path(cfg.config_dir) / "app_config.json"

    # Guarda el contenido original para restaurar al final
    original_text = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else None

    try:
        # Cambia un valor y persiste
        cfg.theme = "dark"
        save_app_config(cfg)

        # Recarga y verifica
        cfg2 = load_app_config()
        assert cfg2.theme == "dark"
        assert Path(cfg2.runs_dir).is_absolute()
        assert Path(cfg2.models_dir).is_absolute()
    finally:
        # Restaurar archivo original
        if original_text is None:
            if cfg_path.exists():
                cfg_path.unlink()
        else:
            cfg_path.write_text(original_text, encoding="utf-8")