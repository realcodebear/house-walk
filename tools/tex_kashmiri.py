"""Extra procedural textures for the Kashmiri design -> blender/tex/k_*.jpg / k_*.png (+ k_*_n.jpg normal maps).

    python3 tools/tex_kashmiri.py            # all
    python3 tools/tex_kashmiri.py k_barge k_jaali
Same rules as tools/make_textures.py: everything is drawn from noise and geometry (no third-party images).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "blender", "tex")


# ---------------------------------------------------------------- helpers (same as make_textures.py)
def fbm(n, beta=2.0, seed=0, aniso=(1.0, 1.0), m=None):
    """Periodic 1/f^beta noise in [0, 1], n rows x m columns (tileable)."""
    m = m or n
    r = np.random.default_rng(seed)
    fx = np.fft.fftfreq(m)[None, :] * aniso[0] * (m / n)
    fy = np.fft.fftfreq(n)[:, None] * aniso[1]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    spec = (r.normal(size=(n, m)) + 1j * r.normal(size=(n, m))) / f ** (beta / 2)
    spec[0, 0] = 0
    a = np.real(np.fft.ifft2(spec))
    a -= a.min()
    return a / a.max()


def grid(n, m=None):
    m = m or n
    y, x = np.mgrid[0:n, 0:m]
    return x / m, y / n


def mix(a, b, t):
    t = t[..., None] if np.ndim(t) == 2 else t
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def save(name, rgb, q=88):
    Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name + ".jpg"), quality=q)


def save_rgba(name, rgb, alpha):
    a = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    img = np.dstack([np.clip(rgb * 255, 0, 255).astype(np.uint8), a])
    Image.fromarray(img, "RGBA").save(os.path.join(OUT, name + ".png"), optimize=True)


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


def wood(light, dark, n=1024, m=None, rings=7, seed=3, along="v"):
    """Wood grain; along='v' runs the grain down the image (columns), 'u' across it (rows)."""
    m = m or n
    x, y = grid(n, m)
    if along == "u":
        t = fbm(n, 3.0, seed, aniso=(10.0, 1.0), m=m)
        g = 0.5 + 0.5 * np.sin(2 * np.pi * (y * rings + t * 2.2))
        pores = fbm(n, 1.1, seed + 1, aniso=(30.0, 1.0), m=m)
    else:
        t = fbm(n, 3.0, seed, aniso=(1.0, 10.0), m=m)
        g = 0.5 + 0.5 * np.sin(2 * np.pi * (x * rings + t * 2.2))
        pores = fbm(n, 1.1, seed + 1, aniso=(1.0, 30.0), m=m)
    return mix(light, dark, np.clip(g ** 1.8 * 0.8 + pores * 0.18, 0, 1))


def wrap_draw(draw, fn, size):
    """Call fn(dx, dy) for the 9 wrap offsets so shapes drawn across an edge tile seamlessly."""
    W, H = size
    for dx in (-W, 0, W):
        for dy in (-H, 0, H):
            fn(dx, dy)


# ---------------------------------------------------------------- textures
def k_barge():
    """Carved walnut bargeboard strip (RGBA, u = along the board): solid top band with grooves and rosettes,
    scalloped kanjdar lower edge with teardrop pendants, see-through below the scallops."""
    W, H = 1024, 256
    ss = 2                                          # supersample for smooth edges
    m = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(m)
    top = int(0.0 * H * ss)
    band = int(0.50 * H * ss)                        # solid board down to here
    d.rectangle([0, top, W * ss, band], fill=255)
    per = W * ss // 8                                # 8 scallops per repeat
    for k in range(-1, 9):
        cx = k * per + per // 2
        # rounded lobe hanging below the band
        d.ellipse([cx - per * 0.47, band - per * 0.30, cx + per * 0.47, band + per * 0.42], fill=255)
        # cusp pendant between lobes
        px = k * per
        d.polygon([(px - 9 * ss, band + 30 * ss), (px + 9 * ss, band + 30 * ss), (px + 3 * ss, band + 66 * ss), (px - 3 * ss, band + 66 * ss)], fill=255)
        d.ellipse([px - 13 * ss, band + 62 * ss, px + 13 * ss, band + 88 * ss], fill=255)
    # pierce the lobes: a small trefoil hole in each
    for k in range(-1, 9):
        cx = k * per + per // 2
        cy = band + 6 * ss
        for a in (-0.9, 0.0, 0.9):
            hx, hy = cx + math.sin(a) * 15 * ss, cy + math.cos(a) * 15 * ss - 6 * ss
            d.ellipse([hx - 8 * ss, hy - 8 * ss, hx + 8 * ss, hy + 8 * ss], fill=0)
    mask = np.asarray(m.resize((W, H), Image.LANCZOS)).astype(float) / 255
    col = wood((0.34, 0.2, 0.11), (0.15, 0.085, 0.045), n=H, m=W, rings=6, seed=21, along="u")
    x, y = grid(H, W)
    # carved grooves (dark lines) and a bead line along the board
    groove = (np.abs(y - 0.10) < 0.012) | (np.abs(y - 0.42) < 0.012)
    col[groove] *= 0.45
    bead = np.abs(y - 0.26) < 0.05
    rose_u = (x * 16) % 1 - 0.5
    rose_v = (y - 0.26) / 0.09
    rr = np.hypot(rose_u * 1.6, rose_v)
    th = np.arctan2(rose_v, rose_u)
    petals = (rr < 0.55 + 0.25 * np.cos(6 * th)) & bead
    col[petals] = col[petals] * 1.35
    col[(rr < 0.18) & bead] *= 0.5
    # lobe outline shading
    edge = gaussian_filter(mask, 2.0)
    col *= (0.6 + 0.4 * np.clip(edge * 1.4, 0, 1))[..., None]
    save_rgba("k_barge", col, (mask > 0.5).astype(float))


def k_jaali():
    """Gable fretwork (pinjrakari): eight-point stars joined by bars, walnut on transparent (RGBA, tileable)."""
    n, ss = 512, 2
    N = n * ss
    m = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(m)
    p = N // 4
    w = 9 * ss

    def star(cx, cy, r, width):
        pts = []
        for k in range(17):
            a = k * math.pi / 8
            rr = r if k % 2 == 0 else r * 0.62
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.line(pts, fill=255, width=width, joint="curve")

    def node(dx, dy):
        for i in range(5):
            for j in range(5):
                cx, cy = i * p + dx, j * p + dy
                star(cx, cy, p * 0.33, w)
                d.ellipse([cx - p * 0.07, cy - p * 0.07, cx + p * 0.07, cy + p * 0.07], fill=255)
                # bars to the neighbours and diagonal lozenge in the cell centre
                d.line([(cx + p * 0.33, cy), (cx + p - p * 0.33, cy)], fill=255, width=w)
                d.line([(cx, cy + p * 0.33), (cx, cy + p - p * 0.33)], fill=255, width=w)
                mx, my = cx + p / 2, cy + p / 2
                d.polygon([(mx, my - p * 0.2), (mx + p * 0.2, my), (mx, my + p * 0.2), (mx - p * 0.2, my)], outline=255, width=w)
                d.line([(cx + p * 0.2, cy + p * 0.2), (mx - p * 0.12, my - p * 0.12)], fill=255, width=w - 2 * ss)

    node(0, 0)
    mask = np.asarray(m.resize((n, n), Image.LANCZOS)).astype(float) / 255
    col = wood((0.36, 0.22, 0.12), (0.17, 0.1, 0.05), n=n, rings=9, seed=23)
    shade = gaussian_filter(mask, 1.5, mode="wrap")
    col *= (0.55 + 0.45 * shade)[..., None]
    save_rgba("k_jaali", col, (mask > 0.45).astype(float))


def k_khatam():
    """Honey-deodar khatamband for the attic: hexagon + star strips (exactly tileable: 7 x 8 hexes per repeat)."""
    n = 1024
    nx, ny = 7, 8
    sx, sy = n / (nx * math.sqrt(3)), n / (ny * 1.5)  # hexagon radius in x / y pixels (1% anisotropy)
    ss = 2
    N = n * ss
    strips = Image.new("L", (N, N), 0)
    stars = Image.new("L", (N, N), 0)
    d, ds = ImageDraw.Draw(strips), ImageDraw.Draw(stars)

    def hexes(dx, dy):
        for j in range(-1, ny + 2):
            for i in range(-1, nx + 2):
                cx = (i * math.sqrt(3) * sx + (j % 2) * math.sqrt(3) * sx / 2) * ss + dx
                cy = (j * 1.5 * sy) * ss + dy
                pts = [(cx + sx * ss * math.cos(math.pi / 6 + k * math.pi / 3), cy + sy * ss * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(7)]
                d.line(pts, fill=255, width=10 * ss, joint="curve")
                st = []
                for k in range(13):
                    r = (0.58 if k % 2 == 0 else 0.3)
                    a = k * math.pi / 6
                    st.append((cx + r * sx * ss * math.cos(a), cy + r * sy * ss * math.sin(a)))
                ds.polygon(st, fill=255)
                d.line(st, fill=255, width=5 * ss, joint="curve")

    wrap_draw(d, hexes, (N, N))
    sm = np.asarray(strips.resize((n, n), Image.LANCZOS)).astype(float) / 255
    st = np.asarray(stars.resize((n, n), Image.LANCZOS)).astype(float) / 255
    panel = wood((0.66, 0.47, 0.27), (0.5, 0.33, 0.17), n=n, rings=16, seed=31)
    star_c = wood((0.52, 0.32, 0.16), (0.36, 0.2, 0.09), n=n, rings=24, seed=32)
    strip_c = np.array([0.3, 0.17, 0.08]) * (0.85 + 0.3 * fbm(n, 1.5, 33))[..., None]
    col = mix(panel, star_c, np.clip(st - sm, 0, 1))
    col = mix(col, strip_c, sm)
    hl = np.clip(gaussian_filter(sm, 2.0, mode="wrap") - sm, 0, 1)
    col = col * (1 - 0.35 * hl)[..., None]
    save("k_khatam", col)
    save_normal("k_khatam", sm * 0.8 + st * 0.3, 3.0, 512)


def k_copper():
    """Hammered copper (samovar, trays, pots)."""
    n = 512
    x, y = grid(n)
    r = np.random.default_rng(41)
    h = np.zeros((n, n))
    for _ in range(900):
        cx, cy, rad = r.uniform(0, 1), r.uniform(0, 1), r.uniform(0.012, 0.03)
        dx = (x - cx + 0.5) % 1 - 0.5
        dy = (y - cy + 0.5) % 1 - 0.5
        dd = np.hypot(dx, dy) / rad
        h = np.minimum(h, np.where(dd < 1, dd ** 2 - 1, 0))
    h = gaussian_filter(h, 1.0, mode="wrap")
    tone = fbm(n, 2.2, 42)
    col = mix([0.78, 0.42, 0.22], [0.62, 0.3, 0.15], tone * 0.8)
    col *= (1.0 + 0.25 * (h - h.mean()))[..., None]
    save("k_copper", col)
    save_normal("k_copper", -h, 4.0)


def k_paisley():
    """Maroon cushion cloth with gold paisley (boteh) motifs."""
    n = 512
    ss = 2
    N = n * ss
    img = Image.new("RGB", (N, N), (112, 20, 28))
    d = ImageDraw.Draw(img)

    def boteh(cx, cy, s, rot, fill, outline):
        pts = []
        for k in range(40):
            t = k / 39 * 2 * math.pi
            # teardrop with a curled tip
            r = s * (0.55 + 0.45 * math.cos(t / 2) ** 2)
            px, py = r * math.cos(t) * 0.7, r * math.sin(t)
            if t > math.pi * 1.4:
                px += s * 0.35 * (t - math.pi * 1.4)
            ca, sa = math.cos(rot), math.sin(rot)
            pts.append((cx + px * ca - py * sa, cy + px * sa + py * ca))
        d.polygon(pts, fill=fill, outline=outline)

    def motifs(dx, dy):
        for i in range(4):
            for j in range(4):
                cx = (i + 0.5 * (j % 2)) * N / 4 + dx
                cy = (j + 0.5) * N / 4 + dy
                boteh(cx, cy, N / 13, 0.5 if (i + j) % 2 else -0.4, (205, 150, 60), (240, 205, 120))
                boteh(cx, cy, N / 26, 0.5 if (i + j) % 2 else -0.4, (150, 40, 34), None)
                d.ellipse([cx - N / 90, cy - N / 90, cx + N / 90, cy + N / 90], fill=(30, 70, 60))
                for k in range(6):
                    a = k * math.pi / 3
                    ex, ey = cx + N / 8 * math.cos(a) + N / 8, cy + N / 8 * math.sin(a)
                    d.ellipse([ex - N / 160, ey - N / 160, ex + N / 160, ey + N / 160], fill=(220, 180, 90))

    wrap_draw(d, motifs, (N, N))
    col = np.asarray(img.resize((n, n), Image.LANCZOS)).astype(float) / 255
    x, y = grid(n)
    weave = 0.92 + 0.08 * np.sin(2 * np.pi * x * 128) * np.sin(2 * np.pi * y * 128)
    col *= (weave * (0.9 + 0.15 * fbm(n, 1.2, 51)))[..., None]
    save("k_paisley", col)


def k_namda():
    """Namda felt: cream wool with chain-stitch flowers and vines in red, green, blue and mustard."""
    n = 512
    ss = 2
    N = n * ss
    img = Image.new("RGB", (N, N), (226, 210, 178))
    d = ImageDraw.Draw(img)
    palette = [(160, 40, 36), (52, 96, 70), (40, 64, 120), (200, 140, 50)]

    def flowers(dx, dy):
        for i in range(3):
            for j in range(3):
                cx, cy = (i + 0.5) * N / 3 + dx + (j % 2) * N / 6, (j + 0.5) * N / 3 + dy
                c = palette[(i + 2 * j) % 4]
                for k in range(8):
                    a = k * math.pi / 4
                    px, py = cx + N / 14 * math.cos(a), cy + N / 14 * math.sin(a)
                    d.ellipse([px - N / 28, py - N / 40, px + N / 28, py + N / 40], fill=c)
                d.ellipse([cx - N / 30, cy - N / 30, cx + N / 30, cy + N / 30], fill=palette[(i + 2 * j + 3) % 4])
                d.arc([cx - N / 5, cy - N / 9, cx + N / 5, cy + N / 3], 200, 340, fill=(52, 96, 70), width=5 * ss)
                for k in (-1, 1):
                    lx, ly = cx + k * N / 7, cy + N / 7
                    d.ellipse([lx - N / 40, ly - N / 80, lx + N / 40, ly + N / 80], fill=(70, 120, 80))

    wrap_draw(d, flowers, (N, N))
    col = np.asarray(img.resize((n, n), Image.LANCZOS)).astype(float) / 255
    col *= (0.88 + 0.2 * fbm(n, 1.0, 61))[..., None]
    save("k_namda", col)


def k_dastarkhan():
    """Dastarkhan (dining cloth spread on the floor): cream cotton, block-printed red border and small buta (uv fit)."""
    n = 1024
    x, y = grid(n)
    col = np.zeros((n, n, 3)) + [0.93, 0.89, 0.8]
    e = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    col[(e > 0.03) & (e < 0.11)] = [0.62, 0.13, 0.12]
    zig = np.abs(((x + y) * 40) % 1 - 0.5) < 0.18
    col[(e > 0.05) & (e < 0.09) & zig] = [0.9, 0.78, 0.5]
    col[(e > 0.12) & (e < 0.13)] = [0.2, 0.36, 0.3]
    fx, fy = (x * 9) % 1 - 0.5, (y * 9) % 1 - 0.5
    rr, th = np.hypot(fx, fy), np.arctan2(fy, fx)
    buta = (rr < 0.13 + 0.06 * np.cos(5 * th)) & (e > 0.16)
    col[buta] = [0.66, 0.2, 0.16]
    col[(rr < 0.04) & (e > 0.16)] = [0.84, 0.66, 0.3]
    col *= (0.93 + 0.1 * fbm(n, 0.9, 71))[..., None]
    save("k_dastarkhan", col)


def k_deodar_planks():
    """Wide honey deodar floor boards for the attic (boards along v, staggered joints)."""
    n = 1024
    x, y = grid(n)
    base = wood((0.66, 0.46, 0.27), (0.46, 0.3, 0.16), rings=10, seed=81)
    rows = 6
    row = (x * rows).astype(int)
    offs = np.sin(row * 91.7) * 0.5 + 0.5
    seg = ((y + offs) * 1.5) % 1
    tint = 1 + np.sin(row * 17.3 + ((y + offs) * 1.5).astype(int) * 5.1) * 0.08
    col = base * tint[..., None]
    gap = np.minimum((x * rows) % 1, 1 - (x * rows) % 1) < 0.01
    joint = np.minimum(seg, 1 - seg) < 0.004
    line = gap | joint
    col[line] *= 0.4
    save("k_deodar_planks", col)
    save_normal("k_deodar_planks", 1 - line.astype(float), 1.2, 512)


def k_chinar():
    """Autumn chinar foliage mottling (red, orange, amber with a little green) for the tree crown."""
    n = 512
    a = fbm(n, 1.7, 91)
    b = fbm(n, 0.9, 92)
    c = fbm(n, 2.6, 93)
    col = mix([0.62, 0.16, 0.06], [0.86, 0.42, 0.08], a)
    col = mix(col, [0.9, 0.62, 0.16], np.clip((b - 0.6) * 2.5, 0, 1))
    col = mix(col, [0.36, 0.38, 0.12], np.clip((c - 0.78) * 3, 0, 1))
    leafy = 0.75 + 0.35 * (fbm(n, 0.4, 94) > 0.5)
    col *= leafy[..., None]
    save("k_chinar", col)


def k_carved():
    """Carved walnut relief (chinar leaf + rosette) for furniture fronts and window heads."""
    n = 512
    ss = 2
    N = n * ss
    h = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(h)

    def motif(dx, dy):
        for i in range(2):
            for j in range(2):
                cx, cy = (i + 0.5) * N / 2 + dx, (j + 0.5) * N / 2 + dy
                for k in range(5):                       # five-lobed chinar leaf
                    a = -math.pi / 2 + (k - 2) * 0.62
                    px, py = cx + N / 8 * math.cos(a), cy + N / 8 * math.sin(a)
                    d.ellipse([px - N / 14, py - N / 14, px + N / 14, py + N / 14], fill=200)
                d.ellipse([cx - N / 12, cy - N / 12, cx + N / 12, cy + N / 12], fill=255)
                d.line([(cx, cy), (cx, cy + N / 5)], fill=160, width=8 * ss)
                for k in range(8):
                    a = k * math.pi / 4
                    rx, ry = cx + N / 4 + N / 22 * math.cos(a), cy + N / 4 + N / 22 * math.sin(a)
                    d.ellipse([rx - N / 50, ry - N / 50, rx + N / 50, ry + N / 50], fill=230)
                d.rectangle([cx - N / 4, cy - N / 4 - 4 * ss, cx + N / 4, cy - N / 4 + 4 * ss], fill=120)

    wrap_draw(d, motif, (N, N))
    hm = np.asarray(h.resize((n, n), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.5))).astype(float) / 255
    base = wood((0.38, 0.23, 0.12), (0.17, 0.1, 0.05), n=n, rings=8, seed=101)
    col = base * (0.55 + 0.6 * hm)[..., None]
    save("k_carved", col)
    save_normal("k_carved", hm, 5.0)


JOBS = {"k_barge": k_barge, "k_jaali": k_jaali, "k_khatam": k_khatam, "k_copper": k_copper, "k_paisley": k_paisley,
        "k_namda": k_namda, "k_dastarkhan": k_dastarkhan, "k_deodar_planks": k_deodar_planks, "k_chinar": k_chinar,
        "k_carved": k_carved}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for nm in sys.argv[1:] or list(JOBS):
        JOBS[nm]()
        print("made", nm)
