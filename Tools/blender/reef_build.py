# Xenobiology — the Kerbin coral reef (XENO_LAIR kerbin_coral_reef).
# Inputs (XenobiologyDev\reef, made by Tools/reef/*.py): reef_high.npz (SDF rock, ~1.3M tris), reef_meta.json,
# corals.npz + corals.json (coral meshes with atlas UVs), and the textures coral_atlas(.png/_glow), seafan.png, reef_shaft.png
# already in the model folder.
# The rock is decimated to ~100k tris, split into 8 chunks (frustum culling) and gets a baked diffuse (stone, dead coral,
# coralline algae, turf, sand, ambient occlusion) and a baked tangent-space normal map from the high-poly + procedural bump.
# Local frame: sea floor at z = 0, lagoon toward -y. Markers: entrance (west swim-through), den (cavern), pen (lagoon).
# Transforms named sway_* rock in the plugin; dayonly_* are hidden at night; emissive materials breathe.
import bpy, bmesh, os, math, json, random
import numpy as np
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
NAME = "coral_reef"
DEV = os.path.join(os.path.dirname(PREVIEW_DIR), "reef")
OUT = os.path.join(XENO_DIR, "Models", "Kerbin", "CoralReef")
STEP = globals().get("STEP", "all")            # "all" | "model" (no bake/export) | "renders"
LOW_TRIS = globals().get("LOW_TRIS", 140000)
random.seed(77)
XS = [-104, -52, 0, 52, 104]; YSPLIT = -6.0     # chunk grid (must match reef_corals.py)
META = json.load(open(os.path.join(DEV, "reef_meta.json")))
CJ = json.load(open(os.path.join(DEV, "corals.json")))

def gpu_cycles():
    scn = bpy.context.scene; scn.render.engine = 'CYCLES'
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = 'OPTIX'; pr.refresh_devices()
        for d in pr.devices: d.use = d.type == 'OPTIX'
        scn.cycles.device = 'GPU'
    except Exception: scn.cycles.device = 'CPU'

def mesh_from_arrays(name, V, Fc, UV=None):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set("co", np.asarray(V, np.float32).ravel())
    me.loops.add(Fc.size); me.loops.foreach_set("vertex_index", Fc.ravel())
    me.polygons.add(len(Fc)); me.polygons.foreach_set("loop_start", np.arange(0, Fc.size, 3)); me.polygons.foreach_set("loop_total", np.full(len(Fc), 3))
    me.update(); me.validate()
    if UV is not None:
        uvl = me.uv_layers.new(name="UVMap"); uvl.data.foreach_set("uv", np.asarray(UV, np.float32)[Fc.ravel()].ravel())
    me.polygons.foreach_set("use_smooth", np.ones(len(Fc), bool))
    return link(bpy.data.objects.new(name, me))

scn = new_scene("CoralReef")
hd = np.load(os.path.join(DEV, "reef_high.npz"))
high = mesh_from_arrays(NAME + "_high", hd["verts"], hd["faces"])
# outward normals: top faces must point up
me = high.data; nz = np.zeros(len(me.polygons) * 3); me.polygons.foreach_get("normal", nz); cz = np.zeros(len(me.polygons) * 3); me.polygons.foreach_get("center", cz)
nz = nz.reshape(-1, 3); cz = cz.reshape(-1, 3); sel = (cz[:, 2] > 8) & (np.abs(nz[:, 2]) > 0.7)
FLIPPED = bool((nz[sel, 2] < 0).mean() > 0.5)
if FLIPPED: me.flip_normals()

# ---------------------------------------------------------------- low poly: decimate, trim the buried skirt, split into chunks
low = high.copy(); low.data = high.data.copy(); link(low); low.name = NAME + "_low"
dc = low.modifiers.new("d", 'DECIMATE'); dc.ratio = LOW_TRIS / len(high.data.polygons); dc.use_collapse_triangulate = True
select_only([low]); bpy.ops.object.modifier_apply(modifier="d")
bm = bmesh.new(); bm.from_mesh(low.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.co.z < -2.6 for v in f.verts)], context='FACES')
bm.to_mesh(low.data); bm.free()
for p in low.data.polygons: p.use_smooth = True
# collider: a coarser copy of the low poly
col = low.copy(); col.data = low.data.copy(); link(col); col.name = NAME + "_collider"
dc = col.modifiers.new("d", 'DECIMATE'); dc.ratio = 0.35
select_only([col]); bpy.ops.object.modifier_apply(modifier="d")
# chunks by face centre
def chunk_of(c):
    i = min(3, max(0, int(np.searchsorted(XS, c[0]) - 1))); return i + 4 * (0 if c[1] < YSPLIT else 1)
select_only([low]); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
chunks = {}
for ch in range(8):
    o = low.copy(); o.data = low.data.copy(); link(o); o.name = "%s_rock_%d" % (NAME, ch)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if chunk_of(f.calc_center_median()) != ch], context='FACES')
    bm.to_mesh(o.data); bm.free()
    if len(o.data.polygons): chunks[ch] = o
    else: bpy.data.objects.remove(o, do_unlink=True)
bpy.data.objects.remove(low, do_unlink=True)

# ---------------------------------------------------------------- rock material for the bake (on the high poly)
def rock_color(N):
    up = N.up01()
    base = N.ramp(N.noise(0.11, 5), [(0.3, (0.47, 0.45, 0.40)), (0.55, (0.62, 0.59, 0.52)), (0.8, (0.53, 0.50, 0.45))])
    # dead coral skeletons: meandering brain grooves, pitted corallites
    brain = N.wave(1.3, 'BANDS', 'X', 9.0)
    base = N.mix(base, N.mul(base, 0.86), N.m('MULTIPLY', N.m('LESS_THAN', brain, 0.12), N.m('GREATER_THAN', N.noise(0.4, 2), 0.62)))   # faint old grooves
    base = N.mix(base, N.mul(base, 0.6), N.m('MULTIPLY', N.m('LESS_THAN', N.voronoi(7.0), 0.12), 0.8))
    # coralline algae: pink-lilac crusts, mottled
    cor = N.m('MULTIPLY', N.m('GREATER_THAN', N.noise(0.35, 4), 0.56), N.m('GREATER_THAN', up, 0.35))
    corc = N.mix((0.70, 0.42, 0.52), (0.58, 0.36, 0.55), N.noise(3.0, 3))
    base = N.mix(base, corc, N.m('MULTIPLY', cor, 0.85))
    # turf algae and sediment on the tops
    turf = N.m('MULTIPLY', N.m('GREATER_THAN', up, 0.82), N.m('GREATER_THAN', N.noise(0.22, 4, rough=0.6), 0.45))
    base = N.mix(base, N.mix((0.34, 0.37, 0.21), (0.46, 0.44, 0.26), N.noise(4.0, 3)), N.m('MULTIPLY', turf, 0.8))
    # encrusting sponges (orange, red, yellow) in the shade
    ao = N.node('ShaderNodeAmbientOcclusion', samples=16, only_local=True); ao.inputs['Distance'].default_value = 2.5
    occl = ao.outputs['AO']
    spg = N.m('MULTIPLY', N.m('LESS_THAN', occl, 0.55), N.m('GREATER_THAN', N.noise(1.1, 3), 0.6))
    base = N.mix(base, N.ramp(N.noise(0.6, 2), [(0.35, (0.85, 0.35, 0.12)), (0.5, (0.75, 0.18, 0.12)), (0.65, (0.9, 0.7, 0.15))]), spg)
    # living colonies painted over the rock, one kind per 2-4 m patch: brain, boulder, encrusting, sponge, turf
    vc = N.node('ShaderNodeTexVoronoi', feature='F1'); N.L(N.obj, vc.inputs['Vector']); vc.inputs['Scale'].default_value = 0.32
    sep = N.node('ShaderNodeSeparateColor'); N.L(vc.outputs['Color'], sep.inputs[0]); k = sep.outputs[0]
    blob = N.m('ADD', vc.outputs['Distance'], N.m('MULTIPLY', N.noise(1.2, 3), 0.35))
    inner = N.m('LESS_THAN', blob, 0.55)                                   # rounded, ragged colonies with bare rock between
    def band(a, b): return N.m('MULTIPLY', N.m('GREATER_THAN', k, a), N.m('LESS_THAN', k, b))
    brain = N.mix((0.56, 0.58, 0.36), (0.22, 0.26, 0.14), N.m('LESS_THAN', N.wave(3.2, 'BANDS', 'X', 14.0), 0.25))
    boulder = N.mix((0.66, 0.52, 0.32), (0.5, 0.38, 0.22), N.m('LESS_THAN', N.voronoi(22.0), 0.25))
    purple = N.mix((0.44, 0.24, 0.52), (0.66, 0.45, 0.72), N.m('LESS_THAN', N.voronoi(16.0), 0.18))
    sponge = N.mix((0.88, 0.64, 0.18), (0.95, 0.45, 0.15), N.noise(2.0, 3))
    turf2 = N.mix((0.30, 0.40, 0.20), (0.42, 0.48, 0.24), N.noise(6.0, 3))
    blue = N.mix((0.30, 0.45, 0.62), (0.45, 0.62, 0.75), N.noise(5.0, 2))
    live = N.m('MULTIPLY', N.m('MULTIPLY', inner, N.m('GREATER_THAN', occl, 0.5)), 0.6)     # muted: the real corals carry the colour now
    for (a, b), cc in (((0.38, 0.52), brain), ((0.52, 0.64), boulder), ((0.64, 0.73), purple), ((0.73, 0.80), sponge), ((0.80, 0.90), turf2), ((0.90, 0.95), blue)):
        base = N.mix(base, cc, N.m('MULTIPLY', band(a, b), live))
    # sand settled on low ledges and the floor of the caves
    sand = N.m('MULTIPLY', N.m('GREATER_THAN', up, 0.9), N.m('LESS_THAN', N.Z, 1.6))
    base = N.mix(base, N.mix((0.80, 0.74, 0.60), (0.70, 0.64, 0.50), N.noise(5.0, 3)), sand)
    base = N.mix(base, N.mix((0.80, 0.74, 0.60), (0.70, 0.64, 0.50), N.noise(5.0, 3)), N.m('MULTIPLY', N.m('LESS_THAN', N.Z, 0.25), 0.7))
    # ambient occlusion: dark crevices and cave interiors
    return N.mul(base, N.m('ADD', N.m('MULTIPLY', N.m('POWER', occl, 1.4), 0.78), 0.22))

def rock_height(N):
    h = N.m('MULTIPLY', N.voronoi(7.0), 0.35)
    h = N.m('ADD', h, N.m('MULTIPLY', N.noise(2.2, 5, rough=0.65), 0.6))
    h = N.m('ADD', h, N.m('MULTIPLY', N.wave(1.3, 'BANDS', 'X', 9.0), 0.25))
    h = N.m('ADD', h, N.m('MULTIPLY', N.noise(12.0, 3), 0.15))
    return h

def set_high_material(mode):
    mat = bpy.data.materials.get("reef_high_" + mode) or bpy.data.materials.new("reef_high_" + mode)
    N = Nodes(mat); out = N.node('ShaderNodeOutputMaterial')
    if mode == "color":
        em = N.node('ShaderNodeEmission'); N.feed(em.inputs['Color'], rock_color(N)); N.L(em.outputs[0], out.inputs['Surface'])
    else:
        bs = N.node('ShaderNodeBsdfPrincipled'); bp = N.node('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.65; bp.inputs['Distance'].default_value = 0.06
        N.L(rock_height(N), bp.inputs['Height']); N.L(bp.outputs['Normal'], bs.inputs['Normal']); N.L(bs.outputs[0], out.inputs['Surface'])
    high.data.materials.clear(); high.data.materials.append(mat)

def bake_to(target, img, kind):
    mat = target.data.materials[0]; nt = mat.node_tree
    tn = nt.nodes.get("bake_target") or nt.nodes.new('ShaderNodeTexImage'); tn.name = "bake_target"; tn.image = img
    for n_ in nt.nodes: n_.select = False
    tn.select = True; nt.nodes.active = tn
    s = bpy.context.scene; s.cycles.samples = 16 if kind == 'EMIT' else 1
    b = s.render.bake; b.use_selected_to_active = True; b.cage_extrusion = 0.4; b.max_ray_distance = 0.9; b.margin = 6; b.use_clear = True
    if kind == 'NORMAL': b.normal_space = 'TANGENT'
    high.hide_render = False; high.hide_set(False)
    for o in scn.objects: o.select_set(o in (high, target))
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.bake(type=kind)

def rock_final_material(o, ch, dimg, nimg):
    fm = bpy.data.materials.get("%s_rock_%d" % (NAME, ch)) or bpy.data.materials.new("%s_rock_%d" % (NAME, ch))
    fm.use_nodes = True; ft = fm.node_tree; ft.nodes.clear()
    bsdf = ft.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.inputs['Roughness'].default_value = 0.85
    fo = ft.nodes.new('ShaderNodeOutputMaterial'); ft.links.new(bsdf.outputs[0], fo.inputs['Surface'])
    dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = dimg; ft.links.new(dt.outputs[0], bsdf.inputs['Base Color'])
    nt_ = ft.nodes.new('ShaderNodeTexImage'); nt_.image = nimg; nimg.colorspace_settings.name = 'Non-Color'
    nm = ft.nodes.new('ShaderNodeNormalMap'); ft.links.new(nt_.outputs[0], nm.inputs['Color']); ft.links.new(nm.outputs[0], bsdf.inputs['Normal'])
    o.data.materials.clear(); o.data.materials.append(fm)
    mp = fm.mumatprop; mp.shaderName = "KSP/Bumped"
    for coll in (mp.color.properties, mp.texture.properties, mp.float2.properties, mp.float3.properties, mp.vector.properties): coll.clear()
    c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
    t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = dimg.name
    t = mp.texture.properties.add(); t.name = "_BumpMap"; t.tex = nimg.name; t.type = True

BAKED = {}
if STEP == "all":
    gpu_cycles()
    os.makedirs(OUT, exist_ok=True)
    for ch, o in chunks.items():
        select_only([o]); bpy.ops.object.mode_set(mode='EDIT')
        if not o.data.uv_layers: o.data.uv_layers.new(name="UVMap")
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(80), island_margin=0.002, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        try: bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, shape_method='CONCAVE', margin_method='FRACTION', margin=0.0015)
        except TypeError: bpy.ops.uv.pack_islands(rotate=True, margin=0.0015)
        bpy.ops.object.mode_set(mode='OBJECT')
        area = sum(p.area for p in o.data.polygons)
        res = 2048 if area > 2600 else 1024
        tmp = bpy.data.materials.new("tmp_%d" % ch); tmp.use_nodes = True; o.data.materials.clear(); o.data.materials.append(tmp)
        dn = "%s_rock_%d" % (NAME, ch); nn = "%s_rock_%d_NRM" % (NAME, ch)
        for old in (dn, nn):                         # never reuse a datablock whose file has been moved away
            if old in bpy.data.images: bpy.data.images.remove(bpy.data.images[old])
        dimg = bpy.data.images.new(dn, res, res, alpha=False)
        nimg = bpy.data.images.new(nn, res // 2, res // 2, alpha=False)
        dimg.colorspace_settings.name = 'Non-Color'; nimg.colorspace_settings.name = 'Non-Color'
        set_high_material("color"); bake_to(o, dimg, 'EMIT')
        dimg.filepath_raw = os.path.join(OUT, dn + ".png"); dimg.file_format = 'PNG'; dimg.save(); dimg.colorspace_settings.name = 'sRGB'
        set_high_material("normal"); bake_to(o, nimg, 'NORMAL')
        nimg.filepath_raw = os.path.join(OUT, nn + ".png"); nimg.file_format = 'PNG'; nimg.save()
        rock_final_material(o, ch, dimg, nimg)
        BAKED[ch] = {"tris": len(o.data.polygons), "area": round(area), "res": res}
    scn.render.engine = 'BLENDER_EEVEE'
high.hide_render = True; high.hide_set(True)

# ---------------------------------------------------------------- corals
cd = np.load(os.path.join(DEV, "corals.npz"))
def coral_mat(kind):
    nm = "%s_%s" % (NAME, kind)
    fm = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
    fm.use_nodes = True; ft = fm.node_tree; ft.nodes.clear()
    bsdf = ft.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.inputs['Roughness'].default_value = 0.7
    fo = ft.nodes.new('ShaderNodeOutputMaterial'); ft.links.new(bsdf.outputs[0], fo.inputs['Surface'])
    mp = fm.mumatprop
    for coll in (mp.color.properties, mp.texture.properties, mp.float2.properties, mp.float3.properties, mp.vector.properties): coll.clear()
    if kind == "fan":
        img = bpy.data.images.load(os.path.join(OUT, "seafan.png"), check_existing=True)
        dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = img; ft.links.new(dt.outputs[0], bsdf.inputs['Base Color']); ft.links.new(dt.outputs[1], bsdf.inputs['Alpha'])
        try: fm.blend_method = 'CLIP'
        except Exception: pass
        fm.use_backface_culling = False
        mp.shaderName = "KSP/Alpha/Cutoff"
        c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
        f_ = mp.float2.properties.add(); f_.name = "_Cutoff"; f_.value = 0.45
        t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = img.name
    elif kind == "shaft":
        img = bpy.data.images.load(os.path.join(OUT, "reef_shaft.png"), check_existing=True)
        em = ft.nodes.new('ShaderNodeEmission'); dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = img
        tr = ft.nodes.new('ShaderNodeBsdfTransparent'); ad = ft.nodes.new('ShaderNodeAddShader')
        ft.links.new(dt.outputs[0], em.inputs['Color']); em.inputs['Strength'].default_value = 0.8
        ft.links.new(em.outputs[0], ad.inputs[0]); ft.links.new(tr.outputs[0], ad.inputs[1]); ft.links.new(ad.outputs[0], fo.inputs['Surface'])
        try: fm.blend_method = 'BLEND'
        except Exception: pass
        fm.use_backface_culling = False
        mp.shaderName = "KSP/Particles/Additive"
        c = mp.color.properties.add(); c.name = "_TintColor"; c.value = (0.32, 0.36, 0.38, 0.5)
        f_ = mp.float2.properties.add(); f_.name = "_InvFade"; f_.value = 1.0
        t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = img.name
    else:
        img = bpy.data.images.load(os.path.join(OUT, "coral_atlas.png"), check_existing=True)
        gimg = bpy.data.images.load(os.path.join(OUT, "coral_atlas_glow.png"), check_existing=True)
        dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = img; ft.links.new(dt.outputs[0], bsdf.inputs['Base Color'])
        gt = ft.nodes.new('ShaderNodeTexImage'); gt.image = gimg; ft.links.new(gt.outputs[0], bsdf.inputs['Emission Color']); bsdf.inputs['Emission Strength'].default_value = 1.5
        mp.shaderName = "KSP/Emissive/Diffuse"
        c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
        t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = img.name
        c = mp.color.properties.add(); c.name = "_EmissiveColor"; c.value = (1, 1, 1, 1)
        t = mp.texture.properties.add(); t.name = "_Emissive"; t.tex = gimg.name
    return fm
MATS = {}
corals = []
for ob in CJ["objects"]:
    nm = ob["name"]; Vv = cd[nm + "_v"].astype(np.float64); Ff = cd[nm + "_f"]; UV = cd[nm + "_uv"]
    piv = ob["pivot"]
    if piv: Vv = Vv - np.array(piv)
    o = mesh_from_arrays(nm, Vv, Ff, UV)
    if piv: o.location = piv
    if ob["mat"] not in MATS: MATS[ob["mat"]] = coral_mat(ob["mat"])
    o.data.materials.append(MATS[ob["mat"]])
    corals.append(o)

# (no fake sun shafts: removed after the in-game test, real light through the skylights reads better)

# ---------------------------------------------------------------- hierarchy, collider, lights, markers
root = link(bpy.data.objects.new(NAME, None)); root.muproperties.layer = 15
for o in list(chunks.values()) + corals:
    o.parent = root; o.muproperties.layer = 15
    for vg in list(o.vertex_groups): o.vertex_groups.remove(vg)
col.parent = root; col.data.materials.clear(); col.hide_render = True
col.muproperties.collider = "MU_COL_MESH"; col.muproperties.layer = 15; col.muproperties.separate = True; col.muproperties.isConvex = False
for L in CJ["lights"]:
    ld = bpy.data.lights.get(L["name"]) or bpy.data.lights.new(L["name"], 'POINT')
    ld.color = L["color"]; ld.energy = 600 * L["energy"]; ld.use_custom_distance = True; ld.cutoff_distance = L["range"]
    lo = link(bpy.data.objects.new(L["name"], ld)); lo.parent = root; lo.location = L["pos"]
tA = META["tunnels"][0]; cav = META["cavern"]["c"]
# the Fossil Reef Core: on the cavern floor, in the western lobe (ray down from inside the cavern onto the rock)
from mathutils.bvhtree import BVHTree as _BVH
_hb = _BVH.FromObject(high, bpy.context.evaluated_depsgraph_get())
for k, (fx, fy) in enumerate(((cav[0] - 5.0, cav[1] - 2.5),)):
    hit = _hb.ray_cast(Vector((fx, fy, cav[2])), Vector((0, 0, -1)), 12.0)
    fz = hit[0].z if hit[0] is not None else cav[2] - 3.8
    e = link(bpy.data.objects.new("fossil_kerbin_reefcore_%02d" % k, None)); e.parent = root; e.location = (fx, fy, fz)
    FOSSIL_AT = (fx, fy, fz)
# field-guide specimen markers: the plugin's Observe Lifeform looks for spec_<lifeform>_##
for sp, pts in CJ.get("specimens", {}).items():
    for i, pt in enumerate(pts):
        e = link(bpy.data.objects.new("spec_%s_%02d" % (sp, i), None)); e.parent = root; e.location = pt
for nm, loc in (("entrance", (tA[0][0], tA[0][1], 0.5)), ("den", (cav[0], cav[1], cav[2] - 3.5)), ("pen", (0.0, -45.0, 3.0))):
    e = link(bpy.data.objects.new(nm, None)); e.parent = root; e.location = loc
scn.frame_start = 0
counts = {o.name: [len(o.data.vertices), len(o.data.polygons)] for o in list(chunks.values()) + corals + [col]}
res = export_mu(NAME, os.path.join(OUT, NAME + ".mu")) if STEP == "all" else None
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(PREVIEW_DIR), "blend", "coral_reef.blend"), copy=True)
result = {"export": res, "baked": BAKED, "flipped": FLIPPED, "maxverts": max(v[0] for v in counts.values()),
          "rock_tris": sum(len(o.data.polygons) for o in chunks.values()), "coral_tris": sum(len(o.data.polygons) for o in corals),
          "collider_tris": len(col.data.polygons), "objects": len(counts)}
