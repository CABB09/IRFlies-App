"""
calibrator.py — Calibración de probabilidades (temperature scaling).
Útil si quieres que los % se acerquen a frecuencias reales.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional
from scipy.optimize import minimize  # scikit-learn trae scipy por dependencia, ok.


@dataclass
class TemperatureScaler:
    T: float = 1.0  # temperatura (>= 0.05 por estabilidad)

    def fit(self, logits: np.ndarray, y_true: np.ndarray) -> "TemperatureScaler":
        """
        Ajusta T para minimizar NLL en un conjunto de validación externo.
        logits: [N,C] salidas no normalizadas del modelo
        y_true: [N] índices verdaderos
        """
        def nll(temp: float) -> float:
            t = max(0.05, float(temp))
            z = logits / t
            z = z - z.max(axis=1, keepdims=True)
            ex = np.exp(z)
            p = ex / ex.sum(axis=1, keepdims=True)
            # -log(p[y])
            n = np.arange(len(y_true))
            loss = -np.log(p[n, y_true] + 1e-12).mean()
            return float(loss)

        res = minimize(lambda v: nll(v[0]), x0=[1.0], bounds=[(0.05, 10.0)], method="L-BFGS-B")
        self.T = float(res.x[0]) if res.success else 1.0
        return self

    def transform_logits(self, logits: np.ndarray) -> np.ndarray:
        t = max(0.05, float(self.T))
        return logits / t

    def transform_probs(self, probs: np.ndarray) -> np.ndarray:
        # Si sólo tienes probs, puedes aproximar aplicando logit y re-softmax (no exacto).
        # Recomendado: calibrar siempre sobre logits.
        z = np.log(np.clip(probs, 1e-12, 1.0))
        z = self.transform_logits(z)
        z = z - z.max(axis=1, keepdims=True)
        ex = np.exp(z)
        return ex / ex.sum(axis=1, keepdims=True)