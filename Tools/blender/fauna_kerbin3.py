# Xenobiology — Kerbin expansion 3 builders for fauna_build.py (exec'd from fauna_kerbin2.py, shares its globals).
# Archetypes: "lepid"  (butterflies: furry thorax, segmented abdomen, clubbed antennae, coiled proboscis, folded legs and four
#                       separate, flexing wings whose ornate patterns come from Tools/lepid_wings.py -> lepid/<name>_wings.png/.json)
#             "turtle" (sea tortoise: a real scuted carapace with growth rings, serrated marginals, plastron, beaked head,
#                       scaly flippers with claws)
#             "nautilus2" (chambered nautilus with radial flame stripes, growth lines, a ribbed hood, ~90 tentacles,
#                       a siphon and a big pinhole eye)
# Units are fractions of `size` (for lepid: the forewing length); +Y forward, Z up.
import json
from mathutils import geometry
LEPID_DIR = os.path.join(os.path.dirname(PREVIEW_DIR), "lepid")      # outside GameData: KSP would load the PNG atlases as textures

# =============================================================================== LEPID (butterflies)
def _pip(pt, poly):
    x, y = pt; ins = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): ins = not ins
    return ins

def build_lepid():
    WJ = json.load(open(os.path.join(LEPID_DIR, NAME + "_wings.json")))
    sk = Skel(S)
    bl = SP.get("bodyL", 1.0)                                     # body length relative to the forewing
    sk.v("head", 0, 0.29 * bl, 0.0, 0.05, 0.05); sk.v("thorax", 0, 0.15 * bl, 0.0, 0.068, 0.072); sk.v("th2", 0, 0.05 * bl, -0.005, 0.058, 0.062)
    ab = [("a1", -0.04, -0.01, 0.05), ("a2", -0.15, -0.018, 0.052), ("a3", -0.27, -0.026, 0.048), ("a4", -0.39, -0.034, 0.038), ("a5", -0.5, -0.04, 0.024)]
    for nm, y, z, r in ab: sk.v(nm, 0, y * bl * SP.get("abdL", 1.0), z, r * SP.get("abdR", 1.0), r * SP.get("abdR", 1.0))
    sk.e("head", "thorax", "th2", "a1", "a2", "a3", "a4", "a5")
    body = metaball_body(NAME, sk, voxel=S * 0.006, faces=2600, floor=False, stiffness=2.4)
    def segs(co, n):                                               # abdominal segment rings
        y = co.y / S
        if y < -0.05 * bl: co -= n * S * 0.004 * (0.5 + 0.5 * math.cos((y / (0.11 * bl)) * math.tau))
        return co
    displace(body, segs)
    FB = Vector((0.045, 0.17 * bl, 0.035)); HB = Vector((0.042, 0.07 * bl, 0.025))
    sweepF, sweepH = math.radians(SP.get("sweepF", 10)), math.radians(SP.get("sweepH", -6))
    def wpos(x, y, base, sweep, side, zoff):
        c, s = math.cos(sweep), math.sin(sweep)
        X = x * c - y * s; Y = x * s + y * c
        camber = 0.025 * math.sin(math.pi * min(1.0, max(0.0, x))) * (1 - abs(y) * 0.6)
        return U((side * (base.x + X), base.y + Y, base.z + zoff + camber))
    bones = [("body", (0, 0.03 * bl, 0), (0, 0.22 * bl, 0), None, False), ("head", (0, 0.22 * bl, 0), (0, 0.34 * bl, 0.0), "body", True),
             ("abd1", (0, 0.03 * bl, 0), (0, -0.16 * bl, -0.018), "body", False), ("abd2", (0, -0.16 * bl, -0.018), (0, -0.33 * bl, -0.03), "abd1", True),
             ("abd3", (0, -0.33 * bl, -0.03), (0, -0.52 * bl, -0.04), "abd2", True)]
    wb = []
    for s, sx in (("R", 1), ("L", -1)):
        for nm, base, sweep, zo in (("fw", FB, sweepF, 0.0), ("hw", HB, sweepH, -0.006)):
            mid = 0.42 if nm == "fw" else 0.32; tipx = 1.0 if nm == "fw" else 0.7
            p0 = wpos(0, 0, base, sweep, sx, zo) / S; p1 = wpos(mid, 0, base, sweep, sx, zo) / S; p2 = wpos(tipx, 0, base, sweep, sx, zo) / S
            bones += [(nm + "1" + s, tuple(p0), tuple(p1), "body", False), (nm + "2" + s, tuple(p1), tuple(p2), nm + "1" + s, True)]
            wb += [nm + "1" + s, nm + "2" + s]
    rig = make_rig(NAME, sk, bones, nondeform=tuple(wb)); mode = skin(body, rig, nondeform=tuple(wb))
    parts = []
    # ---- wings: Delaunay-filled outlines, double sided, each side mapped into its cell of the painted atlas
    wings = Part("wings", 5); WUV = {}
    size = WJ["size"]; cellpx = size / 2
    for nm, key, base, sweep, zo in (("fw", "fore", FB, sweepF, 0.0), ("hw", "hind", HB, sweepH, -0.006)):
        outline = [Vector(p) for p in WJ[key]]
        x0, y0, x1, y1 = WJ[key + "Box"]; sc = cellpx / (x1 - x0)
        pts = list(outline); step = 0.055
        xs = [p.x for p in outline]; ys = [p.y for p in outline]
        yy = min(ys) + step / 2
        while yy < max(ys):
            xx = min(xs) + step / 2
            while xx < max(xs):
                q = (xx + (random.random() - 0.5) * step * 0.3, yy + (random.random() - 0.5) * step * 0.3)
                if _pip(q, [(p.x, p.y) for p in outline]):
                    dmin = min((Vector(q) - p).length for p in outline[::2])
                    if dmin > step * 0.45: pts.append(Vector(q))
                xx += step
            yy += step
        n = len(outline)
        cdt = geometry.delaunay_2d_cdt([p.to_2d() for p in pts], [(i, (i + 1) % n) for i in range(n)], [list(range(n))], 1, 1e-7)
        V2, F = cdt[0], cdt[2]
        mx = max(p.x for p in outline)
        for s, sx in (("R", 1), ("L", -1)):
            for under in (False, True):
                cx, cy = WJ["cells"][key + ("_under" if under else "_top")]
                vs = []
                for p in V2:
                    w2 = smooth01((p.x / mx - 0.32) / 0.5)
                    co = wpos(p.x, p.y, base, sweep, sx, zo + (-0.0018 if under else 0.0018))
                    v = wings.v(co, [(nm + "1" + s, 1 - w2), (nm + "2" + s, w2)], tip=min(1.0, max(0.0, p.x / mx)))
                    col = (p.x - x0) * sc + cx * cellpx; row = (y1 - p.y) * sc + cy * cellpx
                    WUV[len(wings.w) - 1] = (col / size, 1.0 - row / size)
                    vs.append(v)
                for f in F:
                    tri = [vs[i] for i in f]
                    # top faces look up, undersides look down; the left wing is mirrored so its winding flips
                    if (sx < 0) != under: tri = tri[::-1]
                    wings.f(tri)
    wings_o = wings.finish()
    a = wings_o.data.attributes.new("wuv", 'FLOAT_VECTOR', 'POINT')
    for i, uv in WUV.items(): a.data[i].vector = (uv[0], uv[1], 1.0)
    parts.append(wings_o)
    # ---- head: big compound eyes, clubbed antennae, coiled proboscis, palps
    hc = U((0, 0.29 * bl, 0.0)); p = Part("eyes", 3)
    for sx in (1, -1): p.sphere(hc + U((sx * 0.032, 0.012, 0.01)), S * 0.03, "head", scale=(0.9, 1.0, 1.05), sub=3)
    parts.append(p.finish())
    p = Part("antennae", 2)
    for sx in (1, -1):
        a0 = hc + U((sx * 0.015, 0.035, 0.03)); d = Vector((sx * 0.35, 1.0, 0.55)).normalized(); L = S * SP.get("antL", 0.55)
        pts = [a0 + d * L * (i / 6) + Vector((sx * 0.08, 0, -0.06)) * L * (i / 6) ** 2 for i in range(7)]
        for i in range(6): p.tube(pts[i], pts[i + 1], S * 0.005, S * 0.0045, "head", rings=1, segs=5, cap=False)
        p.sphere(pts[-1], S * 0.011, "head", scale=(0.8, 1.6, 0.8), sub=1)
    coil = [hc + U((0, 0.045 + 0.018 * math.cos(t * 2.2) * (1 - t / 9), -0.03 - 0.018 * math.sin(t * 2.2) * (1 - t / 9) - 0.001 * t)) for t in [i * 0.5 for i in range(19)]]
    for i in range(len(coil) - 1): p.tube(coil[i], coil[i + 1], S * 0.004, S * 0.004, "head", rings=1, segs=4, cap=False)
    parts.append(p.finish())
    # ---- legs folded under the thorax (6), and a fuzz of hair-scales on the thorax
    p = Part("legs", 2)
    for k, (y, ang) in enumerate(((0.2, 35), (0.13, 5), (0.07, -25))):
        for sx in (1, -1):
            b0 = U((sx * 0.03, y * bl, -0.04)); a = math.radians(ang)
            knee = b0 + U((sx * 0.07, 0.05 * math.sin(a), -0.03)); foot = knee + U((sx * 0.03, 0.09 * math.sin(a) - 0.02, -0.07))
            p.tube(b0, knee, S * 0.008, S * 0.006, "body", rings=1, segs=4); p.tube(knee, foot, S * 0.006, S * 0.003, "body", rings=1, segs=4)
    parts.append(p.finish())
    bvh = bvh_of(body); fur = Part("fuzz", 4)
    for k in range(240):
        th = random.uniform(0, math.tau); y = random.uniform(-0.04, 0.27) * bl
        d = Vector((math.cos(th), 0, math.sin(th)))
        loc, n = ray(bvh, U((0, y, 0)) + d * S, -d)
        if loc is None or n.z < -0.6: continue
        bn = "head" if y > 0.23 * bl else "body"
        fur.cone(loc - n * S * 0.003, n + Vector((0, -0.4, 0.2)), S * random.uniform(0.02, 0.04), S * 0.006, bn, segs=3)
    parts.append(fur.finish())
    return body, rig, parts, {}, mode

def anim_lepid(A, info):
    Y = (0, 1, 0); X = (1, 0, 0)
    def wings(P, ang, hang, flex, twist):
        for s, sx in (("R", 1), ("L", -1)):
            P["fw1" + s] = qmul(rotaxis(A, "fw1" + s, Y, -sx * ang), rotaxis(A, "fw1" + s, X, twist))
            P["hw1" + s] = qmul(rotaxis(A, "hw1" + s, Y, -sx * hang), rotaxis(A, "hw1" + s, X, -twist * 0.5))
            P["fw2" + s] = rotaxis(A, "fw2" + s, Y, -sx * flex)
            P["hw2" + s] = rotaxis(A, "hw2" + s, Y, -sx * flex * 1.2)
    mid, amp = SP.get("strokeMid", 25), SP.get("strokeAmp", 52)
    def beat(ph):                                                  # one wingbeat: angle, hind angle, flex, twist, body bob
        w = 2 * math.pi * ph
        return (mid + amp * math.sin(w), mid + amp * 0.85 * math.sin(w - 0.35), -14 * math.cos(w), 12 * math.cos(w), -0.03 * S * math.sin(w))
    def flap(t):
        ph = (t * 2) % 1.0; P = {}
        a, h, fl, tw, z = beat(ph); wings(P, a, h, fl, tw)
        P["abd1"] = rotaxis(A, "abd1", X, 5 * math.sin(2 * math.pi * ph + 1.0)); P["abd2"] = rotaxis(A, "abd2", X, 4 * math.sin(2 * math.pi * ph + 0.4))
        return P, (0, 0, z)
    def glide(t):                                                  # three fluttering beats, then a two-second glide on raised wings
        P = {}
        if t < 1 / 3:
            ph = (t * 9) % 1.0; a, h, fl, tw, z = beat(ph)
        else:
            u = (t - 1 / 3) / (2 / 3); s = math.sin(2 * math.pi * u)
            a, h, fl, tw, z = mid + 5 * s, mid + 4 * s, 3 * s, 0.0, 0.01 * S * s
        wings(P, a, h, fl, tw)
        P["abd1"] = rotaxis(A, "abd1", X, 3 * math.sin(2 * math.pi * t)); P["head"] = rotaxis(A, "head", (0, 0, 1), 6 * math.sin(2 * math.pi * t))
        return P, (0, 0, z)
    ff = SP.get("flapFrames", 10)
    return ([("glide", glide, ff * 9, 1, False), ("flap", flap, ff * 2, 1, False)],
            dict(idleAnim="glide", moveAnim="glide", fleeAnim="flap", alertAnim="flap", flapAnim="flap", fleeAnimSpeed=SP["fleeSpeed"]))

BUILD["lepid"] = (build_lepid, anim_lepid)

_prev_post_uv = globals().get("post_uv")
def post_uv(body):
    if _prev_post_uv: _prev_post_uv(body)
    me = body.data
    if "wuv" not in me.attributes or not me.uv_layers: return
    uv = me.uv_layers.active.data; pa = me.attributes["part"].data; wv = me.attributes["wuv"].data
    for f in me.polygons:                                          # wings: straight onto the painted atlas (top 3/4 of the texture)
        wing = pa[f.index].value == 5
        for li in f.loop_indices:
            if wing:
                w = wv[me.loops[li].vertex_index].vector; uv[li].uv = (w[0], 0.25 + 0.75 * w[1])
            else:                                                  # everything else squeezed into the bottom-left corner
                uv[li].uv = (uv[li].uv.x * 0.25, uv[li].uv.y * 0.25)

def post_nodes(N, c, g):
    if SP.get("arch") != "lepid": return c, g
    img = bpy.data.images.load(os.path.join(LEPID_DIR, NAME + "_wings.png"), check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    t = N.node('ShaderNodeTexImage', image=img, interpolation='Cubic', extension='EXTEND')
    N.L(N.vattr("wuv"), t.inputs['Vector'])
    return N.mix(c, t.outputs['Color'], N.is_part(5)), g

# =============================================================================== TURTLE (sea tortoise); size = overall length
def _scute(rho, th, u, v):
    """Scute id and distance (unit-disk units) to the nearest seam, for a point of the carapace in its unit-disk plan."""
    if rho > 0.82:                                                         # marginals: 25 around the rim (nuchal at the front)
        n = 25; a = ((th - math.pi / 2) / math.tau) % 1.0 * n + 0.5
        k = int(a) % n; da = abs(a - round(a)) / n * math.tau * rho
        return 100 + k, min(rho - 0.82, da)
    wv = 0.25 * (1 - 0.35 * v * v)                                         # vertebral half-width
    if abs(u) < wv:
        bands = (-0.84, -0.5, -0.17, 0.17, 0.5, 0.84)
        k = sum(1 for b in bands if v > b) - 1
        return 10 + k, min(wv - abs(u), min(abs(v - b) for b in bands), 0.82 - rho)
    vs = v + 0.25 * (abs(u) - wv)                                          # costal seams slant back towards the rim
    bands = (-0.9, -0.42, 0.0, 0.42, 0.9)
    k = sum(1 for b in bands if vs > b) - 1
    return 20 + k * 2 + (u > 0), min(abs(u) - wv, min(abs(vs - b) for b in bands), 0.82 - rho)

def build_turtle():
    sk = Skel(S)
    for nm, *pv in [("core", 0, -0.02, 0.12, 0.17, 0.055), ("neck0", 0, 0.22, 0.115, 0.06, 0.05), ("neck1", 0, 0.31, 0.125, 0.055, 0.05),
                    ("head", 0, 0.385, 0.13, 0.058, 0.055), ("snout", 0, 0.445, 0.122, 0.038, 0.036), ("tail0", 0, -0.27, 0.1, 0.04, 0.03), ("tail1", 0, -0.39, 0.085, 0.015, 0.012),
                    ("shR", 0.13, 0.18, 0.09, 0.05, 0.03), ("shL", -0.13, 0.18, 0.09, 0.05, 0.03), ("hpR", 0.11, -0.2, 0.09, 0.045, 0.028), ("hpL", -0.11, -0.2, 0.09, 0.045, 0.028)]:
        sk.v(nm, *pv)
    sk.e("tail1", "tail0", "core", "neck0", "neck1", "head", "snout"); sk.e("shR", "core", "shL"); sk.e("hpR", "core", "hpL")
    body = metaball_body(NAME, sk, voxel=S * 0.0045, faces=4500, floor=False, stiffness=2.2)
    def skinbump(co, n): return co + n * S * 0.0025 * noise.noise(co / S * 60.0)          # pebbly skin
    displace(body, skinbump)
    YC, LH, WH, ZR, HD, ZP = -0.02, 0.31, 0.245, 0.10, 0.17, 0.045
    def plan(rho, th):
        u, v = rho * math.cos(th), rho * math.sin(th)
        w = WH * (1 - 0.22 * max(0.0, -v) ** 2) * (1 + 0.05 * max(0.0, v))
        return u, v, u * w, YC + v * LH
    bones = [("body", (0, -0.05, 0.12), (0, 0.15, 0.12), None, False), ("neck", (0, 0.22, 0.115), (0, 0.34, 0.125), "body", False),
             ("head", (0, 0.34, 0.125), (0, 0.47, 0.12), "neck", True), ("tail", (0, -0.27, 0.1), (0, -0.41, 0.08), "body", False)]
    for s, sx in (("R", 1), ("L", -1)):
        bones += [("fl1" + s, (sx * 0.15, 0.18, 0.085), (sx * 0.33, 0.13, 0.06), "body", False), ("fl2" + s, (sx * 0.33, 0.13, 0.06), (sx * 0.58, 0.02, 0.03), "fl1" + s, True),
                  ("bl1" + s, (sx * 0.12, -0.21, 0.085), (sx * 0.21, -0.29, 0.06), "body", False), ("bl2" + s, (sx * 0.21, -0.29, 0.06), (sx * 0.29, -0.39, 0.04), "bl1" + s, True)]
    limbs = tuple(b[0] for b in bones[4:])
    rig = make_rig(NAME, sk, bones, nondeform=limbs); mode = skin(body, rig, nondeform=limbs)
    parts = []
    # ---- the shell: one closed surface (carapace -> curled rim -> plastron), with grooved scute seams and raised scutes
    shell = Part("shell", 1); SC = {}
    NS = 112; rhos = [0.0] + [0.02 + 0.98 * (i / 38) ** 0.9 for i in range(39)]          # (performance: ~5k shell vertices)
    rows = []
    def add(co, sid, ds, ang, under):
        vv = shell.v(co, "body"); SC[len(shell.w) - 1] = (ds, sid + (500 if under else 0), ang); return vv
    for i, rho in enumerate(rhos):                                         # carapace
        row = []
        for k in range(NS if rho > 0 else 1):
            th = k / NS * math.tau; u, v, x, y = plan(rho, th)
            sid, ds = _scute(rho, th, u, v)
            dome = HD * (1 - rho ** 2) ** 0.55 if rho < 1 else 0.0
            keel = 0.012 * math.exp(-(u / 0.1) ** 2) * (1 - rho) if sid < 20 else 0.0
            z = ZR + dome + keel - 0.006 * math.exp(-(ds / 0.018) ** 2) + 0.006 * smooth01(ds / 0.09)
            if rho > 0.9 and v < -0.2:                                     # serrated rear marginals
                a = ((th - math.pi / 2) / math.tau) % 1.0 * 25
                f = abs(a - round(a)) * 2
                x *= 1 + 0.04 * (1 - f) * smooth01((rho - 0.9) / 0.1); y += -LH * 0.04 * (1 - f) * smooth01((rho - 0.9) / 0.1) * (-v)
            cen = (sid % 100) * 0.37
            row.append(add(U((x, y, z)), sid, ds, math.atan2(v - math.sin(cen), u - math.cos(cen)), False))
        rows.append(row)
    for t, rr, dz in ((0.0, 1.015, -0.012), (0.0, 1.0, -0.028), (0.0, 0.93, -0.045)):   # the curled-under rim
        row = []
        for k in range(NS):
            th = k / NS * math.tau; u, v, x, y = plan(rr, th)
            row.append(add(U((x, y, ZR + dz)), 140, 0.05, 0.0, True))
        rows.append(row)
    for i in range(13):                                                    # the plastron, narrower than the carapace
        rho = 0.86 * (1 - i / 12) ** 1.1
        row = []
        for k in range(NS if rho > 0.001 else 1):
            th = k / NS * math.tau; u, v, x, y = plan(rho, th)
            x *= 0.82
            bands = (-0.6, -0.3, 0.0, 0.3, 0.58)
            ds = min(abs(u) * 0.82, min(abs(v - b) for b in bands), 0.86 - rho)
            row.append(add(U((x, y, ZP + ZR * 0.15 * (1 - rho) * 0 - 0.008 * (1 - rho ** 2))), 600 + sum(1 for b in bands if v > b) * 2 + (u > 0), ds, 0.0, True))
        rows.append(row)
    for a_, b_ in zip(rows, rows[1:]):
        if len(a_) == 1:
            for k in range(NS): shell.f([a_[0], b_[k], b_[(k + 1) % NS]][::-1])
        elif len(b_) == 1:
            for k in range(NS): shell.f([a_[k], a_[(k + 1) % NS], b_[0]][::-1])
        else:
            for k in range(NS): shell.f([a_[k], a_[(k + 1) % NS], b_[(k + 1) % NS], b_[k]][::-1])
    shell_o = shell.finish()
    bm_ = bmesh.new(); bm_.from_mesh(shell_o.data); bmesh.ops.recalc_face_normals(bm_, faces=bm_.faces); bm_.to_mesh(shell_o.data); bm_.free()
    at = shell_o.data.attributes.new("sc", 'FLOAT_VECTOR', 'POINT')
    for i, (ds, sid, ang) in SC.items(): at.data[i].vector = (ds, sid, ang)
    parts.append(shell_o)
    # ---- flippers: long paddle fore-flippers, short hind paddles, each with a claw on the leading edge
    fl = Part("flippers", 0); cl = Part("claws", 2)
    for s, sx in (("R", 1), ("L", -1)):
        for b1, b2, base, mid, tip, chord, nail in (("fl1" + s, "fl2" + s, (0.14, 0.18, 0.085), (0.33, 0.13, 0.062), (0.6, 0.0, 0.03), (0.05, 0.075, 0.03), 0.35),
                                                    ("bl1" + s, "bl2" + s, (0.11, -0.2, 0.085), (0.21, -0.29, 0.062), (0.31, -0.41, 0.045), (0.045, 0.065, 0.04), 0.5)):
            B, M, T = U((sx * base[0], base[1], base[2])), U((sx * mid[0], mid[1], mid[2])), U((sx * tip[0], tip[1], tip[2]))
            pts, rad, bw, tps = [], [], [], []
            for i in range(13):
                t = i / 12; p = (B.lerp(M, t * 2) if t < 0.5 else M.lerp(T, (t - 0.5) * 2))
                c = (chord[0] + (chord[1] - chord[0]) * math.sin(math.pi * min(1, t * 1.6) / 2)) if t < 0.62 else chord[1] + (chord[2] - chord[1]) * ((t - 0.62) / 0.38) ** 1.4
                w2 = smooth01((t - 0.35) / 0.4)
                pts.append(p); rad.append(S * max(0.006, c)); bw.append([(b1, 1 - w2), (b2, w2)]); tps.append(t)
            _ring_sweep(fl, pts, rad, bw, segs=12, tips=tps, flat=0.22, up=(0, 0, 1))
            q = pts[int(12 * nail)]; d = (pts[int(12 * nail) + 1] - q).normalized()
            fwd = Vector((0, 1, 0)) if b1.startswith("f") else Vector((sx * 0.3, -1, 0))
            cl.cone(q + fwd.normalized() * rad[int(12 * nail)] * 0.8, fwd + d * 0.3, S * 0.022, S * 0.007, bw[int(12 * nail)], segs=5, bend=(0, 0, -0.3))
    parts += [fl.finish(), cl.finish()]
    # ---- head: horny hooked beak, big dark eyes, scaled with plates (texture), and a short tail
    hb = Part("beak", 2)
    hb.cone(U((0, 0.452, 0.118)), (0, 1, -0.35), S * 0.03, S * 0.024, "head", segs=8, flat=0.8, bend=(0, 0, -0.5))
    hb.cone(U((0, 0.448, 0.1)), (0, 1, 0.1), S * 0.024, S * 0.02, "head", segs=8, flat=0.6)
    parts.append(hb.finish())
    p = Part("eyes", 3)
    for sx in (1, -1): p.sphere(U((sx * 0.04, 0.418, 0.142)), S * 0.014, "head", scale=(0.8, 1.1, 0.9), sub=2)
    parts.append(p.finish())
    return body, rig, parts, {}, mode

def anim_turtle(A, info):
    X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    def limbs(P, f_up, f_sw, f_tw, b_up, b_sw, side_phase=0.0):
        for s, sx in (("R", 1), ("L", -1)):
            P["fl1" + s] = qmul(rotaxis(A, "fl1" + s, Y, -sx * f_up[s]), rotaxis(A, "fl1" + s, Z, sx * f_sw[s]))
            P["fl2" + s] = qmul(rotaxis(A, "fl2" + s, Y, -sx * f_up[s] * 0.4), rotaxis(A, "fl2" + s, X, f_tw[s]))
            P["bl1" + s] = qmul(rotaxis(A, "bl1" + s, Y, -sx * b_up[s]), rotaxis(A, "bl1" + s, Z, sx * b_sw[s]))
    def gait(cyc, sweep, lift, bob):
        def fn(t):
            w = 2 * math.pi * t * cyc; P = {}
            ph = {"R": 0.0, "L": math.pi}
            f_up = {s: lift * max(0.0, math.sin(w + ph[s])) for s in ph}; f_sw = {s: sweep * math.cos(w + ph[s]) for s in ph}
            b_up = {s: lift * 0.6 * max(0.0, math.sin(w + ph[s] + math.pi)) for s in ph}; b_sw = {s: -sweep * 0.7 * math.cos(w + ph[s] + math.pi) for s in ph}
            limbs(P, f_up, f_sw, {s: 0 for s in ph}, b_up, b_sw)
            P["body"] = rotaxis(A, "body", Z, 3 * math.sin(w)); P["neck"] = rotaxis(A, "neck", X, -4 + 3 * math.sin(2 * w)); P["tail"] = rotaxis(A, "tail", Z, 8 * math.sin(w))
            return P, (0, 0, bob * abs(math.sin(w)))
        return fn
    def swim(cyc, amp, head):
        def fn(t):
            w = 2 * math.pi * t * cyc; P = {}
            ss = {"R": 0, "L": 0}
            f_up = {s: amp * math.sin(w) for s in ss}; f_sw = {s: amp * 0.45 * math.cos(w) for s in ss}; f_tw = {s: -25 * math.cos(w) for s in ss}
            b_up = {s: 6 * math.sin(w + 1.2) for s in ss}; b_sw = {s: 10 * math.sin(w * 0.5 + (0 if s == "R" else math.pi)) for s in ss}
            limbs(P, f_up, f_sw, f_tw, b_up, b_sw)
            P["body"] = rotaxis(A, "body", X, 3 * math.sin(w - 0.6)); P["neck"] = rotaxis(A, "neck", X, head + 2 * math.sin(w)); P["head"] = rotaxis(A, "head", Z, 5 * math.sin(w * 0.5))
            return P, (0, 0, S * 0.012 * math.sin(w - 0.8))
        return fn
    def idle(t):
        w = 2 * math.pi * t; P = {}
        z0 = {"R": 0, "L": 0}
        limbs(P, {s: -4 for s in z0}, {s: 0 for s in z0}, {s: 0 for s in z0}, {s: -3 for s in z0}, {s: 0 for s in z0})
        P["neck"] = qmul(rotaxis(A, "neck", Z, 22 * math.sin(w)), rotaxis(A, "neck", X, -6 + 4 * math.sin(2 * w)))
        P["head"] = rotaxis(A, "head", X, 6 * math.sin(3 * w))
        return P, (0, 0, S * 0.003 * math.sin(2 * w))
    def alert(t):
        w = 2 * math.pi * t; P = {}
        P["neck"] = qmul(rotaxis(A, "neck", X, 18), rotaxis(A, "neck", Z, 30 * math.sin(w)))
        P["head"] = rotaxis(A, "head", X, -10 + 4 * math.sin(4 * w))
        return P, (0, 0, S * 0.01)
    return ([("idle", idle, 150, 3, False), ("walk", gait(1, 28, 22, S * 0.012), 48, 2, False), ("run", gait(1, 34, 28, S * 0.018), 30, 2, False),
             ("alert", alert, 90, 3, False), ("swim", swim(1, 42, -6), 45, 1, False), ("float", swim(1, 14, 22), 90, 2, False)],
            dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", swimAnim="swim", floatAnim="float"))

BUILD["turtle"] = (build_turtle, anim_turtle)

_prev_post_nodes = post_nodes
def post_nodes(N, c, g):
    c, g = _prev_post_nodes(N, c, g)
    if SP.get("arch") != "turtle": return c, g
    sc = N.node('ShaderNodeSeparateXYZ'); N.L(N.vattr("sc"), sc.inputs[0]); ds, sid, ang = sc.outputs[0], sc.outputs[1], sc.outputs[2]
    # carapace: olive-brown scutes, each a little different, with growth rings parallel to its edges and streaks radiating from its centre
    tone = N.noise(1.0, 2, vec=N.gray(sid))
    sh = N.mix(SP["shell1"], SP["shell2"], tone)
    rings = N.m('GREATER_THAN', N.m('SINE', N.m('MULTIPLY', ds, 160.0)), 0.55)
    sh = N.mix(sh, N.mul(sh, 0.72), N.m('MULTIPLY', rings, 0.5))
    streak = N.m('GREATER_THAN', N.m('SINE', N.m('ADD', N.m('MULTIPLY', ang, 9.0), N.m('MULTIPLY', N.noise(3.0, 3), 4.0))), 0.6)
    sh = N.mix(sh, SP["streak"], N.m('MULTIPLY', N.m('MULTIPLY', streak, N.m('GREATER_THAN', ds, 0.03)), 0.45))
    sh = N.mix(sh, (0.12, 0.1, 0.07), N.m('LESS_THAN', ds, 0.008))                                # seams
    sh = N.mul(sh, N.m('ADD', N.m('MULTIPLY', N.noise(40.0 / S, 4), 0.25), 0.88))
    under = N.m('GREATER_THAN', sid, 450.0)
    pl = N.mix(SP["plastron"], N.mul(SP["plastron"], 0.8), N.m('GREATER_THAN', N.m('SINE', N.m('MULTIPLY', ds, 120.0)), 0.7))
    pl = N.mix(pl, (0.45, 0.4, 0.3), N.m('LESS_THAN', ds, 0.008))
    sh = N.mix(sh, pl, under)
    # skin: dark scales with pale edges on top, cream underneath; plates on the head
    sc_edge = N.voronoi(90.0 / S, 'DISTANCE_TO_EDGE')
    skin = N.ramp(N.up01(), [(0.0, SP["belly"]), (0.42, SP["belly"]), (0.55, SP["col"]), (1.0, SP["back"])])
    skin = N.mix(skin, SP["scaleEdge"], N.m('MULTIPLY', N.m('MULTIPLY', N.m('LESS_THAN', sc_edge, 0.035), N.m('GREATER_THAN', N.up01(), 0.45)), 0.75))
    head = N.m('GREATER_THAN', N.Y, S * 0.36)
    plate = N.voronoi(55.0 / S, 'DISTANCE_TO_EDGE')
    skin = N.mix(skin, SP["scaleEdge"], N.m('MULTIPLY', N.m('MULTIPLY', N.m('LESS_THAN', plate, 0.045), head), N.m('MULTIPLY', N.m('GREATER_THAN', N.up01(), 0.5), 0.85)))
    c = N.mix(c, skin, N.is_part(0)); c = N.mix(c, sh, N.is_part(1))
    return c, g

# =============================================================================== NAUTILUS2; size = shell diameter
def build_nautilus2():
    turns = 2.35; b = math.log(3.0) / (2 * math.pi); TE = turns * math.tau
    def spiral(th):
        r = 0.36 * math.exp(b * (th - TE))
        return V(0, -math.sin(th) * r, math.cos(th) * r), r
    sk = Skel(S); sk.v("c", 0, 0.0, 0.0, 0.25, 0.4)
    shell = Part("shell", 1); NSH = {}
    n = 150; segs = 30
    pts, rad, tp, ths = [], [], [], []
    for i in range(n + 1):
        th = TE * (0.08 + 0.92 * i / n)
        c, r = spiral(th); pts.append(U(c)); rad.append(S * r * 0.84); tp.append(i / n); ths.append(th)
    rings = _ring_sweep(shell, pts, rad, ["body"] * len(pts), segs=segs, tips=tp, flat=0.78, up=(1, 0, 0), cap=False)
    shell.f(rings[0][::-1])
    shell.bm.verts.index_update()
    for i, ring in enumerate(rings):                                   # unwrapped coil angle and position across the whorl, per vertex
        c = pts[i]; R = rad[i]
        for v in ring:
            p = v.co; phi = math.atan2(-p.y, p.z); d = (phi - ths[i] + math.pi) % math.tau - math.pi
            NSH[v.index] = (ths[i] + d, Vector((0, p.y, p.z)).length / S, abs(p.x - c.x) / R)
    # the aperture lip: a thickened, rolled edge with a dark "black layer" band on its upper side
    end_c, end_r = spiral(TE)
    shell_o = shell.finish()
    at = shell_o.data.attributes.new("nsh", 'FLOAT_VECTOR', 'POINT')
    for i, val in NSH.items(): at.data[i].vector = val
    body = shell_o; body.name = NAME + "_body"
    ap = U(end_c); fwd = Vector((0, -math.cos(TE), -math.sin(TE)))      # direction the aperture opens (spiral tangent at the end)
    fwd = (spiral(TE + 0.01)[0] - spiral(TE)[0]).normalized()
    up = Vector((0, -math.sin(TE), math.cos(TE)))                       # away from the coil axis
    def L(v): return ap / S + fwd * v[0] + up * v[1] + Vector((v[2], 0, 0))   # local frame at the aperture: (forward, up, side)
    bones = [("body", (0, 0.0, -0.1), (0, 0.0, 0.3), None, False), ("hood", tuple(L((-0.02, 0.04, 0))), tuple(L((0.12, 0.05, 0))), "body", False)]
    for k in range(6):
        a = k / 6 * math.tau; base = L((0.06, -0.03 + math.sin(a) * 0.06, math.cos(a) * 0.07))
        bones += [("arm%d" % k, tuple(base), tuple(base + fwd * 0.15), "hood", False), ("armt%d" % k, tuple(base + fwd * 0.15), tuple(base + fwd * 0.3), "arm%d" % k, True)]
    rig = make_rig(NAME, sk, bones)
    body.parent = rig; mod = body.modifiers.new("Armature", 'ARMATURE'); mod.object = rig
    parts = []
    # ---- hood: a leathery, warty cap over the aperture
    p = Part("hood", 4)
    hc = U(L((0.0, 0.05, 0)))
    res = bmesh.ops.create_uvsphere(p.bm, u_segments=28, v_segments=16, radius=1.0)
    for vv in res["verts"]:
        co = vv.co.copy(); wart = 1 + 0.06 * max(0.0, noise.noise(co * 6.0))
        loc = fwd * co.y * 0.95 + up * co.z * 0.55 + Vector((co.x * 0.7, 0, 0))
        vv.co = hc + loc * S * end_r * 0.78 * wart
        p.w.append([("hood", 1.0)]); p.tip.append(0.0)
    # siphon (hyponome): a folded funnel under the head
    p.tube(U(L((0.02, -0.12, 0))), U(L((0.12, -0.15, 0.0))), S * 0.035, S * 0.022, "hood", rings=3, segs=10)
    # ocular tentacles above and below each eye
    for sx in (1, -1):
        for dy in (0.06, -0.05):
            p.cone(U(L((0.1, dy - 0.05, sx * 0.17))), fwd + up * dy * 2 + Vector((sx * 0.4, 0, 0)), S * 0.05, S * 0.009, "hood", segs=5)
    parts.append(p.finish())
    # ---- ~90 digital tentacles in two rings, each with a thicker sheath at its base
    p = Part("tentacles", 4)
    for k in range(92):
        ring2 = k % 2; a = random.uniform(0, math.tau); rr = (0.05 if ring2 else 0.085) + random.uniform(-0.01, 0.01)
        base = L((0.11, -0.04 + math.sin(a) * rr * 0.8, math.cos(a) * rr))
        g = int((a / math.tau) * 6) % 6
        d = (fwd + up * math.sin(a) * 0.35 + Vector((math.cos(a) * 0.35, 0, 0)) - up * 0.15).normalized()
        Lt = S * random.uniform(0.16, 0.3) * (0.8 if ring2 else 1.0)
        p.cone(U(base), d, S * 0.035, S * 0.011, [("arm%d" % g, 0.6), ("hood", 0.4)], 5)                       # sheath
        p.cone(U(base) + d * S * 0.025, d, Lt, S * 0.0065, [("arm%d" % g, 0.5), ("armt%d" % g, 0.5)], 5, bend=(0, 0, -0.25))
    parts.append(p.finish())
    # ---- big pinhole eyes on stalked bulges either side of the head
    p = Part("eyes", 3); EYE = {}
    for sx in (1, -1):
        ec = U(L((0.1, -0.05, sx * 0.2))); er = S * 0.052
        res = bmesh.ops.create_uvsphere(p.bm, u_segments=32, v_segments=20, radius=1.0)
        for vv in res["verts"]:
            co = vv.co.copy(); co.x *= 0.55                                    # a flattened disc facing sideways
            vv.co = ec + Vector((co.x * sx, co.y, co.z)) * er
            p.w.append([("hood", 1.0)]); p.tip.append(0.0)
        p.bm.verts.index_update()
        for vv in res["verts"]:
            q = (vv.co - ec) / er
            EYE[vv.index] = (q.y, q.z, max(0.0, q.x * sx / 0.55 * 1.8))       # disc coordinates: (u, v, facing out)
        # a raised socket ring around the eye
        for j in range(24):
            a0, a1 = j / 24 * math.tau, (j + 1) / 24 * math.tau
            p0 = ec + Vector((sx * er * 0.3, math.cos(a0) * er * 1.08, math.sin(a0) * er * 1.08))
            p1 = ec + Vector((sx * er * 0.3, math.cos(a1) * er * 1.08, math.sin(a1) * er * 1.08))
            p.tube(p0, p1, er * 0.13, er * 0.13, "hood", rings=1, segs=6, cap=False)
    eyes_o = p.finish()
    ea = eyes_o.data.attributes.new("eyeuv", 'FLOAT_VECTOR', 'POINT')
    for i, val in EYE.items(): ea.data[i].vector = val
    parts.append(eyes_o)
    return body, rig, parts, {}, "explicit"

def anim_nautilus2(A, info):
    def hover(cyc, amp, pulse):
        def fn(t):
            w = 2 * math.pi * t * cyc; P = {"body": rotaxis(A, "body", (1, 0, 0), 3 * math.sin(w))}
            for k in range(6):
                P["arm%d" % k] = rotaxis(A, "arm%d" % k, (1, 0, 0) if k % 2 else (0, 0, 1), amp * math.sin(w + k))
                P["armt%d" % k] = rotaxis(A, "armt%d" % k, (1, 0, 0), amp * 1.4 * math.sin(w + k - 0.8))
            P["hood"] = rotaxis(A, "hood", (1, 0, 0), pulse * math.sin(w))
            return P, (0, S * 0.03 * pulse / 10 * max(0, math.sin(w)), S * 0.01 * math.sin(w * 0.5))
        return fn
    return ([("idle", hover(1, 8, 2), 120, 3, False), ("swim", hover(2, 14, 10), 45, 1, False), ("alert", hover(3, 4, 0), 60, 2, False)],
            dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="alert", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))

BUILD["nautilus2"] = (build_nautilus2, anim_nautilus2)

_prev_post_nodes2 = post_nodes
def post_nodes(N, c, g):
    c, g = _prev_post_nodes2(N, c, g)
    if SP.get("arch") != "nautilus2": return c, g
    sep = N.node('ShaderNodeSeparateXYZ'); N.L(N.vattr("nsh"), sep.inputs[0]); phi, rad, side = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    TE = 2.35 * math.tau
    # flame stripes radiate from the coil's centre across the flanks: lines of constant coil angle, bent back toward the venter
    bend = N.m('MULTIPLY', N.m('POWER', N.m('MULTIPLY', rad, 3.0), 1.4), 0.55)
    wob = N.m('MULTIPLY', N.noise(9.0 / S, 3), 0.5)
    arg = N.m('ADD', N.m('ADD', N.m('MULTIPLY', phi, SP.get("stripeK", 22.0)), N.m('MULTIPLY', bend, 6.0)), wob)
    st = N.m('SINE', arg)
    fork = N.m('SINE', N.m('MULTIPLY', arg, 2.0))
    width = N.m('ADD', 0.25, N.m('MULTIPLY', rad, 0.9))                                         # broader toward the outer edge
    stripe = N.m('GREATER_THAN', N.m('ADD', st, N.m('MULTIPLY', N.m('GREATER_THAN', rad, 0.24), N.m('MULTIPLY', fork, 0.35))), N.m('SUBTRACT', 1.0, width))
    fade = N.m('MULTIPLY', N.m('SUBTRACT', TE - 0.35, phi), 1.1, clamp=True)                   # the newest part of the body whorl is plain
    base = N.mix(SP["col"], SP["belly"], N.m('MULTIPLY', rad, 1.5, clamp=True))
    sc = N.mix(base, SP["acc"], N.m('MULTIPLY', stripe, fade))
    sc = N.mix(sc, SP["acc2"], N.m('MULTIPLY', N.m('MULTIPLY', stripe, fade), N.m('GREATER_THAN', N.noise(5.0 / S, 3), 0.55)))
    growth = N.m('GREATER_THAN', N.m('SINE', N.m('MULTIPLY', phi, 260.0)), 0.75)                 # fine growth lines
    sc = N.mul(sc, N.m('SUBTRACT', 1.0, N.m('MULTIPLY', growth, 0.04)))
    c = N.mix(c, sc, N.is_part(1))
    # hood and tentacles: mottled cream and rust
    soft = N.mix(SP["fur"], SP["acc"], N.m('MULTIPLY', N.m('GREATER_THAN', N.noise(14.0 / S, 4), 0.55), 0.6))
    c = N.mix(c, soft, N.is_part(4))
    # the eye: a silver-grey disc with fine radial striations, a dark rim, gold flecks and a black pinhole pupil
    es = N.node('ShaderNodeSeparateXYZ'); N.L(N.vattr("eyeuv"), es.inputs[0]); eu, ev, ef = es.outputs[0], es.outputs[1], es.outputs[2]
    rr = N.m('SQRT', N.m('ADD', N.m('MULTIPLY', eu, eu), N.m('MULTIPLY', ev, ev)))
    ang = N.m('ARCTAN2', ev, eu)
    eye = N.ramp(rr, [(0.0, (0.0, 0.0, 0.0)), (0.13, (0.0, 0.0, 0.0)), (0.16, (0.55, 0.48, 0.3)), (0.24, (0.62, 0.62, 0.6)), (0.7, (0.42, 0.43, 0.44)),
                      (0.86, (0.18, 0.17, 0.17)), (1.0, (0.1, 0.09, 0.09))])
    stri = N.m('GREATER_THAN', N.m('SINE', N.m('MULTIPLY', ang, 48.0)), 0.3)
    eye = N.mix(eye, N.mul(eye, 0.7), N.m('MULTIPLY', N.m('MULTIPLY', stri, N.m('GREATER_THAN', rr, 0.18)), 0.6))
    eye = N.mix(eye, (0.85, 0.7, 0.35), N.m('MULTIPLY', N.m('LESS_THAN', N.voronoi(160.0 / S), 0.06), N.m('MULTIPLY', N.m('GREATER_THAN', rr, 0.2), N.m('LESS_THAN', rr, 0.6))))
    eye = N.mix((0.1, 0.09, 0.09), eye, N.m('GREATER_THAN', ef, 0.15))                            # the back of the eyeball is dark
    c = N.mix(c, eye, N.m('MULTIPLY', N.is_part(3), N.m('GREATER_THAN', N.m('ADD', ef, rr), 0.0)))
    return c, g
