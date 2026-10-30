"""Xenobiology — coral & sponge builders shared by reef_corals.py (the reef) and reef_specimens.py (field-guide portraits).

Every builder takes a Mesh, a base point p and the surface normal n, and calls SNAP(point) -> (point, normal) to stick
parts to the rock (reef: nearest high-poly vertex; specimens: a flat plate). UVs land in one cell of the coral atlas,
4 columns x 8 rows (2048 x 4096, cells of 512):
    row 0: cup orange (cyl) | cup teal (cyl) | fire ochre (blade) | fire olive (blade)
    row 1: leather cap cream (polar) | leather stalk (cyl) | leather cap olive (polar) | elkhorn (branch)
    row 2: zoanthid column | zoanthid disc green | zoanthid disc magenta | zoanthid disc orange/teal   (discs polar)
    row 3: cup crown orange (polar) | cup crown teal (polar) | rock contact | finger leather (cyl)
    row 4: brain coral tan (polar dome) | brain coral green (polar dome) | table coral top (polar) | table coral under (cyl)
    row 5: staghorn (cyl, blue tips) | staghorn (cyl, violet tips) | pillar coral (cyl) | anemone column (cyl)
    row 6: anemone tentacles (cyl, glowing tips) | anemone disc (polar) | barrel sponge outside (cyl) | barrel sponge inside (cyl)
    row 7: tube sponge violet (cyl, glow rim) | tube sponge yellow (cyl, glow rim) | tube sponge inside | anemone tentacles plain
"""
import math
import numpy as np

ROWS = 8
rng = np.random.default_rng(909)
SNAP = None                       # set by the caller

class Mesh:
    def __init__(self): self.v = []; self.uv = []; self.f = []
    def add(self, co, uv): self.v.append(np.asarray(co, float)); self.uv.append(uv); return len(self.v) - 1
    def tri(self, a, b, c): self.f.append((a, b, c))
    def quad(self, a, b, c, d): self.f.append((a, b, c)); self.f.append((a, c, d))

def cell(cx, cy, u, v, pad=0.02):
    return ((cx + pad + (1 - 2 * pad) * min(1, max(0, u))) / 4.0, (cy + pad + (1 - 2 * pad) * min(1, max(0, v))) / ROWS)
def pcell(cx, cy, r, a):
    return cell(cx, cy, 0.5 + 0.47 * r * math.cos(a), 0.5 + 0.47 * r * math.sin(a))
def basis(n):
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    t = np.cross(n, [0, 0, 1.0]) if abs(n[2]) < 0.95 else np.cross(n, [1.0, 0, 0])
    t /= np.linalg.norm(t); b = np.cross(n, t); return t, b, n
def tilt(n, deg):
    t, b, n = basis(n); a = rng.uniform(0, math.tau); s = math.radians(deg) * rng.random()
    d = n * math.cos(s) + (t * math.cos(a) + b * math.sin(a)) * math.sin(s); return d / np.linalg.norm(d)
def ring_pts(c, t, b, r, segs, ph=0.0, flat=1.0, wob=None):
    out = []
    for k in range(segs + 1):
        a = ph + k / segs * math.tau
        rr = r * (wob(a) if wob else 1.0)
        out.append(c + (t * math.cos(a) + b * math.sin(a) * flat) * rr)
    return out

def tube(m, a, b, r0, r1, segs, cx, cy, v0, v1, rings=1, flat=1.0, up=None, cap=False, wob=None, bend=None):
    """open tube a->b (optional cap). flat < 1 squashes the cross-section along 'up'. bend: offset vector * t^2."""
    a = np.array(a, float); b = np.array(b, float); d = b - a; L = np.linalg.norm(d); d /= L
    ref = up if up is not None else ([0, 0, 1.0] if abs(d[2]) < 0.9 else [1.0, 0, 0])
    s1 = np.cross(d, ref); s1 /= np.linalg.norm(s1); s2 = np.cross(s1, d)
    R = []
    for i in range(rings + 1):
        t = i / rings; rr = r0 + (r1 - r0) * t; c = a + d * L * t + (np.asarray(bend) * t * t if bend is not None else 0)
        R.append([m.add(p, cell(cx, cy, k / segs, v0 + (v1 - v0) * t)) for k, p in enumerate(ring_pts(c, s1, s2, rr, segs, flat=flat, wob=wob))])
    for i in range(rings):
        for k in range(segs): m.quad(R[i][k], R[i][k + 1], R[i + 1][k + 1], R[i + 1][k])
    if cap:
        tip = (b + (np.asarray(bend) if bend is not None else 0)) + d * r1 * 0.5
        c = m.add(tip, cell(cx, cy, 0.5, min(1.0, v1 + 0.02)))
        for k in range(segs): m.tri(R[-1][k], R[-1][k + 1], c)
    return R

def open_cup(m, base, axis, r0, r1, H, segs, cx_out, cy_out, cx_in, cy_in, rings=3, wall=0.03, wob=None, flare=1.0):
    """a hollow vessel (sponge, cup): outside wall, rim, inside wall going down to a floor"""
    t, b, ax = basis(axis)
    outer = []; inner = []
    for i in range(rings + 1):
        s = i / rings; r = (r0 + (r1 - r0) * s ** flare); c = base + ax * H * s
        outer.append([m.add(p, cell(cx_out, cy_out, k / segs, s)) for k, p in enumerate(ring_pts(c, t, b, r, segs, wob=wob))])
    for i in range(rings + 1):
        s = 1 - i / rings * 0.85; r = (r0 + (r1 - r0) * s ** flare) - wall; c = base + ax * H * s
        inner.append([m.add(p, cell(cx_in, cy_in, k / segs, s)) for k, p in enumerate(ring_pts(c, t, b, max(0.01, r), segs, wob=wob))])
    for i in range(rings):
        for k in range(segs):
            m.quad(outer[i][k], outer[i][k + 1], outer[i + 1][k + 1], outer[i + 1][k])
            m.quad(inner[i][k], inner[i][k + 1], inner[i + 1][k + 1], inner[i + 1][k])
    for k in range(segs): m.quad(outer[-1][k], outer[-1][k + 1], inner[0][k + 1], inner[0][k])     # rim
    fc = m.add(base + ax * H * 0.15, cell(cx_in, cy_in, 0.5, 0.1))
    for k in range(segs): m.tri(inner[-1][k], inner[-1][k + 1], fc)

# ====================================================================== the species
def cup_cluster(m, p, n, glow):
    cx = 1 if glow else 0
    t, b, _ = basis(n)
    for k in range(rng.integers(5, 10)):
        q, qn = SNAP(p + (t * rng.normal() + b * rng.normal()) * 0.16)
        ax = tilt(qn, 25); r = rng.uniform(0.05, 0.08); L = rng.uniform(0.08, 0.2)
        tip = q + ax * L
        tube(m, q - ax * 0.05, tip, r * 0.85, r, 6, cx, 0, 0.05, 0.7)
        tt, bb, _ = basis(ax); S = 10
        ring = [m.add(p_, cell(cx, 0, i / S, 0.72)) for i, p_ in enumerate(ring_pts(tip, tt, bb, r, S))]
        # tentacle crown: the rim alternates long and short tentacles so the outline is starry
        fl = [m.add(tip + ax * (0.02 + 0.02 * (i % 2)) + (tt * math.cos(i / S * math.tau) + bb * math.sin(i / S * math.tau)) * r * (2.3 if i % 2 == 0 else 1.6),
                    cell(cx, 0, i / S, 0.98)) for i in range(S + 1)]
        for i in range(S): m.quad(ring[i], ring[i + 1], fl[i + 1], fl[i])
        cc = m.add(tip + ax * 0.012, pcell(cx, 3, 0, 0))
        disc = [m.add(tip + ax * (0.02 + 0.02 * (i % 2)) + (tt * math.cos(i / S * math.tau) + bb * math.sin(i / S * math.tau)) * r * (2.3 if i % 2 == 0 else 1.6),
                      pcell(cx, 3, 1.0 if i % 2 == 0 else 0.7, i / S * math.tau)) for i in range(S)]
        for i in range(S): m.tri(cc, disc[i], disc[(i + 1) % S])

def zoanthid_colony(m, p, n, variant, R):
    cx = 1 + variant
    t, b, _ = basis(n)
    for k in range(int(np.clip(math.pi * R * R * 70, 6, 24))):
        rr = R * math.sqrt(rng.random()); a = rng.uniform(0, math.tau)
        q, qn = SNAP(p + (t * math.cos(a) + b * math.sin(a)) * rr)
        ax = tilt(qn, 15); rd = rng.uniform(0.035, 0.06); h = rng.uniform(0.025, 0.06)
        tt, bb, _ = basis(ax); S = 5; ph = rng.uniform(0, math.tau)
        low = [m.add(p_, cell(0, 2, i / S, 0.0)) for i, p_ in enumerate(ring_pts(q - ax * 0.02, tt, bb, rd * 0.8, S, ph))]
        hi = [m.add(p_, cell(0, 2, i / S, 1.0)) for i, p_ in enumerate(ring_pts(q + ax * h, tt, bb, rd, S, ph))]
        for i in range(S): m.quad(low[i], low[i + 1], hi[i + 1], hi[i])
        c = m.add(q + ax * (h + 0.006), pcell(cx, 2, 0, 0))
        rim = [m.add(q + ax * h + (tt * math.cos(ph + i / S * math.tau) + bb * math.sin(ph + i / S * math.tau)) * rd, pcell(cx, 2, 1.0, i / S * math.tau)) for i in range(S)]
        for i in range(S): m.tri(c, rim[i], rim[(i + 1) % S])

def fire_coral(m, p, n, variant):
    """Millepora: upright blades with lobed crests, arranged in rows and crossing walls (thick, with a rim)"""
    cx = 2 + variant
    row = rng.uniform(0, math.tau)
    rowd = np.array([math.cos(row), math.sin(row), 0]); side = np.array([-rowd[1], rowd[0], 0])
    for k in range(rng.integers(3, 8)):
        off = rowd * (k - 3.5) * rng.uniform(0.12, 0.2) + side * rng.normal(0, 0.12)
        q, qn = SNAP(p + off)
        W = rng.uniform(0.3, 0.65); Hh = rng.uniform(0.35, 0.8) * (1.2 if qn[2] > 0.7 else 1.0)
        ang = row + (math.pi / 2 if k % 3 else 0.0) + rng.normal(0, 0.3)
        wd = np.array([math.cos(ang), math.sin(ang), 0.0]); nd = np.array([-wd[1], wd[0], 0.0])
        bend = rng.normal(0, 0.06); lean = tilt(np.array([0, 0, 1.0]), 10)
        NX, NY = 4, 2; lobes = rng.integers(2, 5); ph = rng.uniform(0, math.tau)
        def pt(s, tv, side_):
            crest = 0.72 + 0.28 * abs(math.sin(s * math.pi * lobes + ph))           # scalloped top edge
            hh = Hh * tv * crest * (0.7 + 0.3 * math.sin(math.pi * s))
            th = 0.035 * (1 - 0.6 * tv)                                               # thicker at the base
            return q - lean * 0.08 + wd * (s - 0.5) * W * (0.85 + 0.15 * tv) + lean * hh + nd * (bend * math.sin(math.pi * s) * tv + side_ * th), min(1.0, tv * crest + 0.02)
        G2 = {}
        for sgn in (1, -1):
            for j in range(NY + 1):
                for i in range(NX + 1):
                    co, vv = pt(i / NX, j / NY, sgn); G2[(sgn, i, j)] = m.add(co, cell(cx, 0, i / NX, vv))
            for j in range(NY):
                for i in range(NX):
                    qd = (G2[(sgn, i, j)], G2[(sgn, i + 1, j)], G2[(sgn, i + 1, j + 1)], G2[(sgn, i, j + 1)])
                    m.quad(*(qd if sgn > 0 else qd[::-1]))
        for i in range(NX):           # crest rim joining the two faces (white tips)
            m.quad(G2[(1, i, NY)], G2[(1, i + 1, NY)], G2[(-1, i + 1, NY)], G2[(-1, i, NY)])
        for j in range(NY):           # end walls
            m.quad(G2[(-1, 0, j)], G2[(-1, 0, j + 1)], G2[(1, 0, j + 1)], G2[(1, 0, j)])
            m.quad(G2[(1, NX, j)], G2[(1, NX, j + 1)], G2[(-1, NX, j + 1)], G2[(-1, NX, j)])

def leather(m, p, n, glow, scale=1.0):
    cx = 2 if glow else 0
    ax = np.asarray(n) * 0.3 + np.array([0, 0, 0.7]); ax /= np.linalg.norm(ax); ax = tilt(ax, 15)
    Hs = rng.uniform(0.25, 0.6) * scale; rs = rng.uniform(0.12, 0.25) * scale; Rc = rng.uniform(0.5, 1.25) * scale
    topc = p + ax * Hs
    tt, bb, _ = basis(ax); S = 16
    st = tube(m, p - ax * 0.08, topc, rs * 1.3, rs, S, 1, 1, 0.0, 0.8)
    folds = rng.integers(4, 8); amp = rng.uniform(0.05, 0.13) * Rc; ph = rng.uniform(0, math.tau)
    def cap_pt(r, a):
        z = amp * math.sin(folds * a + ph) * r ** 1.5 - 0.06 * Rc * r * r + 0.04 * Rc
        return topc + (tt * math.cos(a) + bb * math.sin(a)) * r * Rc + ax * z
    cc = m.add(cap_pt(0, 0), pcell(cx, 1, 0, 0))
    rings = [[m.add(cap_pt(r, k / S * math.tau), pcell(cx, 1, r * 0.98, k / S * math.tau)) for k in range(S)] for r in (0.34, 0.67, 1.0)]
    for k in range(S): m.tri(cc, rings[0][k], rings[0][(k + 1) % S])
    for i in range(2):
        for k in range(S): m.quad(rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % S], rings[i][(k + 1) % S])
    under = [m.add(cap_pt(0.8, k / S * math.tau) - ax * 0.05 * Rc, cell(1, 1, k / S, 0.95)) for k in range(S + 1)]
    rimu = [m.add(cap_pt(1.0, k / S * math.tau) - ax * 0.005, cell(1, 1, k / S, 1.0)) for k in range(S + 1)]
    for k in range(S):
        m.quad(rimu[k], under[k], under[k + 1], rimu[k + 1])
        m.quad(under[k], st[-1][k], st[-1][k + 1], under[k + 1])

def finger_leather(m, p, n):
    t, b, _ = basis(n)
    for k in range(rng.integers(8, 15)):
        q, qn = SNAP(p + (t * rng.normal() + b * rng.normal()) * 0.22)
        ax = qn * 0.5 + np.array([0, 0, 0.5]); ax = tilt(ax / np.linalg.norm(ax), 30)
        L = rng.uniform(0.3, 0.6); r = rng.uniform(0.028, 0.045)
        side = np.cross(ax, [0, 0, 1.0]) if abs(ax[2]) < 0.95 else np.array([1.0, 0, 0])
        side = side / max(1e-6, np.linalg.norm(side)) * rng.choice([-1, 1])
        tube(m, q - ax * 0.05, q + ax * L, r * 1.4, r * 0.75, 5, 3, 3, 0.05, 0.92, rings=3, cap=True, bend=side * L * 0.35)

def elkhorn(m, p, n, scale):
    """Acropora palmata: a stout trunk forking into broad, flattened, upward-angled 'palms' with rounded tips"""
    up = np.array([0, 0, 1.0])
    trunk_top = p + (up * 0.85 + np.asarray(n) * 0.15) * 0.16 * scale
    tube(m, p - up * 0.2, trunk_top, 0.3 * scale, 0.24 * scale, 8, 3, 1, 0.0, 0.45, flat=0.7)
    def grow(a, heading, elev, L, w, depth):
        d = np.array([math.cos(heading) * math.cos(elev), math.sin(heading) * math.cos(elev), math.sin(elev)])
        side = np.cross(d, up); side /= max(1e-6, np.linalg.norm(side)); nrm = np.cross(side, d)
        terminal = depth == 0
        S = 6; RINGS = 2
        R = []
        for i in range(RINGS + 1):
            s = i / RINGS
            ww = w * (1 + (1.1 if terminal else 0.35) * s)                     # palms widen toward the tip
            th = w * 0.28 * (1 - 0.35 * s)
            c = a + d * L * s + nrm * L * 0.2 * s * s                             # tips curl upward toward the light
            row = []
            for k in range(S + 1):
                ang = k / S * math.tau
                row.append(m.add(c + side * math.cos(ang) * ww + nrm * math.sin(ang) * th, cell(3, 1, k / S, 0.4 + 0.45 * s if not terminal else 0.5 + 0.5 * s)))
            R.append(row)
        for i in range(RINGS):
            for k in range(S): m.quad(R[i][k], R[i][k + 1], R[i + 1][k + 1], R[i + 1][k])
        tipc = a + d * L * 1.0 + nrm * L * 0.2
        if terminal:                                                                    # rounded tip: fan the last ring onto a point
            e = m.add(tipc + d * w * 0.9, cell(3, 1, 0.5, 1.0))
            for k in range(S): m.tri(R[-1][k], R[-1][k + 1], e)
        else:
            n_ = 2 if rng.random() < 0.65 else 3
            spread = rng.uniform(0.35, 0.6)
            for j in range(n_):
                off = (j - (n_ - 1) / 2) * spread
                grow(tipc - d * w * 0.3, heading + off + rng.normal(0, 0.08), elev + rng.uniform(-0.05, 0.15), L * rng.uniform(0.6, 0.8), w * rng.uniform(0.85, 1.0), depth - 1)
    h0 = rng.uniform(0, math.tau); nb = int(rng.integers(3, 6))
    for k in range(nb):                      # low and wide: thick limbs splaying out almost flat, then fanning into palms
        grow(trunk_top, h0 + k * math.tau / nb + rng.normal(0, 0.25), math.radians(rng.uniform(4, 18)), rng.uniform(0.5, 0.75) * scale, 0.21 * scale, 2)

def brain_coral(m, p, n, variant, R):
    """a hemispherical head, slightly squashed and lumpy, set into the rock; the maze is in the texture (polar)"""
    cx = variant
    up = np.asarray(n) * 0.4 + np.array([0, 0, 0.6]); up /= np.linalg.norm(up)
    t, b, ax = basis(up); S = 16; RI = 5
    c0 = p - ax * R * 0.25
    lump = rng.uniform(0, math.tau, 3)
    def wob(a, e): return 1 + 0.06 * math.sin(3 * a + lump[0]) * math.cos(e) + 0.04 * math.sin(5 * a + lump[1])
    rows = []
    for i in range(RI + 1):
        e = (i / RI) * math.pi * 0.5 * 0.97                # 0 = rim, up to near the top
        row = []
        for k in range(S):
            a = k / S * math.tau; rr = R * wob(a, e)
            co = c0 + (t * math.cos(a) + b * math.sin(a)) * rr * math.cos(e) + ax * rr * math.sin(e) * 0.8
            row.append(m.add(co, pcell(cx, 4, 1 - i / RI, a)))
        rows.append(row)
    for i in range(RI):
        for k in range(S): m.quad(rows[i][k], rows[i][(k + 1) % S], rows[i + 1][(k + 1) % S], rows[i + 1][k])
    top = m.add(c0 + ax * R * 0.8 * wob(0, math.pi / 2), pcell(cx, 4, 0, 0))
    for k in range(S): m.tri(rows[-1][k], rows[-1][(k + 1) % S], top)

def table_coral(m, p, n, R):
    """Acropora table: a short stalk under a flat, lobed, horizontal plate"""
    up = np.array([0, 0, 1.0]); Hs = R * rng.uniform(0.35, 0.6)
    top = p + up * Hs
    tube(m, p - up * 0.15, top, R * 0.22, R * 0.14, 8, 3, 4, 0.0, 0.8)
    t, b, _ = basis(up); S = 20; ph = rng.uniform(0, math.tau); lob = rng.integers(5, 9)
    def rim(a): return R * (1 + 0.13 * math.sin(lob * a + ph) + 0.05 * math.sin(13 * a))
    tilt_ = tilt(up, 8)
    def P(r, a, z): return top + (t * math.cos(a) + b * math.sin(a)) * r + tilt_ * z
    cc = m.add(P(0, 0, 0.1 * R), pcell(2, 4, 0, 0))
    rings = [[m.add(P(rim(k / S * math.tau) * f, k / S * math.tau, (0.1 - 0.06 * f) * R), pcell(2, 4, f * 0.98, k / S * math.tau)) for k in range(S)] for f in (0.5, 1.0)]
    for k in range(S): m.tri(cc, rings[0][k], rings[0][(k + 1) % S])
    for k in range(S): m.quad(rings[0][k], rings[1][k], rings[1][(k + 1) % S], rings[0][(k + 1) % S])
    edge = [m.add(P(rim(k / S * math.tau) * 0.99, k / S * math.tau, 0.0), cell(3, 4, k / S, 0.95)) for k in range(S + 1)]
    under = [m.add(P(rim(k / S * math.tau) * 0.45, k / S * math.tau, -0.02 * R), cell(3, 4, k / S, 0.5)) for k in range(S + 1)]
    rim1 = [m.add(P(rim(k / S * math.tau), k / S * math.tau, 0.04 * R), cell(3, 4, k / S, 1.0)) for k in range(S + 1)]
    for k in range(S):
        m.quad(rim1[k], edge[k], edge[k + 1], rim1[k + 1])
        m.quad(edge[k], under[k], under[k + 1], edge[k + 1])
    uc = m.add(top - up * 0.02, cell(3, 4, 0.5, 0.3))
    for k in range(S): m.tri(under[k + 1], under[k], uc)

def staghorn(m, p, n, variant, scale=1.0):
    """Acropora cervicornis: a thicket of round, antler-like branches with pale growing tips"""
    cx = variant; up = np.array([0, 0, 1.0])
    def grow(a, d, L, r, depth):
        b = a + d * L
        tube(m, a, b, r, r * 0.8, 5, cx, 5, 0.1 + 0.25 * (2 - depth) / 2, 1.0 if depth == 0 else 0.55, cap=depth == 0)
        if depth > 0:
            for j in range(2 if rng.random() < 0.7 else 3):
                nd = tilt(d * 0.7 + up * 0.3, 40); grow(b - d * r, nd / np.linalg.norm(nd), L * rng.uniform(0.7, 0.95), r * 0.85, depth - 1)
    t, b, _ = basis(up)
    for k in range(rng.integers(4, 7)):
        q, qn = SNAP(p + (t * rng.normal() + b * rng.normal()) * 0.3 * scale)
        d = tilt(qn * 0.3 + up * 0.7, 30)
        grow(q - d * 0.05, d / np.linalg.norm(d), rng.uniform(0.25, 0.4) * scale, 0.05 * scale, 2)

def pillar_coral(m, p, n, scale=1.0):
    """Dendrogyra: a few fat vertical columns with rounded tops, furry with polyps by day"""
    up = np.array([0, 0, 1.0]); t, b, _ = basis(up)
    for k in range(rng.integers(3, 7)):
        q, qn = SNAP(p + (t * rng.normal() + b * rng.normal()) * 0.25 * scale)
        H = rng.uniform(0.6, 1.8) * scale; r = rng.uniform(0.07, 0.14) * scale
        d = tilt(up, 6)
        wob = (lambda ph: (lambda a: 1 + 0.08 * math.sin(5 * a + ph)))(rng.uniform(0, 6.3))
        tube(m, q - d * 0.1, q + d * H, r * 1.15, r, 8, 2, 5, 0.0, 0.95, rings=3, cap=True, wob=wob)

def anemone(m, p, n, glow, scale=1.0):
    """a fleshy column, an oral disc and a crown of tentacles (tips glow on the night-blooming kind)"""
    ax = tilt(np.asarray(n) * 0.5 + np.array([0, 0, 0.5]), 10); ax /= np.linalg.norm(ax)
    H = rng.uniform(0.15, 0.3) * scale; r = rng.uniform(0.09, 0.16) * scale
    top = p + ax * H
    tube(m, p - ax * 0.04, top, r * 1.2, r, 10, 3, 5, 0.0, 1.0)
    t, b, _ = basis(ax); S = 10
    cc = m.add(top + ax * 0.01, pcell(1, 6, 0, 0))
    rim = [m.add(top + (t * math.cos(k / S * math.tau) + b * math.sin(k / S * math.tau)) * r * 1.05, pcell(1, 6, 1.0, k / S * math.tau)) for k in range(S)]
    for k in range(S): m.tri(cc, rim[k], rim[(k + 1) % S])
    NT = 20
    for k in range(NT):
        a = k / NT * math.tau + rng.normal(0, 0.05); rr = r * (0.75 if k % 2 else 0.95)
        base = top + (t * math.cos(a) + b * math.sin(a)) * rr
        out = (t * math.cos(a) + b * math.sin(a)) * 0.6 + ax * 0.8; out /= np.linalg.norm(out)
        L = rng.uniform(0.16, 0.26) * scale
        droop = (t * math.cos(a) + b * math.sin(a)) * L * 0.6 - ax * L * 0.55
        tube(m, base, base + out * L, 0.028 * scale, 0.012 * scale, 4, 0 if glow else 3, 6 if glow else 7, 0.0, 1.0, rings=1, cap=True, bend=droop)

def barrel_sponge(m, p, n, R):
    up = np.asarray(n) * 0.25 + np.array([0, 0, 0.75]); up /= np.linalg.norm(up)
    H = R * rng.uniform(1.4, 2.2)
    ph = rng.uniform(0, 6.3)
    open_cup(m, p - up * 0.1, up, R * 0.75, R, H, 14, 2, 6, 3, 6, rings=4, wall=R * 0.18,
             wob=lambda a: 1 + 0.07 * abs(math.sin(7 * a + ph)), flare=0.7)

def tube_sponge(m, p, n, variant):
    t, b, _ = basis(n)
    for k in range(rng.integers(3, 7)):
        q, qn = SNAP(p + (t * rng.normal() + b * rng.normal()) * 0.12)
        ax = tilt(qn * 0.4 + np.array([0, 0, 0.6]), 15); ax /= np.linalg.norm(ax)
        H = rng.uniform(0.3, 0.9); r = rng.uniform(0.05, 0.09)
        open_cup(m, q - ax * 0.05, ax, r * 0.9, r * 1.1, H, 6, variant, 7, 2, 7, rings=2, wall=0.015)

def sea_fan(m, p, n, variant, W):
    """an alpha-cut gorgonian net (seafan.png, 2x2 colours), double sided, bowed, facing the current (+-y)"""
    Hf = W * rng.uniform(0.85, 1.05)
    face = math.pi / 2 + rng.normal(0, 0.4)
    nd = np.array([math.cos(face), math.sin(face), 0.0]); wd = np.array([-nd[1], nd[0], 0.0])
    up = tilt(np.array([0, 0, 1.0]), 12); up = up + np.array([n[0], n[1], 0]) * 0.25; up /= np.linalg.norm(up)
    base = p - up * 0.08
    cu, cv = variant % 2, variant // 2
    NX, NY = 4, 4; bow = rng.normal(0, 0.12) * W
    for sgn in (1, -1):
        idx = [[0] * (NX + 1) for _ in range(NY + 1)]
        for j in range(NY + 1):
            for i in range(NX + 1):
                s, tv = i / NX, j / NY
                co = base + wd * (s - 0.5) * W + up * tv * Hf + nd * (bow * (s - 0.5) ** 2 * 4 * tv + 0.004 * sgn)
                idx[j][i] = m.add(co, ((cu + s) / 2.0, (1 - cv) / 2.0 + tv / 2.0 * 0.995))
        for j in range(NY):
            for i in range(NX):
                qd = (idx[j][i], idx[j][i + 1], idx[j + 1][i + 1], idx[j + 1][i])
                m.quad(*(qd if sgn > 0 else qd[::-1]))
    return base

# species id -> (display, builder kind) used by both scripts
SPECIES = ["kerbin_elkhorncoral", "kerbin_staghorncoral", "kerbin_tablecoral", "kerbin_braincoral", "kerbin_pillarcoral",
           "kerbin_suncupcoral", "kerbin_glowcupcoral", "kerbin_firecoral", "kerbin_leathercoral", "kerbin_fingerleather",
           "kerbin_seafan", "kerbin_zoanthid", "kerbin_anemone", "kerbin_barrelsponge", "kerbin_tubesponge"]
