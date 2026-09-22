"""Closed glass disc with an irregular, piecewise planar upper surface."""
import numpy as np
from scipy.spatial import Delaunay


def fractured_mesh(radius, thickness, pitch, depth):
    rng = np.random.default_rng(123)
    # Bounded complexity keeps interactive CPU/CUDA geometry builds manageable.
    count = min(1600, max(8, int(np.pi * (radius / pitch) ** 2)))
    boundary_count = 64
    angles = np.arange(boundary_count) * 2 * np.pi / boundary_count
    boundary = radius * np.column_stack((np.cos(angles), np.sin(angles)))
    angles = rng.uniform(0, 2 * np.pi, count)
    radii = radius * .97 * np.sqrt(rng.random(count))
    xy = np.vstack((boundary, np.column_stack((radii*np.cos(angles), radii*np.sin(angles)))))
    top = np.column_stack((xy, thickness + depth * rng.random(len(xy))))
    bottom = np.column_stack((xy, np.zeros(len(xy))))
    faces = []
    for indices in Delaunay(xy).simplices:
        a, b, c = indices
        faces.extend([[top[a], top[b], top[c]], [bottom[c], bottom[b], bottom[a]]])
    for a in range(boundary_count):
        b = (a + 1) % boundary_count
        faces.extend([[bottom[a], bottom[b], top[b]], [bottom[a], top[b], top[a]]])
    return np.asarray(faces)
