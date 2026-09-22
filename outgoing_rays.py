"""Bounded reuse of rays after all refracting and masking layers (millimetres)."""
import base64
import hashlib
import json
import math
from collections import OrderedDict
import numpy as np

DISPLAY_KEYS={'detector_z_mm','detector_size_mm','resolution','color_preview','path_samples'}


def exit_plane(cfg):
    upper=[0.]+[m['z_mm'] for m in cfg.get('masks', [cfg['mask']] if cfg.get('mask') else []) if m.get('kind','off')!='off']
    for o in cfg['optics']:
        relief=0 if o['kind']=='flat' else max(.5,o['depth_mm']) if o['kind']=='shard' else o['depth_mm']
        upper.append(o['z_mm']+o['thickness_mm']+relief+o['radius_mm']*abs(math.sin(math.radians(o['tilt_deg']))))
    return max(upper)+.01


def beam_key(cfg,backend,version):
    physical={k:v for k,v in cfg.items() if k not in DISPLAY_KEYS}
    return 'rays:'+hashlib.sha256(json.dumps([version,physical],sort_keys=True,separators=(',',':')).encode()).hexdigest()


class BeamCache:
    def __init__(self,limit=128*1024**2):
        self.limit=limit;self.entries=OrderedDict();self.size=0

    def get(self,key):
        if key not in self.entries:return None
        self.entries.move_to_end(key);return self.entries[key]

    def put(self,key,beam):
        size=beam['hits'].nbytes
        if size>self.limit:return
        if key in self.entries:self.size-=self.entries.pop(key)['hits'].nbytes
        while self.size+size>self.limit:self.size-=self.entries.popitem(last=False)[1]['hits'].nbytes
        self.entries[key]=beam;self.size+=size


def encode(beam):
    return {**{k:v for k,v in beam.items() if k!='hits'},'hits':base64.b64encode(beam['hits'].astype('<f8').tobytes()).decode()}


def decode(value):
    return {**value,'hits':np.frombuffer(base64.b64decode(value['hits']),dtype='<f8').reshape(-1,6).copy()}
