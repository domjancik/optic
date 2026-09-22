"""Approximate spectral presets and display-only wavelength colors.

These helpers do not calibrate a source, sensor, or standard observer.  The
returned RGB values are convenient linear preview contributions for a rendered
display; the ray tracer must retain the supplied spectral weights separately
when calculating optical power.
"""

from __future__ import annotations

from collections.abc import Iterable
import math

import numpy as np


def preview_rgb_weights(wavelengths: Iterable[float]) -> np.ndarray:
    """Return non-negative, per-wavelength approximate linear display RGB.

    This is an intentionally simple smooth wavelength-to-RGB appearance curve,
    normalized per sample. It is not a CIE color matching function and must not
    be used to split physical power or describe a measured light source.
    """
    wave = np.asarray(list(wavelengths), dtype=float).reshape(-1)
    red = np.exp(-0.5 * ((wave - 610.0) / 54.0) ** 2) + 0.22 * np.exp(-0.5 * ((wave - 700.0) / 38.0) ** 2)
    green = np.exp(-0.5 * ((wave - 545.0) / 38.0) ** 2)
    blue = np.exp(-0.5 * ((wave - 450.0) / 31.0) ** 2) + 0.18 * np.exp(-0.5 * ((wave - 495.0) / 28.0) ** 2)
    rgb = np.clip(np.column_stack((red, green, blue)), 0.0, None)
    peak = np.maximum(rgb.max(axis=1, keepdims=True), 1e-12)
    return rgb / peak


def _normalise(weights: np.ndarray) -> list[float]:
    weights = np.clip(weights.astype(float), 0.0, None)
    total = weights.sum()
    if total <= 0:
        weights = np.ones_like(weights)
        total = weights.sum()
    return (weights / total).tolist()


def _blackbody_relative(wavelengths_nm: np.ndarray, kelvin: float) -> np.ndarray:
    """Planck-shaped relative samples, only for an unmeasured white preview."""
    wavelength_m = wavelengths_nm * 1e-9
    c2 = 1.438776877e-2  # second radiation constant, metres kelvin
    exponent = np.clip(c2 / (wavelength_m * kelvin), 1e-8, 700.0)
    return wavelength_m ** -5 / np.expm1(exponent)


def spectrum_preset(name: str, channels: int | None = None) -> tuple[list[float], list[float]]:
    """Return engine-ready wavelengths (nm) and normalized positive weights.

    ``warm-white`` and ``neutral-white`` are broad Planck-shaped stand-ins,
    deliberately labelled approximate rather than measured LED spectra.
    ``channels`` controls their sample count; narrow presets always retain one
    sample so a named laser stays spectrally narrow.
    """
    key = name.strip().lower().replace("_", "-").replace(" ", "-")
    narrow = {
        "laser-450": 450.0,
        "laser-520": 520.0,
        "laser-532": 532.0,
        "laser-638": 638.0,
        "laser-650": 650.0,
        "blue-laser": 450.0,
        "green-laser": 532.0,
        "red-laser": 638.0,
    }
    if key in narrow:
        return [narrow[key]], [1.0]
    if key == "rgb-white":
        return [450.0, 532.0, 638.0], [1 / 3, 1 / 3, 1 / 3]
    if key not in {"warm-white", "neutral-white"}:
        raise ValueError(f"Unknown spectrum preset: {name!r}")

    count = int(channels or 9)
    if count < 3:
        raise ValueError("Broad white presets require at least three channels")
    wavelengths = np.linspace(400.0, 700.0, count)
    kelvin = 2700.0 if key == "warm-white" else 4000.0
    weights = _normalise(_blackbody_relative(wavelengths, kelvin))
    return wavelengths.tolist(), weights
