import bpy
import mathutils
import bmesh
import re
import math

CATEGORIES = {
    "linco": 9680.0,
    "pim": 936.0,
    "ahsapcivisi": 19.48,
    "rafpimi": 234.0,
    "modulbaglantı": 351.35
}
TOLERANCE = 0.05

def execute_pre_preparation():
    ark_pattern = re.compile(r"^([0-9\.]*)(ark)(?:\.\d+)?$")
    ark_groups = {}

    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            match = ark_pattern.match(obj.name)
            if match:
                modul_prefix = match.group(1)
                if modul_prefix == "":
                    modul_prefix = "1"
                if modul_prefix not in ark_groups:
                    ark_groups[modul_prefix] = []
                ark_groups[modul_prefix].append(obj)

    for prefix, objs in ark_groups.items():
        target_name = f"{prefix}ark"

        if len(objs) < 2:
            if objs:
                objs[0].name = target_name
            continue

        total_world_center = mathutils.Vector((0.0, 0.0, 0.0))
        for obj in objs:
            bbox_world = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
            obj_world_center = sum(bbox_world, mathutils.Vector()) / 8.0
            total_world_center += obj_world_center

        final_world_target = total_world_center / len(objs)

        bpy.ops.object.select_all(action='DESELECT')
        active_ark = objs[0]
        active_ark.name = f"{target_name}_temp"

        for obj in objs:
            obj.select_set(True)

        bpy.context.view_layer.objects.active = active_ark
        bpy.ops.object.join()
        active_ark.name = target_name

        bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')
        active_ark.matrix_world.translation = final_world_target

    bpy.ops.object.select_all(action='DESELECT')

    targets_to_delete = ["Front", "Perspective", "Right", "Top"]
    for name in targets_to_delete:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')

def get_offset_target(obj, cab_center_val, axis='x', inner_weight=0.7, outer_weight=0.3):
    bbox = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
    if axis == 'x':
        min_val = min(v.x for v in bbox)
        max_val = max(v.x for v in bbox)
    elif axis == 'z':
        min_val = min(v.z for v in bbox)
        max_val = max(v.z for v in bbox)

    if abs(min_val - cab_center_val) > abs(max_val - cab_center_val):
        outer = min_val
        inner = max_val
    else:
        outer = max_val
        inner = min_val

    return inner * inner_weight + outer * outer_weight

def get_raw_inner_edge(obj, cab_center_val, axis='x'):
    bbox = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
    if axis == 'x':
        min_val = min(v.x for v in bbox)
        max_val = max(v.x for v in bbox)
    elif axis == 'z':
        min_val = min(v.z for v in bbox)
        max_val = max(v.z for v in bbox)

    if abs(min_val - cab_center_val) > abs(max_val - cab_center_val):
        return max_val
    else:
        return min_val

def snap_euler_to_90(euler):
    step = math.pi / 2.0
    return mathutils.Euler((
        round(euler.x / step) * step,
        round(euler.y / step) * step,
        round(euler.z / step) * step
    ), euler.order)

def execute_arkalik_civi_protocol():
    civi_modules = {}
    pattern = re.compile(r"^([0-9\.]*)(tab|tav|sag|sol|ark)(?:\.\d+)?$")

    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            match = pattern.match(obj.name)
            if match:
                prefix = match.group(1)
                part = match.group(2)
                if prefix == "":
                    prefix = "1"
                if prefix not in civi_modules:
                    civi_modules[prefix] = {}
                if part not in civi_modules[prefix]:
                    civi_modules[prefix][part] = []
                civi_modules[prefix][part].append(obj)

    sutunlar = []
    for prefix, parts in civi_modules.items():
        if 'tav' in parts and parts['tav']:
            tav_obj = parts['tav'][0]
            tav_center = sum((tav_obj.matrix_world @ mathutils.Vector(v) for v in tav_obj.bound_box), mathutils.Vector()) / 8.0
            sutunlar.append({'prefix': prefix, 'x': tav_center.x, 'y': tav_center.y, 'z': tav_center.z})

    ust_moduller = set()
    islenen_prefixler = set()

    for m1 in sutunlar:
        if m1['prefix'] in islenen_prefixler:
            continue
        grup = [m1]
        for m2 in sutunlar:
            if m1['prefix'] != m2['prefix']:
                if abs(m1['x'] - m2['x']) < 0.05 and abs(m1['y'] - m2['y']) < 0.05:
                    grup.append(m2)
                    islenen_prefixler.add(m2['prefix'])
        islenen_prefixler.add(m1['prefix'])
        en_ust = max(grup, key=lambda k: k['z'])
        ust_moduller.add(en_ust['prefix'])

    for prefix, parts in civi_modules.items():
        if all(k in parts for k in ['tab', 'tav', 'sag', 'sol', 'ark']):
            all_parts = parts['tab'] + parts['tav'] + parts['sag'] + parts['sol']
            cab_center_x = sum(sum((obj.matrix_world @ mathutils.Vector(v)).x for v in obj.bound_box)/8.0 for obj in all_parts) / 4.0
            cab_center_y = sum(sum((obj.matrix_world @ mathutils.Vector(v)).y for v in obj.bound_box)/8.0 for obj in all_parts) / 4.0
            cab_center_z = sum(sum((obj.matrix_world @ mathutils.Vector(v)).z for v in obj.bound_box)/8.0 for obj in all_parts) / 4.0

            ark_obj = parts['ark'][0]
            ark_center = sum((ark_obj.matrix_world @ mathutils.Vector(v) for v in ark_obj.bound_box), mathutils.Vector()) / 8.0
            target_y = ark_center.y

            sol_target_x = get_offset_target(parts['sol'][0], cab_center_x, axis='x')
            sag_target_x = get_offset_target(parts['sag'][0], cab_center_x, axis='x')
            tab_target_z = get_offset_target(parts['tab'][0], cab_center_z, axis='z')
            tav_target_z = get_offset_target(parts['tav'][0], cab_center_z, axis='z')

            len_x = abs(sag_target_x - sol_target_x)
            len_z = abs(tav_target_z - tab_target_z)

            num_x = max(1, math.ceil(len_x / 0.15))
            num_z = max(1, math.ceil(len_z / 0.15))

            direction = mathutils.Vector((0, 1, 0)) if cab_center_y > target_y else mathutils.Vector((0, -1, 0))
            rot_euler = snap_euler_to_90(direction.to_track_quat('Z', 'Y').to_euler())

            if prefix in ust_moduller:
                raw_sol_x = get_raw_inner_edge(parts['sol'][0], cab_center_x, axis='x')
                raw_sag_x = get_raw_inner_edge(parts['sag'][0], cab_center_x, axis='x')
                raw_tav_z = get_raw_inner_edge(parts['tav'][0], cab_center_z, axis='z')

                duvarbag_configs = [
                    {"name": "solduvarbag.001", "pt": mathutils.Vector((raw_sol_x, target_y, raw_tav_z))},
                    {"name": "sagduvarbag.001", "pt": mathutils.Vector((raw_sag_x, target_y, raw_tav_z))}
                ]

                for config in duvarbag_configs:
                    db_obj = bpy.data.objects.new(config["name"], None)
                    db_obj.empty_display_type = 'SINGLE_ARROW'
                    db_obj.empty_display_size = 5.0
                    bpy.context.collection.objects.link(db_obj)

                    db_obj.parent = ark_obj
                    db_obj.matrix_parent_inverse = ark_obj.matrix_world.inverted()
                    db_obj.location = config["pt"]
                    db_obj.rotation_euler = rot_euler

            points = []
            for i in range(num_x):
                x = sol_target_x + (sag_target_x - sol_target_x) * (i / num_x)
                points.append(mathutils.Vector((x, target_y, tab_target_z)))
            for i in range(num_z):
                z = tab_target_z + (tav_target_z - tab_target_z) * (i / num_z)
                points.append(mathutils.Vector((sag_target_x, target_y, z)))
            for i in range(num_x):
                x = sag_target_x + (sol_target_x - sag_target_x) * (i / num_x)
                points.append(mathutils.Vector((x, target_y, tav_target_z)))
            for i in range(num_z):
                z = tav_target_z + (tab_target_z - tav_target_z) * (i / num_z)
                points.append(mathutils.Vector((sol_target_x, target_y, z)))

            first_civi_index = num_x

            for idx, pt in enumerate(points):
                name_template = "firstcivi" if idx == first_civi_index else "civi.001"
                empty_obj = bpy.data.objects.new(name_template, None)
                empty_obj.empty_display_type = 'SINGLE_ARROW'
                empty_obj.empty_display_size = 5.0
                bpy.context.collection.objects.link(empty_obj)

                empty_obj.parent = ark_obj
                empty_obj.matrix_parent_inverse = ark_obj.matrix_world.inverted()
                empty_obj.location = pt
                empty_obj.rotation_euler = rot_euler

def get_bbox_min_max(obj):
    bbox = [mathutils.Vector(v) for v in obj.bound_box]
    min_b = mathutils.Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    max_b = mathutils.Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    return min_b, max_b

def get_dist_to_bbox(p_local, dir_vec, min_b, max_b):
    if dir_vec.x > 0.5: return max_b.x - p_local.x
    if dir_vec.x < -0.5: return p_local.x - min_b.x
    if dir_vec.y > 0.5: return max_b.y - p_local.y
    if dir_vec.y < -0.5: return p_local.y - min_b.y
    if dir_vec.z > 0.5: return max_b.z - p_local.z
    if dir_vec.z < -0.5: return p_local.z - min_b.z
    return 9999.0

def align_axes(empty, z_dir, x_dir):
    y_dir = z_dir.cross(x_dir)
    mat = mathutils.Matrix()
    mat[0][0], mat[1][0], mat[2][0] = x_dir.x, x_dir.y, x_dir.z
    mat[0][1], mat[1][1], mat[2][1] = y_dir.x, y_dir.y, y_dir.z
    mat[0][2], mat[1][2], mat[2][2] = z_dir.x, z_dir.y, z_dir.z
    empty.rotation_euler = mat.to_euler()

def align_empty_advanced(empty, target_obj, category):
    local_origin = empty.location
    min_b, max_b = get_bbox_min_max(target_obj)

    directions = [
        mathutils.Vector((1, 0, 0)), mathutils.Vector((-1, 0, 0)),
        mathutils.Vector((0, 1, 0)), mathutils.Vector((0, -1, 0)),
        mathutils.Vector((0, 0, 1)), mathutils.Vector((0, 0, -1))
    ]

    open_dirs = []
    for d in directions:
        hit, loc, norm, idx = target_obj.ray_cast(local_origin, d)
        if not hit:
            open_dirs.append(d)

    if not open_dirs: return None

    if category == "linco":
        if len(open_dirs) >= 2:
            dirs_with_dist = [(d, get_dist_to_bbox(local_origin, d, min_b, max_b)) for d in open_dirs]
            dirs_with_dist.sort(key=lambda x: x[1])
            short_dir = dirs_with_dist[0][0]
            long_dir = dirs_with_dist[-1][0]
            align_axes(empty, short_dir, long_dir)
            return short_dir
        else:
            empty.rotation_euler = open_dirs[0].to_track_quat('Z', 'Y').to_euler()
            return open_dirs[0]
    else:
        chosen_dir = open_dirs[0]
        empty.rotation_euler = chosen_dir.to_track_quat('Z', 'Y').to_euler()
        return chosen_dir

def get_perfect_local_bounds(obj):
    verts = obj.data.vertices
    if not verts: return None, None
    min_x = min(v.co.x for v in verts); max_x = max(v.co.x for v in verts)
    min_y = min(v.co.y for v in verts); max_y = max(v.co.y for v in verts)
    min_z = min(v.co.z for v in verts); max_z = max(v.co.z for v in verts)
    dim = mathutils.Vector((max_x - min_x, max_y - min_y, max_z - min_z))
    center_local = mathutils.Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
    return dim, center_local

def create_prism(name, dim, center_local, matrix_world, scale_factor):
    bpy.ops.mesh.primitive_cube_add(size=1)
    prism = bpy.context.active_object
    prism.name = name
    prism.scale = (dim.x * scale_factor, dim.y * scale_factor, dim.z * scale_factor)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bm = bmesh.new(); bm.from_mesh(prism.data)
    bmesh.ops.translate(bm, verts=bm.verts, vec=center_local)
    bm.to_mesh(prism.data); bm.free()
    prism.matrix_world = matrix_world.copy()
    return prism

def execute_double_boolean(original_obj):
    dim, center_local = get_perfect_local_bounds(original_obj)
    if not dim: return []

    bpy.ops.object.select_all(action='DESELECT')
    outer_prism = create_prism("Temp_Outer", dim, center_local, original_obj.matrix_world, 1.002)
    inner_prism = create_prism("Temp_Inner", dim, center_local, original_obj.matrix_world, 0.998)

    bool_diff = outer_prism.modifiers.new(name="Diff", type='BOOLEAN')
    bool_diff.operation = 'DIFFERENCE'; bool_diff.object = original_obj; bool_diff.solver = 'EXACT'
    bpy.context.view_layer.objects.active = outer_prism
    bpy.ops.object.modifier_apply(modifier=bool_diff.name)

    bool_int = outer_prism.modifiers.new(name="Int", type='BOOLEAN')
    bool_int.operation = 'INTERSECT'; bool_int.object = inner_prism; bool_int.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=bool_int.name)

    bpy.data.objects.remove(inner_prism, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    outer_prism.select_set(True); bpy.context.view_layer.objects.active = outer_prism

    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')

    separated_objects = bpy.context.selected_objects
    valid_holes = []

    for part in separated_objects:
        bm = bmesh.new(); bm.from_mesh(part.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        vol = abs(bm.calc_volume()); bm.free()

        if vol > 0.01: valid_holes.append({"object": part, "volume": vol})
        else: bpy.data.objects.remove(part, do_unlink=True)

    return valid_holes

def main():
    execute_pre_preparation()

    prefix_extractor = re.compile(r"^([0-9\.]*)")
    target_meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and not obj.name.startswith("Temp_") and obj.visible_get()]
    modulbaglantı_bellek = []

    if target_meshes:
        for target_obj in target_meshes:
            if target_obj.name.endswith("ark"):
                continue

            prefix_match = prefix_extractor.match(target_obj.name)
            current_prefix = prefix_match.group(1) if prefix_match else ""

            holes = execute_double_boolean(target_obj)
            if not holes:
                continue

            ahsapcivisi_bellek = []

            for i, h in enumerate(holes):
                vol = h['volume']
                obj_part = h['object']
                matched_category = None

                for cat_name, target_val in CATEGORIES.items():
                    lower_bound = target_val * (1 - TOLERANCE)
                    upper_bound = target_val * (1 + TOLERANCE)
                    if lower_bound <= vol <= upper_bound:
                        matched_category = cat_name
                        break

                if matched_category == "modulbaglantı":
                    world_bbox = [obj_part.matrix_world @ mathutils.Vector(v) for v in obj_part.bound_box]
                    world_center = sum(world_bbox, mathutils.Vector()) / 8.0
                    local_bbox_center = sum((mathutils.Vector(b) for b in obj_part.bound_box), mathutils.Vector()) / 8.0

                    modulbaglantı_bellek.append({
                        "target_obj": target_obj,
                        "world_center": world_center,
                        "local_center": local_bbox_center,
                        "prefix": current_prefix
                    })
                    bpy.data.objects.remove(obj_part, do_unlink=True)

                elif matched_category:
                    local_bbox_center = sum((mathutils.Vector(b) for b in obj_part.bound_box), mathutils.Vector()) / 8.0

                    empty_obj = bpy.data.objects.new(f"{matched_category}.001", None)
                    empty_obj.empty_display_type = 'SINGLE_ARROW'
                    empty_obj.empty_display_size = 5.0
                    bpy.context.collection.objects.link(empty_obj)

                    empty_obj.parent = target_obj
                    empty_obj.location = local_bbox_center

                    align_empty_advanced(empty_obj, target_obj, matched_category)

                    if matched_category == "ahsapcivisi":
                        ahsapcivisi_bellek.append(empty_obj)

                    bpy.data.objects.remove(obj_part, do_unlink=True)
                else:
                    bpy.data.objects.remove(obj_part, do_unlink=True)

            if len(ahsapcivisi_bellek) == 4:
                avg_local_pos = sum((c.location for c in ahsapcivisi_bellek), mathutils.Vector()) / 4.0
                z_dir_local = ahsapcivisi_bellek[0].rotation_euler.to_matrix() @ mathutils.Vector((0, 0, 1))

                min_b, max_b = get_bbox_min_max(target_obj)
                all_dirs = [
                    mathutils.Vector((1, 0, 0)), mathutils.Vector((-1, 0, 0)),
                    mathutils.Vector((0, 1, 0)), mathutils.Vector((0, -1, 0)),
                    mathutils.Vector((0, 0, 1)), mathutils.Vector((0, 0, -1))
                ]

                ortho_dirs = [d for d in all_dirs if abs(d.dot(z_dir_local)) < 0.1]
                best_x_dir = None
                min_dist = 9999.0
                for d in ortho_dirs:
                    dist = get_dist_to_bbox(avg_local_pos, d, min_b, max_b)
                    if dist < min_dist:
                        min_dist = dist
                        best_x_dir = d

                if best_x_dir is None: best_x_dir = ortho_dirs[0]

                empty_ay = bpy.data.objects.new("ayarliayak.001", None)
                empty_ay.empty_display_type = 'SINGLE_ARROW'
                empty_ay.empty_display_size = 7.0
                bpy.context.collection.objects.link(empty_ay)

                empty_ay.parent = target_obj
                empty_ay.location = avg_local_pos
                align_axes(empty_ay, z_dir_local, best_x_dir)

                for civi in ahsapcivisi_bellek:
                    bpy.data.objects.remove(civi, do_unlink=True)

    if modulbaglantı_bellek:
        unmatched = modulbaglantı_bellek.copy()
        pairs = []

        while len(unmatched) >= 2:
            h1 = unmatched.pop(0)
            best_match_idx = None
            min_dist = 9999.0

            for i, h2 in enumerate(unmatched):
                dist = (h1["world_center"] - h2["world_center"]).length
                if dist < min_dist:
                    min_dist = dist
                    best_match_idx = i

            if best_match_idx is not None and min_dist < 0.2:
                h2 = unmatched.pop(best_match_idx)
                pairs.append((h1, h2, min_dist))

        for h1, h2, dist in pairs:
            vec_to_B = h2["world_center"] - h1["world_center"]
            if vec_to_B.length < 0.0001:
                vec_to_B = mathutils.Vector((0, 0, 1))

            dir_A_world = vec_to_B.normalized()
            dir_A_local = h1["target_obj"].matrix_world.inverted_safe().to_3x3() @ dir_A_world

            empty_A = bpy.data.objects.new("ModulBagA.001", None)
            empty_A.empty_display_type = 'SINGLE_ARROW'
            empty_A.empty_display_size = 5.0
            bpy.context.collection.objects.link(empty_A)

            empty_A.parent = h1["target_obj"]
            empty_A.location = h1["local_center"]
            empty_A.rotation_euler = snap_euler_to_90(dir_A_local.to_track_quat('Z', 'Y').to_euler())

            dir_B_world = -dir_A_world
            dir_B_local = h2["target_obj"].matrix_world.inverted_safe().to_3x3() @ dir_B_world

            empty_B = bpy.data.objects.new("ModulBagB.001", None)
            empty_B.empty_display_type = 'SINGLE_ARROW'
            empty_B.empty_display_size = 5.0
            bpy.context.collection.objects.link(empty_B)

            empty_B.parent = h2["target_obj"]
            empty_B.location = h2["local_center"]
            empty_B.rotation_euler = snap_euler_to_90(dir_B_local.to_track_quat('Z', 'Y').to_euler())

    execute_arkalik_civi_protocol()
    bpy.ops.object.select_all(action='DESELECT')

if __name__ == "__main__":
    main()
