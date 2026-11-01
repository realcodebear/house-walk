# Builds the two-storey house from plan.jpg in Blender.
#   Ground floor = the drawing.  Second floor = designed on the same structural walls.
# Run:  /Applications/Blender.app/Contents/MacOS/Blender -b -y -P blender/build_v1.py
#   HOUSE_RENDER=0  skip renders (faster)
# All plan numbers are in FEET (origin = outer bottom-left corner of the 31' wide block,
# +x = right on the drawing, +y = up on the drawing). Converted to metres on creation.
# Also writes site/v1/house.glb + site/v1/house.json for the three.js walk-through.
import bpy, bmesh, math, os, json
from mathutils import Vector

FT = 0.3048
H = 10.0          # ground floor wall height (ft) = underside of first slab
SLAB = 0.6        # slab thickness
F2 = H + SLAB     # second floor level (10'-7")
H2 = 9.4          # second floor wall height
TOP = F2 + H2     # underside of roof slab
DOOR_H = 7.0
GROUND = -1.5
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
RENDER = os.environ.get("HOUSE_RENDER", "1") == "1"

# ---------------------------------------------------------------- clean scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll_ in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
    for d in list(coll_):
        coll_.remove(d)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)

scene = bpy.context.scene
scene.unit_settings.system = 'IMPERIAL'
scene.unit_settings.length_unit = 'FEET'

# Collections: per-level ones live under "Ground Floor" / "Second Floor".
LEVEL_PARENT = {"GF": "Ground Floor", "SF": "Second Floor"}
LEVEL_COLLS = {"Walls", "Openings", "Floors", "Furniture", "Labels", "Stairs"}
LEVEL = "GF"
COLLS = {}
def coll(name, parent=None):
    if name not in COLLS:
        c = bpy.data.collections.new(name)
        (coll(parent) if parent else scene.collection).children.link(c)
        COLLS[name] = c
    return COLLS[name]

def level_coll(cname):
    if cname in LEVEL_COLLS:
        return coll(f"{LEVEL} {cname}", LEVEL_PARENT[LEVEL])
    return coll(cname)

# ---------------------------------------------------------------- materials
MATS = {}
def mat(name, color, rough=0.5, metal=0.0, alpha=1.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    m.diffuse_color = (*color, alpha)
    MATS[name] = m
    return m

M = {
    "wall":     mat("Plaster", (0.82, 0.74, 0.60), 0.85),
    "slab":     mat("Slab", (0.90, 0.89, 0.86), 0.9),
    "plinth":   mat("Stone plinth", (0.42, 0.40, 0.37), 0.9),
    "concrete": mat("Concrete", (0.55, 0.55, 0.53), 0.9),
    "marble":   mat("Marble floor", (0.88, 0.86, 0.82), 0.25),
    "wood":     mat("Wood floor", (0.42, 0.26, 0.14), 0.45),
    "wood2":    mat("Light wood floor", (0.62, 0.45, 0.28), 0.45),
    "tile":     mat("Bath tile", (0.62, 0.70, 0.74), 0.3),
    "ktile":    mat("Kitchen tile", (0.74, 0.72, 0.66), 0.35),
    "terrace":  mat("Terrace tile", (0.66, 0.50, 0.40), 0.7),
    "grass":    mat("Grass", (0.18, 0.33, 0.12), 0.95),
    "paving":   mat("Paving", (0.50, 0.47, 0.43), 0.85),
    "glass":    mat("Glass", (0.55, 0.72, 0.80), 0.05, alpha=0.30),
    "frame":    mat("Frame", (0.12, 0.10, 0.09), 0.5),
    "door":     mat("Door wood", (0.36, 0.20, 0.10), 0.5),
    "roof":     mat("Roof", (0.70, 0.68, 0.64), 0.9),
    "fabric":   mat("Sofa fabric", (0.28, 0.33, 0.42), 0.9),
    "fabric2":  mat("Chair fabric", (0.62, 0.48, 0.32), 0.9),
    "fabric3":  mat("Green fabric", (0.25, 0.40, 0.32), 0.9),
    "linen":    mat("Bed linen", (0.90, 0.90, 0.86), 0.9),
    "rug":      mat("Rug", (0.55, 0.22, 0.18), 0.95),
    "rug2":     mat("Blue rug", (0.20, 0.28, 0.45), 0.95),
    "furn":     mat("Furniture wood", (0.30, 0.18, 0.10), 0.5),
    "counter":  mat("Granite", (0.16, 0.16, 0.17), 0.25),
    "cabinet":  mat("Cabinet", (0.80, 0.78, 0.72), 0.5),
    "steel":    mat("Steel", (0.75, 0.75, 0.76), 0.25, metal=1.0),
    "black":    mat("Black", (0.04, 0.04, 0.04), 0.4),
    "white":    mat("Ceramic", (0.95, 0.95, 0.95), 0.15),
    "leaf":     mat("Leaves", (0.12, 0.35, 0.12), 0.8),
    "pot":      mat("Pot", (0.55, 0.30, 0.18), 0.8),
    "label":    mat("Label", (0.08, 0.08, 0.10), 0.6),
    "stair":    mat("Stair marble", (0.80, 0.78, 0.74), 0.3),
    "books":    mat("Books", (0.45, 0.15, 0.12), 0.7),
}

# ---------------------------------------------------------------- mesh helpers
def link(obj, cname):
    level_coll(cname).objects.link(obj)
    return obj

def mesh_obj(name, verts, faces, m, cname):
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(v) * FT for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    me.materials.append(m)
    return link(o, cname)

def box(name, x0, x1, y0, y1, z0, z1, m, cname):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mesh_obj(name, v, f, m, cname)

def prism(name, pts, z0, z1, m, cname):
    """Vertical extrusion of a 2D polygon (ft)."""
    n = len(pts)
    v = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    f = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    o = mesh_obj(name, v, f, m, cname)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    return o

def cyl(name, cx, cy, z0, z1, r, m, cname, sx=1.0, sy=1.0, seg=32):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r * FT, radius2=r * FT, depth=(z1 - z0) * FT)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    me.materials.append(m)
    o.location = (cx * FT, cy * FT, (z0 + z1) / 2 * FT)
    o.scale = (sx, sy, 1)
    return link(o, cname)

def sphere(name, cx, cy, cz, r, m, cname, sz=1.0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r * FT)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    me.materials.append(m)
    o.location = (cx * FT, cy * FT, cz * FT)
    o.scale = (1, 1, sz)
    for p in me.polygons:
        p.use_smooth = True
    return link(o, cname)

def rod(name, p1, p2, r, m, cname):
    a, b = Vector(p1) * FT, Vector(p2) * FT
    d = b - a
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r * FT, radius2=r * FT, depth=d.length)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    me.materials.append(m)
    o.location = (a + b) / 2
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    return link(o, cname)

def label(text, x, y, z, size=0.75):
    cu = bpy.data.curves.new("Label " + text, 'FONT')
    cu.body = text
    cu.size = size * FT
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    o = bpy.data.objects.new(f"{LEVEL} label " + text.split("\n")[0], cu)
    o.data.materials.append(M["label"])
    o.location = (x * FT, y * FT, z * FT)
    return link(o, "Labels")

def railing(name, p0, p1, z, h=3.2):
    """Straight glass-panel railing between two plan points at floor level z."""
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    n = max(2, int(L / 3.0) + 1)
    for i in range(n):
        t = i / (n - 1)
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        rod(f"{name} post{i}", (x, y, z), (x, y, z + h), 0.07, M["steel"], "Stairs")
    rod(f"{name} rail", (x0, y0, z + h), (x1, y1, z + h), 0.11, M["furn"], "Stairs")
    t = 0.04
    box(f"{name} glass", min(x0, x1) - (t if x0 == x1 else 0), max(x0, x1) + (t if x0 == x1 else 0),
        min(y0, y1) - (t if y0 == y1 else 0), max(y0, y1) + (t if y0 == y1 else 0),
        z + 0.3, z + h - 0.25, M["glass"], "Stairs")

# ---------------------------------------------------------------- walls
# Each wall = axis-aligned rectangle (x0, x1, y0, y1) in ft.
# Openings run along the wall's long axis: (kind, a, b, sill, head, extra)
def D(a, b, hinge, side):           return ("door", a, b, 0.0, DOOR_H, (hinge, side))
def D2(a, b, side):                 return ("door2", a, b, 0.0, DOOR_H, side)
def W(a, b, sill=3.0, head=DOOR_H): return ("win", a, b, sill, head, None)
def A(a, b, head=DOOR_H):           return ("arch", a, b, 0.0, head, None)

DOORS = []   # for the game: leaf object names + open/closed angles

def build_wall(name, rect, openings, zb, wh):
    x0, x1, y0, y1 = rect
    along_x = (x1 - x0) >= (y1 - y0)
    lo, hi = (x0, x1) if along_x else (y0, y1)

    def piece(tag, a, b, z0, z1):
        if b - a < 1e-3 or z1 - z0 < 1e-3:
            return
        if along_x:
            box(f"{name} {tag}", a, b, y0, y1, zb + z0, zb + z1, M["wall"], "Walls")
        else:
            box(f"{name} {tag}", x0, x1, a, b, zb + z0, zb + z1, M["wall"], "Walls")

    cur = lo
    for i, (kind, a, b, sill, head, extra) in enumerate(sorted(openings, key=lambda o: o[1])):
        piece(f"solid{i}", cur, a, 0, wh)
        piece(f"below{i}", a, b, 0, sill)
        piece(f"above{i}", a, b, head, wh)
        cur = b
        if kind == "win":
            window(f"{name} window{i}", along_x, rect, a, b, zb + sill, zb + head)
        elif kind == "door":
            door_frame(f"{name} door{i}", along_x, rect, a, b, zb, zb + head)
            door_leaf(f"{name} door{i} leaf", along_x, rect, a, b, zb, *extra)
        elif kind == "door2":
            mid = (a + b) / 2
            door_frame(f"{name} door{i}", along_x, rect, a, b, zb, zb + head)
            door_leaf(f"{name} door{i} leafL", along_x, rect, a, mid, zb, 'a', extra, 80, pair=True)
            door_leaf(f"{name} door{i} leafR", along_x, rect, mid, b, zb, 'b', extra, 80, pair=True)
    piece("solid_end", cur, hi, 0, wh)

def span_box(name, along_x, rect, a, b, z0, z1, t0, t1, m, cname):
    """Box spanning a..b along the wall, t0..t1 across it (fractions of thickness)."""
    x0, x1, y0, y1 = rect
    if along_x:
        th = y1 - y0
        return box(name, a, b, y0 + th * t0, y0 + th * t1, z0, z1, m, cname)
    th = x1 - x0
    return box(name, x0 + th * t0, x0 + th * t1, a, b, z0, z1, m, cname)

def window(name, along_x, rect, a, b, sill, head):
    f = 0.18
    c0, c1 = 0.40, 0.60
    span_box(name + " frame L", along_x, rect, a, a + f, sill, head, c0, c1, M["frame"], "Openings")
    span_box(name + " frame R", along_x, rect, b - f, b, sill, head, c0, c1, M["frame"], "Openings")
    span_box(name + " frame B", along_x, rect, a, b, sill, sill + f, c0, c1, M["frame"], "Openings")
    span_box(name + " frame T", along_x, rect, a, b, head - f, head, c0, c1, M["frame"], "Openings")
    mid = (a + b) / 2
    span_box(name + " mullion", along_x, rect, mid - f / 2, mid + f / 2, sill, head, c0, c1, M["frame"], "Openings")
    span_box(name + " glass", along_x, rect, a + f, b - f, sill + f, head - f, 0.48, 0.52, M["glass"], "Openings")
    span_box(name + " sill", along_x, rect, a - 0.15, b + 0.15, sill - 0.12, sill, -0.15, 1.15, M["concrete"], "Openings")

def door_frame(name, along_x, rect, a, b, z0, head):
    f = 0.12
    span_box(name + " jamb L", along_x, rect, a, a + f, z0, head, 0.0, 1.0, M["frame"], "Openings")
    span_box(name + " jamb R", along_x, rect, b - f, b, z0, head, 0.0, 1.0, M["frame"], "Openings")
    span_box(name + " head", along_x, rect, a, b, head - 0.2, head, 0.0, 1.0, M["frame"], "Openings")

def door_leaf(name, along_x, rect, a, b, zb, hinge, side, open_deg=70, pair=False):
    x0, x1, y0, y1 = rect
    f, t = 0.12, 0.15
    w = (b - a) - f - 0.02 if pair else (b - a) - 2 * f   # a pair meets in the middle
    if along_x:
        cy = (y0 + y1) / 2
        hp = (a + f if hinge == 'a' else b - f, cy); base = 0.0 if hinge == 'a' else math.pi
    else:
        cx = (x0 + x1) / 2
        hp = (cx, a + f if hinge == 'a' else b - f); base = math.pi / 2 if hinge == 'a' else -math.pi / 2
    o = box(name, 0, w, -t / 2, t / 2, 0.02, DOOR_H - 0.22, M["door"], "Openings")
    o.location = (hp[0] * FT, hp[1] * FT, zb * FT)
    best = None
    for s in (1, -1):
        ang = base + s * math.radians(open_deg)
        score = math.cos(ang) * side[0] + math.sin(ang) * side[1]
        if best is None or score > best[0]:
            best = (score, ang)
    o.rotation_euler = (0, 0, best[1])
    o["door_closed"] = base
    o["door_open"] = best[1]
    DOORS.append({"name": name, "closed": base, "open": best[1]})
    for k, sy in enumerate((t / 2 + 0.06, -t / 2 - 0.06)):     # knobs on both faces, parented to the leaf
        kn = sphere(f"{name} knob{k}", 0, 0, 0, 0.11, M["steel"], "Openings")
        kn.parent = o
        kn.location = ((w - 0.3) * FT, sy * FT, 3.2 * FT)

# ================================================================ GROUND FLOOR (from the drawing)
LEVEL = "GF"
WALLS_GF = {
    "GF wall top (back)":          ((0.0, 31.0, 37.5, 38.25), [D(4.6, 7.3, 'b', (0, 1)), W(8.8, 11.2, 4.5), W(14.5, 17.0, 4.5), W(21.4, 27.0)]),
    "GF wall kitchen west":        ((0.0, 0.75, 20.9, 38.25), [W(28.5, 32.3, 3.5)]),
    "GF wall kitchen south":       ((0.0, 9.4, 20.9, 21.6), []),
    "GF wall lounge west":         ((1.7, 2.5, 6.1, 20.9), [W(10.2, 14.2)]),
    "GF wall lounge front":        ((1.7, 17.5, 6.1, 6.8), [W(3.8, 7.7), D2(11.4, 15.4, (0, 1))]),
    "GF wall drawing west":        ((17.5, 18.2, 0.0, 21.7), [D(1.6, 4.8, 'a', (1, 0)), A(8.9, 14.2, 8.0)]),
    "GF wall drawing front":       ((17.5, 31.0, 0.0, 0.77), [W(20.8, 27.4)]),
    "GF wall drawing east":        ((30.25, 31.0, 0.0, 15.5), []),
    "GF wall drawing north":       ((18.2, 31.0, 14.7, 15.5), []),
    "GF wall common WR east":      ((27.9, 28.5, 15.5, 20.9), [W(16.4, 19.4, 5.0)]),
    "GF wall east (bed + bath)":   ((30.25, 31.0, 20.9, 37.5), []),
    "GF wall washrooms north":     ((18.2, 30.25, 20.9, 21.7), [D(18.2, 20.6, 'a', (0, -1))]),
    "GF wall attach WR west":      ((22.5, 23.2, 21.7, 26.7), []),
    "GF wall bedroom-hamam south": ((7.8, 30.25, 26.7, 27.4), [D(10.2, 13.1, 'a', (0, 1)), D(18.6, 21.4, 'a', (0, 1)), D(23.5, 26.1, 'a', (0, -1))]),
    "GF wall hamam-bedroom":       ((17.5, 18.2, 27.4, 37.5), []),
    "GF wall store/kitchen-hamam": ((7.8, 8.5, 27.4, 37.5), [A(27.4, 31.9)]),
    "GF wall kitchen east":        ((8.6, 9.4, 21.6, 26.7), [D(21.9, 24.7, 'a', (-1, 0))]),
    "GF wall store-kitchen":       ((0.75, 7.8, 32.2, 32.6), [A(6.0, 7.8)]),
}
for n, (r, ops) in WALLS_GF.items():
    build_wall(n, r, ops, 0.0, H)

FOOTPRINT = [(0, 38.25), (31, 38.25), (31, 20.9), (28.5, 20.9), (28.5, 15.5), (31, 15.5),
             (31, 0), (17.5, 0), (17.5, 6.1), (1.7, 6.1), (1.7, 20.9), (0, 20.9)]
prism("Plinth", FOOTPRINT, GROUND, 0.0, M["plinth"], "Floors")

ROOMS = []   # (level, name, x0, x1, y0, y1) for labels + game HUD
def floors(rows, z):
    for n, a, b, c, d, m, show in rows:
        box(f"{LEVEL} floor {n}", a, b, c, d, z, z + 0.05, M[m], "Floors")
        if show:
            ROOMS.append({"level": LEVEL, "name": n, "rect": [a, b, c, d]})

floors([
    ("Store / Laundry",  0.75, 7.8, 32.6, 37.5, "concrete", True),
    ("Kitchen",          0.75, 8.6, 21.6, 32.2, "ktile", True),
    ("Hamam",            8.5, 17.5, 27.4, 37.5, "tile", True),
    ("Bed Room",         18.2, 30.25, 27.4, 37.5, "wood", True),
    ("Attach Washroom",  23.2, 30.25, 21.7, 26.7, "tile", True),
    ("Common Washroom",  18.2, 27.9, 15.5, 20.9, "tile", True),
    ("Drawing Room",     18.2, 30.25, 0.77, 14.7, "wood", True),
    ("Lounge",           2.5, 17.5, 6.8, 20.9, "marble", True),
    ("Corridor",         9.4, 22.5, 20.9, 26.7, "marble", True),
], 0.0)

# porch, back landing, site
box("Porch slab", 1.7, 17.5, -3.5, 6.1, GROUND, -0.5, M["paving"], "Site")
box("Porch step", 1.7, 17.5, -4.5, -3.5, GROUND, -1.0, M["paving"], "Site")
box("Porch threshold", 11.4, 15.4, 5.6, 6.1, -0.5, 0.0, M["stair"], "Site")
box("Back landing", 4.2, 8.4, 38.25, 40.9, GROUND, 0.0, M["concrete"], "Site")
box("Back step 1", 2.65, 4.2, 38.25, 40.9, GROUND, -0.5, M["concrete"], "Site")
box("Back step 2", 1.1, 2.65, 38.25, 40.9, GROUND, -1.0, M["concrete"], "Site")
for i, cx in enumerate((6.05, 17.06)):
    box(f"Porch column {i+1}", cx - 0.62, cx + 0.62, -3.12, -1.88, -0.5, H, M["wall"], "Site")
box("Ground", -400, 400, -400, 400, GROUND - 0.5, GROUND, M["grass"], "Site")
box("Front path", 9.0, 14.0, -60, -4.5, GROUND, GROUND + 0.02, M["paving"], "Site")
ROOMS.append({"level": "GF", "name": "Porch", "rect": [1.7, 17.5, -4.5, 6.1]})

# ---------------------------------------------------------------- stair GF -> SF (dog-leg: up west, landing, up south)
R = F2 / 16.0   # 16 risers
TREAD1, TREAD2 = 0.95, 0.7
for i in range(1, 7):
    xa = 11.7 - i * TREAD1
    box(f"Stair step {i}", xa, xa + TREAD1, 18.0, 20.9, 0.0, i * R, M["stair"], "Stairs")
cyl("Stair bullnose", 11.2, 18.0, 0.0, R, 0.9, M["stair"], "Stairs")
box("Stair landing", 2.5, 6.0, 17.0, 20.9, 0.0, 7 * R, M["stair"], "Stairs")
for k in range(1, 10):
    yb = 17.0 - (k - 1) * TREAD2
    top = (7 + k) * R
    box(f"Stair step {7+k}", 2.5, 6.0, yb - TREAD2, yb, top - R - 0.55, top, M["stair"], "Stairs")
RH = 3.0
pts1 = [(11.7 - i * TREAD1 + TREAD1 / 2, 18.15, i * R) for i in range(1, 7)]
pts2 = [(5.85, 17.0 - (k - 1) * TREAD2 - TREAD2 / 2, (7 + k) * R) for k in range(1, 10)]
for j, (x, y, z) in enumerate(pts1 + pts2):
    rod(f"Rail post {j}", (x, y, z), (x, y, z + RH), 0.07, M["steel"], "Stairs")
rod("Handrail A", (pts1[0][0], 18.15, pts1[0][2] + RH), (pts1[-1][0], 18.15, pts1[-1][2] + RH), 0.12, M["furn"], "Stairs")
rod("Handrail corner", (pts1[-1][0], 18.15, pts1[-1][2] + RH), (5.85, 18.15, 7 * R + RH), 0.12, M["furn"], "Stairs")
rod("Handrail landing", (5.85, 18.15, 7 * R + RH), (5.85, pts2[0][1], pts2[0][2] + RH), 0.12, M["furn"], "Stairs")
rod("Handrail B", (5.85, pts2[0][1], pts2[0][2] + RH), (5.85, pts2[-1][1], pts2[-1][2] + RH), 0.12, M["furn"], "Stairs")

# ---------------------------------------------------------------- furniture helpers
F = "Furniture"
def plant(n, x, y, z=0.0):
    cyl(n + " pot", x, y, z, z + 1.3, 0.55, M["pot"], F)
    sphere(n + " leaves", x, y, z + 2.4, 0.9, M["leaf"], F, sz=1.3)

def sofa(n, x0, x1, y0, y1, back, m=None, z=0.0, arm=0.5, seat_h=1.4, back_h=2.7):
    m = m or M["fabric"]
    box(n + " base", x0, x1, y0, y1, z + 0.05, z + seat_h, m, F)
    if back == "+x": box(n + " back", x1 - 0.6, x1, y0, y1, z + seat_h, z + back_h, m, F)
    if back == "-x": box(n + " back", x0, x0 + 0.6, y0, y1, z + seat_h, z + back_h, m, F)
    if back == "+y": box(n + " back", x0, x1, y1 - 0.6, y1, z + seat_h, z + back_h, m, F)
    if back == "-y": box(n + " back", x0, x1, y0, y0 + 0.6, z + seat_h, z + back_h, m, F)
    if back in ("+x", "-x"):
        box(n + " arm1", x0, x1, y0, y0 + arm, z + seat_h, z + 2.1, m, F)
        box(n + " arm2", x0, x1, y1 - arm, y1, z + seat_h, z + 2.1, m, F)
    else:
        box(n + " arm1", x0, x0 + arm, y0, y1, z + seat_h, z + 2.1, m, F)
        box(n + " arm2", x1 - arm, x1, y0, y1, z + seat_h, z + 2.1, m, F)

def wc(n, cx, cy, wall, z=0.0):
    dx, dy = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[wall]
    cyl(n + " bowl", cx, cy, z + 0.05, z + 1.35, 0.6, M["white"], F, sx=1.0 if dx == 0 else 1.25, sy=1.25 if dx == 0 else 1.0)
    tx, ty = cx + dx * 0.95, cy + dy * 0.95
    if dx:
        box(n + " cistern", tx - 0.35, tx + 0.35, ty - 0.75, ty + 0.75, z + 0.05, z + 2.6, M["white"], F)
    else:
        box(n + " cistern", tx - 0.75, tx + 0.75, ty - 0.35, ty + 0.35, z + 0.05, z + 2.6, M["white"], F)

def vanity(n, x0, x1, y0, y1, z=0.0):
    box(n + " cabinet", x0, x1, y0, y1, z + 0.05, z + 2.6, M["cabinet"], F)
    box(n + " top", x0, x1, y0, y1, z + 2.6, z + 2.75, M["counter"], F)
    cyl(n + " basin", (x0 + x1) / 2, (y0 + y1) / 2, z + 2.75, z + 3.1, 0.55, M["white"], F)

def shower(n, x0, x1, y0, y1, z=0.0):
    box(n + " tray", x0, x1, y0, y1, z + 0.05, z + 0.25, M["white"], F)

def bed(n, x0, x1, y0, y1, head, z=0.0, m=None):
    """Bed with headboard on side `head` ('+x', '-x', '+y')."""
    box(n + " base", x0, x1, y0, y1, z + 0.05, z + 1.3, M["furn"], F)
    box(n + " mattress", x0 + 0.1, x1 - 0.1, y0 + 0.1, y1 - 0.1, z + 1.3, z + 2.0, M["linen"], F)
    if head == "+x":
        box(n + " headboard", x1 - 0.2, x1 + 0.25, y0 - 0.1, y1 + 0.1, z + 0.05, z + 3.8, M["furn"], F)
        box(n + " pillows", x1 - 1.5, x1 - 0.4, y0 + 0.4, y1 - 0.4, z + 2.0, z + 2.4, M["white"], F)
        box(n + " throw", x0 + 0.1, x0 + 2.0, y0 + 0.05, y1 - 0.05, z + 2.0, z + 2.05, m or M["rug"], F)
    elif head == "-x":
        box(n + " headboard", x0 - 0.25, x0 + 0.2, y0 - 0.1, y1 + 0.1, z + 0.05, z + 3.8, M["furn"], F)
        box(n + " pillows", x0 + 0.4, x0 + 1.5, y0 + 0.4, y1 - 0.4, z + 2.0, z + 2.4, M["white"], F)
        box(n + " throw", x1 - 2.0, x1 - 0.1, y0 + 0.05, y1 - 0.05, z + 2.0, z + 2.05, m or M["rug"], F)
    else:
        box(n + " headboard", x0 - 0.1, x1 + 0.1, y1 - 0.2, y1 + 0.25, z + 0.05, z + 3.0, M["furn"], F)
        box(n + " pillows", x0 + 0.4, x1 - 0.4, y1 - 1.5, y1 - 0.4, z + 2.0, z + 2.4, M["white"], F)
        box(n + " throw", x0 + 0.05, x1 - 0.05, y0 + 0.1, y0 + 2.0, z + 2.0, z + 2.05, m or M["rug"], F)

# ---------------------------------------------------------------- ground floor furniture
box("Kitchen counter west", 0.75, 2.75, 23.6, 32.2, 0.05, 2.85, M["cabinet"], F)
box("Kitchen counter north", 2.75, 5.2, 30.2, 32.2, 0.05, 2.85, M["cabinet"], F)
box("Kitchen worktop west", 0.75, 2.85, 23.6, 32.2, 2.85, 3.0, M["counter"], F)
box("Kitchen worktop north", 2.75, 5.3, 30.1, 32.2, 2.85, 3.0, M["counter"], F)
box("Kitchen sink", 3.3, 4.7, 30.6, 31.8, 2.7, 3.01, M["steel"], F)
box("Kitchen hob", 1.0, 2.5, 25.2, 27.0, 3.0, 3.05, M["black"], F)
for j, (bx, by) in enumerate(((1.4, 25.6), (2.1, 25.6), (1.4, 26.6), (2.1, 26.6))):
    cyl(f"Kitchen burner {j}", bx, by, 3.05, 3.1, 0.2, M["steel"], F)
box("Kitchen upper cabinets", 0.75, 1.9, 23.6, 28.2, 5.0, 7.3, M["cabinet"], F)
box("Fridge", 3.7, 5.6, 21.65, 23.6, 0.05, 6.0, M["steel"], F)

box("Washer", 0.9, 2.6, 36.0, 37.45, 0.05, 2.9, M["white"], F)
box("Dryer", 0.9, 2.6, 34.5, 35.95, 0.05, 2.9, M["white"], F)
cyl("Washer door", 1.75, 36.7, 2.9, 2.95, 0.5, M["glass"], F)
box("Store shelves", 0.75, 4.0, 32.6, 33.8, 0.05, 6.5, M["furn"], F)

box("Bathtub", 9.0, 14.0, 34.9, 37.45, 0.05, 1.8, M["white"], F)
box("Bathtub water", 9.4, 13.6, 35.3, 37.05, 1.5, 1.55, M["glass"], F)
wc("Hamam WC", 16.6, 31.5, "+x")
vanity("Hamam vanity", 8.5, 9.9, 33.0, 35.0)

box("Bedroom rug", 23.0, 27.5, 28.3, 36.3, 0.05, 0.08, M["rug"], F)
bed("Bed", 24.0, 30.0, 29.4, 35.0, "+x")
box("Side table 1", 28.8, 30.25, 35.3, 36.7, 0.05, 2.0, M["furn"], F)
box("Side table 2", 28.8, 30.25, 27.7, 29.1, 0.05, 2.0, M["furn"], F)
box("TV unit", 18.2, 19.6, 31.0, 35.0, 0.05, 2.2, M["furn"], F)
box("Bedroom TV", 18.3, 18.45, 31.3, 34.7, 2.6, 5.0, M["black"], F)
sofa("Bedroom armchair", 19.6, 21.6, 35.4, 37.4, "+y", M["fabric2"])

wc("Attach WC", 29.0, 25.4, "+x")
vanity("Attach vanity", 26.0, 28.0, 21.7, 23.0)
shower("Attach shower", 28.3, 30.25, 21.7, 23.7)

wc("Common WC", 26.6, 17.9, "+x")
vanity("Common vanity", 22.0, 24.0, 15.5, 16.8)
shower("Common shower", 18.2, 20.5, 15.5, 17.6)

box("Drawing rug", 23.0, 29.0, 6.0, 13.0, 0.05, 0.08, M["rug"], F)
sofa("Drawing sofa", 27.8, 30.2, 6.5, 11.8, "+x")
sofa("Drawing armchair", 24.6, 27.4, 12.0, 14.6, "+y", M["fabric2"])
cyl("Drawing coffee table", 26.4, 9.7, 1.2, 1.4, 0.75, M["furn"], F, sx=1.0, sy=2.0)
cyl("Drawing coffee table leg", 26.4, 9.7, 0.05, 1.2, 0.3, M["furn"], F)
plant("Drawing plant 1", 29.4, 13.6)
plant("Drawing plant 2", 29.4, 5.4)

box("Lounge rug", 6.0, 11.0, 8.1, 11.9, 0.05, 0.08, M["rug"], F)
sofa("Lounge sofa", 5.6, 9.8, 7.0, 9.0, "-y")
sofa("Lounge armchair", 3.0, 5.2, 9.4, 11.8, "-x", M["fabric2"])
cyl("Lounge table", 8.8, 10.6, 1.2, 1.4, 0.75, M["furn"], F, sx=1.8, sy=1.0)
cyl("Lounge table leg", 8.8, 10.6, 0.05, 1.2, 0.3, M["furn"], F)
plant("Lounge plant", 3.3, 7.6)

GF_LABELS = (("STORE /\nLAUNDRY", 5.2, 35.0), ("KITCHEN\n7'x11'", 5.7, 26.5), ("HAMAM\n9'x10'", 13.0, 31.0),
             ("BED ROOM\n12'x10'", 21.4, 29.2), ("ATTACH\nWASHROOM", 26.0, 24.8), ("COMMON WASHROOM\n10'x5'6\"", 23.2, 18.6),
             ("DRAWING ROOM\n12'x14'", 21.6, 3.4), ("LOUNGE", 13.5, 14.0))
for txt, x, y in GF_LABELS:
    label(txt, x, y, 0.08)
label("PORCH", 9.5, 0.5, -0.48, 0.9)

# ================================================================ SECOND FLOOR (designed on the same walls)
LEVEL = "SF"
# slab between floors, with a hole over the stair (x 2.5-8.0, y 10.7-20.9)
for i, (a, b, c, d) in enumerate([
        (0.0, 31.0, 20.9, 38.25), (1.7, 2.5, 10.7, 20.9), (8.0, 28.5, 15.5, 20.9),
        (8.0, 17.5, 10.7, 15.5), (1.7, 17.5, 6.1, 10.7), (17.5, 31.0, 0.0, 15.5),
        (1.7, 17.5, -3.5, 6.1)]):
    box(f"SF slab {i}", a, b, c, d, H, F2, M["slab"], "Floors")

WALLS_SF = {
    "SF wall top (back)":        ((0.0, 31.0, 37.5, 38.25), [W(4.6, 6.8, 5.0), W(9.8, 13.8), W(21.4, 27.0)]),
    "SF wall study west":        ((0.0, 0.75, 20.9, 38.25), [W(25.0, 29.0)]),
    "SF wall study south":       ((0.0, 9.4, 20.9, 21.6), []),
    "SF wall lounge west":       ((1.7, 2.5, 6.1, 20.9), [W(7.5, 10.0), W(12.5, 15.5)]),
    "SF wall lounge front":      ((1.7, 17.5, 6.1, 6.8), [W(3.8, 7.7), D2(11.4, 15.4, (0, 1))]),
    "SF wall master west":       ((17.5, 18.2, 0.0, 21.7), [D(1.6, 4.8, 'b', (1, 0)), D(7.5, 10.3, 'a', (1, 0))]),
    "SF wall master front":      ((17.5, 31.0, 0.0, 0.77), [W(20.8, 27.4)]),
    "SF wall master east":       ((30.25, 31.0, 0.0, 15.5), []),
    "SF wall master north":      ((18.2, 31.0, 14.7, 15.5), []),
    "SF wall common bath east":  ((27.9, 28.5, 15.5, 20.9), [W(16.4, 19.4, 5.0)]),
    "SF wall east (bed + bath)": ((30.25, 31.0, 20.9, 37.5), [W(23.5, 25.5, 5.0)]),
    "SF wall baths north":       ((18.2, 30.25, 20.9, 21.7), [D(18.2, 20.6, 'a', (0, -1))]),
    "SF wall bath 2 west":       ((22.5, 23.2, 21.7, 26.7), []),
    "SF wall bedrooms south":    ((7.8, 30.25, 26.7, 27.4), [D(10.2, 13.1, 'a', (0, 1)), D(18.6, 21.4, 'a', (0, 1)), D(23.5, 26.1, 'a', (0, -1))]),
    "SF wall bed2-bed3":         ((17.5, 18.2, 27.4, 37.5), []),
    "SF wall bed3 west":         ((7.8, 8.5, 27.4, 37.5), [D(33.4, 35.6, 'b', (-1, 0))]),
    "SF wall study east":        ((8.6, 9.4, 21.6, 26.7), [D(21.9, 24.7, 'a', (-1, 0))]),
    "SF wall study-bath":        ((0.75, 7.8, 32.2, 32.6), []),
}
for n, (r, ops) in WALLS_SF.items():
    build_wall(n, r, ops, F2, H2)

floors([
    ("Bath 3",           0.75, 7.8, 32.6, 37.5, "tile", True),
    ("Study",            0.75, 8.6, 21.6, 32.2, "wood2", True),
    ("Bedroom 3",        8.5, 17.5, 27.4, 37.5, "wood2", True),
    ("Bedroom 2",        18.2, 30.25, 27.4, 37.5, "wood", True),
    ("Bath 2",           23.2, 30.25, 21.7, 26.7, "tile", True),
    ("Common Bath",      18.2, 27.9, 15.5, 20.9, "tile", True),
    ("Master Bedroom",   18.2, 30.25, 0.77, 14.7, "wood", True),
    ("Family Lounge",    8.0, 17.5, 6.8, 20.9, "marble", True),
    ("Stair Hall",       2.5, 8.0, 6.8, 10.7, "marble", True),
    ("Upper Corridor",   9.4, 22.5, 20.9, 26.7, "marble", True),
    ("Terrace",          2.15, 17.05, -3.05, 6.1, "terrace", True),
], F2)

# railing around the stair void
railing("Void rail east", (8.0, 10.7), (8.0, 20.85), F2)
railing("Void rail south", (6.0, 10.7), (8.0, 10.7), F2)
# terrace parapet over the porch
PH = 3.2
box("Terrace parapet front", 1.7, 17.5, -3.5, -3.05, F2, F2 + PH, M["wall"], "Walls")
box("Terrace parapet west", 1.7, 2.15, -3.05, 6.1, F2, F2 + PH, M["wall"], "Walls")
box("Terrace parapet east", 17.05, 17.5, -3.05, 0.0, F2, F2 + PH, M["wall"], "Walls")
box("Terrace coping front", 1.6, 17.6, -3.6, -2.95, F2 + PH, F2 + PH + 0.15, M["concrete"], "Walls")

z = F2
# master bedroom 12'x14' (over drawing room)
box("Master rug", 22.0, 28.5, 3.5, 12.0, z + 0.05, z + 0.08, M["rug2"], F)
bed("Master bed", 24.0, 30.0, 5.0, 10.6, "+x", z, M["rug2"])
box("Master side table 1", 28.9, 30.25, 3.4, 4.8, z + 0.05, z + 2.0, M["furn"], F)
box("Master side table 2", 28.9, 30.25, 10.8, 12.2, z + 0.05, z + 2.0, M["furn"], F)
box("Master wardrobe", 19.0, 24.0, 13.0, 14.7, z + 0.05, z + 7.2, M["furn"], F)
box("Master dresser", 18.2, 19.5, 11.0, 13.5, z + 0.05, z + 2.6, M["cabinet"], F)
sofa("Master armchair", 19.0, 21.0, 5.5, 7.4, "-y", M["fabric3"], z)
plant("Master plant", 19.2, 1.6, z)
# bedroom 2 (over ground bedroom)
box("Bedroom 2 rug", 23.0, 27.5, 28.3, 36.3, z + 0.05, z + 0.08, M["rug2"], F)
bed("Bedroom 2 bed", 24.0, 30.0, 29.4, 35.0, "+x", z, M["rug2"])
box("Bedroom 2 side table", 28.8, 30.25, 35.3, 36.7, z + 0.05, z + 2.0, M["furn"], F)
box("Bedroom 2 wardrobe", 18.2, 20.0, 30.0, 35.5, z + 0.05, z + 7.2, M["furn"], F)
# bedroom 3 (over hamam)
bed("Bedroom 3 bed", 12.8, 17.5, 31.0, 35.4, "+x", z, M["fabric3"])
box("Bedroom 3 desk", 8.5, 10.4, 28.0, 31.5, z + 2.4, z + 2.6, M["furn"], F)
box("Bedroom 3 desk legs", 8.6, 10.3, 28.1, 31.4, z + 0.05, z + 2.4, M["cabinet"], F)
box("Bedroom 3 chair", 10.6, 11.9, 29.1, 30.4, z + 0.05, z + 1.5, M["fabric3"], F)
box("Bedroom 3 wardrobe", 13.5, 17.5, 27.4, 28.9, z + 0.05, z + 7.2, M["furn"], F)
# study (over kitchen)
box("Study desk top", 0.75, 3.2, 25.5, 30.0, z + 2.4, z + 2.6, M["furn"], F)
box("Study desk legs", 0.85, 3.1, 25.6, 29.9, z + 0.05, z + 2.4, M["cabinet"], F)
box("Study monitor", 1.1, 1.3, 26.8, 28.7, z + 2.8, z + 4.2, M["black"], F)
box("Study chair", 3.5, 4.8, 27.0, 28.4, z + 0.05, z + 1.5, M["fabric"], F)
box("Study chair back", 4.6, 4.8, 27.0, 28.4, z + 1.5, z + 3.4, M["fabric"], F)
box("Study bookshelf", 2.0, 7.6, 31.0, 32.2, z + 0.05, z + 7.0, M["furn"], F)
box("Study books", 2.2, 7.4, 30.95, 31.1, z + 1.0, z + 6.6, M["books"], F)
sofa("Study sofa", 5.6, 7.7, 22.0, 26.0, "+x", M["fabric2"], z)
# baths
wc("Bath 3 WC", 1.6, 35.5, "-x", z)
vanity("Bath 3 vanity", 3.2, 5.2, 36.2, 37.5, z)
shower("Bath 3 shower", 0.75, 2.8, 32.6, 34.3, z)
wc("Bath 2 WC", 29.0, 25.4, "+x", z)
vanity("Bath 2 vanity", 26.0, 28.0, 21.7, 23.0, z)
shower("Bath 2 shower", 28.3, 30.25, 21.7, 23.7, z)
wc("Common bath WC", 26.6, 17.9, "+x", z)
vanity("Common bath vanity", 22.0, 24.0, 15.5, 16.8, z)
shower("Common bath shower", 18.2, 20.5, 15.5, 17.6, z)
# family lounge
box("Family rug", 10.0, 15.5, 11.0, 16.5, z + 0.05, z + 0.08, M["rug2"], F)
sofa("Family sofa", 14.7, 17.3, 11.0, 16.5, "+x", M["fabric"], z)
sofa("Family loveseat", 10.5, 14.0, 17.2, 19.4, "+y", M["fabric2"], z)
box("Family TV unit", 8.6, 9.6, 11.5, 16.0, z + 0.05, z + 2.0, M["furn"], F)
box("Family TV", 8.9, 9.05, 11.9, 15.6, z + 2.3, z + 5.0, M["black"], F)
cyl("Family table", 12.6, 13.7, z + 1.2, z + 1.4, 0.8, M["furn"], F, sx=1.0, sy=1.6)
cyl("Family table leg", 12.6, 13.7, z + 0.05, z + 1.2, 0.3, M["furn"], F)
plant("Family plant", 16.6, 7.6, z)
plant("Stair hall plant", 3.2, 7.6, z)
# terrace
for i, (cx, cy) in enumerate(((5.0, 0.5), (8.0, 0.5))):
    box(f"Terrace chair {i}", cx - 0.9, cx + 0.9, cy - 0.9, cy + 0.9, z + 0.05, z + 1.5, M["furn"], F)
    box(f"Terrace chair {i} back", cx - 0.9, cx + 0.9, cy - 0.9, cy - 0.7, z + 1.5, z + 3.0, M["furn"], F)
cyl("Terrace table", 6.5, 1.6, z + 2.2, z + 2.35, 0.9, M["steel"], F)
cyl("Terrace table leg", 6.5, 1.6, z + 0.05, z + 2.2, 0.12, M["steel"], F)
for i, cx in enumerate((3.0, 10.0, 15.8)):
    plant(f"Terrace plant {i}", cx, -2.2, z)

SF_LABELS = (("BATH 3", 4.2, 34.6), ("STUDY", 5.0, 24.0), ("BEDROOM 3", 13.0, 29.5), ("BEDROOM 2", 21.6, 29.0),
             ("BATH 2", 26.0, 24.8), ("COMMON BATH", 23.2, 18.6), ("MASTER BEDROOM\n12'x14'", 22.6, 2.6),
             ("FAMILY LOUNGE", 12.6, 9.0), ("TERRACE", 12.5, 2.5))
for txt, x, y in SF_LABELS:
    label(txt, x, y, F2 + 0.08)

# ================================================================ ROOF
prism("Roof slab", FOOTPRINT, TOP, TOP + SLAB, M["roof"], "Roof")
for i in range(len(FOOTPRINT)):
    (ax, ay), (bx, by) = FOOTPRINT[i], FOOTPRINT[(i + 1) % len(FOOTPRINT)]
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy); nx, ny = dy / L, -dx / L      # inward (polygon is clockwise)
    t = 0.45
    xs = [ax, bx, ax + nx * t, bx + nx * t]; ys = [ay, by, ay + ny * t, by + ny * t]
    box(f"Parapet {i}", min(xs), max(xs), min(ys), max(ys), TOP + SLAB, TOP + SLAB + 2.4, M["wall"], "Roof")

# ---------------------------------------------------------------- light, world, cameras
sun_data = bpy.data.lights.new("Sun", 'SUN')
sun_data.energy = 3.2
sun_data.angle = math.radians(3)
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (math.radians(42), math.radians(8), math.radians(35))
link(sun, "Lights")

world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.45, 0.62, 0.92, 1)
bg.inputs["Strength"].default_value = 0.5

def camera(name, loc, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 500
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho * FT
    c = bpy.data.objects.new(name, cd)
    c.location = Vector(loc) * FT
    d = Vector(target) * FT - c.location
    c.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return link(c, "Cameras")

cam_ext = camera("Cam exterior", (62, -48, 40), (15.0, 16.0, 8.0), lens=32)
cam_back = camera("Cam back", (-30, 72, 34), (15.0, 22.0, 8.0), lens=32)
cam_cut = camera("Cam cutaway", (-8, -20, 64), (15.5, 19.0, F2), lens=34)
cam_top = camera("Cam plan top", (15.5, 18.2, 90), (15.5, 18.2, 0.0), ortho=48)
scene.camera = cam_cut

for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
try:
    scene.view_settings.view_transform = 'Standard'
except TypeError:
    pass

def shoot(cam, path, show, res=(1600, 1000)):
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    for n in ("Roof", "Second Floor", "GF Labels", "SF Labels"):
        COLLS[n].hide_render = n not in show
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

if RENDER:
    out = os.path.join(ROOT, "renders", "v1")
    os.makedirs(out, exist_ok=True)
    shoot(cam_ext, os.path.join(out, "1_exterior.png"), {"Roof", "Second Floor"})
    shoot(cam_back, os.path.join(out, "2_back.png"), {"Roof", "Second Floor"})
    shoot(cam_cut, os.path.join(out, "3_cutaway_second_floor.png"), {"Second Floor"})
    shoot(cam_top, os.path.join(out, "4_plan_ground.png"), {"GF Labels"}, res=(1400, 1600))
    shoot(cam_top, os.path.join(out, "5_plan_second.png"), {"Second Floor", "SF Labels"}, res=(1400, 1600))

# ---------------------------------------------------------------- game export (GLB + room/wall data)
game = os.path.join(ROOT, "site", "v1")
os.makedirs(game, exist_ok=True)
for o in scene.objects:
    o.select_set(False)
skip_colls = {"GF Labels", "SF Labels", "Cameras", "Lights"}
for o in scene.objects:
    if o.type == 'MESH' and not any(c.name in skip_colls for c in o.users_collection):
        o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(game, "house.glb"), export_format='GLB',
                          use_selection=True, export_extras=True, export_apply=True,
                          export_cameras=False, export_lights=False)
data = {
    "ft": FT,
    "levels": {"GF": 0.0, "SF": F2},
    "heights": {"GF": H, "SF": H2},
    "rooms": ROOMS,
    "walls": {"GF": [r for r, _ in WALLS_GF.values()], "SF": [r for r, _ in WALLS_SF.values()]},
    "footprint": FOOTPRINT,
    "doors": DOORS,
    "spawn": [11.5, -22.0, GROUND],
}
with open(os.path.join(game, "house.json"), "w") as fh:
    json.dump(data, fh, indent=1)

# viewport: roof hidden so you can look inside; hide "Second Floor" to see the ground floor
for n in ("GF Labels", "SF Labels"):
    COLLS[n].hide_render = True
COLLS["Roof"].hide_render = False
COLLS["Second Floor"].hide_render = False
bpy.context.view_layer.layer_collection.children["Roof"].hide_viewport = True
scene.camera = cam_cut
for o in scene.objects:
    o.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "house_v1.blend"))
print("HOUSE_DONE", len(bpy.data.objects), "objects", len(DOORS), "doors")
