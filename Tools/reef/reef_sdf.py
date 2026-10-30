"""Xenobiology — the Kerbin coral reef: rock and dead-coral base as a signed distance field -> high-poly mesh.

The base is a reef crest (a long winding ridge) with spur-and-groove fingers on its seaward side, a lagoon of
patch-reef bommies (some with overhanging mushroom tops), two free-standing arches, a skylit cavern with two
swim-through tunnels, a second winding tunnel, a slot canyon with a chockstone bridge, and rubble.
Tunnels are cut after the rock noise is applied (with their own light noise) so they keep their size: >= 4 m wide.

Local frame: x east-ish, y toward the lagoon (+y = back reef), z up; z = 0 is the sea floor, the rock continues to
z = -4 so uneven terrain never shows the underside. Writes reef_high.npz (verts, faces) and reef_meta.json
(tunnel paths for clearance checks, skylights, cavern).
Usage: python reef_sdf.py <out_dir> [voxel=0.3]
"""
import sys, os, json, math
import numpy as np
from skimage.measure import marching_cubes

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
VOX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
rng = np.random.default_rng(4242)
X0, X1, Y0, Y1, Z0, Z1 = -104.0, 104.0, -74.0, 52.0, -5.0, 14.0

# ------------------------------------------------------------------ noise (vectorised Perlin)
_perm = rng.permutation(256); _perm = np.concatenate([_perm, _perm])
_grad = rng.normal(size=(256, 3)); _grad /= np.linalg.norm(_grad, axis=1, keepdims=True)
def _fade(t): return t * t * t * (t * (t * 6 - 15) + 10)
def perlin(x, y, z):
    xi, yi, zi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64), np.floor(z).astype(np.int64)
    xf, yf, zf = x - xi, y - yi, z - zi; xi &= 255; yi &= 255; zi &= 255
    u, v, w = _fade(xf), _fade(yf), _fade(zf)
    out = 0
    acc = []
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = _perm[_perm[_perm[xi + dx] + yi + dy] + zi + dz]
                g = _grad[h]
                d = g[..., 0] * (xf - dx) + g[..., 1] * (yf - dy) + g[..., 2] * (zf - dz)
                acc.append(d)
    x00 = acc[0] + u * (acc[4] - acc[0]); x01 = acc[1] + u * (acc[5] - acc[1])
    x10 = acc[2] + u * (acc[6] - acc[2]); x11 = acc[3] + u * (acc[7] - acc[3])
    y0 = x00 + v * (x10 - x00); y1 = x01 + v * (x11 - x01)
    return y0 + w * (y1 - y0)
def fbm(x, y, z, f, octaves, gain=0.5, off=0.0):
    s = 0; a = 1.0; norm = 0
    for o in range(octaves):
        s = s + a * perlin(x * f + off + o * 17.3, y * f + o * 31.1, z * f - off + o * 7.7); norm += a
        a *= gain; f *= 2.03
    return s / norm

# ------------------------------------------------------------------ primitives
def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b + (a - b) * h - k * h * (1 - h)
def smax(a, b, k): return -smin(-a, -b, k)

def seg_dist(P, A, B):
    """distance from points P (...,3) to segment AB, and the parameter t"""
    AB = B - A; t = np.clip(((P - A) @ AB) / max(1e-9, AB @ AB), 0, 1)
    Q = A + t[..., None] * AB
    return np.linalg.norm(P - Q, axis=-1), t

def capsule_chain(P, pts, rad, vscale=1.0):
    """tube through pts with per-point radius; vscale < 1 squashes the cross-section vertically (ellipse)"""
    Ps = P.copy(); Ps[..., 2] /= vscale
    d = np.full(P.shape[:-1], 1e9)
    for i in range(len(pts) - 1):
        A = np.array(pts[i], float); B = np.array(pts[i + 1], float); A[2] /= vscale; B[2] /= vscale
        dd, t = seg_dist(Ps, A, B)
        r = rad[i] + (rad[i + 1] - rad[i]) * t
        d = np.minimum(d, (dd - r) * vscale)
    return d

def ellipsoid(P, c, r):
    q = (P - np.array(c)) / np.array(r)
    k0 = np.linalg.norm(q, axis=-1); k1 = np.linalg.norm(q / np.array(r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)

# ------------------------------------------------------------------ layout
SHAPES = []      # (kind, args, bbox(min,max), blend k)
CUTS = []        # tunnels/caverns (subtracted after noise)
META = {"tunnels": [], "skylights": [], "cavern": None, "arches": [], "slot": None, "bommies": []}
def bb(pts, pad):
    a = np.array(pts, float); return (a.min(0) - pad, a.max(0) + pad)

# reef crest: a ridge winding along x, wider and higher in the middle
crest = [(-96, 26), (-86, 21), (-70, 17), (-55, 22), (-32, 18), (-8, 13), (14, 19), (38, 15), (60, 21), (80, 15), (90, 19), (97, 23)]
cpts = [(x, y, -1.0) for x, y in crest]
crad = [3.0, 8.0, 11.0, 12.0, 13.0, 11.5, 12.5, 12.0, 11.0, 12.5, 8.5, 3.0]
SHAPES.append(("chain", (cpts, crad, 0.78), bb(cpts, 14), 3.0))
# a back-reef shoulder (lower, broader) so the lagoon side slopes away in steps
bpts = [(x, y + 10, -2.5) for x, y in crest]; brad = [r * 0.9 for r in crad]
SHAPES.append(("chain", (bpts, brad, 0.5), bb(bpts, 13), 4.0))
# coral heads and pinnacles along the crest top (relief), and overhanging lips on the seaward face
for k in range(34):
    x = rng.uniform(-84, 86); yc = np.interp(x, [c[0] for c in crest], [c[1] for c in crest]) + rng.uniform(-7, 9)
    if abs(x + 32) < 13 and abs(yc - 18) < 10: continue          # keep the cavern roof thin enough for its skylights
    r = rng.uniform(2.2, 5.0); h = rng.uniform(1.5, 4.0)
    c = (x, yc, 6.2 + rng.uniform(-0.5, 1.0))
    SHAPES.append(("ell", (c, (r * rng.uniform(1.0, 1.5), r, h)), ((x - 9, yc - 9, 0), (x + 9, yc + 9, 14)), 1.6))
for k in range(16):
    x = rng.uniform(-82, 84); yc = np.interp(x, [c[0] for c in crest], [c[1] for c in crest])
    if abs(x + 32) < 14 or abs(x - 74) < 6: continue
    c = (x, yc - rng.uniform(8.5, 10.5), rng.uniform(4.5, 6.5))
    SHAPES.append(("ell", (c, (rng.uniform(3.0, 5.5), rng.uniform(2.0, 3.0), rng.uniform(0.9, 1.4))), ((c[0] - 7, c[1] - 6, c[2] - 3), (c[0] + 7, c[1] + 6, c[2] + 3)), 0.9))
# spurs on the seaward (-y) side, separated by sand grooves
for i, x in enumerate((-88, -66, -46, -14, 6, 24, 50, 88)):
    yc = np.interp(x, [c[0] for c in crest], [c[1] for c in crest])
    L = rng.uniform(18, 30); wig = rng.uniform(-5, 5)
    pts = [(x, yc - 6, 0.0), (x + wig * 0.5, yc - 6 - L * 0.45, -0.3), (x + wig, yc - 6 - L, -0.8)]
    rad = [rng.uniform(5.0, 6.5), rng.uniform(4.0, 5.5), rng.uniform(2.5, 3.5)]
    SHAPES.append(("chain", (pts, rad, rng.uniform(0.75, 0.95)), bb(pts, 8), 2.5))
# lagoon bommies: ellipsoid stacks, mushroom-topped ones overhang
BOM = [(-82, -48, 9.0, 1), (-50, -56, 7.0, 0), (-22, -44, 10.0, 1), (28, -52, 8.0, 0), (56, -40, 11.0, 1), (86, -56, 6.5, 0),
       (-4, -64, 5.0, 0), (72, -24, 6.0, 0), (-66, -26, 5.5, 0)]
for x, y, h, mush in BOM:
    # a bommie is a heap of coral heads: a broad foot, a leaning trunk of stacked lumps, and (some) an overhanging crown
    r0 = rng.uniform(5.0, 7.5); lean = rng.uniform(-0.25, 0.25, 2)
    for j in range(5):
        a = rng.uniform(0, math.tau); rr = rng.uniform(0.3, 0.8) * r0
        c = (x + math.cos(a) * rr, y + math.sin(a) * rr, rng.uniform(-1.0, 0.8))
        e = (r0 * rng.uniform(0.45, 0.75), r0 * rng.uniform(0.4, 0.7), rng.uniform(1.5, 3.0))
        SHAPES.append(("ell", (c, e), ((c[0] - 8, c[1] - 8, -6), (c[0] + 8, c[1] + 8, 6)), 1.2))
    nz_ = max(2, int(h / 2.2))
    for j in range(nz_):
        t = (j + 0.5) / nz_; z = h * t * 0.9
        c = (x + lean[0] * z + rng.uniform(-0.8, 0.8), y + lean[1] * z + rng.uniform(-0.8, 0.8), z)
        w = r0 * (0.75 - 0.3 * t) * rng.uniform(0.75, 1.1)
        SHAPES.append(("ell", (c, (w * rng.uniform(0.8, 1.2), w * rng.uniform(0.8, 1.2), rng.uniform(1.4, 2.2))), ((c[0] - 9, c[1] - 9, z - 4), (c[0] + 9, c[1] + 9, z + 4)), 1.0))
    top = (x + lean[0] * h, y + lean[1] * h, h * 0.92)
    if mush:   # crown: a ring of plates wider than the trunk, undercut beneath
        for j in range(6):
            a = j / 6 * math.tau + rng.uniform(-0.3, 0.3); rr = r0 * rng.uniform(0.35, 0.75)
            c = (top[0] + math.cos(a) * rr, top[1] + math.sin(a) * rr, top[2] + rng.uniform(-0.8, 0.6))
            SHAPES.append(("ell", (c, (r0 * rng.uniform(0.45, 0.65), r0 * rng.uniform(0.4, 0.6), rng.uniform(0.9, 1.5))), ((c[0] - 8, c[1] - 8, c[2] - 3), (c[0] + 8, c[1] + 8, c[2] + 3)), 0.7))
    META["bommies"].append([x, y, h])
# arches: a half-torus standing on the sand (lower half buried); tube radius varies along the span
def arch(c, R, r, yaw):
    pts = []; rad = []
    for k in range(13):
        a = math.pi * k / 12
        px, pz = math.cos(a) * R, math.sin(a) * R
        pts.append((c[0] + px * math.cos(yaw), c[1] + px * math.sin(yaw), c[2] + pz)); rad.append(r * (1.25 - 0.35 * math.sin(a)))
    pts = [(pts[0][0], pts[0][1], c[2] - 3)] + pts + [(pts[-1][0], pts[-1][1], c[2] - 3)]
    rad = [r * 1.5] + rad + [r * 1.5]
    SHAPES.append(("chain", (pts, rad, 1.0), bb(pts, r * 2 + 2), 1.5))
    for p_ in pts[1:-1:2]:                                           # encrusting heads along the span
        c = (p_[0] + rng.uniform(-1, 1), p_[1] + rng.uniform(-1, 1), p_[2] + rng.uniform(0.3, 1.2))
        e = r * rng.uniform(0.5, 0.8)
        SHAPES.append(("ell", (c, (e * 1.3, e, e * 0.8)), ((c[0] - 6, c[1] - 6, c[2] - 5), (c[0] + 6, c[1] + 6, c[2] + 5)), 0.8))
    META["arches"].append({"c": list(c), "R": R, "r": r, "yaw": yaw})
arch((4, -30, -0.6), 8.5, 2.6, math.radians(15))
arch((-60, -33, -0.4), 5.6, 2.1, math.radians(-30))
# rubble: dead coral heads and broken blocks around the bases
for k in range(90):
    x, y = rng.uniform(X0 + 6, X1 - 6), rng.uniform(Y0 + 6, 30)
    r = rng.uniform(0.7, 1.9)
    SHAPES.append(("ell", ((x, y, rng.uniform(-0.6, 0.1)), (r * rng.uniform(1, 1.6), r, r * rng.uniform(0.5, 0.8))), ((x - 4, y - 4, -3), (x + 4, y + 4, 3)), 0.8))

# ---- cuts: the skylit cavern and its two swim-throughs (west), a winding tunnel (east), a slot canyon (far east)
CAV = (-32.0, 18.0, 2.6)
CUTS.append(("ell", (CAV, (10.5, 8.0, 4.4)), 1.5))
META["cavern"] = {"c": CAV, "r": [10.5, 8.0, 4.4]}
tA = [(-29, -8, 2.2), (-30, 2, 2.4), (-31, 10, 2.6)]
tB = [(-35, 25, 2.6), (-38, 33, 2.4), (-41, 44, 2.0)]
for t in (tA, tB):
    CUTS.append(("chain", (t, [3.4, 2.5, 2.7], 0.85), 1.0)); META["tunnels"].append(t)
for (sx, sy, sr) in ((-29.0, 15.0, 1.8), (-36.5, 21.0, 1.3), (-26.0, 21.5, 1.0)):
    CUTS.append(("chain", ([(sx, sy, CAV[2]), (sx + 0.4, sy + 0.2, 16.0)], [sr, sr * 1.25], 1.0), 0.6)); META["skylights"].append([sx, sy, sr])
tC = [(37, -10, 2.0), (39, 1, 2.4), (36, 10, 2.8), (40, 19, 2.6), (43, 30, 2.2), (41, 40, 1.8)]
CUTS.append(("chain", (tC, [3.4, 2.4, 2.8, 2.6, 2.4, 3.3], 0.9), 1.0)); META["tunnels"].append(tC)
CUTS.append(("chain", ([(37.5, 13.5, 3.0), (37.8, 13.8, 16.0)], [1.2, 1.6], 1.0), 0.6)); META["skylights"].append([37.5, 13.5, 1.2])
# slot canyon: a narrow vertical gorge through the crest
SLOT = [(74, -8), (72, 2), (75, 11), (73, 20), (76, 30), (74, 40)]
CUTS.append(("slot", (SLOT, 2.0, 0.6), 0.7)); META["slot"] = SLOT
# a tunnel through the tallest bommie
bx, by, bh, _ = BOM[2]
tD = [(bx - 12, by - 2, 2.4), (bx, by + 0.5, 2.8), (bx + 12, by + 3, 2.4)]
CUTS.append(("chain", (tD, [3.0, 2.6, 3.0], 0.9), 1.0)); META["tunnels"].append(tD)

def eval_kind(kind, args, P):
    if kind == "chain": return capsule_chain(P, *args)
    if kind == "ell": return ellipsoid(P, *args)
    if kind == "slot": return slot_sdf(P, *args)
    raise ValueError(kind)

def lump_pass():
    g = 1.5
    gx, gy, gz = np.arange(X0, X1, g), np.arange(Y0, Y1, g), np.arange(-2, Z1, g)
    Xg, Yg, Zg = np.meshgrid(gx, gy, gz, indexing="ij"); P = np.stack([Xg, Yg, Zg], -1)
    d = np.full(Xg.shape, 50.0)
    for kind, args, (bmin, bmax), k in SHAPES: d = smin(d, eval_kind(kind, args, P), k)
    cand = P[(np.abs(d) < 0.9)]
    pick = cand[rng.choice(len(cand), size=min(len(cand), 700), replace=False)]
    for c in pick:
        r = rng.uniform(0.8, 2.6) * (1.0 if c[2] > 1 else 0.7)
        e = (r * rng.uniform(0.8, 1.5), r * rng.uniform(0.8, 1.5), r * rng.uniform(0.45, 0.9))
        c = tuple(c + rng.uniform(-0.5, 0.5, 3))
        SHAPES.append(("ell", (c, e), ((c[0] - 5, c[1] - 5, c[2] - 4), (c[0] + 5, c[1] + 5, c[2] + 4)), 0.55))
    return len(pick)

def slot_sdf(P, pts, w, zfloor):
    ys = np.array([p[1] for p in pts]); xs = np.array([p[0] for p in pts])
    xc = np.interp(P[..., 1], ys, xs)
    d = np.abs(P[..., 0] - xc) - w * (1 + 0.25 * np.sin(P[..., 2] * 0.9 + P[..., 1] * 0.3))
    d = np.maximum(d, zfloor - P[..., 2])
    d = np.maximum(d, np.maximum(ys.min() - P[..., 1], P[..., 1] - ys.max()))
    return d

META["lumps"] = lump_pass()

# ------------------------------------------------------------------ field evaluation in slabs of x
nx = int(round((X1 - X0) / VOX)) + 1; ny = int(round((Y1 - Y0) / VOX)) + 1; nz = int(round((Z1 - Z0) / VOX)) + 1
xs = np.linspace(X0, X1, nx); ys = np.linspace(Y0, Y1, ny); zs = np.linspace(Z0, Z1, nz)
F = np.empty((nx, ny, nz), np.float32)
SL = 40
for i0 in range(0, nx, SL):
    i1 = min(nx, i0 + SL)
    Xg, Yg, Zg = np.meshgrid(xs[i0:i1], ys, zs, indexing="ij")
    P0 = np.stack([Xg, Yg, Zg], -1)
    W = 2.2                                                          # domain warp: bends every shape organically
    P = P0 + np.stack([fbm(Xg, Yg, Zg, 0.06, 2, off=41.0), fbm(Xg, Yg, Zg, 0.06, 2, off=57.0), 0.5 * fbm(Xg, Yg, Zg, 0.06, 2, off=73.0)], -1) * W
    d = np.full(Xg.shape, 50.0)
    lo = np.array([xs[i0], Y0, Z0]); hi = np.array([xs[i1 - 1], Y1, Z1])
    for kind, args, (bmin, bmax), k in SHAPES:
        if (bmax < lo).any() or (bmin > hi).any(): continue
        # restrict to the bbox for speed
        ia = np.searchsorted(ys, bmin[1]); ib = np.searchsorted(ys, bmax[1]) + 1
        ka = np.searchsorted(zs, bmin[2]); kb = np.searchsorted(zs, bmax[2]) + 1
        xa = max(0, np.searchsorted(xs[i0:i1], bmin[0])); xb = min(i1 - i0, np.searchsorted(xs[i0:i1], bmax[0]) + 1)
        if xa >= xb or ia >= ib or ka >= kb: continue
        sub = P[xa:xb, ia:ib, ka:kb]
        d[xa:xb, ia:ib, ka:kb] = smin(d[xa:xb, ia:ib, ka:kb], eval_kind(kind, args, sub), k)
    X, Y, Z = Xg, Yg, Zg
    # rock: big lumps, coral-head knobs, and a fine pitted layer
    n1 = fbm(X, Y, Z, 0.07, 3)
    n2 = fbm(X, Y, Z, 0.33, 3, off=11.0)
    n3 = np.abs(fbm(X, Y, Z, 1.1, 2, off=5.0))
    n0 = fbm(X, Y, Z * 0.6, 0.035, 2, off=3.0)
    crev = np.abs(fbm(X, Y, Z * 1.6, 0.16, 2, off=91.0))
    d = d + n0 * 2.4 + n1 * 1.4 + n2 * 0.6 - (0.25 - n3) * 0.35 + 0.9 * np.exp(-(crev / 0.06) ** 2)   # crevices along ridge lines
    # flatten the sea floor contact: rock spreads a little at its foot (no knife edges on the sand)
    d = d - np.clip(0.8 - Z, 0, 2) * 0.25
    # cuts (light noise of their own so tunnels keep their size)
    cn = fbm(X, Y, Z, 0.4, 2, off=23.0) * 0.7
    for kind, args, k in CUTS:
        c = eval_kind(kind, args, P0) + cn
        d = smax(d, -c, k)
    d = np.maximum(d, -(Z + 4.0))                      # flat underside at z = -4
    d = np.maximum(d, -(np.minimum(np.minimum(X - X0, X1 - X), np.minimum(Y - Y0, Y1 - Y))) + 0.5)   # closed at the domain edge
    F[i0:i1] = d
    print("slab", i0, "/", nx, flush=True)

verts, faces, normals, _ = marching_cubes(F, level=0.0, spacing=(VOX, VOX, VOX))
verts += np.array([X0, Y0, Z0])
# marching cubes gives outward normals pointing to increasing field = outside; make faces wind outward for Blender
faces = faces[:, ::-1]
os.makedirs(OUT, exist_ok=True)
np.savez_compressed(os.path.join(OUT, "reef_high.npz"), verts=verts.astype(np.float32), faces=faces.astype(np.int32))
META["counts"] = {"verts": int(len(verts)), "faces": int(len(faces))}
META["voxel"] = VOX
json.dump(META, open(os.path.join(OUT, "reef_meta.json"), "w"), indent=1)
print(META["counts"])
