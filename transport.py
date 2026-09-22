"""Shared scalar light transport compiled for CPU or CUDA; lengths in mm."""
import math


def compile_transport(device):
    @device
    def bend(dx,dy,dz,nx,ny,nz,ni,nt):
        c=-(dx*nx+dy*ny+dz*nz)
        c=min(1.,max(0.,c)); eta=ni/nt
        k=1.-eta*eta*(1.-c*c)
        if k <= 0.: return dx+2*c*nx,dy+2*c*ny,dz+2*c*nz,1.
        ct=math.sqrt(k)
        rs=(ni*c-nt*ct)/(ni*c+nt*ct)
        rp=(nt*c-ni*ct)/(nt*c+ni*ct)
        a=eta*c-ct
        return eta*dx+a*nx,eta*dy+a*ny,eta*dz+a*nz,.5*(rs*rs+rp*rp)

    @device
    def trace(i, rays, triangles, normals, nodes, screen_z, n550, dispersion, absorption, depth, seed, mask):
        ox,oy,oz=rays[i,0],rays[i,1],rays[i,2]
        dx,dy,dz=rays[i,3],rays[i,4],rays[i,5]
        power=rays[i,7]; wavelength=rays[i,6]/1000.
        index=n550+dispersion*(1./(wavelength*wavelength)-1./(.55*.55))
        inside=False
        state=(i*747796405+seed*2891336453+1)&0xffffffff
        for bounce in range(depth):
            nearest=1.e30; hit=-1; node=0
            while node < len(nodes):
                lo=0.; hi=nearest
                for axis in range(3):
                    origin=ox if axis==0 else oy if axis==1 else oz
                    direction=dx if axis==0 else dy if axis==1 else dz
                    if abs(direction)<1.e-14:
                        if origin<nodes[node,axis] or origin>nodes[node,axis+3]: hi=-1.
                    else:
                        a=(nodes[node,axis]-origin)/direction
                        b=(nodes[node,axis+3]-origin)/direction
                        lo=max(lo,min(a,b)); hi=min(hi,max(a,b))
                if hi<lo:
                    node=int(nodes[node,8]); continue
                start=int(nodes[node,6]); count=int(nodes[node,7])
                for j in range(start,start+count):
                    ax,ay,az=triangles[j,0,0],triangles[j,0,1],triangles[j,0,2]
                    ex,ey,ez=triangles[j,1,0]-ax,triangles[j,1,1]-ay,triangles[j,1,2]-az
                    fx,fy,fz=triangles[j,2,0]-ax,triangles[j,2,1]-ay,triangles[j,2,2]-az
                    px,py,pz=dy*fz-dz*fy,dz*fx-dx*fz,dx*fy-dy*fx
                    det=ex*px+ey*py+ez*pz
                    if abs(det)<1.e-12: continue
                    tx,ty,tz=ox-ax,oy-ay,oz-az
                    u=(tx*px+ty*py+tz*pz)/det
                    if u<0. or u>1.: continue
                    qx,qy,qz=ty*ez-tz*ey,tz*ex-tx*ez,tx*ey-ty*ex
                    v=(dx*qx+dy*qy+dz*qz)/det
                    if v<0. or u+v>1.: continue
                    t=(fx*qx+fy*qy+fz*qz)/det
                    if t>1.e-5 and t<nearest: nearest=t; hit=j
                node+=1
            target=(screen_z-oz)/dz if dz>1.e-12 else -1.
            # Test each mask crossed by this free-space segment. Open apertures
            # do not consume the reflection/refraction bounce budget.
            for layer in range(len(mask)):
                mt=(mask[layer,1]-oz)/dz if abs(dz)>1.e-12 else -1.
                if mask[layer,0]>0 and mt>1.e-5 and mt<nearest and (target<=0. or mt<target) and not inside:
                    mx=ox+mt*dx-mask[layer,6]; my=oy+mt*dy-mask[layer,7]
                    ca=math.cos(mask[layer,5]);sa=math.sin(mask[layer,5]);x=mx*ca+my*sa;y=-mx*sa+my*ca
                    opened=False
                    count=int(mask[layer,4]) if mask[layer,0]>1 else 1
                    for row in range(count):
                        for col in range(count):
                            cx=(col-(count-1)*.5)*mask[layer,3];cy=(row-(count-1)*.5)*mask[layer,3]
                            xx=x-cx;yy=y-cy;radius=mask[layer,2]
                            if mask[layer,0]==3:
                                phase=col*2.31+row*4.17
                                xx-=mask[layer,3]*.16*math.sin(phase);yy-=mask[layer,3]*.16*math.cos(phase*1.3)
                                theta=math.atan2(yy,xx)
                                radius*=1.+.23*math.sin(3*theta+phase)+.14*math.cos(5*theta-phase)
                            if xx*xx+yy*yy<=radius*radius:opened=True
                    if not opened:return 0.,0.,power,3,0.,0.
            target=(screen_z-oz)/dz if dz>1.e-12 else -1.
            if target>0. and target<nearest and not inside:
                return ox+target*dx,oy+target*dy,power,0,dx/dz,dy/dz
            if hit<0: return 0.,0.,power,2 if inside else 1,0.,0.
            if inside: power*=math.exp(-absorption*nearest)
            ox+=nearest*dx; oy+=nearest*dy; oz+=nearest*dz
            nx,ny,nz=normals[hit,0],normals[hit,1],normals[hit,2]
            entering=dx*nx+dy*ny+dz*nz<0.
            if not entering: nx=-nx; ny=-ny; nz=-nz
            ni=1. if entering else index; nt=index if entering else 1.
            bx,by,bz,r=bend(dx,dy,dz,nx,ny,nz,ni,nt)
            state=(1664525*state+1013904223)&0xffffffff
            if state/4294967296.<r:
                c=dx*nx+dy*ny+dz*nz
                dx-=2*c*nx; dy-=2*c*ny; dz-=2*c*nz
            else:
                dx,dy,dz=bx,by,bz; inside=entering
            ox+=2.e-5*dx; oy+=2.e-5*dy; oz+=2.e-5*dz
        return 0.,0.,power,2,0.,0.
    return bend,trace
