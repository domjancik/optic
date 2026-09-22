import unittest
import importlib.util
import time
import engine

class JobTests(unittest.TestCase):
    def test_process_job_is_nonblocking_and_preserves_map(self):
        self.assertIsNotNone(importlib.util.find_spec('jobs'),'background job engine missing')
        from jobs import Jobs
        cfg=engine.defaults();cfg.update(rays=1000,optics=[],resolution=32)
        jobs=Jobs()
        try:
            start=time.perf_counter(); key=jobs.submit({'config':cfg,'backend':'cpu'})
            self.assertLess(time.perf_counter()-start,1.)
            result=jobs.status(key)
            while result['status']=='running':
                time.sleep(.05); result=jobs.status(key)
            self.assertEqual(result['status'],'complete', result.get('error'))
            self.assertEqual(jobs.lanes[key],'cpu')
            self.assertIn(result['result']['metrics']['backend'],['cpu','cuda'])
            self.assertAlmostEqual(result['result']['metrics']['detected_fraction'],1.)
            import base64
            self.assertEqual(len(base64.b64decode(result['result']['map'])),32*32*4)
        finally: jobs.close()

    def test_cpu_cancellation_does_not_cancel_cuda_lane(self):
        from jobs import Jobs
        cfg=engine.defaults();cfg.update(rays=1000,optics=[],resolution=32)
        jobs=Jobs()
        try:
            cpu=jobs.submit({'config':dict(cfg,rays=5000000),'backend':'cpu'})
            gpu=jobs.submit({'config':cfg,'backend':'hybrid'})
            jobs.cancel(cpu)
            deadline=time.monotonic()+60
            result=jobs.status(gpu)
            while result['status']=='running' and time.monotonic()<deadline:
                time.sleep(.05);result=jobs.status(gpu)
            self.assertEqual(result['status'],'complete',result)
            self.assertEqual(jobs.lanes[gpu],'cuda')
            if not result['result']['cache']['hit']:
                self.assertEqual(result['result']['metrics']['backend'],'cuda')
            else:
                self.assertIn(result['result']['metrics']['backend'],['cpu','cuda'])
            self.assertEqual(jobs.status(cpu)['status'],'cancelled')
        finally:jobs.close()

if __name__=='__main__': unittest.main()
