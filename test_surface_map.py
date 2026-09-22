import unittest
import numpy as np
import engine

class SurfaceMapTests(unittest.TestCase):
    def test_prism_height_matches_actual_profile(self):
        from surface_map import surface_map
        o=engine.defaults()['optics'][0]
        result=surface_map(o,resolution=65)
        h=np.array(result['profile_mm'],dtype=float)
        x=np.linspace(-o['radius_mm'],o['radius_mm'],65)
        phase=(x/o['pitch_mm']+.5)%1-.5
        expected=o['thickness_mm']+o['depth_mm']*(1-2*np.abs(phase))
        np.testing.assert_allclose(h[1:-1],expected[1:-1],atol=1e-8)
        self.assertIsNone(result['heights_mm'][0])
    def test_local_map_ignores_world_pose(self):
        from surface_map import surface_map
        o=engine.defaults()['optics'][0];a=surface_map(o)
        o.update(z_mm=40,angle_deg=47,tilt_deg=8)
        self.assertEqual(a,surface_map(o))
    def test_flat_map(self):
        from surface_map import surface_map
        o=engine.defaults()['optics'][0];o['kind']='flat'
        r=surface_map(o)
        self.assertAlmostEqual(r['min_mm'],o['thickness_mm'])
        self.assertAlmostEqual(r['max_mm'],o['thickness_mm'])
if __name__=='__main__':unittest.main()
