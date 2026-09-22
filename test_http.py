"""Exercise real HTTP headers used by the scene loader and source controls."""
import gzip
import json
import threading
import unittest
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
import app


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_spectra_json_is_not_gzip_encoded(self):
        with urlopen(self.url + '/api/spectra') as response:
            self.assertIsNone(response.headers.get('Content-Encoding'))
            self.assertTrue(json.load(response))

    def test_mesh_encoding_and_float_payload_match_manifest(self):
        manifest = json.loads((app.ROOT / 'assets/demo-scene.json').read_text())
        with urlopen(self.url + '/assets/' + manifest['positions_file']) as response:
            self.assertEqual(response.headers.get('Content-Encoding'), 'gzip')
            payload = gzip.decompress(response.read())
        self.assertEqual(len(payload), manifest['vertex_count'] * 3 * 4)
