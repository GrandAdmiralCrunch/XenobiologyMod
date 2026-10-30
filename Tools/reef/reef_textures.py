"""Xenobiology — coral reef textures (procedural, numpy + PIL).
coral_atlas.png (2048 x 4096, 4x8 cells of 512) + coral_atlas_glow.png (512 x 1024): every coral's UVs land in one cell
(layout in reef_coral_lib.py's docstring):
    row 0: cup orange (column+crown) | cup glow (column+crown) | fire coral ochre | fire coral olive
    row 1: leather cap cream (polar) | leather stalk | leather cap olive (polar) | elkhorn
    row 2: zoanthid column | zoanthid disc green (polar) | zoanthid disc magenta (polar) | zoanthid disc orange/teal (polar)
    row 3: cup crown orange (polar) | cup crown teal (polar) | rock contact | finger leather
    rows 4-7: brain, table, staghorn, pillar, anemone, barrel and tube sponges (see reef_coral_lib.py)
Cylindrical cells: u = around, v = along (0 base, 1 tip). Polar cells: centre = middle of cell, radius 0.5 = rim.
seafan.png (1024 RGBA, 2x2 fans: purple, red, yellow, lilac) for the KSP/Alpha/Cutoff fans.
reef_shaft.png (128x256): additive sun-shaft gradient.
Usage: python reef_textures.py <out_dir>
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(77)
C = 512

def grid(n=C):
    v, u = np.mgrid[0:n, 0:n] / (n - 1.0)
    return u, 1.0 - v          # v = 0 at the bottom of the cell
def polar(n=C):
    u, v = grid(n); x, y = u - 0.5, v - 0.5
    return np.hypot(x, y) / 0.5, (np.arctan2(y, x) / math.tau) % 1.0
def vnoise(n, scale, seed, oct_=4):
    """tileable-ish value noise (bicubic upsampled random grids)"""
    r = np.random.default_rng(seed); acc = np.zeros((n, n)); a = 1.0; tot = 0
    for o in range(oct_):
        g = max(2, int(scale * 2 ** o))
        im = Image.fromarray((r.random((g, g)) * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
        acc += a * (np.asarray(im) / 255.0); tot += a; a *= 0.5
    return acc / tot
def dots(n, count, rmin, rmax, seed, polar_mask=None):
    im = Image.new("L", (n, n), 0); d = ImageDraw.Draw(im); r = np.random.default_rng(seed)
    for _ in range(count):
        x, y = r.random() * n, r.random() * n; rr = r.uniform(rmin, rmax)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.8))) / 255.0
def col(c): return np.array(c, float)[None, None, :]
def lerp(a, b, t): t = np.clip(t, 0, 1)[..., None]; return a * (1 - t) + b * t
def sstep(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

ROWS = 8
D = np.zeros((ROWS * C, 4 * C, 3)); GL = np.zeros((ROWS * C, 4 * C, 3))
def put(cx, cy, rgb, glow=None):
    y0 = (ROWS - 1 - cy) * C        # row 0 at the bottom of the image (v up)
    D[y0:y0 + C, cx * C:(cx + 1) * C] = np.clip(rgb, 0, 1)
    if glow is not None: GL[y0:y0 + C, cx * C:(cx + 1) * C] = np.clip(glow, 0, 1)

u, v = grid(); n1 = vnoise(C, 6, 1); n2 = vnoise(C, 24, 2)
# ---- cup corals (Tubastraea): ribbed column, crown of tentacles at the top
def cup(base, crown, glowc, seed):
    rib = 0.5 + 0.5 * np.cos(u * math.tau * 12)
    c = lerp(col(base) * 0.75, col(base), rib * 0.6 + n1 * 0.4)
    tent = 0.5 + 0.5 * np.cos(u * math.tau * 18 + v * 3)
    c = lerp(c, lerp(col(crown) * 0.8, col(crown), tent), sstep(0.68, 0.78, v))
    g = col(glowc) * (sstep(0.7, 0.85, v) * (0.55 + 0.45 * tent))[..., None]
    return c, g
c, g = cup((0.78, 0.30, 0.10), (1.0, 0.72, 0.18), (0.55, 0.32, 0.05), 3); put(0, 0, c, g)
c, g = cup((0.35, 0.10, 0.16), (0.55, 0.95, 0.9), (0.15, 0.9, 0.85), 4); put(1, 0, c, g)
# ---- fire coral (Millepora): ochre with pores, bleached white edges
def fire(base, seed):
    pores = dots(C, 2600, 0.8, 1.6, seed)
    c = lerp(col(base) * 0.85, col(base) * 1.1, n1)
    c = lerp(c, col(base) * 0.55, pores * 0.7)
    c = lerp(c, col((0.95, 0.92, 0.82)), sstep(0.8, 0.95, v) * (0.7 + 0.3 * n2))
    return c
put(2, 0, fire((0.80, 0.62, 0.22), 5)); put(3, 0, fire((0.62, 0.58, 0.30), 6))
# ---- leather coral (Sarcophyton): polar cap with polyp fuzz and folds; stalk
r_, a_ = polar()
def leather_cap(base, polyp, glowc, seed):
    fold = 0.5 + 0.5 * np.cos(a_ * math.tau * 9 + np.sin(a_ * math.tau * 3) * 2)
    pol = dots(C, 5000, 1.0, 2.2, seed)
    c = lerp(col(base) * 0.8, col(base), fold * 0.5 + n1 * 0.5)
    c = lerp(c, col(polyp), pol * sstep(0.15, 0.4, r_) * 0.8)
    c = lerp(c, col(base) * 0.6, sstep(0.92, 1.0, r_))           # rim underside
    g = col(glowc) * (pol * sstep(0.2, 0.5, r_) * (r_ < 1))[..., None] if glowc else None
    return c, g
c, _ = leather_cap((0.80, 0.72, 0.52), (0.75, 0.85, 0.62), None, 7); put(0, 1, c)
c = lerp(col((0.72, 0.64, 0.48)), col((0.86, 0.80, 0.66)), n1 * 0.6 + (1 - v) * 0.4); c = lerp(c, col((0.6, 0.52, 0.4)), dots(C, 1500, 0.6, 1.2, 8) * 0.5); put(1, 1, c)
c, g = leather_cap((0.48, 0.52, 0.30), (0.62, 0.92, 0.45), (0.2, 0.75, 0.25), 9); put(2, 1, c, g)
# ---- elkhorn (Acropora palmata): golden brown with corallite pores, pale growing tips
por = dots(C, 3500, 1.0, 2.0, 10)
c = lerp(col((0.62, 0.42, 0.20)), col((0.80, 0.58, 0.30)), n1 * 0.7 + n2 * 0.3)
c = lerp(c, col((0.42, 0.26, 0.12)), por * 0.6)
c = lerp(c, col((0.93, 0.88, 0.76)), sstep(0.82, 0.97, v))
put(3, 1, c)
# ---- zoanthids: olive columns; discs with dark mouth, bright oral disc, contrasting rim of short tentacles
c = lerp(col((0.35, 0.33, 0.20)), col((0.50, 0.46, 0.28)), n1); c = lerp(c, col((0.28, 0.25, 0.15)), sstep(0.0, 0.25, 1 - v) * 0.6); put(0, 2, c)
def zoa(disc, rim, glowd, glowr):
    tent = 0.5 + 0.5 * np.cos(a_ * math.tau * 22)
    c = lerp(col((0.08, 0.06, 0.05)), col(disc), sstep(0.06, 0.16, r_))
    c = lerp(c, col(disc) * 0.7, (0.5 + 0.5 * np.cos(a_ * math.tau * 8)) * sstep(0.2, 0.6, r_) * 0.35)
    c = lerp(c, lerp(col(rim) * 0.7, col(rim), tent), sstep(0.68, 0.76, r_))
    g = lerp(col(glowd) * sstep(0.1, 0.3, r_)[..., None], col(glowr) * (0.5 + 0.5 * tent)[..., None], sstep(0.68, 0.76, r_))
    g = g * (r_ < 1.0)[..., None]
    return c, g
c, g = zoa((0.25, 0.85, 0.30), (0.95, 0.55, 0.10), (0.1, 0.7, 0.15), (0.5, 0.25, 0.02)); put(1, 2, c, g)
c, g = zoa((0.80, 0.20, 0.65), (0.98, 0.90, 0.25), (0.6, 0.08, 0.5), (0.55, 0.5, 0.05)); put(2, 2, c, g)
c, g = zoa((0.95, 0.50, 0.12), (0.20, 0.85, 0.85), (0.6, 0.25, 0.02), (0.05, 0.6, 0.6)); put(3, 2, c, g)
# ---- cup crowns (polar): mouth, then radiating tentacles
def crown(cc, glowc):
    tent = 0.5 + 0.5 * np.cos(a_ * math.tau * 16)
    c = lerp(col(cc) * 0.5, col(cc), sstep(0.1, 0.35, r_)); c = lerp(c, col(cc) * (0.75 + 0.25 * tent)[..., None], sstep(0.35, 0.5, r_))
    g = col(glowc) * (sstep(0.15, 0.5, r_) * (0.6 + 0.4 * tent) * (r_ < 1))[..., None]
    return c, g
c, g = crown((1.0, 0.78, 0.2), (0.6, 0.38, 0.05)); put(0, 3, c, g)
c, g = crown((0.6, 1.0, 0.92), (0.2, 1.0, 0.9)); put(1, 3, c, g)
put(2, 3, lerp(col((0.45, 0.42, 0.36)), col((0.6, 0.56, 0.48)), n1))
# finger leather: soft beige-olive fingers with pale polyp fuzz toward the tips
c = lerp(col((0.62, 0.58, 0.40)), col((0.78, 0.74, 0.55)), n1 * 0.6 + v * 0.4)
c = lerp(c, col((0.9, 0.92, 0.78)), dots(C, 4000, 0.8, 1.6, 21) * sstep(0.3, 0.9, v) * 0.7)
put(3, 3, c)

# ---- brain corals (polar dome): meandering valleys = isolines of warped noise, ridges pale, valleys dark
def maze(seed, n=256, steps=6000):
    """labyrinth from a Gray-Scott reaction-diffusion run (the pattern real brain corals follow); 0 in the valleys"""
    r = np.random.default_rng(seed)
    U = np.ones((n, n)); Vv = np.zeros((n, n))
    for _ in range(40):
        x, y = r.integers(0, n, 2); U[y-4:y+4, x-4:x+4] = 0.5; Vv[y-4:y+4, x-4:x+4] = 0.25 + r.random() * 0.1
    Du, Dv, f, k = 0.16, 0.08, 0.029, 0.057
    for _ in range(steps):
        lu = np.roll(U, 1, 0) + np.roll(U, -1, 0) + np.roll(U, 1, 1) + np.roll(U, -1, 1) - 4 * U
        lv = np.roll(Vv, 1, 0) + np.roll(Vv, -1, 0) + np.roll(Vv, 1, 1) + np.roll(Vv, -1, 1) - 4 * Vv
        uvv = U * Vv * Vv
        U += Du * lu - uvv + f * (1 - U); Vv += Dv * lv + uvv - (f + k) * Vv
    img = Image.fromarray((np.clip(Vv / max(1e-6, Vv.max()), 0, 1) * 255).astype(np.uint8)).resize((C, C), Image.BICUBIC)
    m = np.asarray(img) / 255.0
    return 1 - sstep(0.15, 0.55, m)                     # ridges where V is low
def brain(ridge, valley, seed):
    mz = maze(seed)
    c = lerp(col(valley), col(ridge), sstep(0.05, 0.35, mz))
    c = lerp(c, col(ridge) * 1.12, sstep(0.75, 0.95, mz) * 0.6)
    c = lerp(c, c * 0.75, sstep(0.85, 1.0, r_))                           # darker toward the rim (shade, sediment)
    return c
put(0, 4, brain((0.78, 0.70, 0.48), (0.34, 0.26, 0.16), 31))
put(1, 4, brain((0.58, 0.72, 0.40), (0.22, 0.30, 0.18), 32))
# ---- table coral: top = radiating branchlets, underside = plain
spokes = 0.5 + 0.5 * np.cos(a_ * math.tau * 60 + np.sin(r_ * 20) * 0.5)
c = lerp(col((0.60, 0.50, 0.30)), col((0.80, 0.70, 0.48)), spokes * 0.6 + n1 * 0.4)
c = lerp(c, col((0.62, 0.72, 0.85)), sstep(0.85, 0.98, r_) * 0.7)                                  # blue growing edge
c = lerp(c, c * 0.55, dots(C, 3000, 0.8, 1.5, 33) * 0.6)
put(2, 4, c)
put(3, 4, lerp(col((0.40, 0.34, 0.24)), col((0.55, 0.48, 0.34)), n1 * 0.7 + v * 0.3))
# ---- staghorn: tan branches, coloured growing tips (blue / violet)
def stag(tipc, seed):
    c = lerp(col((0.62, 0.52, 0.34)), col((0.78, 0.68, 0.48)), n1)
    c = lerp(c, c * 0.6, dots(C, 3000, 0.7, 1.4, seed) * 0.6)
    return lerp(c, col(tipc), sstep(0.8, 0.95, v))
put(0, 5, stag((0.55, 0.75, 0.95), 34)); put(1, 5, stag((0.78, 0.55, 0.92), 35))
# ---- pillar coral: cream-tan, furry with polyps
c = lerp(col((0.70, 0.62, 0.45)), col((0.86, 0.80, 0.64)), n1)
c = lerp(c, col((0.95, 0.93, 0.85)), dots(C, 9000, 0.6, 1.4, 36) * 0.8)
put(2, 5, c)
# ---- anemone: red-orange column with pale verrucae; disc with radial stripes; tentacles with (glowing) tips
c = lerp(col((0.70, 0.20, 0.12)), col((0.88, 0.38, 0.20)), n1)
c = lerp(c, col((0.95, 0.75, 0.6)), dots(C, 900, 1.5, 3.0, 37) * 0.6)
put(3, 5, c)
def tent(base, tip, glowc):
    stripe = 0.5 + 0.5 * np.cos(v * math.tau * 6)
    c = lerp(col(base) * 0.85, col(base), stripe)
    c = lerp(c, col(tip), sstep(0.7, 0.95, v))
    g = col(glowc) * sstep(0.65, 0.95, v)[..., None] if glowc else None
    return c, g
c, g = tent((0.85, 0.75, 0.55), (0.75, 0.45, 0.95), (0.6, 0.2, 1.0)); put(0, 6, c, g)
c, _ = tent((0.80, 0.68, 0.45), (0.95, 0.85, 0.6), None); put(3, 7, c)
disc = 0.5 + 0.5 * np.cos(a_ * math.tau * 14)
c = lerp(col((0.25, 0.08, 0.06)), col((0.85, 0.55, 0.35)), sstep(0.1, 0.25, r_))
c = lerp(c, c * (0.75 + 0.25 * disc)[..., None], sstep(0.25, 0.9, r_))
put(1, 6, c, col((0.25, 0.05, 0.35)) * (sstep(0.3, 0.9, r_) * disc * (r_ < 1))[..., None])
# ---- barrel sponge: ridged red-brown outside, dark inside
ridge = np.abs(np.sin(u * math.tau * 7))
c = lerp(col((0.40, 0.18, 0.12)), col((0.62, 0.32, 0.22)), ridge * 0.7 + n1 * 0.3)
c = lerp(c, c * 0.6, dots(C, 2000, 1.0, 2.5, 38) * 0.6)
put(2, 6, c)
put(3, 6, lerp(col((0.12, 0.06, 0.05)), col((0.30, 0.16, 0.12)), v * 0.7 + n1 * 0.3))
# ---- tube sponges: violet / yellow tubes whose rims glow
def tube(base, glowc, seed):
    c = lerp(col(base) * 0.8, col(base), n1); c = lerp(c, c * 0.65, dots(C, 2500, 0.8, 1.6, seed) * 0.6)
    c = lerp(c, col(base) * 1.25, sstep(0.88, 0.98, v))
    g = col(glowc) * sstep(0.86, 0.99, v)[..., None]
    return c, g
c, g = tube((0.48, 0.22, 0.62), (0.45, 0.25, 1.0), 39); put(0, 7, c, g)
c, g = tube((0.85, 0.72, 0.18), (0.75, 1.0, 0.2), 40); put(1, 7, c, g)
put(2, 7, lerp(col((0.10, 0.06, 0.10)), col((0.30, 0.20, 0.28)), v))

Image.fromarray((D * 255).astype(np.uint8)).save(os.path.join(OUT, "coral_atlas.png"))
Image.fromarray((GL * 255).astype(np.uint8)).resize((512, 1024), Image.BOX).save(os.path.join(OUT, "coral_atlas_glow.png"))

# ---------------------------------------------------------------- sea fans: branching lattice, 2x2 colours
def fan(colr, seed, n=512):
    r = np.random.default_rng(seed)
    N = n * 2
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0)); d = ImageDraw.Draw(im)   # drawn at 2x, downsampled
    base = (N * 0.5, N - 12)
    rgba = tuple(int(c * 255) for c in colr) + (255,)
    def inside(q):            # fan outline: a wide half-ellipse above the holdfast
        x, y = (q[0] - base[0]) / (N * 0.49), (base[1] - q[1]) / (N * 0.96)
        th = math.atan2(y, x); ph = seed * 1.7
        lim = 1 + 0.10 * math.sin(3 * th + ph) + 0.06 * math.sin(7 * th + ph * 2) - 0.12 * max(0.0, math.cos(th)) ** 8 * (seed % 2)
        return y > 0 and x * x + y * y < lim * lim
    def branch(p, ang, length, w, depth):
        pts = [p]
        for k in range(10):
            ang += r.normal(0, 0.08)
            q = (pts[-1][0] + math.cos(ang) * length / 10, pts[-1][1] - math.sin(ang) * length / 10)
            if not inside(q): break
            pts.append(q)
        if len(pts) > 1: d.line(pts, fill=rgba, width=max(2, int(w)), joint="curve")
        if depth > 0:
            for k in range(2, len(pts), 2):
                if r.random() < 0.7:
                    branch(pts[k], ang + r.choice([-1, 1]) * r.uniform(0.3, 0.7), length * r.uniform(0.4, 0.6), w * 0.72, depth - 1)
    for k in range(9):
        branch(base, math.radians(22 + k * 17 + r.normal(0, 3)), N * r.uniform(0.75, 0.95), 14, 4)
    # the net: Voronoi cell walls inside the outline (the holes of a gorgonian fan), finer toward the rim
    from scipy.spatial import Voronoi
    pts = []
    while len(pts) < 2600:
        q = (r.uniform(0, N), r.uniform(0, N))
        if inside(q): pts.append(q)
    vor = Voronoi(np.array(pts))
    for (i, j) in vor.ridge_vertices:
        if i < 0 or j < 0: continue
        A, B = vor.vertices[i], vor.vertices[j]
        if inside(A) and inside(B) and np.hypot(*(A - B)) < 60: d.line([tuple(A), tuple(B)], fill=rgba, width=4)
    # polyps: brighter dots on the net
    hi = tuple(int(min(1, c * 1.3 + 0.12) * 255) for c in colr) + (255,)
    V = vor.vertices[[inside(v_) for v_ in vor.vertices]]
    for i in r.choice(len(V), size=min(len(V), 1800), replace=False):
        x, y = V[i]
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=hi)
    return im.resize((n, n), Image.LANCZOS)
F = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
for i, (c_, sd) in enumerate((((0.55, 0.18, 0.55), 11), ((0.85, 0.22, 0.12), 12), ((0.95, 0.78, 0.18), 13), ((0.80, 0.70, 0.92), 14))):
    F.paste(fan(c_, sd), ((i % 2) * 512, (i // 2) * 512))
a = np.asarray(F).copy()
rgb = a[..., :3].astype(float); al = a[..., 3]
# bleed colour into transparent texels so mipmaps don't fringe black
blur = np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(6))).astype(float)
w_ = np.clip(blur[..., 3:4] / 255.0, 1e-3, 1)
fill = blur[..., :3] / w_
rgb = np.where(al[..., None] > 0, rgb, np.clip(fill, 0, 255))
Image.fromarray(np.dstack([rgb.astype(np.uint8), al])).save(os.path.join(OUT, "seafan.png"))

# ---------------------------------------------------------------- sun shaft (additive): soft column fading toward the floor
v2, u2 = np.mgrid[0:256, 0:128] / np.array([255.0, 127.0])[:, None, None] if False else (np.mgrid[0:256, 0:128][0] / 255.0, np.mgrid[0:256, 0:128][1] / 127.0)
across = np.exp(-((u2 - 0.5) / 0.22) ** 2)
along = np.clip(1 - v2, 0, 1) ** 0.8 * sstep(0.0, 0.08, v2)        # v2 = 0 top of the image (skylight) -> 1 floor
streak = 0.75 + 0.25 * np.asarray(Image.fromarray((rng.random((1, 16)) * 255).astype(np.uint8)).resize((128, 256), Image.BICUBIC)) / 255.0
I = across * along * streak
sh = np.dstack([I * 0.55, I * 0.85, I * 0.95]) * 255
Image.fromarray(sh.astype(np.uint8)).save(os.path.join(OUT, "reef_shaft.png"))
print("ok")
