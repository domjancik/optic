import numpy as np
import pytest
import engine

@pytest.mark.parametrize('kind',['linear_fresnel','crossed_prism','pyramid','ice','hammer','haircell'])
def test_surface_is_closed_deterministic_and_has_relief(kind):
    o=engine.defaults()['optics'][0];o.update(kind=kind,radius_mm=4,pitch_mm=2,depth_mm=.35,focal_mm=100,design_index=1.49)
    c=engine.defaults();c['optics']=[o];engine.validate(c)
    mesh=engine.optic_mesh(o)
    assert np.array_equal(mesh,engine.optic_mesh(o))
    assert np.isfinite(mesh).all()
    assert mesh[:,:,2].max()>o['z_mm']+o['thickness_mm']
    edges={}
    for face in mesh:
        for a,b in zip(face,np.roll(face,-1,axis=0)):
            key=tuple(sorted((tuple(np.round(a,9)),tuple(np.round(b,9)))))
            edges[key]=edges.get(key,0)+1
    assert set(edges.values())=={2}

def test_fresnel_focus_slopes_increase_toward_edge():
    from patterned_surfaces import fresnel_slope
    assert fresnel_slope(0,100,1.49)==0
    assert fresnel_slope(8,100,1.49)<fresnel_slope(4,100,1.49)<0
    slope=fresnel_slope(8,100,1.49)
    ray=engine.interface(np.array([0.,0.,1.]),np.array([-slope,0.,1.])/np.sqrt(1+slope*slope),1.49,1.)
    # Analytic normal obeys Snell; compare independently via angle equation.
    alpha=np.arctan(-slope)
    assert np.isclose(np.arcsin(1.49*np.sin(alpha))-alpha,np.arctan(8/100))

@pytest.mark.parametrize('kind',['linear_fresnel','crossed_prism','pyramid','ice','hammer','haircell'])
def test_new_surfaces_have_depth_preview(kind):
    from surface_map import surface_map
    o=engine.defaults()['optics'][0];o.update(kind=kind,radius_mm=4,focal_mm=100,design_index=1.49)
    result=surface_map(o,16)
    assert result['max_mm']>result['min_mm']
    if kind=='linear_fresnel':
        assert result!=surface_map({**o,'focal_mm':200},16)

@pytest.mark.parametrize('backend',['cpu','cuda'])
@pytest.mark.parametrize('kind',['linear_fresnel','crossed_prism','pyramid','ice','hammer','haircell'])
def test_new_surface_transport_cpu_and_cuda(kind,backend):
    c=engine.defaults();c.update(rays=1000,resolution=32,detector_z_mm=110.,detector_size_mm=200.,source_radius_mm=3.,divergence_deg=0.)
    c['optics'][0].update(kind=kind,radius_mm=4,pitch_mm=1,depth_mm=.35,focal_mm=100,design_index=1.49)
    r=engine.simulate(c,backend)
    assert np.isfinite(r['irradiance']).all()
    assert r['metrics']['detected_fraction']>0

@pytest.mark.parametrize('kind',['pyramid','crossed_prism','prism'])
@pytest.mark.parametrize('pitch',[.5,1.])
def test_fine_planar_facets_are_supported_and_efficient(kind,pitch):
    o=engine.defaults()['optics'][0];o.update(kind=kind,pitch_mm=pitch,depth_mm=.15)
    c=engine.defaults();c['optics']=[o];engine.validate(c)
    mesh=engine.optic_mesh(o)
    assert len(mesh)<45000
    normals=np.cross(mesh[:,1]-mesh[:,0],mesh[:,2]-mesh[:,0]);normals/=np.linalg.norm(normals,axis=1)[:,None]
    top=normals[normals[:,2]>.01]
    slopes=np.round(top[:,:2]/top[:,2,None],6)
    assert len(np.unique(slopes,axis=0))<=(2 if kind=='prism' else 4)
