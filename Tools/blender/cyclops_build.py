# Xenobiology — the Cyclops (Gigantokerbus polyphemi), 25 m tall. Model, texture, animations, export, icons.
import bpy, os, math, random
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())

NAME = "cyclops"
STEP = globals().get("STEP", "all")      # "model", "all"
random.seed(31)
new_scene("Cyclops")

# ---------------------------------------------------------------- skeleton (metres)
sk = Skel()
sk.v("pelvis", 0, 0.0, 10.6, 3.5, 3.0)
sk.v("belly", 0, 0.5, 13.0, 4.0, 3.8)
sk.v("chest", 0, 0.2, 16.0, 4.2, 3.4)
sk.v("upchest", 0, -0.1, 17.8, 3.6, 2.6)
sk.v("neck", 0, 0.6, 19.3, 1.9, 1.9)
sk.v("head", 0, 1.4, 21.8, 4.0, 3.7)
sk.v("crown", 0, 1.0, 23.4, 3.6, 3.0)
sk.v("jaw", 0, 2.4, 20.3, 1.9, 1.3)
sk.e("pelvis", "belly", "chest", "upchest", "neck", "head", "crown")
sk.e("head", "jaw")
for s, sx in (("L", 1), ("R", -1)):
    sk.v("sh"+s, sx*4.5, -0.1, 17.6, 1.6)
    sk.v("el"+s, sx*6.6, -0.5, 12.6, 1.25)
    sk.v("wr"+s, sx*7.2, 0.6, 8.4, 0.95)
    sk.v("hand"+s, sx*7.4, 1.1, 6.8, 1.15, 1.0)
    sk.v("hip"+s, sx*2.2, 0.0, 10.0, 2.0)
    sk.v("kn"+s, sx*2.6, 0.7, 5.3, 1.5)
    sk.v("an"+s, sx*2.7, 0.0, 1.1, 1.1)
    sk.v("toe"+s, sx*2.9, 2.1, 0.45, 1.05, 0.5)
    sk.e("upchest", "sh"+s, "el"+s, "wr"+s, "hand"+s)
    sk.e("pelvis", "hip"+s, "kn"+s, "an"+s, "toe"+s)

body = metaball_body(NAME, sk, voxel=0.16, faces=11000)
# muscle and gut definition, flatter face plane where the eye sits
def shape(co, n):
    if co.y > 2.3 and 20.2 < co.z < 23.5 and abs(co.x) < 2.6:      # flatten the face a little
        co.y -= (co.y - 2.3) * 0.35
    if 14.0 < co.z < 17.5 and abs(co.x) < 3.5 and co.y > 1.5:      # pectoral ridge
        co.y += 0.25 * math.sin((co.z - 14.0) / 3.5 * math.pi)
    nn = noise.noise(co * 0.35) * 0.18 + noise.noise(co * 1.3) * 0.05
    co += n * nn
    if co.z < 0: co.z = 0
    return co
displace(body, shape)

bones = [("body", "pelvis", "belly", None, False), ("spine", "belly", "chest", "body", True), ("chest", "chest", "upchest", "spine", True),
         ("neck", "upchest", "neck", "chest", True), ("head", "neck", "crown", "neck", True), ("jaw", (0, 1.4, 20.6), (0, 3.2, 19.6), "head", False)]
for s in "LR":
    bones += [("upperarm"+s, "sh"+s, "el"+s, "chest", False), ("forearm"+s, "el"+s, "wr"+s, "upperarm"+s, True), ("hand"+s, "wr"+s, "hand"+s, "forearm"+s, True),
              ("thigh"+s, "hip"+s, "kn"+s, "body", False), ("shin"+s, "kn"+s, "an"+s, "thigh"+s, True), ("foot"+s, "an"+s, "toe"+s, "shin"+s, True)]
rig = make_rig(NAME, sk, bones, nondeform=("jaw",))
mode = skin(body, rig, nondeform=("jaw",))
bvh = bvh_of(body)
parts = []

# ---- the eye: a single huge eyeball set under a heavy brow
eye_loc, eye_n = ray(bvh, (0, 12, 21.9), (0, -1, 0))
eye_c = eye_loc - eye_n * 0.55
p = Part("eye", 3); p.sphere(eye_c, 1.35, "head", sub=3); parts.append(p.finish())
p = Part("brow", 0)
for i in range(9):
    t = i / 8 - 0.5
    loc, n = ray(bvh, (t * 3.6, 12, 23.05 - 0.6 * t * t), (0, -1, 0))
    if loc: p.sphere(loc + Vector((0, 0.25, 0.1)), 0.65, "head", scale=(1.3, 0.9, 0.7), sub=1)
parts.append(p.finish())
# ---- wild mane and beard: clumps of hair as bent cones
p = Part("hair", 4)
for i in range(70):
    a = random.uniform(-2.6, 2.6); el = random.uniform(-0.2, 1.4)
    d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el) * 0.9 - 0.15, math.sin(el)))
    loc, n = ray(bvh, Vector((0, 1.1, 22.0)) + d * 9, -d)
    if loc is None or loc.y > 2.4: continue
    p.cone(loc - n * 0.2, (n + Vector((0, -0.6, -0.5))).normalized(), random.uniform(1.4, 3.0), random.uniform(0.45, 0.8), "head", 5, bend=(0, -0.4, -0.8))
for i in range(26):
    x = random.uniform(-1.9, 1.9); z = random.uniform(19.2, 20.6)
    loc, n = ray(bvh, (x, 10, z), (0, -1, 0))
    if loc is None: continue
    p.cone(loc - n * 0.15, (0, 0.35, -1.0), random.uniform(1.5, 3.2), random.uniform(0.35, 0.6), "jaw", 5, bend=(0, 0.2, -0.3))
parts.append(p.finish())
# ---- mouth (dark slit with tusk-teeth) and a little kerbal nose
p = Part("mouth", 5)
loc, n = ray(bvh, (0, 12, 20.25), (0, -1, 0))
for i in range(11):
    t = i / 10 - 0.5
    l2, n2 = ray(bvh, (t * 2.6, 12, 20.25 - 0.35 * (t * 2) ** 2), (0, -1, 0))
    if l2: p.sphere(l2 - n2 * 0.05, 0.22, "jaw", scale=(1.6, 0.6, 0.6), sub=1)
parts.append(p.finish())
p = Part("tusks", 2)
for sx in (1, -1):
    l2, n2 = ray(bvh, (sx * 0.9, 12, 20.1), (0, -1, 0))
    if l2: p.cone(l2 + Vector((0, 0.05, -0.1)), (sx * 0.15, 0.35, 1.0), 0.75, 0.16, "jaw", 6)
parts.append(p.finish())
# ---- hide wrap: a ragged skirt round the hips and a pelt over the left shoulder
p = Part("hide", 1)
rows = []
for j in range(5):
    z = 11.8 - j * 1.0
    row = []
    for k in range(25):
        a = k / 24 * math.tau
        rad = 3.9 + j * 0.28 + (0.35 * math.sin(a * 5) if j == 4 else 0)
        zz = z - (0.5 * abs(math.sin(a * 3.5)) if j == 4 else 0)
        co = Vector((math.cos(a) * rad, math.sin(a) * rad * 0.82 + 0.2, zz))
        if j < 2: w = [("body", 1.0)]
        else:
            leg = "thighL" if co.x > 0 else "thighR"
            f = min(1.0, abs(co.x) / 2.5) * (j - 1) / 3
            w = [("body", 1 - f), (leg, f)]
        row.append((co, w, j / 4))
    rows.append(row)
p.grid(rows, thickness=0.06)
cape = []
for j in range(5):
    row = []
    for k in range(6):
        u = k / 5; t = j / 4
        co = Vector((1.2 + 3.8 * u, -1.6 + 3.6 * t * 0.9, 18.6 - 4.5 * t - 0.6 * math.sin(u * math.pi)))
        loc, n = ray(bvh, co + Vector((0, 0, 6)), (0, 0, -1)) if t < 0.3 else (None, None)
        if loc is not None: co = loc + n * 0.25
        else: co.z -= 0.0
        w = [("chest", 1 - t * 0.6), ("upperarmL", t * 0.6 * u)]
        row.append((co, w, t))
    cape.append(row)
p.grid(cape, thickness=0.06)
parts.append(p.finish())
# ---- the club: a gnarled olive trunk in the right hand, resting on the ground
p = Part("club", 6)
hand = sk.pt("handR"); top = hand + Vector((-0.3, 1.3, 1.0)); bottom = hand + Vector((-0.6, 3.4, -6.1))
axis = (bottom - top); L = axis.length; d = axis.normalized(); q = d.to_track_quat('Z', 'Y').to_matrix(); R = []
for i in range(13):
    t = i / 12; r = 0.55 + 0.75 * t ** 1.5
    ring = []
    for k in range(8):
        a = k / 8 * math.tau
        knot = 0.18 * max(0.0, noise.noise(Vector((t * 6, k * 0.8, 3.1))))
        ring.append(p.v(top + d * L * t + q @ Vector((math.cos(a) * (r + knot), math.sin(a) * (r + knot), 0)), "handR", t))
    R.append(ring)
for i in range(12):
    for k in range(8): p.f([R[i][k], R[i][(k+1) % 8], R[i+1][(k+1) % 8], R[i+1][k]])
p.f(R[0][::-1]); p.f(R[-1])
for i in range(4):
    t = 0.3 + 0.15 * i; base = top + d * L * t
    p.cone(base, (random.uniform(-1, 1), random.uniform(-1, 1), 0.3), 0.9, 0.22, "handR", 5)
parts.append(p.finish())
# ---- big three-fingered hands with a thumb
p = Part("fingers", 0)
for s, sx in (("L", 1), ("R", -1)):
    h = sk.pt("hand"+s)
    for k, (dx, dy) in enumerate(((0.45, 0.55), (0.0, 0.75), (-0.45, 0.55))):
        base = h + Vector((sx * dx * 0.9, dy * 0.6, -0.6))
        p.cone(base, (sx * dx * 0.3, 0.35, -1.0), 1.7, 0.42, "hand"+s, 6, bend=(0, 0.5, 0.2))
    p.cone(h + Vector((-sx * 0.2, 0.9, 0.2)), (-sx * 0.3, 1.0, -0.4), 1.2, 0.38, "hand"+s, 6)
parts.append(p.finish())
# ---- toenails / fingernails
p = Part("nails", 2)
for s, sx in (("L", 1), ("R", -1)):
    toe = sk.pt("toe"+s)
    for k in (-1, 0, 1):
        p.sphere(toe + Vector((sx * 0.1 + k * 0.55, 0.85, 0.2)), 0.28, "foot"+s, scale=(1, 0.6, 0.45), sub=1)
parts.append(p.finish())

body = join_all(body, parts, NAME)
root = finalize(NAME, body, rig)
result = {"model": {"verts": len(body.data.vertices), "tris": sum(len(f.vertices) - 2 for f in body.data.polygons), "weights": mode,
                    "dims": [round(x, 1) for x in body.dimensions]}}

if STEP != "model":
    # ---------------------------------------------------------------- texture
    uv_unwrap(body)
    def nodes(N):
        skin = N.countershade((0.50, 0.58, 0.36), (0.40, 0.50, 0.28), (0.34, 0.43, 0.24), 0.5)
        skin = N.mul(skin, N.m('ADD', N.m('MULTIPLY', N.noise(0.6, 6), 0.45), 0.78))
        pores = N.voronoi(3.0, 'DISTANCE_TO_EDGE')
        skin = N.mix(skin, (0.18, 0.22, 0.12), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.m('MULTIPLY', pores, 12.0, clamp=True)), 0.25))
        # weathered, sun-darkened shoulders and scars
        scars = N.m('MULTIPLY', N.m('GREATER_THAN', N.noise(0.9, 2), 0.72), N.m('GREATER_THAN', N.wave(1.4, 'BANDS', 'Z', 3.0), 0.97))
        skin = N.mix(skin, (0.58, 0.55, 0.42), N.m('MULTIPLY', scars, 0.7))
        # eye: white, amber iris, black slit pupil, by distance from the eye's front point
        dx = N.m('SUBTRACT', N.X, 0.0); dz = N.m('SUBTRACT', N.Z, eye_c.z)
        rr = N.m('SQRT', N.m('ADD', N.m('MULTIPLY', dx, dx), N.m('MULTIPLY', dz, dz)))
        eye = N.ramp(N.m('DIVIDE', rr, 1.35), [(0.0, (0.02, 0.02, 0.02)), (0.12, (0.02, 0.02, 0.02)), (0.14, (0.85, 0.55, 0.08)), (0.45, (0.95, 0.70, 0.15)),
                                                  (0.5, (0.25, 0.12, 0.03)), (0.53, (0.93, 0.92, 0.86)), (0.9, (0.88, 0.80, 0.78)), (1.0, (0.7, 0.4, 0.4))])
        hide = N.mix((0.40, 0.42, 0.36), (0.28, 0.62, 0.58), N.m('LESS_THAN', N.voronoi(1.2), 0.12))    # mossback hide, teal spots
        hide = N.mul(hide, N.m('ADD', N.m('MULTIPLY', N.noise(2.5, 8), 0.5), 0.7))
        hide = N.mix(hide, (0.22, 0.18, 0.12), N.m('MULTIPLY', N.m('GREATER_THAN', N.tipf, 0.9), 0.8))
        hair = N.mix((0.12, 0.09, 0.07), (0.30, 0.24, 0.17), N.m('MULTIPLY', N.wave(3.0, 'BANDS', 'Z', 12.0), N.tipf))
        bone = N.mix((0.85, 0.80, 0.66), (0.55, 0.48, 0.36), N.tipf)
        mouth = (0.18, 0.06, 0.05)
        bark = N.mul((0.36, 0.27, 0.17), N.m('ADD', N.m('MULTIPLY', N.wave(1.5, 'BANDS', 'Z', 14.0), 0.5), 0.6))
        col = skin
        col = N.mix(col, hide, N.is_part(1)); col = N.mix(col, bone, N.is_part(2)); col = N.mix(col, eye, N.is_part(3))
        col = N.mix(col, hair, N.is_part(4)); col = N.mix(col, mouth, N.is_part(5)); col = N.mix(col, bark, N.is_part(6))
        glow = N.mix((0, 0, 0), (0.45, 0.28, 0.02), N.m('MULTIPLY', N.is_part(3), N.m('LESS_THAN', N.m('DIVIDE', rr, 1.35), 0.47)))
        return col, glow
    bake_and_material(body, NAME, os.path.join(XENO_DIR, "Models", "Kerbin", "Cyclops"), nodes, res=2048, glow_res=256)

    # ---------------------------------------------------------------- animations
    A = Anim(rig)
    def legs_walk(P, t, amp, lift_amt):
        for s, ph in (("L", 0.0), ("R", 0.5)):
            u = (t + ph) % 1.0
            if u < 0.6: sw = amp * (1 - 2 * u / 0.6); lift = 0.0
            else: q = (u - 0.6) / 0.4; sw = -amp * math.cos(math.pi * q); lift = math.sin(math.pi * q)
            P["thigh"+s] = A.rot("thigh"+s, fwd=sw + 10 * lift)
            P["shin"+s] = A.rot("shin"+s, fwd=-lift * lift_amt - 4)
            P["foot"+s] = A.rot("foot"+s, fwd=lift * 15 - (sw * 0.3 if u < 0.6 else 0))
    def arms_swing(P, t, amp):
        for s, ph in (("L", 0.5), ("R", 0.0)):
            sw = amp * math.sin(2 * math.pi * (t + ph))
            P["upperarm"+s] = A.rot("upperarm"+s, fwd=sw * (0.5 if s == "R" else 1.0))
            P["forearm"+s] = A.rot("forearm"+s, fwd=8 + max(0, sw) * 0.5)
    def idle(t):
        P = {}; br = math.sin(2 * math.pi * t * 2)
        P["spine"] = A.rot("spine", up=0.8 * br); P["chest"] = A.rot("chest", up=1.0 * br)
        P["neck"] = A.rot("neck", yaw=14 * math.sin(2 * math.pi * t), up=-2)
        P["head"] = A.rot("head", yaw=10 * math.sin(2 * math.pi * t + 0.6), up=3 * math.sin(4 * math.pi * t))
        P["upperarmL"] = A.rot("upperarmL", fwd=4 * br, out=4)
        P["forearmL"] = A.rot("forearmL", fwd=10)
        tap = max(0.0, math.sin(2 * math.pi * t * 2)) ** 4
        P["upperarmR"] = A.rot("upperarmR", fwd=6 * tap); P["forearmR"] = A.rot("forearmR", fwd=12 * tap)
        return P, (0, 0, 0.05 * br)
    def walk(t):
        P = {}
        legs_walk(P, t, 24.0, 40.0); arms_swing(P, t, 14.0)
        P["body"] = A.rot("body", roll=3 * math.sin(2 * math.pi * t), yaw=4 * math.sin(2 * math.pi * t))
        P["chest"] = A.rot("chest", yaw=-6 * math.sin(2 * math.pi * t), up=-4)
        P["neck"] = A.rot("neck", up=2 * math.sin(4 * math.pi * t))
        P["head"] = A.rot("head", yaw=3 * math.sin(2 * math.pi * t))
        return P, (0, 0, -0.45 * abs(math.cos(2 * math.pi * t)))
    def roar(t):
        P = {}; sh = math.sin(2 * math.pi * t * 6) * seg(t, 0.15, 0.3) * (1 - seg(t, 0.75, 0.95))
        lift = seg(t, 0.0, 0.25) * (1 - seg(t, 0.8, 1.0))
        P["spine"] = A.rot("spine", up=6 * lift); P["chest"] = A.rot("chest", up=8 * lift)
        P["neck"] = A.rot("neck", up=10 * lift); P["head"] = A.rot("head", up=14 * lift, yaw=4 * sh)
        P["jaw"] = A.rot("jaw", up=-30 * lift - 4 * sh)
        for s in "LR":
            P["upperarm"+s] = A.rot("upperarm"+s, out=72 * lift, fwd=8 * lift)
            P["forearm"+s] = A.rot("forearm"+s, out=35 * lift, fwd=20 * lift + 6 * sh)
        return P, (0, 0, 0)
    def throw(t):
        P = {}
        crouch = seg(t, 0.0, 0.25) * (1 - seg(t, 0.32, 0.48))
        wind = seg(t, 0.38, 0.55) * (1 - seg(t, 0.58, 0.66))
        rel = seg(t, 0.58, 0.68) * (1 - seg(t, 0.75, 1.0))
        P["body"] = A.rot("body", up=-22 * crouch, yaw=-12 * wind + 18 * rel)
        P["spine"] = A.rot("spine", up=-16 * crouch + 8 * wind - 10 * rel, yaw=-10 * wind + 10 * rel)
        P["chest"] = A.rot("chest", yaw=-12 * wind + 14 * rel)
        P["neck"] = A.rot("neck", up=10 * crouch)
        for s in "LR":
            P["thigh"+s] = A.rot("thigh"+s, fwd=30 * crouch); P["shin"+s] = A.rot("shin"+s, fwd=-45 * crouch); P["foot"+s] = A.rot("foot"+s, fwd=15 * crouch)
        # left arm reaches down for a boulder, swings it overhead and hurls it
        P["upperarmL"] = A.rot("upperarmL", fwd=45 * crouch - 140 * wind + 70 * rel, out=15 * wind)
        P["forearmL"] = A.rot("forearmL", fwd=20 * crouch + 60 * wind - 10 * rel)
        P["upperarmR"] = A.rot("upperarmR", fwd=10 * crouch, out=15 * wind)
        return P, (0, 0, -1.2 * crouch)
    def smash(t):
        P = {}
        up_ = seg(t, 0.05, 0.40) * (1 - seg(t, 0.45, 0.55))
        hit = seg(t, 0.45, 0.55) * (1 - seg(t, 0.7, 1.0))
        P["spine"] = A.rot("spine", up=6 * up_ - 16 * hit); P["chest"] = A.rot("chest", up=8 * up_ - 10 * hit)
        P["upperarmR"] = A.rot("upperarmR", fwd=150 * up_ + 50 * hit, out=-10 * up_)
        P["forearmR"] = A.rot("forearmR", fwd=50 * up_ + 5 * hit)
        P["upperarmL"] = A.rot("upperarmL", fwd=40 * up_ + 30 * hit, out=20 * up_)
        P["forearmL"] = A.rot("forearmL", fwd=30 * up_)
        for s in "LR":
            P["thigh"+s] = A.rot("thigh"+s, fwd=16 * hit); P["shin"+s] = A.rot("shin"+s, fwd=-24 * hit)
        P["jaw"] = A.rot("jaw", up=-20 * hit)
        return P, (0, 0, -0.9 * hit)
    def sleep(t):
        P = {}; br = math.sin(2 * math.pi * t * 2)
        # sitting slumped against the cave wall, legs out, club across the lap
        P["body"] = A.rot("body", up=-6)
        for s in "LR":
            P["thigh"+s] = A.rot("thigh"+s, fwd=85, out=10); P["shin"+s] = A.rot("shin"+s, fwd=-20); P["foot"+s] = A.rot("foot"+s, fwd=-10)
            P["upperarm"+s] = A.rot("upperarm"+s, fwd=25, out=12); P["forearm"+s] = A.rot("forearm"+s, fwd=40)
        P["spine"] = A.rot("spine", up=-8 + 1.5 * br); P["chest"] = A.rot("chest", up=-10 + 1.5 * br)
        P["neck"] = A.rot("neck", up=-22, yaw=12); P["head"] = A.rot("head", up=-10 + 2 * br)
        P["jaw"] = A.rot("jaw", up=-8 * max(0, br))
        return P, (0, 0, -8.6)
    clips = A.bake([("idle", idle, 150, 5, False), ("walk", walk, 78, 3, False), ("roar", roar, 90, 3, True),
                    ("throw", throw, 96, 2, True), ("smash", smash, 66, 2, True), ("sleep", sleep, 150, 5, False)], default="walk")
    result["clips"] = clips
    result["export"] = export_mu(NAME, os.path.join(XENO_DIR, "Models", "Kerbin", "Cyclops", "cyclops.mu"))
    # ---------------------------------------------------------------- review renders + icons
    cam, g = stage_setup()
    for clip, f, nm in (("idle", 0, "idle"), ("walk", 20, "walk"), ("roar", 40, "roar"), ("throw", 55, "throw"), ("smash", 30, "smash"), ("sleep", 0, "sleep")):
        set_clip(rig, clip, f); look_at(cam, (38, 46, 20), (0, 0, 12))
        cam.data.type = 'PERSP'; cam.data.lens = 40
        render(os.path.join(PREVIEW_DIR, "cyclops_" + nm + ".png"), res=(960, 720))
    set_clip(rig, "idle", 0); look_at(cam, (6, 22, 22), (0, 1.5, 21))
    render(os.path.join(PREVIEW_DIR, "cyclops_face.png"), res=(960, 720))
    icon_renders(rig, "cyclops", "idle", 0, ((0, 60, 12.5), (0, 0, 12.5)), 27.0, "roar", 40, ((26, 36, 10), (0, 0, 13)), lens=40)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(PREVIEW_DIR), "blend", "cyclops.blend"), copy=True)
