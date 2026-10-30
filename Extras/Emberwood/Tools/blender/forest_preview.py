# Xenobiology — beauty preview of the Emberwood: rebuilds part of a ForestLayout dump (layout.json + ground.bin, from
# test/LayoutTest.cs) in Blender with the forest kit, the same way the plugin draws it, and renders a few views.
# Run after forest_build.py (needs the "Emberwood" scene objects). Region: CX, CZ (layout metres), RADIUS.
import bpy, os, math, json, random
import numpy as np
from mathutils import Vector, Matrix, Euler
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
DEV = os.path.join(os.path.dirname(PREVIEW_DIR), "forest")
TEX = os.path.join(DEV, "tex")
STATUS = os.path.join(DEV, "preview_status.json")
VIEWS = globals().get("VIEWS", None)
FOCUS = globals().get("FOCUS", "bridge")

SPECIES = ["emberleaf", "goldenpale", "copperoak", "torchwood", "duskpine", "lanternfruit"]
PROPS = ["fern", "shrub", "sapling", "log", "rock", "streamrock", "mushroom", "stump", "litter", "reed", "lily"]

def status(d): json.dump(d, open(STATUS, "w"))

def tex_mat(name, img, alpha=False, blend=False, tile=None, nrm=None, rough=0.9, tint=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = rough
    out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(bs.outputs[0], out.inputs['Surface'])
    ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(os.path.join(TEX, img + ".png"), check_existing=True)
    if tint is not None:
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        nt.links.new(ti.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = tint; nt.links.new(mx.outputs[2], bs.inputs['Base Color'])
    else: nt.links.new(ti.outputs[0], bs.inputs['Base Color'])
    if alpha: nt.links.new(ti.outputs[1], bs.inputs['Alpha'])
    if nrm:
        ni = nt.nodes.new('ShaderNodeTexImage'); ni.image = bpy.data.images.load(os.path.join(TEX, nrm + ".png"), check_existing=True); ni.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(ni.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
    try: m.surface_render_method = 'BLENDED' if blend else 'DITHERED'
    except Exception: pass
    return m

def mesh(name, V, F, UV=None, mat=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in V], [], [tuple(f) for f in F])
    if UV is not None:
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for lo in poly.loop_indices: uvl.data[lo].uv = UV[me.loops[lo].vertex_index]
    for p in me.polygons: p.use_smooth = True
    if mat: me.materials.append(mat)
    o = bpy.data.objects.new(name, me); link(o); return o

def job():
    try:
        status({"state": "running"})
        L = json.load(open(os.path.join(DEV, "layout.json")))
        E = L["E"]; gN = L["gN"]
        G = np.fromfile(os.path.join(DEV, "ground.bin"), np.float32).reshape(gN, gN)
        base = float(np.median(G[gN // 2 - 50:gN // 2 + 50, gN // 2 - 50:gN // 2 + 50]))
        if FOCUS == "clearing": cx, cz = L["clearing"][0], L["clearing"][1]
        elif FOCUS == "pool": cx, cz = L["pool"][0], L["pool"][1]
        elif FOCUS == "pond": cx, cz = L["pond"][0], L["pond"][1]
        else: cx, cz = L["bridge"][0], L["bridge"][1]
        RAD = globals().get("RADIUS", 140.0); FAR = globals().get("FAR", 380.0)
        def gh(x, z):
            fx, fz = (x + E), (z + E); ix, iz = int(np.clip(fx, 0, gN - 2)), int(np.clip(fz, 0, gN - 2)); tx, tz = fx - ix, fz - iz
            return float((G[iz, ix] * (1 - tx) + G[iz, ix + 1] * tx) * (1 - tz) + (G[iz + 1, ix] * (1 - tx) + G[iz + 1, ix + 1] * tx) * tz) - base
        scn = bpy.data.scenes.get("EmberPreview") or bpy.data.scenes.new("EmberPreview")
        bpy.context.window.scene = scn
        for o in list(scn.objects): bpy.data.objects.remove(o, do_unlink=True)
        kitscn = bpy.data.scenes["Emberwood"]
        # ground: 1 m near, 3 m beyond
        def ground(name, r0, step, ring=None):
            xs = np.arange(cx - r0, cx + r0 + 0.01, step); zs = np.arange(cz - r0, cz + r0 + 0.01, step)
            V = []; UV = []
            for z in zs:
                for x in xs:
                    V.append((x - cx, z - cz, gh(x, z))); UV.append(((x + 3 * math.sin(z * 0.05)) / 6.0, (z + 3 * math.cos(x * 0.05)) / 6.0))
            n = len(xs); F = []
            for j in range(len(zs) - 1):
                for i in range(n - 1):
                    if ring is not None:
                        x, z = xs[i] - cx, zs[j] - cz
                        if max(abs(x), abs(z)) < ring - step: continue
                    a = j * n + i; F.append((a, a + 1, a + n + 1, a + n))
            return mesh(name, V, F, UV, M["floor"])
        M = {"floor": tex_mat("pv_floor", "forest_floor", nrm="forest_floor_NRM"),
             "path": tex_mat("pv_path", "forest_path", alpha=True), "bed": tex_mat("pv_bed", "forest_streambed", alpha=True),
             "water": tex_mat("pv_water", "forest_water", alpha=True, blend=True, rough=0.05), "pond": tex_mat("pv_pond", "forest_pondwater", alpha=True, blend=True, rough=0.05)}
        ground("pv_ground_near", RAD, 1.0); ground("pv_ground_far", FAR, 4.0, ring=RAD)
        # ribbons
        def ribbon(name, pts, hwf, hf, across, vtile, mat, skip=None):
            V, UV, F = [], [], []; rows = 0
            def flush():
                nonlocal V, UV, F, rows
                if rows > 1: mesh(name, V, F, UV, mat)
                V, UV, F, rows = [], [], [], 0
            for i, p in enumerate(pts):
                if abs(p[0] - cx) > FAR or abs(p[1] - cz) > FAR or (skip and skip(i)): flush(); continue
                a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
                tx, tz = b[0] - a[0], b[1] - a[1]; tl = math.hypot(tx, tz) + 1e-9; nx, nz = -tz / tl, tx / tl
                hw = hwf(i)
                for k in range(across):
                    o = (k / (across - 1) * 2 - 1) * hw; x, z = p[0] + nx * o, p[1] + nz * o
                    V.append((x - cx, z - cz, hf(x, z, i))); UV.append((k / (across - 1), (p[4] if len(p) > 4 else i) / vtile))
                if rows > 0:
                    r0 = (rows - 1) * across; r1 = rows * across
                    for k in range(across - 1): F.append((r0 + k, r0 + k + 1, r1 + k + 1, r1 + k))
                rows += 1
            flush()
        st = L["stream"]; pa = L["path"]; mp = L["mainPath"]
        ribbon("pv_bed", st, lambda i: st[i][3] + 1.3, lambda x, z, i: gh(x, z) + 0.03, 7, 2 * (st[0][3] + 1.3), M["bed"])
        ribbon("pv_water", st, lambda i: st[i][3] + 0.35, lambda x, z, i: st[i][2] - base - 0.03, 3, 4.0, M["water"])
        ribbon("pv_path", pa[:mp], lambda i: pa[i][3] * 1.25, lambda x, z, i: gh(x, z) + 0.04, 5, 2.75, M["path"], skip=lambda i: pa[i][5] > 0.5)
        ribbon("pv_trail", pa[mp:], lambda i: pa[mp + i][3] * 1.25, lambda x, z, i: gh(x, z) + 0.04, 5, 2.75, M["path"])
        for nm in ("pool", "pond"):
            b = L[nm]; seg = 32; r = b[3] * 1.35
            V = [(b[0] - cx, b[1] - cz, b[2] - base - 0.02)] + [(b[0] - cx + math.cos(k * 2 * math.pi / seg) * r, b[1] - cz + math.sin(k * 2 * math.pi / seg) * r, b[2] - base - 0.02) for k in range(seg)]
            UV = [(0.5, 0.5)] + [(math.cos(k * 2 * math.pi / seg) * r / 8, math.sin(k * 2 * math.pi / seg) * r / 8) for k in range(seg)]
            mesh("pv_" + nm, V, [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)], UV, M["pond"])
        # instances (linked duplicates of the kit meshes)
        def inst(src, x, y, z, yaw, tilt, tdir, s, sink=0.0):
            ob = bpy.data.objects.get(src)
            if ob is None: return None
            o = bpy.data.objects.new("i_" + src, ob.data); link(o)
            R = Euler((0, 0, math.radians(-tdir)), 'XYZ').to_matrix() @ Euler((math.radians(tilt), 0, 0), 'XYZ').to_matrix() @ Euler((0, 0, math.radians(tdir)), 'XYZ').to_matrix() @ Euler((0, 0, math.radians(-yaw)), 'XYZ').to_matrix()
            o.matrix_world = Matrix.Translation((x - cx, z - cz, y - base - sink * s)) @ R.to_4x4() @ Matrix.Scale(s, 4)
            return o
        nt = 0
        for t in L["trees"]:
            k, v, x, y, z, s, yaw, tilt, tdir = t
            d = math.hypot(x - cx, z - cz)
            if d > FAR: continue
            lod = 0 if d < RAD else 1
            if inst("t_%s_%d_%d" % (SPECIES[k], v, lod), x, y, z, yaw, tilt, tdir, s, 0.25): nt += 1
        npr = 0
        for p in L["props"]:
            k, v, x, y, z, s, yaw, tilt, tdir = p
            if math.hypot(x - cx, z - cz) > RAD * 0.85: continue
            if inst("p_%s_%d" % (PROPS[k], v), x, y, z, yaw, 0 if k in (8, 10) else tilt, tdir, s): npr += 1
        e = L["elder"]
        if math.hypot(e[0] - cx, e[1] - cz) < FAR: inst("elder_0", e[0], e[2], e[1], e[3], 0, 0, 1.0, 0.4)
        # set pieces
        b = L["bridge"]
        for nm, ob in (("bridge_vis", None),):
            src = bpy.data.objects.get("bridge_vis")
            if src and math.hypot(b[0] - cx, b[1] - cz) < FAR:
                o = bpy.data.objects.new("i_bridge", src.data); link(o)
                h = math.radians(b[2]); dirv = Vector((math.sin(h), math.cos(h), 0))
                ang = math.atan2(dirv.y, dirv.x)
                o.matrix_world = Matrix.Translation((b[0] - cx, b[1] - cz, max(b[4], b[5]) - base - 0.08)) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Diagonal((max(1.0, (b[3] + 2.2) / 11.0), 1, 1, 1))
        c = L["cascade"]; pl = L["pool"]
        for nm in ("spring_rocks", "cascade"):
            src = bpy.data.objects.get(nm)
            if src and math.hypot(c[0] - cx, c[1] - cz) < FAR:
                o = bpy.data.objects.new("i_" + nm, src.data); link(o)
                h = math.radians(c[3]); ang = math.atan2(math.cos(h), math.sin(h)) - math.pi / 2
                o.matrix_world = Matrix.Translation((c[0] - cx, c[1] - cz, pl[2] - base - 0.05)) @ Matrix.Rotation(ang, 4, 'Z')
        # light, sky, camera
        sun = bpy.data.objects.new("pv_sun", bpy.data.lights.new("pv_sun", "SUN")); link(sun)
        sun.data.energy = 4.5; sun.data.color = (1.0, 0.9, 0.75); sun.data.angle = math.radians(1.5)
        sun.rotation_euler = (math.radians(58), 0, math.radians(215))
        w = bpy.data.worlds.get("pv_world") or bpy.data.worlds.new("pv_world"); w.use_nodes = True
        bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.62, 0.74, 0.92, 1); bg.inputs[1].default_value = 0.9
        scn.world = w
        cam = bpy.data.objects.new("pv_cam", bpy.data.cameras.new("pv_cam")); link(cam); scn.camera = cam
        cam.data.lens = 24; cam.data.clip_end = 3000
        scn.render.engine = 'BLENDER_EEVEE'; scn.render.resolution_x = 1600; scn.render.resolution_y = 900
        try:
            scn.eevee.use_shadows = True; scn.eevee.use_raytracing = True; scn.eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
        except Exception: pass
        try: scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
        except Exception: pass
        # mist for depth
        scn.world.mist_settings.start = 60; scn.world.mist_settings.depth = 500
        shots = []
        def shoot(name, pos, tgt, lens=24):
            cam.location = Vector(pos); cam.data.lens = lens
            cam.rotation_euler = (Vector(tgt) - cam.location).to_track_quat('-Z', 'Y').to_euler()
            scn.render.filepath = os.path.join(PREVIEW_DIR, name); bpy.ops.render.render(write_still=True); shots.append(name)
        # views around the focus: eye height on the trail, a bit higher, and from above the canopy
        def at(dx, dz, up): return (dx, dz, gh(cx + dx, cz + dz) - 0 + up)
        hb = (L["bridge"][4] - base) if FOCUS == "bridge" else gh(cx, cz)
        views = VIEWS or [("ember_%s_a.png" % FOCUS, at(-14, -10, 1.7), (0, 0, hb + 1.2), 22),
                          ("ember_%s_b.png" % FOCUS, at(18, 12, 3.5), (0, 0, hb + 0.5), 24),
                          ("ember_%s_c.png" % FOCUS, (-70, -90, hb + 70), (0, 0, hb), 24)]
        for nm, pos, tgt, lens in views: shoot(nm, pos, tgt, lens)
        status({"state": "done", "trees": nt, "props": npr, "shots": shots})
    except Exception:
        import traceback
        status({"state": "error", "error": traceback.format_exc()})
    return None

bpy.app.timers.register(job, first_interval=0.1)
