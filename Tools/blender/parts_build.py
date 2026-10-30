# Xenobiology — part models: Xenofauna Tracking Camera, Hydrophone, CO-Z Containment Unit.
# Set PART = "camera" | "hydrophone" | "coz" | "all" before exec'ing this file inside Blender.
# Blender frame: Z = Unity Y (along the vessel), Y = Unity Z. Radial parts mount on their -Y face at Y = 0
# (part cfg: node_attach = 0,0,0, 0,0,-1). Stack parts span Z = +-height/2.
# Texture ids ("part" face attribute): 0 shell, 1 dark metal, 2 glass, 3 LED glow, 4 orange hazard, 5 gel glow.
import bpy, bmesh, os, math
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
PART = globals().get("PART", "all")

SHELL, DARK, GLASS, LED, HAZARD, GEL = range(6)

class B:
    """Tiny hard-surface builder: every face carries a texture id ("part") and a hierarchy group ("grp")."""
    def __init__(self):
        self.bm = bmesh.new()
        self.pl = self.bm.faces.layers.int.new("part"); self.gl = self.bm.faces.layers.int.new("grp")
        self.pid = 0; self.grp = 0
    def use(self, pid=None, grp=None):
        if pid is not None: self.pid = pid
        if grp is not None: self.grp = grp
        return self
    def face(self, vs):
        try: f = self.bm.faces.new(vs)
        except ValueError: return None
        f[self.pl] = self.pid; f[self.gl] = self.grp; return f
    def v(self, co): return self.bm.verts.new(Vector(co))
    def box(self, c, s, M=None):
        M = M or Matrix.Identity(4); c = Vector(c); h = Vector(s) * 0.5
        vs = [self.v(M @ (c + Vector((sx * h.x, sy * h.y, sz * h.z)))) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)): self.face([vs[i] for i in q])
    def lathe(self, prof, M, segs=24, cap0=True, cap1=True, a0=0.0, a1=math.tau):
        """prof: [(r, z), ...] around local Z, transformed by M"""
        full = abs(a1 - a0 - math.tau) < 1e-6
        n = segs if full else segs + 1
        rings = []
        for r, z in prof:
            if r < 1e-6: rings.append([self.v(M @ Vector((0, 0, z)))] * n)
            else: rings.append([self.v(M @ Vector((math.cos(a0 + (a1 - a0) * k / segs) * r, math.sin(a0 + (a1 - a0) * k / segs) * r, z))) for k in range(n)])
        for i in range(len(rings) - 1):
            A, Bv = rings[i], rings[i + 1]
            for k in range(segs):
                k1 = (k + 1) % n
                q = [A[k], A[k1], Bv[k1], Bv[k]]
                q = [x for j, x in enumerate(q) if x not in q[:j]]
                if len(q) >= 3: self.face(q)
        if full:
            if cap0 and prof[0][0] > 1e-6: self.face(rings[0][::-1])
            if cap1 and prof[-1][0] > 1e-6: self.face(rings[-1])
    def tube(self, a, b, r, segs=10):
        a = Vector(a); b = Vector(b); d = b - a
        M = Matrix.Translation(a) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        self.lathe([(r, 0), (r, d.length)], M, segs)
    def finish(self, name):
        me = bpy.data.meshes.new(name); self.bm.to_mesh(me); self.bm.free()
        return link(bpy.data.objects.new(name, me))

def axis_m(c, z_dir):
    """matrix whose local Z points along z_dir, origin c"""
    return Matrix.Translation(Vector(c)) @ Vector(z_dir).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()

def hard_normals(obj, angle=38):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(angle)]
    bmesh.ops.split_edges(bm, edges=sharp)
    bm.to_mesh(obj.data); bm.free()
    for p in obj.data.polygons: p.use_smooth = True

def split_groups(obj, groups):
    """groups: {grp: (name, parent, pivot)} -> mesh objects with origins at their pivots"""
    out = {}
    for g, (nm, parent, pivot) in groups.items():
        bm = bmesh.new(); bm.from_mesh(obj.data); gl = bm.faces.layers.int.get("grp")
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[gl] != g], context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        for v in bm.verts: v.co -= Vector(pivot)
        me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free()
        for m in obj.data.materials: me.materials.append(m)
        for p in me.polygons: p.use_smooth = True
        o = link(bpy.data.objects.new(nm, me)); o.parent = parent; o.location = (0, 0, 0)
        out[g] = o
    bpy.data.objects.remove(obj, do_unlink=True)
    return out

def empty(name, parent, loc):
    e = link(bpy.data.objects.new(name, None)); e.parent = parent; e.location = loc; return e

def convex_collider(name, parent, build):
    b = B(); build(b); o = b.finish(name); o.parent = parent
    o.hide_render = True; o.display_type = 'WIRE'
    o.muproperties.collider = 'MU_COL_MESH'; o.muproperties.isConvex = True; o.muproperties.separate = True
    return o

def part_nodes(scale):
    """shared paint scheme; scale ~ 1/part size so noise reads at the right size"""
    def build(N):
        shell = N.ramp(N.noise(6.0 * scale, 5), [(0.35, (0.80, 0.80, 0.77)), (0.65, (0.88, 0.88, 0.85))])
        seams = N.m('LESS_THAN', N.voronoi(1.6 * scale, 'DISTANCE_TO_EDGE', rand=0.0), 0.012)
        shell = N.mix(shell, (0.55, 0.56, 0.55), N.m('MULTIPLY', seams, 0.6))
        dark = N.ramp(N.noise(14.0 * scale, 6), [(0.3, (0.13, 0.14, 0.15)), (0.7, (0.22, 0.23, 0.24))])
        glass = N.ramp(N.up01(), [(0.0, (0.02, 0.03, 0.05)), (1.0, (0.18, 0.26, 0.34))])
        led = (0.35, 1.0, 0.45)
        stripes = N.wave(6.0 * scale, 'BANDS', 'DIAGONAL', 0.0)
        hazard = N.mix((0.95, 0.45, 0.06), (0.08, 0.08, 0.08), N.m('GREATER_THAN', stripes, 0.62))
        bub = N.voronoi(9.0 * scale, 'F1')
        gel = N.ramp(N.m('ADD', N.m('MULTIPLY', bub, 0.9), N.m('MULTIPLY', N.noise(4.0 * scale, 3), 0.3)),
                     [(0.0, (0.75, 1.0, 0.55)), (0.35, (0.30, 0.85, 0.30)), (0.8, (0.10, 0.45, 0.16))])
        col = shell
        for i, c in ((DARK, dark), (GLASS, glass), (LED, led), (HAZARD, hazard), (GEL, gel)): col = N.mix(col, c, N.is_part(i))
        glow = N.mix((0, 0, 0), led, N.is_part(LED))
        glow = N.mix(glow, N.mul(gel, 0.85), N.is_part(GEL))
        return col, glow
    return build

def bake_obj(obj, name, out, res, scale):
    hard_normals(obj)
    uv_unwrap(obj, margin=0.02)
    bake_and_material(obj, name, out, part_nodes(scale), res=res, glow_res=res // 2)

def preview(name, root, cam_pos, target, lens=50):
    cam, g = stage_setup(ground=False, sky=(0.42, 0.47, 0.52))
    cam.data.type = 'PERSP'; cam.data.lens = lens
    look_at(cam, cam_pos, target)
    return render(os.path.join(PREVIEW_DIR, "part_" + name + ".png"), res=(900, 700))

results = {}

# ======================================================================== Xenofauna Tracking Camera
def build_camera():
    new_scene("XenoPart_camera")
    NAME = "xeno_trackcam"; OUT = os.path.join(XENO_DIR, "Parts", "TrackingCamera")
    b = B()
    Y = axis_m((0, 0, 0), (0, 1, 0))            # local Z -> +Y (out of the hull)
    # --- base (grp 0)
    b.use(DARK, 0); b.box((0, 0.012, 0), (0.30, 0.024, 0.30))
    for sx in (-1, 1):
        for sz in (-1, 1): b.lathe([(0.012, 0.024), (0.012, 0.034), (0, 0.034)], axis_m((sx * 0.12, 0, sz * 0.12), (0, 1, 0)), 8)
    b.use(SHELL); b.lathe([(0.11, 0.024), (0.10, 0.05), (0.07, 0.07), (0.065, 0.165), (0.08, 0.17)], Y, 28)
    b.use(HAZARD); b.lathe([(0.0695, 0.12), (0.0695, 0.15)], Y, 28, False, False)
    b.use(DARK); b.box((0, 0.10, 0.068), (0.05, 0.05, 0.012))
    b.use(LED); b.box((0, 0.11, 0.075), (0.012, 0.012, 0.004))
    # --- pan (grp 1): turntable + yoke, pivot (0, 0.17, 0)
    b.use(DARK, 1); b.lathe([(0.0, 0.17), (0.095, 0.17), (0.095, 0.19), (0.085, 0.20), (0.0, 0.20)], Y, 28)
    b.use(SHELL)
    b.box((0, 0.215, 0), (0.25, 0.03, 0.08))
    for sx in (-1, 1):
        b.box((sx * 0.112, 0.29, 0), (0.026, 0.13, 0.07))
        b.use(DARK); b.lathe([(0.03, 0), (0.03, 0.012), (0.0, 0.012)], axis_m((sx * 0.125, 0.34, 0), (sx, 0, 0)), 16); b.use(SHELL)
    # --- tilt (grp 2): camera body + telephoto lens along +Z (Unity +Y), pivot (0, 0.34, 0)
    b.use(SHELL, 2); b.box((0, 0.34, -0.01), (0.17, 0.12, 0.20))
    b.use(DARK); b.box((0, 0.405, -0.03), (0.08, 0.012, 0.10))                 # top rail
    b.box((0, 0.34, -0.115), (0.12, 0.08, 0.012))                               # rear plate
    b.use(LED); b.box((0.035, 0.36, -0.122), (0.014, 0.014, 0.004))
    b.use(GLASS); b.box((-0.025, 0.33, -0.122), (0.05, 0.035, 0.003))          # rear screen
    b.use(HAZARD); b.box((0.0865, 0.34, -0.01), (0.002, 0.12, 0.04)); b.box((-0.0865, 0.34, -0.01), (0.002, 0.12, 0.04))
    for sx in (-1, 1): b.use(DARK); b.lathe([(0.022, 0), (0.022, 0.03), (0.0, 0.03)], axis_m((sx * 0.085, 0.34, 0), (sx, 0, 0)), 16)
    L = axis_m((0, 0.34, 0.09), (0, 0, 1))
    b.use(DARK); b.lathe([(0.0, 0.0), (0.05, 0.0), (0.05, 0.03), (0.045, 0.04), (0.045, 0.16), (0.052, 0.17), (0.052, 0.20)], L, 32, cap1=False)
    b.use(SHELL); b.lathe([(0.0455, 0.06), (0.0455, 0.10)], L, 32, False, False)          # focus ring
    b.use(DARK); b.lathe([(0.052, 0.20), (0.058, 0.25), (0.054, 0.25), (0.048, 0.205)], L, 32, False, False)   # hood
    b.use(GLASS); b.lathe([(0.048, 0.205), (0.03, 0.208), (0.0, 0.21)], L, 32, False, False)
    obj = b.finish(NAME + "_mesh")
    bake_obj(obj, NAME, OUT, 512, 2.0)
    root = link(bpy.data.objects.new(NAME, None))
    pan = empty("pan", root, (0, 0.17, 0)); tilt = empty("tilt", pan, (0, 0.17, 0))
    empty("lens", tilt, (0, 0, 0.30))
    split_groups(obj, {0: ("cam_base", root, (0, 0, 0)), 1: ("cam_yoke", pan, (0, 0.17, 0)), 2: ("cam_head", tilt, (0, 0.34, 0))})
    convex_collider("cam_collider", root, lambda c: c.box((0, 0.21, 0.02), (0.30, 0.42, 0.34)))
    res = export_mu(NAME, os.path.join(OUT, NAME + ".mu"))
    tilt.rotation_euler = (math.radians(-25), 0, 0); pan.rotation_euler = (0, math.radians(35), 0)
    res["preview"] = preview("trackcam", root, (0.75, 0.95, 0.55), (0, 0.22, 0.05))
    tilt.rotation_euler = (0, 0, 0); pan.rotation_euler = (0, 0, 0)
    return res

# ======================================================================== Hydrophone
def build_hydrophone():
    new_scene("XenoPart_hydrophone")
    NAME = "xeno_hydrophone"; OUT = os.path.join(XENO_DIR, "Parts", "Hydrophone")
    b = B()
    # pylon
    b.use(DARK, 0); b.box((0, 0.012, 0), (0.12, 0.024, 0.36))
    b.use(SHELL); b.box((0, 0.06, 0), (0.05, 0.08, 0.30))
    # pod along Z (Unity Y), centred (0, 0.17, 0)
    P = axis_m((0, 0.17, -0.30), (0, 0, 1))
    prof = [(0.0, 0.0), (0.03, 0.005), (0.06, 0.04), (0.075, 0.10), (0.08, 0.16)]
    b.use(SHELL); b.lathe(prof, P, 28, cap1=False)
    b.lathe([(0.08, 0.16), (0.08, 0.36)], P, 28, False, False)
    b.use(HAZARD); b.lathe([(0.0805, 0.36), (0.0805, 0.40)], P, 28, False, False)
    b.use(DARK); b.lathe([(0.08, 0.40), (0.078, 0.43)], P, 28, False, False)
    b.use(GLASS); b.lathe([(0.078, 0.43), (0.078, 0.50)], P, 28, False, False)     # acoustic window
    b.use(DARK); b.lathe([(0.078, 0.50), (0.07, 0.54), (0.05, 0.58), (0.02, 0.60), (0.0, 0.602)], P, 28, cap0=False)
    # hydrophone elements around the window
    for k in range(8):
        a = k / 8 * math.tau; d = Vector((math.cos(a), math.sin(a), 0))
        c = Vector((0, 0.17, -0.30 + 0.465)) + Vector((d.x, d.y, 0)) * 0.079
        b.use(DARK); b.lathe([(0.012, 0), (0.012, 0.008), (0.0, 0.01)], axis_m(c, (d.x, d.y, 0)), 10)
    # tail fins (cross)
    b.use(DARK)
    for a in (0, 90, 180, 270):
        r = math.radians(a); d = Vector((math.cos(r), math.sin(r), 0))
        if d.y < -0.5: continue                                                 # no fin into the pylon
        base = Vector((0, 0.17, 0)) + Vector((d.x, d.y, 0)) * 0.06
        side = Vector((d.y, -d.x, 0))
        M = Matrix.Translation(base) @ Matrix(((side.x, d.x, 0, 0), (side.y, d.y, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
        vs = []
        for t in (0.004, -0.004):
            vs.append([b.v(M @ Vector(p)) for p in ((t, 0, -0.235), (t, 0, -0.11), (t, 0.075, -0.20), (t, 0.08, -0.25))])
        b.face(vs[0][::-1]); b.face(vs[1])
        for i in range(4): b.face([vs[0][i], vs[1][i], vs[1][(i + 1) % 4], vs[0][(i + 1) % 4]][::-1])
    # status light (grp 1, its own object so the plugin can blink it)
    b.use(LED, 1); b.lathe([(0.016, 0), (0.014, 0.012), (0.0, 0.016)], axis_m((0, 0.248, 0.08), (0, 1, 0)), 12)
    b.use(DARK, 0); b.lathe([(0.024, 0), (0.024, 0.006), (0.017, 0.006)], axis_m((0, 0.246, 0.08), (0, 1, 0)), 12, cap1=False)
    obj = b.finish(NAME + "_mesh")
    bake_obj(obj, NAME, OUT, 512, 2.0)
    root = link(bpy.data.objects.new(NAME, None))
    split_groups(obj, {0: ("hydro_body", root, (0, 0, 0)), 1: ("status_light", root, (0, 0, 0))})
    convex_collider("hydro_collider", root, lambda c: (c.box((0, 0.17, 0.0), (0.17, 0.17, 0.58)), c.box((0, 0.05, 0), (0.06, 0.1, 0.3))))
    res = export_mu(NAME, os.path.join(OUT, NAME + ".mu"))
    res["preview"] = preview("hydrophone", root, (0.7, 0.75, 0.35), (0, 0.13, 0.0))
    return res

# ======================================================================== CO-Z Containment Unit
def build_coz():
    new_scene("XenoPart_coz")
    NAME = "xeno_coz"; OUT = os.path.join(XENO_DIR, "Parts", "COZContainment")
    b = B(); I = Matrix.Identity(4); R = 0.6
    # core, rims, hazard bands
    b.use(DARK, 0); b.lathe([(0.0, -0.5), (0.6, -0.5), (0.625, -0.48), (0.625, -0.43), (0.605, -0.42)], I, 48, cap1=False)
    b.lathe([(0.605, 0.42), (0.625, 0.43), (0.625, 0.48), (0.6, 0.5), (0.0, 0.5)], I, 48, cap0=False)
    b.use(SHELL); b.lathe([(0.605, -0.42), (R, -0.41), (R, 0.41), (0.605, 0.42)], I, 48, False, False)
    b.use(HAZARD)
    for z0, z1 in ((0.33, 0.39), (-0.39, -0.33)): b.lathe([(0.603, z0), (0.603, z1)], I, 48, False, False)
    b.use(DARK)
    for z in (0.33, 0.39, -0.33, -0.39): b.lathe([(0.598, z - 0.003), (0.608, z - 0.003), (0.608, z + 0.003), (0.598, z + 0.003)], I, 48, False, False)
    # top/bottom bolt rings
    for z in (0.5, -0.5):
        for k in range(16):
            a = k / 16 * math.tau
            b.lathe([(0.018, 0), (0.018, 0.01), (0.0, 0.012)], axis_m((math.cos(a) * 0.54, math.sin(a) * 0.54, z), (0, 0, 1 if z > 0 else -1)), 6)
    # gel windows (3) with frames, hatch on the 4th side
    def curved(r0, r1, a0, a1, z0, z1, segs=10):
        rings_out = [[b.v((math.cos(a0 + (a1 - a0) * k / segs) * r1, math.sin(a0 + (a1 - a0) * k / segs) * r1, z)) for k in range(segs + 1)] for z in (z0, z1)]
        rings_in = [[b.v((math.cos(a0 + (a1 - a0) * k / segs) * r0, math.sin(a0 + (a1 - a0) * k / segs) * r0, z)) for k in range(segs + 1)] for z in (z0, z1)]
        for k in range(segs):
            b.face([rings_out[0][k], rings_out[0][k + 1], rings_out[1][k + 1], rings_out[1][k]])
            b.face([rings_in[0][k + 1], rings_out[0][k + 1], rings_out[0][k], rings_in[0][k]])
            b.face([rings_in[1][k], rings_out[1][k], rings_out[1][k + 1], rings_in[1][k + 1]])
        b.face([rings_in[0][0], rings_out[0][0], rings_out[1][0], rings_in[1][0]])
        b.face([rings_in[0][-1], rings_in[1][-1], rings_out[1][-1], rings_out[0][-1]])
    for w in range(3):
        mid = math.radians(90 * w + 90); hw = math.radians(24)
        b.use(GEL); curved(R - 0.01, R + 0.004, mid - hw, mid + hw, -0.27, 0.27, 14)
        b.use(DARK)
        fw = math.radians(3.2)
        curved(R - 0.01, R + 0.018, mid - hw - fw, mid - hw + fw * 0.4, -0.29, 0.29, 2)
        curved(R - 0.01, R + 0.018, mid + hw - fw * 0.4, mid + hw + fw, -0.29, 0.29, 2)
        curved(R - 0.01, R + 0.018, mid - hw, mid + hw, 0.262, 0.29, 14)
        curved(R - 0.01, R + 0.018, mid - hw, mid + hw, -0.29, -0.262, 14)
        curved(R - 0.01, R + 0.016, mid - math.radians(1.2), mid + math.radians(1.2), -0.262, 0.262, 1)   # centre mullion
    # round loading hatch on the +X side
    H = axis_m((R, 0, 0), (1, 0, 0))
    b.use(DARK); b.lathe([(0.25, -0.07), (0.25, 0.02), (0.235, 0.03), (0.215, 0.03), (0.215, 0.01)], H, 40, False, False)
    b.use(SHELL); b.lathe([(0.215, 0.01), (0.2, 0.025), (0.0, 0.03)], H, 40, cap0=False)
    b.use(HAZARD); b.lathe([(0.20, 0.0272), (0.17, 0.0292)], H, 40, False, False)
    b.use(DARK)
    hw_ = axis_m((R + 0.03, 0, 0), (1, 0, 0))
    b.lathe([(0.03, 0), (0.03, 0.05), (0.0, 0.05)], hw_, 16)
    for a in (0, 60, 120):
        r = math.radians(a)
        b.box((R + 0.10, 0, 0), (0.016, 0.24, 0.024), Matrix.Translation((R + 0.10, 0, 0)) @ Matrix.Rotation(r, 4, 'X') @ Matrix.Translation((-R - 0.10, 0, 0)))
    b.lathe([(0.12, 0.055), (0.12, 0.085), (0.105, 0.085), (0.105, 0.055), (0.12, 0.055)], hw_, 32, False, False)     # wheel rim
    for hz in (0.17, -0.17): b.box((0.575, -0.255, hz), (0.06, 0.04, 0.08))   # hinges
    # status panel above the hatch
    b.use(DARK); b.box((R, 0, 0.29), (0.04, 0.20, 0.05))
    for k, c in enumerate((LED, LED, HAZARD)):
        b.use(c); b.box((R + 0.022, -0.06 + k * 0.06, 0.29), (0.006, 0.03, 0.022))
    # vertical life-support pipes between the windows
    b.use(DARK)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        d = Vector((math.cos(a), math.sin(a), 0)); rr = R + 0.045
        b.tube(d * (R - 0.01) + Vector((0, 0, 0.36)), d * rr + Vector((0, 0, 0.36)), 0.022, 10)
        b.tube(d * rr + Vector((0, 0, 0.36)), d * rr + Vector((0, 0, -0.36)), 0.022, 10)
        b.tube(d * (R - 0.01) + Vector((0, 0, -0.36)), d * rr + Vector((0, 0, -0.36)), 0.022, 10)
        for z in (0.12, -0.12): b.lathe([(0.03, -0.02), (0.03, 0.02)], axis_m(d * rr + Vector((0, 0, z)), (0, 0, 1)), 10)
        b.use(SHELL); b.box(d * (R + 0.012) + Vector((0, 0, 0)), (0.05, 0.05, 0.05)); b.use(DARK)
    obj = b.finish(NAME + "_mesh")
    bake_obj(obj, NAME, OUT, 1024, 1.0)
    root = link(bpy.data.objects.new(NAME, None))
    split_groups(obj, {0: ("coz_body", root, (0, 0, 0))})
    convex_collider("coz_collider", root, lambda c: c.lathe([(0.625, -0.5), (0.625, 0.5)], Matrix.Identity(4), 20))
    for nm, z in (("node_top", 0.5), ("node_bottom", -0.5)): empty(nm, root, (0, 0, z))
    res = export_mu(NAME, os.path.join(OUT, NAME + ".mu"))
    res["preview"] = preview("coz", root, (2.2, -1.5, 1.0), (0, 0, 0), lens=45)
    res["preview2"] = preview("coz_hatch", root, (2.6, 0.5, 0.5), (0, 0, 0), lens=45)
    return res

if PART in ("camera", "all"): results["camera"] = build_camera()
if PART in ("hydrophone", "all"): results["hydrophone"] = build_hydrophone()
if PART in ("coz", "all"): results["coz"] = build_coz()
print(results)
