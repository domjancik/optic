import unittest
import engine
class MaskTests(unittest.TestCase):
 def test_dot_area_and_gpu(self):
  c=engine.defaults();c.update(rays=100000,optics=[],divergence_deg=0,source_radius_mm=10)
  c['mask']=dict(kind='dot',z_mm=5,radius_mm=5,pitch_mm=6,count=3,angle_deg=0,x_mm=0,y_mm=0)
  a=engine.simulate(c,'cpu');b=engine.simulate(c,'cuda')
  self.assertAlmostEqual(a['metrics']['detected_fraction'],.25,delta=.006)
  self.assertAlmostEqual(a['metrics']['fractions']['masked'],.75,delta=.006)
  self.assertAlmostEqual(a['metrics']['detected_fraction'],b['metrics']['detected_fraction'])
  self.assertAlmostEqual(sum(a['metrics']['fractions'].values()),1)
 def test_inside_optic_rejected(self):
  c=engine.defaults();c['mask']=dict(kind='dot',z_mm=11,radius_mm=1,pitch_mm=3,count=3,angle_deg=0,x_mm=0,y_mm=0)
  with self.assertRaisesRegex(ValueError,'mask|Mask'):engine.validate(c)
if __name__=='__main__':unittest.main()
