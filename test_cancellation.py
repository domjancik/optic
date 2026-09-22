import unittest
import time
import engine
import numpy as np
from jobs import Jobs


class CancellationTests(unittest.TestCase):
    def test_chunking_preserves_ray_random_streams(self):
        cfg=engine.defaults();cfg.update(rays=140000,resolution=32)
        whole=engine.simulate(cfg,'cpu')['irradiance']
        chunked=engine.simulate(cfg,'cpu',cancel=lambda:False)['irradiance']
        gpu=engine.simulate(cfg,'cuda',cancel=lambda:False)['irradiance']
        np.testing.assert_array_equal(whole,chunked)
        np.testing.assert_allclose(whole,gpu,atol=1e-5)

    def test_transport_observes_cancellation(self):
        cfg=engine.defaults();cfg.update(rays=1000,optics=[],resolution=32)
        with self.assertRaisesRegex(RuntimeError,'[Cc]ancel'):
            engine.simulate(cfg,'cpu',cancel=lambda: True)

    def test_cancelled_job_does_not_block_replacement(self):
        cfg=engine.defaults();cfg.update(rays=5000000,optics=[],resolution=32)
        jobs=Jobs()
        try:
            old=jobs.submit({'config':cfg,'backend':'cpu'})
            self.assertTrue(jobs.cancel(old))
            new=jobs.submit({'config':dict(cfg,rays=1000),'backend':'cpu'})
            deadline=time.monotonic()+60
            result=jobs.status(new)
            while result['status']=='running' and time.monotonic()<deadline:
                time.sleep(.05);result=jobs.status(new)
            self.assertEqual(result['status'],'complete',result)
            self.assertEqual(jobs.status(old)['status'],'cancelled')
            self.assertEqual(result['result']['metrics']['rays'],1000)
        finally:jobs.close()


if __name__=='__main__':unittest.main()
