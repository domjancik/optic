import unittest
import numpy as np
import engine

class RidgeLaserTests(unittest.TestCase):
    def test_gaussian_laser_waist_and_divergence(self):
        c=engine.defaults();c.update(source_model='laser',rays=100000,source_radius_mm=2,divergence_deg=.1)
        r=engine.source_rays(c)
        self.assertAlmostEqual(np.std(r[:,0]),1,delta=.015)
        self.assertGreater(np.mean(np.hypot(r[:,0],r[:,1])>2),.12)
        self.assertAlmostEqual(np.std(r[:,3]/r[:,5]),np.tan(np.deg2rad(.1/2))/2,delta=1e-5)
        self.assertAlmostEqual(r[:,7].sum(),c['optical_power_w'])
    def test_laser_diffraction_limit_rejected(self):
        c=engine.defaults();c.update(source_model='laser',divergence_deg=0)
        with self.assertRaisesRegex(ValueError,'diffraction'):engine.validate(c)
    def test_cylindrical_ridges_have_constant_y_profile(self):
        c=engine.defaults();o=c['optics'][0];o.update(kind='cylindrical',depth_mm=.01)
        engine.validate(c)
        mesh=engine.optic_mesh(o);v=mesh.reshape(-1,3);v=v[v[:,2]>o['z_mm']+.1]
        x=v[:,0];a=o['pitch_mm']/2;h=o['depth_mm'];radius=(a*a+h*h)/(2*h);phase=(x+ a)%(2*a)-a
        expected=o['z_mm']+o['thickness_mm']+np.sqrt(radius*radius-phase*phase)-(radius-h)
        np.testing.assert_allclose(v[:,2],expected,atol=1e-9)

if __name__=='__main__':unittest.main()
