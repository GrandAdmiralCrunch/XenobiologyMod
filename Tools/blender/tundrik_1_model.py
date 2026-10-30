# Xenobiology — Tundrik (six-legged polar burrower), step 1: body, shaggy fur shaping, rig, details.
# Faces +Y, feet on Z = 0.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

NAME = "tundrik"; SCN = "Tundrik"
random.seed(5)
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
v("tail", 0, -1.30, 0.80, 0.10)
v("rump", 0, -1.05, 0.88, 0.40, 0.42)
v("hips", 0, -0.75, 0.92, 0.58, 0.55)
v("mid",  0, -0.10, 0.98, 0.64, 0.60)
v("chest", 0, 0.50, 0.98, 0.62, 0.60)
v("neck", 0, 0.92, 0.90, 0.44, 0.44)
v("head", 0, 1.18, 0.86, 0.36, 0.33)
v("snout", 0, 1.42, 0.76, 0.20, 0.18)
v("nose", 0, 1.56, 0.73, 0.12, 0.11)
for a, b in [("tail","rump"),("rump","hips"),("hips","mid"),("mid","chest"),("chest","neck"),("neck","head"),("head","snout"),("snout","nose")]: e(a, b)
LEGS = {"F": ((0.45, 0.58), (0.62, 0.74, 0.42), (0.62, 0.82, 0.13), (0.68, 1.00, 0.05), (0.22, 0.18, 0.15, 0.19)),
        "M": ((0.50, 0.00), (0.68, 0.06, 0.40), (0.68, -0.02, 0.13), (0.72, 0.13, 0.05), (0.20, 0.16, 0.13, 0.16)),
        "H": ((0.46, -0.72), (0.64, -0.58, 0.42), (0.64, -0.84, 0.13), (0.70, -0.68, 0.05), (0.24, 0.18, 0.14, 0.17))}
for k, (sh, el, wr, pw, r) in LEGS.items():
    for s, sx in (("L", 1), ("R", -1)):
        v("sh"+k+s, sx*sh[0], sh[1], 0.75, r[0]); v("el"+k+s, sx*el[0], el[1], el[2], r[1])
        v("wr"+k+s, sx*wr[0], wr[1], wr[2], r[2]); v("pw"+k+s, sx*pw[0], pw[1], pw[2], r[3], 0.07)
        spine_pt = {"F": "chest", "M": "mid", "H": "hips"}[k]
        e(spine_pt, "sh"+k+s); e("sh"+k+s, "el"+k+s); e("el"+k+s, "wr"+k+s); e("wr"+k+s, "pw"+k+s)

mb = bpy.data.metaballs.new(NAME + "_mb"); mb.resolution = 0.035; mb.render_resolution = 0.035; mb.threshold = 0.6
for a_, b_ in E:
    pa, ras, rav = P[a_]; pb, rbs, rbv = P[b_]
    L = (pb - pa).length; step = max(0.02, 0.35 * min(ras, rav, rbs, rbv)); n = max(2, int(math.ceil(L / step)) + 1)
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
rm = body.modifiers.new("Remesh", 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.025; rm.adaptivity = 0
sm = body.modifiers.new("Smooth", 'SMOOTH'); sm.factor = 0.6; sm.iterations = 3
dc = body.modifiers.new("Decimate", 'DECIMATE')
dg = bpy.context.evaluated_depsgraph_get()
dc.ratio = min(1.0, 8000.0 / max(1, len(body.evaluated_get(dg).data.polygons)))
for m in list(body.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
me = body.data; me.name = NAME
for p in me.polygons: p.use_smooth = True

# shaggy fur: streaky ridges that flow backward and downward, longer on the back and flanks
bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
for vert in bm.verts:
    co = vert.co.copy(); nrm = vert.normal
    shag = max(0.0, min(1.0, (co.z - 0.35) / 0.5))          # legs/paws stay short-haired
    if co.y > 1.30: shag *= 0.2                               # bare snout
    streak = noise.noise(Vector((co.x * 9.0, co.y * 2.2, co.z * 9.0))) * 0.5 + 0.5
    clump = noise.noise(Vector((co.x * 3.0, co.y * 3.0, co.z * 3.0)))
    off = (0.035 + 0.05 * streak + 0.02 * clump) * shag
    vert.co = co + nrm * off + Vector((0, -0.03, -0.02)) * shag * streak   # combed back and down
    if vert.co.z < 0: vert.co.z = 0
bm.to_mesh(me); bm.free()

# ---------------------------------------------------------------- armature
ad_ = bpy.data.armatures.new(NAME + "_rig"); rig = link(bpy.data.objects.new(NAME + "_rig", ad_))
bpy.context.view_layer.objects.active = rig
for o in scn.objects: o.select_set(o == rig)
bpy.ops.object.mode_set(mode='EDIT'); eb = ad_.edit_bones
def pt(x): return P[x][0] if isinstance(x, str) else Vector(x)
def bone(name, a, b, parent=None, connect=False):
    bn = eb.new(name); bn.head = pt(a); bn.tail = pt(b)
    if parent: bn.parent = eb[parent]; bn.use_connect = connect
    return bn
bone("body", "hips", "mid"); bone("spine", "mid", "chest", "body", True)
bone("neck", "chest", "neck", "spine", True); bone("head", "neck", "snout", "neck", True)
bone("nose", "snout", "nose", "head", True)
bone("tail", "hips", "tail", "body")
for k, par in (("F", "spine"), ("M", "body"), ("H", "body")):
    for s in "LR":
        bone("up"+k+s, "sh"+k+s, "el"+k+s, par)
        bone("lo"+k+s, "el"+k+s, "wr"+k+s, "up"+k+s, True)
        bone("paw"+k+s, "wr"+k+s, "pw"+k+s, "lo"+k+s, True)
for bn in eb:
    d = (bn.tail - bn.head).normalized()
    bn.align_roll(Vector((0, 0, 1)) if abs(d.z) < 0.7 else Vector((0, -1, 0)))
bpy.ops.object.mode_set(mode='OBJECT')
for o in scn.objects: o.select_set(o in (body, rig))
bpy.context.view_layer.objects.active = rig
weight_mode = "heat"
try: bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except Exception:
    weight_mode = "envelope"; bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')

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
            if bn not in groups: groups[bn] = o.vertex_groups.new(name=bn)
            groups[bn].add([vi], w, 'REPLACE')
    a = m2.attributes.new("part", 'INT', 'FACE')
    for i in range(len(m2.polygons)): a.data[i].value = info["part"]
    tp = m2.attributes.new("tipf", 'FLOAT', 'POINT')
    for i, t in enumerate(info["tip"]): tp.data[i].value = t
    parts.append(o)
def cone(bm2, info, base, direction, length, r0, bn, segs=6, flat=1.0, up=Vector((0, 0, 1))):
    d = Vector(direction).normalized(); q = d.to_track_quat('Z', 'Y').to_matrix()
    ring = [addv(bm2, info, base + q @ Vector((math.cos(k / segs * math.tau) * r0, math.sin(k / segs * math.tau) * r0 * flat, 0)), [(bn, 1.0)], 0.0) for k in range(segs)]
    mid = [addv(bm2, info, base + d * length * 0.55 + q @ Vector((math.cos(k / segs * math.tau) * r0 * 0.6, math.sin(k / segs * math.tau) * r0 * 0.6 * flat, 0)), [(bn, 1.0)], 0.55) for k in range(segs)]
    tipv = addv(bm2, info, base + d * length, [(bn, 1.0)], 1.0)
    for k in range(segs):
        bm2.faces.new([ring[k], ring[(k+1) % segs], mid[(k+1) % segs], mid[k]])
        bm2.faces.new([mid[k], mid[(k+1) % segs], tipv])
    bm2.faces.new(ring[::-1])

# claws: big curved shovel claws on the front pair, small ones elsewhere
bm2, info = new_part("claws", 2)
for k, n_claws, ln, r0 in (("F", 5, 0.26, 0.045), ("M", 3, 0.12, 0.03), ("H", 3, 0.12, 0.03)):
    for s, sx in (("L", 1), ("R", -1)):
        base = P["pw"+k+s][0]
        for i in range(n_claws):
            t = (i / (n_claws - 1) - 0.5) if n_claws > 1 else 0
            b = base + Vector((t * 0.30 + sx * 0.02, 0.12, 0.03))
            cone(bm2, info, b, (t * 0.4, 1.0, -0.55 if k == "F" else -0.4), ln, r0, "paw"+k+s, 6, 0.55 if k == "F" else 1.0)
finish(bm2, info)
# star nose: ring of fleshy feelers around the nose tip
bm2, info = new_part("starnose", 4)
tipc = P["nose"][0] + Vector((0, 0.05, 0))
for i in range(11):
    a = i / 11 * math.tau
    d = Vector((math.cos(a) * 0.9, 0.55, math.sin(a) * 0.9))
    cone(bm2, info, tipc + Vector((math.cos(a), 0, math.sin(a))) * 0.07, d, 0.13 + 0.03 * (i % 2), 0.028, "nose", 6)
finish(bm2, info)
# tiny eyes, small round ears
bm2, info = new_part("eyes", 3)
for sx in (1, -1):
    loc, nrm = surf((sx * 1.5, 1.27, 0.94), (-sx, 0, 0))
    if loc is None: continue
    res = bmesh.ops.create_uvsphere(bm2, u_segments=8, v_segments=6, radius=0.035)
    for vv in res["verts"]:
        vv.co += loc - nrm * 0.01; info["weights"].append([("head", 1.0)]); info["tip"].append(0)
finish(bm2, info)
bm2, info = new_part("ears", 0)
for sx in (1, -1):
    loc, nrm = surf((sx * 0.25, 1.05, 3.0), (0, 0, -1))
    if loc is None: continue
    res = bmesh.ops.create_uvsphere(bm2, u_segments=10, v_segments=6, radius=0.085)
    for vv in res["verts"]:
        vv.co.y *= 0.45; vv.co += loc + Vector((sx * 0.06, -0.02, 0.02)); info["weights"].append([("head", 1.0)]); info["tip"].append(0)
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
