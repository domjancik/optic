import numpy as np

from spectral import preview_rgb_weights, spectrum_preset


def test_red_and_blue_wavelengths_have_distinct_preview_dominants():
    colors = preview_rgb_weights([450, 650])
    assert colors.shape == (2, 3)
    assert colors[0, 2] > colors[0, 0]
    assert colors[1, 0] > colors[1, 2]
    assert np.all(colors >= 0)


def test_narrow_laser_presets_are_single_positive_spectral_samples():
    wavelengths, weights = spectrum_preset("laser-532")
    assert wavelengths == [532.0]
    assert weights == [1.0]


def test_warm_and_neutral_white_are_positive_normalized_multispectral_previews():
    for name in ("warm-white", "neutral-white", "rgb-white"):
        wavelengths, weights = spectrum_preset(name, channels=9)
        assert len(wavelengths) > 1
        assert len(wavelengths) == len(weights)
        assert all(weight > 0 for weight in weights)
        assert np.isclose(sum(weights), 1.0)
