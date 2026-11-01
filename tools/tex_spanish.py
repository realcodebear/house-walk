"""Procedural textures for the Spanish Villa design -> blender/tex/s_*.jpg (+ s_*_n.jpg normal maps, s_*.png cut-outs).

    python3 tools/tex_spanish.py              # all
    python3 tools/tex_spanish.py s_azulejo s_kilim
Everything is drawn from noise and simple geometry (helpers copied from make_textures.py), no third-party images.
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "blender", "tex")


# ---------------------------------------------------------------- helpers (from make_textures.py)
def fbm(n, beta=2.0, seed=0, aniso=(1.0, 1.0)):
    """Periodic 1/f^beta noise in [0, 1] (tileable by construction: built in frequency space)."""
    r = np.random.default_rng(seed)
    fx = np.fft.fftfreq(n)[None, :] * aniso[0]
    fy = np.fft.fftfreq(n)[:, None] * aniso[1]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    spec = (r.normal(size=(n, n)) + 1j * r.normal(size=(n, n))) / f ** (beta / 2)
    spec[0, 0] = 0
    a = np.real(np.fft.ifft2(spec))
    a -= a.min()
    return a / a.max()


def grid(n, m=None):
    m = m or n
    y, x = np.mgrid[0:m, 0:n]
    return x / n, y / m


def save(name, rgb, q=88):
    os.makedirs(OUT, exist_ok=True)
    img = Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8))
    img.save(os.path.join(OUT, name + ".jpg"), quality=q)


def save_png(name, rgba):
    Image.fromarray(np.clip(rgba * 255, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, name + ".png"), optimize=True)


def save_normal(name, height, strength=2.0, size=None):
    h = height
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nrm = np.dstack([-dx, dy, np.ones_like(h)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    img = Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8))
    if size:
        img = img.resize((size, size), Image.LANCZOS)
    img.save(os.path.join(OUT, name + "_n.jpg"), quality=90)


def mix(a, b, t):
    t = t[..., None] if np.ndim(t) == 2 else t
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def tiles_mask(n, count, grout, warp=None):
    """1 inside tiles, 0 in the grout lines; `count` tiles per side (optionally warped for a hand-made look)."""
    x, y = grid(n)
    if warp is not None:
        x, y = x + warp[0], y + warp[1]
    gx = np.abs(((x * count) % 1) - 0.5) * 2
    gy = np.abs(((y * count) % 1) - 0.5) * 2
    g = grout * count * 2
    return np.clip((1 - gx) / g, 0, 1) * np.clip((1 - gy) / g, 0, 1)


def hash01(k, s=0.0):
    return (np.sin(np.asarray(k, float) * 12.9898 + s * 78.233) * 43758.5453) % 1.0


def down(a, f=2):
    """Box-filter downsample (anti-aliasing for shapes drawn at f x resolution)."""
    h, w = a.shape[:2]
    return a.reshape(h // f, f, w // f, f, *a.shape[2:]).mean(axis=(1, 3))


C = lambda *v: np.array(v, float)


# ---------------------------------------------------------------- tiles
def azulejo_tile(m, variant=0):
    """One 4-fold symmetric blue-and-white tile (corner motifs join into circles across four tiles)."""
    x, y = grid(m)
    u, v = x - 0.5, y - 0.5
    r, th = np.hypot(u, v), np.arctan2(v, u)
    white, cob, light, ochre = C(0.93, 0.92, 0.86), C(0.06, 0.16, 0.48), C(0.36, 0.53, 0.8), C(0.84, 0.6, 0.17)
    col = np.zeros((m, m, 3)) + white
    pr = 0.2 * (0.42 + 0.58 * np.abs(np.cos(4 * th)) ** 0.8)
    petal = r < pr
    col[petal] = light
    col[petal & (r > pr - 0.022)] = cob
    col[r < 0.075] = cob
    col[r < 0.058] = ochre
    col[(r > 0.252) & (r < 0.274)] = cob
    rc = np.minimum.reduce([np.hypot(x - a, y - b) for a in (0, 1) for b in (0, 1)])
    col[rc < 0.17] = cob
    col[rc < 0.125] = white
    col[rc < 0.105] = light
    col[rc < 0.05] = ochre
    d1, d2 = (u + v) / math.sqrt(2), (u - v) / math.sqrt(2)
    for a, b in ((d1, d2), (d2, d1)):
        for s in (1, -1):
            e = ((a - s * 0.335) / 0.072) ** 2 + (b / 0.034) ** 2
            col[e < 1] = light
            col[(e < 1) & (e > 0.55)] = cob
    for cx, cy in ((0.5, 0), (0.5, 1), (0, 0.5), (1, 0.5)):
        dd = np.abs(x - cx) + np.abs(y - cy)
        col[dd < 0.11] = cob
        col[dd < 0.055] = white if variant == 0 else ochre
    if variant == 1:                                  # second pattern: star instead of rosette
        star = r < 0.21 * (0.55 + 0.45 * np.abs(np.cos(4 * th + math.pi / 4)) ** 3)
        col[star & (r > 0.08)] = cob
    return col


def azulejo(name, variant=0):
    n, k = 1024, 4
    m = n // k
    tile = down(azulejo_tile(m * 2, variant), 2)
    col = np.tile(tile, (k, k, 1))
    x, y = grid(n)
    ti = (x * k).astype(int) * 5 + (y * k).astype(int) * 3
    paint = gaussian_filter(fbm(n, 1.4, 201 + variant), 0.6, mode="wrap")
    blue = col[..., 2] - col[..., 0] > 0.2
    col[blue] *= (0.82 + 0.3 * paint[blue])[:, None]               # hand-painted cobalt density
    col *= (0.96 + 0.06 * hash01(ti))[..., None]
    fx, fy = (x * k) % 1, (y * k) % 1
    e = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
    col *= (0.9 + 0.1 * np.clip(e / 0.05, 0, 1))[..., None]          # glaze pillowing at the tile edge
    msk = tiles_mask(n, k, 0.0035)
    col = mix(C(0.78, 0.76, 0.71), col, msk)
    save(name, col)
    save_normal(name, msk * 0.7 + 0.03 * fbm(n, 1.0, 205), 2.0, 512)


def azulejo_border(name):
    """A frieze tile row (cenefa): vine scroll in cobalt and ochre between two blue lines, 4 tiles per repeat."""
    w, h = 512, 128
    x, y = grid(w * 2, h * 2)
    fx = (x * 4) % 1
    col = np.zeros((h * 2, w * 2, 3)) + C(0.93, 0.92, 0.86)
    cob, ochre, light = C(0.06, 0.16, 0.48), C(0.84, 0.6, 0.17), C(0.36, 0.53, 0.8)
    col[(y < 0.1) | (y > 0.9)] = cob
    wave = 0.5 + 0.2 * np.sin(2 * math.pi * fx)
    col[np.abs(y - wave) < 0.035] = cob
    for k in range(2):
        cx = 0.25 + 0.5 * k
        cy = 0.5 + 0.2 * math.sin(2 * math.pi * cx) * -1
        rr = np.hypot((fx - cx) * 4, (y - (1 - cy)) * 1)
        col[rr < 0.16] = light
        col[rr < 0.07] = ochre
    col[(np.abs(y - 0.5) < 0.03) & (np.abs(fx - 0.5) < 0.04)] = ochre
    col = down(col, 2)
    xx, yy = grid(w, h)
    g = np.minimum((xx * 4) % 1, 1 - (xx * 4) % 1) < 0.006
    col[g] = C(0.78, 0.76, 0.71)
    save(name, col)


def terracotta(name):
    """Hand-made Spanish floor tiles (Saltillo style): 3 x 3 per repeat, uneven colour, darker worn edges."""
    n, k = 1024, 3
    x, y = grid(n)
    wx = (fbm(n, 3.2, 301) - 0.5) * 0.006
    wy = (fbm(n, 3.2, 302) - 0.5) * 0.006
    msk = tiles_mask(n, k, 0.0042, (wx, wy))
    ti = ((x + wx) * k).astype(int) % k * 7 + ((y + wy) * k).astype(int) % k * 13
    h1, h2 = hash01(ti, 1), hash01(ti, 2)
    base = mix(C(0.6, 0.28, 0.14), C(0.77, 0.45, 0.25), h1) * (0.9 + 0.18 * h2)[..., None]
    blot = fbm(n, 2.3, 303)
    base = mix(base, base * C(0.82, 0.74, 0.7), np.clip(blot * 1.6 - 0.6, 0, 1))
    base *= (0.92 + 0.14 * fbm(n, 0.6, 304))[..., None]
    fx, fy = ((x + wx) * k) % 1, ((y + wy) * k) % 1
    e = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
    base *= (0.84 + 0.16 * np.clip(e / 0.07, 0, 1))[..., None]
    col = mix(C(0.66, 0.62, 0.54), base, msk)
    save(name, col)
    save_normal(name, msk * 0.8 + 0.12 * fbm(n, 2.0, 305), 2.2, 512)


def roof_barrel(name):
    """Clay barrel tiles for the corrugated roof shell: 4 tiles across (u) x 4 courses (v) per repeat.
    The geometry makes the barrels; this adds colour per tile, course shadows, dirt in the channels, lichen."""
    n, cols, rows = 512, 4, 4
    x, y = grid(n)
    vv = 1 - y                                     # image rows run top->bottom; v runs up the slope
    cx = (x * cols) % 1
    cv = (vv * rows) % 1
    ci, ri = (x * cols).astype(int), (vv * rows).astype(int)
    tid = ci * 11 + ri * 17
    pal = [C(0.70, 0.33, 0.18), C(0.6, 0.27, 0.15), C(0.75, 0.42, 0.24), C(0.56, 0.3, 0.2), C(0.79, 0.47, 0.3), C(0.66, 0.36, 0.22)]
    pick = (hash01(tid, 3) * len(pal)).astype(int)
    col = np.zeros((n, n, 3))
    for i, p in enumerate(pal):
        col[pick == i] = p
    col *= (0.9 + 0.2 * hash01(tid, 4))[..., None]
    col *= (0.88 + 0.22 * fbm(n, 1.6, 401))[..., None]
    streak = fbm(n, 2.4, 402, aniso=(1.0, 12.0))
    col *= (0.86 + 0.2 * streak)[..., None]
    chan = np.exp(-(np.minimum(cx, 1 - cx) / 0.13) ** 2)
    col = mix(col, col * C(0.62, 0.6, 0.5), chan * 0.6)
    shadow = np.clip((cv - 0.8) / 0.2, 0, 1) ** 1.5
    col *= (1 - 0.55 * shadow)[..., None]
    col *= (1 + 0.12 * (cv < 0.05))[..., None]
    lich = np.clip((fbm(n, 1.2, 403) - 0.78) * 6, 0, 1) * np.clip((fbm(n, 2.5, 404) - 0.4) * 3, 0, 1)
    col = mix(col, C(0.72, 0.7, 0.55), lich * 0.6)
    save(name, col)
    save_normal(name, (1 - cv) * 0.6 + 0.05 * fbm(n, 1.5, 405), 3.0)


# ---------------------------------------------------------------- wood
def wood_along(n, light, dark, rings, seed, along="x"):
    x, y = grid(n)
    if along == "x":
        t = fbm(n, 3.0, seed, aniso=(10.0, 1.0))
        g = 0.5 + 0.5 * np.sin(2 * np.pi * (y * rings + t * 2.2))
        pores = fbm(n, 1.1, seed + 1, aniso=(30.0, 1.0))
    else:
        t = fbm(n, 3.0, seed, aniso=(1.0, 10.0))
        g = 0.5 + 0.5 * np.sin(2 * np.pi * (x * rings + t * 2.2))
        pores = fbm(n, 1.1, seed + 1, aniso=(1.0, 30.0))
    return mix(light, dark, np.clip(g ** 1.8 * 0.8 + pores * 0.18, 0, 1))


def beam(name):
    """Hand-hewn dark oak beam, grain along u (the beam builder maps u along the beam)."""
    n = 512
    x, y = grid(n)
    col = wood_along(n, C(0.34, 0.22, 0.13), C(0.17, 0.1, 0.06), 9, 501, "x")
    adze = 0.5 + 0.5 * np.sin(2 * np.pi * (x * 5 + 0.6 * fbm(n, 2.5, 502)))
    col *= (0.88 + 0.16 * adze)[..., None]
    crack = (np.abs(np.sin(2 * np.pi * (y * 3 + 0.08 * fbm(n, 3.0, 503, aniso=(8.0, 1.0))))) < 0.012) & (fbm(n, 2.0, 504, aniso=(6.0, 1.0)) > 0.55)
    col[crack] *= 0.35
    save(name, col)


def door_planks(name):
    """Vertical oak planks with V-grooves (front door, gates, shutters)."""
    n, k = 512, 4
    x, y = grid(n)
    col = wood_along(n, C(0.4, 0.26, 0.15), C(0.2, 0.12, 0.07), 14, 511, "y")
    pi = (x * k).astype(int)
    col *= (0.88 + 0.2 * hash01(pi, 5))[..., None]
    d = np.minimum((x * k) % 1, 1 - (x * k) % 1)
    gro = np.clip(d / 0.02, 0, 1)
    col *= (0.3 + 0.7 * gro)[..., None]
    save(name, col)
    save_normal(name, gro, 2.5)


def oak(name):
    n = 512
    col = wood_along(n, C(0.5, 0.33, 0.19), C(0.3, 0.19, 0.1), 8, 521, "y")
    col *= (0.93 + 0.1 * fbm(n, 1.5, 522))[..., None]
    save(name, col)


# ---------------------------------------------------------------- textiles
def leather(name):
    n = 512
    pebble = fbm(n, 0.35, 601)
    pebble = gaussian_filter(pebble, 1.0, mode="wrap")
    grain = np.clip((pebble - pebble.mean()) * 5 + 0.5, 0, 1)
    wear = fbm(n, 2.6, 602)
    col = mix(C(0.36, 0.16, 0.07), C(0.56, 0.29, 0.13), wear)
    col *= (0.88 + 0.16 * grain)[..., None]
    crease = fbm(n, 2.0, 603, aniso=(1.0, 4.0))
    col *= (0.92 + 0.1 * crease)[..., None]
    save(name, col)
    save_normal(name, grain * 0.5 + crease * 0.3, 1.5)


def kilim(name, field, med, frame, accent, cream, dark, seed=0):
    """A whole woven rug (UV 'fit'): stepped diamond medallion, diamond lattice field, zig-zag borders."""
    n = 1024
    x, y = grid(n)
    u = np.floor(x * 180) / 180                    # weave grid -> stepped edges
    v = np.floor(y * 220) / 220
    col = np.zeros((n, n, 3)) + field
    fu, fv = (u * 9) % 1 - 0.5, (v * 11) % 1 - 0.5
    dmd = np.abs(fu) + np.abs(fv)
    col[dmd < 0.26] = accent
    col[dmd < 0.12] = cream
    col[(dmd > 0.36) & (dmd < 0.42)] = dark
    md = np.abs(u - 0.5) / 0.3 + np.abs(v - 0.5) / 0.34
    col[md < 1.0] = frame
    col[md < 0.86] = med
    col[(md < 0.7)] = cream
    col[md < 0.56] = field
    col[md < 0.4] = accent
    col[md < 0.22] = frame
    col[md < 0.1] = cream
    hook = (np.abs(md - 0.93) < 0.04) & ((np.floor(u * 40) + np.floor(v * 40)) % 2 == 0)
    col[hook] = cream
    e = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    band = e < 0.11
    col[band] = dark
    zz = np.abs(((u + v) * 26) % 1 - 0.5) + np.abs(((u - v) * 26) % 1 - 0.5)
    col[band & (zz < 0.42)] = frame
    col[band & (zz < 0.22)] = cream
    col[(e > 0.11) & (e < 0.125)] = cream
    col[(e > 0.135) & (e < 0.15)] = accent
    col[e < 0.018] = cream * 0.9
    weft = 0.92 + 0.08 * np.sin(2 * np.pi * y * 420)
    col *= (weft * (0.88 + 0.22 * fbm(n, 0.9, 611 + seed)))[..., None]
    col *= (0.92 + 0.1 * fbm(n, 2.4, 612 + seed))[..., None]           # gentle fading
    save(name, col)


def jute(name):
    n, rows = 512, 8
    x, y = grid(n)
    ri = (y * rows).astype(int)
    sgn = np.where(ri % 2 == 0, 1, -1)
    s = 0.5 + 0.5 * np.sin(2 * np.pi * (x * 24 + sgn * y * 24))
    gap = np.minimum((y * rows) % 1, 1 - (y * rows) % 1) < 0.05
    col = mix(C(0.56, 0.44, 0.28), C(0.76, 0.64, 0.45), s * 0.8 + 0.2 * fbm(n, 1.0, 621))
    col[gap] *= 0.55
    save(name, col)
    save_normal(name, s * (1 - gap), 1.5)


def linen(name):
    n = 512
    x, y = grid(n)
    a = np.sin(2 * np.pi * (x * 110 + 1.5 * fbm(n, 2.5, 631, aniso=(1.0, 6.0))))
    b = np.sin(2 * np.pi * (y * 110 + 1.5 * fbm(n, 2.5, 632, aniso=(6.0, 1.0))))
    slub = fbm(n, 1.4, 633, aniso=(1.0, 14.0))
    val = 0.8 + 0.06 * a + 0.06 * b + 0.12 * (slub - 0.5)
    save(name, np.dstack([val, val, val * 0.98]))


def stripe(name):
    """Andalusian striped cotton for cushions and throws."""
    n = 256
    x, y = grid(n)
    bands = [(0.0, C(0.86, 0.8, 0.66)), (0.3, C(0.62, 0.14, 0.1)), (0.38, C(0.86, 0.8, 0.66)), (0.46, C(0.8, 0.56, 0.16)),
             (0.52, C(0.86, 0.8, 0.66)), (0.68, C(0.13, 0.2, 0.36)), (0.78, C(0.86, 0.8, 0.66)), (0.9, C(0.62, 0.14, 0.1)), (0.94, C(0.86, 0.8, 0.66))]
    col = np.zeros((n, n, 3))
    for i, (s, c) in enumerate(bands):
        e = bands[i + 1][0] if i + 1 < len(bands) else 1.01
        col[(y >= s) & (y < e)] = c
    col *= (0.9 + 0.1 * np.sin(2 * np.pi * x * 64))[..., None]
    save(name, col)


def limewash(name):
    """Hand-trowelled lime stucco: soft warm-white clouds, trowel sweeps and a bumpy normal map."""
    n = 1024
    cloud = fbm(n, 2.6, 901)
    sweep = fbm(n, 2.2, 902, aniso=(3.0, 1.0))
    grit = fbm(n, 0.9, 903)
    val = 0.95 + 0.05 * (cloud - 0.5) * 2 + 0.025 * (sweep - 0.5) * 2 + 0.02 * (grit - 0.5) * 2
    col = np.dstack([val, val * 0.985, val * 0.95])
    save(name, col)
    save_normal(name, sweep * 0.5 + grit * 0.35 + cloud * 0.4, 3.0, 512)


# ---------------------------------------------------------------- ground
def cobble(name):
    """Andalusian pebble paving (empedrado): pebbles set on edge, bands of dark and light stones."""
    n, k = 1024, 26
    rng = np.random.default_rng(701)
    hmap = np.zeros((n, n))
    col = np.zeros((n, n, 3)) + C(0.6, 0.55, 0.46)
    cs = n / k
    yy, xx = np.mgrid[0:int(cs * 2), 0:int(cs * 2)]
    for i in range(k):
        for j in range(k):
            band = (j // 3) % 3 == 0
            cx, cy = (i + 0.5 + rng.uniform(-0.15, 0.15)) * cs, (j + 0.5 + rng.uniform(-0.15, 0.15)) * cs
            rx, ry = rng.uniform(0.34, 0.47) * cs, rng.uniform(0.22, 0.32) * cs
            a = rng.uniform(-0.4, 0.4) + (math.pi / 2 if (i + j) % 2 else 0)
            g = rng.uniform(0.25, 0.4) if band else rng.uniform(0.62, 0.86)
            tint = C(g, g * 0.98, g * 0.94)
            ox, oy = int(cx - cs), int(cy - cs)
            px, py = xx + ox - cx, yy + oy - cy
            ca, sa = math.cos(a), math.sin(a)
            qx, qy = (px * ca + py * sa) / rx, (-px * sa + py * ca) / ry
            d = qx * qx + qy * qy
            inside = d < 1
            hh = np.sqrt(np.clip(1 - d, 0, 1))
            rows, cols_ = (yy + oy) % n, (xx + ox) % n
            sel = inside & (hh > hmap[rows, cols_])
            hmap[rows[sel], cols_[sel]] = hh[sel]
            shade = (0.75 + 0.35 * hh[sel])[:, None]
            col[rows[sel], cols_[sel]] = tint * shade
    col *= (0.92 + 0.12 * fbm(n, 1.0, 702))[..., None]
    save(name, col)
    save_normal(name, hmap, 3.0, 512)


def gravel(name):
    n = 512
    a = fbm(n, 0.2, 711)
    b = fbm(n, 1.8, 712)
    col = mix(C(0.6, 0.53, 0.41), C(0.8, 0.73, 0.6), np.clip((a - 0.5) * 3 + 0.5, 0, 1))
    col *= (0.9 + 0.15 * b)[..., None]
    save(name, col)


def bark(name, base, fiss, seed=721):
    n = 512
    f = fbm(n, 2.2, seed, aniso=(1.0, 8.0))
    ridges = np.clip((np.abs(np.sin(2 * np.pi * (fbm(n, 2.6, seed + 1, aniso=(1.0, 5.0)) * 6))) - 0.15) * 3, 0, 1)
    col = mix(fiss, base, ridges) * (0.85 + 0.25 * f)[..., None]
    save(name, col)


def foliage(name, dark, light, seed, n=512, leaf=(10, 4), count=2600):
    """Dense tileable foliage (cypress, hedges, bush blobs): many small leaves over a dark base."""
    rng = np.random.default_rng(seed)
    s = 2
    img = Image.new("RGB", (n * s, n * s), tuple(int(c * 255) for c in dark))
    d = ImageDraw.Draw(img)
    for _ in range(count):
        cx, cy = rng.uniform(0, n * s), rng.uniform(0, n * s)
        L, W = rng.uniform(0.7, 1.3) * leaf[0] * s, rng.uniform(0.7, 1.3) * leaf[1] * s
        a = rng.uniform(0, math.pi)
        t = rng.uniform(0, 1)
        c = tuple(int(255 * (dark[k] * (1 - t) + light[k] * t)) for k in range(3))
        pts = [(L * math.cos(q), W * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 9)]
        for ox in (-n * s, 0, n * s):
            for oy in (-n * s, 0, n * s):
                d.polygon([(cx + ox + px * math.cos(a) - py * math.sin(a), cy + oy + px * math.sin(a) + py * math.cos(a)) for px, py in pts], fill=c)
    arr = np.asarray(img.resize((n, n), Image.LANCZOS)).astype(float) / 255
    arr *= (0.8 + 0.3 * fbm(n, 2.0, seed + 1))[..., None]
    save(name, arr)


# ---------------------------------------------------------------- leaf cards (RGBA cut-outs)
def card(name, leaves, extras=(), seed=0, n=512, holes=0.0, shape="round"):
    """Leaf-cluster card. leaves: (count, length px, width px, [colours]); extras: callables(draw, rng, s)."""
    rng = np.random.default_rng(seed)
    s = 2
    img = Image.new("RGBA", (n * s, n * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cnt, L0, W0, cols = leaves
    for _ in range(cnt):
        if shape == "round":
            rr = math.sqrt(rng.uniform(0, 1)) * 0.46 * n * s
            q = rng.uniform(0, 2 * math.pi)
            cx, cy = n * s / 2 + rr * math.cos(q), n * s / 2 + rr * math.sin(q) * 0.92
        else:                                        # 'spike': lavender-like clump growing from the bottom
            cx, cy = rng.uniform(0.15, 0.85) * n * s, rng.uniform(0.25, 0.98) * n * s
        L, W = rng.uniform(0.7, 1.3) * L0 * s, rng.uniform(0.7, 1.3) * W0 * s
        a = rng.uniform(0, 2 * math.pi) if shape == "round" else rng.uniform(-0.3, 0.3) + math.pi / 2
        c = cols[rng.integers(len(cols))]
        sh = rng.uniform(0.8, 1.15)
        fill = tuple(int(min(1, c[k] * sh) * 255) for k in range(3)) + (255,)
        pts = [(L * math.cos(t), W * math.sin(t) * (1 - 0.25 * math.cos(t))) for t in np.linspace(0, 2 * math.pi, 12)]
        d.polygon([(cx + px * math.cos(a) - py * math.sin(a), cy + px * math.sin(a) + py * math.cos(a)) for px, py in pts], fill=fill)
        mid = tuple(int(min(1, c[k] * sh * 1.25) * 255) for k in range(3)) + (255,)
        d.line([(cx - L * 0.8 * math.cos(a), cy - L * 0.8 * math.sin(a)), (cx + L * 0.8 * math.cos(a), cy + L * 0.8 * math.sin(a))], fill=mid, width=max(1, s))
    for fn in extras:
        fn(d, rng, s, n)
    arr = np.asarray(img.resize((n, n), Image.LANCZOS)).astype(float) / 255
    a = arr[..., 3]
    arr[..., 3] = np.clip((a - 0.25) * 2.0, 0, 1)
    save_png(name, arr)


def bracts(count, cols, size=9):
    def fn(d, rng, s, n):
        for _ in range(count):
            rr = math.sqrt(rng.uniform(0, 1)) * 0.44 * n * s
            q = rng.uniform(0, 2 * math.pi)
            cx, cy = n * s / 2 + rr * math.cos(q), n * s / 2 + rr * math.sin(q) * 0.9
            c = cols[rng.integers(len(cols))]
            for k in range(3):
                a = rng.uniform(0, 0.5) + k * 2 * math.pi / 3
                L, W = size * s * rng.uniform(0.9, 1.3), size * 0.75 * s
                bx, by = cx + L * 0.6 * math.cos(a), cy + L * 0.6 * math.sin(a)
                pts = [(L * 0.65 * math.cos(t), W * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 10)]
                sh = rng.uniform(0.85, 1.12)
                d.polygon([(bx + px * math.cos(a) - py * math.sin(a), by + px * math.sin(a) + py * math.cos(a)) for px, py in pts],
                          fill=tuple(int(min(1, c[j] * sh) * 255) for j in range(3)) + (255,))
            d.ellipse([cx - 1.5 * s, cy - 1.5 * s, cx + 1.5 * s, cy + 1.5 * s], fill=(240, 230, 200, 255))
    return fn


def fruits(count, col, r=13):
    def fn(d, rng, s, n):
        for _ in range(count):
            rr = math.sqrt(rng.uniform(0, 1)) * 0.38 * n * s
            q = rng.uniform(0, 2 * math.pi)
            cx, cy = n * s / 2 + rr * math.cos(q), n * s / 2 + rr * math.sin(q)
            rx, ry = r * s * 1.2, r * s
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=tuple(int(c * 255) for c in col) + (255,))
            d.ellipse([cx - rx * 0.5, cy - ry * 0.7, cx + rx * 0.1, cy - ry * 0.1], fill=tuple(int(min(1, c * 1.25) * 255) for c in col) + (255,))
    return fn


def blooms(count, col, r=10):
    def fn(d, rng, s, n):
        for _ in range(count):
            rr = math.sqrt(rng.uniform(0, 1)) * 0.4 * n * s
            q = rng.uniform(0, 2 * math.pi)
            cx, cy = n * s / 2 + rr * math.cos(q), n * s / 2 + rr * math.sin(q) * 0.8 - 0.06 * n * s
            for _k in range(9):
                fx, fy = cx + rng.normal(0, r * s * 0.7), cy + rng.normal(0, r * s * 0.7)
                pr = r * s * 0.45
                sh = rng.uniform(0.85, 1.15)
                d.ellipse([fx - pr, fy - pr, fx + pr, fy + pr], fill=tuple(int(min(1, c * sh) * 255) for c in col) + (255,))
    return fn


def spikes(count, col):
    def fn(d, rng, s, n):
        for _ in range(count):
            bx = rng.uniform(0.12, 0.88) * n * s
            top = rng.uniform(0.05, 0.35) * n * s
            d.line([(bx, n * s), (bx + rng.uniform(-30, 30) * s, top)], fill=(96, 112, 80, 255), width=2 * s)
            for k in range(14):
                yy = top + k * 4.5 * s
                sh = rng.uniform(0.85, 1.15)
                d.ellipse([bx - 4 * s, yy - 3 * s, bx + 4 * s, yy + 3 * s], fill=tuple(int(min(1, c * sh) * 255) for c in col) + (255,))
    return fn


# ---------------------------------------------------------------- paintings
def landscape(name):
    """Oil-sketch of an Andalusian landscape: white village, olive rows, cypresses (UV 'fit' on frames)."""
    w, h = 1024, 768
    x, y = grid(w, h)
    col = mix(C(0.5, 0.66, 0.86), C(0.96, 0.86, 0.7), np.clip(y / 0.48, 0, 1) ** 1.4)
    far = 0.42 + 0.04 * np.sin(x * 7 + 1) + 0.03 * np.sin(x * 17)
    col[y > far] = C(0.56, 0.58, 0.72)
    mid = 0.53 + 0.06 * np.sin(x * 4 + 2) + 0.02 * np.sin(x * 23)
    col[y > mid] = C(0.6, 0.6, 0.36)
    near = 0.72 + 0.05 * np.sin(x * 3 + 0.5)
    col[y > near] = C(0.8, 0.64, 0.3)
    rows = (y > mid + 0.02) & (y < near) & (np.abs(np.sin(y * 160)) > 0.55) & (np.abs(np.sin(x * 120 + y * 30)) > 0.6)
    col[rows] = C(0.32, 0.36, 0.2)
    for i in range(14):                                # white village on the hill
        bx, by = 0.6 + (i % 5) * 0.035 + (i // 5) * 0.012, 0.5 + (i // 5) * 0.03 - (i % 3) * 0.008
        m = (np.abs(x - bx) < 0.016) & (y > by) & (y < by + 0.035)
        col[m] = C(0.96, 0.94, 0.88)
        col[(np.abs(x - bx) < 0.017) & (y > by - 0.008) & (y < by + 0.002)] = C(0.72, 0.36, 0.2)
    for bx, sc in ((0.12, 1.0), (0.17, 0.8), (0.86, 0.9)):
        m = ((x - bx) / (0.022 * sc)) ** 2 + ((y - (0.58 - 0.0)) / (0.2 * sc)) ** 2 < 1
        col[m & (y < 0.8)] = C(0.12, 0.22, 0.12)
    col = gaussian_filter(col, (1.2, 1.2, 0))
    stroke = fbm(w if w == h else 1024, 2.0, 801, aniso=(1.0, 3.0))[:h, :w]
    col *= (0.9 + 0.18 * stroke)[..., None]
    canvas = 0.95 + 0.05 * np.sin(x * 900) * np.sin(y * 700)
    save(name, col * canvas[..., None])


def lemons(name):
    """Still life: blue-and-white bowl of lemons on a dark ground."""
    w, h = 1024, 768
    x, y = grid(w, h)
    col = mix(C(0.16, 0.11, 0.07), C(0.3, 0.2, 0.12), fbm(1024, 2.6, 811)[:h, :w])
    col[y > 0.68] = C(0.42, 0.26, 0.14)
    bowl = ((x - 0.47) / 0.27) ** 2 + ((y - 0.62) / 0.14) ** 2 < 1
    col[bowl & (y > 0.6)] = C(0.9, 0.9, 0.86)
    col[bowl & (y > 0.6) & (np.abs(np.sin(x * 70)) > 0.85)] = C(0.12, 0.2, 0.5)
    for cx, cy in ((0.37, 0.56), (0.47, 0.53), (0.57, 0.56), (0.43, 0.47), (0.52, 0.46), (0.73, 0.68)):
        m = ((x - cx) / 0.06) ** 2 + ((y - cy) / 0.045) ** 2 < 1
        col[m] = C(0.92, 0.76, 0.18)
        col[m & (((x - cx + 0.02) / 0.03) ** 2 + ((y - cy + 0.015) / 0.015) ** 2 < 1)] = C(1.0, 0.92, 0.5)
    for cx, cy, a in ((0.33, 0.47, 0.6), (0.6, 0.44, -0.5)):
        m = (((x - cx) * math.cos(a) + (y - cy) * math.sin(a)) / 0.07) ** 2 + ((-(x - cx) * math.sin(a) + (y - cy) * math.cos(a)) / 0.02) ** 2 < 1
        col[m] = C(0.2, 0.36, 0.16)
    jug = ((x - 0.8) / 0.08) ** 2 + ((y - 0.5) / 0.17) ** 2 < 1
    col[jug & (y < 0.66)] = C(0.66, 0.34, 0.18)
    col = gaussian_filter(col, (1.4, 1.4, 0))
    col *= (0.92 + 0.14 * fbm(1024, 1.8, 812)[:h, :w])[..., None]
    save(name, col)


JOBS = {
    "s_azulejo": lambda: azulejo("s_azulejo", 0),
    "s_azulejo2": lambda: azulejo("s_azulejo2", 1),
    "s_azulejo_border": lambda: azulejo_border("s_azulejo_border"),
    "s_terracotta": lambda: terracotta("s_terracotta"),
    "s_stucco": lambda: limewash("s_stucco"),
    "s_roof_barrel": lambda: roof_barrel("s_roof_barrel"),
    "s_beam": lambda: beam("s_beam"),
    "s_door_planks": lambda: door_planks("s_door_planks"),
    "s_oak": lambda: oak("s_oak"),
    "s_leather": lambda: leather("s_leather"),
    "s_kilim": lambda: kilim("s_kilim", C(0.56, 0.12, 0.08), C(0.12, 0.17, 0.34), C(0.17, 0.09, 0.06), C(0.8, 0.56, 0.2), C(0.87, 0.8, 0.65), C(0.17, 0.09, 0.06)),
    "s_kilim2": lambda: kilim("s_kilim2", C(0.15, 0.2, 0.33), C(0.6, 0.24, 0.12), C(0.85, 0.78, 0.62), C(0.74, 0.5, 0.2), C(0.88, 0.82, 0.68), C(0.12, 0.1, 0.12), seed=5),
    "s_jute": lambda: jute("s_jute"),
    "s_linen": lambda: linen("s_linen"),
    "s_stripe": lambda: stripe("s_stripe"),
    "s_cobble": lambda: cobble("s_cobble"),
    "s_gravel": lambda: gravel("s_gravel"),
    "s_bark": lambda: bark("s_bark", C(0.46, 0.43, 0.38), C(0.18, 0.15, 0.12)),
    "s_cypress": lambda: foliage("s_cypress", C(0.06, 0.13, 0.06), C(0.2, 0.33, 0.14), 731, leaf=(7, 3), count=5200),
    "s_hedge": lambda: foliage("s_hedge", C(0.08, 0.16, 0.06), C(0.3, 0.46, 0.16), 741, leaf=(9, 4.5), count=3200),
    "s_leafcard": lambda: card("s_leafcard", (420, 16, 7, [C(0.16, 0.32, 0.1), C(0.24, 0.43, 0.14), C(0.12, 0.25, 0.08), C(0.3, 0.48, 0.18)]), seed=751),
    "s_bougain": lambda: card("s_bougain", (300, 14, 7, [C(0.14, 0.32, 0.1), C(0.22, 0.42, 0.13), C(0.11, 0.25, 0.08)]),
                              (bracts(150, [C(0.82, 0.1, 0.47), C(0.9, 0.2, 0.58), C(0.7, 0.06, 0.38)], 10),), seed=761),
    "s_olivecard": lambda: card("s_olivecard", (520, 18, 3.5, [C(0.42, 0.48, 0.34), C(0.56, 0.62, 0.48), C(0.34, 0.4, 0.27), C(0.62, 0.66, 0.55)]), seed=771),
    "s_lemoncard": lambda: card("s_lemoncard", (380, 15, 7, [C(0.1, 0.26, 0.08), C(0.17, 0.36, 0.11), C(0.08, 0.2, 0.06)]), (fruits(12, C(0.95, 0.8, 0.15)),), seed=781),
    "s_geranium": lambda: card("s_geranium", (260, 12, 10, [C(0.18, 0.38, 0.12), C(0.24, 0.46, 0.16)]), (blooms(16, C(0.86, 0.1, 0.1), 11),), seed=791),
    "s_lavender": lambda: card("s_lavender", (160, 16, 2.5, [C(0.42, 0.5, 0.38), C(0.52, 0.58, 0.46)]), (spikes(46, C(0.52, 0.4, 0.72)),), seed=801, shape="spike"),
    "s_art_landscape": lambda: landscape("s_art_landscape"),
    "s_art_lemons": lambda: lemons("s_art_lemons"),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    for nm in names:
        JOBS[nm]()
        print("made", nm)
