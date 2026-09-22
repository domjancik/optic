"""Generic relief models, not measured manufacturer surface profiles."""
import math
import numpy as np
from scipy.spatial import Delaunay
from scipy.ndimage import gaussian_filter, map_coordinates

KINDS=('linear_fresnel','crossed_prism','pyramid','ice','hammer','haircell')

def fresnel_slope(x,f,n):
    theta=math.atan2(x,f)
    return -math.sin(theta)/(n-math.cos(theta))

def fresnel_mesh(o):
    r,t,p,d=o['radius_mm'],o['thickness_mm'],o['pitch_mm'],o['depth_mm']
    f,n=o.get('focal_mm',300.),o.get('design_index',1.49)
    if not np.isfinite(f) or f<=0 or not np.isfinite(n) or not 1<n<3:
        raise ValueError('Fresnel focal length must be positive; design index must be 1..3')
    edges=np.unique(np.r_[-r,np.arange(math.ceil(-r/p),math.floor(r/p)+1)*p,r])
    profile=[]
    for a,b in zip(edges[:-1],edges[1:]):
        slope=fresnel_slope((a+b)/2,f,n)
        relief=abs(slope)*(b-a)
        if relief>d+1e-9:raise ValueError('Fresnel relief allowance too small; increase relief or reduce groove pitch')
        profile.extend([(a,max(0,-slope*(b-a))),(b,max(0,slope*(b-a)))])
    # Extrude the stepped profile along Y, clipping each column to the disc.
    v=[]
    for x,h in profile:
        y=math.sqrt(max(0,r*r-x*x));v.append([[x,-y,0],[x,y,0],[x,-y,t+h],[x,y,t+h]])
    faces=[]
    for a,b in zip(np.asarray(v)[:-1],np.asarray(v)[1:]):
        faces.extend([[a[2],b[2],b[3]],[a[2],b[3],a[3]],[a[0],b[1],b[0]],[a[0],a[1],b[1]],
                      [a[0],b[0],b[2]],[a[0],b[2],a[2]],[a[1],a[3],b[3]],[a[1],b[3],b[1]]])
    mesh=np.asarray(faces)
    area=np.linalg.norm(np.cross(mesh[:,1]-mesh[:,0],mesh[:,2]-mesh[:,0]),axis=1)
    mesh=mesh[area>1e-10]
    # Split side-wall T junctions at groove reset heights for a watertight mesh.
    points=np.unique(mesh.reshape(-1,3),axis=0)
    pending=list(mesh);closed=[]
    while pending:
        face=pending.pop();split=False
        for i in range(3):
            a,b,c=face[i],face[(i+1)%3],face[(i+2)%3]
            delta=b-a;length=np.dot(delta,delta)
            q=(points-a)@delta/length
            valid=(q>1e-8)&(q<1-1e-8)&(np.linalg.norm(points-a-q[:,None]*delta,axis=1)<1e-9)
            if np.any(valid):
                v=points[np.flatnonzero(valid)[0]]
                pending.extend([np.array([a,v,c]),np.array([v,b,c])]);split=True;break
        if not split:closed.append(face)
    return np.asarray(closed)

def patterned_mesh(o):
    if o['kind']=='linear_fresnel':return fresnel_mesh(o)
    if o['kind'] in ('pyramid','crossed_prism'):return planar_array_mesh(o)
    r,t,p,d=o['radius_mm'],o['thickness_mm'],o['pitch_mm'],o['depth_mm']
    # Preserve sufficient samples per feature; reject rather than silently alias detail.
    if r/p>12:raise ValueError('Texture pitch too small for this aperture; use radius/pitch <= 12')
    step=p/8
    axis=np.arange(math.ceil(-r/step),math.floor(r/step)+1)*step
    xx,yy=np.meshgrid(axis,axis);xy=np.column_stack((xx.ravel(),yy.ravel()))
    xy=xy[np.linalg.norm(xy,axis=1)<r-step*.15]
    angle=np.arange(192)*2*np.pi/192
    boundary=r*np.column_stack((np.cos(angle),np.sin(angle)))
    xy=np.vstack((boundary,xy));x,y=xy.T
    tx=1-2*np.abs((x/p+.5)%1-.5);ty=1-2*np.abs((y/p+.5)%1-.5)
    kind=o['kind']
    if kind=='crossed_prism':h=(tx+ty)/2
    elif kind=='pyramid':h=np.minimum(tx,ty)
    else:
        rng=np.random.default_rng(123)
        # Seeded correlated relief: hammer is rounded, ice has sharper detail,
        # hair-cell has short elongated grain. No unmeasured BSDF haze is added.
        noise=rng.random((256,256))
        scale=256*p/(2*r)
        sigma=(scale*.06,scale*.35) if kind=='haircell' else scale*(.12 if kind=='ice' else .3)
        field=gaussian_filter(noise,sigma=sigma,mode='reflect')
        field=(field-field.min())/(field.max()-field.min())
        h=map_coordinates(field,[(y/r+1)*127.5,(x/r+1)*127.5],order=1)
    top=np.column_stack((xy,t+d*h));bottom=np.column_stack((xy,np.zeros(len(xy))))
    faces=[]
    for a,b,c in Delaunay(xy).simplices:
        faces.extend([[top[a],top[b],top[c]],[bottom[c],bottom[b],bottom[a]]])
    for a in range(192):
        b=(a+1)%192;faces.extend([[bottom[a],bottom[b],top[b]],[bottom[a],top[b],top[a]]])
    return np.asarray(faces)

def planar_array_mesh(o):
    """Exact planar facets clipped to a polygonal circular aperture."""
    r,p,t,d=o['radius_mm'],o['pitch_mm'],o['thickness_mm'],o['depth_mm']
    if r/p>40:raise ValueError('Planar array needs radius/pitch <= 40')
    angles=np.arange(128)*2*np.pi/128
    boundary=r*np.column_stack((np.cos(angles),np.sin(angles)))
    inward=np.roll(boundary,-1,axis=0)-boundary
    normals=np.column_stack((-inward[:,1],inward[:,0]))
    normals/=np.linalg.norm(normals,axis=1)[:,None]
    offsets=np.sum(normals*boundary,axis=1)
    top=[]
    def emit(points):
        poly=np.array(points,float)
        if np.all(np.linalg.norm(poly[:,:2],axis=1)<r*np.cos(np.pi/128)):
            top.append(poly);return
        for normal,offset in zip(normals,offsets):
            dist=poly[:,:2]@normal-offset
            if np.all(dist>=-1e-10):continue
            if np.all(dist<0):return
            clipped=[]
            for i,a in enumerate(poly):
                b=poly[(i+1)%len(poly)];da,db=dist[i],dist[(i+1)%len(poly)]
                if da>=0:clipped.append(a)
                if (da>=0)!=(db>=0):clipped.append(a+(b-a)*da/(da-db))
            poly=np.array(clipped)
            if len(poly)<3:return
        for i in range(1,len(poly)-1):
            tri=poly[[0,i,i+1]]
            if np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))>1e-10:top.append(tri)
    if o['kind']=='pyramid':
        count=math.ceil(r/p+.5)
        for ix in range(-count,count+1):
            for iy in range(-count,count+1):
                x,y=ix*p,iy*p
                if math.hypot(max(0,abs(x)-p/2),max(0,abs(y)-p/2))>r:continue
                corners=[[x-p/2,y-p/2,t],[x+p/2,y-p/2,t],[x+p/2,y+p/2,t],[x-p/2,y+p/2,t]]
                for i in range(4):emit([corners[i],corners[(i+1)%4],[x,y,t+d]])
    else:
        step=p/2;count=math.ceil(r/step)
        def point(ix,iy):return [ix*step,iy*step,t+d*((1-abs(ix%2))+(1-abs(iy%2)))/2]
        for ix in range(-count,count):
            for iy in range(-count,count):
                a,b,c,e=point(ix,iy),point(ix+1,iy),point(ix+1,iy+1),point(ix,iy+1)
                if math.hypot(max(0,abs((ix+.5)*step)-step/2),max(0,abs((iy+.5)*step)-step/2))>r:continue
                emit([a,b,c]);emit([a,c,e])
    top=np.round(np.asarray(top),10)
    bottom=top[:,[2,1,0]].copy();bottom[:,:,2]=0
    edges={}
    for face in top:
        for a,b in zip(face,np.roll(face,-1,axis=0)):
            key=tuple(sorted((tuple(a),tuple(b))))
            if key in edges:del edges[key]
            else:edges[key]=(a,b)
    sides=[]
    for a,b in edges.values():
        lowa=a.copy();lowa[2]=0;lowb=b.copy();lowb[2]=0
        sides.extend([[lowa,lowb,b],[lowa,b,a]])
    return np.concatenate((top,bottom,np.asarray(sides)))
