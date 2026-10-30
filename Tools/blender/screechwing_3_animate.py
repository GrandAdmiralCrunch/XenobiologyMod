# Xenobiology — Screechwing, step 3: clips (fly, glide, dive, screech) as NLA tracks.
import bpy, math
from mathutils import Vector, Quaternion

scn = bpy.context.scene; scn.frame_start = 0
rig = bpy.data.objects["screechwing_rig"]; arm = rig.data
AX = {}
def dof_axis(bname, world_dir):
    key = (bname, tuple(round(c, 3) for c in world_dir))
    if key in AX: return AX[key]
    b = arm.bones[bname]; m = b.matrix_local.to_3x3(); vec = b.tail_local - b.head_local
    best = None
    for local in (Vector((1, 0, 0)), Vector((0, 0, 1))):
        score = (m @ local).normalized().cross(vec).dot(Vector(world_dir))
        if best is None or abs(score) > abs(best[1]): best = (local, score)
    AX[key] = best[0] * (1 if best[1] > 0 else -1); return AX[key]
def side(b): return 1 if arm.bones[b].head_local.x >= 0 else -1
def rot(b, fwd=0.0, up=0.0, out=0.0, yaw=0.0, back=0.0):
    q = Quaternion()
    if fwd: q = q @ Quaternion(dof_axis(b, (0, 1, 0)), math.radians(fwd))
    if back: q = q @ Quaternion(dof_axis(b, (0, -1, 0)), math.radians(back))
    if up: q = q @ Quaternion(dof_axis(b, (0, 0, 1)), math.radians(up))
    if out: q = q @ Quaternion(dof_axis(b, (side(b), 0, 0)), math.radians(out))
    if yaw: q = q @ Quaternion(dof_axis(b, (1, 0, 0)), math.radians(yaw))
    return q
def local_off(b, v): return arm.bones[b].matrix_local.to_3x3().inverted() @ Vector(v)

def wings(P, beat, fold=0.0, sweep=0.0):
    """beat: -1 (down) .. +1 (up).  fold: 0 spread .. 1 tucked.  sweep: wings swept back (deg)."""
    for s in "LR":
        P["arm"+s] = rot("arm"+s, up=42 * beat, back=sweep + 25 * fold)
        P["fore"+s] = rot("fore"+s, up=18 * beat, back=50 * fold)
        for i in range(4):
            # fingers furl toward the body on the upstroke and when folded
            P[f"fing{i}{s}"] = rot(f"fing{i}{s}", up=10 * beat, back=(12 + 6 * i) * max(0.0, beat) + 55 * fold)
        P["thigh"+s] = rot("thigh"+s, up=-10 * beat)
        P["shin"+s] = rot("shin"+s, up=-6 * beat)

def fly(t):
    P = {}; beat = math.cos(2 * math.pi * t)
    wings(P, beat)
    P["neck"] = rot("neck", up=4 * math.sin(2 * math.pi * t))
    P["head"] = rot("head", up=-3 * math.sin(2 * math.pi * t))
    for k in (1, 2, 3): P[f"tail{k}"] = rot(f"tail{k}", up=5 * math.sin(2 * math.pi * t - k * 0.8))
    for s in "LR": P["ear"+s] = rot("ear"+s, back=10 + 5 * beat)
    return P, (0, 0, -0.06 * beat)

def glide(t):
    P = {}; w = math.sin(2 * math.pi * t)
    wings(P, 0.05 + 0.04 * w)
    P["head"] = rot("head", yaw=8 * math.sin(2 * math.pi * t * 0.5))
    for k in (1, 2, 3): P[f"tail{k}"] = rot(f"tail{k}", yaw=6 * math.sin(2 * math.pi * t - k))
    for s in "LR": P["ear"+s] = rot("ear"+s, back=20)
    return P, (0, 0, 0.02 * w)

def dive(t):
    P = {}; w = math.sin(2 * math.pi * t * 2)
    wings(P, -0.2 + 0.06 * w, fold=0.55, sweep=10)
    P["neck"] = rot("neck", up=-10); P["head"] = rot("head", up=-8)
    for k in (1, 2, 3): P[f"tail{k}"] = rot(f"tail{k}", up=4, yaw=3 * w)
    for s in "LR": P["ear"+s] = rot("ear"+s, back=45)
    return P, (0, 0, 0)

def screech(t):
    P = {}; beat = math.cos(2 * math.pi * t * 2)
    wings(P, beat * 0.8)
    shriek = 0.6 + 0.4 * math.sin(2 * math.pi * t * 6)
    P["neck"] = rot("neck", up=-6 + 6 * shriek)
    P["head"] = rot("head", up=10 * shriek, yaw=6 * math.sin(2 * math.pi * t * 3))
    P["jaw"] = rot("jaw", up=-38 * shriek)            # gaping mouth
    for s in "LR": P["ear"+s] = rot("ear"+s, back=55, out=15)   # ears pinned flat
    for k in (1, 2, 3): P[f"tail{k}"] = rot(f"tail{k}", up=8 * math.sin(2 * math.pi * t * 2 - k), yaw=10 * math.sin(2 * math.pi * t * 4 - k))
    return P, (0, 0, -0.05 * beat)

CLIPS = [("fly", fly, 15, 1), ("glide", glide, 60, 3), ("dive", dive, 30, 2), ("screech", screech, 30, 1)]
if rig.animation_data is None: rig.animation_data_create()
ad = rig.animation_data
for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
ad.action = None
for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
made = []
for name, fn, frames, step in CLIPS:
    an = "screechwing_" + name
    if an in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[an])
    act = bpy.data.actions.new(an); act.use_fake_user = True; ad.action = act
    for f in sorted(set(list(range(0, frames, step)) + [frames])):
        P, off = fn((f / frames) % 1.0)
        for pb in rig.pose.bones:
            pb.rotation_quaternion = P.get(pb.name, Quaternion())
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
        b = rig.pose.bones["body"]; b.location = local_off("body", off); b.keyframe_insert("location", frame=f, group="body")
    tr = ad.nla_tracks.new(); tr.name = name; tr.strips.new(name, 0, act); tr.mute = True
    ad.action = None; made.append((name, frames))
for pb in rig.pose.bones: pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)
ad.nla_tracks["fly"].mute = False
result = {"clips": made}
