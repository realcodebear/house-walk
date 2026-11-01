"""Make site/assets/jack.glb: Last Shepherd's Jack (low-poly body, jack2_far.glb) plus a few of the
Kimodo clips from jack2_kimodo.glb. Both share the GAME skeleton, so clips are matched by bone name.
Also writes site/assets/jack.json with each clip's measured speed and cycle length (from the clip JSON).

    python3 tools/make_jack.py
"""
import json, os, struct, sys

SRC = os.path.expanduser("~/code-bear-channel/animal-generator/world/assets")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "assets")
KEEP = ["K_Idle", "K_IdleLook", "K_Walk", "K_Jog", "K_Run", "Jump_Air", "Jump_Land"]
COMP = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    data = open(path, "rb").read()
    off, chunks = 12, []
    while off < len(data):
        n, kind = struct.unpack("<I4s", data[off:off + 8])
        chunks.append((kind, data[off + 8:off + 8 + n]))
        off += 8 + n
    return json.loads(chunks[0][1]), (chunks[1][1] if len(chunks) > 1 else b"")


def accessor_bytes(j, bin_, ai):
    a = j["accessors"][ai]
    bv = j["bufferViews"][a["bufferView"]]
    el = COMP[a["componentType"]] * NCOMP[a["type"]]
    stride = bv.get("byteStride", el)
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    if stride == el:
        return bytes(bin_[start:start + el * a["count"]])
    return b"".join(bin_[start + i * stride:start + i * stride + el] for i in range(a["count"]))


def main():
    body, body_bin = read_glb(os.path.join(SRC, "jack2_far.glb"))
    full, full_bin = read_glb(os.path.join(SRC, "jack2_kimodo.glb"))
    meta = json.load(open(os.path.join(SRC, "jack2_kimodo_clips.json")))
    by_name = {n.get("name"): i for i, n in enumerate(body["nodes"])}
    out_bin = bytearray(body_bin)
    body.setdefault("animations", [])
    copied = {}

    def copy_accessor(ai, values=None):
        """Append accessor `ai` of the full model to the body's buffer (optionally with new float data)."""
        if ai in copied and values is None:
            return copied[ai]
        while len(out_bin) % 4:
            out_bin.append(0)
        raw = values if values is not None else accessor_bytes(full, full_bin, ai)
        body["bufferViews"].append({"buffer": 0, "byteOffset": len(out_bin), "byteLength": len(raw)})
        out_bin.extend(raw)
        acc = dict(full["accessors"][ai])
        acc["bufferView"] = len(body["bufferViews"]) - 1
        acc.pop("byteOffset", None)
        body["accessors"].append(acc)
        idx = len(body["accessors"]) - 1
        if values is None:
            copied[ai] = idx
        return idx

    for name in KEEP:
        anim = next(a for a in full["animations"] if a["name"] == name)
        new = {"name": name, "channels": [], "samplers": []}
        for ch in anim["channels"]:
            bone = full["nodes"][ch["target"]["node"]].get("name")
            if bone not in by_name:
                continue
            s = anim["samplers"][ch["sampler"]]
            out_vals = None
            if bone == "root" and ch["target"]["path"] == "translation":
                # keep him in place: the game moves the body, the clip only animates it
                raw = accessor_bytes(full, full_bin, s["output"])
                f = list(struct.unpack(f"<{len(raw) // 4}f", raw))
                x0, z0 = f[0], f[2]
                for k in range(0, len(f), 3):
                    f[k], f[k + 2] = x0, z0
                out_vals = struct.pack(f"<{len(f)}f", *f)
            new["samplers"].append({"input": copy_accessor(s["input"]), "output": copy_accessor(s["output"], out_vals),
                                    "interpolation": s.get("interpolation", "LINEAR")})
            new["channels"].append({"sampler": len(new["samplers"]) - 1,
                                    "target": {"node": by_name[bone], "path": ch["target"]["path"]}})
        body["animations"].append(new)

    while len(out_bin) % 4:
        out_bin.append(0)
    body["buffers"] = [{"byteLength": len(out_bin)}]
    js = json.dumps(body, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "jack.glb"), "wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(out_bin)))
        fh.write(struct.pack("<I4s", len(js), b"JSON") + js)
        fh.write(struct.pack("<I4s", len(out_bin), b"BIN\x00") + bytes(out_bin))
    clips = {k: {f: meta[k][f] for f in ("speed_mps", "cycle_s", "duration") if f in meta.get(k, {})} for k in KEEP}
    json.dump(clips, open(os.path.join(OUT, "jack.json"), "w"), indent=1)
    print("jack.glb", round((12 + 16 + len(js) + len(out_bin)) / 1e6, 2), "MB,", len(KEEP), "clips")


if __name__ == "__main__":
    sys.exit(main())
