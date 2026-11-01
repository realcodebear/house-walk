"""v2 design 1: Modern Cozy — stone + teak facade, black frames, flat roof; warm marble, oak and walnut inside.

    /Applications/Blender.app/Contents/MacOS/Blender -b -y -P blender/design_modern.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
from kit import *          # noqa: F401,F403
import plan
from plan import GROUND, H, F2, TOP, SLAB, FOOT_SF, build_structure
import furnish

reset_scene()
S = STYLE
S.update({
    "wall": mat("Warm white paint", (0.93, 0.9, 0.85), 0.9, tex="plaster", nrm="plaster_n", tile=2.0),
    "slab": mat("Ceiling white", (0.95, 0.94, 0.92), 0.95),
    "ceiling": mat("Gypsum", (0.97, 0.96, 0.94), 0.95),
    "plinth": mat("Plinth stone", (0.62, 0.6, 0.57), 0.9, tex="stone", nrm="stone_n", tile=1.6),
    "frame": mat("Black aluminium", (0.05, 0.05, 0.055), 0.35, 0.6),
    "glass": mat("Glass", (0.62, 0.74, 0.8), 0.05, alpha=0.22),
    "sill": mat("White marble sill", (1, 1, 1), 0.25, tex="marble_white", tile=1.2),
    "curtain": mat("Linen curtain", (0.86, 0.8, 0.7), 0.95, tex="fabric", tile=0.5, double=True),
    "metal": mat("Brushed steel", (0.72, 0.72, 0.73), 0.3, 1.0),
    "door": mat("Walnut door", (1, 1, 1), 0.45, tex="walnut", tile=1.2),
    "door_panel": mat("Walnut panel", (0.9, 0.86, 0.82), 0.4, tex="walnut", tile=1.2),
    "door_frame": mat("Walnut frame", (0.75, 0.7, 0.66), 0.45, tex="walnut", tile=1.2),
    "door_style": "english",
    "handle": mat("Brass", (0.86, 0.66, 0.36), 0.3, 1.0),
    "led": mat("LED cove", (1, 0.86, 0.62), 0.5, emit=(1, 0.8, 0.55), emit_strength=3.5),
    "downlight": mat("Downlight", (1, 1, 1), 0.3, emit=(1, 0.9, 0.75), emit_strength=4),
    "mdf": mat("MDF walnut panel", (1, 1, 1), 0.5, tex="mdf_walnut", nrm="mdf_walnut_n", tile=1.2),
    "trim": mat("White trim", (0.95, 0.94, 0.92), 0.6),
    "stair": mat("Italian marble", (1, 1, 1), 0.18, tex="marble_white", nrm="marble_white_n", tile=1.2),
    "rail_post": mat("Brushed steel", (0.72, 0.72, 0.73), 0.3, 1.0),
    "rail_top": mat("Walnut handrail", (1, 1, 1), 0.4, tex="walnut", tile=1.0),
    "porch": mat("Paving", (1, 1, 1), 0.85, tex="paving", nrm="paving_n", tile=1.2),
    "linen": mat("Bed linen", (0.93, 0.92, 0.89), 0.95, tex="fabric", tile=0.4),
    "pillow": mat("Pillow", (0.82, 0.77, 0.68), 0.95, tex="fabric", tile=0.4),
    "throw": mat("Rust throw", (0.6, 0.33, 0.2), 0.95, tex="fabric", tile=0.4),
    "wood_dark": mat("Walnut", (1, 1, 1), 0.45, tex="walnut", tile=1.0),
    "wood": mat("Oak", (1, 1, 1), 0.5, tex="teak", tile=1.0),
    "cushion": mat("Mustard cushion", (0.78, 0.56, 0.22), 0.95, tex="fabric", tile=0.4),
    "lampshade": mat("Lamp shade", (1, 0.95, 0.85), 0.8, emit=(1, 0.84, 0.6), emit_strength=1.2),
    "pendant": mat("Black pendant", (0.06, 0.06, 0.06), 0.4, 0.5),
    "pot": mat("Grey pot", (0.42, 0.42, 0.4), 0.8),
    "leaf": mat("Leaves", (0.13, 0.32, 0.13), 0.8),
    "bark": mat("Bark", (0.3, 0.22, 0.15), 0.95),
    "ceramic": mat("Ceramic", (0.96, 0.96, 0.95), 0.12),
    "counter": mat("Black granite", (1, 1, 1), 0.2, tex="marble_black", tile=1.2),
    "cabinet": mat("Oak cabinet", (1, 1, 1), 0.5, tex="mdf_oak", tile=1.2),
    "mirror": mat("Mirror", (0.92, 0.94, 0.96), 0.02, 1.0),
    "fridge": mat("Fridge steel", (0.78, 0.78, 0.8), 0.25, 0.9),
    "black": mat("Black", (0.03, 0.03, 0.035), 0.35),
    "backsplash": mat("Subway tile", (1, 1, 1), 0.2, tex="subway", nrm="subway_n", tile=0.6),
    "seat": mat("Seat fabric", (0.55, 0.5, 0.44), 0.95, tex="fabric", tile=0.4),
    "bath_wall": mat("Porcelain wall", (1, 1, 1), 0.25, tex="porcelain", nrm="porcelain_n", tile=1.2),
    "water": mat("Water", (0.55, 0.7, 0.78), 0.02, alpha=0.5),
    "wardrobe": mat("Wardrobe oak", (1, 1, 1), 0.5, tex="mdf_oak", tile=1.2),
    "rug_a": mat("Beige rug", (1, 1, 1), 0.95, tex="carpet_beige", uv="fit"),
    "rug_b": mat("Stripe rug", (1, 1, 1), 0.95, tex="carpet_stripe", uv="fit"),
    "chair_fabric": mat("Camel fabric", (0.66, 0.48, 0.3), 0.95, tex="fabric", tile=0.4),
    "sofa": mat("Sofa fabric", (0.36, 0.4, 0.44), 0.95, tex="fabric", tile=0.4),
    "table_top": mat("Table walnut", (1, 1, 1), 0.35, tex="walnut", tile=1.0),
    "art": mat("Art papier", (1, 1, 1), 0.7, tex="papier", uv="fit"),
    "art2": mat("Art crewel", (1, 1, 1), 0.7, tex="crewel", uv="fit"),
    "books": [mat("Book red", (0.5, 0.12, 0.1), 0.7), mat("Book navy", (0.1, 0.14, 0.3), 0.7),
              mat("Book cream", (0.85, 0.8, 0.68), 0.7), mat("Book green", (0.15, 0.32, 0.22), 0.7)],
    "fan_body": mat("Fan body", (0.85, 0.83, 0.8), 0.4, 0.3),
    "fan_blade": mat("Fan blade", (1, 1, 1), 0.5, tex="walnut", tile=1.0),
})
stone = mat("Stone cladding", (1, 1, 1), 0.85, tex="stone", nrm="stone_n", tile=1.6)
teak = mat("Teak cladding", (1, 1, 1), 0.6, tex="mdf_oak", nrm="mdf_oak_n", tile=1.0)
marble = mat("Italian white marble", (1, 1, 1), 0.15, tex="marble_white", nrm="marble_white_n", tile=1.2)
diana = mat("Turkish Diana marble", (1, 1, 1), 0.18, tex="marble_diana", nrm="marble_diana_n", tile=1.2)
oak = mat("Oak floor", (1, 1, 1), 0.45, tex="oak_planks", nrm="oak_planks_n", tile=1.6)
walnut_floor = mat("Walnut floor", (1, 1, 1), 0.45, tex="walnut_planks", nrm="walnut_planks_n", tile=1.6)
porcelain = mat("Porcelain floor", (0.82, 0.82, 0.8), 0.3, tex="porcelain", nrm="porcelain_n", tile=1.2)
grass = mat("Lawn", (1, 1, 1), 0.95, tex="grass", tile=2.0)
dark_grey = mat("Charcoal", (0.16, 0.16, 0.17), 0.6)


def column(name, cx, cy, z0, z1):
    box(name, cx - 0.65, cx + 0.65, cy - 0.65, cy + 0.65, z0, z1, stone, "Site")


cfg = {
    "floors": {
        "default": marble,
        "Drawing Room": diana, "Bed Room": oak, "Kitchen": porcelain, "Store / Laundry": porcelain,
        "Hamam": porcelain, "Attach Washroom": porcelain, "Common Washroom": porcelain,
        "Bedroom 2": oak, "Bedroom 3": oak, "Master Bedroom": oak, "Dressing": oak, "Study": walnut_floor,
        "Family Lounge": oak, "Dining & Library": diana, "Bath 2": porcelain, "Bath 3": porcelain,
        "Common Bath": porcelain, "Master Bath": porcelain,
    },
    "ceilings": {"default": "cornice", "Lounge": None, "Family Lounge": None, "Drawing Room": "false",
                 "Bed Room": "false", "Master Bedroom": "false", "Bedroom 2": "false", "Bedroom 3": "false",
                 "Dining & Library": "false"},
    "rail": "glass",
    "column": column,
}
build_structure(cfg)
furnish.all_common()
furnish.lounge_gf()
furnish.drawing_room()
furnish.family_lounge()

# ---------------------------------------------------------------- facade
level("GF")
wall("Clad drawing front", (17.5, 31.0, -0.1, 0.0), [W(20.8, 27.4)], 0.0, H + SLAB, stone, frames=False, cname="Facade")
wall("Clad porch wall", (1.7, 17.5, 6.0, 6.1), [W(3.8, 7.7), D2(11.4, 15.4)], 0.0, H, stone, frames=False, cname="Facade")
level("SF")
wall("Clad SF front", (1.7, 17.5, -3.6, -3.5), [W(3.2, 10.2, 2.0, 8.0), W(13.6, 16.0, 5.0)], F2, TOP - F2 + SLAB, teak, frames=False, cname="Facade")
# deep charcoal frame around the master bedroom window
for nm, r in (("L", (19.8, 20.3, -1.4, 0.0, F2 + 1.6, F2 + 8.4)), ("R", (27.9, 28.4, -1.4, 0.0, F2 + 1.6, F2 + 8.4)),
              ("T", (19.8, 28.4, -1.4, 0.0, F2 + 7.9, F2 + 8.4)), ("B", (19.8, 28.4, -1.4, 0.0, F2 + 1.6, F2 + 2.1))):
    box(f"Window box {nm}", *r, dark_grey, "Facade")
# band between floors
box("Floor band front", 1.6, 31.1, -3.7, 0.0, H - 0.1, F2, dark_grey, "Facade")
for (a, b, c, d) in ((-0.1, 0.0, 20.9, 38.25), (31.0, 31.1, 0.0, 38.25), (0.0, 31.0, 38.25, 38.35), (1.6, 1.7, -3.5, 20.9)):
    box("Floor band", a, b, c, d, H - 0.1, F2, dark_grey, "Facade")

# ---------------------------------------------------------------- roof
roof_m = mat("Roof screed", (0.6, 0.58, 0.55), 0.9)
prism("Roof slab", FOOT_SF, TOP, TOP + SLAB, roof_m, "Roof")
for i in range(len(FOOT_SF)):
    (ax, ay), (bx, by) = FOOT_SF[i], FOOT_SF[(i + 1) % len(FOOT_SF)]
    L = math.hypot(bx - ax, by - ay)
    nx, ny = (by - ay) / L, -(bx - ax) / L
    t = 0.5
    xs = [ax, bx, ax + nx * t, bx + nx * t]
    ys = [ay, by, ay + ny * t, by + ny * t]
    box(f"Parapet {i}", min(xs), max(xs), min(ys), max(ys), TOP + SLAB, TOP + SLAB + 3.0, S["wall"], "Roof")
    box(f"Coping {i}", min(xs) - 0.08, max(xs) + 0.08, min(ys) - 0.08, max(ys) + 0.08, TOP + SLAB + 3.0, TOP + SLAB + 3.2, dark_grey, "Roof")
cyl("Water tank", 6.0, 32.0, TOP + SLAB + 1.0, TOP + SLAB + 6.0, 2.2, mat("Tank white", (0.9, 0.9, 0.88), 0.6), "Roof", seg=24)
box("Tank stand", 4.0, 8.0, 30.0, 34.0, TOP + SLAB, TOP + SLAB + 1.0, dark_grey, "Roof")
solar = mat("Solar panel", (0.05, 0.08, 0.16), 0.15, 0.6)
for i in range(3):
    slab3d(f"Solar {i}", [(14 + i * 4.5, 26.0, TOP + SLAB + 1.2), (17.8 + i * 4.5, 26.0, TOP + SLAB + 1.2),
                          (17.8 + i * 4.5, 32.0, TOP + SLAB + 3.6), (14 + i * 4.5, 32.0, TOP + SLAB + 3.6)], 0.15, solar, "Roof")

# ---------------------------------------------------------------- site
level("GF")
box("Lawn", -200, 200, -200, 200, GROUND - 0.5, GROUND, grass, "Site")
box("Street", -200, 200, -48, -26, GROUND, GROUND + 0.02, mat("Asphalt", (0.2, 0.2, 0.21), 0.9), "Site")
box("Driveway", 1.7, 17.5, -20.0, -4.5, GROUND, GROUND + 0.03, S["porch"], "Site")
box("Front path", 9.5, 14.0, -26.0, -20.0, GROUND, GROUND + 0.03, S["porch"], "Site")
bw = mat("Boundary wall", (0.9, 0.88, 0.84), 0.9, tex="plaster", tile=2.0)
for nm, r in (("front L", (-6, 8.0, -20.6, -20.0)), ("front R", (15.5, 37, -20.6, -20.0)),
              ("side L", (-6, -5.4, -20.6, 44)), ("side R", (36.4, 37, -20.6, 44)), ("back", (-6, 37, 43.4, 44))):
    box(f"Boundary {nm}", *r, GROUND, GROUND + 5.0, bw, "Site")
    box(f"Boundary cap {nm}", r[0] - 0.1, r[1] + 0.1, r[2] - 0.1, r[3] + 0.1, GROUND + 5.0, GROUND + 5.25, dark_grey, "Site")
for x in (7.2, 15.5):
    box(f"Gate pillar {x}", x - 0.8 if x < 10 else x, x + 0.8 if x < 10 else x + 1.6, -21.0, -19.6, GROUND, GROUND + 6.0, stone, "Site")
gate = mat("Gate metal", (0.08, 0.08, 0.09), 0.4, 0.7)
for k in range(13):
    x = 8.2 + k * 0.56
    box(f"Gate bar {k}", x, x + 0.08, -20.35, -20.25, GROUND + 0.3, GROUND + 5.2, gate, "Site")
box("Gate rail low", 8.0, 15.5, -20.4, -20.2, GROUND + 0.5, GROUND + 0.7, gate, "Site")
box("Gate rail high", 8.0, 15.5, -20.4, -20.2, GROUND + 4.8, GROUND + 5.0, gate, "Site")
tree("Tree front", 27.0, -12.0, GROUND, 16, r=4.5)
tree("Tree back", 33.0, 41.0, GROUND, 14, r=3.8)
tree("Tree side", -3.0, 10.0, GROUND, 15, r=3.6)
hedge("Hedge front", 18.5, 35.8, -19.4, -18.2, GROUND, 2.4)
hedge("Hedge side", 34.8, 36.0, -18.0, 12.0, GROUND, 2.4)
for i, x in enumerate((19.5, 24.0, 28.5, 33.0)):
    cyl(f"Garden light {i}", x, -17.2, GROUND, GROUND + 2.6, 0.12, dark_grey, "Site", seg=8)
    cyl(f"Garden light head {i}", x, -17.2, GROUND + 2.6, GROUND + 3.0, 0.3, S["lampshade"], "Site", seg=12)

# ---------------------------------------------------------------- labels (Blender only)
for lv, rooms, z in (("GF", plan.GF_ROOMS, 0.1), ("SF", plan.SF_ROOMS, F2 + 0.1)):
    level(lv)
    for n, (x0, x1, y0, y1) in rooms.items():
        if "Corridor" in n:
            continue
        label(n.upper(), (x0 + x1) / 2, (y0 + y1) / 2, z, 0.6)

# ---------------------------------------------------------------- cameras + export
sun_and_sky()
cam_front = camera("Cam front", (52, -58, 30), (15.0, 10.0, 9.0), lens=30)
cam_back = camera("Cam back", (-32, 74, 34), (15.0, 22.0, 9.0), lens=30)
cam_cut_gf = camera("Cam cutaway ground", (-10, -22, 52), (15.5, 18.0, 0.0), lens=32)
cam_cut_sf = camera("Cam cutaway second", (-10, -24, 62), (15.5, 17.0, F2), lens=32)
cam_lounge = camera("Cam lounge", (3.6, 7.6, F2 + 5.0), (11.0, -0.5, F2 + 3.2), lens=20)
look = {"sky": [0.62, 0.76, 0.95], "fog": [70, 260], "hemi": [[0.86, 0.91, 1.0], [0.45, 0.4, 0.33], 1.05],
        "sun": {"color": [1.0, 0.95, 0.86], "intensity": 2.7, "offset": [14, 24, 12]}, "exposure": 1.0,
        "interior": {"color": [1.0, 0.83, 0.62], "intensity": 3.2}, "env": 0.28}
kit.finish("modern", {"title": "Modern Cozy", "look": look, "footprint": FOOT_SF}, renders=[
    (cam_front, "1_front", (), (1600, 1000)),
    (cam_back, "2_back", (), (1600, 1000)),
    (cam_cut_gf, "3_cutaway_ground", ("Second Floor", "Roof", "Attic"), (1600, 1000)),
    (cam_cut_sf, "4_cutaway_second", ("Roof", "Attic"), (1600, 1000)),
    (cam_lounge, "5_family_lounge", (), (1600, 1000)),
])
