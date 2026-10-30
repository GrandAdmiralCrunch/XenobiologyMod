# Xenobiology — dedicated builders for Laythe's giants (exec'd from fauna_extra.py, shares fauna_build globals).
#   "cetacean": the Veilcheek Leviathan (whale body, gaping jaw, billowing cheek pouches, humpback flippers, flukes)
#   "seadragon": the Sagen Sea Serpent (draconic head, jaw, horns, frill fans, dorsal sail, tail fan, photophores)
#   "skysac":   the SkyReef (lobed gas sac, hanging reef underside, rippling flank fins, clustered sticky tendrils)
# Units are fractions of the creature's length (S metres); +Y forward, +Z up.

def _wts(*pairs):
    tot = sum(w for _, w in pairs if w > 0) or 1.0
    return [(b, w / tot) for b, w in pairs if w > 0]

# =============================================================================== CETACEAN
def build_cetacean():
    sk = Skel(S)
    sk.v("rost", 0, 0.50, -0.015, 0.035, 0.022)
    sk.v("snout", 0, 0.43, 0.0, 0.07, 0.045)
    sk.v("crown", 0, 0.32, 0.015, 0.1, 0.08)
    sk.v("chest", 0, 0.14, 0.0, 0.118, 0.105)
    sk.v("belly", 0, -0.04, -0.005, 0.108, 0.098)
    sk.v("lumbar", 0, -0.2, 0.005, 0.072, 0.07)
    sk.v("ped", 0, -0.33, 0.005, 0.03, 0.05)
    sk.v("stock", 0, -0.42, 0.0, 0.016, 0.026)
    sk.v("jawF", 0, 0.46, -0.055, 0.045, 0.025)
    sk.v("jawB", 0, 0.30, -0.07, 0.085, 0.05)
    sk.v("hump", 0, -0.12, 0.085, 0.02, 0.025)          # small dorsal hump
    sk.e("rost", "snout", "crown", "chest", "belly", "lumbar", "ped", "stock")
    sk.e("jawF", "jawB", "chest"); sk.e("lumbar", "hump")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.0032), faces=SP.get("faces", 8000), floor=False, stiffness=2.2)
    def skin_bumps(co, n):                               # tubercles on the head, a few scars elsewhere
        y = co.y / S
        if y > 0.3 and co.z > 0: co += n * S * 0.004 * max(0.0, noise.noise(co / S * 60.0))
        return co
    displace(body, skin_bumps)
    bones = [("body", (0, -0.04, 0), (0, 0.14, 0), None, False),
             ("head", (0, 0.14, 0), (0, 0.48, -0.005), "body", True),
             ("jaw", (0, 0.27, -0.065), (0, 0.48, -0.06), "head", False),
             ("pouch", (0, 0.24, -0.1), (0, 0.42, -0.1), "jaw", False),
             ("tail1", (0, -0.04, 0), (0, -0.2, 0.005), "body", False),
             ("tail2", (0, -0.2, 0.005), (0, -0.33, 0.005), "tail1", True),
             ("tail3", (0, -0.33, 0.005), (0, -0.42, 0.0), "tail2", True),
             ("fluke", (0, -0.42, 0.0), (0, -0.5, 0.0), "tail3", True)]
    for s, sx in (("L", 1), ("R", -1)):
        bones += [("fin1" + s, (sx * 0.09, 0.2, -0.07), (sx * 0.2, 0.15, -0.12), "body", False),
                  ("fin2" + s, (sx * 0.2, 0.15, -0.12), (sx * 0.33, 0.08, -0.16), "fin1" + s, True)]
    nd = ("pouch", "fin1L", "fin2L", "fin1R", "fin2R", "fluke")
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd)
    bvh = bvh_of(body); parts = []
    # eyes at the corners of the mouth
    p = Part("eyes", 3)
    for sx in (1, -1):
        d = Vector((sx, 0.1, 0.05)).normalized()
        loc, n = ray(bvh, U((0, 0.27, -0.02)) + d * S, -d)
        if loc: p.sphere(loc - n * S * 0.003, S * 0.009, "head", sub=2)
    parts.append(p.finish())
    # blowholes
    p = Part("blow", 3)
    for sx in (1, -1):
        loc, n = ray(bvh, U((sx * 0.012, 0.29, 1)), (0, 0, -1))
        if loc: p.sphere(loc, S * 0.008, "head", scale=(0.6, 1.6, 0.3), sub=1)
    parts.append(p.finish())
    # cheek pouches: two great veils hanging from the lower jaw, pleated, glowing faintly from within
    p = Part("pouches", 6)
    for sx in (1, -1):
        p.sphere(U((sx * 0.045, 0.335, -0.088)), S * 0.06, _wts(("pouch", 0.75), ("jaw", 0.25)), scale=(0.95, 2.1, 0.95), sub=4)
    parts.append(p.finish())
    # filter combs along both sides of the mouth line
    p = Part("combs", 2)
    for sx in (1, -1):
        for k in range(26):
            t = k / 25
            base = U((sx * (0.012 + 0.07 * (1 - t) ** 0.8), 0.27 + 0.2 * t, -0.03 - 0.012 * t))
            p.cone(base, (sx * 0.15, 0.05, -1), S * (0.035 - 0.015 * t), S * 0.0035, "head", 3, flat=0.25)
    parts.append(p.finish())
    # humpback flippers: long, narrow, with a knobbly leading edge
    p = Part("flippers", 5); kn = Part("knobs", 1)
    for s, sx in (("L", 1), ("R", -1)):
        root = Vector((sx * 0.09, 0.2, -0.07)); tip = Vector((sx * 0.31, 0.06, -0.15))
        rows = []
        for j in range(3):
            row = []
            for k in range(9):
                t = k / 8; c = root.lerp(tip, t) + Vector((0, 0.02 * math.sin(math.pi * t), 0))
                chord = 0.075 * (1 - 0.7 * t) + 0.01
                w = _wts(("fin1" + s, 1 - min(1, t * 1.6)), ("fin2" + s, min(1, t * 1.6)))
                row.append((U(c + Vector((0, -chord * j / 2 + 0.015, -0.002 * j))), w, t))
                if j == 0 and k % 2 == 0: kn.sphere(U(c + Vector((0, 0.016, 0))), S * 0.009, w, scale=(1, 1, 0.7), sub=2)
            rows.append(row)
        p.grid(rows, flip=sx < 0, thickness=S * 0.004)
    # flukes: wide, swept back, notched in the middle
    rows = []                                   # columns spanwise, rows from leading to trailing edge
    for j in range(4):
        row = []
        for k in range(15):
            u = k / 14 * 2 - 1; a = abs(u)
            x = u * 0.17
            le = -0.415 - 0.055 * a ** 1.3
            chord = 0.075 * (1 - 0.65 * a) + 0.008
            te = le - chord + (0.022 * (1 - a / 0.22) if a < 0.22 else 0.0)     # central notch
            yy = le + (te - le) * j / 3
            w = _wts(("fluke", 0.75 + 0.25 * a), ("tail3", 0.25 * (1 - a)))
            row.append((U((x, yy, 0.0)), w, a))
        rows.append(row)
    p.grid(rows, flip=True, thickness=S * 0.005)
    parts += [p.finish(), kn.finish()]
    # barnacle clusters and tubercles
    p = Part("barnacles", 1)
    for k in range(70):
        y = random.choice((random.uniform(0.35, 0.5), random.uniform(-0.3, 0.2)))
        d = Vector((random.uniform(-1, 1), 0, random.uniform(0.1, 1))).normalized()
        loc, n = ray(bvh, U((0, y, 0)) + d * S, -d)
        if loc is None: continue
        bn = "head" if y > 0.14 else ("body" if y > -0.04 else "tail1")
        p.sphere(loc, S * random.uniform(0.0025, 0.006), bn, scale=(1, 1, 0.6), sub=1, jitter=0.3)
    parts.append(p.finish())
    return body, rig, parts, {}, mode

def anim_cetacean(A, info):
    def stroke(amp, gapeOn=False):
        def fn(t):
            P = {}; w = 2 * math.pi * t
            P["body"] = A.rot("body", up=-amp * 0.12 * math.sin(w))
            P["head"] = A.rot("head", up=amp * 0.08 * math.sin(w - 0.2))
            for i, b in enumerate(("tail1", "tail2", "tail3")):
                P[b] = A.rot(b, up=amp * (0.25 + 0.3 * i) * math.sin(w - 0.7 * (i + 1)))
            P["fluke"] = A.rot("fluke", up=amp * 1.1 * math.sin(w - 2.6))
            for s in "LR":
                P["fin1" + s] = A.rot("fin1" + s, up=4 + 5 * math.sin(w * 0.5 + (0 if s == "L" else 0.4)), fwd=-6)
                P["fin2" + s] = A.rot("fin2" + s, up=3 * math.sin(w * 0.5 - 0.6))
            gape = 0.0
            if gapeOn: gape = seg(t, 0.15, 0.35) * (1 - seg(t, 0.55, 0.8))
            P["jaw"] = A.rot("jaw", up=-14 * gape)
            sw = 1.0 + 0.4 * gape + 0.25 * seg(t, 0.35, 0.6) * (1 - seg(t, 0.75, 1.0))
            P["pouch"] = (A.rot("pouch", up=0), (1.0 + 0.3 * (sw - 1), 1.0, sw))
            return P, (0, 0, 0.004 * S * math.sin(w))
        return fn
    def breach(t):
        P = {}
        arch = math.sin(math.pi * t)
        P["body"] = A.rot("body", up=30 * (0.5 - t) * 2 * 0.7)
        P["head"] = A.rot("head", up=8 * arch)
        for i, b in enumerate(("tail1", "tail2", "tail3")): P[b] = A.rot(b, up=-10 * arch * (1 + 0.3 * i))
        P["fluke"] = A.rot("fluke", up=-15 * arch)
        for s in "LR":
            P["fin1" + s] = A.rot("fin1" + s, up=35 * arch, fwd=-15 * arch)
            P["fin2" + s] = A.rot("fin2" + s, up=10 * arch)
        P["pouch"] = (A.rot("pouch", up=0), 1.0)
        return P, (0, 0, 0)
    sf = SP.get("swimFrames", 120)
    return ([("idle", stroke(7, True), SP.get("idleFrames", 270), 3, False), ("swim", stroke(14), sf, 2, False), ("breach", breach, 135, 3, False)],
            dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="idle", leapAnim="breach", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))

# =============================================================================== SEA DRAGON
def build_seadragon():
    nseg = SP.get("bones", 16)
    def radius(y):                    # body profile along the length (y: 0.30 chest .. -0.5 tail tip)
        t = (0.30 - y) / 0.80
        return 0.033 * (0.9 + 0.12 * math.sin(math.pi * min(1, t * 1.4))) * (1 - 0.85 * max(0, t - 0.55) / 0.45) + 0.004
    sk = Skel(S)
    sk.v("snout", 0, 0.535, 0.002, 0.011, 0.008)
    sk.v("muzzle", 0, 0.49, 0.006, 0.019, 0.013)
    sk.v("skull", 0, 0.44, 0.012, 0.03, 0.024)
    sk.v("n1", 0, 0.39, 0.0, 0.024, 0.024)
    sk.v("n2", 0, 0.345, 0.0, 0.028, 0.028)
    sk.v("chest", 0, 0.30, 0.0, radius(0.30), radius(0.30))
    chain = ["snout", "muzzle", "skull", "n1", "n2", "chest"]
    ys = [0.30 - 0.80 * (i + 1) / nseg for i in range(nseg)]
    for i, y in enumerate(ys):
        sk.v("t%d" % i, 0, y, 0.0, radius(y) * 1.05, radius(y)); chain.append("t%d" % i)
    sk.v("jawB", 0, 0.425, -0.02, 0.024, 0.012); sk.v("jawF", 0, 0.52, -0.012, 0.01, 0.006); sk.e("jawF", "jawB", "n1")
    sk.e(*chain)
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.0024), faces=SP.get("faces", 9000), floor=False, stiffness=2.1)
    bones = [("body", (0, 0.30, 0), (0, 0.34, 0), None, False),
             ("neck1", (0, 0.34, 0), (0, 0.38, 0), "body", True),
             ("neck2", (0, 0.38, 0), (0, 0.42, 0.005), "neck1", True),
             ("head", (0, 0.42, 0.005), (0, 0.52, 0.004), "neck2", True),
             ("jaw", (0, 0.42, -0.015), (0, 0.51, -0.012), "head", False)]
    prev = "body"; prevpt = (0, 0.30, 0)
    for i, y in enumerate(ys):
        bones.append(("seg%d" % i, prevpt, (0, y, 0), prev if i else "body", i > 0)); prev = "seg%d" % i; prevpt = (0, y, 0)
    for s, sx in (("L", 1), ("R", -1)):
        bones.append(("frill" + s, (sx * 0.02, 0.405, 0.005), (sx * 0.06, 0.37, 0.01), "head", False))
    bones.append(("tailfan", prevpt, (0, prevpt[1] - 0.05, 0), prev, True))
    nd = ("frillL", "frillR", "tailfan")
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd)
    bvh = bvh_of(body); parts = []
    def segname(y):
        if y >= 0.30: return "body"
        i = min(nseg - 1, int((0.30 - y) / 0.80 * nseg)); return "seg%d" % i
    # eyes: two pairs, under heavy brows
    p = Part("eyes", 3)
    for (yy, zz, r) in ((0.46, 0.02, 0.0085), (0.442, 0.01, 0.006)):
        for sx in (1, -1):
            d = Vector((sx, 0.25, 0.25)).normalized()
            loc, n = ray(bvh, U((0, yy, zz)) + d * S, -d)
            if loc: p.sphere(loc - n * S * 0.002, S * r, "head", sub=2)
    parts.append(p.finish())
    # horns: two long swept-back, two short; brow ridges
    p = Part("horns", 2)
    for sx in (1, -1):
        p.cone(U((sx * 0.016, 0.43, 0.035)), (sx * 0.35, -1, 0.55), S * 0.075, S * 0.007, "head", 6, bend=(0, -0.3, 0.2))
        p.cone(U((sx * 0.022, 0.415, 0.022)), (sx * 0.8, -1, 0.2), S * 0.03, S * 0.004, "head", 5)
        p.sphere(U((sx * 0.017, 0.462, 0.026)), S * 0.009, "head", scale=(1, 2.6, 0.55), sub=2)
        for k in range(4):                                   # cheek spikes
            p.cone(U((sx * 0.026, 0.425 - 0.008 * k, -0.004)), (sx * 1, -0.8, -0.1 * k), S * (0.02 - 0.003 * k), S * 0.003, "head", 4)
    # teeth on both jaws
    for k in range(14):
        t = k / 13; yy = 0.43 + 0.085 * t
        for sx in (1, -1):
            p.cone(U((sx * (0.016 - 0.01 * t), yy, -0.004)), (sx * 0.1, 0.25, -1), S * 0.011, S * 0.0022, "head", 3)
            p.cone(U((sx * (0.013 - 0.008 * t), yy - 0.002, -0.016)), (sx * 0.1, 0.25, 1), S * 0.008, S * 0.0018, "jaw", 3)
    parts.append(p.finish())
    # frill fans behind the head, with spines
    pf = Part("frills", 5); ps = Part("frillspines", 2)
    for s, sx in (("L", 1), ("R", -1)):
        base = Vector((sx * 0.022, 0.405, 0.006)); rows = []
        for j in range(4):
            row = []
            for k in range(9):
                a = (k / 8 - 0.5) * 2.6
                L = 0.085 * (j / 3) * (1.0 - 0.25 * abs(a)) * (1.0 - (0.18 * abs(math.sin(k * math.pi / 2)) if j == 3 else 0))
                row.append((U(base + Vector((sx * (0.004 + L * math.cos(a) * 0.9), -L * 0.55, L * math.sin(a)))), _wts(("frill" + s, j / 3), ("head", 1 - j / 3)), j / 3))
            rows.append(row)
        pf.grid(rows, flip=sx < 0, thickness=S * 0.0008)
        for k in range(9):
            a = (k / 8 - 0.5) * 2.6
            ps.cone(U(base), (sx * math.cos(a) * 0.9, -0.55, math.sin(a)), S * 0.095 * (1.0 - 0.25 * abs(a)), S * 0.0022, "frill" + s, 3)
    # dorsal sail with spine rays from neck to two-thirds down the tail
    rows = []; NK = 30
    for j in range(3):
        row = []
        for k in range(NK + 1):
            t = k / NK; y = 0.36 - 0.62 * t
            loc, n = ray(bvh, U((0, y, 0.2)), (0, 0, -1))
            z0 = loc.z if loc else U((0, 0, radius(y))).z
            h = S * 0.05 * math.sin(math.pi * min(1, t * 1.15)) ** 0.7 * (j / 2) * (1.0 - (0.3 * abs(math.sin(k * math.pi / 2)) if j == 2 else 0))
            row.append((Vector((0, y * S, z0 - S * 0.002 + h)), segname(y) if y < 0.34 else "neck1", j / 2))
        rows.append(row)
    pf.grid(rows, thickness=S * 0.0006)
    for k in range(0, NK + 1, 2):
        t = k / NK; y = 0.36 - 0.62 * t
        loc, n = ray(bvh, U((0, y, 0.2)), (0, 0, -1))
        if loc: ps.cone(loc, (0, -0.25, 1), S * 0.058 * math.sin(math.pi * min(1, t * 1.15)) ** 0.7 + S * 0.004, S * 0.0026, segname(y) if y < 0.34 else "neck1", 3)
    # tail fan: vertical, wide
    rows = []
    tip = Vector((0, ys[-1], 0))
    for j in range(3):
        row = []
        for k in range(7):
            v = k / 6 - 0.5
            row.append((U(tip + Vector((0, -0.06 * (j / 2) * (1 - 0.4 * abs(v)), v * 0.09 * (0.3 + 0.7 * j / 2)))), _wts(("tailfan", j / 2 + 0.3), (prev, 0.7 - j / 2 * 0.7)), j / 2))
        rows.append(row)
    pf.grid(rows, thickness=S * 0.0008)
    parts += [pf.finish(), ps.finish()]
    # two pairs of paddle fins
    pp = Part("paddles", 5)
    for (yy, L) in ((0.26, 0.06), (0.0, 0.045)):
        for sx in (1, -1):
            rows = []
            bn = segname(yy)
            for j in range(3):
                row = []
                for k in range(5):
                    t = k / 4
                    row.append((U((sx * (0.03 + L * (j / 2)), yy + 0.02 - 0.05 * t - 0.03 * (j / 2) * t, -0.014 - 0.012 * (j / 2))), bn, j / 2))
                rows.append(row)
            pp.grid(rows, flip=sx < 0, thickness=S * 0.0012)
    parts.append(pp.finish())
    # photophore rows along the flanks
    p = Part("lights", 6)
    for k in range(40):
        y = 0.3 - 0.62 * k / 39
        for sx in (1, -1):
            for zz in (0.25, -0.35):
                d = Vector((sx, 0, zz)).normalized()
                loc, n = ray(bvh, U((0, y, 0)) + d * S, -d)
                if loc and k % 2 == (0 if zz > 0 else 1): p.sphere(loc, S * 0.0028, segname(y), sub=1)
    parts.append(p.finish())
    return body, rig, parts, dict(nseg=nseg), mode

def anim_seadragon(A, info):
    n = info["nseg"]
    def humps(amp, cycles, yawA, headUp):
        def fn(t):
            P = {}
            for i in range(n):
                ph = 2 * math.pi * (t - i / n * cycles)
                P["seg%d" % i] = A.rot("seg%d" % i, up=amp * math.sin(ph) * (0.6 + 0.4 * i / n), yaw=yawA * math.sin(ph * 0.5 + 0.7))
            P["body"] = A.rot("body", up=amp * 0.4 * math.sin(2 * math.pi * t + 0.4))
            P["neck1"] = A.rot("neck1", up=headUp * 0.6 + 3 * math.sin(2 * math.pi * t))
            P["neck2"] = A.rot("neck2", up=headUp * 0.4, yaw=6 * math.sin(2 * math.pi * t * 0.5))
            P["head"] = A.rot("head", up=-headUp * 0.7 - 2 * math.sin(2 * math.pi * t), yaw=-4 * math.sin(2 * math.pi * t * 0.5))
            P["jaw"] = A.rot("jaw", up=-3 - 3 * max(0, math.sin(2 * math.pi * t * 2)))
            for s, sg in (("L", 1), ("R", -1)): P["frill" + s] = A.rot("frill" + s, yaw=sg * 6 * math.sin(2 * math.pi * t), up=4 * math.sin(2 * math.pi * t + 1))
            P["tailfan"] = A.rot("tailfan", yaw=12 * math.sin(2 * math.pi * (t - cycles)))
            return P, (0, 0, 0)
        return fn
    def alert(t):
        P = {}; w = 2 * math.pi * t
        for i in range(n): P["seg%d" % i] = A.rot("seg%d" % i, up=6 * math.sin(w - i * 0.5), yaw=4 * math.sin(w * 0.5 - i * 0.3))
        P["body"] = A.rot("body", up=14)
        P["neck1"] = A.rot("neck1", up=26); P["neck2"] = A.rot("neck2", up=18, yaw=14 * math.sin(w)); P["head"] = A.rot("head", up=-34)
        P["jaw"] = A.rot("jaw", up=-16 - 6 * max(0, math.sin(w * 3)))
        for s, sg in (("L", 1), ("R", -1)): P["frill" + s] = A.rot("frill" + s, yaw=sg * 30, up=10)
        return P, (0, 0, 0)
    return ([("idle", humps(5, 1.0, 3, 30), 180, 3, False), ("move", humps(11, 1.6, 6, 22), 72, 2, False), ("alert", alert, 90, 2, False)],
            dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="alert", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))

# =============================================================================== SKY SAC (SkyReef)
def build_skysac():
    sk = Skel(S)
    # a long, living airship: lobed along its length, rounded underneath, tapering at both ends
    lobes = [("core", 0, 0.0, 0.02, 0.31, 0.31), ("fore", 0, 0.25, 0.03, 0.27, 0.28), ("aft", 0, -0.25, 0.02, 0.28, 0.28),
             ("nose", 0, 0.45, 0.05, 0.18, 0.18), ("tail", 0, -0.46, 0.01, 0.18, 0.17),
             ("noseTip", 0, 0.6, 0.06, 0.09, 0.09), ("tailTip", 0, -0.62, 0.0, 0.09, 0.08),
             ("topF", 0.06, 0.13, 0.24, 0.16, 0.15), ("topA", -0.07, -0.15, 0.23, 0.17, 0.15), ("topM", 0.0, -0.01, 0.29, 0.14, 0.12),
             ("keelF", 0, 0.16, -0.2, 0.22, 0.18), ("keelA", 0, -0.17, -0.2, 0.23, 0.18), ("keelM", 0, 0.0, -0.24, 0.2, 0.16)]
    for sx, nm in ((1, "L"), (-1, "R")):
        lobes += [("side%sF" % nm, sx * 0.19, 0.13, 0.02, 0.17, 0.17), ("side%sA" % nm, sx * 0.2, -0.16, 0.02, 0.18, 0.17)]
    BLOAT = SP.get("form") == "bloat"
    if BLOAT:   # bloatfloater: a fat, near-round bag in lumpy lobes, a flattened crown on top, skirt underneath
        lobes = [("core", 0, 0.0, 0.03, 0.29, 0.27), ("crown", 0, 0.0, 0.25, 0.21, 0.11), ("skirt", 0, 0.0, -0.16, 0.24, 0.13)]
        for k in range(7):                               # swollen lobes bulging out all round, uneven like an overfilled bag
            a = k / 7 * math.tau + 0.4; r = 0.25 + 0.03 * math.sin(k * 2.9)
            lobes.append(("bulge%d" % k, math.cos(a) * r, math.sin(a) * r, 0.04 + 0.07 * math.sin(k * 2.3), 0.15 + 0.025 * math.cos(k * 1.7), 0.17 + 0.02 * math.sin(k)))
        for k in range(4):                               # a second, smaller tier of blisters higher up
            a = k / 4 * math.tau + 1.1
            lobes.append(("blister%d" % k, math.cos(a) * 0.17, math.sin(a) * 0.17, 0.2, 0.11, 0.1))
    for nm, x, y, z, rs, rv in lobes: sk.v(nm, x, y, z, rs, rv)
    for nm, *_ in lobes:
        if nm != "core": sk.e("core", nm)
    if not BLOAT: sk.e("noseTip", "nose", "fore", "core", "aft", "tail", "tailTip")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.006), faces=SP.get("faces", 8000), floor=False, mb_scale=1.15, stiffness=2.0)
    def organic(co, n):
        d = noise.noise(co / S * 5.0) * 0.012 + noise.noise(co / S * 14.0) * 0.004
        if co.z < -S * 0.16: d -= 0.004                 # slightly puckered keel where the reef grows
        if BLOAT and co.z > S * 0.3: d -= 0.012 * min(1.0, (co.z / S - 0.3) * 12)   # flattened crown
        co += n * S * d
        return co
    displace(body, organic)
    tag_body(body, 5)                                    # the sac is membrane: veined, translucent-looking, faintly glowing
    bones = [("body", (0, -0.25, 0), (0, 0.25, 0), None, False),
             ("fore", (0, 0.25, 0.01), (0, 0.66, 0.05), "body", True),
             ("aft", (0, -0.25, 0), (0, -0.68, -0.01), "body", False),
             ("dome", (0, 0, 0.05), (0, 0, 0.3), "body", False)]
    if BLOAT:
        bones = [("body", (0, -0.12, 0), (0, 0.12, 0), None, False), ("fore", (0, 0.12, 0.02), (0, 0.33, 0.03), "body", True),
                 ("aft", (0, -0.12, 0.02), (0, -0.33, 0.02), "body", False), ("dome", (0, 0, 0.08), (0, 0, 0.34), "body", False)]
    hasFins = SP.get("fins", True)
    for s, sx in ((("L", 1), ("R", -1)) if hasFins else ()):
        for k in range(4):
            y0 = 0.36 - 0.18 * k; y1 = y0 - 0.18
            bones.append(("fin%s%d" % (s, k), (sx * 0.36, y0, -0.08), (sx * 0.36, y1, -0.08), "body", False))
    clusters = []
    nc = SP.get("clusters", 8)
    for c in range(nc):
        y = 0.4 - 0.8 * (c // 2) / max(1, (nc - 1) // 2); x = (0.07 if c % 2 else -0.07) + 0.02 * math.sin(c * 2.1)
        base = Vector((x, y, -0.3))
        if BLOAT:                                        # a ring of tendril clusters round the skirt, one in the middle
            a = c / max(1, nc - 1) * math.tau
            base = Vector((0, 0, -0.27)) if c == nc - 1 else Vector((math.cos(a) * 0.19, math.sin(a) * 0.19, -0.24))
        TL = SP["TL"] * (0.7 + 0.3 * ((c * 37) % 7) / 6)
        back = SP.get("trailBack", 0.22)
        rad = Vector((base.x, base.y, 0)); rad = rad.normalized() * TL * SP.get("splay", 0.0) if rad.length > 1e-6 else Vector()
        pts = [base + Vector((0, -TL * back * (k / 4) ** 1.4, -TL * k / 4)) + rad * (k / 4) ** 1.2 for k in range(5)]
        for k in range(4):
            bones.append(("c%d_%d" % (c, k), tuple(pts[k]), tuple(pts[k + 1]), "body" if k == 0 else "c%d_%d" % (c, k - 1), k > 0))
        clusters.append((base, TL, pts))
    nd = tuple(b[0] for b in bones if b[0].startswith(("fin", "c")))
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd)
    bvh = bvh_of(body); parts = []
    # ---- the hanging reef: branching colonies, fans and polyps crowding the underside
    pr = Part("reef", 1); pp = Part("polyps", 6); ph = Part("fans", 2)
    def under_pt(x, y):
        loc, n = ray(bvh, U((x, y, -1)), (0, 0, 1))
        return loc, n
    for k in range(SP.get("reefN", 220)):
        x = random.uniform(-0.2, 0.2); y = random.uniform(-0.55, 0.55)
        if BLOAT: x = random.uniform(-0.27, 0.27); y = random.uniform(-0.27, 0.27)
        if (x / 0.2) ** 2 + (y / 0.56) ** 2 > 1 and not BLOAT: continue
        if BLOAT and x * x + y * y > 0.27 ** 2: continue
        loc, n = under_pt(x, y)
        if loc is None: continue
        bn = "fore" if y > 0.3 else ("aft" if y < -0.3 else "body")
        kind = random.random()
        if BLOAT:                                          # feeding frills and glowing digestive sacs, no reef
            if kind < 0.45: ph.cone(loc, (random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), -1), S * random.uniform(0.03, 0.06), S * random.uniform(0.015, 0.03), bn, 6, flat=0.15)
            elif kind < 0.75: pp.sphere(loc + n * S * 0.004, S * random.uniform(0.01, 0.022), bn, scale=(1, 1, 0.8), sub=2)
            else: pr.sphere(loc, S * random.uniform(0.008, 0.016), bn, scale=(1, 1, 0.5), sub=1, jitter=0.3)
        elif kind < 0.4:                                     # branching coral hanging down
            d = (Vector((random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), -1))).normalized()
            L = S * random.uniform(0.02, 0.06)
            pr.cone(loc, d, L * 1.8, S * random.uniform(0.008, 0.016), bn, 5, bend=(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), 0))
            pp.sphere(loc + d * L, S * 0.004, bn, sub=1)
        elif kind < 0.65:                                  # boulder colonies
            pr.sphere(loc, S * random.uniform(0.012, 0.03), bn, scale=(1, 1, 0.6), sub=2, jitter=0.35)
        elif kind < 0.85:                                  # sea-fan plates
            a = random.uniform(0, math.pi)
            ph.cone(loc, (math.cos(a) * 0.2, math.sin(a) * 0.2, -1), S * random.uniform(0.035, 0.065), S * random.uniform(0.02, 0.035), bn, 6, flat=0.12)
        else:
            pp.sphere(loc, S * random.uniform(0.003, 0.007), bn, sub=1)
    parts += [pr.finish(), pp.finish(), ph.finish()]
    # ---- spiracles: rimmed gas vents along the top of the sac
    p = Part("spiracles", 3); pr2 = Part("spirims", 1)
    for k in range(9):
        y = 0.48 - 0.96 * k / 8; x = 0.05 * math.sin(k * 1.9)
        if BLOAT: a = k / 9 * math.tau; x = math.cos(a) * 0.25; y = math.sin(a) * 0.25
        loc, n = ray(bvh, U((x, y, 1)), (0, 0, -1))
        if loc is None: continue
        bn = "fore" if y > 0.3 else ("aft" if y < -0.3 else "dome")
        pr2.sphere(loc, S * 0.016, bn, scale=(1, 1, 0.35), sub=2)
        p.sphere(loc + n * S * 0.003, S * 0.009, bn, scale=(1, 1, 0.3), sub=1)
    parts += [p.finish(), pr2.finish()]
    if BLOAT:   # ---- the crown: a colony of papery nest cells, chimneys and burrow holes where the crestflies live
        pc = Part("nests", 1); pk = Part("nestholes", 3)
        for k in range(SP.get("nestN", 140)):
            r = 0.17 * math.sqrt(random.random()); a = random.uniform(0, math.tau)
            x, y = math.cos(a) * r, math.sin(a) * r
            loc, n = ray(bvh, U((x, y, 1)), (0, 0, -1))
            if loc is None: continue
            kind = random.random()
            if kind < 0.45:
                h = S * random.uniform(0.012, 0.03); rr = S * random.uniform(0.008, 0.014)
                pc.cone(loc - n * S * 0.002, (n + Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0))).normalized(), h, rr, "dome", 6)
                pk.sphere(loc + n * h * 0.55, rr * 0.45, "dome", scale=(1, 1, 0.4), sub=1)
            elif kind < 0.8:
                pc.sphere(loc, S * random.uniform(0.01, 0.02), "dome", scale=(1, 1, 0.55), sub=2, jitter=0.25)
            else:
                pk.sphere(loc + n * S * 0.002, S * random.uniform(0.006, 0.01), "dome", scale=(1, 1, 0.3), sub=1)
        parts += [pc.finish(), pk.finish()]
    # ---- flank fins: long rippling membranes that push it sideways through the air
    p = Part("fins", 5)
    for s, sx in ((("L", 1), ("R", -1)) if hasFins else ()):
        rows = []
        for j in range(3):
            row = []
            for k in range(17):
                t = k / 16; y = 0.36 - 0.72 * t
                seg_ = min(3, int(t * 4))
                loc, n = ray(bvh, U((sx * 1, y, -0.08)), (-sx, 0, 0))
                root = loc if loc else U((sx * 0.36, y, -0.08))
                w = S * 0.11 * math.sin(math.pi * (0.1 + 0.8 * t)) * (j / 2)
                row.append((root + Vector((sx * w * 0.45, 0, -w)), [("fin%s%d" % (s, seg_), 1.0)] if j else [("body", 1.0)], j / 2))
            rows.append(row)
        p.grid(rows, flip=sx < 0, thickness=S * 0.0012)
    parts.append(p.finish())
    # ---- sticky tendrils in clusters, beaded with glistening droplets
    pt = Part("tendrils", 0); pb = Part("beads", 6)
    per = SP.get("perCluster", 6)
    for c, (base, TL, pts) in enumerate(clusters):
        for q in range(per):
            ang = q / per * math.tau
            off = Vector((math.cos(ang), math.sin(ang), 0)) * random.uniform(0.006, 0.03)
            Lq = random.uniform(0.6, 1.0)
            prev = None; NR = 16
            loc, n = ray(bvh, U(base + off + Vector((0, 0, 0.25))), (0, 0, -1))
            top = loc if loc else U(base + off)
            for kk in range(NR + 1):
                t = kk / NR * Lq; seg_ = min(3, int(t * 4)); f = t * 4 - seg_
                c3 = top + U(Vector((0, -TL * SP.get("trailBack", 0.22) * t ** 1.4, -TL * t))) + U(off * (1 + 2 * t))
                if BLOAT: c3 += U((pts[4] - pts[0] - Vector((0, -TL * SP.get("trailBack", 0.22), -TL))) * t ** 1.2)
                rr = S * SP.get("tentThick", 0.0022) * (1 - 0.6 * t / Lq)
                w = [("c%d_%d" % (c, seg_), 1 - 0.5 * max(0, f - 0.5)), ("c%d_%d" % (c, min(3, seg_ + 1)), 0.5 * max(0, f - 0.5))] if seg_ < 3 else [("c%d_3" % c, 1.0)]
                if kk == 0: w = [("body", 1.0)]
                cur = [pt.v(c3 + Vector((math.cos(j / 5 * math.tau) * rr, math.sin(j / 5 * math.tau) * rr, 0)), w, t) for j in range(5)]
                if prev:
                    for j in range(5): pt.f([prev[j], prev[(j + 1) % 5], cur[(j + 1) % 5], cur[j]])
                prev = cur
                if kk % 2 == 1: pb.sphere(c3, rr * 2.6, w, sub=1)
    parts += [pt.finish(), pb.finish()]
    return body, rig, parts, dict(nc=len(clusters)), mode

def anim_skysac(A, info):
    nc = info["nc"]
    def drift(trail, finSpeed, sway):
        def fn(t):
            P = {}; w = 2 * math.pi * t
            br = math.sin(w)
            P["body"] = (A.rot("body", roll=1.2 * math.sin(w + 0.5), up=0.8 * math.sin(w)), (1.0 + 0.012 * br, 1.0 + 0.008 * br, 1.0 + 0.018 * br))
            P["dome"] = (A.rot("dome", up=0), 1.0 + 0.03 * math.sin(w + 1.2))
            P["fore"] = A.rot("fore", up=1.5 * math.sin(w + 0.8))
            P["aft"] = A.rot("aft", up=-1.5 * math.sin(w + 2.0))
            for s, sg in ((("L", 1), ("R", -1)) if "finL0" in A.arm.bones else ()):
                for k in range(4):
                    P["fin%s%d" % (s, k)] = A.rot("fin%s%d" % (s, k), roll=sg * 14 * math.sin(finSpeed * w - k * 1.3))
            for c in range(nc):
                for k in range(4):
                    b = "c%d_%d" % (c, k)
                    P[b] = qmul(rotaxis(A, b, (1, 0, 0), trail * (0.6 if k == 0 else 0.25) + sway * math.sin(w + c * 0.9 - k * 0.7)),
                                rotaxis(A, b, (0, 1, 0), sway * 0.6 * math.sin(w * (1 if c % 2 else 2) + c * 1.7 - k * 0.5)))
            return P, (0, 0, 0)
        return fn
    return ([("idle", drift(0.0, 2, 2.5), SP.get("idleFrames", 600), 6, False), ("drift", drift(-6.0, 3, 3.0), SP.get("moveFrames", 600), 6, False)],
            dict(idleAnim="idle", moveAnim="drift", fleeAnim="drift", alertAnim="idle", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))

BUILD["cetacean"] = (build_cetacean, anim_cetacean)
BUILD["seadragon"] = (build_seadragon, anim_seadragon)
BUILD["skysac"] = (build_skysac, anim_skysac)

# =============================================================================== SKY LEVIATHAN (Laythe) + its pupa and larva
# form = "adult": an arching, swept-back canopy of segmented ribs with membrane between them, a filter-comb throat,
#                 and a mass of trailing tentacles - nearly a kilometre from canopy to tentacle tips.
# form = "pupa":  the gas-swollen sac with the canopy ribs crumpled over it, the grub body still slung beneath.
# form = "larva": a fat segmented seafloor grub.
LEV_TK = (0.0, 0.4, 0.8, 1.18)          # rib bone breaks along the rib parameter t (1.0 = membrane edge)

def lev_rib(phi, Lr, t):
    hub = Vector((0, 0.045, 0.075))
    d = Vector((math.sin(phi), -math.cos(phi), 0))
    z = Lr * (0.46 * math.sin(math.pi * min(t, 1.0) * 0.72) - SP.get("droop", 0.34) * t * t)
    return hub + d * (Lr * t * (1 - 0.12 * t)) + Vector((0, -Lr * 0.24 * t * t, z))

def lev_bone(i, t):
    k = 0 if t < LEV_TK[1] else (1 if t < LEV_TK[2] else 2)
    return "r%d_%d" % (i, k)

def build_skylev():
    form = SP.get("form", "adult")
    return {"adult": build_lev_adult, "pupa": build_lev_pupa, "larva": build_lev_larva}[form]()

def build_lev_adult():
    sk = Skel(S)
    for nm, x, y, z, rs, rv in (("head", 0, 0.115, 0.05, 0.03, 0.026), ("neck", 0, 0.06, 0.055, 0.045, 0.042), ("core", 0, 0.0, 0.02, 0.056, 0.05),
                                ("belly", 0, -0.045, -0.03, 0.05, 0.045), ("tail", 0, -0.095, -0.07, 0.03, 0.03), ("tip", 0, -0.14, -0.1, 0.012, 0.012)):
        sk.v(nm, x, y, z, rs, rv)
    sk.e("head", "neck", "core", "belly", "tail", "tip")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.004), faces=SP.get("faces", 6000), floor=False, mb_scale=1.15, stiffness=2.0)
    def ridged(co, n):
        u = co / S
        d = 0.0035 * math.sin(u.y * 140.0) + noise.noise(u * 12.0) * 0.004
        co += n * S * d
        return co
    displace(body, ridged)
    tag_body(body, 0)
    span = SP.get("ribSpan", 112); nr = SP.get("nr", 15); phis = [math.radians(-span + 2 * span * i / (nr - 1)) for i in range(nr)]
    Lrs = [SP.get("ribL", 0.3) * (0.72 + 0.28 * math.cos(p * 0.85)) for p in phis]
    bones = [("body", (0, -0.06, 0.0), (0, 0.06, 0.035), None, False), ("head", (0, 0.06, 0.035), (0, 0.135, 0.05), "body", True),
             ("tailb", (0, -0.06, 0.0), (0, -0.14, -0.1), "body", False)]
    for i, (p, Lr) in enumerate(zip(phis, Lrs)):
        for k in range(3):
            bones.append(("r%d_%d" % (i, k), tuple(lev_rib(p, Lr, LEV_TK[k])), tuple(lev_rib(p, Lr, LEV_TK[k + 1])), "body" if k == 0 else "r%d_%d" % (i, k - 1), k > 0))
    nc = SP.get("nc", 10); TL = SP.get("TL", 0.72); clusters = []
    for c in range(nc):
        a = c / (nc - 1) * math.tau if c < nc - 1 else 0.0
        base = Vector((0, -0.04, -0.07)) if c == nc - 1 else Vector((math.cos(a) * 0.04, -0.03 + math.sin(a) * 0.05, -0.055))
        rad = Vector((base.x, base.y + 0.03, 0))
        rad = rad.normalized() * TL * 0.1 if rad.length > 1e-6 else Vector()
        pts = [base + Vector((0, -TL * 0.34 * (k / 4) ** 1.4, -TL * k / 4)) + rad * (k / 4) ** 1.2 for k in range(5)]
        for k in range(4):
            bones.append(("c%d_%d" % (c, k), tuple(pts[k]), tuple(pts[k + 1]), "body" if k == 0 else "c%d_%d" % (c, k - 1), k > 0))
        clusters.append((base, pts))
    nd = tuple(b[0] for b in bones if b[0].startswith(("r", "c")) and b[0] != "body")
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd)
    bvh = bvh_of(body); parts = []
    # ---- ribs: segmented dark spines with knobbed joints, running past the membrane as bare tattered spikes
    pr = Part("ribs", 2); pk = Part("ribknobs", 2); pl = Part("photophores", 6)
    for i, (p, Lr) in enumerate(zip(phis, Lrs)):
        n = 24
        for j in range(n):
            t0 = 1.18 * j / n; t1 = 1.18 * (j + 1) / n
            r0 = S * 0.0058 * (1 - 0.62 * t0 / 1.18) + S * 0.0008; r1 = S * 0.0058 * (1 - 0.62 * t1 / 1.18) + S * 0.0008
            pr.tube(U(lev_rib(p, Lr, t0)), U(lev_rib(p, Lr, t1)), r0, r1, lev_bone(i, (t0 + t1) / 2), rings=1, segs=6, cap=False, tip_from=t0 / 1.18)
            if j % 3 == 2: pk.sphere(U(lev_rib(p, Lr, t1)), r1 * 1.55, lev_bone(i, t1), scale=(1, 1, 0.8), sub=1)
            if j % 4 == 1 and t1 < 1.0: pl.sphere(U(lev_rib(p, Lr, t1)) + Vector((0, 0, -r1 * 1.1)), r1 * 0.55, lev_bone(i, t1), sub=1)
    parts += [pr.finish(), pk.finish(), pl.finish()]
    # ---- membrane: scalloped between ribs, billowing slightly down, double-sided
    pm = Part("canopy", 5); R = 9; C = 5
    for i in range(nr - 1):
        rows = []
        for j in range(R + 1):
            row = []
            for m in range(C + 1):
                u = m / C; te = 1.0 - 0.17 * math.sin(math.pi * u) ** 0.9
                t = 0.04 + (te - 0.04) * j / R
                pa = lev_rib(phis[i], Lrs[i], t); pb = lev_rib(phis[i + 1], Lrs[i + 1], t)
                co = pa.lerp(pb, u) + Vector((0, 0, -(Lrs[i] + Lrs[i + 1]) * 0.5 * 0.05 * math.sin(math.pi * u) * math.sin(math.pi * t / te)))
                row.append((U(co), [(lev_bone(i, t), 1 - u), (lev_bone(i + 1, t), u)], t))
            rows.append(row)
        pm.grid(rows, thickness=S * 0.0006)
    parts.append(pm.finish())
    # ---- fringe: ragged strands hanging from the rib tips and the scallops
    pf = Part("fringe", 5)
    def strand(top, w, L, back=0.35):
        pts = [top + U(Vector((0, -L * back * (k / 4) ** 1.5, -L * k / 4))) for k in range(5)]
        th = S * (0.0012 + 0.006 * L)
        for k in range(4): pf.tube(pts[k], pts[k + 1], th * (1 - k / 5), th * (1 - (k + 1) / 5) + S * 0.0002, w, rings=2 if L > 0.1 else 1, segs=4, cap=False, tip_from=k / 4)
    for i, (p, Lr) in enumerate(zip(phis, Lrs)):
        strand(U(lev_rib(p, Lr, 1.18)), [("r%d_2" % i, 1.0)], random.uniform(0.04, 0.08))
        for tt in SP.get("ribStreamers", (0.35, 0.6, 0.85)):     # long streamers hanging from under the wing
            tt += random.uniform(-0.05, 0.05)
            strand(U(lev_rib(p, Lr, tt)) + Vector((0, 0, -S * 0.004)), [(lev_bone(i, tt), 1.0)], random.uniform(0.12, 0.3) * (1.1 - 0.4 * tt), back=0.5)
        if i < nr - 1:
            for uu in (0.35, 0.65):
                te = 1.0 - 0.17 * math.sin(math.pi * uu) ** 0.9
                top = lev_rib(phis[i], Lrs[i], te).lerp(lev_rib(phis[i + 1], Lrs[i + 1], te), uu)
                strand(U(top), [("r%d_2" % i, 1 - uu), ("r%d_2" % (i + 1), uu)], random.uniform(0.05, 0.11))
    parts.append(pf.finish())
    # ---- filter comb: a skirt of fine baleen strands round the throat, sieving bacteria out of the air
    pc = Part("comb", 4)
    for k in range(SP.get("combN", 70)):
        a = k / SP.get("combN", 70) * math.tau
        org = U((0, 0.04, 0.02)); d = Vector((math.cos(a), math.sin(a) * 0.7, -0.35)).normalized()
        loc, nn = ray(bvh, org + d * S * 0.3, -d)
        if loc is None: continue
        L = S * random.uniform(0.02, 0.035)
        pc.cone(loc, (nn * 0.3 + Vector((0, 0, -1))).normalized(), L, S * 0.0025, "body", 4, bend=(0, -0.3, 0))
    parts.append(pc.finish())
    # ---- tentacles
    pt = Part("tentacles", 0); pb = Part("suckers", 6)
    per = SP.get("perCluster", 4)
    for c, (base, cpts) in enumerate(clusters):
        for q in range(per):
            ang = q / per * math.tau + c
            off = Vector((math.cos(ang), math.sin(ang), 0)) * random.uniform(0.004, 0.014)
            Lq = random.uniform(0.55, 1.0); NR = 22; prev = None
            loc, n = ray(bvh, U(base + off + Vector((0, 0, 0.2))), (0, 0, -1))
            top = loc if loc else U(base + off)
            curl = random.uniform(-0.03, 0.03)
            for kk in range(NR + 1):
                t = kk / NR * Lq; seg_ = min(3, int(t * 4)); f = t * 4 - seg_
                c3 = top + U(Vector((0, -TL * 0.34 * t ** 1.4, -TL * t)) + (cpts[4] - cpts[0] - Vector((0, -TL * 0.34, -TL))) * t ** 1.2
                             + off * (1 + 3 * t) + Vector((curl * math.sin(t * 9), curl * math.cos(t * 7), 0)))
                rr = S * (0.0055 * (1 - 0.85 * t / Lq) + 0.0005)
                w = [("c%d_%d" % (c, seg_), 1 - 0.5 * max(0, f - 0.5)), ("c%d_%d" % (c, min(3, seg_ + 1)), 0.5 * max(0, f - 0.5))] if seg_ < 3 else [("c%d_3" % c, 1.0)]
                if kk == 0: w = [("body", 1.0)]
                cur = [pt.v(c3 + Vector((math.cos(j / 6 * math.tau) * rr, math.sin(j / 6 * math.tau) * rr, 0)), w, t) for j in range(6)]
                if prev:
                    for j in range(6): pt.f([prev[j], prev[(j + 1) % 6], cur[(j + 1) % 6], cur[j]])
                prev = cur
                if kk % 3 == 2 and t < 0.6: pb.sphere(c3 + Vector((0, rr * 0.9, 0)), rr * 0.45, w, sub=1)
    parts += [pt.finish(), pb.finish()]
    # ---- eyes: a row of small dark eyes along the head
    pe = Part("eyes", 3)
    for sx in (1, -1):
        for k in range(3):
            loc, n = ray(bvh, U((sx * 0.3, 0.12 - 0.02 * k, 0.05)), (-sx, 0, 0))
            if loc: pe.sphere(loc, S * 0.004, "head", sub=1)
    parts.append(pe.finish())
    return body, rig, parts, dict(nr=nr, nc=nc, phis=phis), mode

def build_lev_pupa():
    sk = Skel(S)
    sk.v("sac", 0, 0, 0.05, 0.34, 0.3)
    for k in range(6):
        y = 0.36 - 0.72 * k / 5
        sk.v("g%d" % k, 0, y, -0.24 + 0.06 * (y / 0.36) ** 2, 0.11 + 0.012 * (k % 2), 0.1)
    sk.e("g0", "g1", "g2", "g3", "g4", "g5"); sk.e("sac", "g2"); sk.e("sac", "g3")
    body = metaball_body(NAME, sk, voxel=S * 0.008, faces=SP.get("faces", 5000), floor=False, mb_scale=1.15, stiffness=2.0)
    tag_body(body, 0)
    bones = [("body", (0, -0.2, -0.22), (0, 0.2, -0.22), None, False), ("sac", (0, 0, 0.05), (0, 0, 0.42), "body", False)]
    nr = 9; betas = [math.radians(-75 + 150 * i / (nr - 1)) for i in range(nr)]
    def rp(beta, t):    # rib crumpled over the sac: from the front-top over and down the back
        al = math.radians(28 + 118 * t)
        return Vector((0.43 * math.sin(al) * math.sin(beta), 0.43 * math.cos(al), 0.05 + 0.4 * math.sin(al) * math.cos(beta)))
    for i, b in enumerate(betas): bones.append(("r%d_0" % i, tuple(rp(b, 0)), tuple(rp(b, 1)), "sac", False))
    nb = 9
    for k in range(nb):
        y = 0.3 - 0.6 * k / (nb - 1); x = 0.06 * (1 if k % 2 else -1)
        bones.append(("b%d" % k, (x, y, -0.3), (x * 2, y - 0.05, -0.62), "body", False))
    nd = tuple(b[0] for b in bones if b[0].startswith(("r", "b")) and b[0] != "body")
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd)
    parts = []
    pr = Part("ribs", 2); pm = Part("canopy", 5)
    for i, b in enumerate(betas):
        for j in range(10):
            t0, t1 = j / 10, (j + 1) / 10
            pr.tube(U(rp(b, t0)), U(rp(b, t1)), S * 0.016 * (1 - 0.5 * t0), S * 0.016 * (1 - 0.5 * t1), "r%d_0" % i, rings=1, segs=6, cap=False, tip_from=t0)
    for i in range(nr - 1):
        rows = []
        for j in range(7):
            row = []
            for m in range(5):
                u = m / 4; t = 0.03 + 0.9 * j / 6
                co = rp(betas[i], t).lerp(rp(betas[i + 1], t), u)
                crumple = 0.025 * math.sin(math.pi * u) * (1 + noise.noise(co * 14.0))
                co = co + co.normalized() * crumple
                row.append((U(co), [("r%d_0" % i, 1 - u), ("r%d_0" % (i + 1), u)], t))
            rows.append(row)
        pm.grid(rows, thickness=S * 0.002)
    parts += [pr.finish(), pm.finish()]
    pt = Part("buds", 0)
    for k in range(nb):
        y = 0.3 - 0.6 * k / (nb - 1); x = 0.06 * (1 if k % 2 else -1)
        pt.cone(U((x, y, -0.28)), (x * 2, -0.12, -1), S * random.uniform(0.28, 0.42), S * 0.035, "b%d" % k, 6, bend=(0, -0.3, 0))
    pg = Part("spots", 6)
    for k in range(26):
        a = random.uniform(0, math.tau); el = random.uniform(-0.2, 1.0)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        pg.sphere(U(Vector((0, 0, 0.05)) + Vector((d.x * 0.4, d.y * 0.4, d.z * 0.36))), S * 0.012, "sac", sub=1)
    parts += [pt.finish(), pg.finish()]
    return body, rig, parts, dict(nr=nr, nb=nb), mode

def build_lev_larva():
    sk = Skel(S); n = 11
    for k in range(n):
        y = 0.42 - 0.84 * k / (n - 1)
        sk.v("s%d" % k, 0, y, 0.11 + 0.05 * (y / 0.42) ** 2, 0.12 if k % 2 == 0 else 0.105, 0.105 if k % 2 == 0 else 0.095)
    sk.v("head", 0, 0.5, 0.12, 0.075, 0.07)
    sk.e("head", *["s%d" % k for k in range(n)])
    body = metaball_body(NAME, sk, voxel=S * 0.008, faces=SP.get("faces", 3500), floor=True, mb_scale=1.12, stiffness=2.4)
    tag_body(body, 0)
    bones = [("body", (0, -0.1, 0.11), (0, 0.1, 0.11), None, False), ("front", (0, 0.1, 0.11), (0, 0.42, 0.12), "body", True),
             ("head", (0, 0.42, 0.12), (0, 0.56, 0.12), "front", True), ("back", (0, -0.1, 0.11), (0, -0.42, 0.13), "body", False)]
    rig = make_rig(NAME, sk, bones); mode = skin(body, rig)
    bvh = bvh_of(body); parts = []
    ph = Part("headshell", 1)
    ph.sphere(U((0, 0.53, 0.13)), S * 0.07, "head", scale=(1.0, 0.8, 0.85), sub=2)
    parts.append(ph.finish())
    pc = Part("comb", 2)
    for k in range(10):
        a = math.radians(-70 + 140 * k / 9)
        pc.cone(U((math.sin(a) * 0.05, 0.585, 0.11 + 0.04 * math.cos(a))), (math.sin(a) * 0.6, 1, -0.3), S * 0.06, S * 0.008, "head", 4, bend=(0, 0, -0.4))
    parts.append(pc.finish())
    pl = Part("prolegs", 0); pg = Part("glowspots", 6)
    for k in range(2, n - 1):
        y = 0.42 - 0.84 * k / (n - 1); bn = "front" if y > 0.1 else ("back" if y < -0.1 else "body")
        for sx in (1, -1):
            pl.cone(U((sx * 0.07, y, 0.06)), (sx * 0.4, 0, -1), S * 0.06, S * 0.025, bn, 5)
            loc, nn = ray(bvh, U((sx * 0.5, y, 0.14)), (-sx, 0, 0))
            if loc: pg.sphere(loc, S * 0.016, bn, sub=1)
    parts += [pl.finish(), pg.finish()]
    return body, rig, parts, dict(), mode

def anim_skylev(A, info):
    form = SP.get("form", "adult")
    if form == "adult":
        nr, nc, phis = info["nr"], info["nc"], info["phis"]
        def wave(amp, trail, sway):
            def fn(t):
                P = {}; w = 2 * math.pi * t
                P["body"] = A.rot("body", up=1.0 * math.sin(w), roll=0.8 * math.sin(w + 1))
                P["head"] = A.rot("head", up=2.5 * math.sin(w + 0.6), yaw=2 * math.sin(w))
                P["tailb"] = A.rot("tailb", up=-3 * math.sin(w - 0.8))
                for i in range(nr):
                    ax = (-math.cos(phis[i]), -math.sin(phis[i]), 0)
                    for k in range(3):
                        ang = amp * (0.5 + 0.5 * k) * math.sin(w - 1.1 * k - 0.22 * abs(i - (nr - 1) / 2))
                        P["r%d_%d" % (i, k)] = rotaxis(A, "r%d_%d" % (i, k), ax, ang)
                for c in range(nc):
                    for k in range(4):
                        b = "c%d_%d" % (c, k)
                        P[b] = qmul(rotaxis(A, b, (1, 0, 0), trail * (0.6 if k == 0 else 0.25) + sway * math.sin(w + c * 0.9 - k * 0.7)),
                                    rotaxis(A, b, (0, 1, 0), sway * 0.6 * math.sin(w * (1 if c % 2 else 2) + c * 1.7 - k * 0.5)))
                return P, (0, 0, 0)
            return fn
        return ([("idle", wave(4, 0, 2), SP.get("idleFrames", 900), 6, False), ("move", wave(7, -5, 3), SP.get("moveFrames", 900), 6, False)],
                dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="idle", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))
    if form == "pupa":
        nr, nb = info["nr"], info["nb"]
        def breathe(amp):
            def fn(t):
                P = {}; w = 2 * math.pi * t
                P["sac"] = (A.rot("sac", up=0), 1.0 + amp * math.sin(w))
                P["body"] = A.rot("body", yaw=4 * math.sin(w * 2), up=3 * math.sin(w))
                for i in range(nr): P["r%d_0" % i] = A.rot("r%d_0" % i, up=3 * math.sin(w * 2 + i * 0.8))
                for k in range(nb): P["b%d" % k] = A.rot("b%d" % k, fwd=10 * math.sin(w + k * 0.9), yaw=6 * math.sin(w * 2 + k))
                return P, (0, 0, 0)
            return fn
        return ([("idle", breathe(0.04), 240, 4, False), ("move", breathe(0.06), 180, 4, False)],
                dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="move", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))
    def writhe(amp, sp_, lift):
        def fn(t):
            P = {}; w = 2 * math.pi * t
            P["body"] = A.rot("body", yaw=amp * 0.4 * math.sin(w), up=lift * math.sin(w * 2))
            P["front"] = A.rot("front", yaw=amp * math.sin(w + 0.9), up=lift * math.sin(w * 2 + 1.2))
            P["head"] = A.rot("head", yaw=amp * 0.6 * math.sin(w + 1.6), up=6 * math.sin(w * 3))
            P["back"] = A.rot("back", yaw=-amp * math.sin(w - 0.9), up=lift * math.sin(w * 2 - 1.2))
            return P, (0, 0, 0)
        return fn
    return ([("idle", writhe(8, 1, 3), 150, 3, False), ("move", writhe(14, 1, 8), 60, 2, False)],
            dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="idle", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["fleeSpeed"]))

BUILD["skylev"] = (build_skylev, anim_skylev)

# =============================================================================== TIDEWALKER (Laythe): a colossal, many-eyed cephalopod
# that stands and strides on eight thick tentacles. Origin on the ground between the feet; head ~0.8 S up.
def catmull(pts, n):
    """n+1 samples along a Catmull-Rom curve through pts (Vectors)."""
    P = [pts[0] + (pts[0] - pts[1])] + list(pts) + [pts[-1] + (pts[-1] - pts[-2])]
    segs = len(pts) - 1; out = []
    for i in range(n + 1):
        u = i / n * segs; k = min(segs - 1, int(u)); t = u - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    return out

def tentacle(part, pts, bones, r0, r1, NR=24, segs=8, root="head", suckers=None, inward=None):
    """pts: unit-space control points (one per bone joint); bones: names of the bones between them."""
    C = catmull([U(p) for p in pts], NR); n = len(bones); prev = None
    T = [(C[min(i + 1, NR)] - C[max(i - 1, 0)]).normalized() for i in range(NR + 1)]
    x, y, _ = basis_z(T[0])
    for i in range(NR + 1):
        t = i / NR
        y = (y - T[i] * y.dot(T[i])).normalized(); x = y.cross(T[i])
        s = min(n - 1, int(t * n)); f = t * n - s
        w = [(bones[s], 1 - max(0, f - 0.5)), (bones[min(n - 1, s + 1)], max(0, f - 0.5))]
        if i == 0: w = [(root, 1.0)]
        rr = (r0 + (r1 - r0) * t ** 0.8) * S
        ring = [part.v(C[i] + (x * math.cos(j / segs * math.tau) + y * math.sin(j / segs * math.tau)) * rr, w, t) for j in range(segs)]
        if prev:
            for j in range(segs): part.f([prev[j], prev[(j + 1) % segs], ring[(j + 1) % segs], ring[j]])
        prev = ring
        if suckers is not None and inward is not None and i % 2 == 1 and 0.15 < t < 0.95:
            d = Vector(inward) - T[i] * Vector(inward).dot(T[i])
            if d.length > 1e-6: suckers.sphere(C[i] + d.normalized() * rr * 0.9, rr * 0.32, w, scale=(1, 1, 1), sub=1)

def basis_z(z):
    z = Vector(z).normalized(); ref = Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((1, 0, 0))
    y = (ref - z * ref.dot(z)).normalized(); x = y.cross(z)
    return x, y, z

def build_colossus():
    sk = Skel(S)
    for nm, x, y, z, rs, rv in (("crown", 0, -0.02, 0.87, 0.15, 0.13), ("brow", 0, 0.09, 0.81, 0.13, 0.11), ("cheekL", 0.085, 0.06, 0.745, 0.08, 0.08),
                                ("cheekR", -0.085, 0.06, 0.745, 0.08, 0.08), ("under", 0, 0.0, 0.705, 0.12, 0.08), ("nape", 0, -0.13, 0.82, 0.1, 0.1),
                                ("snout", 0, 0.23, 0.79, 0.065, 0.06), ("snoutTip", 0, 0.37, 0.74, 0.035, 0.032), ("snoutEnd", 0, 0.46, 0.67, 0.014, 0.014)):
        hk = SP.get("headScale", 1.0) if nm in ("crown", "brow", "cheekL", "cheekR", "nape") else 1.0
        sk.v(nm, x, y, z, rs * hk, rv * hk)
    sk.e("nape", "crown", "brow", "snout", "snoutTip", "snoutEnd"); sk.e("crown", "under"); sk.e("brow", "cheekL"); sk.e("brow", "cheekR")
    sk.e("under", "cheekL"); sk.e("under", "cheekR")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.006), faces=SP.get("faces", 7000), floor=False, mb_scale=1.15, stiffness=2.0)
    def wrinkle(co, n):
        u = co / S
        d = 0.007 * (1 - abs(noise.noise(u * 9.0))) ** 4 - 0.003 * (1 - abs(noise.noise(u * 22.0 + Vector((3, 1, 2))))) ** 3 + noise.noise(u * 30.0) * 0.0015
        co += n * S * d
        return co
    displace(body, wrinkle)
    tag_body(body, 0)
    bones = [("body", (0, 0, 0.55), (0, 0, 0.71), None, False), ("head", (0, 0, 0.71), (0, 0.02, 0.96), "body", True),
             ("snout1", (0, 0.18, 0.8), (0, 0.32, 0.76), "head", False), ("snout2", (0, 0.32, 0.76), (0, 0.47, 0.66), "snout1", True)]
    legs = []; NL = SP.get("legs", 8)
    for k in range(NL):
        a = k / NL * math.tau + math.pi / NL; c, s_ = math.cos(a), math.sin(a)
        tg = Vector((-s_, c, 0)) * (1 if k % 2 else -1)
        pts = [Vector((c * 0.07, s_ * 0.07, 0.68)), Vector((c * 0.18, s_ * 0.18, 0.62)) + tg * 0.02, Vector((c * 0.26, s_ * 0.26, 0.42)) + tg * 0.045,
               Vector((c * 0.33, s_ * 0.33, 0.2)) - tg * 0.03, Vector((c * 0.35, s_ * 0.35, 0.0))]
        nm = ["L%d_%d" % (k, j) for j in range(4)]
        for j in range(4): bones.append((nm[j], tuple(pts[j]), tuple(pts[j + 1]), "body" if j == 0 else nm[j - 1], j > 0))
        legs.append((a, pts, nm))
    feeders = []; NF = SP.get("feeders", 14)
    for k in range(NF):
        a = k / NF * math.tau + 0.2; c, s_ = math.cos(a), math.sin(a); r = 0.035 + 0.02 * (k % 2)
        end = random.uniform(0.04, 0.3); cu = random.uniform(-0.06, 0.06)
        pts = [Vector((c * r, s_ * r, 0.67)), Vector((c * (r + 0.03) + cu * s_, s_ * (r + 0.03) - cu * c, 0.52)),
               Vector((c * (r + 0.05) - cu * s_ * 1.5, s_ * (r + 0.05) + cu * c * 1.5, (0.52 + end) / 2)), Vector((c * (r + 0.04) + cu * s_ * 2, s_ * (r + 0.04) - cu * c * 2, end))]
        nm = ["F%d_%d" % (k, j) for j in range(3)]
        for j in range(3): bones.append((nm[j], tuple(pts[j]), tuple(pts[j + 1]), "body" if j == 0 else nm[j - 1], j > 0))
        feeders.append((a, pts, nm))
    arms = []
    for sx, side in ((1, "L"), (-1, "R")):
        pts = [Vector((sx * 0.09, 0.05, 0.7)), Vector((sx * 0.2, 0.13, 0.79)), Vector((sx * 0.32, 0.21, 0.86)), Vector((sx * 0.43, 0.23, 0.81)), Vector((sx * 0.48, 0.19, 0.7))]
        nm = ["A%s_%d" % (side, j) for j in range(4)]
        for j in range(4): bones.append((nm[j], tuple(pts[j]), tuple(pts[j + 1]), "body" if j == 0 else nm[j - 1], j > 0))
        arms.append((sx, pts, nm))
    nd = tuple(b[0] for b in bones if b[0][0] in "LFA" and "_" in b[0])
    rig = make_rig(NAME, sk, bones, nondeform=nd); mode = skin(body, rig, nondeform=nd)
    bvh = bvh_of(body); parts = []
    pt = Part("tentacles", 0); ps = Part("suckers", 2)
    for a, pts, nm in legs:
        tentacle(pt, pts, nm, SP.get("legR", 0.05), 0.012, NR=28, segs=10, root="body", suckers=ps, inward=(-math.cos(a), -math.sin(a), 0))
        ps.sphere(U(pts[-1]) + Vector((0, 0, S * 0.006)), S * 0.016, nm[-1], scale=(1, 1, 0.5), sub=2)      # flattened foot pad
    for a, pts, nm in feeders: tentacle(pt, pts, nm, 0.022, 0.003, NR=22, segs=7, root="body")
    for sx, pts, nm in arms: tentacle(pt, pts, nm, 0.032, 0.004, NR=26, segs=8, root="body", suckers=ps, inward=(0, 0, -1))
    parts += [pt.finish(), ps.finish()]
    # ---- eyes: a crowded scatter of sunken, rimmed eyes with ember irises across the brow and sides
    pr = Part("sockets", 0); pe = Part("eyes", 3); pi = Part("irises", 6)
    placed = []
    for k in range(SP.get("eyes", 16) * 6):
        if len(placed) >= SP.get("eyes", 16): break
        az = random.uniform(-1.9, 1.9); el = random.uniform(-0.15, 0.75)
        d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
        org = U((0, 0.06, 0.8))
        loc, n = ray(bvh, org + d * S * 0.5, -d)
        if loc is None or any((loc - q).length < S * 0.05 for q in placed): continue
        r = S * random.uniform(0.011, 0.022)
        if loc.y < S * 0.0 and abs(loc.x) < S * 0.08: continue
        placed.append(loc)
        bn = "snout1" if loc.y > S * 0.2 else "head"
        pr.sphere(loc - n * r * 0.25, r * 1.3, bn, sub=2)                 # swollen lid ring, mostly sunk into the skin
        pe.sphere(loc + n * r * 0.5, r * 0.92, bn, sub=2)                 # glossy black eyeball bulging out of it
        pi.sphere(loc + n * r * 1.28, r * 0.5, bn, sub=1)                 # ember iris
    parts += [pr.finish(), pe.finish(), pi.finish()]
    # ---- bony ridges raking back over the crown, and knobs along the snout
    pb = Part("ridges", 1)
    for lane in (-0.07, 0.0, 0.07):
        for k in range(9):
            y = 0.16 - 0.035 * k
            loc, n = ray(bvh, U((lane, y, 1.2)), (0, 0, -1))
            if loc is None: continue
            pb.sphere(loc, S * (0.014 - 0.0008 * k), "head", scale=(0.6, 1.6, 0.45), sub=1)
    for k in range(8):
        y = 0.22 + 0.03 * k
        loc, n = ray(bvh, U((0, y, 1.2)), (0, 0, -1))
        if loc is not None: pb.sphere(loc, S * 0.008, "snout1" if y < 0.32 else "snout2", scale=(1, 1, 0.6), sub=1)
    parts.append(pb.finish())
    return body, rig, parts, dict(legs=[(a, nm) for a, _, nm in legs], feeders=[(a, nm) for a, _, nm in feeders], arms=[(sx, nm) for sx, _, nm in arms]), mode

def anim_colossus(A, info):
    legs, feeders, arms = info["legs"], info["feeders"], info["arms"]
    def sway(P, w, amp):
        for k, (a, nm) in enumerate(feeders):
            for j, b in enumerate(nm):
                P[b] = qmul(rotaxis(A, b, (1, 0, 0), amp * math.sin(w + k * 0.9 - j * 0.8)), rotaxis(A, b, (0, 1, 0), amp * 0.7 * math.sin(w * 2 + k * 1.7 - j * 0.6)))
        for sx, nm in arms:
            for j, b in enumerate(nm):
                P[b] = qmul(rotaxis(A, b, (0, 1, 0), sx * amp * 0.9 * math.sin(w + j * 0.7 + (0 if sx > 0 else 2))), rotaxis(A, b, (1, 0, 0), amp * 0.6 * math.sin(w * 2 - j)))
        P["snout1"] = A.rot("snout1", up=4 * math.sin(w + 0.5), yaw=5 * math.sin(w * 0.5)); P["snout2"] = A.rot("snout2", up=7 * math.sin(w + 1.2), yaw=8 * math.sin(w * 0.5 + 0.7))
    def idle(t):
        P = {}; w = 2 * math.pi * t
        sway(P, w, 6)
        P["head"] = A.rot("head", yaw=3 * math.sin(w), up=2 * math.sin(w * 2))
        for k, (a, nm) in enumerate(legs):
            P[nm[0]] = rotaxis(A, nm[0], (-math.sin(a), math.cos(a), 0), 1.2 * math.sin(w + k))
        return P, (0, 0, 0.004 * S * math.sin(w * 2))
    def gait(stride, lift):
        def fn(t):
            P = {}; w = 2 * math.pi * t
            sway(P, w * 2, 8)
            P["head"] = A.rot("head", yaw=2 * math.sin(w), up=2 * math.sin(w * 2), roll=2 * math.sin(w))
            for k, (a, nm) in enumerate(legs):
                ph = w + (math.pi if k % 2 else 0.0) + k * 0.25
                up_ = max(0.0, math.sin(ph)); tang = (-math.sin(a), math.cos(a), 0)
                P[nm[0]] = qmul(rotaxis(A, nm[0], (1, 0, 0), -stride * math.cos(ph)), rotaxis(A, nm[0], tang, lift * up_))
                P[nm[1]] = rotaxis(A, nm[1], tang, -lift * 0.6 * up_)
                P[nm[2]] = rotaxis(A, nm[2], tang, -lift * 0.5 * up_)
            return P, (0, 0, 0.006 * S * abs(math.sin(w * 2)))
        return fn
    def roar(t):
        P = {}; w = 2 * math.pi * t; e = math.sin(math.pi * t) ** 0.6
        sway(P, w * 3, 10)
        P["head"] = A.rot("head", up=14 * e)
        P["snout1"] = A.rot("snout1", up=18 * e); P["snout2"] = A.rot("snout2", up=24 * e)
        for sx, nm in arms:
            for j, b in enumerate(nm): P[b] = rotaxis(A, b, (0, 1, 0), sx * (-25 if j < 2 else -10) * e)
        return P, (0, 0, 0.01 * S * e)
    return ([("idle", idle, 360, 4, False), ("walk", gait(9, 14), 300, 3, False), ("roar", roar, 150, 3, True)],
            dict(idleAnim="idle", moveAnim="walk", fleeAnim="walk", alertAnim="idle", roarAnim="roar", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["speed"]))

BUILD["colossus"] = (build_colossus, anim_colossus)
