import sys,os,json,time,hashlib,traceback
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,'/home/rocket/Jupiter/Projects/otonom_kit')
import bpy
from mathutils import Vector
from module_segmenter import segment
from parca_sayim import prepare_unique_parts

PALETTE=[(.1,.5,.95,1),(.15,.75,.3,1),(.95,.35,.1,1),(.65,.2,.9,1),(.95,.75,.1,1)]

def display(result,objects):
    collection=bpy.data.collections.get('MODUL_ADAYLARI')
    if collection is None:
        collection=bpy.data.collections.new('MODUL_ADAYLARI');bpy.context.scene.collection.children.link(collection)
    for old in list(collection.objects):
        if old.get('_modul_marker'):bpy.data.objects.remove(old,do_unlink=True)
    for o in objects:
        o.hide_set(False);o.hide_render=False
        a=result['assignment'].get(o.name)
        o.color=PALETTE[(int(a['module'][1:])-1)%len(PALETTE)] if a else (.9,.04,.08,1)
        o['modul_adayi']=a['module'] if a else 'COZULMEDI'
        o['atama_gerekcesi']=a['reason'] if a else result['unresolved'][o.name]['reason']
    for i,c in enumerate(result['boundaries'],1):
        axis=c['axis'];others=[k for k in range(3) if k!=axis]
        center=Vector((0,0,0));size=Vector((.001,.001,.001));center[axis]=c['plane_mm']/1000
        for j,k in enumerate(others):center[k]=(c['lo_mm'][j]+c['hi_mm'][j])/2000;size[k]=(c['hi_mm'][j]-c['lo_mm'][j])/2000
        mark=bpy.data.objects.new('Temas_%02d_%s_%s'%(i,c['modules'][0],c['modules'][1]),None);collection.objects.link(mark)
        mark.empty_display_type='CUBE';mark.empty_display_size=1;mark.location=center;mark.scale=size;mark.show_in_front=True
        bpy.context.view_layer.update();world=mark.matrix_world.copy();mark.parent=bpy.data.objects[c['a']];mark.matrix_parent_inverse=mark.parent.matrix_world.inverted();mark.matrix_world=world
        mark['_modul_marker']=True;mark['diger_parca']=c['b'];mark['temas_alani_mm2']=c['area_mm2']
    return collection


def main():
    stems=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['9422','9440','9441','9477','9482','9449-2']
    out=Path(os.environ.get('MODUL_OUTPUT_DIR',str(ROOT/'results-v2')));out.mkdir(parents=True,exist_ok=True)
    for stem in stems:
        if any((out/(stem+suffix)).exists() for suffix in ('.json','.blend','-full.png','-core.png')):
            raise FileExistsError('Yeni MODUL_OUTPUT_DIR seçin; mevcut sonuçlar korunuyor: '+stem)
    for stem in stems:
        source=Path('/home/rocket/Belgeler/Capcut/siparişler fbx')/(stem+'.fbx')
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(source))
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];raw=len(meshes)
        meshes,removed=prepare_unique_parts(meshes)
        start=time.monotonic();r=segment(meshes);r.update(source=source.name,sha256=before,duplicates_removed=removed,raw_parts=raw,seconds=round(time.monotonic()-start,3))
        assert len(r['assignment'])+len(r['unresolved'])==len(meshes)
        assert len({n for m in r['modules'] for n in m['parts']})==len(r['assignment'])
        marks=display(r,meshes);r['markers_parented']=all(o.parent is not None for o in marks.objects)
        for o in bpy.context.scene.objects:
            if o.type in ('CAMERA','LIGHT'):o.hide_set(True);o.hide_render=True
        points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
        lo=Vector([min(p[k] for p in points) for k in range(3)]);hi=Vector([max(p[k] for p in points) for k in range(3)]);center=(lo+hi)/2;span=max(hi-lo)
        camdata=bpy.data.cameras.new('Sonuc_Kamera');cam=bpy.data.objects.new('Sonuc_Kamera',camdata);bpy.context.scene.collection.objects.link(cam)
        cam.location=center+Vector((.35,-1,.23)).normalized()*span*3;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=span*1.35;bpy.context.scene.camera=cam
        scene=bpy.context.scene;scene.world=scene.world or bpy.data.worlds.new('Sonuc_Dunya');scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.background_type='WORLD';scene.world.color=(.08,.08,.08)
        scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
        for screen in bpy.data.screens:
            for ar in screen.areas:
                if ar.type=='VIEW_3D':
                    ar.spaces.active.shading.color_type='OBJECT';ar.spaces.active.overlay.show_relationship_lines=False
                    ar.spaces.active.region_3d.view_location=center;ar.spaces.active.region_3d.view_distance=span*1.7;ar.spaces.active.region_3d.view_rotation=Vector((.35,-1,.23)).to_track_quat('Z','Y');ar.spaces.active.region_3d.view_perspective='ORTHO'
        bpy.ops.wm.save_as_mainfile(filepath=str(out/(stem+'.blend')))
        r['source_unchanged']=before==hashlib.sha256(source.read_bytes()).hexdigest();assert r['source_unchanged']
        with (out/(stem+'.json')).open('x') as f:json.dump(r,f,ensure_ascii=False,indent=2)
        print('RESULT',stem,'modules',len(r['modules']),'assigned',len(r['assignment']),'unresolved',len(r['unresolved']),'seconds',r['seconds'],flush=True)
        scene.render.filepath=str(out/(stem+'-full.png'));bpy.ops.render.render(write_still=True)
        core={n for m in r['modules'] for n in m['core_parts']}
        for o in meshes:o.hide_render=o.name not in core
        scene.render.filepath=str(out/(stem+'-core.png'));bpy.ops.render.render(write_still=True)

if __name__=='__main__':
    status=0
    try:main()
    except Exception:traceback.print_exc();status=1
    sys.stdout.flush();sys.stderr.flush();os._exit(status)
