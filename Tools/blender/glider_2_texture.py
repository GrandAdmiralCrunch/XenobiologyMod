# Xenobiology — Patagiata gliders, step 2: UVs, procedural scales/membrane material, bake, KSP material.
import bpy, os

VARIANT = globals().get("VARIANT", "spiketail")
OUT_DIR = globals().get("OUT_DIR", os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Models\Kerbin", VARIANT.capitalize()))
os.makedirs(OUT_DIR, exist_ok=True)
RES = globals().get("RES", 1024)
scn = bpy.context.scene
body = bpy.data.objects[VARIANT + "_body"]
me = body.data
S = 1.0 if VARIANT == "spiketail" else 0.74

PAL = {
    # dorsal, flank, belly, stripe, membrane base, membrane rim, membrane vein, eye, bone, bone tip
    "spiketail": dict(dorsal=(0.10, 0.36, 0.30), flank=(0.13, 0.40, 0.46), belly=(0.70, 0.70, 0.52), stripe=(0.04, 0.15, 0.14),
                      mem=(0.16, 0.52, 0.50), rim=(0.88, 0.62, 0.14), vein=(0.05, 0.22, 0.24), eye=(0.95, 0.72, 0.08),
                      bone=(0.80, 0.76, 0.62), tip=(0.12, 0.10, 0.09), stripes=True),
    "tritail":   dict(dorsal=(0.14, 0.34, 0.50), flank=(0.20, 0.46, 0.60), belly=(0.80, 0.80, 0.86), stripe=(0.10, 0.18, 0.36),
                      mem=(0.30, 0.42, 0.78), rim=(0.78, 0.60, 0.90), vein=(0.12, 0.16, 0.40), eye=(0.55, 0.95, 0.85),
                      bone=(0.82, 0.82, 0.86), tip=(0.40, 0.30, 0.55), stripes=False),
}[VARIANT]

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

# --- skin: countershaded by surface normal (top dark, belly pale)
up = m_('MULTIPLY', m_('ADD', NZ, 1.0), 0.5)
skin = ramp(up, [(0.0, PAL["belly"]), (0.32, PAL["belly"]), (0.48, PAL["flank"]), (0.75, PAL["dorsal"]), (1.0, PAL["dorsal"])])
# scales: small voronoi cells with dark seams
sc = node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); L(obj, sc.inputs['Vector']); sc.inputs['Scale'].default_value = 34.0 / S
seam = m_('SUBTRACT', 1.0, m_('MULTIPLY', sc.outputs['Distance'], 18.0, clamp=True))
skin = mix(skin, (0.03, 0.06, 0.06), m_('MULTIPLY', seam, 0.35))
nz = node('ShaderNodeTexNoise'); L(obj, nz.inputs['Vector']); nz.inputs['Scale'].default_value = 3.0 / S; nz.inputs['Detail'].default_value = 5.0
skin = mul_rgb(skin, m_('ADD', m_('MULTIPLY', nz.outputs['Fac'], 0.5), 0.75))
if PAL["stripes"]:
    # dark chevron bands across the back and tail
    band = m_('SINE', m_('MULTIPLY', m_('ADD', Y, m_('MULTIPLY', m_('ABSOLUTE', X), 1.2)), 6.0 / S))
    bandm = m_('MULTIPLY', m_('GREATER_THAN', band, 0.55), m_('GREATER_THAN', NZ, 0.25))
    skin = mix(skin, PAL["stripe"], m_('MULTIPLY', bandm, 0.8))
else:
    # pale dorsal spots
    sp = node('ShaderNodeTexVoronoi', feature='F1'); L(obj, sp.inputs['Vector']); sp.inputs['Scale'].default_value = 7.0 / S
    spots = m_('MULTIPLY', m_('LESS_THAN', sp.outputs['Distance'], 0.16), m_('GREATER_THAN', NZ, 0.2))
    skin = mix(skin, (0.70, 0.82, 0.95), m_('MULTIPLY', spots, 0.8))

# --- membrane: veined, darkening toward the rim, bright warning rim
dist = m_('DIVIDE', m_('SUBTRACT', m_('ABSOLUTE', X), 0.35 * S), 2.2 * S)
mem = ramp(m_('MAXIMUM', dist, 0.0), [(0.0, PAL["dorsal"]), (0.15, PAL["mem"]), (0.82, PAL["mem"]), (0.9, PAL["rim"]), (1.0, PAL["rim"])])
vn = node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y'); L(obj, vn.inputs['Vector'])
vn.inputs['Scale'].default_value = 3.2 / S; vn.inputs['Distortion'].default_value = 2.5; vn.inputs['Detail'].default_value = 3.0
mem = mix(mem, PAL["vein"], m_('MULTIPLY', m_('GREATER_THAN', vn.outputs['Fac'], 0.82), 0.6))
mspot = node('ShaderNodeTexVoronoi', feature='F1'); L(obj, mspot.inputs['Vector']); mspot.inputs['Scale'].default_value = 5.0 / S
mem = mix(mem, PAL["rim"], m_('MULTIPLY', m_('LESS_THAN', mspot.outputs['Distance'], 0.10), 0.5))
# --- bone parts (claws, spikes, horns) with dark tips; ribs; eyes
bone = mix(PAL["bone"], PAL["tip"], m_('POWER', tipf, 2.2))
rib = mix(PAL["dorsal"], PAL["rim"], m_('POWER', tipf, 3.0))

col = skin
col = mix(col, mem, is_part(1))
col = mix(col, bone, is_part(2))
col = mix(col, PAL["eye"], is_part(3))
col = mix(col, rib, is_part(4))
glow = mix((0, 0, 0), PAL["eye"], m_('MULTIPLY', is_part(3), 0.55))
glow = mix(glow, PAL["rim"], m_('MULTIPLY', is_part(1), m_('MULTIPLY', m_('LESS_THAN', mspot.outputs['Distance'], 0.10), 0.35 if VARIANT == "tritail" else 0.0)))

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
