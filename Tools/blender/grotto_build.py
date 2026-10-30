# Xenobiology — the Glowworm Grotto (v2): a bedded limestone outcrop with a fern-hung mouth, a winding stream passage
# and a domed chamber with a pool, rimstone dams, stalactite lines, columns, flowstone curtains and a ceiling of glowing
# glowworm threads. Kerbal scale, walkable.
# Local frame: entrance faces +Y. The cave floor is a rock slab at z = FLOOR (above the terrain, so terrain can't show
# through it); a ramp at the mouth runs down below ground level. Transforms "entrance", "den", "pen" are read by the
# plugin; the resident glowworm colony (kerbin_glowworm, size = its hang height) lives at "den" under the highest crown.
# The collider is a separate low-poly mesh (rock + columns, stalagmites, boulders) exported NON-convex: a convex mesh
# collider is a solid hull and would seal the tunnel.
import bpy, os, math, random
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
NAME = "glowworm_grotto"
random.seed(2611)
scn = new_scene("GlowwormGrotto")
OUT = os.path.join(XENO_DIR, "Models", "Kerbin", "GlowwormGrotto")
STEP = globals().get("STEP", "all")
FLOOR = 1.2                                  # cave floor height in the model (the model is sunk ~0.3 m: floor ~0.9 m above terrain)
def F(y):                                    # floor height along the passage: flat inside, a ramp that dips below ground at the mouth
    if y < 8: return FLOOR
    t = min(1.0, (y - 8) / 14.0); return FLOOR - 2.0 * (t * t * (3 - 2 * t))

# ---------------------------------------------------------------- the passage (centre line used for the void, stream and clearance)
PATH = [(0.0, 31.0, 0.4), (0.3, 22.0, 1.0), (0.9, 14.0, 1.9), (2.4, 6.0, 2.5), (1.6, -2.0, 2.5), (-1.0, -9.0, 2.6), (0.0, -16.0, 3.6)]
CH = Vector((0.0, -29.0, 0.0))
def near_path(x, y, r):
    for (x0, y0, _), (x1, y1, _) in zip(PATH, PATH[1:]):
        a = Vector((x0, y0)); b = Vector((x1, y1)); p = Vector((x, y)); d = b - a
        t = max(0.0, min(1.0, (p - a).dot(d) / d.length_squared))
        if (a + d * t - p).length < r: return True
    return False

# ---------------------------------------------------------------- outcrop (metaballs)
sk = Skel()
sk.v("a", 0, -30, 3, 30, 15); sk.v("b", 0, -6, 2, 21, 11); sk.v("brow", 0, 9, 6.5, 13, 8.5); sk.e("a", "b", "brow")
for i in range(12):
    a = random.uniform(0, math.tau); r = random.uniform(14, 30)
    nm = "l%d" % i
    sk.v(nm, math.cos(a) * r, -26 + math.sin(a) * r * 0.85, random.uniform(-3, 9), random.uniform(6, 13), random.uniform(4, 11)); sk.e("a", nm)
for i in range(5):                                         # knobbly tors on the crest
    sk.v("t%d" % i, random.uniform(-14, 14), random.uniform(-44, -10), random.uniform(13, 17), random.uniform(3, 5), random.uniform(3, 5)); sk.e("a", "t%d" % i)
sk.v("crag", 6, -22, 15, 7, 6); sk.e("a", "crag"); sk.v("crag2", -8, -38, 13, 6, 5); sk.e("a", "crag2")
hill = metaball_body(NAME + "_hill", sk, voxel=0.5, faces=16000, mb_scale=1.15, smooth=2, floor=False)

# ---------------------------------------------------------------- the void: a metaball worm for the passage plus a lobed chamber
vs = Skel()
R = [(4.6, 3.8), (3.8, 3.5), (3.0, 3.1), (2.8, 2.9), (2.8, 2.9), (3.0, 3.0), (5.2, 4.4)]
for i, ((x, y, z), (rs, rv)) in enumerate(zip(PATH, R)): vs.v("p%d" % i, x, y, z, rs, rv)
vs.e(*["p%d" % i for i in range(len(PATH))])
lobes = [("C", 0, -29, 4.2, 11.0, 6.8), ("L1", 6.5, -35, 4.8, 7.0, 5.6), ("L2", -7.5, -31, 4.4, 7.0, 5.2), ("L3", -1.5, -41, 4.8, 7.0, 5.4),
         ("L4", 5.0, -22, 4.0, 6.0, 4.6), ("K1", 2.0, -31, 8.4, 4.0, 3.2), ("K2", -4.5, -27, 7.8, 3.6, 2.6), ("K3", 5.5, -36, 8.4, 3.0, 2.6),
         ("K4", -2.0, -38, 8.6, 3.2, 2.8), ("A1", -12.5, -36, 2.9, 3.0, 2.3), ("A2", -17.0, -40, 2.7, 2.4, 1.9)]
for nm, *v in lobes: vs.v(nm, *v)
vs.e("p6", "C"); vs.e("C", "L1"); vs.e("C", "L2"); vs.e("C", "L3"); vs.e("C", "L4"); vs.e("L2", "A1", "A2")
for k in ("K1", "K2", "K3", "K4"): vs.e("C", k)
void = metaball_body(NAME + "_void", vs, voxel=0.4, faces=9000, mb_scale=1.15, stiffness=2.0, smooth=1, floor=False)
def wobble(co, n):                                        # irregular, scalloped walls
    d = noise.noise(co * 0.22) * 0.75 + noise.noise(co * 0.7) * 0.25 + noise.noise(co * 2.0) * 0.06
    return co + n * d
displace(void, wobble)

def cutter_mesh(name, build):
    bm = bmesh.new(); build(bm); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))
def floor_region(bm):                                     # everything above the floor profile
    ys = [-75 + 1.0 * i for i in range(121)]
    rows = []
    for x in (-45.0, 45.0):
        rows.append([bm.verts.new((x, y, F(y))) for y in ys] + [bm.verts.new((x, y, 40.0)) for y in reversed(ys)])
    n = len(rows[0])
    bm.faces.new(rows[0][::-1]); bm.faces.new(rows[1])
    for k in range(n):
        a, b = rows[0][k], rows[0][(k + 1) % n]; c, d = rows[1][(k + 1) % n], rows[1][k]
        bm.faces.new((a, b, c, d))
def boolean(target, cutter, op):
    mod = target.modifiers.new("b", 'BOOLEAN'); mod.operation = op; mod.solver = 'EXACT'; mod.object = cutter
    select_only([target]); bpy.ops.object.modifier_apply(modifier=mod.name)

region = cutter_mesh("cut_region", floor_region)
boolean(void, region, 'INTERSECT'); bpy.data.objects.remove(region, do_unlink=True)
boolean(hill, void, 'DIFFERENCE')
void_bvh = bvh_of(void)

# pool basin and the stream groove that drains it out through the mouth
PC = Vector((5.0, -33.5, FLOOR))
def basin(bm):
    res = bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=12, radius=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(PC) @ Matrix.Diagonal((4.4, 3.3, 1.15, 1)), verts=res["verts"])
STREAM = [(3.2, -30.5), (2.2, -24.0), (1.8, -17.0), (0.2, -10.0), (2.6, -3.0), (3.4, 5.0), (1.9, 13.0), (1.2, 21.0), (0.9, 31.0)]
def groove(bm):
    pts = []
    for (x0, y0), (x1, y1) in zip(STREAM, STREAM[1:]):
        for k in range(6): t = k / 6; pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    pts.append(STREAM[-1])
    for (x, y) in pts:
        res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, F(y))) @ Matrix.Diagonal((0.75, 0.9, 0.42, 1)), verts=res["verts"])
for nm, fn in (("cut_basin", basin), ("cut_groove", groove)):
    c = cutter_mesh(nm, fn)
    if nm == "cut_groove":                                # union the beads into one closed cutter first
        rm = c.modifiers.new("r", 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.12
        select_only([c]); bpy.ops.object.modifier_apply(modifier="r")
    boolean(hill, c, 'DIFFERENCE'); bpy.data.objects.remove(c, do_unlink=True)

# ---------------------------------------------------------------- weathering: bedded strata ledges outside, scalloped walls inside
def cave_dist(co):
    loc, nrm, i, d = void_bvh.find_nearest(co)
    return d if loc is not None else 99.0
bm = bmesh.new(); bm.from_mesh(hill.data); bm.normal_update()
cave_w = {}
for v in bm.verts:
    co = v.co.copy(); n = v.normal.copy()
    inside = cave_dist(co) < 0.9 or (abs(co.z - F(co.y)) < 0.05 and near_path(co.x, co.y, 6.0)) or (co.z < FLOOR + 0.2 and (Vector((co.x, co.y)) - Vector((PC.x, PC.y))).length < 5)
    cave_w[v.index] = 1.0 if inside else 0.0
    if inside:
        if n.z > 0.75 and co.z < FLOOR + 0.3: d = noise.noise(co * 2.0) * 0.03          # floor: barely touched (walkable)
        else: d = noise.noise(co * 0.9 + Vector((7, 1, 3))) * 0.22 + noise.noise(co * 3.0) * 0.05
    else:
        d = noise.noise(co * 0.12) * 1.0 + noise.noise(co * 0.5) * 0.35 + noise.noise(co * 2.0) * 0.08
        if abs(n.z) < 0.8:                                                              # bedding: stepped ledges on steep faces
            h = 1.6; zz = co.z / h + noise.noise(co * 0.05) * 0.6 + noise.noise(co * 0.2) * 0.12
            ph = zz - math.floor(zz)
            stair = (smooth01(ph / 0.3) - ph) * h                                       # continuous: 0 at both ends of a bed
            amt = max(0.0, 0.25 + noise.noise(co * 0.04 + Vector((3, 3, 3))) * 0.9)  # beds stand out in some places, not everywhere
            d += amt * (1 - abs(n.z) / 0.8) * stair
            jt = abs(noise.noise(Vector((co.x * 0.18, co.y * 0.18, 0.0))))              # vertical joints
            d -= 0.45 * math.exp(-(jt / 0.035) ** 2)
        if co.z < 0.6: d *= max(0.0, co.z + 0.4)                                        # keep the skirt sunk into the ground
    v.co = co + n * d
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
STATS = {"hill_boundary": sum(1 for e in bm.edges if e.is_boundary)}
bm.to_mesh(hill.data); bm.free()
cv = hill.data.attributes.new("cave", 'FLOAT', 'POINT')
for i, w in cave_w.items(): cv.data[i].value = w
for p in hill.data.polygons: p.use_smooth = True
tag_body(hill, 0)
bvh = bvh_of(hill)
def ceiling_z(x, y, z0=None):                             # None unless (x, y) is open cave: the roof must face down at us
    loc, n = ray(bvh, (x, y, (z0 if z0 is not None else F(y)) + 0.4), (0, 0, 1), 30.0)
    if loc is None or n.z > -0.05: return None
    lo, n2 = ray(bvh, (x, y, (z0 if z0 is not None else F(y)) + 0.4), (0, 0, -1), 1.5)
    if lo is None or n2.z < 0.3: return None
    return loc.z
def floor_z(x, y):
    loc, n = ray(bvh, (x, y, F(y) + 2.5), (0, 0, -1), 6.0)
    return loc.z if (loc and n.z > 0.2) else F(y)

# walkability probe: along the passage the floor must be flat at F(y) with >= 2.4 m of headroom
FP = []
for (x0, y0, _), (x1, y1, _) in zip(PATH, PATH[1:]):
    for k in range(8):
        t_ = k / 8; x, y = x0 + (x1 - x0) * t_, y0 + (y1 - y0) * t_
        if y > 24: continue
        lo, n_ = ray(bvh, (x, y, F(y) + 0.5), (0, 0, -1), 1.2); hi, n2 = ray(bvh, (x, y, F(y) + 0.5), (0, 0, 1), 40.0)
        ok = lo is not None and n_.z > 0.5 and hi is not None and n2.z < 0 and hi.z - lo.z > 2.4
        if not ok: FP.append((round(x, 1), round(y, 1), lo is not None and round(lo.z, 2), hi is not None and round(hi.z, 2)))
# ---------------------------------------------------------------- water: the pool and the stream ribbon
water = Part("water", 3)
water.f([water.v(PC + Vector((math.cos(k / 28 * math.tau) * 4.25 * (1 + 0.06 * math.sin(k * 1.9)), math.sin(k / 28 * math.tau) * 3.15, -0.42)), "root") for k in range(28)])
prev = None
spts = []
for (x0, y0), (x1, y1) in zip(STREAM, STREAM[1:]):
    for k in range(6): t = k / 6; spts.append(Vector((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)))
spts.append(Vector(STREAM[-1]))
for i, p2 in enumerate(spts):
    d = (spts[min(i + 1, len(spts) - 1)] - spts[max(i - 1, 0)]).normalized(); side = Vector((-d.y, d.x))
    z = F(p2.y) - 0.24
    row = [water.v(Vector((p2.x + side.x * s, p2.y + side.y * s, z)), "root") for s in (-0.5, 0.5)]
    if prev: water.f([row[0], row[1], prev[1], prev[0]])
    prev = row
water_o = water.finish()

# ---------------------------------------------------------------- speleothems, curtains, boulders (solid ones also go into the collider)
def bead(p, c, r, tip=0.0):
    vv = [p.v(c + Vector(o) * r, "root", tip) for o in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1.4), (0, 0, -1.4))]
    for a, b in ((0, 2), (2, 1), (1, 3), (3, 0)):
        p.f([vv[a], vv[b], vv[4]]); p.f([vv[b], vv[a], vv[5]])
solid = Part("solid", 2); fine = Part("fine", 2); curt = Part("curtains", 5); rocks = Part("rocks", 7)
def stal(p, top, L, r, up=False, segs=6):
    rings = []; n = 5
    if up: segs, n = 9, 7
    for i in range(n + 1):
        t = i / n
        rr = r * ((1 - t) ** 0.75 if not up else (1 - t ** 2.4) ** 0.5) * (1 + 0.1 * math.sin(t * 11 + top.x * 3)) + (0.004 if t == 1 else 0)
        z = top.z + (L * t if up else -L * t)
        rings.append([p.v(Vector((top.x + math.cos(k / segs * math.tau) * rr, top.y + math.sin(k / segs * math.tau) * rr, z)), "root", t) for k in range(segs)])
    for i in range(n):
        for k in range(segs): p.f([rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]][::(1 if up else -1)])
    if not up: bead(p, Vector((top.x, top.y, top.z - L - 0.01)), max(0.012, r * 0.1), tip=1.0)   # drip
def column(p, x, y, z0, z1, r):
    segs = 10; n = 12; rings = []
    for i in range(n + 1):
        t = i / n; z = z0 + (z1 - z0) * t
        base = r * (0.5 + 0.5 * abs(2 * t - 1) ** 1.6) * (1 + 0.06 * math.sin(t * 17 + x))
        rings.append([p.v(Vector((x + math.cos(a) * base * (1 + 0.12 * math.cos(6 * a + t * 3)), y + math.sin(a) * base * (1 + 0.12 * math.cos(6 * a + t * 3)), z)), "root", t)
                      for a in [k / segs * math.tau for k in range(segs)]])
    for i in range(n):
        for k in range(segs): p.f([rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]])
# stalactite lines along ceiling joints, with stalagmites below their drips
lines = []
for k in range(9):
    a = random.uniform(0, math.pi); c = CH + Vector((random.uniform(-8, 8), random.uniform(-9, 9), 0))
    lines.append((c, Vector((math.cos(a), math.sin(a), 0))))
lines += [(Vector((1.8, 2.0, 0)), Vector((0.2, 1, 0)).normalized()), (Vector((0.0, -10.0, 0)), Vector((-0.3, 1, 0)).normalized())]
nst = 0
for c, d in lines:
    for j in range(22):
        q = c + d * random.uniform(-9, 9) + Vector((random.gauss(0, 0.35), random.gauss(0, 0.35), 0))
        zc = ceiling_z(q.x, q.y)
        fz = F(q.y)
        if zc is None or zc - fz < 1.8: continue
        L = min(random.uniform(0.25, 1.7) ** 1.3, (zc - fz) * 0.4)
        stal(fine, Vector((q.x, q.y, zc + 0.15)), L + 0.15, random.uniform(0.07, 0.22)); nst += 1
        clear = not near_path(q.x, q.y, 1.9) and (Vector((q.x, q.y)) - Vector((PC.x, PC.y))).length > 4.8
        if random.random() < 0.45 and clear:
            stal(solid, Vector((q.x, q.y, floor_z(q.x, q.y) - 0.1)), random.uniform(0.3, 1.4) * min(1.0, (zc - fz) / 5), random.uniform(0.16, 0.38), up=True)
for k in range(80):                                        # soda straws in clusters
    if k % 10 == 0: cc = CH + Vector((random.uniform(-7, 7), random.uniform(-8, 8), 0))
    x, y = cc.x + random.gauss(0, 0.5), cc.y + random.gauss(0, 0.5); zc = ceiling_z(x, y)
    if zc is None or zc - F(y) < 2.5: continue
    fine.tube(Vector((x, y, zc + 0.1)), Vector((x, y, zc - random.uniform(0.15, 0.6))), 0.022, 0.018, "root", rings=1, segs=5)
ncol = 0
for (x, y, r) in ((-6.0, -35.0, 0.75), (8.5, -27.0, 0.6), (-3.5, -22.5, 0.5), (9.5, -38.0, 0.9), (-9.0, -27.0, 0.55), (3.0, -10.5, 0.4)):
    zc = ceiling_z(x, y)
    if zc is None or near_path(x, y, 1.5): continue
    column(solid, x, y, floor_z(x, y) - 0.2, zc + 0.3, r); ncol += 1
# flowstone curtains hanging from the chamber's rim, banded like bacon
ncur = 0
for k in range(14):
    a = random.uniform(0, math.tau)
    for rr in (0.92, 0.85, 0.78, 0.7):
        x, y = CH.x + math.cos(a) * 11.0 * rr, CH.y + math.sin(a) * 9.5 * rr
        zc = ceiling_z(x, y)
        if zc is not None and zc - F(y) < 5.5: break
    if zc is None or near_path(x, y, 2.0): continue
    tang = Vector((-math.sin(a), math.cos(a), 0)); W = random.uniform(0.6, 1.3); H = min(random.uniform(1.6, 3.2), (zc - F(y)) * 0.65)
    rows = []
    for j in range(5):
        t = j / 4; row = []
        for i in range(9):
            s = i / 8; hgt = H * (0.6 + 0.4 * math.sin(math.pi * s) + 0.08 * math.sin(s * 23 + k)) * (1 - 0.35 * t * t * abs(s - 0.5))
            off = tang * (s - 0.5) * W * (1 - 0.3 * t) + Vector((math.cos(a), math.sin(a), 0)) * (0.16 * math.sin(s * math.tau * 2.0 + k) * (0.4 + t))
            row.append((Vector((x, y, zc + 0.25)) + off - Vector((0, 0, (hgt + 0.25) * t)), "root", t))
        rows.append(row)
    curt.grid(rows, thickness=0.02); ncur += 1
# rimstone dams on the pool's downstream lip
for k in range(5):
    a0 = math.radians(110 + k * 6); rr = 4.6 + k * 0.55
    pts = [PC + Vector((math.cos(a0 + t * 0.9) * rr * 1.05, math.sin(a0 + t * 0.9) * rr * 0.8, 0.0)) for t in [i / 8 for i in range(9)]]
    for p0, p1 in zip(pts, pts[1:]):
        z0, z1 = floor_z(p0.x, p0.y), floor_z(p1.x, p1.y)
        fine.tube(Vector((p0.x, p0.y, z0 - 0.02)), Vector((p1.x, p1.y, z1 - 0.02)), 0.07, 0.07, "root", rings=1, segs=5)
# breakdown boulders against the walls, and a rock fall outside the mouth
nrock = 0
for k in range(70):
    if k < 45:
        a = random.uniform(0, math.tau); r = random.uniform(0.6, 0.95)
        x, y = CH.x + math.cos(a) * 11 * r, CH.y + math.sin(a) * 9.5 * r
        if random.random() < 0.3: x, y = PATH[3][0] + random.uniform(-3, 3), random.uniform(-12, 10)
    else:
        if k > 58: continue
        x, y = random.uniform(-9, 9), random.uniform(21, 30)
        if abs(x) < 2.2: continue
    if near_path(x, y, 2.0 if y < 18 else 1.6) or (Vector((x, y)) - Vector((PC.x, PC.y))).length < 5: continue
    loc, n = ray(bvh, (x, y, F(y) + 3.0), (0, 0, -1), 12.0)
    z = loc.z if loc else 0.2
    if y > 22: z = max(z, 0.15)
    s = random.uniform(0.25, 1.1) * (1.3 if y > 22 else 1.0)
    rocks.sphere(Vector((x, y, z + s * 0.15)), s, "root", scale=(random.uniform(0.9, 1.5), random.uniform(0.8, 1.3), random.uniform(0.45, 0.75)), sub=2, jitter=0.22)
    nrock += 1
# ---------------------------------------------------------------- the mouth: ferns on the ledges and roots hanging over the lintel
flora = Part("flora", 8); roots = Part("roots", 9)
def frond(p, base, d, L):
    d = d.normalized(); side = d.cross(Vector((0, 0, 1))).normalized(); n = 7
    spine = [base + d * L * (i / n) + Vector((0, 0, L * 0.55 * math.sin(math.pi * 0.8 * i / n) - L * 0.35 * (i / n) ** 2)) for i in range(n + 1)]
    for i in range(1, n):
        t = i / n; w = L * 0.22 * math.sin(math.pi * min(1.0, t * 1.15)) + 0.01
        for sgn in (1, -1):
            a = spine[i]; b = spine[i + 1]; tip = a.lerp(b, 0.5) + side * sgn * w - Vector((0, 0, w * 0.25))
            for s2 in (1, -1):                         # double sided
                vv = [p.v(a, "root", t), p.v(b, "root", t), p.v(tip + Vector((0, 0, 0.004 * s2)), "root", min(1.0, t + 0.2))]
                p.f(vv if (sgn * s2) > 0 else vv[::-1])
    for i in range(n): p.tube(spine[i], spine[i + 1], 0.012, 0.01, "root", rings=1, segs=3, cap=False)
nfern = 0
for k in range(300):
    if nfern >= 28: break
    x, y = random.uniform(-14, 14), random.uniform(14, 32)
    loc, n = ray(bvh, (x, y, 30.0), (0, 0, -1), 40.0)
    if loc is None: loc, n = Vector((x, y, 0.25)), Vector((0, 0, 1))
    if n.z < 0.55 or near_path(x, y, 2.3 if loc.z < 3 else 0.0) or loc.z < 0.0: continue
    nf = random.randint(5, 8); L = random.uniform(0.45, 0.95)
    for j in range(nf):
        a = j / nf * math.tau + random.uniform(-0.2, 0.2)
        frond(flora, loc - Vector((0, 0, 0.02)), Vector((math.cos(a), math.sin(a), 0.0)), L * random.uniform(0.8, 1.1))
    nfern += 1
lintel = []
for k in range(40):
    x = random.uniform(-3.0, 3.5); y = random.uniform(9.0, 14.5)
    zc = ceiling_z(x, y)
    if zc is None or zc - F(y) < 2.2: continue
    L = random.uniform(0.6, min(2.6, zc - F(y) - 1.0)); pts = [Vector((x, y, zc + 0.2))]
    for i in range(6): pts.append(pts[-1] + Vector((random.gauss(0, 0.06), random.gauss(0, 0.06), -L / 6)))
    for a_, b_ in zip(pts, pts[1:]): roots.tube(a_, b_, 0.03, 0.022, "root", rings=1, segs=4, cap=False)
    lintel.append(1)

# ---------------------------------------------------------------- glowing threads: densest over the water
TH = [Part("threads", 6), Part("threads2", 6)]; SI = [Part("silk", 5), Part("silk2", 5)]
def over_water(x, y):
    if (Vector((x, y)) - Vector((PC.x, PC.y))).length < 4.5: return True
    return any((Vector((x, y)) - Vector(s)).length < 1.2 for s in STREAM)
nthreads = 0
for k in range(6000):
    if nthreads >= 900: break
    u = random.random()
    if u < 0.72: a = random.uniform(0, math.tau); r = math.sqrt(random.random()); x, y = CH.x + math.cos(a) * r * 12.5, CH.y + math.sin(a) * r * 11.5
    elif u < 0.92: x, y = random.uniform(-2.0, 4.5), random.uniform(-20, 0)
    else: x, y = random.uniform(-17, -10), random.uniform(-42, -33)
    if not over_water(x, y) and random.random() < 0.45: continue
    zc = ceiling_z(x, y)
    if zc is None or zc - F(y) < 2.4: continue
    threads, silk = TH[nthreads % 2], SI[nthreads % 2]
    L = random.uniform(0.15, 0.5) * (zc - F(y) - 0.6) * (1.25 if over_water(x, y) else 1.0)
    silk.tube(Vector((x, y, zc + 0.05)), Vector((x, y, zc - L)), 0.005, 0.004, "root", rings=1, segs=3, cap=False)
    nb = 2 + int(L * 2.2)
    for b in range(nb):
        zz = zc - 0.1 - (L - 0.1) * (b + 0.5) / nb
        bead(threads, Vector((x, y, zz)), random.uniform(0.014, 0.026))
    bead(threads, Vector((x, y, zc - 0.03)), 0.03, tip=1.0)                     # the larva's lit tail at the nest
    nthreads += 1

# ---------------------------------------------------------------- assemble objects
water_o.name = NAME + "_water"
solid_o = solid.finish(); fine_o = fine.finish(); curt_o = curt.finish(); rocks_o = rocks.finish(); flora_o = flora.finish(); roots_o = roots.finish()
glow_o = TH[0].finish(); silk_o = SI[0].finish(); glow2 = TH[1].finish(); silk2 = SI[1].finish()
# collider source: the rock plus everything solid you could bump into
colsrc = [o.copy() for o in (solid_o, rocks_o)]
for o in colsrc: o.data = o.data.copy(); link(o)
col = hill.copy(); col.data = hill.data.copy(); link(col)
dc = col.modifiers.new("d", 'DECIMATE'); dc.ratio = 0.3
select_only([col]); bpy.ops.object.modifier_apply(modifier="d")
select_only([col] + colsrc, col); bpy.ops.object.join(); col.name = NAME + "_collider"
# the walls/floor inside the hill get their own texture (more texels where kerbals look closely)
select_only([hill]); bpy.ops.object.mode_set(mode='EDIT')
ebm = bmesh.from_edit_mesh(hill.data); cl = ebm.verts.layers.float.get("cave")
for f in ebm.faces: f.select_set(sum(v[cl] for v in f.verts) / len(f.verts) > 0.5)
bmesh.update_edit_mesh(hill.data); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
inner = [o for o in scn.objects if o.name.startswith(hill.name) and o != hill][0]
select_only([inner, water_o], inner); bpy.ops.object.join(); inner.name = NAME + "_inner"
hill.name = NAME + "_outer"
select_only([solid_o, fine_o, curt_o, rocks_o], solid_o); bpy.ops.object.join(); decor = solid_o; decor.name = NAME + "_decor"
select_only([flora_o, roots_o], flora_o); bpy.ops.object.join(); flora_o.name = NAME + "_flora"
select_only([glow_o, silk_o], glow_o); bpy.ops.object.join(); glow_o.name = NAME + "_threads"
select_only([glow2, silk2], glow2); bpy.ops.object.join(); glow2.name = NAME + "_threads2"
for o in (hill, inner, decor, flora_o, glow_o, glow2, col):
    for vg in list(o.vertex_groups): o.vertex_groups.remove(vg)
bpy.data.objects.remove(void, do_unlink=True)

# ---------------------------------------------------------------- textures
def vsc(N, sx, sy, sz):
    n = N.node('ShaderNodeVectorMath', operation='MULTIPLY'); N.L(N.obj, n.inputs[0]); n.inputs[1].default_value = (sx, sy, sz); return n.outputs[0]
def limestone(N):
    base = N.ramp(N.noise(0.22, 6), [(0.25, (0.5, 0.48, 0.43)), (0.5, (0.64, 0.61, 0.55)), (0.78, (0.45, 0.43, 0.39))])
    bed = N.wave(0.55, 'BANDS', 'Z', 2.5)
    base = N.mix(base, (0.72, 0.68, 0.6), N.m('MULTIPLY', N.m('GREATER_THAN', bed, 0.78), 0.3))
    base = N.mix(base, (0.36, 0.34, 0.31), N.m('MULTIPLY', N.m('LESS_THAN', bed, 0.12), 0.35))
    cracks = N.voronoi(0.7, 'DISTANCE_TO_EDGE')
    cracks = N.m('ADD', cracks, N.m('MULTIPLY', N.noise(0.5, 3), 0.25))
    base = N.mix(base, (0.22, 0.21, 0.19), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.m('MULTIPLY', N.m('SUBTRACT', cracks, 0.06), 30.0, clamp=True)), 0.35))
    return base
def outer_nodes(N):
    up = N.up01(); c = limestone(N)
    streak = N.noise(1.0, 3, vec=vsc(N, 2.5, 2.5, 0.15))                         # rain streaks running down the faces
    c = N.mix(c, N.mul(c, 0.6), N.m('MULTIPLY', N.m('GREATER_THAN', streak, 0.6), N.m('LESS_THAN', up, 0.7)))
    lich = N.voronoi(3.5)
    c = N.mix(c, (0.78, 0.74, 0.5), N.m('MULTIPLY', N.m('LESS_THAN', lich, 0.12), 0.6))
    c = N.mix(c, (0.85, 0.55, 0.2), N.m('MULTIPLY', N.m('LESS_THAN', N.voronoi(2.2, rand=0.9), 0.07), 0.5))
    mossy = N.m('MULTIPLY', N.m('GREATER_THAN', up, 0.7), N.m('GREATER_THAN', N.noise(0.35, 3), 0.42))
    moss = N.mul((0.24, 0.4, 0.15), N.m('ADD', N.m('MULTIPLY', N.noise(4.0, 4), 0.5), 0.72))
    c = N.mix(c, moss, N.m('MULTIPLY', mossy, N.m('GREATER_THAN', N.Z, 0.8)))
    soil = N.mix((0.27, 0.22, 0.15), (0.2, 0.3, 0.13), N.noise(1.5, 4))
    c = N.mix(c, soil, N.m('LESS_THAN', N.Z, 0.7))
    return c, None
def inner_nodes(N):
    up = N.up01(); c = limestone(N)
    deep = N.m('SUBTRACT', 1.0, N.m('DIVIDE', N.m('ADD', N.Y, 25.0), 45.0), clamp=True)          # 0 at the mouth, 1 deep inside
    c = N.mul(c, N.m('SUBTRACT', 1.0, N.m('MULTIPLY', deep, 0.35)))                                 # damp, darker deeper in
    flow = N.noise(0.9, 4, vec=vsc(N, 1.8, 1.8, 0.12))                                              # flowstone streaks down the walls
    flowc = N.ramp(N.wave(4.0, 'BANDS', 'Z', 1.5), [(0.0, (0.86, 0.68, 0.42)), (0.5, (0.93, 0.85, 0.7)), (1.0, (0.7, 0.45, 0.22))])
    c = N.mix(c, flowc, N.m('MULTIPLY', N.m('MULTIPLY', N.m('SUBTRACT', flow, 0.55), 6.0, clamp=True), N.m('MULTIPLY', N.m('LESS_THAN', up, 0.8), 0.7)))
    mang = N.noise(2.0, 3, vec=vsc(N, 3.0, 3.0, 0.3))                                              # black manganese stains
    c = N.mix(c, (0.1, 0.09, 0.08), N.m('MULTIPLY', N.m('GREATER_THAN', mang, 0.66), 0.7))
    floorc = N.mix((0.3, 0.25, 0.19), (0.2, 0.16, 0.12), N.noise(1.4, 5))                          # wet mud and gravel
    floorc = N.mix(floorc, (0.5, 0.47, 0.42), N.m('LESS_THAN', N.voronoi(9.0), 0.1))
    c = N.mix(c, floorc, N.m('GREATER_THAN', up, 0.86))
    algae = N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.m('MULTIPLY', deep, 3.0), clamp=True), 0.55)    # twilight-zone green at the mouth
    c = N.mix(c, (0.25, 0.38, 0.18), N.m('MULTIPLY', algae, N.m('GREATER_THAN', N.noise(1.2, 3), 0.45)))
    c = N.mix(c, (0.03, 0.06, 0.06), N.is_part(3))                                                 # water: black-green, mirrors the threads
    g = N.mix((0, 0, 0), (0.03, 0.14, 0.12), N.is_part(3))
    g = N.mix(g, (0.012, 0.035, 0.03), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.is_part(3)), N.m('MULTIPLY', deep, N.m('LESS_THAN', up, 0.3))))  # faint ceiling glow
    return c, g
def decor_nodes(N):
    sp = N.mix((0.9, 0.85, 0.74), (0.74, 0.62, 0.45), N.m('MULTIPLY', N.m('GREATER_THAN', N.wave(6.0, 'BANDS', 'Z', 2.0), 0.6), 0.6))
    sp = N.mix(sp, (0.97, 0.96, 0.92), N.m('MULTIPLY', N.tipf, 0.5))
    cur = N.ramp(N.wave(11.0, 'BANDS', 'Z', 1.2), [(0.0, (0.93, 0.84, 0.68)), (0.4, (0.86, 0.64, 0.38)), (0.6, (0.72, 0.45, 0.24)), (0.8, (0.9, 0.78, 0.6)), (1.0, (0.93, 0.84, 0.68))])
    cur = N.mix(cur, (0.97, 0.94, 0.86), N.m('MULTIPLY', N.tipf, 0.45))
    rk = N.mix((0.5, 0.48, 0.43), (0.36, 0.34, 0.31), N.noise(2.0, 5))
    rk = N.mix(rk, (0.3, 0.42, 0.18), N.m('MULTIPLY', N.m('GREATER_THAN', N.up01(), 0.75), N.m('MULTIPLY', N.m('GREATER_THAN', N.Y, 18.0), N.m('GREATER_THAN', N.noise(1.5, 3), 0.45))))
    fern = N.mix((0.12, 0.3, 0.08), (0.42, 0.62, 0.2), N.tipf)
    fern = N.mul(fern, N.m('ADD', N.m('MULTIPLY', N.noise(5.0, 3), 0.4), 0.8))
    root = N.mix((0.3, 0.22, 0.14), (0.45, 0.36, 0.25), N.noise(4.0, 3))
    c = sp
    c = N.mix(c, cur, N.is_part(5)); c = N.mix(c, rk, N.is_part(7)); c = N.mix(c, fern, N.is_part(8)); c = N.mix(c, root, N.is_part(9))
    return c, None
def glow_nodes(N):
    c = N.mix((0.75, 0.85, 0.85), (0.5, 1.0, 0.9), N.is_part(6))
    g = N.mix((0.04, 0.1, 0.1), (0.3, 1.0, 0.85), N.is_part(6))
    g = N.mix(g, (0.5, 1.0, 0.9), N.m('MULTIPLY', N.tipf, N.is_part(6)))
    return c, g
if STEP != "model":
    uv_unwrap(hill, margin=0.002); bake_and_material(hill, NAME + "_outer", OUT, outer_nodes, res=2048)
    uv_unwrap(inner, margin=0.002); bake_and_material(inner, NAME + "_inner", OUT, inner_nodes, res=2048, glow_res=256)
    uv_unwrap(decor, margin=0.003); bake_and_material(decor, NAME + "_decor", OUT, decor_nodes, res=1024)
    uv_unwrap(flora_o, margin=0.003); bake_and_material(flora_o, NAME + "_flora", OUT, decor_nodes, res=512)
    uv_unwrap(glow_o, margin=0.004); bake_and_material(glow_o, NAME + "_threads", OUT, glow_nodes, res=256, glow_res=128)
    uv_unwrap(glow2, margin=0.004); bake_and_material(glow2, NAME + "_threads2", OUT, glow_nodes, res=256, glow_res=128)

# ---------------------------------------------------------------- hierarchy, collider, lights, markers
root = link(bpy.data.objects.new(NAME, None)); root.muproperties.layer = 15
for o in (hill, inner, decor, flora_o, glow_o, glow2): o.parent = root; o.muproperties.layer = 15
col.parent = root; col.data.materials.clear(); col.hide_render = True
col.muproperties.collider = "MU_COL_MESH"; col.muproperties.layer = 15; col.muproperties.separate = True; col.muproperties.isConvex = False
# den: under the highest point of the chamber's ceiling
best = None
for k in range(400):
    a = random.uniform(0, math.tau); r = math.sqrt(random.random()) * 6
    x, y = CH.x + math.cos(a) * r, CH.y + math.sin(a) * r; zc = ceiling_z(x, y)
    if (Vector((x, y)) - Vector((PC.x, PC.y))).length < 5.6 or near_path(x, y, 1.0): continue
    if zc is not None and (best is None or zc > best[2]): best = (x, y, zc)
den = Vector((best[0], best[1], floor_z(best[0], best[1])))
for nm, loc in (("entrance", (0.4, 22.0, F(22.0))), ("den", tuple(den)), ("pen", tuple(den))):
    e = link(bpy.data.objects.new(nm, None)); e.parent = root; e.location = loc
for nm, loc, energy, rng, colr in (("glow_light", (CH.x + 1, CH.y - 2, 5.0), 900, 24.0, (0.3, 1.0, 0.85)), ("glow_light2", (1.0, -6.0, 3.0), 350, 11.0, (0.3, 1.0, 0.85))):
    ld = bpy.data.lights.new(nm, 'POINT'); ld.color = colr; ld.energy = energy; ld.use_custom_distance = True; ld.cutoff_distance = rng
    lo = link(bpy.data.objects.new(nm, ld)); lo.parent = root; lo.location = loc
scn.frame_start = 0
counts = {o.name: len(o.data.vertices) for o in (hill, inner, decor, flora_o, glow_o, glow2, col)}
res = export_mu(NAME, os.path.join(OUT, NAME + ".mu")) if STEP != "model" else None

# ---------------------------------------------------------------- review renders
cam, g = stage_setup(ground_size=300.0)
g.location.z = 0.3
cam.data.type = 'PERSP'; cam.data.lens = 28; cam.data.clip_start = 0.05
look_at(cam, (40, 62, 22), (0, -10, 5)); render(os.path.join(PREVIEW_DIR, "grotto_outside.png"), res=(960, 600))
look_at(cam, (2.5, 34, 2.6), (0.3, 12, 2.2)); render(os.path.join(PREVIEW_DIR, "grotto_mouth.png"), res=(960, 600))
scn.world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
for o in scn.objects:
    if o.type == 'LIGHT' and o.name.startswith("xr_"): o.hide_render = True
look_at(cam, (CH.x + 7, CH.y + 9, FLOOR + 1.6), (CH.x - 2, CH.y - 4, FLOOR + 3.5)); render(os.path.join(PREVIEW_DIR, "grotto_inside.png"), res=(960, 600))
look_at(cam, (2.0, 4.0, FLOOR + 1.6), (0.5, -14, FLOOR + 1.8)); render(os.path.join(PREVIEW_DIR, "grotto_tunnel.png"), res=(960, 600))
g.location.z = 0.0
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(PREVIEW_DIR), "blend", "glowworm_grotto.blend"), copy=True)
result = {"export": res, "verts": counts, "threads": nthreads, "stalactites": nst, "columns": ncol, "curtains": ncur, "rocks": nrock, "ferns": nfern,
          "roots": len(lintel), "stats": STATS, "floorprobe": FP, "den": [round(c, 2) for c in den], "crown": round(best[2], 2), "hangHeight": round(best[2] - den.z, 2)}
