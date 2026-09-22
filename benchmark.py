"""Reproducible warm-run timing and sampling study; saves actual maps and motion."""
import json
import copy
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import engine
from app import export_result,preview

out=Path(__file__).parent/'outputs'/'benchmark'; out.mkdir(parents=True,exist_ok=True)
cfg=engine.defaults();cfg.update(rays=500000,resolution=512)
cfg['optics'][0]['depth_mm']=.35
engine.simulate(cfg,'cuda');engine.simulate(cfg,'cpu')
records=[];gallery=[]
for kind in ['flat','prism','lenticular','shard']:
    c=copy.deepcopy(cfg);c['optics'][0]['kind']=kind
    for backend in ['cpu','cuda']:
        r=engine.simulate(c,backend);records.append(dict(case=kind,**r['metrics']))
        if backend=='cuda':
            image,_=export_result(r,out/kind)
            canvas=Image.new('RGB',(512,560),'#101a27');canvas.paste(image,(0,38))
            ImageDraw.Draw(canvas).text((14,10),f"{kind} | {r['metrics']['total_seconds']:.3f}s | 500,000 rays",fill='white')
            gallery.append(canvas)
comparison=Image.new('RGB',(1024,1120))
for i,image in enumerate(gallery): comparison.paste(image,((i%2)*512,(i//2)*560))
comparison.save(out/'comparison.png')
frames=[];scale=None
for i in range(24):
    c=copy.deepcopy(cfg);c['optics'][0]['angle_deg']=15*i
    c['optics'].append(dict(c['optics'][0],z_mm=18.,angle_deg=45-15*i))
    r=engine.simulate(c,'cuda');image,scale=export_result(r,out/'motion'/f'{i:03d}',scale)
    frames.append(image)
frames[0].save(out/'motion.gif',save_all=True,append_images=frames[1:],duration=150,loop=0)
convergence=[]
for count in [100000,500000,2000000]:
    for seed in [42,731]:
        c=copy.deepcopy(cfg);c.update(rays=count,seed=seed,resolution=64)
        r=engine.simulate(c,'cuda');export_result(r,out/f'convergence-{count}-{seed}')
        convergence.append(dict(count=count,seed=seed,**r['metrics']))
report=dict(timings=records,convergence=convergence,notes='Warm process; timings include host/device transfer and CPU detector binning. Excludes PNG/HDR export. No Blender timing comparison was performed.')
(out/'benchmark.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
