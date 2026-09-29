"""Hole scan for the module segmenter (Blender side).

Per 18 mm board: cavities via the double-boolean trick (fbx-preprocessor
``blender.holes``), family by ``parca_sayim`` volume bands, and the mount-frame
direction ("mouth") from ``blender.orient``. Per hardware part: the mesh volume in
mm3, so handles can be recognised by volume as well as by bounding box.

World geometry is never changed: the board's mesh datablock is *copied* and
re-expressed in the board's own plate frame before the boolean, and the object's
``matrix_world`` is compensated so every vertex stays where it was. The source FBX
is not touched. Ported from ``Efforts/otonom_kit/2026-09-09-son-50-modul-incelemesi/
siparisleri_incele.py::tara`` (2026-09-09), which measured the 62-order corpus.
"""
import sys, time
from collections import defaultdict
import bpy, bmesh, mathutils

sys.path.insert(0, '/home/rocket/Jupiter/Projects/otonom_kit')
sys.path.insert(0, '/home/rocket/Jupiter/Projects/fbx-preprocessor/src')
import parca_sayim as sayim
from blender import holes as delikler, orient

SCANNED_THICKNESSES = (18.0,)
THICKNESS_TOL = 0.35
ORIENTED_FAMILIES = ('linco', 'pim', 'rafpimi', 'menteseTabani', 'modulbaglanti', 'tipa')


def plate_frame(o):
    """Panel basis from the largest flat face normal (u, v in-plane, n = normal)."""
    areas = defaultdict(float)
    for poly in o.data.polygons:
        n = poly.normal.copy()
        if n.length < .9:
            continue
        k = max(range(3), key=lambda i: abs(n[i]))
        if n[k] < 0:
            n = -n
        areas[tuple(round(x, 5) for x in n)] += poly.area
    if not areas:
        return None
    normals = sorted(areas, key=areas.get, reverse=True)
    n = mathutils.Vector(normals[0]).normalized()
    u = None
    for q in normals[1:]:
        q = mathutils.Vector(q)
        if abs(q.dot(n)) < .001:
            u = (q - n * q.dot(n)).normalized(); break
    if u is None:
        axis = min(range(3), key=lambda i: abs(n[i]))
        q = mathutils.Vector(tuple(1 if i == axis else 0 for i in range(3)))
        u = (q - n * q.dot(n)).normalized()
    v = n.cross(u).normalized()
    basis = mathutils.Matrix((u, v, n)).transposed()
    pts = [basis.transposed() @ x.co for x in o.data.vertices]
    low = mathutils.Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    high = mathutils.Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    dims = high - low
    axes = o.matrix_world.to_3x3() @ basis
    world_dims = [dims[i] * axes.col[i].length * 1000 for i in range(3)]
    return basis, world_dims


def mesh_volume_mm3(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.transform(o.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    v = abs(bm.calc_volume()) * 1e9
    bm.free()
    return v


def scan_part(o):
    """Holes of one mesh object; hardware gets its volume instead."""
    rec = dict(name=o.name, holes=[], volume_mm3=None, status='')
    frame = plate_frame(o)
    if frame is None:
        rec['status'] = 'no_flat_face'; return rec
    basis, dims = frame
    thickness = dims[2]
    rec['plate_thickness_mm'] = round(thickness, 4)
    if min(abs(thickness - t) for t in SCANNED_THICKNESSES) > THICKNESS_TOL:
        rec['status'] = 'thin_or_hardware'
        rec['volume_mm3'] = round(mesh_volume_mm3(o), 3)
        return rec
    o.data = o.data.copy()
    original_world = o.matrix_world.copy()
    o.parent = None
    o.data.transform(basis.transposed().to_4x4())
    o.matrix_world = original_world @ basis.to_4x4()
    bpy.context.view_layer.update()
    vmin, vmax = delikler.local_bounds(o)
    start = time.monotonic()
    cs = []
    before = {ob.name for ob in bpy.data.objects}
    try:
        cs = delikler.extract_cavities(o)
        for c in cs:
            family = sayim.match_category(c.volume_mm3)
            if family is None and sayim.is_ray_hole(c.volume_mm3):
                family = 'ray'
            if family is None and sayim.agac_vidasi_degisken_mi(c.obj, c.volume_mm3):
                family = 'agacvidasiDegisken'
            h = dict(family=family, volume_mm3=round(c.volume_mm3, 4),
                     dims_local_mm=[round(x, 3) for x in c.dim],
                     centre_world_mm=[round(x, 3) for x in (o.matrix_world @ c.centre) * 1000],
                     mouth_world=None)
            if family in ORIENTED_FAMILIES:
                try:
                    fam = 'mentese' if family == 'menteseTabani' else family
                    ori = orient.orient_cavity(o, vmin, vmax, c, fam)
                    r = o.matrix_world.to_3x3()
                    h['mouth_world'] = [round(x, 4) for x in (r @ ori.z_dir).normalized()]
                    h['orientation_rule'] = ori.rule
                except Exception as exc:
                    h['orientation_error'] = str(exc)
            rec['holes'].append(h)
        rec['status'] = 'scanned'
    except Exception as exc:
        rec['status'] = 'scan_error'; rec['error'] = str(exc)
    finally:
        delikler.discard(cs)
        # A failed boolean can leave prisms/plugs behind; they must never reach a render.
        for ob in [ob for ob in bpy.data.objects if ob.name not in before]:
            bpy.data.objects.remove(ob, do_unlink=True)
    rec['seconds'] = round(time.monotonic() - start, 3)
    return rec


def scan(meshes):
    """{name: hole list}, {name: volume_mm3 or None}, [records]."""
    records = [scan_part(o) for o in meshes]
    holes = {r['name']: r['holes'] for r in records}
    volumes = {r['name']: r['volume_mm3'] for r in records}
    return holes, volumes, records
