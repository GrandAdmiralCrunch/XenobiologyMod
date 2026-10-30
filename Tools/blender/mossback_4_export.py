# Xenobiology — Greater Mossback, step 4: export the hierarchy under the "mossback" empty to .mu
# with the io_object_mu add-on (armature, skinned mesh, material, NLA clips).
import bpy, os, importlib

OUT_DIR = globals().get("OUT_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Models\Kerbin\Mossback")
path = os.path.join(OUT_DIR, "mossback.mu")
scn = bpy.context.scene
root = bpy.data.objects["mossback"]
rig = bpy.data.objects["mossback_rig"]

# rest pose, no active action, so the exported bind pose is clean
ad = rig.animation_data
if ad:
    ad.action = None
for pb in rig.pose.bones:
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
scn.frame_set(0)

exp = importlib.import_module("io_object_mu.export_mu.export")
collections = exp.enable_collections()
try:
    mu = exp.export_object(root, path)
finally:
    exp.restore_collections(collections)
msgs = [str(m[1]) for m in getattr(mu, "messages", [])]
result = {"path": path, "bytes": os.path.getsize(path), "messages": msgs}
