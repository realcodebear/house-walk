"""Download CC0 furniture / decor / plant models from Poly Haven (glTF, 1k textures) into blender/assets/ph/<id>/.

    python3 tools/fetch_models.py            # the default set below
    python3 tools/fetch_models.py sofa_02 ArmChair_01
All Poly Haven assets are CC0 (public domain): https://polyhaven.com/license
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "blender", "assets", "ph")
DEFAULT = [
    # seating
    "sofa_02", "sofa_03", "Sofa_01", "chinese_sofa", "painted_wooden_sofa", "vintage_day_bed",
    "ArmChair_01", "modern_arm_chair_01", "mid_century_lounge_chair", "GreenChair_01", "chinese_armchair",
    "gallinera_chair", "painted_wooden_chair_01", "WoodenChair_01", "Ottoman_01",
    # tables + storage
    "CoffeeTable_01", "coffee_table_round_01", "modern_coffee_table_01", "modern_coffee_table_02",
    "gothic_coffee_table", "side_table_01", "side_table_tall_01", "small_wooden_table_01",
    "round_wooden_table_01", "chinese_tea_table", "ClassicConsole_01", "ClassicNightstand_01",
    "painted_wooden_nightstand", "chinese_console_table", "gallinera_table", "WoodenTable_02",
    "modern_wooden_cabinet", "vintage_cabinet_01", "chinese_cabinet", "drawer_cabinet",
    "wooden_bookshelf_worn", "wooden_display_shelves_01",
    # lighting
    "Chandelier_01", "Chandelier_02", "chinese_chandelier", "lantern_chandelier_01", "modern_ceiling_lamp_01",
    "Lantern_01", "brass_diya_lantern", "desk_lamp_arm_01", "street_lamp_01", "ceiling_fan",
    # plants + garden
    "potted_plant_01", "potted_plant_02", "potted_plant_04", "calathea_orbifolia_01", "anthurium_botany_01",
    "pachira_aquatica_01", "fern_02", "shrub_01", "shrub_02", "shrub_04", "island_tree_01", "island_tree_02",
    "jacaranda_tree", "tree_small_02", "pine_tree_01",
    # decor
    "brass_pot_01", "brass_vase_01", "brass_vase_03", "ceramic_vase_01", "ceramic_vase_03", "antique_ceramic_vase_01",
    "decorative_book_set_01", "book_encyclopedia_set_01", "hanging_picture_frame_01", "hanging_picture_frame_02",
    "hanging_picture_frame_03", "fancy_picture_frame_01", "ornate_mirror_01", "wall_clock", "mantel_clock_01",
    "tea_set_01", "throw_pillows_01", "wicker_basket_01", "wooden_bowl_01", "carved_wooden_plate",
    "scandinavian_masonry_heater", "exterior_aircon_unit", "vintage_electric_kettle", "electric_stove",
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "house-walk-builder/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch(asset, res="1k"):
    d = os.path.join(OUT, asset)
    if os.path.exists(os.path.join(d, "done")):
        return "cached"
    files = json.loads(get(f"https://api.polyhaven.com/files/{asset}"))
    g = files.get("gltf", {})
    pick = res if res in g else sorted(g, key=lambda k: int(k.rstrip("k")))[0]
    entry = g[pick]["gltf"]
    os.makedirs(d, exist_ok=True)
    main = os.path.join(d, os.path.basename(entry["url"]))
    open(main, "wb").write(get(entry["url"]))
    total = os.path.getsize(main)
    for rel, inc in entry.get("include", {}).items():
        p = os.path.normpath(os.path.join(d, rel))
        if not p.startswith(d):                      # never write outside the asset folder
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(get(inc["url"]))
        total += os.path.getsize(p)
    open(os.path.join(d, "done"), "w").write(pick)
    return f"{pick} {total / 1e6:.1f} MB"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[1:] or DEFAULT
    for n in names:
        try:
            print(n, fetch(n), flush=True)
        except Exception as e:
            print(n, "FAILED", e, flush=True)
    with open(os.path.join(OUT, "CREDITS.md"), "w") as fh:
        fh.write("# Models\n\nAll models in this folder are from Poly Haven (https://polyhaven.com), licensed CC0 (public domain).\n\n")
        for n in sorted(os.listdir(OUT)):
            if os.path.isdir(os.path.join(OUT, n)):
                fh.write(f"- {n}: https://polyhaven.com/a/{n}\n")
