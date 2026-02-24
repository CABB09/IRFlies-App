# app/tests/test_predictor.py

import os, tempfile
from pathlib import Path
from PIL import Image
import tensorflow as tf

from core.predictor import predict_files, Prediction
from core.model_loader import LoadedModel
from core.config import AppConfig

# Modelo Keras minimal que ignora la imagen y devuelve logits fijos
class DummyModel(tf.keras.Model):
    def __init__(self, num_classes: int):
        super().__init__()
        self.num_classes = num_classes

    def call(self, inputs, training=False):
        # logits: favorece la clase 0 > 1 > 2 ...
        batch = tf.shape(inputs)[0]
        base = tf.range(self.num_classes, 0, -1, dtype=tf.float32)  # [C..1]
        return tf.tile(base[tf.newaxis, :], [batch, 1])

def _tmp_image():
    f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    Image.new("RGB", (224, 224), color=(100, 120, 140)).save(f.name)
    return f.name

def test_predictor_pipeline_with_dummy_model():
    classes = ["-8", "-9"]
    lm = LoadedModel(
        model=DummyModel(num_classes=len(classes)),
        classes=classes,
        class_to_idx={c: i for i, c in enumerate(classes)},
        idx_to_class={i: c for i, c in enumerate(classes)},
        path="dummy.keras",
        classes_path="dummy.json",
    )

    cfg = AppConfig()  # usa defaults del dataclass

    img_path = _tmp_image()
    try:
        preds = predict_files(lm, cfg, [img_path])
        assert isinstance(preds, list) and len(preds) == 1
        p: Prediction = preds[0]
        # Debe elegir la clase índice 0 por cómo definimos los logits
        assert p.top1_class == classes[0]
        assert 0.0 <= p.top1_prob <= 1.0
        assert set(p.full_probs.keys()) == set(classes)
    finally:
        os.remove(img_path)