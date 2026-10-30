# Generic: export the hierarchy under the empty ROOT to OUT_PATH (.mu) with io_object_mu, in rest pose.
import bpy, os, importlib
ROOT = globals()["ROOT"]; OUT_PATH = globals()["OUT_PATH"]
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
root = bpy.data.objects[ROOT]
for o in root.children_recursive:
    if o.type == 'ARMATURE':
        if o.animation_data: o.animation_data.action = None
        for pb in o.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
bpy.context.scene.frame_set(0)
exp = importlib.import_module("io_object_mu.export_mu.export")
cols = exp.enable_collections()
try:
    mu = exp.export_object(root, OUT_PATH)
finally:
    exp.restore_collections(cols)
result = {"path": OUT_PATH, "bytes": os.path.getsize(OUT_PATH), "messages": [str(m[1]) for m in getattr(mu, "messages", [])]}
