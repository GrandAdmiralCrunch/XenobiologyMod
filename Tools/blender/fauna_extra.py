# Xenobiology — extra archetypes and species features for fauna_build.py (exec'd from it, shares its globals).
# New archetypes: "ceph" (squids, krakens, capwright) and "sessile" (form = puffball | coral | mat).
# Feature hooks (quad_feats, fish_feats, ...) are called from the matching builders with locals().

def rotaxis(A, b, axis, deg):
    """Rotation of bone b about a world-space axis (taken at the rest pose), in degrees."""
    if not deg: return Quaternion()
    m = A.arm.bones[b].matrix_local.to_3x3().inverted()
    return Quaternion((m @ Vector(axis)).normalized(), math.radians(deg))

def qmul(*qs):
    q = Quaternion()
    for x in qs: q = q @ x
    return q

# =============================================================================== CEPHALOPOD
# Head at the origin, arms forward (+Y), mantle trailing behind (-Y). Units of total length.
def build_ceph():
    ML = SP.get("mantleL", 0.5); MR = SP.get("mantleR", 0.09); HR = SP.get("headR", 0.075)
    na = SP.get("arms", 8); AL = SP.get("armL", 0.38); AR = SP.get("armR", 0.022); TLn = SP.get("tentL", 0.7)
    z0 = SP.get("z0", 0.0)
    sk = Skel(S)
    sk.v("head", 0, 0.0, z0, HR, HR * 0.9)
    sk.v("neck", 0, -0.06, z0, MR * 0.8, MR * 0.75)
    sk.v("m1", 0, -0.06 - ML * 0.3, z0 + MR * 0.1, MR, MR * 0.95)
    sk.v("m2", 0, -0.06 - ML * 0.65, z0 + MR * 0.15, MR * 0.8, MR * 0.75)
    sk.v("m3", 0, -0.06 - ML, z0 + MR * 0.1, MR * 0.2, MR * 0.2)
    sk.v("armring", 0, 0.07, z0, HR * 0.75, HR * 0.7)
    sk.e("armring", "head", "neck", "m1", "m2", "m3")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.005), faces=SP.get("faces", 4500), floor=False)
    bones = [("body", (0, -0.06, z0), (0, 0.0, z0), None, False), ("head", (0, 0.0, z0), (0, 0.07, z0), "body", True),
             ("mantle", (0, -0.06, z0), (0, -0.06 - ML * 0.55, z0 + MR * 0.12), "body", False),
             ("mantle2", (0, -0.06 - ML * 0.55, z0 + MR * 0.12), (0, -0.06 - ML, z0 + MR * 0.1), "mantle", True)]
    for s, sx in (("L", 1), ("R", -1)):
        bones.append(("fin" + s, (sx * MR * 0.5, -0.06 - ML * 0.75, z0 + MR * 0.1), (sx * MR * 2.2, -0.06 - ML * 0.8, z0 + MR * 0.1), "mantle2", False))
    arms = []
    for i in range(na + (2 if TLn > 0 else 0)):
        tent = i >= na
        if tent: a = math.pi * (0.5 + (0.22 if i == na else -0.22))     # two long hunting tentacles, lower middle
        else: a = (i + 0.5) / na * math.tau
        rad = Vector((math.cos(a), 0, math.sin(a)))
        if SP.get("splay") and not tent: rad = Vector((math.cos(a), math.sin(a) * 0.9 + 0.25, 0)).normalized()   # flat star on the seabed
        L = TLn if tent else AL * (1.0 - 0.15 * abs(math.sin(a)) if SP.get("unequal") else 1.0)
        base = Vector((0, 0.08, z0)) + rad * HR * 0.55
        dirv = (Vector((0, 1, 0)) + rad * SP.get("armSpread", 0.18)).normalized()
        if SP.get("splay") and not tent: dirv = rad                              # kraken: arms laid out like a star
        pts = [base + dirv * L * k / 4 + (Vector((0, 0, -1)) * L * 0.05 * (k / 4) ** 2 if SP.get("splay") else Vector()) for k in range(5)]
        for k in range(4):
            bones.append(("a%d_%d" % (i, k), tuple(pts[k]), tuple(pts[k + 1]), "head" if k == 0 else "a%d_%d" % (i, k - 1), k > 0))
        arms.append((pts, tent, rad, a))
    rig = make_rig(NAME, sk, bones)
    for b in rig.data.bones:
        if b.name.startswith("a"): b.use_deform = False
    mode = skin(body, rig)
    for b in rig.data.bones: b.use_deform = True
    bvh = bvh_of(body); parts = []
    # eyes: large, on the sides of the head
    p = Part("eyes", 3)
    for sx in (1, -1):
        d = Vector((sx, 0.15, 0.25)).normalized()
        loc, n = ray(bvh, U((0, 0.0, z0)) + d * S, -d)
        if loc: p.sphere(loc - n * S * HR * 0.15, S * HR * SP.get("eyeR", 0.45), "head", sub=2)
    parts.append(p.finish())
    # arms: tapering tubes with explicit chain weights; suckers on the inner face
    p = Part("arms", 0); ps = Part("suckers", 2)
    for i, (pts, tent, rad, a) in enumerate(arms):
        NR = 16; prev = None
        for kk in range(NR + 1):
            t = kk / NR; seg_ = min(3, int(t * 4)); f = t * 4 - seg_
            c = pts[seg_].lerp(pts[min(4, seg_ + 1)], f) * S
            thick = AR * (1 - 0.8 * t)
            if tent: thick = AR * 0.55 * (1 - 0.5 * t) * (1.0 + 1.6 * max(0, t - 0.78) / 0.22 * (1 - max(0, t - 0.95) / 0.05))   # club
            rr = S * thick
            d = (pts[min(4, seg_ + 1)] - pts[seg_]).normalized()
            q = d.to_track_quat('Z', 'Y').to_matrix()
            w = [("a%d_%d" % (i, seg_), 1.0 - 0.5 * max(0, f - 0.5)), ("a%d_%d" % (i, min(3, seg_ + 1)), 0.5 * max(0, f - 0.5))] if seg_ < 3 else [("a%d_3" % i, 1.0)]
            if kk == 0: w = [("head", 1.0)]
            cur = [p.v(c + q @ Vector((math.cos(j / 6 * math.tau) * rr, math.sin(j / 6 * math.tau) * rr, 0)), w, t) for j in range(6)]
            if prev:
                for j in range(6): p.f([prev[j], prev[(j + 1) % 6], cur[(j + 1) % 6], cur[j]])
            else: p.f(cur[::-1])
            prev = cur
            if kk % 2 == 1 and (not tent or t > 0.78) and kk < NR:
                ps.sphere(c - rad * rr * 0.75, rr * 0.35, w, scale=(1, 1, 1), sub=1, tip=t)
        p.f(prev)
    parts += [p.finish(), ps.finish()]
    # fins
    p = Part("fins", 5)
    for s, sx in (("L", 1), ("R", -1)):
        rows = []
        for j in range(3):
            row = []
            for k in range(6):
                yy = -0.06 - ML * (0.55 + 0.45 * k / 5)
                halfw = MR * (0.6 + SP.get("finW", 1.6) * math.sin(math.pi * (k + 0.5) / 6)) * (j / 2)
                row.append((U((sx * (MR * 0.55 + halfw), yy, z0 + MR * 0.12)), [("fin" + s, j / 2), ("mantle2", 1 - j / 2)], j / 2))
            rows.append(row)
        p.grid(rows, flip=sx < 0, thickness=S * 0.002)
    parts.append(p.finish())
    if "photophores" in FE:       # rows of light organs along the arms and mantle
        p = Part("lights", 6)
        for i, (pts, tent, rad, a) in enumerate(arms):
            for k in range(1, 4):
                c = pts[k] * S + Vector((0, 0, 1)) * S * AR * 0.9
                p.sphere(c, S * AR * 0.35, "a%d_%d" % (i, k - 1), sub=1)
        for k in range(10):
            yy = -0.1 - ML * 0.85 * k / 9
            for sx in (1, -1):
                d = Vector((sx * 0.6, 0, 1)).normalized()
                loc, n = ray(bvh, U((0, yy, z0)) + d * S, -d)
                if loc: p.sphere(loc, S * MR * 0.09, "mantle" if k < 6 else "mantle2", sub=1)
        parts.append(p.finish())
    if "cap" in FE:               # capwright: a self-built cap of coral chips, shells and stones
        p = Part("cap", 1); p2 = Part("capbits", 2)
        loc, n = ray(bvh, U((0, -0.06 - ML * 0.4, z0 + 1)), (0, 0, -1))
        top = loc if loc else U((0, -0.25, z0 + MR))
        p.sphere(top + Vector((0, 0, S * MR * 0.15)), S * MR * 1.35, [("mantle", 0.6), ("body", 0.4)], scale=(1.0, 1.25, 0.55), sub=3, jitter=0.25)
        for k in range(26):
            d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.2, 1))).normalized()
            c = top + Vector((0, 0, S * MR * 0.15)) + Vector((d.x * S * MR * 1.3, d.y * S * MR * 1.6, d.z * S * MR * 0.75))
            if k % 3 == 0: p2.cone(c, d, S * MR * random.uniform(0.4, 0.8), S * MR * 0.12, "mantle", 5)
            else: p2.sphere(c, S * MR * random.uniform(0.15, 0.3), "mantle", sub=1, jitter=0.4, tip=random.random())
        parts += [p.finish(), p2.finish()]
    return body, rig, parts, dict(na=na, arms=arms), mode

def anim_ceph(A, info):
    arms = info["arms"]; splay = SP.get("splay", False)
    def armpose(P, t, spread, curl, wave, close=0.0, speed=1.0):
        for i, (pts, tent, rad, a) in enumerate(arms):
            tang = Vector((0, 1, 0)).cross(rad).normalized()       # rotating about this swings the arm outward
            if splay and not tent: tang = rad.cross(Vector((0, 0, 1))).normalized()   # splayed arms: "outward" = lift off the floor
            ph = 2 * math.pi * (t * speed) + i * 1.3
            for k in range(4):
                b = "a%d_%d" % (i, k)
                out = (spread - close * 25) if k == 0 else 0.0
                c = curl * (k / 3) + wave * math.sin(ph - k * 0.9)
                P[b] = qmul(rotaxis(A, b, tang, out + c), rotaxis(A, b, rad.cross(tang), wave * 0.5 * math.cos(ph - k)))
    def idle(t):
        P = {}; br = math.sin(2 * math.pi * t)
        armpose(P, t, 6 if not splay else 2, 6 if not splay else -4, 5)
        P["mantle"] = (A.rot("mantle", up=2 * br), 1.0 + 0.03 * br)
        for s in "LR": P["fin" + s] = A.rot("fin" + s, up=12 * math.sin(2 * math.pi * t * 2 + (0 if s == "L" else 0.3)))
        return P, (0, 0, 0.004 * S * br)
    def swim(t):
        P = {}; w = math.sin(2 * math.pi * t)
        armpose(P, t, -4, 2, 6, speed=1)
        P["mantle"] = (A.rot("mantle", up=3 * w), 1.0 + 0.05 * w)
        P["mantle2"] = A.rot("mantle2", up=-4 * w)
        for s in "LR": P["fin" + s] = A.rot("fin" + s, up=28 * math.sin(2 * math.pi * t * 2))
        return P, (0, 0, 0)
    def jet(t):
        P = {}; pump = max(0.0, math.sin(2 * math.pi * t)) ** 2
        armpose(P, t, -10 + 14 * pump, 0, 3, close=1.0 - pump)
        P["mantle"] = (A.rot("mantle", up=0), 1.0 + 0.12 * pump - 0.06)
        for s in "LR": P["fin" + s] = A.rot("fin" + s, up=-20)
        return P, (0, 0, 0)
    def attack(t):
        P = {}
        open_ = seg(t, 0.0, 0.35) * (1 - seg(t, 0.42, 0.55)); strike = seg(t, 0.4, 0.55) * (1 - seg(t, 0.75, 1.0))
        armpose(P, t, 45 * open_ - 15 * strike, -25 * strike, 4)
        for i, (pts, tent, rad, a) in enumerate(arms):
            if tent:
                for k in range(4):
                    b = "a%d_%d" % (i, k)
                    P[b] = A.rot(b, up=20 * open_ - 10 * strike)
        P["body"] = A.rot("body", up=-10 * strike + 6 * open_)
        return P, (0, 0, 0)
    def alert(t):
        P = {}; fl = math.sin(2 * math.pi * t * 3)
        armpose(P, t, 30 + 5 * fl, -10, 8, speed=2)
        P["body"] = A.rot("body", up=8)
        for s in "LR": P["fin" + s] = A.rot("fin" + s, up=15 * fl)
        return P, (0, 0, 0)
    sp_ = SP["speed"]
    clips = [("idle", idle, 120, 3, False), ("swim", swim, 60, 2, False), ("jet", jet, 30, 1, False), ("attack", attack, 45, 1, True), ("alert", alert, 60, 2, False)]
    return clips, dict(idleAnim="idle", moveAnim="swim", fleeAnim="jet", alertAnim="alert", attackAnim="attack", moveAnimSpeed=sp_, fleeAnimSpeed=SP["fleeSpeed"])

# =============================================================================== SESSILE
def build_sessile():
    form = SP["form"]
    if form == "puffball": return build_puffball()
    if form == "coral": return build_coral()
    return build_mat()

def build_puffball():
    # one big puffball (size = height) with a few small ones at its foot; ball on bone "ball"
    sk = Skel(S)
    sk.v("foot", 0, 0, 0.05, 0.22, 0.08); sk.v("ball", 0, 0, 0.42, 0.42, 0.38); sk.v("top", 0, 0, 0.72, 0.18, 0.12)
    sk.e("foot", "ball", "top")
    body = metaball_body(NAME, sk, voxel=S * 0.012, faces=2600, floor=True)
    def wrinkly(co, n):
        co += n * S * (0.012 * noise.noise(co / S * 9.0) + 0.006 * noise.noise(co / S * 25.0))
        return co
    displace(body, wrinkly)
    bones = [("body", (0, 0, 0), (0, 0, 0.2), None, False), ("ball", (0, 0, 0.2), (0, 0, 0.8), "body", True)]
    rig = make_rig(NAME, sk, bones); mode = skin(body, rig); parts = []
    p = Part("pore", 3)                                    # the dark spore pore on top
    p.sphere(U((0, 0, 0.78)), S * 0.06, "ball", scale=(1, 1, 0.35), sub=2)
    parts.append(p.finish())
    p = Part("small", 0)
    for k in range(5):
        a = k / 5 * math.tau + 0.4; r = random.uniform(0.38, 0.55)
        c = U((math.cos(a) * r, math.sin(a) * r, 0.1)); rr = S * random.uniform(0.07, 0.14)
        p.sphere(c + Vector((0, 0, rr * 0.6)), rr, "body", scale=(1, 1, 0.85), sub=2, jitter=0.15)
    parts.append(p.finish())
    p = Part("scales", 1)                                  # papery flakes on the skin
    bvh = bvh_of(body)
    for k in range(60):
        d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.1, 1))).normalized()
        loc, n = ray(bvh, U((0, 0, 0.42)) + d * S, -d)
        if loc is None or loc.z < S * 0.15: continue
        p.sphere(loc, S * random.uniform(0.02, 0.04), "ball", scale=(1.0, 1.0, 0.3), sub=1, jitter=0.5)
    parts.append(p.finish())
    return body, rig, parts, dict(form="puffball"), mode

def build_coral():
    # branching chalk coral: a recursive tree of tubes, glowing feeding tips; height bands bend with the current
    nb = 4
    bones = [("body", (0, 0, 0), (0, 0, 0.18), None, False)]
    for k in range(1, nb):
        bones.append(("b%d" % k, (0, 0, 0.18 + 0.24 * (k - 1)), (0, 0, 0.18 + 0.24 * k), "body" if k == 1 else "b%d" % (k - 1), True))
    def band(z):
        k = int(max(0, z / S - 0.18) / 0.24) + 1
        return "body" if z < S * 0.18 else "b%d" % min(nb - 1, k)
    sk = Skel(S); sk.v("a", 0, 0, 0.0, 0.1, 0.05); sk.v("b", 0, 0, 0.05, 0.08, 0.04); sk.e("a", "b")
    body = metaball_body(NAME, sk, voxel=S * 0.01, faces=600, floor=True)      # chalky foot
    rig = make_rig(NAME, sk, bones); mode = skin(body, rig); parts = []
    p = Part("branches", 0); tips = Part("tips", 6)
    def branch(a, d, L, r, depth):
        b = a + d * L
        p.tube(a, b, r, r * 0.78, band((a.z + b.z) * 0.5), rings=2, segs=7)
        p.sphere(b, r * 0.8, band(b.z), sub=1, jitter=0.2)
        if depth == 0 or r < S * 0.01:
            tips.sphere(b + d * r * 0.6, r * 0.75, band(b.z), sub=1, tip=1.0); return
        for k in range(random.choice((2, 2, 3))):
            nd = (d + Vector((random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8), random.uniform(0.0, 0.6)))).normalized()
            if nd.z < 0.15: nd.z = 0.15; nd.normalize()
            branch(b, nd, L * random.uniform(0.6, 0.8), r * 0.72, depth - 1)
    for k in range(3):
        d0 = Vector((random.uniform(-0.35, 0.35), random.uniform(-0.35, 0.35), 1)).normalized()
        branch(U((random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), 0.03)), d0, S * 0.3, S * 0.07, SP.get("depth", 4))
    parts += [p.finish(), tips.finish()]
    return body, rig, parts, dict(form="coral", nb=nb), mode

def build_mat():
    # floating fungal raft: lumpy disc (size = diameter), frilled rim, filaments hanging below
    nr = SP.get("rims", 12)
    sk = Skel(S)
    for i in range(nr):
        a = i / nr * math.tau; r = 0.36 * (1 + 0.18 * math.sin(3 * a + 1) + 0.1 * math.sin(7 * a))
        sk.v("r%d" % i, r * math.cos(a), r * math.sin(a), 0.0, 0.16, 0.022)
        sk.e("r%d" % i, "r%d" % ((i + 1) % nr))
    sk.v("c", 0, 0, 0.005, 0.3, 0.03)
    for i in range(nr): sk.e("c", "r%d" % i)
    body = metaball_body(NAME, sk, voxel=S * 0.006, faces=SP.get("faces", 6000), floor=False, mb_scale=1.15)
    def lumps(co, n):
        co += n * S * (0.012 * noise.noise(co / S * 7.0) + 0.006 * noise.noise(co / S * 22.0))
        return co
    displace(body, lumps)
    bones = [("body", (0, 0, 0), (0, 0.08, 0), None, False)]
    for i in range(nr):
        a = i / nr * math.tau
        bones.append(("rim%d" % i, (0.08 * math.cos(a), 0.08 * math.sin(a), 0), (0.46 * math.cos(a), 0.46 * math.sin(a), 0), "body", False))
    rig = make_rig(NAME, sk, bones); mode = skin(body, rig); bvh = bvh_of(body); parts = []
    p = Part("knobs", 1)                                  # fruiting knobs and ridges on top
    for k in range(70):
        a = random.uniform(0, math.tau); r = random.uniform(0, 0.38)
        loc, n = ray(bvh, U((r * math.cos(a), r * math.sin(a), 1)), (0, 0, -1))
        if loc is None: continue
        ai = int(round(a / math.tau * nr)) % nr
        p.sphere(loc, S * random.uniform(0.006, 0.016), [("rim%d" % ai, min(1, r / 0.3)), ("body", max(0, 1 - r / 0.3))], scale=(1, 1, 0.6), sub=1, jitter=0.3)
    parts.append(p.finish())
    p = Part("filaments", 5)                              # feeding filaments hanging into the water
    for k in range(SP.get("filaments", 90)):
        a = random.uniform(0, math.tau); r = random.uniform(0.02, 0.36)
        loc, n = ray(bvh, U((r * math.cos(a), r * math.sin(a), -1)), (0, 0, 1))
        if loc is None: continue
        ai = int(round(a / math.tau * nr)) % nr
        p.cone(loc, (random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), -1), S * random.uniform(0.03, 0.08), S * 0.004,
               [("rim%d" % ai, min(1, r / 0.3)), ("body", max(0, 1 - r / 0.3))], 4)
    parts.append(p.finish())
    return body, rig, parts, dict(form="mat", nr=nr), mode

def anim_sessile(A, info):
    form = info["form"]
    if form == "puffball":
        def idle(t):
            br = math.sin(2 * math.pi * t)
            return {"ball": (A.rot("ball", yaw=1.5 * br), 1.0 + 0.015 * br)}, (0, 0, 0)
        def alert(t):
            return {"ball": (A.rot("ball", yaw=2 * math.sin(2 * math.pi * t * 3)), 0.97)}, (0, 0, 0)
        def burst(t):
            swell = seg(t, 0.0, 0.25); pop = seg(t, 0.25, 0.45)
            sc = (1.0 + 0.25 * swell) * (1 - pop) + pop * 0.3
            return {"ball": (A.rot("ball", up=0), (1.0 + 0.25 * swell * (1 - pop) + 0.6 * pop * (1 - pop), 1.0 + 0.25 * swell * (1 - pop) + 0.6 * pop * (1 - pop), sc))}, (0, 0, 0)
        return ([("idle", idle, 120, 4, False), ("alert", alert, 30, 2, False), ("burst", burst, 24, 1, True)],
                dict(idleAnim="idle", moveAnim="idle", fleeAnim="idle", alertAnim="alert", burstAnim="burst"))
    if form == "coral":
        nb = info["nb"]
        def sway(amp):
            def fn(t):
                P = {}
                for k in range(1, nb):
                    P["b%d" % k] = A.rot("b%d" % k, fwd=amp * math.sin(2 * math.pi * t - k * 0.6), yaw=amp * 0.5 * math.cos(2 * math.pi * t - k * 0.4))
                return P, (0, 0, 0)
            return fn
        return ([("idle", sway(3.0), 150, 5, False), ("alert", sway(0.5), 60, 3, False)],
                dict(idleAnim="idle", moveAnim="idle", fleeAnim="idle", alertAnim="alert"))
    nr = info["nr"]
    def swell(amp, cycles):
        def fn(t):
            P = {}
            for i in range(nr):
                P["rim%d" % i] = A.rot("rim%d" % i, up=amp * math.sin(2 * math.pi * (t * cycles) - i / nr * math.tau * 2))
            return P, (0, 0, 0)
        return fn
    return ([("idle", swell(2.5, 1), 240, 6, False), ("alert", swell(1.0, 1), 120, 6, False)],
            dict(idleAnim="idle", moveAnim="idle", fleeAnim="idle", alertAnim="alert"))

BUILD["ceph"] = (build_ceph, anim_ceph)
BUILD["sessile"] = (build_sessile, anim_sessile)

# =============================================================================== feature hooks for the classic archetypes
def quad_feats(L):
    sk, bvh, hc, hcw, hr, zb, W, B, legH, Rv = L["sk"], L["bvh"], L["hc"], L["hcw"], L["hr"], L["zb"], L["W"], L["B"], L["legH"], L["Rv"]
    parts = []
    if "turtleshell" in FE:      # high domed shell, crusted with chalk; rim plates
        p = Part("carapace", 1)
        p.sphere(U((0, -0.02, zb + Rv * 0.45)), S * W * 0.62, [("body", 0.5), ("spine", 0.5)], scale=(1.0, 1.35, 0.62), sub=3, jitter=0.05)
        for i in range(14):
            a = i / 14 * math.tau
            p.sphere(U((math.cos(a) * W * 0.6, -0.02 + math.sin(a) * W * 0.8, zb)), S * W * 0.1, "body" if math.sin(a) < 0 else "spine", scale=(1.2, 1.2, 0.4), sub=1)
        parts.append(p.finish())
        p = Part("crust", 2)
        for k in range(24):
            d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.4, 1))).normalized()
            c = U((0, -0.02, zb + Rv * 0.45)) + Vector((d.x * S * W * 0.6, d.y * S * W * 0.82, d.z * S * W * 0.38))
            p.sphere(c, S * random.uniform(0.01, 0.025), "body", sub=1, jitter=0.5, tip=random.random())
        parts.append(p.finish())
    if "beak" in FE:
        p = Part("beak", 2)
        p.cone(hcw + U((0, hr * SP.get("snoutL", 1.0) * 0.9, -hr * 0.3)), (0, 1, -0.4), S * hr * 0.6, S * hr * 0.35, "head", 6, bend=(0, 0, -0.5))
        parts.append(p.finish())
    if "flippers" in FE:         # broad paddles over the feet
        p = Part("flippers", 0)
        for s, sx in (("L", 1), ("R", -1)):
            for f, bn, ln in (("tf", "ftF", 1.6), ("th", "ftH", 1.0)):
                c = sk.pt(f + s)
                p.sphere(c + Vector((sx * S * 0.03, S * 0.02, S * 0.01)), S * W * 0.16 * ln, bn + s, scale=(1.0, 1.4, 0.18), sub=2)
        parts.append(p.finish())
    if "tailfin" in FE:          # shorestega: fin membrane along the tail
        p = Part("tailfin", 5)
        for side in (1, -1):
            rows = []
            for j in range(2):
                row = []
                for k, (a_, b_) in enumerate((("pelvis", "t1"), ("t1", "t2"), ("t2", "t3"))):
                    for q in ((0.0, 0.5) if k < 2 else (0.0, 0.5, 1.0)):
                        c = sk.pt(a_).lerp(sk.pt(b_), q)
                        bn = ("tail1", "tail2", "tail3")[k]
                        h = S * SP.get("tailR", 0.06) * (1.6 if side > 0 else 1.0) * (0.3 + 0.7 * k / 2) * j
                        row.append((c + Vector((0, 0, side * (S * SP.get("tailR", 0.06) * 0.8 + h))), bn, j))
                rows.append(row)
            p.grid(rows, flip=side < 0, thickness=S * 0.002)
        parts.append(p.finish())
    if "proboscis" in FE:        # tidestilt: long drooping sieve-trunk
        p = Part("proboscis", 0)
        a = sk.pt("snout"); prev = a
        for k in range(1, 6):
            nxt = a + U((0, hr * 0.5 * k, -SP.get("probL", 0.25) * k / 5 - 0.02 * k * k / 25))
            p.tube(prev, nxt, S * hr * 0.22 * (1 - 0.1 * k), S * hr * 0.22 * (1 - 0.1 * (k + 1)), "head", rings=1, segs=7)
            prev = nxt
        parts.append(p.finish())
    if "stiltknees" in FE:       # knobbly joints on the stilt legs
        p = Part("knees", 2)
        for s in "LR":
            for nm, bn in (("el", "loF"), ("kn", "loH")):
                p.sphere(sk.pt(nm + s), S * SP.get("legR", 0.02) * 1.6, bn + s, sub=1)
        parts.append(p.finish())
    if "fringe" in FE:           # wavesprinter: fringed toes
        p = Part("fringe", 5)
        for s in "LR":
            for f, bn in (("tf", "ftF"), ("th", "ftH")):
                c = sk.pt(f + s)
                for k in range(5):
                    ang = (k / 4 - 0.5) * 2.2
                    p.cone(c + Vector((0, 0, S * 0.004)), (math.sin(ang), math.cos(ang), 0), S * 0.05, S * 0.006, bn + s, 3, flat=0.2)
        parts.append(p.finish())
    return parts

def fish_feats(L):
    bvh = L["bvh"]; W, H, hr = SP["W"], SP["H"], SP["headR"]
    parts = []
    if "cheeks" in FE:           # leviathan: huge translucent filter pouches along the jaw
        p = Part("cheeks", 6)
        for sx in (1, -1):
            p.sphere(U((sx * W * 0.38, 0.3, -H * 0.38)), S * H * 0.55, [("head", 0.6), ("body", 0.4)], scale=(0.65, 1.5, 0.85), sub=3)
        parts.append(p.finish())
        p = Part("combs", 2)     # filter combs showing at the mouth
        for k in range(18):
            x = (k / 17 - 0.5) * W * 0.8
            p.cone(U((x, 0.45, -H * 0.08)), (0, 0.2, -1), S * H * 0.28, S * 0.004, "head", 3, flat=0.3)
        parts.append(p.finish())
        p = Part("grooves", 1)   # throat grooves
        for k in range(7):
            x = (k / 6 - 0.5) * W * 0.7
            p.tube(U((x, 0.42, -H * 0.62)), U((x, 0.05, -H * 0.72)), S * 0.006, S * 0.006, "body", rings=2, segs=4)
        parts.append(p.finish())
    if "longsnout" in FE:        # shasta: teeth along the rostrum
        p = Part("teeth", 2); snL = SP.get("snoutLen", 0.3)
        for k in range(16):
            y = 0.47 + snL * (k / 16) * 0.95
            for sx in (1, -1):
                p.cone(U((sx * W * 0.08 * (1 - k / 20), y, -H * 0.05)), (sx * 0.3, 0.15, -1), S * 0.012, S * 0.003, "beak" if y > 0.5 else "head", 3)
        parts.append(p.finish())
    if "maw" in FE:              # voidmaw: a gaping mouth ringed with glassy fangs, and photophores
        p = Part("mouth", 3)
        p.sphere(U((0, 0.44, -H * 0.05)), S * H * 0.62, "head", scale=(0.9, 0.35, 1.0), sub=2)
        parts.append(p.finish())
        p = Part("fangs", 2)
        for k in range(14):
            a = k / 14 * math.tau
            c = U((math.cos(a) * W * 0.32, 0.47, -H * 0.05 + math.sin(a) * H * 0.48))
            p.cone(c, (-math.cos(a) * 0.4, 0.6, -math.sin(a) * 0.9), S * random.uniform(0.05, 0.11), S * 0.006, "head", 4)
        parts.append(p.finish())
        p = Part("photophores", 6)
        for k in range(12):
            y = 0.25 - 0.5 * k / 11
            for sx in (1, -1):
                d = Vector((sx, 0, -0.4)).normalized()
                loc, n = ray(bvh, U((0, y, 0)) + d * S, -d)
                if loc: p.sphere(loc, S * 0.012, "body" if y > 0.08 else ("tail1" if y > -0.18 else "tail2"), sub=1)
        parts.append(p.finish())
    if "pennant" in FE:          # nebcrest: tall dorsal with a long trailing streamer
        p = Part("pennant", 5); rows = []
        for j in range(2):
            row = []
            for k in range(8):
                t = k / 7
                row.append((U((0, 0.12 - 0.55 * t, H * (0.9 + 1.3 * t * (1 - t) * 2 + 0.8 * t) + 0.012 * j)), [("body", 1 - t), ("tail1", t)], t))
            rows.append(row)
        p.grid(rows, thickness=S * 0.002)
        parts.append(p.finish())
        p = Part("tube", 0)
        p.tube(U((0, 0.46, 0)), U((0, 0.56, -H * 0.05)), S * H * 0.08, S * H * 0.06, "head", rings=2, segs=6)
        parts.append(p.finish())
    if "screw" in FE:            # screwtail: a helical rotor round the tail tip (bone "fin" spins)
        p = Part("rotor", 5)
        for blade in range(SP.get("blades", 3)):
            rows = []
            for j in range(3):
                row = []
                for k in range(10):
                    t = k / 9; ang = blade / SP.get("blades", 3) * math.tau + t * math.pi * 1.2
                    r = S * H * (0.15 + 1.1 * j / 2 * math.sin(math.pi * (0.15 + 0.7 * t)))
                    row.append((U((0, -0.34 - 0.16 * t, 0)) + Vector((math.cos(ang) * r, 0, math.sin(ang) * r)), "fin", j / 2))
                rows.append(row)
            p.grid(rows, thickness=S * 0.002)
        p.sphere(U((0, -0.345, 0)), S * H * 0.22, "tail2", scale=(1, 0.6, 1), sub=2)   # the ring joint
        parts.append(p.finish())
    if "fluke" in FE:            # horizontal tail flukes (cetacean-style)
        p = Part("fluke", 5); rows = []
        for j in range(3):
            row = []
            for k in range(7):
                v = k / 6 - 0.5; fork = 0.5 + 0.6 * abs(v) * 2
                row.append((U((v * H * 3.2 * (0.35 + 0.65 * j / 2), -0.33 - 0.15 * fork * j / 2, 0)), [("fin", 0.4 + 0.6 * j / 2), ("tail2", 0.6 - 0.6 * j / 2)], j / 2))
            rows.append(row)
        p.grid(rows, thickness=S * 0.002)
        parts.append(p.finish())
    return parts

def serpent_feats(L):
    bvh, sk, hc, n, z = L["bvh"], L["sk"], L["hc"], L["n"], L["z"]; R = SP["R"]; hr = SP["headR"]
    parts = []
    if "disc" in FE:             # trifin skimmer: a flat disc of a head
        p = Part("disc", 1)
        p.sphere(U(hc + V(0, hr * 0.2, hr * 0.15)), S * hr * SP.get("discR", 2.2), "head", scale=(1.0, 0.9, 0.22), sub=3)
        parts.append(p.finish())
    if "trifins" in FE:          # three fins at the tail: one dorsal, two ventro-lateral
        p = Part("trifins", 5)
        tail = sk.pt("s%d" % n); pre = sk.pt("s%d" % max(0, n - 2))
        for ang in (90, -30, 210):
            d = Vector((math.cos(math.radians(ang)), 0, math.sin(math.radians(ang))))
            rows = []
            for j in range(3):
                row = []
                for k in range(5):
                    t = k / 4; c = pre.lerp(tail, t) - Vector((0, S * 0.06 * t * j / 2, 0))
                    row.append((c + d * S * (R * 0.5 + SP.get("finH", 0.07) * j / 2 * math.sin(math.pi * (0.2 + 0.8 * t))), "seg%d" % (n - 1), j / 2))
                rows.append(row)
            p.grid(rows, flip=(ang == 210), thickness=S * 0.001)
        parts.append(p.finish())
    if "lobes" in FE:            # rakeclaw: overlapping swimming lobes down each side
        p = Part("lobes", 5)
        for i in range(n):
            t = (i + 0.5) / n; y = 0.42 - 0.92 * t
            if t > 0.85: continue
            for sx in (1, -1):
                rows = []
                for j in range(2):
                    row = []
                    for k in range(4):
                        yy = y + 0.04 - 0.08 * k / 3
                        w = R * SP.get("flatX", 1.0) * (0.9 + 1.4 * j * (1 - 0.6 * t)) * math.sin(math.pi * (0.15 + 0.7 * k / 3))
                        row.append((U((sx * (R * SP.get("flatX", 1.0) * 0.8 + w * j), yy, z - 0.004 * j)), "seg%d" % i, j))
                    rows.append(row)
                p.grid(rows, flip=sx < 0, thickness=S * 0.0008)
        parts.append(p.finish())
    if "rakes" in FE:            # rakeclaw: two spiny grasping limbs under the head
        p = Part("rakes", 2)
        for sx in (1, -1):
            a = U(hc + V(sx * hr * 0.5, hr * 0.6, -hr * 0.3)); prev = a
            for k in range(1, 7):
                ang = k / 6 * 2.2
                nxt = a + U((sx * hr * 0.4, hr * 1.4 * math.sin(ang) * 0.9, -hr * (1 - math.cos(ang)) * 0.9))
                p.tube(prev, nxt, S * hr * 0.16 * (1 - k / 9), S * hr * 0.16 * (1 - (k + 1) / 9), "head", rings=1, segs=5)
                p.cone(nxt, (0, -0.3, -1), S * hr * 0.35, S * hr * 0.05, "head", 3)
                prev = nxt
        parts.append(p.finish())
    if "stalkeyes" in FE:
        p = Part("stalks", 0); pe = Part("seyes", 3)
        for sx in (1, -1):
            a = U(hc + V(sx * hr * 0.55, hr * 0.1, hr * 0.4)); b = a + U((sx * hr * 0.6, hr * 0.2, hr * 0.9))
            p.tube(a, b, S * hr * 0.12, S * hr * 0.1, "head", rings=2, segs=6); pe.sphere(b, S * hr * 0.3, "head", sub=2)
        parts += [p.finish(), pe.finish()]
    if "sac" in FE:              # screwtail larva: the swelling rotor sac on its rear
        p = Part("sac", 6)
        p.sphere(sk.pt("s%d" % int(n * 0.8)) + Vector((0, 0, S * R * 0.6)), S * R * 2.0, [("seg%d" % int(n * 0.75), 0.5), ("seg%d" % min(n - 1, int(n * 0.85)), 0.5)], scale=(1, 1.4, 1), sub=2)
        parts.append(p.finish())
    if "slime" in FE:            # glistening mucus beads
        p = Part("slime", 6)
        for k in range(40):
            i = random.randrange(n); t = (i + 0.5) / n; y = 0.42 - 0.92 * t
            d = Vector((random.uniform(-1, 1), 0, random.uniform(-1, 1))).normalized()
            loc, nn = ray(bvh, U((0, y, z)) + d * S, -d)
            if loc: p.sphere(loc, S * R * 0.18, "seg%d" % i, sub=1)
        parts.append(p.finish())
    return parts

def avian_feats(L):
    sk, bvh, hc, W, hr = L["sk"], L["bvh"], L["hc"], SP["W"], SP["headR"]
    parts = []
    if "hindwings" in FE:        # thrumwing: a second, narrower pair of wings behind the first
        p = Part("hindwings", 5)
        for s, sx in (("L", 1), ("R", -1)):
            chain = [sk.pt("sh" + s), sk.pt("el" + s), sk.pt("wr" + s), sk.pt("tp" + s)]
            rows = []
            for j in range(3):
                row = []
                for k in range(9):
                    u = k / 8; i = min(2, int(u * 3)); f = u * 3 - i
                    le = chain[i].lerp(chain[i + 1], f) * Vector((0.85, 1, 1)) - Vector((0, S * (SP.get("chordRoot", 0.3) * 1.15), 0))
                    ch = S * SP.get("hindChord", SP.get("chordRoot", 0.3) * 0.85) * math.sin(math.pi * (0.06 + 0.92 * u)) ** 0.55 * (1 - 0.25 * u)
                    row.append((le + Vector((0, -ch * j / 2, -S * 0.01)), [("wing%d%s" % (i + 1, s), 1.0)], u))
                rows.append(row)
            p.grid(rows, flip=sx < 0, thickness=S * 0.0015)
        parts.append(p.finish())
    if "insectlegs" in FE:       # six jointed legs folded under the body, mandibles, antennae
        p = Part("legs", 2)
        for sx in (1, -1):
            for k in range(3):
                a = U((sx * W * 0.25, 0.12 - 0.12 * k, -W * 0.2)); b = a + U((sx * 0.12, -0.02, -0.08)); c = b + U((sx * 0.02, -0.06, -0.1))
                p.tube(a, b, S * 0.008, S * 0.006, "body", rings=1, segs=4); p.tube(b, c, S * 0.006, S * 0.003, "body", rings=1, segs=4)
            hcw = U(hc)
            p.cone(hcw + U((sx * hr * 0.4, hr * 0.8, -hr * 0.4)), (-sx * 0.5, 1, -0.2), S * hr * 1.0, S * hr * 0.2, "head", 4, bend=(-sx * 0.5, 0, 0))
            p.cone(hcw + U((sx * hr * 0.3, hr * 0.5, hr * 0.5)), (sx * 0.5, 1, 0.8), S * 0.2, S * 0.005, "head", 4, bend=(sx * 0.3, 0, -0.3))
        parts.append(p.finish())
        p = Part("compound", 3)
        for sx in (1, -1): p.sphere(U(hc) + U((sx * hr * 0.6, hr * 0.2, hr * 0.2)), S * hr * 0.6, "head", scale=(0.8, 1, 1), sub=2)
        parts.append(p.finish())
    if "ribs" in FE:             # skullkite: bones showing through thin skin
        p = Part("ribs", 2)
        for k in range(7):
            y = 0.14 - 0.035 * k
            for sx in (1, -1):
                prev = None
                for q in range(6):
                    ang = q / 5 * math.pi * 0.85
                    d = Vector((sx * math.sin(ang), 0, math.cos(ang)))
                    loc, n = ray(bvh, U((0, y, 0)) + d * S, -d)
                    if loc is None: continue
                    loc = loc + n * S * 0.003
                    if prev: p.tube(prev, loc, S * 0.004, S * 0.004, "body", rings=1, segs=4)
                    prev = loc
        for s in "LR":                        # finger bones along the wing
            for a_, b_, bn in (("sh", "el", "wing1"), ("el", "wr", "wing2"), ("wr", "tp", "wing3")):
                p.tube(sk.pt(a_ + s), sk.pt(b_ + s), S * 0.008, S * 0.005, bn + s, rings=2, segs=5)
        hcw = U(hc)                           # skull: brow ridges and empty-looking sockets
        for sx in (1, -1): p.sphere(hcw + U((sx * hr * 0.45, hr * 0.15, hr * 0.5)), S * hr * 0.35, "head", scale=(1, 1.2, 0.5), sub=1)
        parts.append(p.finish())
    if "gillslits" in FE:        # geyserkite: filter slits under the body
        p = Part("gills", 3)
        for k in range(5):
            for sx in (1, -1):
                p.sphere(U((sx * W * 0.25, 0.1 - 0.04 * k, -W * 0.18)), S * 0.012, "body", scale=(3.0, 0.4, 0.4), sub=1)
        parts.append(p.finish())
    return parts

def floater_feats(L):
    R, H = SP["R"], SP["H"]; tents = L["tents"]
    parts = []
    if "reefcrown" in FE:        # skyreef: coral-like feeding colonies crowding the top of the sac
        p = Part("reef", 1); q = Part("reefpolyps", 2)
        for k in range(SP.get("reefN", 140)):
            a = random.uniform(0, math.tau); r = R * math.sqrt(random.uniform(0, 0.85))
            zt = H * (0.62 - 0.55 * (r / R) ** 2)
            c = U((r * math.cos(a), r * math.sin(a), zt))
            kind = random.random(); rs = SP.get("reefScale", 1.0)
            if kind < 0.45: p.cone(c, (random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), 1), S * H * random.uniform(0.06, 0.18) * rs, S * R * random.uniform(0.015, 0.035) * rs, "body", 5, bend=(random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), 0))
            elif kind < 0.8: p.sphere(c, S * R * random.uniform(0.03, 0.07) * rs, "body", scale=(1, 1, 0.6), sub=1, jitter=0.35)
            else: q.sphere(c, S * R * random.uniform(0.02, 0.04) * rs, "body", sub=1, tip=random.random())
        parts += [p.finish(), q.finish()]
    if "siphon" in FE:           # bloomjelly: a chain of small bells down the central stem
        p = Part("bells", 6)
        for ti, (base, Lt, par, th, fl, a) in enumerate(tents):
            if fl >= 1: continue
            for k in range(1, 5):
                t = k / 5
                c = U(base + V(0, 0, -Lt * t))
                p.sphere(c, S * R * 0.28 * (1 - 0.12 * k), [("t%d_%d" % (ti, min(2, int(t * 3))), 1.0)], scale=(1, 1, 0.65), sub=2)
            break
        parts.append(p.finish())
    return parts

def blob_feats(L):
    bvh = L["bvh"]; parts = []
    if "cerata" in FE:           # slughorn: a ruff of finger-like cerata along the back
        p = Part("cerata", 5)
        for k in range(SP.get("ceraN", 90)):
            y = random.uniform(-0.4, 0.22); x = random.choice((-1, 1)) * random.uniform(0.08, 0.26)
            loc, n = ray(bvh, U((x, y, 1)), (0, 0, -1))
            if loc is None: continue
            bn = "front" if y > 0.15 else ("back" if y < -0.05 else "body")
            p.cone(loc - n * S * 0.005, (n + Vector((x * 2, -0.3, 0.4))).normalized(), S * random.uniform(0.05, 0.1), S * 0.012, bn, 5, bend=(0, -0.2, 0))
        parts.append(p.finish())
    if "foamglands" in FE:       # saponator: soap glands along the flanks
        p = Part("glands", 6)
        for k in range(30):
            y = -0.35 + 0.65 * k / 29
            for sx in (1, -1):
                d = Vector((sx, 0, 0.35)).normalized()
                loc, n = ray(bvh, U((0, y, 0.12)) + d * S, -d)
                if loc: p.sphere(loc, S * random.uniform(0.012, 0.022), "front" if y > 0.15 else ("back" if y < -0.05 else "body"), sub=1)
        parts.append(p.finish())
    return parts

exec(open(os.path.join(TOOLS, "fauna_giants.py"), encoding="utf-8").read(), globals())
exec(open(os.path.join(TOOLS, "fauna_birds.py"), encoding="utf-8").read(), globals())
