from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.utils.hooks import collect_submodules

# ---- Rutas base
ROOT = Path.cwd()
APP_MAIN = str(ROOT / "app" / "main.py")
APP_NAME = "IRFLies-App"

# ---- Datos a incluir (usar pares (src, dest); si src es carpeta, copia recursiva)
datas = []
for folder in ["app/assets", "app/config", "app/models", "app/runs_app"]:
    src = ROOT / folder
    if src.exists():
        # (source_path, dest_folder_inside_app)
        datas.append((str(src), folder))

reg_yaml = ROOT / "app" / "config" / "registry.yaml"
if reg_yaml.exists():
    datas.append((str(reg_yaml), "."))

# ---- Hidden imports (por si PyInstaller no detecta algo)
hiddenimports = []
hiddenimports += collect_submodules("tensorflow")
hiddenimports += collect_submodules("keras")

# ---- Icono del EXE (.ico)
icon_path = ROOT / "app" / "assets" / "icons" / "app_icon.ico"
icon_arg = str(icon_path) if icon_path.exists() else None

block_cipher = None

a = Analysis(
    [APP_MAIN],
    pathex=[str(ROOT), str(ROOT / "app")],
    binaries=[],
    datas=datas,                 # << lista de (src, dest)
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=["tests", "app/tests"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=APP_NAME,
    icon=icon_arg,
    debug=False,
    strip=False,
    upx=False,
    console=False,  # sin consola
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=APP_NAME,
)

# packaging/pyinstaller.spec
# Ejecuta:
#   (.venv) PS D:\IRFLies-App> python -m PyInstaller -y packaging\pyinstaller.spec
