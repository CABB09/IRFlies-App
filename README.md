# IRFLies-App 🪰

Aplicación de escritorio (PySide6 + TensorFlow) para **clasificar la edad de moscas** de dos especies:
- *Anastrepha ludens*
- *Ceratitis capitata*

## Estructura general
La app está organizada en módulos:
- `core/` → lógica interna (config, carga de modelo, predictor, etc.)
- `ui/` → interfaz PySide6
- `models/` → modelos `.keras` y `classes.json` por especie
- `runs_app/` → bitácoras y exportaciones
- `config/` → parámetros y ajustes globales

## Requisitos
- Python 3.11
- Dependencias listadas en `requirements.txt`

## Ejecución
```bash
cd D:\IRFLies-App
.\.venv\Scripts\activate

python scripts/download_models.py

python -m app.main
