"""Room-by-room furniture shared by the v2 designs. Everything takes its materials from kit.STYLE, so one layout
serves every design; designs override the rooms where their style differs (lounges, drawing room, decor)."""
from kit import *   # noqa: F401,F403
from plan import F2, H, TOP, H2, finish_room, GF_ROOMS, SF_ROOMS

S = STYLE


def _fan(name, x, y, ceil):
    fan(name, x, y, ceil, S["fan_body"], S["fan_blade"])


# ================================================================ ground floor
def kitchen():
    level("GF")
    z = 0.0
    box("Fridge", 0.8, 3.0, 21.65, 24.15, z, z + 6.2, S["fridge"])
    box("Fridge handle", 3.0, 3.08, 23.6, 23.7, z + 2.6, z + 5.4, S["handle"])
    kitchen_run("Kitchen W", 0.75, 2.85, 24.2, 32.2, front="+x", upper=False)
    kitchen_run("Kitchen N", 2.85, 5.4, 30.1, 32.2, front="-y", upper=True)
    box("Kitchen upper W", 0.75, 1.85, 24.2, 25.3, z + 5.0, z + 7.4, S["cabinet"])
    box("Hob", 1.0, 2.6, 25.6, 27.6, z + 3.0, z + 3.04, S["black"])
    for j, (bx, by) in enumerate(((1.45, 26.1), (2.15, 26.1), (1.45, 27.1), (2.15, 27.1))):
        cyl(f"Burner {j}", bx, by, z + 3.04, z + 3.08, 0.2, S["metal"], seg=12)
    box("Hood", 0.75, 2.2, 25.4, 27.8, z + 5.6, z + 6.4, S["metal"])
    box("Hood flue", 0.75, 1.4, 26.2, 27.0, z + 6.4, z + 9.9, S["metal"])
    box("Sink", 3.4, 5.0, 30.6, 31.8, z + 2.9, z + 3.01, S["metal"])
    rod("Tap", (4.2, 31.9, 3.0), (4.2, 31.9, 3.9), 0.05, S["metal"])
    rod("Tap spout", (4.2, 31.9, 3.9), (4.2, 31.3, 3.9), 0.04, S["metal"])
    panel_wall("Backsplash W", (0.75, 0.8, 24.2, 32.2), z + 3.0, z + 5.0, S["backsplash"])
    panel_wall("Backsplash N", (2.85, 5.4, 32.15, 32.2), z + 3.0, z + 5.0, S["backsplash"])
    light(4.8, 26.9, H - 0.9, power=0.8)


def store():
    level("GF")
    box("Washer", 0.9, 2.6, 35.95, 37.45, 0, 2.9, S["ceramic"])
    box("Dryer", 2.7, 4.4, 35.95, 37.45, 0, 2.9, S["ceramic"])
    cyl("Washer door", 1.75, 35.94, 1.2, 1.3, 0.5, S["glass"], seg=16)
    box("Laundry shelf", 0.75, 1.9, 32.7, 35.6, 0, 6.5, S["wood"])
    for k in range(4):
        box(f"Laundry shelf board {k}", 0.75, 1.95, 32.7, 35.6, 0.6 + k * 1.5, 0.68 + k * 1.5, S["wood_dark"])


def hamam():
    level("GF")
    r = GF_ROOMS["Hamam"]
    finish_room("Hamam tiles", "GF", r, 0.0, 4.4, S["bath_wall"])
    box("Bathtub", 13.0, 17.45, 34.9, 37.45, 0, 1.9, S["ceramic"])
    box("Bathtub water", 13.4, 17.05, 35.3, 37.05, 1.6, 1.65, S["water"])
    wc("Hamam WC", 16.42, 30.6, "+x")
    vanity("Hamam vanity", 8.5, 10.0, 32.0, 34.6, mirror_side="-x")
    shower("Hamam shower", 8.55, 11.6, 35.2, 37.45, glass_side="x1")
    box("Towel rail", 17.38, 17.45, 32.0, 33.6, 4.0, 4.1, S["metal"])
    plant("Hamam plant", 16.6, 28.3, h=2.6)


def bedroom_gf():
    level("GF")
    panel_wall("Bed Room panel", (30.17, 30.25, 28.0, 37.0), 0.0, 9.2)
    bed("Bed", 23.8, 30.1, 29.6, 35.6, "+x")
    for (y0, y1) in ((35.9, 37.3), (27.85, 29.25)):
        unit("Side table", "nightstand", 28.7, 30.1, y0, y1, 0, "-x", S["wood"], 2.0)
        lamp("Bedside lamp", 29.4, (y0 + y1) / 2, 2.0, h=1.7, r=0.45)
        light(29.4, (y0 + y1) / 2, 3.6, power=0.35)
    wardrobe("Wardrobe", 18.2, 20.2, 30.0, 36.6, 7.6, S["wardrobe"], front="+x")
    rug("Bed Room rug", 22.4, 28.6, 28.4, 36.8, S["rug_b"])
    sofa("Bed Room chair", 20.7, 22.7, 34.8, 36.8, "+y", S["chair_fabric"], cushions=False, arm=0.45)
    _fan("Bed Room fan", 25.0, 32.45, H)


def washrooms_gf():
    level("GF")
    finish_room("Attach tiles", "GF", GF_ROOMS["Attach Washroom"], 0.0, 7.0, S["bath_wall"])
    wc("Attach WC", 29.17, 25.3, "+x")
    vanity("Attach vanity", 26.4, 28.4, 21.75, 23.0, mirror_side="-y")
    shower("Attach shower", 28.5, 30.2, 21.75, 23.9, glass_side="x0")
    finish_room("Common tiles", "GF", GF_ROOMS["Common Washroom"], 0.0, 4.9, S["bath_wall"])
    wc("Common WC", 26.82, 18.0, "+x")
    vanity("Common vanity", 21.5, 23.5, 15.55, 16.8, mirror_side="-y")
    shower("Common shower", 18.25, 20.4, 15.55, 17.6, glass_side="y1")


def lounge_gf():
    """Entrance lounge = the house's crossroads (front door -> corridor, stairs, drawing room):
    one seating group in the front-left corner, everything else left clear."""
    level("GF")
    rug("Lounge rug", 3.2, 9.4, 9.2, 13.8, S["rug_a"])
    sofa("Lounge sofa", 2.9, 8.3, 7.0, 9.6, "-y", S["sofa"])
    sofa("Lounge armchair", 8.7, 10.8, 9.8, 12.0, "+x", S["chair_fabric"], cushions=False, arm=0.45)
    table("Lounge coffee table", 4.4, 7.0, 10.4, 12.2, 1.4, S["table_top"], S["wood_dark"])
    false_ceiling("GF Lounge ceiling", (8.0, 17.5, 6.8, 15.2), H)
    plant("Lounge plant", 16.7, 7.5)
    _fan("Lounge fan", 5.6, 10.6, H)


def drawing_room():
    level("GF")
    panel_wall("Drawing panel", (30.17, 30.25, 1.5, 14.0), 0.0, 9.2)
    rug("Drawing rug", 21.0, 29.4, 3.6, 11.4, S["rug_a"])
    sofa("Drawing sofa", 27.8, 30.15, 4.0, 10.6, "+x", S["sofa"])
    sofa("Drawing chair 1", 21.6, 23.7, 4.6, 6.8, "-x", S["chair_fabric"], cushions=False, arm=0.45)
    sofa("Drawing chair 2", 21.6, 23.7, 8.0, 10.2, "-x", S["chair_fabric"], cushions=False, arm=0.45)
    table("Drawing coffee table", 24.4, 26.8, 6.0, 8.8, 1.4, S["table_top"], S["wood_dark"])
    for (y0, y1) in ((2.4, 3.8), (10.8, 12.2)):
        unit("Drawing side table", "side_unit", 28.6, 30.0, y0, y1, 0, "-x", S["wood"], 2.0)
        lamp("Drawing lamp", 29.3, (y0 + y1) / 2, 2.0, h=1.9, r=0.5)
        light(29.3, (y0 + y1) / 2, 3.8, power=0.35)
    unit("Drawing console", "console", 21.0, 26.0, 13.4, 14.65, 0, "-y", S["wood"], 2.6)
    frame_art("Drawing art", "x", 14.7, 21.6, 25.4, 4.2, 6.8, "-y", S["art"])
    plant("Drawing plant 1", 29.4, 1.6)
    plant("Drawing plant 2", 19.4, 13.9)
    chandelier("Drawing chandelier", 24.2, 7.7, H - 0.75)


def corridor_gf():
    level("GF")
    frame_art("Corridor art", "x", 26.7, 14.0, 16.6, 4.3, 6.3, "-y", S["art2"])


# ================================================================ second floor
def family_lounge():
    level("SF")
    z = F2
    panel_wall("Family TV panel", (11.52, 11.6, -2.6, 6.0), z, z + H2)
    tv("Family TV", "y", 11.52, -0.2, 4.2, z + 3.1, "-x", S["black"])
    unit("Family TV unit", "tv_unit", 10.3, 11.5, -1.6, 5.0, z, "-x", S["wood"], 1.6)
    rug("Family rug", 4.0, 9.8, -1.4, 5.4, S["rug_a"], z)
    sofa("Family sofa", 2.9, 5.5, -1.6, 5.4, "-x", S["sofa"], z)
    sofa("Family armchair", 6.6, 8.7, -2.6, -0.5, "-y", S["chair_fabric"], z, cushions=False, arm=0.45)
    table("Family coffee table", 6.2, 8.6, 1.0, 3.8, 1.4, S["table_top"], S["wood_dark"], z)
    false_ceiling("SF Family ceiling", (2.5, 11.6, -2.75, 6.0), TOP)
    plant("Family plant", 10.6, 5.9, z)
    _fan("Family fan", 7.0, 1.6, TOP - 0.75)


def dining_library():
    """Upstairs sitting nook between the stair well and the bedrooms (no dining table: the family eats on a
    dastarkhan or in the lounge). Two chairs by the well railing; a clear 3-ft route along the east side."""
    level("SF")
    z = F2
    rug("Nook rug", 8.6, 13.4, 13.0, 18.4, S["rug_b"], z)
    sofa("Nook chair 1", 8.9, 11.0, 13.4, 15.5, "-x", S["chair_fabric"], z, cushions=False, arm=0.45)
    sofa("Nook chair 2", 8.9, 11.0, 15.9, 18.0, "-x", S["chair_fabric"], z, cushions=False, arm=0.45)
    table("Nook table", 11.6, 13.2, 14.9, 16.5, 1.6, S["table_top"], S["wood_dark"], z, round_=True)
    plant("Nook plant", 13.0, 19.8, z, h=3.2)
    light(11.0, 15.7, TOP - 0.9, power=0.8)


def master_suite():
    level("SF")
    z = F2
    panel_wall("Master panel", (19.6, 30.2, 14.62, 14.7), z, z + 8.6)
    bed("Master bed", 22.2, 28.4, 8.05, 14.45, "+y", z)        # 3+ ft clear between the door and the bed
    for x0 in (20.5, 28.75):
        unit("Master side table", "nightstand", x0, x0 + 1.4, 12.9, 14.3, z, "-y", S["wood"], 2.0)
        lamp("Master lamp", x0 + 0.7, 13.6, z + 2.0, h=1.7, r=0.45)
        light(x0 + 0.7, 13.6, z + 3.6, power=0.35)
    rug("Master rug", 21.2, 29.4, 4.8, 12.6, S["rug_b"], z)
    sofa("Master chair", 27.7, 29.8, 1.3, 3.4, "+x", S["chair_fabric"], z, cushions=False, arm=0.45)
    plant("Master plant", 19.3, 1.6, z)
    _fan("Master fan", 25.3, 8.0, TOP)
    # bath + dressing
    finish_room("Master bath tiles", "SF", SF_ROOMS["Master Bath"], z, 4.9, S["bath_wall"])
    vanity("Master vanity", 12.0, 13.3, -2.5, 0.2, z, mirror_side="-x")
    shower("Master shower", 12.05, 14.3, 0.1, 1.95, z, glass_side="x1")
    wc("Master WC", 16.42, -1.65, "+x", z)
    wardrobe("Dressing wardrobe", 12.0, 13.8, 2.45, 6.05, 7.6, S["wardrobe"], z=z, front="+x")
    box("Dressing mirror", 17.35, 17.45, 5.7, 6.05, z + 0.5, z + 6.5, S["mirror"])


def bedroom2():
    level("SF")
    z = F2
    panel_wall("Bedroom 2 panel", (30.17, 30.25, 28.0, 37.0), z, z + 8.6)
    bed("Bedroom 2 bed", 23.8, 30.1, 29.6, 35.6, "+x", z)
    for (y0, y1) in ((35.9, 37.3), (27.85, 29.25)):
        unit("Bedroom 2 side table", "nightstand", 28.7, 30.1, y0, y1, z, "-x", S["wood"], 2.0)
        lamp("Bedroom 2 lamp", 29.4, (y0 + y1) / 2, z + 2.0, h=1.7, r=0.45)
    wardrobe("Bedroom 2 wardrobe", 18.2, 20.2, 30.0, 36.6, 7.6, S["wardrobe"], z=z, front="+x")
    table("Bedroom 2 desk", 20.8, 23.6, 35.6, 37.4, 2.5, S["wood"], S["wood_dark"], z)
    chair("Bedroom 2 chair", 22.2, 34.6, "-y", S["wood_dark"], S["seat"], z)
    rug("Bedroom 2 rug", 22.4, 28.6, 28.4, 36.8, S["rug_b"], z)
    _fan("Bedroom 2 fan", 25.0, 32.45, TOP)


def bedroom3():
    level("SF")
    z = F2
    panel_wall("Bedroom 3 panel", (17.42, 17.5, 29.4, 36.8), z, z + 8.6)
    bed("Bedroom 3 bed", 11.8, 17.4, 32.1, 36.7, "+x", z)       # smaller double, clear of the door swing
    unit("Bedroom 3 side table", "nightstand", 16.1, 17.4, 30.5, 31.8, z, "-x", S["wood"], 2.0)
    lamp("Bedroom 3 lamp", 16.75, 31.15, z + 2.0, h=1.7, r=0.45)
    wardrobe("Bedroom 3 wardrobe", 13.6, 17.45, 27.45, 29.2, 7.6, S["wardrobe"], z=z, front="+y")
    rug("Bedroom 3 rug", 10.4, 16.0, 31.2, 37.0, S["rug_b"], z)
    _fan("Bedroom 3 fan", 13.0, 32.4, TOP)


def study():
    level("SF")
    z = F2
    table("Study desk", 0.8, 3.0, 25.2, 28.8, 2.5, S["wood"], S["wood_dark"], z)
    box("Study monitor", 1.0, 1.15, 26.2, 27.8, z + 2.8, z + 4.0, S["black"])
    chair("Study chair", 3.7, 27.0, "-x", S["wood_dark"], S["seat"], z)
    bookshelf("Study shelf", 1.0, 7.6, 30.45, 32.15, 7.6, S["wood"], S["books"], z, front="-y")
    rug("Study rug", 2.4, 7.0, 23.2, 30.4, S["rug_b"], z)
    lamp("Study lamp", 2.4, 25.6, z + 2.5, h=1.5, r=0.35)


def baths_sf():
    level("SF")
    z = F2
    finish_room("Bath 3 tiles", "SF", SF_ROOMS["Bath 3"], z, 4.9, S["bath_wall"])
    wc("Bath 3 WC", 1.83, 35.4, "-x", z)
    vanity("Bath 3 vanity", 3.0, 5.0, 36.2, 37.45, z)
    shower("Bath 3 shower", 0.8, 2.8, 32.65, 34.3, z, glass_side="x1")
    finish_room("Bath 2 tiles", "SF", SF_ROOMS["Bath 2"], z, 4.9, S["bath_wall"])
    wc("Bath 2 WC", 29.17, 25.3, "+x", z)
    vanity("Bath 2 vanity", 26.4, 28.4, 21.75, 23.0, z, mirror_side="-y")
    shower("Bath 2 shower", 28.5, 30.2, 21.75, 23.9, z, glass_side="x0")
    finish_room("Common bath tiles", "SF", SF_ROOMS["Common Bath"], z, 4.9, S["bath_wall"])
    wc("Common bath WC", 26.82, 18.0, "+x", z)
    vanity("Common bath vanity", 21.5, 23.5, 15.55, 16.8, z, mirror_side="-y")
    shower("Common bath shower", 18.25, 20.4, 15.55, 17.6, z, glass_side="y1")


# ================================================================ lights / decor helpers
def pendant(name, x, y, ceil, drop=3.0):
    if has_model("pendant"):
        model(name, M_("pendant"), x - 1.0, x + 1.0, y - 1.0, y + 1.0, hang=ceil, h=2.6)
        light(x, y, ceil - 2.8, power=0.8)
        return
    rod(name + " cord", (x, y, ceil), (x, y, ceil - drop), 0.02, S["black"])
    cyl(name + " shade", x, y, ceil - drop - 0.9, ceil - drop, 0.9, S["pendant"], r2=0.3, seg=24)
    cyl(name + " bulb", x, y, ceil - drop - 0.85, ceil - drop - 0.7, 0.35, S["lampshade"], seg=12)
    light(x, y, ceil - drop - 1.2, power=0.8)


def chandelier(name, x, y, ceil):
    if has_model("chandelier"):
        model(name, M_("chandelier"), x - 1.4, x + 1.4, y - 1.4, y + 1.4, hang=ceil, h=2.6)
        light(x, y, ceil - 2.4, power=1.0)
        return
    rod(name + " chain", (x, y, ceil), (x, y, ceil - 1.6), 0.03, S["handle"])
    cyl(name + " ring", x, y, ceil - 1.9, ceil - 1.75, 1.3, S["handle"], seg=28)
    for k in range(8):
        a = k * math.pi / 4
        cyl(f"{name} candle{k}", x + 1.2 * math.cos(a), y + 1.2 * math.sin(a), ceil - 1.75, ceil - 1.3, 0.12, S["lampshade"], seg=8)
    light(x, y, ceil - 2.2, power=1.0)


def decor():
    """Small real objects that make rooms feel lived in (each only if the design names a model for it)."""
    if has_model("vase"):
        level("GF"); model("Drawing vase", M_("vase"), 21.4, 22.4, 13.6, 14.5, 2.6, "-y", h=1.4)
    if has_model("clock"):
        level("GF"); model("Kitchen clock", M_("clock"), 8.45, 8.6, 27.0, 28.4, 6.2, "-x", h=1.05)
    if has_model("books"):
        level("SF"); model("Study books", M_("books"), 1.2, 2.8, 28.0, 28.7, F2 + 2.5, "+x", h=0.8)
    if has_model("tea"):
        level("SF"); model("Family tea set", M_("tea"), 6.6, 8.2, 1.6, 3.2, F2 + 1.4, "-y", h=0.5)
    if has_model("aircon"):
        level("GF"); model("Outdoor AC", M_("aircon"), 31.0, 32.3, 24.0, 30.0, 0.0, "+x", cname="Site")
        level("SF"); model("Outdoor AC 2", M_("aircon"), 31.0, 32.3, 4.0, 10.0, F2 - 0.6, "+x", cname="Site")


def all_common(skip=()):
    """Every room that looks the same in all designs. skip: names of room functions to leave out."""
    for fn in (kitchen, store, hamam, bedroom_gf, washrooms_gf, corridor_gf, dining_library, master_suite,
               bedroom2, bedroom3, study, baths_sf):
        if fn.__name__ not in skip:
            fn()
    if "decor" not in skip:
        decor()
