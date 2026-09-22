"""Disposable, lossless result cache. SQLite caps the entire on-disk database."""
import hashlib
import json
import shutil
import sqlite3
import time
import zlib
from contextlib import contextmanager
from pathlib import Path

LIMIT = 1_000_000_000
ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / '.result-cache'


def engine_version():
    digest = hashlib.sha256(b'optical-result-v1')
    for name in ('engine.py', 'transport.py', 'mask.py', 'spectral.py', 'jobs.py', 'outgoing_rays.py', 'fractured_glass.py', 'patterned_surfaces.py'):
        path = ROOT / name
        if path.exists(): digest.update(path.read_bytes())
    return digest.hexdigest()


def cache_key(payload, version):
    # Compute backend is provenance, not a physical simulation input.
    value = dict(config=payload['config'], engine=version)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class ResultCache:
    def __init__(self, folder=CACHE_DIR, limit=LIMIT, reserve=64 * 1024**2):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / 'results.sqlite'
        self.limit = min(LIMIT, limit)
        self.reserve = reserve
        with self.connect() as db:
            db.execute('PRAGMA auto_vacuum=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS entries (key TEXT PRIMARY KEY, data BLOB NOT NULL, hits INTEGER NOT NULL, used REAL NOT NULL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.execute('PRAGMA journal_mode=MEMORY')
        db.execute('PRAGMA temp_store=MEMORY')
        db.execute(f'PRAGMA max_page_count={max(4, self.limit // 4096)}')
        try:
            with db: yield db
        finally: db.close()

    def get(self, key):
        with self.connect() as db:
            row = db.execute('SELECT data FROM entries WHERE key=?', (key,)).fetchone()
            if row is None: return None
            try: result = json.loads(zlib.decompress(row[0]))
            except (ValueError, zlib.error, UnicodeError):
                db.execute('DELETE FROM entries WHERE key=?', (key,))
                return None
            db.execute('UPDATE entries SET hits=hits+1, used=? WHERE key=?', (time.time(), key))
            return result

    def put(self, key, result):
        data = zlib.compress(json.dumps(result, separators=(',', ':'), allow_nan=False).encode(), 1)
        # Allow SQLite page/record overhead, and preserve free disk for the rest of the app.
        required = len(data) + 16384 + len(data) // 64
        if required + 16384 > self.limit: return False
        with self.connect() as db:
            while (self.path.stat().st_size + required > self.limit or
                   shutil.disk_usage(self.folder).free - required < self.reserve):
                victim = db.execute('SELECT key FROM entries ORDER BY hits / (1.0 + (? - used)/86400.0), used LIMIT 1', (time.time(),)).fetchone()
                if victim is None: return False
                db.execute('DELETE FROM entries WHERE key=?', victim)
                db.commit()  # FULL auto-vacuum releases pages before replacement.
            db.execute('INSERT OR REPLACE INTO entries VALUES (?, ?, 1, ?)', (key, data, time.time()))
        return True

    def stats(self, key=None):
        with self.connect() as db:
            count, average = db.execute('SELECT COUNT(*), COALESCE(AVG(LENGTH(data)),0) FROM entries').fetchone()
            row = db.execute('SELECT LENGTH(data) FROM entries WHERE key=?', (key,)).fetchone()
        return dict(bytes=self.path.stat().st_size, limit=self.limit, entries=count,
                    frame_bytes=row[0] if row else 0,
                    average_frame_bytes=round(average), free_bytes=shutil.disk_usage(self.folder).free,
                    reserve_bytes=self.reserve)
