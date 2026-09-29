"""Run with blender --background --python-exit-code 1 --python tests/test_duplicate_parts.py."""
import bpy
import runpy
from pathlib import Path
from mathutils import Matrix, Vector

P = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'parca_sayim.py'))
assert 'prepare_unique_parts' in P, 'Missing duplicate-part preparation'
prepare = P['prepare_unique_parts']

def cube(name, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o = bpy.context.object
    o.name = name
    return o

def clone(o, name, delta=(0, 0, 0)):
    n = o.copy()
    n.data = o.data.copy()
    bpy.context.collection.objects.link(n)
    n.name = name
    n.location += Vector(delta)
    return n

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def run_pair(delta, expected):
    reset()
    a = cube('A', (3, 2, 1))
    b = clone(a, 'B', delta)
    kept, pairs = prepare([a, b])
    assert len(kept) == expected, (delta, len(kept))
    assert len(pairs) == 2 - expected

if not bpy.app.background:
    raise RuntimeError('This test resets the scene; run in a separate background Blender.')
run_pair((0, 0, 0), 1)
run_pair((0.00009, 0, 0), 1)
run_pair((0.00011, 0, 0), 2)
run_pair((1, 0, 0), 2)
# Relative tolerance must not depend on distance to world origin.
reset()
a = cube('A', (0, 0, 0)); b = clone(a, 'B', (0.00011, 0, 0))
assert len(prepare([a, b])[0]) == 2
# Different geometry at same center is preserved.
reset()
a = cube('A'); b = clone(a, 'B'); b.data.vertices[0].co.x += 0.05
assert len(prepare([a, b])[0]) == 2
# Origin changes and non-uniform scale do not move any world vertex or child.
reset()
a = cube('A', (3, 2, 1)); a.scale = (0.5, 2, 3)
bpy.context.view_layer.update()
b = clone(a, 'B')
b.data.transform(Matrix.Translation((4, 5, 6)))
b.matrix_world = b.matrix_world @ Matrix.Translation((-4, -5, -6))
child = bpy.data.objects.new('child', None); bpy.context.collection.objects.link(child)
child.parent = a; child.location = (1, 2, 3)
bpy.context.view_layer.update()
before = [a.matrix_world @ v.co for v in a.data.vertices]
child_before = child.matrix_world.copy()
kept, pairs = prepare([a, b])
assert len(kept) == 1
assert max((a.matrix_world @ v.co - w).length for v, w in zip(a.data.vertices, before)) < 1e-5
assert max(abs(child.matrix_world[i][j] - child_before[i][j]) for i in range(4) for j in range(4)) < 1e-5
# Different surface connectivity with the same vertex cloud is preserved.
reset()
a = cube('A'); b = clone(a, 'B')
coords = [tuple(v.co) for v in b.data.vertices]
faces = [tuple(p.vertices) for p in b.data.polygons][:-1]
m = bpy.data.meshes.new('open'); m.from_pydata(coords, [], faces); b.data = m
assert len(prepare([a, b])[0]) == 2
# Idempotence and triple copies.
reset()
a = cube('A'); b = clone(a, 'B'); c = clone(a, 'C')
kept, pairs = prepare([c, b, a]); assert len(kept) == 1 and len(pairs) == 2
assert prepare(kept)[1] == []
# Reordered vertices/faces represent the same mesh.
reset()
a = cube('A'); b = clone(a, 'B')
coords = [tuple(v.co) for v in a.data.vertices]
permutation = list(reversed(range(len(coords))))
inverse = {old: new for new, old in enumerate(permutation)}
faces = [tuple(inverse[i] for i in reversed(p.vertices)) for p in a.data.polygons]
m = bpy.data.meshes.new('reordered'); m.from_pydata([coords[i] for i in permutation], [], faces); b.data = m
assert len(prepare([a, b])[0]) == 1
print('PASS: duplicate parts, tolerance boundaries, distinct geometry, transforms, children, idempotence')
