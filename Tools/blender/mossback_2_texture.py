# Xenobiology — Greater Mossback, step 2: UVs, procedural hide material, bake to diffuse + glow PNGs,
# and set up the KSP material (KSP/Emissive/Diffuse) for the .mu exporter.
import bpy, os

OUT_DIR = globals().get("OUT_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Models\Kerbin\Mossback")
DIFF_RES = globals().get("DIFF_RES", 2048)
GLOW_RES = globals().get("GLOW_RES", 1024)
os.makedirs(OUT_DIR, exist_ok=True)
scn = bpy.context.scene
body = bpy.data.objects["mossback_body"]
me = body.data

# ---------------------------------------------------------------- UVs
bpy.context.view_layer.objects.active = body
for o in scn.objects: o.select_set(o == body)
if not me.uv_layers:
    me.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode='EDIT')
# moss clumps are many tiny islands with no detail worth texels: unwrap everything else,
# then squeeze moss into a thin strip on the right edge of the atlas.
import bmesh
bm = bmesh.from_edit_mesh(me)
pl = bm.faces.layers.int.get("part")
for f in bm.faces: f.select = (f[pl] != 2)
bmesh.update_edit_mesh(me)
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.003, area_weight=0.0, correct_aspect=True, scale_to_bounds=True)
bm = bmesh.from_edit_mesh(me)
pl = bm.faces.layers.int.get("part")
uvl = bm.loops.layers.uv.active
STRIP = 0.94
for f in bm.faces:
    for lp in f.loops:
        if f[pl] == 2:
            co = lp.vert.co
            lp[uvl].uv = (STRIP + 0.01 + 0.04 * ((co.x + 1.2) / 2.4), (co.y + 3.0) / 6.0)
        else:
            lp[uvl].uv = (lp[uvl].uv.x * (STRIP - 0.005), lp[uvl].uv.y)
bmesh.update_edit_mesh(me)
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------------------------------------------- procedural bake material
mat = bpy.data.materials.get("mossback_bake") or bpy.data.materials.new("mossback_bake")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
N = nt.nodes.new
L = nt.links.new
col_x = [0]
def node(t, **kw):
    n = N(t)
    for k, v in kw.items():
        setattr(n, k, v)
    return n
def rgb(c): return (c[0], c[1], c[2], 1.0)
def mix(a, b, fac, blend='MIX'):
    m = node('ShaderNodeMix', data_type='RGBA', blend_type=blend)
    for sock, val in ((m.inputs[6], a), (m.inputs[7], b), (m.inputs[0], fac)):
        if isinstance(val, (tuple, list)): sock.default_value = val
        elif isinstance(val, (int, float)): sock.default_value = val
        else: L(val, sock)
    return m.outputs[2]
def math_(op, a, b=None, clamp=False):
    m = node('ShaderNodeMath', operation=op, use_clamp=clamp)
    for sock, val in ((m.inputs[0], a), (m.inputs[1], b)):
        if val is None: continue
        if isinstance(val, (int, float)): sock.default_value = val
        else: L(val, sock)
    return m.outputs[0]
def ramp(fac, stops):
    r = node('ShaderNodeValToRGB')
    L(fac, r.inputs[0])
    els = r.color_ramp.elements
    while len(els) > 1: els.remove(els[-1])
    els[0].position, els[0].color = stops[0][0], rgb(stops[0][1])
    for pos, c in stops[1:]:
        e = els.new(pos); e.color = rgb(c)
    return r.outputs[0]

tc = node('ShaderNodeTexCoord')
obj = tc.outputs['Object']
sep = node('ShaderNodeSeparateXYZ'); L(obj, sep.inputs[0])
X, Y, Z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
attr = node('ShaderNodeAttribute', attribute_name="part", attribute_type='GEOMETRY')
part = attr.outputs['Fac']
def cmp_part(i):
    m = node('ShaderNodeMath', operation='COMPARE')
    L(part, m.inputs[0]); m.inputs[1].default_value = float(i); m.inputs[2].default_value = 0.5
    return m.outputs[0]

# --- hide: dorsal-ventral countershading
zf = math_('MULTIPLY', math_('SUBTRACT', Z, 1.4), 1 / 3.4, clamp=True)
hide = ramp(zf, [(0.0, (0.42, 0.35, 0.24)), (0.28, (0.47, 0.40, 0.28)), (0.48, (0.30, 0.33, 0.29)), (0.85, (0.19, 0.24, 0.23)), (1.0, (0.16, 0.20, 0.20))])
# mud-stained lower legs
legs = math_('SUBTRACT', 1.0, math_('MULTIPLY', Z, 1 / 0.9, clamp=True), clamp=True)
hide = mix(hide, (0.24, 0.19, 0.14, 1), legs)
# large-scale mottling
noise = node('ShaderNodeTexNoise'); L(obj, noise.inputs['Vector']); noise.inputs['Scale'].default_value = 1.6; noise.inputs['Detail'].default_value = 6.0
mott = math_('ADD', math_('MULTIPLY', noise.outputs['Fac'], 0.55), 0.72)
mm = node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mm.inputs[0].default_value = 1.0
L(hide, mm.inputs[6]); cm_ = node('ShaderNodeCombineColor'); L(mott, cm_.inputs[0]); L(mott, cm_.inputs[1]); L(mott, cm_.inputs[2]); L(cm_.outputs[0], mm.inputs[7])
hide = mm.outputs[2]
# leathery wrinkles: voronoi cell edges
vor = node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); L(obj, vor.inputs['Vector']); vor.inputs['Scale'].default_value = 14.0
wr = math_('MULTIPLY', math_('SUBTRACT', 1.0, math_('MULTIPLY', vor.outputs['Distance'], 20.0, clamp=True)), 0.18)
hide = mix(hide, (0.08, 0.08, 0.07, 1), wr)
# bioluminescent flank spots (|x| large, mid height)
spv = node('ShaderNodeTexVoronoi', feature='F1'); L(obj, spv.inputs['Vector']); spv.inputs['Scale'].default_value = 2.6; spv.inputs['Randomness'].default_value = 0.9
spot = math_('LESS_THAN', spv.outputs['Distance'], 0.16)
band = math_('MULTIPLY', math_('MULTIPLY', math_('SUBTRACT', math_('ABSOLUTE', X), 0.75), 3.0, clamp=True),
             math_('MULTIPLY', math_('GREATER_THAN', Z, 2.15), math_('LESS_THAN', Z, 3.7)))
band = math_('MULTIPLY', band, math_('MULTIPLY', math_('GREATER_THAN', Y, -2.0), math_('LESS_THAN', Y, 2.0)))
spots = math_('MULTIPLY', spot, band)
hide = mix(hide, (0.42, 0.66, 0.60, 1), spots)

# --- sails: hide at base, teal toward the tips, dark veins
sail_t = math_('MULTIPLY', math_('SUBTRACT', Z, 4.0), 0.85, clamp=True)
sail = ramp(sail_t, [(0.0, (0.22, 0.26, 0.24)), (0.45, (0.18, 0.38, 0.38)), (1.0, (0.30, 0.66, 0.62))])
wave = node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z'); L(obj, wave.inputs['Vector']); wave.inputs['Scale'].default_value = 3.0; wave.inputs['Distortion'].default_value = 6.0
sail = mix(sail, (0.10, 0.17, 0.17, 1), math_('MULTIPLY', math_('GREATER_THAN', wave.outputs['Fac'], 0.88), 0.35))
# --- moss
mn = node('ShaderNodeTexNoise'); L(obj, mn.inputs['Vector']); mn.inputs['Scale'].default_value = 14.0; mn.inputs['Detail'].default_value = 8.0
moss = ramp(mn.outputs['Fac'], [(0.3, (0.12, 0.24, 0.06)), (0.55, (0.26, 0.42, 0.10)), (0.75, (0.48, 0.55, 0.16))])
# --- eyes, claws, frills
eye = (0.70, 0.42, 0.06, 1)
claw = (0.72, 0.67, 0.55, 1)
fan = node('ShaderNodeAttribute', attribute_name="fan", attribute_type='GEOMETRY')
fsep = node('ShaderNodeSeparateXYZ'); L(fan.outputs['Vector'], fsep.inputs[0])
fk, fr = fsep.outputs[0], fsep.outputs[1]
frill = ramp(fr, [(0.0, (0.26, 0.27, 0.24)), (0.35, (0.38, 0.26, 0.28)), (0.8, (0.56, 0.30, 0.42)), (1.0, (0.36, 0.14, 0.26))])
veins = math_('POWER', math_('ABSOLUTE', node_sin := math_('SINE', math_('MULTIPLY', fk, 3.14159 * 12))), 12.0)
frill = mix(frill, (0.22, 0.08, 0.16, 1), math_('MULTIPLY', veins, math_('MULTIPLY', fr, 0.8)))

diffuse = hide
diffuse = mix(diffuse, sail, cmp_part(1))
diffuse = mix(diffuse, moss, cmp_part(2))
diffuse = mix(diffuse, eye, cmp_part(3))
diffuse = mix(diffuse, claw, cmp_part(4))
diffuse = mix(diffuse, frill, cmp_part(5))

# --- glow map: spots, eyes, sail tips, frill veins
glow = mix((0, 0, 0, 1), (0.25, 0.95, 0.80, 1), math_('MULTIPLY', spots, cmp_part(0)))
glow = mix(glow, (0.9, 0.55, 0.12, 1), math_('MULTIPLY', cmp_part(3), 0.45))
glow = mix(glow, (0.15, 0.55, 0.50, 1), math_('MULTIPLY', cmp_part(1), math_('MULTIPLY', sail_t, sail_t)))
glow = mix(glow, (0.45, 0.12, 0.35, 1), math_('MULTIPLY', cmp_part(5), math_('MULTIPLY', veins, 0.5)))

emit = node('ShaderNodeEmission')
out = node('ShaderNodeOutputMaterial')
L(emit.outputs[0], out.inputs['Surface'])
img_node = node('ShaderNodeTexImage')

me.materials.clear()
me.materials.append(mat)

def bake(sock, name, res):
    img = bpy.data.images.get(name)
    if img is None or img.size[0] != res:
        if img: bpy.data.images.remove(img)
        img = bpy.data.images.new(name, res, res, alpha=False)
    # keep the baked numbers as-is in the PNG (KSP renders in gamma space)
    img.colorspace_settings.name = 'Non-Color'
    img_node.image = img
    for n_ in nt.nodes: n_.select = False
    img_node.select = True
    nt.nodes.active = img_node
    L(sock, emit.inputs['Color'])
    scn.render.engine = 'CYCLES'
    scn.cycles.samples = 1
    scn.cycles.device = 'CPU'
    scn.render.bake.margin = 12
    scn.render.bake.use_clear = True
    bpy.ops.object.bake(type='EMIT')
    img.filepath_raw = os.path.join(OUT_DIR, name + ".png")
    img.file_format = 'PNG'
    img.save()
    img.colorspace_settings.name = 'sRGB'   # display the saved values as KSP will
    return img

d_img = bake(diffuse, "mossback_diffuse", DIFF_RES)
g_img = bake(glow, "mossback_glow", GLOW_RES)

# ---------------------------------------------------------------- final material: preview nodes + KSP shader properties
fm = bpy.data.materials.get("mossback") or bpy.data.materials.new("mossback")
fm.use_nodes = True
ft = fm.node_tree
ft.nodes.clear()
bsdf = ft.nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Roughness'].default_value = 0.85
fo = ft.nodes.new('ShaderNodeOutputMaterial')
ft.links.new(bsdf.outputs[0], fo.inputs['Surface'])
dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = d_img; dt.name = "_MainTex"
gt = ft.nodes.new('ShaderNodeTexImage'); gt.image = g_img; gt.name = "_Emissive"
ft.links.new(dt.outputs[0], bsdf.inputs['Base Color'])
ft.links.new(gt.outputs[0], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 1.0
me.materials.clear()
me.materials.append(fm)

mp = fm.mumatprop
mp.shaderName = "KSP/Emissive/Diffuse"
for coll in (mp.color.properties, mp.texture.properties, mp.float2.properties, mp.float3.properties, mp.vector.properties):
    coll.clear()
c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
c = mp.color.properties.add(); c.name = "_EmissiveColor"; c.value = (1, 1, 1, 1)
t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = d_img.name; t.type = False
t = mp.texture.properties.add(); t.name = "_Emissive"; t.tex = g_img.name; t.type = False
scn.render.engine = 'BLENDER_EEVEE'
result = {"diffuse": d_img.filepath_raw, "glow": g_img.filepath_raw, "uv_layers": len(me.uv_layers)}
