import unittest
import numpy as np
import engine


def mask(z, radius=5, x=0):
    return dict(kind='dot', z_mm=z, radius_mm=radius, pitch_mm=4, count=1,
                angle_deg=0, x_mm=x, y_mm=0)


class LayerTransportTests(unittest.TestCase):
    def config(self):
        c=engine.defaults()
        c.update(rays=20000,optics=[],divergence_deg=0,source_radius_mm=10,resolution=64)
        return c

    def test_multiple_masks_intersect_apertures(self):
        c=self.config();c['masks']=[mask(5,5),mask(8,2)]
        r=engine.simulate(c,'cpu')
        self.assertAlmostEqual(r['metrics']['detected_fraction'],.04,delta=.005)
        self.assertAlmostEqual(sum(r['metrics']['fractions'].values()),1.)
        gpu=engine.simulate(c,'cuda')
        np.testing.assert_allclose(r['irradiance'],gpu['irradiance'],atol=1e-5)

    def test_disjoint_masks_block_every_ray(self):
        c=self.config();c['masks']=[mask(5,1,-3),mask(8,1,3)]
        r=engine.simulate(c,'cpu')
        self.assertEqual(r['metrics']['detected_fraction'],0)
        self.assertAlmostEqual(r['metrics']['fractions']['masked'],1)

    def test_list_order_is_not_optical_order(self):
        c=self.config();c['masks']=[mask(5,5),mask(8,2)]
        a=engine.simulate(c,'cpu')['irradiance'];c['masks'].reverse()
        np.testing.assert_array_equal(a,engine.simulate(c,'cpu')['irradiance'])

    def test_validation_checks_all_masks(self):
        c=engine.defaults();c['masks']=[mask(5),mask(11)]
        with self.assertRaisesRegex(ValueError,'Mask intersects'):engine.validate(c)

    def test_coincident_masks_rejected(self):
        c=self.config();c['masks']=[mask(5),mask(5)]
        with self.assertRaisesRegex(ValueError,'Mask planes'):engine.validate(c)

if __name__=='__main__':unittest.main()
