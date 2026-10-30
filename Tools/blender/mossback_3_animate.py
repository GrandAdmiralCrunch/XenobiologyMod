# Xenobiology — Greater Mossback, step 3: procedural keyframed clips pushed to NLA tracks.
# Track names become the .mu animation clip names: idle, walk, run, alert.
import bpy, math
from mathutils import Vector, Quaternion, Matrix

scn = bpy.context.scene
scn.frame_start = 0
rig = bpy.data.objects["mossback_rig"]
arm = rig.data
FPS = scn.render.fps

# ---------------------------------------------------------------- DOF helpers
# For each bone and a desired world-space direction for its tail, find the local rotation axis
# (X or Z, with sign) that moves the tail that way. Keeps the animation code readable:
#   fwd = tail toward +Y (forward), up = tail toward +Z, out = tail away from the body midline.
AX = {}
def dof_axis(bname, world_dir):
    key = (bname, tuple(round(c, 3) for c in world_dir))
    if key in AX: return AX[key]
    b = arm.bones[bname]
    m = b.matrix_local.to_3x3()
    vec = (b.tail_local - b.head_local)
    best = None
    for local in (Vector((1, 0, 0)), Vector((0, 0, 1))):
        w = (m @ local).normalized()
        d = w.cross(vec)
        score = d.dot(Vector(world_dir))
        if best is None or abs(score) > abs(best[1]):
            best = (local, score)
    axis = best[0] * (1 if best[1] > 0 else -1)
    AX[key] = axis
    return axis

def outward(bname):
    x = arm.bones[bname].head_local.x
    return (1 if x >= 0 else -1, 0, 0)

def rot(bname, fwd=0.0, up=0.0, out=0.0, roll=0.0):
    q = Quaternion()
    if fwd: q = q @ Quaternion(dof_axis(bname, (0, 1, 0)), math.radians(fwd))
    if up: q = q @ Quaternion(dof_axis(bname, (0, 0, 1)), math.radians(up))
    if out: q = q @ Quaternion(dof_axis(bname, outward(bname)), math.radians(out))
    if roll: q = q @ Quaternion((0, 1, 0), math.radians(roll))
    return q

def world_offset_to_local(bname, v):
    m = arm.bones[bname].matrix_local.to_3x3()
    return m.inverted() @ Vector(v)

# ---------------------------------------------------------------- gait helpers
def leg_cycle(u, amp, flex, stance=0.65):
    """returns (upper swing deg, lower flex 0..1) for normalised phase u"""
    u %= 1.0
    if u < stance:
        s = u / stance
        return amp * (1 - 2 * s), 0.0                    # planted: sweeps from forward to back
    s = (u - stance) / (1 - stance)
    return amp * (-math.cos(math.pi * s)), math.sin(math.pi * s) * flex   # lifted: swings forward

def legs_pose(P, t, amp, flex, phases, stance):
    for s in "LR":
        fu, ff = leg_cycle(t + phases["F" + s], amp, flex, stance)
        hu, hf = leg_cycle(t + phases["H" + s], amp, flex, stance)
        P["upperarm" + s] = rot("upperarm" + s, fwd=fu)
        P["forearm" + s] = rot("forearm" + s, fwd=-ff * 1.0)
        P["ffoot" + s] = rot("ffoot" + s, fwd=ff * 0.7)
        P["thigh" + s] = rot("thigh" + s, fwd=hu * 0.9)
        P["shin" + s] = rot("shin" + s, fwd=ff * 0 - hf * 0.9)
        P["hfoot" + s] = rot("hfoot" + s, fwd=hf * 0.8)

def trunks(P, t, sway, curl, lift=0.0, sniff=0.0):
    for i, s in enumerate("LR"):
        off = i * 0.37
        for k in range(1, 5):
            w = math.sin(2 * math.pi * (t + off) - k * 0.7)
            c = curl * k / 4
            extra = sniff * (1 if s == "L" else 0) * max(0.0, math.sin(2 * math.pi * t)) * k / 2
            P[f"trunk{k}{s}"] = rot(f"trunk{k}{s}", fwd=w * sway + c + extra + (lift if k == 1 else lift * 0.6),
                                    out=math.cos(2 * math.pi * (t + off) - k) * sway * 0.4)

def tail(P, t, sway, lift=0.0):
    for k in range(1, 4):
        P[f"tail{k}"] = rot(f"tail{k}", up=lift / k, out=0) @ Quaternion(dof_axis(f"tail{k}", (1, 0, 0)), math.radians(sway * math.sin(2 * math.pi * t - k * 0.8) * (0.6 + 0.4 * k)))

def frills(P, t, fold, flutter=0.0):
    for s in "LR":
        P["frill" + s] = rot("frill" + s, fwd=-fold * 0.8, up=-fold * 0.5, out=flutter * math.sin(2 * math.pi * t * 3 + (0 if s == "L" else 1.3)))

# ---------------------------------------------------------------- clips: each returns {bone: Quaternion} and body world offset
def walk(t):
    P = {}
    legs_pose(P, t, 16.0, 38.0, {"HL": 0.0, "FL": 0.25, "HR": 0.5, "FR": 0.75}, 0.65)
    P["body"] = rot("body", roll=2.0 * math.sin(2 * math.pi * t))
    P["chest"] = rot("chest", up=1.0 * math.sin(4 * math.pi * t))
    P["neck1"] = rot("neck1", up=-2.0 + 2.5 * math.sin(4 * math.pi * t + 1.0), out=0)
    P["neck2"] = rot("neck2", up=1.5 * math.sin(4 * math.pi * t + 1.4))
    P["head"] = rot("head", up=-1.5 * math.sin(4 * math.pi * t + 1.8)) @ Quaternion(dof_axis("head", (1, 0, 0)), math.radians(3 * math.sin(2 * math.pi * t)))
    trunks(P, t, 7.0, 4.0)
    tail(P, t, 8.0, 3.0)
    frills(P, t, 28.0, 3.0)
    bob = -0.05 * abs(math.cos(2 * math.pi * t))
    return P, (0, 0, bob)

def run(t):
    P = {}
    legs_pose(P, t, 27.0, 55.0, {"FL": 0.0, "HR": 0.0, "FR": 0.5, "HL": 0.5}, 0.5)
    P["body"] = rot("body", up=2.0 * math.sin(4 * math.pi * t), roll=3.0 * math.sin(2 * math.pi * t))
    P["neck1"] = rot("neck1", up=-7.0 + 4.0 * math.sin(4 * math.pi * t + 0.8))
    P["neck2"] = rot("neck2", up=2.0 * math.sin(4 * math.pi * t + 1.2))
    P["head"] = rot("head", up=-3.0 * math.sin(4 * math.pi * t + 1.6))
    trunks(P, t * 2, 12.0, 14.0)
    tail(P, t, 6.0, 12.0)
    frills(P, t, 42.0, 0.0)
    bob = 0.10 * math.sin(4 * math.pi * t) - 0.04
    return P, (0, 0, bob)

def idle(t):
    P = {}
    br = math.sin(2 * math.pi * t * 3)            # three breaths per loop
    P["spine"] = rot("spine", up=0.6 * br)
    P["chest"] = rot("chest", up=0.8 * br)
    P["neck1"] = rot("neck1", up=-4.0 + 3.0 * math.sin(2 * math.pi * t)) @ Quaternion(dof_axis("neck1", (1, 0, 0)), math.radians(6 * math.sin(2 * math.pi * t)))
    P["neck2"] = rot("neck2", up=2.0 * math.sin(2 * math.pi * t + 0.6))
    P["head"] = rot("head", up=-6.0 + 3.0 * math.sin(2 * math.pi * t + 1.2)) @ Quaternion(dof_axis("head", (1, 0, 0)), math.radians(10 * math.sin(2 * math.pi * t + 0.4)))
    trunks(P, t, 5.0, 6.0, sniff=22.0)
    tail(P, t * 2, 12.0, 0.0)
    frills(P, t, 25.0, 4.0)
    shift = math.sin(2 * math.pi * t)
    for s, sg in (("L", 1), ("R", -1)):
        P["upperarm" + s] = rot("upperarm" + s, fwd=1.0 * shift * sg)
        P["thigh" + s] = rot("thigh" + s, fwd=-1.0 * shift * sg)
    return P, (0, 0, 0.01 * br)

def alert(t):
    P = {}
    w = math.sin(2 * math.pi * t)
    P["body"] = rot("body", up=2.0)
    P["chest"] = rot("chest", up=2.0)
    P["neck1"] = rot("neck1", up=16.0 + 1.0 * w) @ Quaternion(dof_axis("neck1", (1, 0, 0)), math.radians(8 * math.sin(2 * math.pi * t)))
    P["neck2"] = rot("neck2", up=8.0)
    P["head"] = rot("head", up=-8.0 + 2.0 * w)
    for s in "LR":
        P["trunk1" + s] = rot("trunk1" + s, fwd=35.0 + 4 * w, out=8.0)
        P["trunk2" + s] = rot("trunk2" + s, fwd=40.0 + 6 * w)
        P["trunk3" + s] = rot("trunk3" + s, fwd=35.0 + 8 * w)
        P["trunk4" + s] = rot("trunk4" + s, fwd=30.0 + 10 * w)
    tail(P, t, 3.0, 18.0)
    frills(P, t, -12.0, 6.0)            # spread wide, quivering
    return P, (0, 0, 0.03)

CLIPS = [("idle", idle, 120, 4), ("walk", walk, 42, 2), ("run", run, 24, 2), ("alert", alert, 60, 3)]

# ---------------------------------------------------------------- bake keys into actions -> NLA
if rig.animation_data is None:
    rig.animation_data_create()
ad = rig.animation_data
for tr in list(ad.nla_tracks):
    ad.nla_tracks.remove(tr)
ad.action = None
bpy.context.view_layer.objects.active = rig
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'

made = []
for name, fn, frames, step in CLIPS:
    act = bpy.data.actions.get("mossback_" + name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new("mossback_" + name)
    act.use_fake_user = True
    ad.action = act
    keyed = set()
    for f in list(range(0, frames, step)) + [frames]:
        t = f / frames
        P, off = fn(t % 1.0)
        for pb in rig.pose.bones:
            q = P.get(pb.name, Quaternion())
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
            keyed.add(pb.name)
        bodyb = rig.pose.bones["body"]
        bodyb.location = world_offset_to_local("body", off)
        bodyb.keyframe_insert("location", frame=f, group="body")
    track = ad.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 0, act)
    strip.extrapolation = 'HOLD'
    track.mute = True
    ad.action = None
    made.append((name, frames))

# leave the walk clip active for viewport playback
for pb in rig.pose.bones:
    pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)
ad.nla_tracks["walk"].mute = False
scn.frame_end = 42
result = {"clips": made, "axes": len(AX)}
