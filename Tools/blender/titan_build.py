# Xenobiology — the Fallen Titan: a landmark fossil kilometres long, lying in Kerbin's Badlands.
# Run inside Blender:  exec(src, {"__name__": "__xeno__", "STEP": "model" | "all"})
# Blender metres, Z up, origin on the ground at the middle of the ribcage, +Y toward the skull.
# Texture ids ("part"): 0 sediment, 1 bone, 2 old bone (teeth, knuckles), 3 dark (sockets), 4 orb (glow),
#                       5 metal (cage, lance), 6 scorched glass (glowing veins)
import bpy, bmesh, os, math, random
from mathutils import Vector, Matrix, Euler, noise
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
_STEP = globals().get("STEP", "all")
_lib = {"__name__": "lib"}
exec(open(os.path.join(TOOLS, "fossils_build.py"), encoding="utf-8").read(), _lib)
globals().update({k: v for k, v in _lib.items() if not k.startswith("__")})
STEP = _STEP
NAME = "fallen_titan"
SED, BONE, OLD, DARK, ORB, METAL, SCORCH = range(7)
random.seed(1729)

def rot(yaw=0, pitch=0, roll=0): return Euler((math.radians(roll), math.radians(pitch), math.radians(yaw)), 'XYZ').to_matrix()

def bone_tube(b, pts, r0, r1, segs=10, flat=1.0, up=None, knobs=True, pid=BONE):
    """a long bone: smooth Catmull-Rom tube with knobbed ends"""
    pts = [Vector(p) for p in pts]
    C = []
    P = [pts[0] + (pts[0] - pts[1])] + pts + [pts[-1] + (pts[-1] - pts[-2])]
    n = 6 * (len(pts) - 1)
    for i in range(n + 1):
        u = i / n * (len(pts) - 1); k = min(len(pts) - 2, int(u)); t = u - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        C.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    rad = [r0 + (r1 - r0) * (i / n) for i in range(n + 1)]
    rmod = lambda i, ph: 1 + 0.07 * noise.noise(Vector((i * 0.35, math.cos(ph), math.sin(ph) + len(pts))))
    b.pid = pid
    tube_path(b, C, rad, segs, up=up, flat=flat, rmod=rmod)
    if knobs:
        for end, r in ((C[0], r0), (C[-1], r1)):
            ellipsoid(b, end, (r * 1.45, r * 1.45, r * 1.3 * flat), sub=2, jitter=0.18, seed=r, pid=OLD)

def mound(b, c, rx, ry, h, yaw=0, pid=SED):
    """sediment heaped round a buried bone; its lower half is below ground"""
    ellipsoid(b, c, (rx, ry, h), rot(yaw), sub=3, jitter=0.16, seed=c[0] * 0.01 + c[1] * 0.007, pid=pid)

def build_titan():
    b = B()
    # ---------------------------------------------------------------- spine: neck to tail, gently S-curved, half buried
    def spine_pt(t):          # t: 0 neck .. 1 tail tip
        y = 380 - t * 1750
        return Vector((40 * math.sin(t * 5.0) - 20 * t, y, 28 - 30 * t * t))
    NV = 44; verts = []
    for i in range(NV):
        t = i / (NV - 1); c = spine_pt(t); r = 30 * (1 - 0.6 * t) + 6
        verts.append((c, r))
        ellipsoid(b, c, (r * 1.15, r * 0.75, r), sub=2, jitter=0.14, seed=i * 1.7, pid=BONE)
        # spinous process: a tall blade, tipped toward the fallen side
        d = Vector((-0.55, -0.15, 1)).normalized()
        cone(b, c + Vector((0, 0, r * 0.6)), d, r * (2.6 if t < 0.55 else 1.6), r * 0.45, segs=6, pid=BONE)
        for sx in (1, -1):            # transverse processes
            cone(b, c + Vector((sx * r * 0.8, 0, 0)), (sx, -0.1, 0.15), r * 1.2, r * 0.3, segs=5, pid=OLD)
    # neck: cervical vertebrae curving from the shoulders to where the skull came to rest
    n0 = spine_pt(0.0); nk = [n0, n0 + Vector((-10, 70, 6)), n0 + Vector((-45, 140, 4)), Vector((-75, 560, 18))]
    for i in range(9):
        t = (i + 1) / 10; k = min(2, int(t * 3)); f = t * 3 - k
        c = nk[k].lerp(nk[k + 1], f); r = 30 - 6 * t
        ellipsoid(b, c, (r * 1.1, r * 0.8, r * 0.9), rot(15 * t), sub=2, jitter=0.14, seed=40 + i, pid=BONE)
        cone(b, c + Vector((0, 0, r * 0.5)), (-0.6, 0.1, 1), r * 1.3, r * 0.35, segs=5, pid=OLD)
    mound(b, nk[2] + Vector((0, 0, -12)), 80, 60, 20)
    for i in range(0, NV, 3):
        c, r = verts[i]
        mound(b, c + Vector((-r * 0.8, 0, -r * 0.6)), r * 3.2, r * 2.2, r * 1.1)
    # ---------------------------------------------------------------- ribs: towering arches on one side, splayed flat on the other
    NR = 15; broken = {3, 7, 11, 13}
    for k in range(NR):
        t = 0.06 + 0.36 * k / (NR - 1); s = spine_pt(t); y0 = s.y
        bell = math.sin(math.pi * (0.15 + 0.85 * k / (NR - 1))) ** 0.7
        H = 70 + 150 * bell; Wd = 130 + 200 * bell
        pts = [s + Vector((14, 0, 8)), s + Vector((Wd * 0.18, -8, H * 0.6)), s + Vector((Wd * 0.45, -22, H * 1.0)),
               s + Vector((Wd * 0.75, -36, H * 0.75)), s + Vector((Wd * 0.95, -44, H * 0.25)), s + Vector((Wd * 1.05, -48, -25))]
        if k in broken:                     # snapped mid-arch, the rest lying in the dirt below
            cut = 3 if k % 2 else 4
            bone_tube(b, pts[:cut], 11, 7, segs=10, flat=0.65, up=(0, 1, 0))
            cone(b, pts[cut - 1], pts[cut - 1] - pts[cut - 2], 22, 7, segs=6, pid=OLD)
            g = Vector((pts[cut - 1].x + 30, pts[cut - 1].y - 20, 4))
            bone_tube(b, [g, g + Vector((60, -40, -8)), g + Vector((140, -50, -14))], 8, 5, segs=8, flat=0.6, up=(0, 0, 1))
            mound(b, g + Vector((70, -40, -10)), 50, 25, 14)
        else:
            bone_tube(b, pts, 11, 5, segs=10, flat=0.65, up=(0, 1, 0))
            mound(b, pts[-1] + Vector((0, 0, -4)), 28, 22, 16)
        # the fallen side: shorter ribs lying flat on the ground, half under sediment
        L = Wd * 0.75
        lp = [s + Vector((-12, 0, 4)), s + Vector((-L * 0.4, -10, 14)), s + Vector((-L * 0.8, -26, 4)), s + Vector((-L, -34, -12))]
        bone_tube(b, lp, 9, 4, segs=8, flat=0.6, up=(0, 0, 1))
        if k % 2 == 0: mound(b, lp[2] + Vector((0, 0, -6)), 40, 22, 12)
    # ---------------------------------------------------------------- the lance: a colossal broken weapon driven through the chest
    tip = spine_pt(0.22) + Vector((90, 0, -40)); dirv = Vector((0.45, 0.25, 1)).normalized()
    shaft = [tip + dirv * (L_) for L_ in (0, 160, 330, 520)]
    b.pid = METAL
    tube_path(b, shaft, [6, 9, 9, 8], 8, rmod=lambda i, ph: 1 + 0.25 * max(0.0, math.cos(ph * 4)) ** 8)
    cone(b, shaft[-1], dirv, 40, 8, segs=8, pid=METAL)          # splintered butt end
    for k in range(4):                                         # guard fins
        a = k * math.pi / 2
        cone(b, shaft[1] + Vector((math.cos(a) * 9, math.sin(a) * 9, 0)), Vector((math.cos(a), math.sin(a), -0.6)), 55, 7, segs=4, pid=METAL)
    bh = tip + Vector((60, 140, -6))                            # the broken head lies on the ground beyond
    b.pid = METAL; tube_path(b, [bh, bh + Vector((80, 60, 4)), bh + Vector((150, 120, 0))], [8, 10, 2], 8, flat=0.4, up=(0, 0, 1))
    mound(b, tip + Vector((0, 0, -10)), 60, 50, 20)
    # ---------------------------------------------------------------- pelvis and legs
    pc = spine_pt(0.62)
    for sx in (1, -1):
        ellipsoid(b, pc + Vector((sx * 90, -10, 20 if sx > 0 else -10)), (110, 60, 22), rot(sx * 25, 0, sx * 30), sub=3, jitter=0.12, seed=sx * 3, pid=BONE)
    ellipsoid(b, pc + Vector((0, -40, 10)), (40, 80, 30), sub=2, jitter=0.12, seed=5, pid=BONE)
    hip = pc + Vector((120, -40, 10)); knee = hip + Vector((240, -280, -8)); ankle = knee + Vector((-90, -360, -18))
    bone_tube(b, [hip, hip + (knee - hip) * 0.5 + Vector((0, 0, 14)), knee], 34, 26, segs=12)
    bone_tube(b, [knee, knee + (ankle - knee) * 0.5 + Vector((10, 0, 6)), ankle], 24, 17, segs=10)
    bone_tube(b, [knee + Vector((24, -10, 0)), ankle + Vector((24, 5, -4))], 12, 9, segs=8)
    for f in range(4):
        a = math.radians(-40 + 25 * f)
        bone_tube(b, [ankle, ankle + Vector((math.sin(a) * 60, -math.cos(a) * 70, -6)), ankle + Vector((math.sin(a) * 120, -math.cos(a) * 140, -14))], 10, 6, segs=7)
    mound(b, knee + Vector((0, 0, -16)), 90, 70, 26); mound(b, ankle + Vector((20, -60, -10)), 120, 90, 20)
    h2 = pc + Vector((-110, -60, -10))                          # the other leg: a femur stub jutting from the sediment
    bone_tube(b, [h2 + Vector((0, 0, -40)), h2 + Vector((-80, -90, 60)), h2 + Vector((-120, -150, 120))], 30, 24, segs=12)
    mound(b, h2 + Vector((-20, -20, -10)), 120, 100, 35)
    # ---------------------------------------------------------------- the reaching arm, the hand, and the orb it never let go of
    sh = spine_pt(0.02) + Vector((70, -20, 20)); el = sh + Vector((260, 150, -4)); wr = el + Vector((150, 290, -18))
    bone_tube(b, [sh, sh + (el - sh) * 0.5 + Vector((0, 0, 18)), el], 32, 24, segs=12)
    for off in (-12, 12):
        bone_tube(b, [el + Vector((off, 0, 0)), el + (wr - el) * 0.5 + Vector((off * 1.2, 0, 8)), wr + Vector((off * 0.8, 0, 0))], 16, 12, segs=10)
    mound(b, el + Vector((0, 0, -14)), 70, 60, 20); mound(b, sh + Vector((0, 0, -12)), 80, 70, 24)
    orbC = wr + Vector((110, 150, 58)); orbR = 66
    # scorched, glassy ground round the orb
    mound(b, orbC + Vector((0, 0, -orbR - 4)), 210, 190, 16, pid=SCORCH)
    # the orb: cracked, glowing
    tmp = bmesh.new(); bmesh.ops.create_icosphere(tmp, subdivisions=4, radius=1.0)
    M = Matrix.Translation(orbC) @ Matrix.Diagonal((orbR, orbR, orbR, 1))
    b.add_bm(tmp, M, ORB, jitter=0.03, seed=3.0)
    # the cage: two broken bands round it
    for tilt, yaw, gap in ((22, 10, 50), (-65, 80, 80)):
        Rm = rot(yaw, 0, tilt); pts = []
        for k in range(49):
            a = math.radians(gap / 2 + (360 - gap) * k / 48)
            pts.append(orbC + Rm @ Vector((math.cos(a) * (orbR + 26), math.sin(a) * (orbR + 26), 0)))
        b.pid = METAL
        tube_path(b, pts, 7, 6, flat=0.35, up=tuple(Rm @ Vector((0, 0, 1))), rmod=lambda i, ph: 1 + 0.4 * (1 if i % 8 == 0 else 0))
    # palm: five metacarpals fanning from the wrist toward the orb
    toO = (orbC - wr); toO.z = 0; toO.normalize(); side = Vector((-toO.y, toO.x, 0))
    knuckles = []
    for f in range(5):
        s_ = (f - 2) / 2.0
        kn = wr + toO * 95 + side * s_ * 55 + Vector((0, 0, 6 + 8 * (1 - abs(s_))))
        bone_tube(b, [wr + side * s_ * 14, wr + toO * 50 + side * s_ * 34 + Vector((0, 0, 8)), kn], 12, 10, segs=8)
        knuckles.append(kn)
    # fingers curl up over the orb; the thumb wraps from the other side
    for f, kn in enumerate(knuckles):
        u = (kn - orbC); u.normalize()
        w = Vector((0, 0, 1)) - u * u.z; w.normalize()
        R2 = orbR + 14; pts = [kn]
        for j in range(1, 6):
            th = math.radians(18 + j * (16 if f != 4 else 12))
            pts.append(orbC + (u * math.cos(th) + w * math.sin(th)) * R2)
        for j in range(0, 5, 2):
            bone_tube(b, pts[j:j + 3], 10 - j * 1.2, 9 - j * 1.4, segs=8)
        cone(b, pts[-1], pts[-1] - pts[-2], 26, 6, segs=6, pid=OLD)          # claw
    th_base = wr + toO * 40 - side * 70
    tp = [th_base, th_base + toO * 50 - side * 40 + Vector((0, 0, 30)), orbC - side * (orbR + 10) + Vector((0, 0, 30)), orbC - side * (orbR * 0.6) + toO * 20 + Vector((0, 0, orbR * 0.9))]
    bone_tube(b, tp, 14, 8, segs=8)
    mound(b, wr + Vector((0, 0, -10)), 70, 70, 16)
    # the other arm: torn off and lying back along the body
    sh2 = spine_pt(0.05) + Vector((-60, 0, 10))
    bone_tube(b, [sh2, sh2 + Vector((-160, -120, -6)), sh2 + Vector((-210, -310, -14))], 30, 22, segs=12)
    mound(b, sh2 + Vector((-200, -300, -16)), 90, 80, 24)
    # ---------------------------------------------------------------- debris: smashed bone and blocks thrown about by the battle
    rng = random.Random(7)
    for k in range(70):
        a = rng.uniform(0, math.tau); r = rng.uniform(150, 1100)
        c = Vector((math.cos(a) * r * 0.7 + 120, math.sin(a) * r - 200, rng.uniform(-6, 4)))
        s_ = rng.uniform(5, 26)
        if rng.random() < 0.55: ellipsoid(b, c, (s_, s_ * rng.uniform(1.2, 2.5), s_ * 0.6), rot(rng.uniform(0, 360), rng.uniform(-30, 30)), sub=1, jitter=0.3, seed=k, pid=OLD)
        else: cone(b, c, (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.2, 1.2)), s_ * 3, s_ * 0.5, segs=5, pid=BONE)
    return b

def build_skull():
    """the cranium: an elongated alien helmet of bone with deep sockets, tipped onto its side"""
    sk = Skel(1.0)
    for nm, x, y, z, rs, rv in (("cran", 0, 0, 0, 120, 110), ("occ", 0, -130, 45, 100, 95), ("crest", 0, -230, 105, 62, 58),
                                ("brow", 0, 95, 5, 88, 70), ("face", 0, 175, -45, 58, 52), ("muzzle", 0, 235, -75, 34, 32),
                                ("cheekL", 78, 120, -40, 40, 34), ("cheekR", -78, 120, -40, 40, 34)):
        sk.v(nm, x, y, z, rs, rv)
    sk.e("crest", "occ", "cran", "brow", "face", "muzzle"); sk.e("brow", "cheekL"); sk.e("brow", "cheekR"); sk.e("face", "cheekL"); sk.e("face", "cheekR")
    body = metaball_body("titan_skull", sk, voxel=7.0, faces=14000, floor=False, mb_scale=1.12, stiffness=2.0)
    def weather(co, n):
        d = 3.5 * (1 - abs(noise.noise(co * 0.012))) ** 5 * -1.0 + noise.noise(co * 0.03) * 2.0 + noise.noise(co * 0.004) * 6.0
        return co + n * d
    displace(body, weather)
    cutters = [((70, 120, 22), 52), ((-70, 120, 22), 52), ((0, 210, -38), 30), ((112, -40, 30), 46), ((-112, -40, 30), 46),
               ((40, -120, 140), 34), ((-55, -200, 120), 22), ((95, 60, -95), 26)]
    for i, (c, r) in enumerate(cutters):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=c)
        cu = bpy.context.active_object; cu.name = "cut%d" % i
        m = body.modifiers.new("cut%d" % i, 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cu
        try: m.solver = 'EXACT'
        except Exception: pass
        select_only([body]); bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(cu, do_unlink=True)
    me = body.data
    a = me.attributes.new("part", 'INT', 'FACE')
    for p in me.polygons:
        cpos = p.center; pid = BONE
        for c, r in cutters:
            if (cpos - Vector(c)).length < r * 1.04: pid = DARK
        a.data[p.index].value = pid
    # teeth along the upper jaw
    tb = B(); tb.pid = OLD
    for k in range(9):
        for sx in (1, -1):
            y = 230 - k * 16; x = sx * (24 + k * 4.5)
            cone(tb, (x, y, -95), (sx * 0.15, 0.25, -1), 34 - k * 1.5, 7, segs=6, pid=OLD)
    teeth = tb.finish("titan_teeth")
    for o in (body, teeth):
        o.matrix_world = Matrix.Translation((-90, 690, 70)) @ rot(-8, -18, 62).to_4x4()
    return body, teeth


def split_chunks(obj, limit=60000):
    """KSP meshes are 16-bit indexed: cut the mesh into spatial chunks under the vertex limit"""
    todo = [obj]; done = []
    while todo:
        o = todo.pop()
        if len(o.data.loops) <= limit: done.append(o); continue      # worst case: every corner its own exported vertex
        me = o.data; cs = [p.center.copy() for p in me.polygons]
        dims = [max(c[i] for c in cs) - min(c[i] for c in cs) for i in range(3)]; ax = dims.index(max(dims))
        vals = sorted(c[ax] for c in cs); med = vals[len(vals) // 2]
        for v in me.vertices: v.select = False
        for e in me.edges: e.select = False
        for p, c in zip(me.polygons, cs): p.select = c[ax] < med
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        select_only([o]); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
        new = [x for x in bpy.context.selected_objects if x is not o]
        todo += [o] + new
    for i, o in enumerate(sorted(done, key=lambda x: x.name)): o.name = "%s_mesh%d" % (NAME, i); o.data.name = o.name
    return done

# ============================================================================ material
def titan_nodes(N):
    k = 1.0
    zz = N.Z
    crack = N.m('LESS_THAN', N.voronoi(0.012, 'DISTANCE_TO_EDGE', rand=1.0), 0.012)
    crack2 = N.m('LESS_THAN', N.voronoi(0.11, 'DISTANCE_TO_EDGE', rand=1.0), 0.02)
    mott = N.noise(0.02, 6, rough=0.6)
    bone = N.mix((0.80, 0.76, 0.68), (0.62, 0.58, 0.50), mott)
    bone = N.mix(bone, (0.90, 0.88, 0.82), N.m('MULTIPLY', N.m('GREATER_THAN', N.noise(0.006, 3), 0.62), 0.5))
    bone = N.mix(bone, (0.36, 0.32, 0.28), N.m('MULTIPLY', N.m('MULTIPLY', crack, N.m('GREATER_THAN', N.noise(0.01, 2), 0.45)), 0.7)); bone = N.mix(bone, (0.42, 0.38, 0.33), N.m('MULTIPLY', crack2, 0.6))
    soil = N.mix((0.55, 0.39, 0.29), (0.45, 0.32, 0.24), N.noise(0.015, 5))
    stain = N.m('SUBTRACT', 1.0, N.m('DIVIDE', N.m('MAXIMUM', zz, 0.0), 30.0), clamp=True)      # red badlands staining near the ground
    dust = N.m('MULTIPLY', N.m('GREATER_THAN', N.NZ, 0.55), N.m('GREATER_THAN', N.noise(0.03, 3), 0.45))
    bone = N.mix(bone, soil, N.m('ADD', N.m('MULTIPLY', stain, 0.75), N.m('MULTIPLY', dust, 0.45), clamp=True))
    old = N.mix((0.55, 0.48, 0.38), (0.38, 0.32, 0.26), mott); old = N.mix(old, soil, N.m('MULTIPLY', stain, 0.6))
    sed = N.mix(soil, (0.60, 0.44, 0.32), N.m('MULTIPLY', N.m('GREATER_THAN', N.wave(0.08, 'BANDS', 'Z', 2.0), 0.7), 0.25))
    dark = N.mix((0.08, 0.06, 0.05), (0.2, 0.15, 0.12), N.noise(0.05, 3))
    orbcr = N.m('LESS_THAN', N.voronoi(0.045, 'DISTANCE_TO_EDGE', rand=1.0), 0.03)
    orb = N.mix(N.mix((0.30, 0.20, 0.14), (0.62, 0.42, 0.24), N.noise(0.05, 4)), (1.0, 0.8, 0.45), orbcr)
    metal = N.mix((0.32, 0.26, 0.20), (0.18, 0.15, 0.12), N.noise(0.08, 5)); metal = N.mix(metal, (0.45, 0.30, 0.18), N.m('MULTIPLY', N.m('GREATER_THAN', N.noise(0.03, 4), 0.6), 0.6))
    veins = N.m('MULTIPLY', N.m('LESS_THAN', N.voronoi(0.03, 'DISTANCE_TO_EDGE', rand=1.0), 0.018), N.m('GREATER_THAN', N.noise(0.02, 3), 0.42))
    glass = N.mix((0.09, 0.07, 0.07), (0.22, 0.14, 0.10), N.noise(0.05, 4)); glass = N.mix(glass, (0.9, 0.45, 0.15), N.m('MULTIPLY', veins, 0.8))
    c = sed
    for i, col in ((BONE, bone), (OLD, old), (DARK, dark), (ORB, orb), (METAL, metal), (SCORCH, glass)): c = N.mix(c, col, N.is_part(i))
    ao = N.node('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 40.0
    try: ao.samples = 16
    except Exception: pass
    c = N.mix(c, N.ramp(ao.outputs['AO'], [(0.0, (0.35, 0.35, 0.35)), (1.0, (1, 1, 1))]), 1.0, 'MULTIPLY')
    g = N.mix((0, 0, 0), N.mix((0.55, 0.25, 0.05), (1.0, 0.75, 0.35), orbcr), N.is_part(ORB))
    g = N.mix(g, (0.9, 0.35, 0.08), N.m('MULTIPLY', N.m('MULTIPLY', veins, N.is_part(SCORCH)), 0.85))
    return c, g

def bake(obj, out_dir, res=2048, gres=1024, samples=8):
    os.makedirs(out_dir, exist_ok=True); scn = bpy.context.scene; me = obj.data
    mat = bpy.data.materials.get(NAME + "_bake") or bpy.data.materials.new(NAME + "_bake")
    N = Nodes(mat); col, glow = titan_nodes(N)
    emit = N.node('ShaderNodeEmission'); out = N.node('ShaderNodeOutputMaterial'); N.L(emit.outputs[0], out.inputs['Surface'])
    img_node = N.node('ShaderNodeTexImage'); me.materials.clear(); me.materials.append(mat)
    def one(sock, iname, r):
        img = bpy.data.images.get(iname)
        if img is None or img.size[0] != r:
            if img: bpy.data.images.remove(img)
            img = bpy.data.images.new(iname, r, r, alpha=False)
        img.colorspace_settings.name = 'Non-Color'; img_node.image = img
        for n_ in N.nt.nodes: n_.select = False
        img_node.select = True; N.nt.nodes.active = img_node
        N.L(sock, emit.inputs['Color'])
        scn.render.engine = 'CYCLES'; scn.cycles.samples = samples; scn.cycles.device = 'CPU'
        scn.render.bake.margin = 8; scn.render.bake.use_clear = True
        select_only([obj]); bpy.ops.object.bake(type='EMIT')
        img.filepath_raw = os.path.join(out_dir, iname + ".png"); img.file_format = 'PNG'; img.save()
        img.colorspace_settings.name = 'sRGB'
        return img
    d_img = one(col, NAME + "_diffuse", res); g_img = one(glow, NAME + "_glow", gres)
    fm = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    fm.use_nodes = True; ft = fm.node_tree; ft.nodes.clear()
    bs = ft.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = 0.9
    fo = ft.nodes.new('ShaderNodeOutputMaterial'); ft.links.new(bs.outputs[0], fo.inputs['Surface'])
    dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = d_img; ft.links.new(dt.outputs[0], bs.inputs['Base Color'])
    gt = ft.nodes.new('ShaderNodeTexImage'); gt.image = g_img; ft.links.new(gt.outputs[0], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = 1.0
    me.materials.clear(); me.materials.append(fm)
    mp = fm.mumatprop; mp.shaderName = "KSP/Emissive/Diffuse"
    for coll in (mp.color.properties, mp.texture.properties, mp.float2.properties, mp.float3.properties, mp.vector.properties): coll.clear()
    c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
    t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = d_img.name
    c = mp.color.properties.add(); c.name = "_EmissiveColor"; c.value = (1, 1, 1, 1)
    t = mp.texture.properties.add(); t.name = "_Emissive"; t.tex = g_img.name
    scn.render.engine = 'BLENDER_EEVEE'

def preview_mat(obj):
    mat = bpy.data.materials.get(NAME + "_prev") or bpy.data.materials.new(NAME + "_prev")
    N = Nodes(mat); col, glow = titan_nodes(N)
    gm = N.node('ShaderNodeGamma'); N.L(col, gm.inputs[0]); gm.inputs[1].default_value = 2.2
    bs = N.node('ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = 0.9
    N.L(gm.outputs[0], bs.inputs['Base Color']); N.L(glow, bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = 3.0
    out = N.node('ShaderNodeOutputMaterial'); N.L(bs.outputs[0], out.inputs['Surface'])
    obj.data.materials.clear(); obj.data.materials.append(mat)

def views(final):
    cam, g = stage_setup(ground=True, sky=(0.62, 0.66, 0.72), ground_col=(0.55, 0.38, 0.27), ground_size=6000.0)
    cam.data.type = 'PERSP'; cam.data.clip_start = 1.0; cam.data.clip_end = 30000
    out = {}
    for tag, pos, tgt, lens in (("a", (2300, -1900, 1100), (80, -100, 40), 35), ("b", (900, 1700, 260), (180, 300, 80), 30),
                                ("c", (520, -620, 140), (60, 150, 90), 24), ("d", (0, -0.01, 4200), (0, -150, 0), 35)):
        cam.data.lens = lens; look_at(cam, Vector(pos), Vector(tgt))
        out[tag] = render(os.path.join(PREVIEW_DIR, "titan_%s.png" % tag), res=(1280, 800))
    return out

if __name__ == "__xeno__":
    new_scene("XenoTitan")
    b = build_titan()
    obj = b.finish(NAME + "_mesh")
    skull, teeth = build_skull()
    for o in (skull, teeth):
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
        if "part" not in o.data.attributes:
            a = o.data.attributes.new("part", 'INT', 'FACE')
            for i in range(len(o.data.polygons)): a.data[i].value = BONE
    select_only([obj, skull, teeth], obj); bpy.ops.object.join()
    obj = bpy.context.active_object; obj.name = NAME + "_mesh"
    bm = bmesh.new(); bm.from_mesh(obj.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(obj.data); bm.free()
    hard_normals(obj, 55)
    root = link(bpy.data.objects.new(NAME, None)); obj.parent = root
    result = {"tris": len(obj.data.polygons), "dims": [round(x) for x in obj.dimensions]}
    if STEP == "model":
        preview_mat(obj); result.update(views(False))
    else:
        out_dir = os.path.join(XENO_DIR, "Models", "Fossils", "Kerbin")
        uv_unwrap(obj, margin=0.002)
        bake(obj, out_dir)
        parts = split_chunks(obj)
        for o in parts: o.parent = root
        result["chunks"] = [len(o.data.loops) for o in parts]
        result["export"] = export_mu(NAME, os.path.join(out_dir, NAME + ".mu"))
        result.update(views(True))
        # silhouette mask: just the skeleton, from above
        obj = parts[0]
        if len(parts) > 1:
            select_only(parts, parts[0]); bpy.ops.object.join(); obj = bpy.context.active_object
        keep = list(obj.data.materials)
        mat = bpy.data.materials.get("titan_mask") or bpy.data.materials.new("titan_mask")
        N = Nodes(mat); m = N.m('MULTIPLY', N.m('GREATER_THAN', N.part, 0.5), N.m('LESS_THAN', N.part, 5.5))
        mix = N.node('ShaderNodeMixShader'); tr = N.node('ShaderNodeBsdfTransparent'); em = N.node('ShaderNodeEmission')
        N.L(m, mix.inputs[0]); N.L(tr.outputs[0], mix.inputs[1]); N.L(em.outputs[0], mix.inputs[2])
        o2 = N.node('ShaderNodeOutputMaterial'); N.L(mix.outputs[0], o2.inputs['Surface'])
        obj.data.materials.clear(); obj.data.materials.append(mat)
        cam, g = stage_setup(ground=False); g.hide_render = True
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2600; cam.location = (60, -250, 3000); cam.rotation_euler = (0, 0, 0)
        bpy.context.scene.cycles.samples = 8
        result["silmask"] = render(os.path.join(PREVIEW_DIR, "titan_silmask.png"), 'CYCLES', (1024, 1024), True)
        obj.data.materials.clear()
        for mm in keep: obj.data.materials.append(mm)
        cam.data.type = 'PERSP'; g.hide_render = False
