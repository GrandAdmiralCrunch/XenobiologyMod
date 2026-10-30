"""Xenobiology — grow the corals and sponges on the reef base (low-poly, atlas-mapped).

Reads reef_high.npz / reef_meta.json from reef_sdf.py, samples the rock surface and places 15 species
(builders in reef_coral_lib.py), each where it would grow: elkhorn, table and staghorn on the bright tops, brain
corals and pillar corals on the slopes, fire coral on the upper slopes, leather corals and barrel sponges lower down,
sea fans on steep walls facing the current, cup corals under overhangs and in the caves, zoanthids, anemones and
glowing tube sponges everywhere (densest in the dark).
Objects are grouped by the base's 8-chunk grid (frustum culling) and by size tier:
  coral_<mat>_<chunk>    big corals, drawn out to the lair's detailRange
  coral_s_<mat>_<chunk>  small ones (cups, zoanthids, anemones, tube sponges, finger leathers), hidden beyond detailRangeSmall
  sway_fan_##            the biggest sea fans, rocked by the plugin
Materials: atlas0/1/2 (KSP/Emissive/Diffuse, three glow phases) and fan (KSP/Alpha/Cutoff).
Specimen points (field guide): up to 14 per species, written to corals.json as "specimens"; reef_build.py makes them
empty transforms named spec_<species>_## that the plugin's Observe Lifeform looks for.
Usage: python reef_corals.py <dir with reef_high.npz>
"""
import sys, os, json, math
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reef_coral_lib as L

DIR = sys.argv[1] if len(sys.argv) > 1 else "."
rng = L.rng
H = np.load(os.path.join(DIR, "reef_high.npz")); V = H["verts"].astype(np.float64); F = H["faces"]
M = json.load(open(os.path.join(DIR, "reef_meta.json")))

# ------------------------------------------------------------------ surface data
A, B, Cc = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
fn = np.cross(B - A, Cc - A); area = np.linalg.norm(fn, axis=1) * 0.5
fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
top = (A[:, 2] > 8) & (np.abs(fn[:, 2]) > 0.7)
if (fn[top, 2] < 0).mean() > 0.5: fn = -fn
vn = np.zeros_like(V)
for k in range(3): np.add.at(vn, F[:, k], fn * area[:, None])
vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
TREE = cKDTree(V)
def snap(p):
    _, i = TREE.query(p); return V[i], vn[i]
L.SNAP = snap

def poly_dist(p, pts):
    best = 1e9
    for a, b in zip(pts, pts[1:]):
        a = np.array(a, float); b = np.array(b, float); d = b - a
        t = np.clip((p - a) @ d / (d @ d), 0, 1); best = min(best, np.linalg.norm(a + d * t - p))
    return best
CAV = np.array(M["cavern"]["c"]); CAVR = np.array(M["cavern"]["r"])
SLOT = np.array(M["slot"])
def region(p):
    q = (p - CAV) / CAVR
    if q @ q < 1.35 ** 2: return "cave"
    td = min(poly_dist(p, t) for t in M["tunnels"])
    if td < 3.6: return "cave"
    if SLOT[:, 1].min() - 1 < p[1] < SLOT[:, 1].max() + 1 and abs(p[0] - np.interp(p[1], SLOT[:, 1], SLOT[:, 0])) < 3.2 and p[2] < 9: return "cave"
    if td < 6.5: return "mouth"
    return "open"

cdf = np.cumsum(area); cdf /= cdf[-1]
def sample(n):
    idx = np.searchsorted(cdf, rng.random(n))
    r1, r2 = rng.random(n), rng.random(n); s = np.sqrt(r1)
    P = A[idx] * (1 - s)[:, None] + B[idx] * (s * (1 - r2))[:, None] + Cc[idx] * (s * r2)[:, None]
    return P, fn[idx]

XS = [-104, -52, 0, 52, 104]; YSPLIT = -6.0
def chunk_of(p):
    i = min(3, max(0, int(np.searchsorted(XS, p[0]) - 1))); j = 0 if p[1] < YSPLIT else 1
    return i + 4 * j
GROUPS = {}
def G(p, mat, small=False):
    k = (chunk_of(p), mat, small)
    if k not in GROUPS: GROUPS[k] = L.Mesh()
    return GROUPS[k]

# ------------------------------------------------------------------ placement rules
# name: (species, caps, spacing, eligible(p, n, reg) -> weight, build(p, n, reg), small tier)
SWAY = []
def build_fan(p, n, reg):
    big = len(SWAY) < 28 and rng.random() < 0.3
    W = rng.uniform(1.1, 1.9) * (1.4 if big else 1.0)
    if big:
        m = L.Mesh(); piv = L.sea_fan(m, p, n, int(rng.integers(0, 4)), W); SWAY.append((m, piv))
    else: L.sea_fan(G(p, "fan"), p, n, int(rng.integers(0, 4)), W)
RULES = {
    "elkhorn":  ("kerbin_elkhorncoral", 55, 3.6, lambda p, n, r: 3.0 if r == "open" and n[2] > 0.75 and p[2] > 5 else 0,
                 lambda p, n, r: L.elkhorn(G(p, "atlas"), p, n, rng.uniform(1.2, 2.2)), False),
    "table":    ("kerbin_tablecoral", 45, 4.2, lambda p, n, r: 2.0 if r == "open" and n[2] > 0.7 and p[2] > 3 else 0,
                 lambda p, n, r: L.table_coral(G(p, "atlas"), p, n, rng.uniform(0.7, 1.5)), False),
    "staghorn": ("kerbin_staghorncoral", 55, 2.8, lambda p, n, r: 2.0 if r == "open" and n[2] > 0.6 and p[2] > 2 else 0,
                 lambda p, n, r: L.staghorn(G(p, "atlas"), p, n, int(rng.integers(0, 2)), rng.uniform(0.9, 1.5)), False),
    "brain":    ("kerbin_braincoral", 90, 2.6, lambda p, n, r: 2.0 if r == "open" and n[2] > 0.45 and p[2] > 0.8 else 0,
                 lambda p, n, r: L.brain_coral(G(p, "atlas"), p, n, int(rng.random() < 0.4), rng.uniform(0.35, 1.1)), False),
    "pillar":   ("kerbin_pillarcoral", 30, 5.0, lambda p, n, r: 1.5 if r == "open" and n[2] > 0.7 and 1 < p[2] < 7 else 0,
                 lambda p, n, r: L.pillar_coral(G(p, "atlas"), p, n, rng.uniform(0.9, 1.4)), False),
    "fire":     ("kerbin_firecoral", 90, 2.4, lambda p, n, r: 2.0 if r == "open" and n[2] > 0.45 and p[2] > 2.5 else 0,
                 lambda p, n, r: L.fire_coral(G(p, "atlas"), p, n, int(rng.random() < 0.35)), False),
    "leather":  ("kerbin_leathercoral", 80, 2.2, lambda p, n, r: 1.5 if r == "open" and n[2] > 0.55 and 0.8 < p[2] < 8.5 else 0,
                 lambda p, n, r: L.leather(G(p, "atlas"), p, n, rng.random() < 0.35), False),
    "finger":   ("kerbin_fingerleather", 45, 2.2, lambda p, n, r: 1.0 if r != "cave" and n[2] > 0.4 and p[2] > 0.6 else 0,
                 lambda p, n, r: L.finger_leather(G(p, "atlas", True), p, n), True),
    "barrel":   ("kerbin_barrelsponge", 35, 4.5, lambda p, n, r: 1.5 if r != "cave" and n[2] > 0.6 and p[2] < 5 else 0,
                 lambda p, n, r: L.barrel_sponge(G(p, "atlas"), p, n, rng.uniform(0.3, 0.7)), False),
    "fan":      ("kerbin_seafan", 150, 2.3, lambda p, n, r: 3.0 if r == "open" and -0.25 < n[2] < 0.45 and p[2] > 1.2 else 0,
                 build_fan, False),
    "cup":      ("kerbin_suncupcoral", 180, 1.0, lambda p, n, r: (4.0 if r == "cave" and n[2] < 0.6 else 2.0 if n[2] < -0.25 else 0),
                 None, True),
    "zoa":      ("kerbin_zoanthid", 120, 1.6, lambda p, n, r: (2.5 if r == "cave" and n[2] > -0.3 else 0.4 if n[2] > 0.3 else 0),
                 lambda p, n, r: L.zoanthid_colony(G(p, "atlas", True), p, n, int(rng.integers(0, 3)), rng.uniform(0.18, 0.5)), True),
    "anemone":  ("kerbin_anemone", 50, 2.4, lambda p, n, r: (2.0 if r != "open" and n[2] > 0.2 else 0.5 if n[2] > 0.4 else 0),
                 lambda p, n, r: L.anemone(G(p, "atlas", True), p, n, r != "open" or rng.random() < 0.3, rng.uniform(0.9, 1.6)), True),
    "tube":     ("kerbin_tubesponge", 60, 2.0, lambda p, n, r: (2.0 if r != "open" and n[2] > 0.1 else 0.6 if n[2] > 0.3 else 0),
                 lambda p, n, r: L.tube_sponge(G(p, "atlas", True), p, n, int(rng.integers(0, 2))), True),
}
def build_cup(p, n, r):
    glow = rng.random() < (0.65 if r == "cave" else 0.25)
    L.cup_cluster(G(p, "atlas", True), p, n, glow)
    return "kerbin_glowcupcoral" if glow else "kerbin_suncupcoral"

placed = {k: [] for k in RULES}
SPEC = {s: [] for s in L.SPECIES}
def far_enough(p, lst, r):
    return all(np.linalg.norm(p - q) > r for q in lst[-500:])
P, N = sample(90000)
for p, n in zip(P, N):
    if p[2] < 0.25: continue
    reg = region(p)
    cands = [(k, R[3](p, n, reg)) for k, R in RULES.items() if len(placed[k]) < R[1]]
    cands = [(k, w) for k, w in cands if w > 0]
    if not cands: continue
    ws = np.array([w for _, w in cands]); k = cands[rng.choice(len(cands), p=ws / ws.sum())][0]
    if rng.random() > 0.35: continue                                   # thin the sampling out evenly
    R = RULES[k]
    if not far_enough(p, placed[k], R[2]): continue
    if k == "cup": species = build_cup(p, n, reg)
    else: R[4](p, n, reg); species = R[0]
    placed[k].append(p)
    if len(SPEC[species]) < 14 and (not SPEC[species] or min(np.linalg.norm(p - np.array(q)) for q in SPEC[species]) > 12):
        SPEC[species].append([float(c) for c in (p + n * 0.3)])

# ------------------------------------------------------------------ write
out = {}; objs = []
for (ch, mat, small), m in sorted(GROUPS.items()):
    name = "coral_%s%s_%d" % ("s_" if small else "", mat, ch)
    out[name + "_v"] = np.array(m.v, np.float32); out[name + "_f"] = np.array(m.f, np.int32); out[name + "_uv"] = np.array(m.uv, np.float32)
    objs.append({"name": name, "mat": mat if mat == "fan" else "atlas%d" % (ch % 3), "chunk": ch, "pivot": None, "tris": len(m.f), "verts": len(m.v)})
for i, (m, piv) in enumerate(SWAY):
    name = "sway_fan_%02d" % i
    out[name + "_v"] = np.array(m.v, np.float32); out[name + "_f"] = np.array(m.f, np.int32); out[name + "_uv"] = np.array(m.uv, np.float32)
    objs.append({"name": name, "mat": "fan", "chunk": chunk_of(piv), "pivot": [float(c) for c in piv], "tris": len(m.f), "verts": len(m.v)})
np.savez_compressed(os.path.join(DIR, "corals.npz"), **out)
lights = [{"name": "glow_cavern", "pos": [CAV[0], CAV[1], CAV[2] + 1.5], "color": [0.25, 1.0, 0.85], "range": 16, "energy": 1.2},
          {"name": "glow_tunnel", "pos": [M["tunnels"][2][2][0], M["tunnels"][2][2][1], 3.0], "color": [0.35, 1.0, 0.4], "range": 12, "energy": 1.0},
          {"name": "glow_slot", "pos": [float(np.interp(18, SLOT[:, 1], SLOT[:, 0])), 18.0, 4.0], "color": [1.0, 0.6, 0.25], "range": 12, "energy": 0.9}]
info = {"placed": {k: len(v) for k, v in placed.items()}, "tris": int(sum(o["tris"] for o in objs)),
        "small_tris": int(sum(o["tris"] for o in objs if "_s_" in o["name"])), "objects": len(objs),
        "maxverts": max(o["verts"] for o in objs), "specimens": {k: len(v) for k, v in SPEC.items()}}
json.dump({"objects": objs, "placed": info["placed"], "lights": lights, "tris": info["tris"], "specimens": SPEC}, open(os.path.join(DIR, "corals.json"), "w"), indent=1)
print(json.dumps(info))
