import numpy as np
import engine

def test_sparse_rays_follow_straight_free_space_and_preserve_map():
    c=engine.defaults()
    c.update(optics=[],rays=100,resolution=16,path_samples=True,detector_z_mm=100)
    a=engine.simulate(c,'cpu')
    c['detector_z_mm']=200
    b=engine.simulate(c,'cpu')
    source=engine.source_rays(c)
    for first,second in zip(a['ray_samples'],b['ray_samples']):
        i=int(first[0]);assert i==second[0]
        np.testing.assert_allclose(np.array(second[1:3])-first[1:3],100*source[i,3:5]/source[i,5],atol=1e-10)
    c.pop('path_samples')
    np.testing.assert_array_equal(b['irradiance'],engine.simulate(c,'cpu')['irradiance'])


def test_probe_before_optics_and_mask_is_not_blocked_by_downstream_layers():
    c=engine.defaults()
    c.update(rays=100,resolution=16,path_samples=True,detector_z_mm=5,
             masks=[dict(kind='dot',z_mm=20,radius_mm=.01,pitch_mm=1,count=1,angle_deg=0,x_mm=0,y_mm=0)])
    result=engine.simulate(c,'cpu')
    assert result['metrics']['detected_fraction']>.99
    assert len(result['ray_samples'])==96
