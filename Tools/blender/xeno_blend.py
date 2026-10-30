# Xenobiology — shared Blender helpers for the creature pipeline.
# Usage inside a build script:   exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
# Conventions: creature faces +Y, Z up, feet on Z = 0 (flyers/swimmers: origin at the body centre).
import bpy, bmesh, math, random, os, importlib
from mathutils import Vector, Matrix, Quaternion, noise
from mathutils.bvhtree import BVHTree

KSP_GAMEDATA = r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData"
XENO_DIR = os.path.join(KSP_GAMEDATA, "Xenobiology")
PREVIEW_DIR = os.path.join(os.path.dirname(KSP_GAMEDATA), "XenobiologyDev", "previews")   # outside GameData!

# ============================================================================ scene
def new_scene(name):
    if name in bpy.data.scenes:
        scn = bpy.data.scenes[name]
        for o in list(scn.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        scn = bpy.data.scenes.new(name)
    bpy.context.window.scene = scn
    scn.render.fps = 30
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.metaballs, bpy.data.curves):
        for d in [d for d in coll if d.users == 0]: coll.remove(d)
    return scn

def link(o):
    bpy.context.scene.collection.objects.link(o); return o

def select_only(objs, active=None):
    for o in bpy.context.scene.objects: o.select_set(o in objs)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)

# ============================================================================ body from a skeleton graph
class Skel:
    """Named points (pos, side radius, vertical radius) and edges; drives metaballs and bones."""
    def __init__(self, scale=1.0):
        self.P = {}; self.E = []; self.S = scale
    def v(self, n, x, y, z, rs, rv=None):
        self.P[n] = (Vector((x, y, z)) * self.S, rs * self.S, (rv if rv is not None else rs) * self.S)
    def e(self, *chain):
        for a, b in zip(chain, chain[1:]): self.E.append((a, b))
    def pt(self, n): return self.P[n][0] if isinstance(n, str) else Vector(n) * self.S
    def mirror(self, n, x, y, z, rs, rv=None):
        self.v(n + "L", x, y, z, rs, rv); self.v(n + "R", -x, y, z, rs, rv)

def metaball_body(name, sk, voxel, faces, mb_scale=1.22, stiffness=2.0, smooth=3, floor=True):
    mb = bpy.data.metaballs.new(name + "_mb")
    mb.resolution = voxel * 1.3; mb.render_resolution = voxel * 1.3; mb.threshold = 0.6
    for a_, b_ in sk.E:
        pa, ras, rav = sk.P[a_]; pb, rbs, rbv = sk.P[b_]
        L = (pb - pa).length; step = max(voxel * 0.8, 0.35 * min(ras, rav, rbs, rbv)); n = max(2, int(math.ceil(L / step)) + 1)
        for i in range(n):
            t = i / (n - 1); el = mb.elements.new(); el.co = pa.lerp(pb, t)
            rs = (ras + (rbs - ras) * t) * mb_scale; rv = (rav + (rbv - rav) * t) * mb_scale; r = max(rs, rv)
            el.type = 'ELLIPSOID'; el.radius = r; el.size_x = rs / r; el.size_y = 1.0; el.size_z = rv / r; el.stiffness = stiffness
    mbo = link(bpy.data.objects.new(name + "_mb", mb))
    dg = bpy.context.evaluated_depsgraph_get()
    body = link(bpy.data.objects.new(name + "_body", bpy.data.meshes.new_from_object(mbo.evaluated_get(dg))))
    bpy.data.objects.remove(mbo, do_unlink=True)
    bpy.data.metaballs.remove(mb)
    select_only([body])
    rm = body.modifiers.new("Remesh", 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = voxel; rm.adaptivity = 0
    if smooth:
        sm = body.modifiers.new("Smooth", 'SMOOTH'); sm.factor = 0.6; sm.iterations = smooth
    dc = body.modifiers.new("Decimate", 'DECIMATE')
    dg = bpy.context.evaluated_depsgraph_get()
    dc.ratio = min(1.0, faces / max(1, len(body.evaluated_get(dg).data.polygons)))
    for m in list(body.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
    body.data.name = name
    for p in body.data.polygons: p.use_smooth = True
    if floor:
        for v in body.data.vertices:
            if v.co.z < 0: v.co.z = 0
    return body

def displace(obj, fn):
    """fn(co, normal) -> new co"""
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.normal_update()
    for v in bm.verts: v.co = fn(v.co.copy(), v.normal.copy())
    bm.to_mesh(obj.data); bm.free()

# ============================================================================ rig
def make_rig(name, sk, bones, nondeform=()):
    """bones: list of (name, head, tail, parent, connect). head/tail = skeleton point names or xyz tuples (unscaled)."""
    ad = bpy.data.armatures.new(name + "_rig"); rig = link(bpy.data.objects.new(name + "_rig", ad))
    select_only([rig]); bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    for nm, h, t, par, con in bones:
        b = eb.new(nm); b.head = sk.pt(h); b.tail = sk.pt(t)
        if par: b.parent = eb[par]; b.use_connect = con
    for b in eb:
        d = (b.tail - b.head).normalized()
        b.align_roll(Vector((0, 0, 1)) if abs(d.z) < 0.7 else Vector((0, -1, 0)))
    bpy.ops.object.mode_set(mode='OBJECT')
    for nm in nondeform: ad.bones[nm].use_deform = False
    return rig

def skin(body, rig, nondeform=()):
    select_only([body, rig], rig)
    mode = "heat"
    try: bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except Exception:
        mode = "envelope"; bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
    for nm in nondeform: rig.data.bones[nm].use_deform = True
    return mode

def bvh_of(obj):
    me = obj.data
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [list(p.vertices) for p in me.polygons])

def ray(bvh, origin, d, dist=500.0):
    loc, nrm, i, dd = bvh.ray_cast(Vector(origin), Vector(d).normalized(), dist)
    return loc, nrm

# ============================================================================ detail parts with explicit weights
class Part:
    def __init__(self, name, pid):
        self.name = name; self.pid = pid; self.bm = bmesh.new(); self.w = []; self.tip = []
    def v(self, co, weights, tip=0.0):
        if isinstance(weights, str): weights = [(weights, 1.0)]
        vv = self.bm.verts.new(Vector(co)); self.w.append(weights); self.tip.append(tip); return vv
    def f(self, verts):
        try: return self.bm.faces.new(verts)
        except ValueError: return None
    def grid(self, rows, flip=False, thickness=0.004):
        """rows: [[(co, weights, tip), ...], ...] -> double sided membrane"""
        for side in (1, -1):
            vs = [[self.v(Vector(co) + Vector((0, 0, side * thickness)), w, tp) for co, w, tp in row] for row in rows]
            for j in range(len(vs) - 1):
                for k in range(len(vs[j]) - 1):
                    q = [vs[j][k], vs[j][k+1], vs[j+1][k+1], vs[j+1][k]]
                    self.f(q[::-1] if (side > 0) != flip else q)
    def tube(self, a, b, r0, r1, bone, rings=5, segs=6, cap=True, tip_from=0.0):
        a = Vector(a); b = Vector(b); d = b - a; L = d.length; d.normalize(); q = d.to_track_quat('Z', 'Y').to_matrix(); R = []
        for i in range(rings + 1):
            t = i / rings; rr = r0 + (r1 - r0) * t
            R.append([self.v(a + d * L * t + q @ Vector((math.cos(k / segs * math.tau) * rr, math.sin(k / segs * math.tau) * rr, 0)), bone, tip_from + (1 - tip_from) * t) for k in range(segs)])
        for i in range(rings):
            for k in range(segs): self.f([R[i][k], R[i][(k+1) % segs], R[i+1][(k+1) % segs], R[i+1][k]])
        if cap: self.f(R[0][::-1]); self.f(R[-1])
    def cone(self, base, direction, length, r0, bone, segs=6, flat=1.0, bend=None):
        base = Vector(base); d = Vector(direction).normalized(); q = d.to_track_quat('Z', 'Y').to_matrix()
        rings = []
        for i, (t, rr) in enumerate(((0.0, r0), (0.5, r0 * 0.6), (1.0, 0.0))):
            off = (Vector(bend) * (t * t) * length) if bend else Vector()
            c = base + d * length * t + off
            if rr == 0: rings.append([self.v(c, bone, 1.0)])
            else: rings.append([self.v(c + q @ Vector((math.cos(k / segs * math.tau) * rr, math.sin(k / segs * math.tau) * rr * flat, 0)), bone, t) for k in range(segs)])
        for k in range(segs):
            self.f([rings[0][k], rings[0][(k+1) % segs], rings[1][(k+1) % segs], rings[1][k]])
            self.f([rings[1][k], rings[1][(k+1) % segs], rings[2][0]])
        self.f(rings[0][::-1])
    def sphere(self, c, r, bone, scale=(1, 1, 1), sub=2, jitter=0.0, tip=0.0):
        res = bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=r)
        for vv in res["verts"]:
            co = vv.co.copy()
            if jitter: co += co.normalized() * (noise.noise(co * 3.0 + Vector(c)) * jitter * r)
            vv.co = Vector(c) + Vector((co.x * scale[0], co.y * scale[1], co.z * scale[2]))
            self.w.append([(bone, 1.0)] if isinstance(bone, str) else bone); self.tip.append(tip)
    def finish(self):
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        for p in me.polygons: p.use_smooth = True
        o = link(bpy.data.objects.new(self.name, me)); groups = {}
        for vi, wl in enumerate(self.w):
            for bn, w in wl:
                if w <= 0: continue
                if bn not in groups: groups[bn] = o.vertex_groups.new(name=bn)
                groups[bn].add([vi], w, 'REPLACE')
        a = me.attributes.new("part", 'INT', 'FACE')
        for i in range(len(me.polygons)): a.data[i].value = self.pid
        tp = me.attributes.new("tipf", 'FLOAT', 'POINT')
        for i, t in enumerate(self.tip): tp.data[i].value = t
        return o

def tag_body(body, pid=0):
    me = body.data
    if "part" not in me.attributes:
        a = me.attributes.new("part", 'INT', 'FACE')
        for i in range(len(me.polygons)): a.data[i].value = pid
    if "tipf" not in me.attributes: me.attributes.new("tipf", 'FLOAT', 'POINT')

def join_all(body, parts, name):
    tag_body(body)
    select_only([body] + parts, body)
    if parts: bpy.ops.object.join()
    body.name = name + "_body"
    return body

def finalize(name, body, rig):
    root = link(bpy.data.objects.new(name, None)); rig.parent = root
    return root

# ============================================================================ animation (DOF helper)
class Anim:
    """Rotate bones by intent rather than raw axes: fwd (tail toward +Y), up (+Z), out (away from midline), yaw (+X)."""
    def __init__(self, rig):
        self.rig = rig; self.arm = rig.data; self.AX = {}
    def axis(self, b, wd):
        key = (b, tuple(round(c, 3) for c in wd))
        if key in self.AX: return self.AX[key]
        bone = self.arm.bones[b]; m = bone.matrix_local.to_3x3(); vec = bone.tail_local - bone.head_local
        best = None
        for local in (Vector((1, 0, 0)), Vector((0, 0, 1))):
            s = (m @ local).normalized().cross(vec).dot(Vector(wd))
            if best is None or abs(s) > abs(best[1]): best = (local, s)
        self.AX[key] = best[0] * (1 if best[1] > 0 else -1); return self.AX[key]
    def side(self, b): return 1 if self.arm.bones[b].head_local.x >= 0 else -1
    def rot(self, b, fwd=0.0, up=0.0, out=0.0, yaw=0.0, roll=0.0):
        q = Quaternion()
        if fwd: q = q @ Quaternion(self.axis(b, (0, 1, 0)), math.radians(fwd))
        if up: q = q @ Quaternion(self.axis(b, (0, 0, 1)), math.radians(up))
        if out: q = q @ Quaternion(self.axis(b, (self.side(b), 0, 0)), math.radians(out))
        if yaw: q = q @ Quaternion(self.axis(b, (1, 0, 0)), math.radians(yaw))
        if roll: q = q @ Quaternion((0, 1, 0), math.radians(roll))
        return q
    def local_off(self, b, v): return self.arm.bones[b].matrix_local.to_3x3().inverted() @ Vector(v)
    def bake(self, clips, root_bone="body", default=None):
        """clips: [(name, fn(t)->(P, offset), frames, step, oneshot)]"""
        rig = self.rig; scn = bpy.context.scene; scn.frame_start = 0
        if rig.animation_data is None: rig.animation_data_create()
        ad = rig.animation_data
        for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
        ad.action = None
        for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
        made = []
        scaled = set()                               # bones that scale in any clip get scale keys in every clip
        for name, fn, frames, step, oneshot in clips:
            for f in (0, frames // 3, frames // 2, (2 * frames) // 3, frames):
                P, _ = fn(f / frames if oneshot else (f / frames) % 1.0)
                scaled.update(k for k, v in P.items() if isinstance(v, tuple))
        for name, fn, frames, step, oneshot in clips:
            an = rig.name.replace("_rig", "") + "_" + name
            if an in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[an])
            act = bpy.data.actions.new(an); act.use_fake_user = True; ad.action = act
            for f in sorted(set(list(range(0, frames, step)) + [frames])):
                t = f / frames
                P, off = fn(t if oneshot else t % 1.0)
                for pb in rig.pose.bones:
                    v = P.get(pb.name, Quaternion())
                    if isinstance(v, tuple):          # (rotation, scale): scale is a number or an xyz triple
                        q, sc = v
                        pb.scale = (sc, sc, sc) if isinstance(sc, (int, float)) else sc
                        pb.keyframe_insert("scale", frame=f, group=pb.name)
                    else:
                        q = v
                        if pb.name in scaled:
                            pb.scale = (1, 1, 1); pb.keyframe_insert("scale", frame=f, group=pb.name)
                    pb.rotation_quaternion = q
                    pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
                if root_bone:
                    b = rig.pose.bones[root_bone]; b.location = self.local_off(root_bone, off)
                    b.keyframe_insert("location", frame=f, group=root_bone)
            tr = ad.nla_tracks.new(); tr.name = name; tr.strips.new(name, 0, act); tr.mute = True
            ad.action = None; made.append((name, frames))
        for pb in rig.pose.bones: pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
        if default and default in ad.nla_tracks: ad.nla_tracks[default].mute = False
        return made

def smooth01(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def seg(t, a, b): return smooth01((t - a) / (b - a)) if b > a else float(t >= a)

# ============================================================================ texturing
class Nodes:
    def __init__(self, mat):
        mat.use_nodes = True; self.nt = mat.node_tree; self.nt.nodes.clear()
        tc = self.node('ShaderNodeTexCoord'); self.obj = tc.outputs['Object']
        sep = self.node('ShaderNodeSeparateXYZ'); self.L(self.obj, sep.inputs[0])
        self.X, self.Y, self.Z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
        g = self.node('ShaderNodeNewGeometry'); ns = self.node('ShaderNodeSeparateXYZ'); self.L(g.outputs['Normal'], ns.inputs[0])
        self.NX, self.NY, self.NZ = ns.outputs[0], ns.outputs[1], ns.outputs[2]
        self.part = self.attr("part"); self.tipf = self.attr("tipf")
    def node(self, t, **kw):
        n = self.nt.nodes.new(t)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def L(self, a, b): self.nt.links.new(a, b)
    def feed(self, sock, val):
        if isinstance(val, (tuple, list)): sock.default_value = tuple(val) if len(val) == 4 else (val[0], val[1], val[2], 1.0)
        elif isinstance(val, (int, float)): sock.default_value = val
        else: self.L(val, sock)
    def attr(self, name): return self.node('ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY').outputs['Fac']
    def vattr(self, name): return self.node('ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY').outputs['Vector']
    def mix(self, a, b, fac, blend='MIX'):
        m = self.node('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        self.feed(m.inputs[6], a); self.feed(m.inputs[7], b); self.feed(m.inputs[0], fac); return m.outputs[2]
    def m(self, op, a, b=None, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.feed(n.inputs[0], a)
        if b is not None: self.feed(n.inputs[1], b)
        return n.outputs[0]
    def gray(self, f):
        c = self.node('ShaderNodeCombineColor'); self.feed(c.inputs[0], f); self.feed(c.inputs[1], f); self.feed(c.inputs[2], f); return c.outputs[0]
    def mul(self, col, f): return self.mix(col, self.gray(f), 1.0, 'MULTIPLY')
    def ramp(self, fac, stops):
        r = self.node('ShaderNodeValToRGB'); self.L(fac, r.inputs[0]); els = r.color_ramp.elements
        while len(els) > 1: els.remove(els[-1])
        els[0].position = stops[0][0]; els[0].color = tuple(stops[0][1]) + (1.0,) if len(stops[0][1]) == 3 else stops[0][1]
        for pos, c in stops[1:]:
            e = els.new(pos); e.color = tuple(c) + (1.0,) if len(c) == 3 else c
        return r.outputs[0]
    def noise(self, scale, detail=4.0, vec=None, rough=0.5):
        n = self.node('ShaderNodeTexNoise'); self.L(vec or self.obj, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
        return n.outputs['Fac']
    def voronoi(self, scale, feature='F1', vec=None, rand=1.0):
        n = self.node('ShaderNodeTexVoronoi', feature=feature); self.L(vec or self.obj, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale
        if 'Randomness' in n.inputs: n.inputs['Randomness'].default_value = rand
        return n.outputs['Distance']
    def wave(self, scale, kind='BANDS', direction='X', distortion=2.0, vec=None):
        n = self.node('ShaderNodeTexWave', wave_type=kind)
        if kind == 'BANDS': n.bands_direction = direction
        else: n.rings_direction = direction
        self.L(vec or self.obj, n.inputs['Vector']); n.inputs['Scale'].default_value = scale; n.inputs['Distortion'].default_value = distortion
        return n.outputs['Fac']
    def is_part(self, i):
        n = self.node('ShaderNodeMath', operation='COMPARE'); self.L(self.part, n.inputs[0]); n.inputs[1].default_value = float(i); n.inputs[2].default_value = 0.5
        return n.outputs[0]
    def up01(self): return self.m('MULTIPLY', self.m('ADD', self.NZ, 1.0), 0.5)
    def countershade(self, belly, flank, back, mid=0.48):
        return self.ramp(self.up01(), [(0.0, belly), (mid - 0.16, belly), (mid, flank), (mid + 0.27, back), (1.0, back)])

def uv_unwrap(obj, margin=0.004, squeeze_part=None, strip=0.94):
    me = obj.data
    select_only([obj]); bpy.ops.object.mode_set(mode='EDIT')
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    bm = bmesh.from_edit_mesh(me); pl = bm.faces.layers.int.get("part")
    for f in bm.faces: f.select = (squeeze_part is None or f[pl] != squeeze_part)
    bmesh.update_edit_mesh(me)
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=True)
    if squeeze_part is not None:
        bm = bmesh.from_edit_mesh(me); pl = bm.faces.layers.int.get("part"); uvl = bm.loops.layers.uv.active
        xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        for f in bm.faces:
            for lp in f.loops:
                if f[pl] == squeeze_part:
                    co = lp.vert.co
                    lp[uvl].uv = (strip + 0.01 + (1 - strip - 0.02) * (co.x - x0) / max(1e-6, x1 - x0), (co.y - y0) / max(1e-6, y1 - y0))
                else:
                    lp[uvl].uv = (lp[uvl].uv.x * (strip - 0.005), lp[uvl].uv.y)
        bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode='OBJECT')

def bake_and_material(obj, name, out_dir, build_nodes, res=1024, glow_res=None, shader="KSP/Emissive/Diffuse"):
    """build_nodes(N) -> (diffuse_socket, glow_socket or None)"""
    os.makedirs(out_dir, exist_ok=True)
    scn = bpy.context.scene; me = obj.data
    mat = bpy.data.materials.get(name + "_bake") or bpy.data.materials.new(name + "_bake")
    N = Nodes(mat)
    diffuse, glow = build_nodes(N)
    emit = N.node('ShaderNodeEmission'); out = N.node('ShaderNodeOutputMaterial'); N.L(emit.outputs[0], out.inputs['Surface'])
    img_node = N.node('ShaderNodeTexImage')
    me.materials.clear(); me.materials.append(mat)
    def bake(sock, iname, r):
        img = bpy.data.images.get(iname)
        if img is None or img.size[0] != r:
            if img: bpy.data.images.remove(img)
            img = bpy.data.images.new(iname, r, r, alpha=False)
        img.colorspace_settings.name = 'Non-Color'
        img_node.image = img
        for n_ in N.nt.nodes: n_.select = False
        img_node.select = True; N.nt.nodes.active = img_node
        N.feed(emit.inputs['Color'], sock)
        scn.render.engine = 'CYCLES'; scn.cycles.samples = 1; scn.cycles.device = 'CPU'
        scn.render.bake.margin = 8; scn.render.bake.use_clear = True
        select_only([obj]); bpy.ops.object.bake(type='EMIT')
        img.filepath_raw = os.path.join(out_dir, iname + ".png"); img.file_format = 'PNG'; img.save()
        img.colorspace_settings.name = 'sRGB'
        return img
    d_img = bake(diffuse, name + "_diffuse", res)
    g_img = bake(glow, name + "_glow", glow_res or max(64, res // 4)) if glow is not None and shader.startswith("KSP/Emissive") else None
    fm = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    fm.use_nodes = True; ft = fm.node_tree; ft.nodes.clear()
    bsdf = ft.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.inputs['Roughness'].default_value = 0.7
    fo = ft.nodes.new('ShaderNodeOutputMaterial'); ft.links.new(bsdf.outputs[0], fo.inputs['Surface'])
    dt = ft.nodes.new('ShaderNodeTexImage'); dt.image = d_img; ft.links.new(dt.outputs[0], bsdf.inputs['Base Color'])
    if g_img:
        gt = ft.nodes.new('ShaderNodeTexImage'); gt.image = g_img; ft.links.new(gt.outputs[0], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 1.0
    me.materials.clear(); me.materials.append(fm)
    mp = fm.mumatprop; mp.shaderName = shader if g_img else "KSP/Diffuse"
    for coll in (mp.color.properties, mp.texture.properties, mp.float2.properties, mp.float3.properties, mp.vector.properties): coll.clear()
    c = mp.color.properties.add(); c.name = "_Color"; c.value = (1, 1, 1, 1)
    t = mp.texture.properties.add(); t.name = "_MainTex"; t.tex = d_img.name
    if g_img:
        c = mp.color.properties.add(); c.name = "_EmissiveColor"; c.value = (1, 1, 1, 1)
        t = mp.texture.properties.add(); t.name = "_Emissive"; t.tex = g_img.name
    scn.render.engine = 'BLENDER_EEVEE'
    return fm

# ============================================================================ export + renders
def export_mu(root_name, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    root = bpy.data.objects[root_name]
    for o in root.children_recursive:
        if o.type == 'ARMATURE':
            if o.animation_data: o.animation_data.action = None
            for pb in o.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.scene.frame_set(0)
    exp = importlib.import_module("io_object_mu.export_mu.export")
    cols = exp.enable_collections()
    try: mu = exp.export_object(root, out_path)
    finally: exp.restore_collections(cols)
    return {"bytes": os.path.getsize(out_path), "messages": [str(m[1]) for m in getattr(mu, "messages", [])]}

def _ensure(name, data):
    scn = bpy.context.scene
    o = bpy.data.objects.get(name)
    if o is None: o = bpy.data.objects.new(name, data)
    if o.name not in scn.objects: scn.collection.objects.link(o)
    return o

def look_at(cam, pos, target):
    cam.location = pos; cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()

def stage_setup(ground=True, sky=(0.55, 0.7, 0.9), ground_col=(0.25, 0.32, 0.18), ground_size=200.0):
    scn = bpy.context.scene
    cam = _ensure("xr_cam", bpy.data.cameras.get("xr_cam") or bpy.data.cameras.new("xr_cam")); scn.camera = cam
    sun = _ensure("xr_sun", bpy.data.lights.get("xr_sun") or bpy.data.lights.new("xr_sun", 'SUN'))
    sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(140))
    g = bpy.data.objects.get("xr_ground")
    if g is None:
        me = bpy.data.meshes.new("xr_ground"); s = ground_size
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        g = bpy.data.objects.new("xr_ground", me)
        gm = bpy.data.materials.new("xr_ground"); gm.use_nodes = True
        gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = ground_col + (1,)
        me.materials.append(gm)
    if g.name not in scn.objects: scn.collection.objects.link(g)
    g.hide_render = not ground
    if scn.world is None: scn.world = bpy.data.worlds.new("xr_world")
    scn.world.use_nodes = True
    bg = scn.world.node_tree.nodes["Background"]; bg.inputs[0].default_value = sky + (1,); bg.inputs[1].default_value = 0.7
    return cam, g

def set_clip(rig, clip, frame):
    ad = rig.animation_data
    for tr in ad.nla_tracks: tr.mute = (tr.name != clip)
    bpy.context.scene.frame_set(frame)

def render(path, engine='BLENDER_EEVEE', res=(1280, 800), transparent=False, flat=False):
    scn = bpy.context.scene
    scn.render.engine = engine
    if flat:
        sh = scn.display.shading; sh.light = 'FLAT'; sh.color_type = 'SINGLE'; sh.single_color = (1, 1, 1)
    scn.render.film_transparent = transparent
    scn.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    scn.render.resolution_x, scn.render.resolution_y = res; scn.render.resolution_percentage = 100
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scn.render.filepath = path; bpy.ops.render.render(write_still=True)
    return path

def icon_renders(rig, var, sil_clip, sil_frame, sil_cam, ortho, por_clip, por_frame, por_cam, lens=45, top=False):
    """Writes PREVIEW_DIR/<var>_silmask.png and <var>_portrait.png"""
    cam, g = stage_setup()
    g.hide_render = True
    set_clip(rig, sil_clip, sil_frame)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    if top: cam.location = sil_cam[0]; cam.rotation_euler = (0, 0, 0)
    else: look_at(cam, *sil_cam)
    render(os.path.join(PREVIEW_DIR, var + "_silmask.png"), 'BLENDER_WORKBENCH', (1024, 1024), True, True)
    set_clip(rig, por_clip, por_frame)
    cam.data.type = 'PERSP'; cam.data.lens = lens; look_at(cam, *por_cam)
    render(os.path.join(PREVIEW_DIR, var + "_portrait.png"), 'BLENDER_EEVEE', (768, 576), True)
    g.hide_render = False
