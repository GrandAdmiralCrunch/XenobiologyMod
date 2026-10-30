"""Xenobiology — one specimen of each reef species, for the Field Guide portraits and silhouettes.
Builds every species with reef_coral_lib on a flat plate (SNAP = the z = 0 plane) and writes specimens.npz
(per species: v, f, uv, plus a 'mat' list) for Blender's reef_portraits.py.
Usage: python reef_specimens.py <out_dir>
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reef_coral_lib as L

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
L.SNAP = lambda p: (np.array([p[0], p[1], 0.0]), np.array([0, 0, 1.0]))
n = np.array([0, 0, 1.0]); o = np.zeros(3)
BUILD = {
    "kerbin_elkhorncoral":  lambda m: L.elkhorn(m, o, n, 1.7),
    "kerbin_staghorncoral": lambda m: L.staghorn(m, o, n, 0, 1.3),
    "kerbin_tablecoral":    lambda m: L.table_coral(m, o, n, 1.1),
    "kerbin_braincoral":    lambda m: L.brain_coral(m, o, n, 0, 0.8),
    "kerbin_pillarcoral":   lambda m: L.pillar_coral(m, o, n, 1.2),
    "kerbin_suncupcoral":   lambda m: L.cup_cluster(m, o, n, False),
    "kerbin_glowcupcoral":  lambda m: L.cup_cluster(m, o, n, True),
    "kerbin_firecoral":     lambda m: L.fire_coral(m, o, n, 0),
    "kerbin_leathercoral":  lambda m: L.leather(m, o, n, True),
    "kerbin_fingerleather": lambda m: L.finger_leather(m, o, n),
    "kerbin_seafan":        lambda m: L.sea_fan(m, o, np.array([0, -1.0, 0.2]), 0, 1.6),
    "kerbin_zoanthid":      lambda m: L.zoanthid_colony(m, o, n, 0, 0.32),
    "kerbin_anemone":       lambda m: L.anemone(m, o, n, True, 1.3),
    "kerbin_barrelsponge":  lambda m: L.barrel_sponge(m, o, n, 0.5),
    "kerbin_tubesponge":    lambda m: L.tube_sponge(m, o, n, 0),
}
out = {}; info = {}
for sp, fn in BUILD.items():
    best = None
    for seed in range(6):                       # a well-grown specimen: the richest of a few tries
        L.rng = np.random.default_rng(sum(map(ord, sp)) * 7 + seed)
        m = L.Mesh(); fn(m)
        if best is None or len(m.f) > len(best.f): best = m
    m = best
    V = np.array(m.v, np.float32)
    out[sp + "_v"] = V; out[sp + "_f"] = np.array(m.f, np.int32); out[sp + "_uv"] = np.array(m.uv, np.float32)
    info[sp] = {"mat": "fan" if sp == "kerbin_seafan" else "atlas", "min": V.min(0).tolist(), "max": V.max(0).tolist(), "tris": len(m.f)}
np.savez_compressed(os.path.join(OUT, "specimens.npz"), **out)
json.dump(info, open(os.path.join(OUT, "specimens.json"), "w"), indent=1)
print(json.dumps({k: v["tris"] for k, v in info.items()}))
