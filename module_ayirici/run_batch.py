"""Batch module-segmentation runner over real order FBX files (Blender -b).

Usage:
  MODUL_OUTPUT_DIR=<dir> blender -b --factory-startup -noaudio \
      --python-exit-code 1 --python run_batch.py -- <stem> [<stem> ...]

Env:
  MODUL_OUTPUT_DIR  required output directory (created if missing)
  MODUL_SAVE_BLEND  "1" to also save a coloured .blend per order
  MODUL_FBX_DIR     override source FBX directory
  MODUL_HOLES       "0" to skip the v0.5 hole scan / panel roles (default "1")
  MODUL_RENDER      "0" to write JSON only, no PNG renders (default "1")

Never modifies the source FBX; the SHA-256 is checked before and after.
Each order is isolated: an exception is recorded and the batch continues.
"""
import sys, os, json, time, hashlib, traceback
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, '/home/rocket/Jupiter/Projects/otonom_kit')
import bpy
from mathutils import Vector
from module_segmenter import segment, measure
from parca_sayim import prepare_unique_parts
import hole_scan, panel_roles

FBX_DIR = Path(os.environ.get('MODUL_FBX_DIR', '/home/rocket/Belgeler/Capcut/siparişler fbx'))
PALETTE = [(.1,.5,.95,1),(.15,.75,.3,1),(.95,.35,.1,1),(.65,.2,.9,1),(.95,.75,.1,1),
           (.1,.85,.85,1),(.9,.45,.7,1),(.55,.55,.2,1)]


def display(result, objects):
    collection = bpy.data.collections.get('MODUL_ADAYLARI')
    if collection is None:
        collection = bpy.data.collections.new('MODUL_ADAYLARI')
        bpy.context.scene.collection.children.link(collection)
    for old in list(collection.objects):
        if old.get('_modul_marker'):
            bpy.data.objects.remove(old, do_unlink=True)
    for o in objects:
        o.hide_set(False); o.hide_render = False
        a = result['assignment'].get(o.name)
        o.color = PALETTE[(int(a['module'][1:]) - 1) % len(PALETTE)] if a else (.9,.04,.08,1)
        o['modul_adayi'] = a['module'] if a else 'COZULMEDI'
        o['atama_gerekcesi'] = a['reason'] if a else result['unresolved'][o.name]['reason']
    for i, c in enumerate(result['boundaries'], 1):
        axis = c['axis']; others = [k for k in range(3) if k != axis]
        center = Vector((0,0,0)); size = Vector((.001,.001,.001)); center[axis] = c['plane_mm']/1000
        for j, k in enumerate(others):
            center[k] = (c['lo_mm'][j] + c['hi_mm'][j]) / 2000
            size[k] = (c['hi_mm'][j] - c['lo_mm'][j]) / 2000
        mark = bpy.data.objects.new('Temas_%02d_%s_%s' % (i, c['modules'][0], c['modules'][1]), None)
        collection.objects.link(mark)
        mark.empty_display_type = 'CUBE'; mark.empty_display_size = 1
        mark.location = center; mark.scale = size; mark.show_in_front = True
        bpy.context.view_layer.update()
        world = mark.matrix_world.copy()
        mark.parent = bpy.data.objects[c['a']]
        mark.matrix_parent_inverse = mark.parent.matrix_world.inverted()
        mark.matrix_world = world
        mark['_modul_marker'] = True; mark['diger_parca'] = c['b']; mark['temas_alani_mm2'] = c['area_mm2']
    return collection


def setup_camera(meshes, direction):
    points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    lo = Vector([min(p[k] for p in points) for k in range(3)])
    hi = Vector([max(p[k] for p in points) for k in range(3)])
    center = (lo + hi) / 2; span = max(hi - lo)
    cam = bpy.context.scene.camera
    if cam is None:
        camdata = bpy.data.cameras.new('Sonuc_Kamera')
        cam = bpy.data.objects.new('Sonuc_Kamera', camdata)
        bpy.context.scene.collection.objects.link(cam)
        bpy.context.scene.camera = cam
    cam.location = center + direction.normalized() * span * 3
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = span * 1.35
    return center, span


def run_one(stem, out, save_blend):
    source = FBX_DIR / (stem + '.fbx')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    raw = len(meshes)
    meshes, removed = prepare_unique_parts(meshes)
    start = time.monotonic()
    r = segment(meshes)
    r.update(source=source.name, sha256=before, duplicates_removed=removed,
             raw_parts=raw, seconds=round(time.monotonic() - start, 3))
    assert len(r['assignment']) + len(r['unresolved']) == len(meshes)
    assert len({n for m in r['modules'] for n in m['parts']}) == len(r['assignment'])
    if os.environ.get('MODUL_HOLES', '1') == '1':
        # v0.5: hole signatures -> panel roles, door/handle ownership, type guess.
        # Runs after segment(); world geometry is preserved by hole_scan.
        t0 = time.monotonic()
        parts = {p['name']: p for o in meshes for p in [measure(o)] if p}
        holes, volumes, records = hole_scan.scan(meshes)
        statuses = {rec['name']: rec['status'] for rec in records}
        roles = panel_roles.analyse(r, parts, holes, volumes, statuses)
        scan_errors = sorted(n for n, s in statuses.items() if s == 'scan_error')
        assert len([o for o in bpy.context.scene.objects if o.type == 'MESH']) == len(meshes), 'hole scan left objects behind'
        r.update(version='0.5.1', hole_scan=dict(records=records, scan_errors=scan_errors,
                                                seconds=round(time.monotonic() - t0, 3)), **roles)
        if scan_errors:
            print('SCAN_ERROR', stem, scan_errors, flush=True)
    marks = display(r, meshes)
    r['markers_parented'] = all(o.parent is not None for o in marks.objects)
    for o in bpy.context.scene.objects:
        if o.type in ('CAMERA', 'LIGHT'):
            o.hide_set(True); o.hide_render = True
    scene = bpy.context.scene
    scene.world = scene.world or bpy.data.worlds.new('Sonuc_Dunya')
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.color_type = 'OBJECT'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = 'WORLD'
    scene.world.color = (.08, .08, .08)
    scene.render.resolution_x = 900; scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    r['source_unchanged'] = before == hashlib.sha256(source.read_bytes()).hexdigest()
    assert r['source_unchanged']
    with (out / (stem + '.json')).open('w') as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    if os.environ.get('MODUL_RENDER', '1') != '1':
        return r
    # front-left three-quarter view, all parts
    setup_camera(meshes, Vector((.35, -1, .23)))
    scene.render.filepath = str(out / (stem + '-full.png'))
    bpy.ops.render.render(write_still=True)
    # back-right three-quarter view: reveals backs, hidden panels, open doors
    setup_camera(meshes, Vector((-.35, 1, .23)))
    scene.render.filepath = str(out / (stem + '-back.png'))
    bpy.ops.render.render(write_still=True)
    # structural cores only
    core = {n for m in r['modules'] for n in m['core_parts']}
    for o in meshes:
        o.hide_render = o.name not in core
    setup_camera(meshes, Vector((.35, -1, .23)))
    scene.render.filepath = str(out / (stem + '-core.png'))
    bpy.ops.render.render(write_still=True)
    for o in meshes:
        o.hide_render = False
    if save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(out / (stem + '.blend')))
    return r


def main():
    stems = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if not stems:
        raise SystemExit('stem listesi gerekli')
    out = Path(os.environ['MODUL_OUTPUT_DIR']); out.mkdir(parents=True, exist_ok=True)
    save_blend = os.environ.get('MODUL_SAVE_BLEND') == '1'
    summary = {}
    for stem in stems:
        try:
            r = run_one(stem, out, save_blend)
            summary[stem] = dict(ok=True, modules=len(r['modules']), assigned=len(r['assignment']),
                                 unresolved=len(r['unresolved']), parts=r['part_count'],
                                 raw_parts=r['raw_parts'], duplicates_removed=r['duplicates_removed'],
                                 boundaries=len(r['boundaries']), seconds=r['seconds'])
            print('RESULT', stem, 'modules', len(r['modules']), 'assigned', len(r['assignment']),
                  'unresolved', len(r['unresolved']), 'seconds', r['seconds'], flush=True)
        except Exception as exc:
            summary[stem] = dict(ok=False, error=repr(exc), traceback=traceback.format_exc())
            print('FAIL', stem, repr(exc), flush=True)
            traceback.print_exc()
    with (out / ('_summary-%s.json' % os.environ.get('MODUL_SHARD', '0'))).open('w') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    status = 0
    try:
        main()
    except Exception:
        traceback.print_exc(); status = 1
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(status)
