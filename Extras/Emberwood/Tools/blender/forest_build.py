# Xenobiology — the Emberwood kit: autumn trees (6 species x 3 variants, LOD0 + LOD1 + impostor card), undergrowth,
# the elder tree, the footbridge and the spring's cascade rocks. Exported as
#   Models/Kerbin/Emberwood/forest_kit.mu   (meshes only; the plugin combines them into chunk meshes)
#   Models/Kerbin/Emberwood/forest_bridge.mu, forest_spring.mu  (placed set pieces with colliders)
# Kit child names (the plugin looks these up):
#   t_<species>_<v>_0 / _1   tree LOD0 / LOD1 (submeshes: bark, leaves[, glow])
#   t_<species>_imp          far card (3 crossed quads)
#   p_<prop>_<v>             fern, shrub, sapling, log, rock, streamrock, mushroom, stump, litter, reed, lily
#   elder_0, elder_1, elder_imp
# Origin at the base of the trunk, +Z up (Unity +Y), units metres.
import bpy, bmesh, os, math, random, json
import numpy as np
from mathutils import Vector, Matrix, Quaternion, noise
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
DEV = os.path.join(os.path.dirname(PREVIEW_DIR), "forest")
TEX = os.path.join(DEV, "tex")
OUT = os.path.join(XENO_DIR, "Models", "Kerbin", "Emberwood")
STEP = globals().get("STEP", "all")
STATUS = os.path.join(DEV, "build_status.json")
os.makedirs(OUT, exist_ok=True)

STRIPS = {"maple": 0, "birch": 1, "oak": 2, "torch": 3, "pine": 4, "lantern": 5, "rock": 6, "misc": 7}
def strip_u(k, u): return (k + 0.03 + 0.94 * u) / 8.0
def cell_uv(c, u, v):
    col, row = c % 4, c // 4
    return ((col + 0.02 + 0.96 * u) / 4.0, 1.0 - (row + 1) / 4.0 + (0.02 + 0.96 * v) / 4.0)

# ---------------------------------------------------------------------------- mesh builder
class MB:
    def __init__(self): self.V = []; self.F = []; self.UV = []; self.M = []
    def v(self, p): self.V.append(tuple(p)); return len(self.V) - 1
    def f(self, idx, uvs, m):
        self.F.append(tuple(idx)); self.UV.append(tuple(uvs)); self.M.append(m)
    def tris(self): return sum(len(f) - 2 for f in self.F)
    def build(self, name, mats):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.V, [], self.F)
        uvl = me.uv_layers.new(name="UVMap")
        k = 0
        for pi, poly in enumerate(me.polygons):
            for li, lo in enumerate(poly.loop_indices): uvl.data[lo].uv = self.UV[pi][li]
            poly.material_index = self.M[pi]; poly.use_smooth = True
        for m in mats: me.materials.append(m)
        o = bpy.data.objects.new(name, me); link(o)
        return o

def frame_of(d):
    d = d.normalized(); a = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    x = d.cross(a).normalized(); y = d.cross(x).normalized(); return x, y

def tube(mb, pts, rads, sides, strip, mat=0, cap=False, vbase=0.0):
    """Ring per point (parallel-transported frame), UV around = the bark strip, v = metres / tile length."""
    n = len(pts); x, y = frame_of(pts[1] - pts[0])
    rings = []; s = vbase
    circ0 = 2 * math.pi * max(rads[0], 0.04)
    for i in range(n):
        if i > 0:
            d = (pts[min(n - 1, i + 1)] - pts[i - 1]).normalized()
            x = (x - d * x.dot(d)).normalized(); y = d.cross(x).normalized()
            s += (pts[i] - pts[i - 1]).length
        ring = []
        for k in range(sides + 1):
            a = k / sides * 2 * math.pi
            p = pts[i] + (x * math.cos(a) + y * math.sin(a)) * rads[i]
            ring.append((mb.v(p), (strip_u(strip, k / sides), s / (circ0 * 8))))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            a, b, c, d = rings[i][k], rings[i][k + 1], rings[i + 1][k + 1], rings[i + 1][k]
            mb.f([a[0], b[0], c[0], d[0]], [a[1], b[1], c[1], d[1]], mat)
    if cap:
        c = mb.v(pts[-1] + (pts[-1] - pts[-2]).normalized() * rads[-1] * 0.3)
        for k in range(sides):
            a, b = rings[-1][k], rings[-1][k + 1]
            mb.f([a[0], b[0], c], [a[1], b[1], (strip_u(strip, 0.5), a[1][1])], mat)
    return s

def card(mb, base, up, side, w, h, cell, mat, bend=0.0, segs=2):
    """A leaf card: bottom-centre at base, rising along `up`, `side` across, bending forward (toward up x side) by bend."""
    up = up.normalized(); side = (side - up * side.dot(up))
    if side.length < 1e-4: side = frame_of(up)[0]
    side = side.normalized(); fwd = side.cross(up)
    rows = []
    p = Vector(base); dirv = Vector(up)
    for j in range(segs + 1):
        t = j / segs
        if j > 0:
            dirv = (up * math.cos(bend * t) + fwd * math.sin(bend * t)).normalized()
            p = p + dirv * (h / segs)
        rows.append((mb.v(p - side * w * 0.5), mb.v(p + side * w * 0.5), t))
    for j in range(segs):
        a, b, t0 = rows[j]; c, d, t1 = rows[j + 1]
        mb.f([a, b, d, c], [cell_uv(cell, 0, t0), cell_uv(cell, 1, t0), cell_uv(cell, 1, t1), cell_uv(cell, 0, t1)], mat)

# ---------------------------------------------------------------------------- species
SPEC = {
    "emberleaf": dict(bark="maple", cells=[0, 1, 2], H=(13, 16), trunkR=0.32, split=0.32, limbs=(3, 4), limbAng=(28, 42), limbLen=0.62,
                      sub=(3, 5), subAng=(35, 60), subLen=0.5, depth=3, droop=0.05, up=0.35, card=(2.1, 2.7), leaves=1.0, crownW=1.0),
    "goldenpale": dict(bark="birch", cells=[3, 4], H=(15, 19), trunkR=0.22, split=0.98, limbs=(9, 12), limbAng=(40, 65), limbLen=0.26,
                       sub=(2, 4), subAng=(30, 55), subLen=0.55, depth=3, droop=0.25, up=0.1, card=(1.8, 2.3), leaves=1.0, leader=True, crownW=0.6),
    "copperoak": dict(bark="oak", cells=[5, 6], H=(13, 17), trunkR=0.55, split=0.24, limbs=(3, 4), limbAng=(45, 65), limbLen=0.5,
                      sub=(3, 5), subAng=(30, 60), subLen=0.52, depth=3, droop=0.12, up=0.15, card=(2.4, 3.0), leaves=1.1, gnarl=0.35, crownW=1.35, roots=5),
    "torchwood": dict(bark="torch", cells=[7, 8], H=(11, 14), trunkR=0.26, split=0.12, limbs=(4, 6), limbAng=(18, 30), limbLen=0.6,
                      sub=(2, 4), subAng=(30, 55), subLen=0.42, depth=3, droop=0.05, up=0.4, card=(2.2, 2.8), leaves=0.9, crownW=0.95),
    "duskpine": dict(bark="pine", cells=[9, 10], H=(18, 24), trunkR=0.3, conifer=True, card=(2.6, 3.3), crownW=0.55),
    "lanternfruit": dict(bark="lantern", cells=[11], H=(6.5, 8.5), trunkR=0.2, split=0.38, limbs=(3, 4), limbAng=(40, 60), limbLen=0.7,
                         sub=(2, 4), subAng=(35, 60), subLen=0.5, depth=3, droop=0.18, up=0.1, card=(1.7, 2.2), leaves=0.9, gnarl=0.45, pods=True, crownW=1.1),
}
ORDER = ["emberleaf", "goldenpale", "copperoak", "torchwood", "duskpine", "lanternfruit"]

def wobble(v, seed, amt):
    return Vector((noise.noise(v * 0.6 + Vector((seed, 0, 0))), noise.noise(v * 0.6 + Vector((0, seed, 0))), noise.noise(v * 0.6 + Vector((0, 0, seed))))) * amt

class Tree:
    def __init__(self, sp, seed, scale=1.0):
        self.sp = SPEC[sp]; self.name = sp; self.rng = random.Random(seed); self.seed = seed
        self.H = self.rng.uniform(*self.sp["H"]) * scale
        self.branches = []      # (pts, rads, depth)
        self.leafpts = []       # (pos, dir, size)
        self.pods = []
        self.roots = []

    def grow(self):
        sp = self.sp; R = self.rng
        if sp.get("conifer"): return self.grow_conifer()
        H = self.H; r0 = sp["trunkR"] * H / 15
        trunkH = H * sp["split"] if not sp.get("leader") else H * 0.92
        lean = Vector((R.uniform(-1, 1), R.uniform(-1, 1), 0)) * 0.04
        pts, rads = [], []
        n = 8
        for i in range(n + 1):
            t = i / n
            p = Vector((0, 0, trunkH * t)) + lean * trunkH * t * t + wobble(Vector((0, 0, trunkH * t)), self.seed, sp.get("gnarl", 0.08) * r0 * 3 * t)
            pts.append(p)
            flare = 1 + 0.6 * max(0, 1 - t * 6) ** 2
            rads.append(r0 * (1 - 0.35 * t) * flare * (0.6 if sp.get("leader") and t > 0.5 else 1) * (1 - 0.5 * t if sp.get("leader") else 1))
        self.branches.append((pts, rads, 0))
        top, topR = pts[-1], rads[-1]
        if sp.get("leader"):
            # birch-like: one leader to the top, short limbs all the way up
            nl = R.randint(*sp["limbs"])
            for k in range(nl):
                t = 0.3 + 0.68 * k / nl
                i = int(t * n); p = pts[i]; rr = rads[i]
                az = k * 2.39996 + R.uniform(-0.3, 0.3); el = math.radians(R.uniform(*sp["limbAng"]))
                d = Vector((math.cos(az) * math.sin(el), math.sin(az) * math.sin(el), math.cos(el)))
                L = H * sp["limbLen"] * (1.25 - t * 0.7) * R.uniform(0.8, 1.15)
                self.branch(p, d, L, rr * 0.55, 1)
            self.leafpts.append((top, Vector((0, 0, 1)), sp["card"][1]))
            return self
        nl = R.randint(*sp["limbs"])
        for k in range(nl):
            az = k * 2 * math.pi / nl + R.uniform(-0.4, 0.4); el = math.radians(R.uniform(*sp["limbAng"]))
            d = Vector((math.cos(az) * math.sin(el), math.sin(az) * math.sin(el), math.cos(el)))
            L = (H - trunkH) * sp["limbLen"] * 1.35 * R.uniform(0.85, 1.15) * (sp["crownW"] ** 0.5)
            self.branch(top, d, L, topR * R.uniform(0.62, 0.78), 1)
        if sp.get("roots"):
            for k in range(sp["roots"]):
                az = k * 2 * math.pi / sp["roots"] + R.uniform(-0.3, 0.3)
                d = Vector((math.cos(az), math.sin(az), 0))
                rp = [Vector((0, 0, r0 * 1.1)) + d * r0 * 0.3, Vector((0, 0, r0 * 0.25)) + d * r0 * 1.6, d * r0 * 2.8 + Vector((0, 0, -0.15))]
                self.roots.append((rp, [r0 * 0.55, r0 * 0.3, r0 * 0.1]))
        return self

    def branch(self, p, d, L, r, depth):
        sp = self.sp; R = self.rng
        n = max(3, int(L / 1.2) + 2)
        pts, rads = [Vector(p)], [r]
        dd = Vector(d); q = Vector(p)
        for i in range(1, n + 1):
            t = i / n
            dd = (dd + Vector((0, 0, sp["up"] * 0.15 - sp["droop"] * 0.25 * t)) + wobble(q * 1.3, self.seed + depth, 0.18 + sp.get("gnarl", 0) * 0.4)).normalized()
            q = q + dd * (L / n); pts.append(Vector(q)); rads.append(r * (1 - 0.75 * t) + 0.012)
        self.branches.append((pts, rads, depth))
        if depth >= sp["depth"] - 1:
            for i in range(max(1, int(n * 0.4)), n + 1):
                self.leafpts.append((pts[i], (pts[i] - pts[i - 1]).normalized(), R.uniform(*sp["card"]) * 1.15))
        if depth >= sp["depth"] or r < 0.035:
            # leaves: along the outer part and at the tip
            for i in range(max(1, n // 2), n + 1):
                self.leafpts.append((pts[i], (pts[i] - pts[i - 1]).normalized(), R.uniform(*sp["card"])))
            return
        ns = R.randint(*sp["sub"])
        for k in range(ns):
            t = R.uniform(0.35, 0.95)
            i = min(n - 1, int(t * n)); bp = pts[i]
            ax = (pts[i + 1] - pts[i]).normalized(); x, y = frame_of(ax)
            az = R.uniform(0, 2 * math.pi); el = math.radians(R.uniform(*sp["subAng"]))
            nd = (ax * math.cos(el) + (x * math.cos(az) + y * math.sin(az)) * math.sin(el)).normalized()
            # keep shoots pointing outward from the crown and not too far down
            outward = Vector((bp.x, bp.y, 0));
            if outward.length > 0.1: nd = (nd + outward.normalized() * 0.35).normalized()
            if nd.z < -0.3: nd.z = -0.3; nd.normalize()
            self.branch(bp, nd, L * sp["subLen"] * R.uniform(0.75, 1.2), rads[i] * R.uniform(0.55, 0.7), depth + 1)
        self.leafpts.append((pts[-1], (pts[-1] - pts[-2]).normalized(), R.uniform(*sp["card"])))
        if sp.get("pods") and depth >= 1 and R.random() < 0.5:
            for k in range(R.randint(2, 4)):
                self.pods.append(pts[-1] + Vector((R.uniform(-0.4, 0.4), R.uniform(-0.4, 0.4), -R.uniform(0.3, 0.7))))

    def grow_conifer(self):
        sp = self.sp; R = self.rng; H = self.H; r0 = sp["trunkR"] * H / 20
        pts = [Vector((0, 0, H * i / 10)) + wobble(Vector((0, 0, H * i / 10)), self.seed, 0.06) for i in range(11)]
        rads = [r0 * (1 - 0.92 * i / 10) * (1 + 0.5 * max(0, 1 - i * 1.5) ** 2) for i in range(11)]
        self.branches.append((pts, rads, 0))
        z = H * 0.18
        while z < H * 0.97:
            t = (z - H * 0.18) / (H * 0.8)
            L = (H * 0.3) * (1 - t) ** 0.9 + 0.6
            nw = R.randint(5, 7)
            for k in range(nw):
                az = k * 2 * math.pi / nw + R.uniform(-0.3, 0.3) + z
                d = Vector((math.cos(az), math.sin(az), -0.15 + 0.35 * t)).normalized()
                p0 = Vector((0, 0, z))
                n = 3; bp = [p0]; q = Vector(p0)
                for i in range(1, n + 1):
                    q = q + d * (L / n) + Vector((0, 0, -0.08 * L / n * i)); bp.append(Vector(q))
                self.branches.append((bp, [r0 * 0.25 * (1 - t * 0.6) * (1 - 0.7 * i / n) + 0.01 for i in range(n + 1)], 1))
                # flat needle sprays along the branch
                for i in range(1, n + 1):
                    j = min(n, max(1, i))
                    self.leafpts.append((bp[i] - (bp[j] - bp[j - 1]) * 0.3, (bp[j] - bp[j - 1]).normalized(), R.uniform(*sp["card"]) * (0.55 + 0.45 * (1 - t))))
            z += R.uniform(0.55, 0.8) * (1.0 - 0.35 * t)
        self.leafpts.append((pts[-1] - Vector((0, 0, 0.5)), Vector((0, 0, 1)), 1.4))
        return self

    def mesh(self, lod, mats, name):
        sp = self.sp; R = random.Random(self.seed * 7 + lod); mb = MB()
        strip = STRIPS[sp["bark"]]
        for pts, rads, depth in self.branches:
            if lod == 1 and (depth >= 2 or (sp.get("conifer") and depth >= 1)): continue
            if lod == 0 and depth >= 3 and rads[0] < 0.03: continue
            sides = (8 if depth == 0 else (3 if sp.get('conifer') else 6) if depth == 1 else 4) if lod == 0 else (5 if depth == 0 else 3)
            if lod == 1 and depth == 1: pts, rads = pts[::2] + ([pts[-1]] if len(pts) % 2 == 0 else []), rads[::2] + ([rads[-1]] if len(rads) % 2 == 0 else [])
            tube(mb, pts, rads, sides, strip, 0)
        for rp, rr in self.roots:
            tube(mb, rp, rr, 8 if lod == 0 else 4, strip, 0)
        cells = sp["cells"]
        leaf = self.leafpts if lod == 0 else R.sample(self.leafpts, max(10, len(self.leafpts) // (6 if sp.get('conifer') else 4)))
        grow = 1.12 if lod == 0 else (1.8 if sp.get('conifer') else 1.95)
        ctr = Vector((0, 0, 0))
        for p, d, s in self.leafpts: ctr += p
        ctr /= max(1, len(self.leafpts))
        for p, d, s in leaf:
            s *= grow
            if sp.get("conifer"):
                # spray lies along the branch, roughly horizontal
                side = d.cross(Vector((0, 0, 1)))
                if side.length < 0.1: side = Vector((1, 0, 0))
                side.normalize()
                upv = d; base = p - d * 0.2
                rot = Quaternion(d, R.uniform(-0.35, 0.35))
                card(mb, base, upv, rot @ side, s * 0.95, s, R.choice(cells), 1, bend=-0.35, segs=2 if lod == 0 else 1)
                rot2 = Quaternion(d, R.choice([-1, 1]) * R.uniform(0.8, 1.1))
                card(mb, base, upv, rot2 @ side, s * 0.8, s * 0.9, R.choice(cells), 1, bend=-0.2, segs=1)
                continue
            out = (p - ctr); out.z *= 0.5
            out = out.normalized() if out.length > 0.01 else Vector((0, 0, 1))
            upv = (d * 0.6 + out * 0.6 + Vector((0, 0, 0.35))).normalized()
            for kk in range(1 if lod == 1 else 2 if R.random() < 0.45 else 1):   # ~1.45 cards a point: a third fewer triangles
                side = Quaternion(upv, R.uniform(0, math.pi)) @ frame_of(upv)[0]
                card(mb, p - upv * s * 0.25, upv, side, s * R.uniform(0.85, 1.05), s, R.choice(cells), 1, bend=R.uniform(0.2, 0.5) * (1 if R.random() < 0.5 else -1), segs=2 if lod == 0 else 1)
        if sp.get("pods") and lod == 0:
            for p in self.pods:
                b0 = len(mb.V)
                for k in range(6):
                    a = k / 6 * 2 * math.pi
                    for z in (-0.12, 0.12): mb.v(p + Vector((math.cos(a) * 0.1 * (1 - abs(z) * 2), math.sin(a) * 0.1 * (1 - abs(z) * 2), z)))
                top = mb.v(p + Vector((0, 0, 0.2))); bot = mb.v(p + Vector((0, 0, -0.2)))
                for k in range(6):
                    k2 = (k + 1) % 6
                    a0, a1, b0_, b1_ = b0 + k * 2, b0 + k2 * 2, b0 + k * 2 + 1, b0 + k2 * 2 + 1
                    mb.f([a0, a1, b1_, b0_], [(0.5, 0.2), (0.6, 0.2), (0.6, 0.8), (0.5, 0.8)], 2)
                    mb.f([b0_, b1_, top], [(0.5, 0.8), (0.6, 0.8), (0.55, 1.0)], 2)
                    mb.f([a1, a0, bot], [(0.6, 0.2), (0.5, 0.2), (0.55, 0.0)], 2)
                # stalk
                mb.f([mb.v(p + Vector((0, 0, 0.2))), mb.v(p + Vector((0.01, 0, 0.55))), mb.v(p + Vector((-0.01, 0, 0.55)))], [(0.07, 0.6), (0.07, 0.7), (0.06, 0.7)], 0)
        o = mb.build(name, mats)
        return o, mb.tris()

# ---------------------------------------------------------------------------- materials
def img(name):
    path = os.path.join(TEX, name + ".png")
    if name in bpy.data.images: bpy.data.images.remove(bpy.data.images[name])
    im = bpy.data.images.load(path); im.name = name
    return im

def mat_ksp(name, shader, tex, nrm=None, cutoff=None, emis=None, emiscol=(1, 1, 1, 1)):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = 0.9
    out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(bs.outputs[0], out.inputs['Surface'])
    ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = tex; nt.links.new(ti.outputs[0], bs.inputs['Base Color'])
    if cutoff is not None:
        nt.links.new(ti.outputs[1], bs.inputs['Alpha'])
        try: m.blend_method = 'CLIP'
        except Exception: pass
        m.use_backface_culling = False
    if emis is not None:
        nt.links.new(ti.outputs[0], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = 3.0
    mp = m.mumatprop; mp.shaderName = shader
    for coll in (mp.color.properties, mp.texture.properties, mp.float2.properties, mp.float3.properties, mp.vector.properties): coll.clear()
    c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
    t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = tex.name
    if nrm is not None:
        t = mp.texture.properties.add(); t.name = "_BumpMap"; t.tex = nrm.name; t.type = True
    if cutoff is not None:
        f = mp.float2.properties.add(); f.name = "_Cutoff"; f.value = cutoff
    if emis is not None:
        c = mp.color.properties.add(); c.name = "_EmissiveColor"; c.value = emiscol
        t = mp.texture.properties.add(); t.name = "_Emissive"; t.tex = emis.name
    return m

def glow_image():
    path = os.path.join(TEX, "forest_glow.png")
    if not os.path.exists(path):
        im = bpy.data.images.new("forest_glow", 64, 64, alpha=False)
        px = []
        for y in range(64):
            for x in range(64):
                t = y / 63
                px += [1.0, 0.55 + 0.4 * t, 0.15 + 0.5 * t ** 2, 1.0]
        im.pixels = px; im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    return img("forest_glow")

def status(d):
    json.dump(d, open(STATUS, "w"))

# ---------------------------------------------------------------------------- props
def prop_mesh(kind, v, M):
    R = random.Random(hash((kind, v)) & 0xffff); mb = MB()
    if kind == "fern":
        n = R.randint(9, 13); cell = 12 + (v % 2)
        for k in range(n):
            a = k / n * 2 * math.pi + R.uniform(-0.25, 0.25)
            out = Vector((math.cos(a), math.sin(a), 0))
            up = (out * R.uniform(0.7, 1.0) + Vector((0, 0, 1)) * R.uniform(0.45, 0.75)).normalized()
            card(mb, out * 0.05, up, out.cross(Vector((0, 0, 1))), R.uniform(0.38, 0.5), R.uniform(0.75, 1.05), cell, 1, bend=-R.uniform(0.7, 1.1), segs=3)   # negative: arches outward
        return mb, [M["bark"], M["leaf"]]
    if kind == "shrub":
        for k in range(R.randint(3, 5)):
            a = R.uniform(0, 6.28); d = Vector((math.cos(a) * 0.4, math.sin(a) * 0.4, 1)).normalized()
            pts = [Vector((0, 0, 0)), d * 0.6, d * 1.1 + Vector((math.cos(a) * 0.2, math.sin(a) * 0.2, 0))]
            tube(mb, pts, [0.03, 0.02, 0.01], 3, STRIPS["torch"], 0)
        cell = 14 if v < 2 else 2
        for k in range(14):
            a = R.uniform(0, 6.28); r = R.uniform(0.1, 0.6)
            p = Vector((math.cos(a) * r, math.sin(a) * r, R.uniform(0.3, 1.1)))
            up = (Vector((math.cos(a), math.sin(a), 0)) * 0.6 + Vector((0, 0, 1))).normalized()
            card(mb, p - up * 0.3, up, Quaternion(up, R.uniform(0, 3.14)) @ frame_of(up)[0], R.uniform(0.9, 1.2), R.uniform(0.9, 1.2), cell, 1, bend=0.4)
        return mb, [M["bark"], M["leaf"]]
    if kind == "reed":
        for k in range(3):
            a = k * math.pi / 3 + R.uniform(-0.2, 0.2)
            card(mb, Vector((0, 0, -0.05)), Vector((0, 0, 1)), Vector((math.cos(a), math.sin(a), 0)), 1.6, 1.8, 15, 1, bend=0.0, segs=1)
        return mb, [M["bark"], M["leaf"]]
    if kind == "lily":
        a = Vector((-0.6, -0.6, 0)); b = Vector((0.6, -0.6, 0)); c = Vector((0.6, 0.6, 0)); d = Vector((-0.6, 0.6, 0))
        mb.f([mb.v(a), mb.v(b), mb.v(c), mb.v(d)], [(0, 0), (1, 0), (1, 1), (0, 1)], 0)
        return mb, [M["lily"]]
    if kind in ("rock", "streamrock"):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        sq = (1.0, 0.8, 0.55) if kind == "rock" else (1.0, 0.75, 0.38)
        seed = v * 13 + (0 if kind == "rock" else 50)
        for vert in bm.verts:
            p = vert.co
            dsp = 1 + 0.28 * noise.noise(p * 1.4 + Vector((seed, 0, 0))) + 0.1 * noise.noise(p * 4 + Vector((0, seed, 0)))
            vert.co = Vector((p.x * sq[0], p.y * sq[1], p.z * sq[2])) * dsp
            if vert.co.z < -0.15: vert.co.z = -0.15 + (vert.co.z + 0.15) * 0.2
        bm.verts.ensure_lookup_table()
        for f in bm.faces:
            idx = [mb.v(vv.co) for vv in f.verts]
            uvs = [(strip_u(6, (math.atan2(vv.co.y, vv.co.x) / 6.283 + 0.5)), (vv.co.z + 1) * 0.12 + vv.co.x * 0.05) for vv in f.verts]
            # fix the seam: keep u continuous within a face
            us = [u for u, _ in uvs]
            if max(us) - min(us) > 0.06: uvs = [(u if u > strip_u(6, 0.5) else u + 0.94 / 8, vv) for u, vv in uvs]
            mb.f(idx, uvs, 0)
        bm.free()
        return mb, [M["bark"]]
    if kind == "log":
        L = R.uniform(4, 6.5); r = R.uniform(0.28, 0.4); bark = [STRIPS["maple"], STRIPS["oak"], STRIPS["birch"]][v % 3]
        pts = [Vector((-L / 2 + L * t, 0, r * 0.7 + 0.05 * math.sin(t * 6))) for t in np.linspace(0, 1, 6)]
        tube(mb, pts, [r * (1 - 0.15 * t) for t in np.linspace(0, 1, 6)], 9, bark, 0)
        for end, rr in ((pts[0], r), (pts[-1], r * 0.85)):
            c = mb.v(end); ring = []
            for k in range(10):
                a = k / 10 * 2 * math.pi
                ring.append((mb.v(end + Vector((0, math.cos(a) * rr, math.sin(a) * rr))), (strip_u(7, 0.5 + 0.47 * math.cos(a)), 1 - (0.5 + 0.47 * math.sin(a)) * 0.125)))
            for k in range(10):
                a_, b_ = ring[k], ring[(k + 1) % 10]
                mb.f([c, a_[0], b_[0]], [(strip_u(7, 0.5), 1 - 0.0625), a_[1], b_[1]], 0)
        # a broken branch stub
        tube(mb, [pts[2], pts[2] + Vector((0.2, 0.5, 0.6))], [r * 0.35, r * 0.15], 5, bark, 0, cap=True)
        return mb, [M["bark"]]
    if kind == "stump":
        r = R.uniform(0.35, 0.55); bark = [STRIPS["oak"], STRIPS["maple"]][v % 2]
        pts = [Vector((0, 0, -0.1)), Vector((0, 0, 0.3)), Vector((0, 0, 0.55))]
        tube(mb, pts, [r * 1.5, r * 1.05, r], 10, bark, 0)
        c = mb.v(Vector((0, 0, 0.6))); ring = []
        for k in range(10):
            a = k / 10 * 2 * math.pi; z = 0.55 + 0.06 * math.sin(a * 3)
            ring.append((mb.v(Vector((math.cos(a) * r, math.sin(a) * r, z))), (strip_u(7, 0.5 + 0.47 * math.cos(a)), 1 - (0.5 + 0.47 * math.sin(a)) * 0.125)))
        for k in range(10):
            a_, b_ = ring[k], ring[(k + 1) % 10]
            mb.f([c, a_[0], b_[0]], [(strip_u(7, 0.5), 1 - 0.0625), a_[1], b_[1]], 0)
        return mb, [M["bark"]]
    if kind == "mushroom":
        for k in range(R.randint(3, 6)):
            p = Vector((R.uniform(-0.3, 0.3), R.uniform(-0.3, 0.3), 0)); h = R.uniform(0.08, 0.22); cr = R.uniform(0.06, 0.14)
            st = [mb.v(p + Vector((math.cos(a) * cr * 0.25, math.sin(a) * cr * 0.25, z))) for z in (0, h) for a in np.linspace(0, 6.283, 6, endpoint=False)]
            for j in range(6):
                j2 = (j + 1) % 6
                mb.f([st[j], st[j2], st[6 + j2], st[6 + j]], [(strip_u(7, j / 6), 1 - 0.4), (strip_u(7, (j + 1) / 6), 1 - 0.4), (strip_u(7, (j + 1) / 6), 1 - 0.49), (strip_u(7, j / 6), 1 - 0.49)], 0)
            top = mb.v(p + Vector((0, 0, h + cr * 0.6)))
            rim = [mb.v(p + Vector((math.cos(a) * cr, math.sin(a) * cr, h - cr * 0.05))) for a in np.linspace(0, 6.283, 8, endpoint=False)]
            for j in range(8):
                mb.f([rim[j], rim[(j + 1) % 8], top], [(strip_u(7, j / 8), 1 - 0.36), (strip_u(7, (j + 1) / 8), 1 - 0.36), (strip_u(7, j / 8 + 0.06), 1 - 0.14)], 0)
        return mb, [M["bark"]]
    if kind == "litter":
        # a low drift of leaves: a soft mound with ragged edge, floor texture planar-mapped
        rr = R.uniform(0.9, 1.6); n = 12
        c = mb.v(Vector((0, 0, R.uniform(0.12, 0.25)))); ring = []
        for k in range(n):
            a = k / n * 2 * math.pi; r = rr * (0.75 + 0.35 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, v))))
            ring.append(Vector((math.cos(a) * r, math.sin(a) * r, -0.04)))
        mid = [Vector((p.x * 0.55, p.y * 0.55, 0.08 + R.uniform(0, 0.06))) for p in ring]
        ir = [mb.v(p) for p in ring]; im = [mb.v(p) for p in mid]
        uv = lambda p: (p.x / 6.0 + 0.5, p.y / 6.0 + 0.5)
        for k in range(n):
            k2 = (k + 1) % n
            mb.f([ir[k], ir[k2], im[k2], im[k]], [uv(ring[k]), uv(ring[k2]), uv(mid[k2]), uv(mid[k])], 0)
            mb.f([im[k], im[k2], c], [uv(mid[k]), uv(mid[k2]), (0.5, 0.5)], 0)
        return mb, [M["floor"]]
    if kind == "sapling":
        t = Tree("emberleaf" if v == 0 else "torchwood", 900 + v, scale=0.22).grow()
        return t, None
    raise ValueError(kind)

PROPS = [("fern", 3), ("shrub", 3), ("sapling", 2), ("log", 3), ("rock", 4), ("streamrock", 4), ("mushroom", 3), ("stump", 2), ("litter", 4), ("reed", 3), ("lily", 2)]

# ---------------------------------------------------------------------------- impostors
def impostor_mesh(name, H, W, col, mats):
    """Three vertical quads crossed at 60 degrees, mapped to one cell (512 x 1024) of the 4 x 2 impostor atlas."""
    mb = MB(); u0, u1 = (col % 4) / 4 + 0.002, (col % 4 + 1) / 4 - 0.002
    v0, v1 = (1 - (col // 4 + 1) / 2) + 0.002, (1 - (col // 4) / 2) - 0.002      # 4 x 2 square cells (2048 x 1024)
    for k in range(3):
        a = k * math.pi / 3; d = Vector((math.cos(a), math.sin(a), 0)) * W / 2
        p = [mb.v(-d), mb.v(d), mb.v(d + Vector((0, 0, H))), mb.v(-d + Vector((0, 0, H)))]
        mb.f(p, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], 0)
    return mb.build(name, mats)

def render_impostors(trees):
    """Orthographic side views of variant 0 of each species (flat albedo, alpha), packed into an 8-column atlas."""
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE'; scn.render.film_transparent = True
    scn.render.resolution_x = 512; scn.render.resolution_y = 512; scn.render.image_settings.file_format = 'PNG'; scn.render.image_settings.color_mode = 'RGBA'
    try: scn.view_settings.view_transform = 'Standard'
    except Exception: pass
    cam = bpy.data.objects.get("imp_cam") or link(bpy.data.objects.new("imp_cam", bpy.data.cameras.new("imp_cam")))
    cam.data.type = 'ORTHO'; scn.camera = cam
    # emission-only copies of the materials so the cards carry albedo, not lighting
    for o in bpy.data.objects: o.hide_render = True
    cam.hide_render = False
    atlas = np.zeros((1024, 2048, 4), np.float32)
    dims = {}
    for col, (nm, o) in enumerate(trees):
        o.hide_render = False
        saved = [s.material for s in o.material_slots]
        for s in o.material_slots:
            m = s.material.copy(); nt = m.node_tree
            bs = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]; ti = [n for n in nt.nodes if n.type == 'TEX_IMAGE'][0]
            em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(ti.outputs[0], em.inputs['Color'])
            mix = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
            cut = any(k in m.name for k in ("leaves", "lily", "imp"))
            if cut: nt.links.new(ti.outputs[1], mix.inputs[0])
            else: mix.inputs[0].default_value = 1.0
            nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
            out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]; nt.links.new(mix.outputs[0], out.inputs['Surface'])
            try: m.surface_render_method = 'DITHERED'
            except Exception: pass
            s.material = m
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        H = max(p.z for p in bb) * 1.02; W = max(max(abs(p.x) for p in bb), max(abs(p.y) for p in bb)) * 2 * 1.02
        H = max(H, W)                              # square cell: frame fits the taller or wider side
        cam.data.ortho_scale = H
        cam.location = (0, -80, H / 2); cam.rotation_euler = (math.pi / 2, 0, 0)
        dims[nm] = (H, H)
        path = os.path.join(DEV, "imp_%s.png" % nm)
        scn.render.filepath = path; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(path); a = np.array(im.pixels[:], np.float32).reshape(512, 512, 4); bpy.data.images.remove(im)
        r0 = 512 * (1 - col // 4)                  # pixel rows run bottom-up in Blender
        atlas[r0:r0 + 512, (col % 4) * 512:(col % 4 + 1) * 512] = a
        for s, m in zip(o.material_slots, saved): s.material = m
        o.hide_render = True
    # bleed colour into the transparent area (mip fringes) and save
    rgb = atlas[..., :3]; al = atlas[..., 3]
    known = al > 0.05
    for it in range(8):
        acc = np.zeros_like(rgb); cnt = np.zeros(al.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(np.roll(known, dy, 0), dx, 1); acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * sh[..., None]; cnt += sh
        new = (~known) & (cnt > 0); rgb[new] = acc[new] / cnt[new][:, None]; known |= new
    atlas[..., :3] = rgb
    im = bpy.data.images.new("forest_imp", 2048, 1024, alpha=True); im.pixels = atlas.ravel()
    im.filepath_raw = os.path.join(TEX, "forest_imp.png"); im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)
    for o in bpy.data.objects: o.hide_render = False
    return dims

# ---------------------------------------------------------------------------- bridge and spring
def build_bridge(M):
    """An arched timber footbridge, 11 m long (x), 2.2 m wide, deck ends at z = 0, crown +0.7 m. Stone abutments."""
    mb = MB(); L = 11.0; W = 2.2; rise = 0.7
    def zx(x): return rise * (1 - (2 * x / L) ** 2)
    def box(c, sx, sy, sz, rotz=0.0, pitch=0.0, mat=0, ustrip=None):
        R_ = Matrix.Rotation(rotz, 3, 'Z') @ Matrix.Rotation(pitch, 3, 'Y')
        corners = [Vector((x * sx / 2, y * sy / 2, z * sz / 2)) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        vs = [mb.v(c + R_ @ p) for p in corners]
        F = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        for f in F:
            mb.f([vs[i] for i in f], [(0.0, 0.0), (0.12, 0.0), (0.12, sx / 3), (0.0, sx / 3)], mat)
    # deck planks across the arch
    n = 30
    for i in range(n):
        x = -L / 2 + (i + 0.5) * L / n; z = zx(x)
        slope = math.atan(-rise * 8 * x / (L * L))
        box(Vector((x, 0, z - 0.04)), L / n * 0.9, W, 0.07, pitch=-slope, mat=0)
    # two arched stringers under the deck
    for y in (-W * 0.38, W * 0.38):
        for i in range(10):
            x0 = -L / 2 + i * L / 10; x1 = x0 + L / 10; xm = (x0 + x1) / 2
            box(Vector((xm, y, zx(xm) - 0.2)), L / 10 + 0.05, 0.18, 0.26, pitch=-math.atan(-rise * 8 * xm / (L * L)), mat=0)
    # posts and handrails
    for y in (-W / 2 + 0.06, W / 2 - 0.06):
        for i in range(7):
            x = -L / 2 + 0.4 + i * (L - 0.8) / 6; z = zx(x)
            box(Vector((x, y, z + 0.5)), 0.12, 0.12, 1.05, mat=0)
        for i in range(12):
            x0 = -L / 2 + 0.4 + i * (L - 0.8) / 12; xm = x0 + (L - 0.8) / 24
            box(Vector((xm, y, zx(xm) + 1.0)), (L - 0.8) / 12 + 0.04, 0.09, 0.08, pitch=-math.atan(-rise * 8 * xm / (L * L)), mat=0)
            box(Vector((xm, y, zx(xm) + 0.55)), (L - 0.8) / 12 + 0.04, 0.05, 0.05, pitch=-math.atan(-rise * 8 * xm / (L * L)), mat=0)
    # stone abutments at both ends
    rocks = MB()
    for sx in (-1, 1):
        for k in range(7):
            c = Vector((sx * (L / 2 - 0.3 + random.uniform(-0.3, 0.6)), random.uniform(-1.6, 1.6), random.uniform(-0.6, -0.1)))
            bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=random.uniform(0.45, 0.8))
            for v_ in bm.verts: v_.co = Vector((v_.co.x * 1.1, v_.co.y, v_.co.z * 0.7)) * (1 + 0.2 * noise.noise(v_.co * 2 + Vector((k, sx, 0))))
            for f in bm.faces:
                mb.f([mb.v(c + vv.co) for vv in f.verts], [(strip_u(6, (math.atan2(vv.co.y, vv.co.x) / 6.283 + 0.5) % 1 * 0.5), vv.co.z * 0.2 + 0.5) for vv in f.verts], 1)
            bm.free()
    o = mb.build("bridge_vis", [M["wood"], M["bark"]])
    # collider: a thin curved deck + both rails as boxes
    cb = MB()
    for i in range(12):
        x0 = -L / 2 - 0.6 + i * (L + 1.2) / 12; x1 = x0 + (L + 1.2) / 12
        z0 = zx(max(-L / 2, min(L / 2, x0))); z1 = zx(max(-L / 2, min(L / 2, x1)))
        vs = [cb.v((x0, -W / 2, z0)), cb.v((x1, -W / 2, z1)), cb.v((x1, W / 2, z1)), cb.v((x0, W / 2, z0))]
        cb.f(vs, [(0, 0)] * 4, 0)
        for y in (-W / 2, W / 2):
            ws = [cb.v((x0, y, z0)), cb.v((x1, y, z1)), cb.v((x1, y, z1 + 1.1)), cb.v((x0, y, z0 + 1.1))]
            cb.f(ws, [(0, 0)] * 4, 0)
    col = cb.build("bridge_collider", [])
    return o, col

def build_spring(M):
    """Mossy rock ledge (~7 m wide, 3.4 m high) with a notch; a cascade sheet falls from the notch into the pool (+y)."""
    mb = MB(); rng = random.Random(5)
    blocks = [((-2.6, -0.6, 1.0), (1.9, 1.6, 1.5)), ((2.5, -0.5, 1.1), (2.0, 1.7, 1.6)), ((-0.9, -1.4, 1.9), (1.5, 1.3, 1.9)),
              ((1.0, -1.3, 1.8), (1.4, 1.3, 1.8)), ((0.0, -2.3, 2.6), (2.6, 1.4, 1.6)), ((-3.4, 0.6, 0.4), (1.2, 1.0, 0.8)),
              ((3.5, 0.6, 0.45), (1.3, 1.1, 0.8)), ((-1.6, 0.9, 0.2), (0.8, 0.7, 0.5)), ((1.7, 1.0, 0.25), (0.9, 0.7, 0.5)),
              ((0.0, -0.6, 0.7), (1.0, 0.8, 0.9))]
    for k, (c, s) in enumerate(blocks):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        for v_ in bm.verts:
            p = v_.co; d = 1 + 0.22 * noise.noise(p * 1.6 + Vector((k * 3.1, 0, 0))) + 0.08 * noise.noise(p * 5 + Vector((0, k, 0)))
            v_.co = Vector((p.x * s[0], p.y * s[1], p.z * s[2])) * d + Vector(c)
            if v_.co.z < -0.3: v_.co.z = -0.3
        for f in bm.faces:
            mb.f([mb.v(vv.co) for vv in f.verts], [(strip_u(6, ((math.atan2(vv.co.y - c[1], vv.co.x - c[0]) / 6.283 + 0.5) % 1) * 0.5 + 0.25), vv.co.z * 0.09 + k * 0.1) for vv in f.verts], 0)
        bm.free()
    rocks = mb.build("spring_rocks", [M["bark"]])
    # the falls: a curved sheet from the lip (z 2.9) down to the pool surface (z ~0), plus a smaller side trickle
    cs = MB()
    for (x0, w, top) in ((0.0, 1.3, 2.95), (1.55, 0.45, 2.2)):
        rows = []
        for j in range(7):
            t = j / 6; y = -0.9 + 1.6 * t ** 0.7; z = top * (1 - t)
            rows.append((cs.v((x0 - w / 2 * (1 + 0.25 * t), y, z)), cs.v((x0 + w / 2 * (1 + 0.25 * t), y, z)), t))
        for j in range(6):
            a, b, t0 = rows[j]; c_, d, t1 = rows[j + 1]
            cs.f([a, b, d, c_], [(0, 1 - t0), (1, 1 - t0), (1, 1 - t1), (0, 1 - t1)], 0)
    falls = cs.build("cascade", [M["cascade"]])
    col = rocks.copy(); col.data = rocks.data.copy(); link(col); col.name = "spring_collider"
    return rocks, falls, col

# ============================================================================ main
def job():
    try:
        status({"state": "running", "step": "setup"})
        scn = new_scene("Emberwood")
        T = {n: img(n) for n in ("forest_bark", "forest_bark_NRM", "forest_foliage", "forest_floor", "forest_floor_NRM", "forest_lily", "forest_wood", "forest_wood_NRM", "forest_cascade")}
        for n in ("forest_bark_NRM", "forest_floor_NRM", "forest_wood_NRM"): T[n].colorspace_settings.name = 'Non-Color'
        G = glow_image()
        M = {"bark": mat_ksp("forest_bark", "KSP/Bumped", T["forest_bark"], T["forest_bark_NRM"]),
             "leaf": mat_ksp("forest_leaves", "KSP/Alpha/Cutoff", T["forest_foliage"], cutoff=0.42),
             "glow": mat_ksp("forest_pods", "KSP/Emissive/Diffuse", G, emis=G, emiscol=(1.0, 0.7, 0.3, 1)),
             "floor": mat_ksp("forest_litter", "KSP/Bumped", T["forest_floor"], T["forest_floor_NRM"]),
             "lily": mat_ksp("forest_lily", "KSP/Alpha/Cutoff", T["forest_lily"], cutoff=0.5),
             "wood": mat_ksp("forest_wood", "KSP/Bumped", T["forest_wood"], T["forest_wood_NRM"]),
             "cascade": mat_ksp("forest_cascade", "KSP/Alpha/Translucent", T["forest_cascade"])}
        root = link(bpy.data.objects.new("forest_kit", None))
        stats = {}; imp_src = []
        for si, sp in enumerate(ORDER):
            for v in range(3):
                status({"state": "running", "step": "tree %s %d" % (sp, v)})
                tr = Tree(sp, 100 * si + v * 7 + 1).grow()
                mats = [M["bark"], M["leaf"]] + ([M["glow"]] if SPEC[sp].get("pods") else [])
                o0, t0 = tr.mesh(0, mats, "t_%s_%d_0" % (sp, v))
                o1, t1 = tr.mesh(1, mats[:2], "t_%s_%d_1" % (sp, v))
                for o in (o0, o1): o.parent = root
                stats["%s_%d" % (sp, v)] = [t0, t1, round(tr.H, 1)]
                if v == 0: imp_src.append((sp, o0))
        # the elder: a vast copperoak
        status({"state": "running", "step": "elder"})
        SPEC["elder"] = dict(SPEC["copperoak"]); SPEC["elder"].update(H=(26, 28), trunkR=0.9, roots=8, limbs=(5, 6), gnarl=0.5, crownW=1.0, limbLen=0.42, card=(2.6, 3.2), depth=3, split=0.3)
        el = Tree("elder", 4242).grow()
        e0, et0 = el.mesh(0, [M["bark"], M["leaf"]], "elder_0"); e1, et1 = el.mesh(1, [M["bark"], M["leaf"]], "elder_1")
        e0.parent = root; e1.parent = root; stats["elder"] = [et0, et1, round(el.H, 1)]
        imp_src.append(("elder", e0))
        # props
        for kind, nv in PROPS:
            for v in range(nv):
                status({"state": "running", "step": "prop %s %d" % (kind, v)})
                mb, mats = prop_mesh(kind, v, M)
                if mats is None:
                    o, t = mb.mesh(0, [M["bark"], M["leaf"]], "p_%s_%d" % (kind, v))
                else:
                    o = mb.build("p_%s_%d" % (kind, v), mats); t = mb.tris()
                o.parent = root; stats["p_%s_%d" % (kind, v)] = t
        # impostors
        status({"state": "running", "step": "impostors"})
        dims = render_impostors(imp_src)
        T["forest_imp"] = img("forest_imp")
        M["imp"] = mat_ksp("forest_imp", "KSP/Alpha/Cutoff", T["forest_imp"], cutoff=0.45)
        for col, (nm, o) in enumerate(imp_src):
            H, W = dims[nm]
            io = impostor_mesh("%s_imp" % ("t_" + nm if nm != "elder" else "elder"), H, W, col, [M["imp"]]); io.parent = root
        for o in root.children: o.muproperties.layer = 15
        res = {}
        if STEP == "all":
            status({"state": "running", "step": "export kit"})
            res["kit"] = export_mu("forest_kit", os.path.join(OUT, "forest_kit.mu"))
        # bridge
        status({"state": "running", "step": "bridge"})
        br = link(bpy.data.objects.new("forest_bridge", None))
        bv, bc = build_bridge(M); bv.parent = br; bc.parent = br
        bc.muproperties.collider = "MU_COL_MESH"; bc.muproperties.isConvex = False; bc.hide_render = True
        for o in (br, bv, bc): o.muproperties.layer = 15
        if STEP == "all": res["bridge"] = export_mu("forest_bridge", os.path.join(OUT, "forest_bridge.mu"))
        sp_ = link(bpy.data.objects.new("forest_spring", None))
        rk, fl, sc = build_spring(M); rk.parent = sp_; fl.parent = sp_; sc.parent = sp_
        sc.data.materials.clear(); sc.muproperties.collider = "MU_COL_MESH"; sc.muproperties.isConvex = False; sc.hide_render = True
        for o in (sp_, rk, fl, sc): o.muproperties.layer = 15
        if STEP == "all": res["spring"] = export_mu("forest_spring", os.path.join(OUT, "forest_spring.mu"))
        json.dump({"dims": dims, "stats": stats}, open(os.path.join(DEV, "kit_meta.json"), "w"))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(PREVIEW_DIR), "blend", "emberwood_kit.blend"), copy=True)
        status({"state": "done", "stats": stats, "dims": dims, "export": res, "bridge_tris": len(bv.data.polygons), "spring_tris": len(rk.data.polygons)})
    except Exception as e:
        import traceback
        status({"state": "error", "error": traceback.format_exc()})
    return None

if globals().get("RUN_NOW", True):
    bpy.app.timers.register(job, first_interval=0.1)
