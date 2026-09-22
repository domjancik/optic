"""Local-space upper-surface height sampled from the actual transport triangles."""
from functools import lru_cache
import json
import numpy as np
import engine


def surface_map(optic, resolution=128):
    local=dict(optic,z_mm=0.,angle_deg=0.,tilt_deg=0.)
    keys=['kind','radius_mm','thickness_mm','pitch_mm','depth_mm']
    values={k:local[k] for k in keys}
    if local['kind']=='linear_fresnel':values.update(focal_mm=local.get('focal_mm',300.),design_index=local.get('design_index',1.49))
    key=json.dumps(values,sort_keys=True)
    return _cached(key,int(resolution))


@lru_cache(maxsize=32)
def _cached(key,resolution):
    o=json.loads(key);o.update(z_mm=0.,angle_deg=0.,tilt_deg=0.)
    if o['kind'] not in ['flat','prism','lenticular','cylindrical','shard','fractured','linear_fresnel','crossed_prism','pyramid','ice','hammer','haircell']:
        raise ValueError('Unknown surface')
    if not all(np.isfinite(o[k]) for k in ['radius_mm','thickness_mm','pitch_mm','depth_mm']):
        raise ValueError('Surface dimensions must be finite')
    if not 16<=resolution<=256 or min(o['radius_mm'],o['thickness_mm'],o['pitch_mm'])<=0 or o['depth_mm']<0 or o['radius_mm']/o['pitch_mm']>100:
        raise ValueError('Invalid surface dimensions or resolution')
    if o['kind']=='cylindrical' and o['depth_mm']>o['pitch_mm']/2:
        raise ValueError('Cylindrical sag must not exceed half pitch')
    r=o['radius_mm'];axis=np.linspace(-r,r,resolution)
    x,y=np.meshgrid(axis,axis)
    # Append exact y=0 cross-section to the same mesh query.
    xs=np.r_[x.ravel(),axis];ys=np.r_[y.ravel(),np.zeros(resolution)]
    z=np.full(xs.shape,-np.inf)
    for tri in engine.optic_mesh(o):
        a,b,c=tri
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-14:continue
        ids=np.flatnonzero((xs>=tri[:,0].min()-1e-9)&(xs<=tri[:,0].max()+1e-9)&(ys>=tri[:,1].min()-1e-9)&(ys<=tri[:,1].max()+1e-9))
        xx=xs[ids];yy=ys[ids]
        u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        inside=(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)
        ids=ids[inside];u=u[inside];v=v[inside]
        z[ids]=np.maximum(z[ids],u*a[2]+v*b[2]+(1-u-v)*c[2])
    values=z[:resolution*resolution];finite=values[np.isfinite(values)]
    serial=lambda data:[float(v) if np.isfinite(v) else None for v in data]
    return dict(resolution=resolution,heights_mm=serial(values),profile_mm=serial(z[resolution*resolution:]),
                min_mm=float(finite.min()),max_mm=float(finite.max()),diameter_mm=2*r,
                units='mm above local base plane',origin='lower left',geometry='actual triangulated upper envelope')
