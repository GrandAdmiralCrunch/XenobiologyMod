# Xenobiology — Greater Mossback, step 1: body mesh, armature, weights, details.
# Blender 4.2+/5.x. Builds everything in its own scene "Mossback". Creature faces +Y, feet at Z=0
# (exports to Unity +Z forward, Y up).
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

random.seed(7)
SCN = "Mossback"

# ---------------------------------------------------------------- scene
if SCN in bpy.data.scenes:
    old = bpy.data.scenes[SCN]
    for o in list(old.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    scn = old
else:
    scn = bpy.data.scenes.new(SCN)
bpy.context.window.scene = scn
scn.render.fps = 30
for m in [m for m in bpy.data.meshes if m.users == 0]:
    bpy.data.meshes.remove(m)
for a in [a for a in bpy.data.armatures if a.users == 0]:
    bpy.data.armatures.remove(a)

def link(o):
    scn.collection.objects.link(o)
    return o

# ---------------------------------------------------------------- skeleton graph for the Skin modifier
# (x, y, z, radius_side, radius_vertical)
P = {}
E = []
def v(name, x, y, z, rs, rv=None):
    P[name] = (Vector((x, y, z)), rs, rv if rv is not None else rs)
def e(a, b): E.append((a, b))

# spine: tail tip -> snout
v("tail3", 0, -4.15, 1.75, 0.10)
v("tail2", 0, -3.40, 2.25, 0.32, 0.30)
v("tail1", 0, -2.65, 2.70, 0.62, 0.60)
v("hips",  0, -1.70, 3.00, 1.20, 1.30)
v("back",  0, -0.40, 3.20, 1.42, 1.55)
v("chest", 0,  0.90, 3.30, 1.38, 1.60)
v("withers", 0, 1.85, 3.55, 1.05, 1.20)
v("neck1", 0,  2.60, 3.70, 0.82, 0.86)
v("neck2", 0,  3.20, 3.80, 0.70, 0.70)
v("head",  0,  3.75, 3.72, 0.66, 0.62)
v("snout", 0,  4.30, 3.42, 0.40, 0.36)
v("lip",   0,  4.62, 3.18, 0.22, 0.20)
for a, b in [("tail3","tail2"),("tail2","tail1"),("tail1","hips"),("hips","back"),("back","chest"),
             ("chest","withers"),("withers","neck1"),("neck1","neck2"),("neck2","head"),("head","snout"),
             ("snout","lip")]:
    e(a, b)

for s, sx in (("L", 1), ("R", -1)):
    # front legs: pillar
    v("shoulder"+s, sx*0.95, 1.55, 2.85, 0.66, 0.75)
    v("elbow"+s,    sx*1.04, 1.72, 1.70, 0.50)
    v("wrist"+s,    sx*1.06, 1.66, 0.60, 0.44)
    v("ffoot"+s,    sx*1.08, 1.76, 0.02, 0.58, 0.26)
    e("chest", "shoulder"+s); e("shoulder"+s, "elbow"+s); e("elbow"+s, "wrist"+s); e("wrist"+s, "ffoot"+s)
    # hind legs: heavier thigh, forward knee
    v("hip"+s,   sx*0.95, -1.55, 2.65, 0.80, 0.90)
    v("knee"+s,  sx*1.08, -1.20, 1.55, 0.58)
    v("hock"+s,  sx*1.08, -1.62, 0.70, 0.45)
    v("hfoot"+s, sx*1.12, -1.48, 0.02, 0.58, 0.26)
    e("hips", "hip"+s); e("hip"+s, "knee"+s); e("knee"+s, "hock"+s); e("hock"+s, "hfoot"+s)
    # forked feeding trunks
    v("trunkA"+s, sx*0.20, 4.50, 3.05, 0.17)
    v("trunkB"+s, sx*0.30, 4.62, 2.35, 0.13)
    v("trunkC"+s, sx*0.36, 4.55, 1.65, 0.09)
    v("trunkD"+s, sx*0.42, 4.75, 1.25, 0.05)
    e("snout", "trunkA"+s); e("trunkA"+s, "trunkB"+s); e("trunkB"+s, "trunkC"+s); e("trunkC"+s, "trunkD"+s)

# Metaballs give a robust organic union of the skeleton (no skin-modifier hull artifacts),
# then a voxel remesh + decimate produces clean, evenly spaced topology for skinning.
MB_SCALE = globals().get("MB_SCALE", 1.22)   # metaball element radius -> visible surface radius
mb = bpy.data.metaballs.new("mossback_mb")
mb.resolution = 0.06
mb.render_resolution = 0.06
mb.threshold = 0.6
for a_, b_ in E:
    pa, ra_s, ra_v = P[a_]; pb, rb_s, rb_v = P[b_]
    length = (pb - pa).length
    step = max(0.04, 0.35 * min(ra_s, ra_v, rb_s, rb_v))
    n = max(2, int(math.ceil(length / step)) + 1)
    for i in range(n):
        t = i / (n - 1)
        el = mb.elements.new()
        el.co = pa.lerp(pb, t)
        rs = (ra_s + (rb_s - ra_s) * t) * MB_SCALE
        rv = (ra_v + (rb_v - ra_v) * t) * MB_SCALE
        r = max(rs, rv)
        el.type = 'ELLIPSOID'
        el.radius = r
        el.size_x = rs / r
        el.size_y = 1.0
        el.size_z = rv / r
        el.stiffness = 2.0
mbo = link(bpy.data.objects.new("mossback_mb", mb))
dg = bpy.context.evaluated_depsgraph_get()
ev = mbo.evaluated_get(dg)
tmp = bpy.data.meshes.new_from_object(ev)
body = link(bpy.data.objects.new("mossback_body", tmp))
bpy.data.objects.remove(mbo, do_unlink=True)
bpy.context.view_layer.objects.active = body
for o in scn.objects: o.select_set(o == body)
rm = body.modifiers.new("Remesh", 'REMESH')
rm.mode = 'VOXEL'
rm.voxel_size = 0.045
rm.adaptivity = 0.0
sm = body.modifiers.new("Smooth", 'SMOOTH')
sm.factor = 0.6
sm.iterations = 4
dc = body.modifiers.new("Decimate", 'DECIMATE')
dc.ratio = 1.0
dg = bpy.context.evaluated_depsgraph_get()
cnt = len(body.evaluated_get(dg).data.polygons)
dc.ratio = min(1.0, 9000.0 / max(1, cnt))
for m in list(body.modifiers):
    bpy.ops.object.modifier_apply(modifier=m.name)
newme = body.data
newme.name = "mossback"
for p in newme.polygons: p.use_smooth = True

# ---------------------------------------------------------------- sculpt-ish shaping in bmesh
bm = bmesh.new(); bm.from_mesh(newme)
for vert in bm.verts:
    co = vert.co
    # broaden the barrel of the torso sideways, flatten the belly line
    if -2.0 < co.y < 2.0 and co.z > 1.9:
        t = 1.0 - abs(co.y) / 2.0
        co.x *= 1.0 + 0.10 * t
    # heavy brow ridge over the eyes
    if 3.45 < co.y < 3.95 and co.z > 3.95 and abs(co.x) < 0.55:
        co.z += 0.06
    # flat soles on the ground plane
    if co.z < 0.0:
        co.z = 0.0
    # slight lumpy hide
    n = math.sin(co.x * 5.1) * math.sin(co.y * 4.3) * math.sin(co.z * 3.7)
    co += vert.normal * (0.025 * n)
    if co.z < 0.0:
        co.z = 0.0
bm.to_mesh(newme); bm.free()

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new("mossback_rig")
rig = link(bpy.data.objects.new("mossback_rig", arm_data))
bpy.context.view_layer.objects.active = rig
for o in scn.objects: o.select_set(o == rig)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones
def bone(name, a, b, parent=None, connect=False, roll=0.0):
    bn = eb.new(name)
    bn.head = P[a][0] if isinstance(a, str) else Vector(a)
    bn.tail = P[b][0] if isinstance(b, str) else Vector(b)
    bn.roll = roll
    if parent:
        bn.parent = eb[parent]
        bn.use_connect = connect
    return bn
bone("body", "hips", "back")
bone("spine", "back", "chest", "body", True)
bone("chest", "chest", "withers", "spine", True)
bone("neck1", "withers", "neck1", "chest", True)
bone("neck2", "neck1", "neck2", "neck1", True)
bone("head", "neck2", "snout", "neck2", True)
bone("tail1", "hips", "tail1", "body")
bone("tail2", "tail1", "tail2", "tail1", True)
bone("tail3", "tail2", "tail3", "tail2", True)
for s in "LR":
    bone("trunk1"+s, "snout", "trunkA"+s, "head")
    bone("trunk2"+s, "trunkA"+s, "trunkB"+s, "trunk1"+s, True)
    bone("trunk3"+s, "trunkB"+s, "trunkC"+s, "trunk2"+s, True)
    bone("trunk4"+s, "trunkC"+s, "trunkD"+s, "trunk3"+s, True)
    bone("upperarm"+s, "shoulder"+s, "elbow"+s, "chest")
    bone("forearm"+s, "elbow"+s, "wrist"+s, "upperarm"+s, True)
    bone("ffoot"+s, "wrist"+s, "ffoot"+s, "forearm"+s, True)
    bone("thigh"+s, "hip"+s, "knee"+s, "body")
    bone("shin"+s, "knee"+s, "hock"+s, "thigh"+s, True)
    bone("hfoot"+s, "hock"+s, "hfoot"+s, "shin"+s, True)
# consistent rolls so local X is the sideways hinge axis everywhere
for bn in eb:
    bn.align_roll(Vector((0, 0, 1)) if abs((bn.tail - bn.head).normalized().z) < 0.7 else Vector((0, -1, 0)))
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------------------------------------------- weights (automatic heat, envelope fallback)
for o in scn.objects: o.select_set(o in (body, rig))
bpy.context.view_layer.objects.active = rig
weight_mode = "heat"
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except Exception:
    weight_mode = "envelope"
    bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
unweighted = sum(1 for vv in body.data.vertices if not any(g.weight > 0.01 for g in vv.groups))

# ---------------------------------------------------------------- surface queries for placing details
bvh = BVHTree.FromPolygons([vv.co.copy() for vv in body.data.vertices], [list(p.vertices) for p in body.data.polygons])
def surf(origin, direction):
    loc, nrm, idx, dist = bvh.ray_cast(Vector(origin), Vector(direction).normalized(), 50.0)
    return loc, nrm
def spine_top(y, x=0.0):
    loc, nrm = surf((x, y, 9.0), (0, 0, -1))
    return loc.z if loc is not None else 4.2

# ---------------------------------------------------------------- extra bones: display frills behind the head
bpy.context.view_layer.objects.active = rig
for o in scn.objects: o.select_set(o == rig)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones
FRILL = {}
for s_, sx in (("L", 1), ("R", -1)):
    loc, nrm = surf((sx * 2.0, 3.30, 4.05), (-sx, 0, 0))
    root_pt = (loc - nrm * 0.05) if loc is not None else Vector((sx * 0.6, 3.3, 4.05))
    FRILL[s_] = root_pt
    bn = eb.new("frill" + s_)
    bn.head = root_pt
    bn.tail = root_pt + Vector((sx * 0.35, -0.45, 0.35))
    bn.parent = eb["head"]
    bn.align_roll(Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------------------------------------------- detail parts (joined, rigidly weighted)
def add_part(me_builder, bone_name, name):
    bm2 = bmesh.new()
    me_builder(bm2)
    m2 = bpy.data.meshes.new(name)
    bm2.to_mesh(m2); bm2.free()
    for p in m2.polygons: p.use_smooth = True
    o = link(bpy.data.objects.new(name, m2))
    vg = o.vertex_groups.new(name=bone_name)
    vg.add(list(range(len(m2.vertices))), 1.0, 'REPLACE')
    return o

parts = []
# dorsal sails: curved fleshy plates along the spine, tallest over the back
sail_spots = [(-2.45, 0.45, "tail1"), (-1.75, 1.05, "body"), (-1.0, 1.45, "body"), (-0.25, 1.70, "spine"),
              (0.50, 1.60, "spine"), (1.20, 1.25, "chest"), (1.85, 0.70, "chest")]
for i, (y, h, bn) in enumerate(sail_spots):
    base = spine_top(y) - 0.15
    def build(bm2, y=y, h=h, base=base):
        w = 0.55 + 0.25 * h
        res_u, res_v = 6, 6
        rows = []
        for j in range(res_v + 1):
            t = j / res_v
            row = []
            for k in range(res_u + 1):
                u = k / res_u - 0.5
                width = w * (1 - t ** 1.6)
                yy = y + u * width - 0.25 * t * h          # swept back
                zz = base + t * h * (1 - 0.2 * abs(u))
                thick = 0.07 * (1 - t) + 0.015
                row.append((yy, zz, thick))
            rows.append(row)
        for side in (1, -1):
            vs = [[bm2.verts.new((side * r[2], r[0], r[1])) for r in row] for row in rows]
            for j in range(res_v):
                for k in range(res_u):
                    f = [vs[j][k], vs[j][k+1], vs[j+1][k+1], vs[j+1][k]]
                    bm2.faces.new(f if side > 0 else f[::-1])
    parts.append(add_part(build, bn, f"sail{i}"))

# moss clumps on the back and between the sails
moss_bones = [("body", -1.7, -0.6), ("spine", -0.6, 0.9), ("chest", 0.9, 1.9), ("tail1", -2.6, -1.7)]
for bn, y0, y1 in moss_bones:
    def build(bm2, y0=y0, y1=y1):
        for _ in range(22):
            y = random.uniform(y0, y1)
            x = random.gauss(0, 0.45)
            loc, nrm = surf((x, y, 9.0), (0, 0, -1))
            if loc is None or nrm.z < 0.45:
                continue
            r = random.uniform(0.14, 0.32)
            res = bmesh.ops.create_icosphere(bm2, subdivisions=1, radius=r)
            rot = nrm.to_track_quat('Z', 'Y').to_matrix()
            for vv in res["verts"]:
                c = vv.co.copy()
                c.z *= 0.45
                c += c.normalized() * random.uniform(-0.04, 0.04)
                vv.co = loc + rot @ c - nrm * 0.03
    parts.append(add_part(build, bn, "moss_" + bn))

# eyes: two lateral + one median brow eye
EYES = []
def build_eyes(bm2):
    shots = [((2.0, 3.95, 3.98), (-1, 0, 0), 0.17), ((-2.0, 3.95, 3.98), (1, 0, 0), 0.17), ((0.0, 4.02, 7.0), (0, 0, -1), 0.13)]
    for origin, d, r in shots:
        loc, nrm = surf(origin, d)
        if loc is None: continue
        c = loc - nrm * (r * 0.35)
        EYES.append(c)
        res = bmesh.ops.create_uvsphere(bm2, u_segments=14, v_segments=10, radius=r)
        for vv in res["verts"]: vv.co += c
parts.append(add_part(build_eyes, "head", "eyes"))

# toes: three blunt claws per foot
for s, sx in (("L", 1), ("R", -1)):
    for bn, fy, fx in (("ffoot"+s, 1.78, 1.08), ("hfoot"+s, -1.48, 1.12)):
        def build(bm2, sx=sx, fy=fy, fx=fx):
            for k in (-1, 0, 1):
                res = bmesh.ops.create_cone(bm2, cap_ends=True, segments=8, radius1=0.11, radius2=0.03, depth=0.26)
                rot = Matrix.Rotation(math.radians(-80), 4, 'X')
                bmesh.ops.transform(bm2, matrix=rot, verts=res["verts"])
                for vv in res["verts"]:
                    vv.co += Vector((sx * fx + k * 0.26, fy + 0.50 - abs(k) * 0.1, 0.10))
        parts.append(add_part(build, bn, "toes_" + bn))

# beak plate at the mouth, between the trunks
def build_beak(bm2):
    res = bmesh.ops.create_cone(bm2, cap_ends=True, segments=10, radius1=0.2, radius2=0.04, depth=0.38)
    rot = Matrix.Rotation(math.radians(-115), 4, 'X')
    bmesh.ops.transform(bm2, matrix=rot, verts=res["verts"])
    for vv in res["verts"]:
        vv.co.x *= 1.3
        vv.co += Vector((0, 4.70, 3.02))
parts.append(add_part(build_beak, "head", "beak"))

# display frills: ribbed, scalloped fan membranes behind the head (spread wide when alarmed)
FAN = {}
for s_, sx in (("L", 1), ("R", -1)):
    def build(bm2, s_=s_, sx=sx):
        o = FRILL[s_]
        rings, spokes = 5, 12
        grid = []
        for i in range(rings + 1):
            fr = i / rings
            row = []
            for k in range(spokes + 1):
                fk = k / spokes
                a = math.radians(-15 + 120 * fk)              # fan from backwards to up-and-forward
                prof = 0.45 + 0.55 * math.sin(math.pi * (0.15 + 0.85 * fk))   # leaf-shaped outline
                scallop = 1.0 - 0.10 * fr * (0.5 + 0.5 * math.cos(fk * spokes * math.pi * 2))
                rr = (0.06 + 0.85 * fr) * prof * scallop
                p_ = Vector((sx * (0.05 + 0.22 * fr), -math.cos(a) * rr, math.sin(a) * rr * 0.95))
                row.append((o + p_, fk, fr))
            grid.append(row)
        for side in (1, -1):
            vs = []
            for row in grid:
                vrow = []
                for p_, fk, fr in row:
                    vv = bm2.verts.new(p_ + Vector((side * 0.012 * sx, 0, 0)))
                    FAN[vv.co.copy().freeze()] = (fk, fr)
                    vrow.append(vv)
                vs.append(vrow)
            for i in range(rings):
                for k in range(spokes):
                    f = [vs[i][k], vs[i][k+1], vs[i+1][k+1], vs[i+1][k]]
                    bm2.faces.new(f if side * sx > 0 else f[::-1])
    parts.append(add_part(build, "frill" + s_, "frill" + s_))

# tag a material slot index per part type (0 hide, 1 sail, 2 moss, 3 eye, 4 claw) via an attribute
def tag(o, val):
    a = o.data.attributes.new("part", 'INT', 'FACE')
    for i in range(len(o.data.polygons)): a.data[i].value = val
tag(body, 0)
for o in parts:
    tag(o, 5 if o.name.startswith("frill") else 1 if o.name.startswith("sail") else 2 if o.name.startswith("moss") else 3 if o.name == "eyes" else 4)

# join everything into the body
for o in scn.objects: o.select_set(o is body or o in parts)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
body.name = "mossback_body"
body.data.name = "mossback"

# fan coordinates for the frill material (spoke position, radial distance)
fa = body.data.attributes.new("fan", 'FLOAT2', 'POINT')
for vv in body.data.vertices:
    key = vv.co.copy().freeze()
    fa.data[vv.index].vector = FAN.get(key, (0.0, 0.0))

# root empty: the exported model's root
root = link(bpy.data.objects.new("mossback", None))
root.empty_display_type = 'ARROWS'
rig.parent = root

result = {"verts": len(body.data.vertices), "tris": sum(len(p.vertices) - 2 for p in body.data.polygons),
          "bones": len(arm_data.bones), "weights": weight_mode, "unweighted_body_verts": unweighted,
          "dims": [round(x, 2) for x in body.dimensions]}
