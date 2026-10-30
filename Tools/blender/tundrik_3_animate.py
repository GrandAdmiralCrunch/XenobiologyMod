# Xenobiology — Tundrik, step 3: clips (idle, walk, run, alert, dig, emerge) as NLA tracks.
import bpy, math
from mathutils import Vector, Quaternion

scn = bpy.context.scene; scn.frame_start = 0
rig = bpy.data.objects["tundrik_rig"]; arm = rig.data

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
def rot(b, fwd=0.0, up=0.0, out=0.0, yaw=0.0, roll=0.0):
    q = Quaternion()
    if fwd: q = q @ Quaternion(dof_axis(b, (0, 1, 0)), math.radians(fwd))
    if up: q = q @ Quaternion(dof_axis(b, (0, 0, 1)), math.radians(up))
    if out: q = q @ Quaternion(dof_axis(b, (side(b), 0, 0)), math.radians(out))
    if yaw: q = q @ Quaternion(dof_axis(b, (1, 0, 0)), math.radians(yaw))
    if roll: q = q @ Quaternion((0, 1, 0), math.radians(roll))
    return q
def local_off(b, v): return arm.bones[b].matrix_local.to_3x3().inverted() @ Vector(v)
def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def seg(t, a, b): return smooth((t - a) / (b - a))

TRIPOD = {"FL": 0.0, "MR": 0.0, "HL": 0.0, "FR": 0.5, "ML": 0.5, "HR": 0.5}   # alternating tripods, like an insect
def legs(P, t, amp, flex, stance=0.55):
    for k in "FMH":
        for s in "LR":
            u = (t + TRIPOD[k + s]) % 1.0
            if u < stance: sw = amp * (1 - 2 * u / stance); lift = 0.0
            else:
                q = (u - stance) / (1 - stance); sw = -amp * math.cos(math.pi * q); lift = math.sin(math.pi * q)
            P["up"+k+s] = rot("up"+k+s, fwd=sw)
            P["lo"+k+s] = rot("lo"+k+s, fwd=-lift * flex)
            P["paw"+k+s] = rot("paw"+k+s, fwd=lift * flex * 0.6)

def idle(t):
    P = {}; br = math.sin(2 * math.pi * t * 2)
    sniff = math.sin(2 * math.pi * t * 9) * (0.5 + 0.5 * math.sin(2 * math.pi * t))
    P["spine"] = rot("spine", up=0.8 * br)
    P["neck"] = rot("neck", up=-4 + 3 * math.sin(2 * math.pi * t), yaw=12 * math.sin(2 * math.pi * t))
    P["head"] = rot("head", up=-3 + 2.5 * sniff, yaw=6 * math.sin(2 * math.pi * t + 0.5))
    P["nose"] = rot("nose", up=6 * sniff)
    P["tail"] = rot("tail", yaw=10 * math.sin(2 * math.pi * t * 2))
    return P, (0, 0, 0.006 * br)

def walk(t):
    P = {}
    legs(P, t, 20.0, 35.0)
    P["body"] = rot("body", roll=3 * math.sin(2 * math.pi * t * 2), yaw=3 * math.sin(2 * math.pi * t))
    P["neck"] = rot("neck", up=-6, yaw=-4 * math.sin(2 * math.pi * t))
    P["head"] = rot("head", up=2 * math.sin(4 * math.pi * t))
    P["nose"] = rot("nose", up=4 * math.sin(2 * math.pi * t * 6))
    P["tail"] = rot("tail", yaw=8 * math.sin(2 * math.pi * t))
    return P, (0, 0, -0.025 * abs(math.sin(2 * math.pi * t * 2)))

def run(t):
    P = {}
    legs(P, t, 32.0, 55.0, stance=0.45)
    P["body"] = rot("body", up=3 * math.sin(4 * math.pi * t), roll=4 * math.sin(2 * math.pi * t * 2))
    P["neck"] = rot("neck", up=-10 + 3 * math.sin(4 * math.pi * t + 1))
    P["head"] = rot("head", up=-2 * math.sin(4 * math.pi * t + 1.5))
    P["tail"] = rot("tail", up=10, yaw=12 * math.sin(2 * math.pi * t))
    return P, (0, 0, 0.08 * math.sin(4 * math.pi * t) - 0.02)

REAR = 38.0
def alert(t):
    P = {}; w = math.sin(2 * math.pi * t)
    sniff = math.sin(2 * math.pi * t * 6)
    P["body"] = rot("body", up=REAR)                      # rear up on the hind four legs
    P["spine"] = rot("spine", up=6)
    P["neck"] = rot("neck", up=-18 + 3 * w, yaw=14 * math.sin(2 * math.pi * t))
    P["head"] = rot("head", up=-14 + 3 * sniff)
    P["nose"] = rot("nose", up=8 * sniff)
    for s in "LR":
        P["upH"+s] = rot("upH"+s, fwd=REAR * 0.9)        # keep hind feet planted
        P["loH"+s] = rot("loH"+s, fwd=-8)
        P["pawH"+s] = rot("pawH"+s, fwd=-REAR * 0.5)
        P["upM"+s] = rot("upM"+s, fwd=REAR * 0.5, out=10)   # middle pair braces
        P["upF"+s] = rot("upF"+s, fwd=-30 + 6 * w, out=12)  # big front claws held up and out, like a boxer
        P["loF"+s] = rot("loF"+s, fwd=-45 - 6 * w)
        P["pawF"+s] = rot("pawF"+s, fwd=-30)
    P["tail"] = rot("tail", up=-REAR * 0.6)
    return P, (0, 0, 0.0)

def dig(t):
    P = {}
    tip = seg(t, 0.0, 0.25)
    for s, ph in (("L", 0.0), ("R", 0.5)):
        sc = math.sin(2 * math.pi * (t * 5 + ph))
        P["upF"+s] = rot("upF"+s, fwd=-20 * tip + 38 * sc * tip, out=15 * tip)
        P["loF"+s] = rot("loF"+s, fwd=-30 * tip - 20 * max(0, sc))
        P["pawF"+s] = rot("pawF"+s, fwd=-35 * tip)
        sm = math.sin(2 * math.pi * (t * 5 + ph + 0.25))
        P["upM"+s] = rot("upM"+s, fwd=-15 * tip + 20 * sm * tip)
        P["upH"+s] = rot("upH"+s, fwd=-14 * tip)
    P["body"] = rot("body", up=-16 * tip, roll=4 * math.sin(2 * math.pi * t * 5))
    P["neck"] = rot("neck", up=-20 * tip)
    P["head"] = rot("head", up=-15 * tip)
    P["nose"] = rot("nose", up=10 * math.sin(2 * math.pi * t * 10))
    P["tail"] = rot("tail", up=25 * tip, yaw=15 * math.sin(2 * math.pi * t * 5))
    return P, (0, 0, -0.1 * tip)

def emerge(t):
    P = {}
    rise = seg(t, 0.0, 0.45)
    shake = math.sin(2 * math.pi * t * 7) * (1 - seg(t, 0.45, 1.0)) * seg(t, 0.3, 0.45)
    up = 22 * (1 - rise) * 0.0 + 14 * math.sin(math.pi * seg(t, 0.0, 0.5))
    P["body"] = rot("body", up=up, roll=18 * shake)
    P["neck"] = rot("neck", up=10 * (1 - rise), yaw=25 * shake)
    P["head"] = rot("head", up=-10 * (1 - rise), yaw=20 * shake)
    P["nose"] = rot("nose", up=10 * math.sin(2 * math.pi * t * 8))
    for s in "LR":
        push = math.sin(math.pi * seg(t, 0.0, 0.45))
        P["upF"+s] = rot("upF"+s, fwd=30 * push, out=10 * push)
        P["loF"+s] = rot("loF"+s, fwd=-25 * push)
    P["tail"] = rot("tail", yaw=25 * shake)
    return P, (0, 0, 0.0)

CLIPS = [("idle", idle, 90, 3), ("walk", walk, 36, 2), ("run", run, 18, 1), ("alert", alert, 60, 3),
         ("dig", dig, 45, 1), ("emerge", emerge, 36, 1)]
ONESHOT = ("dig", "emerge")
if rig.animation_data is None: rig.animation_data_create()
ad = rig.animation_data
for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
ad.action = None
for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
made = []
for name, fn, frames, step in CLIPS:
    an = "tundrik_" + name
    if an in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[an])
    act = bpy.data.actions.new(an); act.use_fake_user = True; ad.action = act
    for f in sorted(set(list(range(0, frames, step)) + [frames])):
        t = f / frames
        P, off = fn(t if name in ONESHOT else t % 1.0)
        for pb in rig.pose.bones:
            pb.rotation_quaternion = P.get(pb.name, Quaternion())
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
        b = rig.pose.bones["body"]; b.location = local_off("body", off); b.keyframe_insert("location", frame=f, group="body")
    tr = ad.nla_tracks.new(); tr.name = name; tr.strips.new(name, 0, act); tr.mute = True
    ad.action = None; made.append((name, frames))
for pb in rig.pose.bones: pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)
ad.nla_tracks["walk"].mute = False
result = {"clips": made}
