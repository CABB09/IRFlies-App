# app/main.py
from __future__ import annotations
import sys
from pathlib import Path

# --- bootstrap imports para "from core ..." y "from ui ..."
APP_ROOT = Path(__file__).resolve().parent  # .../app
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon, QGuiApplication
from PySide6.QtCore import Qt

from core.config import load_app_config
from core.tf_session import init_tf_session
from core.registry import Registry
from ui.main_window import MainWindow


def base_dir() -> Path:
    """Raíz del bundle si está congelado; en dev, raíz del repo."""
    if getattr(sys, "frozen", False):
        # ONEDIR: carpeta del .exe | ONEFILE: también apunta al dir del ejecutable wrapper
        return Path(sys.executable).parent
    # Dev: .../app -> sube 1 nivel al repo
    return APP_ROOT.parent


def find_registry_yaml() -> Path:
    """Busca registry.yaml junto al .exe y en app/config/."""
    b = base_dir()
    candidates = [
        b / "registry.yaml",
        b / "app" / "config" / "registry.yaml",
    ]
    for c in candidates:
        if c.is_file():
            return c
    # Si no aparece, regresa el primero para el mensaje de error
    return candidates[0]


def main():
    # High-DPI moderno (evita el zoom raro sin warnings deprecados)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 1) Cargar configuración
    cfg = load_app_config()

    # 2) Inicializar TensorFlow (mem growth, warmup, hilos...)
    init_tf_session(cfg)

    # 3) Lanzar la app Qt
    app = QApplication(sys.argv)

    # Icono global (opcional)
    icon_path = APP_ROOT / "assets" / "icons" / "app_icon.png"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 4) Cargar Registry con ruta explícita (junto al .exe o app/config/)
    try:
        yaml_path = find_registry_yaml()
        registry = Registry(yaml_path)
    except Exception as e:
        QMessageBox.critical(None, "IRFLies-App", f"Error cargando registry:\n{e}")
        return 1

    # 5) Ventana principal
    # Si tu MainWindow no acepta el parámetro, cambia a: win = MainWindow()
    win = MainWindow(registry)
    win.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
    
    
# cd /d D:\IRFLies-App
# python -m venv .venv
# .\.venv\Scripts\activate
# pip install -r requirements.txt
# python -m app.main