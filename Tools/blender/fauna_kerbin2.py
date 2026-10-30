# Xenobiology — Kerbin expansion 2 builders for fauna_build.py (exec'd from fauna_mammals.py, shares its globals).
# Archetypes: "whale" (beluga: melon head, flexible neck, dorsal ridge, paddle flippers, flukes),
#             "shark" (megalodon: torpedo body, hinged jaw with tooth rows, gill slits, tall dorsal, crescent tail),
#             "siphon" (man o' war: gas float with a crest sail, polyp cluster, long beaded stinging tentacles),
#             "nautilus" (coiled chambered shell, hood, ring of short tentacles),
#             "vent" (hydrothermal chimney with a colony of tubeworms whose plumes retract),
#             "glowworm" (a curtain of glowing silk threads hanging from a cave ceiling).
# Also an avian feature "tails" (moth hindwing tails). Units are fractions of `size`; +Y forward, Z up.

def _ring_sweep(p, pts, radii, bones, segs=10, tips=None, flat=1.0, up=None, cap=True):
    """Tube along a polyline with per-point radius / bone weights (bone name or weight list)."""
    rings = []
    n = len(pts)
    for i in range(n):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector(up) if up is not None else (Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0)))
        y = (ref - d * ref.dot(d)).normalized(); x = y.cross(d)
        ring = []
        for k in range(segs):
            a = k / segs * math.tau
            ring.append(p.v(pts[i] + (x * math.cos(a) + y * math.sin(a) * flat) * radii[i], bones[i], tips[i] if tips else i / max(1, n - 1)))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(segs): p.f([rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]])
    if cap: p.f(rings[0][::-1]); p.f(rings[-1])
    return rings

def _recalc(o):
    bm_ = bmesh.new(); bm_.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm_, faces=bm_.faces); bm_.to_mesh(o.data); bm_.free(); return o

def _resample(pts, m):
    out = []
    for i in range(m):
        f = i / (m - 1) * (len(pts) - 1); k = min(int(f), len(pts) - 2); out.append(pts[k].lerp(pts[k + 1], f - k))
    return out

def _fin(p, base_pts, tip_pts, bone, tip_from=0.0, thick=0.002, rows=6):
    """Fin between a root polyline and a tip polyline: a closed blade, thick at the root and thinning to a sharp edge."""
    A = _resample([Vector(v) for v in base_pts], 7); B = _resample([Vector(v) for v in tip_pts], 7)
    nrm = (B[3] - A[3]).cross(A[-1] - A[0])
    if nrm.length < 1e-9: nrm = Vector((1, 0, 0))
    nrm.normalize()
    sides = []
    for side in (1, -1):
        G = []
        for j in range(rows):
            t = j / (rows - 1); row = []
            for i, (a, b) in enumerate(zip(A, B)):
                edge = math.sin(math.pi * i / 6) ** 0.5                                   # thin toward the leading/trailing edges
                th = S * thick * (2.2 * (1 - t) ** 1.3 + 0.25) * edge
                w = bone if isinstance(bone, (str, list)) else bone(j)
                row.append(p.v(a.lerp(b, t) + nrm * side * th * 0.5, w, tip_from + (1 - tip_from) * t))
            G.append(row)
        for j in range(rows - 1):
            for i in range(6):
                q = [G[j][i], G[j][i + 1], G[j + 1][i + 1], G[j + 1][i]]
                p.f(q if side > 0 else q[::-1])
        sides.append(G)
    for j in range(rows - 1):                                                             # close the leading and trailing edges
        for i in (0, 6):
            q = [sides[0][j][i], sides[0][j + 1][i], sides[1][j + 1][i], sides[1][j][i]]
            p.f(q if i == 0 else q[::-1])

# =============================================================================== WHALE (beluga)
def build_whale():
    sk = Skel(S)
    P = [("beak", 0, 0.49, -0.025, 0.026, 0.022), ("melon", 0, 0.425, 0.02, 0.07, 0.068), ("head", 0, 0.36, -0.005, 0.082, 0.078),
         ("neck", 0, 0.29, -0.005, 0.088, 0.083), ("chest", 0, 0.16, 0.0, 0.112, 0.106), ("belly", 0, -0.01, -0.006, 0.106, 0.1),
         ("lumbar", 0, -0.17, 0.0, 0.072, 0.072), ("ped", 0, -0.31, 0.004, 0.034, 0.045), ("stock", 0, -0.41, 0.0, 0.016, 0.022)]
    for nm, *v in P: sk.v(nm, *v)
    sk.e("beak", "melon", "head", "neck", "chest", "belly", "lumbar", "ped", "stock")
    sk.v("jaw", 0, 0.43, -0.05, 0.035, 0.02); sk.e("jaw", "head")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.0035), faces=SP.get("faces", 6000), floor=False, stiffness=2.2)
    def ridge(co, n):                                     # low dorsal ridge instead of a fin, and a soft neck crease
        y = co.y / S
        if n.z > 0.6 and -0.2 < y < 0.05: co += n * S * 0.012 * math.sin(math.pi * (y + 0.2) / 0.25)
        if 0.27 < y < 0.31: co -= n * S * 0.004
        return co
    displace(body, ridge)
    bones = [("body", (0, -0.01, 0), (0, 0.16, 0), None, False), ("neck", (0, 0.16, 0), (0, 0.29, 0), "body", True),
             ("head", (0, 0.29, 0), (0, 0.5, -0.02), "neck", True),
             ("tail1", (0, -0.01, 0), (0, -0.17, 0), "body", False), ("tail2", (0, -0.17, 0), (0, -0.31, 0.004), "tail1", True),
             ("tail3", (0, -0.31, 0.004), (0, -0.41, 0), "tail2", True), ("fluke", (0, -0.41, 0), (0, -0.49, 0), "tail3", True)]
    for s, sx in (("L", 1), ("R", -1)):
        bones += [("fin" + s, (sx * 0.08, 0.2, -0.06), (sx * 0.17, 0.15, -0.1), "body", False)]
    nd = ("finL", "finR", "fluke")
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd)
    bvh = bvh_of(body); parts = []
    p = Part("eyes", 3)
    for sx in (1, -1):
        d = Vector((sx, 0.15, 0.1)).normalized()
        loc, n = ray(bvh, U((0, 0.39, -0.01)) + d * S, -d)
        if loc: p.sphere(loc - n * S * 0.002, S * 0.007, "head", sub=2)
    loc, n = ray(bvh, U((0, 0.33, 1)), (0, 0, -1))
    if loc: p.sphere(loc, S * 0.008, "head", scale=(1.6, 0.6, 0.3), sub=1)              # blowhole
    for sx in (1, -1):                                                                     # smiling mouth line
        for k in range(8):
            t = k / 7; d = Vector((sx, 0.1, -0.4)).normalized()
            loc, n = ray(bvh, U((0, 0.42 + 0.06 * t - 0.02, -0.035 - 0.006 * math.sin(math.pi * t))) + d * S, -d)
            if loc: p.sphere(loc, S * 0.003, "head", scale=(1, 2.2, 0.6), sub=1)
    parts.append(p.finish())
    p = Part("flippers", 0)
    for s, sx in (("L", 1), ("R", -1)):
        p.sphere(U((sx * 0.13, 0.17, -0.085)), S * 0.06, "fin" + s, scale=(1.0, 0.55, 0.12), sub=3)
    parts.append(p.finish())
    p = Part("flukes", 0)
    for sx in (1, -1):
        root = [U((0, -0.41 - 0.012 * k, 0)) for k in range(4)]
        tip = [U((sx * (0.06 + 0.035 * k), -0.43 - 0.03 * k - 0.01 * k * k, 0)) for k in range(4)]
        _fin(p, root, tip, [("fluke", 1.0)], thick=0.004)
    parts.append(_recalc(p.finish()))
    return body, rig, parts, {}, mode

def anim_whale(A, info):
    X = (1, 0, 0)
    def R(b, deg, ax=X): return rotaxis(A, b, ax, deg)
    def swim(amp, cyc, look=0.0):
        def fn(t):
            w = 2 * math.pi * t * cyc; P = {}
            for i, b in enumerate(("tail1", "tail2", "tail3", "fluke")):
                P[b] = R(b, amp * (0.4 + 0.3 * i) * math.sin(w - i * 0.7))
            P["body"] = R("body", -amp * 0.15 * math.sin(w + 0.6))
            P["neck"] = qmul(R("neck", amp * 0.2 * math.sin(w + 1.2)), R("neck", look * math.sin(2 * math.pi * t), (0, 0, 1)))
            P["head"] = R("head", look * 0.4 * math.sin(2 * math.pi * t * 2), (0, 0, 1))
            for s, sx in (("L", 1), ("R", -1)): P["fin" + s] = R("fin" + s, sx * 8 * math.sin(w), (0, 1, 0))
            return P, (0, 0, S * 0.01 * math.sin(w))
        return fn
    clips = [("idle", swim(4, 1, 18), 180, 3, False), ("swim", swim(12, 1, 6), 60, 2, False), ("alert", swim(3, 2, 35), 90, 3, False)]
    return clips, dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="alert", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"])

# =============================================================================== SHARK (megalodon)
def build_shark():
    sk = Skel(S)
    for nm, *v in [("snout", 0, 0.49, 0.005, 0.03, 0.03), ("head", 0, 0.4, 0.0, 0.07, 0.062), ("chest", 0, 0.24, 0.0, 0.098, 0.1),
                   ("belly", 0, 0.06, 0.0, 0.092, 0.095), ("rear", 0, -0.12, 0.008, 0.06, 0.066), ("ped", 0, -0.27, 0.015, 0.024, 0.032),
                   ("stock", 0, -0.33, 0.02, 0.014, 0.02), ("jawB", 0, 0.31, -0.055, 0.07, 0.035), ("jawF", 0, 0.43, -0.04, 0.04, 0.02)]:
        sk.v(nm, *v)
    sk.e("snout", "head", "chest", "belly", "rear", "ped", "stock"); sk.e("jawF", "jawB", "chest")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.0032), faces=SP.get("faces", 6500), floor=False, stiffness=2.1)
    bones = [("body", (0, 0.06, 0), (0, 0.24, 0), None, False), ("head", (0, 0.24, 0), (0, 0.5, 0.005), "body", True),
             ("jaw", (0, 0.3, -0.05), (0, 0.44, -0.04), "head", False),
             ("tail1", (0, 0.06, 0), (0, -0.12, 0.008), "body", False), ("tail2", (0, -0.12, 0.008), (0, -0.27, 0.015), "tail1", True),
             ("tail3", (0, -0.27, 0.015), (0, -0.34, 0.02), "tail2", True)]
    for s, sx in (("L", 1), ("R", -1)): bones.append(("pec" + s, (sx * 0.07, 0.2, -0.05), (sx * 0.2, 0.1, -0.1), "body", False))
    nd = ("pecL", "pecR")
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd)
    bvh = bvh_of(body); parts = []
    fins = Part("fins", 0)
    def surf(y, x, z):
        d = Vector((x, 0, z)).normalized(); loc, n = ray(bvh, U((0, y, 0)) + d * S, -d); return loc if loc else U((x * 0.05, y, z * 0.05))
    # first dorsal: tall swept triangle; second dorsal small
    for (y0, y1, h, sw, bn) in ((0.12, -0.02, 0.16, 0.09, "body"), (-0.2, -0.24, 0.035, 0.02, "tail2")):
        root = [surf(y0 + (y1 - y0) * t, 0, 1) - Vector((0, 0, S * 0.006)) for t in (0, 0.5, 1)]
        tip = [root[0] + U((0, -sw, h)), root[0].lerp(root[2], 0.5) + U((0, -sw * 1.05, h * 0.98)), root[2] + U((0, -sw * 0.4, h * 0.25))]
        tip = [tip[0], tip[0].lerp(tip[1], 0.5), tip[2]]
        _fin(fins, root, tip, bn, thick=0.003)
    for s, sx in (("L", 1), ("R", -1)):                       # long pectorals
        root = [surf(0.23 - 0.07 * t, sx, -0.6) for t in (0, 0.5, 1)]
        apex = root[0] + U((sx * 0.13, -0.13, -0.075))                         # swept, sickle-shaped
        tip = [apex, apex + U((-sx * 0.012, -0.004, 0.004)), root[2] + U((sx * 0.035, -0.05, -0.018))]
        _fin(fins, root, tip, "pec" + s, thick=0.003)
        root = [surf(-0.08 - 0.04 * t, sx * 0.5, -1) for t in (0, 0.5, 1)]       # pelvic fins
        tip = [r + U((sx * 0.04, -0.04, -0.03)) for r in root]
        _fin(fins, root, tip, "tail1", thick=0.002)
    # crescent caudal: two swept lobes (upper bigger) meeting at a notch behind the tail stock
    _fin(fins, [U((0, -0.31, 0.032)), U((0, -0.33, 0.024)), U((0, -0.35, 0.016))], [U((0, -0.43, 0.165)), U((0, -0.44, 0.152)), U((0, -0.375, 0.03))], "tail3", thick=0.004)
    _fin(fins, [U((0, -0.31, 0.004)), U((0, -0.33, 0.008)), U((0, -0.35, 0.012))], [U((0, -0.405, -0.105)), U((0, -0.415, -0.098)), U((0, -0.372, 0.004))], "tail3", thick=0.004)
    parts.append(_recalc(fins.finish()))
    p = Part("eyes", 3)
    for sx in (1, -1):
        d = Vector((sx, 0.2, 0.25)).normalized(); loc, n = ray(bvh, U((0, 0.43, 0.0)) + d * S, -d)
        if loc: p.sphere(loc - n * S * 0.002, S * 0.007, "head", sub=2)
        for k in range(5):                                                       # gill slits
            d = Vector((sx, 0, -0.15)).normalized(); loc, n = ray(bvh, U((0, 0.31 - 0.022 * k, -0.01)) + d * S, -d)
            if loc: p.sphere(loc, S * 0.004, "head" if k < 2 else "body", scale=(0.4, 0.4, 7.0), sub=1)
    parts.append(p.finish())
    teeth = Part("teeth", 2)                                                      # rows of serrated triangles, upper on head, lower on jaw
    for row, (bn, zz, sgn) in enumerate((("head", -0.03, -1), ("jaw", -0.047, 1))):
        for k in range(22):
            t = k / 21; a = (t - 0.5) * 2.6
            c = U((math.sin(a) * 0.052 * (1 - 0.35 * abs(t - 0.5) * 2), 0.31 + 0.12 * math.cos(a * 0.6), zz))
            teeth.cone(c, (math.sin(a) * 0.1, 0.15, sgn), S * 0.016 * (1 - 0.4 * abs(t - 0.5) * 2), S * 0.006, bn, 4, flat=0.35)
    parts.append(teeth.finish())
    mouth = Part("mouth", 6)                                                      # dark mouth lining between the jaws
    mouth.sphere(U((0, 0.36, -0.04)), S * 0.05, [("head", 0.5), ("jaw", 0.5)], scale=(0.95, 1.3, 0.25), sub=2)
    parts.append(mouth.finish())
    return body, rig, parts, {}, mode

def anim_shark(A, info):
    Z = (0, 0, 1)
    def R(b, deg, ax=Z): return rotaxis(A, b, ax, deg)
    def swim(amp, cyc, gape=0.0):
        def fn(t):
            w = 2 * math.pi * t * cyc; P = {}
            for i, b in enumerate(("tail1", "tail2", "tail3")): P[b] = R(b, amp * (0.5 + 0.35 * i) * math.sin(w - i * 0.8))
            P["head"] = R("head", -amp * 0.18 * math.sin(w + 0.4))
            P["jaw"] = rotaxis(A, "jaw", (1, 0, 0), -gape * (0.6 + 0.4 * math.sin(2 * math.pi * t)))
            for s, sx in (("L", 1), ("R", -1)): P["pec" + s] = rotaxis(A, "pec" + s, (0, 1, 0), sx * 4 * math.sin(w))
            return P, (0, 0, 0)
        return fn
    def bite(t):
        o = seg(t, 0.0, 0.35) * (1 - seg(t, 0.45, 0.6)); P = swim(10, 2)(t)[0]
        P["jaw"] = rotaxis(A, "jaw", (1, 0, 0), -38 * o); P["head"] = qmul(P["head"], rotaxis(A, "head", (1, 0, 0), 10 * o))
        return P, (0, 0, 0)
    return ([("idle", swim(6, 1, 4), 120, 2, False), ("swim", swim(14, 1), 50, 1, False), ("alert", swim(8, 1, 14), 60, 2, False), ("bite", bite, 30, 1, True)],
            dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="alert", attackAnim="bite", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))

# =============================================================================== SIPHON (man o' war); size = float length, tentacles hang far below
def build_siphon():
    sk = Skel(S)
    sk.v("f0", 0, 0.38, 0.06, 0.12, 0.13); sk.v("f1", 0, 0.1, 0.1, 0.2, 0.21); sk.v("f2", 0, -0.2, 0.1, 0.19, 0.2); sk.v("f3", 0, -0.42, 0.04, 0.1, 0.11)
    sk.e("f0", "f1", "f2", "f3")
    body = metaball_body(NAME, sk, voxel=S * 0.008, faces=2500, floor=False)
    nT = SP.get("tents", 10); TL = SP.get("TL", 8.0)
    bones = [("body", (0, -0.3, 0.05), (0, 0.3, 0.05), None, False), ("sail", (0, 0.0, 0.18), (0, 0.0, 0.4), "body", False)]
    tents = []
    for i in range(nT):
        a = i / nT * math.tau; base = V(math.cos(a) * 0.12, -0.05 + math.sin(a) * 0.22, -0.08)
        pts = [base + V(0.0, 0.0, -TL * k / 3) for k in range(4)]
        for k in range(3): bones.append(("t%d_%d" % (i, k), tuple(pts[k]), tuple(pts[k + 1]), "body" if k == 0 else "t%d_%d" % (i, k - 1), k > 0))
        tents.append((base, i))
    nd = tuple(b[0] for b in bones if b[0] != "body")
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd); parts = []
    p = Part("sail", 5)                                                            # wavy crest along the top of the float
    root = [U((0, 0.32 - 0.6 * t, 0.17 + 0.05 * math.sin(math.pi * t))) for t in [k / 8 for k in range(9)]]
    tip = [r + U((0.02 * math.sin(k * 1.3), 0, 0.12 * math.sin(math.pi * (k / 8)) ** 0.7 + 0.02)) for k, r in enumerate(root)]
    _fin(p, root, tip, [("sail", 1.0)], thick=0.004)
    parts.append(_recalc(p.finish()))
    p = Part("polyps", 6); q = Part("tentacles", 4)
    for base, i in tents:                                                          # a polyp cluster, then a beaded fishing tentacle
        c = U(base)
        for k in range(5): p.sphere(c + U((random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04), -0.02 - 0.03 * k)), S * random.uniform(0.022, 0.035), "body", sub=1, jitter=0.2)
        n = 24; pts = []; rad = []; bn = []
        for k in range(n + 1):
            t = k / n; z = -0.1 - TL * t * random.uniform(0.85, 1.0)
            pts.append(c + U((0.03 * math.sin(t * 40 + i), 0.03 * math.cos(t * 33 + i), z + 0.1)))
            rad.append(S * 0.014 * (1 - 0.6 * t)); bi = min(2, int(t * 3)); bn.append([("t%d_%d" % (i, bi), 1.0)])
        _ring_sweep(q, pts, rad, bn, segs=5)
        for k in range(2, n, 2): q.sphere(pts[k], S * 0.02 * (1 - 0.5 * k / n), bn[k], sub=1)
    parts += [p.finish(), q.finish()]
    return body, rig, parts, dict(nT=nT), mode

def anim_siphon(A, info):
    nT = info["nT"]
    def drift(amp, cyc):
        def fn(t):
            P = {"body": rotaxis(A, "body", (0, 1, 0), 4 * math.sin(2 * math.pi * t * cyc)), "sail": rotaxis(A, "sail", (0, 1, 0), 6 * math.sin(2 * math.pi * t * cyc + 1))}
            for i in range(nT):
                for k in range(3):
                    P["t%d_%d" % (i, k)] = qmul(rotaxis(A, "t%d_%d" % (i, k), (1, 0, 0), amp * math.sin(2 * math.pi * t * cyc - k * 0.9 + i)),
                                                rotaxis(A, "t%d_%d" % (i, k), (0, 1, 0), amp * 0.7 * math.cos(2 * math.pi * t * cyc - k * 0.7 + i * 1.7)))
            return P, (0, 0, S * 0.02 * math.sin(2 * math.pi * t * cyc * 2))
        return fn
    def sting(t):
        P, o = drift(14, 2)(t)
        for i in range(nT): P["t%d_0" % i] = qmul(P["t%d_0" % i], rotaxis(A, "t%d_0" % i, (1, 0, 0), -25 * math.sin(math.pi * t)))
        return P, o
    return ([("idle", drift(6, 1), 240, 4, False), ("move", drift(9, 1), 180, 4, False), ("alert", drift(12, 2), 90, 3, False), ("sting", sting, 30, 1, True)],
            dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="alert", attackAnim="sting"))

# =============================================================================== NAUTILUS; size = shell diameter
def build_nautilus():
    turns = 2.3; b = math.log(3.0) / (2 * math.pi)                                # whorl triples each turn
    def spiral(th):
        r = 0.36 * math.exp(b * (th - turns * math.tau))
        return V(0, -math.sin(th) * r, math.cos(th) * r + 0.0), r
    sk = Skel(S); sk.v("c", 0, 0.0, 0.0, 0.25, 0.4); sk.v("h", 0, -0.32, -0.26, 0.12, 0.12); sk.e("c", "h")
    shell = Part("shell", 0)                                                       # the body mesh is the shell itself
    n = 90; pts = []; rad = []; tp = []
    for i in range(n + 1):
        th = turns * math.tau * i / n
        c, r = spiral(th); pts.append(U(c)); rad.append(S * r * 0.82); tp.append(i / n)
    rings = _ring_sweep(shell, pts, rad, ["body"] * len(pts), segs=18, tips=tp, flat=0.75, up=(1, 0, 0), cap=False)
    shell.f(rings[0][::-1])
    end_c, end_r = spiral(turns * math.tau)
    bones = [("body", (0, 0.0, -0.1), (0, 0.0, 0.3), None, False), ("hood", tuple(end_c + V(0, -0.02, -0.05)), tuple(end_c + V(0, -0.14, -0.1)), "body", False)]
    for k in range(6):
        a = k / 6 * math.tau
        base = end_c + V(math.cos(a) * 0.08, -0.12, -0.1 + math.sin(a) * 0.08)
        bones += [("arm%d" % k, tuple(base), tuple(base + V(0, -0.16, -0.04)), "hood", False), ("armt%d" % k, tuple(base + V(0, -0.16, -0.04)), tuple(base + V(0, -0.3, -0.08)), "arm%d" % k, True)]
    shell_o = shell.finish()
    body = shell_o; body.name = NAME + "_body"
    rig = make_rig(NAME, sk, bones)
    for o in (body,): o.parent = rig
    mod = body.modifiers.new("Armature", 'ARMATURE'); mod.object = rig
    parts = []
    p = Part("soft", 4)                                                            # hood and a fringe of ~40 tentacles from the aperture
    p.sphere(U(end_c + V(0, -0.06, -0.04)), S * end_r * 0.75, [("hood", 1.0)], scale=(0.95, 0.7, 0.85), sub=3, jitter=0.08)
    for k in range(40):
        a = random.uniform(0, math.tau); rr = random.uniform(0.02, 0.09)
        base = end_c + V(math.cos(a) * rr, -0.1, -0.1 + math.sin(a) * rr)
        g = k % 6
        p.cone(U(base), (math.cos(a) * 0.4, -1, -0.25 + math.sin(a) * 0.4), S * random.uniform(0.18, 0.3), S * 0.012, [("arm%d" % g, 0.5), ("armt%d" % g, 0.5)], 5, bend=(0, 0, -0.25))
    parts.append(p.finish())
    p = Part("eyes", 3)
    for sx in (1, -1): p.sphere(U(end_c + V(sx * 0.095, -0.03, 0.0)), S * 0.025, "hood", sub=2)
    parts.append(p.finish())
    return body, rig, parts, {}, "explicit"

def anim_nautilus(A, info):
    def hover(cyc, amp, pulse):
        def fn(t):
            w = 2 * math.pi * t * cyc; P = {"body": rotaxis(A, "body", (1, 0, 0), 3 * math.sin(w))}
            for k in range(6):
                P["arm%d" % k] = rotaxis(A, "arm%d" % k, (1, 0, 0) if k % 2 else (0, 0, 1), amp * math.sin(w + k))
                P["armt%d" % k] = rotaxis(A, "armt%d" % k, (1, 0, 0), amp * 1.4 * math.sin(w + k - 0.8))
            P["hood"] = rotaxis(A, "hood", (1, 0, 0), pulse * math.sin(w))
            return P, (0, -S * 0.03 * pulse / 10 * max(0, math.sin(w)), S * 0.01 * math.sin(w * 0.5))
        return fn
    return ([("idle", hover(1, 8, 2), 120, 3, False), ("swim", hover(2, 14, 10), 45, 1, False), ("alert", hover(3, 4, 0), 60, 2, False)],
            dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="alert", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))

# =============================================================================== VENT (black smoker with tubeworms); size = chimney height
def build_vent():
    sk = Skel(S)
    sk.v("base", 0, 0, 0.04, 0.42, 0.1); sk.v("m1", 0.03, 0.02, 0.3, 0.17, 0.2); sk.v("m2", -0.02, 0.0, 0.62, 0.12, 0.18); sk.v("top", 0.0, 0.01, 0.92, 0.09, 0.09)
    for k in range(4):
        a = k / 4 * math.tau + 0.5; sk.v("lob%d" % k, math.cos(a) * 0.25, math.sin(a) * 0.25, 0.08, 0.14, 0.09); sk.e("base", "lob%d" % k)
    sk.e("base", "m1", "m2", "top")
    body = metaball_body(NAME, sk, voxel=S * 0.008, faces=4000, floor=True)
    def crust(co, n):
        return co + n * S * (0.02 * noise.noise(co / S * 8.0) + 0.008 * noise.noise(co / S * 26.0))
    displace(body, crust)
    nW = SP.get("worms", 44)
    bvh = bvh_of(body); worms = []
    for k in range(nW):
        for _ in range(30):
            a = random.uniform(0, math.tau); h = random.uniform(0.02, 0.5) ** 1.4
            d = Vector((math.cos(a), math.sin(a), 0.1))
            loc, nn = ray(bvh, U((0, 0, h)) + d * S, -d)
            if loc is not None and nn.z > -0.3: break
        L = S * random.uniform(0.12, 0.3) * (1.2 - h)
        dirv = (nn * 0.35 + Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 1.0))).normalized()
        worms.append((loc - nn * S * 0.01, dirv, L))
    bones = [("body", (0, 0, 0), (0, 0, 0.3), None, False)]
    for k, (b0, d, L) in enumerate(worms):
        top = b0 + d * L
        bones.append(("w%d" % k, tuple(top / S), tuple((top + d * S * 0.05) / S), "body", False))
    ndw = tuple("w%d" % k for k in range(nW))
    rig = make_rig(NAME, sk, bones, nondeform=ndw); mode = skin(body, rig, nondeform=ndw); parts = []
    tubes = Part("tubes", 2); plumes = Part("plumes", 4)
    for k, (b0, d, L) in enumerate(worms):
        tubes.tube(b0, b0 + d * L, S * 0.016, S * 0.018, "body", rings=3, segs=7, tip_from=0.0)
        top = b0 + d * L
        for q in range(7):                                                         # feathery red plume
            a = q / 7 * math.tau
            v = (d * 0.9 + Vector((math.cos(a), math.sin(a), 0)) * 0.55).normalized()
            plumes.cone(top + d * S * 0.005, v, S * random.uniform(0.04, 0.06), S * 0.01, "w%d" % k, 4, flat=0.4)
    mouth = Part("mouth", 6)                                                       # glowing orifice at the chimney top
    loc, nn = ray(bvh, U((0, 0.01, 2.0)), (0, 0, -1))
    if loc: mouth.sphere(loc + Vector((0, 0, S * 0.01)), S * 0.06, "body", scale=(1, 1, 0.35), sub=2)
    parts += [tubes.finish(), plumes.finish(), mouth.finish()]
    return body, rig, parts, dict(nW=nW), mode

def anim_vent(A, info):
    nW = info["nW"]
    def sway(amp, retract=0.0):
        def fn(t):
            P = {}
            for k in range(nW):
                sc = 1.0 - (1.0 - 0.05) * retract * seg((t * 4 + k * 0.13) % 1.0 if retract < 1 else 1.0, 0.0, 0.2) if retract else 1.0
                P["w%d" % k] = (qmul(rotaxis(A, "w%d" % k, (1, 0, 0), amp * math.sin(2 * math.pi * t + k)), rotaxis(A, "w%d" % k, (0, 1, 0), amp * math.cos(2 * math.pi * t + k * 1.7))), sc)
            return P, (0, 0, 0)
        return fn
    return ([("idle", sway(10), 150, 5, False), ("alert", sway(2, 1.0), 60, 6, False)],
            dict(idleAnim="idle", moveAnim="idle", fleeAnim="idle", alertAnim="alert"))

# =============================================================================== GLOWWORM curtain; size = hanging height (threads hang from z = size down)
def build_glowworm():
    H = 1.0; nT = SP.get("threads", 160); R = SP.get("spread", 0.45)
    sk = Skel(S); sk.v("a", 0, 0, H, R * 0.9, 0.025); sk.v("b", 0.1, 0.05, H, R * 0.6, 0.02); sk.e("a", "b")
    body = metaball_body(NAME, sk, voxel=S * 0.01, faces=1500, floor=False)           # the silk mat / nest on the ceiling
    nb = 6
    bones = [("body", (0, 0, H), (0, 0, H + 0.05), None, False)]
    for k in range(nb):
        a = k / nb * math.tau
        bones.append(("g%d" % k, (math.cos(a) * R * 0.5, math.sin(a) * R * 0.5, H), (math.cos(a) * R * 0.5, math.sin(a) * R * 0.5, H - 0.6), "body", False))
    ndg = tuple("g%d" % k for k in range(nb))
    rig = make_rig(NAME, sk, bones, nondeform=ndg); mode = skin(body, rig, nondeform=ndg); parts = []
    silk = Part("silk", 5); beads = Part("beads", 6); larvae = Part("larvae", 6)
    for i in range(nT):
        a = random.uniform(0, math.tau); r = R * math.sqrt(random.random())
        x, y = math.cos(a) * r, math.sin(a) * r
        Lh = random.uniform(0.15, 0.75)
        g = int(((math.atan2(y, x) % math.tau) / math.tau) * nb) % nb
        top = U((x, y, H - 0.01)); bot = U((x, y, H - Lh))
        silk.tube(top, bot, S * 0.0018, S * 0.0012, [("g%d" % g, 1.0)], rings=1, segs=3, cap=False)
        nbd = int(Lh * 14)
        for k in range(nbd):                                                       # sticky glowing droplets down the line (6-vertex beads)
            z = H - 0.03 - (Lh - 0.03) * (k + random.random() * 0.5) / max(1, nbd)
            r_ = S * random.uniform(0.004, 0.007); c_ = U((x, y, z)); w_ = [("g%d" % g, 1.0)]
            vv = [beads.v(c_ + Vector(o) * r_, w_) for o in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1.4), (0, 0, -1.4))]
            for a_, b_ in ((0, 2), (2, 1), (1, 3), (3, 0)):
                beads.f([vv[a_], vv[b_], vv[4]]); beads.f([vv[b_], vv[a_], vv[5]])
        if i % 3 == 0: larvae.sphere(top + U((0, 0, -0.008)), S * 0.008, "body", scale=(1, 2.6, 0.7), sub=1)
    parts += [silk.finish(), beads.finish(), larvae.finish()]
    return body, rig, parts, dict(nb=nb), mode

def anim_glowworm(A, info):
    nb = info["nb"]
    def sway(amp, reel=0.0):
        def fn(t):
            P = {}
            for k in range(nb):
                q = qmul(rotaxis(A, "g%d" % k, (1, 0, 0), amp * math.sin(2 * math.pi * t + k)), rotaxis(A, "g%d" % k, (0, 1, 0), amp * 0.8 * math.cos(2 * math.pi * t + k * 1.3)))
                P["g%d" % k] = (q, (1.0, 1.0 - reel * seg(t, 0.0, 0.5), 1.0)) if reel else q
            return P, (0, 0, 0)
        return fn
    return ([("idle", sway(2.5), 240, 6, False), ("alert", sway(1.0, 0.45), 120, 6, False)],
            dict(idleAnim="idle", moveAnim="idle", fleeAnim="idle", alertAnim="alert"))

BUILD["whale"] = (build_whale, anim_whale); BUILD["shark"] = (build_shark, anim_shark); BUILD["siphon"] = (build_siphon, anim_siphon)
BUILD["nautilus"] = (build_nautilus, anim_nautilus); BUILD["vent"] = (build_vent, anim_vent); BUILD["glowworm"] = (build_glowworm, anim_glowworm)

# =============================================================================== avian feature: hindwing tails (moths)
_avian_feats_base = avian_feats
def avian_feats(L):
    parts = _avian_feats_base(L)
    if "tails" in FE:
        p = Part("tails", 5); cr = SP.get("chordRoot", 0.3); span = SP["span"]
        for s, sx in (("L", 1), ("R", -1)):
            base = U((sx * span * 0.13, -cr * 1.85, -0.01))
            rows = []
            for j in range(2):
                row = []
                for k in range(6):
                    t = k / 5; w = S * 0.05 * (1 - 0.6 * t) * (1 if j else -1)
                    c = base + U((sx * (0.06 * t + 0.03 * t * t), -SP.get("tailL", 0.9) * t, -0.02 * t)) + Vector((w, 0, 0))
                    row.append((c, [("wing2" + s, 1.0)], 0.4 + 0.6 * t))
                rows.append(row)
            p.grid(rows, flip=sx < 0, thickness=S * 0.0015)
        parts.append(p.finish())
    return parts

exec(open(os.path.join(TOOLS, "fauna_kerbin3.py"), encoding="utf-8").read(), globals())
