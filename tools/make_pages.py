"""Write each v2 design's page (site/v2/<design>/index.html), its thumbnail, and the picker page site/index.html.

    python3 tools/make_pages.py
"""
import html, json, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DESIGNS = [
    ("modern", "Modern Cozy",
     "Stone and teak outside, warm Italian and Turkish Diana marble, oak floors and walnut panelling inside. Flat roof with a water tank and solar panels."),
    ("kashmiri", "Kashmiri",
     "Steep green tin roof with a carpeted hall in the attic, walnut khatamband ceilings, pinjrakari lattice windows, Kashmiri carpets and a samovar."),
    ("spanish", "Spanish Villa",
     "White stucco, round arches, a terracotta tile roof and floors, wooden beams and wrought-iron railings."),
]


def design_pages():
    tpl = open(os.path.join(SITE, "v2", "_template.html")).read()
    built = []
    for key, title, blurb in DESIGNS:
        d = os.path.join(SITE, "v2", key)
        if not os.path.exists(os.path.join(d, "house.json")):
            continue
        data = json.load(open(os.path.join(d, "house.json")))
        attic = " / attic" if "AT" in data["levels"] else ""
        page = (tpl.replace("{{TITLE}}", html.escape(title)).replace("{{BLURB}}", html.escape(blurb))
                .replace("{{ATTIC_KEY}}", attic))
        open(os.path.join(d, "index.html"), "w").write(page)
        src = os.path.join(ROOT, "renders", "v2", f"{key}_1_front.png")
        if os.path.exists(src):
            im = Image.open(src).convert("RGB")
            im.thumbnail((800, 500))
            im.save(os.path.join(d, "thumb.jpg"), quality=82)
        built.append((key, title, blurb))
    return built


def picker(built):
    cards = []
    for key, title, blurb in built:
        cards.append(f"""
    <a class="card" href="v2/{key}/index.html">
      <img src="v2/{key}/thumb.jpg" alt="{html.escape(title)} house, front view" loading="lazy">
      <div class="txt"><h2>{html.escape(title)}</h2><p>{html.escape(blurb)}</p><span class="play">Walk in ▸</span></div>
    </a>""")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#1b1d22">
<title>House Walk</title>
<meta name="description" content="One hand-drawn floor plan built as three walkable 3D houses.">
<style>
  :root {{ --bg: #1b1d22; --card: #25282e; --ink: #f4efe6; --dim: #b9b2a6; --accent: #e8b25c; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}
  header {{ max-width: 1120px; margin: 0 auto; padding: 40px 16px 12px; }}
  h1 {{ margin: 0 0 6px; font-size: clamp(28px, 5vw, 44px); letter-spacing: .3px; }}
  header p {{ margin: 0; color: var(--dim); font-size: 16px; line-height: 1.5; max-width: 640px; }}
  main {{ max-width: 1120px; margin: 0 auto; padding: 20px 16px 40px; display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
  .card {{ display: flex; flex-direction: column; background: var(--card); border-radius: 14px; overflow: hidden; color: inherit; text-decoration: none; box-shadow: 0 6px 24px rgba(0,0,0,.25); transition: transform .15s ease; }}
  .card:hover {{ transform: translateY(-3px); }}
  .card img {{ width: 100%; aspect-ratio: 16 / 10; object-fit: cover; display: block; background: #30343b; }}
  .txt {{ padding: 14px 16px 18px; display: flex; flex-direction: column; gap: 6px; flex: 1; }}
  .txt h2 {{ margin: 0; font-size: 20px; }}
  .txt p {{ margin: 0; color: var(--dim); font-size: 14px; line-height: 1.45; flex: 1; }}
  .play {{ color: var(--accent); font-weight: 600; margin-top: 6px; }}
  footer {{ max-width: 1120px; margin: 0 auto; padding: 0 16px 40px; color: var(--dim); font-size: 14px; line-height: 1.6; }}
  footer a {{ color: var(--ink); }}
</style>
</head>
<body>
<header>
  <h1>House Walk</h1>
  <p>One floor plan (31' × 38'-3"), built as three different two-storey houses. Walk Jack through any of them on a computer or a phone. Open doors, take the stairs, look around.</p>
</header>
<main>{''.join(cards)}
</main>
<footer>
  Controls: <b>WASD</b> + mouse on a computer; on a phone, hold it sideways, left thumb walks and right thumb looks. Tap or press <b>E</b> on a door to open it.<br>
  <a href="v1/index.html">First version (plain model)</a> · <a href="https://github.com/realcodebear/house-walk">Source on GitHub</a>
</footer>
</body>
</html>
"""
    open(os.path.join(SITE, "index.html"), "w").write(page)


if __name__ == "__main__":
    b = design_pages()
    picker(b)
    print("pages:", [k for k, _, _ in b])
