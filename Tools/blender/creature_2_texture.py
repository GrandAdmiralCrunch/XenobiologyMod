# Xenobiology — Tundrik / Screechwing, step 2: UVs, procedural fur / hide / membrane material, bake, KSP material.
import bpy, os

VARIANT = globals().get("VARIANT", "tundrik")
OUT_DIR = globals().get("OUT_DIR", os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Models\Kerbin", VARIANT.capitalize()))
os.makedirs(OUT_DIR, exist_ok=True)
RES = globals().get("RES", 1024)
scn = bpy.context.scene
body = bpy.data.objects[VARIANT + "_body"]
me = body.data
S = 1.0

# ---------------------------------------------------------------- UVs
bpy.context.view_layer.objects.active = body
for o in scn.objects: o.select_set(o == body)
if not me.uv_layers: me.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------------------------------------------- node helpers
mat = bpy.data.materials.get(VARIANT + "_bake") or bpy.data.materials.new(VARIANT + "_bake")
mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
N = nt.nodes.new; L = nt.links.new
def node(t, **kw):
    n = N(t)
    for k, v in kw.items(): setattr(n, k, v)
    return n
def c4(c): return (c[0], c[1], c[2], 1.0)
def feed(sock, val):
    if isinstance(val, (tuple, list)): sock.default_value = val if len(val) == 4 else c4(val)
    elif isinstance(val, (int, float)): sock.default_value = val
    else: L(val, sock)
def mix(a, b, fac):
    m = node('ShaderNodeMix', data_type='RGBA', blend_type='MIX')
    feed(m.inputs[6], a); feed(m.inputs[7], b); feed(m.inputs[0], fac)
    return m.outputs[2]
def mul_rgb(a, f):
    m = node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); m.inputs[0].default_value = 1.0
    feed(m.inputs[6], a)
    cc = node('ShaderNodeCombineColor'); feed(cc.inputs[0], f); feed(cc.inputs[1], f); feed(cc.inputs[2], f)
    L(cc.outputs[0], m.inputs[7]); return m.outputs[2]
def m_(op, a, b=None, clamp=False):
    m = node('ShaderNodeMath', operation=op, use_clamp=clamp)
    feed(m.inputs[0], a)
    if b is not None: feed(m.inputs[1], b)
    return m.outputs[0]
def ramp(fac, stops):
    r = node('ShaderNodeValToRGB'); L(fac, r.inputs[0])
    els = r.color_ramp.elements
    while len(els) > 1: els.remove(els[-1])
    els[0].position, els[0].color = stops[0][0], c4(stops[0][1])
    for pos, c in stops[1:]:
        e = els.new(pos); e.color = c4(c)
    return r.outputs[0]
def attr(name):
    return node('ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY').outputs['Fac']
def is_part(i):
    m = node('ShaderNodeMath', operation='COMPARE'); L(part, m.inputs[0]); m.inputs[1].default_value = float(i); m.inputs[2].default_value = 0.5
    return m.outputs[0]

tc = node('ShaderNodeTexCoord'); obj = tc.outputs['Object']
sep = node('ShaderNodeSeparateXYZ'); L(obj, sep.inputs[0])
X, Y, Z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
part = attr("part"); tipf = attr("tipf")
gn = node('ShaderNodeNewGeometry'); nsep = node('ShaderNodeSeparateXYZ'); L(gn.outputs['Normal'], nsep.inputs[0])
NZ = nsep.outputs[2]


if VARIANT == "tundrik":
    # ---- shaggy fur: cream belly, blue-grey back, strand streaks combed backwards, darker legs
    up = m_('MULTIPLY', m_('ADD', NZ, 1.0), 0.5)
    fur = ramp(up, [(0.0, (0.86, 0.85, 0.80)), (0.45, (0.86, 0.85, 0.80)), (0.62, (0.70, 0.73, 0.76)), (0.85, (0.52, 0.58, 0.66)), (1.0, (0.46, 0.52, 0.60))])
    strand_v = node('ShaderNodeMapping'); L(obj, strand_v.inputs['Vector']); strand_v.inputs['Scale'].default_value = (28.0, 3.0, 28.0)
    st = node('ShaderNodeTexNoise'); L(strand_v.outputs[0], st.inputs['Vector']); st.inputs['Scale'].default_value = 2.0; st.inputs['Detail'].default_value = 8.0
    fur = mul_rgb(fur, m_('ADD', m_('MULTIPLY', st.outputs['Fac'], 0.55), 0.70))
    legs = m_('SUBTRACT', 1.0, m_('MULTIPLY', Z, 1 / 0.55, clamp=True), clamp=True)
    fur = mix(fur, (0.38, 0.40, 0.45), m_('MULTIPLY', legs, 0.85))
    # pale mask around the eyes and a darker saddle
    saddle = m_('MULTIPLY', m_('LESS_THAN', m_('ABSOLUTE', m_('SUBTRACT', Y, -0.2)), 0.45), m_('GREATER_THAN', NZ, 0.6))
    fur = mix(fur, (0.36, 0.42, 0.50), m_('MULTIPLY', saddle, 0.45))
    col = fur
    col = mix(col, (0.10, 0.09, 0.08), is_part(2))       # claws
    col = mix(col, mix((0.16, 0.14, 0.13), (0.05, 0.05, 0.05), m_('POWER', tipf, 2.0)), is_part(2))
    col = mix(col, (0.02, 0.02, 0.03), is_part(3))       # eyes
    col = mix(col, mix((0.86, 0.45, 0.52), (0.95, 0.62, 0.66), tipf), is_part(4))   # star nose
    glow = mix((0, 0, 0), (0, 0, 0), 0.0)
else:
    # ---- screechwing: sandy desert hide, rusty dorsal stripe, dusky rose membranes with dark finger veins
    up = m_('MULTIPLY', m_('ADD', NZ, 1.0), 0.5)
    hide = ramp(up, [(0.0, (0.86, 0.72, 0.50)), (0.4, (0.80, 0.62, 0.36)), (0.7, (0.66, 0.42, 0.20)), (1.0, (0.46, 0.25, 0.12))])
    nz = node('ShaderNodeTexNoise'); L(obj, nz.inputs['Vector']); nz.inputs['Scale'].default_value = 9.0; nz.inputs['Detail'].default_value = 6.0
    hide = mul_rgb(hide, m_('ADD', m_('MULTIPLY', nz.outputs['Fac'], 0.4), 0.80))
    dist = m_('ABSOLUTE', X)
    mem = ramp(m_('DIVIDE', dist, 1.9), [(0.0, (0.62, 0.36, 0.24)), (0.55, (0.58, 0.30, 0.24)), (0.9, (0.38, 0.16, 0.14)), (1.0, (0.24, 0.10, 0.09))])
    vn = node('ShaderNodeTexWave', wave_type='RINGS', rings_direction='SPHERICAL'); L(obj, vn.inputs['Vector'])
    vn.inputs['Scale'].default_value = 3.0; vn.inputs['Distortion'].default_value = 3.0
    mem = mix(mem, (0.22, 0.10, 0.08), m_('MULTIPLY', m_('GREATER_THAN', vn.outputs['Fac'], 0.86), 0.45))
    col = hide
    col = mix(col, mem, is_part(1))
    col = mix(col, (0.92, 0.88, 0.78), is_part(2))       # teeth
    col = mix(col, (0.85, 0.12, 0.08), is_part(3))       # eyes
    col = mix(col, (0.30, 0.12, 0.10), is_part(4))       # finger bones / ribs
    col = mix(col, mix((0.85, 0.55, 0.50), (0.60, 0.30, 0.28), tipf), is_part(5))    # inner ear / mouth
    glow = mix((0, 0, 0), (0.75, 0.10, 0.05), m_('MULTIPLY', is_part(3), 0.8))

emit = node('ShaderNodeEmission'); out = node('ShaderNodeOutputMaterial'); L(emit.outputs[0], out.inputs['Surface'])
img_node = node('ShaderNodeTexImage')
me.materials.clear(); me.materials.append(mat)

def bake(sock, name, res):
    img = bpy.data.images.get(name)
    if img is None or img.size[0] != res:
        if img: bpy.data.images.remove(img)
        img = bpy.data.images.new(name, res, res, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    img_node.image = img
    for n_ in nt.nodes: n_.select = False
    img_node.select = True; nt.nodes.active = img_node
    L(sock, emit.inputs['Color'])
    scn.render.engine = 'CYCLES'; scn.cycles.samples = 1; scn.cycles.device = 'CPU'
    scn.render.bake.margin = 8; scn.render.bake.use_clear = True
    bpy.ops.object.bake(type='EMIT')
    img.filepath_raw = os.path.join(OUT_DIR, name + ".png"); img.file_format = 'PNG'; img.save()
    img.colorspace_settings.name = 'sRGB'
    return img

d_img = bake(col, VARIANT + "_diffuse", RES)
g_img = bake(glow, VARIANT + "_glow", RES // 4)

fm = bpy.data.materials.get(VARIANT) or bpy.data.materials.new(VARIANT)
fm.use_nodes = True
ft = fm.node_tree; ft.nodes.clear()
bsdf = ft.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.inputs['Roughness'].default_value = 0.55
fo = ft.nodes.new('ShaderNodeOutputMaterial'); ft.links.new(bsdf.outputs[0], fo.inputs['Surface'])
dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = d_img
gt = ft.nodes.new('ShaderNodeTexImage'); gt.image = g_img
ft.links.new(dt.outputs[0], bsdf.inputs['Base Color']); ft.links.new(gt.outputs[0], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 1.0
me.materials.clear(); me.materials.append(fm)
mp = fm.mumatprop
mp.shaderName = "KSP/Emissive/Diffuse"
for coll in (mp.color.properties, mp.texture.properties, mp.float2.properties, mp.float3.properties, mp.vector.properties): coll.clear()
c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
c = mp.color.properties.add(); c.name = "_EmissiveColor"; c.value = (1, 1, 1, 1)
t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = d_img.name
t = mp.texture.properties.add(); t.name = "_Emissive"; t.tex = g_img.name
scn.render.engine = 'BLENDER_EEVEE'
result = {"diffuse": d_img.filepath_raw, "glow": g_img.filepath_raw}
