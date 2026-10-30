# Xenobiology — Field Guide portraits and silhouette masks for the reef species.
# Reads XenobiologyDev\reef\specimens.npz/.json (Tools/reef/reef_specimens.py) and the coral textures in
# Models/Kerbin/CoralReef (PNG, before DDS conversion). Writes PREVIEW_DIR/reef_<species>_portrait.png (768x576, transparent)
# and reef_<species>_silmask.png (1024, white on transparent). Then run, outside Blender:
#   xeno_tool.py stylize <silmask> PluginData/Silhouettes/<species>.png   and downsize the portrait to 512x384 in PluginData/Portraits.
import bpy, os, json, math
import numpy as np
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
DEV = os.path.join(os.path.dirname(PREVIEW_DIR), "reef")
TEX = os.path.join(XENO_DIR, "Models", "Kerbin", "CoralReef")
ONLY = globals().get("ONLY")
scn = new_scene("ReefPortraits")
d = np.load(os.path.join(DEV, "specimens.npz")); info = json.load(open(os.path.join(DEV, "specimens.json")))

def img(name): return bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
def material(kind, sil):
    nm = "rp_%s_%s" % (kind, "sil" if sil else "col")
    m = bpy.data.materials.get(nm)
    if m: return m
    m = bpy.data.materials.new(nm); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img("seafan.png" if kind == "fan" else "coral_atlas.png")
    try: m.blend_method = 'CLIP'
    except Exception: pass
    m.use_backface_culling = False
    if sil:
        em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1, 1, 1, 1)
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
        if kind == "fan": nt.links.new(tex.outputs['Alpha'], mx.inputs[0])
        else: mx.inputs[0].default_value = 1.0
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs['Surface'])
    else:
        bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = 0.65
        nt.links.new(tex.outputs['Color'], bs.inputs['Base Color'])
        if kind == "fan":
            tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
            nt.links.new(tex.outputs['Alpha'], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(bs.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs['Surface'])
        else:
            g = nt.nodes.new('ShaderNodeTexImage'); g.image = img("coral_atlas_glow.png")
            nt.links.new(g.outputs['Color'], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = 0.8
            nt.links.new(bs.outputs[0], out.inputs['Surface'])
    return m

cam, g = stage_setup(ground=False)
g.hide_render = True
scn.world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 0.8, 1)
scn.world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
made = []
for sp, inf in info.items():
    if ONLY and sp not in ONLY: continue
    for o in [o for o in scn.objects if o.name.startswith("spec_")]: bpy.data.objects.remove(o, do_unlink=True)
    V = d[sp + "_v"]; F = d[sp + "_f"]; UV = d[sp + "_uv"]
    me = bpy.data.meshes.new("spec_" + sp)
    me.vertices.add(len(V)); me.vertices.foreach_set("co", V.ravel())
    me.loops.add(F.size); me.loops.foreach_set("vertex_index", F.ravel())
    me.polygons.add(len(F)); me.polygons.foreach_set("loop_start", np.arange(0, F.size, 3)); me.polygons.foreach_set("loop_total", np.full(len(F), 3))
    me.update(); me.validate()
    uvl = me.uv_layers.new(name="UVMap"); uvl.data.foreach_set("uv", UV[F.ravel()].ravel())
    me.polygons.foreach_set("use_smooth", np.ones(len(F), bool))
    ob = link(bpy.data.objects.new("spec_" + sp, me))
    lo, hi = np.array(inf["min"]), np.array(inf["max"]); c = (lo + hi) / 2; ext = hi - lo; s = float(max(ext))
    kind = inf["mat"]
    # portrait: three-quarter view from the front, a little above
    me.materials.clear(); me.materials.append(material(kind, False))
    cam.data.type = 'PERSP'; cam.data.lens = 50
    dirv = np.array([0.55, -1.0, 0.6]) if kind != "fan" else np.array([0.15, -1.0, 0.25])
    dirv /= np.linalg.norm(dirv)
    look_at(cam, tuple(c + dirv * s * 2.1), tuple(c))
    render(os.path.join(PREVIEW_DIR, "reef_%s_portrait.png" % sp), 'BLENDER_EEVEE', (768, 576), True)
    # silhouette: flat white, from the side (front for the fan), orthographic
    me.materials.clear(); me.materials.append(material(kind, True))
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = s * 1.15
    side = np.array([0.0, -1.0, 0.12]); side /= np.linalg.norm(side)
    look_at(cam, tuple(c + side * s * 3), tuple(c))
    render(os.path.join(PREVIEW_DIR, "reef_%s_silmask.png" % sp), 'BLENDER_EEVEE', (1024, 1024), True)
    made.append(sp)
result = {"made": made}
