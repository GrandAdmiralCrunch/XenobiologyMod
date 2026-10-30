# Xenobiology — Patagiata gliders (Spiketail / Tri-tail), step 1: body, membranes, rig, weights.
# Set VARIANT = "spiketail" or "tritail" in globals before exec. Faces +Y, feet on Z = 0.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

VARIANT = globals().get("VARIANT", "spiketail")
V = {
    "spiketail": dict(scale=1.0, tail_r=1.0, span=2.35, club=True, fin=False, horns=True, spines=True, seed=11),
    "tritail":   dict(scale=0.74, tail_r=0.62, span=2.55, club=False, fin=True, horns=False, spines=False, seed=23),
}[VARIANT]
S = V["scale"]
random.seed(V["seed"])
NAME = VARIANT
SCN = VARIANT.capitalize()

if SCN in bpy.data.scenes:
    scn = bpy.data.scenes[SCN]
    for o in list(scn.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    scn = bpy.data.scenes.new(SCN)
bpy.context.window.scene = scn
scn.render.fps = 30
for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.metaballs):
    for d in [d for d in coll if d.users == 0]:
        coll.remove(d)
def link(o):
    scn.collection.objects.link(o); return o

# ---------------------------------------------------------------- skeleton points (x, y, z, r_side, r_vert)
P = {}; E = []
def v(n, x, y, z, rs, rv=None): P[n] = (Vector((x, y, z)) * S, rs * S, (rv if rv is not None else rs) * S)
def e(a, b): E.append((a, b))
tr = V["tail_r"]
v("tail5", 0, -3.75, 0.42, 0.07 * tr)
v("tail4", 0, -3.20, 0.46, 0.10 * tr)
v("tail3", 0, -2.55, 0.52, 0.15 * tr)
v("tail2", 0, -1.85, 0.60, 0.21 * (0.5 + 0.5 * tr))
v("tail1", 0, -1.20, 0.68, 0.29, 0.26)
v("hips",  0, -0.60, 0.74, 0.37, 0.31)
v("belly", 0,  0.00, 0.78, 0.41, 0.33)
v("chest", 0,  0.55, 0.84, 0.39, 0.33)
v("neck1", 0,  1.05, 1.00, 0.23, 0.23)
v("neck2", 0,  1.45, 1.15, 0.19, 0.19)
v("head",  0,  1.80, 1.20, 0.22, 0.18)
v("snout", 0,  2.22, 1.12, 0.13, 0.10)
v("nose",  0,  2.42, 1.08, 0.07, 0.06)
for a, b in [("tail5","tail4"),("tail4","tail3"),("tail3","tail2"),("tail2","tail1"),("tail1","hips"),("hips","belly"),
             ("belly","chest"),("chest","neck1"),("neck1","neck2"),("neck2","head"),("head","snout"),("snout","nose")]:
    e(a, b)
if V["club"]:
    v("club", 0, -3.85, 0.42, 0.19, 0.15)
    e("tail5", "club")
for s, sx in (("L", 1), ("R", -1)):
    v("shoulder"+s, sx*0.30, 0.55, 0.76, 0.15)
    v("elbow"+s,    sx*0.66, 0.62, 0.52, 0.12)
    v("wrist"+s,    sx*0.74, 0.78, 0.13, 0.09)
    v("hand"+s,     sx*0.80, 0.96, 0.03, 0.11, 0.05)
    e("chest","shoulder"+s); e("shoulder"+s,"elbow"+s); e("elbow"+s,"wrist"+s); e("wrist"+s,"hand"+s)
    v("hip"+s,   sx*0.28, -0.60, 0.70, 0.19)
    v("knee"+s,  sx*0.70, -0.45, 0.52, 0.14)
    v("ankle"+s, sx*0.78, -0.78, 0.13, 0.095)
    v("foot"+s,  sx*0.84, -0.52, 0.03, 0.12, 0.05)
    e("hips","hip"+s); e("hip"+s,"knee"+s); e("knee"+s,"ankle"+s); e("ankle"+s,"foot"+s)

# ---------------------------------------------------------------- metaball body -> remesh
MB_SCALE = 1.22
mb = bpy.data.metaballs.new(NAME + "_mb")
mb.resolution = 0.03 * S; mb.render_resolution = 0.03 * S; mb.threshold = 0.6
for a_, b_ in E:
    pa, ras, rav = P[a_]; pb, rbs, rbv = P[b_]
    L = (pb - pa).length
    step = max(0.02, 0.35 * min(ras, rav, rbs, rbv))
    n = max(2, int(math.ceil(L / step)) + 1)
    for i in range(n):
        t = i / (n - 1)
        el = mb.elements.new()
        el.co = pa.lerp(pb, t)
        rs = (ras + (rbs - ras) * t) * MB_SCALE; rv = (rav + (rbv - rav) * t) * MB_SCALE
        r = max(rs, rv)
        el.type = 'ELLIPSOID'; el.radius = r
        el.size_x = rs / r; el.size_y = 1.0; el.size_z = rv / r
        el.stiffness = 2.0
mbo = link(bpy.data.objects.new(NAME + "_mb", mb))
dg = bpy.context.evaluated_depsgraph_get()
body = link(bpy.data.objects.new(NAME + "_body", bpy.data.meshes.new_from_object(mbo.evaluated_get(dg))))
bpy.data.objects.remove(mbo, do_unlink=True)
bpy.context.view_layer.objects.active = body
for o in scn.objects: o.select_set(o == body)
rm = body.modifiers.new("Remesh", 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.022 * S; rm.adaptivity = 0
sm = body.modifiers.new("Smooth", 'SMOOTH'); sm.factor = 0.6; sm.iterations = 3
dc = body.modifiers.new("Decimate", 'DECIMATE')
dg = bpy.context.evaluated_depsgraph_get()
dc.ratio = min(1.0, 5500.0 / max(1, len(body.evaluated_get(dg).data.polygons)))
for m in list(body.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
me = body.data; me.name = NAME
for p in me.polygons: p.use_smooth = True
bm = bmesh.new(); bm.from_mesh(me)
for vert in bm.verts:
    co = vert.co
    # flatten the belly a little and widen the flanks where the membrane attaches (lizard cross-section)
    if -0.9 * S < co.y < 0.8 * S and co.z < 0.78 * S:
        co.z += (0.78 * S - co.z) * 0.18
    if co.z < 0: co.z = 0
bm.to_mesh(me); bm.free()

# ---------------------------------------------------------------- armature
ad_ = bpy.data.armatures.new(NAME + "_rig")
rig = link(bpy.data.objects.new(NAME + "_rig", ad_))
bpy.context.view_layer.objects.active = rig
for o in scn.objects: o.select_set(o == rig)
bpy.ops.object.mode_set(mode='EDIT')
eb = ad_.edit_bones
def pt(x): return P[x][0] if isinstance(x, str) else Vector(x) * S
def bone(name, a, b, parent=None, connect=False, deform=True):
    bn = eb.new(name); bn.head = pt(a); bn.tail = pt(b); bn.use_deform = deform
    if parent: bn.parent = eb[parent]; bn.use_connect = connect
    return bn
bone("body", "hips", "belly")
bone("spine", "belly", "chest", "body", True)
bone("neck1", "chest", "neck1", "spine", True)
bone("neck2", "neck1", "neck2", "neck1", True)
bone("head", "neck2", "snout", "neck2", True)
bone("tail1", "hips", "tail1", "body")
bone("tail2", "tail1", "tail2", "tail1", True)
bone("tail3", "tail2", "tail3", "tail2", True)
bone("tail4", "tail3", "tail4", "tail3", True)
bone("tail5", "tail4", "tail5", "tail4", True)
for s in "LR":
    bone("upperarm"+s, "shoulder"+s, "elbow"+s, "spine")
    bone("forearm"+s, "elbow"+s, "wrist"+s, "upperarm"+s, True)
    bone("hand"+s, "wrist"+s, "hand"+s, "forearm"+s, True)
    bone("thigh"+s, "hip"+s, "knee"+s, "body")
    bone("shin"+s, "knee"+s, "ankle"+s, "thigh"+s, True)
    bone("foot"+s, "ankle"+s, "foot"+s, "shin"+s, True)
# membrane spars (elongated ribs). Rest pose = fully spread (glide); clips fold them back.
SPAR = {}
span = V["span"]
for s, sx in (("L", 1), ("R", -1)):
    # fanned like a Draco lizard's patagium: leading spar swept forward, trailing spar swept back and shorter
    for k, (ry, sweep, length, par) in enumerate(((0.42, -0.30, 1.00, "spine"), (0.02, 0.25, 0.93, "spine"), (-0.38, 0.95, 0.74, "body"))):
        root = (sx * 0.34, ry, 0.90)
        tip = (sx * (0.34 + span * length * math.cos(math.atan2(sweep, span))), ry - sweep, 1.00)
        nm = f"spar{'ABC'[k]}{s}"
        bone(nm, root, tip, par)
        SPAR[nm] = (Vector(root) * S, Vector(tip) * S)
bone("saddle", (0, 0.20, 1.15), (0, 0.20, 1.40), "spine", deform=False)
for bn in eb:
    d = (bn.tail - bn.head).normalized()
    bn.align_roll(Vector((0, 0, 1)) if abs(d.z) < 0.7 else Vector((0, -1, 0)))
bpy.ops.object.mode_set(mode='OBJECT')

# heat weights for the body (spars/saddle excluded from deformation of the body itself)
for nm in list(SPAR) + ["saddle"]:
    ad_.bones[nm].use_deform = False
for o in scn.objects: o.select_set(o in (body, rig))
bpy.context.view_layer.objects.active = rig
weight_mode = "heat"
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except Exception:
    weight_mode = "envelope"; bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
for nm in SPAR:
    ad_.bones[nm].use_deform = True

bvh = BVHTree.FromPolygons([x.co.copy() for x in me.vertices], [list(p.vertices) for p in me.polygons])
def surf(origin, d):
    loc, nrm, i, dist = bvh.ray_cast(Vector(origin), Vector(d).normalized(), 50.0)
    return loc, nrm

# ---------------------------------------------------------------- parts with explicit weights
parts = []
def new_part(name, part_id):
    bm2 = bmesh.new()
    return bm2, {"name": name, "part": part_id, "weights": [], "tip": []}
def finish(bm2, info):
    m2 = bpy.data.meshes.new(info["name"]); bm2.to_mesh(m2); bm2.free()
    for p in m2.polygons: p.use_smooth = True
    o = link(bpy.data.objects.new(info["name"], m2))
    groups = {}
    for vi, wl in enumerate(info["weights"]):
        for bn, w in wl:
            if w <= 0: continue
            if bn not in groups: groups[bn] = o.vertex_groups.new(name=bn)
            groups[bn].add([vi], w, 'REPLACE')
    a = m2.attributes.new("part", 'INT', 'FACE')
    for i in range(len(m2.polygons)): a.data[i].value = info["part"]
    tp = m2.attributes.new("tipf", 'FLOAT', 'POINT')
    for i, t in enumerate(info["tip"]): tp.data[i].value = t
    parts.append(o)
def addv(bm2, info, co, weights, tip=0.0):
    vv = bm2.verts.new(co); info["weights"].append(weights); info["tip"].append(tip); return vv

# --- patagium membranes, double sided, scalloped trailing edges between spars
for s, sx in (("L", 1), ("R", -1)):
    bm2, info = new_part("membrane" + s, 1)
    A, B, C = (SPAR[f"spar{c}{s}"] for c in "ABC")
    lead_root = Vector((sx * 0.30, 0.68, 0.88)) * S
    trail_root = Vector((sx * 0.30, -0.78, 0.80)) * S
    lines = [
        (lead_root, A[0].lerp(A[1], 0.25) + Vector((0, 0.10, 0)) * S, "sparA" + s, "spine"),  # leading-edge fold
        (A[0], A[1], "sparA" + s, None),
        (B[0], B[1], "sparB" + s, None),
        (C[0], C[1], "sparC" + s, None),
        (trail_root, C[0].lerp(C[1], 0.38) - Vector((0, 0.18, 0.02)) * S, "sparC" + s, "body"),
    ]
    NU, NV = 9, 3
    grid = []  # rows across chord, cols along span
    for li in range(len(lines) - 1):
        r0, t0, b0, _ = lines[li]; r1, t1, b1, _ = lines[li + 1]
        for j in range(NV if li < len(lines) - 2 else NV + 1):
            t = j / NV
            row = []
            for k in range(NU + 1):
                u = k / NU
                p0 = r0.lerp(t0, u); p1 = r1.lerp(t1, u)
                p = p0.lerp(p1, t)
                if k == NU and 0 < t < 1:   # scalloped trailing edge between spar tips
                    p = p - (p - r0.lerp(r1, t)) * (0.32 * math.sin(math.pi * t))
                # weights: spar blend across the chord, body near the root
                ws = {}
                ws[b0] = ws.get(b0, 0) + (1 - t); ws[b1] = ws.get(b1, 0) + t
                root_w = max(0.0, 1.0 - u / 0.22)
                for kk in ws: ws[kk] *= (1 - root_w)
                rootb = "spine" if p.y > -0.2 * S else "body"
                ws[rootb] = ws.get(rootb, 0) + root_w
                row.append((p, list(ws.items())))
            grid.append(row)
    for side in (1, -1):
        vs = []
        for row in grid:
            vs.append([addv(bm2, info, p + Vector((0, 0, side * 0.008)), w) for p, w in row])
        for j in range(len(vs) - 1):
            for k in range(NU):
                f = [vs[j][k], vs[j][k+1], vs[j+1][k+1], vs[j+1][k]]
                if side * sx < 0: f = f[::-1]
                try: bm2.faces.new(f)
                except ValueError: pass
    finish(bm2, info)

# --- visible rib spars (thin tapered tubes)
for nm, (r0, t0) in SPAR.items():
    bm2, info = new_part("rib_" + nm, 4)
    axis = (t0 - r0); Ln = axis.length; d = axis.normalized()
    q = d.to_track_quat('Z', 'Y').to_matrix()
    rings = []
    for i in range(7):
        t = i / 6
        rad = (0.045 * (1 - t) + 0.012) * S
        ring = []
        for k in range(6):
            a = k / 6 * math.tau
            c = r0 + d * (Ln * t) + q @ Vector((math.cos(a) * rad, math.sin(a) * rad, 0))
            ring.append(addv(bm2, info, c, [(nm, 1.0)], t))
        rings.append(ring)
    for i in range(6):
        for k in range(6):
            bm2.faces.new([rings[i][k], rings[i][(k+1) % 6], rings[i+1][(k+1) % 6], rings[i+1][k]])
    finish(bm2, info)

def cone(bm2, info, base, direction, length, radius, bone_name, segs=6):
    d = Vector(direction).normalized()
    q = d.to_track_quat('Z', 'Y').to_matrix()
    ring = [addv(bm2, info, base + q @ Vector((math.cos(k / segs * math.tau) * radius, math.sin(k / segs * math.tau) * radius, 0)), [(bone_name, 1.0)], 0.0) for k in range(segs)]
    tipv = addv(bm2, info, base + d * length, [(bone_name, 1.0)], 1.0)
    for k in range(segs):
        bm2.faces.new([ring[k], ring[(k+1) % segs], tipv])
    bm2.faces.new(ring[::-1])

# --- claws
bm2, info = new_part("claws", 2)
for s, sx in (("L", 1), ("R", -1)):
    for pnt, bn, fwd in (("hand"+s, "hand"+s, 0.98), ("foot"+s, "foot"+s, -0.52)):
        base = P[pnt][0]
        for k in (-1, 0, 1):
            b = base + Vector((k * 0.06 + sx * 0.02, 0.06, 0.02)) * S
            cone(bm2, info, b, (k * 0.25 + sx * 0.15, 1.0, -0.35), 0.13 * S, 0.025 * S, bn)
finish(bm2, info)

# --- eyes (two big forward-set eyes)
bm2, info = new_part("eyes", 3)
for sx in (1, -1):
    loc, nrm = surf(Vector((sx * 1.5, 1.86, 1.27)) * S, (-sx, 0, 0))
    if loc is None: continue
    r = 0.075 * S
    c = loc - nrm * r * 0.3
    res = bmesh.ops.create_uvsphere(bm2, u_segments=12, v_segments=8, radius=r)
    for vv in res["verts"]:
        vv.co += c
        info["weights"].append([("head", 1.0)]); info["tip"].append(0.0)
finish(bm2, info)

# --- spiketail: tail club spikes, dorsal spines, swept horns
if V["club"]:
    bm2, info = new_part("tailspikes", 2)
    c = P["club"][0]
    for d in ((1, -0.3, 0.25), (-1, -0.3, 0.25), (0.8, -0.9, 0.1), (-0.8, -0.9, 0.1), (0.5, 0.15, 0.8), (-0.5, 0.15, 0.8)):
        dv = Vector(d).normalized()
        cone(bm2, info, c + dv * 0.13 * S, dv, 0.42 * S, 0.06 * S, "tail5")
    finish(bm2, info)
if V["spines"]:
    bm2, info = new_part("spines", 2)
    for y, bn in ((0.9, "neck1"), (0.55, "spine"), (0.25, "spine"), (-0.1, "body"), (-0.45, "body"), (-0.85, "tail1"), (-1.25, "tail1"), (-1.65, "tail2"), (-2.05, "tail2"), (-2.45, "tail3"), (-2.85, "tail4")):
        loc, nrm = surf(Vector((0, y, 3.0)) * S, (0, 0, -1))
        if loc is None: continue
        h = (0.16 if y > -1.5 else 0.11) * S
        cone(bm2, info, loc - Vector((0, 0, 0.02)) * S, (0, -0.45, 1.0), h, 0.045 * S, bn, 5)
    finish(bm2, info)
if V["horns"]:
    bm2, info = new_part("horns", 2)
    for sx in (1, -1):
        loc, nrm = surf(Vector((sx * 0.08, 1.62, 3.0)) * S, (0, 0, -1))
        if loc is None: continue
        cone(bm2, info, loc - Vector((0, 0, 0.02)) * S, (sx * 0.35, -1.0, 0.45), 0.34 * S, 0.05 * S, "head")
    finish(bm2, info)

# --- tri-tail: three-pronged horizontal tail wing
if V["fin"]:
    bm2, info = new_part("tailfin", 1)
    base = P["tail5"][0]
    for ang in (-38, 0, 38):
        d = Vector((math.sin(math.radians(ang)), -math.cos(math.radians(ang)), 0))
        sidev = Vector((-d.y, d.x, 0))
        Lf = (0.75 if ang == 0 else 0.62) * S
        for side in (1, -1):
            ring = []
            for i in range(7):
                t = i / 6
                w = 0.13 * S * math.sin(math.pi * min(1.0, t * 1.15)) * (1 - 0.3 * t)
                c = base + d * (Lf * t)
                ring.append((c + sidev * w, c - sidev * w, t))
            va = [addv(bm2, info, a + Vector((0, 0, side * 0.006)), [("tail5", 1.0)], t) for a, b, t in ring]
            vb = [addv(bm2, info, b + Vector((0, 0, side * 0.006)), [("tail5", 1.0)], t) for a, b, t in ring]
            for i in range(6):
                f = [va[i], va[i+1], vb[i+1], vb[i]]
                if side < 0: f = f[::-1]
                try: bm2.faces.new(f)
                except ValueError: pass
    finish(bm2, info)

# ---------------------------------------------------------------- tag body, join, root
a = me.attributes.new("part", 'INT', 'FACE')
for i in range(len(me.polygons)): a.data[i].value = 0
tp = me.attributes.new("tipf", 'FLOAT', 'POINT')
for o in scn.objects: o.select_set(o is body or o in parts)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
for o in scn.objects: o.select_set(False)
root = link(bpy.data.objects.new(NAME, None))
root.empty_display_type = 'ARROWS'
rig.parent = root
result = {"variant": VARIANT, "verts": len(body.data.vertices), "tris": sum(len(p.vertices) - 2 for p in body.data.polygons),
          "bones": len(ad_.bones), "weights": weight_mode, "dims": [round(x, 2) for x in body.dimensions]}
