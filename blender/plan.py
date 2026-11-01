"""The house layout shared by all v2 designs.

Ground floor = the reference drawing (plan.jpg, 31' x 38'-3"). Second floor = same structural walls; the old
terrace over the porch is enclosed, so the family lounge runs to the front and the master bedroom gets its own
bath + dressing room. Designs pass a `cfg` dict to choose finishes; geometry stays the same in every design.
"""
from kit import *   # noqa: F401,F403  (kit helpers, STYLE, LEVELS ...)
import kit

GROUND = -1.5
H = 10.0                 # ground floor ceiling (underside of the first slab)
SLAB = 0.6
F2 = H + SLAB            # second floor level
H2 = 9.4                 # second floor ceiling height
TOP = F2 + H2            # underside of the roof / attic slab
R = F2 / 16.0            # stair riser

FOOT_GF = [(0, 38.25), (31, 38.25), (31, 20.9), (28.5, 20.9), (28.5, 15.5), (31, 15.5),
           (31, 0), (17.5, 0), (17.5, 6.1), (1.7, 6.1), (1.7, 20.9), (0, 20.9)]
FOOT_SF = [(0, 38.25), (31, 38.25), (31, 20.9), (28.5, 20.9), (28.5, 15.5), (31, 15.5),
           (31, 0), (17.5, 0), (17.5, -3.5), (1.7, -3.5), (1.7, 20.9), (0, 20.9)]

# rooms: name -> rect (ft). Floor finishes are chosen per design.
GF_ROOMS = {
    "Store / Laundry": (0.75, 7.8, 32.6, 37.5),
    "Kitchen": (0.75, 8.6, 21.6, 32.2),
    "Hamam": (8.5, 17.5, 27.4, 37.5),
    "Bed Room": (18.2, 30.25, 27.4, 37.5),
    "Attach Washroom": (23.2, 30.25, 21.7, 26.7),
    "Common Washroom": (18.2, 27.9, 15.5, 20.9),
    "Drawing Room": (18.2, 30.25, 0.77, 14.7),
    "Lounge": (2.5, 17.5, 6.8, 20.9),
    "Corridor": (9.4, 22.5, 20.9, 26.7),
}
SF_ROOMS = {
    "Bath 3": (0.75, 7.8, 32.6, 37.5),
    "Study": (0.75, 8.6, 21.6, 32.2),
    "Bedroom 3": (8.5, 17.5, 27.4, 37.5),
    "Bedroom 2": (18.2, 30.25, 27.4, 37.5),
    "Bath 2": (23.2, 30.25, 21.7, 26.7),
    "Common Bath": (18.2, 27.9, 15.5, 20.9),
    "Master Bedroom": (18.2, 30.25, 0.77, 14.7),
    "Master Bath": (12.0, 17.5, -2.75, 2.0),
    "Dressing": (12.0, 17.5, 2.4, 6.1),
    "Family Lounge": (2.5, 11.6, -2.75, 10.7),
    "Dining & Library": (8.0, 17.5, 10.7, 20.9),
    "Upper Corridor": (9.4, 22.5, 20.9, 26.7),
}
WET = {"Hamam", "Attach Washroom", "Common Washroom", "Bath 3", "Bath 2", "Common Bath", "Master Bath", "Store / Laundry"}


def gf_walls(cfg):
    arch = cfg.get("arches", False)                 # Spanish: arched openings and windows
    lat = cfg.get("lattice", False)                 # Kashmiri: pinjrakari screens on the street windows
    grille = cfg.get("grille", False)
    win = lambda a, b, sill=3.0, head=DOOR_H, curtains=True: W(a, b, sill, head, arch=arch and head - sill > 3.5, lattice=lat, curtains=curtains, grille=grille)
    return {
        "GF wall back":         ((0.0, 31.0, 37.5, 38.25), [D(4.6, 7.3, 'b', (0, 1)), W(8.8, 11.2, 4.5, curtains=False), W(14.5, 17.0, 4.5, curtains=False), win(21.4, 27.0)], "-y"),
        "GF wall kitchen W":    ((0.0, 0.75, 20.9, 38.25), [W(28.5, 32.3, 3.5, curtains=False)], "+x"),
        "GF wall kitchen S":    ((0.0, 9.4, 20.9, 21.6), [], None),
        "GF wall lounge W":     ((1.7, 2.5, 6.1, 20.9), [win(10.2, 14.2)], "+x"),
        "GF wall lounge front": ((1.7, 17.5, 6.1, 6.8), [win(3.8, 7.7), D2(11.4, 15.4, (0, 1), arch=arch, head=8.0 if arch else DOOR_H)], "+y"),
        "GF wall drawing W":    ((17.5, 18.2, 0.0, 21.7), [D(1.6, 4.8, 'a', (1, 0)), A(8.9, 14.2, 8.0, arch=arch)], None),
        "GF wall drawing front": ((17.5, 31.0, 0.0, 0.77), [win(20.8, 27.4)], "+y"),
        "GF wall drawing E":    ((30.25, 31.0, 0.0, 15.5), [], "-x"),
        "GF wall drawing N":    ((18.2, 31.0, 14.7, 15.5), [], None),
        "GF wall common WR E":  ((27.9, 28.5, 15.5, 20.9), [W(16.4, 19.4, 5.0, curtains=False)], "-x"),
        "GF wall east":         ((30.25, 31.0, 20.9, 37.5), [], "-x"),
        "GF wall washrooms N":  ((18.2, 30.25, 20.9, 21.7), [D(18.2, 20.6, 'a', (0, -1))], None),
        "GF wall attach W":     ((22.5, 23.2, 21.7, 26.7), [], None),
        "GF wall bed-hamam S":  ((7.8, 30.25, 26.7, 27.4), [D(10.2, 13.1, 'a', (0, 1)), D(18.6, 21.4, 'a', (0, 1)), D(23.5, 26.1, 'a', (0, -1))], None),
        "GF wall hamam-bed":    ((17.5, 18.2, 27.4, 37.5), [], None),
        "GF wall kitchen-hamam": ((7.8, 8.5, 27.4, 37.5), [A(27.4, 31.9, arch=arch)], None),
        "GF wall kitchen E":    ((8.6, 9.4, 21.6, 26.7), [D(21.9, 24.7, 'a', (-1, 0))], None),
        "GF wall store-kitchen": ((0.75, 7.8, 32.2, 32.6), [A(5.4, 7.8, arch=False)], None),
    }


def sf_walls(cfg):
    arch = cfg.get("arches", False)
    lat = cfg.get("lattice", False)
    grille = cfg.get("grille", False)
    win = lambda a, b, sill=3.0, head=DOOR_H, curtains=True: W(a, b, sill, head, arch=arch and head - sill > 3.5, lattice=lat, curtains=curtains, grille=grille)
    big_head = 8.0 if not arch else 8.2
    return {
        "SF wall back":         ((0.0, 31.0, 37.5, 38.25), [W(4.6, 6.8, 5.0, curtains=False), win(9.8, 13.8), win(21.4, 27.0)], "-y"),
        "SF wall study W":      ((0.0, 0.75, 20.9, 38.25), [win(25.0, 29.0), W(34.5, 36.5, 5.0, curtains=False)], "+x"),
        "SF wall study S":      ((0.0, 9.4, 20.9, 21.6), [], None),
        "SF wall lounge W":     ((1.7, 2.5, -3.5, 20.9), [win(-0.5, 4.0), win(12.5, 15.5)], "+x"),
        "SF wall front":        ((1.7, 17.5, -3.5, -2.75), [W(3.2, 10.2, 2.0, big_head, arch=False, lattice=lat, grille=grille), W(13.6, 16.0, 5.0, curtains=False, lattice=lat)], "+y"),
        "SF wall master W":     ((17.5, 18.2, -3.5, 21.7), [D(3.0, 5.6, 'a', (-1, 0)), D(7.5, 10.3, 'a', (1, 0))], None),
        "SF wall master front": ((17.5, 31.0, 0.0, 0.77), [win(20.8, 27.4)], "+y"),
        "SF wall master E":     ((30.25, 31.0, 0.0, 15.5), [win(3.0, 7.0)], "-x"),
        "SF wall master N":     ((18.2, 31.0, 14.7, 15.5), [], None),
        "SF wall common bath E": ((27.9, 28.5, 15.5, 20.9), [W(16.4, 19.4, 5.0, curtains=False)], "-x"),
        "SF wall east":         ((30.25, 31.0, 20.9, 37.5), [W(23.5, 25.5, 5.0, curtains=False)], "-x"),
        "SF wall baths N":      ((18.2, 30.25, 20.9, 21.7), [D(18.2, 20.6, 'a', (0, -1))], None),
        "SF wall bath2 W":      ((22.5, 23.2, 21.7, 26.7), [], None),
        "SF wall bedrooms S":   ((7.8, 30.25, 26.7, 27.4), [D(10.2, 13.1, 'a', (0, 1)), D(18.6, 21.4, 'a', (0, 1)), D(23.5, 26.1, 'a', (0, -1))], None),
        "SF wall bed2-bed3":    ((17.5, 18.2, 27.4, 37.5), [], None),
        "SF wall bed3 W":       ((7.8, 8.5, 27.4, 37.5), [D(33.4, 35.6, 'b', (-1, 0))], None),
        "SF wall study E":      ((8.6, 9.4, 21.6, 26.7), [D(21.9, 24.7, 'a', (-1, 0))], None),
        "SF wall study-bath":   ((0.75, 7.8, 32.2, 32.6), [], None),
        "SF wall suite W":      ((11.6, 12.0, -2.75, 6.1), [], None),
        "SF wall suite N":      ((11.6, 17.5, 6.1, 6.8), [], None),
        "SF wall bath-dressing": ((12.0, 17.5, 2.0, 2.4), [D(14.6, 17.1, 'a', (0, -1))], None),
    }


def stairs_gf(rail_kind="glass"):
    """Dog-leg stair from the lounge to the second floor: up west, landing, up south (16 risers)."""
    T1, T2 = 0.95, 0.7
    level("GF")
    m = STYLE["stair"]
    steps1 = [(11.7 - i * T1, 11.7 - (i - 1) * T1, 18.0, 20.9, i * R) for i in range(1, 7)]
    stair_flight("Stair A", steps1, m, R, floor_z=0.0)
    cyl("Stair bullnose", 11.2, 18.0, 0.0, R, 0.9, m, "Stairs", seg=24)
    box("Stair landing", 2.5, 6.0, 17.0, 20.9, 0.0, 7 * R, m, "Stairs")
    steps2 = [(2.5, 6.0, 17.0 - k * T2, 17.0 - (k - 1) * T2, (7 + k) * R) for k in range(1, 10)]
    stair_flight("Stair B", steps2, m, R)
    pts = [(11.25, 18.15), (6.0, 18.15), (5.85, 18.15), (5.85, 11.0)]
    zs = [R, 6 * R, 7 * R, 16 * R - 0.2]
    railing("Stair rail", pts, zs, kind=rail_kind)


WALLDEFS = {}


def room_gaps(lv, rect, below=7.5):
    """Door / arch / low-window openings on each inner face of a room, from the wall definitions."""
    x0, x1, y0, y1 = rect
    out = {"S": [], "N": [], "W": [], "E": []}
    for (wx0, wx1, wy0, wy1), ops, _ in WALLDEFS.get(lv, {}).values():
        along_x = (wx1 - wx0) >= (wy1 - wy0)
        for o in ops:
            if o["sill"] >= below:
                continue
            a, b = o["a"], o["b"]
            if along_x and wx0 <= b and wx1 >= a:
                if abs(wy1 - y0) < 0.05 and a < x1 and b > x0: out["S"].append((a, b))
                if abs(wy0 - y1) < 0.05 and a < x1 and b > x0: out["N"].append((a, b))
            if not along_x and wy0 <= b and wy1 >= a:
                if abs(wx1 - x0) < 0.05 and a < y1 and b > y0: out["W"].append((a, b))
                if abs(wx0 - x1) < 0.05 and a < y1 and b > y0: out["E"].append((a, b))
    return out


def finish_room(name, lv, rect, z0, h, m, faces="SNWE", below=None):
    """Tiles / panelling on a room's inner faces, leaving door and window gaps."""
    wainscot(name, rect, z0, h, m, room_gaps(lv, rect, below if below is not None else h), faces=faces)


def build_structure(cfg):
    """Walls, floors, ceilings, stairs and rooms for both floors (+ the attic slab if cfg['attic'])."""
    fl = cfg["floors"]                               # room -> material (missing rooms use fl['default'])
    # ---------------------------------------------------------------- ground floor
    level("GF", 0.0, H, "Ground floor")
    WALLDEFS["GF"], WALLDEFS["SF"] = gf_walls(cfg), sf_walls(cfg)
    for n, (r, ops, inside) in WALLDEFS["GF"].items():
        wall(n, r, ops, 0.0, H, inside=inside)
    prism("Plinth", FOOT_GF, GROUND, 0.0, STYLE["plinth"], "Floors")
    for n, r in GF_ROOMS.items():
        floor(n, r, 0.0, fl.get(n, fl["default"]), show=n != "Corridor")
    add_room("Porch", [(1.7, 17.5, -4.5, 6.1)])
    stairs_gf(cfg.get("rail", "glass"))
    # ceilings of the ground floor = underside of the first slab, plus finishes
    for n, r in GF_ROOMS.items():
        ceil_finish(cfg, n, r, H)
        cx, cy = (r[0] + r[1]) / 2, (r[2] + r[3]) / 2
        light(cx, cy, H - 0.9, power=1.0 if n not in WET else 0.7)

    # ---------------------------------------------------------------- second floor
    level("SF", F2, H2, "Second floor")
    for i, (a, b, c, d) in enumerate([(0.0, 31.0, 20.9, 38.25), (1.7, 2.5, 10.7, 20.9), (8.0, 28.5, 15.5, 20.9),
                                      (8.0, 17.5, 10.7, 15.5), (1.7, 17.5, -3.5, 10.7), (17.5, 31.0, 0.0, 15.5)]):
        box(f"SF slab {i}", a, b, c, d, H, F2, STYLE["slab"], "Floors")
    for n, (r, ops, inside) in WALLDEFS["SF"].items():
        wall(n, r, ops, F2, H2, inside=inside)
    for n, r in SF_ROOMS.items():
        floor(n, r, F2, fl.get(n, fl["default"]), show=n not in ("Upper Corridor",))
    floor("Family Lounge", (11.6, 17.5, 6.8, 10.7), F2, fl.get("Family Lounge", fl["default"]))
    if not cfg.get("attic"):
        railing("Void rail E", [(8.0, 10.7), (8.0, 20.85)], [F2, F2], kind=cfg.get("rail", "glass"))
    railing("Void rail S", [(6.0, 10.7), (8.0, 10.7)], [F2, F2], kind=cfg.get("rail", "glass"))
    for n, r in SF_ROOMS.items():
        ceil_finish(cfg, n, r, TOP)
        cx, cy = (r[0] + r[1]) / 2, (r[2] + r[3]) / 2
        light(cx, cy, TOP - 0.9, power=1.0 if n not in WET else 0.7)

    # ---------------------------------------------------------------- porch, steps, columns
    level("GF")
    box("Porch slab", 1.7, 17.5, -3.5, 6.1, GROUND, -0.5, STYLE["porch"], "Site")
    box("Porch step", 1.7, 17.5, -4.5, -3.5, GROUND, -1.0, STYLE["porch"], "Site")
    box("Porch threshold", 11.4, 15.4, 5.6, 6.1, -0.5, 0.0, STYLE["stair"], "Site")
    box("Back landing", 4.2, 8.4, 38.25, 40.9, GROUND, 0.0, STYLE["porch"], "Site")
    box("Back step 1", 2.65, 4.2, 38.25, 40.9, GROUND, -0.5, STYLE["porch"], "Site")
    box("Back step 2", 1.1, 2.65, 38.25, 40.9, GROUND, -1.0, STYLE["porch"], "Site")
    for i, cx in enumerate((6.05, 17.06)):
        cfg["column"](f"Porch column {i + 1}", cx, -2.5, -0.5, H)
    SPAWNS[:] = [
        {"name": "Outside", "x": 11.5, "y": -24.0, "z": GROUND, "yaw": 0.0},
        {"name": "Ground floor", "x": 13.5, "y": 13.0, "z": 0.05, "yaw": 0.0},
        {"name": "Second floor", "x": 7.0, "y": 4.0, "z": F2 + 0.05, "yaw": -1.2},
    ]


def ceil_finish(cfg, n, r, ceil):
    kind = cfg.get("ceilings", {}).get(n, cfg.get("ceilings", {}).get("default", "cornice"))
    x0, x1, y0, y1 = r
    if kind == "false" and (x1 - x0) > 6.5 and (y1 - y0) > 6.5:
        false_ceiling(f"{STATE['level']} {n} ceiling", r, ceil, center=cfg.get("ceiling_centre", {}).get(n))
    elif kind == "khatam":
        false_ceiling(f"{STATE['level']} {n} ceiling", r, ceil, drop=0.6, border=1.2, center=STYLE["khatam"], downlights=True)
    elif kind == "beams":
        bm = STYLE["beam"]
        along_x = (x1 - x0) < (y1 - y0)
        k = int(((y1 - y0) if along_x else (x1 - x0)) / 2.0)
        for i in range(1, k + 1):
            if along_x:
                y = y0 + (y1 - y0) * i / (k + 1)
                box(f"{STATE['level']} {n} beam{i}", x0, x1, y - 0.25, y + 0.25, ceil - 0.6, ceil, bm, "Ceilings")
            else:
                x = x0 + (x1 - x0) * i / (k + 1)
                box(f"{STATE['level']} {n} beam{i}", x - 0.25, x + 0.25, y0, y1, ceil - 0.6, ceil, bm, "Ceilings")
    elif kind == "cornice":
        cornice(f"{STATE['level']} {n}", r, ceil)


def gf_floors_ceiling_paint(m):
    """Paint the underside of the first slab (seen as the ground floor ceiling) over the whole footprint."""
    level("GF")
    prism("GF ceiling paint", FOOT_GF, H - 0.04, H, m, "Ceilings")
