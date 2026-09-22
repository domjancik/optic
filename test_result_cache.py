import base64
import os
import tempfile
import unittest
from unittest.mock import patch
from result_cache import ResultCache, cache_key


class CacheTests(unittest.TestCase):
    def test_low_free_disk_skips_storage_without_exceeding_reserve(self):
        from collections import namedtuple
        with tempfile.TemporaryDirectory() as folder:
            cache=ResultCache(folder)
            usage=namedtuple('Usage','total used free')(1000,1000,0)
            with patch('result_cache.shutil.disk_usage',return_value=usage):
                self.assertFalse(cache.put('frame',{'map':'small'}))
            self.assertEqual(cache.stats()['entries'],0)

    def test_repeated_job_skips_transport_and_changed_samples_recompute(self):
        import jobs
        import engine
        import numpy as np
        with tempfile.TemporaryDirectory() as folder:
            cache=ResultCache(folder, reserve=0)
            cfg=engine.defaults();cfg.update(rays=1000,resolution=16)
            result={'metrics':{'backend':'cpu'},'irradiance':np.zeros((16,16),dtype=np.float32)}
            with patch.multiple(jobs,_cache=cache,_engine_version='test',_cancel_before=None,_source_key=None), patch.object(engine,'source_rays',return_value=None), patch.object(engine,'simulate',return_value=result) as simulate:
                first=jobs.calculate({'config':cfg,'backend':'cpu'})
                second=jobs.calculate({'config':cfg,'backend':'cuda'})
                self.assertFalse(first['cache']['hit'])
                self.assertTrue(second['cache']['hit'])
                self.assertEqual(first['map'],second['map'])
                self.assertEqual(second['metrics']['backend'],'cpu')
                self.assertEqual(simulate.call_count,1)
                jobs.calculate({'config':{**cfg,'rays':2000},'backend':'cpu'})
                self.assertEqual(simulate.call_count,2)

    def test_exact_key_shares_backends_but_invalidates_physics_and_engine(self):
        a = {'config': {'rays': 100, 'seed': 1}, 'backend': 'cpu'}
        self.assertEqual(cache_key(a, 'v1'), cache_key({**a, 'revision': 42}, 'v1'))
        for backend in ['cuda','auto','hybrid']:
            self.assertEqual(cache_key(a,'v1'),cache_key({**a,'backend':backend},'v1'))
        for b, version in [
                           ({**a, 'config': {'rays': 101, 'seed': 1}}, 'v1'), (a, 'v2')]:
            self.assertNotEqual(cache_key(a, 'v1'), cache_key(b, version))

    def test_persists_losslessly_and_evicts_less_used_first(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = ResultCache(folder, limit=131072, reserve=0)
            result = {'map': base64.b64encode(os.urandom(24000)).decode(), 'metrics': {}}
            self.assertTrue(cache.put('hot', result))
            for _ in range(5): self.assertEqual(cache.get('hot'), result)
            for i in range(9): cache.put(str(i), result)
            self.assertEqual(ResultCache(folder, limit=131072, reserve=0).get('hot'), result)
            self.assertIsNone(cache.get('0'))
            self.assertLessEqual(cache.stats()['bytes'], 131072)

    def test_oversize_is_skipped_and_corrupt_payload_is_a_miss(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = ResultCache(folder, limit=65536, reserve=0)
            self.assertFalse(cache.put('large', {'map': base64.b64encode(os.urandom(90000)).decode()}))
            cache.put('bad', {'map': 'good'})
            with cache.connect() as db: db.execute("UPDATE entries SET data=x'0000' WHERE key='bad'")
            self.assertIsNone(cache.get('bad'))
