# Xenobiology — fossil outcrop models.
# Each fossil is a small slab of bedded rock (a heightfield whose edges sink below the ground) with the fossil
# either carved into the bedding plane as relief (impressions, trackways, burrows) or sitting half-weathered
# out of it as solid geometry (shells, teeth, crystals). Everything is about a metre across or less.
#
# Inside Blender:  exec(src, {"__name__": "__xeno__", "FOSSIL": "duna_ammonoid" | "all" | "Duna" | [names], "STEP": "model" | "all"})
#   STEP "model": geometry + live material + review renders only (fast)
#   STEP "all":   + texture bake, .mu export, portrait + silhouette mask
# Output: GameData/Xenobiology/Models/Fossils/<Body>/<name>.mu (+ <name>_diffuse.png)
# Conventions: Z up, the bedding plane sits around Z = 0.1, slab edges reach Z = -0.17 (always under the ground).
# Texture ids ("part" face attribute): 0 rock, 1 fossil, 2 fossil secondary, 3 dark (chitin / sockets), 4 crystal / glass.
import bpy, bmesh, os, math, random, json
from mathutils import Vector, Matrix, Euler, noise
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
FOSSIL = globals().get("FOSSIL", "all")
STEP = globals().get("STEP", "all")

ROCK, FOS, FOS2, DARK, CRYST = range(5)
TAU = math.tau

# ============================================================================ mesh builder
class B:
    def __init__(s):
        s.bm = bmesh.new()
        s.pl = s.bm.faces.layers.int.new("part")
        s.fl = s.bm.verts.layers.float.new("fos"); s.dl = s.bm.verts.layers.float.new("dk"); s.ll = s.bm.verts.layers.float.new("lin")
        s.pid = FOS; s.solid = []
    def v(s, co, fos=0.0, dk=0.0, lin=0.5):
        vv = s.bm.verts.new(Vector(co)); vv[s.fl] = fos; vv[s.dl] = dk; vv[s.ll] = lin; return vv
    def f(s, vs, pid=None, solid=True):
        vs = [x for j, x in enumerate(vs) if x not in vs[:j]]
        if len(vs) < 3: return None
        try: fc = s.bm.faces.new(vs)
        except ValueError: return None
        fc[s.pl] = s.pid if pid is None else pid
        if solid: s.solid.append(fc)
        return fc
    def cap(s, ring, rev=False, pid=None):
        c = sum((x.co for x in ring), Vector()) / len(ring); cv = s.v(c, lin=ring[0][s.ll])
        n = len(ring)
        for k in range(n):
            a, b_ = ring[k], ring[(k + 1) % n]
            s.f([a, b_, cv] if rev else [b_, a, cv], pid)
    def sweep(s, rings, lins=None, cap0=True, cap1=True, closed=False, pid=None, cap_pid=None):
        R = [[s.v(p, lin=(lins[i] if lins else 0.5)) for p in ring] for i, ring in enumerate(rings)]
        n = len(R[0]); m = len(R)
        for i in range(m if closed else m - 1):
            A, C = R[i], R[(i + 1) % m]
            for k in range(n): s.f([A[k], A[(k + 1) % n], C[(k + 1) % n], C[k]], pid)
        if not closed:
            if cap0: s.cap(R[0], True, cap_pid if cap_pid is not None else pid)
            if cap1: s.cap(R[-1], False, cap_pid if cap_pid is not None else pid)
        return R
    def add_bm(s, tmp, M, pid=None, jitter=0.0, seed=0.0):
        mp = {}
        for vv in tmp.verts:
            co = vv.co.copy()
            if jitter: co += co.normalized() * noise.noise(co * 2.3 + Vector((seed, seed * 0.7, 1.3))) * jitter
            mp[vv] = s.v(M @ co)
        for fc in tmp.faces: s.f([mp[x] for x in fc.verts], pid)
        tmp.free()
    def finish(s, name):
        bmesh.ops.recalc_face_normals(s.bm, faces=[f for f in s.solid if f.is_valid])
        loose = [vv for vv in s.bm.verts if not vv.link_faces]
        if loose: bmesh.ops.delete(s.bm, geom=loose, context='VERTS')
        bmesh.ops.triangulate(s.bm, faces=s.bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
        me = bpy.data.meshes.new(name); s.bm.to_mesh(me); s.bm.free()
        return link(bpy.data.objects.new(name, me))

def basis(z, up=None):
    z = Vector(z).normalized()
    ref = Vector(up) if up is not None else (Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((1, 0, 0)))
    y = (ref - z * ref.dot(z)); y = y.normalized() if y.length > 1e-6 else z.orthogonal().normalized()
    x = y.cross(z)
    return x, y, z

def rotm(yaw=0.0, pitch=0.0, roll=0.0):
    return Euler((math.radians(roll), math.radians(pitch), math.radians(yaw)), 'XYZ').to_matrix()

def smooth01(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ---------------------------------------------------------------------------- solid primitives
def ellipsoid(b, c, scale, rot=None, sub=2, jitter=0.0, seed=0.0, pid=None):
    tmp = bmesh.new(); bmesh.ops.create_icosphere(tmp, subdivisions=sub, radius=1.0)
    M = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4)) @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    b.add_bm(tmp, M, pid, jitter, seed)

def cube(b, c, size, rot=None, bevel=0.12, pid=None):
    tmp = bmesh.new(); bmesh.ops.create_cube(tmp, size=1.0)
    if bevel:
        try: bmesh.ops.bevel(tmp, geom=tmp.edges[:] + tmp.verts[:], offset=bevel * 0.5, offset_type='OFFSET', segments=1, profile=0.5, affect='EDGES')
        except Exception: pass
    sz = size if isinstance(size, (tuple, list)) else (size, size, size)
    M = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4)) @ Matrix.Diagonal((sz[0], sz[1], sz[2], 1.0))
    b.add_bm(tmp, M, pid)

def revolve(b, M, prof, segs=24, rmod=None, zmod=None, pids=None, a0=0.0, a1=TAU, lins=None):
    """prof [(r, z)] around local Z. rmod(phi, z, i) -> radius factor, zmod(phi, r, i) -> dz. pids: per profile segment."""
    full = abs(a1 - a0 - TAU) < 1e-6
    n = segs if full else segs + 1
    rings = []
    for i, (r, z) in enumerate(prof):
        ln = lins[i] if lins else 0.5
        if r < 1e-6: rings.append([b.v(M @ Vector((0, 0, z)), lin=ln)] * n); continue
        ring = []
        for k in range(n):
            ph = a0 + (a1 - a0) * k / segs
            rr = r * (rmod(ph, z, i) if rmod else 1.0); zz = z + (zmod(ph, r, i) if zmod else 0.0)
            ring.append(b.v(M @ Vector((math.cos(ph) * rr, math.sin(ph) * rr, zz)), lin=ln))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, C = rings[i], rings[i + 1]; pid = pids[i] if pids else None
        for k in range(segs): b.f([A[k], A[(k + 1) % n], C[(k + 1) % n], C[k]], pid)
    if not full:      # close the cut: one polygon through the profile at a0 and a1
        b.f([r_[0] for r_ in rings] + [r_[-1] for r_ in rings][::-1], FOS2)
    else:
        if prof[0][0] > 1e-6: b.f(rings[0][::-1])
        if prof[-1][0] > 1e-6: b.f(rings[-1])
    return rings

def tube_path(b, pts, radii, segs=10, lins=None, up=None, flat=1.0, rmod=None, cap0=True, cap1=True, closed=False, pid=None, cap_pid=None):
    pts = [Vector(p) for p in pts]; n = len(pts)
    T = []
    for i in range(n):
        if closed: d = pts[(i + 1) % n] - pts[i - 1]
        else: d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        T.append(d.normalized())
    rings = []
    x, y, _ = basis(T[0], up)
    for i in range(n):
        if up is not None: x, y, _ = basis(T[i], up)
        elif i:
            y = (y - T[i] * y.dot(T[i])).normalized(); x = y.cross(T[i])
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        ring = []
        for k in range(segs):
            ph = TAU * k / segs
            rr = r * (rmod(i, ph) if rmod else 1.0)
            ring.append(pts[i] + (x * math.cos(ph) + y * math.sin(ph) * flat) * rr)
        rings.append(ring)
    return b.sweep(rings, lins, cap0, cap1, closed, pid, cap_pid)

def cone(b, base, d, length, r0, segs=8, pid=None, bend=None):
    d = Vector(d).normalized(); pts = []; rad = []
    for t in (0.0, 0.35, 0.7, 1.0):
        p = Vector(base) + d * length * t
        if bend is not None: p += Vector(bend) * length * t * t
        pts.append(p); rad.append(max(r0 * (1 - t), r0 * 0.04))
    tube_path(b, pts, rad, segs, pid=pid)

# ---------------------------------------------------------------------------- shells
def coil(b, c, R, turns=3.2, ratio=0.42, flat=0.78, W=2.3, ribs=24, rib_amp=0.07, sutures=0.0, keel=0.0, rot=None,
         span=None, steps=40, segs=16, pid=FOS, cap_pid=FOS2):
    """Planispiral (ammonite-like) shell around axis rot@Z, outer whorl radius R. span: only the last `span` turns (fragment)."""
    rot = rot or Matrix.Identity(3); u, v, nrm = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0)), rot @ Vector((0, 0, 1))
    kk = math.log(W) / TAU; thm = turns * TAU; th0 = 0.0 if span is None else thm - span * TAU
    N = max(8, int((thm - th0) / TAU * steps)); rings = []; lins = []
    for i in range(N + 1):
        th = th0 + (thm - th0) * i / N
        r = R * math.exp(kk * (th - thm)) / (1 + ratio)
        a = r * ratio
        rib = 1 + rib_amp * (0.5 + 0.5 * math.cos(th * ribs)) ** 3
        d = u * math.cos(th) + v * math.sin(th); P = Vector(c) + d * r
        ring = []
        for k in range(segs):
            ph = TAU * k / segs; cph = math.cos(ph)
            ko = 1 + keel * max(0.0, cph) ** 12
            ring.append(P + (d * cph * ko + nrm * math.sin(ph) * flat) * a * rib)
        rings.append(ring); lins.append(th * sutures / TAU if sutures else 0.5)
    b.sweep(rings, lins, True, True, pid=pid, cap_pid=cap_pid)

def spire(b, c, axis, rmax, turns=12, W=1.12, S=14.0, ratio=None, cords=5, cord_amp=0.06, steps=18, segs=10, pid=FOS):
    """High-spired (turritelline) shell: apex at c, growing along axis."""
    ax = Vector(axis).normalized(); u, v, _ = basis(ax)
    kk = math.log(W) / TAU; thm = turns * TAU; N = int(turns * steps)
    a_ratio = ratio if ratio is not None else 0.575 * S * (1 - 1 / W)
    rings = []
    for i in range(N + 1):
        th = thm * i / N
        rho = rmax * math.exp(kk * (th - thm)); a = rho * a_ratio
        d = u * math.cos(th) + v * math.sin(th)
        P = Vector(c) + ax * S * rho + d * rho
        ring = []
        for k in range(segs):
            ph = TAU * k / segs
            cr = 1 + cord_amp * math.cos(ph * cords)
            ring.append(P + (d * math.cos(ph) + ax * math.sin(ph)) * a * cr)
        rings.append(ring)
    b.sweep(rings, None, True, True, pid=pid, cap_pid=FOS2)

def valve(b, c, L, Wd, H, ribs=20, rot=None, growth=7, pid=FOS, nr=10, ns=28):
    """Brachiopod-like domed valve; umbo (beak) toward local -X, base on local z = 0."""
    M = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot else Matrix.Identity(4))
    ux = -0.36 * L
    top = [b.v(M @ Vector((ux * 0.55, 0, H)), lin=0.0)]; prev = None; rings = []
    for i in range(1, nr + 1):
        rho = i / nr; ring = []
        for k in range(ns):
            ps = TAU * k / ns
            x = math.cos(ps) * L * 0.5; y = math.sin(ps) * Wd * 0.5
            if x < 0: y *= 1 - 0.25 * (-x / (L * 0.5)) ** 2          # narrow toward the hinge
            px = ux * 0.55 * (1 - rho) + x * rho; py = y * rho
            ang = math.atan2(py, px - ux)
            z = H * (1 - rho ** 2) ** 0.6 + H * 0.07 * rho * math.cos(ang * ribs)
            ring.append(b.v(M @ Vector((px, py, z)), lin=rho * growth))
        rings.append(ring)
    for k in range(ns): b.f([top[0], rings[0][k], rings[0][(k + 1) % ns]], pid)
    for i in range(nr - 1):
        A, C = rings[i], rings[i + 1]
        for k in range(ns): b.f([A[k], C[k], C[(k + 1) % ns], A[(k + 1) % ns]], pid)
    low = []
    Mi = M.inverted()
    for vv in rings[-1]:
        lc = Mi @ vv.co; low.append(b.v(M @ Vector((lc.x * 0.97, lc.y * 0.97, -H * 0.3))))
    for k in range(ns): b.f([rings[-1][k], low[k], low[(k + 1) % ns], rings[-1][(k + 1) % ns]], FOS2)
    b.cap(low, False, FOS2)
    # beak
    ellipsoid(b, M @ Vector((ux * 1.02, 0, H * 0.45)), (L * 0.09, Wd * 0.08, H * 0.35), rot=M.to_3x3(), sub=1, pid=pid)

# ============================================================================ bedding-plane heightfield
class Field:
    def __init__(s, sx, sy, step=0.012, H0=0.10, p=2.6, jag=0.12, seed=1, layer=0.028, tilt=(0.015, -0.01), rough=0.006, edge=0.24, terr=0.6, inner_terr=0.12):
        s.sx, s.sy, s.ax, s.ay = sx, sy, sx / 2, sy / 2
        s.nx = int(round(sx / step)) + 1; s.ny = int(round(sy / step)) + 1
        s.dx = sx / (s.nx - 1); s.dy = sy / (s.ny - 1)
        s.xs = [-s.ax + i * s.dx for i in range(s.nx)]; s.ys = [-s.ay + j * s.dy for j in range(s.ny)]
        mk = lambda: [[0.0] * s.nx for _ in range(s.ny)]
        s.P, s.N, s.F, s.D, s.A = mk(), mk(), mk(), mk(), mk()
        s.H0, s.p, s.jag, s.seed, s.layer, s.tilt, s.rough, s.edge, s.terr, s.inner = H0, p, jag, seed, layer, tilt, rough, edge, terr, inner_terr
        s.Z = None
    def outline(s, x, y):
        sd = s.seed * 7.31
        ang = math.atan2(y / s.ay, x / s.ax)
        rr = (abs(x / s.ax) ** s.p + abs(y / s.ay) ** s.p) ** (1 / s.p)
        return rr * (1 + s.jag * noise.noise(Vector((math.cos(ang) * 1.4 + sd, math.sin(ang) * 1.4, sd))))
    def base(s, x, y):
        sd = s.seed * 7.31
        e = smooth01((s.outline(x, y) - (1 - s.edge)) / s.edge)
        top = s.H0 + s.tilt[0] * x + s.tilt[1] * y + s.rough * noise.fractal(Vector((x * 5 + sd, y * 5, 0.3)), 0.6, 2.0, 4)
        z = top * (1 - e) - 0.17 * e + 0.035 * e * (1 - e) * noise.noise(Vector((x * 9, y * 9, sd + 2)))
        s._e = e
        if s.layer > 0:
            q = z / s.layer; fl = math.floor(q); fr = q - fl
            zt = s.layer * (fl + smooth01((fr - s.terr) / (1 - s.terr)))
            z += (zt - z) * min(1.0, s.inner + e * 3.0)
        return z
    def _reg(s, x0, x1, y0, y1):
        i0 = max(0, int((x0 + s.ax) / s.dx)); i1 = min(s.nx - 1, int((x1 + s.ax) / s.dx) + 1)
        j0 = max(0, int((y0 + s.ay) / s.dy)); j1 = min(s.ny - 1, int((y1 + s.ay) / s.dy) + 1)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1): yield i, j, s.xs[i], s.ys[j]
    def _apply(s, i, j, hv, f, dk, neg):
        if neg: s.N[j][i] = min(s.N[j][i], -hv)
        else: s.P[j][i] = max(s.P[j][i], hv)
        if f > s.F[j][i]: s.F[j][i] = f
        if dk > s.D[j][i]: s.D[j][i] = dk
    def ridge(s, pts, r, h, fos=1.0, dk=0.0, neg=False, taper=None):
        """raised (or, neg, grooved) round-profile line along a polyline; taper: per-point radius factors"""
        pts = [Vector((p[0], p[1])) for p in pts]
        for k in range(len(pts) - 1):
            a, c = pts[k], pts[k + 1]; ab = c - a; L2 = max(ab.length_squared, 1e-12)
            ra = r * (taper[k] if taper else 1.0); rb = r * (taper[k + 1] if taper else 1.0); rm = max(ra, rb)
            for i, j, x, y in s._reg(min(a.x, c.x) - rm, max(a.x, c.x) + rm, min(a.y, c.y) - rm, max(a.y, c.y) + rm):
                p = Vector((x, y)); t = max(0.0, min(1.0, (p - a).dot(ab) / L2)); d = (p - (a + ab * t)).length
                rr = ra + (rb - ra) * t
                if d >= rr: continue
                prof = math.sqrt(1 - (d / rr) ** 2)
                s._apply(i, j, h * prof * (rr / rm if taper else 1.0), fos * min(1.0, prof * 2.5), dk * prof, neg)
    def blob(s, x0, y0, rx, ry, ang, h, fos=1.0, dk=0.0, neg=False, power=0.5, rim=0.0):
        c, sn = math.cos(ang), math.sin(ang); R = max(rx, ry) * (1.5 if rim else 1.0)
        for i, j, x, y in s._reg(x0 - R, x0 + R, y0 - R, y0 + R):
            dx, dy = x - x0, y - y0; u = (dx * c + dy * sn) / rx; v = (-dx * sn + dy * c) / ry; q = u * u + v * v
            if q < 1:
                prof = (1 - q) ** power; s._apply(i, j, h * prof, fos * min(1.0, prof * 3), dk * min(1.0, prof * 2), neg)
            elif rim:
                rq = math.sqrt(q)
                if rq < 1.45: s._apply(i, j, rim * math.sin(math.pi * (rq - 1) / 0.45), 0.0, 0.0, False)
    def wave(s, fn, ffn=None):
        for j in range(s.ny):
            for i in range(s.nx):
                x, y = s.xs[i], s.ys[j]; s.A[j][i] += fn(x, y)
                if ffn: s.F[j][i] = max(s.F[j][i], ffn(x, y))
    def finalize(s):
        s.Z = []; s.E = []
        for j in range(s.ny):
            zr = []; er = []
            for i in range(s.nx):
                z = s.base(s.xs[i], s.ys[j]); e = s._e
                zr.append(max(-0.175, z + (s.A[j][i] + s.P[j][i] + s.N[j][i]) * (1 - e))); er.append(e)
            s.Z.append(zr); s.E.append(er)
        return s
    def surf(s, x, y):
        fx = min(max((x + s.ax) / s.dx, 0), s.nx - 1.001); fy = min(max((y + s.ay) / s.dy, 0), s.ny - 1.001)
        i, j = int(fx), int(fy); tx, ty = fx - i, fy - j; Z = s.Z
        return (Z[j][i] * (1 - tx) + Z[j][i + 1] * tx) * (1 - ty) + (Z[j + 1][i] * (1 - tx) + Z[j + 1][i + 1] * tx) * ty
    def on(s, x, y, dz=0.0): return Vector((x, y, s.surf(x, y) + dz))
    def inside(s, x, y, m=0.7): return s.outline(x, y) < m
    def build(s, b):
        V = [[b.v((s.xs[i], s.ys[j], s.Z[j][i]), s.F[j][i], s.D[j][i]) for i in range(s.nx)] for j in range(s.ny)]
        for j in range(s.ny - 1):
            for i in range(s.nx - 1):
                if min(s.E[j][i], s.E[j][i + 1], s.E[j + 1][i], s.E[j + 1][i + 1]) > 0.999: continue
                b.f([V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]], ROCK, solid=False)

def pebbles(b, f, rng, n=6, rmin=0.015, rmax=0.045):
    for _ in range(n):
        a = rng.uniform(0, TAU)
        for rr in [x / 100 for x in range(60, 140)]:
            x, y = math.cos(a) * f.ax * rr, math.sin(a) * f.ay * rr
            if f.outline(x, y) > 0.92: break
        r = rng.uniform(rmin, rmax)
        ellipsoid(b, (x, y, -0.03 + r * 0.2), (r, r * rng.uniform(0.6, 1.0), r * 0.55), rotm(rng.uniform(0, 360)), 1, r * 0.35, rng.random() * 9, ROCK)

def scatter(f, rng, n, m=0.62, avoid=(), gap=0.05):
    """n points inside the outline (< m) keeping `gap` apart; the gap shrinks if they won't fit (never loops forever)"""
    out = []; tries = 0
    while len(out) < n:
        tries += 1
        if tries % 400 == 0: gap *= 0.85; m = min(0.8, m * 1.03)
        if tries > 20000: break
        x, y = rng.uniform(-f.ax, f.ax), rng.uniform(-f.ay, f.ay)
        if f.outline(x, y) > m: continue
        if any((Vector((x, y)) - Vector(a[:2])).length < (a[2] if len(a) > 2 else gap) for a in list(avoid) + [(p[0], p[1], gap) for p in out]): continue
        out.append((x, y))
    return out

def wander(rng, start, heading, n, step, turn=0.35, bounds=None):
    p = Vector(start); h = heading; pts = [p.copy()]; w = 0.0
    for _ in range(n):
        w = w * 0.8 + rng.uniform(-turn, turn); h += w
        p = p + Vector((math.cos(h), math.sin(h))) * step
        if bounds and not bounds(p.x, p.y): h += math.pi * 0.6; w = 0
        pts.append(p.copy())
    return pts

# ============================================================================ palettes
def pal(base, **kw): d = dict(base); d.update(kw); return d
SAND = dict(ra=(0.63, 0.55, 0.43), rb=(0.54, 0.46, 0.36), rc=(0.71, 0.64, 0.51), layer=0.022, wob=0.012,
            fa=(0.86, 0.81, 0.68), fb=(0.73, 0.66, 0.52), f2=(0.56, 0.48, 0.37), line=(0.38, 0.30, 0.22), dark=(0.13, 0.11, 0.10),
            cr=(0.92, 0.88, 0.84), ftint=0.85, lam=0.0, flay=0.012, pore=0.0, ns=6.0, grain=0.14, ao=0.05)
LIME = pal(SAND, ra=(0.66, 0.63, 0.57), rb=(0.58, 0.55, 0.50), rc=(0.74, 0.71, 0.65), layer=0.03)
RED = pal(SAND, ra=(0.58, 0.31, 0.21), rb=(0.47, 0.25, 0.18), rc=(0.68, 0.42, 0.29), layer=0.02,
          fa=(0.80, 0.56, 0.42), fb=(0.66, 0.42, 0.30), f2=(0.45, 0.25, 0.18), line=(0.30, 0.15, 0.10), dark=(0.16, 0.09, 0.07))
BASALT = pal(SAND, ra=(0.30, 0.27, 0.32), rb=(0.24, 0.22, 0.26), rc=(0.37, 0.33, 0.39), layer=0.035, grain=0.25,
             fa=(0.62, 0.48, 0.70), fb=(0.48, 0.36, 0.56), f2=(0.30, 0.22, 0.36), dark=(0.08, 0.06, 0.10), cr=(0.20, 0.14, 0.28))
SHALE = pal(SAND, ra=(0.30, 0.31, 0.32), rb=(0.24, 0.25, 0.27), rc=(0.38, 0.39, 0.40), layer=0.014, wob=0.006, grain=0.08)
BLACKSAND = pal(SAND, ra=(0.22, 0.22, 0.24), rb=(0.17, 0.17, 0.19), rc=(0.30, 0.30, 0.31), layer=0.02, grain=0.3)

# ============================================================================ fossils
SPECS = {}
def fossil(name, body, palette, res=1024, kind=None, cam=(0.55, -0.78, 0.62), lens=50):
    def reg(fn): SPECS[name] = dict(name=name, body=body, pal=palette, fn=fn, res=res, kind=kind, cam=cam, lens=lens); return fn
    return reg

# ---------------------------------------------------------------------------- Kerbin
@fossil("kerbin_quadrimembra_skull", "Kerbin", pal(SAND, fa=(0.85, 0.80, 0.66), fb=(0.70, 0.63, 0.50), cr=(0.90, 0.86, 0.74)), kind="Skull")
def f_skull(b, rng):
    f = Field(0.95, 0.72, seed=11, tilt=(0.02, 0.01)).finalize(); f.build(b)
    cx, cy = 0.02, 0.06; z = f.surf(cx, cy) - 0.005
    ellipsoid(b, (cx, cy, z), (0.115, 0.09, 0.07), sub=3, jitter=0.004, seed=1)                        # cranium
    ellipsoid(b, (cx + 0.13, cy, z - 0.008), (0.10, 0.055, 0.045), sub=3, jitter=0.003, seed=2)          # snout
    ellipsoid(b, (cx + 0.215, cy, z - 0.012), (0.04, 0.04, 0.034), sub=2)                                 # nose
    tube_path(b, [(cx - 0.11, cy, z + 0.055), (cx - 0.02, cy, z + 0.072), (cx + 0.06, cy, z + 0.06)], [0.006, 0.011, 0.004], 8)   # crest
    for sgn in (-1, 1):
        oc = Vector((cx + 0.055, cy + sgn * 0.06, z + 0.03))
        ring = [oc + Vector((math.cos(a) * 0.032, 0, math.sin(a) * 0.026)) + Vector((0, sgn * 0.012 * math.cos(a) ** 2, 0)) for a in [TAU * k / 14 for k in range(14)]]
        tube_path(b, ring, 0.008, 8, closed=True)
        ellipsoid(b, oc + Vector((0, sgn * 0.004, 0)), (0.028, 0.012, 0.022), pid=DARK, sub=2)
        tube_path(b, [(cx + 0.11, cy + sgn * 0.045, z), (cx + 0.02, cy + sgn * 0.105, z + 0.005), (cx - 0.07, cy + sgn * 0.075, z + 0.01)], [0.012, 0.014, 0.01], 8)
        ellipsoid(b, (cx + 0.225, cy + sgn * 0.015, z + 0.012), (0.01, 0.006, 0.006), pid=DARK, sub=1)     # nostrils
    for k in range(6):                                                                                     # upper teeth just showing
        t = k / 5; x = cx + 0.06 + t * 0.15; w = 0.045 - t * 0.012
        for sgn in (-1, 1): cone(b, (x, cy + sgn * w, z - 0.03), (0, sgn * 0.3, -1), 0.03 - 0.008 * t, 0.009, pid=FOS2)
    jy = cy - 0.2; jp = [Vector((cx - 0.06 + 0.3 * t, jy + 0.035 * math.sin(t * 2.4), 0)) for t in [k / 10 for k in range(11)]]
    for p in jp: p.z = f.surf(p.x, p.y) + 0.004
    tube_path(b, jp, [0.024 - 0.012 * (k / 10) for k in range(11)], 10, flat=0.65, up=(0, 0, 1))
    ellipsoid(b, jp[0] + Vector((-0.01, 0, 0.012)), (0.03, 0.02, 0.03))                                     # jaw hinge
    for k in range(7):
        p = jp[3 + k] if 3 + k < len(jp) else jp[-1]
        cone(b, p + Vector((0, 0, 0.008)), (0.12, 0, 1), 0.032 - 0.002 * k, 0.008 - 0.0004 * k, pid=FOS2)
    for k in range(5):                                                                                     # trailing vertebrae
        x, y = cx - 0.17 - k * 0.062, cy + 0.025 * math.sin(k * 0.9); zz = f.surf(x, y) - 0.006
        ellipsoid(b, (x, y, zz), (0.024, 0.033, 0.024), sub=2, jitter=0.003, seed=k)
        cone(b, (x, y, zz + 0.015), (-0.4, 0, 1), 0.035, 0.011, pid=FOS)
        for sgn in (-1, 1): cone(b, (x, y + sgn * 0.02, zz), (0, sgn, 0.15), 0.03, 0.007)
    pebbles(b, f, rng)
    return f

@fossil("kerbin_ribwing", "Kerbin", pal(LIME, ftint=0.9), kind="Impression")
def f_ribwing(b, rng):
    f = Field(1.1, 0.85, seed=21, tilt=(0.01, 0.015), rough=0.004)
    sp = [(-0.30 + 0.05 * k, 0.012 * math.sin(k * 0.5)) for k in range(12)]
    f.ridge(sp, 0.012, 0.008)
    for x, y in sp[1:-1]: f.blob(x, y, 0.014, 0.017, 0, 0.011)
    f.blob(0.30, 0.02, 0.062, 0.034, 0.1, 0.013); f.blob(0.31, 0.03, 0.012, 0.01, 0, 0.006, dk=0.8, neg=True)
    f.ridge([(0.345, 0.0), (0.39, 0.012)], 0.006, 0.006)
    tail = [(-0.30 - 0.04 * k, 0.03 * math.sin(k * 0.7)) for k in range(7)]
    f.ridge(tail, 0.007, 0.006, taper=[1 - k / 8 for k in range(7)])
    for sgn in (-1, 1):
        f.blob(-0.03, sgn * 0.22, 0.17, 0.19, 0.0, 0.0025, fos=0.38, power=0.2)
        for r in range(7):
            x0 = -0.13 + r * 0.033
            pts = [(x0 - 0.13 * t ** 1.4, sgn * (0.016 + 0.36 * t * (1 - 0.15 * abs(r - 3) / 3))) for t in [k / 12 for k in range(13)]]
            f.ridge(pts, 0.0055, 0.006, taper=[1 - 0.55 * k / 12 for k in range(13)])
        for x0, back in ((0.17, 1), (-0.24, -1)):                       # small limbs with toes
            knee = (x0 + back * 0.03, sgn * 0.075); foot = (x0 + back * 0.0, sgn * 0.11)
            f.ridge([(x0, sgn * 0.015), knee, foot], 0.005, 0.006)
            for a in (-0.5, 0, 0.5): f.ridge([foot, (foot[0] + 0.025 * math.sin(a) * back + 0.02 * back, foot[1] + sgn * 0.022 * math.cos(a))], 0.0025, 0.004)
    f.finalize(); f.build(b); pebbles(b, f, rng)
    return f

@fossil("kerbin_hexapod_trackway", "Kerbin", pal(SAND, ra=(0.55, 0.50, 0.42), rb=(0.47, 0.42, 0.35), layer=0.016), kind="Trackway", cam=(0.75, -0.55, 0.65))
def f_hextrack(b, rng):
    f = Field(0.9, 2.0, step=0.01, seed=31, tilt=(0.0, 0.02), rough=0.003, p=3.2)
    f.wave(lambda x, y: 0.0014 * math.sin((x * 0.55 + y * 0.83) * TAU / 0.075 + 1.5 * noise.noise(Vector((x * 3, y * 3, 0.0)))))
    def print3(x, y, h, sgn):
        f.blob(x, y, 0.024, 0.02, 0, 0.014, dk=0.8, neg=True, rim=0.004)
        for a in (-0.5, 0.0, 0.5):
            d = Vector((math.sin(a), math.cos(a)))
            tip = Vector((x, y)) + d * 0.05
            f.ridge([(x, y), tip], 0.009, 0.012, dk=0.85, neg=True, fos=0.0, taper=None)
            f.blob(tip.x, tip.y, 0.006, 0.006, 0, 0.012, dk=0.9, neg=True, fos=0.0)
    for k in range(7):
        yk = -0.82 + k * 0.26
        for sgn in (-1, 1):
            off = 0.13 if (k % 2 == 0) == (sgn > 0) else 0.0
            for leg, dy, dxx in ((0, 0.075, 0.105), (1, 0.0, 0.15), (2, -0.075, 0.115)):
                if leg == 1: o = 0.13 - off
                else: o = off
                y = yk + dy + o
                if abs(y) < 0.9: print3(sgn * dxx + rng.uniform(-0.006, 0.006), y, 0.009, sgn)
    f.ridge([(0.012 * math.sin(y * 7), y) for y in [-0.9 + 0.05 * k for k in range(37)]], 0.009, 0.0035, dk=0.35, neg=True, fos=0.0)
    f.finalize(); f.build(b); pebbles(b, f, rng, 8)
    return f

@fossil("kerbin_thalassoshell", "Kerbin", pal(LIME, fa=(0.86, 0.77, 0.58), fb=(0.72, 0.62, 0.45), f2=(0.55, 0.47, 0.35)), kind="Coiled shell")
def f_thalasso(b, rng):
    f = Field(0.95, 0.75, seed=41, tilt=(0.01, -0.02)).finalize(); f.build(b)
    coil(b, f.on(0.04, 0.03, 0.012), 0.16, turns=3.4, ribs=26, rib_amp=0.07, sutures=10, rot=rotm(30, 9, 4))
    coil(b, f.on(-0.30, 0.17, 0.004), 0.055, turns=3.0, ribs=22, sutures=8, rot=rotm(110, -6))
    coil(b, f.on(-0.27, -0.2, 0.004), 0.045, turns=2.8, ribs=20, rot=rotm(200, 4, 10))
    coil(b, f.on(0.32, -0.2, 0.0), 0.10, turns=3.4, span=0.55, ribs=26, rib_amp=0.08, rot=rotm(250, 12))
    pebbles(b, f, rng)
    return f

def domes(b, f, rng, n, rc=(0.07, 0.14), h=(0.12, 0.3), broken=1, avoid=()):
    pos = scatter(f, rng, n, 0.6, avoid, gap=0.2)
    for k, (x, y) in enumerate(pos):
        r = rng.uniform(*rc); hh = rng.uniform(*h); z0 = f.surf(x, y) - 0.04; sd = rng.random() * 50
        prof = [(0, -0.04), (r * 0.85, -0.04), (r * 0.9, hh * 0.2), (r * 1.05, hh * 0.45), (r * 1.08, hh * 0.6), (r * 0.98, hh * 0.74), (r * 0.8, hh * 0.86), (r * 0.52, hh * 0.95), (r * 0.22, hh * 0.995), (0, hh)]
        rmod = lambda ph, z, i, sd=sd: 1 + 0.07 * noise.noise(Vector((math.cos(ph) * 1.5, math.sin(ph) * 1.5, z * 8 + sd))) + 0.025 * math.sin(z * 260)
        a1 = TAU if k >= broken else math.pi * rng.uniform(0.9, 1.25)
        revolve(b, Matrix.Translation((x, y, z0)) @ rotm(rng.uniform(0, 360), rng.uniform(-6, 6)).to_4x4(), prof, 28, rmod=rmod, a1=a1)

@fossil("kerbin_stromatolite", "Kerbin", pal(LIME, fa=(0.74, 0.66, 0.54), fb=(0.62, 0.54, 0.43), f2=(0.80, 0.73, 0.60), lam=0.55, flay=0.011), kind="Stromatolite", cam=(0.6, -0.8, 0.75))
def f_kstrom(b, rng):
    f = Field(1.2, 1.0, seed=51, H0=0.05, layer=0.03).finalize(); f.build(b)
    domes(b, f, rng, 7, (0.06, 0.1), (0.14, 0.3)); pebbles(b, f, rng, 8)
    return f

@fossil("kerbin_giant_tooth", "Kerbin", pal(SAND, fa=(0.90, 0.86, 0.74), fb=(0.80, 0.75, 0.62), f2=(0.55, 0.43, 0.30)), kind="Tooth")
def f_tooth(b, rng):
    f = Field(0.8, 0.62, seed=61, H0=0.09).finalize(); f.build(b)
    M = Matrix.Translation(f.on(0.0, 0.02, -0.035)) @ rotm(25, 0, 28).to_4x4()
    prof = [(0.05, -0.005), (0.058, 0.02), (0.063, 0.05), (0.062, 0.08), (0.054, 0.10), (0.04, 0.112), (0.02, 0.105), (0.0, 0.1)]
    cusp = lambda ph: (0.5 + 0.5 * math.cos(4 * (ph - math.pi / 4))) ** 1.5
    zmod = lambda ph, r, i: (0.016 * cusp(ph) if i in (4, 5) else 0.0) + (0.008 * cusp(ph) if i == 6 else 0.0)
    rmod = lambda ph, z, i: 1 + 0.06 * math.cos(4 * (ph - math.pi / 4))
    revolve(b, M @ Matrix.Diagonal((1.15, 0.95, 1, 1)), prof, 32, rmod=rmod, zmod=zmod)
    for sx in (-1, 1):                                                    # roots
        pts = [M @ Vector((sx * 0.03, 0, 0.01)), M @ Vector((sx * 0.04, 0, -0.06)), M @ Vector((sx * 0.045, 0.005, -0.12)), M @ Vector((sx * 0.04, 0.008, -0.17))]
        tube_path(b, pts, [0.03, 0.026, 0.018, 0.007], 10, pid=FOS2)
    revolve(b, M, [(0.0, -0.02), (0.052, -0.02), (0.056, 0.005), (0.0, 0.005)], 28, pids=[FOS2, FOS2, FOS2])
    for k in range(4):
        x, y = scatter(f, rng, 1, 0.6, [(0, 0, 0.18)])[0]
        cube(b, f.on(x, y, 0.004), (0.02, 0.014, 0.008), rotm(rng.uniform(0, 360), rng.uniform(-20, 20)), bevel=0.3)
    pebbles(b, f, rng)
    return f

# ---------------------------------------------------------------------------- Kerbin birds & mammals
@fossil("kerbin_feather_impression", "Kerbin", pal(LIME, ra=(0.62, 0.61, 0.58), rb=(0.53, 0.52, 0.50), layer=0.012, wob=0.005, ftint=0.85), kind="Impression")
def f_feather(b, rng):
    """A single spread pennavian wing pressed into lake shale: arm bones, a fan of primaries with shafts and barbs."""
    f = Field(1.05, 0.8, seed=161, tilt=(0.012, -0.01), rough=0.003)
    sh, el, wr, tp = Vector((-0.36, -0.12)), Vector((-0.16, -0.02)), Vector((0.06, -0.05)), Vector((0.2, -0.02))
    f.ridge([sh, el], 0.011, 0.009); f.ridge([el, wr], 0.008, 0.008); f.ridge([wr, tp], 0.006, 0.007)
    f.ridge([el + Vector((0.0, -0.012)), wr + Vector((0.0, -0.012))], 0.005, 0.006)          # second forearm bone
    for p in (sh, el, wr): f.blob(p.x, p.y, 0.016, 0.014, 0, 0.01)
    for k in range(22):                                        # flight feathers fanning back from the arm
        t = k / 21
        base = (sh.lerp(el, t * 2) if t < 0.5 else el.lerp(wr, (t - 0.5) * 1.6)) if t < 0.8 else wr.lerp(tp, (t - 0.8) * 5)
        ang = math.radians(-95 + 75 * t ** 1.3); L = 0.16 + 0.2 * t ** 0.8
        d = Vector((math.cos(ang), math.sin(ang)))
        tip = base + d * L
        f.ridge([base, base.lerp(tip, 0.5), tip], 0.003, 0.008, taper=[1.0, 0.8, 0.3])          # rachis
        n = Vector((-d.y, d.x))
        for q in range(9):                                     # vane: barbs either side, raked toward the tip
            c = base.lerp(tip, 0.12 + 0.85 * q / 8); w = 0.016 * math.sin(math.pi * (0.1 + 0.85 * q / 8)) + 0.004
            for sgn in (-1, 1): f.ridge([c, c + (n * sgn * 0.9 + d * 0.45) * w], 0.0022, 0.004)
        f.blob(*(base.lerp(tip, 0.55)), L * 0.5, 0.02, ang, 0.004, fos=0.7, power=0.3)
    for k in range(8):                                         # covert feathers over the arm
        c = sh.lerp(wr, 0.15 + 0.1 * k) + Vector((0.0, -0.035))
        f.blob(c.x, c.y, 0.03, 0.012, math.radians(-60), 0.003, fos=0.6, power=0.4)
    f.finalize(); f.build(b); pebbles(b, f, rng, n=4)
    return f

@fossil("kerbin_egg_clutch", "Kerbin", pal(SAND, fa=(0.90, 0.85, 0.72), fb=(0.80, 0.74, 0.60), f2=(0.62, 0.55, 0.42), cr=(0.93, 0.89, 0.80)), kind="Eggs", cam=(0.6, -0.78, 0.7))
def f_eggs(b, rng):
    """A nest scrape with whole eggs weathering out and a few hatched, broken shells."""
    f = Field(0.95, 0.85, seed=171, H0=0.07, tilt=(0.01, 0.0))
    f.blob(0.0, 0.0, 0.3, 0.26, 0.2, 0.025, fos=0.0, neg=True, power=0.8, rim=0.012)          # nest hollow with a raised rim
    f.finalize(); f.build(b)
    spots = [(-0.11, 0.06), (0.04, 0.1), (0.13, -0.02), (-0.03, -0.08), (0.0, 0.01)]
    for k, (x, y) in enumerate(spots):
        z = f.surf(x, y); L = 0.085 + rng.uniform(-0.006, 0.006)
        R = rotm(rng.uniform(0, 360), rng.uniform(-12, 12), 90 + rng.uniform(-8, 8))
        if k < 3:                                              # whole egg, half buried, lying on its side
            ellipsoid(b, (x, y, z + 0.012), (0.062, 0.062, L), rot=R, sub=3, jitter=0.0015, seed=k)
        else:                                                  # broken shell: an open cup with a jagged rim
            M = Matrix.Translation(Vector((x, y, z + 0.045))) @ rotm(rng.uniform(0, 360), rng.uniform(25, 45), 0).to_4x4()
            prof = [(0.0, -L * 0.95), (0.03, -L * 0.88), (0.052, -L * 0.6), (0.062, -L * 0.2), (0.06, 0.0), (0.055, 0.0), (0.056, -L * 0.2), (0.047, -L * 0.6), (0.0, -L * 0.85)]
            jag = lambda ph, r, i, s=k: (0.012 * (0.5 + 0.5 * math.sin(ph * 7 + s)) + 0.006 * math.sin(ph * 17)) if i in (4, 5) else 0.0
            revolve(b, M, prof, 28, zmod=jag, pids=[FOS] * 4 + [FOS2] * 4)
    for k in range(10):                                        # shell fragments
        x, y = scatter(f, rng, 1, 0.55, [(0, 0, 0.12)])[0]
        a = rng.uniform(0, 360); r = rng.uniform(0.012, 0.022)
        ellipsoid(b, f.on(x, y, 0.002), (r, r * 0.8, 0.004), rot=rotm(a, rng.uniform(-25, 25), rng.uniform(-25, 25)), sub=1, jitter=0.003, seed=k)
    pebbles(b, f, rng, n=5)
    return f

@fossil("kerbin_bear_skull", "Kerbin", pal(SAND, ra=(0.58, 0.54, 0.47), rb=(0.50, 0.46, 0.40), fa=(0.86, 0.82, 0.70), fb=(0.72, 0.66, 0.53), f2=(0.92, 0.88, 0.76), cr=(0.90, 0.86, 0.74)), kind="Skull")
def f_bearskull(b, rng):
    """A broad, short-faced bear skull: domed cranium with a sagittal crest, wide cheekbones, huge canines, loose jaw."""
    f = Field(0.95, 0.75, seed=181, tilt=(0.015, 0.01)).finalize(); f.build(b)
    cx, cy = -0.02, 0.05; z = f.surf(cx, cy) - 0.004
    ellipsoid(b, (cx, cy, z), (0.12, 0.085, 0.072), sub=3, jitter=0.004, seed=3)                         # cranium
    ellipsoid(b, (cx + 0.12, cy, z - 0.004), (0.075, 0.062, 0.05), sub=3, jitter=0.003, seed=4)            # short broad muzzle
    ellipsoid(b, (cx + 0.18, cy, z - 0.01), (0.03, 0.045, 0.036), sub=2)
    tube_path(b, [(cx - 0.12, cy, z + 0.05), (cx - 0.04, cy, z + 0.075), (cx + 0.05, cy, z + 0.062)], [0.008, 0.013, 0.004], 8)   # crest
    for sgn in (-1, 1):
        tube_path(b, [(cx + 0.09, cy + sgn * 0.05, z), (cx + 0.0, cy + sgn * 0.11, z + 0.006), (cx - 0.08, cy + sgn * 0.08, z + 0.01)], [0.014, 0.017, 0.012], 8)   # zygomatic arch
        oc = Vector((cx + 0.075, cy + sgn * 0.055, z + 0.03))
        ellipsoid(b, oc, (0.022, 0.012, 0.018), pid=DARK, sub=2)                                             # orbit
        ellipsoid(b, (cx + 0.2, cy + sgn * 0.016, z + 0.006), (0.01, 0.007, 0.007), pid=DARK, sub=1)         # nostrils
        cone(b, (cx + 0.165, cy + sgn * 0.038, z - 0.02), (0.15, sgn * 0.15, -1), 0.07, 0.014, pid=FOS2, bend=(-0.25, 0, 0))   # canines
        for k in range(3): cone(b, (cx + 0.1 - 0.035 * k, cy + sgn * 0.045, z - 0.03), (0, sgn * 0.2, -1), 0.022, 0.011, pid=FOS2)
    jy = cy - 0.2; jp = [Vector((cx - 0.04 + 0.25 * t, jy + 0.03 * math.sin(t * 2.2), 0)) for t in [k / 10 for k in range(11)]]
    for p in jp: p.z = f.surf(p.x, p.y) + 0.005
    tube_path(b, jp, [0.03 - 0.012 * (k / 10) for k in range(11)], 10, flat=0.7, up=(0, 0, 1))
    ellipsoid(b, jp[0] + Vector((-0.012, 0, 0.016)), (0.032, 0.022, 0.034))
    cone(b, jp[-2] + Vector((0, 0, 0.01)), (0.25, 0, 1), 0.06, 0.012, pid=FOS2, bend=(0.2, 0, 0))
    for k in range(5): cone(b, jp[3 + k] + Vector((0, 0, 0.01)), (0.1, 0, 1), 0.022, 0.01, pid=FOS2)
    for k in range(3):                                                                                       # a few vertebrae
        x, y = cx - 0.19 - k * 0.07, cy - 0.04 + 0.03 * math.sin(k); zz = f.surf(x, y) - 0.006
        ellipsoid(b, (x, y, zz), (0.028, 0.036, 0.026), sub=2, jitter=0.003, seed=k + 9)
        cone(b, (x, y, zz + 0.016), (-0.3, 0, 1), 0.04, 0.012)
    pebbles(b, f, rng)
    return f

@fossil("kerbin_megalodon_tooth", "Kerbin", pal(SAND, ra=(0.52, 0.5, 0.46), rb=(0.44, 0.42, 0.39), fa=(0.32, 0.3, 0.3), fb=(0.22, 0.21, 0.21), f2=(0.62, 0.52, 0.38), cr=(0.4, 0.38, 0.36)), kind="Tooth", cam=(0.6, -0.75, 0.7))
def f_megatooth(b, rng):
    """A palm-sized serrated triangular tooth, glossy black enamel over a tan root, weathering out of shore sandstone."""
    f = Field(0.8, 0.65, seed=191, H0=0.08, tilt=(0.01, 0.0)).finalize(); f.build(b)
    def tooth(cx, cy, sc, yaw, tilt):
        M = Matrix.Translation(f.on(cx, cy, -0.004)) @ rotm(yaw, tilt, 0).to_4x4()
        H, Wd, T = 0.17 * sc, 0.14 * sc, 0.022 * sc
        n = 14; rings = []
        for i in range(n + 1):                                  # cross-sections from the root (i = 0) to the tip, lying flat
            t = i / n
            w = Wd * (1 - t) ** 0.9 * (1 + 0.12 * math.sin(math.pi * t)); th = T * (1 - 0.75 * t)
            ring = []
            for k in range(16):
                a = k / 16 * TAU; x = math.cos(a) * w * 0.5
                serr = 0.0035 * sc * (abs(math.cos(a)) > 0.95) * (0.5 + 0.5 * math.sin(i * 7.0))
                ring.append(b.v(M @ Vector((x + math.copysign(serr, x), t * H, math.sin(a) * th * 0.5 + th * 0.5)), lin=t))
            rings.append(ring)
        for i in range(n):
            for k in range(16): b.f([rings[i][k], rings[i][(k + 1) % 16], rings[i + 1][(k + 1) % 16], rings[i + 1][k]], FOS if i > 2 else FOS2)
        b.cap(rings[0], True, FOS2)
        for sx in (-1, 1):                                      # two-lobed root
            ellipsoid(b, M @ Vector((sx * Wd * 0.25, -0.012 * sc, T * 0.5)), (Wd * 0.28, 0.03 * sc, T * 0.55), rot=M.to_3x3(), sub=2, pid=FOS2)
    tooth(0.0, -0.02, 1.0, 25, 4)
    tooth(0.24, 0.14, 0.45, -70, 8)
    for k in range(6):
        x, y = scatter(f, rng, 1, 0.55, [(0, 0, 0.16)])[0]
        cube(b, f.on(x, y, 0.004), (0.016, 0.01, 0.006), rotm(rng.uniform(0, 360), rng.uniform(-20, 20)), bevel=0.3, pid=FOS)
    pebbles(b, f, rng)
    return f

# ---------------------------------------------------------------------------- Duna
@fossil("duna_stromatolite", "Duna", pal(RED, fa=(0.70, 0.42, 0.30), fb=(0.58, 0.33, 0.24), f2=(0.78, 0.52, 0.38), lam=0.65, flay=0.009), kind="Stromatolite", cam=(0.6, -0.8, 0.75))
def f_dstrom(b, rng):
    f = Field(1.15, 0.95, seed=71, H0=0.05, layer=0.025).finalize(); f.build(b)
    domes(b, f, rng, 8, (0.05, 0.09), (0.09, 0.22), broken=2); pebbles(b, f, rng, 8)
    return f

@fossil("duna_ammonoid", "Duna", pal(RED, fa=(0.84, 0.60, 0.46), fb=(0.70, 0.46, 0.34)), kind="Coiled shell")
def f_dammo(b, rng):
    f = Field(0.9, 0.72, seed=81, tilt=(0.02, 0.0)).finalize(); f.build(b)
    coil(b, f.on(0.02, 0.03, 0.012), 0.17, turns=3.6, ratio=0.38, ribs=20, rib_amp=0.1, sutures=12, keel=0.12, rot=rotm(60, 7, -5))
    coil(b, f.on(-0.28, -0.18, 0.004), 0.11, turns=3.5, span=0.45, ratio=0.38, ribs=20, rib_amp=0.1, sutures=12, keel=0.12, rot=rotm(140, -8, 6))
    coil(b, f.on(0.28, -0.2, 0.004), 0.04, turns=3.0, ribs=18, rib_amp=0.1, keel=0.1, rot=rotm(10, 3))
    pebbles(b, f, rng)
    return f

@fossil("duna_saltfossil", "Duna", pal(RED, ra=(0.82, 0.72, 0.68), rb=(0.74, 0.63, 0.58), rc=(0.88, 0.80, 0.76), layer=0.012, grain=0.1, cr=(0.95, 0.80, 0.70)), kind="Halite crystal", cam=(0.6, -0.75, 0.8))
def f_salt(b, rng):
    f = Field(0.8, 0.66, seed=91, H0=0.06, rough=0.008, layer=0.02)
    f.wave(lambda x, y: 0.004 * max(0.0, 1 - abs(noise.noise(Vector((x * 9, y * 9, 4.0)))) * 6) ** 2)
    f.finalize(); f.build(b)
    for k in range(11):
        a = rng.uniform(0, TAU); d = 0.02 + 0.13 * math.sqrt(rng.random()); s_ = rng.uniform(0.035, 0.12) * (1.3 if k == 0 else 1.0)
        x, y = (math.cos(a) * d, math.sin(a) * d) if k else (0.0, 0.0)
        cube(b, f.on(x, y, s_ * rng.uniform(0.0, 0.3)), (s_, s_ * rng.uniform(0.85, 1.15), s_), rotm(rng.uniform(0, 90), rng.uniform(-35, 35), rng.uniform(-35, 35)), bevel=0.08, pid=CRYST)
    for k in range(10):
        x, y = scatter(f, rng, 1, 0.65, [(0, 0, 0.2)])[0]; s_ = rng.uniform(0.012, 0.03)
        cube(b, f.on(x, y, s_ * 0.2), s_, rotm(rng.uniform(0, 90), rng.uniform(-20, 20)), bevel=0.1, pid=CRYST)
    pebbles(b, f, rng, 4)
    return f

@fossil("duna_ironmat", "Duna", pal(RED, ra=(0.62, 0.27, 0.17), rb=(0.27, 0.24, 0.25), rc=(0.70, 0.36, 0.22), layer=0.011, wob=0.004, fa=(0.55, 0.30, 0.22), fb=(0.45, 0.24, 0.18), f2=(0.30, 0.26, 0.27), lam=0.7, flay=0.006, ftint=0.6), kind="Microbial mat")
def f_ironmat(b, rng):
    f = Field(1.0, 0.8, seed=101, H0=0.07, layer=0.012, terr=0.5, inner_terr=0.25, tilt=(0.03, 0.01))
    wr = lambda x, y: (1 - abs(noise.noise(Vector((x * 13, y * 13, 1.7))))) ** 4
    f.wave(lambda x, y: 0.005 * wr(x, y) + 0.0015 * noise.noise(Vector((x * 40, y * 40, 3.0))), lambda x, y: 0.55 * wr(x, y))
    f.finalize(); f.build(b)
    for x, y in scatter(f, rng, 9, 0.62, gap=0.08):
        r = rng.uniform(0.015, 0.045)
        ellipsoid(b, f.on(x, y, -r * 0.25), (r, r * rng.uniform(0.75, 0.95), r * 0.7), rotm(rng.uniform(0, 360)), 2, r * 0.12, rng.random() * 9)
    pebbles(b, f, rng)
    return f

@fossil("duna_burrows", "Duna", pal(RED, fa=(0.78, 0.55, 0.40), ftint=0.75), kind="Trace fossil")
def f_dburrows(b, rng):
    f = Field(1.0, 0.8, seed=111, tilt=(0.01, 0.015), rough=0.004)
    inb = lambda x, y: f.inside(x, y, 0.62)
    for k in range(5):
        st = scatter(f, rng, 1, 0.5)[0]
        pts = wander(rng, st, rng.uniform(0, TAU), 34, 0.015, 0.3, inb)
        f.ridge(pts, rng.uniform(0.008, 0.012), 0.008, fos=0.9)
    hx, hy, R = 0.24, -0.16, 0.11                        # hexagonal net trace
    cell = 0.024; cent = []
    for i in range(-6, 7):
        for j in range(-6, 7):
            cx = hx + (i + 0.5 * (j % 2)) * cell * math.sqrt(3); cy = hy + j * cell * 1.5
            if (Vector((cx - hx, cy - hy))).length < R: cent.append((cx, cy))
    for cx, cy in cent:
        hexp = [(cx + cell * math.cos(a), cy + cell * math.sin(a)) for a in [math.pi / 6 + k * math.pi / 3 for k in range(7)]]
        f.ridge(hexp, 0.0035, 0.0035, fos=0.8)
    for k in range(6):                                     # U-burrow openings
        x, y = scatter(f, rng, 1, 0.55)[0]; a = rng.uniform(0, TAU)
        for sgn in (-1, 1): f.blob(x + sgn * 0.02 * math.cos(a), y + sgn * 0.02 * math.sin(a), 0.007, 0.007, 0, 0.012, dk=0.9, neg=True, rim=0.002, fos=0.0)
    f.finalize(); f.build(b); pebbles(b, f, rng)
    return f

def frond(f, x0, y0, ang, L, Wm, nseg=16, h=0.007):
    d = Vector((math.cos(ang), math.sin(ang))); n = Vector((-d.y, d.x)); P0 = Vector((x0, y0))
    f.blob(x0 - d.x * 0.09 * L / 0.6, y0 - d.y * 0.09 * L / 0.6, 0.055 * L / 0.6, 0.055 * L / 0.6, 0, 0.006, fos=0.8)
    for rr in (0.6, 0.95):
        ring = [(P0 - d * 0.09 * L / 0.6 + Vector((math.cos(a), math.sin(a))) * 0.05 * L / 0.6 * rr) for a in [TAU * k / 24 for k in range(25)]]
        f.ridge(ring, 0.003, 0.004, fos=0.9)
    f.ridge([P0 - d * 0.05 * L / 0.6, P0 + d * 0.08 * L], 0.008 * L / 0.6, 0.006)
    for side in (-1, 1):
        for k in range(nseg):
            t = (k + (0.5 if side > 0 else 0.0) + 0.5) / (nseg + 0.5)
            w = Wm * math.sin(math.pi * min(0.99, t * 0.95 + 0.04)) ** 0.7
            c = P0 + d * (0.08 * L + t * 0.92 * L) + n * side * w * 0.5 - d * w * 0.18
            f.blob(c.x, c.y, w * 0.55, 0.92 * L / nseg * 0.55, ang + side * 0.45, h * 1.4, fos=0.85, power=0.7)
    f.ridge([P0 + d * 0.08 * L, P0 + d * L], 0.003, 0.004, neg=True, dk=0.5)

@fossil("duna_frond", "Duna", pal(RED, ra=(0.64, 0.42, 0.33), rb=(0.56, 0.36, 0.28), fa=(0.80, 0.62, 0.50), ftint=0.55), kind="Impression")
def f_frond(b, rng):
    f = Field(1.05, 0.82, seed=121, tilt=(0.012, -0.01), rough=0.003)
    frond(f, -0.32, -0.08, 0.25, 0.58, 0.19)
    frond(f, 0.08, 0.22, -0.35, 0.3, 0.11, 12)
    f.finalize(); f.build(b); pebbles(b, f, rng)
    return f

@fossil("duna_cupreef", "Duna", pal(RED, fa=(0.82, 0.60, 0.48), fb=(0.70, 0.48, 0.36), f2=(0.40, 0.22, 0.16), pore=0.75), kind="Reef cups", cam=(0.6, -0.8, 0.8))
def f_cups(b, rng):
    f = Field(0.9, 0.75, seed=131, H0=0.07).finalize(); f.build(b)
    def cup(M, h, r1):
        r0 = r1 * 0.2
        prof = [(0, -0.03), (r0, -0.03), (r0 * 1.2, 0.0), (r1 * 0.65, h * 0.45), (r1 * 0.92, h * 0.85), (r1, h), (r1 * 0.82, h * 1.0), (r1 * 0.72, h * 0.8), (r1 * 0.45, h * 0.45), (0, h * 0.25)]
        revolve(b, M, prof, 24, rmod=lambda ph, z, i: 1 + 0.05 * math.cos(ph * 14), pids=[FOS] * 5 + [FOS2] * 4)
    for x, y in scatter(f, rng, 7, 0.45, gap=0.1):
        h = rng.uniform(0.06, 0.13)
        cup(Matrix.Translation(f.on(x, y, -0.02)) @ rotm(rng.uniform(0, 360), rng.uniform(-14, 14), rng.uniform(-10, 10)).to_4x4(), h, h * rng.uniform(0.38, 0.5))
    for x, y in scatter(f, rng, 3, 0.62, gap=0.15):
        h = rng.uniform(0.07, 0.1)
        cup(Matrix.Translation(f.on(x, y, 0.01)) @ rotm(rng.uniform(0, 360), 0, 95).to_4x4(), h, h * 0.45)
    pebbles(b, f, rng)
    return f

@fossil("kerbin_reefcore", "Kerbin", pal(LIME, ra=(0.74, 0.70, 0.60), rb=(0.64, 0.60, 0.51), rc=(0.82, 0.78, 0.68), layer=0.035,
                                     fa=(0.93, 0.89, 0.78), fb=(0.80, 0.74, 0.60), f2=(0.62, 0.55, 0.42), line=(0.42, 0.36, 0.28)), kind="Fossil reef", res=2048, cam=(0.6, -0.8, 0.7))
def f_reefcore(b, rng):
    """a slab of ancient reef limestone from the floor of the Glimmering Reef's cavern: branching corals lying in the
    bedding, half-buried brain-coral heads (one broken open), and a cluster of cup corals - the ancestors of the reef above"""
    f = Field(1.45, 1.1, seed=171, H0=0.09, layer=0.035).finalize(); f.build(b)
    # branching (staghorn-like) colonies toppled onto the old sea floor
    for k in range(5):
        x0, y0 = rng.uniform(-0.45, 0.35), rng.uniform(-0.35, 0.3)
        h = rng.uniform(0, TAU)
        def branch(p, h, L, r, depth):
            pts = []; q = Vector(p)
            for i in range(6):
                pts.append(Vector((q.x, q.y, f.surf(q.x, q.y) - r * 0.35)))
                h += rng.uniform(-0.18, 0.18); q = q + Vector((math.cos(h), math.sin(h))) * (L / 5)
            if any(f.outline(pp.x, pp.y) > 0.8 for pp in pts): return
            tube_path(b, pts, [r * (1 - 0.35 * i / 5) for i in range(6)], 8, pid=FOS, cap_pid=FOS2)
            if depth > 0:
                for s_ in (-1, 1):
                    if rng.random() < 0.75: branch((pts[3].x, pts[3].y), h + s_ * rng.uniform(0.5, 0.9), L * 0.6, r * 0.75, depth - 1)
        branch((x0, y0), h, rng.uniform(0.3, 0.45), rng.uniform(0.022, 0.032), 2)
    # brain-coral heads weathering out (the first is broken open to show the radiating walls)
    domes(b, f, rng, 3, (0.1, 0.17), (0.1, 0.16), broken=1, avoid=())
    # a cluster of cup corals
    def cup(M, h, r1):
        r0 = r1 * 0.25
        prof = [(0, -0.03), (r0, -0.03), (r0 * 1.2, 0.0), (r1 * 0.65, h * 0.45), (r1 * 0.92, h * 0.85), (r1, h), (r1 * 0.82, h * 1.0), (r1 * 0.72, h * 0.8), (r1 * 0.45, h * 0.45), (0, h * 0.25)]
        revolve(b, M, prof, 20, rmod=lambda ph, z, i: 1 + 0.06 * math.cos(ph * 16), pids=[FOS] * 5 + [FOS2] * 4)
    cx, cy = rng.uniform(0.25, 0.45), rng.uniform(-0.3, -0.1)
    for k in range(6):
        x, y = cx + rng.normal(0, 0.06) if hasattr(rng, "normal") else cx + rng.uniform(-0.08, 0.08), cy + rng.uniform(-0.08, 0.08)
        hh = rng.uniform(0.05, 0.09)
        cup(Matrix.Translation(f.on(x, y, -0.015)) @ rotm(rng.uniform(0, 360), rng.uniform(-18, 18), rng.uniform(-12, 12)).to_4x4(), hh, hh * 0.45)
    pebbles(b, f, rng, 10)
    return f

@fossil("duna_orthocone", "Duna", pal(RED, fa=(0.82, 0.62, 0.48), fb=(0.68, 0.48, 0.36), f2=(0.52, 0.33, 0.24)), kind="Straight shell")
def f_ortho(b, rng):
    f = Field(1.0, 0.75, seed=141, tilt=(0.0, 0.015)).finalize(); f.build(b)
    for k, (L, r1, x, y) in enumerate(((0.46, 0.042, 0.02, 0.05), (0.34, 0.032, -0.04, -0.15), (0.24, 0.025, 0.12, 0.2))):
        a = math.radians(18 + rng.uniform(-10, 10)); d = Vector((math.cos(a), math.sin(a), 0))
        n = 18; pts = []; rad = []; lins = []
        for i in range(n + 1):
            t = i / n; p = Vector((x, y, 0)) + d * (t - 0.5) * L
            p.z = f.surf(p.x, p.y) - 0.012 + 0.012 * t
            pts.append(p); rad.append(0.003 + (r1 - 0.003) * t); lins.append(t * L / 0.024)
        tube_path(b, pts, rad, 16, lins=lins, rmod=lambda i, ph, L=L: 1 + 0.035 * math.cos(i * 2.6), cap_pid=FOS2)
        end = pts[-1]
        tube_path(b, [end - d * 0.002, end + d * 0.004], [rad[-1] * 0.16, rad[-1] * 0.16], 8, pid=DARK)
    pebbles(b, f, rng)
    return f

@fossil("duna_brachiopod", "Duna", pal(RED, fa=(0.86, 0.66, 0.52), fb=(0.72, 0.52, 0.40)), kind="Paired shells")
def f_brach(b, rng):
    f = Field(0.85, 0.7, seed=151, rough=0.005).finalize(); f.build(b)
    for x, y in scatter(f, rng, 9, 0.6, gap=0.11):
        L = rng.uniform(0.05, 0.085)
        valve(b, f.on(x, y, -0.006), L, L * rng.uniform(1.0, 1.2), L * rng.uniform(0.3, 0.42), rng.randint(16, 24), rotm(rng.uniform(0, 360), rng.uniform(-10, 10), rng.uniform(-10, 10)))
    for k in range(6):
        x, y = scatter(f, rng, 1, 0.62)[0]
        cube(b, f.on(x, y, 0.002), (0.018, 0.012, 0.004), rotm(rng.uniform(0, 360), rng.uniform(-15, 15)), bevel=0.3)
    pebbles(b, f, rng)
    return f

# ---------------------------------------------------------------------------- Eve
@fossil("eve_gasbag_impression", "Eve", pal(BASALT, ra=(0.36, 0.32, 0.38), rb=(0.29, 0.26, 0.31), ftint=0.7), kind="Impression")
def f_gasbag(b, rng):
    f = Field(1.1, 0.85, seed=161, rough=0.004, tilt=(0.01, 0.0))
    cx, cy = 0.05, 0.03
    f.blob(cx, cy, 0.3, 0.21, 0.15, 0.014, fos=0.6, dk=0.2, neg=True, power=0.35, rim=0.004)
    for k in range(16):
        a = TAU * k / 16; d = Vector((math.cos(a) * 0.29, math.sin(a) * 0.2))
        pts = [(cx + d.x * t + 0.01 * math.sin(t * 9 + k), cy + d.y * t) for t in [0.12 + 0.88 * j / 10 for j in range(11)]]
        f.ridge(pts, 0.004, 0.004, fos=0.9)
    for ox, oy, r in ((-0.33, 0.2, 0.08), (-0.36, -0.12, 0.06), (0.36, -0.25, 0.05)):
        f.blob(ox, oy, r, r * 0.75, rng.uniform(0, 3), 0.008, fos=0.6, neg=True, power=0.4, rim=0.003)
    for k in range(5):
        y0 = cy - 0.12 + k * 0.06
        pts = [(cx + 0.28 + 0.03 * j, y0 + 0.02 * math.sin(j * 0.8 + k)) for j in range(9)]
        f.ridge(pts, 0.006, 0.004, fos=0.6, neg=True, dk=0.3)
    f.finalize(); f.build(b); pebbles(b, f, rng)
    return f

@fossil("eve_burrows", "Eve", pal(BASALT, grain=0.35, fa=(0.32, 0.22, 0.42), fb=(0.22, 0.15, 0.30), cr=(0.26, 0.18, 0.36)), kind="Trace fossil")
def f_eburrows(b, rng):
    f = Field(1.0, 0.8, seed=171, rough=0.007, layer=0.04)
    inb = lambda x, y: f.inside(x, y, 0.6)
    paths = []
    for k in range(4):
        st = scatter(f, rng, 1, 0.5)[0]
        pts = wander(rng, st, rng.uniform(0, TAU), 26, 0.02, 0.28, inb); paths.append(pts)
        f.ridge(pts, rng.uniform(0.014, 0.019), 0.014, fos=1.0, dk=0.3, neg=True)
    f.finalize(); f.build(b)
    for pts in paths[:2]:
        seg = pts[6:16]
        p3 = [f.on(p.x, p.y, -0.004) for p in seg]
        tube_path(b, p3, 0.017, 12, pid=CRYST, cap_pid=DARK)
    pebbles(b, f, rng, 7)
    return f

# ---------------------------------------------------------------------------- Laythe
@fossil("laythe_reefcoil", "Laythe", pal(SHALE, fa=(0.72, 0.80, 0.78), fb=(0.58, 0.66, 0.65), f2=(0.42, 0.48, 0.48)), kind="Spired shell")
def f_reefcoil(b, rng):
    f = Field(0.95, 0.75, seed=181, tilt=(0.01, 0.02)).finalize(); f.build(b)
    for k, (x, y, rm, a) in enumerate(((0.0, 0.02, 0.036, 20), (-0.27, 0.19, 0.018, 140), (-0.25, -0.17, 0.02, 80), (0.27, -0.16, 0.016, 250))):
        ax = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0))
        L = 14 * rm * 0.74
        spire(b, f.on(x, y, -rm * 0.4) - ax * L * 0.55, ax, rm, turns=12 if k == 0 else 10)
    pebbles(b, f, rng)
    return f

@fossil("laythe_trackway", "Laythe", pal(BLACKSAND), kind="Trackway", cam=(0.75, -0.55, 0.65))
def f_ltrack(b, rng):
    f = Field(0.9, 2.0, step=0.009, seed=191, tilt=(0.0, -0.015), rough=0.004, p=3.2)
    f.wave(lambda x, y: 0.003 * math.sin((x * 0.3 + y * 0.95) * TAU / 0.09 + noise.noise(Vector((x * 2, y * 2, 5.0)))))
    def pr(x, y, s_, sgn):
        f.blob(x, y, 0.024 * s_, 0.02 * s_, 0, 0.01, dk=0.5, neg=True, rim=0.003)
        f.blob(x, y + 0.03 * s_, 0.032 * s_, 0.022 * s_, 0, 0.004, dk=0.3, neg=True, fos=0.0)       # web
        for a in (-0.7, -0.25, 0.25, 0.7):
            tip = Vector((x + math.sin(a) * 0.05 * s_, y + math.cos(a) * 0.05 * s_))
            f.ridge([(x, y), tip], 0.006 * s_, 0.008, dk=0.6, neg=True, fos=0.0)
    for k in range(5):
        yk = -0.78 + k * 0.36
        for sgn in (-1, 1):
            o = 0.18 if (k % 2 == 0) == (sgn > 0) else 0.0
            pr(sgn * 0.16, yk + o + 0.09, 1.3, sgn)             # fore
            if yk + o - 0.07 > -0.92: pr(sgn * 0.2, yk + o - 0.07, 1.6, sgn)   # hind
    f.ridge([(0.04 * math.sin(y * 4.5), y) for y in [-0.92 + 0.04 * k for k in range(47)]], 0.014, 0.005, dk=0.3, neg=True, fos=0.0)
    f.finalize(); f.build(b); pebbles(b, f, rng, 8)
    return f

@fossil("laythe_sporeash", "Laythe", pal(SAND, ra=(0.70, 0.66, 0.56), rb=(0.58, 0.55, 0.46), rc=(0.78, 0.74, 0.64), layer=0.014, grain=0.18, fa=(0.86, 0.76, 0.52), fb=(0.74, 0.62, 0.40), f2=(0.62, 0.50, 0.32), ftint=0.5), kind="Spore bed")
def f_sporeash(b, rng):
    f = Field(1.0, 0.8, seed=201, layer=0.016, inner_terr=0.3, terr=0.5)
    for k in range(5):
        x, y = scatter(f, rng, 1, 0.55)[0]; f.blob(x, y, rng.uniform(0.06, 0.12), rng.uniform(0.05, 0.1), rng.uniform(0, 3), 0.002, fos=0.45, power=0.3)
    f.finalize(); f.build(b)
    big = scatter(f, rng, 2, 0.5, gap=0.3)
    for x, y in big:
        r = rng.uniform(0.045, 0.06)
        ellipsoid(b, f.on(x, y, -r * 0.1), (r, r, r * 0.8), sub=3, jitter=r * 0.14, seed=rng.random() * 9)
    for x, y in scatter(f, rng, 46, 0.64, [(bx, by, 0.09) for bx, by in big], gap=0.035):
        r = rng.uniform(0.006, 0.018)
        ellipsoid(b, f.on(x, y, -r * 0.1), (r, r, r * 0.85), sub=1 if r < 0.01 else 2, jitter=r * 0.12, seed=rng.random() * 9, pid=FOS if rng.random() < 0.7 else FOS2)
    pebbles(b, f, rng)
    return f

@fossil("laythe_filtercomb", "Laythe", pal(SHALE, fa=(0.86, 0.84, 0.76), fb=(0.74, 0.72, 0.64), f2=(0.62, 0.60, 0.52)), kind="Bone")
def f_comb(b, rng):
    f = Field(1.05, 0.8, seed=211, rough=0.003)
    bristles = []
    C = Vector((0.0, -0.42)); R = 0.42; arc = [math.radians(a) for a in range(58, 123, 4)]
    bar = [C + Vector((math.cos(a), math.sin(a))) * R for a in arc]
    for k, a in enumerate([math.radians(x) for x in range(60, 121, 2)]):
        p = C + Vector((math.cos(a), math.sin(a))) * (R - 0.02); dn = -Vector((math.cos(a), math.sin(a)))
        L = 0.17 + 0.03 * math.sin(k * 1.7) - 0.05 * abs(k - 15) / 15
        tip = p + dn * L + Vector((-dn.y, dn.x)) * 0.012 * math.sin(k)
        bristles.append((p, tip))
        f.blob((p.x + tip.x) / 2, (p.y + tip.y) / 2, L * 0.5, 0.004, math.atan2(dn.y, dn.x), 0.0, fos=0.35, power=0.3)
    f.finalize(); f.build(b)
    for p, tip in bristles:
        mid = p + (tip - p) * 0.5
        tube_path(b, [f.on(p.x, p.y, -0.001), f.on(mid.x, mid.y, 0.0), f.on(tip.x, tip.y, -0.001)], [0.0042, 0.0034, 0.0015], 4, pid=FOS2)
    pts = [f.on(p.x, p.y, -0.006) for p in bar]
    tube_path(b, pts, [0.022 + 0.008 * math.sin(math.pi * k / (len(pts) - 1)) for k in range(len(pts))], 12, flat=0.45, up=(0, 0, 1))
    frag = [f.on(0.32 + 0.1 * t, 0.2 + 0.04 * math.sin(t * 3), -0.004) for t in [k / 5 for k in range(6)]]
    tube_path(b, frag, 0.014, 10, flat=0.45, up=(0, 0, 1), pid=FOS2)
    pebbles(b, f, rng)
    return f

@fossil("laythe_krakenbeak", "Laythe", pal(SHALE, ra=(0.40, 0.40, 0.41), rb=(0.32, 0.32, 0.34), dark=(0.17, 0.12, 0.10)), kind="Beak")
def f_beak(b, rng):
    f = Field(0.85, 0.7, seed=221, rough=0.004).finalize(); f.build(b)
    def beak(c, yaw, s_, lower=False):
        # a hooked rostrum curling down to a sharp point, a tall crest, and two thin lateral wings, lying on its side
        M = rotm(yaw); c = Vector(c); pts = []; rad = []
        for k in range(16):
            t = k / 15; a = math.radians(105 * t ** 1.3)
            pts.append(c + M @ Vector((0.11 * s_ * math.sin(a), -0.11 * s_ * (1 - math.cos(a)), 0.012 * s_ * (1 - t))))
            rad.append(0.034 * s_ * (1 - t) ** 1.6 + 0.0012)
        tube_path(b, pts, rad, 12, up=(0, 0, 1), flat=0.55, pid=DARK)
        crest = [c + M @ Vector((-0.07 * s_ + 0.075 * s_ * t, 0.022 * s_ * math.sin(math.pi * t) + 0.004 * s_, 0.006 * s_)) for t in [k / 6 for k in range(7)]]
        tube_path(b, crest, [0.004 * s_, 0.012 * s_, 0.016 * s_, 0.017 * s_, 0.015 * s_, 0.012 * s_, 0.008 * s_], 8, up=(0, 0, 1), flat=0.5, pid=DARK)
        for wz in (-1, 1):
            ellipsoid(b, c + M @ Vector((-0.06 * s_, -0.012 * s_, wz * 0.004 * s_ + 0.004)), (0.075 * s_, 0.03 * s_, 0.0045 * s_), rot=M @ rotm(-12 if lower else 8), sub=2, pid=DARK)
    beak(f.on(-0.05, 0.06, 0.012), 12, 1.0)
    beak(f.on(0.1, -0.13, 0.012), 205, 1.2, True)
    for k in range(5):
        x, y = scatter(f, rng, 1, 0.62, [(0, 0, 0.22)])[0]
        cube(b, f.on(x, y, 0.002), (0.016, 0.01, 0.003), rotm(rng.uniform(0, 360), rng.uniform(-15, 15)), bevel=0.3, pid=DARK)
    pebbles(b, f, rng)
    return f

@fossil("laythe_raptorlimb", "Laythe", pal(SHALE, ra=(0.42, 0.38, 0.33), rb=(0.34, 0.31, 0.27), fa=(0.72, 0.55, 0.38), fb=(0.60, 0.44, 0.30), f2=(0.48, 0.34, 0.22)), kind="Limb")
def f_limb(b, rng):
    f = Field(0.95, 0.75, seed=231, rough=0.003)
    f.blob(-0.1, 0.12, 0.26, 0.09, 0.4, 0.002, fos=0.3, power=0.2)
    f.finalize(); f.build(b)
    n = 11; pts2 = []; th = -0.3; p = Vector((-0.28, -0.12)); seglen = []
    for k in range(n + 1):
        pts2.append(p.copy()); L = 0.075 - 0.04 * k / n; seglen.append(L)
        th += 0.18 + 0.05 * k / n; p = p + Vector((math.cos(th), math.sin(th))) * L
    fine = []; rad = []; lins = []
    for k in range(n):
        a, c = pts2[k], pts2[k + 1]; r = 0.034 - 0.022 * k / n
        for j in range(4):
            t = j / 4; q = a + (c - a) * t; fine.append(f.on(q.x, q.y, -r * 0.3)); rad.append(r * (0.82 + 0.18 * math.sin(math.pi * t) ** 0.5)); lins.append(k + t)
    fine.append(f.on(pts2[-1].x, pts2[-1].y, -0.002)); rad.append(0.004); lins.append(n)
    tube_path(b, fine, rad, 12, lins=lins, flat=0.7, up=(0, 0, 1))
    for k in range(2, n):
        a, c = pts2[k], pts2[k + 1]; d = (c - a).normalized(); inner = Vector((-d.y, d.x)); r = 0.034 - 0.022 * k / n
        for o in (-0.25, 0.25):
            base = f.on(*(a + (c - a) * (0.5 + o)), r * 0.15) + Vector((inner.x, inner.y, 0)) * r * 0.6
            dirv = Vector((inner.x * 0.85 + d.x * 0.5, inner.y * 0.85 + d.y * 0.5, 0.3))
            cone(b, base, dirv, 0.06 - 0.03 * k / n, r * 0.3, pid=FOS2)
    pebbles(b, f, rng)
    return f

@fossil("laythe_chalkreef", "Laythe", pal(LIME, ra=(0.84, 0.82, 0.76), rb=(0.76, 0.74, 0.68), rc=(0.90, 0.88, 0.83), layer=0.03, fa=(0.95, 0.93, 0.87), fb=(0.85, 0.83, 0.76), f2=(0.70, 0.68, 0.60), pore=0.6, grain=0.1), kind="Fungal reef", cam=(0.6, -0.8, 0.8))
def f_chalk(b, rng):
    f = Field(1.1, 0.9, seed=241, H0=0.08).finalize(); f.build(b)
    def branch(p, d, r, depth):
        L = rng.uniform(0.035, 0.06) * (1.0 if depth < 2 else 1.3); bend = Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0.15))
        pts = [p + (d + bend * t) * L * t for t in (0, 0.33, 0.66, 1.0)]
        tube_path(b, pts, [r, r * 0.95, r * 0.9, r * 0.82], 10)
        end = pts[-1]
        if depth == 0:
            ellipsoid(b, end, (r * 0.95, r * 0.95, r * 0.95), sub=1); return
        dn = (pts[-1] - pts[-2]).normalized(); xb, yb, _ = basis(dn)
        for c in range(rng.choice((2, 2, 3))):
            a = TAU * c / 3 + rng.uniform(-0.4, 0.4); sp = math.radians(rng.uniform(25, 42))
            nd = (dn * math.cos(sp) + (xb * math.cos(a) + yb * math.sin(a)) * math.sin(sp)).normalized()
            branch(end, nd, r * 0.78, depth - 1)
    for x, y in scatter(f, rng, 3, 0.4, gap=0.3):
        branch(f.on(x, y, -0.02), Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 1)).normalized(), 0.022, 2)
    for x, y in scatter(f, rng, 5, 0.6, gap=0.2):
        a = rng.uniform(0, TAU); d = Vector((math.cos(a), math.sin(a), 0.08))
        branch(f.on(x, y, -0.006), d, 0.015, 1)
    pebbles(b, f, rng)
    return f

# ============================================================================ material
def fossil_nodes(P):
    def build(N):
        wob = N.m('MULTIPLY', N.m('SUBTRACT', N.noise(3.0, 3), 0.5), P['wob'])
        zz = N.m('ADD', N.Z, wob)
        strata = N.m('MULTIPLY', N.m('ADD', N.m('SINE', N.m('MULTIPLY', zz, TAU / P['layer'])), 1.0), 0.5)
        fine = N.m('MULTIPLY', N.m('ADD', N.m('SINE', N.m('MULTIPLY', zz, TAU / (P['layer'] * 0.31))), 1.0), 0.5)
        rock = N.mix(P['ra'], P['rb'], N.m('ADD', N.m('MULTIPLY', strata, 0.75), N.m('MULTIPLY', fine, 0.25)))
        blot = N.m('MULTIPLY', N.m('SUBTRACT', N.noise(P['ns'], 4), 0.45), 3.0, clamp=True)
        rock = N.mix(rock, P['rc'], N.m('MULTIPLY', blot, 0.6))
        speck = N.m('LESS_THAN', N.voronoi(160.0, 'F1'), 0.16)
        rock = N.mix(rock, N.gray(1.0 - P['grain']), speck, 'MULTIPLY')
        fos = N.attr("fos"); dk = N.attr("dk"); lin = N.attr("lin")
        fcol = N.mix(P['fa'], P['fb'], N.noise(14.0, 5))
        rock = N.mix(rock, fcol, N.m('MULTIPLY', fos, P['ftint']))
        rock = N.mix(rock, N.gray(0.45), N.m('MULTIPLY', dk, 1.0), 'MULTIPLY')
        sol = fcol
        if P['lam']:
            lam = N.m('MULTIPLY', N.m('ADD', N.m('SINE', N.m('MULTIPLY', zz, TAU / P['flay'])), 1.0), 0.5)
            sol = N.mix(sol, P['f2'], N.m('MULTIPLY', N.m('POWER', lam, 3.0), P['lam']))
        ln = N.m('ADD', lin, N.m('MULTIPLY', N.m('SUBTRACT', N.noise(45.0, 3), 0.5), 0.22))
        fr = N.m('FRACT', ln); dd = N.m('MINIMUM', fr, N.m('SUBTRACT', 1.0, fr))
        line = N.m('SUBTRACT', 1.0, N.m('DIVIDE', dd, 0.07), clamp=True)
        sol = N.mix(sol, P['line'], N.m('MULTIPLY', line, 0.8))
        if P['pore']:
            pores = N.m('LESS_THAN', N.voronoi(110.0, 'F1'), 0.2)
            sol = N.mix(sol, P['f2'], N.m('MULTIPLY', pores, P['pore']))
        sec = N.mix(P['f2'], N.mul(P['f2'], 0.8), N.noise(20.0, 4))
        if P['lam']: sec = N.mix(sec, P['fa'], N.m('MULTIPLY', N.m('POWER', lam, 3.0), P['lam'] * 0.6))
        dark = N.mix(P['dark'], N.mul(P['dark'], 1.8), N.noise(18.0, 5))
        cry = N.mix(P['cr'], N.mul(P['cr'], 0.85), N.noise(9.0, 3))
        incl = N.m('LESS_THAN', N.voronoi(70.0, 'F1'), 0.09)
        cry = N.mix(cry, N.mul(P['cr'], 0.35), N.m('MULTIPLY', incl, 0.8))
        col = rock
        for i, c in ((FOS, sol), (FOS2, sec), (DARK, dark), (CRYST, cry)): col = N.mix(col, c, N.is_part(i))
        ao = N.node('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = P['ao']
        try: ao.samples = 16; ao.only_local = True
        except Exception: pass
        aof = N.ramp(ao.outputs['AO'], [(0.0, (0.42, 0.42, 0.42)), (1.0, (1.0, 1.0, 1.0))])
        col = N.mix(col, aof, 1.0, 'MULTIPLY')
        return col, None
    return build

def preview_material(obj, name, P):
    mat = bpy.data.materials.get(name + "_prev") or bpy.data.materials.new(name + "_prev")
    N = Nodes(mat); col, _ = fossil_nodes(P)(N)
    gm = N.node('ShaderNodeGamma'); N.L(col, gm.inputs[0]); gm.inputs[1].default_value = 2.2
    bs = N.node('ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = 0.85
    out = N.node('ShaderNodeOutputMaterial'); N.L(gm.outputs[0], bs.inputs['Base Color']); N.L(bs.outputs[0], out.inputs['Surface'])
    obj.data.materials.clear(); obj.data.materials.append(mat)

def fossil_bake(obj, name, out_dir, P, res, samples=12):
    os.makedirs(out_dir, exist_ok=True)
    scn = bpy.context.scene; me = obj.data
    mat = bpy.data.materials.get(name + "_bake") or bpy.data.materials.new(name + "_bake")
    N = Nodes(mat); col, _ = fossil_nodes(P)(N)
    emit = N.node('ShaderNodeEmission'); out = N.node('ShaderNodeOutputMaterial'); N.L(emit.outputs[0], out.inputs['Surface'])
    img_node = N.node('ShaderNodeTexImage'); N.L(col, emit.inputs['Color'])
    me.materials.clear(); me.materials.append(mat)
    iname = name + "_diffuse"; img = bpy.data.images.get(iname)
    if img is None or img.size[0] != res:
        if img: bpy.data.images.remove(img)
        img = bpy.data.images.new(iname, res, res, alpha=False)
    img.colorspace_settings.name = 'Non-Color'; img_node.image = img
    for n_ in N.nt.nodes: n_.select = False
    img_node.select = True; N.nt.nodes.active = img_node
    scn.render.engine = 'CYCLES'; scn.cycles.samples = samples; scn.cycles.device = 'CPU'
    scn.render.bake.margin = 8; scn.render.bake.use_clear = True
    select_only([obj]); bpy.ops.object.bake(type='EMIT')
    img.filepath_raw = os.path.join(out_dir, iname + ".png"); img.file_format = 'PNG'; img.save()
    img.colorspace_settings.name = 'sRGB'
    fm = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    fm.use_nodes = True; ft = fm.node_tree; ft.nodes.clear()
    bs = ft.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = 0.85
    fo = ft.nodes.new('ShaderNodeOutputMaterial'); ft.links.new(bs.outputs[0], fo.inputs['Surface'])
    dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = img; ft.links.new(dt.outputs[0], bs.inputs['Base Color'])
    me.materials.clear(); me.materials.append(fm)
    mp = fm.mumatprop; mp.shaderName = "KSP/Diffuse"
    for coll in (mp.color.properties, mp.texture.properties, mp.float2.properties, mp.float3.properties, mp.vector.properties): coll.clear()
    c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
    t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = img.name
    scn.render.engine = 'BLENDER_EEVEE'
    return fm

def mask_material(obj):
    mat = bpy.data.materials.get("fossil_mask") or bpy.data.materials.new("fossil_mask")
    N = Nodes(mat)
    solid = N.m('GREATER_THAN', N.part, 0.5)
    fos = N.m('GREATER_THAN', N.attr("fos"), 0.45)
    dk = N.m('GREATER_THAN', N.attr("dk"), 0.3)
    m = N.m('MAXIMUM', N.m('MAXIMUM', solid, fos), dk)
    mix = N.node('ShaderNodeMixShader'); tr = N.node('ShaderNodeBsdfTransparent'); em = N.node('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1, 1, 1, 1)
    N.L(m, mix.inputs[0]); N.L(tr.outputs[0], mix.inputs[1]); N.L(em.outputs[0], mix.inputs[2])
    out = N.node('ShaderNodeOutputMaterial'); N.L(mix.outputs[0], out.inputs['Surface'])
    keep = list(obj.data.materials); obj.data.materials.clear(); obj.data.materials.append(mat)
    return keep

def fossil_uv(obj, side=0.35, solid=1.15, margin=0.004):
    """smart-project, then shrink islands that are steep rock (the buried flanks) and enlarge the fossil pieces,
    so the bedding plane and the fossil get most of the texture"""
    from bpy_extras.bmesh_utils import bmesh_linked_uv_islands
    uv_unwrap(obj, margin=margin)
    select_only([obj]); bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data); uvl = bm.loops.layers.uv.active; pl = bm.faces.layers.int.get("part")
    for isl in bmesh_linked_uv_islands(bm, uvl):
        area = sum(f.calc_area() for f in isl) or 1.0
        rock = sum(f.calc_area() for f in isl if f[pl] == ROCK) / area
        steep = sum(f.calc_area() for f in isl if f[pl] == ROCK and f.normal.z < 0.55) / area
        k = side if steep > 0.5 else (solid if rock < 0.5 else 1.0)
        if k == 1.0: continue
        loops = [l for f in isl for l in f.loops]
        c = sum((l[uvl].uv for l in loops), Vector((0, 0))) / len(loops)
        for l in loops: l[uvl].uv = c + (l[uvl].uv - c) * k
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
    try: bpy.ops.uv.pack_islands(rotate=True, margin=margin, scale=True)
    except TypeError: bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')

def hard_normals(obj, angle=52):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(angle)]
    bmesh.ops.split_edges(bm, edges=sharp); bm.to_mesh(obj.data); bm.free()
    for p in obj.data.polygons: p.use_smooth = True

# ============================================================================ run
def render_views(name, root, S, f, final):
    cam, g = stage_setup(ground=False, sky=(0.42, 0.45, 0.5))
    span = max(f.sx, f.sy)
    tgt = Vector((0, 0, 0.06)); d = Vector(S['cam']).normalized()
    cam.data.type = 'PERSP'; cam.data.lens = S['lens']; cam.data.clip_start = 0.01
    look_at(cam, tgt + d * span * 1.55, tgt)
    out = {}
    out["a"] = render(os.path.join(PREVIEW_DIR, "fossil_%s_a.png" % name), res=(900, 700), transparent=final)
    if final:
        out["portrait"] = os.path.join(PREVIEW_DIR, "fossil_%s_a.png" % name)
    else:
        look_at(cam, Vector((0.0, -0.001, span * 1.6)), Vector((0, 0, 0)))
        out["b"] = render(os.path.join(PREVIEW_DIR, "fossil_%s_b.png" % name), res=(900, 700))
    return out

def silmask(name, obj, f):
    cam, g = stage_setup(ground=False); g.hide_render = True
    keep = mask_material(obj)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(f.sx, f.sy) * 1.02
    cam.location = (0, 0, 3); cam.rotation_euler = (0, 0, 0)
    bpy.context.scene.cycles.samples = 8
    p = render(os.path.join(PREVIEW_DIR, "fossil_%s_silmask.png" % name), 'CYCLES', (1024, 1024), True)
    obj.data.materials.clear()
    for m in keep: obj.data.materials.append(m)
    return p

def build(name):
    S = SPECS[name]; rng = random.Random(hash(name) & 0xffff)
    rng.seed(sum(ord(c) * (i + 1) for i, c in enumerate(name)))
    new_scene("XenoFossil_" + name)
    b = B(); f = S['fn'](b, rng)
    obj = b.finish(name + "_mesh"); hard_normals(obj)
    root = link(bpy.data.objects.new(name, None)); obj.parent = root
    P = S['pal']; res = {"tris": len(obj.data.polygons), "verts": len(obj.data.vertices), "size": [round(f.sx, 2), round(f.sy, 2)], "kind": S['kind'], "body": S['body']}
    if STEP == "model":
        preview_material(obj, name, P); res.update(render_views(name, root, S, f, False)); return res
    out_dir = os.path.join(XENO_DIR, "Models", "Fossils", S['body'])
    fossil_uv(obj)
    fossil_bake(obj, name, out_dir, P, S['res'])
    res.update(export_mu(name, os.path.join(out_dir, name + ".mu")))
    res["model"] = "Xenobiology/Models/Fossils/%s/%s" % (S['body'], name)
    res.update(render_views(name, root, S, f, True))
    res["silmask"] = silmask(name, obj, f)
    return res

def wanted():
    if isinstance(FOSSIL, (list, tuple)): return list(FOSSIL)
    if FOSSIL == "all": return list(SPECS)
    if FOSSIL in SPECS: return [FOSSIL]
    return [n for n, s in SPECS.items() if s['body'] == FOSSIL]

if __name__ == "__xeno__":
    results = {}
    for nm in wanted():
        try: results[nm] = build(nm)
        except Exception as e:
            import traceback; results[nm] = {"error": traceback.format_exc()[-1500:]}
    rp = os.path.join(os.path.dirname(PREVIEW_DIR), "fossil_results.json")
    old = {}
    if os.path.exists(rp):
        try: old = json.load(open(rp))
        except Exception: old = {}
    if STEP != "model": old.update(results); json.dump(old, open(rp, "w"), indent=1)
    result = results
