import unittest
import numpy as np
import engine

class ColorTransportTests(unittest.TestCase):
    def test_color_preview_keeps_physical_map_and_tints_red(self):
        cfg=engine.defaults();cfg.update(rays=5000,resolution=32,optics=[],wavelengths_nm=[638.],spectral_weights=[1.])
        plain=engine.simulate(cfg,'cpu')
        cfg['color_preview']=True
        color=engine.simulate(cfg,'cpu')
        np.testing.assert_array_equal(plain['irradiance'],color['irradiance'])
        self.assertEqual(color['display_rgba'].shape,(32,32,4))
        self.assertGreater(color['display_rgba'][:,:,0].sum(),color['display_rgba'][:,:,2].sum()*10)

    def test_dispersive_ridges_separate_wavelengths(self):
        cfg=engine.defaults();cfg.update(rays=40000,resolution=128,divergence_deg=0.,dispersion=.008,wavelengths_nm=[450.,650.],spectral_weights=[1.,1.],color_preview=True)
        result=engine.simulate(cfg,'cpu'); rgb=result['display_rgba'][:,:,:3]
        distance=np.abs(np.arange(128)-63.5)[None,:]
        red=(rgb[:,:,0]*distance).sum()/rgb[:,:,0].sum()
        blue=(rgb[:,:,2]*distance).sum()/rgb[:,:,2].sum()
        self.assertGreater(blue,red)

if __name__=='__main__':unittest.main()
