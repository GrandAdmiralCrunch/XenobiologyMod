# Xenobiology — archetype generator for the "everyday" fauna (replaces the procedural placeholders).
# One run builds one species:  VARIANT = "glimmerback"  (see SPECIES below), STEP = "model" | "all".
# Archetypes: quad, hex, serpent, avian, fish, floater, blob. All sizes are in units of the creature's
# length (or height for floaters) and scaled by `size` metres, so the .mu is authored at real size.
import bpy, os, math, random
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
exec(open(os.path.join(TOOLS, "fauna_species.py"), encoding="utf-8").read(), globals())

VARIANT = globals().get("VARIANT", "glimmerback")
STEP = globals().get("STEP", "all")
SP = dict(SPECIES[VARIANT]); SP.setdefault("feats", [])
NAME = VARIANT
S = SP["size"]
FE = SP["feats"]
random.seed(sum(ord(c) * (i + 1) for i, c in enumerate(NAME)))
new_scene("Fauna_" + NAME)
OUT_DIR = os.path.join(XENO_DIR, "Models", SP["world"], NAME[0].upper() + NAME[1:])
result = {"species": NAME}

def V(*a): return Vector(a)
def U(v): return Vector(v) * S                  # unit -> metres
def eyes_on(bvh, p, centre, r, n=2, spread=0.55, up=0.25, fwd=0.6, bone="head", pid=3):
    """Ray-cast eyes onto a head: n eyes spread around the front/sides."""
    c = U(centre); placed = []
    for k in range(n):
        if n == 1: ang = 0.0
        else: ang = (k / (n - 1) - 0.5) * 2 * spread * math.pi
        d = Vector((math.sin(ang), math.cos(ang) * fwd + 0.15, up)).normalized()
        if n > 2 and k % 2: d.z += 0.25
        loc, nrm = ray(bvh, c + d * S * 2, -d)
        if loc is None: continue
        p.sphere(loc - nrm * r * 0.35, r, bone, sub=2); placed.append(loc)
    return placed

# =============================================================================== QUADRUPED
def build_quad():
    legH, W, Rv = SP["legH"], SP["W"], SP["Rv"]
    B = SP.get("B", 0.38); neck = SP.get("neck", 0.2); nup = SP.get("neckUp", 0.8); hr = SP["headR"]; tail = SP.get("tail", 0.25)
    zb = legH + Rv * 0.35
    sk = Skel(S)
    sk.v("pelvis", 0, -B / 2, zb, W * 0.48, Rv)
    sk.v("belly", 0, 0, zb - 0.01, W * 0.52, Rv * 1.08)
    sk.v("chest", 0, B / 2, zb + 0.01, W * 0.5, Rv * 1.02)
    if SP.get("hump"):      # bison: a high muscular hump over the shoulders
        sk.v("hump", 0, B * 0.3, zb + Rv * SP["hump"], W * 0.36, Rv * 0.75); sk.e("belly", "hump", "chest")
    ntop = V(0, B / 2 + neck * math.cos(nup), zb + neck * math.sin(nup))
    sk.v("necktop", *ntop, SP.get("neckR", W * 0.2))
    hc = ntop + V(0, hr * 0.7, hr * 0.15)
    sk.v("head", *hc, hr * SP.get("headW", 0.85), hr)
    sn = hc + V(0, hr * SP.get("snoutL", 1.3), -hr * 0.4)
    sk.v("snout", *sn, hr * 0.5, hr * 0.45)
    t1 = V(0, -B / 2 - tail * 0.35, zb + SP.get("tailUp", -0.02)); t2 = V(0, -B / 2 - tail * 0.7, zb - 0.04 + SP.get("tailUp", 0)); t3 = V(0, -B / 2 - tail, zb - 0.07 + SP.get("tailUp", 0) * 1.5)
    tr = SP.get("tailR", W * 0.12)
    sk.v("t1", *t1, tr); sk.v("t2", *t2, tr * 0.7); sk.v("t3", *t3, tr * SP.get("tailTip", 0.35))
    sk.e("pelvis", "belly", "chest", "necktop", "head", "snout"); sk.e("pelvis", "t1", "t2", "t3")
    lr = SP.get("legR", W * 0.11); x = W * 0.3
    for s, sx in (("L", 1), ("R", -1)):
        sk.v("sh" + s, sx * x, B / 2 - 0.01, zb - Rv * 0.35, lr * 1.5)
        sk.v("el" + s, sx * x, B / 2 + 0.015, legH * 0.55, lr)
        sk.v("wr" + s, sx * x, B / 2, legH * 0.13, lr * 0.75)
        sk.v("tf" + s, sx * x, B / 2 + 0.035, 0.0, lr * 0.85, lr * 0.45)
        sk.v("hp" + s, sx * x, -B / 2 + 0.02, zb - Rv * 0.3, lr * 1.7)
        sk.v("kn" + s, sx * x, -B / 2 + 0.07, legH * 0.58, lr * 1.05)
        sk.v("hk" + s, sx * x, -B / 2 - 0.04, legH * 0.2, lr * 0.75)
        sk.v("th" + s, sx * x, -B / 2 - 0.005, 0.0, lr * 0.85, lr * 0.45)
        sk.e("chest", "sh" + s, "el" + s, "wr" + s, "tf" + s); sk.e("pelvis", "hp" + s, "kn" + s, "hk" + s, "th" + s)
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.007), faces=SP.get("faces", 5000))
    bones = [("body", "pelvis", "belly", None, False), ("spine", "belly", "chest", "body", True), ("neck", "chest", "necktop", "spine", True),
             ("head", "necktop", "snout", "neck", True), ("tail1", "pelvis", "t1", "body", False), ("tail2", "t1", "t2", "tail1", True), ("tail3", "t2", "t3", "tail2", True)]
    for s in "LR":
        bones += [("upF" + s, "sh" + s, "el" + s, "spine", False), ("loF" + s, "el" + s, "wr" + s, "upF" + s, True), ("ftF" + s, "wr" + s, "tf" + s, "loF" + s, True),
                  ("upH" + s, "hp" + s, "kn" + s, "body", False), ("loH" + s, "kn" + s, "hk" + s, "upH" + s, True), ("ftH" + s, "hk" + s, "th" + s, "loH" + s, True)]
    rig = make_rig(NAME, sk, bones); mode = skin(body, rig); bvh = bvh_of(body); parts = []
    p = Part("eyes", 3); eyes_on(bvh, p, hc, hr * S * 0.2, SP.get("eyes", 2), spread=0.42, up=0.3, fwd=0.45); parts.append(p.finish())
    hcw = U(hc)
    # ---- species features
    if "scales" in FE:      # glimmerback: overlapping mirror scales down the back
        p = Part("scales", 1)
        for i in range(30):
            yy = -B / 2 - 0.03 + (B + 0.06) * i / 29
            for sx in (-2, -1, 0, 1, 2):
                d = Vector((sx * 0.35, 0, 1)).normalized()
                loc, n = ray(bvh, U((0, yy, zb)) + d * S, -d)
                if loc is None: continue
                p.sphere(loc - n * S * 0.003, S * 0.018, [("body", 0.5), ("spine", 0.5)] if yy > 0 else "body", scale=(1.0, 1.3, 0.25), sub=1)
        parts.append(p.finish())
    if "horns" in FE:
        p = Part("horns", 2)
        for sx in (1, -1):
            p.cone(hcw + U((sx * hr * 0.45, -hr * 0.1, hr * 0.7)), (sx * 0.3, -0.5, 1.0), S * hr * 1.4, S * hr * 0.16, "head", 6, bend=(0, -0.5, 0))
        parts.append(p.finish())
    if "ears" in FE:
        p = Part("ears", 0)
        for sx in (1, -1):
            p.cone(hcw + U((sx * hr * 0.6, -hr * 0.4, hr * 0.5)), (sx * 0.9, -0.4, 0.5), S * hr * 0.9, S * hr * 0.3, "head", 6, flat=0.35)
        parts.append(p.finish())
    if "plates" in FE:      # rockstrider: big overlapping armour plates
        p = Part("plates", 1)
        for i in range(9):
            yy = -B / 2 - 0.05 + (B + 0.1) * i / 8
            for sx in (-1, 1, 0):
                d = Vector((sx * 0.75, 0, 1)).normalized() if sx else Vector((0, 0, 1))
                loc, n = ray(bvh, U((0, yy, zb)) + d * S, -d)
                if loc is None: continue
                p.sphere(loc + n * S * 0.01, S * (0.07 if sx == 0 else 0.06), "body" if yy < 0 else "spine", scale=(1.0, 1.15, 0.35), sub=2, jitter=0.25)
        loc, n = ray(bvh, hcw + U((0, 0, 1)), (0, 0, -1))
        if loc: p.sphere(loc + n * S * 0.01, S * hr * 0.6, "head", scale=(1.2, 1.4, 0.45), sub=2, jitter=0.3)
        parts.append(p.finish())
    if "fur" in FE:         # snortle: shaggy coat of hanging hair clumps
        p = Part("fur", 4)
        for i in range(SP.get("furN", 260)):
            d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.2, 1))).normalized()
            org = U((0, random.uniform(-B / 2 - 0.05, B / 2 + 0.04), zb))
            loc, n = ray(bvh, org + d * S, -d)
            if loc is None or loc.z < S * legH * 0.75: continue
            if SP.get("furFront") is not None and loc.y < S * B * SP["furFront"]: continue    # bison: shaggy cape on the front half only
            bn = "body" if loc.y < 0 else "spine"
            fl = SP.get("furLen", 1.0)
            p.cone(loc - n * S * 0.01, (n + Vector((0, -0.2, -1.4))).normalized(), S * random.uniform(0.06, 0.12) * fl, S * random.uniform(0.018, 0.03) * max(0.6, fl), bn, 5, bend=(0, -0.2, -0.4))
        for i in range(40):
            d = Vector((random.uniform(-1, 1), random.uniform(-0.3, 1), random.uniform(0, 1))).normalized()
            loc, n = ray(bvh, hcw + d * S, -d)
            if loc is None: continue
            p.cone(loc - n * S * 0.005, (n + Vector((0, 0, -1))).normalized(), S * random.uniform(0.04, 0.08), S * 0.016, "head", 5)
        parts.append(p.finish())
    if "trunknose" in FE:   # snortle: tubular snorkel nose
        p = Part("nose", 0)
        a = U(sn) + U((0, hr * 0.2, 0)); b = a + U((0, hr * 1.2, -hr * 0.9))
        p.tube(a, b, S * hr * 0.28, S * hr * 0.22, "head", rings=4, segs=8)
        p.tube(b, b + U((0, hr * 0.15, -hr * 0.05)), S * hr * 0.26, S * hr * 0.3, "head", rings=1, segs=8)
        parts.append(p.finish())
    if "frill" in FE:       # dunestrider: tall dorsal sail + crest
        p = Part("frill", 5); rows = []
        for j in range(3):
            row = []
            for k in range(9):
                yy = -B / 2 + B * k / 8
                loc, n = ray(bvh, U((0, yy, zb + 1)), (0, 0, -1))
                z0 = loc.z if loc else U((0, 0, zb + Rv)).z
                hgt = S * 0.09 * math.sin(math.pi * (k + 0.5) / 9) * (j / 2)
                row.append((Vector((0, loc.y if loc else yy * S, z0 - S * 0.01 + hgt)), [("body", 1 - k / 8), ("spine", k / 8)], j / 2))
            rows.append(row)
        p.grid(rows, thickness=S * 0.002)
        rows = []
        for j in range(3):
            row = []
            for k in range(5):
                c = hcw + U((0, -hr * 0.6 + hr * 1.0 * k / 4, hr * 0.8))
                row.append((c + U((0, -hr * 0.25 * j, hr * 0.5 * j * (1 - abs(k - 2) / 3))), "head", j / 2))
            rows.append(row)
        p.grid(rows, thickness=S * 0.002)
        parts.append(p.finish())
    if "flippers" not in FE:
        p = Part("hooves", 2)
        for s in "LR":
            for f, bn in (("tf", "ftF"), ("th", "ftH")):
                c = sk.pt(f + s); p.sphere(c + U((0, 0.008, 0.012)), S * lr * 0.95, bn + s, scale=(1.0, 1.3, 0.55), sub=1)
        parts.append(p.finish())
    parts += quad_feats(locals())
    info = dict(Lg=zb * S, zb=zb)
    return body, rig, parts, info, mode

def anim_quad(A, info):
    clips = []; Lg = info["Lg"]; graze = "graze" in FE
    def leg(P, s, fh, u, amp, lift_amt, stance):
        if u < stance: sw = amp * (1 - 2 * u / stance); lift = 0.0
        else: q = (u - stance) / (1 - stance); sw = -amp * math.cos(math.pi * q); lift = math.sin(math.pi * q)
        P["up" + fh + s] = A.rot("up" + fh + s, fwd=sw + (8 if fh == "H" else 4) * lift)
        P["lo" + fh + s] = A.rot("lo" + fh + s, fwd=(-1 if fh == "H" else -1.3) * lift * lift_amt)
        P["ft" + fh + s] = A.rot("ft" + fh + s, fwd=lift * 20 - (sw * 0.3 if u < stance else 0))
    def gait(phases, amp, lift_amt, stance, bob, tailsw):
        def fn(t):
            P = {}
            for (fh, s), ph in phases.items(): leg(P, s, fh, (t + ph) % 1.0, amp, lift_amt, stance)
            P["body"] = A.rot("body", roll=2 * math.sin(2 * math.pi * t))
            P["neck"] = A.rot("neck", up=4 * math.sin(4 * math.pi * t) - (6 if stance < 0.6 else 0))
            P["head"] = A.rot("head", up=-3 * math.sin(4 * math.pi * t))
            for i, b in enumerate(("tail1", "tail2", "tail3")): P[b] = A.rot(b, yaw=tailsw * math.sin(2 * math.pi * t - i * 0.7), up=4 * math.sin(4 * math.pi * t))
            return P, (0, 0, -bob * S * abs(math.sin(2 * math.pi * t)))
        return fn
    amp_w, amp_r = 22.0, 32.0
    sweep_w = 2 * Lg * math.sin(math.radians(amp_w)); sweep_r = 2 * Lg * math.sin(math.radians(amp_r))
    Tw = max(0.4, min(2.5, sweep_w / (0.62 * SP["speed"]))); Tr = max(0.3, min(1.4, sweep_r / (0.45 * SP["fleeSpeed"])))
    fw, fr = int(round(Tw * 30)), int(round(Tr * 30))
    walk = gait({("H", "L"): 0.0, ("F", "L"): 0.25, ("H", "R"): 0.5, ("F", "R"): 0.75}, amp_w, 35, 0.62, 0.006, 6)
    run = gait({("F", "L"): 0.0, ("H", "R"): 0.08, ("F", "R"): 0.5, ("H", "L"): 0.58}, amp_r, 55, 0.45, 0.02, 10)
    def idle(t):
        P = {}; br = math.sin(2 * math.pi * t * 2)
        g = seg(t, 0.1, 0.25) * (1 - seg(t, 0.6, 0.75)) if graze else 0
        P["neck"] = A.rot("neck", up=-45 * g + 2 * br, yaw=12 * math.sin(2 * math.pi * t) * (1 - g))
        P["head"] = A.rot("head", up=-20 * g + 8 * g * math.sin(2 * math.pi * t * 8), yaw=8 * math.sin(2 * math.pi * t + 1))
        for s in "LR": P["upF" + s] = A.rot("upF" + s, fwd=-6 * g)
        for i, b in enumerate(("tail1", "tail2", "tail3")): P[b] = A.rot(b, yaw=8 * math.sin(2 * math.pi * t * 2 - i * 0.8))
        return P, (0, 0, 0.003 * S * br)
    def alert(t):
        P = {}; tw = math.sin(2 * math.pi * t * 3)
        P["neck"] = A.rot("neck", up=18, yaw=20 * math.sin(2 * math.pi * t)); P["head"] = A.rot("head", up=-8 + 3 * tw)
        P["body"] = A.rot("body", up=3)
        for i, b in enumerate(("tail1", "tail2", "tail3")): P[b] = A.rot(b, up=14 - 4 * i)
        return P, (0, 0, 0)
    clips = [("idle", idle, 150, 5, False), ("walk", walk, fw, 1, False), ("run", run, fr, 1, False), ("alert", alert, 90, 3, False)]
    speeds = dict(moveAnimSpeed=round(sweep_w / (0.62 * fw / 30), 2), fleeAnimSpeed=round(sweep_r / (0.45 * fr / 30), 2))
    return clips, dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", **speeds)

# =============================================================================== HEXAPOD
def build_hex():
    W, h, legL, hr = SP["W"], SP["H"], SP["legL"], SP["headR"]
    zb = SP.get("zb", legL * 0.5)
    sk = Skel(S)
    sk.v("head", 0, 0.36, zb + 0.01, hr, hr * 0.8)
    sk.v("thorax", 0, 0.14, zb, W * 0.4, h * 0.85)
    sk.v("waist", 0, -0.02, zb, W * 0.36, h * 0.8)
    sk.v("abdomen", 0, -0.2, zb + 0.01, W * 0.5, h)
    sk.v("tip", 0, -0.4, zb - 0.01, W * 0.22, h * 0.5)
    sk.e("tip", "abdomen", "waist", "thorax", "head")
    lr = SP.get("legR", 0.022)
    for s, sx in (("L", 1), ("R", -1)):
        for i, (yy, ang) in enumerate(((0.2, 0.55), (0.1, 0.0), (0.0, -0.55))):
            c = V(sx * W * 0.28, yy, zb - h * 0.2)
            out = V(sx * math.cos(ang), math.sin(ang), 0)
            knee = c + out * legL * 0.5 + V(0, 0, legL * 0.38)
            foot = c + out * legL * 1.0 + V(0, 0, -c.z)
            lri = lr
            if i == 2 and "jumplegs" in FE:      # springhopper: long, thick-thighed hind legs folded high, knee above the back
                knee = c + V(sx * 0.07, -0.16, legL * 0.75); foot = c + V(sx * 0.11, -0.34, -c.z); lri = lr * 1.6
            foot.z = 0.0
            sk.v("cx%s%d" % (s, i), *c, lri * 1.3); sk.v("kn%s%d" % (s, i), *knee, lri); sk.v("ft%s%d" % (s, i), *foot, lr * 0.55)
            sk.e("thorax", "cx%s%d" % (s, i), "kn%s%d" % (s, i), "ft%s%d" % (s, i))
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.006), faces=SP.get("faces", 4500), stiffness=2.2)
    bones = [("body", "waist", "thorax", None, False), ("head", "thorax", "head", "body", True), ("abdomen", "waist", "tip", "body", False)]
    for s in "LR":
        for i in range(3):
            bones += [("fem%s%d" % (s, i), "cx%s%d" % (s, i), "kn%s%d" % (s, i), "body", False), ("tib%s%d" % (s, i), "kn%s%d" % (s, i), "ft%s%d" % (s, i), "fem%s%d" % (s, i), True)]
    rig = make_rig(NAME, sk, bones); mode = skin(body, rig); bvh = bvh_of(body); parts = []
    hc = V(0, 0.36, zb + 0.01)
    if "eyestalks" in FE:
        p = Part("eyestalks", 0); pe = Part("eyes", 3)
        for sx in (1, -1):
            a = U(hc + V(sx * hr * 0.5, hr * 0.3, hr * 0.5)); b = a + U((sx * hr * 0.25, hr * 0.2, hr * 1.1))
            p.tube(a, b, S * hr * 0.12, S * hr * 0.1, "head", rings=2, segs=6); pe.sphere(b, S * hr * 0.24, "head", sub=2)
        parts += [p.finish(), pe.finish()]
    else:
        p = Part("eyes", 3); eyes_on(bvh, p, hc, hr * S * 0.22, SP.get("eyes", 2), spread=0.3, up=0.35, fwd=0.6); parts.append(p.finish())
    if "carapace" in FE:    # crab-like shell over the whole body
        p = Part("shell", 1)
        p.sphere(U((0, 0.06, zb + h * 0.45)), S * W * 0.62, [("body", 0.6), ("abdomen", 0.4)], scale=(1.0, 0.85, 0.42), sub=3, jitter=0.06)
        parts.append(p.finish())
    if "dome" in FE:        # tidal crawler: rounded, ribbed dome shell
        p = Part("shell", 1)
        p.sphere(U((0, -0.02, zb + h * 0.5)), S * W * 0.6, [("body", 0.5), ("abdomen", 0.5)], scale=(0.95, 1.15, 0.62), sub=3)
        parts.append(p.finish())
    if "elytra" in FE:      # beetle wing cases leaving the glowing abdomen tip exposed
        p = Part("elytra", 1)
        for sx in (1, -1):
            p.sphere(U((sx * W * 0.2, -0.1, zb + h * 0.55)), S * W * 0.33, [("abdomen", 0.7), ("body", 0.3)], scale=(0.75, 1.45, 0.5), sub=3)
        parts.append(p.finish())
        if "nolantern" not in FE:
            p = Part("lantern", 6)
            p.sphere(U((0, -0.36, zb + 0.005)), S * W * 0.26, "abdomen", scale=(1.0, 1.1, 0.8), sub=2)
            parts.append(p.finish())
    if "rhinohorn" in FE:   # ironhorn: a long curved horn on the head and a forked one on the thorax shield
        p = Part("horns", 2)
        p.cone(U(hc + V(0, hr * 0.6, hr * 0.2)), (0, 1.0, 0.25), S * SP.get("hornL", 0.32), S * hr * 0.7, "head", 8, bend=(0, -0.3, 0.55))
        p.cone(U(hc + V(0, hr * 0.5, -hr * 0.2)), (0, 1.0, -0.3), S * 0.06, S * hr * 0.22, "head", 5)
        for sx in (1, -1):
            p.cone(U((sx * W * 0.08, 0.2, zb + h * 0.75)), (sx * 0.25, 1.0, 0.45), S * SP.get("hornL", 0.32) * 0.45, S * hr * 0.2, "body", 6, bend=(-sx * 0.2, 0, 0.3))
        p.sphere(U((0, 0.16, zb + h * 0.45)), S * W * 0.36, "body", scale=(1.0, 0.8, 0.55), sub=3)
        parts.append(p.finish())
    if "tegmina" in FE:     # springhopper: narrow leathery wings folded flat along the back, a little past the tail
        p = Part("tegmina", 5)
        for sx in (1, -1):
            rows = []
            for j in range(3):
                row = []
                for k in range(8):
                    u = k / 7; y = 0.12 - 0.62 * u
                    wdt = W * 0.24 * math.sin(math.pi * (0.15 + 0.7 * u)) ** 0.5
                    row.append((U((sx * (0.01 + wdt * j / 2), y, zb + h * (0.95 - 0.25 * j / 2) - 0.05 * u * 0)), [("body", 1.0)] if y > -0.02 else [("abdomen", 1.0)], u))
                rows.append(row)
            p.grid(rows, flip=sx < 0, thickness=S * 0.002)
        parts.append(p.finish())
    if "mineral" in FE:     # basalt crawler: crystalline plates grown from its diet
        p = Part("plates", 1)
        for i in range(34):
            d = Vector((random.uniform(-1, 1), random.uniform(-0.6, 0.6), random.uniform(0.2, 1))).normalized()
            org = U((0, random.uniform(-0.3, 0.2), zb))
            loc, n = ray(bvh, org + d * S, -d)
            if loc is None: continue
            p.cone(loc - n * S * 0.01, (n + Vector((0, -0.4, 0.3))).normalized(), S * random.uniform(0.05, 0.11), S * random.uniform(0.025, 0.045), "body" if loc.y > -0.02 * S else "abdomen", 5)
        parts.append(p.finish())
    if "claws" in FE or "clackers" in FE:
        p = Part("claws", 2); big = 1.6 if "clackers" in FE else 1.0
        for s, sx in (("L", 1), ("R", -1)):
            f = sk.pt("ft%s0" % s)
            p.sphere(f + U((0, 0.0, legL * 0.12)), S * 0.035 * big, "tib%s0" % s, scale=(0.8, 1.5, 0.7), sub=2)
            p.cone(f + U((sx * 0.01, 0.03, legL * 0.14)), (sx * 0.2, 1.0, 0.1), S * 0.07 * big, S * 0.016 * big, "tib%s0" % s, 5)
            p.cone(f + U((sx * 0.01, 0.03, legL * 0.08)), (sx * 0.2, 1.0, -0.15), S * 0.06 * big, S * 0.013 * big, "tib%s0" % s, 5)
        parts.append(p.finish())
    if "antennae" in FE:
        p = Part("antennae", 2)
        for sx in (1, -1):
            p.cone(U(hc + V(sx * hr * 0.4, hr * 0.6, hr * 0.4)), (sx * 0.5, 1.0, 0.6), S * SP.get("antL", 0.25), S * 0.007, "head", 4, bend=(sx * 0.2, 0, -0.3))
        parts.append(p.finish())
    p = Part("feet", 2)
    for s in "LR":
        for i in range(3): p.cone(sk.pt("ft%s%d" % (s, i)) + U((0, 0, 0.02)), (0, 0, -1), S * 0.025, S * lr * 0.6, "tib%s%d" % (s, i), 4)
    parts.append(p.finish())
    return body, rig, parts, dict(reach=legL * S, zb=zb), mode

def anim_hex(A, info):
    reach = info["reach"]
    def legs(P, t, amp, lift, stance, groups):
        for s in "LR":
            for i in range(3):
                ph = 0.0 if (s == "L") == (i % 2 == 0) else 0.5
                u = (t + ph) % 1.0
                if u < stance: sw = amp * (1 - 2 * u / stance); lf = 0.0
                else: q = (u - stance) / (1 - stance); sw = -amp * math.cos(math.pi * q); lf = math.sin(math.pi * q)
                P["fem%s%d" % (s, i)] = A.rot("fem%s%d" % (s, i), fwd=sw, up=lift * lf)
                P["tib%s%d" % (s, i)] = A.rot("tib%s%d" % (s, i), up=-lift * 0.5 * lf)
    def gait(amp, lift, stance, bob):
        def fn(t):
            P = {}; legs(P, t, amp, lift, stance, None)
            P["body"] = A.rot("body", yaw=2 * math.sin(4 * math.pi * t))
            P["abdomen"] = A.rot("abdomen", yaw=4 * math.sin(4 * math.pi * t + 1), up=2 * math.sin(4 * math.pi * t))
            P["head"] = A.rot("head", yaw=-3 * math.sin(4 * math.pi * t))
            return P, (0, 0, bob * S * abs(math.sin(4 * math.pi * t)))
        return fn
    aw, ar = 18.0, 26.0
    sweep_w = 2 * reach * math.sin(math.radians(aw)); sweep_r = 2 * reach * math.sin(math.radians(ar))
    fw = int(round(30 * max(0.35, min(2.0, sweep_w / (0.55 * SP["speed"]))))); fr = int(round(30 * max(0.22, min(1.0, sweep_r / (0.5 * SP["fleeSpeed"])))))
    def idle(t):
        P = {}; br = math.sin(2 * math.pi * t * 2)
        P["head"] = A.rot("head", yaw=10 * math.sin(2 * math.pi * t), up=3 * br)
        P["abdomen"] = A.rot("abdomen", up=3 * br)
        tap = max(0, math.sin(2 * math.pi * t * 3)) ** 3
        for s in "LR": P["fem%s0" % s] = A.rot("fem%s0" % s, up=10 * tap, fwd=6 * tap)
        return P, (0, 0, 0.002 * S * br)
    def alert(t):
        P = {}; rear = 1.0 if "rears" in FE else 0.4
        clack = math.sin(2 * math.pi * t * 4)
        P["body"] = A.rot("body", up=22 * rear); P["head"] = A.rot("head", up=-10 * rear, yaw=8 * math.sin(2 * math.pi * t))
        P["abdomen"] = A.rot("abdomen", up=-18 * rear)
        for s in "LR":
            P["fem%s0" % s] = A.rot("fem%s0" % s, up=40 * rear + 8 * clack * rear, fwd=20)
            P["tib%s0" % s] = A.rot("tib%s0" % s, up=-30 * rear + 15 * clack * rear)
            P["fem%s2" % s] = A.rot("fem%s2" % s, up=-12 * rear)
        return P, (0, 0, 0.03 * S * rear)
    clips = [("idle", idle, 120, 4, False), ("walk", gait(aw, 22, 0.55, 0.004), fw, 1, False), ("run", gait(ar, 30, 0.5, 0.008), fr, 1, False), ("alert", alert, 60, 2, False)]
    return clips, dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert",
                       moveAnimSpeed=round(sweep_w / (0.55 * fw / 30), 2), fleeAnimSpeed=round(sweep_r / (0.5 * fr / 30), 2))

# =============================================================================== SERPENT
def build_serpent():
    n = SP.get("bones", 10); r = SP["R"]; water = SP.get("water", False); hr = SP["headR"]
    z = 0.0 if water else r
    sk = Skel(S)
    pts = []
    for i in range(n + 1):
        t = i / n
        y = 0.42 - 0.92 * t
        rr = r * (0.85 + 0.35 * math.sin(math.pi * min(1, t * 1.6))) * (1 - 0.82 * max(0, t - 0.55) / 0.45)
        sk.v("s%d" % i, 0, y, z if water else max(rr, r * 0.3), rr * SP.get("flatX", 1.0), rr)
        pts.append("s%d" % i)
    sk.v("head", 0, 0.5, (z if water else hr * 0.8), hr * SP.get("headW", 1.0), hr * 0.8)
    sk.v("snout", 0, 0.57, (z if water else hr * 0.6) - hr * 0.1, hr * 0.55, hr * 0.45)
    sk.e("snout", "head", *pts)
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.004), faces=SP.get("faces", 4500), floor=not water)
    bones = [("body", "s0", "head", None, False), ("head", "head", "snout", "body", True)]
    prev = "body"
    for i in range(n):
        b = "seg%d" % i; bones.append((b, "s%d" % i, "s%d" % (i + 1), prev, prev != "body")); prev = b
    rig = make_rig(NAME, sk, bones); mode = skin(body, rig); bvh = bvh_of(body); parts = []
    hc = V(0, 0.5, z if water else hr * 0.8)
    p = Part("eyes", 3); eyes_on(bvh, p, hc, hr * S * 0.25, SP.get("eyes", 2), spread=0.35, up=0.5, fwd=0.5); parts.append(p.finish())
    if "frills" in FE:      # sea serpent: fan-like gill frills behind the head
        p = Part("frills", 5)
        for sx in (1, -1):
            rows = []
            for j in range(3):
                row = []
                for k in range(6):
                    a = (k / 5 - 0.5) * 1.6
                    base = hc + V(sx * hr * 0.8, -hr * 0.9, 0)
                    row.append((U(base + V(sx * (0.02 + hr * 1.4 * j / 2) * math.cos(a), -hr * 0.3 * j / 2, hr * 1.4 * j / 2 * math.sin(a))), [("head", 0.5), ("body", 0.5)], j / 2))
                rows.append(row)
            p.grid(rows, flip=sx < 0, thickness=S * 0.0008)
        parts.append(p.finish())
    if "spines" in FE:
        p = Part("spines", 2)
        for i in range(n * 2):
            t = (i + 0.5) / (n * 2); y = 0.42 - 0.92 * t
            loc, nrm = ray(bvh, U((0, y, z + 1)), (0, 0, -1))
            if loc is None: continue
            bi = min(n - 1, int(t * n))
            p.cone(loc - nrm * S * 0.002, (0, -0.5, 1), S * SP["R"] * 0.9 * (1 - t * 0.6), S * SP["R"] * 0.22, "seg%d" % bi, 4)
        parts.append(p.finish())
    if "finridge" in FE:    # eel: continuous dorsal + ventral fin
        p = Part("fins", 5)
        for side in (1, -1):
            rows = []
            for j in range(2):
                row = []
                for i in range(n * 2 + 1):
                    t = 0.15 + 0.85 * i / (n * 2); y = 0.42 - 0.92 * t
                    loc, nrm = ray(bvh, U((0, y, z + side * 1)), (0, 0, -side))
                    if loc is None: loc = U((0, y, z))
                    bi = min(n - 1, int(t * n)); hgt = S * SP["R"] * 1.3 * math.sin(math.pi * (t - 0.15) / 0.85) ** 0.5
                    row.append((loc + Vector((0, 0, side * hgt * j)), "seg%d" % bi, j))
                rows.append(row)
            p.grid(rows, flip=side < 0, thickness=S * 0.0006)
        parts.append(p.finish())
    if "tongue" in FE:
        p = Part("tongue", 5)
        tip = U((0, 0.62, (z if water else hr * 0.45)))
        for sx in (1, -1): p.cone(U((0, 0.565, (z if water else hr * 0.5))), (sx * 0.25, 1, 0), S * 0.05, S * 0.004, "head", 4)
        parts.append(p.finish())
    parts += serpent_feats(locals())
    return body, rig, parts, dict(n=n), mode

def anim_serpent(A, info):
    n = info["n"]; water = SP.get("water", False)
    def wave(amp, cycles, rise):
        def fn(t):
            P = {}
            for i in range(n):
                P["seg%d" % i] = A.rot("seg%d" % i, yaw=amp * math.sin(2 * math.pi * (t - i / n * cycles)), up=rise * math.sin(2 * math.pi * (2 * t - i / n * cycles)) if water else 0)
            P["body"] = A.rot("body", yaw=amp * 0.6 * math.sin(2 * math.pi * (t + 0.1)))
            P["head"] = A.rot("head", yaw=-amp * 0.7 * math.sin(2 * math.pi * (t + 0.1)))
            return P, (0, 0, 0)
        return fn
    def idle(t):
        P = {}
        for i in range(n): P["seg%d" % i] = A.rot("seg%d" % i, yaw=9 * math.sin(2 * math.pi * (t - i / n)) + 4, up=(3 * math.sin(2 * math.pi * (t - i / n))) if water else 0)
        P["head"] = A.rot("head", up=6 + 6 * math.sin(2 * math.pi * t * 2) if not water else 4 * math.sin(2 * math.pi * t), yaw=10 * math.sin(2 * math.pi * t))
        return P, (0, 0, 0)
    def alert(t):
        P = {}
        P["body"] = A.rot("body", up=28 if not water else 18); P["head"] = A.rot("head", up=-20, yaw=10 * math.sin(2 * math.pi * t))
        for i in range(n): P["seg%d" % i] = A.rot("seg%d" % i, up=(-12 if i < 2 else 0), yaw=10 * math.sin(2 * math.pi * (t - i / n)))
        return P, (0, 0, 0)
    frames = 48
    return ([("idle", idle, 120, 4, False), ("move", wave(14, 1.3, 4), frames, 2, False), ("alert", alert, 60, 3, False)],
            dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="alert", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["speed"]))

# =============================================================================== AVIAN (Air)
def build_avian():
    W, span, hr, tail = SP["W"], SP["span"], SP["headR"], SP.get("tail", 0.3)
    sk = Skel(S)
    flat = SP.get("flatBody", 1.0)
    sk.v("pelvis", 0, -0.13, 0, W * 0.38 * flat, W * 0.36)
    sk.v("chest", 0, 0.1, 0.005, W * 0.5 * flat, W * 0.45)
    sk.v("neck", 0, 0.24, 0.02, W * 0.22, W * 0.22)
    sk.v("head", 0, 0.24 + hr * 1.2, 0.03, hr * SP.get("headW", 0.85), hr * 0.85)
    sk.v("tb", 0, -0.27, 0.0, W * 0.15, W * 0.12)
    sk.v("tt", 0, -0.27 - tail, 0.0, W * SP.get("tailTipR", 0.04), W * SP.get("tailTipR", 0.04))
    sk.e("tt", "tb", "pelvis", "chest", "neck", "head")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.006), faces=SP.get("faces", 3200), floor=False)
    sh, el, wr, tp = [], [], [], []
    bones = [("body", "pelvis", "chest", None, False), ("neck", "chest", "neck", "body", True), ("head", "neck", "head", "neck", True),
             ("tail1", "pelvis", "tb", "body", False), ("tail2", "tb", "tt", "tail1", True)]
    for s, sx in (("L", 1), ("R", -1)):
        sk.v("sh" + s, sx * W * 0.32, 0.08, 0.03, 0.02); sk.v("el" + s, sx * (W * 0.3 + span * 0.17), 0.1, 0.035, 0.02)
        sk.v("wr" + s, sx * (W * 0.3 + span * 0.33), 0.07, 0.04, 0.02); sk.v("tp" + s, sx * span * 0.5, SP.get("tipBack", -0.04), 0.04, 0.02)
        bones += [("wing1" + s, "sh" + s, "el" + s, "body", False), ("wing2" + s, "el" + s, "wr" + s, "wing1" + s, True), ("wing3" + s, "wr" + s, "tp" + s, "wing2" + s, True)]
    rig = make_rig(NAME, sk, bones); mode = skin(body, rig); bvh = bvh_of(body); parts = []
    hc = sk.pt("head") / S
    p = Part("eyes", 3); eyes_on(bvh, p, hc, hr * S * 0.2, SP.get("eyes", 2), spread=0.33, up=0.3, fwd=0.55); parts.append(p.finish())
    # ---- wings: membrane/feather sheet hung from the arm, chord tapering to the tip
    p = Part("wings", 5)
    cr, ct = SP.get("chordRoot", 0.3), SP.get("chordTip", 0.08)
    for s, sx in (("L", 1), ("R", -1)):
        chain = [sk.pt("sh" + s), sk.pt("el" + s), sk.pt("wr" + s), sk.pt("tp" + s)]
        segL = [(chain[i + 1] - chain[i]).length for i in range(3)]; tot = sum(segL)
        rows = []
        NU = 16; NJ = 5
        insect = "hindwings" in FE
        tipR = SP.get("tipRound", 0.0 if "fingers" in FE else 0.16)
        for j in range(NJ):
            jj = j / (NJ - 1)
            row = []
            for k in range(NU + 1):
                u = k / NU; d = u * tot; i = 0
                while i < 2 and d > segL[i]: d -= segL[i]; i += 1
                le = chain[i].lerp(chain[i + 1], min(1.0, d / segL[i]))
                if insect:      # teardrop insect wing: pinched at the root, broadest a third out, rounded tip
                    ch = S * cr * 1.15 * math.sin(math.pi * (0.06 + 0.92 * u)) ** 0.55 * (1 - 0.22 * u)
                else:
                    ch = S * (cr + (ct - cr) * u ** SP.get("chordPow", 1.0))
                    if tipR > 0 and u > 1 - tipR:      # round the tip off instead of ending square
                        q = (u - (1 - tipR)) / tipR
                        ch *= max(0.08, math.sqrt(max(0.0, 1 - q * q)))
                        le = le + Vector((0, -S * ct * 0.35 * q * q, 0))
                if "scallop" in FE and j == NJ - 1: ch *= 1.0 - 0.18 * abs(math.sin(u * math.pi * 6))
                camber = S * 0.07 * (ch / S) * math.sin(math.pi * jj) * (0.4 if insect else 1.0)
                bow = S * 0.012 * math.sin(math.pi * u) * (0 if insect else 1)
                co = le + Vector((0, -ch * jj, -S * 0.004 * jj * 3 + camber + bow))
                # blend weights across the joint
                wts = [("wing%d%s" % (i + 1, s), 1.0)]
                if j > 0 and u < 0.12: wts = [("wing1" + s, 0.6), ("body", 0.4)]
                row.append((co, wts, u))
            rows.append(row)
        p.grid(rows, flip=sx < 0, thickness=S * 0.002)
    if "tailfan" in FE:
        rows = []
        for j in range(3):
            row = []
            for k in range(5):
                a = (k / 4 - 0.5) * SP.get("fanAngle", 1.0)
                L = S * tail * (0.4 + 0.75 * j / 2) * (1 - 0.25 * abs(math.cos(a * 3)) if "forked" in FE else 1)
                row.append((sk.pt("tb") + Vector((math.sin(a) * L, -math.cos(a) * L, 0)), [("tail2", 0.7), ("tail1", 0.3)], j / 2))
            rows.append(row)
        p.grid(rows, thickness=S * 0.002)
    if "tassel" in FE:
        rows = []
        for j in range(2):
            row = []
            for k in range(4):
                a = (k / 3 - 0.5) * 1.4; L = S * 0.09 * (j + 0.2)
                row.append((sk.pt("tt") + Vector((math.sin(a) * L, -math.cos(a) * L, 0)), "tail2", 1.0))
            rows.append(row)
        p.grid(rows, thickness=S * 0.002)
    parts.append(p.finish())
    if "fingers" in FE:      # gyrewing: slotted primary feathers at the tips
        p = Part("primaries", 5)
        for s, sx in (("L", 1), ("R", -1)):
            tpp = sk.pt("tp" + s)
            for k in range(5):
                base = tpp + Vector((-sx * S * 0.03 * k, -S * 0.025 * k, 0))
                p.cone(base, (sx * 1.0, 0.2 - 0.25 * k, 0), S * (0.14 - 0.012 * k), S * 0.018, "wing3" + s, 4, flat=0.25)
        parts.append(p.finish())
    if "beak" in FE:
        p = Part("beak", 2)
        p.cone(U(hc + V(0, hr * 0.7, -hr * 0.05)), (0, 1, -0.25), S * hr * SP.get("beakL", 1.4), S * hr * 0.38, "head", 6, bend=(0, 0, -0.6) if "hook" in FE else None)
        parts.append(p.finish())
    if "crest" in FE:
        p = Part("crest", 1)
        p.cone(U(hc + V(0, -hr * 0.2, hr * 0.5)), (0, -1, 0.5), S * hr * 2.0, S * hr * 0.35, "head", 5, flat=0.3)
        parts.append(p.finish())
    if "insectlegs" not in FE:
        p = Part("feet", 2)
        for sx in (1, -1): p.cone(U((sx * W * 0.12, -0.16, -W * 0.25)), (0, -1, -0.2), S * 0.06, S * 0.014, "body", 4)
        parts.append(p.finish())
    parts += avian_feats(locals())
    return body, rig, parts, {}, mode

def anim_avian(A, info):
    def flap(T_up):
        def fn(t):
            P = {}; w = math.sin(2 * math.pi * t)
            for s in "LR":
                P["wing1" + s] = A.rot("wing1" + s, up=32 * w + 4, fwd=6 * math.cos(2 * math.pi * t))
                P["wing2" + s] = A.rot("wing2" + s, up=18 * math.sin(2 * math.pi * t - 0.6))
                P["wing3" + s] = A.rot("wing3" + s, up=16 * math.sin(2 * math.pi * t - 1.1), fwd=-8 * math.cos(2 * math.pi * t - 1.1))
            P["tail1"] = A.rot("tail1", up=4 * math.sin(2 * math.pi * t + 1)); P["neck"] = A.rot("neck", up=-3 * w)
            return P, (0, 0, -0.02 * S * w)
        return fn
    def glide(t):
        P = {}; g = math.sin(2 * math.pi * t)
        for s, sg in (("L", 1), ("R", -1)):
            P["wing1" + s] = A.rot("wing1" + s, up=8 + 3 * g * sg); P["wing2" + s] = A.rot("wing2" + s, up=-3 + 2 * g); P["wing3" + s] = A.rot("wing3" + s, up=5 + 3 * math.sin(2 * math.pi * t * 2))
        P["tail1"] = A.rot("tail1", yaw=5 * g); P["tail2"] = A.rot("tail2", yaw=8 * math.sin(2 * math.pi * t - 0.5))
        P["head"] = A.rot("head", yaw=14 * math.sin(2 * math.pi * t * 0.5 + 0.3), up=-6)
        return P, (0, 0, 0.01 * S * g)
    fl = SP.get("flapFrames", 24)
    return ([("glide", glide, 150, 5, False), ("flap", flap(0.5), fl, 1, False)],
            dict(idleAnim="glide", moveAnim="glide", fleeAnim="flap", alertAnim="flap", fleeAnimSpeed=SP["fleeSpeed"]))

# =============================================================================== FISH
def build_fish():
    W, H, hr = SP["W"], SP["H"], SP["headR"]
    sk = Skel(S)
    sk.v("snout", 0, 0.47, 0, W * 0.18, H * 0.22); sk.v("head", 0, 0.3, 0, W * 0.42, H * 0.82)
    sk.v("mid", 0, 0.08, 0.01, W * 0.5, H); sk.v("rear", 0, -0.18, 0, W * 0.32, H * 0.65); sk.v("ped", 0, -0.33, 0, W * 0.12, H * 0.22)
    sk.e("snout", "head", "mid", "rear", "ped")
    if "longsnout" in FE:
        sk.v("rost", 0, 0.47 + SP.get("snoutLen", 0.3), -H * 0.05, W * 0.06, H * 0.07); sk.e("snout", "rost")
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.005), faces=SP.get("faces", 3000), floor=False)
    bones = [("body", "mid", "head", None, False), ("head", "head", "snout", "body", True), ("tail1", "mid", "rear", "body", False),
             ("tail2", "rear", "ped", "tail1", True), ("fin", "ped", (0, -0.47, 0), "tail2", True)]
    if "longsnout" in FE: bones.append(("beak", "snout", "rost", "head", True))
    pk = SP.get("pecScale", 1.0)
    for s, sx in (("L", 1), ("R", -1)): bones.append(("pec" + s, (sx * W * 0.35, 0.22, -H * 0.3), (sx * W * 1.2 * pk, 0.12, -H * 0.55), "body", False))
    rig = make_rig(NAME, sk, bones, nondeform=("pecL", "pecR")); mode = skin(body, rig, nondeform=("pecL", "pecR")); bvh = bvh_of(body); parts = []
    p = Part("eyes", 3); eyes_on(bvh, p, (0, 0.33, 0.03), hr * S * 0.25, 2, spread=0.5, up=0.2, fwd=0.35); parts.append(p.finish())
    p = Part("fins", 5)
    rows = []                                  # forked caudal fin
    for j in (range(3) if "fluke" not in FE and "screw" not in FE else ()):
        row = []
        for k in range(7):
            v = k / 6 - 0.5; fork = 0.5 + 0.6 * abs(v) * 2
            row.append((U((0, -0.33 - 0.17 * fork * j / 2, v * H * 2.6 * (0.35 + 0.65 * j / 2))), [("fin", 0.4 + 0.6 * j / 2), ("tail2", 0.6 - 0.6 * j / 2)], j / 2))
        rows.append(row)
    if rows: p.grid(rows, thickness=S * 0.002)
    rows = []                                  # dorsal fin
    for j in range(3):
        row = []
        for k in range(6):
            y = 0.16 - 0.3 * k / 5
            loc, n = ray(bvh, U((0, y, 1)), (0, 0, -1)); z0 = loc.z if loc else U((0, 0, H)).z
            row.append((Vector((0, U((0, y - 0.05 * j / 2, 0)).y, z0 - S * 0.005 + S * H * 0.9 * (j / 2) * math.sin(math.pi * (k + 0.5) / 6))), [("tail1", k / 5), ("body", 1 - k / 5)], j / 2))
        rows.append(row)
    p.grid(rows, thickness=S * 0.002)
    for s, sx in (("L", 1), ("R", -1)):     # pectoral fins
        rows = []
        for j in range(2):
            row = []
            for k in range(4):
                a = k / 3
                row.append((U((sx * (W * 0.35 + W * 0.9 * j * pk), 0.22 - 0.12 * a * pk - 0.08 * j * pk, -H * 0.3 - H * 0.25 * j)), "pec" + s, j))
            rows.append(row)
        p.grid(rows, flip=sx < 0, thickness=S * 0.002)
    parts.append(p.finish())
    parts += fish_feats(locals())
    return body, rig, parts, {}, mode

def anim_fish(A, info):
    def swim(amp):
        def fn(t):
            P = {}; w = 2 * math.pi * t
            P["body"] = A.rot("body", yaw=amp * 0.25 * math.sin(w)); P["head"] = A.rot("head", yaw=-amp * 0.2 * math.sin(w))
            if "fluke" in FE:           # cetacean stroke: up and down
                P["body"] = A.rot("body", up=-amp * 0.15 * math.sin(w)); P["head"] = A.rot("head", up=amp * 0.1 * math.sin(w))
                P["tail1"] = A.rot("tail1", up=amp * 0.5 * math.sin(w - 0.8)); P["tail2"] = A.rot("tail2", up=amp * 0.8 * math.sin(w - 1.6)); P["fin"] = A.rot("fin", up=amp * 0.8 * math.sin(w - 2.4))
            else:
                P["tail1"] = A.rot("tail1", yaw=amp * 0.6 * math.sin(w - 0.8)); P["tail2"] = A.rot("tail2", yaw=amp * math.sin(w - 1.6)); P["fin"] = A.rot("fin", yaw=amp * 0.8 * math.sin(w - 2.4))
            if "screw" in FE:           # the rotor spins whole turns per cycle so the loop is seamless
                P["fin"] = A.rot("fin", roll=360.0 * SP.get("spins", 2) * t * (2 if amp > 14 else 1))
                P["tail2"] = A.rot("tail2", yaw=amp * 0.3 * math.sin(w - 1.6))
            for s in "LR": P["pec" + s] = A.rot("pec" + s, up=10 * math.sin(w + (0 if s == "L" else math.pi)))
            return P, (0, 0, 0)
        return fn
    sf = SP.get("swimFrames", 24); idf = SP.get("idleFrames", 60)
    return ([("idle", swim(10), idf, 2, False), ("swim", swim(18), sf, 1, False)],
            dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="idle", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["speed"]))

# =============================================================================== FLOATER (jellies, gas bags)
def build_floater():
    R, H, nr = SP["R"], SP["H"], SP.get("rims", 8); TL = SP["TL"]; ntent = SP.get("tents", 8)
    sk = Skel(S)
    sk.v("crown", 0, 0, H * 0.55, R * 0.55, H * 0.3); sk.v("core", 0, 0, H * 0.15, R * 0.82, H * 0.42)
    sk.e("core", "crown")
    for i in range(nr):
        a = i / nr * math.tau
        sk.v("rim%d" % i, R * math.cos(a), R * math.sin(a), -H * 0.08, R * 0.24, H * 0.14)
        sk.e("core", "rim%d" % i)
    for i in range(nr): sk.e("rim%d" % i, "rim%d" % ((i + 1) % nr))
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.008), faces=SP.get("faces", 3500), stiffness=2.0, floor=False)
    # hollow out the underside a little: push bottom verts up toward the centre
    def under(co, n):
        r = math.hypot(co.x, co.y) / S
        if co.z < S * H * 0.05 and r < R * 0.8: co.z += S * H * 0.25 * (1 - r / (R * 0.8)) ** 1.5
        return co
    displace(body, under)
    bones = [("body", (0, 0, -0.05 * H), (0, 0, H * 0.6), None, False)]
    for i in range(nr):
        a = i / nr * math.tau
        bones.append(("rim%d" % i, (R * 0.4 * math.cos(a), R * 0.4 * math.sin(a), H * 0.1), (R * 1.05 * math.cos(a), R * 1.05 * math.sin(a), -H * 0.1), "body", False))
    tents = []
    for i in range(ntent):
        a = (i + 0.5) / ntent * math.tau; rr = R * SP.get("tentR", 0.85)
        ri = int(round(((i + 0.5) / ntent) * nr)) % nr
        tents.append((V(rr * math.cos(a), rr * math.sin(a), -H * 0.05), TL, "rim%d" % ri, SP.get("tentThick", 0.012), 1.0, a))
    for i in range(SP.get("arms", 0)):        # frilly oral arms from the centre
        a = (i + 0.25) / max(1, SP.get("arms", 1)) * math.tau
        tents.append((V(R * 0.12 * math.cos(a), R * 0.12 * math.sin(a), 0.0), TL * SP.get("armL", 0.6), "body", SP.get("armThick", 0.03), 0.35, a))
    for ti, (base, L, par, th, fl, a) in enumerate(tents):
        drift = V(math.cos(a), math.sin(a), 0) * L * 0.08
        for k in range(3):
            h0 = base + drift * (k / 3) + V(0, 0, -L * k / 3); h1 = base + drift * ((k + 1) / 3) + V(0, 0, -L * (k + 1) / 3)
            bones.append(("t%d_%d" % (ti, k), tuple(h0), tuple(h1), par if k == 0 else "t%d_%d" % (ti, k - 1), k > 0))
    rig = make_rig(NAME, sk, bones)
    # the bell only follows body + rim bones; tentacles get explicit weights
    for b in rig.data.bones:
        if b.name.startswith("t"): b.use_deform = False
    mode = skin(body, rig)
    for b in rig.data.bones: b.use_deform = True
    parts = []
    p = Part("tentacles", 5)
    for ti, (base, L, par, th, fl, a) in enumerate(tents):
        drift = V(math.cos(a), math.sin(a), 0) * L * 0.08
        NR = 12; ring = []
        q = Matrix.Rotation(a, 3, 'Z')
        prev = None
        for k in range(NR + 1):
            t = k / NR; c = U(base + drift * t + V(0, 0, -L * t)); rr = S * th * (1 - 0.75 * t)
            seg_ = min(2, int(t * 3)); f = t * 3 - seg_
            w = [("t%d_%d" % (ti, seg_), 1.0 - 0.5 * max(0, f - 0.5)), ("t%d_%d" % (ti, min(2, seg_ + 1)), 0.5 * max(0, f - 0.5))] if seg_ < 2 else [("t%d_2" % ti, 1.0)]
            if k == 0: w = [(par, 1.0)]
            cur = [p.v(c + q @ Vector((math.cos(j / 6 * math.tau) * rr, math.sin(j / 6 * math.tau) * rr * fl, 0)), w, t) for j in range(6)]
            if prev:
                for j in range(6): p.f([prev[j], prev[(j + 1) % 6], cur[(j + 1) % 6], cur[j]])
            prev = cur
        if "frilly" in FE and fl < 1:    # ruffles along the oral arms
            for k in range(1, 9):
                t = k / 9; c = U(base + drift * t + V(0, 0, -L * t))
                p.sphere(c, S * th * 1.4, [("t%d_%d" % (ti, min(2, int(t * 3))), 1.0)], scale=(1.6, 1.6, 0.35), sub=1, jitter=0.5)
    parts.append(p.finish())
    if "crownspikes" in FE:   # bellcrown: ring of soft crown lobes
        p = Part("crown", 1)
        for i in range(nr * 2):
            a = i / (nr * 2) * math.tau
            p.cone(U((R * 0.45 * math.cos(a), R * 0.45 * math.sin(a), H * 0.62)), (math.cos(a) * 0.6, math.sin(a) * 0.6, 1), S * H * 0.28, S * R * 0.09, "body", 5)
        parts.append(p.finish())
    if "gonads" in FE:        # moonjelly: four horseshoe organs seen through the bell
        p = Part("organs", 6)
        for i in range(4):
            a = i / 4 * math.tau + 0.4
            p.sphere(U((R * 0.32 * math.cos(a), R * 0.32 * math.sin(a), H * 0.45)), S * R * 0.17, "body", scale=(1.0, 0.55, 0.45), sub=2)
        parts.append(p.finish())
    if "lanterns" in FE:      # glowing nodes round the rim
        p = Part("lanterns", 6)
        for i in range(nr):
            a = i / nr * math.tau
            p.sphere(U((R * 1.0 * math.cos(a), R * 1.0 * math.sin(a), -H * 0.06)), S * R * 0.09, "rim%d" % i, sub=1)
        parts.append(p.finish())
    parts += floater_feats(locals())
    return body, rig, parts, dict(nr=nr, nt=len(tents)), mode

def anim_floater(A, info):
    nr, nt = info["nr"], info["nt"]
    def pulse(amp, wav):
        def fn(t):
            P = {}; c = math.sin(2 * math.pi * t); cc = max(0.0, c) ** 1.5 - 0.35 * max(0.0, -c)
            for i in range(nr): P["rim%d" % i] = A.rot("rim%d" % i, up=-amp * cc)
            for ti in range(nt):
                for k in range(3):
                    ph = 2 * math.pi * (t - 0.12 * (k + 1)) + ti * 0.9
                    P["t%d_%d" % (ti, k)] = A.rot("t%d_%d" % (ti, k), yaw=wav * math.sin(ph) * (0.5 + 0.5 * k), fwd=wav * 0.6 * math.cos(ph * 0.7 + ti))
            return P, (0, 0, 0.03 * S * c * SP.get("bob", 1.0))
        return fn
    return ([("idle", pulse(SP.get("pulse", 18), 10), SP.get("idleFrames", 90), 3, False), ("move", pulse(SP.get("pulse", 18) * 1.3, 14), SP.get("moveFrames", 54), 2, False)],
            dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="idle", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["speed"]))

# =============================================================================== BLOB
def build_blob():
    sk = Skel(S)
    sk.v("front", 0, 0.3, 0.13, 0.24, 0.15); sk.v("mid", 0, 0.0, 0.17, 0.3, 0.19); sk.v("back", 0, -0.3, 0.12, 0.23, 0.13); sk.v("tail", 0, -0.46, 0.06, 0.14, 0.07)
    sk.v("hump", 0.05, -0.05, 0.3, 0.17, 0.13)
    sk.e("tail", "back", "mid", "front"); sk.e("mid", "hump")
    for s, sx in (("L", 1), ("R", -1)):
        sk.v("sk" + s, sx * 0.26, 0.05, 0.05, 0.12, 0.06); sk.e("mid", "sk" + s)
    body = metaball_body(NAME, sk, voxel=S * 0.008, faces=SP.get("faces", 4000))
    def lumpy(co, n):
        co += n * S * 0.025 * noise.noise(co / S * 6.0)
        return co
    displace(body, lumpy)
    for v in body.data.vertices:
        if v.co.z < 0: v.co.z = 0
    bones = [("body", (0, -0.05, 0.12), (0, 0.15, 0.13), None, False), ("front", (0, 0.15, 0.13), (0, 0.42, 0.1), "body", True), ("back", (0, -0.05, 0.12), (0, -0.48, 0.06), "body", False)]
    stalks = []
    n = SP.get("eyes", 5)
    for i in range(n):
        a = (i / (n - 1) - 0.5) * 1.6 if n > 1 else 0
        base = V(math.sin(a) * 0.14, 0.26 + 0.04 * math.cos(a), 0.22); top = base + V(math.sin(a) * 0.06, 0.05, 0.14 + 0.03 * (i % 2))
        bones.append(("stalk%d" % i, tuple(base), tuple(top), "front", False)); stalks.append((base, top))
    rig = make_rig(NAME, sk, bones)
    for i in range(n): rig.data.bones["stalk%d" % i].use_deform = False
    mode = skin(body, rig)
    for i in range(n): rig.data.bones["stalk%d" % i].use_deform = True
    bvh = bvh_of(body); parts = []
    p = Part("stalks", 0); pe = Part("eyes", 3)
    for i, (b, t) in enumerate(stalks):
        loc, nn = ray(bvh, U(b + V(0, 0, 0.5)), (0, 0, -1))
        a = loc - nn * S * 0.01 if loc else U(b)
        p.tube(a, U(t), S * 0.022, S * 0.014, "stalk%d" % i, rings=3, segs=6)
        if "horns" in FE: p.cone(U(t), (0, 0.2, 1), S * 0.05, S * 0.016, "stalk%d" % i, 6)
        else: pe.sphere(U(t), S * 0.03, "stalk%d" % i, sub=2)
    parts += [p.finish(), pe.finish()]
    p = Part("crystals", 6)          # glassy nodules where dissolved rock is concentrated
    for i in range(14 if "smooth" not in FE else 0):
        d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.3, 1))).normalized()
        loc, nn = ray(bvh, U((0, random.uniform(-0.3, 0.2), 0.15)) + d * S, -d)
        if loc is None: continue
        p.sphere(loc, S * random.uniform(0.018, 0.035), "body" if loc.y > 0 else "back", sub=1, jitter=0.4)
    parts.append(p.finish())
    parts += blob_feats(locals())
    return body, rig, parts, dict(n=n), mode

def anim_blob(A, info):
    n = info["n"]
    def ooze(amp, sp_):
        def fn(t):
            P = {}; w = 2 * math.pi * t
            P["front"] = A.rot("front", up=amp * math.sin(w), yaw=amp * 0.4 * math.sin(w * 0.5 if sp_ < 1 else w))
            P["back"] = A.rot("back", up=amp * math.sin(w - 1.6))
            for i in range(n): P["stalk%d" % i] = A.rot("stalk%d" % i, fwd=12 * math.sin(w + i * 1.3), yaw=14 * math.sin(w * 0.5 + i * 2.1))
            return P, (0, 0, 0.01 * S * math.sin(w * 2))
        return fn
    return ([("idle", ooze(4, 0.5), 150, 5, False), ("move", ooze(9, 1), 90, 3, False)],
            dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="idle", moveAnimSpeed=SP["speed"], fleeAnimSpeed=SP["speed"]))

BUILD = {"quad": (build_quad, anim_quad), "hex": (build_hex, anim_hex), "serpent": (build_serpent, anim_serpent), "avian": (build_avian, anim_avian),
         "fish": (build_fish, anim_fish), "floater": (build_floater, anim_floater), "blob": (build_blob, anim_blob)}
exec(open(os.path.join(TOOLS, "fauna_extra.py"), encoding="utf-8").read(), globals())

# =============================================================================== texture
def fauna_nodes(N):
    k = 1.0 / S
    col, belly, back, acc = SP["col"], SP.get("belly", tuple(min(1, c * 1.35 + 0.08) for c in SP["col"])), SP.get("back", tuple(c * 0.7 for c in SP["col"])), SP["acc"]
    if SP.get("shadeFront"):  # upright animals (penguins): pale front, dark back
        f = N.m('ADD', N.m('MULTIPLY', N.m('ADD', N.m('MULTIPLY', N.NY, -0.85), N.m('MULTIPLY', N.NZ, 0.3)), 0.5), 0.5)
        base = N.ramp(f, [(0.0, belly), (SP.get("mid", 0.46) - 0.1, belly), (SP.get("mid", 0.46), col), (SP.get("mid", 0.46) + 0.12, back), (1.0, back)])
    else:
        base = N.countershade(belly, col, back, SP.get("mid", 0.46))
    base = N.mul(base, N.m('ADD', N.m('MULTIPLY', N.noise(6.0 * k, 6), 0.35), 0.82))
    pat = SP.get("pattern")
    pm = None
    if pat == "spots": pm = N.m('LESS_THAN', N.voronoi(SP.get("patScale", 14.0) * k), SP.get("patSize", 0.16))
    elif pat == "bands": pm = N.m('GREATER_THAN', N.wave(SP.get("patScale", 6.0) * k, 'BANDS', 'Y', 1.5), SP.get("patSize", 0.7))
    elif pat == "stripes": pm = N.m('GREATER_THAN', N.wave(SP.get("patScale", 8.0) * k, 'BANDS', 'Z', 3.0), SP.get("patSize", 0.75))
    elif pat == "mottle": pm = N.m('GREATER_THAN', N.noise(SP.get("patScale", 9.0) * k, 3), SP.get("patSize", 0.56))
    elif pat == "feathers":  # scalloped feather edges
        pm = N.m('LESS_THAN', N.voronoi(SP.get("patScale", 40.0) * k, 'DISTANCE_TO_EDGE'), SP.get("patSize", 0.06))
    elif pat == "bars":      # fine cross-barring (hawks, owls, turkeys)
        pm = N.m('GREATER_THAN', N.wave(SP.get("patScale", 30.0) * k, 'BANDS', 'Y', 4.0), SP.get("patSize", 0.7))
    elif pat == "rings": pm = N.m('GREATER_THAN', N.wave(SP.get("patScale", 9.0) * k, 'RINGS', 'Z', 1.0), SP.get("patSize", 0.8))
    if pm is not None: base = N.mix(base, acc, N.m('MULTIPLY', pm, SP.get("patStrength", 0.85)))
    if SP.get("headCol"):     # birds: coloured head/neck (hood) and a collar ring below it
        base = N.mix(base, SP["headCol"], N.m('MULTIPLY', N.attr("hood"), SP.get("headStrength", 1.0)))
    if SP.get("collarCol"):
        base = N.mix(base, SP["collarCol"], N.attr("collar"))
    if SP.get("tipMul"):      # hair cards: lighter (or darker) toward the tips
        base = N.mix(base, N.mul(base, SP["tipMul"]), N.tipf)
    if SP.get("pleats"):      # ventral throat grooves (front half, underside)
        pl = N.m('GREATER_THAN', N.wave(SP["pleats"] * k, 'BANDS', 'X', 0.4), 0.82)
        mask = N.m('MULTIPLY', N.m('LESS_THAN', N.NZ, -0.2), N.m('GREATER_THAN', N.Y, 0.0))
        base = N.mix(base, N.mul(base, 0.55), N.m('MULTIPLY', N.m('MULTIPLY', pl, mask), 0.8))
    shell = N.mix(acc, tuple(c * 0.6 for c in acc), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.m('MULTIPLY', N.voronoi(10.0 * k, 'DISTANCE_TO_EDGE'), 10.0, clamp=True)), 0.8))
    shell = N.mix(shell, (1, 1, 1), N.m('MULTIPLY', N.up01(), SP.get("shellSheen", 0.15)))
    horn = N.mix(SP.get("horn", (0.85, 0.8, 0.68)), tuple(c * 0.5 for c in SP.get("horn", (0.85, 0.8, 0.68))), N.tipf)
    eyec = SP.get("eyeCol", (0.03, 0.03, 0.03))
    eye = N.mix(eyec, tuple(min(1.0, c * 2.2 + 0.07) for c in eyec), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.up01()), 0.55))
    lit = N.m('ADD', N.m('ADD', N.m('MULTIPLY', N.m('ABSOLUTE', N.NX), 0.33), N.m('MULTIPLY', N.NY, 0.52)), N.m('MULTIPLY', N.NZ, 0.79))
    eye = N.mix(eye, (0.97, 0.97, 0.95), N.m('GREATER_THAN', lit, 0.93))
    fur = N.mix(SP.get("fur", col), tuple(c * 0.65 for c in SP.get("fur", col)), N.m('MULTIPLY', N.wave(30.0 * k, 'BANDS', 'Z', 8.0), 0.6))
    if SP.get("furBands", True) is False:   # plain hair (manes, tails): no banding, a little lighter at the tips
        fur = N.mix(SP["fur"], tuple(min(1.0, c * 1.6 + 0.04) for c in SP["fur"]), N.m('MULTIPLY', N.tipf, 0.6))
    memc = SP.get("mem", acc)
    mem = N.mix(memc, SP.get("memTip", tuple(c * 0.55 for c in memc)), N.m('POWER', N.tipf, 2.0))
    if SP.get("veinNoise"):   # organic, wandering veins: thin bands where a noise field crosses 0.5
        vn = N.m('ABSOLUTE', N.m('SUBTRACT', N.noise(SP.get("veinScale", 18.0) * k, 3.0, rough=0.45), 0.5))
        vm = N.m('LESS_THAN', vn, SP.get("veinWidth", 0.02))
    else:
        vm = N.m('LESS_THAN', N.voronoi(SP.get("veinScale", 18.0) * k, 'DISTANCE_TO_EDGE', vec=None), SP.get("veinWidth", 0.04))
    if SP.get("memMottle"):   # translucent-looking membrane: blotchy, rosier underneath
        mem = N.mix(mem, SP["memMottle"], N.m('MULTIPLY', N.m('ADD', N.m('MULTIPLY', N.noise(4.0 * k, 4), 0.8), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.up01()), 0.5)), 0.7, clamp=True))
    if SP.get("veins", True): mem = N.mix(mem, SP.get("veinCol", tuple(c * 0.6 for c in memc)), N.m('MULTIPLY', vm, 0.6))
    if SP.get("memBands"): mem = N.mix(mem, SP["memBands"], N.m('GREATER_THAN', N.wave(SP.get("memBandScale", 20.0) * k, 'BANDS', 'X', 1.0), 0.75))
    if SP.get("memSpots"):    # eyespots on moth wings: a dark ring with a pale pupil
        vs = N.voronoi(SP.get("memSpotScale", 7.0) * k, 'F1', rand=0.6)
        ring, pupil = SP["memSpots"]
        mem = N.mix(mem, ring, N.m('LESS_THAN', vs, 0.2)); mem = N.mix(mem, pupil, N.m('LESS_THAN', vs, 0.09))
    glowc = SP.get("glow", (0, 0, 0))
    organ = SP.get("organ", tuple(min(1, g * 1.4 + 0.15) for g in glowc) if any(glowc) else acc)
    if SP.get("organBands"): organ = N.mix(organ, tuple(c * 0.7 for c in organ), N.m('MULTIPLY', N.m('GREATER_THAN', N.wave(SP["organBands"] * k, 'BANDS', 'X', 0.3), 0.7), 0.7))
    c = base
    c = N.mix(c, shell, N.is_part(1)); c = N.mix(c, horn, N.is_part(2)); c = N.mix(c, eye, N.is_part(3))
    c = N.mix(c, fur, N.is_part(4)); c = N.mix(c, mem, N.is_part(5)); c = N.mix(c, organ, N.is_part(6))
    g = None
    if any(glowc):
        g = N.mix((0, 0, 0), glowc, N.is_part(6))
        if SP.get("glowPattern") and pm is not None: g = N.mix(g, tuple(x * 0.7 for x in glowc), N.m('MULTIPLY', pm, N.m('SUBTRACT', 1.0, N.is_part(6))))
        if SP.get("glowBody"): g = N.mix(g, tuple(x * SP["glowBody"] for x in glowc), N.m('SUBTRACT', 1.0, N.is_part(3)))
        if SP.get("glowMem"): g = N.mix(g, tuple(x * SP["glowMem"] for x in glowc), N.is_part(5))
        if SP.get("glowEyes"): g = N.mix(g, tuple(x * SP["glowEyes"] for x in glowc), N.is_part(3))
        if SP.get("glowVeins"): g = N.mix(g, tuple(x * SP["glowVeins"] for x in glowc), N.m('MULTIPLY', vm, N.is_part(5)))
    if SP.get("sheen"):        # mirror scales flash a little in the dark
        g = N.mix(g if g is not None else (0, 0, 0), tuple(x * SP["sheen"] for x in acc), N.is_part(1))
    if "post_nodes" in globals(): c, g = post_nodes(N, c, g)
    return c, g

# =============================================================================== run
build, animate = BUILD[SP["arch"]]
body, rig, parts, info, mode = build()
body = join_all(body, parts, NAME)
if "post_join" in globals(): post_join(body)
root = finalize(NAME, body, rig)
result["model"] = {"verts": len(body.data.vertices), "tris": sum(len(f.vertices) - 2 for f in body.data.polygons), "weights": mode,
                   "dims": [round(x, 2) for x in body.dimensions]}

if STEP != "model":
    uv_unwrap(body, squeeze_part=SP.get("squeezePart"))
    if "post_uv" in globals(): post_uv(body)
    bake_and_material(body, NAME, OUT_DIR, fauna_nodes, res=SP.get("res", 1024), glow_res=128)
    A = Anim(rig)
    clips, cfg = animate(A, info)
    made = A.bake(clips, default=clips[1][0])
    result["clips"] = made; result["cfg"] = cfg
    result["export"] = export_mu(NAME, os.path.join(OUT_DIR, NAME + ".mu"))
    # ---- review renders + icons
    cam, g = stage_setup(ground=SP["arch"] not in ("avian", "lepid", "fish", "floater", "ceph", "cetacean", "seadragon", "skysac", "skylev") and not SP.get("water"))
    dims = body.dimensions; L = max(dims)
    cam.data.clip_start = max(0.01, L * 0.0005); cam.data.clip_end = max(1000.0, L * 10)
    bb = [body.matrix_world @ Vector(b) for b in body.bound_box]
    cen = sum(bb, Vector()) / 8; zc = cen.z
    if SP.get("focusTop"):            # frame the main body, not the trailing tendrils
        vs = [body.matrix_world @ v.co for v in body.data.vertices if v.co.z > -S * SP["focusTop"]]
        lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        cen = (lo + hi) / 2; L = max(hi - lo) * 1.3
    cam.data.type = 'PERSP'; cam.data.lens = 50
    cdir = Vector(SP.get("camDir", (0.95, 1.1, 0.55))).normalized()
    for clip, f, nm in ((clips[0][0], 10, "a"), (clips[1][0], max(1, clips[1][2] // 3), "b")):
        set_clip(rig, clip, f); look_at(cam, cen + cdir * L * 2.3, cen)
        render(os.path.join(PREVIEW_DIR, "fauna_%s_%s.png" % (NAME, nm)), res=(640, 480))
    side = SP["arch"] not in ("avian",) and not SP.get("silTop")
    sil_clip = clips[0][0]
    if side: sil = ((L * 3, cen.y, zc), (0, cen.y, zc))
    else: sil = ((cen.x, cen.y, L * 3), None)
    ortho = max(dims.y, dims.z) * 1.15 if side else max(dims.x, dims.y) * 1.1
    if SP["arch"] == "skysac": ortho = max(dims.y, dims.z) * 1.1
    if SP["arch"] == "floater": ortho = max(dims.x, dims.z) * 1.15; sil = ((0, -L * 3, zc), (0, 0, zc))
    por = (cen + Vector(SP.get("porDir", (0.8, 1.2, 0.45))).normalized() * L * SP.get("porDist", 1.9), cen)
    por_frame = max(1, int(round(clips[1][2] * 0.25))) if SP["arch"] in ("avian",) else 10
    por_clip = clips[1][0] if SP["arch"] in ("avian",) else clips[0][0]
    if "porClip" in SP: por_clip = clips[SP["porClip"]][0]
    por_frame = SP.get("porFrame", por_frame)
    icon_renders(rig, "fauna_" + NAME, sil_clip, SP.get("silFrame", 10), sil, ortho, por_clip, por_frame, por, lens=50, top=not side)
    os.makedirs(os.path.join(os.path.dirname(PREVIEW_DIR), "blend", "fauna"), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(PREVIEW_DIR), "blend", "fauna", NAME + ".blend"), copy=True)
