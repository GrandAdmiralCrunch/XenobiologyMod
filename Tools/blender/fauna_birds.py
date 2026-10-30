# Xenobiology — "bird" archetype for fauna_build.py (exec'd from fauna_extra.py, shares its globals).
# Two-legged feathered fliers, waders, swimmers and runners: Kerbin's Aerokerba.
#   * Built in flight posture (torso level, wings spread); ground clips pitch the torso up by `perch` and
#     counter-rotate the thighs so the feet stay planted.
#   * Each wing exists twice: a spread wing (wing1-3 bones) and a folded wing lying on the flank (fold bone).
#     Ground clips scale the spread wing to nothing and flight clips scale the folded one away, so cross-fading
#     between clips reads as the wings opening and closing.
#   * Legs, toes, webs and talons are explicit tubes/cones; the body is a metaball torso + neck chain + head.
# Units are fractions of `size` (beak tip to tail tip), +Y forward, Z up, feet on Z = 0.
# Spec keys: B W Rv legH legR toeL neckL neckN neckUp neckCurve neckR headR headW beak beakL tail tailW span chordRoot
# chordTip chordPow tipRound perch restPitch foldTip foldChord flight hoodStart headCol collarCol collarW + feats:
# fingers talons webbed crest facedisc eartufts snood wattle beard fan plumes pouch knob flippers bareshins dabble hophop

BIRD_FOLDED = 0.02        # scale of the hidden wing set

def _rx(v, piv, deg):
    """Rotate a unit-space point about the X axis through `piv`."""
    a = math.radians(deg); d = Vector(v) - Vector(piv)
    return Vector(piv) + Vector((d.x, d.y * math.cos(a) - d.z * math.sin(a), d.y * math.sin(a) + d.z * math.cos(a)))

def _r2(y, z, deg):
    a = math.radians(deg); return (y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))

def build_bird():
    SP.setdefault("veins", False)
    B, W, Rv, legH = SP["B"], SP["W"], SP["Rv"], SP["legH"]
    hr = SP["headR"]; tail = SP.get("tail", 0.15); legR = SP.get("legR", 0.012); toeL = SP.get("toeL", 0.05)
    rp = SP.get("restPitch", 0.0); flight = SP.get("flight", True)
    zb = legH + Rv * 0.75
    hipY = SP.get("hipY", -0.05)
    hip = V(0, hipY, legH + Rv * 0.45)
    P = lambda *a: _rx(V(*a), hip, rp)
    sk = Skel(S)
    rump = P(0, -B * 0.5, zb + Rv * 0.05); belly = P(0, -B * 0.06, zb); chest = P(0, B * 0.4, zb + Rv * 0.12)
    sk.v("rump", *rump, W * 0.34, Rv * 0.66); sk.v("belly", *belly, W * 0.5, Rv); sk.v("chest", *chest, W * 0.46, Rv * 0.9)
    # ---- neck chain and head (neckUp / neckCurve are world angles, so upright penguins still look forward)
    nb = P(0, B * 0.5, zb + Rv * 0.5)
    nN = SP.get("neckN", 2); nL = SP.get("neckL", 0.08); ang = SP.get("neckUp", 50.0); curve = SP.get("neckCurve", 0.0)
    nr0 = SP.get("neckR", W * 0.22)
    pts = [nb]; cur = nb
    for k in range(nN):
        a = math.radians(ang + curve * k)
        cur = cur + V(0, nL / nN * math.cos(a), nL / nN * math.sin(a)); pts.append(cur)
    nnames = ["nb"] + ["n%d" % (k + 1) for k in range(nN)]
    for k, (nm, pt) in enumerate(zip(nnames, pts)):
        r = nr0 * (1 - SP.get("neckTaper", 0.3) * k / max(1, nN))
        sk.v(nm, *pt, r)
    hc = pts[-1] + V(0, hr * SP.get("headFwd", 0.5), hr * 0.3)
    sk.v("head", *hc, hr * SP.get("headW", 0.9), hr)
    tb = P(0, -B * 0.62, zb + Rv * 0.12 + SP.get("tailUp", 0.0))
    sk.v("tb", *tb, W * 0.15, Rv * 0.22)
    sk.e("tb", "rump", "belly", "chest", *nnames); sk.e(nnames[-1], "head")
    # ---- legs (built straight down from the hips with a backward-bending ankle)
    legs = {}
    for s, sx in (("L", 1), ("R", -1)):
        x = sx * W * SP.get("legX", 0.22)
        hp = V(x, hipY, hip.z); kn = V(x, hipY + legH * 0.16 + Rv * 0.15, legH * 0.72)
        an = V(x, hipY - legH * 0.1, legH * 0.34); ft = V(x, hipY + legH * 0.02, legR * 0.6)
        legs[s] = (hp, kn, an, ft)
    # ---- spread wing chain (shoulder joint buried in the body) and folded-wing pivot
    span = SP.get("span", 1.6)
    wing = {}
    for s, sx in (("L", 1), ("R", -1)):
        sh = P(sx * W * 0.2, B * 0.28, zb + Rv * 0.45)
        el = V(sx * (W * 0.42 + span * 0.13), sh.y + 0.015, sh.z + 0.01)
        wr = V(sx * (W * 0.42 + span * 0.27), sh.y - 0.005, sh.z + 0.015)
        tp = V(sx * span * 0.5, sh.y + SP.get("tipBack", -0.05), sh.z + 0.02)
        fh = P(sx * W * 0.18, B * 0.3, zb + Rv * 0.35)
        wing[s] = (sh, el, wr, tp, fh)
    body = metaball_body(NAME, sk, voxel=S * SP.get("voxel", 0.0055), faces=SP.get("faces", 4200), floor=False)
    hf = hc + V(0, hr, 0)
    bones = [("body", tuple(hip), "chest", None, False), ("tail", "rump", "tb", "body", False),
             ("neck1", "nb", "n1", "body", False)]
    for k in range(2, nN + 1): bones.append(("neck%d" % k, "n%d" % (k - 1), "n%d" % k, "neck%d" % (k - 1), True))
    bones.append(("head", "n%d" % nN, tuple(hf), "neck%d" % nN, True))
    nondef = []
    for s in "LR":
        hp, kn, an, ft = legs[s]
        bones += [("thigh" + s, tuple(hp), tuple(kn), "body", False), ("shin" + s, tuple(kn), tuple(an), "thigh" + s, True),
                  ("tars" + s, tuple(an), tuple(ft), "shin" + s, True), ("toe" + s, tuple(ft), tuple(ft + V(0, toeL, 0)), "tars" + s, True)]
        nondef += ["shin" + s, "tars" + s, "toe" + s]
        sh, el, wr, tp, fh = wing[s]
        if "flippers" in FE:
            bones.append(("wing1" + s, tuple(sh), tuple(sh + V(0, -0.02, -B * 0.4)), "body", False)); nondef.append("wing1" + s)
        else:
            if flight:
                bones += [("wing1" + s, tuple(sh), tuple(el), "body", False), ("wing2" + s, tuple(el), tuple(wr), "wing1" + s, True),
                          ("wing3" + s, tuple(wr), tuple(tp), "wing2" + s, True)]
                nondef += ["wing1" + s, "wing2" + s, "wing3" + s]
            bones.append(("fold" + s, tuple(fh), tuple(fh + V(0, -B * 0.5, 0)), "body", False)); nondef.append("fold" + s)
    if "fan" in FE:
        bones.append(("fan", "tb", tuple(tb + V(0, -0.01, SP.get("fanR", 0.3))), "tail", False)); nondef.append("fan")
    rig = make_rig(NAME, sk, bones, nondeform=nondef); mode = skin(body, rig, nondeform=nondef)
    bvh = bvh_of(body); parts = []
    hcw = U(hc)
    # ---- hood / collar regions (vertex attributes read by the texture): position along the neck chain
    chain = [U(p) for p in pts] + [hcw]
    hs, cw = SP.get("hoodStart", 0.85), SP.get("collarW", 0.06)
    hood = body.data.attributes.new("hood", 'FLOAT', 'POINT'); col = body.data.attributes.new("collar", 'FLOAT', 'POINT')
    seglen = [(chain[i + 1] - chain[i]).length for i in range(len(chain) - 1)]; tot = sum(seglen) or 1.0
    for vi, v in enumerate(body.data.vertices):
        best = (1e9, 0.0); acc = 0.0
        for i in range(len(chain) - 1):
            a, b_ = chain[i], chain[i + 1]; d = b_ - a; L2 = max(1e-9, d.length_squared)
            t = max(0.0, min(1.0, (v.co - a).dot(d) / L2)); dist = (v.co - (a + d * t)).length
            if dist < best[0]: best = (dist, (acc + t * seglen[i]) / tot)
            acc += seglen[i]
        dist, s_ = best
        near = dist < S * max(hr * 1.6, W * 0.45)
        # past the chest the torso is closer to the first segment; only the neck/head side counts
        hv = smooth01((s_ - hs) / 0.06) if near else 0.0
        if (v.co - hcw).length < S * hr * 1.25: hv = 1.0
        if s_ <= 0.001 and (v.co - chain[0]).length > S * W * 0.3: hv = 0.0
        hood.data[vi].value = hv
        col.data[vi].value = (smooth01((s_ - (hs - cw)) / 0.02) * (1 - smooth01((s_ - hs + 0.01) / 0.02))) if near and hs > 0.02 else 0.0
    # ---- eyes
    p = Part("eyes", 3)
    if "facedisc" in FE:
        for sx in (1, -1): p.sphere(hcw + U((sx * hr * 0.42, hr * 0.92, hr * 0.12)), S * hr * 0.27, "head", scale=(1, 0.6, 1), sub=2)
    else:
        eyes_on(bvh, p, hc, hr * S * SP.get("eyeR", 0.2), 2, spread=SP.get("eyeSpread", 0.36), up=0.3, fwd=0.35)
    parts.append(p.finish())
    # ---- beak
    beak = SP.get("beak", "cone"); bL = SP.get("beakL", 1.2); bpid = SP.get("beakPart", 2)
    p = Part("beak", bpid); bb = hcw + U((0, hr * 0.78, -hr * 0.12))
    if beak == "cone":
        p.cone(bb, (0, 1, -0.12), S * hr * bL, S * hr * 0.36, "head", 6)
    elif beak == "hook":
        p.cone(bb + U((0, 0, hr * 0.05)), (0, 1, -0.1), S * hr * bL, S * hr * 0.42, "head", 7, bend=(0, -0.15, -0.9))
    elif beak == "bill":        # spatulate waterfowl bill with a nail at the tip
        p.sphere(bb + U((0, hr * bL * 0.45, -hr * 0.12)), S * hr * bL * 0.5, "head", scale=(SP.get("billW", 0.62), 1.0, 0.24), sub=2)
        p.sphere(bb + U((0, hr * bL * 0.12, 0)), S * hr * 0.42, "head", scale=(1.0, 0.8, 0.7), sub=2)
    elif beak == "pouch":       # pelican: long flat upper bill; the pouch hangs underneath (organ colour)
        p.sphere(bb + U((0, hr * bL * 0.5, -hr * 0.05)), S * hr * bL * 0.5, "head", scale=(0.16, 1.0, 0.07), sub=2)
        p.cone(bb + U((0, hr * bL * 0.98, -hr * 0.05)), (0, 0.4, -1), S * hr * 0.3, S * hr * 0.09, "head", 5)
    elif beak == "short":
        p.cone(bb, (0, 1, -0.35), S * hr * bL, S * hr * 0.42, "head", 6, flat=0.8, bend=(0, 0, -0.3))
    parts.append(p.finish())
    if "pouch" in FE:
        p = Part("pouch", 6)
        p.sphere(bb + U((0, hr * bL * 0.42, -hr * 0.45)), S * hr * bL * 0.42, "head", scale=(0.15, 1.0, 0.32), sub=2)
        parts.append(p.finish())
    if "knob" in FE:            # swan: black knob at the base of the bill
        p = Part("knob", 3); p.sphere(bb + U((0, hr * 0.1, hr * 0.18)), S * hr * 0.25, "head", scale=(0.8, 1.2, 0.9), sub=1); parts.append(p.finish())
    # ---- head ornaments
    if "crest" in FE:
        p = Part("crest", 4)
        for k in range(5):
            p.cone(hcw + U((0, -hr * 0.1 - hr * 0.12 * k, hr * 0.75)), (0, -1, 0.9 - 0.12 * k), S * hr * SP.get("crestL", 1.3) * (1 - 0.1 * k), S * hr * 0.2, "head", 5, flat=0.35)
        parts.append(p.finish())
    if "facedisc" in FE:
        p = Part("disc", 4)
        for sx in (1, -1): p.sphere(hcw + U((sx * hr * 0.4, hr * 0.62, 0)), S * hr * 0.72, "head", scale=(1.0, 0.38, 1.05), sub=2)
        parts.append(p.finish())
    if "eartufts" in FE:
        p = Part("tufts", 4)
        for sx in (1, -1): p.cone(hcw + U((sx * hr * 0.55, hr * 0.15, hr * 0.7)), (sx * 0.35, 0.15, 1.0), S * hr * 0.75, S * hr * 0.2, "head", 5, flat=0.35)
        parts.append(p.finish())
    if "snood" in FE or "wattle" in FE:
        p = Part("wattle", 6)
        if "snood" in FE:
            p.tube(bb + U((0, -hr * 0.1, hr * 0.32)), bb + U((0, hr * 0.5, hr * 0.15)), S * hr * 0.12, S * hr * 0.1, "head", rings=2, segs=6)
            p.tube(bb + U((0, hr * 0.5, hr * 0.15)), bb + U((0.02 * hr, hr * 0.7, -hr * 1.1)), S * hr * 0.1, S * hr * 0.06, "head", rings=4, segs=6)
        if "wattle" in FE:
            for k in range(4):
                p.sphere(hcw + U((0, hr * 0.2 - hr * 0.15 * k, -hr * (0.75 + 0.3 * k))), S * hr * (0.32 - 0.03 * k), "head" if k < 2 else "neck%d" % nN, scale=(0.7, 0.9, 1.0), sub=2, jitter=0.25)
        parts.append(p.finish())
    if "beard" in FE:           # turkey: a tuft of bristles hanging from the chest
        p = Part("beard", 4); c = U(chest + V(0, B * 0.08, Rv * 0.2))
        for k in range(10):
            p.cone(c + U((random.uniform(-0.01, 0.01), random.uniform(-0.01, 0.01), 0)), (random.uniform(-0.1, 0.1), 0.2, -1), S * random.uniform(0.09, 0.12), S * 0.006, "body", 4)
        parts.append(p.finish())
    # ---- legs and feet
    pl = Part("thighs", 0); pf = Part("feet", 2)
    for s, sx in (("L", 1), ("R", -1)):
        hp, kn, an, ft = legs[s]
        pl.tube(U(hp), U(kn), S * legR * SP.get("thighR", 2.6), S * legR * 2.0, "thigh" + s, rings=3, segs=7)
        (pf if "bareshins" in FE else pl).tube(U(kn), U(an), S * legR * 1.7, S * legR * 1.15, "shin" + s, rings=3, segs=6)
        pf.tube(U(an), U(ft), S * legR * 1.05, S * legR * 0.9, "tars" + s, rings=3, segs=6)
        pf.sphere(U(an), S * legR * 1.25, "shin" + s, sub=1)
        toes = SP.get("toes", (-0.5, 0.0, 0.5))
        tips = []
        for k, a in enumerate(toes):
            d = Vector((math.sin(a), math.cos(a), -0.02))
            Lt = toeL * (1.0 if a == 0 else SP.get("sideToe", 0.8))
            pf.cone(U(ft) + U((0, 0, legR * 0.2)), d, S * Lt, S * legR * 0.7, "toe" + s, 5, flat=0.6)
            tips.append((U(ft) + d * S * Lt, d))
            if "talons" in FE:
                pf.cone(U(ft) + d * S * Lt * 0.9, (d.x, d.y, -0.9), S * legR * 1.6, S * legR * 0.38, "toe" + s, 5, bend=(0, -0.6, 0))
        if SP.get("hallux", 0.45) > 0:
            pf.cone(U(ft) + U((0, 0, legR * 0.4)), (0, -1, 0.05), S * toeL * SP.get("hallux", 0.45), S * legR * 0.6, "tars" + s, 5, flat=0.6)
        if "webbed" in FE and len(tips) == 3:
            rows = []
            for j, f in enumerate((0.12, 0.97)):
                rows.append([(U(ft) + U((0, 0, legR * 0.15)) + (tp_ - U(ft)) * f, "toe" + s, f) for tp_, d in tips])
            pf.grid(rows, thickness=S * legR * 0.12)
    parts += [pl.finish(), pf.finish()]
    # ---- spread wings (flight)
    if flight and "flippers" not in FE:
        p = Part("wings", 5)
        cr, ct = SP.get("chordRoot", 0.3), SP.get("chordTip", 0.1)
        for s, sx in (("L", 1), ("R", -1)):
            sh, el, wr, tp, fh = wing[s]
            ch_ = [U(sh), U(el), U(wr), U(tp)]
            segL = [(ch_[i + 1] - ch_[i]).length for i in range(3)]; totw = sum(segL)
            rows = []; NU = 18; NJ = 5
            tipR = SP.get("tipRound", 0.0 if "fingers" in FE else 0.18)
            for j in range(NJ):
                jj = j / (NJ - 1); row = []
                for k in range(NU + 1):
                    u = k / NU; d = u * totw; i = 0
                    while i < 2 and d > segL[i]: d -= segL[i]; i += 1
                    le = ch_[i].lerp(ch_[i + 1], min(1.0, d / segL[i]))
                    ch = S * (cr + (ct - cr) * u ** SP.get("chordPow", 1.0))
                    if tipR > 0 and u > 1 - tipR:
                        q = (u - (1 - tipR)) / tipR; ch *= max(0.08, math.sqrt(max(0.0, 1 - q * q)))
                        le = le + Vector((0, -S * ct * 0.35 * q * q, 0))
                    if j == NJ - 1 and SP.get("scallop", 0): ch *= 1.0 - SP["scallop"] * abs(math.sin(u * math.pi * 7))
                    camber = S * 0.07 * (ch / S) * math.sin(math.pi * jj); bow = S * 0.01 * math.sin(math.pi * u)
                    co = le + Vector((0, -ch * jj, camber + bow))
                    wts = [("wing%d%s" % (i + 1, s), 1.0)]
                    if u < 0.1: wts = [("wing1" + s, 1.0)]
                    row.append((co, wts, u * 0.6 + jj * 0.4))
                rows.append(row)
            p.grid(rows, flip=sx < 0, thickness=S * 0.002)
        parts.append(p.finish())
        if "fingers" in FE:      # slotted primaries at the wingtips
            p = Part("primaries", 5)
            for s, sx in (("L", 1), ("R", -1)):
                tpp = U(wing[s][3])
                for k in range(SP.get("nFingers", 5)):
                    base = tpp + Vector((-sx * S * 0.025 * k, -S * 0.022 * k, 0))
                    p.cone(base, (sx * 1.0, 0.25 - 0.28 * k, 0), S * (SP.get("fingerL", 0.12) - 0.012 * k), S * 0.016, "wing3" + s, 4, flat=0.22)
            parts.append(p.finish())
    # ---- folded wings lying on the flanks (ground)
    if "flippers" in FE:
        p = Part("flippers", 5)
        for s, sx in (("L", 1), ("R", -1)):
            sh = U(wing[s][0]); a = sh + U((sx * W * 0.32, 0.0, 0.0))
            d = V(sx * 0.12, -0.12, -1.0).normalized()       # hangs along the (upright) torso
            p.cone(a, d, S * B * SP.get("flipperL", 0.62), S * W * 0.26, "wing1" + s, 8, flat=0.28)
        parts.append(p.finish())
    else:
        p = Part("folded", 5)
        y0, y1 = B * 0.34, -B * 0.5 - SP.get("foldTip", 0.08)
        zTop = zb + Rv * 0.55; chF = Rv * SP.get("foldChord", 1.05)
        for s, sx in (("L", 1), ("R", -1)):
            rows = []; NU = 14; NJ = 4; lastx = [None] * NJ
            for j in range(NJ):
                jj = j / (NJ - 1); row = []
                for k in range(NU + 1):
                    u = k / NU
                    y = y0 + (y1 - y0) * u
                    h = chF * math.sin(math.pi * min(1.0, 0.12 + u * 1.25)) ** 0.6 * (1 - 0.55 * u) + chF * 0.08
                    z = zTop - Rv * 0.3 * u * u - h * jj
                    pu = P(0, y, z)
                    loc, n = ray(bvh, U((sx * 2.0, pu.y, pu.z)), (-sx, 0, 0))
                    if loc is not None and (lastx[j] is None or abs(loc.x) > abs(lastx[j]) * 0.35):
                        co = loc + Vector((sx * S * (0.004 + 0.006 * (1 - jj)), 0, 0)); lastx[j] = co.x
                    else:
                        xx = lastx[j] if lastx[j] is not None else sx * S * W * 0.35
                        co = Vector((xx * (1 - 0.15 * u), pu.y * S, pu.z * S)); lastx[j] = co.x
                    row.append((co, "fold" + s, min(1.0, u * 1.1)))
                rows.append(row)
            p.grid(rows, flip=sx < 0, thickness=S * 0.0018)
        parts.append(p.finish())
        if "plumes" in FE:       # ostrich: loose white plumes on the wings and tail
            p = Part("plumes", 5)
            for s, sx in (("L", 1), ("R", -1)):
                for k in range(9):
                    yy = y1 + 0.02 + (y0 - y1) * 0.45 * k / 8
                    pu = P(0, yy, zb - Rv * 0.1)
                    loc, n = ray(bvh, U((sx * 2.0, pu.y, pu.z)), (-sx, 0, 0))
                    base = loc if loc is not None else U((sx * W * 0.4, pu.y, pu.z))
                    p.cone(base, (sx * 0.4, -1.0, -0.35 - 0.05 * k), S * random.uniform(0.12, 0.17), S * 0.03, "fold" + s, 5, flat=0.35, bend=(0, 0, -0.25))
            parts.append(p.finish())
    # ---- tail feathers
    p = Part("tailfeathers", 5)
    if "fan" in FE:              # turkey: display fan, authored open and raised
        tbw = U(tb); R = S * SP.get("fanR", 0.3); rows = []
        for j in range(4):
            row = []
            for k in range(13):
                a = (k / 12 - 0.5) * math.pi * 0.95; rr = R * (0.15 + 0.85 * j / 3)
                if j == 3: rr *= 1 - 0.06 * abs(math.sin(k * math.pi / 2))
                row.append((tbw + Vector((math.sin(a) * rr, -0.06 * rr - S * 0.01, math.cos(a) * rr)), "fan", j / 3))
            rows.append(row)
        p.grid(rows, thickness=S * 0.0025)
    else:
        tbw = U(tb); tlen = S * tail; rows = []
        for j in range(3):
            row = []
            for k in range(7):
                a = (k / 6 - 0.5) * SP.get("tailW", 0.7)
                L_ = tlen * (0.04 + 0.96 * j / 2) * (1 - SP.get("fork", 0.0) * (1 - abs(k / 3 - 1)))
                d = _rx(V(math.sin(a), -math.cos(a), SP.get("tailTilt", 0.0)), V(0, 0, 0), rp)
                row.append((tbw + d * L_, "tail", j / 2))
            rows.append(row)
        p.grid(rows, thickness=S * 0.002)
    parts.append(p.finish())
    info = dict(hip=hip, legs=legs, zb=zb, nN=nN, rp=rp, flight=flight and "flippers" not in FE)
    return body, rig, parts, info, mode

# ------------------------------------------------------------------------------------------- animation
def anim_bird(A, info):
    perch = SP.get("perch", 0.0); nN = info["nN"]; hip = info["hip"]; legs = info["legs"]
    flier = info["flight"]; flip = "flippers" in FE; fan = "fan" in FE
    upAng = SP.get("neckUp", 50.0); curve = SP.get("neckCurve", 0.0)
    X = (1, 0, 0)
    def R(b, deg, axis=X): return rotaxis(A, b, axis, deg)

    def fk(s, body, t1, t2, t3):
        """Foot height (unit) for local rotations about X: body, thigh, shin, tarsus."""
        hp, kn, an, ft = legs[s]
        g1 = body + t1; g2 = g1 + t2; g3 = g2 + t3
        y, z = hp.y - hip.y, hp.z - hip.z
        y, z = _r2(y, z, body); y += hip.y; z += hip.z
        for (a, b_), g in (((hp, kn), g1), ((kn, an), g2), ((an, ft), g3)):
            dy, dz = _r2(b_.y - a.y, b_.z - a.z, g); y += dy; z += dz
        return y, z

    def wings_folded(P):
        if flier:
            for s in "LR": P["wing1" + s] = (Quaternion(), BIRD_FOLDED)
        return P
    def wings_open(P, k=1.0):
        """k = 1 open, 0 folded (cross-scales the two wing sets)."""
        if flier:
            sc = BIRD_FOLDED + (1 - BIRD_FOLDED) * k
            for s in "LR":
                q = P.get("wing1" + s, Quaternion())
                if isinstance(q, tuple): q = q[0]
                P["wing1" + s] = (q, sc)
                fq = P.get("fold" + s, Quaternion())
                if isinstance(fq, tuple): fq = fq[0]
                P["fold" + s] = (fq, max(BIRD_FOLDED, 1 - k * (1 - BIRD_FOLDED) * 1.0))
        return P

    def neck_pose(P, body, lift=0.0, yaw=0.0, level=0.0, down=0.0):
        """Counter the torso pitch, then optionally straighten the neck to horizontal (level = 0..1, flight)."""
        straight = level * (upAng - 4)
        P["neck1"] = qmul(R("neck1", -body * SP.get("neckComp", 0.9) - straight + lift - down * 0.5), R("neck1", yaw, (0, 0, 1)))
        for k in range(2, nN + 1): P["neck%d" % k] = R("neck%d" % k, -level * curve - down * 0.5 / max(1, nN - 1))
        P["head"] = R("head", level * (upAng + curve * (nN - 1) - 4) + body * SP.get("neckComp", 0.9) - body - lift + down * 0.3)
        return P

    def ground(t1=(0, 0), t2=(0, 0), t3=(0, 0), body=None, lowest=True):
        """Torso pitch + legs; returns (P, root offset) with the lower foot on the ground."""
        body = perch if body is None else body
        P = {"body": R("body", body)}
        zs = []
        for i, s in enumerate("LR"):
            a1, a2, a3 = -body + t1[i], t2[i], t3[i]
            P["thigh" + s] = R("thigh" + s, a1); P["shin" + s] = R("shin" + s, a2); P["tars" + s] = R("tars" + s, a3)
            P["toe" + s] = R("toe" + s, -(body + a1 + a2 + a3))
            zs.append(fk(s, body, a1, a2, a3)[1])
        fz = min(zs) if lowest else zs[0]
        return P, (0, 0, -(fz - legs["L"][3].z) * S)

    def tail_pose(P, up=0.0, wag=0.0):
        P["tail"] = qmul(R("tail", -up), R("tail", wag, (0, 0, 1)))
        if fan: P["fan"] = (qmul(R("fan", 78), R("fan", wag * 0.5, (0, 1, 0))), (0.2, 0.8, 0.3))
        return P
    def flippers(P, out=0.0, fwd=0.0):
        if flip:
            for s, sx in (("L", 1), ("R", -1)): P["wing1" + s] = qmul(R("wing1" + s, -out * sx, (0, 1, 0)), R("wing1" + s, fwd))
        return P

    # ---------------- ground clips
    peck = "graze" in FE
    def idle(t):
        br = math.sin(2 * math.pi * t * 2)
        P, off = ground()
        g = seg(t, 0.35, 0.45) * (1 - seg(t, 0.62, 0.72)) if peck else 0.0
        yaw = 35 * math.sin(2 * math.pi * t) * (1 - g) + (55 * seg(t, 0.75, 0.8) * (1 - seg(t, 0.9, 0.95)) if "facedisc" in FE else 0)
        neck_pose(P, perch, lift=3 * br, yaw=yaw, down=g * SP.get("peckDown", 70) * (0.85 + 0.15 * math.sin(2 * math.pi * t * 12)))
        tail_pose(P, wag=6 * math.sin(2 * math.pi * t * 3) if "wag" in FE else 0)
        flippers(P, out=6 + 3 * br)
        return wings_folded(P), (off[0], off[1], off[2] + 0.004 * S * br)

    def stepper(amp, lift, stance, bob, sway=0.0, hop=False):
        def fn(t):
            t1, t2, t3 = [0, 0], [0, 0], [0, 0]
            for i, ph in enumerate((0.0, 0.5)):
                u = (t + (0 if hop else ph)) % 1.0
                if u < stance: sw = amp * (1 - 2 * u / stance); lf = 0.0
                else: q = (u - stance) / (1 - stance); sw = -amp * math.cos(math.pi * q); lf = math.sin(math.pi * q)
                t1[i] = sw + 25 * lf * lift; t2[i] = -70 * lf * lift; t3[i] = 55 * lf * lift
            P, off = ground(tuple(t1), tuple(t2), tuple(t3))
            P["body"] = qmul(P["body"], R("body", sway * math.sin(2 * math.pi * t), (0, 1, 0)))
            bobz = math.sin(4 * math.pi * t)
            neck_pose(P, perch, lift=-bob * 40 * bobz)
            tail_pose(P, wag=8 * math.sin(2 * math.pi * t) if sway else 0)
            flippers(P, out=14 + 6 * math.sin(2 * math.pi * t), fwd=0)
            if "runwings" in FE and amp > 30:
                for s, sx in (("L", 1), ("R", -1)):
                    P["fold" + s] = R("fold" + s, -sx * 35, (0, 1, 0))
            return wings_folded(P), (off[0], off[1], off[2] + (S * 0.06 * abs(math.sin(2 * math.pi * t)) if hop else 0))
        return fn

    def alert(t):
        P, off = ground()
        tw = math.sin(2 * math.pi * t * 2)
        neck_pose(P, perch, lift=15, yaw=40 * math.sin(2 * math.pi * t) if "facedisc" not in FE else 90 * math.sin(2 * math.pi * t))
        if fan:      # strut: fan raised and spread, wings drooped, head pulled back
            P["fan"] = (R("fan", -4 + 3 * tw), (1.0, 1.0, 1.0))
            for s, sx in (("L", 1), ("R", -1)): P["fold" + s] = qmul(R("fold" + s, 14), R("fold" + s, -sx * 12, (0, 1, 0)))
            P["tail"] = R("tail", -20)
        else:
            tail_pose(P, up=8)
        flippers(P, out=25)
        return wings_folded(P), off

    def sleep(t):
        br = math.sin(2 * math.pi * t)
        P, off = ground((40, 40), (-95, -95), (60, 60), body=perch * 0.5)
        P["neck1"] = R("neck1", -perch * 0.5 - SP.get("tuck", 35))
        for k in range(2, nN + 1): P["neck%d" % k] = R("neck%d" % k, -min(60.0, curve * 0.5 + 25))
        P["head"] = qmul(R("head", -20), R("head", 120 if nN >= 3 else 60, (0, 0, 1)))
        tail_pose(P)
        flippers(P, out=3)
        return wings_folded(P), (off[0], off[1], off[2] + 0.004 * S * br)

    # ---------------- flight clips
    tuck = ((-70, -70), (60, 60), (-80, -80))
    def flight_legs(P, k=1.0):
        for i, s in enumerate("LR"):
            P["thigh" + s] = R("thigh" + s, tuck[0][i] * k); P["shin" + s] = R("shin" + s, tuck[1][i] * k)
            P["tars" + s] = R("tars" + s, tuck[2][i] * k); P["toe" + s] = R("toe" + s, -30 * k)
        return P
    def flap_wings(P, ph, amp=1.0):
        w = math.sin(2 * math.pi * ph)
        for s in "LR":
            P["wing1" + s] = qmul(A.rot("wing1" + s, up=36 * w * amp + 4, fwd=8 * math.cos(2 * math.pi * ph) * amp))
            P["wing2" + s] = A.rot("wing2" + s, up=20 * math.sin(2 * math.pi * ph - 0.6) * amp)
            P["wing3" + s] = A.rot("wing3" + s, up=18 * math.sin(2 * math.pi * ph - 1.1) * amp, fwd=-10 * math.cos(2 * math.pi * ph - 1.1) * amp)
        return w
    def flap(t):
        P = {"body": R("body", 0)}
        flight_legs(P); w = flap_wings(P, t)
        neck_pose(P, 0, level=1.0, lift=3 * w)
        tail_pose(P, up=-4 * w)
        return wings_open(P, 1.0), (0, 0, -0.02 * S * w)
    def glide(t):
        g = math.sin(2 * math.pi * t)
        P = {"body": R("body", 0)}
        flight_legs(P)
        for s, sg in (("L", 1), ("R", -1)):
            P["wing1" + s] = A.rot("wing1" + s, up=SP.get("dihedral", 6) + 3 * g * sg)
            P["wing2" + s] = A.rot("wing2" + s, up=-2 + 2 * g); P["wing3" + s] = A.rot("wing3" + s, up=4 + 3 * math.sin(4 * math.pi * t))
        neck_pose(P, 0, level=1.0, yaw=14 * math.sin(2 * math.pi * t * 0.5 + 0.3))
        tail_pose(P, wag=5 * g)
        return wings_open(P, 1.0), (0, 0, 0.01 * S * g)
    def takeoff(t):
        crouch = seg(t, 0.0, 0.12) * (1 - seg(t, 0.12, 0.22))
        k = seg(t, 0.12, 0.42)                 # ground -> flight blend
        P, off = ground((30 * crouch, 30 * crouch), (-60 * crouch, -60 * crouch), (40 * crouch, 40 * crouch), body=perch * (1 - k) - 8 * seg(t, 0.15, 0.3) * (1 - seg(t, 0.5, 0.8)))
        if k > 0:
            F = {}; flight_legs(F, seg(t, 0.3, 0.7))
            for s in "LR":
                for b in ("thigh", "shin", "tars", "toe"): P[b + s] = P[b + s].slerp(F[b + s], seg(t, 0.25, 0.7))
        w = flap_wings(P, max(0.0, t - 0.12) * SP.get("takeoffFlaps", 4.0), amp=1.25)
        neck_pose(P, perch * (1 - k), level=k)
        tail_pose(P, up=-10 * k)
        wings_open(P, seg(t, 0.06, 0.3))
        return P, (0, 0, off[2] * (1 - k) - 0.02 * S * w * k)
    def land(t):
        k = 1 - seg(t, 0.55, 0.85)             # flight -> ground blend
        P, off = ground(body=perch * (1 - k) + 25 * k * seg(t, 0.15, 0.55))
        F = {}; flight_legs(F, 1 - seg(t, 0.0, 0.45))
        for i, s in enumerate("LR"):
            reach = R("thigh" + s, 45 * seg(t, 0.25, 0.5) * k)
            for b in ("thigh", "shin", "tars", "toe"):
                q = P[b + s].slerp(F[b + s], k)
                P[b + s] = qmul(q, reach) if b == "thigh" else q
        if t < 0.75:
            w = flap_wings(P, t * SP.get("landFlaps", 2.5), amp=0.9 + 0.4 * seg(t, 0.3, 0.6))
            for s in "LR": P["wing1" + s] = qmul(P["wing1" + s], A.rot("wing1" + s, fwd=-25 * seg(t, 0.2, 0.55)))
        neck_pose(P, perch * (1 - k), level=k)
        tail_pose(P, up=25 * k * seg(t, 0.2, 0.5))
        wings_open(P, 1 - seg(t, 0.62, 0.95))
        return P, (0, 0, off[2] * (1 - k))

    # ---------------- water clips (feet at the waterline offset; torso level)
    swimBody = -info["rp"] if flip else 0.0
    def paddle(rate, amp):
        def fn(t):
            P = {"body": R("body", swimBody)}
            for i, (s, ph) in enumerate((("L", 0.0), ("R", 0.5))):
                w = math.sin(2 * math.pi * (t * rate + ph))
                P["thigh" + s] = R("thigh" + s, -swimBody - 20 + amp * w)
                P["shin" + s] = R("shin" + s, -25 + 20 * w); P["tars" + s] = R("tars" + s, 30 - 25 * max(0, w))
                P["toe" + s] = R("toe" + s, -10)
            if flip:     # penguins fly underwater with their flippers
                for s, sx in (("L", 1), ("R", -1)):
                    P["wing1" + s] = qmul(R("wing1" + s, -sx * 70, (0, 1, 0)), R("wing1" + s, 20 * math.sin(2 * math.pi * t * rate)))
                P["neck1"] = R("neck1", 0); P["head"] = R("head", -swimBody * 0.85)
            else:
                neck_pose(P, 0, lift=-6, yaw=10 * math.sin(2 * math.pi * t))
            dab = 0.0
            if "dabble" in FE and amp < 20:   # dabbling: tail up, head under, in the float clip
                dab = seg(t, 0.55, 0.62) * (1 - seg(t, 0.78, 0.85))
                P["body"] = R("body", -48 * dab)
                P["neck1"] = qmul(P["neck1"], R("neck1", -40 * dab))
            tail_pose(P, up=4 * math.sin(2 * math.pi * t) + 30 * dab)
            return wings_folded(P), (0, 0, 0.003 * S * math.sin(2 * math.pi * t * 2))
        return fn

    # ---------------- assemble
    Lg = (hip.z) * S
    amp_w, amp_r = SP.get("stepAmp", 24.0), SP.get("runAmp", 38.0)
    sweep_w = 2 * Lg * math.sin(math.radians(amp_w)); sweep_r = 2 * Lg * math.sin(math.radians(amp_r))
    Tw = max(0.3, min(2.0, sweep_w / (0.55 * SP["speed"]))); Tr = max(0.25, min(1.2, sweep_r / (0.45 * SP["fleeSpeed"])))
    fw, fr = max(8, int(round(Tw * 30))), max(8, int(round(Tr * 30)))
    hop = "hophop" in FE
    clips = [("idle", idle, 150, 3, False), ("walk", stepper(amp_w, 1.0, 0.55, SP.get("headBob", 0.3), SP.get("waddle", 0.0), hop), fw, 1, False),
             ("alert", alert, 90, 3, False), ("sleep", sleep, 120, 6, False)]
    cfg = dict(idleAnim="idle", moveAnim="walk", alertAnim="alert", sleepAnim="sleep",
               moveAnimSpeed=round(sweep_w / (0.55 * fw / 30), 2))
    if SP.get("runs", not flier):
        clips.append(("run", stepper(amp_r, 1.3, 0.42, SP.get("headBob", 0.3) * 0.4, SP.get("waddle", 0.0) * 0.6, hop), fr, 1, False))
        cfg.update(fleeAnim="run", fleeAnimSpeed=round(sweep_r / (0.45 * fr / 30), 2))
    else:
        cfg.update(fleeAnim="walk", fleeAnimSpeed=cfg["moveAnimSpeed"])
    if flier:
        fl = SP.get("flapFrames", 18)
        clips += [("glide", glide, 150, 3, False), ("flap", flap, fl, 1, False), ("takeoff", takeoff, 36, 1, True), ("land", land, 36, 1, True)]
        cfg.update(glideAnim="glide", flapAnim="flap", takeoffAnim="takeoff", landAnim="land")
    if SP.get("swims"):
        clips += [("swim", paddle(2.0, 28), 30, 1, False), ("float", paddle(0.5, 10), 180, 3, False)]
        cfg.update(swimAnim="swim", floatAnim="float", swimAnimSpeed=SP.get("swimSpeed", SP["speed"]))
        cfg["waterline"] = round((hip.z if flip else (info["zb"] - SP["Rv"] * 0.35)) * S, 3)
    return clips, cfg

BUILD["bird"] = (build_bird, anim_bird)

# =============================================================================== quadruped extras (Kerbin mammals)
# Features: roundears, bisonhorns, mbeard, claws, brush (bushy tail). Clips: rears (alert = stand up on the hind legs),
# swipe (attackAnim), howl (roarAnim: sits and howls), swim/float (swimmers).
_quad_feats_base = quad_feats
def quad_feats(L):
    parts = _quad_feats_base(L)
    sk, bvh, hc, hcw, hr, zb, W, B, legH = L["sk"], L["bvh"], L["hc"], L["hcw"], L["hr"], L["zb"], L["W"], L["B"], L["legH"]
    if "roundears" in FE:
        p = Part("rears", 0)
        for sx in (1, -1):
            p.sphere(hcw + U((sx * hr * 0.62, -hr * 0.35, hr * 0.72)), S * hr * SP.get("earR", 0.32), "head", scale=(1.0, 0.45, 0.95), sub=2)
        parts.append(p.finish())
    if "bisonhorns" in FE:
        p = Part("bhorns", 2)
        for sx in (1, -1):
            p.cone(hcw + U((sx * hr * 0.7, -hr * 0.2, hr * 0.45)), (sx * 1.0, 0.0, 0.35), S * hr * 0.9, S * hr * 0.17, "head", 7, bend=(-sx * 0.2, 0.15, 0.9))
        parts.append(p.finish())
    if "mbeard" in FE:
        p = Part("mbeard", 4)
        for k in range(26):
            c = hcw + U((random.uniform(-hr * 0.35, hr * 0.35), hr * random.uniform(0.0, 0.8), -hr * 0.75))
            p.cone(c, (random.uniform(-0.15, 0.15), -0.15, -1), S * hr * random.uniform(0.5, 0.9), S * hr * 0.09, "head", 4)
        parts.append(p.finish())
    if "claws" in FE:
        p = Part("pclaws", 2)
        for s in "LR":
            for f, bn in (("tf", "ftF"), ("th", "ftH")):
                c = sk.pt(f + s)
                for k in range(5):
                    a = (k / 4 - 0.5) * 1.1
                    p.cone(c + Vector((math.sin(a) * S * W * 0.05, S * SP.get("legR", 0.05) * 0.7, S * 0.004)), (math.sin(a) * 0.3, 1, -0.5), S * SP.get("clawL", 0.035) * (1.3 if f == "tf" else 1.0), S * 0.006, bn + s, 4, bend=(0, 0, -0.8))
        parts.append(p.finish())
    if "brush" in FE:            # wolf: bushy tail
        p = Part("brush", 4)
        for (a_, b_, bn) in (("t1", "t2", "tail2"), ("t2", "t3", "tail3")):
            A_, B_ = sk.pt(a_), sk.pt(b_)
            for k in range(40):
                q = random.random(); c = A_.lerp(B_, q)
                d = Vector((random.uniform(-1, 1), random.uniform(-0.3, -0.1), random.uniform(-1, 1))).normalized()
                p.cone(c, (d + Vector((0, -1.2, 0))).normalized(), S * random.uniform(0.04, 0.07), S * SP.get("tailR", 0.04) * 0.6, bn, 4)
        parts.append(p.finish())
    return parts

_anim_quad_base = anim_quad
def anim_quad_ext(A, info):
    clips, cfg = _anim_quad_base(A, info)
    X = (1, 0, 0)
    def R(b, deg, axis=X): return rotaxis(A, b, axis, deg)
    zb = info["zb"]
    if "rears" in FE:            # alert: stands up on the hind legs to look and smell
        def rear(t):
            k = seg(t, 0.0, 0.25) * (1 - seg(t, 0.8, 1.0)); sn = math.sin(2 * math.pi * t * 3)
            P = {"body": R("body", 52 * k)}
            for s in "LR":
                P["upH" + s] = R("upH" + s, -52 * k + 10 * k); P["loH" + s] = R("loH" + s, -12 * k); P["ftH" + s] = R("ftH" + s, 2 * k)
                P["upF" + s] = R("upF" + s, -30 * k); P["loF" + s] = R("loF" + s, 60 * k); P["ftF" + s] = R("ftF" + s, 30 * k)
            P["neck"] = R("neck", -35 * k + 4 * sn * k); P["head"] = qmul(R("head", -10 * k + 6 * sn), R("head", 15 * math.sin(2 * math.pi * t), (0, 0, 1)))
            return P, (0, 0, -S * 0.02 * k)
        clips = [c for c in clips if c[0] != "alert"] + [("alert", rear, 120, 2, False)]
    if "swipe" in FE:            # attack: half-rears and rakes with a forepaw
        def swipe(t):
            k = seg(t, 0.0, 0.3) * (1 - seg(t, 0.75, 1.0)); hit = seg(t, 0.32, 0.5)
            P = {"body": R("body", 28 * k)}
            for s in "LR": P["upH" + s] = R("upH" + s, -28 * k)
            P["upFR"] = qmul(R("upFR", (-40 + 100 * hit) * k), R("upFR", -25 * hit * k, (0, 1, 0))); P["loFR"] = R("loFR", (70 - 50 * hit) * k)
            P["upFL"] = R("upFL", -10 * k)
            P["neck"] = R("neck", -10 * k); P["head"] = R("head", 15 * hit * k)
            return P, (0, 0, 0)
        clips.append(("swipe", swipe, 30, 1, True)); cfg["attackAnim"] = "swipe"
    if "howl" in FE:             # sits back on its haunches, muzzle to the sky
        def howl(t):
            k = seg(t, 0.0, 0.2) * (1 - seg(t, 0.85, 1.0)); w = math.sin(2 * math.pi * t * 4) * seg(t, 0.25, 0.4) * (1 - seg(t, 0.7, 0.8))
            P = {"body": R("body", 30 * k)}
            for s in "LR":
                P["upH" + s] = R("upH" + s, -30 * k + 55 * k); P["loH" + s] = R("loH" + s, -110 * k); P["ftH" + s] = R("ftH" + s, 85 * k)
                P["upF" + s] = R("upF" + s, -25 * k); P["ftF" + s] = R("ftF" + s, 25 * k)
            P["neck"] = R("neck", 25 * k); P["head"] = R("head", 35 * k + 3 * w)
            for i, b in enumerate(("tail1", "tail2", "tail3")): P[b] = R(b, 10 * k)
            return P, (0, 0, -S * info["zb"] * 0.32 * k)
        clips.append(("howl", howl, 120, 2, True)); cfg["roarAnim"] = "howl"
    if SP.get("swims"):          # dog-paddle with the head held up
        def paddle(rate, amp):
            def fn(t):
                P = {}
                for s, ph in (("L", 0.0), ("R", 0.5)):
                    for f, o in (("F", 0.0), ("H", 0.25)):
                        w = math.sin(2 * math.pi * (t * rate + ph + o))
                        P["up" + f + s] = R("up" + f + s, amp * w - 10); P["lo" + f + s] = R("lo" + f + s, -25 + 20 * w)
                P["neck"] = R("neck", 12); P["head"] = R("head", -6 + 3 * math.sin(2 * math.pi * t))
                for i, b in enumerate(("tail1", "tail2", "tail3")): P[b] = R(b, 0, (0, 0, 1))
                return P, (0, 0, 0.004 * S * math.sin(2 * math.pi * t * 2))
            return fn
        clips += [("swim", paddle(2.0, 35), 30, 1, False), ("float", paddle(0.5, 8), 150, 3, False)]
        cfg.update(swimAnim="swim", floatAnim="float", swimAnimSpeed=SP.get("swimSpeed", SP["speed"]))
        cfg["waterline"] = round((zb + SP["Rv"] * 0.35) * S, 3)
    return clips, cfg
BUILD["quad"] = (build_quad, anim_quad_ext)
exec(open(os.path.join(TOOLS, "fauna_mammals.py"), encoding="utf-8").read(), globals())
