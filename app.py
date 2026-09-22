"""Local-only UI and command-line export. No network dependencies."""
import argparse
import base64
import io
import json
import time
import uuid
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import numpy as np
from PIL import Image
import engine

ROOT=Path(__file__).resolve().parent
SOURCE_CACHE={}
JOBS=None


def preview(array,scale=None):
    # Fixed user-selected scale is used across an animation; display only.
    if scale is None: scale=max(float(np.percentile(array[array>0],99)) if np.any(array>0) else 1.,1e-9)
    value=1-np.exp(-np.maximum(array,0)/scale*2)
    pixels=np.uint8(np.clip(value,0,1)**(1/2.2)*255)
    return Image.fromarray(np.flipud(pixels)),scale


def export_result(result,folder,scale=None):
    folder.mkdir(parents=True,exist_ok=True)
    array=result['irradiance']; np.save(folder/'irradiance.npy',array)
    image,scale=preview(array,scale); image.save(folder/'preview.png')
    if 'display_rgba' in result:
        rgb=result['display_rgba'][:,:,:3]
        np.save(folder/'display_rgb.npy',rgb)
        image=Image.fromarray(np.uint8(np.clip(1-np.exp(-np.flipud(rgb)/scale*2),0,1)**(1/2.2)*255))
        image.save(folder/'preview.png')
    # Radiance flat RGBE encoding. Channels equal irradiance for a monochrome map.
    # Values are W/m², NOT scene radiance: use as a calibrated map, not an environment.
    a=np.flipud(array).astype(float); mantissa,exponent=np.frexp(a)
    byte=np.uint8(np.clip(mantissa*256,0,255)); e=np.uint8(np.clip(exponent+128,0,255))
    rgba=np.stack((byte,byte,byte,e),axis=-1); rgba[a<=0]=0
    with (folder/'irradiance.hdr').open('wb') as f:
        f.write(f'#?RADIANCE\n# Detector irradiance W/m2, grayscale; not radiance\nFORMAT=32-bit_rle_rgbe\n\n-Y {len(a)} +X {a.shape[1]}\n'.encode())
        # Flat scanlines are supported by RGBE readers; first byte cannot be 2,2,128+.
        f.write(rgba.tobytes())
    (folder/'result.json').write_text(json.dumps(dict(config=result['config'],metrics=result['metrics'],
        units='W/m^2',npy_origin='lower left',preview_scale_w_m2=scale,
        assumptions='Effective uniform pupil/cone; unpolarized geometric optics; common material; no measured LED/lens prescription'),indent=2))
    return image,scale


def cached_source(cfg):
    keys=['source_model','rays','seed','source_radius_mm','divergence_deg','optical_power_w','wavelengths_nm','spectral_weights']
    key=json.dumps({k:cfg.get(k,'led') for k in keys},sort_keys=True)
    if key not in SOURCE_CACHE:
        SOURCE_CACHE.clear(); SOURCE_CACHE[key]=engine.source_rays(cfg)
    return SOURCE_CACHE[key]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/jobs/'):
            self.send_json(JOBS.status(self.path.rsplit('/',1)[-1])); return
        if self.path=='/api/defaults':
            self.send_json(engine.defaults()); return
        if self.path=='/api/spectra':
            from spectral import spectrum_preset
            self.send_json({name:spectrum_preset(name) for name in ['neutral-white','warm-white','laser-450','laser-520','laser-532','laser-638','laser-650']});return
        path=ROOT/'index.html' if self.path=='/' else (ROOT/self.path.lstrip('/')).resolve()
        if not path.is_relative_to(ROOT) or (path.suffix not in ['.html','.js','.css','.png','.npy','.hdr','.json','.bin'] and not path.name.endswith('.bin.gz')) or not path.is_file():
            self.send_error(404); return
        data=path.read_bytes(); self.send_response(200)
        self.send_header('Content-Type',{'html':'text/html','js':'text/javascript','css':'text/css','png':'image/png','json':'application/json'}.get(path.suffix[1:],'application/octet-stream'))
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        if path.name.endswith('.bin.gz'):self.send_header('Content-Encoding','gzip')
        self.end_headers(); self.wfile.write(data)

    def send_json(self,data,status=200):
        raw=json.dumps(data,allow_nan=False).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw)))
        self.end_headers(); self.wfile.write(raw)

    def do_POST(self):
        if self.path not in ['/api/simulate','/api/jobs','/api/export','/api/surface-map','/api/cancel']: self.send_error(404); return
        # Refuse browser requests originating outside this local UI.
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{self.headers.get("Host")}': self.send_error(403); return
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<65536: raise ValueError('Invalid request size')
            payload=json.loads(self.rfile.read(length))
            if self.path=='/api/cancel':
                self.send_json(dict(cancelled=JOBS.cancel(payload['id'])));return
            if self.path=='/api/surface-map':
                from surface_map import surface_map
                self.send_json(surface_map(payload['optic']));return
            if self.path=='/api/jobs':
                self.send_json(dict(id=JOBS.submit(payload)),202);return
            if self.path=='/api/export':
                state=JOBS.status(payload['id'])
                if state['status']!='complete': raise ValueError('Result unavailable')
                raw=state['result']; res=raw['config']['resolution']
                result=dict(config=raw['config'],metrics=raw['metrics'],irradiance=np.frombuffer(base64.b64decode(raw['map']),dtype='<f4').reshape(res,res))
                if raw.get('color_map'):result['display_rgba']=np.frombuffer(base64.b64decode(raw['color_map']),dtype='<f4').reshape(res,res,4)
                folder=ROOT/'outputs'/('saved-'+payload['id'])
                export_result(result,folder);self.send_json(dict(folder='/outputs/'+folder.name));return
            cfg=payload['config']; engine.validate(cfg)
            result=engine.simulate(cfg,backend=payload.get('backend','auto'),source=cached_source(cfg))
            run=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
            image,scale=export_result(result,ROOT/'outputs'/run,payload.get('scale'))
            stream=io.BytesIO(); image.save(stream,format='PNG')
            self.send_json(dict(metrics=result['metrics'],scale=scale,folder='/outputs/'+run,
                image='data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()))
        except Exception as e: self.send_json(dict(error=str(e)),400)


def main():
    global JOBS
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--config'); parser.add_argument('--backend',choices=['auto','cpu','cuda'],default='auto')
    parser.add_argument('--out',default='outputs/cli'); args=parser.parse_args()
    if args.config:
        cfg=json.loads(Path(args.config).read_text()); result=engine.simulate(cfg,args.backend)
        export_result(result,Path(args.out)); print(json.dumps(result['metrics'],indent=2))
    else:
        from jobs import Jobs
        JOBS=Jobs()
        print(f'Optical bench: http://127.0.0.1:{args.port}',flush=True)
        try: ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
        finally: JOBS.close()


if __name__=='__main__': main()
