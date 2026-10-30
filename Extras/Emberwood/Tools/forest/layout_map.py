# Plan view of a ForestLayout dump (layout.json + ground.bin + pqs.bin) for checking layouts.
import json, sys, numpy as np
from PIL import Image, ImageDraw
d = json.load(open(sys.argv[1])); g = np.fromfile(sys.argv[2], np.float32); q = np.fromfile(sys.argv[3], np.float32)
N = d["gN"]; E = d["E"]; g = g.reshape(N, N); q = q.reshape(N, N)
S = 2  # px per m /2 -> image 1 px = 0.5... use downsample
step = 1
gy, gx = np.gradient(g)
shade = np.clip(0.75 + (gx * -0.7 + gy * 0.7) * 1.2, 0.2, 1.3)
lift = g - q
col = np.zeros((N, N, 3))
col[:] = (0.72, 0.42, 0.18)
col[lift < 0] = (0.35, 0.55, 0.25)
col *= shade[..., None]
img = Image.fromarray((np.clip(col, 0, 1)[::-1] * 255).astype(np.uint8))
dr = ImageDraw.Draw(img)
P = lambda x, z: (x + E, E - z)
st = d["stream"]
for i in range(len(st) - 1):
    dr.line([P(st[i][0], st[i][1]), P(st[i + 1][0], st[i + 1][1])], fill=(60, 120, 220), width=int(st[i][3] * 2))
for b in ("pool", "pond"):
    x, z, w, r = d[b]; dr.ellipse([P(x - r, z + r), P(x + r, z - r)], fill=(60, 120, 220))
pa = d["path"]
for i in range(len(pa) - 1):
    if i + 1 == d.get('mainPath', -1): continue
    dr.line([P(pa[i][0], pa[i][1]), P(pa[i + 1][0], pa[i + 1][1])], fill=(230, 200, 140) if pa[i][5] < 0.5 else (140, 80, 30), width=3)
cols = [(200, 30, 30), (240, 210, 60), (170, 90, 40), (250, 130, 20), (30, 80, 50), (255, 240, 160)]
for t in d["trees"]:
    x, z = P(t[2], t[4]); r = 1.6 * t[5] * (1.5 if t[0] == 2 else 1)
    dr.ellipse([x - r, z - r, x + r, z + r], fill=cols[t[0]])
c = d["clearing"]; x, z = P(c[0], c[1]); dr.ellipse([x - c[2], z - c[2], x + c[2], z + c[2]], outline=(255, 255, 255))
e = d["elder"]; x, z = P(e[0], e[1]); dr.ellipse([x - 5, z - 5, x + 5, z + 5], fill=(255, 60, 200))
b = d["bridge"]; x, z = P(b[0], b[1]); dr.rectangle([x - 4, z - 4, x + 4, z + 4], outline=(255, 0, 255), width=2)
ca = d["cascade"]; x, z = P(ca[0], ca[1]); dr.rectangle([x - 4, z - 4, x + 4, z + 4], fill=(120, 120, 130))
en = d["entrance"]; x, z = P(en[0], en[1]); dr.ellipse([x - 6, z - 6, x + 6, z + 6], outline=(0, 255, 255), width=3)
img.save(sys.argv[4])
print("lift range in forest:", float(np.percentile(lift, 5)), float(np.percentile(lift, 99.9)), "max", float(lift.max()))
