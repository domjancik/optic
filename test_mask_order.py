import unittest

import numpy as np

import engine


def dot(z_mm, radius_mm, x_mm=0.0, y_mm=0.0):
    return dict(kind='dot', z_mm=z_mm, radius_mm=radius_mm, pitch_mm=1., count=1,
                angle_deg=0., x_mm=x_mm, y_mm=y_mm)


class MaskOrderTests(unittest.TestCase):
    def config(self):
        cfg = engine.defaults()
        cfg.update(rays=100, divergence_deg=0., source_radius_mm=1., resolution=32,
                   detector_size_mm=100., optics=[])
        return cfg

    def test_mask_list_preserves_legacy_single_mask_result(self):
        cfg = self.config()
        legacy = dot(5., 1.)
        cfg['mask'] = legacy
        old = engine.simulate(cfg, 'cpu')
        cfg['masks'] = [legacy]
        new = engine.simulate(cfg, 'cpu')
        np.testing.assert_array_equal(old['irradiance'], new['irradiance'])
        self.assertEqual(old['metrics']['fractions'], new['metrics']['fractions'])

    def test_mask_plane_uses_ray_position_before_and_after_slab(self):
        cfg = self.config()
        # Keep Fresnel reflection negligible so this test isolates slab refraction.
        cfg.update(seed=1, n550=1.01)
        cfg['optics'] = [dict(kind='flat', radius_mm=13., z_mm=10., thickness_mm=2.,
                              pitch_mm=2., depth_mm=0., angle_deg=0., tilt_deg=0.)]
        direction = np.array([.3, 0., np.sqrt(.91)])
        source = np.array([[0., 0., 0., *direction, 550., 1.]])
        x_before = 5. * direction[0] / direction[2]
        cfg['masks'] = [dot(5., .05, x_before)]
        before = engine.simulate(cfg, 'cpu', source=source)
        self.assertEqual(before['metrics']['fractions']['masked'], 0.)
        cfg['masks'] = [dot(15., .05, x_before)]
        after = engine.simulate(cfg, 'cpu', source=source)
        self.assertEqual(after['metrics']['fractions']['masked'], 1.)

    def test_reflected_ray_is_masked_when_crossing_plane_backward(self):
        cfg = self.config()
        cfg.update(seed=30, max_bounces=3)
        cfg['optics'] = [dict(kind='flat', radius_mm=13., z_mm=10., thickness_mm=2.,
                              pitch_mm=2., depth_mm=0., angle_deg=0., tilt_deg=0.)]
        # The aperture is deliberately away from the returning ray, so a crossing
        # must be reported as masked rather than allowed through the opening.
        cfg['masks'] = [dot(5., 1., x_mm=3.)]
        source = np.array([[0., 0., 0., 0., 0., 1., 550., 1.]])
        result = engine.simulate(cfg, 'cpu', source=source)
        self.assertEqual(result['metrics']['fractions']['masked'], 1.)
        self.assertEqual(sum(result['metrics']['fractions'].values()), 1.)


if __name__ == '__main__':
    unittest.main()
