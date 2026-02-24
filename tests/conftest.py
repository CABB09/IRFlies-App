# Hace que "from core import ..." funcione dentro de tests
import sys, os
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # .../app
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)