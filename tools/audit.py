"""Furniture placement audit for a built design.

    /Applications/Blender.app/Contents/MacOS/Blender -b -y blender/house_v2_<design>.blend -P tools/audit.py -- <design> [--render]

Checks, per floor:
  1. furniture pushed into walls (deeper than 0.15 ft),
  2. furniture overlapping other furniture,
  3. furniture inside a door's swing,
  4. circulation: every room reachable on foot from the entrance with the player's body width,
and (with --render) writes a top-down picture of every floor without ceilings to renders/audit/.
Prints a report and writes renders/audit/<design>.txt.
"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector

FT = 0.3048
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
design = args[0] if args else "modern"
do_render = "--render" in args
data = json.load(open(os.path.join(ROOT, "site", "v2", design, "house.json")))
LEVELS = data["levels"]
R_BODY = 0.24 / FT                       # player radius used by the engine (0.22 m) + a little slack
NOCOLLIDE = ("curtain", "leaves", "lampshade", "led", "downlight", "water", "label")


def bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs, ys, zs = [p.x / FT for p in pts], [p.y / FT for p in pts], [p.z / FT for p in pts]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def mats(o):
    return " ".join(m.name.lower() for m in o.data.materials if m) if o.type == 'MESH' else ""


def coll_of(o):
    return [c.name for c in o.users_collection]


PARTS = {"base", "leg", "seat", "backc", "back", "armL", "armR", "pillow", "frame", "mattress", "headboard", "duvet",
         "throw", "top", "stem", "foot", "body", "seam", "handle", "shade", "pot", "leaf", "cabinet", "basin", "mirror",
         "tray", "head", "screen", "bowl", "pedestal", "cistern", "rod", "motor", "rotor", "cord", "bulb", "ring",
         "candle", "chain", "shelf", "book", "side", "plinth", "worktop", "upper", "panel", "art", "water", "lever",
         "plate", "glass", "strap", "carving", "rosette", "crown", "trunk", "spout", "flue", "board"}


def item_key(name):
    """'Lounge sofa armL.003' -> 'Lounge sofa' (strip Blender's .NNN and trailing part words)."""
    import re
    toks = name.split(".")[0].split(" ")
    while len(toks) > 1 and re.sub(r"\d+$", "", toks[-1]) in PARTS:
        toks.pop()
    return " ".join(toks)


def is_door_part(o):
    p = o
    while p is not None:
        if "door_closed" in p.keys():
            return True
        p = p.parent
    return False


report = []
objs = [o for o in bpy.data.objects if o.type == 'MESH']
for lv, info in sorted(LEVELS.items(), key=lambda kv: kv[1]["z"]):
    fz = info["z"]
    furn, walls, block = [], [], []
    for o in objs:
        cs = coll_of(o)
        if not any(c.startswith(lv + " ") or c in ("Site", "Facade") for c in cs):
            continue
        b = bbox(o)
        if b[5] < fz + 0.35 or b[4] > fz + 5.6:          # not at body height on this floor
            continue
        m = mats(o) + " " + o.name.lower()
        if any(k in m for k in NOCOLLIDE):
            continue
        if any(c == f"{lv} Furniture" for c in cs):
            if b[5] - b[4] < 0.15:                          # rugs
                continue
            if "fan" in o.name.lower() and b[4] > fz + 6:
                continue
            furn.append((o, b))
            block.append(b)
        elif any(c in (f"{lv} Walls", f"{lv} Stairs", f"{lv} Openings", "Site", "Facade") for c in cs):
            if is_door_part(o):
                continue
            if any(c == f"{lv} Walls" for c in cs):
                walls.append((o, b))
            block.append(b)

    # 1. into walls
    for o, b in furn:
        for w, c in walls:
            dx = min(b[1], c[1]) - max(b[0], c[0]); dy = min(b[3], c[3]) - max(b[2], c[2]); dz = min(b[5], c[5]) - max(b[4], c[4])
            if dx > 0.15 and dy > 0.15 and dz > 0.3 and (c[1] - c[0] > 0.12 and c[3] - c[2] > 0.12):
                if min(dx, dy) > 0.15:
                    report.append(f"[{lv}] WALL   '{o.name}' goes {min(dx, dy):.2f} ft into '{w.name}'")
                    break

    # 2. furniture vs furniture (different items)
    for i in range(len(furn)):
        oi, bi = furn[i]
        ki = item_key(oi.name)
        for j in range(i + 1, len(furn)):
            oj, bj = furn[j]
            kj = item_key(oj.name)
            if ki == kj:
                continue
            dx = min(bi[1], bj[1]) - max(bi[0], bj[0]); dy = min(bi[3], bj[3]) - max(bi[2], bj[2]); dz = min(bi[5], bj[5]) - max(bi[4], bj[4])
            if dx > 0.08 and dy > 0.08 and dz > 0.08:
                report.append(f"[{lv}] CLASH  '{oi.name}' overlaps '{oj.name}' ({dx:.2f} x {dy:.2f} x {dz:.2f} ft)")

    # 3. door swings
    for o in objs:
        if "door_closed" not in o.keys() or not any(c.startswith(lv + " ") for c in coll_of(o)):
            continue
        hx, hy = o.matrix_world.translation.x / FT, o.matrix_world.translation.y / FT
        if abs(o.matrix_world.translation.z / FT - fz) > 1:
            continue
        w = max(v.co.x for v in o.data.vertices) / FT
        a0, a1 = o["door_closed"], o["door_open"]
        hits = set()
        for k in range(1, 9):
            a = a0 + (a1 - a0) * k / 8
            for rr in np.arange(0.4, w + 0.01, 0.3):
                px, py = hx + rr * math.cos(a), hy + rr * math.sin(a)
                for f, b in furn:
                    if b[0] - 0.05 <= px <= b[1] + 0.05 and b[2] - 0.05 <= py <= b[3] + 0.05 and b[4] < fz + 6.5:
                        hits.add(item_key(f.name))
        for h in sorted(hits):
            report.append(f"[{lv}] DOOR   '{o.name}' swings into '{h}'")

    # 4. circulation flood fill
    x0, x1, y0, y1, step = -4.0, 34.0, -7.0, 42.0, 0.25
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    free = np.zeros((ny, nx), bool)
    for r in data["rooms"]:
        if r["level"] != lv:
            continue
        for (a, b, c, d) in r["rects"]:          # grown by 0.8 ft so doorways (inside the wall thickness) count as floor
            a, b, c, d = a - 0.8, b + 0.8, c - 0.8, d + 0.8
            free[int((c - y0) / step):int((d - y0) / step), int((a - x0) / step):int((b - x0) / step)] = True
    blocked = np.zeros_like(free)
    for (a, b, c, d, _, _) in block:
        i0, i1 = int((c - R_BODY - y0) / step), int(math.ceil((d + R_BODY - y0) / step))
        j0, j1 = int((a - R_BODY - x0) / step), int(math.ceil((b + R_BODY - x0) / step))
        blocked[max(0, i0):max(0, i1), max(0, j0):max(0, j1)] = True
    walk = free & ~blocked
    seeds = {"GF": (13.4, 7.6), "SF": (4.2, 9.2), "AT": None}
    seed = seeds.get(lv)
    if lv not in seeds or seed is None:
        sp = [s for s in data["spawns"] if abs(s["z"] - fz) < 1.5]
        seed = (sp[0]["x"], sp[0]["y"]) if sp else None
    reach = np.zeros_like(walk)
    if seed:
        si, sj = int((seed[1] - y0) / step), int((seed[0] - x0) / step)
        if not walk[si, sj]:
            # nearest walkable cell to the seed
            ii, jj = np.nonzero(walk)
            k = np.argmin((ii - si) ** 2 + (jj - sj) ** 2)
            si, sj = ii[k], jj[k]
        stack = [(si, sj)]
        reach[si, sj] = True
        while stack:
            i, j = stack.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < ny and 0 <= b < nx and walk[a, b] and not reach[a, b]:
                    reach[a, b] = True
                    stack.append((a, b))
    for r in data["rooms"]:
        if r["level"] != lv:
            continue
        tot = rch = 0
        for (a, b, c, d) in r["rects"]:
            sl = (slice(int((c - y0) / step), int((d - y0) / step)), slice(int((a - x0) / step), int((b - x0) / step)))
            tot += int(walk[sl].sum()); rch += int(reach[sl].sum())
        if tot == 0:
            report.append(f"[{lv}] ROOM   '{r['name']}' has no free floor at all (furniture fills it)")
        elif rch == 0:
            report.append(f"[{lv}] ROOM   '{r['name']}' cannot be reached from the entrance")
        elif rch / tot < 0.5:
            report.append(f"[{lv}] ROOM   '{r['name']}' only {100 * rch / tot:.0f}% of its free floor is reachable")
    np.save(os.path.join(ROOT, "renders", "audit", f"_{design}_{lv}_reach.npy"), reach) if os.path.isdir(os.path.join(ROOT, "renders", "audit")) else None

os.makedirs(os.path.join(ROOT, "renders", "audit"), exist_ok=True)
txt = "\n".join(report) or "no problems found"
open(os.path.join(ROOT, "renders", "audit", f"{design}.txt"), "w").write(txt + "\n")
print("AUDIT", design, len(report), "issues")
print(txt)

if do_render:
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    cd = bpy.data.cameras.new("Audit cam")
    cd.type = 'ORTHO'
    cd.ortho_scale = 48 * FT
    cam = bpy.data.objects.new("Audit cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 1300, 1600
    for lv, info in LEVELS.items():
        cam.location = (15.5 * FT, 17.5 * FT, (info["z"] + info["h"] - 0.5) * FT)
        cam.rotation_euler = (0, 0, 0)
        cd.clip_start = 0.05
        cd.clip_end = (info["h"] + 2) * FT
        for c in bpy.data.collections:
            hide = c.name in ("Roof",) or c.name.endswith("Ceilings") or (c.name.endswith("Labels") and not c.name.startswith(lv))
            c.hide_render = hide
        sc.render.filepath = os.path.join(ROOT, "renders", "audit", f"{design}_{lv}.png")
        bpy.ops.render.render(write_still=True)
