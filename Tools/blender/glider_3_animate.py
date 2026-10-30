# Xenobiology — Patagiata gliders, step 3: clips as NLA tracks.
#   idle, walk, sleep (loops) · glide (loop) · takeoff, land, tailswing (one-shot)
import bpy, math
from mathutils import Vector, Quaternion

VARIANT = globals().get("VARIANT", "spiketail")
scn = bpy.context.scene
scn.frame_start = 0
rig = bpy.data.objects[VARIANT + "_rig"]
arm = rig.data
S = 1.0 if VARIANT == "spiketail" else 0.74

AX = {}
def dof_axis(bname, world_dir):
    key = (bname, tuple(round(c, 3) for c in world_dir))
    if key in AX: return AX[key]
    b = arm.bones[bname]
    m = b.matrix_local.to_3x3()
    vec = b.tail_local - b.head_local
    best = None
    for local in (Vector((1, 0, 0)), Vector((0, 0, 1))):
        w = (m @ local).normalized()
        score = w.cross(vec).dot(Vector(world_dir))
        if best is None or abs(score) > abs(best[1]): best = (local, score)
    AX[key] = best[0] * (1 if best[1] > 0 else -1)
    return AX[key]
def side(bname): return 1 if arm.bones[bname].head_local.x >= 0 else -1
def rot(bname, fwd=0.0, up=0.0, out=0.0, yaw=0.0):
    """fwd: tail toward +Y · up: tail toward +Z · out: tail away from midline · yaw: tail toward +X"""
    q = Quaternion()
    if fwd: q = q @ Quaternion(dof_axis(bname, (0, 1, 0)), math.radians(fwd))
    if up: q = q @ Quaternion(dof_axis(bname, (0, 0, 1)), math.radians(up))
    if out: q = q @ Quaternion(dof_axis(bname, (side(bname), 0, 0)), math.radians(out))
    if yaw: q = q @ Quaternion(dof_axis(bname, (1, 0, 0)), math.radians(yaw))
    return q
def local_off(bname, v):
    return arm.bones[bname].matrix_local.to_3x3().inverted() @ (Vector(v) * S)
def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def seg(t, a, b): return smooth((t - a) / (b - a)) if b > a else float(t >= a)

# ---------------------------------------------------------------- reusable sub-poses
FOLD = -78.0  # spar angle (deg, toward the tail) when the membranes are folded along the flanks
def spars(P, fold01, flap=0.0, cup=0.0, flutter=0.0, t=0.0):
    for s in "LR":
        for k, c in enumerate("ABC"):
            nm = f"spar{c}{s}"
            f = FOLD * fold01 * (1.0 - 0.12 * k)
            u = flap * (1.0 - 0.15 * k) + cup - 8.0 * fold01 + flutter * math.sin(2 * math.pi * t * 3 + k * 0.7)
            P[nm] = rot(nm, fwd=f, up=u)

def legs_walk(P, t, amp=24.0, flex=40.0):
    ph = {"FL": 0.0, "HR": 0.0, "FR": 0.5, "HL": 0.5}
    for s in "LR":
        for limb, a, b, c in (("F", "upperarm", "forearm", "hand"), ("H", "thigh", "shin", "foot")):
            u = (t + ph[limb + s]) % 1.0
            if u < 0.55:
                sw = amp * (1 - 2 * u / 0.55); lift = 0.0
            else:
                q = (u - 0.55) / 0.45; sw = -amp * math.cos(math.pi * q); lift = math.sin(math.pi * q)
            P[a + s] = rot(a + s, fwd=sw, up=lift * 18.0)
            P[b + s] = rot(b + s, fwd=-lift * flex * 0.5, up=-lift * flex * 0.4)
            P[c + s] = rot(c + s, fwd=lift * 20.0)

def legs_tucked(P, amount=1.0):
    for s in "LR":
        P["upperarm" + s] = rot("upperarm" + s, fwd=40 * amount, up=25 * amount)
        P["forearm" + s] = rot("forearm" + s, fwd=-35 * amount, up=30 * amount)
        P["hand" + s] = rot("hand" + s, fwd=30 * amount)
        P["thigh" + s] = rot("thigh" + s, fwd=-60 * amount, up=20 * amount)
        P["shin" + s] = rot("shin" + s, fwd=-30 * amount, up=25 * amount)
        P["foot" + s] = rot("foot" + s, fwd=-40 * amount)

def tail_wave(P, t, amp, lift=0.0, freq=1.0, curl=0.0):
    for k in range(1, 6):
        P[f"tail{k}"] = rot(f"tail{k}", up=lift / k, yaw=curl + amp * math.sin(2 * math.pi * t * freq - k * 0.9) * (0.5 + 0.18 * k))

def spine_wave(P, t, amp):
    P["body"] = rot("body", yaw=amp * math.sin(2 * math.pi * t))
    P["spine"] = rot("spine", yaw=-amp * 1.2 * math.sin(2 * math.pi * t))
    P["neck1"] = rot("neck1", yaw=amp * 0.8 * math.sin(2 * math.pi * t))

# ---------------------------------------------------------------- clips
def idle(t):
    P = {}
    br = math.sin(2 * math.pi * t * 2)
    display = math.sin(math.pi * seg(t, 0.55, 0.85)) * 0.45        # brief half-open membrane flick
    spars(P, 1.0 - display, t=t)
    P["spine"] = rot("spine", up=0.8 * br)
    P["neck1"] = rot("neck1", up=6.0, yaw=10 * math.sin(2 * math.pi * t))
    P["neck2"] = rot("neck2", up=4.0 + 3 * math.sin(2 * math.pi * t + 1))
    P["head"] = rot("head", up=-6.0 + 4 * math.sin(4 * math.pi * t), yaw=14 * math.sin(2 * math.pi * t + 0.5))
    tail_wave(P, t, 7.0)
    return P, (0, 0, 0.005 * br)

def walk(t):
    P = {}
    spars(P, 1.0, flutter=1.5, t=t)
    legs_walk(P, t)
    spine_wave(P, t, 7.0)
    P["neck2"] = rot("neck2", up=3.0, yaw=-5 * math.sin(2 * math.pi * t))
    P["head"] = rot("head", up=-3.0, yaw=-6 * math.sin(2 * math.pi * t))
    tail_wave(P, t, 12.0, lift=4.0)
    return P, (0, 0, -0.02 * abs(math.sin(2 * math.pi * t)))

def glide(t):
    P = {}
    w = math.sin(2 * math.pi * t)
    spars(P, 0.0, flap=3.0 * w, cup=4.0)
    legs_tucked(P, 1.0)
    P["neck1"] = rot("neck1", up=-4.0)
    P["head"] = rot("head", up=-8.0 + 2 * w, yaw=4 * math.sin(2 * math.pi * t * 0.5))
    tail_wave(P, t, 4.0, lift=6.0)
    return P, (0, 0, 0.0)

def takeoff(t):
    P = {}
    crouch = seg(t, 0.0, 0.25) * (1 - seg(t, 0.28, 0.40))
    leap = seg(t, 0.28, 0.45)
    unfold = seg(t, 0.32, 0.58)
    flap = 0.0
    if t > 0.55:
        q = (t - 0.55) / 0.45
        flap = 28.0 * math.sin(2 * math.pi * 2 * q) * (1 - q)
    spars(P, 1.0 - unfold, flap=flap)
    if leap < 1e-3:
        for s in "LR":
            P["upperarm" + s] = rot("upperarm" + s, up=20 * crouch)
            P["forearm" + s] = rot("forearm" + s, up=-25 * crouch)
            P["thigh" + s] = rot("thigh" + s, up=22 * crouch)
            P["shin" + s] = rot("shin" + s, up=-28 * crouch)
    else:
        legs_tucked(P, leap)
    P["neck1"] = rot("neck1", up=10 * crouch - 4 * leap)
    P["head"] = rot("head", up=-8 * leap)
    tail_wave(P, t, 3.0, lift=-10 * crouch + 8 * leap)
    return P, (0, 0, -0.18 * crouch + 0.10 * leap * (1 - seg(t, 0.6, 1.0)))

def land(t):
    P = {}
    flare = seg(t, 0.0, 0.35) * (1 - seg(t, 0.55, 0.7))
    fold = seg(t, 0.55, 0.95)
    reach = seg(t, 0.05, 0.35)
    absorb = math.sin(math.pi * seg(t, 0.38, 0.75))
    spars(P, fold, flap=14 * flare, cup=16 * flare)
    legs_tucked(P, 1.0 - reach)
    for s in "LR":
        if reach > 0.99:
            P["upperarm" + s] = rot("upperarm" + s, fwd=10 * (1 - fold), up=18 * absorb)
            P["forearm" + s] = rot("forearm" + s, up=-22 * absorb)
            P["thigh" + s] = rot("thigh" + s, up=20 * absorb)
            P["shin" + s] = rot("shin" + s, up=-24 * absorb)
    P["neck1"] = rot("neck1", up=8 * flare + 4 * fold)
    P["head"] = rot("head", up=-10 * flare)
    tail_wave(P, t, 4.0, lift=-12 * flare)
    return P, (0, 0, -0.14 * absorb)

def sleep(t):
    P = {}
    br = math.sin(2 * math.pi * t * 2)
    spars(P, 1.05, flap=-6.0)
    for s in "LR":
        P["upperarm" + s] = rot("upperarm" + s, up=26, fwd=-10)
        P["forearm" + s] = rot("forearm" + s, up=-14)
        P["thigh" + s] = rot("thigh" + s, up=26, fwd=8)
        P["shin" + s] = rot("shin" + s, up=-14)
    P["spine"] = rot("spine", up=1.0 * br)
    P["neck1"] = rot("neck1", up=-4, yaw=28)
    P["neck2"] = rot("neck2", up=-1, yaw=22)
    P["head"] = rot("head", up=5 + 1.2 * br, yaw=12)
    for k in range(1, 6):
        P[f"tail{k}"] = rot(f"tail{k}", up=-2, yaw=16 + 1.5 * math.sin(2 * math.pi * t - k))
    return P, (0, 0, -0.22)

def tailswing(t):
    P = {}
    wind = seg(t, 0.0, 0.30) * (1 - seg(t, 0.30, 0.42))
    whip = seg(t, 0.30, 0.44) * (1 - seg(t, 0.55, 1.0))
    a = 34 * wind - 48 * whip
    spars(P, 1.0 - 0.35 * math.sin(math.pi * seg(t, 0.0, 0.7)), t=t)   # membranes flash open as a warning
    P["body"] = rot("body", yaw=-a * 0.3)
    P["spine"] = rot("spine", yaw=a * 0.15)
    P["neck1"] = rot("neck1", yaw=a * 0.25, up=6 * wind)
    P["head"] = rot("head", yaw=a * 0.2)
    for k in range(1, 6):
        lag = 0.03 * k
        wk = seg(t, 0.0, 0.30) * (1 - seg(t, 0.30 + lag, 0.42 + lag))
        hk = seg(t, 0.30 + lag, 0.44 + lag) * (1 - seg(t, 0.55 + lag, 1.0))
        P[f"tail{k}"] = rot(f"tail{k}", yaw=(30 * wk - 42 * hk) * (0.6 + 0.12 * k), up=3 * wk)
    for s in "LR":
        P["thigh" + s] = rot("thigh" + s, up=10 * (wind + whip))
        P["upperarm" + s] = rot("upperarm" + s, up=8 * (wind + whip))
    return P, (0, 0, -0.06 * (wind + whip))

CLIPS = [("idle", idle, 90, 3), ("walk", walk, 30, 2), ("glide", glide, 60, 3), ("takeoff", takeoff, 36, 2),
         ("land", land, 36, 2), ("sleep", sleep, 120, 4)]
if VARIANT == "spiketail":
    CLIPS.append(("tailswing", tailswing, 30, 1))

if rig.animation_data is None: rig.animation_data_create()
ad = rig.animation_data
for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
ad.action = None
for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
made = []
for name, fn, frames, step in CLIPS:
    an = f"{VARIANT}_{name}"
    if an in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[an])
    act = bpy.data.actions.new(an); act.use_fake_user = True
    ad.action = act
    for f in sorted(set(list(range(0, frames, step)) + [frames])):
        t = f / frames
        P, off = fn(t if name in ("takeoff", "land", "tailswing") else t % 1.0)
        for pb in rig.pose.bones:
            pb.rotation_quaternion = P.get(pb.name, Quaternion())
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
        b = rig.pose.bones["body"]
        b.location = local_off("body", off)
        b.keyframe_insert("location", frame=f, group="body")
    tr = ad.nla_tracks.new(); tr.name = name
    tr.strips.new(name, 0, act); tr.mute = True
    ad.action = None
    made.append((name, frames))
for pb in rig.pose.bones:
    pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)
ad.nla_tracks["walk"].mute = False
result = {"clips": made}
