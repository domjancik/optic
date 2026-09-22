"""Independent persistent CPU/CUDA lanes with bounded queues and cancellation."""

import base64

import uuid
import os

import threading
import multiprocessing
import time
import sqlite3
from result_cache import ResultCache, cache_key, engine_version
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import engine
from outgoing_rays import BeamCache, beam_key, exit_plane, encode, decode
_beams=BeamCache()



_source_key=None

_source=None
_cancel_before=None
_cache=None
_engine_version=None

def initialize_worker(cancel_before):
    global _cancel_before
    _cancel_before=cancel_before
    from numba import set_num_threads, config
    set_num_threads(min(4,max(1,(os.cpu_count() or 2)//2),config.NUMBA_NUM_THREADS))


def calculate(payload,generation=0):
    global _source_key,_source,_cache,_engine_version
    import json

    cancelled=lambda: _cancel_before is not None and _cancel_before.value>=generation
    if cancelled(): raise RuntimeError('Cancelled')
    cfg=payload['config']
    started=time.perf_counter();cache_error=None;hit=None
    try:
        if _cache is None: _cache=ResultCache()
        if _engine_version is None: _engine_version=engine_version()
        result_key=cache_key(payload,_engine_version)
        hit=_cache.get(result_key)
    except (OSError,sqlite3.Error) as error: cache_error=str(error)
    if cancelled(): raise RuntimeError('Cancelled')
    if hit is not None:
        try: stats=_cache.stats(result_key)
        except (OSError,sqlite3.Error): stats={}
        hit['cache']=dict(hit=True,lookup_ms=round((time.perf_counter()-started)*1000,1),**stats)
        return hit
    key=json.dumps({k:cfg.get(k,'led') for k in ['source_model','rays','seed','source_radius_mm','divergence_deg','led_softness','optical_power_w','wavelengths_nm','spectral_weights']},sort_keys=True)

    if key!=_source_key: _source=engine.source_rays(cfg);_source_key=key

    backend=payload.get('backend','cuda');beam=None;beam_id=None
    if cfg['detector_z_mm']>=exit_plane(cfg) and cfg['rays']*48<=128*1024**2:
        beam_id=beam_key(cfg,backend,_engine_version)
        beam=_beams.get(beam_id)
        if beam is None and _cache is not None:
            try:
                stored=_cache.get(beam_id)
                if stored is not None:beam=decode(stored);_beams.put(beam_id,beam)
            except (OSError,sqlite3.Error,ValueError):pass
    if cancelled():raise RuntimeError('Cancelled')
    result=engine.simulate(cfg,backend,source=_source,cancel=cancelled,outgoing=beam,capture_exit=beam_id is not None and beam is None)
    captured=result.pop('_outgoing',None)
    if captured is not None and not cancelled():
        _beams.put(beam_id,captured)
        if _cache is not None and captured['hits'].nbytes<=128*1024**2:
            try:_cache.put(beam_id,encode(captured))
            except (OSError,sqlite3.Error):pass

    response=dict(config=cfg,metrics=result['metrics'],map=base64.b64encode(result['irradiance'].astype('<f4').tobytes()).decode())
    if 'ray_samples' in result:response['ray_samples']=result['ray_samples']
    if 'display_rgba' in result:response['color_map']=base64.b64encode(result['display_rgba'].astype('<f4').tobytes()).decode()
    if cancelled(): raise RuntimeError('Cancelled')
    saved=False;stats={}
    try:
        if _cache is not None and cache_error is None: saved=_cache.put(result_key,response);stats=_cache.stats(result_key)
    except (OSError,sqlite3.Error) as error: cache_error=str(error)
    response['cache']=dict(hit=False,saved=saved,error=cache_error,**stats)
    return response


class Jobs:

    def __init__(self):

        self.cancel_limits={lane:multiprocessing.get_context().Value('q',0) for lane in ('cpu','cuda')}
        self.generation=0;self.generations={};self.cancelled=set();self.lanes={}
        self.pools={lane:ProcessPoolExecutor(max_workers=1,initializer=initialize_worker,initargs=(limit,)) for lane,limit in self.cancel_limits.items()}
        self.futures={};self.lock=threading.Lock()

    def submit(self,payload):

        payload=dict(payload)
        backend=payload.get('backend','cuda')
        if backend=='hybrid':payload['backend']='cuda';backend='cuda'
        if backend not in ('cpu','cuda','auto'):raise ValueError('Unknown compute backend')
        lane='cpu' if backend=='cpu' else 'cuda'
        engine.validate(payload['config'])

        with self.lock:

            if sum(not f.done() and self.lanes[k]==lane for k,f in self.futures.items())>=2: raise ValueError('Compute queue full; wait for current job')

            for k in list(self.futures):

                if len(self.futures)<8: break

                if self.futures[k].done():
                    del self.futures[k]
                    self.generations.pop(k,None);self.cancelled.discard(k);self.lanes.pop(k,None)
            key=uuid.uuid4().hex;self.generation+=1;self.generations[key]=self.generation
            self.lanes[key]=lane
            self.futures[key]=self.pools[lane].submit(calculate,payload,self.generation)
            return key
    def cancel(self,key):
        with self.lock:
            future=self.futures.get(key)
            if future is None or future.done(): return False
            self.cancelled.add(key)
            limit=self.cancel_limits[self.lanes[key]]
            limit.value=max(limit.value,self.generations[key])
            future.cancel()
            return True
    def status(self,key):

        with self.lock: future=self.futures.get(key)

        if future is None: return dict(status='error',error='Job expired or unknown')
        if key in self.cancelled: return dict(status='cancelled')
        if not future.done(): return dict(status='running')

        try: return dict(status='complete',result=future.result())

        except Exception as e: return dict(status='cancelled') if str(e)=='Cancelled' else dict(status='error',error=str(e) or type(e).__name__)
    def close(self):
        for limit in self.cancel_limits.values():limit.value=self.generation
        for pool in self.pools.values():pool.shutdown(wait=True,cancel_futures=True)
