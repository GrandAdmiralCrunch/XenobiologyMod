# Xenobiology — "mammal" archetype for fauna_build.py (exec'd from fauna_birds.py, shares its globals).
# An anatomical quadruped: each species gives its body as a table of named metaball points (torso masses, hump,
# brisket, neck, skull, muzzle, legs with joints) joined by chains, so silhouettes can be shaped bone by bone.
# Bone names match the "quad" archetype (body, spine, neck, head, tail1-3, upF/loF/ftF, upH/loH/ftH), so the quad
# walk/run/idle/alert clips and the rear / swipe / howl / swim extras all work unchanged.
# Fur is a pelt of overlapping hair cards laid along the body (part 0, so they take the body's countershading, face
# mask and socks), lightened or darkened toward the tips by `tipMul`. Regions set length, width, droop and density.
#
# Spec keys:  pts {name: (x, y, z, rs, rv)} unit coords; x > 0 on a name in LEGPTS is mirrored to L/R
#             chains [[names...]]  metaball links (leg names expand per side)
#             pelt [dict(n, len, w, box=(x0, x1, y0, y1, z0, z1), g=(gx, gy, gz), lift, jit)]
#             face=(point, radius) + headCol (face mask), sock=z + collarCol (lower legs), nose, ears ("pointy"/"round"),
#             earPos, earH, horns, hooves/paws, claws, eyeR, eyeSpread, eyeUp, eyeFwd, tipMul
from mathutils.kdtree import KDTree

LEGPTS = ("sh", "el", "wr", "tf", "hp", "kn", "hk", "th")

def build_mammal():
    pts = SP["pts"]; sk = Skel(S)
    for nm, (x, y, z, rs, rv) in pts.items():
        if nm in LEGPTS:
            sk.v(nm + "L", x, y, z, rs, rv); sk.v(nm + "R", -x, y, z, rs, rv)
        else:
            sk.v(nm, x, y, z, rs, rv)
    for ch in SP["chains"]:
        if any(c in LEGPTS for c in ch):
            for s in "LR": sk.e(*[c + s if c in LEGPTS else c for c in ch])
        else:
            sk.e(*ch)
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.0045), faces=SP.get("faces", 5000))
    bones = [("body", "pelvis", "belly", None, False), ("spine", "belly", "chest", "body", True), ("neck", "chest", "necktop", "spine", True),
             ("head", "necktop", "snout", "neck", True), ("tail1", "pelvis", "t1", "body", False), ("tail2", "t1", "t2", "tail1", True), ("tail3", "t2", "t3", "tail2", True)]
    for s in "LR":
        bones += [("upF" + s, "sh" + s, "el" + s, "spine", False), ("loF" + s, "el" + s, "wr" + s, "upF" + s, True), ("ftF" + s, "wr" + s, "tf" + s, "loF" + s, True),
                  ("upH" + s, "hp" + s, "kn" + s, "body", False), ("loH" + s, "kn" + s, "hk" + s, "upH" + s, True), ("ftH" + s, "hk" + s, "th" + s, "loH" + s, True)]
    nd = ()
    if SP.get("saddle"):        # rideable: a non-deforming "saddle" transform the rider is pinned to (MOUNT seat = saddle)
        sy, sz = SP["saddle"]; bones.append(("saddle", (0, sy, sz), (0, sy - 0.06, sz), "spine", False)); nd = ("saddle",)
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig)
    bvh = bvh_of(body); me = body.data
    # ---- per-vertex skin weights (copied onto every detail part from the nearest body vertex)
    gname = {g.index: g.name for g in body.vertex_groups}
    vw = []
    for v in me.vertices:
        ws = sorted(((gname[g.group], g.weight) for g in v.groups if g.weight > 0.02), key=lambda a: -a[1])[:3]
        tot = sum(w for _, w in ws) or 1.0
        vw.append([(n, w / tot) for n, w in ws] or [("body", 1.0)])
    kd = KDTree(len(me.vertices))
    for i, v in enumerate(me.vertices): kd.insert(v.co, i)
    kd.balance()
    def wts(co): return vw[kd.find(co)[1]]
    # ---- colour regions: face mask (hood) and lower-leg socks (collar)
    hood = me.attributes.new("hood", 'FLOAT', 'POINT'); col = me.attributes.new("collar", 'FLOAT', 'POINT')
    fp, fr = SP.get("face", ("snout", 0.0)); fc = sk.pt(fp); frS = S * fr
    sock = SP.get("sock", 0.0) * S
    for i, v in enumerate(me.vertices):
        hood.data[i].value = (1 - smooth01(((v.co - fc).length - frS * 0.6) / max(1e-6, frS * 0.5))) if fr > 0 else 0.0
        col.data[i].value = smooth01((sock - v.co.z) / max(1e-6, S * 0.03)) if sock > 0 else 0.0
    hv = [d.value for d in hood.data]; cv = [d.value for d in col.data]
    def tag(o):
        """Give a finished part the hood/collar values of the body beneath it."""
        m = o.data; h = m.attributes.new("hood", 'FLOAT', 'POINT'); c = m.attributes.new("collar", 'FLOAT', 'POINT')
        for i, v in enumerate(m.vertices):
            j = kd.find(v.co)[1]; h.data[i].value = hv[j]; c.data[i].value = cv[j]
        return o
    parts = []
    # ---- pelt: overlapping hair cards
    polys = [(p.center.copy(), p.normal.copy(), p.area, p) for p in me.polygons]
    rnd = random.Random(sum(ord(c) for c in NAME) * 7)
    pelt = Part("pelt", 7); pnrm = []; proot = []     # part 7: colour comes from the body under the root; shaded with the body normal
    furp = Part("pelt_fur", 4)                        # regions with fur = True (manes, tails) use the `fur` colour instead
    for reg in SP.get("pelt", []):
        x0, x1, y0, y1, z0, z1 = reg["box"]
        cand = [(c, n, a, p) for c, n, a, p in polys if x0 * S <= abs(c.x) <= x1 * S and y0 * S <= c.y <= y1 * S and z0 * S <= c.z <= z1 * S and (reg.get("up", -2) <= n.z)]
        if not cand: continue
        acc = []; t = 0.0
        for c in cand: t += c[2]; acc.append(t)
        g = Vector(reg.get("g", (0, -0.8, -0.6)))
        ps = SP.get("peltScale", 0.55)                 # performance: fewer, slightly wider cards (2-row, 8 vertices each)
        for k in range(int(reg["n"] * ps)):
            r = rnd.random() * t; lo, hi = 0, len(acc) - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if acc[mid] < r: lo = mid + 1
                else: hi = mid
            c, n, a, p = cand[lo]
            vs = [me.vertices[i].co for i in p.vertices]
            wb = [rnd.random() for _ in vs]; sw = sum(wb)
            base = sum((v * (w / sw) for v, w in zip(vs, wb)), Vector())
            gg = g + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * reg.get("jit", 0.25)
            if reg.get("outward"): gg = gg + Vector((math.copysign(reg["outward"], base.x), 0, 0))
            d = gg - n * gg.dot(n)
            if d.length < 1e-4: d = Vector((0, -1, 0)) - n * n.y
            d = (d.normalized() + n * reg.get("lift", 0.25)).normalized()
            side = n.cross(d).normalized()
            L = S * reg["len"] * rnd.uniform(0.7, 1.25); w = S * reg["w"] * rnd.uniform(0.8, 1.2) / max(0.4, ps) ** 0.5
            r0 = base - n * S * 0.004; mid_ = base + d * L * 0.5 + n * L * 0.06; tip = base + d * L + n * L * 0.02
            ww = wts(base)
            tgt = furp if reg.get("fur") else pelt
            if tgt is pelt: pnrm += [n] * 8; proot += [base.copy()] * 8
            tip = mid_ * 0.35 + tip * 0.65
            tgt.grid([[(r0 - side * w * 0.5, ww, 0.0), (r0 + side * w * 0.5, ww, 0.0)],
                       [(tip - side * w * 0.12, ww, 1.0), (tip + side * w * 0.12, ww, 1.0)]], thickness=S * 0.0012)
    po = tag(pelt.finish())
    cn = po.data.attributes.new("cn", 'FLOAT_VECTOR', 'POINT')
    rt = po.data.attributes.new("root", 'FLOAT_VECTOR', 'POINT')
    for i, nv in enumerate(pnrm[:len(po.data.vertices)]): cn.data[i].vector = nv; rt.data[i].vector = proot[i]
    parts += [po, tag(furp.finish())]
    hc = pts["head"]; hcU = V(0, hc[1], hc[2]); hrS = S * hc[3]
    # ---- eyes and nose
    p = Part("eyes", 3); pn = Part("nose", 2)
    eyes_on(bvh, p, hcU + V(0, SP.get("eyeFwd", 0.0), SP.get("eyeUp", 0.0)), S * SP.get("eyeR", 0.012), 2, spread=SP.get("eyeSpread", 0.3), up=0.2, fwd=0.6)
    sn = sk.pt("snout"); snr = S * pts["snout"][3]
    nose = SP.get("nose", 1.0)
    if nose:
        loc, nn = ray(bvh, sn + Vector((0, S, 0)), (0, -1, 0))
        if loc is not None: pn.sphere(loc - Vector((0, snr * 0.25, 0)), snr * 0.55 * nose, [("head", 1.0)], scale=(1.15, 0.6, 0.8), sub=2)
    parts += [p.finish(), pn.finish()]
    # ---- ears
    ears = SP.get("ears")
    if ears:
        p = Part("ears", 0)
        ex, ey, ez = SP["earPos"]; eh = S * SP.get("earH", 0.04)
        for sx in (1, -1):
            base = U((sx * ex, ey, ez))
            if ears == "pointy":
                d = Vector((sx * SP.get("earOut", 0.3), -0.15, 1.0)).normalized()
                p.cone(base, d, eh, eh * 0.45, "head", 6, flat=0.4)
            else:
                p.sphere(base, eh, "head", scale=(1.0, 0.45, 0.9), sub=2)
        parts.append(tag(p.finish()))
    # ---- horns
    if SP.get("horns"):
        p = Part("horns", 2)
        hx, hy, hz, hl, hr0 = SP["horns"]
        for sx in (1, -1):
            p.cone(U((sx * hx, hy, hz)), (sx * 1.0, 0.05, 0.25), S * hl, S * hr0, "head", 8, bend=(-sx * 0.25, 0.1, 1.1))
        parts.append(p.finish())
    # ---- feet: hooves or paws (+ claws)
    p = Part("feet", 2 if SP.get("hooves") else 0); q = Part("claws", 2)
    for s in "LR":
        for f, bn in (("tf", "ftF"), ("th", "ftH")):
            c = sk.pt(f + s); rs_ = S * pts[f][3]
            if SP.get("hooves"):
                p.sphere(c + Vector((0, rs_ * 0.15, rs_ * 0.35)), rs_ * 1.05, bn + s, scale=(1.0, 1.15, 0.75), sub=2)
                p.sphere(c + Vector((0, rs_ * 0.15, rs_ * 0.35)), rs_ * 0.4, bn + s, scale=(0.15, 1.6, 1.2), sub=1)   # cleft
            else:
                p.sphere(c + Vector((0, rs_ * 0.35, rs_ * 0.35)), rs_ * 1.05, bn + s, scale=(1.0, 1.3, 0.55), sub=2)
                for k in range(4):
                    a = (k / 3 - 0.5) * 1.1; tb = c + Vector((math.sin(a) * rs_ * 0.75, rs_ * (1.15 + 0.15 * math.cos(a)), rs_ * 0.3))
                    p.sphere(tb, rs_ * 0.32, bn + s, scale=(1, 1.1, 0.8), sub=1)
                    if SP.get("claws"): q.cone(tb + Vector((0, rs_ * 0.2, 0)), (math.sin(a) * 0.2, 1, -0.55), S * SP["claws"], rs_ * 0.11, bn + s, 5, bend=(0, 0, -0.6))
    parts.append(tag(p.finish()) if not SP.get("hooves") else p.finish())
    if SP.get("claws"): parts.append(q.finish())
    info = dict(Lg=pts["pelvis"][2] * S, zb=pts["pelvis"][2])
    return body, rig, parts, info, mode

BUILD["mammal"] = (build_mammal, anim_quad_ext)
exec(open(os.path.join(TOOLS, "fauna_kerbin2.py"), encoding="utf-8").read(), globals())

def post_join(body):
    """Pelt cards borrow the body's surface normal (attribute "cn") as custom normals so the fur shades like a coat."""
    me = body.data
    if "cn" not in me.attributes: return
    cn = me.attributes["cn"]
    nr = [Vector(cn.data[i].vector) if Vector(cn.data[i].vector).length > 0.5 else v.normal.copy() for i, v in enumerate(me.vertices)]
    me.normals_split_custom_set_from_vertices([n.normalized() for n in nr])
    me.attributes.remove(me.attributes["cn"])

def post_uv(body):
    """Hair cards (part 7) sample the body texture at their root: every card loop gets the UV of the nearest body vertex."""
    me = body.data
    if "root" not in me.attributes or not me.uv_layers: return
    uv = me.uv_layers.active.data; pa = me.attributes["part"].data; rt = me.attributes["root"].data
    vuv = {}
    for f in me.polygons:
        if pa[f.index].value == 7: continue
        for li in f.loop_indices:
            vi = me.loops[li].vertex_index
            if vi not in vuv: vuv[vi] = uv[li].uv.copy()
    kd = KDTree(len(vuv))
    for vi in vuv: kd.insert(me.vertices[vi].co, vi)
    kd.balance()
    for f in me.polygons:
        if pa[f.index].value != 7: continue
        for li in f.loop_indices:
            vi = me.loops[li].vertex_index
            uv[li].uv = vuv[kd.find(Vector(rt[vi].vector))[1]]
    me.attributes.remove(me.attributes["root"])
