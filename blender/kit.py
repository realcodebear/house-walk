"""Shared building kit for the v2 houses.

Numbers going in are FEET in plan coordinates (x = right on the drawing, y = up on the drawing, z = up);
meshes come out in metres. Design scripts import this module, call the builders, then `finish(...)`
which renders previews, exports site/v2/<design>/house.glb + house.json and saves the .blend.
"""
import bpy, bmesh, math, os, json
from mathutils import Vector

FT = 0.3048
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "blender", "tex")
DOOR_H = 7.0

LEVEL_PARENT = {"GF": "Ground Floor", "SF": "Second Floor", "AT": "Attic"}
LEVEL_COLLS = {"Walls", "Openings", "Floors", "Furniture", "Labels", "Stairs", "Ceilings", "Facade"}
STATE = {"level": "GF"}
COLLS, MATS, MATINFO = {}, {}, {}
DOORS, FANS, LIGHTS, ROOMS, SPAWNS = [], [], [], [], []
LEVELS = {}            # name -> {"z": floor level ft, "h": ceiling height ft, "label": str}
WALL_RECTS = {}        # level -> [rect, ...] for the minimap
STYLE = {}             # filled by the design: materials for frames, doors, glass ...


# ================================================================ scene + collections
def reset_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.images):
        for d in list(c):
            c.remove(d)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    sc = bpy.context.scene
    sc.unit_settings.system = 'IMPERIAL'
    sc.unit_settings.length_unit = 'FEET'


def level(name, z=None, h=None, label=None):
    STATE["level"] = name
    if z is not None:
        LEVELS[name] = {"z": z, "h": h, "label": label or name}


def coll(name, parent=None):
    if name not in COLLS:
        c = bpy.data.collections.new(name)
        (coll(parent) if parent else bpy.context.scene.collection).children.link(c)
        COLLS[name] = c
    return COLLS[name]


def link(obj, cname):
    lv = STATE["level"]
    c = coll(f"{lv} {cname}", LEVEL_PARENT[lv]) if cname in LEVEL_COLLS else coll(cname)
    c.objects.link(obj)
    return obj


# ================================================================ materials
def _img(name, noncolor=False):
    for ext in (".jpg", ".png"):
        p = os.path.join(TEX, name + ext)
        if os.path.exists(p):
            img = bpy.data.images.load(p, check_existing=True)
            if noncolor:
                img.colorspace_settings.name = 'Non-Color'
            return img
    raise FileNotFoundError(name)


def _sock(node, ident, out=False):
    return next(s for s in (node.outputs if out else node.inputs) if s.identifier == ident)


def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, tex=None, nrm=None, nrm_strength=1.0, tile=1.0,
        uv="world", emit=None, emit_strength=0.0, alpha=1.0, alpha_tex=False, double=False, rot=False):
    """tile = metres covered by one texture repeat. uv: 'world' (tiles by size) or 'fit' (stretches 0..1).
    rot = turn the texture 90 degrees (e.g. floor boards running along x)."""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if tex:
        ti = nt.nodes.new("ShaderNodeTexImage")
        ti.image = _img(tex)
        if tuple(color) != (1, 1, 1):
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = 'RGBA'
            mix.blend_type = 'MULTIPLY'
            mix.inputs[0].default_value = 1.0
            nt.links.new(ti.outputs["Color"], _sock(mix, "A_Color"))
            _sock(mix, "B_Color").default_value = (*color, 1)
            nt.links.new(_sock(mix, "Result_Color", out=True), b.inputs["Base Color"])
            m["tint"] = list(color)           # the web engine applies it (glTF has no multiply node)
        else:
            nt.links.new(ti.outputs["Color"], b.inputs["Base Color"])
        if alpha_tex:
            nt.links.new(ti.outputs["Alpha"], b.inputs["Alpha"])
    else:
        b.inputs["Base Color"].default_value = (*color, 1)
    if nrm:
        ni = nt.nodes.new("ShaderNodeTexImage")
        ni.image = _img(nrm, noncolor=True)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nrm_strength
        nt.links.new(ni.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1 or alpha_tex:
        if alpha < 1:
            b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    m.use_backface_culling = not (double or alpha < 1 or alpha_tex)
    m.diffuse_color = (*color, alpha)
    MATS[name] = m
    MATINFO[name] = {"tile": tile, "uv": uv if tex or nrm else None, "rot": rot}
    return m


# ================================================================ meshes
def _uv(me, m, offset=(0.0, 0.0, 0.0)):
    info = MATINFO.get(m.name if m else "", {})
    mode = info.get("uv")
    if not mode:
        return
    tile, rot = info["tile"], info.get("rot")
    uvl = me.uv_layers.new(name="UVMap")
    ox, oy, oz = offset
    if mode == "fit":
        xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
        span = (max(xs) - min(xs) or 1, max(ys) - min(ys) or 1, max(zs) - min(zs) or 1)
        mn = (min(xs), min(ys), min(zs))
    for p in me.polygons:
        n = p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            c = me.vertices[me.loops[li].vertex_index].co
            x, y, z = c.x + ox, c.y + oy, c.z + oz
            if mode == "fit":
                fx, fy, fz = (c.x - mn[0]) / span[0], (c.y - mn[1]) / span[1], (c.z - mn[2]) / span[2]
                u, v = (fx, fy) if ax == 2 else (fy, fz) if ax == 0 else (fx, fz)
            else:
                u, v = ((x, y) if ax == 2 else (y, z) if ax == 0 else (x, z))
                u, v = u / tile, v / tile
            if rot:
                u, v = v, -u
            uvl.data[li].uv = (u, v)


def mesh_obj(name, verts, faces, m, cname, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(v) * FT for v in verts], [], faces)
    me.update()
    me.materials.append(m)
    _uv(me, m)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    return link(o, cname)


def box(name, x0, x1, y0, y1, z0, z1, m, cname="Furniture"):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mesh_obj(name, v, f, m, cname)


def prism(name, pts, z0, z1, m, cname="Floors"):
    """Vertical extrusion of a 2D polygon (plan feet)."""
    n = len(pts)
    v = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    f = [tuple(reversed(range(n))), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    o = mesh_obj(name, v, f, m, cname)
    _fix_normals(o)
    return o


def solid(name, verts, faces, m, cname="Furniture"):
    """Arbitrary closed mesh from vertices (ft) + faces; normals recalculated outward."""
    o = mesh_obj(name, verts, faces, m, cname)
    _fix_normals(o)
    return o


def _fix_normals(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    while o.data.uv_layers:
        o.data.uv_layers.remove(o.data.uv_layers[0])
    _uv(o.data, o.data.materials[0])


def slab3d(name, pts, thick, m, cname="Facade"):
    """A flat polygon in 3D (ft) thickened along its normal (roof planes, gable boards...)."""
    P = [Vector(p) for p in pts]
    nrm = (P[1] - P[0]).cross(P[2] - P[0]).normalized()
    top = [p + nrm * thick for p in P]
    n = len(P)
    v = [tuple(p) for p in P] + [tuple(p) for p in top]
    f = [tuple(reversed(range(n))), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return solid(name, v, f, m, cname)


def cyl(name, cx, cy, z0, z1, r, m, cname="Furniture", sx=1.0, sy=1.0, seg=24, r2=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r * FT, radius2=(r if r2 is None else r2) * FT, depth=(z1 - z0) * FT)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    _uv(me, m, (cx * FT, cy * FT, (z0 + z1) / 2 * FT))
    o = bpy.data.objects.new(name, me)
    o.location = (cx * FT, cy * FT, (z0 + z1) / 2 * FT)
    o.scale = (sx, sy, 1)
    return link(o, cname)


def sphere(name, cx, cy, cz, r, m, cname="Furniture", sx=1.0, sy=1.0, sz=1.0, sub=2):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r * FT)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    _uv(me, m)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    o.location = (cx * FT, cy * FT, cz * FT)
    o.scale = (sx, sy, sz)
    return link(o, cname)


def rod(name, p1, p2, r, m, cname="Furniture", seg=10):
    a, b = Vector(p1) * FT, Vector(p2) * FT
    d = b - a
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r * FT, radius2=r * FT, depth=d.length)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    o.location = (a + b) / 2
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    return link(o, cname)


def label(text, x, y, z, size=0.7):
    cu = bpy.data.curves.new("Label " + text, 'FONT')
    cu.body = text
    cu.size = size * FT
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    o = bpy.data.objects.new(f"{STATE['level']} label {text.splitlines()[0]}", cu)
    o.data.materials.append(mat("Label", (0.05, 0.05, 0.06)))
    o.location = (x * FT, y * FT, z * FT)
    return link(o, "Labels")


def arch_outline(a, b, z_spring, top, steps=14):
    """2D outline (along, z) of the wall piece above an arched opening: arch from a to b springing at z_spring."""
    r = (b - a) / 2
    mid = (a + b) / 2
    pts = [(a, z_spring)]
    for i in range(1, steps):
        t = math.pi - math.pi * i / steps
        pts.append((mid + r * math.cos(t), z_spring + r * math.sin(t)))
    pts += [(b, z_spring), (b, top), (a, top)]
    return pts


def wall_profile(name, along_x, rect, outline, m, cname):
    """Extrude a 2D outline (along-axis, z) across the wall thickness."""
    x0, x1, y0, y1 = rect
    if along_x:
        v = [(u, y0, z) for u, z in outline] + [(u, y1, z) for u, z in outline]
    else:
        v = [(x0, u, z) for u, z in outline] + [(x1, u, z) for u, z in outline]
    n = len(outline)
    f = [tuple(reversed(range(n))), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return solid(name, v, f, m, cname)


# ================================================================ walls, windows, doors
def D(a, b, hinge='a', side=(0, 1), arch=False):            # single door
    return {"kind": "door", "a": a, "b": b, "sill": 0.0, "head": DOOR_H, "hinge": hinge, "side": side, "arch": arch}


def D2(a, b, side=(0, 1), arch=False, head=DOOR_H):        # double door
    return {"kind": "door2", "a": a, "b": b, "sill": 0.0, "head": head, "side": side, "arch": arch}


def W(a, b, sill=3.0, head=DOOR_H, arch=False, lattice=False, curtains=True, grille=False):
    return {"kind": "win", "a": a, "b": b, "sill": sill, "head": head, "arch": arch, "lattice": lattice,
            "curtains": curtains, "grille": grille}


def A(a, b, head=DOOR_H, arch=False):                       # open archway
    return {"kind": "arch", "a": a, "b": b, "sill": 0.0, "head": head, "arch": arch}


def wall(name, rect, openings=(), zb=0.0, h=10.0, m=None, inside=None, frames=True, cname="Walls"):
    """Axis-aligned wall box with openings. inside: '+x' | '-x' | '+y' | '-y' (room side) for curtains/trim."""
    m = m or STYLE["wall"]
    x0, x1, y0, y1 = rect
    along_x = (x1 - x0) >= (y1 - y0)
    lo, hi = (x0, x1) if along_x else (y0, y1)
    if frames:
        WALL_RECTS.setdefault(STATE["level"], []).append([x0, x1, y0, y1])

    def piece(tag, a, b, z0, z1):
        if b - a < 1e-3 or z1 - z0 < 1e-3:
            return
        if along_x:
            box(f"{name} {tag}", a, b, y0, y1, zb + z0, zb + z1, m, cname)
        else:
            box(f"{name} {tag}", x0, x1, a, b, zb + z0, zb + z1, m, cname)

    cur = lo
    for i, o in enumerate(sorted(openings, key=lambda o: o["a"])):
        a, b, sill, head = o["a"], o["b"], o["sill"], o["head"]
        piece(f"solid{i}", cur, a, 0, h)
        piece(f"below{i}", a, b, 0, sill)
        if o.get("arch"):
            r = (b - a) / 2
            spring = head - r
            wall_profile(f"{name} arch{i}", along_x, rect, [(u, zb + z) for u, z in arch_outline(a, b, spring, h)], m, cname)
        else:
            piece(f"above{i}", a, b, head, h)
        cur = b
        if not frames:
            continue
        if o["kind"] == "win":
            window(f"{name} window{i}", along_x, rect, o, zb, inside)
        elif o["kind"] == "door":
            door_frame(f"{name} door{i}", along_x, rect, a, b, zb, head, o.get("arch"))
            door_leaf(f"{name} door{i} leaf", along_x, rect, a, b, zb, o["hinge"], o["side"], head=head)
        elif o["kind"] == "door2":
            mid = (a + b) / 2
            door_frame(f"{name} door{i}", along_x, rect, a, b, zb, head, o.get("arch"))
            door_leaf(f"{name} door{i} leafL", along_x, rect, a, mid, zb, 'a', o["side"], 80, pair=True, head=head)
            door_leaf(f"{name} door{i} leafR", along_x, rect, mid, b, zb, 'b', o["side"], 80, pair=True, head=head)
        elif o["kind"] == "arch" and STYLE.get("arch_trim"):
            door_frame(f"{name} opening{i}", along_x, rect, a, b, zb, head, o.get("arch"), leafless=True)
    piece("end", cur, hi, 0, h)


def span_box(name, along_x, rect, a, b, z0, z1, t0, t1, m, cname="Openings"):
    """Box spanning a..b along the wall, t0..t1 across it (fractions of thickness; may go outside 0..1)."""
    x0, x1, y0, y1 = rect
    if along_x:
        th = y1 - y0
        return box(name, a, b, y0 + th * t0, y0 + th * t1, z0, z1, m, cname)
    th = x1 - x0
    return box(name, x0 + th * t0, x0 + th * t1, a, b, z0, z1, m, cname)


def _inside_t(rect, along_x, inside):
    """Which face is the room side: returns (face t, direction) in thickness fractions."""
    if inside in ("+y", "+x"):
        return 1.0, 1
    if inside in ("-y", "-x"):
        return 0.0, -1
    return None, 0


def window(name, along_x, rect, o, zb, inside):
    a, b = o["a"], o["b"]
    sill, head = zb + o["sill"], zb + o["head"]
    fm, gm = STYLE["frame"], STYLE["glass"]
    f = 0.16
    arch = o.get("arch")
    top = head - (b - a) / 2 if arch else head          # straight frame stops at the spring line
    span_box(name + " frame L", along_x, rect, a, a + f, sill, top, 0.38, 0.62, fm)
    span_box(name + " frame R", along_x, rect, b - f, b, sill, top, 0.38, 0.62, fm)
    span_box(name + " frame B", along_x, rect, a, b, sill, sill + f, 0.38, 0.62, fm)
    if not arch:
        span_box(name + " frame T", along_x, rect, a, b, head - f, head, 0.38, 0.62, fm)
    w = b - a
    n = 2 if w < 5 else 3
    for k in range(1, n):
        u = a + w * k / n
        span_box(f"{name} mullion{k}", along_x, rect, u - f / 2, u + f / 2, sill, top, 0.4, 0.6, fm)
    if not arch and head - sill > 4.5:
        span_box(name + " transom", along_x, rect, a, b, head - 1.4, head - 1.4 + f, 0.4, 0.6, fm)
    span_box(name + " glass", along_x, rect, a + f, b - f, sill + f, top if arch else head - f, 0.48, 0.52, gm)
    if arch:
        r = (b - a) / 2
        x0, x1, y0, y1 = rect
        th = (y1 - y0) if along_x else (x1 - x0)
        base = (y0 if along_x else x0)
        sub = (rect[0], rect[1], base + th * 0.48, base + th * 0.52) if along_x else (base + th * 0.48, base + th * 0.52, rect[2], rect[3])
        out = [(a + f, top)] + [((a + b) / 2 + (r - f) * math.cos(math.pi - math.pi * i / 14), top + (r - f) * math.sin(math.pi - math.pi * i / 14)) for i in range(1, 14)] + [(b - f, top)]
        wall_profile(name + " glass arch", along_x, sub, out, gm, "Openings")
        ring = [(a, top)] + [((a + b) / 2 + r * math.cos(math.pi - math.pi * i / 14), top + r * math.sin(math.pi - math.pi * i / 14)) for i in range(1, 14)] + [(b, top)]
        ring_in = [(u, z) for u, z in reversed(out)]
        sub2 = (rect[0], rect[1], base + th * 0.38, base + th * 0.62) if along_x else (base + th * 0.38, base + th * 0.62, rect[2], rect[3])
        wall_profile(name + " frame arch", along_x, sub2, ring + ring_in, fm, "Openings")
    span_box(name + " sill", along_x, rect, a - 0.2, b + 0.2, sill - 0.14, sill, -0.2, 1.2, STYLE.get("sill", fm))
    if o.get("lattice") and STYLE.get("lattice"):
        t_in, d = _inside_t(rect, along_x, inside)
        tl = 0.7 if d >= 0 else 0.3
        span_box(name + " lattice", along_x, rect, a + f, b - f, sill + f, (top if arch else head - f), tl - 0.02, tl + 0.02, STYLE["lattice"])
    if o.get("grille") and STYLE.get("iron"):
        x0, x1, y0, y1 = rect
        k = int((b - a) / 0.45)
        for i in range(1, k):
            u = a + (b - a) * i / k
            span_box(f"{name} grille{i}", along_x, rect, u - 0.03, u + 0.03, sill + f, top if arch else head - f, -0.12, -0.06, STYLE["iron"])
    if o.get("curtains") and inside and STYLE.get("curtain"):
        curtains(name + " curtain", along_x, rect, a, b, sill, head, inside)


def curtains(name, along_x, rect, a, b, sill, head, inside):
    """Two pleated panels drawn to the sides, hung from a rod just above the window."""
    x0, x1, y0, y1 = rect
    cm = STYLE["curtain"]
    off = 0.35
    if along_x:
        face = y1 if inside == "+y" else y0
        s = 1 if inside == "+y" else -1
    else:
        face = x1 if inside == "+x" else x0
        s = 1 if inside == "+x" else -1
    top, bot = head + 0.6, max(sill - 0.6, head - 7.4)
    for k, (u0, u1) in enumerate(((a - 0.9, a + 0.5), (b - 0.5, b + 0.9))):
        verts, faces = [], []
        steps = 9
        for i in range(steps + 1):
            u = u0 + (u1 - u0) * i / steps
            dep = face + s * (off + (0.12 if i % 2 else 0.0))
            for z in (bot, top):
                verts.append((u, dep, z) if along_x else (dep, u, z))
        for i in range(steps):
            q = i * 2
            faces.append((q, q + 2, q + 3, q + 1))
        o = mesh_obj(f"{name}{k}", verts, faces, cm, "Openings", smooth=True)
    rp = (lambda u: (u, face + s * off, top + 0.08)) if along_x else (lambda u: (face + s * off, u, top + 0.08))
    rod(name + " rod", rp(a - 1.0), rp(b + 1.0), 0.05, STYLE.get("metal", cm), "Openings")


def door_frame(name, along_x, rect, a, b, zb, head, arch=False, leafless=False):
    """Jambs + head inside the opening and architrave trim on both faces (English style)."""
    fm = STYLE["door_frame"]
    f = 0.12
    if not arch:
        span_box(name + " jamb L", along_x, rect, a, a + f, zb, head, 0.0, 1.0, fm)
        span_box(name + " jamb R", along_x, rect, b - f, b, zb, head, 0.0, 1.0, fm)
        span_box(name + " head", along_x, rect, a, b, head - f, head, 0.0, 1.0, fm)
        tw = 0.28
        for t0, t1 in ((-0.06, 0.0), (1.0, 1.06)):
            span_box(name + " trim L", along_x, rect, a - tw, a + 0.02, zb, head + tw, t0, t1, fm)
            span_box(name + " trim R", along_x, rect, b - 0.02, b + tw, zb, head + tw, t0, t1, fm)
            span_box(name + " trim T", along_x, rect, a - tw, b + tw, head - 0.02, head + tw, t0, t1, fm)
    else:
        r = (b - a) / 2
        spring = head - r
        span_box(name + " jamb L", along_x, rect, a, a + f, zb, spring, 0.0, 1.0, fm)
        span_box(name + " jamb R", along_x, rect, b - f, b, zb, spring, 0.0, 1.0, fm)
        ring = arch_outline(a, b, spring, spring)[:-2]
        inner = [((a + b) / 2 + (r - f) * math.cos(math.pi - math.pi * i / 14), spring + (r - f) * math.sin(math.pi - math.pi * i / 14)) for i in range(0, 15)]
        wall_profile(name + " arch ring", along_x, rect, ring + list(reversed(inner)), fm, "Openings")


def door_leaf(name, along_x, rect, a, b, zb, hinge, side, open_deg=78, pair=False, head=DOOR_H):
    """English panel door: leaf (collision box) + raised panels and lever handles as children."""
    x0, x1, y0, y1 = rect
    f, t = 0.12, 0.15
    w = (b - a) - f - 0.02 if pair else (b - a) - 2 * f
    h = head - f - 0.04
    if along_x:
        cy = (y0 + y1) / 2
        hp = (a + f if hinge == 'a' else b - f, cy)
        base = 0.0 if hinge == 'a' else math.pi
    else:
        cx = (x0 + x1) / 2
        hp = (cx, a + f if hinge == 'a' else b - f)
        base = math.pi / 2 if hinge == 'a' else -math.pi / 2
    dm = STYLE["door"]
    o = box(name, 0, w, -t / 2, t / 2, 0.03, h, dm, "Openings")
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
    DOORS.append(name)
    style = STYLE.get("door_style", "english")
    pm = STYLE.get("door_panel", dm)

    def child(nm, x0_, x1_, y0_, y1_, z0_, z1_, m):
        c = box(nm, x0_, x1_, y0_, y1_, z0_, z1_, m, "Openings")
        c.parent = o
        return c

    if style == "english":
        # six raised panels: 2 columns x (small top, tall middle, mid bottom)
        mx, gap = 0.28, 0.22
        cw = (w - 2 * mx - gap) / 2
        rows = [(0.45, 2.1), (2.45, 5.0), (5.35, h - 0.45)]
        for side_y in (t / 2, -t / 2 - 0.04):
            for c in range(2):
                u0 = mx + c * (cw + gap)
                for r0, r1 in rows:
                    child(f"{name} panel", u0, u0 + cw, side_y, side_y + 0.04, r0, r1, pm)
    elif style == "plank":
        for side_y in (t / 2, -t / 2 - 0.03):
            for zz in (0.9, h - 1.0):
                child(f"{name} strap", 0.1, w - 0.1, side_y, side_y + 0.03, zz, zz + 0.25, STYLE.get("iron", dm))
    elif style == "carved":
        mx = 0.3
        for side_y in (t / 2, -t / 2 - 0.05):
            child(f"{name} carving", mx, w - mx, side_y, side_y + 0.05, 0.5, h - 0.5, pm)
            for k in range(4):
                z = 1.0 + k * (h - 2.0) / 3
                child(f"{name} rosette", w / 2 - 0.35, w / 2 + 0.35, side_y + 0.03, side_y + 0.07, z - 0.35, z + 0.35, STYLE.get("door_frame", dm))
    hm = STYLE.get("handle", STYLE.get("metal"))
    for sy in (t / 2 + 0.02, -t / 2 - 0.12):
        child(f"{name} plate", w - 0.42, w - 0.3, sy, sy + 0.1, 2.9, 3.7, hm)
        child(f"{name} lever", w - 0.75, w - 0.3, sy + (0.06 if sy > 0 else -0.06), sy + (0.12 if sy > 0 else 0.0), 3.42, 3.5, hm)


# ================================================================ interior finishes
def floor(name, rect, z, m, room=None, show=True):
    x0, x1, y0, y1 = rect
    box(f"{STATE['level']} floor {name}", x0, x1, y0, y1, z, z + 0.05, m, "Floors")
    if room is not False:
        add_room(room or name, [rect], show)


def add_room(name, rects, show=True):
    for r in ROOMS:
        if r["name"] == name and r["level"] == STATE["level"]:
            r["rects"] += [list(x) for x in rects]
            return
    ROOMS.append({"level": STATE["level"], "name": name, "rects": [list(x) for x in rects], "show": show})


def false_ceiling(name, rect, ceil, drop=0.75, border=1.6, m=None, cove=True, downlights=True, center=None):
    """Gypsum drop ceiling: a lowered border band with an LED cove around the raised centre, plus downlights."""
    m = m or STYLE.get("ceiling", STYLE["wall"])
    x0, x1, y0, y1 = rect
    zb = ceil - drop
    th = 0.25
    box(name + " band S", x0, x1, y0, y0 + border, zb, zb + th, m, "Ceilings")
    box(name + " band N", x0, x1, y1 - border, y1, zb, zb + th, m, "Ceilings")
    box(name + " band W", x0, x0 + border, y0 + border, y1 - border, zb, zb + th, m, "Ceilings")
    box(name + " band E", x1 - border, x1, y0 + border, y1 - border, zb, zb + th, m, "Ceilings")
    lip = 0.35
    for nm, r in (("S", (x0 + border, x1 - border, y0 + border, y0 + border + 0.08)),
                  ("N", (x0 + border, x1 - border, y1 - border - 0.08, y1 - border)),
                  ("W", (x0 + border, x0 + border + 0.08, y0 + border, y1 - border)),
                  ("E", (x1 - border - 0.08, x1 - border, y0 + border, y1 - border))):
        box(f"{name} lip {nm}", *r, zb + th, zb + th + lip, m, "Ceilings")
    if cove:
        led = STYLE["led"]
        for nm, r in (("S", (x0 + border - 0.05, x1 - border + 0.05, y0 + border - 0.12, y0 + border - 0.02)),
                      ("N", (x0 + border - 0.05, x1 - border + 0.05, y1 - border + 0.02, y1 - border + 0.12)),
                      ("W", (x0 + border - 0.12, x0 + border - 0.02, y0 + border, y1 - border)),
                      ("E", (x1 - border + 0.02, x1 - border + 0.12, y0 + border, y1 - border))):
            box(f"{name} cove {nm}", *r, zb + th, zb + th + 0.06, led, "Ceilings")
    if center is not None:
        box(name + " centre", x0 + border, x1 - border, y0 + border, y1 - border, ceil - 0.06, ceil, center, "Ceilings")
    if downlights:
        dl = STYLE["downlight"]
        for (u, v) in ((x0 + border / 2, y0 + border / 2), (x1 - border / 2, y0 + border / 2),
                       (x0 + border / 2, y1 - border / 2), (x1 - border / 2, y1 - border / 2)):
            cyl(f"{name} downlight", u, v, zb - 0.02, zb, 0.16, dl, "Ceilings", seg=16)


def panel_wall(name, rect, z0, z1, m=None, cname="Walls"):
    """MDF panelling / tiles: a thin finish box laid on a wall face (rect is the finish volume, ft)."""
    x0, x1, y0, y1 = rect
    return box(name, x0, x1, y0, y1, z0, z1, m or STYLE["mdf"], cname)


def wainscot(name, rect, z0, h, m, gaps=None, t=0.05, faces="SNWE"):
    """Finish layer (tiles, MDF, stone) on the inner faces of a room from z0 up h feet.
    gaps: {'S': [(a, b), ...], ...} openings along each face (x for S/N faces, y for W/E faces)."""
    x0, x1, y0, y1 = rect
    gaps = gaps or {}

    def runs(lo, hi, gl):
        cur, out = lo, []
        for a, b in sorted(gl):
            if a > cur:
                out.append((cur, min(a, hi)))
            cur = max(cur, b)
        if cur < hi:
            out.append((cur, hi))
        return [(a, b) for a, b in out if b - a > 0.05]

    if "S" in faces:
        for a, b in runs(x0, x1, gaps.get("S", [])): box(f"{name} S", a, b, y0, y0 + t, z0, z0 + h, m, "Walls")
    if "N" in faces:
        for a, b in runs(x0, x1, gaps.get("N", [])): box(f"{name} N", a, b, y1 - t, y1, z0, z0 + h, m, "Walls")
    if "W" in faces:
        for a, b in runs(y0, y1, gaps.get("W", [])): box(f"{name} W", x0, x0 + t, a, b, z0, z0 + h, m, "Walls")
    if "E" in faces:
        for a, b in runs(y0, y1, gaps.get("E", [])): box(f"{name} E", x1 - t, x1, a, b, z0, z0 + h, m, "Walls")


def cornice(name, rect, ceil, m=None, d=0.22, hgt=0.3):
    m = m or STYLE.get("trim", STYLE["wall"])
    x0, x1, y0, y1 = rect
    for nm, r in (("S", (x0, x1, y0, y0 + d)), ("N", (x0, x1, y1 - d, y1)), ("W", (x0, x0 + d, y0, y1)), ("E", (x1 - d, x1, y0, y1))):
        box(f"{name} cornice {nm}", *r, ceil - hgt, ceil, m, "Ceilings")


def light(x, y, z, color=(1.0, 0.82, 0.6), power=1.0, room=None):
    """A point light for the web engine (a pool of real lights follows the player)."""
    LIGHTS.append({"level": STATE["level"], "x": x, "y": y, "z": z, "color": list(color), "power": power})


def fan(name, x, y, ceil, m_body, m_blade, drop=1.2):
    rod(name + " rod", (x, y, ceil), (x, y, ceil - drop), 0.06, m_body)
    cyl(name + " motor", x, y, ceil - drop - 0.35, ceil - drop, 0.45, m_body, seg=20)
    me = bpy.data.meshes.new(name + " rotor")
    bm = bmesh.new()
    for k in range(3):
        a = k * 2 * math.pi / 3
        ca, sa = math.cos(a), math.sin(a)
        L, W0, W1 = 2.6, 0.2, 0.42
        quad = [(0.3, -W0), (L, -W1), (L, W1), (0.3, W0)]
        vs = []
        for (u, v) in quad:
            vs.append(bm.verts.new(((u * ca - v * sa) * FT, (u * sa + v * ca) * FT, 0.0)))
        for (u, v) in quad:
            vs.append(bm.verts.new(((u * ca - v * sa) * FT, (u * sa + v * ca) * FT, 0.04 * FT)))
        bm.faces.new(vs[:4][::-1]); bm.faces.new(vs[4:])
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((vs[i], vs[j], vs[4 + j], vs[4 + i]))
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m_blade)
    o = bpy.data.objects.new(name + " rotor", me)
    o.location = (x * FT, y * FT, (ceil - drop - 0.3) * FT)
    o["spin"] = 3.2
    FANS.append(o.name)
    link(o, "Furniture")


# ================================================================ stairs
def stair_flight(name, steps, m, riser, waist=0.55, floor_z=None):
    """steps: (x0, x1, y0, y1, top_z) treads in ft. floor_z given -> blocks run down to that floor (solid flight);
    otherwise each tread is a floating block `riser + waist` deep, which reads as a sawtooth stringer."""
    for i, (x0, x1, y0, y1, top) in enumerate(steps):
        bottom = floor_z if floor_z is not None else top - riser - waist
        box(f"{name} step{i}", x0, x1, y0, y1, bottom, top, m, "Stairs")


def railing(name, pts, z_list, h=3.1, kind="glass"):
    """Railing along a polyline of plan points with matching floor heights (ft)."""
    post = STYLE.get("rail_post", STYLE.get("metal"))
    top = STYLE.get("rail_top", STYLE.get("door"))
    for i in range(len(pts) - 1):
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        za, zb = z_list[i], z_list[i + 1]
        rod(f"{name} rail{i}", (xa, ya, za + h), (xb, yb, zb + h), 0.11, top, "Stairs")
        L = math.hypot(xb - xa, yb - ya)
        n = max(1, int(L / (0.5 if kind != "glass" else 3.0)))
        for k in range(n + (1 if i == len(pts) - 2 else 0)):
            t = k / n
            x, y, z = xa + (xb - xa) * t, ya + (yb - ya) * t, za + (zb - za) * t
            rod(f"{name} post{i}_{k}", (x, y, z), (x, y, z + h), 0.06 if kind != "glass" else 0.08, post, "Stairs")
        if kind == "glass":
            gm = STYLE["glass"]
            d = 0.03
            nx, ny = (-(yb - ya) / L, (xb - xa) / L)
            v = [(xa - nx * d, ya - ny * d, za + 0.3), (xb - nx * d, yb - ny * d, zb + 0.3), (xb - nx * d, yb - ny * d, zb + h - 0.25), (xa - nx * d, ya - ny * d, za + h - 0.25),
                 (xa + nx * d, ya + ny * d, za + 0.3), (xb + nx * d, yb + ny * d, zb + 0.3), (xb + nx * d, yb + ny * d, zb + h - 0.25), (xa + nx * d, ya + ny * d, za + h - 0.25)]
            f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
            solid(f"{name} glass{i}", v, f, gm, "Stairs")
        elif kind == "iron":
            rod(f"{name} lowrail{i}", (xa, ya, za + 0.35), (xb, yb, zb + 0.35), 0.05, post, "Stairs")


# ================================================================ roofs
def roof_gable(name, x0, x1, y0, y1, z_eave, pitch_deg, m_roof, m_under, m_gable, thick=0.35, ridge_m=None, along="y"):
    """Gable roof over the rectangle, ridge along `along`. Returns the ridge height (ft)."""
    if along == "y":
        half = (x1 - x0) / 2
        rise = half * math.tan(math.radians(pitch_deg))
        xm, zr = (x0 + x1) / 2, z_eave + rise
        slab3d(name + " slope W", [(x0, y0, z_eave), (x0, y1, z_eave), (xm, y1, zr), (xm, y0, zr)], thick, m_roof, "Facade")
        slab3d(name + " slope E", [(xm, y0, zr), (xm, y1, zr), (x1, y1, z_eave), (x1, y0, z_eave)], thick, m_roof, "Facade")
        # underside lining (seen from inside the attic)
        slab3d(name + " lining W", [(xm, y0, zr - 0.02), (xm, y1, zr - 0.02), (x0, y1, z_eave - 0.02), (x0, y0, z_eave - 0.02)], 0.05, m_under, "Facade")
        slab3d(name + " lining E", [(x1, y0, z_eave - 0.02), (x1, y1, z_eave - 0.02), (xm, y1, zr - 0.02), (xm, y0, zr - 0.02)], 0.05, m_under, "Facade")
        if ridge_m:
            rod(name + " ridge", (xm, y0 - 0.2, zr + thick + 0.05), (xm, y1 + 0.2, zr + thick + 0.05), 0.28, ridge_m, "Facade")
        return zr
    raise NotImplementedError


def roof_hip(name, x0, x1, y0, y1, z_eave, pitch_deg, m_roof, m_under, thick=0.3):
    """Hip roof: ridge along the longer side."""
    w, d = x1 - x0, y1 - y0
    if d >= w:
        half = w / 2
        rise = half * math.tan(math.radians(pitch_deg))
        zr = z_eave + rise
        xm = (x0 + x1) / 2
        ya, yb = y0 + half, y1 - half
        faces = {
            "W": [(x0, y0, z_eave), (x0, y1, z_eave), (xm, yb, zr), (xm, ya, zr)],
            "E": [(xm, ya, zr), (xm, yb, zr), (x1, y1, z_eave), (x1, y0, z_eave)],
            "S": [(x1, y0, z_eave), (x0, y0, z_eave), (xm, ya, zr)],
            "N": [(x0, y1, z_eave), (x1, y1, z_eave), (xm, yb, zr)],
        }
    else:
        half = d / 2
        rise = half * math.tan(math.radians(pitch_deg))
        zr = z_eave + rise
        ym = (y0 + y1) / 2
        xa, xb = x0 + half, x1 - half
        faces = {
            "S": [(x1, y0, z_eave), (x0, y0, z_eave), (xa, ym, zr), (xb, ym, zr)],
            "N": [(x0, y1, z_eave), (x1, y1, z_eave), (xb, ym, zr), (xa, ym, zr)],
            "W": [(x0, y0, z_eave), (x0, y1, z_eave), (xa, ym, zr)],
            "E": [(x1, y1, z_eave), (x1, y0, z_eave), (xb, ym, zr)],
        }
    for k, pts in faces.items():
        slab3d(f"{name} {k}", pts, thick, m_roof, "Facade")
    box(name + " soffit", x0, x1, y0, y1, z_eave - 0.15, z_eave - 0.05, m_under, "Facade")
    return zr


# ================================================================ furniture library
F = "Furniture"


def sofa(n, x0, x1, y0, y1, back, m, z=0.0, legs=None, cushions=True, arm=0.55, seat=1.5, top=2.8):
    """Sofa with base, seat cushions, back cushions and arms. back = side of the backrest."""
    legs = legs or STYLE.get("wood_dark")
    lh = 0.35
    for (lx, ly) in ((x0 + 0.2, y0 + 0.2), (x1 - 0.2, y0 + 0.2), (x0 + 0.2, y1 - 0.2), (x1 - 0.2, y1 - 0.2)):
        cyl(n + " leg", lx, ly, z, z + lh, 0.07, legs, F, seg=8)
    box(n + " base", x0, x1, y0, y1, z + lh, z + seat - 0.35, m, F)
    horiz = back in ("+y", "-y")
    L = (x1 - x0) if horiz else (y1 - y0)
    D_ = (y1 - y0) if horiz else (x1 - x0)
    inner0 = arm
    inner1 = L - arm
    k = max(1, round((inner1 - inner0) / 2.2))
    bd = 0.75
    for i in range(k):
        u0 = inner0 + (inner1 - inner0) * i / k + 0.03
        u1 = inner0 + (inner1 - inner0) * (i + 1) / k - 0.03
        if back == "-y":
            box(f"{n} seat{i}", x0 + u0, x0 + u1, y0 + bd, y1 - 0.05, z + seat - 0.35, z + seat, m, F)
            box(f"{n} backc{i}", x0 + u0, x0 + u1, y0 + 0.25, y0 + bd + 0.1, z + seat, z + top, m, F)
        elif back == "+y":
            box(f"{n} seat{i}", x0 + u0, x0 + u1, y0 + 0.05, y1 - bd, z + seat - 0.35, z + seat, m, F)
            box(f"{n} backc{i}", x0 + u0, x0 + u1, y1 - bd - 0.1, y1 - 0.25, z + seat, z + top, m, F)
        elif back == "-x":
            box(f"{n} seat{i}", x0 + bd, x1 - 0.05, y0 + u0, y0 + u1, z + seat - 0.35, z + seat, m, F)
            box(f"{n} backc{i}", x0 + 0.25, x0 + bd + 0.1, y0 + u0, y0 + u1, z + seat, z + top, m, F)
        else:
            box(f"{n} seat{i}", x0 + 0.05, x1 - bd, y0 + u0, y0 + u1, z + seat - 0.35, z + seat, m, F)
            box(f"{n} backc{i}", x1 - bd - 0.1, x1 - 0.25, y0 + u0, y0 + u1, z + seat, z + top, m, F)
    if back == "-y": box(n + " back", x0, x1, y0, y0 + 0.3, z + lh, z + top + 0.1, m, F)
    if back == "+y": box(n + " back", x0, x1, y1 - 0.3, y1, z + lh, z + top + 0.1, m, F)
    if back == "-x": box(n + " back", x0, x0 + 0.3, y0, y1, z + lh, z + top + 0.1, m, F)
    if back == "+x": box(n + " back", x1 - 0.3, x1, y0, y1, z + lh, z + top + 0.1, m, F)
    if horiz:
        box(n + " armL", x0, x0 + arm, y0, y1, z + lh, z + 2.2, m, F)
        box(n + " armR", x1 - arm, x1, y0, y1, z + lh, z + 2.2, m, F)
    else:
        box(n + " armL", x0, x1, y0, y0 + arm, z + lh, z + 2.2, m, F)
        box(n + " armR", x0, x1, y1 - arm, y1, z + lh, z + 2.2, m, F)
    if cushions and STYLE.get("cushion"):
        cm = STYLE["cushion"]
        if horiz:
            yy = y1 - bd - 0.05 if back == "+y" else y0 + bd + 0.05
            for cx in (x0 + arm + 0.7, x1 - arm - 0.7):
                box(n + " pillow", cx - 0.6, cx + 0.6, min(yy, yy + (0.35 if back == '-y' else -0.35)), max(yy, yy + (0.35 if back == '-y' else -0.35)), z + seat, z + seat + 1.1, cm, F)
        else:
            xx = x1 - bd - 0.05 if back == "+x" else x0 + bd + 0.05
            for cy in (y0 + arm + 0.7, y1 - arm - 0.7):
                box(n + " pillow", min(xx, xx + (0.35 if back == '-x' else -0.35)), max(xx, xx + (0.35 if back == '-x' else -0.35)), cy - 0.6, cy + 0.6, z + seat, z + seat + 1.1, cm, F)


def bed(n, x0, x1, y0, y1, head, z=0.0, linen=None, throw=None, frame=None, headboard=None, hb_h=4.2):
    linen = linen or STYLE["linen"]
    frame = frame or STYLE["wood_dark"]
    headboard = headboard or frame
    box(n + " frame", x0, x1, y0, y1, z + 0.3, z + 1.2, frame, F)
    for (lx, ly) in ((x0 + 0.15, y0 + 0.15), (x1 - 0.15, y0 + 0.15), (x0 + 0.15, y1 - 0.15), (x1 - 0.15, y1 - 0.15)):
        box(n + " leg", lx - 0.12, lx + 0.12, ly - 0.12, ly + 0.12, z, z + 0.3, frame, F)
    box(n + " mattress", x0 + 0.1, x1 - 0.1, y0 + 0.1, y1 - 0.1, z + 1.2, z + 1.95, linen, F)
    tm = throw or STYLE.get("throw", linen)
    if head == "+x":
        box(n + " headboard", x1 - 0.1, x1 + 0.25, y0 - 0.25, y1 + 0.25, z, z + hb_h, headboard, F)
        box(n + " duvet", x0 + 0.05, x1 - 1.9, y0 + 0.05, y1 - 0.05, z + 1.4, z + 2.12, linen, F)
        box(n + " throw", x0 + 0.02, x0 + 1.9, y0 + 0.02, y1 - 0.02, z + 1.5, z + 2.16, tm, F)
        for cy in ((y0 + y1) / 2 - 1.3, (y0 + y1) / 2 + 1.3):
            box(n + " pillow", x1 - 1.6, x1 - 0.35, cy - 1.0, cy + 1.0, z + 1.95, z + 2.55, STYLE.get("pillow", linen), F)
    elif head == "-x":
        box(n + " headboard", x0 - 0.25, x0 + 0.1, y0 - 0.25, y1 + 0.25, z, z + hb_h, headboard, F)
        box(n + " duvet", x0 + 1.9, x1 - 0.05, y0 + 0.05, y1 - 0.05, z + 1.4, z + 2.12, linen, F)
        box(n + " throw", x1 - 1.9, x1 - 0.02, y0 + 0.02, y1 - 0.02, z + 1.5, z + 2.16, tm, F)
        for cy in ((y0 + y1) / 2 - 1.3, (y0 + y1) / 2 + 1.3):
            box(n + " pillow", x0 + 0.35, x0 + 1.6, cy - 1.0, cy + 1.0, z + 1.95, z + 2.55, STYLE.get("pillow", linen), F)
    elif head == "+y":
        box(n + " headboard", x0 - 0.25, x1 + 0.25, y1 - 0.1, y1 + 0.25, z, z + hb_h, headboard, F)
        box(n + " duvet", x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 1.9, z + 1.4, z + 2.12, linen, F)
        box(n + " throw", x0 + 0.02, x1 - 0.02, y0 + 0.02, y0 + 1.9, z + 1.5, z + 2.16, tm, F)
        for cx in ((x0 + x1) / 2 - 1.3, (x0 + x1) / 2 + 1.3):
            box(n + " pillow", cx - 1.0, cx + 1.0, y1 - 1.6, y1 - 0.35, z + 1.95, z + 2.55, STYLE.get("pillow", linen), F)


def table(n, x0, x1, y0, y1, h, top_m, leg_m=None, z=0.0, thick=0.12, round_=False):
    leg_m = leg_m or top_m
    if round_:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cyl(n + " top", cx, cy, z + h - thick, z + h, (x1 - x0) / 2, top_m, F, sy=(y1 - y0) / (x1 - x0), seg=32)
        cyl(n + " stem", cx, cy, z, z + h - thick, 0.18, leg_m, F, seg=12)
        cyl(n + " foot", cx, cy, z, z + 0.08, 0.7, leg_m, F, seg=16)
        return
    box(n + " top", x0, x1, y0, y1, z + h - thick, z + h, top_m, F)
    for (lx, ly) in ((x0 + 0.2, y0 + 0.2), (x1 - 0.2, y0 + 0.2), (x0 + 0.2, y1 - 0.2), (x1 - 0.2, y1 - 0.2)):
        box(n + " leg", lx - 0.08, lx + 0.08, ly - 0.08, ly + 0.08, z, z + h - thick, leg_m, F)


def chair(n, cx, cy, face, m_wood, m_seat, z=0.0):
    """Dining chair centred at (cx, cy) facing direction `face` ('+x', '-x', '+y', '-y')."""
    s = 0.8
    for (dx, dy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        lx, ly = cx + dx * (s - 0.1), cy + dy * (s - 0.1)
        box(n + " leg", lx - 0.06, lx + 0.06, ly - 0.06, ly + 0.06, z, z + 1.5, m_wood, F)
    box(n + " seat", cx - s, cx + s, cy - s, cy + s, z + 1.5, z + 1.7, m_seat, F)
    bx = {"+x": (cx - s, cx - s + 0.15, cy - s, cy + s), "-x": (cx + s - 0.15, cx + s, cy - s, cy + s),
          "+y": (cx - s, cx + s, cy - s, cy - s + 0.15), "-y": (cx - s, cx + s, cy + s - 0.15, cy + s)}[face]
    box(n + " back", *bx, z + 1.7, z + 3.3, m_wood, F)


def wardrobe(n, x0, x1, y0, y1, h, m, handle=None, z=0.0, front="+y"):
    box(n + " body", x0, x1, y0, y1, z, z + h, m, F)
    hm = handle or STYLE.get("handle")
    horiz = front in ("+y", "-y")
    L = (x1 - x0) if horiz else (y1 - y0)
    k = max(2, round(L / 1.6))
    for i in range(1, k):
        u = (x0 if horiz else y0) + L * i / k
        if front == "+y": box(n + " seam", u - 0.02, u + 0.02, y1, y1 + 0.02, z + 0.2, z + h - 0.2, STYLE.get("wood_dark", m), F)
        if front == "-y": box(n + " seam", u - 0.02, u + 0.02, y0 - 0.02, y0, z + 0.2, z + h - 0.2, STYLE.get("wood_dark", m), F)
        if front == "+x": box(n + " seam", x1, x1 + 0.02, u - 0.02, u + 0.02, z + 0.2, z + h - 0.2, STYLE.get("wood_dark", m), F)
        if front == "-x": box(n + " seam", x0 - 0.02, x0, u - 0.02, u + 0.02, z + 0.2, z + h - 0.2, STYLE.get("wood_dark", m), F)
    for i in range(k):
        u = (x0 if horiz else y0) + L * (i + 0.5) / k + (0.35 if i % 2 == 0 else -0.35)
        if front == "+y": box(n + " handle", u - 0.03, u + 0.03, y1 + 0.02, y1 + 0.1, z + 3.0, z + 4.4, hm, F)
        if front == "-y": box(n + " handle", u - 0.03, u + 0.03, y0 - 0.1, y0 - 0.02, z + 3.0, z + 4.4, hm, F)
        if front == "+x": box(n + " handle", x1 + 0.02, x1 + 0.1, u - 0.03, u + 0.03, z + 3.0, z + 4.4, hm, F)
        if front == "-x": box(n + " handle", x0 - 0.1, x0 - 0.02, u - 0.03, u + 0.03, z + 3.0, z + 4.4, hm, F)


def lamp(n, cx, cy, z, shade_m=None, base_m=None, h=2.0, r=0.55, on=True):
    shade_m = shade_m or STYLE["lampshade"]
    base_m = base_m or STYLE.get("metal")
    cyl(n + " base", cx, cy, z, z + h * 0.6, 0.12, base_m, F, seg=12)
    cyl(n + " shade", cx, cy, z + h * 0.55, z + h, r, shade_m, F, r2=r * 0.7, seg=20)


def plant(n, x, y, z=0.0, h=3.0, pot_m=None, leaf_m=None):
    pot_m = pot_m or STYLE.get("pot")
    leaf_m = leaf_m or STYLE.get("leaf")
    cyl(n + " pot", x, y, z, z + 1.2, 0.55, pot_m, F, r2=0.45, seg=16)
    for k, (dx, dy, dz, r) in enumerate(((0, 0, h * 0.75, 0.75), (0.35, 0.2, h * 0.55, 0.55), (-0.3, -0.25, h * 0.6, 0.55), (0.1, -0.35, h * 0.9, 0.5))):
        sphere(f"{n} leaf{k}", x + dx, y + dy, z + dz, r, leaf_m, F, sz=1.25, sub=1)


def rug(n, x0, x1, y0, y1, m, z=0.0):
    box(n, x0, x1, y0, y1, z + 0.05, z + 0.09, m, F)


def frame_art(n, along, at, u0, u1, z0, z1, inside, m_art, m_frame=None):
    """Picture on a wall face: along 'x' wall (face at y = at) or 'y' wall (face at x = at)."""
    m_frame = m_frame or STYLE.get("wood_dark")
    s = 1 if inside in ("+y", "+x") else -1
    if along == "x":
        box(n + " frame", u0 - 0.12, u1 + 0.12, at, at + s * 0.1, z0 - 0.12, z1 + 0.12, m_frame, F)
        box(n + " art", u0, u1, at + s * 0.1, at + s * 0.13, z0, z1, m_art, F)
    else:
        box(n + " frame", at, at + s * 0.1, u0 - 0.12, u1 + 0.12, z0 - 0.12, z1 + 0.12, m_frame, F)
        box(n + " art", at + s * 0.1, at + s * 0.13, u0, u1, z0, z1, m_art, F)


def tv(n, along, at, u0, u1, z0, inside, m_black):
    s = 1 if inside in ("+y", "+x") else -1
    h = (u1 - u0) * 0.5625
    if along == "x":
        box(n, u0, u1, at + s * 0.05, at + s * 0.15, z0, z0 + h, m_black, F)
    else:
        box(n, at + s * 0.05, at + s * 0.15, u0, u1, z0, z0 + h, m_black, F)


def bookshelf(n, x0, x1, y0, y1, h, m, books, z=0.0, front="+y"):
    box(n + " back", x0, x1, y0, y1, z, z + 0.08, m, F)
    rows = int(h / 1.3)
    horiz = front in ("+y", "-y")
    for r in range(rows + 1):
        zz = z + r * h / rows
        box(f"{n} shelf{r}", x0, x1, y0, y1, zz, zz + 0.08, m, F)
        if r < rows:
            L = (x1 - x0) if horiz else (y1 - y0)
            u = 0.1
            k = 0
            while u < L - 0.4:
                w = 0.12 + (k * 37 % 7) * 0.025
                hh = 0.75 + (k * 53 % 5) * 0.08
                bm_ = books[k % len(books)]
                if horiz:
                    box(f"{n} book", x0 + u, x0 + u + w, y0 + 0.1, y1 - 0.1, zz + 0.08, zz + 0.08 + hh, bm_, F)
                else:
                    box(f"{n} book", x0 + 0.1, x1 - 0.1, y0 + u, y0 + u + w, zz + 0.08, zz + 0.08 + hh, bm_, F)
                u += w + 0.01
                k += 1
                if k % 9 == 0:
                    u += 0.6
    for (a, b) in ((x0, x0 + 0.08), (x1 - 0.08, x1)) if horiz else ((y0, y0 + 0.08), (y1 - 0.08, y1)):
        if horiz:
            box(n + " side", a, b, y0, y1, z, z + h, m, F)
        else:
            box(n + " side", x0, x1, a, b, z, z + h, m, F)


def wc(n, cx, cy, wall_side, z=0.0):
    wm = STYLE["ceramic"]
    dx, dy = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[wall_side]
    cyl(n + " pedestal", cx - dx * 0.2, cy - dy * 0.2, z, z + 1.0, 0.42, wm, F, sx=1.0 if dx == 0 else 1.3, sy=1.3 if dx == 0 else 1.0, seg=20)
    cyl(n + " bowl", cx - dx * 0.25, cy - dy * 0.25, z + 1.0, z + 1.35, 0.62, wm, F, sx=1.0 if dx == 0 else 1.3, sy=1.3 if dx == 0 else 1.0, seg=24)
    tx, ty = cx + dx * 0.75, cy + dy * 0.75
    if dx:
        box(n + " cistern", tx - 0.3, tx + 0.3, ty - 0.8, ty + 0.8, z + 1.0, z + 2.6, wm, F)
    else:
        box(n + " cistern", tx - 0.8, tx + 0.8, ty - 0.3, ty + 0.3, z + 1.0, z + 2.6, wm, F)


def vanity(n, x0, x1, y0, y1, z=0.0, mirror_side=None, cab=None):
    cab = cab or STYLE.get("wood_dark")
    box(n + " cabinet", x0, x1, y0, y1, z + 0.6, z + 2.6, cab, F)
    box(n + " top", x0 - 0.05, x1 + 0.05, y0 - 0.05, y1 + 0.05, z + 2.6, z + 2.75, STYLE.get("counter"), F)
    cyl(n + " basin", (x0 + x1) / 2, (y0 + y1) / 2, z + 2.75, z + 3.05, 0.6, STYLE["ceramic"], F, seg=24)
    if mirror_side:
        mm = STYLE.get("mirror")
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if mirror_side == "+y": box(n + " mirror", cx - 1.0, cx + 1.0, y1 - 0.05, y1, z + 3.6, z + 6.2, mm, F)
        if mirror_side == "-y": box(n + " mirror", cx - 1.0, cx + 1.0, y0, y0 + 0.05, z + 3.6, z + 6.2, mm, F)
        if mirror_side == "+x": box(n + " mirror", x1 - 0.05, x1, cy - 1.0, cy + 1.0, z + 3.6, z + 6.2, mm, F)
        if mirror_side == "-x": box(n + " mirror", x0, x0 + 0.05, cy - 1.0, cy + 1.0, z + 3.6, z + 6.2, mm, F)


def shower(n, x0, x1, y0, y1, z=0.0, glass_side=None):
    box(n + " tray", x0, x1, y0, y1, z, z + 0.15, STYLE["ceramic"], F)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cyl(n + " head", cx, cy, z + 7.0, z + 7.05, 0.4, STYLE.get("metal"), F, seg=16)
    if glass_side:
        gm = STYLE["glass"]
        if glass_side == "x0": box(n + " screen", x0, x0 + 0.04, y0, y1, z + 0.15, z + 6.6, gm, F)
        if glass_side == "x1": box(n + " screen", x1 - 0.04, x1, y0, y1, z + 0.15, z + 6.6, gm, F)
        if glass_side == "y0": box(n + " screen", x0, x1, y0, y0 + 0.04, z + 0.15, z + 6.6, gm, F)
        if glass_side == "y1": box(n + " screen", x0, x1, y1 - 0.04, y1, z + 0.15, z + 6.6, gm, F)


def kitchen_run(n, x0, x1, y0, y1, z=0.0, upper=True, front="+x", cab=None, top=None, handle=None):
    """Base cabinets with worktop, plinth, doors and handles; optional upper cabinets."""
    cab = cab or STYLE["cabinet"]
    top = top or STYLE["counter"]
    handle = handle or STYLE.get("handle")
    box(n + " plinth", x0 + (0.1 if front == "-x" else 0), x1 - (0.1 if front == "+x" else 0), y0 + (0.1 if front == "-y" else 0), y1 - (0.1 if front == "+y" else 0), z, z + 0.35, STYLE.get("wood_dark", cab), F)
    box(n + " base", x0, x1, y0, y1, z + 0.35, z + 2.85, cab, F)
    box(n + " worktop", x0 - (0.08 if front == "-x" else 0), x1 + (0.08 if front == "+x" else 0), y0 - (0.08 if front == "-y" else 0), y1 + (0.08 if front == "+y" else 0), z + 2.85, z + 3.0, top, F)
    horiz = front in ("+y", "-y")
    L = (x1 - x0) if horiz else (y1 - y0)
    k = max(1, round(L / 1.5))
    for i in range(k):
        u = (x0 if horiz else y0) + L * (i + 0.5) / k
        if front == "+x": box(n + " handle", x1, x1 + 0.08, u - 0.4, u + 0.4, z + 2.5, z + 2.56, handle, F)
        if front == "-x": box(n + " handle", x0 - 0.08, x0, u - 0.4, u + 0.4, z + 2.5, z + 2.56, handle, F)
        if front == "+y": box(n + " handle", u - 0.4, u + 0.4, y1, y1 + 0.08, z + 2.5, z + 2.56, handle, F)
        if front == "-y": box(n + " handle", u - 0.4, u + 0.4, y0 - 0.08, y0, z + 2.5, z + 2.56, handle, F)
        if i:
            v = (x0 if horiz else y0) + L * i / k
            if front == "+x": box(n + " seam", x1, x1 + 0.02, v - 0.015, v + 0.015, z + 0.45, z + 2.75, STYLE.get("wood_dark", cab), F)
            if front == "-x": box(n + " seam", x0 - 0.02, x0, v - 0.015, v + 0.015, z + 0.45, z + 2.75, STYLE.get("wood_dark", cab), F)
            if front == "+y": box(n + " seam", v - 0.015, v + 0.015, y1, y1 + 0.02, z + 0.45, z + 2.75, STYLE.get("wood_dark", cab), F)
            if front == "-y": box(n + " seam", v - 0.015, v + 0.015, y0 - 0.02, y0, z + 0.45, z + 2.75, STYLE.get("wood_dark", cab), F)
    if upper:
        d = 1.1
        if front == "+x": ux = (x0, x0 + d, y0, y1)
        elif front == "-x": ux = (x1 - d, x1, y0, y1)
        elif front == "+y": ux = (x0, x1, y0, y0 + d)
        else: ux = (x0, x1, y1 - d, y1)
        box(n + " upper", *ux, z + 5.0, z + 7.4, cab, F)


# ================================================================ site
def tree(n, x, y, z, h=14.0, trunk_m=None, leaf_m=None, r=4.0):
    trunk_m = trunk_m or STYLE.get("bark")
    leaf_m = leaf_m or STYLE.get("leaf")
    cyl(n + " trunk", x, y, z, z + h * 0.55, 0.45, trunk_m, "Site", r2=0.3, seg=10)
    for k, (dx, dy, dz, rr) in enumerate(((0, 0, 0.75, 1.0), (1.4, 0.8, 0.62, 0.75), (-1.3, -0.6, 0.66, 0.8), (0.4, -1.4, 0.85, 0.7), (-0.6, 1.3, 0.9, 0.65))):
        sphere(f"{n} crown{k}", x + dx * r * 0.45, y + dy * r * 0.45, z + h * dz, r * rr, leaf_m, "Site", sz=0.85, sub=2)


def hedge(n, x0, x1, y0, y1, z, h, leaf_m=None):
    box(n, x0, x1, y0, y1, z, z + h, leaf_m or STYLE.get("leaf"), "Site")


# ================================================================ export
def camera(name, loc, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 600
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho * FT
    c = bpy.data.objects.new(name, cd)
    c.location = Vector(loc) * FT
    d = Vector(target) * FT - c.location
    c.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    link(c, "Cameras")
    return c


def sun_and_sky(color=(0.45, 0.62, 0.92), strength=0.55, sun=3.0, rot=(42, 8, 35)):
    sd = bpy.data.lights.new("Sun", 'SUN')
    sd.energy = sun
    sd.angle = math.radians(3)
    s = bpy.data.objects.new("Sun", sd)
    s.rotation_euler = tuple(math.radians(a) for a in rot)
    link(s, "Lights")
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength


def render(cam, path, hide=(), res=(1600, 1000)):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    hidden = []
    for c in COLLS.values():
        if c.name in hide:
            c.hide_render = True
            hidden.append(c)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for c in hidden:
        c.hide_render = False


def finish(design, data, renders=(), blend_name=None):
    """Export the game model + data, write renders, save the .blend."""
    out = os.path.join(ROOT, "site", "v2", design)
    os.makedirs(out, exist_ok=True)
    if os.environ.get("HOUSE_RENDER", "1") == "1":
        rdir = os.path.join(ROOT, "renders", "v2")
        os.makedirs(rdir, exist_ok=True)
        for cam, fname, hide, res in renders:
            render(cam, os.path.join(rdir, f"{design}_{fname}.png"), hide, res)
    sc = bpy.context.scene
    for o in sc.objects:
        o.select_set(False)
    skip = {c for c in COLLS if c.endswith("Labels")} | {"Cameras", "Lights"}
    for o in sc.objects:
        if o.type == 'MESH' and not any(c.name in skip for c in o.users_collection):
            o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "house.glb"), export_format='GLB', use_selection=True,
                              export_extras=True, export_apply=True, export_cameras=False, export_lights=False,
                              export_image_format='AUTO')
    data = dict(data)
    data.update({"ft": FT, "levels": LEVELS, "rooms": ROOMS, "walls": WALL_RECTS, "doors": DOORS, "fans": FANS,
                 "lights": LIGHTS, "spawns": SPAWNS})
    with open(os.path.join(out, "house.json"), "w") as fh:
        json.dump(data, fh, indent=1)
    for c in COLLS.values():
        if c.name.endswith("Labels"):
            c.hide_render = True
    for o in sc.objects:
        o.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", blend_name or f"house_v2_{design}.blend"))
    print("HOUSE_DONE", design, len(sc.objects), "objects", len(DOORS), "doors")
