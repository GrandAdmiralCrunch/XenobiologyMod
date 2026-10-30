"""Xenobiology — convert model textures (PNG) to DDS for KSP.
DXT1 (BC1) with a full mipmap chain, rows stored bottom-up as KSP's DDS loader expects (images are flipped).
A 2048 RGBA PNG takes 16 MB of memory once loaded (no mipmaps); the same texture as DXT1 with mipmaps takes 2.8 MB,
loads several times faster and renders faster at a distance. Textures with real transparency are written as DXT5.
Normal maps (file name ending in _NRM) are written as DXT5nm: x in alpha, y in green (what KSP's bumped shaders unpack).

Usage:  python xeno_dds.py <png> [<png> ...]          writes <name>.dds next to each PNG (delete the PNG afterwards:
        python xeno_dds.py --dir <folder>             KSP would otherwise load both)
Needs numpy, Pillow and etcpak (pip install etcpak).
"""
import sys, os, struct
import numpy as np
from PIL import Image, ImageOps
import etcpak

COVERAGE = ("foliage", "_imp", "lily", "fallleaves", "seafan")

def _blocks(img, alpha):
    w, h = img.size
    pw, ph = max(4, (w + 3) // 4 * 4), max(4, (h + 3) // 4 * 4)
    a = np.array(img.convert("RGBA"), dtype=np.uint8)
    if (pw, ph) != (w, h):                                    # tiny mips: pad by repeating edge pixels
        a = np.pad(a, ((0, ph - h), (0, pw - w), (0, 0)), mode="edge")
    data = np.ascontiguousarray(a).tobytes()
    return etcpak.compress_bc3(data, pw, ph) if alpha else etcpak.compress_bc1(data, pw, ph)

def convert(src, dst=None, force_alpha=None):
    img = Image.open(src)
    img.load()
    if os.path.splitext(os.path.basename(src))[0].upper().endswith("_NRM"):
        a = np.array(img.convert("RGB"))
        nm = np.dstack([np.full(a.shape[:2], 255, np.uint8), a[..., 1], a[..., 1], a[..., 0]])
        img = Image.fromarray(nm, "RGBA"); force_alpha = True
    has_alpha = img.mode in ("RGBA", "LA") and np.array(img.getchannel("A")).min() < 250
    alpha = has_alpha if force_alpha is None else force_alpha
    img = img.convert("RGBA")
    w, h = img.size
    mips = []
    cur = img
    name = os.path.basename(src).lower()
    keep = alpha and any(k in name for k in COVERAGE)
    cov0 = None
    while True:
        out = cur
        if keep:
            # alpha-tested foliage thins out in small mips: scale alpha so the share of pixels above the cutoff stays put
            a_ = np.array(cur.getchannel("A"), np.float32) / 255
            if cov0 is None: cov0 = (a_ > 0.5).mean()
            elif a_.size > 16:
                lo, hi = 1.0, 4.0
                for _ in range(14):
                    mid = (lo + hi) / 2
                    if (np.clip(a_ * mid, 0, 1) > 0.5).mean() < cov0: lo = mid
                    else: hi = mid
                arr = np.array(cur); arr[..., 3] = np.clip(a_ * lo * 255, 0, 255).astype(np.uint8); out = Image.fromarray(arr, "RGBA")
        mips.append(_blocks(ImageOps.flip(out), alpha))
        if cur.size == (1, 1): break
        nxt = (max(1, cur.size[0] // 2), max(1, cur.size[1] // 2))
        if keep:
            # alpha-weighted average: transparent texels don't pull leaf colours toward their (meaningless) fill colour
            a4 = np.array(cur, np.float32) / 255; al = a4[..., 3:4]
            pm = Image.fromarray(np.clip(np.concatenate([a4[..., :3] * al, al], -1) * 255, 0, 255).astype(np.uint8), "RGBA").resize(nxt, Image.BOX)
            q = np.array(pm, np.float32) / 255; qa = q[..., 3:4]
            box = np.array(cur.resize(nxt, Image.BOX), np.float32) / 255
            rgb = np.where(qa > 1e-3, q[..., :3] / np.maximum(qa, 1e-3), box[..., :3])
            cur = Image.fromarray(np.clip(np.concatenate([rgb, qa], -1) * 255, 0, 255).astype(np.uint8), "RGBA")
        else:
            cur = cur.resize(nxt, Image.BOX)
    bs = 16 if alpha else 8
    linear = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * bs
    pf = struct.pack("<II4sIIIII", 32, 0x4, b"DXT5" if alpha else b"DXT1", 0, 0, 0, 0, 0)
    hdr = struct.pack("<IIIIIII", 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000, h, w, linear, 0, len(mips)) + b"\0" * 44 + pf \
        + struct.pack("<IIIII", 0x1000 | 0x400000 | 0x8, 0, 0, 0, 0)
    dst = dst or os.path.splitext(src)[0] + ".dds"
    with open(dst, "wb") as f:
        f.write(b"DDS ")
        f.write(hdr)
        for m in mips: f.write(m)
    return dst, (w, h), alpha, len(mips)

if __name__ == "__main__":
    args = sys.argv[1:]
    files = []
    if args and args[0] == "--dir":
        for root, _, names in os.walk(args[1]):
            files += [os.path.join(root, n) for n in names if n.lower().endswith(".png")]
    else:
        files = args
    for f in files:
        d, size, a, n = convert(f)
        print("%s  %dx%d  %s  %d mips" % (d, size[0], size[1], "DXT5" if a else "DXT1", n))
