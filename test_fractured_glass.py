import numpy as np
from fractured_glass import fractured_mesh

def test_closed_oriented_surface_and_detail():
    mesh=fractured_mesh(13,2,2,1)
    edges={}
    for tri in mesh:
        for a,b in zip(tri,np.roll(tri,-1,axis=0)):
            a,b=tuple(a),tuple(b)
            key=tuple(sorted((a,b)))
            edges.setdefault(key,[]).append(1 if a<b else -1)
    assert all(len(v)==2 and sum(v)==0 for v in edges.values())
    assert mesh[:,:,2].min()==0
    assert 2<mesh[:,:,2].max()<=3
    assert len(fractured_mesh(13,2,1,1))>len(mesh)
    assert np.array_equal(mesh,fractured_mesh(13,2,2,1))
