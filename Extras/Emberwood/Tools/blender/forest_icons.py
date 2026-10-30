# Xenobiology — field-guide portraits and silhouette masks for the Emberwood plants (run after forest_build.py).
# Writes PREVIEW_DIR/flora_<id>_portrait.png (768x576) and flora_<id>_silmask.png (1024, white on transparent).
import bpy, os, math, json
from mathutils import Vector
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
DEV = os.path.join(os.path.dirname(PREVIEW_DIR), "forest"); TEX = os.path.join(DEV, "tex")
STATUS = os.path.join(DEV, "icons_status.json")
TARGETS = [("kerbin_emberleaf", "t_emberleaf_0_0"), ("kerbin_goldenpale", "t_goldenpale_0_0"), ("kerbin_copperoak", "t_copperoak_1_0"),
           ("kerbin_torchwood", "t_torchwood_0_0"), ("kerbin_duskpine", "t_duskpine_0_0"), ("kerbin_lanternfruit", "t_lanternfruit_0_0"),
           ("kerbin_goldfern", "p_fern_0"), ("kerbin_emberberry", "p_shrub_0"), ("kerbin_lanternreed", "p_reed_0")]

def white_copy(m):
    w = m.copy(); nt = w.node_tree
    ti = [n for n in nt.nodes if n.type == 'TEX_IMAGE'][0]
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1, 1, 1, 1)
    mix = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    if any(k in m.name for k in ("leaves", "lily")):
        gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.42
        nt.links.new(ti.outputs[1], gt.inputs[0]); nt.links.new(gt.outputs[0], mix.inputs[0])
    else: mix.inputs[0].default_value = 1.0
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]; nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return w

def job():
    try:
        scn = bpy.data.scenes.get("EmberIcons") or bpy.data.scenes.new("EmberIcons")
        bpy.context.window.scene = scn
        for o in list(scn.objects): scn.collection.objects.unlink(o)
        cam, g = stage_setup(ground=True, sky=(0.62, 0.74, 0.9), ground_col=(0.28, 0.14, 0.06))
        # leaf-litter ground
        gm = bpy.data.materials.get("icon_floor") or bpy.data.materials.new("icon_floor"); gm.use_nodes = True; nt = gm.node_tree
        bs = nt.nodes.get("Principled BSDF"); ti = nt.nodes.get("floor_tex") or nt.nodes.new('ShaderNodeTexImage'); ti.name = "floor_tex"
        ti.image = bpy.data.images.load(os.path.join(TEX, "forest_floor.png"), check_existing=True)
        mp = nt.nodes.get("floor_map") or nt.nodes.new('ShaderNodeMapping'); mp.name = "floor_map"; mp.inputs['Scale'].default_value = (60, 60, 1)
        tc = nt.nodes.get("floor_tc") or nt.nodes.new('ShaderNodeTexCoord'); tc.name = "floor_tc"
        nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], ti.inputs['Vector']); nt.links.new(ti.outputs[0], bs.inputs['Base Color'])
        if not g.data.uv_layers: g.data.uv_layers.new(name="UVMap")
        g.data.materials.clear(); g.data.materials.append(gm)
        scn.render.engine = 'BLENDER_EEVEE'
        try: scn.view_settings.view_transform = 'AgX'
        except Exception: pass
        done = []
        for lid, src in TARGETS:
            ob = bpy.data.objects.get(src)
            if ob is None: continue
            o = bpy.data.objects.new("icon_" + lid, ob.data); scn.collection.objects.link(o)
            bb = [Vector(c) for c in ob.bound_box]
            lo = Vector((min(p.x for p in bb), min(p.y for p in bb), min(p.z for p in bb))); hi = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
            cen = (lo + hi) / 2; L = max(hi - lo)
            # portrait: three-quarter view from slightly below the crown
            g.hide_render = True                # the guide's portraits sit on a transparent background
            cam.data.type = 'PERSP'; cam.data.lens = 40; cam.data.clip_end = 2000
            d = Vector((0.75, -1.0, 0.18 if L > 4 else 0.55)).normalized()
            look_at(cam, cen + d * L * 1.6, cen)
            render(os.path.join(PREVIEW_DIR, "flora_%s_portrait.png" % lid), 'BLENDER_EEVEE', (768, 576), True)
            # silhouette mask: side view, white, transparent background
            saved = [s.material for s in ob.material_slots]
            whites = [white_copy(m) for m in saved]
            for s_, w in zip(o.material_slots, whites): pass
            o.data = ob.data.copy()
            for i, w in enumerate(whites): o.data.materials[i] = w
            g.hide_render = True
            cam.data.type = 'ORTHO'; cam.data.ortho_scale = L * 1.08
            look_at(cam, Vector((cen.x, cen.y - L * 3, cen.z)), cen)
            render(os.path.join(PREVIEW_DIR, "flora_%s_silmask.png" % lid), 'BLENDER_EEVEE', (1024, 1024), True)
            bpy.data.objects.remove(o, do_unlink=True)
            done.append(lid)
        json.dump({"state": "done", "done": done}, open(STATUS, "w"))
    except Exception:
        import traceback
        json.dump({"state": "error", "error": traceback.format_exc()}, open(STATUS, "w"))
    return None

bpy.app.timers.register(job, first_interval=0.1)
