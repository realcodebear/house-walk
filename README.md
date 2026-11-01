# House Walk

A two-storey house built in Blender from a hand-drawn floor plan (`plan.jpg`), walkable in the browser with Jack from *Last Shepherd*.

**Play:** https://realcodebear.github.io/house-walk/

## Controls

| Desktop | Phone / tablet |
|---|---|
| `W A S D` walk, mouse look, `Shift` run, `Space` jump | left thumb: walk, right thumb: look |
| `E` or click: open / close a door | tap a door, or press **Open** |
| `V` first / third person, mouse wheel: camera distance | **View** button |
| `1` `2` `0` ground floor / second floor / outside | **Floor ▸** button |
| `M` map, `L` room lights | **Map**, **Lights** |

## Layout

- `plan.jpg` — the reference floor plan (31' × 38'-3")
- `blender/build_v1.py` — builds the whole house from plan measurements in feet; writes `blender/house_v1.blend`, `renders/v1/` and the game model `site/v1/house.glb` + `house.json`
- `site/` — the website (GitHub Pages): `v1/` is the game, `assets/` holds Jack
- `tools/make_jack.py` — makes `site/assets/jack.glb` (low-poly Jack + walk / jog / run / idle clips)

Rebuild the house:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -y -P blender/build_v1.py
```
