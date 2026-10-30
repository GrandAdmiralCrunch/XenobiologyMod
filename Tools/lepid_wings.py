"""Xenobiology — butterfly wing painter.
Defines each butterfly's wing outlines (forewing + hindwing, in wing units: x = span outward, y = forward, the wing base at 0,0)
and paints an ornate 2048 atlas: forewing top | hindwing top / forewing underside | hindwing underside, with veins,
margins, fringes, eyespots and bands laid out between the veins. Writes <out_dir>/<name>_wings.png and
<name>_wings.json (outlines, veins, atlas cells). Use XenobiologyDev/lepid (outside GameData!): the Blender builder
(arch "lepid" in fauna_kerbin3.py) reads both from there.
Usage:  python lepid_wings.py <out_dir> [species ...]          needs numpy, scipy, Pillow
"""
import sys, os, json, math
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter

CELL = 1024
rng = np.random.default_rng(5)

# ------------------------------------------------------------------ outlines
def catmull(pts, n=240, closed=True):
    P = np.array(pts, float); m = len(P); out = []
    for i in range(m):
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        for k in range(n // m):
            t = k / (n // m)
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)

def scallop(poly, depth, n, lo, hi):
    """Wavy margin on the outline points between fractions lo..hi of the loop (toward the wing's inside)."""
    P = poly.copy(); m = len(P); c = P.mean(0)
    for i in range(m):
        f = i / m
        if lo <= f <= hi:
            u = (f - lo) / (hi - lo)
            d = P[i] - c; d /= np.linalg.norm(d) + 1e-9
            P[i] -= d * depth * (0.5 - 0.5 * math.cos(u * n * 2 * math.pi)) * math.sin(math.pi * u) ** 0.3
    return P

SPECS = {
    # ---------------- Sunwing Butterfly: monarch-like orange, black veins, black borders with two rows of white dots
    "butterfly": dict(
        fore=[(0.0, 0.0), (0.22, 0.09), (0.52, 0.16), (0.82, 0.19), (0.99, 0.15), (1.0, 0.04), (0.94, -0.14), (0.83, -0.31), (0.68, -0.43),
              (0.45, -0.41), (0.2, -0.27), (0.04, -0.09)],
        hind=[(0.0, 0.0), (0.3, 0.05), (0.56, 0.0), (0.7, -0.16), (0.71, -0.36), (0.61, -0.56), (0.43, -0.68), (0.22, -0.66), (0.08, -0.46), (0.0, -0.2)],
        style="monarch"),
    # ---------------- Peacock Eyewing: rust red, a huge eyespot on every wing, scalloped margins, a bark-dark underside
    "peacock": dict(
        fore=[(0.0, 0.0), (0.24, 0.1), (0.55, 0.16), (0.86, 0.17), (1.0, 0.1), (0.97, -0.02), (0.9, -0.08), (0.92, -0.2), (0.84, -0.33), (0.7, -0.43),
              (0.46, -0.42), (0.2, -0.28), (0.04, -0.09)],
        hind=[(0.0, 0.0), (0.32, 0.05), (0.6, -0.02), (0.74, -0.2), (0.72, -0.4), (0.62, -0.58), (0.44, -0.7), (0.24, -0.68), (0.08, -0.48), (0.0, -0.2)],
        scallop=(0.012, 9, 0.38, 0.72), hscallop=(0.016, 8, 0.25, 0.75), style="peacock"),
    # ---------------- Jewel Swallowtail: black, an emerald-gold band, blue lunules, a red eyespot and long spatulate tails
    "swallowtail": dict(
        fore=[(0.0, 0.0), (0.22, 0.08), (0.52, 0.14), (0.84, 0.15), (1.02, 0.09), (0.98, -0.06), (0.88, -0.22), (0.76, -0.36), (0.62, -0.44),
              (0.42, -0.41), (0.18, -0.26), (0.04, -0.08)],
        hind=[(0.0, 0.0), (0.3, 0.04), (0.55, -0.02), (0.68, -0.2), (0.68, -0.38), (0.62, -0.52), (0.6, -0.62), (0.63, -0.92), (0.58, -1.06),
              (0.52, -1.0), (0.52, -0.7), (0.42, -0.72), (0.3, -0.7), (0.16, -0.62), (0.06, -0.42), (0.0, -0.18)],
        hscallop=(0.01, 6, 0.3, 0.55), style="swallowtail"),
}

# venation templates: (start, end) in wing units; ends snap to the outline. Hub = where veins fan out (end of the discal cell).
FORE_VEINS = [((0.04, 0.03), (0.55, 0.2)), ((0.48, 0.06), (0.74, 0.2)), ((0.5, 0.05), (0.9, 0.2)), ((0.5, 0.05), (1.0, 0.12)),
              ((0.5, 0.03), (1.0, 0.0)), ((0.48, -0.02), (0.96, -0.12)), ((0.46, -0.07), (0.9, -0.24)), ((0.44, -0.11), (0.82, -0.34)),
              ((0.36, -0.12), (0.72, -0.42)), ((0.26, -0.11), (0.6, -0.45)), ((0.03, -0.05), (0.45, -0.44))]
FORE_CELL = [(0.05, 0.02), (0.5, 0.06), (0.44, -0.12), (0.06, -0.04)]
FORE_HUB = (0.45, -0.03)
HIND_VEINS = [((0.04, 0.03), (0.4, 0.06)), ((0.3, -0.12), (0.6, -0.02)), ((0.33, -0.17), (0.72, -0.2)), ((0.33, -0.22), (0.72, -0.37)),
              ((0.3, -0.28), (0.65, -0.52)), ((0.26, -0.3), (0.55, -0.66)), ((0.18, -0.29), (0.42, -0.72)), ((0.04, -0.06), (0.24, -0.7)),
              ((0.02, -0.08), (0.07, -0.48))]
HIND_CELL = [(0.04, 0.0), (0.33, -0.14), (0.31, -0.29), (0.05, -0.1)]
HIND_HUB = (0.26, -0.22)

# ------------------------------------------------------------------ geometry helpers on a pixel grid
class Wing:
    def __init__(self, outline, veins, cell, hub, box):
        self.poly = outline; self.hub = np.array(hub)
        x0, y0, x1, y1 = box; s = max(x1 - x0, y1 - y0); self.x0, self.y1 = x0, y0 + s; self.sc = CELL / s
        self.box = (x0, y0, x0 + s, y0 + s)
        jj, ii = np.meshgrid(np.arange(CELL), np.arange(CELL))
        self.X = self.x0 + (jj + 0.5) / self.sc; self.Y = self.y1 - (ii + 0.5) / self.sc
        from matplotlib.path import Path
        self.mask = Path(outline).contains_points(np.c_[self.X.ravel(), self.Y.ravel()]).reshape(CELL, CELL)
        self.dm = distance_transform_edt(self.mask) / self.sc                         # distance to the edge, wing units
        # veins: snap the ends to the outline
        self.veins = []
        for a, b in veins:
            b = np.array(b); k = np.argmin(((outline - b) ** 2).sum(1)); self.veins.append((np.array(a), outline[k]))
        self.cell = np.array(cell)
        self.dv = np.full((CELL, CELL), 9.0); self.vid = np.zeros((CELL, CELL), int)
        segs = list(self.veins) + [(self.cell[i], self.cell[(i + 1) % len(self.cell)]) for i in range(len(self.cell))]
        for n, (a, b) in enumerate(segs):
            d = b - a; L2 = (d ** 2).sum()
            t = np.clip(((self.X - a[0]) * d[0] + (self.Y - a[1]) * d[1]) / L2, 0, 1)
            dist = np.hypot(self.X - (a[0] + d[0] * t), self.Y - (a[1] + d[1] * t))
            sel = dist < self.dv; self.dv[sel] = dist[sel]; self.vid[sel] = n
        # polar coordinates about the hub: angle -> interspace index and fraction, radius -> fraction of the way to the margin
        ang = np.arctan2(self.Y - hub[1], self.X - hub[0])
        ve = np.array([math.atan2(b[1] - hub[1], b[0] - hub[0]) for a, b in self.veins])
        order = np.argsort(ve)[::-1]; self.ve = ve[order]                              # from the leading edge round to the trailing edge
        self.ang = ang
        self.space = np.zeros((CELL, CELL), int); self.sfrac = np.zeros((CELL, CELL))
        for i in range(len(self.ve) - 1):
            a1, a2 = self.ve[i], self.ve[i + 1]
            sel = (ang <= a1) & (ang > a2); self.space[sel] = i; self.sfrac[sel] = (a1 - ang[sel]) / (a1 - a2)
        oa = np.arctan2(outline[:, 1] - hub[1], outline[:, 0] - hub[0]); orr = np.hypot(outline[:, 0] - hub[0], outline[:, 1] - hub[1])
        bins = np.linspace(-math.pi, math.pi, 721); rmax = np.zeros(720)
        idx = np.clip(np.digitize(oa, bins) - 1, 0, 719)
        for i, r in zip(idx, orr): rmax[i] = max(rmax[i], r)
        for i in range(720):
            if rmax[i] == 0: rmax[i] = rmax[i - 1]
        rmax = gaussian_filter(np.r_[rmax, rmax, rmax], 2)[720:1440]
        self.R = np.hypot(self.X - hub[0], self.Y - hub[1]) / np.maximum(1e-3, rmax[np.clip(((ang + math.pi) / (2 * math.pi) * 720).astype(int), 0, 719)])
        self.nspace = len(self.ve) - 1
        self.B = np.hypot(self.X, self.Y) / np.hypot(outline[:, 0], outline[:, 1]).max()     # 0 at the wing root, 1 at the furthest tip
    def space_point(self, i, sub, r):
        a = self.ve[i] + (self.ve[i + 1] - self.ve[i]) * sub
        hits = [(abs(math.atan2(p[1] - self.hub[1], p[0] - self.hub[0]) - a), p) for p in self.poly]
        m = min(hits, key=lambda h: h[0])[1]
        return self.hub + (m - self.hub) * r
    def space_centre(self, i, r):
        """Point in interspace i at radial fraction r."""
        a = (self.ve[i] + self.ve[i + 1]) / 2
        hits = [(abs(math.atan2(p[1] - self.hub[1], p[0] - self.hub[0]) - a), p) for p in self.poly]
        m = min(hits, key=lambda h: h[0])[1]
        return self.hub + (m - self.hub) * r

def ss(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def put(img, col, a):
    a = np.clip(a, 0, 1)[..., None]; img[:] = img * (1 - a) + np.array(col, float) * a
def disk(W, c, r, soft=0.004): return 1 - ss(r - soft, r + soft, np.hypot(W.X - c[0], W.Y - c[1]))
def ell(W, c, rx, ry, rot=0.0, soft=0.004):
    dx, dy = W.X - c[0], W.Y - c[1]; cr, sr = math.cos(rot), math.sin(rot)
    u = (dx * cr + dy * sr) / rx; v = (-dx * sr + dy * cr) / ry
    return 1 - ss(1 - soft / min(rx, ry), 1 + soft / min(rx, ry), np.hypot(u, v))
def scales(W, amt=0.06):                                     # scale-tile shimmer: fine noise aligned with the veins
    n = gaussian_filter(rng.standard_normal((CELL, CELL)), 1.2); return 1 + amt * n / (n.std() + 1e-6)
def veins(W, img, col, w, wmargin=None):
    put(img, col, 1 - ss(w * 0.6, w * 1.2, W.dv))
def fringe(W, img, a, b, w=0.008):                             # chequered fringe of hair-scales on the margin
    chk = (np.floor((W.ang + math.pi) * 60) % 2)[..., None]
    col = np.where(chk > 0, np.array(a, float), np.array(b, float))
    m = ((W.dm < w) & W.mask)[..., None] * 1.0; img[:] = img * (1 - m) + col * m
def eyespot(W, img, c, rings, rot=0.0, aspect=1.0):
    for r, col in rings: put(img, col, ell(W, c, r, r * aspect, rot))

# ------------------------------------------------------------------ styles
def monarch(W, hind, under):
    o = np.array((0.97, 0.52, 0.08)); img = np.zeros((CELL, CELL, 3)) + o
    if under: img[:] = np.array((0.93, 0.62, 0.22)) if not hind else np.array((0.9, 0.74, 0.42))
    put(img, (1.0, 0.68, 0.22), ss(0.35, 0.0, W.B) * 0.5)                        # paler towards the base
    img *= scales(W)[..., None]
    if under:                                                                   # pale-edged veins underneath
        put(img, (0.96, 0.92, 0.82), 1 - ss(0.008, 0.014, W.dv))
    veins(W, img, (0.04, 0.03, 0.03), 0.011 if not hind else 0.013)
    put(img, (0.05, 0.04, 0.04), ss(0.09, 0.075, W.dm))                         # black border
    put(img, (0.05, 0.04, 0.04), ss(0.03, 0.015, W.dv) * ss(0.25, 0.4, W.R) * 0)
    for i in range(W.nspace):                                                   # two rows of white dots in the border, one pair per interspace
        for r, rr in ((0.955, 0.018), (0.905, 0.014)):
            for sub in ((0.3, 0.7) if r > 0.93 else (0.5,)):
                put(img, (0.97, 0.95, 0.9), disk(W, W.space_point(i, sub, r), rr) * W.mask)
    if not hind:                                                                # black apex with a subapical band of pale spots
        apex = ss(0.18, 0.08, np.hypot(W.X - 0.95, W.Y - 0.13)) ; put(img, (0.05, 0.04, 0.04), ss(0.0, 0.3, apex))
        put(img, (0.05, 0.04, 0.04), ss(0.06, 0.03, W.Y - 0.13 + 0.0) * ss(0.3, 0.5, W.X) * 0)
        for k, (x, y, r) in enumerate(((0.72, 0.1, 0.03), (0.78, 0.07, 0.028), (0.84, 0.035, 0.026), (0.87, -0.0, 0.022), (0.66, 0.135, 0.022))):
            put(img, (1.0, 0.93, 0.8) if k < 3 else (1.0, 0.72, 0.3), disk(W, (x, y), r) * W.mask)
        put(img, (0.05, 0.04, 0.04), ss(0.03, 0.02, W.dm) * 1.0)
    else:
        put(img, (0.05, 0.04, 0.04), ss(0.025, 0.012, np.abs(W.X - 0.0) + 0 * W.Y) * 0)
        put(img, (0.12, 0.08, 0.05), ss(0.22, 0.0, W.B) * 0.6)                  # dusky hairy base
    fringe(W, img, (0.96, 0.95, 0.9), (0.06, 0.05, 0.05))
    return img

def peacock(W, hind, under):
    img = np.zeros((CELL, CELL, 3))
    if under:                                                                   # cryptic: near-black with fine bark striations
        img[:] = (0.13, 0.1, 0.09)
        stri = np.sin((W.X * 0.3 + W.Y) * 260 + gaussian_filter(rng.standard_normal((CELL, CELL)), 6) * 40)
        put(img, (0.28, 0.22, 0.18), (stri > 0.6) * 0.6)
        put(img, (0.06, 0.05, 0.05), ss(0.5, 0.1, W.B) * 0.5)
        put(img, (0.36, 0.3, 0.25), ss(0.05, 0.0, np.abs(W.R - 0.62) - 0.04) * 0.7)       # a paler median band
        put(img, (0.32, 0.27, 0.22), ss(0.05, 0.02, W.dm) * 0.6)
        img *= scales(W, 0.1)[..., None]
        veins(W, img, (0.08, 0.06, 0.05), 0.006)
        fringe(W, img, (0.4, 0.34, 0.28), (0.1, 0.08, 0.07), 0.006)
        return img
    img[:] = (0.68, 0.11, 0.06)
    put(img, (0.45, 0.06, 0.04), ss(0.45, 0.05, W.B) * 0.7)                      # deeper red, then brown, towards the body
    put(img, (0.18, 0.08, 0.06), ss(0.25, 0.0, W.B) * 0.85)
    img *= scales(W, 0.07)[..., None]
    veins(W, img, (0.4, 0.07, 0.04), 0.006)
    put(img, (0.25, 0.12, 0.08), ss(0.07, 0.04, W.dm))                          # brown scalloped border
    if not hind:
        for k in range(5):                                                      # black and cream blocks along the costa
            x = 0.25 + k * 0.11; put(img, (0.05, 0.04, 0.04) if k % 2 == 0 else (0.95, 0.85, 0.55), ell(W, (x, 0.14 - 0.01 * k), 0.045, 0.035) * W.mask * ss(0.06, 0.0, W.dm + 0.0) * 0 + ell(W, (x, 0.15 - 0.008 * k), 0.045, 0.05) * W.mask)
        c = (0.82, 0.03)                                                        # the apical eye
        eyespot(W, img, c, [(0.17, (0.96, 0.86, 0.55)), (0.135, (0.35, 0.1, 0.08)), (0.12, (0.06, 0.04, 0.05)), (0.09, (0.25, 0.32, 0.72)),
                            (0.065, (0.08, 0.06, 0.1)), (0.04, (0.55, 0.62, 0.95))], rot=-0.5, aspect=0.8)
        for d in ((0.03, 0.04), (-0.02, -0.03), (0.05, -0.02)): put(img, (0.95, 0.95, 1.0), disk(W, (c[0] + d[0], c[1] + d[1]), 0.012))
        put(img, (0.05, 0.04, 0.04), ell(W, (0.55, -0.05), 0.06, 0.035, 0.5))   # dark discal bars
        put(img, (0.05, 0.04, 0.04), ell(W, (0.38, -0.0), 0.05, 0.03, 0.4))
    else:
        c = (0.5, -0.36)
        eyespot(W, img, c, [(0.2, (0.58, 0.55, 0.5)), (0.17, (0.06, 0.04, 0.05)), (0.135, (0.08, 0.1, 0.28)), (0.11, (0.2, 0.36, 0.85)),
                            (0.075, (0.06, 0.05, 0.1)), (0.045, (0.35, 0.55, 1.0))], rot=0.4, aspect=0.85)
        for d in ((0.04, 0.03), (-0.03, 0.05), (0.0, -0.05)): put(img, (0.9, 0.95, 1.0), disk(W, (c[0] + d[0], c[1] + d[1]), 0.013))
        put(img, (0.15, 0.08, 0.06), ss(0.3, 0.0, W.B) * 0.75)
    fringe(W, img, (0.55, 0.45, 0.35), (0.12, 0.08, 0.06), 0.007)
    return img

def swallowtail(W, hind, under):
    img = np.zeros((CELL, CELL, 3)) + np.array((0.035, 0.035, 0.045))
    img *= scales(W, 0.15)[..., None]
    if not under:
        sheen = np.clip(0.5 + 0.5 * np.sin(W.X * 9 + W.Y * 4), 0, 1)[..., None]
        band = (np.array((0.25, 0.85, 0.45)) * (1 - sheen) + np.array((0.95, 0.85, 0.25)) * sheen)
    else:
        band = np.zeros((CELL, CELL, 3)) + np.array((0.92, 0.86, 0.6))
    if not hind:
        b = ss(0.075, 0.045, np.abs(((W.X - 0.66) * (-0.44 - 0.16) - (W.Y - 0.16) * (0.44 - 0.66)) / 0.6391)) * (W.dv > 0.007)       # diagonal band across the forewing
        a = b[..., None]; img[:] = img * (1 - a) + band * a
        for i in range(1, W.nspace):                                                             # submarginal pale spots
            c = W.space_centre(i, 0.86); put(img, (0.95, 0.9, 0.6) if not under else (0.95, 0.85, 0.55), disk(W, c, 0.017))
        put(img, (0.6, 0.65, 0.7), ss(0.2, 0.0, W.B) * 0.15)
    else:
        b = ss(0.085, 0.05, np.abs(((W.X - 0.46) * (-0.66 - 0.05) - (W.Y - 0.05) * (0.2 - 0.46)) / 0.7561)) * (W.dv > 0.007)                  # the band continues across the hindwing
        a = b[..., None]; img[:] = img * (1 - a) + band * a
        for i in range(W.nspace):                                                                # blue lunules (or orange spots underneath)
            c = W.space_centre(i, 0.8)
            col = (0.2, 0.45, 1.0) if not under else (0.95, 0.35, 0.12)
            put(img, col, ell(W, c, 0.035, 0.018, math.atan2(c[1] - W.hub[1], c[0] - W.hub[0]) + math.pi / 2) * (W.Y > -0.75))
        c = (0.36, -0.62)                                                                        # red eye at the anal angle
        eyespot(W, img, c, [(0.055, (0.9, 0.18, 0.08)), (0.03, (0.05, 0.03, 0.04)), (0.014, (0.35, 0.55, 1.0))])
        put(img, (0.95, 0.85, 0.4), ss(0.02, 0.01, W.dm) * (W.Y < -0.85))                        # pale-edged tail tip
    veins(W, img, (0.02, 0.02, 0.025), 0.007)
    fringe(W, img, (0.9, 0.85, 0.6), (0.03, 0.03, 0.04), 0.006)
    return img

STYLES = {"monarch": monarch, "peacock": peacock, "swallowtail": swallowtail}

def build(name, out_dir):
    sp = SPECS[name]
    fo = catmull(sp["fore"]); ho = catmull(sp["hind"], n=320)
    if sp.get("scallop"): fo = scallop(fo, *sp["scallop"])
    if sp.get("hscallop"): ho = scallop(ho, *sp["hscallop"])
    fb = (fo[:, 0].min() - 0.03, fo[:, 1].min() - 0.03, fo[:, 0].max() + 0.03, fo[:, 1].max() + 0.03)
    hb = (ho[:, 0].min() - 0.03, ho[:, 1].min() - 0.03, ho[:, 0].max() + 0.03, ho[:, 1].max() + 0.03)
    FW = Wing(fo, FORE_VEINS, FORE_CELL, FORE_HUB, fb); HW = Wing(ho, HIND_VEINS, HIND_CELL, HIND_HUB, hb)
    atlas = np.zeros((2 * CELL, 2 * CELL, 3))
    style = STYLES[sp["style"]]
    for (W, hind, under, r0, c0) in ((FW, False, False, 0, 0), (HW, True, False, 0, CELL), (FW, False, True, CELL, 0), (HW, True, True, CELL, CELL)):
        img = style(W, hind, under)
        m = gaussian_filter(W.mask.astype(float), 0.7)[..., None]
        bg = img.copy()                                  # bleed the colour past the edge so the bake never samples black
        atlas[r0:r0 + CELL, c0:c0 + CELL] = img * m + gaussian_filter(bg, (8, 8, 0)) * (1 - m)
    os.makedirs(out_dir, exist_ok=True)
    Image.fromarray((np.clip(atlas, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out_dir, name + "_wings.png"))
    js = {"fore": fo[::2].round(4).tolist(), "hind": ho[::2].round(4).tolist(), "foreBox": FW.box, "hindBox": HW.box,
          "cells": {"fore_top": [0, 0], "hind_top": [1, 0], "fore_under": [0, 1], "hind_under": [1, 1]}, "size": 2 * CELL}
    json.dump(js, open(os.path.join(out_dir, name + "_wings.json"), "w"))
    return js

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for n in (sys.argv[2:] or list(SPECS)):
        build(n, out); print("painted", n)
