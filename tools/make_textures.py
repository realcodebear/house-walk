"""Procedural, tileable textures for the v2 houses -> blender/tex/*.jpg (+ *_n.jpg normal maps, *.png with alpha).

    python3 tools/make_textures.py            # all
    python3 tools/make_textures.py marble_white carpet_kashmir
Everything is generated from noise and simple geometry, so the repo carries no third-party images.
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "blender", "tex")
rng = np.random.default_rng(7)


# ---------------------------------------------------------------- helpers
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


def grid(n):
    y, x = np.mgrid[0:n, 0:n] / n
    return x, y


def save(name, rgb, q=88):
    os.makedirs(OUT, exist_ok=True)
    img = Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8))
    img.save(os.path.join(OUT, name + ".jpg"), quality=q)


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


def tiles_mask(n, count, grout):
    """1 inside tiles, 0 in the grout lines; `count` tiles per side."""
    x, y = grid(n)
    gx = np.abs(((x * count) % 1) - 0.5) * 2
    gy = np.abs(((y * count) % 1) - 0.5) * 2
    g = grout * count * 2
    return np.clip((1 - gx) / g, 0, 1) * np.clip((1 - gy) / g, 0, 1)


# ---------------------------------------------------------------- textures
def marble(name, base, vein, veins=2, turb=1.6, seed=1, tiles=2, grout_col=(0.82, 0.8, 0.77)):
    n = 1024
    x, y = grid(n)
    t = fbm(n, 3.9, seed)                      # smooth turbulence -> flowing veins
    t2 = fbm(n, 3.6, seed + 5)
    val = np.abs(np.sin(2 * np.pi * (x * veins + y * 1 + t * turb)))
    v = (1 - val) ** 2.5 * 0.3 + (1 - val) ** 14 * 0.6
    val2 = np.abs(np.sin(2 * np.pi * (x * 1 - y * 2 + t2 * 2.5)))
    v += (1 - val2) ** 22 * 0.35
    v = gaussian_filter(v, 1.2, mode="wrap")
    cloud = fbm(n, 3.0, seed + 9)
    col = mix(base, np.array(base) * 0.95, cloud)
    col = mix(col, vein, np.clip(v, 0, 1))
    tx, ty = (x * tiles).astype(int), (y * tiles).astype(int)
    col *= (1 + np.sin(tx * 12.9 + ty * 78.2) * 0.02)[..., None]
    m = tiles_mask(n, tiles, 0.0022)
    col = mix(np.array(grout_col), col, m)
    save(name, col)
    save_normal(name, m * 0.6, 1.5, 512)


def wood(name, light, dark, rings=7, seed=3, n=1024):
    x, y = grid(n)
    t = fbm(n, 3.0, seed, aniso=(1.0, 10.0))   # long, smooth figure along v (slow change in y)
    g = 0.5 + 0.5 * np.sin(2 * np.pi * (x * rings + t * 2.2))
    pores = fbm(n, 1.1, seed + 1, aniso=(1.0, 30.0))
    col = mix(light, dark, np.clip(g ** 1.8 * 0.8 + pores * 0.18, 0, 1))
    save(name, col)
    return col


def planks(name, light, dark, rows=8, seed=4):
    """Floor boards running along v; `rows` boards across the texture, staggered end joints."""
    n = 1024
    x, y = grid(n)
    base = wood("_tmp", light, dark, rings=14, seed=seed)
    row = (x * rows).astype(int)
    offs = (np.sin(row * 91.7) * 0.5 + 0.5)
    seg = ((y + offs) * 2) % 1
    tint = 1 + np.sin(row * 17.3 + ((y + offs) * 2).astype(int) * 5.1) * 0.07
    col = base * tint[..., None]
    gap = np.minimum(np.abs((x * rows) % 1), np.abs(1 - (x * rows) % 1)) < 0.012
    joint = np.minimum(seg, 1 - seg) < 0.004
    line = gap | joint
    col[line] *= 0.45
    save(name, col)
    save_normal(name, 1 - line.astype(float), 1.2, 512)
    os.remove(os.path.join(OUT, "_tmp.jpg"))


def mdf_panel(name, light, dark, grooves=4, seed=6):
    n = 1024
    x, y = grid(n)
    col = wood("_tmp", light, dark, rings=22, seed=seed)
    d = np.minimum((x * grooves) % 1, 1 - (x * grooves) % 1)
    h = np.clip(d / 0.012, 0, 1)
    col *= (0.35 + 0.65 * h)[..., None]
    save(name, col)
    save_normal(name, h, 2.5, 512)
    os.remove(os.path.join(OUT, "_tmp.jpg"))


def khatamband(name):
    """Kashmiri walnut ceiling: interlocking hexagon-and-star strips (one repeat = 1024 px)."""
    n = 1024
    walnut = wood("_tmp", (0.36, 0.22, 0.12), (0.16, 0.09, 0.05), rings=18, seed=11)
    img = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(img)
    s = n / 4                                   # hexagon spacing
    hx = s * math.sqrt(3) / 2
    for i in range(-1, 6):
        for j in range(-1, 6):
            cx = i * 2 * hx * 0.5 * 2 / 1.0 * 0.5 + (j % 2) * hx * 0.5 + i * hx * 0.5
            cx = i * hx + (j % 2) * hx / 2
            cy = j * s * 0.75
            pts = [(cx + s / 2 * math.cos(math.pi / 6 + k * math.pi / 3), cy + s / 2 * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(7)]
            d.line(pts, fill=255, width=9)
            star = []
            for k in range(13):
                r = s * (0.32 if k % 2 == 0 else 0.16)
                a = k * math.pi / 6
                star.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            d.line(star, fill=255, width=6)
    # make it tile: the pattern above repeats every 4 hexes horizontally / 4 rows vertically only roughly,
    # so mirror-wrap the strip mask through a blur to hide the seam
    m = np.asarray(img.filter(ImageFilter.GaussianBlur(1.2))).astype(float) / 255
    m = np.maximum(m, m[:, ::-1] * 0)            # keep as drawn
    strip = mix(walnut * 0.55, np.array([0.55, 0.38, 0.22]) * (0.85 + 0.3 * fbm(n, 1.5, 12))[..., None], m)
    save(name, strip)
    save_normal(name, m, 3.0, 512)
    os.remove(os.path.join(OUT, "_tmp.jpg"))


def carpet_kashmir(name):
    """A whole rug (not tiled): border bands, field of small flowers, central medallion, corner pieces."""
    n = 1024
    x, y = grid(n)
    u, v = x - 0.5, y - 0.5
    red, navy, ivory, gold, green = (np.array(c) for c in [(0.5, 0.07, 0.07), (0.07, 0.1, 0.26), (0.86, 0.8, 0.66), (0.78, 0.58, 0.24), (0.15, 0.32, 0.22)])
    col = np.zeros((n, n, 3)) + red
    # field: small rosettes on a lattice
    fx, fy = (x * 14) % 1 - 0.5, (y * 14) % 1 - 0.5
    rr, th = np.hypot(fx, fy), np.arctan2(fy, fx)
    petal = rr < 0.18 + 0.1 * np.cos(6 * th)
    col[petal] = gold * 0.9
    col[rr < 0.07] = ivory
    # lattice vines
    vine = (np.abs(np.sin(np.pi * (x * 14 + y * 14))) < 0.06) | (np.abs(np.sin(np.pi * (x * 14 - y * 14))) < 0.06)
    col[vine & ~petal] = green
    # medallion
    r, t = np.hypot(u / 0.6, v / 0.75), np.arctan2(v, u)
    med = r < 0.42 + 0.06 * np.cos(16 * t)
    col[med] = navy
    ring = med & (r > 0.36 + 0.05 * np.cos(16 * t))
    col[ring] = ivory
    inner = r < 0.22 + 0.05 * np.cos(8 * t)
    col[inner] = red
    col[(r < 0.3) & (r > 0.27)] = gold
    pet2 = (r < 0.2) & (np.cos(8 * t) > 0.3)
    col[pet2] = ivory * 0.95
    # corners
    for cx, cy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        rc = np.hypot((x - cx) / 0.9, (y - cy) / 1.1)
        cm = rc < 0.33 + 0.03 * np.cos(20 * np.arctan2(y - cy, x - cx))
        col[cm] = navy
        col[cm & (rc > 0.29)] = ivory
    # borders
    e = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    band = (e < 0.1)
    col[band] = navy
    motif = band & (np.cos(2 * np.pi * (x + y) * 24) * np.cos(2 * np.pi * (x - y) * 24) > 0.25)
    col[motif] = red
    col[(e > 0.1) & (e < 0.115)] = ivory
    col[(e > 0.03) & (e < 0.04)] = gold
    col[e < 0.012] = ivory * 0.8                      # fringe edge
    wool = 0.88 + 0.24 * fbm(n, 0.8, 21)
    col = col * wool[..., None]
    save(name, col)


def carpet_plain(name, c1, c2, stripes=0):
    n = 512
    x, y = grid(n)
    w = 0.85 + 0.3 * fbm(n, 0.7, 31)
    col = mix(c1, c2, (np.sin(2 * np.pi * y * stripes) * 0.5 + 0.5) if stripes else fbm(n, 2.5, 33) * 0.5)
    e = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    col[(e > 0.04) & (e < 0.06)] *= 0.75
    save(name, col * w[..., None])


def lattice(name):
    """Pinjrakari window screen: walnut lattice with see-through gaps (RGBA png)."""
    n = 512
    img = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(img)
    k = 8
    s = n / k
    for i in range(-1, k + 2):
        d.line([(i * s, 0), (i * s + n, n)], fill=255, width=10)
        d.line([(i * s, 0), (i * s - n, n)], fill=255, width=10)
        d.line([(i * s, 0), (i * s, n)], fill=255, width=6)
    for i in range(k + 1):
        for j in range(k + 1):
            d.ellipse([i * s - 14, j * s - 14, i * s + 14, j * s + 14], outline=255, width=6)
    a = np.asarray(img).astype(float) / 255
    walnut = wood("_tmp", (0.40, 0.25, 0.13), (0.18, 0.10, 0.05), rings=10, seed=14, n=n)
    rgba = np.dstack([np.clip(walnut * 255, 0, 255), (a * 255)]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, name + ".png"))
    os.remove(os.path.join(OUT, "_tmp.jpg"))


def roof_cgi(name, paint):
    n = 512
    x, y = grid(n)
    corr = 0.5 + 0.5 * np.sin(2 * np.pi * x * 8)
    dirt = fbm(n, 2.2, 41, aniso=(1.0, 5.0))
    col = np.array(paint) * (0.72 + 0.4 * corr)[..., None] * (0.9 + 0.15 * dirt)[..., None]
    lap = ((y * 2) % 1) < 0.015
    col[lap] *= 0.6
    save(name, col)
    save_normal(name, corr * 0.8, 2.0)


def roof_terracotta(name):
    n = 512
    x, y = grid(n)
    cols, rows = 6, 5
    cx = (x * cols) % 1
    ry = (y * rows) % 1
    arch = np.sin(np.pi * cx) ** 0.6
    ri = (y * rows).astype(int)
    ci = (x * cols).astype(int)
    tint = 1 + np.sin(ci * 37.1 + ri * 11.3) * 0.08
    shade = arch * (0.75 + 0.25 * ry)
    base = np.array([0.66, 0.30, 0.16])
    col = base * (0.55 + 0.6 * shade)[..., None] * tint[..., None] * (0.9 + 0.2 * fbm(n, 1.8, 43))[..., None]
    col[ry > 0.93] *= 0.45
    save(name, col)
    save_normal(name, arch * 0.7 + ry * 0.3, 2.5)


def terracotta_floor(name):
    n = 1024
    x, y = grid(n)
    count = 3
    m = tiles_mask(n, count, 0.004)
    ti = (x * count).astype(int) * 7 + (y * count).astype(int) * 3
    tint = 1 + np.sin(ti * 12.7) * 0.09
    blot = fbm(n, 2.3, 51)
    col = mix([0.62, 0.32, 0.18], [0.74, 0.42, 0.25], blot) * tint[..., None]
    col = mix(np.array([0.78, 0.74, 0.66]), col, m)
    save(name, col)
    save_normal(name, m, 2.0, 512)


def brick(name):
    n = 1024
    x, y = grid(n)
    rows, per = 16, 4
    ri = (y * rows).astype(int)
    off = (ri % 2) * 0.5
    bx = (x * per + off) % 1
    by = (y * rows) % 1
    bi = ((x * per + off).astype(int) * 13 + ri * 7)
    tint = 1 + np.sin(bi * 9.13) * 0.12
    mortar = (bx < 0.035) | (by < 0.09)
    col = mix([0.55, 0.25, 0.17], [0.68, 0.36, 0.24], fbm(n, 2.0, 61)) * tint[..., None]
    col[mortar] = [0.72, 0.69, 0.62]
    save(name, col)
    save_normal(name, 1 - mortar.astype(float), 2.0, 512)


def stone_clad(name):
    n = 1024
    img = Image.new("RGB", (n, n))
    hmap = Image.new("L", (n, n), 0)
    d, dh = ImageDraw.Draw(img), ImageDraw.Draw(hmap)
    r = np.random.default_rng(71)
    y = 0
    while y < n:
        h = int(r.integers(50, 110))
        x = -int(r.integers(0, 120))
        while x < n:
            w = int(r.integers(90, 260))
            c = np.array([0.6, 0.57, 0.52]) * r.uniform(0.78, 1.12) + r.uniform(-0.015, 0.015, 3)
            for dx in (-n, 0, n):                     # wrap horizontally
                d.rectangle([x + dx + 3, y + 3, x + dx + w - 3, y + h - 3], fill=tuple(int(v * 255) for v in np.clip(c, 0, 1)))
                dh.rectangle([x + dx + 3, y + 3, x + dx + w - 3, y + h - 3], fill=255)
            x += w
        y += h
    col = np.asarray(img).astype(float) / 255
    col *= (0.85 + 0.3 * fbm(n, 1.4, 72))[..., None]
    save(name, col)
    save_normal(name, np.asarray(hmap.filter(ImageFilter.GaussianBlur(2))).astype(float) / 255, 3.0, 512)


def plaster(name, color, rough=0.12, seed=81, n=512):
    a = fbm(n, 2.4, seed) * 0.6 + fbm(n, 1.0, seed + 1) * 0.4
    col = np.array(color) * (1 - rough + rough * 2 * a)[..., None]
    save(name, col)
    save_normal(name, a, 1.2 + rough * 6)


def fabric(name, n=512):
    x, y = grid(n)
    weave = 0.5 + 0.25 * np.sin(2 * np.pi * x * 96) + 0.25 * np.sin(2 * np.pi * y * 96)
    col = np.dstack([0.78 + 0.18 * weave + 0.05 * fbm(n, 1.5, 91)] * 3)
    save(name, np.clip(col, 0, 1))


def grass(name):
    n = 512
    a = fbm(n, 1.6, 101)
    b = fbm(n, 0.9, 102)
    col = mix([0.16, 0.30, 0.10], [0.30, 0.44, 0.16], a * 0.7 + b * 0.3)
    save(name, col)


def paving(name):
    n = 512
    x, y = grid(n)
    m = tiles_mask(n, 4, 0.006)
    ti = (x * 4).astype(int) * 5 + (y * 4).astype(int)
    col = np.array([0.58, 0.55, 0.5]) * (1 + np.sin(ti * 3.3) * 0.06)[..., None] * (0.9 + 0.2 * fbm(n, 1.5, 111))[..., None]
    col = mix(np.array([0.35, 0.33, 0.3]), col, m)
    save(name, col)
    save_normal(name, m, 1.5)


def subway(name):
    n = 512
    x, y = grid(n)
    rows, per = 12, 6
    ri = (y * rows).astype(int)
    bx = (x * per + (ri % 2) * 0.5) % 1
    by = (y * rows) % 1
    grout = (bx < 0.02) | (by < 0.05)
    col = np.zeros((n, n, 3)) + 0.93
    col[grout] = 0.7
    save(name, col)
    save_normal(name, 1 - grout.astype(float), 1.5)


def porcelain(name, color):
    n = 512
    x, y = grid(n)
    m = tiles_mask(n, 2, 0.004)
    col = np.array(color) * (0.95 + 0.1 * fbm(n, 2.4, 121))[..., None]
    col = mix(np.array(color) * 0.75, col, m)
    save(name, col)
    save_normal(name, m, 1.5)


def crewel(name):
    """Kashmiri crewel embroidery on cream cloth (curtains, cushions)."""
    n = 512
    x, y = grid(n)
    col = np.zeros((n, n, 3)) + [0.88, 0.83, 0.72]
    fx, fy = (x * 4 + (np.floor(y * 4) % 2) * 0.5) % 1 - 0.5, (y * 4) % 1 - 0.5
    rr, th = np.hypot(fx, fy), np.arctan2(fy, fx)
    petals = rr < 0.2 + 0.12 * np.cos(5 * th)
    col[petals] = [0.62, 0.12, 0.12]
    col[rr < 0.07] = [0.86, 0.62, 0.2]
    stem = (np.abs(fx + 0.25 * np.sin(fy * 9)) < 0.015) & (fy > 0.1)
    col[stem] = [0.2, 0.38, 0.22]
    leaf = (np.hypot(fx - 0.18, fy - 0.3) < 0.08)
    col[leaf] = [0.25, 0.45, 0.25]
    col *= (0.92 + 0.12 * fbm(n, 0.6, 131))[..., None]
    save(name, col)


def papier_mache(name):
    """Kashmiri papier-mâché: gold flowers and vines on deep blue lacquer."""
    n = 512
    x, y = grid(n)
    col = np.zeros((n, n, 3)) + [0.08, 0.12, 0.3]
    fx, fy = (x * 6) % 1 - 0.5, (y * 6) % 1 - 0.5
    rr, th = np.hypot(fx, fy), np.arctan2(fy, fx)
    col[rr < 0.22 + 0.1 * np.cos(8 * th)] = [0.8, 0.6, 0.25]
    col[rr < 0.1] = [0.7, 0.15, 0.12]
    col[(np.abs(np.sin(np.pi * (x * 6 + y * 6))) < 0.05)] = [0.75, 0.55, 0.22]
    save(name, col)


JOBS = {
    "marble_white": lambda: marble("marble_white", (0.93, 0.92, 0.9), (0.55, 0.56, 0.58), seed=1),
    "marble_diana": lambda: marble("marble_diana", (0.86, 0.76, 0.6), (0.62, 0.48, 0.32), veins=2, turb=2.0, seed=2, grout_col=(0.75, 0.68, 0.56)),
    "marble_black": lambda: marble("marble_black", (0.12, 0.12, 0.13), (0.7, 0.7, 0.7), veins=4, seed=5, tiles=1, grout_col=(0.2, 0.2, 0.2)),
    "walnut": lambda: wood("walnut", (0.38, 0.23, 0.13), (0.16, 0.09, 0.05)),
    "teak": lambda: wood("teak", (0.62, 0.40, 0.20), (0.38, 0.22, 0.10), seed=8),
    "oak_planks": lambda: planks("oak_planks", (0.72, 0.55, 0.36), (0.50, 0.34, 0.19)),
    "walnut_planks": lambda: planks("walnut_planks", (0.42, 0.27, 0.15), (0.22, 0.13, 0.07), seed=9),
    "mdf_walnut": lambda: mdf_panel("mdf_walnut", (0.45, 0.29, 0.16), (0.25, 0.15, 0.08)),
    "mdf_oak": lambda: mdf_panel("mdf_oak", (0.74, 0.58, 0.40), (0.55, 0.40, 0.25), seed=7),
    "khatamband": khatamband,
    "carpet_kashmir": carpet_kashmir,
    "carpet_beige": lambda: carpet_plain("carpet_beige", (0.78, 0.7, 0.58), (0.66, 0.58, 0.47)),
    "carpet_stripe": lambda: carpet_plain("carpet_stripe", (0.32, 0.36, 0.42), (0.55, 0.52, 0.46), stripes=7),
    "lattice": lattice,
    "roof_green": lambda: roof_cgi("roof_green", (0.16, 0.34, 0.22)),
    "roof_tile": roof_terracotta,
    "terracotta": terracotta_floor,
    "brick": brick,
    "stone": stone_clad,
    "plaster": lambda: plaster("plaster", (0.95, 0.93, 0.89)),
    "stucco": lambda: plaster("stucco", (0.96, 0.94, 0.88), rough=0.28, seed=85),
    "fabric": fabric,
    "grass": grass,
    "paving": paving,
    "subway": subway,
    "porcelain": lambda: porcelain("porcelain", (0.8, 0.8, 0.79)),
    "crewel": crewel,
    "papier": papier_mache,
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    for nm in names:
        fn = JOBS[nm]
        fn() if fn.__name__ == "<lambda>" else fn(nm)
        print("made", nm)
