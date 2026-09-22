import copy
import numpy as np
import pytest
import engine
from outgoing_rays import BeamCache,beam_key,encode,decode,exit_plane


@pytest.mark.parametrize('backend',['cpu','cuda'])
@pytest.mark.parametrize('kind',['prism','fractured','cylindrical'])
def test_reused_exit_rays_match_full_trace(backend,kind):
    c=engine.defaults();c.update(rays=2000,resolution=64,color_preview=True,dispersion=.004,wavelengths_nm=[450,550,638],spectral_weights=[1,1,1],path_samples=True)
    c['optics'][0].update(kind=kind,pitch_mm=4,depth_mm=.5)
    c['masks']=[dict(kind='dot',z_mm=20,radius_mm=7,pitch_mm=4,count=1,angle_deg=0,x_mm=0,y_mm=0)]
    first=engine.simulate(c,backend,capture_exit=True)
    beam=decode(encode(first['_outgoing']))
    for z in [100,300]:
        c['detector_z_mm']=z
        reused=engine.simulate(c,backend,outgoing=beam)
        full=engine.simulate(c,backend)
        np.testing.assert_allclose(reused['irradiance'],full['irradiance'],atol=1e-6)
        np.testing.assert_allclose(reused['display_rgba'],full['display_rgba'],atol=1e-6)
        np.testing.assert_allclose(reused['ray_samples'],full['ray_samples'],atol=1e-9)
        assert reused['metrics']['fractions']==full['metrics']['fractions']
    c['detector_z_mm']=exit_plane(c)-1
    with pytest.raises(ValueError):engine.simulate(c,backend,outgoing=beam)


def test_beam_cache_is_bounded_and_display_changes_reuse_key():
    c=engine.defaults();key=beam_key(c,'cuda','test')
    assert beam_key(c,'cpu','test')==key
    assert beam_key(c,'auto','test')==key
    changed={**c,'detector_z_mm':300,'resolution':128,'path_samples':True}
    assert beam_key(changed,'cuda','test')==key
    for field,value in [('rays',1234),('seed',123),('dispersion',.004)]:
        assert beam_key({**c,field:value},'cuda','test')!=key
    moved=copy.deepcopy(c);moved['optics'][0]['angle_deg']=15
    assert beam_key(moved,'cuda','test')!=key
    cache=BeamCache(limit=100);beam={'hits':np.zeros((1,6))}
    cache.put('a',beam);cache.put('b',beam);cache.get('a');cache.put('c',beam)
    assert cache.get('b') is None and cache.get('a') is beam and cache.size<=100
