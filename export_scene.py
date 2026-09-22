"""Export continuous visible custom receiver geometry as binary triangles.

Run from this directory (Blender is never asked to save the source file)::

    blender --background --disable-autoexec your-scene.blend --python export_scene.py -- --output assets/demo-scene.json

The export evaluates the saved scene at a static authored frame.  Mesh, curve,
surface, font, and meta objects that are visible to the renderer are converted
to triangles; cameras, lights, empties, and volume-only objects are excluded.
All evaluated triangles are retained. The manifest stays compact by streaming
world-space float32 position and normal buffers into sibling ``.bin.gz`` files;
no uncompressed buffer file is written. The source .blend is never written.
"""

import argparse
from array import array
import gzip
import hashlib
import json
import math
import os
import sys

import bpy
from mathutils import Matrix


DEFAULT_FRAME = 1
DEFAULT_MAX_TRIANGLES = 0
GEOMETRY_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}
CONTENT_BOUNDS_EXCLUDED_NAMES = set()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=os.path.join("assets", "demo-scene.json"))
    parser.add_argument("--frame", type=int, default=DEFAULT_FRAME)
    parser.add_argument(
        "--max-triangles",
        type=int,
        default=DEFAULT_MAX_TRIANGLES,
        help="Optional safety assertion; zero exports every evaluated triangle (default).",
    )
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def visible_geometry(scene):
    """Return render-visible geometry that can form physical receivers."""
    return [
        obj
        for obj in scene.objects
        if obj.type in GEOMETRY_TYPES
        and not is_volume_only(obj)
        and not obj.hide_render
        and not obj.hide_get()
        and obj.visible_get()
    ]


def is_volume_only(obj):
    """Exclude a mesh used solely as the container for a volume shader."""
    materials = [slot.material for slot in obj.material_slots if slot.material]
    if not materials:
        return False
    for material in materials:
        if not material.use_nodes or not material.node_tree:
            return False
        outputs = [node for node in material.node_tree.nodes if node.type == "OUTPUT_MATERIAL"]
        if not outputs:
            return False
        has_volume = any(output.inputs["Volume"].is_linked for output in outputs)
        has_surface = any(output.inputs["Surface"].is_linked for output in outputs)
        if has_surface or not has_volume:
            return False
    return True


def evaluated_mesh(obj, depsgraph):
    """Create a disposable evaluated mesh; no source datablocks are changed."""
    return bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)


def triangle_count(obj, depsgraph):
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
    mesh.calc_loop_triangles()
    count = len(mesh.loop_triangles)
    bpy.data.meshes.remove(mesh)
    return count


def extend_bounds(bounds, point):
    for axis, value in enumerate(point):
        bounds[0][axis] = min(bounds[0][axis], value)
        bounds[1][axis] = max(bounds[1][axis], value)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_gzip_float32(path, values):
    """Stream a float32 buffer to gzip without making an uncompressed file."""
    digest = hashlib.sha256()
    raw_bytes = 0
    floats_per_chunk = 3 * 65_536
    with gzip.open(path, "wb", compresslevel=6) as handle:
        for start in range(0, len(values), floats_per_chunk):
            chunk = array("f", values[start : start + floats_per_chunk]).tobytes()
            handle.write(chunk)
            digest.update(chunk)
            raw_bytes += len(chunk)
    return {
        "uncompressed_bytes": raw_bytes,
        "float32_sha256": digest.hexdigest(),
        "gzip_sha256": sha256_file(path),
    }


def export_object(obj, depsgraph, positions, normals, bounds, content_bounds):
    mesh = evaluated_mesh(obj, depsgraph)
    try:
        mesh.calc_loop_triangles()
        world = obj.matrix_world.copy()
        normal_matrix = world.to_3x3().inverted_safe().transposed()
        reverse = world.to_3x3().determinant() < 0.0
        count = 0
        for triangle in mesh.loop_triangles:
            loops = list(triangle.loops)
            if reverse:
                loops[1], loops[2] = loops[2], loops[1]
            for loop_index in loops:
                loop = mesh.loops[loop_index]
                vertex = mesh.vertices[loop.vertex_index]
                point = world @ vertex.co
                normal = (normal_matrix @ loop.normal).normalized()
                positions.extend((point.x, point.y, point.z))
                normals.extend((normal.x, normal.y, normal.z))
                extend_bounds(bounds, point)
                if obj.name not in CONTENT_BOUNDS_EXCLUDED_NAMES:
                    extend_bounds(content_bounds, point)
            count += 1
        return count
    finally:
        bpy.data.meshes.remove(mesh)


def main():
    args = parse_args()
    if args.max_triangles < 0:
        raise ValueError("--max-triangles cannot be negative")

    scene = bpy.context.scene
    scene.frame_set(args.frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = visible_geometry(scene)
    raw_counts = [(obj, triangle_count(obj, depsgraph)) for obj in objects]
    raw_total = sum(count for _, count in raw_counts)
    if args.max_triangles and raw_total > args.max_triangles:
        raise RuntimeError(
            f"Scene has {raw_total} evaluated triangles, above --max-triangles={args.max_triangles}; "
            "refusing to create a holey sampled receiver mesh."
        )

    positions, normals = array("f"), array("f")
    bounds = [[math.inf, math.inf, math.inf], [-math.inf, -math.inf, -math.inf]]
    content_bounds = [[math.inf, math.inf, math.inf], [-math.inf, -math.inf, -math.inf]]
    exported_objects = []
    for obj, raw_count in raw_counts:
        if not raw_count:
            continue
        count = export_object(obj, depsgraph, positions, normals, bounds, content_bounds)
        if count:
            exported_objects.append({"name": obj.name, "triangles": count})

    if not exported_objects:
        raise RuntimeError("No visible receiver triangles were found")
    if not math.isfinite(content_bounds[0][0]):
        content_bounds = bounds

    output = os.path.abspath(args.output)
    output_dir = os.path.dirname(output)
    os.makedirs(output_dir, exist_ok=True)
    positions_path = os.path.join(output_dir, "demo-positions.bin.gz")
    normals_path = os.path.join(output_dir, "demo-normals.bin.gz")
    position_buffer = write_gzip_float32(positions_path, positions)
    normal_buffer = write_gzip_float32(normals_path, normals)
    with open(bpy.data.filepath, "rb") as handle:
        source_digest = hashlib.sha256(handle.read()).hexdigest()
    centre_x = (content_bounds[0][0] + content_bounds[1][0]) / 2.0
    centre_y = (content_bounds[0][1] + content_bounds[1][1]) / 2.0
    projector_z = content_bounds[0][2] + 0.15
    roof_z = content_bounds[1][2] - 0.15
    data = {
        "positions_file": os.path.basename(positions_path),
        "normals_file": os.path.basename(normals_path),
        "format": "float32-le gzip, flat xyz per triangle vertex",
        "vertex_count": len(positions) // 3,
        "triangle_count": len(positions) // 9,
        "bounds": {"min": bounds[0], "max": bounds[1]},
        "content_bounds": {"min": content_bounds[0], "max": content_bounds[1]},
        "objects": exported_objects,
        "source": os.path.basename(bpy.data.filepath),
        "frame": {"number": args.frame, "fps": scene.render.fps, "frame_start": scene.frame_start, "frame_end": scene.frame_end},
        "units": "m",
        "up": "Z",
        "lights": {
            "recommended_projector": {
                "position": [centre_x, centre_y, projector_z],
                "target": [centre_x, centre_y, roof_z],
                "purpose": "Generic centre-near-floor projector aimed upward through the content bounds.",
            }
        },
        "checksums": {
            "algorithm": "sha256",
            "source_blend": source_digest,
            "positions": position_buffer,
            "normals": normal_buffer,
        },
    }
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(data, handle, separators=(",", ":"), allow_nan=False)
    print(
        f"EXPORTED triangles={len(positions) // 9} raw_triangles={raw_total} "
        f"objects={len(exported_objects)} output={output}"
    )


if __name__ == "__main__":
    main()
