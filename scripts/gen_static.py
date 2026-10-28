#!/usr/bin/env python3
"""Generate the static profile graphics: banner, typing line, project cards, badges.

Run from the repository root:  python3 scripts/gen_static.py
Outputs are committed; this script is not part of the daily workflow.
"""
import os
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

BG = "#0D1117"
PANEL = "#161B22"
BORDER = "#30363D"
CYAN = "#22D3EE"
VIOLET = "#A78BFA"
TEXT = "#E6EDF3"
MUTED = "#9DA7B3"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
MONO_RATIO = 0.6  # advance width of a monospace glyph, in em


def mono_width(text, size):
    return len(text) * size * MONO_RATIO


def write(rel, content):
    path = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("wrote", os.path.relpath(path, ROOT))


def gradient(id_, x2="100%", y2="0%"):
    return (
        f'<linearGradient id="{id_}" x1="0%" y1="0%" x2="{x2}" y2="{y2}">'
        f'<stop offset="0%" stop-color="{CYAN}"/><stop offset="100%" stop-color="{VIOLET}"/>'
        "</linearGradient>"
    )


# --------------------------------------------------------------------------- banner
def banner():
    w, h = 1000, 280
    hexes = []
    # three-hexagon honeycomb on the right, a nod to containers and clusters
    import math

    def hexagon(cx, cy, r):
        pts = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
        return " ".join(pts)

    r = 34
    dx = r * math.sqrt(3)
    centers = [(820, 112), (820 + dx, 112), (820 + dx / 2, 112 + 1.5 * r)]
    for i, (cx, cy) in enumerate(centers):
        stroke = CYAN if i != 1 else VIOLET
        hexes.append(
            f'<polygon points="{hexagon(cx, cy, r)}" fill="{PANEL}" stroke="{stroke}" stroke-width="2"/>'
            f'<polygon points="{hexagon(cx, cy, r * 0.45)}" fill="none" stroke="{stroke}" stroke-opacity="0.45" stroke-width="1.5"/>'
        )

    nodes = [(700, 70, CYAN, 5), (952, 58, VIOLET, 6), (930, 232, CYAN, 5), (705, 222, VIOLET, 6), (760, 150, CYAN, 4)]
    hub = (820 + dx / 2, 112 + 0.5 * r)
    edges = "".join(
        f'<line x1="{x}" y1="{y}" x2="{hub[0]:.1f}" y2="{hub[1]:.1f}" stroke="url(#g)" stroke-opacity="0.35" stroke-width="1.5"/>'
        for x, y, _, _ in nodes
    )
    dots = "".join(
        f'<circle cx="{x}" cy="{y}" r="{rad}" fill="{c}">'
        f'<animate attributeName="r" values="{rad};{rad + 2.5};{rad}" dur="{3 + i * 0.7:.1f}s" repeatCount="indefinite"/>'
        "</circle>"
        for i, (x, y, c, rad) in enumerate(nodes)
    )

    sep = f'<tspan fill="{VIOLET}"> · </tspan>'
    subtitle = sep.join(escape(p) for p in ["Full-stack Engineer", "Backend", "AI Integrations", "Cloud"])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">
<title id="t">Muhammadali Jawhar</title>
<desc id="d">Full-stack Engineer, Backend, AI Integrations, Cloud</desc>
<defs>
{gradient("g")}
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.2" fill="{MUTED}" fill-opacity="0.18"/></pattern>
<clipPath id="clip"><rect width="{w}" height="{h}" rx="18"/></clipPath>
</defs>
<g clip-path="url(#clip)">
<rect width="{w}" height="{h}" fill="{BG}"/>
<rect x="600" width="400" height="{h}" fill="url(#dots)"/>
<circle cx="900" cy="140" r="190" fill="{VIOLET}" fill-opacity="0.06"/>
<circle cx="700" cy="40" r="120" fill="{CYAN}" fill-opacity="0.05"/>
{edges}
{"".join(hexes)}
{dots}
<rect width="{w}" height="4" fill="url(#g)"/>
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="{BORDER}"/>
<text x="60" y="88" font-family="{MONO}" font-size="18" fill="{CYAN}">~/jawhar <tspan fill="{MUTED}">$ whoami</tspan></text>
<text x="60" y="152" font-family="{SANS}" font-size="52" font-weight="700" fill="{TEXT}">Muhammadali Jawhar</text>
<rect x="60" y="172" width="140" height="4" rx="2" fill="url(#g)"/>
<text x="60" y="218" font-family="{SANS}" font-size="21" fill="{MUTED}">{subtitle}</text>
</svg>
'''
    write("banner.svg", svg)


# --------------------------------------------------------------------------- typing line
def typing():
    phrases = [
        "Building backend APIs",
        "Shipping full-stack applications",
        "Integrating AI into products",
        "Running Kubernetes & GitOps",
    ]
    w, h, size = 640, 56, 22
    char_w = size * MONO_RATIO
    type_step, hold, del_step, gap = 0.07, 1.6, 0.03, 0.35
    slots = [len(p) * type_step + hold + len(p) * del_step + gap for p in phrases]
    total = sum(slots)
    caret_w = 11

    groups = []
    t0 = 0.0
    for idx, p in enumerate(phrases):
        n = len(p)
        width = n * char_w
        x0 = (w - width - caret_w - 30) / 2 + 30
        # discrete keyframes: chars visible over time
        times, widths = [0.0], [0.0]
        t = t0
        times.append(t); widths.append(0.0)
        for i in range(1, n + 1):
            t += type_step
            times.append(t); widths.append(i * char_w)
        t += hold
        times.append(t); widths.append(width)
        for i in range(n - 1, -1, -1):
            t += del_step
            times.append(t); widths.append(i * char_w)
        times.append(total); widths.append(0.0)
        # dedupe identical consecutive times, normalise
        kt, kv = [], []
        for tt, ww in zip(times, widths):
            v = round(min(tt / total, 1.0), 5)
            if kt and v <= kt[-1]:
                kt[-1] = v; kv[-1] = ww
                continue
            kt.append(v); kv.append(ww)
        kt[0], kt[-1] = 0.0, 1.0
        key_times = ";".join(f"{v:.5f}" for v in kt)
        clip_vals = ";".join(f"{v:.1f}" for v in kv)
        caret_vals = ";".join(f"{x0 + v:.1f}" for v in kv)
        # visibility of the caret only during this phrase's slot
        s0, s1 = t0 / total, (t0 + slots[idx]) / total
        vis_kt, vis_v = ["0"], ["0"]
        if s0 > 0:
            vis_kt.append(f"{s0:.5f}"); vis_v.append("1")
        else:
            vis_v[0] = "1"
        if s1 < 1:
            vis_kt.append(f"{s1:.5f}"); vis_v.append("0")
        vis_kt.append("1"); vis_v.append(vis_v[-1])
        groups.append(f'''<clipPath id="c{idx}"><rect x="{x0:.1f}" y="0" width="0" height="{h}">
<animate attributeName="width" calcMode="discrete" keyTimes="{key_times}" values="{clip_vals}" dur="{total:.2f}s" repeatCount="indefinite"/>
</rect></clipPath>
<text clip-path="url(#c{idx})" x="{x0:.1f}" y="36" font-family="{MONO}" font-size="{size}" fill="{CYAN}" textLength="{width:.1f}" lengthAdjust="spacingAndGlyphs">{escape(p)}</text>
<rect y="16" width="{caret_w}" height="26" rx="1.5" fill="{VIOLET}" opacity="0">
<animate attributeName="x" calcMode="discrete" keyTimes="{key_times}" values="{caret_vals}" dur="{total:.2f}s" repeatCount="indefinite"/>
<animate attributeName="opacity" calcMode="discrete" keyTimes="{";".join(vis_kt)}" values="{";".join(vis_v)}" dur="{total:.2f}s" repeatCount="indefinite"/>
</rect>''')
        t0 += slots[idx]

    alt = ", ".join(phrases)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(alt)}">
<title>{escape(alt)}</title>
{"".join(groups)}
</svg>
'''
    write("typing.svg", svg)


# --------------------------------------------------------------------------- chips and badges
def chip(x, y, label, accent, size=12, height=24):
    tw = mono_width(label, size)
    width = 12 + 8 + 7 + tw + 12
    g = (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height}" rx="{height / 2}" fill="{BG}" stroke="{BORDER}"/>'
        f'<circle cx="{x + 12 + 4:.1f}" cy="{y + height / 2:.1f}" r="4" fill="{accent}"/>'
        f'<text x="{x + 12 + 8 + 7:.1f}" y="{y + height / 2 + size * 0.36:.1f}" font-family="{MONO}" font-size="{size}" '
        f'fill="{TEXT}" textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs">{escape(label)}</text>'
    )
    return g, width


def badge(slug, label, accent):
    size, height = 13, 30
    tw = mono_width(label, size)
    width = 14 + 9 + 9 + tw + 14
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height}" viewBox="0 0 {width:.0f} {height}" role="img" aria-label="{escape(label)}">
<title>{escape(label)}</title>
<rect x="0.5" y="0.5" width="{width - 1:.0f}" height="{height - 1}" rx="{(height - 1) / 2}" fill="{PANEL}" stroke="{BORDER}"/>
<circle cx="{14 + 4.5}" cy="{height / 2}" r="4.5" fill="{accent}"/>
<text x="{14 + 9 + 9}" y="{height / 2 + size * 0.36:.1f}" font-family="{MONO}" font-size="{size}" fill="{TEXT}" textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs">{escape(label)}</text>
</svg>
'''
    write(f"badges/{slug}.svg", svg)


# --------------------------------------------------------------------------- project cards
def card(slug, index, title, lang, lines, chips):
    w = 640
    pad = 32
    # lay chips out in rows
    rows, row, row_w = [], [], 0
    for i, label in enumerate(chips):
        _, cw = chip(0, 0, label, CYAN)
        if row and row_w + cw > w - 2 * pad:
            rows.append(row); row, row_w = [], 0
        row.append((label, cw)); row_w += cw + 8
    if row:
        rows.append(row)
    desc_y0 = 108
    chips_y0 = desc_y0 + (len(lines) - 1) * 26 + 30
    h = int(chips_y0 + len(rows) * 32 + pad - 6)

    chip_svg = []
    k = 0
    for r_i, r in enumerate(rows):
        x = pad
        for label, cw in r:
            g, _ = chip(x, chips_y0 + r_i * 32, label, CYAN if k % 2 == 0 else VIOLET)
            chip_svg.append(g); x += cw + 8; k += 1

    desc = "".join(
        f'<text x="{pad}" y="{desc_y0 + i * 26}" font-family="{SANS}" font-size="17" fill="{MUTED}">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    lang_w = mono_width(lang, 12)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">
<title id="t">{escape(title)}</title>
<desc id="d">{escape(" ".join(lines))} Stack: {escape(", ".join(chips))}.</desc>
<defs>{gradient("g", "0%", "100%")}<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath></defs>
<g clip-path="url(#clip)">
<rect width="{w}" height="{h}" fill="{PANEL}"/>
<rect width="5" height="{h}" fill="url(#g)"/>
<circle cx="{w - 40}" cy="-10" r="110" fill="{VIOLET}" fill-opacity="0.07"/>
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="{BORDER}"/>
<text x="{pad}" y="44" font-family="{MONO}" font-size="13" fill="{VIOLET}">featured · {index:02d}</text>
<text x="{w - pad - lang_w:.1f}" y="44" font-family="{MONO}" font-size="12" fill="{MUTED}" textLength="{lang_w:.1f}" lengthAdjust="spacingAndGlyphs">{escape(lang)}</text>
<text x="{pad}" y="78" font-family="{SANS}" font-size="28" font-weight="700" fill="{TEXT}">{escape(title)}</text>
{desc}
{"".join(chip_svg)}
</svg>
'''
    write(f"cards/{slug}.svg", svg)


BADGE_GROUPS = {
    # group: (accent, [(slug, label), ...])
    "languages": (CYAN, ["Python", "TypeScript", "JavaScript", "SQL", "Bash", "HTML/CSS"]),
    "frontend": (VIOLET, ["React", "Next.js", "Redux Toolkit", "Tailwind CSS", "Vite"]),
    "backend": (CYAN, ["FastAPI", "NestJS", "Node.js", "Express", "Pydantic"]),
    "data": (VIOLET, ["PostgreSQL", "SQL Server", "MongoDB", "Redis", "Kafka"]),
    "ai": (CYAN, ["OpenAI", "Azure OpenAI", "MLflow", "Pandas", "NumPy"]),
    "cloud": (VIOLET, ["Kubernetes", "Docker", "Helm", "Argo CD", "Azure", "Azure DevOps", "AWS S3"]),
    "secondary": (MUTED, ["SQLAlchemy", "Alembic", "RabbitMQ", "Qdrant", "Azure AI Search", "Socket.IO", "Firebase", "Nginx", "Git", "Poetry"]),
    "ui": (MUTED, ["Flowbite", "Bootstrap", "Lucide", "ApexCharts", "Formik", "Yup"]),
    "auth": (MUTED, ["JWT", "OAuth 2.0", "Keycloak", "bcrypt", "TOTP 2FA", "Azure AD"]),
    "observability": (MUTED, ["OpenTelemetry", "Prometheus", "Structured logging", "Pytest", "Jest"]),
    "payments": (MUTED, ["Stripe", "Razorpay"]),
    "links": (CYAN, ["LinkedIn", "LeetCode"]),
}


def slugify(label):
    s = label.lower()
    for a, b in [("/", "-"), (".", ""), (" ", "-"), ("+", "p")]:
        s = s.replace(a, b)
    return s


def main():
    banner()
    typing()
    for group, (accent, labels) in BADGE_GROUPS.items():
        for label in labels:
            badge(slugify(label), label, accent)
    # Project cards: add entries here once projects live on this account, e.g.
    # card("slug", 1, "Title", "Language", ["line one", "line two"], ["Stack", "Chips"])


if __name__ == "__main__":
    main()
