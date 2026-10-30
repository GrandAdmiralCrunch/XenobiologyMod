# Xenobiology — the Cyclops' cave: a rocky hill with a 30 m entrance, tunnel and domed chamber,
# a rolling boulder door (clips "open"/"close"), interior props, a fire light and terrain colliders (layer 15).
# Local frame: entrance faces +Y, cave floor at Z = 0. Transforms named "entrance", "den", "pen" are read by the plugin.
import bpy, os, math, random
TOOLS = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData\Xenobiology\Tools\blender")
exec(open(os.path.join(TOOLS, "xeno_blend.py"), encoding="utf-8").read(), globals())
NAME = "cyclops_cave"
random.seed(77)
scn = new_scene("CyclopsCave")
OUT = os.path.join(XENO_DIR, "Models", "Kerbin", "CyclopsCave")

# ---------------------------------------------------------------- hill mass (metaballs) -> remesh
sk = Skel()
sk.v("a", 0, -30, 6, 62, 40); sk.v("b", 0, 0, 0, 52, 30); sk.e("a", "b")
for i in range(9):
    a = random.uniform(0, math.tau); r = random.uniform(25, 55)
    nm = "l%d" % i
    sk.v(nm, math.cos(a) * r, -30 + math.sin(a) * r * 0.8, random.uniform(-4, 16), random.uniform(18, 30), random.uniform(14, 24))
    sk.e("a", nm)
sk.v("brow", 0, 18, 24, 30, 22); sk.e("b", "brow")
hill = metaball_body(NAME + "_hill", sk, voxel=1.4, faces=9000, mb_scale=1.15, smooth=2, floor=False)
# (the metaball mass already extends ~30 m below the ground plane, hiding uneven terrain)

# ---------------------------------------------------------------- the void: tunnel + chamber, boolean difference
def cutter(name, build):
    bm = bmesh.new(); build(bm)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))
def tunnel(bm):
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=12.5, radius2=11.5, depth=130)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 35, 19)) @ Matrix.Rotation(math.radians(90), 4, 'X'), verts=res["verts"])
    res = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 35, 9)) @ Matrix.Diagonal((24.5, 130, 22, 1)), verts=res["verts"])
def chamber(bm):
    res = bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, -40, 8)) @ Matrix.Diagonal((32, 28, 28, 1)), verts=res["verts"])
for nm, fn in (("cut_tunnel", tunnel), ("cut_chamber", chamber)):
    c = cutter(nm, fn)
    mod = hill.modifiers.new(nm, 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.solver = 'EXACT'; mod.object = c; mod.use_self = True
    select_only([hill]); bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(c, do_unlink=True)
# rough rock surface
def rock(co, n):
    d = noise.noise(co * 0.06) * 2.5 + noise.noise(co * 0.25) * 0.8 + noise.noise(co * 0.9) * 0.2
    if abs(co.z) < 0.3: d *= 0.2
    return co + n * d
displace(hill, rock)
for p in hill.data.polygons: p.use_smooth = True   # smooth keeps the vertex count under KSP's 65k limit
tag_body(hill, 0)

# ---------------------------------------------------------------- floor slab (covers tunnel + chamber)
p = Part("floor", 1)
ring = []
for k in range(48):
    a = k / 48 * math.tau
    ring.append(Vector((math.cos(a) * 31, -40 + math.sin(a) * 27, 0.15)))
rect = [Vector((-12.2, 70, 0.15)), Vector((12.2, 70, 0.15)), Vector((12.2, -14, 0.15)), Vector((-12.2, -14, 0.15))]
for poly in (ring, rect):
    vs = [p.v(c, "root") for c in poly]
    p.f(vs)
floor = p.finish()

# ---------------------------------------------------------------- props (palette-coloured parts)
props = Part("props", 2)
def rocklump(c, r, sc=(1, 1, 0.7), pid_tip=0.0): props.sphere(c, r, "root", scale=sc, sub=2, jitter=0.25, tip=pid_tip)
# fire pit: ring of stones, logs, embers
fire = Vector((6, -36, 0))
for k in range(11):
    a = k / 11 * math.tau
    rocklump(fire + Vector((math.cos(a) * 4.2, math.sin(a) * 4.2, 0.6)), 1.2, (1, 0.9, 0.7), 0.1)
for k in range(5):
    a = k / 5 * math.tau + 0.3
    props.tube(fire + Vector((math.cos(a) * 2.6, math.sin(a) * 2.6, 0.4)), fire + Vector((-math.cos(a) * 0.6, -math.sin(a) * 0.6, 1.8)), 0.5, 0.4, "root", 3, 6, tip_from=0.3)
embers = Part("embers", 3)
embers.sphere(fire + Vector((0, 0, 0.3)), 2.4, "root", scale=(1, 1, 0.25), sub=2, jitter=0.3)
# bed of hides
for c, sz in (((-15, -50, 0.4), (9, 6, 1.0)), ((-19, -44, 0.6), (7, 6, 1.2)), ((-12, -56, 0.5), (6, 5, 0.9))):
    rocklump(Vector(c), 1.0, sz, 0.5)
# cheese shelf: stone slab on two pillars, wheels of cheese on top
shelf = Vector((20, -54, 0))
for dx in (-5, 5):
    rocklump(shelf + Vector((dx, 0, 2.5)), 1.4, (1, 1, 2.0), 0.1)
rocklump(shelf + Vector((0, 0, 5.2)), 1.0, (8, 2.4, 0.7), 0.1)
cheese = Part("cheese", 4)
for k in range(6):
    c = shelf + Vector((-5.5 + k * 2.2, random.uniform(-0.6, 0.6), 6.3))
    cheese.tube(c, c + Vector((0, 0, 1.0)), 1.0, 1.0, "root", 1, 14, True)
for k in range(3):
    c = Vector((22 + k * 2.4, -46, 0)); cheese.tube(c, c + Vector((0, 0, 1.1)), 1.1, 1.1, "root", 1, 14, True)
# old bones: a mossback skull and ribs
bones = Part("bones", 5)
sk0 = Vector((-8, -24, 1.6))
bones.sphere(sk0, 1.6, "root", scale=(1.2, 1.6, 0.9), sub=2)
for sx in (1, -1):
    bones.cone(sk0 + Vector((sx * 0.6, 1.6, -0.4)), (sx * 0.3, 1, -0.6), 2.4, 0.35, "root", 6, bend=(0, 0.3, -0.6))
for k in range(6):
    b = Vector((-14 + k * 1.2, -28, 0.3))
    bones.cone(b, (0.2, 0.3, 1), 3.2 - 0.25 * k, 0.22, "root", 5, bend=(0.6, 0, -0.2))
# ---------------------------------------------------------------- boulder door (separate animated object)
door = Part("door", 6)
door.sphere((0, 0, 0), 15.0, "root", scale=(1, 0.75, 1), sub=3, jitter=0.18)
door_o = door.finish()

parts = [floor, props.finish(), embers.finish(), cheese.finish(), bones.finish()]
select_only([hill] + parts, hill); bpy.ops.object.join()
hill.name = NAME + "_rock"
for vg in list(hill.vertex_groups): hill.vertex_groups.remove(vg)
for vg in list(door_o.vertex_groups): door_o.vertex_groups.remove(vg)

# ---------------------------------------------------------------- texture: one atlas for rock + props, one for the door
uv_unwrap(hill, margin=0.002)
def nodes(N):
    up = N.up01()
    rockc = N.ramp(N.noise(0.08, 6), [(0.3, (0.36, 0.34, 0.31)), (0.55, (0.46, 0.44, 0.40)), (0.8, (0.30, 0.29, 0.27))])
    strata = N.wave(0.12, 'BANDS', 'Z', 3.0)
    rockc = N.mix(rockc, (0.52, 0.47, 0.38), N.m('MULTIPLY', N.m('GREATER_THAN', strata, 0.8), 0.35))
    cracks = N.voronoi(0.35, 'DISTANCE_TO_EDGE')
    rockc = N.mix(rockc, (0.16, 0.15, 0.14), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.m('MULTIPLY', cracks, 6.0, clamp=True)), 0.5))
    # grass and moss on the outer upward faces above the ground line; soot near the fire inside
    outside = N.m('GREATER_THAN', N.m('ADD', N.m('MULTIPLY', N.m('ABSOLUTE', N.X), 0.0), N.Z), 2.5)
    grassy = N.m('MULTIPLY', N.m('GREATER_THAN', up, 0.82), N.m('GREATER_THAN', N.noise(0.15, 3), 0.42))
    grass = N.mul((0.30, 0.42, 0.16), N.m('ADD', N.m('MULTIPLY', N.noise(1.5, 4), 0.5), 0.75))
    col = N.mix(rockc, grass, N.m('MULTIPLY', grassy, outside))
    dist_fire = N.m('SQRT', N.m('ADD', N.m('POWER', N.m('SUBTRACT', N.X, 6.0), 2.0), N.m('POWER', N.m('SUBTRACT', N.Y, -36.0), 2.0)))
    col = N.mix(col, (0.08, 0.07, 0.06), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.m('DIVIDE', dist_fire, 16.0), clamp=True), 0.6))
    floorc = N.mix((0.33, 0.29, 0.24), (0.22, 0.19, 0.16), N.noise(0.4, 5))
    floorc = N.mix(floorc, (0.10, 0.09, 0.08), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.m('DIVIDE', dist_fire, 10.0), clamp=True), 0.7))
    hidecol = N.mix((0.40, 0.42, 0.36), (0.28, 0.62, 0.58), N.m('LESS_THAN', N.voronoi(0.8), 0.15))
    propc = N.mix(rockc, hidecol, N.m('GREATER_THAN', N.tipf, 0.4))
    propc = N.mix(propc, (0.30, 0.20, 0.11), N.m('MULTIPLY', N.m('GREATER_THAN', N.tipf, 0.25), N.m('LESS_THAN', N.tipf, 0.4)))
    ember = N.mix((0.95, 0.45, 0.08), (0.25, 0.05, 0.02), N.m('GREATER_THAN', N.noise(3.0, 3), 0.55))
    cheesec = N.mix((0.95, 0.80, 0.30), (0.80, 0.55, 0.15), N.m('LESS_THAN', N.voronoi(2.0), 0.12))
    bonec = (0.86, 0.82, 0.70)
    col = N.mix(col, floorc, N.is_part(1)); col = N.mix(col, propc, N.is_part(2)); col = N.mix(col, ember, N.is_part(3))
    col = N.mix(col, cheesec, N.is_part(4)); col = N.mix(col, bonec, N.is_part(5))
    glow = N.mix((0, 0, 0), ember, N.is_part(3))
    return col, glow
bake_and_material(hill, NAME, OUT, nodes, res=2048, glow_res=128)
uv_unwrap(door_o, margin=0.004)
def door_nodes(N):
    c = N.ramp(N.noise(0.12, 6), [(0.3, (0.34, 0.32, 0.29)), (0.6, (0.47, 0.45, 0.41)), (0.85, (0.30, 0.29, 0.26))])
    cr = N.voronoi(0.4, 'DISTANCE_TO_EDGE')
    c = N.mix(c, (0.15, 0.14, 0.13), N.m('MULTIPLY', N.m('SUBTRACT', 1.0, N.m('MULTIPLY', cr, 6.0, clamp=True)), 0.5))
    c = N.mix(c, (0.30, 0.40, 0.18), N.m('MULTIPLY', N.m('GREATER_THAN', N.up01(), 0.85), 0.7))
    return c, None
bake_and_material(door_o, NAME + "_door", OUT, door_nodes, res=1024, shader="KSP/Diffuse")

# ---------------------------------------------------------------- colliders (layer 15 = local scenery, so it behaves like terrain)
def mesh_collider(src, name, parent):
    me = src.data.copy(); o = link(bpy.data.objects.new(name, me)); o.parent = parent
    o.data.materials.clear(); o.hide_render = True
    o.muproperties.collider = "MU_COL_MESH"; o.muproperties.layer = 15; o.muproperties.separate = True
    o.muproperties.isConvex = False      # a convex mesh collider is a solid hull: it would seal the cave
    return o
root = link(bpy.data.objects.new(NAME, None)); root.muproperties.layer = 15
hill.parent = root
hill.muproperties.layer = 15
col_hill = mesh_collider(hill, NAME + "_collider", root)
door_pivot = link(bpy.data.objects.new("door_pivot", None)); door_pivot.parent = root
door_o.parent = door_pivot; door_o.location = (0, 0, 0)
door_o.muproperties.layer = 15
dc = link(bpy.data.objects.new("door_collider", None)); dc.parent = door_o
dc.muproperties.collider = 'MU_COL_SPHERE'; dc.muproperties.radius = 13.5; dc.muproperties.layer = 15
# named marker transforms the plugin looks for
for nm, loc in (("entrance", (0, 48, 0)), ("den", (-6, -44, 0)), ("pen", (0, 95, 0)), ("firelight", (6, -36, 4))):
    e = link(bpy.data.objects.new(nm, None)); e.parent = root; e.location = loc
light = bpy.data.lights.new("fire_light", 'POINT'); light.color = (1.0, 0.55, 0.2); light.energy = 2500
light.use_custom_distance = True; light.cutoff_distance = 70
lo = link(bpy.data.objects.new("fire_light", light)); lo.parent = bpy.data.objects["firelight"]

# ---------------------------------------------------------------- door animation: rolled aside (open) <-> sealing the mouth (closed)
OPEN = Vector((27, 50, 13.5)); CLOSED = Vector((0, 46, 13.5))
door_pivot.rotation_mode = 'QUATERNION'
if door_pivot.animation_data is None: door_pivot.animation_data_create()
ad = door_pivot.animation_data
for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
def door_clip(name, a, b):
    act = bpy.data.actions.get("door_" + name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new("door_" + name); act.use_fake_user = True; ad.action = act
    frames = 120
    for f in range(0, frames + 1, 4):
        t = smooth01(f / frames)
        door_pivot.location = a.lerp(b, t)
        roll = (b - a).length / 15.0 * t * (1 if b.x < a.x else -1)
        door_pivot.rotation_quaternion = Quaternion((0, 1, 0), roll)
        door_pivot.keyframe_insert("location", frame=f); door_pivot.keyframe_insert("rotation_quaternion", frame=f)
    tr = ad.nla_tracks.new(); tr.name = name; tr.strips.new(name, 0, act); tr.mute = True
    ad.action = None
door_clip("close", OPEN, CLOSED); door_clip("open", CLOSED, OPEN)
door_pivot.location = OPEN; door_pivot.rotation_quaternion = Quaternion()
scn.frame_start = 0

res = export_mu(NAME, os.path.join(OUT, NAME + ".mu"))
# ---------------------------------------------------------------- review renders
cam, g = stage_setup(ground_size=600.0)
cam.data.type = 'PERSP'; cam.data.lens = 35
look_at(cam, (140, 190, 70), (0, -10, 15)); render(os.path.join(PREVIEW_DIR, "cave_outside.png"), res=(1280, 800))
look_at(cam, (2, 60, 14), (0, -40, 8)); render(os.path.join(PREVIEW_DIR, "cave_mouth.png"), res=(1280, 800))
lo.data.energy = 250000
look_at(cam, (0, -8, 10), (0, -45, 4)); render(os.path.join(PREVIEW_DIR, "cave_inside.png"), res=(1280, 800))
lo.data.energy = 2500
ad.nla_tracks["close"].mute = False; scn.frame_set(120)
look_at(cam, (140, 190, 70), (0, -10, 15)); render(os.path.join(PREVIEW_DIR, "cave_closed.png"), res=(1280, 800))
ad.nla_tracks["close"].mute = True; scn.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(PREVIEW_DIR), "blend", "cyclops_cave.blend"), copy=True)
result = {"export": res, "rock_tris": sum(len(p.vertices) - 2 for p in hill.data.polygons)}
