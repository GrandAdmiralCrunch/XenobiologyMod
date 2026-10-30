# Renders review shots of the current creature scene. Set PREFIX / FRAME in globals before exec.
import bpy, math, os
from mathutils import Vector
scn = bpy.context.scene
OUT = os.path.join(os.path.dirname(bpy.path.abspath("//")) if bpy.data.filepath else "", "")
OUT = globals().get("OUT_DIR") or r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender\previews"
PREFIX = globals().get("PREFIX", "preview")
os.makedirs(OUT, exist_ok=True)

def ensure(name, data):
    o = bpy.data.objects.get(name)
    if o is None:
        o = bpy.data.objects.new(name, data)
    if o.name not in scn.objects:
        scn.collection.objects.link(o)
    return o

cam = ensure("preview_cam", bpy.data.cameras.get("preview_cam") or bpy.data.cameras.new("preview_cam"))
cam.data.lens = 50
scn.camera = cam
def look(pos, target):
    cam.location = pos
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
sun = ensure("preview_sun", bpy.data.lights.get("preview_sun") or bpy.data.lights.new("preview_sun", 'SUN'))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(140))
gr = bpy.data.objects.get("preview_ground")
if gr is None:
    me = bpy.data.meshes.new("preview_ground")
    me.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
    gr = bpy.data.objects.new("preview_ground", me)
if gr.name not in scn.objects: scn.collection.objects.link(gr)
gm = bpy.data.materials.get("preview_ground") or bpy.data.materials.new("preview_ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.32, 0.18, 1)
if not gr.data.materials: gr.data.materials.append(gm)
if scn.world is None: scn.world = bpy.data.worlds.new("preview_world")
scn.world.use_nodes = True
bg = scn.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.55, 0.7, 0.9, 1); bg.inputs[1].default_value = 0.7
scn.render.engine = 'BLENDER_EEVEE'
scn.render.resolution_x, scn.render.resolution_y = 1280, 800
scn.render.resolution_percentage = 100
scn.render.film_transparent = False
if "FRAME" in globals(): scn.frame_set(globals()["FRAME"])
shots = globals().get("SHOTS", {"34": ((13.5, 12.0, 6.5), (0, 0.4, 2.3)), "side": ((19.0, 0.3, 3.5), (0, 0.3, 2.6))})
paths = []
for k, (pos, tgt) in shots.items():
    look(pos, tgt)
    scn.render.filepath = os.path.join(OUT, f"{PREFIX}_{k}.png")
    bpy.ops.render.render(write_still=True)
    paths.append(scn.render.filepath)
result = {"paths": paths}
