import unittest
import importlib.util
import numpy as np


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('engine'), 'focused engine is not implemented')
        import engine
        self.e = engine

    def test_snell_and_fresnel(self):
        direction, reflectance = self.e.interface(np.array([0.5, 0., np.sqrt(.75)]), np.array([0., 0., -1.]), 1., 1.5)
        self.assertAlmostEqual(direction[0], 1/3, places=6)
        self.assertAlmostEqual(np.linalg.norm(direction), 1., places=6)
        _, r = self.e.interface(np.array([0., 0., 1.]), np.array([0., 0., -1.]), 1., 1.5)
        self.assertAlmostEqual(r, .04, places=6)

    def test_total_internal_reflection(self):
        _, r = self.e.interface(np.array([np.sqrt(.75), 0., .5]), np.array([0., 0., -1.]), 1.5, 1.)
        self.assertEqual(r, 1.)

    def test_flat_plate_energy_and_direction(self):
        cfg = self.e.defaults()
        cfg.update(rays=60000, divergence_deg=0., source_radius_mm=3., resolution=64, detector_size_mm=100.)
        cfg['optics'] = [dict(kind='flat', z_mm=10., radius_mm=13., thickness_mm=2., angle_deg=0., tilt_deg=0., pitch_mm=2., depth_mm=.5)]
        r = self.e.simulate(cfg, backend='cpu')
        self.assertAlmostEqual(r['metrics']['detected_fraction'], .96/1.04, delta=.006)
        self.assertAlmostEqual(sum(r['metrics']['fractions'].values()), 1., places=5)
        self.assertLess(abs(r['metrics']['centroid_mm'][0]), .06)
        self.assertLess(r['metrics']['fractions']['unresolved'], .001)

    def test_empty_scene_power_and_cached_source(self):
        cfg=self.e.defaults(); cfg.update(rays=5000, divergence_deg=0., detector_size_mm=100., resolution=32, optics=[])
        source=self.e.source_rays(cfg)
        a=self.e.simulate(cfg,backend='cpu',source=source)
        b=self.e.simulate(cfg,backend='cpu',source=source)
        np.testing.assert_array_equal(a['irradiance'],b['irradiance'])
        self.assertAlmostEqual(a['metrics']['detected_fraction'],1.,places=6)
        self.assertAlmostEqual(float(a['irradiance'].sum())*(.1/32)**2,cfg['optical_power_w'],places=5)

    def test_closed_meshes(self):
        for kind in ['flat','prism','lenticular','shard']:
            cfg=self.e.defaults(); cfg['optics'][0]['kind']=kind
            mesh=self.e.optic_mesh(cfg['optics'][0])
            edges={}
            for tri in mesh:
                for i in range(3):
                    a=tuple(np.round(tri[i],6)); b=tuple(np.round(tri[(i+1)%3],6))
                    key=tuple(sorted((a,b))); edges[key]=edges.get(key,0)+1
            self.assertTrue(all(v==2 for v in edges.values()),kind)

    def test_cpu_gpu_agreement(self):
        cfg=self.e.defaults(); cfg.update(rays=40000,resolution=64)
        cpu=self.e.simulate(cfg,backend='cpu'); gpu=self.e.simulate(cfg,backend='cuda')
        self.assertEqual(gpu['metrics']['backend'],'cuda')
        np.testing.assert_allclose(cpu['irradiance'],gpu['irradiance'],atol=1e-5)

    def test_detector_crop_accounts_for_power(self):
        cfg=self.e.defaults(); cfg.update(rays=5000,optics=[],detector_size_mm=1.)
        result=self.e.simulate(cfg,backend='cpu')
        self.assertGreater(result['metrics']['fractions']['outside_detector'],.99)
        self.assertAlmostEqual(sum(result['metrics']['fractions'].values()),1.)

    def test_exports_are_physical_and_reopenable(self):
        self.assertIsNotNone(importlib.util.find_spec('app'),'export/UI layer is not implemented')
        import app, tempfile, json
        from pathlib import Path
        from PIL import Image
        cfg=self.e.defaults(); cfg.update(rays=1000,optics=[],resolution=32)
        result=self.e.simulate(cfg,backend='cpu')
        with tempfile.TemporaryDirectory() as folder:
            app.export_result(result,Path(folder))
            np.testing.assert_array_equal(np.load(Path(folder)/'irradiance.npy'),result['irradiance'])
            with Image.open(Path(folder)/'preview.png') as img: self.assertEqual(img.size,(32,32))
            self.assertTrue((Path(folder)/'irradiance.hdr').read_bytes().startswith(b'#?RADIANCE'))
            self.assertEqual(json.loads((Path(folder)/'result.json').read_text())['config']['rays'],1000)

    def test_absorbing_plate(self):
        cfg=self.e.defaults(); cfg.update(rays=60000,divergence_deg=0.,source_radius_mm=3.,absorption_per_mm=.2)
        cfg['optics'][0].update(kind='flat',thickness_mm=2.)
        result=self.e.simulate(cfg,backend='cpu'); a=np.exp(-.4)
        self.assertAlmostEqual(result['metrics']['detected_fraction'],.96**2*a/(1-.04**2*a*a),delta=.005)
        self.assertGreater(result['metrics']['fractions']['absorbed'],.25)
        self.assertAlmostEqual(sum(result['metrics']['fractions'].values()),1.,places=6)

    def test_overlapping_optics_rejected(self):
        cfg=self.e.defaults(); cfg['optics'].append(dict(cfg['optics'][0]))
        with self.assertRaisesRegex(ValueError,'overlap'): self.e.simulate(cfg,backend='cpu')

    def test_zero_power_cached_source_rejected(self):
        cfg=self.e.defaults(); cfg['rays']=100
        rays=self.e.source_rays(cfg); rays[:,7]=0
        with self.assertRaisesRegex(ValueError,'power'): self.e.simulate(cfg,source=rays)

    def test_ui_ray_and_cuda_options_exist(self):
        from html.parser import HTMLParser
        from pathlib import Path
        class Options(HTMLParser):
            values=[]
            def handle_starttag(self,tag,attrs):
                if tag=='option': self.values.append(dict(attrs).get('value'))
        p=Options();p.feed(Path('index.html').read_text(encoding='utf8'))
        self.assertIn('500000',p.values)
        self.assertIn('cuda',p.values)


if __name__=='__main__': unittest.main()
