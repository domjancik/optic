"""Detector-map simulator. Effective post-collimator source; no proprietary lens prescription."""

import copy

import math

import time

import os

from pathlib import Path

import numpy as np

from numba import njit, prange

from scipy.spatial import ConvexHull

from transport import compile_transport



_bend,_trace=compile_transport(njit)





def interface(direction, normal, ni, nt):

    r=_bend(*direction,*normal,ni,nt)

    return np.array(r[:3]),r[3]





def defaults():

    return dict(rays=200000,seed=42,source_model="led",source_radius_mm=9.,divergence_deg=5.,optical_power_w=1.,

                detector_z_mm=1000.,detector_size_mm=600.,resolution=512,n550=1.49,

                dispersion=0.,absorption_per_mm=0.,max_bounces=24,

                wavelengths_nm=[550.],spectral_weights=[1.],

                optics=[dict(kind='prism',radius_mm=13.,z_mm=10.,thickness_mm=2.,

                             pitch_mm=2.,depth_mm=.35,angle_deg=0.,tilt_deg=0.)])





def source_rays(cfg):

    """Uniform pupil and uniform-solid-angle cone, full angle, NOT Gaussian FWHM."""

    rng=np.random.default_rng(cfg['seed']); count=int(cfg['rays'])

    r=cfg['source_radius_mm']*np.sqrt(rng.random(count)); phi=rng.uniform(0,2*np.pi,count)

    cos=1-rng.random(count)*(1-np.cos(np.deg2rad(cfg['divergence_deg']/2)))

    azi=rng.uniform(0,2*np.pi,count); sin=np.sqrt(1-cos*cos)

    weights=np.asarray(cfg['spectral_weights'],float); weights/=weights.sum()

    wave=rng.choice(cfg['wavelengths_nm'],count,p=weights)

    if cfg.get('source_model','led')=='laser':

        # Gaussian phase-space envelope at a waist; intensity radius and angle are 1/e².

        xy=rng.normal(0,cfg['source_radius_mm']/2,(count,2))

        slopes=rng.normal(0,np.tan(np.deg2rad(cfg['divergence_deg']/2))/2,(count,2))

        direction=np.column_stack((slopes,np.ones(count)))

        direction/=np.linalg.norm(direction,axis=1)[:,None]

        return np.ascontiguousarray(np.column_stack((xy,np.zeros(count),direction,wave,

            np.full(count,cfg['optical_power_w']/count))),dtype=np.float64)

    softness=cfg.get('led_softness',0.)
    if softness:
        sigma=softness*np.tan(np.deg2rad(cfg['divergence_deg']/2))
        slopes=np.column_stack((sin*np.cos(azi)/cos,sin*np.sin(azi)/cos))
        slopes+=rng.normal(0,sigma,(count,2))
        direction=np.column_stack((slopes,np.ones(count)))
        direction/=np.linalg.norm(direction,axis=1)[:,None]
        return np.ascontiguousarray(np.column_stack((r*np.cos(phi),r*np.sin(phi),np.zeros(count),direction,wave,
            np.full(count,cfg['optical_power_w']/count))),dtype=np.float64)
    return np.ascontiguousarray(np.column_stack((r*np.cos(phi),r*np.sin(phi),np.zeros(count),

                            sin*np.cos(azi),sin*np.sin(azi),cos,wave,

                            np.full(count,cfg['optical_power_w']/count))),dtype=np.float64)





def optic_mesh(o):

    r=o['radius_mm']; t=o['thickness_mm']; kind=o['kind']

    if kind in ('linear_fresnel','crossed_prism','pyramid','ice','hammer','haircell'):
        from patterned_surfaces import patterned_mesh
        mesh=patterned_mesh(o)
    elif kind=='fractured':
        from fractured_glass import fractured_mesh
        mesh=fractured_mesh(r,t,o['pitch_mm'],o['depth_mm'])
    elif kind=='shard':
        rng=np.random.default_rng(123)

        a=np.arange(9)*2*np.pi/9

        points=np.column_stack((r*np.cos(a),r*np.sin(a),rng.uniform(-.5,.5,9)))

        points=np.vstack((points+[0,0,t],points,[0,0,t+o['depth_mm']]))

        hull=ConvexHull(points); mesh=points[hull.simplices].copy()

        for i,eq in enumerate(hull.equations):

            if np.dot(np.cross(mesh[i,1]-mesh[i,0],mesh[i,2]-mesh[i,0]),eq[:3])<0: mesh[i]=mesh[i,[0,2,1]]

    else:

        # Columns align with every prism cusp. Circular boundary is a polygon.

        pitch=o['pitch_mm']; depth=o['depth_mm']

        step=pitch/(48 if kind in ['lenticular','cylindrical'] else 2)

        xs=np.unique(np.r_[-r,np.arange(math.ceil(-r/step),math.floor(r/step)+1)*step,r])

        xs=xs[(xs>=-r)&(xs<=r)]

        verts=[]

        for x in xs:

            y=math.sqrt(max(0,r*r-x*x))

            phase=(x/pitch+.5)%1-.5

            h=0. if kind=='flat' else depth*(1-2*abs(phase)) if kind=='prism' else depth*math.sqrt(max(0,1-(2*phase)**2))

            if kind=='cylindrical':

                a=pitch/2

                radius=(a*a+depth*depth)/(2*depth) if depth else 1.

                h=math.sqrt(max(0,radius*radius-(phase*pitch)**2))-(radius-depth) if depth else 0.

            verts.append([[x,-y,0],[x,y,0],[x,-y,t+h],[x,y,t+h]])

        v=np.array(verts); faces=[]

        for a,b in zip(v[:-1],v[1:]):

            faces.extend([[a[2],b[2],b[3]],[a[2],b[3],a[3]],

                          [a[0],b[1],b[0]],[a[0],a[1],b[1]],

                          [a[0],b[0],b[2]],[a[0],b[2],a[2]],

                          [a[1],a[3],b[3]],[a[1],b[3],b[1]]])

        mesh=np.array(faces)

        area=np.linalg.norm(np.cross(mesh[:,1]-mesh[:,0],mesh[:,2]-mesh[:,0]),axis=1)

        mesh=mesh[area>1.e-10]

    angle=np.deg2rad(o['angle_deg']); tilt=np.deg2rad(o['tilt_deg'])

    rz=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])

    rx=np.array([[1,0,0],[0,np.cos(tilt),-np.sin(tilt)],[0,np.sin(tilt),np.cos(tilt)]])

    return mesh @ (rx@rz).T + [o.get('x_mm',0.),o.get('y_mm',0.),o['z_mm']]





def bvh(mesh):

    nodes=[]; ordered=[]

    def visit(indices):

        n=len(nodes); points=mesh[indices].reshape(-1,3)

        low=points.min(0)-1.e-6; high=points.max(0)+1.e-6

        nodes.append([*low,*high,0,0,0])

        if len(indices)<=8:

            nodes[n][6]=len(ordered); nodes[n][7]=len(indices); ordered.extend(indices)

        else:

            axis=np.argmax(high-low); centers=mesh[indices].mean(1)[:,axis]

            ids=indices[np.argsort(centers)]; mid=len(ids)//2

            visit(ids[:mid]); visit(ids[mid:])

        nodes[n][8]=len(nodes)

    if len(mesh): visit(np.arange(len(mesh)))

    tri=np.ascontiguousarray(mesh[ordered]); normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])

    if len(tri): normals/=np.linalg.norm(normals,axis=1)[:,None]

    return tri,normals,np.array(nodes,dtype=np.float64).reshape(-1,9)





@njit(parallel=True)

def _cpu(rays,tri,normals,nodes,z,n,b,a,depth,seed,mask):

    out=np.empty((len(rays),6),np.float64)
    for i in prange(len(rays)):

        x,y,p,s,sx,sy=_trace(i,rays,tri,normals,nodes,z,n,b,a,depth,seed,mask)
        out[i,0]=x; out[i,1]=y; out[i,2]=p; out[i,3]=s; out[i,4]=sx; out[i,5]=sy
    return out





_gpu_kernel=None

def gpu_kernel():

    global _gpu_kernel

    if _gpu_kernel is not None: return _gpu_kernel

    # CUDA 13 Windows puts DLLs in bin/x64, unlike older Numba discovery.

    root=Path(os.environ.get('CUDA_HOME','C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.1'))

    from numba.cuda.cuda_paths import get_cuda_paths

    paths=get_cuda_paths()

    for key,folder,pattern in [('nvvm',root/'nvvm/bin/x64','nvvm*.dll'),('cudalib_dir',root/'bin/x64','cudart*.dll')]:

        matches=list(folder.glob(pattern))

        if matches:

            paths[key]=type(paths[key])('simulator local discovery',str(matches[0] if key=='nvvm' else folder))

    from numba import cuda

    _,trace=compile_transport(lambda f:cuda.jit(device=True)(f))

    @cuda.jit

    def kernel(rays,tri,normals,nodes,z,n,b,a,depth,seed,mask,out):

        i=cuda.grid(1)

        if i<len(rays):

            x,y,p,s,sx,sy=trace(i,rays,tri,normals,nodes,z,n,b,a,depth,seed,mask)
            out[i,0]=x; out[i,1]=y; out[i,2]=p; out[i,3]=s; out[i,4]=sx; out[i,5]=sy
    _gpu_kernel=kernel

    return kernel





def mask_layers(cfg):

    """New lists override the legacy single-mask field, including an empty list."""

    masks=cfg.get('masks', [cfg['mask']] if cfg.get('mask') else [])

    if not isinstance(masks,list) or len(masks)>16:

        raise ValueError('Masks must be a list of at most 16 layers')

    return [m for m in masks if m.get('kind','off')!='off']





def validate(cfg):
    for field in ('rays','resolution','max_bounces','seed'):
        value=cfg.get(field)
        if isinstance(value,(bool,str)) or not isinstance(value,(int,float,np.integer,np.floating)) or not np.isfinite(value) or value!=int(value):
            raise ValueError(field+' must be a finite integer')
        cfg[field]=int(value)
    model=cfg.get('source_model','led')

    if model not in ['led','laser']: raise ValueError('Unknown source model')

    if model=='laser':

        limit=max(cfg['wavelengths_nm'])*1e-6/(np.pi*cfg['source_radius_mm'])

        if np.tan(np.deg2rad(cfg['divergence_deg']/2))<limit: raise ValueError('Laser divergence below diffraction limit for this waist and wavelength')

    if not 100<=cfg['rays']<=5000000: raise ValueError('Ray count must be 100..5,000,000')

    if not 16<=cfg['resolution']<=2048: raise ValueError('Resolution must be 16..2048')

    for key in ['detector_z_mm','detector_size_mm','optical_power_w','source_radius_mm']:

        if not np.isfinite(cfg[key]) or cfg[key]<=0: raise ValueError(key+' must be positive')

    softness=cfg.get('led_softness',0.)
    if not isinstance(softness,(int,float)) or not np.isfinite(softness) or not 0<=softness<=1:raise ValueError('LED softness must be 0..1')
    if not 0<=cfg['divergence_deg']<90: raise ValueError('Full cone angle must be 0..90 degrees')

    if not 1<cfg['n550']<3: raise ValueError('Refractive index must be 1..3')

    if cfg['absorption_per_mm']<0 or not 1<=cfg['max_bounces']<=128: raise ValueError('Invalid absorption or bounce limit')

    w=np.asarray(cfg['wavelengths_nm']); s=np.asarray(cfg['spectral_weights'])

    if len(w)==0 or len(w)!=len(s) or np.any(w<380) or np.any(w>780) or np.any(s<0) or s.sum()<=0: raise ValueError('Invalid spectrum')

    bounds=[]

    for o in cfg['optics']:

        if not all(np.isfinite(o.get(k,0.)) for k in ['radius_mm','thickness_mm','pitch_mm','depth_mm','angle_deg','tilt_deg','z_mm','x_mm','y_mm']):raise ValueError('Optic dimensions and pose must be finite')

        if o['kind'] not in ['flat','prism','lenticular','cylindrical','shard','fractured','linear_fresnel','crossed_prism','pyramid','ice','hammer','haircell']: raise ValueError('Unknown optic')
        if min(o['radius_mm'],o['thickness_mm'],o['pitch_mm'])<=0 or o['depth_mm']<0: raise ValueError('Invalid optic dimensions')

        if o['radius_mm']/o['pitch_mm']>100: raise ValueError('Pitch too small for geometric preview')

        if o['kind']=='cylindrical' and o['depth_mm']>o['pitch_mm']/2: raise ValueError('Cylindrical sag must not exceed half pitch')

        mesh=optic_mesh(o); bounds.append((mesh[:,:,2].min(),mesh[:,:,2].max()))

    masks=mask_layers(cfg)

    for m in masks:

        if m.get('kind') not in ['dot','multiple','splotches']:raise ValueError('Unknown mask pattern')

        if not all(np.isfinite(m[k]) for k in ['z_mm','radius_mm','pitch_mm','count','angle_deg','x_mm','y_mm']):raise ValueError('Mask values must be finite')

        if not (m['z_mm']>0 and (cfg.get('path_samples') or m['z_mm']<cfg['detector_z_mm'])) or m['radius_mm']<=0 or m['pitch_mm']<=0 or not 1<=m['count']<=9 or m['count']!=int(m['count']):raise ValueError('Invalid mask dimensions or count')
        if any(a-.01<=m['z_mm']<=b+.01 for a,b in bounds):raise ValueError('Mask intersects optic; move mask plane')

    planes=sorted(m['z_mm'] for m in masks)

    if any(b-a<.01 for a,b in zip(planes,planes[1:])):raise ValueError('Mask planes need at least 0.01 mm separation')

    bounds.sort()

    if any(a<=0 or (not cfg.get('path_samples') and b>=cfg['detector_z_mm']) for a,b in bounds): raise ValueError('Optics must be between source and screen')
    if any(a[1]+.01>=b[0] for a,b in zip(bounds,bounds[1:])): raise ValueError('Optics axial envelopes overlap; increase separation or reduce tilt')





def simulate(cfg,backend='auto',source=None,cancel=None,outgoing=None,capture_exit=False):
    def check_cancel():
        if cancel is not None and cancel(): raise RuntimeError('Cancelled')
    check_cancel()
    if backend not in ['auto','cpu','cuda']: raise ValueError('Unknown compute backend')
    validate(cfg); started=time.perf_counter()
    rays=source_rays(cfg) if source is None else np.ascontiguousarray(source,dtype=np.float64)
    if rays.ndim!=2 or rays.shape[1]!=8 or not np.all(np.isfinite(rays)) or np.any(rays[:,7]<0): raise ValueError('Source must be finite N x 8 rays')
    if rays[:,7].sum()<=0: raise ValueError('Source power must be positive')
    if not np.allclose(np.linalg.norm(rays[:,3:6],axis=1),1.,atol=1e-6): raise ValueError('Source directions must be normalized')
    if outgoing is not None:
        hits=outgoing['hits'].copy();trace_z=outgoing['z'];actual=outgoing['backend'];fallback=outgoing['fallback'];triangles=outgoing['triangles'];trace_seconds=0.
        if cfg['detector_z_mm']<trace_z:raise ValueError('Outgoing rays cannot sample before the exit plane')
    else:
        check_cancel()
        meshes=[]
        for optic in cfg['optics']:
            check_cancel(); meshes.append(optic_mesh(optic))
        mesh=np.concatenate(meshes) if meshes else np.empty((0,3,3))
        from outgoing_rays import exit_plane
        exit_z=exit_plane(cfg)
        trace_z=exit_z if capture_exit and cfg['detector_z_mm']>=exit_z else cfg['detector_z_mm']
        tri,normals,nodes=bvh(mesh)
        mask=np.asarray([[{'dot':1,'multiple':2,'splotches':3}[m['kind']],m['z_mm'],m['radius_mm'],m['pitch_mm'],m['count'],np.deg2rad(m['angle_deg']),m['x_mm'],m['y_mm']]
            for m in sorted(mask_layers(cfg),key=lambda m:m['z_mm'])],dtype=np.float64).reshape(-1,8)
        args=(rays,tri,normals,nodes,trace_z,cfg['n550'],cfg['dispersion'],cfg['absorption_per_mm'],cfg['max_bounces'],cfg['seed'],mask)
        actual=backend; fallback=None; trace_start=time.perf_counter()
        batch=65536 if cancel is not None else len(rays)
        # Offset the seed to preserve each ray's stream when chunk-local i starts at 0.
        seed_stride=(747796405*pow(2891336453,-1,2**32)) % 2**32
        def cpu_batches():
            result=np.empty((len(rays),6),np.float64)
            for start in range(0,len(rays),batch):
                check_cancel();end=min(start+batch,len(rays))
                seed=(cfg['seed']+start*seed_stride) % 2**32
                result[start:end]=_cpu(rays[start:end],*args[1:9],seed,mask)
            return result
        if backend in ['auto','cuda']:
            try:
                check_cancel();kernel=gpu_kernel()
                from numba import cuda
                device_geometry=[cuda.to_device(x) for x in args[1:4]]
                device_mask=cuda.to_device(mask)
                hits=np.empty((len(rays),6),np.float64)
                for start in range(0,len(rays),batch):
                    check_cancel();end=min(start+batch,len(rays))
                    device_rays=cuda.to_device(rays[start:end])
                    out=cuda.device_array((end-start,6),dtype=np.float64)
                    seed=(cfg['seed']+start*seed_stride) % 2**32
                    kernel[(end-start+127)//128,128](device_rays,*device_geometry,*args[4:9],seed,device_mask,out)
                    hits[start:end]=out.copy_to_host()
                actual='cuda'
            except Exception as error:
                check_cancel()
                if backend=='cuda': raise
                fallback=str(error); hits=cpu_batches(); actual='cpu'
        else: hits=cpu_batches(); actual='cpu'
        check_cancel()
        trace_seconds=time.perf_counter()-trace_start
        triangles=len(tri)
    beam=None
    if capture_exit:
        from outgoing_rays import exit_plane
        if trace_z>=exit_plane(cfg):beam=dict(hits=hits.copy(),z=trace_z,backend=actual,fallback=fallback,triangles=triangles)
    arrived_at_exit=hits[:,3]==0
    travel=cfg['detector_z_mm']-trace_z
    hits[arrived_at_exit,0]+=hits[arrived_at_exit,4]*travel
    hits[arrived_at_exit,1]+=hits[arrived_at_exit,5]*travel

    size=cfg['detector_size_mm']; res=cfg['resolution']; total=float(rays[:,7].sum())
    arrived=hits[:,3]==0
    inframe=arrived&(abs(hits[:,0])<size/2)&(abs(hits[:,1])<size/2)
    hist=np.histogram2d(hits[inframe,1],hits[inframe,0],bins=res,range=[[-size/2,size/2]]*2,weights=hits[inframe,2])[0]
    fractions=dict(detected=float(hits[inframe,2].sum()/total),outside_detector=float(hits[arrived&~inframe,2].sum()/total),
                   escaped=float(hits[hits[:,3]==1,2].sum()/total),unresolved=float(hits[hits[:,3]==2,2].sum()/total),
                   masked=float(hits[hits[:,3]==3,2].sum()/total),absorbed=float(1-hits[:,2].sum()/total))
    detected_power=hits[inframe,2].sum()
    centroid=(hits[inframe,:2]*hits[inframe,2,None]).sum(0)/detected_power if detected_power>0 else np.zeros(2)
    metrics=dict(backend=actual,fallback=fallback,rays=len(rays),triangles=triangles,trace_seconds=trace_seconds,
                 total_seconds=time.perf_counter()-started,fractions=fractions,detected_fraction=fractions['detected'],
                 centroid_mm=centroid.tolist(),input_power_w=total)
    result=dict(irradiance=(hist/(size/res/1000)**2).astype(np.float32),metrics=metrics,config=copy.deepcopy(cfg))
    if cfg.get('color_preview'):
        from spectral import preview_rgb_weights
        # Bin the same traced spectral rays. RGB is appearance only; scalar power stays authoritative.
        colors=preview_rgb_weights(rays[inframe,6])
        rgba=np.ones((res,res,4),dtype=np.float32)
        for channel in range(3):
            check_cancel()
            rgba[:,:,channel]=np.histogram2d(hits[inframe,1],hits[inframe,0],bins=res,range=[[-size/2,size/2]]*2,
                weights=hits[inframe,2]*colors[:,channel])[0]/(size/res/1000)**2
        result['display_rgba']=rgba
    if cfg.get('path_samples'):
        ids=np.linspace(0,len(rays)-1,min(96,len(rays)),dtype=int)
        result['ray_samples']=[[int(i),float(hits[i,0]),float(hits[i,1]),float(rays[i,6])] for i in ids if arrived[i]]
    if beam is not None:result['_outgoing']=beam
    metrics['outgoing_reused']=outgoing is not None
    metrics['total_seconds']=time.perf_counter()-started
    return result
