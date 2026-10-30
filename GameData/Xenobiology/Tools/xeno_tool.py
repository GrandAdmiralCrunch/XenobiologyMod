#!/usr/bin/env python3
"""
Xenobiology modder tool
=======================

  python xeno_tool.py validate  <GameData>            check every XENO_* node for broken links
  python xeno_tool.py outlines  <GameData> [--force]   render silhouette PNGs for every species/fossil
  python xeno_tool.py tree      <GameData> <biosphere> print a biosphere's full tree of life (spoilers!)
      validate / tree accept  --mods A,B  (folders treated as installed for :NEEDS[] and @-patches;
      default: every folder found in GameData) and read MICROBE nodes (Microbiology Expansion) if present
  python xeno_tool.py stylize   <mask.png> <out.png>   turn a rendered alpha mask (e.g. a flat-white Blender
                                                       render on a transparent background) into a field-guide outline

Silhouettes are drawn from the same PROCEDURAL proportions the plugin uses to build
the 3D creature, so the field guide outline always matches what walks around in game.
They are written to the path given by each node's `silhouette =` value (relative to
GameData, without extension). Existing files are kept unless --force is given, so you
can hand-paint replacements.

Requires Pillow (pip install pillow).
"""
import math
import os
import re
import sys
from collections import defaultdict

# --------------------------------------------------------------------------- cfg parsing

class Node:
    def __init__(self, name):
        self.name = name
        self.values = []      # list of (key, value)
        self.nodes = []
        self.src = ""

    def get(self, key, default=None):
        for k, v in self.values:
            if k == key:
                return v
        return default

    def child(self, name):
        for n in self.nodes:
            if n.name == name:
                return n
        return None


def parse_cfg(text, src=""):
    text = re.sub(r"//[^\n]*", "", text)
    tokens = re.findall(r"\{|\}|[^{}\n]+", text)
    root = Node("root")
    stack = [root]
    pending = None
    for tok in tokens:
        t = tok.strip()
        if not t:
            continue
        if t == "{":
            n = Node(pending or "")
            n.src = src
            stack[-1].nodes.append(n)
            stack.append(n)
            pending = None
        elif t == "}":
            if pending:
                pending = None
            if len(stack) > 1:
                stack.pop()
        elif "=" in t:
            k, v = t.split("=", 1)
            stack[-1].values.append((k.strip(), v.strip()))
            pending = None
        else:
            pending = t
    return root


MODS = None   # set of installed mod folder names (None = scan GameData)


def _needs_ok(name, mods):
    m = re.search(r":NEEDS\[([^\]]*)\]", name)
    if not m:
        return True
    for term in m.group(1).replace("&", ",").split(","):
        term = term.strip()
        if not term:
            continue
        neg = term.startswith("!")
        alts = term.lstrip("!").split("|")
        ok = any(a.strip() in mods for a in alts)
        if ok == neg:
            return False
    return True


def load_all(gamedata):
    """Reads every XENO_* (and MICROBE) node, honouring :NEEDS[] and applying simple @NODE[name] patches
    (%key / @key / plain key / -key), roughly the way ModuleManager would."""
    mods = MODS if MODS is not None else {d for d in os.listdir(gamedata) if os.path.isdir(os.path.join(gamedata, d))}
    nodes = defaultdict(list)
    patches = []
    for dp, _, files in os.walk(gamedata, followlinks=True):
        for f in files:
            if f.lower().endswith(".cfg"):
                p = os.path.join(dp, f)
                try:
                    txt = open(p, encoding="utf-8-sig", errors="replace").read()
                except OSError:
                    continue
                for n in parse_cfg(txt, p).nodes:
                    if not _needs_ok(n.name, mods):
                        continue
                    base = re.sub(r":.*$", "", n.name)
                    if base.startswith("@"):
                        patches.append((base, n))
                    elif base.startswith("XENO_") or base == "MICROBE":
                        n.name = base
                        nodes[base].append(n)
    for base, pn in patches:
        m = re.match(r"@(\w+)\[([^\]]+)\]", base)
        if not m:
            continue
        for tgt in nodes.get(m.group(1), []):
            if tgt.get("name") != m.group(2):
                continue
            for k, v in pn.values:
                op, key = (k[0], k[1:]) if k[0] in "%@-" else ("", k)
                tgt.values = [(a, b) for a, b in tgt.values if not (a == key and op in "%@-")]
                if op != "-":
                    tgt.values.append((key, v))
    return nodes


def split_list(s):
    return [x.strip() for x in re.split(r"[,;]", s or "") if x.strip()]


def place_microbes(nodes):
    """Mirror of XenoDatabase.LinkMicrobes: microbe name -> clade name."""
    bios = {n.get("name"): n for n in nodes["XENO_BIOSPHERE"]}
    clades = {n.get("name"): n for n in nodes["XENO_CLADE"]}
    def depth(c):
        d, cur = 0, clades.get(c)
        while cur is not None and cur.get("parent") in clades and d < 50:
            d += 1; cur = clades[cur.get("parent")]
        return d
    micro = {n.get("name"): n for n in nodes["MICROBE"]}
    place, problems = {}, []
    for cn, c in clades.items():
        for m in split_list(c.get("microbes")):
            if m not in micro:
                continue
            if m in place:
                problems.append(f"microbe '{m}' listed by both {place[m]} and {cn}")
            place[m] = cn
    for mn, m in micro.items():
        cat = (m.get("category") or "Unknown").strip()
        if mn in place or cat in ("Debris", "Unknown"):
            continue
        bio = next((b for b in bios.values() if (b.get("body") or "").lower() == (m.get("homePlanet") or "").strip().lower()), None)
        if bio is None:
            continue
        best = None
        for cn, c in clades.items():
            if c.get("biosphere") == bio.get("name") and cat.lower() in [x.lower() for x in split_list(c.get("microbeCategories"))]:
                if best is None or depth(cn) > depth(best):
                    best = cn
        if best is None and bio.get("microbeClade") in clades:
            best = bio.get("microbeClade")
        if best:
            place[mn] = best
    return place, problems


def color(s, default=(0.6, 0.6, 0.6)):
    if not s:
        return default
    try:
        parts = [float(x) for x in s.split(",")]
        return tuple(parts[:3])
    except ValueError:
        return default


def fnum(n, key, d):
    try:
        return float(n.get(key, d))
    except (TypeError, ValueError):
        return d

# --------------------------------------------------------------------------- validate

def validate(gamedata):
    nodes = load_all(gamedata)
    bios = {n.get("name"): n for n in nodes["XENO_BIOSPHERE"]}
    clades = {n.get("name"): n for n in nodes["XENO_CLADE"]}
    species = {n.get("name"): n for n in nodes["XENO_LIFEFORM"]}
    fossils = {n.get("name"): n for n in nodes["XENO_FOSSIL"]}
    pans = {n.get("name"): n for n in nodes["XENO_PANSPERMIA"]}
    problems = []
    placed, mp = place_microbes(nodes)
    micro_names = {n.get("name") for n in nodes["MICROBE"]}

    def p(msg):
        problems.append(msg)
    for x in mp:
        p(x)

    for kind, d in (("XENO_BIOSPHERE", bios), ("XENO_CLADE", clades), ("XENO_LIFEFORM", species), ("XENO_FOSSIL", fossils), ("XENO_PANSPERMIA", pans)):
        if None in d:
            p(f"{kind} without a name in {d[None].src}")
        if len(d) != len(nodes[kind]):
            p(f"duplicate names among {kind} nodes")

    for name, b in bios.items():
        if not b.get("body"):
            p(f"biosphere {name}: missing body")
        r = b.get("rootClade")
        if r and r not in clades:
            p(f"biosphere {name}: rootClade '{r}' not defined")
    for name, c in clades.items():
        if c.get("biosphere") not in bios:
            p(f"clade {name}: biosphere '{c.get('biosphere')}' not defined")
        par = c.get("parent")
        if par:
            if par not in clades:
                p(f"clade {name}: parent '{par}' not defined")
            elif clades[par].get("biosphere") != c.get("biosphere"):
                p(f"clade {name}: parent '{par}' is in a different biosphere (use XENO_PANSPERMIA for cross-world links)")
        seen, cur = set(), c
        while cur is not None and cur.get("parent"):
            if cur.get("name") in seen:
                p(f"clade {name}: parent cycle")
                break
            seen.add(cur.get("name"))
            cur = clades.get(cur.get("parent"))
    for name, s in species.items():
        if s.get("clade") not in clades:
            p(f"lifeform {name}: clade '{s.get('clade')}' not defined")
        else:
            bio = bios.get(clades[s.get("clade")].get("biosphere"))
            if bio is not None and bio.get("body") != s.get("body"):
                p(f"lifeform {name}: body '{s.get('body')}' differs from its biosphere's body '{bio.get('body')}'")
        so = s.get("lifeStageOf")
        if so and so not in species:
            p(f"lifeform {name}: lifeStageOf '{so}' not defined")
        for col in [n for n in s.nodes if n.name == "COLONY"]:
            cs = col.get("species")
            if cs not in species: p(f"lifeform {name}: COLONY species '{cs}' not defined")
            elif species[cs].get("body") != s.get("body"): p(f"lifeform {name}: COLONY species '{cs}' lives on another body")
        for d in split_list(s.get("diet")):
            if re.match(r"^[a-z]+_[a-z0-9_]+$", d) and d not in species:
                p(f"lifeform {name}: diet '{d}' looks like a lifeform id but is not defined")
        if s.child("BURST") is not None and s.get("habitat", "Ground") == "Air":
            p(f"lifeform {name}: BURST on an Air creature will never trigger")
        hab = s.get("habitat", "Ground")
        if hab not in ("Ground", "Water", "Underwater", "Air", "Flyer"):
            p(f"lifeform {name}: unknown habitat '{hab}'")
        proc = s.child("PROCEDURAL")
        fixed = s.get("unique", "false").lower() == "true" and s.get("sessile", "false").lower() == "true"   # lair-only fixed life lives in the lair model
        if proc is None and s.child("MODEL") is None and not fixed:
            p(f"lifeform {name}: no PROCEDURAL or MODEL node (defaults will be used)")
    for name, f in fossils.items():
        for e in [x.strip() for x in (f.get("evidenceFor") or "").split(",") if x.strip()]:
            if e not in clades and e not in pans:
                p(f"fossil {name}: evidenceFor '{e}' is neither a clade nor a panspermia event")
    for f in nodes.get("XENO_FEATURE", []):
        fn = f.get("name")
        if not fn or not f.get("body"):
            p(f"XENO_FEATURE without name/body in {f.src}")
        if f.get("kind", "Geyser") not in ("Geyser", "Fumarole"):
            p(f"feature {fn}: unknown kind '{f.get('kind')}'")
        a = f.get("attracts")
        if a and a not in species:
            p(f"feature {fn}: attracts '{a}', which is not defined")
        elif a and species[a].get("body") != f.get("body"):
            p(f"feature {fn}: attracts '{a}', which lives on another body")
    for name, pa in pans.items():
        if pa.get("sourceClade") not in clades:
            p(f"panspermia {name}: sourceClade '{pa.get('sourceClade')}' not defined")
        if pa.get("targetBiosphere") not in bios:
            p(f"panspermia {name}: targetBiosphere '{pa.get('targetBiosphere')}' not defined")
        tc = pa.get("targetClade")
        if tc and (tc not in clades or clades[tc].get("biosphere") != pa.get("targetBiosphere")):
            p(f"panspermia {name}: targetClade '{tc}' is not a clade of {pa.get('targetBiosphere')}")

    # reachability of reveal thresholds
    def species_under(c):
        out = [s for s in species.values() if s.get("clade") == c] + [m for m, cl in placed.items() if cl == c] * 2   # microbe: discovered + lab
        for ch in clades.values():
            if ch.get("parent") == c:
                out += species_under(ch.get("name"))
        return out

    def desc(c):
        out = []
        for ch in clades.values():
            if ch.get("parent") == c:
                out.append(ch.get("name"))
                out += desc(ch.get("name"))
        return out

    def fossil_points(target):
        return sum(int(fnum(f, "evidence", 1)) for f in fossils.values()
                   if target in [x.strip() for x in (f.get("evidenceFor") or "").split(",")])

    for name, c in clades.items():
        maxscore = len(species_under(name)) + fossil_points(name) + sum(fossil_points(d) for d in desc(name))
        thr = int(fnum(c, "revealThreshold", 2))
        if maxscore < thr:
            p(f"clade {name}: can never be revealed (max evidence {maxscore} < revealThreshold {thr})")
    for name, pa in pans.items():
        maxscore = fossil_points(name) + 2 + sum(1 for m in split_list(pa.get("microbeEvidence")) if m in micro_names)
        thr = int(fnum(pa, "revealThreshold", 3))
        if maxscore < thr:
            p(f"panspermia {name}: can never be revealed (max evidence {maxscore} < revealThreshold {thr})")

    print(f"{len(bios)} biospheres, {len(clades)} clades, {len(species)} lifeforms, {len(fossils)} fossils, {len(pans)} panspermia events, {len(placed)}/{len(micro_names)} microbes placed")
    for x in problems:
        print("  PROBLEM:", x)
    if not problems:
        print("  no problems found")
    return problems

# --------------------------------------------------------------------------- tree print

def print_tree(gamedata, bio):
    nodes = load_all(gamedata)
    clades = {n.get("name"): n for n in nodes["XENO_CLADE"]}
    species = [n for n in nodes["XENO_LIFEFORM"]]
    b = next((n for n in nodes["XENO_BIOSPHERE"] if n.get("name") == bio), None)
    if b is None:
        print("unknown biosphere", bio)
        return
    placed, _ = place_microbes(nodes)

    def rec(c, ind):
        n = clades[c]
        for pa in nodes["XENO_PANSPERMIA"]:
            if pa.get("targetBiosphere") == bio and (pa.get("targetClade") or b.get("rootClade")) == c:
                print("  " * ind + f"<~~ {pa.get('displayName')} from clade {pa.get('sourceClade')}")
        tag = "  (grouping: no common ancestor)" if n.get("grouping") == "true" else ""
        print("  " * ind + f"[{n.get('rank', 'Clade')}] {n.get('displayName')}  (reveal {n.get('revealThreshold', 2)}){tag}")
        for ch in sorted([x for x in clades.values() if x.get("parent") == c], key=lambda x: x.get("name")):
            rec(ch.get("name"), ind + 1)
        for s in species:
            if s.get("clade") == c:
                print("  " * (ind + 1) + f"- {s.get('displayName')} ({s.get('habitat', 'Ground')}{', ' + s.get('lifeStage') + ' of ' + s.get('lifeStageOf') if s.get('lifeStageOf') else ''})")
        for m in sorted(x for x, cl in placed.items() if cl == c):
            print("  " * (ind + 1) + f"~ {m} (microbe)")
    rec(b.get("rootClade"), 0)

# --------------------------------------------------------------------------- outlines

S = 4            # supersampling
SIZE = 256


class Pen:
    def __init__(self, img_size=SIZE * S):
        from PIL import Image, ImageDraw
        self.Image = Image
        self.mask = Image.new("L", (img_size, img_size), 0)
        self.detail = Image.new("L", (img_size, img_size), 0)
        self.d = ImageDraw.Draw(self.mask)
        self.dd = ImageDraw.Draw(self.detail)
        self.shapes = []

    # all shape coordinates are in "creature units"; transformed later
    def ellipse(self, cx, cy, w, h, rot=0):
        self.shapes.append(("ell", cx, cy, w, h, rot))

    def poly(self, pts):
        self.shapes.append(("poly", pts))

    def line(self, pts, width):
        self.shapes.append(("line", pts, width))

    def eye(self, cx, cy, r):
        self.shapes.append(("eye", cx, cy, r))

    def bounds(self):
        xs, ys = [], []
        for s in self.shapes:
            if s[0] == "ell":
                _, cx, cy, w, h, _r = s
                m = max(w, h) / 2
                xs += [cx - m, cx + m]; ys += [cy - m, cy + m]
            elif s[0] in ("poly", "line"):
                for x, y in s[1]:
                    xs.append(x); ys.append(y)
                if s[0] == "line":
                    xs += [min(xs) - s[2], max(xs) + s[2]]; ys += [min(ys) - s[2], max(ys) + s[2]]
        return min(xs), min(ys), max(xs), max(ys)

    def render(self):
        from PIL import ImageFilter, ImageChops
        x0, y0, x1, y1 = self.bounds()
        pad = 0.08
        span = max(x1 - x0, y1 - y0) * (1 + 2 * pad)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        k = SIZE * S / span

        def T(x, y):
            return ((x - cx) * k + SIZE * S / 2, SIZE * S / 2 - (y - cy) * k)

        for s in self.shapes:
            if s[0] == "ell":
                _, ex, ey, w, h, rot = s
                pts = []
                for i in range(48):
                    a = i / 48 * math.tau
                    px, py = math.cos(a) * w / 2, math.sin(a) * h / 2
                    c, sn = math.cos(rot), math.sin(rot)
                    pts.append(T(ex + px * c - py * sn, ey + px * sn + py * c))
                self.d.polygon(pts, fill=255)
            elif s[0] == "poly":
                self.d.polygon([T(*p) for p in s[1]], fill=255)
            elif s[0] == "line":
                pts = [T(*p) for p in s[1]]
                wpx = max(2, int(s[2] * k))
                self.d.line(pts, fill=255, width=wpx, joint="curve")
                r = wpx / 2
                for px, py in (pts[0], pts[-1]):
                    self.d.ellipse([px - r, py - r, px + r, py + r], fill=255)
        for s in self.shapes:
            if s[0] == "eye":
                _, ex, ey, r = s
                px, py = T(ex, ey)
                rr = max(3 * S, r * k)
                self.dd.ellipse([px - rr, py - rr, px + rr, py + rr], fill=255)

        mask = self.mask
        edge_w = 5 * S
        inner = mask.filter(ImageFilter.MinFilter(edge_w * 2 + 1 if edge_w * 2 + 1 <= 99 else 99))
        outline = ImageChops.subtract(mask, inner)
        # composite: outline white, fill light grey with soft vertical shading, eyes dark
        rgba = self.Image.new("RGBA", mask.size, (0, 0, 0, 0))
        fill = self.Image.new("RGBA", mask.size, (205, 205, 205, 255))
        grad = self.Image.linear_gradient("L").resize(mask.size)
        shade = self.Image.merge("RGBA", [grad.point(lambda v: 255 - v // 5)] * 3 + [self.Image.new("L", mask.size, 255)])
        fill = ImageChops.multiply(fill, shade)
        rgba.paste(fill, (0, 0), mask)
        rgba.paste((255, 255, 255, 255), (0, 0), outline)
        rgba.paste((25, 25, 30, 255), (0, 0), ImageChops.multiply(self.detail, mask))
        return rgba.resize((SIZE, SIZE), self.Image.LANCZOS)


def draw_species(n):
    proc = n.child("PROCEDURAL")
    g = (lambda k, d: fnum(proc, k, d)) if proc is not None else (lambda k, d: d)
    plan = (proc.get("bodyPlan") if proc is not None else None) or "Quadruped"
    L, W, Lg, H = g("bodyLength", 1), g("bodyWidth", 0.45), g("legLength", 0.5), g("headSize", 0.3)
    tail, span, segs, eyes = g("tailLength", 0.5), g("wingSpan", 2), int(g("segments", 8)), int(g("eyes", 2))
    pen = Pen()
    # creatures face right (+x)
    if plan in ("Quadruped", "Hexapod"):
        by = Lg + W * 0.35
        if plan == "Hexapod":
            pen.ellipse(L * 0.05, by, L * 0.4, W * 0.7)
            pen.ellipse(-L * 0.35, by + W * 0.05, L * 0.6, W * 0.85)
            for i, x in enumerate((L * 0.28, 0.0, -L * 0.28)):
                for side, k in ((1, 1.0), (-1, 0.75)):
                    dx = (0.14 if i == 0 else (-0.04 if i == 1 else -0.16)) * L * k
                    knee = (x + dx * 0.6, by + W * 0.2 * k)
                    pen.line([(x + side * 0.02, by - W * 0.1), knee, (x + dx * 1.3, 0)], max(0.04, W * 0.12))
            hx, hy = L * 0.5 + H * 0.3, by + W * 0.25
            pen.ellipse(hx, hy, H * 1.2, H * 0.85)
            pen.line([(hx + H * 0.2, hy + H * 0.3), (hx + H * 0.9, hy + H * 1.3)], 0.03)
            pen.line([(hx + H * 0.05, hy + H * 0.35), (hx + H * 0.5, hy + H * 1.5)], 0.03)
        else:
            pen.ellipse(0, by, L, W * 0.85)
            pen.ellipse(-L * 0.05, by + W * 0.3, L * 0.8, W * 0.4)
            leg = max(0.08, W * 0.3)
            for x in (L * 0.3, -L * 0.3):
                pen.line([(x, by - W * 0.1), (x + 0.04 * L, Lg * 0.55), (x - 0.01, leg * 0.3)], leg)
                pen.line([(x - 0.1 * L, by - W * 0.1), (x - 0.13 * L, Lg * 0.5), (x - 0.08 * L, leg * 0.3)], leg * 0.85)
                pen.ellipse(x + leg * 0.2, leg * 0.2, leg * 1.6, leg * 0.6)
            hx, hy = L * 0.5 + H * 0.3, by + W * 0.25
            pen.line([(L * 0.35, by + W * 0.1), (hx, hy)], H * 0.6)
            pen.ellipse(hx, hy, H * 1.2, H * 0.85)
            if tail > 0.01:
                pts = [(-L * 0.5, by + W * 0.1)]
                for i in range(1, 5):
                    t = i / 4
                    pts.append((-L * 0.5 - tail * t, by + W * 0.1 - math.sin(t * 2) * tail * 0.25))
                pen.line(pts, W * 0.18)
        if eyes:
            pen.eye(hx + H * 0.3, hy + H * 0.15, H * 0.1)
    elif plan == "Serpent":
        n_s = max(4, segs)
        pts = []
        for i in range(n_s * 3):
            t = i / (n_s * 3 - 1)
            pts.append((L * 0.5 - t * L, math.sin(t * math.tau * 1.3) * W * 1.6))
        for i, (x, y) in enumerate(pts):
            t = i / (len(pts) - 1)
            r = W * (1 - 0.65 * t * t)
            pen.ellipse(x, y, r * 1.3, r)
        hx, hy = pts[0][0] + H * 0.5, pts[0][1] + W * 0.1
        pen.ellipse(hx, hy, H * 1.4, H * 0.8)
        if eyes:
            pen.eye(hx + H * 0.3, hy + H * 0.15, H * 0.12)
    elif plan == "Avian":
        by = Lg + W * 0.5
        pen.ellipse(0, by, L, W * 0.9, rot=0.12)
        hx, hy = L * 0.5 + H * 0.2, by + W * 0.35
        pen.ellipse(hx, hy, H, H)
        pen.poly([(hx + H * 0.35, hy + H * 0.1), (hx + H * 1.1, hy - H * 0.05), (hx + H * 0.35, hy - H * 0.2)])
        half = span / 2
        pen.poly([(L * 0.2, by + W * 0.2), (-L * 0.35, by + W * 0.15), (-L * 0.15 - half * 0.35, by + half * 0.8), (L * 0.05, by + half * 0.55)])
        pen.poly([(-L * 0.45, by), (-L * 0.5 - tail, by + tail * 0.25), (-L * 0.5 - tail * 0.9, by - tail * 0.2)])
        pen.line([(0, by - W * 0.3), (0.05, 0)], 0.04)
        if eyes:
            pen.eye(hx + H * 0.15, hy + H * 0.15, H * 0.1)
    elif plan == "Fish":
        pen.ellipse(0, 0, L, W)
        pen.poly([(-L * 0.42, 0), (-L * 0.5 - tail * 0.7, W * 0.65), (-L * 0.5 - tail * 0.5, 0), (-L * 0.5 - tail * 0.7, -W * 0.65)])
        pen.poly([(L * 0.1, W * 0.4), (-L * 0.2, W * 0.4), (-L * 0.1, W * 0.85)])
        pen.poly([(L * 0.15, -W * 0.25), (L * 0.0, -W * 0.25), (-L * 0.05, -W * 0.6)])
        if eyes:
            pen.eye(L * 0.33, W * 0.1, W * 0.08)
    elif plan == "Floater":
        Wd = W * 2
        bell_y = L
        pen.ellipse(0, bell_y, Wd, Wd * 0.6)
        pen.poly([(-Wd / 2, bell_y), (Wd / 2, bell_y), (Wd * 0.4, bell_y - Wd * 0.12), (-Wd * 0.4, bell_y - Wd * 0.12)])
        nt = max(3, min(12, segs))
        for i in range(nt):
            x0 = (i / (nt - 1) - 0.5) * Wd * 0.75
            pts = []
            for j in range(9):
                t = j / 8
                pts.append((x0 + math.sin(t * 5 + i) * Wd * 0.06, bell_y - Wd * 0.12 - t * L * 0.9))
            pen.line(pts, 0.035)
        if eyes:
            pen.eye(Wd * 0.2, bell_y + Wd * 0.05, H * 0.1)
    else:  # Blob
        Wd = W * 2
        pen.ellipse(0, Wd * 0.4, Wd * L, Wd * 0.8)
        for i in range(max(1, eyes)):
            pen.eye(Wd * L * 0.3 - i * 0.08, Wd * 0.55 + (i % 2) * 0.06, H * 0.12)
    return pen.render()


def draw_fossil(form):
    pen = Pen()
    if form == "Shell":
        for i in range(40):
            a = i * 0.42
            r = 0.04 * math.exp(0.075 * i)
            s = 0.05 + r * 0.5
            pen.ellipse(math.cos(a) * r, math.sin(a) * r, s, s)
    elif form == "Bones":
        for i in range(10):
            pen.ellipse(-0.6 + i * 0.12, 0, 0.1, 0.08)
            if 1 < i < 8:
                pen.line([(-0.6 + i * 0.12, 0), (-0.62 + i * 0.12, -0.22 - 0.02 * (i % 3))], 0.03)
        pen.ellipse(0.65, 0.04, 0.3, 0.18)
        pen.eye(0.7, 0.07, 0.03)
    elif form == "Trackway":
        for i in range(5):
            x = -0.8 + i * 0.4
            y = 0.15 if i % 2 else -0.15
            for t in (-1, 0, 1):
                pen.ellipse(x + 0.07, y + t * 0.06, 0.12, 0.035, rot=t * 0.4)
            pen.ellipse(x - 0.02, y, 0.08, 0.07)
    elif form == "Stromatolite":
        for i, (x, h) in enumerate(((-0.5, 0.5), (-0.15, 0.75), (0.2, 0.6), (0.5, 0.4))):
            pen.poly([(x - 0.17, 0), (x + 0.17, 0), (x + 0.15, h), (x - 0.15, h)])
            pen.ellipse(x, h, 0.3, 0.16)
        pen.poly([(-0.8, 0), (0.8, 0), (0.8, -0.08), (-0.8, -0.08)])
    elif form == "Amber":
        pen.ellipse(0, 0, 0.9, 0.62, rot=0.2)
        pen.eye(0.02, 0.02, 0.07)
        pen.eye(0.12, -0.05, 0.03)
    else:  # unknown: a question mark
        pts = [(math.cos(a) * 0.32, 0.35 + math.sin(a) * 0.3) for a in [math.pi * (1 - i / 12 * 1.5) for i in range(13)]]
        pts += [(0.0, -0.05), (0.0, -0.2)]
        pen.line(pts, 0.14)
        pen.ellipse(0, -0.45, 0.17, 0.17)
    return pen.render()


def icon_path(gamedata, rel):
    """Field-guide images live under PluginData (KSP's GameDatabase skips it), loaded by the plugin only when shown."""
    rel = rel.replace("/Textures/Silhouettes/", "/PluginData/Silhouettes/").replace("/Textures/Portraits/", "/PluginData/Portraits/")
    return os.path.join(gamedata, *rel.split("/")) + ".png"


def write_png(img, gamedata, rel, force):
    path = icon_path(gamedata, rel)
    if os.path.exists(path) and not force:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return True


def outlines(gamedata, force):
    nodes = load_all(gamedata)
    made = 0
    for s in nodes["XENO_LIFEFORM"]:
        rel = s.get("silhouette")
        if rel and write_png(draw_species(s), gamedata, rel, force):
            made += 1
            print("  species", rel)
    forms = {}
    for f in nodes["XENO_FOSSIL"]:
        rel = f.get("silhouette")
        if rel:
            forms[rel] = f.get("form", "Shell")
    for rel, form in forms.items():
        if write_png(draw_fossil(form), gamedata, rel, force):
            made += 1
            print("  fossil ", rel)
    print(f"{made} outline(s) written")


def stylize(mask_path, out_path):
    """Alpha mask -> 256px outline in the same style as the procedural silhouettes."""
    from PIL import Image, ImageFilter, ImageChops
    src = Image.open(mask_path).convert("RGBA")
    alpha = src.split()[3]
    bbox = alpha.point(lambda a: 255 if a > 20 else 0).getbbox()
    if bbox is None:
        raise SystemExit("mask is empty")
    alpha = alpha.crop(bbox)
    big = SIZE * S
    pad = int(big * 0.07)
    w, h = alpha.size
    k = (big - 2 * pad) / max(w, h)
    alpha = alpha.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    mask = Image.new("L", (big, big), 0)
    mask.paste(alpha, ((big - alpha.width) // 2, (big - alpha.height) // 2))
    mask = mask.point(lambda a: 255 if a > 110 else 0)
    inner = mask.filter(ImageFilter.MinFilter(41))
    outline = ImageChops.subtract(mask, inner)
    fill = Image.new("RGBA", mask.size, (205, 205, 205, 255))
    grad = Image.linear_gradient("L").resize(mask.size)
    shade = Image.merge("RGBA", [grad.point(lambda v: 255 - v // 5)] * 3 + [Image.new("L", mask.size, 255)])
    fill = ImageChops.multiply(fill, shade)
    rgba = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    rgba.paste(fill, (0, 0), mask)
    rgba.paste((255, 255, 255, 255), (0, 0), outline)
    rgba.resize((SIZE, SIZE), Image.LANCZOS).save(out_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd, gd = sys.argv[1], sys.argv[2]
    if "--mods" in sys.argv:
        MODS = set(split_list(sys.argv[sys.argv.index("--mods") + 1]))
    if cmd == "validate":
        sys.exit(1 if validate(gd) else 0)
    elif cmd == "outlines":
        outlines(gd, "--force" in sys.argv)
    elif cmd == "stylize":
        stylize(sys.argv[2], sys.argv[3])
    elif cmd == "tree":
        print_tree(gd, sys.argv[3])
    else:
        print(__doc__)
