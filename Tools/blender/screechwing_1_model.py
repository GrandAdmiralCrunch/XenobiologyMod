# Xenobiology — Screechwing (desert bat with fore- and hind-wings), step 1: body, membranes, ears, jaw, rig.
# Faces +Y. Origin at the body's centre of mass (it is always airborne). Rest pose = wings fully spread.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

NAME = "screechwing"; SCN = "Screechwing"
random.seed(9)
if SCN in bpy.data.scenes:
    scn = bpy.data.scenes[SCN]
    for o in list(scn.objects): bpy.data.objects.remove(o, do_unlink=True)
else:
    scn = bpy.data.scenes.new(SCN)
bpy.context.window.scene = scn
scn.render.fps = 30
for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.metaballs):
    for d in [d for d in coll if d.users == 0]: coll.remove(d)
def link(o): scn.collection.objects.link(o); return o

P = {}; E = []
def v(n, x, y, z, rs, rv=None): P[n] = (Vector((x, y, z)), rs, rv if rv is not None else rs)
def e(a, b): E.append((a, b))
v("tail3", 0, -1.45, -0.02, 0.025)
v("tail2", 0, -1.05, 0.00, 0.04)
v("tail1", 0, -0.62, 0.01, 0.07)
v("hips",  0, -0.32, 0.00, 0.13, 0.12)
v("belly", 0, -0.05, 0.00, 0.17, 0.15)
v("chest", 0,  0.18, 0.02, 0.19, 0.17)
v("neck",  0,  0.36, 0.05, 0.12, 0.12)
v("head",  0,  0.52, 0.07, 0.14, 0.13)
v("snout", 0,  0.70, 0.04, 0.08, 0.07)
for a, b in [("tail3","tail2"),("tail2","tail1"),("tail1","hips"),("hips","belly"),("belly","chest"),("chest","neck"),("neck","head"),("head","snout")]: e(a, b)
for s, sx in (("L", 1), ("R", -1)):
    v("sh"+s, sx*0.13, 0.20, 0.06, 0.07); v("el"+s, sx*0.55, 0.06, 0.06, 0.045); v("wr"+s, sx*0.95, 0.24, 0.06, 0.035)
    e("chest", "sh"+s); e("sh"+s, "el"+s); e("el"+s, "wr"+s)
    v("hip"+s, sx*0.10, -0.30, -0.02, 0.06); v("kn"+s, sx*0.36, -0.52, -0.03, 0.04); v("ft"+s, sx*0.46, -0.80, -0.04, 0.03)
    e("hips", "hip"+s); e("hip"+s, "kn"+s); e("kn"+s, "ft"+s)

mb = bpy.data.metaballs.new(NAME + "_mb"); mb.resolution = 0.012; mb.render_resolution = 0.012; mb.threshold = 0.6
for a_, b_ in E:
    pa, ras, rav = P[a_]; pb, rbs, rbv = P[b_]
    L = (pb - pa).length; step = max(0.008, 0.35 * min(ras, rav, rbs, rbv)); n = max(2, int(math.ceil(L / step)) + 1)
    for i in range(n):
        t = i / (n - 1); el = mb.elements.new(); el.co = pa.lerp(pb, t)
        rs = (ras + (rbs - ras) * t) * 1.22; rv = (rav + (rbv - rav) * t) * 1.22; r = max(rs, rv)
        el.type = 'ELLIPSOID'; el.radius = r; el.size_x = rs / r; el.size_y = 1; el.size_z = rv / r; el.stiffness = 2.0
mbo = link(bpy.data.objects.new(NAME + "_mb", mb))
dg = bpy.context.evaluated_depsgraph_get()
body = link(bpy.data.objects.new(NAME + "_body", bpy.data.meshes.new_from_object(mbo.evaluated_get(dg))))
bpy.data.objects.remove(mbo, do_unlink=True)
bpy.context.view_layer.objects.active = body
for o in scn.objects: o.select_set(o == body)
rm = body.modifiers.new("Remesh", 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.01; rm.adaptivity = 0
sm = body.modifiers.new("Smooth", 'SMOOTH'); sm.factor = 0.6; sm.iterations = 3
dc = body.modifiers.new("Decimate", 'DECIMATE')
dg = bpy.context.evaluated_depsgraph_get()
dc.ratio = min(1.0, 3500.0 / max(1, len(body.evaluated_get(dg).data.polygons)))
for m in list(body.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
me = body.data; me.name = NAME
for p in me.polygons: p.use_smooth = True

# ---------------------------------------------------------------- rig
ad_ = bpy.data.armatures.new(NAME + "_rig"); rig = link(bpy.data.objects.new(NAME + "_rig", ad_))
bpy.context.view_layer.objects.active = rig
for o in scn.objects: o.select_set(o == rig)
bpy.ops.object.mode_set(mode='EDIT'); eb = ad_.edit_bones
def pt(x): return P[x][0] if isinstance(x, str) else Vector(x)
def bone(name, a, b, parent=None, connect=False, deform=True):
    bn = eb.new(name); bn.head = pt(a); bn.tail = pt(b); bn.use_deform = deform
    if parent: bn.parent = eb[parent]; bn.use_connect = connect
    return bn
bone("body", "hips", "belly"); bone("spine", "belly", "chest", "body", True)
bone("neck", "chest", "neck", "spine", True); bone("head", "neck", "snout", "neck", True)
bone("jaw", (0, 0.50, 0.00), (0, 0.70, -0.02), "head")
bone("tail1", "hips", "tail1", "body"); bone("tail2", "tail1", "tail2", "tail1", True); bone("tail3", "tail2", "tail3", "tail2", True)
FING = {}
for s, sx in (("L", 1), ("R", -1)):
    bone("arm"+s, "sh"+s, "el"+s, "spine"); bone("fore"+s, "el"+s, "wr"+s, "arm"+s, True)
    tips = [(sx*1.78, 0.40, 0.07), (sx*1.80, -0.12, 0.06), (sx*1.42, -0.58, 0.05), (sx*0.98, -0.80, 0.04)]
    for i, tp in enumerate(tips):
        bone(f"fing{i}{s}", "wr"+s, tp, "fore"+s)
        FING[f"fing{i}{s}"] = (P["wr"+s][0].copy(), Vector(tp))
    bone("thigh"+s, "hip"+s, "kn"+s, "body"); bone("shin"+s, "kn"+s, "ft"+s, "thigh"+s, True)
    ear_root = Vector((sx * 0.07, 0.50, 0.17))
    bone("ear"+s, ear_root, ear_root + Vector((sx * 0.10, -0.08, 0.32)), "head")
for bn in eb:
    d = (bn.tail - bn.head).normalized()
    bn.align_roll(Vector((0, 0, 1)) if abs(d.z) < 0.7 else Vector((0, -1, 0)))
bpy.ops.object.mode_set(mode='OBJECT')
nondeform = [b.name for b in ad_.bones if b.name.startswith(("fing", "ear", "jaw"))]
for nm in nondeform: ad_.bones[nm].use_deform = False
for o in scn.objects: o.select_set(o in (body, rig))
bpy.context.view_layer.objects.active = rig
weight_mode = "heat"
try: bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except Exception:
    weight_mode = "envelope"; bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
for nm in nondeform: ad_.bones[nm].use_deform = True
bvh = BVHTree.FromPolygons([x.co.copy() for x in me.vertices], [list(p.vertices) for p in me.polygons])
def surf(origin, d):
    loc, nrm, i, dist = bvh.ray_cast(Vector(origin), Vector(d).normalized(), 50.0); return loc, nrm

parts = []
def new_part(name, pid): return bmesh.new(), {"name": name, "part": pid, "weights": [], "tip": []}
def addv(bm2, info, co, w, tip=0.0):
    vv = bm2.verts.new(co); info["weights"].append(w); info["tip"].append(tip); return vv
def finish(bm2, info):
    m2 = bpy.data.meshes.new(info["name"]); bm2.to_mesh(m2); bm2.free()
    for p in m2.polygons: p.use_smooth = True
    o = link(bpy.data.objects.new(info["name"], m2)); groups = {}
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
def double_grid(bm2, info, grid, flip):
    """grid: rows of (co, weights, tip). Builds a two-sided membrane."""
    for side in (1, -1):
        vs = [[addv(bm2, info, co + Vector((0, 0, side * 0.004)), w, tp) for co, w, tp in row] for row in grid]
        for j in range(len(vs) - 1):
            for k in range(len(vs[j]) - 1):
                f = [vs[j][k], vs[j][k+1], vs[j+1][k+1], vs[j+1][k]]
                if (side > 0) != flip: f = f[::-1]
                try: bm2.faces.new(f)
                except ValueError: pass
def tube(bm2, info, a, b, r0, r1, bn, rings=5, segs=5, pid_tip=True):
    d = (b - a); Ln = d.length; d.normalize(); q = d.to_track_quat('Z', 'Y').to_matrix(); R = []
    for i in range(rings + 1):
        t = i / rings; rr = r0 + (r1 - r0) * t
        R.append([addv(bm2, info, a + d * Ln * t + q @ Vector((math.cos(k / segs * math.tau) * rr, math.sin(k / segs * math.tau) * rr, 0)), [(bn, 1.0)], t) for k in range(segs)])
    for i in range(rings):
        for k in range(segs): bm2.faces.new([R[i][k], R[i][(k+1) % segs], R[i+1][(k+1) % segs], R[i+1][k]])

for s, sx in (("L", 1), ("R", -1)):
    # --- forewing: inner panel (body ↔ arm) plus three panels between the fingers, scalloped trailing edge
    bm2, info = new_part("wing" + s, 1)
    sh, el, wr = P["sh"+s][0], P["el"+s][0], P["wr"+s][0]
    hipside = Vector((sx * 0.11, -0.34, 0.0))
    NU = 6
    inner = []
    for j in range(5):  # rows from arm chain (j=0) to body side (j=4)
        t = j / 4; row = []
        for k in range(NU + 1):
            u = k / NU
            arm_pt = sh.lerp(el, u * 2) if u <= 0.5 else el.lerp(wr, (u - 0.5) * 2)
            body_pt = Vector((sx * 0.12, 0.18 - 0.52 * u, 0.02))
            p = arm_pt.lerp(body_pt.lerp(hipside, u), t)
            wa = ("arm"+s) if u < 0.5 else ("fore"+s)
            row.append((p, [(wa, 1 - t), ("spine" if u < 0.5 else "body", t)], 0.0))
        inner.append(row)
    double_grid(bm2, info, inner, sx < 0)
    spokes = [FING[f"fing{i}{s}"] for i in range(4)]
    for i in range(3):
        (r0, t0), (r1, t1) = spokes[i], spokes[i + 1]
        grid = []
        for j in range(4):
            t = j / 3; row = []
            for k in range(7):
                u = k / 6
                p0 = r0.lerp(t0, u); p1 = r1.lerp(t1, u); p = p0.lerp(p1, t)
                if k == 6 and 0 < t < 1: p = p - (p - r0.lerp(r1, t)) * (0.28 * math.sin(math.pi * t))
                row.append((p, [(f"fing{i}{s}", 1 - t), (f"fing{i+1}{s}", t)], u))
            grid.append(row)
        double_grid(bm2, info, grid, sx < 0)
    # last finger back to the hip
    r3, t3 = spokes[3]
    grid = []
    for j in range(3):
        t = j / 2; row = []
        for k in range(7):
            u = k / 6
            p0 = r3.lerp(t3, u); p1 = hipside.lerp(hipside + Vector((sx * 0.25, -0.15, 0)), u)
            p = p0.lerp(p1, t)
            if k == 6 and 0 < t < 1: p = p - (p - r3.lerp(hipside, t)) * (0.2 * math.sin(math.pi * t))
            row.append((p, [(f"fing3{s}", 1 - t), ("body", t)], u))
        grid.append(row)
    double_grid(bm2, info, grid, sx < 0)
    finish(bm2, info)
    # finger bones (visible struts)
    bm2, info = new_part("fingers" + s, 4)
    tube(bm2, info, sh, el, 0.035, 0.03, "arm"+s); tube(bm2, info, el, wr, 0.03, 0.025, "fore"+s)
    for i in range(4):
        r0, t0 = FING[f"fing{i}{s}"]; tube(bm2, info, r0, t0, 0.02, 0.006, f"fing{i}{s}")
    finish(bm2, info)
    # --- hind-wing: membrane from shin to tail
    bm2, info = new_part("hindwing" + s, 1)
    hp, kn, ft = P["hip"+s][0], P["kn"+s][0], P["ft"+s][0]
    t1p, t2p = P["tail1"][0], P["tail2"][0]
    grid = []
    for j in range(4):
        t = j / 3; row = []
        for k in range(6):
            u = k / 5
            leg_pt = hp.lerp(kn, u * 2) if u <= 0.5 else kn.lerp(ft, (u - 0.5) * 2)
            tail_pt = P["hips"][0].lerp(t1p, u * 2) if u <= 0.5 else t1p.lerp(t2p, (u - 0.5) * 2)
            p = leg_pt.lerp(tail_pt, t)
            if k == 5 and 0 < t < 1: p = p + Vector((0, 0.10 * math.sin(math.pi * t), 0))
            lb = ("thigh"+s) if u < 0.5 else ("shin"+s); tb = "tail1" if u < 0.5 else "tail2"
            row.append((p, [(lb, 1 - t), (tb, t)], u))
        grid.append(row)
    double_grid(bm2, info, grid, sx < 0)
    finish(bm2, info)
    # --- huge ears (pink inside), on their own bones so they can flatten back
    bm2, info = new_part("ear" + s, 5)
    root = Vector((sx * 0.07, 0.50, 0.17)); up = Vector((sx * 0.10, -0.08, 0.32)).normalized()
    side_v = Vector((0, 1, 0)).cross(up).normalized() if sx > 0 else up.cross(Vector((0, 1, 0))).normalized()
    grid = []
    for j in range(3):
        t = j / 2; row = []
        for k in range(7):
            u = k / 6
            w = 0.11 * math.sin(math.pi * min(1.0, u * 1.05 + 0.02)) * (1.0 - 0.3 * u)
            c = root + up * (0.36 * u) + Vector((0, 0.03, 0)) * math.sin(math.pi * t)
            row.append((c + side_v * w * (t * 2 - 1), [("ear"+s, 1.0)], u))
        grid.append(row)
    double_grid(bm2, info, grid, sx < 0)
    finish(bm2, info)

# --- lower jaw with teeth, on the jaw bone (opens to screech)
bm2, info = new_part("jaw", 0)
grid = []
for x in (-1, 0, 1):
    row = []
    for i in range(6):
        t = i / 5; y = 0.50 + 0.20 * t; w = 0.075 * (1 - 0.55 * t)
        row.append((Vector((x * w, y, -0.03 - 0.035 * math.sin(math.pi * (0.2 + 0.6 * t)) + 0.01 * t - (0.01 if x == 0 else 0))), [("jaw", 1.0)], 0))
    grid.append(row)
double_grid(bm2, info, grid, False)
finish(bm2, info)
bm2, info = new_part("teeth", 2)
def fang(base, d, ln, bn):
    dd = Vector(d).normalized(); q = dd.to_track_quat('Z', 'Y').to_matrix()
    ring = [addv(bm2, info, base + q @ Vector((math.cos(k / 4 * math.tau) * 0.008, math.sin(k / 4 * math.tau) * 0.008, 0)), [(bn, 1)], 0) for k in range(4)]
    tp = addv(bm2, info, base + dd * ln, [(bn, 1)], 1)
    for k in range(4): bm2.faces.new([ring[k], ring[(k+1) % 4], tp])
for sx in (1, -1):
    fang(Vector((sx * 0.03, 0.70, 0.0)), (0, 0.2, -1), 0.05, "head")
    fang(Vector((sx * 0.025, 0.66, -0.035)), (0, 0.1, 1), 0.035, "jaw")
finish(bm2, info)
# --- four red eyes
bm2, info = new_part("eyes", 3)
for sx in (1, -1):
    for oy, oz, r in ((0.62, 0.11, 0.026), (0.56, 0.15, 0.018)):
        loc, nrm = surf((sx * 0.6, oy, oz), (-sx, 0, 0))
        if loc is None: continue
        res = bmesh.ops.create_uvsphere(bm2, u_segments=8, v_segments=6, radius=r)
        for vv in res["verts"]:
            vv.co += loc - nrm * r * 0.3; info["weights"].append([("head", 1.0)]); info["tip"].append(0)
finish(bm2, info)
# tail fin (small diamond at the tail tip)
bm2, info = new_part("tailfin", 1)
tt = P["tail3"][0]
grid = [[(tt + Vector((0, 0.10, 0)), [("tail3", 1)], 0), (tt + Vector((0.09, -0.04, 0)), [("tail3", 1)], 0.5), (tt + Vector((0, -0.14, 0)), [("tail3", 1)], 1)],
        [(tt + Vector((0, 0.10, 0)), [("tail3", 1)], 0), (tt + Vector((-0.09, -0.04, 0)), [("tail3", 1)], 0.5), (tt + Vector((0, -0.14, 0)), [("tail3", 1)], 1)]]
double_grid(bm2, info, grid, False)
finish(bm2, info)

a = me.attributes.new("part", 'INT', 'FACE')
for i in range(len(me.polygons)): a.data[i].value = 0
me.attributes.new("tipf", 'FLOAT', 'POINT')
for o in scn.objects: o.select_set(o is body or o in parts)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
root = link(bpy.data.objects.new(NAME, None)); rig.parent = root
result = {"verts": len(body.data.vertices), "tris": sum(len(p.vertices) - 2 for p in body.data.polygons), "bones": len(ad_.bones),
          "weights": weight_mode, "dims": [round(x, 2) for x in body.dimensions]}
