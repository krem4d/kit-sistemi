"""Run with Blender in background mode; verifies diagnostic Empty parenting."""
import bpy
import runpy
from pathlib import Path
from mathutils import Vector


if not bpy.app.background:
    raise RuntimeError("Run this test in a separate background Blender process.")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=1, location=(3.0, 2.0, 1.0))
parent = bpy.context.object
parent.name = "Panel"
parent.scale = (0.009, 0.02, 0.5)
bpy.context.view_layer.update()

script = Path(__file__).resolve().parents[1] / "test_scriptleri" / "agac_vidasi_empty.py"
tool = runpy.run_path(str(script))
collection = tool["_teshis_koleksiyonu"]()
location = Vector((0.25, 0.5, 0.75))
empty = tool["add_empty"]("VIDA_ESKI_Test", location, "VIDA_ESKI", collection, parent)
bpy.context.view_layer.update()

assert empty.parent is parent
assert (empty.matrix_world.translation - location).length < 1e-8
world_scale = empty.matrix_world.to_scale()
assert max(abs(value - 1.0) for value in world_scale) < 1e-6, world_scale
assert empty in parent.children
assert empty in collection.objects[:]
print("PASS: diagnostic Empty is a visible child with preserved world transform")
