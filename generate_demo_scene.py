"""Generate an original generic receiver: a cube on a floor (metres, Z up)."""
import gzip
import json
from pathlib import Path
import struct


def main():
    positions, normals = [], []

    def quad(a, b, c, d, normal):
        for vertex in (a, b, c, a, c, d):
            positions.extend(vertex)
            normals.extend(normal)

    quad((-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0), (0, 0, 1))
    quad((-.5, -.5, 0), (.5, -.5, 0), (.5, -.5, 1), (-.5, -.5, 1), (0, -1, 0))
    quad((.5, .5, 0), (-.5, .5, 0), (-.5, .5, 1), (.5, .5, 1), (0, 1, 0))
    quad((-.5, .5, 0), (-.5, -.5, 0), (-.5, -.5, 1), (-.5, .5, 1), (-1, 0, 0))
    quad((.5, -.5, 0), (.5, .5, 0), (.5, .5, 1), (.5, -.5, 1), (1, 0, 0))
    quad((-.5, -.5, 1), (.5, -.5, 1), (.5, .5, 1), (-.5, .5, 1), (0, 0, 1))
    assets = Path(__file__).parent / 'assets'
    assets.mkdir(exist_ok=True)
    for name, values in [('positions', positions), ('normals', normals)]:
        payload = struct.pack(f'<{len(values)}f', *values)
        (assets / f'demo-{name}.bin.gz').write_bytes(gzip.compress(payload, mtime=0))
    manifest = {
        'source': 'Generic cube and floor', 'units': 'm', 'up': 'Z',
        'positions_file': 'demo-positions.bin.gz', 'normals_file': 'demo-normals.bin.gz',
        'vertex_count': len(positions) // 3, 'triangle_count': len(positions) // 9,
        'bounds': {'min': [-2, -2, 0], 'max': [2, 2, 1]},
        'lights': {'recommended_projector': {'position': [0, -2, 1], 'target': [0, 0, .5]}},
    }
    (assets / 'demo-scene.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
