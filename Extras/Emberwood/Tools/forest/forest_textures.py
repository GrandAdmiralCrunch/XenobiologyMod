# Xenobiology — textures for the Emberwood (autumn forest lair). Everything is procedural and tileable where it tiles.
#   forest_bark.png (+_NRM)   2048x2048: 8 vertical strips 256 wide, each tiling in v (and wrapping in u around a trunk):
#                             0 emberleaf  1 goldenpale  2 copperoak  3 torchwood  4 duskpine  5 lanternfruit  6 mossy rock  7 misc
#                             strip 7 rows (px from the top): 0-256 log end rings, 256-768 mushroom cap, 768-1024 mushroom stem,
#                             1024-2048 weathered wood
#   forest_foliage.png        2048x2048 RGBA, 4x4 cells of 512: leaf sprigs, needle sprays, ferns, shrubs, reeds, lily pads
#   forest_floor.png (+_NRM)  2048 tile (~6 m) of leaf litter
#   forest_path.png           1024x1024, tiles in v; u = across the path, ragged alpha edges (cutout)
#   forest_streambed.png      1024x1024, tiles in v; pebbles and wet mud, ragged alpha edges
#   forest_water.png          512x1024 RGBA, tiles in v: translucent water, ripples, a few floating leaves
#   forest_fallleaves.png     512x512, 4x4 single leaves for the falling-leaf particles
#   forest_cascade.png        256x512 RGBA water streaks for the spring's little waterfall
#   forest_wood.png (+_NRM)   1024 weathered planks (bridge)
import os, sys, math, json, numpy as np
from PIL import Image, ImageDraw, ImageFilter
OUT = sys.argv[1] if len(sys.argv) > 1 else "forest_tex"
os.makedirs(OUT, exist_ok=True)
R = np.random.default_rng(1234)

def save(a, name, mode=None):
    a = np.clip(a, 0, 1)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8), mode).save(os.path.join(OUT, name))

def periodic_noise(h, w, scale_y, scale_x, seed, power=2.0):
    """Tileable band-limited noise (FFT-filtered white noise): features ~scale px across. Returns 0..1."""
    g = np.random.default_rng(seed).standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None] * scale_y; fx = np.fft.fftfreq(w)[None, :] * scale_x
    f = np.sqrt(fx * fx + fy * fy)
    filt = 1.0 / (1.0 + (f * 1.0) ** (power * 2))
    filt[0, 0] = 0
    n = np.real(np.fft.ifft2(np.fft.fft2(g) * filt))
    n = (n - n.mean()) / (n.std() + 1e-9)
    return np.clip(0.5 + n * 0.18, 0, 1)

def fbm(h, w, sy, sx, seed, oct=4):
    v = np.zeros((h, w)); amp = 1.0; tot = 0
    for o in range(oct):
        v += periodic_noise(h, w, sy / 2 ** o, sx / 2 ** o, seed + o * 7) * amp; tot += amp; amp *= 0.5
    return v / tot

def normal_from_height(hm, strength):
    gx = (np.roll(hm, -1, 1) - np.roll(hm, 1, 1)) * 0.5 * strength
    gy = (np.roll(hm, -1, 0) - np.roll(hm, 1, 0)) * 0.5 * strength
    n = np.stack([-gx, gy, np.ones_like(hm)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5

def lerp(a, b, t): return a + (np.asarray(b) - a) * t[..., None] if np.ndim(t) else a + (np.asarray(b) - a) * t
def C(*c): return np.array(c, float)
def ss(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

# ============================================================== leaf shapes
def leaf_outline(kind, n=64):
    """Unit leaf: base at (0,0), tip at (0,1). Returns list of (x, y)."""
    pts = []
    if kind == "maple":      # palmate, five pointed lobes, serrated
        for i in range(n * 2):
            th = i / (n * 2) * 2 * math.pi
            lobe = abs(math.cos(2.5 * th)) ** 1.6
            r = 0.38 + 0.62 * lobe
            r *= 1 + 0.07 * math.cos(22 * th)
            if abs(((th + math.pi) % (2 * math.pi)) - math.pi) > 2.75: r *= 0.25   # petiole notch at the base
            pts.append((math.sin(th) * r * 0.5, 0.42 + math.cos(th) * r * 0.55))
        return pts
    prof = {
        "ovate": lambda t: math.sin(t * math.pi) ** 0.8 * (1 - 0.45 * t) * 0.42,
        "oak": lambda t: math.sin(t * math.pi) ** 0.7 * (0.55 + 0.45 * abs(math.sin(t * math.pi * 3.5))) * 0.4 * (1 - 0.2 * t),
        "lance": lambda t: math.sin(t * math.pi) ** 1.1 * 0.17,
        "round": lambda t: math.sin(t * math.pi) ** 0.55 * 0.5,
        "heart": lambda t: (math.sin(t * math.pi) ** 0.6) * (0.55 - 0.25 * t) * (1.15 if t < 0.25 else 1),
    }[kind]
    serr = {"ovate": 0.035, "oak": 0.0, "lance": 0.02, "round": 0.0, "heart": 0.015}[kind]
    right, left = [], []
    for i in range(n + 1):
        t = i / n; w = prof(t)
        w *= 1 + serr * math.sin(t * 60) if serr else 1
        right.append((w, t)); left.append((-w, t))
    return right + left[::-1]

def leaf_poly(kind, cx, cy, size, ang, curl=0.0):
    ca, sa = math.cos(ang), math.sin(ang); out = []
    for x, y in leaf_outline(kind):
        x = x * (1 - curl * y * 0.5)
        X = x * size; Y = y * size
        out.append((cx + X * ca - Y * sa, cy + X * sa + Y * ca))
    return out

def draw_leaf(dr, kind, cx, cy, size, ang, col, vein=True, alpha=255, shade=0.18, curl=0.0):
    poly = leaf_poly(kind, cx, cy, size, ang, curl)
    c = tuple(int(max(0, min(1, v)) * 255) for v in col)
    dr.polygon(poly, fill=c + (alpha,))
    # one half a touch lighter: reads as a fold along the midrib
    half = poly[:len(poly) // 2 + 1] if kind != "maple" else poly[:len(poly) // 2]
    lc = tuple(int(max(0, min(1, v * (1 + shade))) * 255) for v in col)
    if len(half) > 2: dr.polygon(half + [(cx, cy)], fill=lc + (alpha,))
    if vein:
        ca, sa = math.cos(ang), math.sin(ang)
        vc = tuple(int(max(0, min(1, v * 0.62)) * 255) for v in col) + (alpha,)
        tip = (cx - 0 * ca - size * 0.92 * sa, cy + size * 0.92 * ca)
        dr.line([(cx, cy), tip], fill=vc, width=max(1, int(size * 0.03)))
        if kind == "maple":
            bx, by = cx - size * 0.3 * math.sin(ang), cy + size * 0.3 * math.cos(ang)
            for da in (-1.15, -0.6, 0.6, 1.15):
                a2 = ang + da
                dr.line([(bx, by), (bx - size * 0.38 * math.sin(a2), by + size * 0.38 * math.cos(a2))], fill=vc, width=max(1, int(size * 0.022)))
    return poly

def jitter(col, rng, amt=0.08):
    c = np.array(col) * (1 + rng.uniform(-amt, amt)) + rng.uniform(-amt, amt, 3) * 0.5
    return np.clip(c, 0, 1)

PAL = {
    "maple": [C(0.72, 0.07, 0.05), C(0.86, 0.16, 0.05), C(0.92, 0.3, 0.07), C(0.58, 0.05, 0.11), C(0.8, 0.1, 0.08)],
    "maple2": [C(0.93, 0.36, 0.06), C(0.96, 0.48, 0.1), C(0.86, 0.2, 0.05), C(0.98, 0.6, 0.15)],
    "gold": [C(0.95, 0.74, 0.1), C(0.99, 0.84, 0.24), C(0.86, 0.7, 0.12), C(0.82, 0.78, 0.22), C(0.97, 0.64, 0.08)],
    "copper": [C(0.64, 0.3, 0.1), C(0.76, 0.42, 0.14), C(0.52, 0.2, 0.08), C(0.7, 0.36, 0.16), C(0.6, 0.38, 0.14)],
    "torch": [C(0.98, 0.48, 0.05), C(0.96, 0.6, 0.12), C(0.88, 0.34, 0.04), C(0.99, 0.7, 0.2)],
    "lantern": [C(0.98, 0.62, 0.16), C(0.95, 0.5, 0.14), C(0.99, 0.74, 0.3), C(0.62, 0.26, 0.5)],
    "dead": [C(0.45, 0.3, 0.16), C(0.55, 0.36, 0.18), C(0.36, 0.22, 0.12)],
    "pine": [C(0.13, 0.29, 0.15), C(0.17, 0.35, 0.17), C(0.21, 0.4, 0.19), C(0.15, 0.32, 0.2)],
}

# ============================================================== foliage atlas
def sprig(kind, palette, seed, nleaf=60, size=(0.09, 0.15), twig=(0.32, 0.22, 0.14), spread=1.0, berries=None, droop=0.0):
    """One 512 cell (drawn at 1024 and reduced): a twig rising from the bottom centre, fanning out into side shoots,
    leaves along all of it (denser toward the tips) so the cell is filled like a leafy oval."""
    S = 1024; rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    tc = tuple(int(v * 255) for v in twig) + (255,)
    branches = []
    base = (S * 0.5, S * 0.99)
    main = [base]; x, y = base; a = -math.pi / 2 + rng.uniform(-0.1, 0.1)
    for k in range(9):
        a += rng.uniform(-0.12, 0.12)
        x += math.cos(a) * S * 0.092; y += math.sin(a) * S * 0.092; main.append((x, y))
    branches.append(main)
    for k in range(2, 9):
        for side in (-1, 1):
            if rng.random() < 0.15: continue
            st = main[k]; t = k / 9
            ba = -math.pi / 2 + side * (rng.uniform(0.55, 1.15) * spread)
            L = S * (0.42 * math.sin(min(1.0, t * 1.15) * math.pi) ** 0.7 + 0.08) * rng.uniform(0.8, 1.1)
            pts = [st]; xx, yy = st
            for j in range(5):
                ba += rng.uniform(-0.12, 0.12) + droop * 0.06 * side
                xx += math.cos(ba) * L / 5; yy += math.sin(ba) * L / 5; pts.append((xx, yy))
            branches.append(pts)
            if L > S * 0.25 and rng.random() < 0.7:     # a sub-shoot
                st2 = pts[2]; ba2 = ba - side * rng.uniform(0.4, 0.8); pts2 = [st2]; xx, yy = st2
                for j in range(3): xx += math.cos(ba2) * L * 0.12; yy += math.sin(ba2) * L * 0.12; pts2.append((xx, yy))
                branches.append(pts2)
    for i, b in enumerate(branches):
        for j in range(len(b) - 1):
            w = max(2, int((9 if i == 0 else 5) * (1 - j / len(b))))
            dr.line([b[j], b[j + 1]], fill=tc, width=w)
    cand = []
    for b in branches:
        for j in range(1, len(b)):
            for t in (0.2, 0.55, 0.9):
                p = (b[j - 1][0] + (b[j][0] - b[j - 1][0]) * t, b[j - 1][1] + (b[j][1] - b[j - 1][1]) * t)
                if not (40 < p[0] < S - 40 and 40 < p[1] < S - 30): continue
                da = math.atan2(b[j][1] - b[j - 1][1], b[j][0] - b[j - 1][0])
                cand.append((p, da, (j - 1 + t) / (len(b) - 1)))
    w = np.array([0.35 + c[2] for c in cand]); w /= w.sum()
    pick = rng.choice(len(cand), size=min(nleaf, len(cand) * 2), replace=True, p=w)
    for idx in pick:
        (px, py), da, tip = cand[idx]
        sz = rng.uniform(*size) * S * (0.85 + 0.3 * tip)
        side = rng.choice([-1, 1])
        ang = da + side * rng.uniform(0.3, 1.2) - math.pi / 2 + math.pi + droop * 0.4
        pl = sz * 0.2
        ex, ey = px - math.sin(ang) * pl * 0, py
        col = jitter(palette[int(rng.integers(len(palette)))], rng, 0.07)
        if rng.random() < 0.07: col = jitter(PAL["dead"][int(rng.integers(3))], rng)
        dr.line([(px, py), (px - math.sin(ang) * pl, py + math.cos(ang) * pl)], fill=tc, width=2)
        draw_leaf(dr, kind, px - math.sin(ang) * pl, py + math.cos(ang) * pl, sz, ang, col, curl=rng.uniform(0, 0.4))
    if berries is not None:
        for k in range(int(rng.integers(6, 10))):
            b = branches[int(rng.integers(1, len(branches)))]; cx, cy = b[-1]
            for m in range(int(rng.integers(4, 8))):
                r = rng.uniform(7, 11); ox, oy = rng.normal(0, 14, 2)
                c = jitter(berries, rng, 0.08); cc = tuple(int(v * 255) for v in c) + (255,)
                dr.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r], fill=cc)
                hl = tuple(int(min(1, v * 1.5 + 0.2) * 255) for v in c) + (255,)
                dr.ellipse([cx + ox - r * 0.45, cy + oy - r * 0.6, cx + ox - r * 0.05, cy + oy - r * 0.2], fill=hl)
    return grain(im).resize((512, 512), Image.LANCZOS)

def grain(im, amt=0.22, seed=5):
    """Fine mottling and darker leaf edges (multiplied in), so flat-filled leaves read as leaves up close."""
    a = np.asarray(im).astype(float) / 255
    n = np.random.default_rng(seed).random(a.shape[:2])
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(float) / 255
    al = a[..., 3]
    inner = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))).astype(float) / 255
    edge = np.clip(al - inner, 0, 1)
    a[..., :3] *= ((1 - amt / 2) + amt * (n - 0.5) * 2 + amt / 2)[..., None]
    a[..., :3] *= (1 - edge * 0.35)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGBA")

def needles(seed, palette):
    S = 1024; rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    tw = (88, 52, 34, 255)
    # a flat spray: main axis up, side shoots alternately, all covered in short needles
    axes = []
    x, y = S * 0.5, S * 0.98; a = -math.pi / 2
    main = [(x, y)]
    for k in range(9):
        a += rng.uniform(-0.06, 0.06); x += math.cos(a) * S * 0.1; y += math.sin(a) * S * 0.1; main.append((x, y))
    axes.append((main, 1.0))
    for k in range(2, 9):
        st = main[k]
        for side in (-1, 1):
            if rng.random() < 0.2: continue
            ba = -math.pi / 2 + side * rng.uniform(0.9, 1.3); L = S * 0.36 * (1 - k / 11) + S * 0.05
            pts = [st]; xx, yy = st
            for j in range(4): ba += side * 0.05; xx += math.cos(ba) * L / 4; yy += math.sin(ba) * L / 4; pts.append((xx, yy))
            axes.append((pts, 0.7))
    for pts, w in axes:
        for j in range(len(pts) - 1): dr.line([pts[j], pts[j + 1]], fill=tw, width=int(6 * w))
    for pts, w in axes:
        for j in range(len(pts) - 1):
            for t in np.linspace(0, 1, 13):
                px = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * t; py = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * t
                da = math.atan2(pts[j + 1][1] - pts[j][1], pts[j + 1][0] - pts[j][0])
                for side in (-1, 1):
                    na = da + side * rng.uniform(0.55, 1.15); L = rng.uniform(38, 62) * w
                    c = jitter(palette[int(rng.integers(len(palette)))], rng, 0.1)
                    tip = np.clip(c * 1.5 + 0.03, 0, 1)
                    ex, ey = px + math.cos(na) * L, py + math.sin(na) * L
                    dr.line([(px, py), (ex, ey)], fill=tuple(int(v * 255) for v in c) + (255,), width=4)
                    dr.line([((px + ex) / 2, (py + ey) / 2), (ex, ey)], fill=tuple(int(v * 255) for v in tip) + (255,), width=3)
    return im.resize((512, 512), Image.LANCZOS)

def fern(seed, cols, rachis=(0.42, 0.3, 0.14)):
    S = 1024; rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    rc = tuple(int(v * 255) for v in rachis) + (255,)
    pts = []; x, y = S * 0.5, S * 0.99; a = -math.pi / 2 - 0.08
    for k in range(40):
        a += 0.014; x += math.cos(a) * S * 0.0235; y += math.sin(a) * S * 0.0235; pts.append((x, y))
    for j in range(3, len(pts) - 1, 1):
        if j % 2: continue
        t = j / len(pts)
        L = S * 0.4 * math.sin(min(1, t * 1.2) * math.pi) ** 0.7 + 10
        da = math.atan2(pts[j + 1][1] - pts[j][1], pts[j + 1][0] - pts[j][0])
        for side in (-1, 1):
            pass
            na = da + side * (1.25 - 0.45 * t)
            c = jitter(cols[int(rng.integers(len(cols)))], rng, 0.07)
            px, py = pts[j]
            # a pinna: a slender, toothed lance curving toward the tip, with a dark midrib
            poly_r, poly_l = [], []
            for k in range(13):
                u = k / 12
                wdt = math.sin(u * math.pi) ** 0.6 * (1 - 0.5 * u) * L * 0.075 * (1 + 0.45 * (k % 2))
                cu = na - side * 0.25 * u
                cx, cy = px + math.cos(cu) * L * u, py + math.sin(cu) * L * u
                nx, ny = -math.sin(cu), math.cos(cu)
                poly_r.append((cx + nx * wdt, cy + ny * wdt)); poly_l.append((cx - nx * wdt, cy - ny * wdt))
            dr.polygon(poly_r + poly_l[::-1], fill=tuple(int(v * 255) for v in c) + (255,))
            dr.polygon(poly_r + [ (px, py) ], fill=tuple(int(min(1, v * 1.15) * 255) for v in c) + (255,))
            dr.line([(px, py), poly_r[-1]], fill=tuple(int(v * 150) for v in c) + (255,), width=2)
    for j in range(len(pts) - 1): dr.line([pts[j], pts[j + 1]], fill=rc, width=max(2, int(8 * (1 - j / 40))))
    return grain(im).resize((512, 512), Image.LANCZOS)

def reeds(seed):
    S = 1024; rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    for k in range(26):
        x0 = S * 0.5 + rng.normal(0, 60); h = rng.uniform(0.55, 0.95) * S; bend = rng.normal(0, 90)
        c = jitter(C(0.66, 0.55, 0.26) if rng.random() < 0.7 else C(0.45, 0.48, 0.2), rng, 0.08)
        pts = [(x0 + bend * (t ** 2), S - h * t) for t in np.linspace(0, 1, 12)]
        w0 = rng.uniform(8, 14)
        for j in range(11):
            w = w0 * (1 - j / 12) + 2
            dr.line([pts[j], pts[j + 1]], fill=tuple(int(v * 255) for v in c * (0.85 + 0.15 * j / 11)) + (255,), width=int(w))
        if rng.random() < 0.35:   # seed heads
            hx, hy = pts[9]; hc = jitter(C(0.36, 0.2, 0.1), rng)
            dr.rounded_rectangle([hx - 11, hy - 70, hx + 11, hy], radius=10, fill=tuple(int(v * 255) for v in hc) + (255,))
    return im.resize((512, 512), Image.LANCZOS)

def lily(seed):
    S = 1024; rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    for k in range(3):
        cx, cy = S * (0.3 + 0.4 * rng.random()), S * (0.3 + 0.4 * rng.random()); r = S * rng.uniform(0.16, 0.24)
        n0 = rng.uniform(0, 6.28)
        poly = []
        for i in range(90):
            th = i / 90 * 2 * math.pi
            if abs(((th - n0 + math.pi) % (2 * math.pi)) - math.pi) < 0.09: poly.append((cx, cy)); continue
            poly.append((cx + math.cos(th) * r, cy + math.sin(th) * r))
        c = jitter(C(0.42, 0.42, 0.16) if k else C(0.62, 0.36, 0.14), rng, 0.08)
        dr.polygon(poly, fill=tuple(int(v * 255) for v in c) + (255,))
        for v in range(9):
            th = v / 9 * 2 * math.pi
            dr.line([(cx, cy), (cx + math.cos(th) * r * 0.95, cy + math.sin(th) * r * 0.95)], fill=tuple(int(v2 * 200) for v2 in c) + (255,), width=3)
    # one pale violet bloom
    cx, cy = S * 0.62, S * 0.4
    for i in range(10):
        th = i / 10 * 2 * math.pi; ex, ey = cx + math.cos(th) * 60, cy + math.sin(th) * 60
        dr.ellipse([ex - 34, ey - 34, ex + 34, ey + 34], fill=(212, 170, 225, 255))
    dr.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(250, 210, 90, 255))
    return im.resize((512, 512), Image.LANCZOS)

def bleed(im, it=6):
    """Spread colour into transparent pixels so mipmaps don't fringe dark/black around cutouts."""
    a = np.asarray(im).astype(float) / 255
    rgb, al = a[..., :3].copy(), a[..., 3].copy()
    known = al > 0.02
    for k in range(it):
        acc = np.zeros_like(rgb); cnt = np.zeros(al.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(np.roll(known, dy, 0), dx, 1); acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * sh[..., None]; cnt += sh
        new = (~known) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]; known = known | new
    rgb[~known] = rgb[known].mean(0)
    return Image.fromarray((np.dstack([rgb, al]) * 255).astype(np.uint8), "RGBA")

def foliage_atlas():
    cells = [
        sprig("maple", PAL["maple"], 1, 95, (0.085, 0.13)),
        sprig("maple", PAL["maple"], 2, 85, (0.09, 0.14)),
        sprig("maple", PAL["maple2"], 3, 95, (0.085, 0.13)),
        sprig("ovate", PAL["gold"], 4, 210, (0.045, 0.07), twig=(0.25, 0.22, 0.2), droop=0.8),
        sprig("ovate", PAL["gold"], 5, 200, (0.045, 0.072), twig=(0.25, 0.22, 0.2), droop=1.2),
        sprig("oak", PAL["copper"], 6, 110, (0.08, 0.12), twig=(0.28, 0.18, 0.1)),
        sprig("oak", PAL["copper"], 7, 105, (0.08, 0.125), twig=(0.28, 0.18, 0.1)),
        sprig("lance", PAL["torch"], 8, 150, (0.085, 0.13), twig=(0.36, 0.22, 0.12), spread=0.9),
        sprig("lance", PAL["torch"], 9, 140, (0.09, 0.135), twig=(0.36, 0.22, 0.12), spread=0.9, droop=0.6),
        needles(10, PAL["pine"]),
        needles(11, PAL["pine"]),
        sprig("heart", PAL["lantern"], 12, 90, (0.09, 0.13), twig=(0.32, 0.2, 0.26)),
        fern(13, [C(0.78, 0.6, 0.2), C(0.7, 0.5, 0.16), C(0.84, 0.68, 0.26)]),
        fern(14, [C(0.62, 0.3, 0.12), C(0.7, 0.38, 0.14), C(0.52, 0.26, 0.1)]),
        sprig("ovate", [C(0.78, 0.1, 0.12), C(0.66, 0.08, 0.16), C(0.86, 0.22, 0.12), C(0.6, 0.12, 0.3)], 15, 140, (0.06, 0.09), twig=(0.3, 0.14, 0.12), berries=C(0.95, 0.85, 0.3)),
        reeds(16),
    ]
    A = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        A.paste(c, ((i % 4) * 512, (i // 4) * 512))
    A = bleed(A, 8)
    A.save(os.path.join(OUT, "forest_foliage.png"))
    lily(17).save(os.path.join(OUT, "forest_lily.png"))
    return A

# ============================================================== bark
def bark_strip(kind, seed):
    H, W = 2048, 256
    y = np.linspace(0, 1, H, endpoint=False)[:, None]; x = np.linspace(0, 1, W, endpoint=False)[None, :]
    if kind == "maple":
        f = fbm(H, W, 40, 6, seed); g = periodic_noise(H, W, 180, 30, seed + 3)
        ridge = 1 - np.abs(f - 0.5) * 2; hm = ridge ** 2 * 0.7 + g * 0.3
        col = lerp(C(0.27, 0.24, 0.22), C(0.5, 0.47, 0.43), hm)
        col *= (0.85 + 0.3 * periodic_noise(H, W, 300, 60, seed + 9))[..., None]
    elif kind == "birch":
        n = periodic_noise(H, W, 400, 40, seed); hm = 0.6 + 0.4 * n
        col = lerp(C(0.86, 0.84, 0.8), C(0.95, 0.94, 0.9), n)
        # lenticels: short dark horizontal dashes
        len_ = periodic_noise(H, W, 6, 220, seed + 5)
        dash = ss(0.78, 0.86, len_)
        col = lerp(col, C(0.18, 0.16, 0.15), dash * 0.9); hm -= dash * 0.3
        # black patches where branches fell, and grey peeling
        patch = ss(0.74, 0.8, periodic_noise(H, W, 30, 30, seed + 7))
        col = lerp(col, C(0.1, 0.09, 0.09), patch); hm -= patch * 0.4
        peel = ss(0.62, 0.7, periodic_noise(H, W, 60, 120, seed + 11))
        col = lerp(col, C(0.72, 0.62, 0.5), peel * 0.6)
    elif kind == "oak":
        f = fbm(H, W, 22, 5, seed, 5); ridge = 1 - np.abs(f - 0.5) * 2
        hm = ss(0.35, 0.85, ridge)
        col = lerp(C(0.12, 0.09, 0.07), C(0.38, 0.3, 0.24), hm)
        col *= (0.85 + 0.3 * periodic_noise(H, W, 200, 40, seed + 4))[..., None]
        lich = ss(0.68, 0.75, periodic_noise(H, W, 40, 40, seed + 8)) * hm
        col = lerp(col, C(0.42, 0.48, 0.3), lich * 0.7)
    elif kind == "torch":
        n = periodic_noise(H, W, 300, 30, seed); hm = 0.5 + 0.3 * n
        col = lerp(C(0.42, 0.38, 0.33), C(0.56, 0.52, 0.46), n)
        rings = ss(0.75, 0.82, periodic_noise(H, W, 5, 90, seed + 2))
        col = lerp(col, C(0.3, 0.26, 0.22), rings * 0.8); hm -= rings * 0.25
    elif kind == "pine":
        # plates: a tileable cellular pattern from thresholded noise ridges
        f = fbm(H, W, 14, 4, seed, 4)
        edges = ss(0.04, 0.0, np.abs(f - 0.5) - 0.02) if False else ss(0.06, 0.0, np.abs(f - 0.5))
        hm = 1 - edges * 0.9
        col = lerp(C(0.55, 0.28, 0.16), C(0.7, 0.4, 0.24), periodic_noise(H, W, 120, 30, seed + 1))
        col = lerp(col, C(0.16, 0.1, 0.08), edges)
    elif kind == "lantern":
        n = periodic_noise(H, W, 300, 30, seed); hm = 0.5 + 0.2 * n
        col = lerp(C(0.36, 0.3, 0.38), C(0.5, 0.44, 0.52), n)
        spiral = 0.5 + 0.5 * np.sin((y * 14 + x * 1.0) * 2 * math.pi)
        col = lerp(col, C(0.56, 0.48, 0.44), ss(0.88, 0.97, spiral) * 0.35)
    elif kind == "rock":
        n = fbm(H, W, 60, 60, seed, 5); hm = n
        col = lerp(C(0.36, 0.35, 0.33), C(0.6, 0.58, 0.54), n)
        cr = ss(0.08, 0.0, np.abs(fbm(H, W, 25, 25, seed + 5) - 0.5)); col = lerp(col, C(0.2, 0.19, 0.18), cr * 0.7); hm -= cr * 0.3
        moss = ss(0.5, 0.62, fbm(H, W, 30, 30, seed + 9) + (1 - y) * 0.0)
        col = lerp(col, C(0.3, 0.38, 0.14), moss * 0.85)
        lic = ss(0.7, 0.74, periodic_noise(H, W, 12, 12, seed + 13)); col = lerp(col, C(0.75, 0.72, 0.5), lic * 0.6)
    return np.clip(col, 0, 1), np.clip(hm, 0, 1)

def misc_strip():
    H, W = 2048, 256
    col = np.zeros((H, W, 3)); hm = np.zeros((H, W))
    # 0-256: end grain rings
    yy, xx = np.mgrid[0:256, 0:256]; r = np.hypot(xx - 128, yy - 128) / 128
    n = periodic_noise(256, 256, 30, 30, 5)
    rings = 0.5 + 0.5 * np.sin((r + n * 0.08) * 34)
    c = lerp(C(0.62, 0.46, 0.3), C(0.78, 0.62, 0.42), rings[..., None][..., 0])
    c = lerp(c, C(0.3, 0.2, 0.12), ss(0.9, 0.98, r)); c = lerp(c, C(0.36, 0.22, 0.12), ss(0.6, 0.0, r) * ss(0.95, 0.99, rings) * 0)
    crack = ss(0.03, 0.0, np.abs(np.arctan2(yy - 128, xx - 128) - 0.6)) * (r < 0.85); c = lerp(c, C(0.2, 0.14, 0.08), crack)
    col[0:256] = c; hm[0:256] = rings * 0.3
    # 256-768: mushroom cap, v up = toward the cap centre (spots)
    n = periodic_noise(512, 256, 40, 40, 7)
    t = np.linspace(0, 1, 512)[:, None] * np.ones((1, 256))
    c = lerp(C(0.62, 0.14, 0.06), C(0.92, 0.42, 0.1), t[..., None][..., 0] * 0.8 + n * 0.2)
    spots = ss(0.72, 0.76, periodic_noise(512, 256, 14, 14, 8)); c = lerp(c, C(0.96, 0.9, 0.78), spots)
    col[256:768] = c; hm[256:768] = spots * 0.4
    # 768-1024: stem / gills, pale
    n = periodic_noise(256, 256, 60, 10, 9)
    col[768:1024] = lerp(C(0.86, 0.8, 0.68), C(0.95, 0.9, 0.8), n); hm[768:1024] = n * 0.2
    # 1024-2048: weathered wood, grain along v
    n = fbm(1024, 256, 120, 6, 10)
    grain = 0.5 + 0.5 * np.sin(n * 60)
    c = lerp(C(0.36, 0.3, 0.24), C(0.56, 0.5, 0.42), grain * 0.6 + n * 0.4)
    col[1024:] = c; hm[1024:] = grain * 0.5
    return col, hm

def bark_atlas():
    cols, hms = [], []
    for i, k in enumerate(["maple", "birch", "oak", "torch", "pine", "lantern", "rock"]):
        c, h = bark_strip(k, 100 + i * 10); cols.append(c); hms.append(h)
    c, h = misc_strip(); cols.append(c); hms.append(h)
    col = np.concatenate(cols, 1); hm = np.concatenate(hms, 1)
    save(col, "forest_bark.png"); save(normal_from_height(hm, 6.0), "forest_bark_NRM.png")
    return col

# ============================================================== forest floor
def litter_layer(S, n, rng, kinds, size, wrap=True, dark=0.0, im=None, hmap=None, depth=1.0):
    if im is None: im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    hd = ImageDraw.Draw(hmap) if hmap is not None else None
    for k in range(n):
        kind, pal = kinds[int(rng.integers(len(kinds)))]
        sz = rng.uniform(*size) * S; ang = rng.uniform(0, 2 * math.pi)
        cx, cy = rng.uniform(0, S), rng.uniform(0, S)
        col = jitter(pal[int(rng.integers(len(pal)))], rng, 0.1) * (1 - dark * rng.random())
        if rng.random() < 0.3: col = col * 0.55 + jitter(PAL["dead"][0], rng) * 0.45      # browning
        for ox in ((-S, 0, S) if wrap else (0,)):
            for oy in ((-S, 0, S) if wrap else (0,)):
                if not (-sz * 1.2 < cx + ox < S + sz * 1.2 and -sz * 1.2 < cy + oy < S + sz * 1.2): continue
                draw_leaf(dr, kind, cx + ox, cy + oy, sz, ang, col, curl=rng.uniform(0, 0.5))
                if hd is not None:
                    hv = int(min(255, 90 + depth * 160 * rng.uniform(0.6, 1)))
                    hd.polygon(leaf_poly(kind, cx + ox, cy + oy, sz, ang), fill=hv)
    return im

def floor_texture():
    S = 4096; rng = np.random.default_rng(42)
    # soil and humus underneath
    soil = fbm(S // 2, S // 2, 60, 60, 3, 5)
    base = lerp(C(0.16, 0.1, 0.06), C(0.3, 0.2, 0.12), soil)
    base = np.asarray(Image.fromarray((base * 255).astype(np.uint8)).resize((S, S), Image.BILINEAR)).astype(float) / 255
    im = Image.fromarray((np.dstack([base, np.ones((S, S))]) * 255).astype(np.uint8), "RGBA")
    hmap = Image.new("L", (S, S), 30)
    allk = [("maple", PAL["maple"]), ("maple", PAL["maple2"]), ("ovate", PAL["gold"]), ("oak", PAL["copper"]), ("lance", PAL["torch"]), ("maple", PAL["dead"]), ("oak", PAL["dead"])]
    # bottom layers: older, darker, brown leaves; top layers: fresh colour
    layers = [(2600, [("oak", PAL["dead"]), ("maple", PAL["dead"]), ("ovate", PAL["dead"])], 0.5, 0.25), (2400, allk, 0.25, 0.55), (1800, allk, 0.0, 0.85)]
    for n, kinds, dark, depth in layers:
        # a soft shadow of the next layer onto what lies beneath
        sh = Image.new("L", (S, S), 0); tmp = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        state = rng.bit_generator.state
        litter_layer(S, n, rng, kinds, (0.012, 0.026), im=tmp, hmap=None)
        a = np.asarray(tmp)[..., 3].astype(float) / 255
        blur = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(float) / 255
        blur = np.roll(np.roll(blur, 5, 0), 3, 1)
        arr = np.asarray(im).astype(float) / 255
        arr[..., :3] *= (1 - blur * 0.45)[..., None]
        im = Image.fromarray((arr * 255).astype(np.uint8), "RGBA")
        rng.bit_generator.state = state
        litter_layer(S, n, rng, kinds, (0.012, 0.026), im=im, hmap=hmap, dark=dark, depth=depth)
    # twigs
    dr = ImageDraw.Draw(im)
    for k in range(160):
        x, y = rng.uniform(0, S, 2); a = rng.uniform(0, 6.28); L = rng.uniform(40, 160)
        c = tuple(int(v * 255) for v in jitter(C(0.3, 0.22, 0.15), rng)) + (255,)
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                dr.line([(x + ox, y + oy), (x + ox + math.cos(a) * L, y + oy + math.sin(a) * L)], fill=c, width=int(rng.uniform(4, 8)))
    col = np.asarray(im.resize((2048, 2048), Image.LANCZOS)).astype(float)[..., :3] / 255
    # large-scale tone variation (still tileable)
    col *= (0.88 + 0.24 * periodic_noise(2048, 2048, 3, 3, 77))[..., None]
    hm = np.asarray(hmap.filter(ImageFilter.GaussianBlur(2)).resize((2048, 2048), Image.LANCZOS)).astype(float) / 255
    save(col, "forest_floor.png"); save(normal_from_height(hm, 9.0), "forest_floor_NRM.png")
    return col

# ============================================================== path, streambed, water
def path_texture():
    S = 2048; rng = np.random.default_rng(7)
    u = np.linspace(0, 1, S)[None, :] * np.ones((S, 1))
    dirt = fbm(S, S, 50, 50, 21, 5)
    col = lerp(C(0.33, 0.24, 0.16), C(0.5, 0.39, 0.27), dirt)
    pebble = ss(0.8, 0.84, periodic_noise(S, S, 8, 8, 22)); col = lerp(col, C(0.58, 0.54, 0.48), pebble * 0.7)
    rut = np.exp(-((u - 0.35) / 0.06) ** 2) + np.exp(-((u - 0.65) / 0.06) ** 2)
    col *= (1 - 0.12 * rut)[..., None]
    im = Image.fromarray((np.dstack([col, np.ones((S, S))]) * 255).astype(np.uint8), "RGBA")
    # leaves: sparse in the middle (trodden), thick at the sides
    dr = ImageDraw.Draw(im)
    allk = [("maple", PAL["maple"]), ("ovate", PAL["gold"]), ("oak", PAL["copper"]), ("lance", PAL["torch"]), ("maple", PAL["dead"]), ("oak", PAL["dead"])]
    for k in range(5200):
        x = rng.uniform(0, S); edge = abs(x / S - 0.5) * 2
        if rng.random() > 0.08 + 0.92 * ss(0.45, 0.9, edge): continue
        y = rng.uniform(0, S); kind, pal = allk[int(rng.integers(len(allk)))]
        col_ = jitter(pal[int(rng.integers(len(pal)))], rng, 0.1) * (0.75 if edge < 0.5 else 1)
        sz = rng.uniform(0.022, 0.045) * S; ang = rng.uniform(0, 6.28)
        for oy in (-S, 0, S): draw_leaf(dr, kind, x, y + oy, sz, ang, col_)
    a = np.asarray(im).astype(float) / 255
    # ragged edge: alpha (cutout at 0.5) wobbles with v; leaves past the edge stay opaque where they overlap the dirt
    wob = periodic_noise(S, 1, 40, 1, 31)[:, :1] * 0.5 + fbm(S, S, 6, 6, 32) * 0.5
    edge = np.abs(u - 0.5) * 2
    alpha = 1 - ss(0.78, 0.96, edge + (wob - 0.5) * 0.35)
    a[..., 3] = alpha
    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGBA").resize((1024, 1024), Image.LANCZOS)
    out.save(os.path.join(OUT, "forest_path.png"))

def streambed_texture():
    S = 1024; rng = np.random.default_rng(9)
    u = np.linspace(0, 1, S)[None, :] * np.ones((S, 1))
    mud = fbm(S, S, 30, 30, 41, 4)
    col = lerp(C(0.2, 0.16, 0.1), C(0.32, 0.27, 0.18), mud)
    im = Image.fromarray((np.dstack([col, np.ones((S, S))]) * 255).astype(np.uint8), "RGBA"); dr = ImageDraw.Draw(im)
    for k in range(1600):
        x, y = rng.uniform(0, S), rng.uniform(0, S); r = rng.uniform(5, 22) * (1.3 - abs(x / S - 0.5))
        c = jitter(rng.choice([C(0.42, 0.4, 0.36), C(0.5, 0.45, 0.38), C(0.32, 0.3, 0.28), C(0.55, 0.42, 0.3)]), rng, 0.1)
        for oy in (-S, 0, S):
            dr.ellipse([x - r, y + oy - r * 0.75, x + r, y + oy + r * 0.75], fill=tuple(int(v * 255) for v in c) + (255,))
            dr.ellipse([x - r * 0.6, y + oy - r * 0.6, x + r * 0.1, y + oy - r * 0.05], fill=tuple(int(min(1, v * 1.25) * 255) for v in c) + (255,))
    a = np.asarray(im).astype(float) / 255
    algae = ss(0.55, 0.7, fbm(S, S, 20, 20, 43)); a[..., :3] = lerp(a[..., :3], C(0.24, 0.3, 0.1), algae * 0.55)
    wob = fbm(S, S, 8, 8, 44)
    a[..., 3] = 1 - ss(0.8, 0.97, np.abs(u - 0.5) * 2 + (wob - 0.5) * 0.3)
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "forest_streambed.png"))

def water_texture():
    H, W = 1024, 512; rng = np.random.default_rng(11)
    u = np.linspace(0, 1, W)[None, :] * np.ones((H, 1))
    rip = periodic_noise(H, W, 90, 18, 51)               # elongated along the flow (v)
    rip2 = periodic_noise(H, W, 40, 9, 52)
    hl = ss(0.62, 0.78, rip) * 0.6 + ss(0.66, 0.8, rip2) * 0.4
    col = lerp(C(0.05, 0.09, 0.08), C(0.12, 0.18, 0.16), rip)
    col = lerp(col, C(0.6, 0.68, 0.7), hl * 0.6)
    alpha = 0.38 + 0.3 * hl
    edge = np.abs(u - 0.5) * 2
    foam = ss(0.7, 0.92, edge) * ss(0.55, 0.75, periodic_noise(H, W, 30, 12, 53))
    col = lerp(col, C(0.85, 0.85, 0.8), foam * 0.6); alpha = np.maximum(alpha, foam * 0.75)
    im = Image.fromarray((np.dstack([col, alpha]) * 255).astype(np.uint8), "RGBA"); dr = ImageDraw.Draw(im)
    allk = [("maple", PAL["maple"]), ("ovate", PAL["gold"]), ("lance", PAL["torch"]), ("oak", PAL["copper"])]
    for k in range(9):
        x, y = rng.uniform(0.25, 0.75) * W, rng.uniform(0, H); kind, pal = allk[k % 4]
        for oy in (-H, 0, H): draw_leaf(dr, kind, x, y + oy, rng.uniform(26, 40), rng.uniform(0, 6.28), jitter(pal[0], rng))
    im.save(os.path.join(OUT, "forest_water.png"))
    # pond water: same look, tiling both ways, fewer leaves, calmer
    H2 = 512; rip = periodic_noise(H2, H2, 40, 40, 61); rip2 = periodic_noise(H2, H2, 14, 14, 62)
    hl = ss(0.66, 0.8, rip) * 0.5 + ss(0.7, 0.82, rip2) * 0.5
    col = lerp(lerp(C(0.04, 0.08, 0.07), C(0.1, 0.15, 0.13), rip), C(0.6, 0.68, 0.7), hl * 0.5)
    Image.fromarray((np.dstack([col, 0.5 + 0.25 * hl]) * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "forest_pondwater.png"))

def fall_leaves():
    S = 1024; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); rng = np.random.default_rng(13)
    spec = [("maple", PAL["maple"][0]), ("maple", PAL["maple"][1]), ("maple", PAL["maple2"][0]), ("maple", PAL["maple2"][2]),
            ("ovate", PAL["gold"][0]), ("ovate", PAL["gold"][1]), ("ovate", PAL["gold"][4]),
            ("oak", PAL["copper"][0]), ("oak", PAL["copper"][1]), ("oak", PAL["copper"][2]),
            ("lance", PAL["torch"][0]), ("lance", PAL["torch"][1]), ("lance", PAL["torch"][3]),
            ("heart", PAL["lantern"][0]), ("maple", PAL["dead"][1]), ("oak", PAL["dead"][0])]
    for i, (k, c) in enumerate(spec):
        cx, cy = (i % 4) * 256 + 128, (i // 4) * 256 + 128
        sz = 200 if k in ("maple",) else 210
        draw_leaf(dr, k, cx, cy + sz * 0.45, sz, math.pi, jitter(c, rng, 0.04))
    im = bleed(im.resize((512, 512), Image.LANCZOS), 4); im.save(os.path.join(OUT, "forest_fallleaves.png"))

def cascade_texture():
    H, W = 512, 256
    n = periodic_noise(H, W, 120, 6, 71); n2 = periodic_noise(H, W, 60, 3, 72)
    streak = ss(0.45, 0.75, n) * 0.7 + ss(0.5, 0.8, n2) * 0.5
    col = lerp(C(0.55, 0.62, 0.62), C(0.95, 0.97, 0.97), streak)
    u = np.linspace(0, 1, W)[None, :] * np.ones((H, 1))
    alpha = np.clip(0.25 + streak * 0.7, 0, 1) * (1 - ss(0.8, 1.0, np.abs(u - 0.5) * 2))
    save(np.dstack([col, alpha]), "forest_cascade.png")

def wood_texture():
    S = 1024; rng = np.random.default_rng(15)
    col = np.zeros((S, S, 3)); hm = np.zeros((S, S))
    planks = 8; pw = S // planks
    for p in range(planks):
        n = fbm(S, pw, 200, 5, 80 + p, 4)
        grain = 0.5 + 0.5 * np.sin(n * 50 + rng.uniform(0, 6))
        base = jitter(C(0.42, 0.34, 0.25), rng, 0.08)
        c = lerp(base * 0.75, base * 1.2, grain * 0.5 + n * 0.5)
        c = lerp(c, C(0.52, 0.52, 0.48), ss(0.5, 0.8, periodic_noise(S, pw, 80, 20, 90 + p)) * 0.35)   # silvered
        h = grain * 0.4 + 0.6
        h[:, :4] = 0; h[:, -4:] = 0; c[:, :4] *= 0.4; c[:, -4:] *= 0.4
        col[:, p * pw:(p + 1) * pw] = c; hm[:, p * pw:(p + 1) * pw] = h
    moss = ss(0.6, 0.72, fbm(S, S, 20, 20, 99)); col = lerp(col, C(0.28, 0.36, 0.12), moss * 0.5)
    save(col, "forest_wood.png"); save(normal_from_height(hm, 5.0), "forest_wood_NRM.png")

if __name__ == "__main__":
    which = sys.argv[2:] or ["foliage", "bark", "floor", "path", "bed", "water", "leaves", "cascade", "wood"]
    for w in which:
        {"foliage": foliage_atlas, "bark": bark_atlas, "floor": floor_texture, "path": path_texture, "bed": streambed_texture,
         "water": water_texture, "leaves": fall_leaves, "cascade": cascade_texture, "wood": wood_texture}[w]()
        print("done", w, flush=True)
