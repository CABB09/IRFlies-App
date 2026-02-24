from PIL import Image
import numpy as np
import tempfile, os

from core.preprocessor import load_and_preprocess

def test_preprocess_image():
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)  # importantísimo en Windows

    try:
        Image.new("RGB", (300, 300), color=(128, 128, 128)).save(path)
        arr = load_and_preprocess(path, image_size=224)

        assert isinstance(arr, np.ndarray)
        assert arr.shape == (224, 224, 3)
        assert arr.dtype == np.float32
        # Implementación actual: valores en 0..255 (pre-normalización)
        assert arr.min() >= 0.0 and arr.max() <= 255.0
    finally:
        if os.path.exists(path):
            os.remove(path)
from PIL import Image
import numpy as np
import tempfile, os

from core.preprocessor import load_and_preprocess

def test_preprocess_image():
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)  # importantísimo en Windows

    try:
        Image.new("RGB", (300, 300), color=(128, 128, 128)).save(path)
        arr = load_and_preprocess(path, image_size=224)

        assert isinstance(arr, np.ndarray)
        assert arr.shape == (224, 224, 3)
        assert arr.dtype == np.float32
        # Implementación actual: valores en 0..255 (pre-normalización)
        assert arr.min() >= 0.0 and arr.max() <= 255.0
    finally:
        if os.path.exists(path):
            os.remove(path)