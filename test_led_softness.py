import numpy as np
import pytest
import engine

def test_led_softness_spreads_edge_without_changing_power_or_seed():
    c=engine.defaults();c.update(rays=30000,led_softness=.25)
    soft=engine.source_rays(c)
    hard=engine.source_rays({**c,'led_softness':0})
    angle=np.arccos(soft[:,5])
    assert np.count_nonzero(angle>np.deg2rad(2.5))>1000
    assert np.array_equal(soft,engine.source_rays(c))
    assert np.array_equal(soft[:,:3],hard[:,:3])
    assert np.allclose(np.linalg.norm(soft[:,3:6],axis=1),1)
    assert soft[:,7].sum()==pytest.approx(c['optical_power_w'])
    assert np.array_equal(hard,engine.source_rays({k:v for k,v in c.items() if k!='led_softness'}))

def test_laser_is_unchanged_by_led_softness():
    c=engine.defaults();c.update(source_model='laser',rays=1000)
    assert np.array_equal(engine.source_rays(c),engine.source_rays({**c,'led_softness':1}))

@pytest.mark.parametrize('value',[-.1,1.1,float('nan')])
def test_invalid_softness_rejected(value):
    c=engine.defaults();c['led_softness']=value
    with pytest.raises(ValueError):engine.validate(c)
