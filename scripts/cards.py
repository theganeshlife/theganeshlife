"""Builds the project cards on the profile page from the account's public repositories."""
import json, math, os, re, sys, textwrap, urllib.request

USER = "theganeshlife"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
START, END = "<!-- cards:start -->", "<!-- cards:end -->"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
FLAG = ["#2A62C9", "#F4F4F0", "#D8343A", "#1F9A5B", "#F2B71F"]  # prayer-flag order: blue, white, red, green, yellow

THEMES = {
    "light": dict(bg="#F4F7FB", card="#FFFFFF", ink="#13203A", muted="#55627A", faint="#8D98AC", line="#DDE4EE",
                  ridge=["#C9D5E6", "#A9BAD3", "#7F95B6"], sky1="#FDEBD5", sky2="#F4F7FB", sun="#F2B71F", accent="#1E5B8F",
                  chip="#EEF3F9", node="#1E5B8F", flagwhite="#E6EAF0", shadow="rgba(19,32,58,.10)"),
    "dark": dict(bg="#0D1526", card="#141F35", ink="#E9EEF7", muted="#A5B1C6", faint="#7484A0", line="#24324D",
                 ridge=["#1C2A45", "#243656", "#2E4469"], sky1="#2B2340", sky2="#0D1526", sun="#F2B71F", accent="#7FB2F0",
                 chip="#1B2842", node="#7FB2F0", flagwhite="#D9DEE8", shadow="rgba(0,0,0,.35)"),
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def flag_stripe(x, y, w, h, t):
    seg = w / 5
    out = []
    for i, c in enumerate(FLAG):
        col = t["flagwhite"] if c == "#F4F4F0" else c
        out.append(f'<rect x="{x + i * seg:.1f}" y="{y}" width="{seg + .5:.1f}" height="{h}" fill="{col}"/>')
    return "".join(out)


def svg(w, h, body, t, rx=18, title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title><style>text{{font-family:{FONT}}}</style>'
            f'<defs><clipPath id="c"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath></defs>'
            f'<g clip-path="url(#c)">{body}</g></svg>')



def art_sortwise(t):
    cols = ["#5B7FE8", "#E0574F", "#2E9E62", "#A66BD6"]
    g = []
    for i, c in enumerate(cols):
        x, y = 34 + (i % 2) * 112, 34 + (i // 2) * 72
        g.append(f'<rect x="{x}" y="{y}" width="40" height="12" rx="4" fill="{c}" opacity=".85"/>'
                 f'<rect x="{x}" y="{y + 8}" width="96" height="52" rx="7" fill="{c}"/>'
                 f'<rect x="{x + 12}" y="{y + 36}" width="44" height="5" rx="2.5" fill="#fff" opacity=".85"/>')
    g.append('<g transform="translate(246,30) rotate(9)"><rect width="54" height="66" rx="6" fill="#fff" stroke="#C9D3E2"/>'
             '<rect x="9" y="12" width="34" height="4" rx="2" fill="#C9D3E2"/><rect x="9" y="22" width="28" height="4" rx="2" fill="#C9D3E2"/><rect x="9" y="32" width="32" height="4" rx="2" fill="#C9D3E2"/></g>')
    return "".join(g)


def art_pocketdeck(t):
    g = [f'<rect x="80" y="20" width="180" height="140" rx="16" fill="{"#0A0F1C" if t["card"] != "#FFFFFF" else "#1B2438"}" stroke="{t["line"]}" stroke-width="1.5"/>', '<rect x="90" y="30" width="160" height="120" rx="9" fill="#26324D"/>']
    cols = ["#5B7FE8", "#2E9E62", "#E8822E", "#A66BD6", "#E0574F", "#1FA3B0", "#D9A520", "#D0659F", "#56647E", "#4472DB", "#2F9580", "#D94862"]
    for i, c in enumerate(cols):
        x, y = 100 + (i % 4) * 37, 40 + (i // 4) * 36
        g.append(f'<rect x="{x}" y="{y}" width="30" height="29" rx="6" fill="{c}"/>')
    return "".join(g)


def art_dawn(t):
    g = [f'<rect x="40" y="18" width="260" height="146" rx="10" fill="{"#0A0F1C" if t["card"] != "#FFFFFF" else "#1B2438"}" stroke="{t["line"]}" stroke-width="1.5"/>',
         '<defs><linearGradient id="dawn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F7B267"/><stop offset="1" stop-color="#F4845F"/></linearGradient></defs>',
         '<rect x="48" y="26" width="244" height="130" rx="5" fill="url(#dawn)"/>',
         '<circle cx="236" cy="70" r="18" fill="#FFE8A8"/>',
         '<path d="M48 156 L48 118 L92 82 L120 104 L162 62 L204 108 L232 92 L292 130 L292 156 Z" fill="#5B4B7A"/>',
         '<path d="M162 62 L176 76 L168 74 L162 80 L156 74 L148 76 Z" fill="#fff" opacity=".9"/>',
         '<path d="M48 156 L48 136 L110 116 L170 134 L236 120 L292 140 L292 156 Z" fill="#3A3157"/>',
         '<rect x="62" y="38" width="86" height="34" rx="6" fill="#00000033"/>',
         '<text x="72" y="61" font-size="17" font-weight="700" fill="#fff">06:15</text>',
         '<rect x="150" y="164" width="40" height="6" rx="3" fill="#1B2438"/>']
    return "".join(g)



def art_generic(name, t):
    """Folder-and-files motif with the project's initial, coloured from the prayer-flag palette."""
    cols = [c for c in FLAG if c != "#F4F4F0"]
    c = cols[sum(map(ord, name)) % len(cols)]
    c2 = cols[(sum(map(ord, name)) + 2) % len(cols)]
    g = [f'<rect x="96" y="40" width="54" height="16" rx="5" fill="{c}" opacity=".8"/>',
         f'<rect x="96" y="50" width="148" height="104" rx="12" fill="{c}"/>',
         f'<text x="170" y="122" text-anchor="middle" font-size="46" font-weight="800" fill="#fff">{esc(name[:1].upper())}</text>',
         f'<g transform="translate(232,30) rotate(10)"><rect width="50" height="62" rx="6" fill="{t["card"]}" stroke="{t["line"]}" stroke-width="1.5"/>'
         f'<rect x="9" y="12" width="32" height="4" rx="2" fill="{c2}"/><rect x="9" y="22" width="24" height="4" rx="2" fill="{t["line"]}"/>'
         f'<rect x="9" y="32" width="28" height="4" rx="2" fill="{t["line"]}"/></g>',
         flag_stripe(0, 184, 340, 6, t)]
    return "".join(g)


def card(name, line1, line2, tags, art, t):
    W, H = 340, 400
    b = [f'<rect width="{W}" height="{H}" rx="18" fill="{t["card"]}"/>',
         f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="18" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>',
         f'<rect x="0" y="0" width="{W}" height="190" fill="{t["chip"]}"/>', art(t),
         f'<text x="26" y="236" font-size="24" font-weight="700" fill="{t["ink"]}" letter-spacing="-.4">{esc(name)}</text>',
         f'<text x="26" y="266" font-size="15" fill="{t["muted"]}">{esc(line1)}</text>',
         f'<text x="26" y="288" font-size="15" fill="{t["muted"]}">{esc(line2)}</text>']
    x = 26
    for tag in tags:
        w = 18 + len(tag) * 7.2
        b.append(f'<rect x="{x}" y="310" width="{w:.0f}" height="28" rx="14" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>'
                 f'<text x="{x + w / 2:.0f}" y="329" text-anchor="middle" font-size="12.5" font-weight="600" fill="{t["muted"]}">{esc(tag)}</text>')
        x += w + 8
    b.append(f'<text x="26" y="374" font-size="14.5" font-weight="700" fill="{t["accent"]}">View on GitHub</text>')
    return svg(W, H, "".join(b), t, title=f"{name}: {line1} {line2}")



# Cards with hand-made artwork and wording, in display order.
FIXED = {
    "sortwise": dict(name="SortWise", lines=("Sorts any folder by what your files", "are about, and keeps it that way."),
                     tags=["Windows", "macOS"], art=art_sortwise, file="card-sortwise",
                     alt="SortWise: sorts any folder by what your files are about, and keeps it that way. Windows and macOS."),
    "pocketdeck": dict(name="PocketDeck", lines=("Turns an Android phone or tablet into", "a control deck for your Windows PC."),
                       tags=["Windows", "Android"], art=art_pocketdeck, file="card-pocketdeck",
                       alt="PocketDeck: turns an Android phone or tablet into a control deck for your Windows PC."),
    "himalayan-dawn": dict(name="Himalayan Dawn", lines=("Ad-free Android TV home screen with", "the Nepali calendar and a Nepal clock."),
                           tags=["Android TV"], art=art_dawn, file="card-dawn",
                           alt="Himalayan Dawn: ad-free Android TV home screen with the Nepali calendar and a Nepal clock."),
}
SKIP = {USER.lower(), ".github"}
TAGS = {"windows": "Windows", "macos": "macOS", "mac": "macOS", "linux": "Linux", "android": "Android", "android-tv": "Android TV",
        "google-tv": "Google TV", "ios": "iOS", "web": "Web", "website": "Web", "chrome-extension": "Chrome", "cli": "CLI"}


def repos():
    req = urllib.request.Request(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=created&direction=asc",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": USER})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return [d for d in data if not d["fork"] and not d["archived"] and not d["private"] and d["name"].lower() not in SKIP]


SMALL = {"a", "an", "and", "at", "for", "in", "of", "on", "or", "the", "to"}


def pretty(name):
    words = [w for w in re.split(r"[-_ ]+", name) if w]
    return " ".join(w if w.isupper() or (i and w.lower() in SMALL) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def fit(text, width=37):
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    lines = textwrap.wrap(text, width) or [""]
    if len(lines) > 2:
        lines = [lines[0], textwrap.shorten(" ".join(lines[1:]), width, placeholder="…")]
    return (lines + [""])[:2]


def entry(d):
    key = d["name"].lower()
    if key in FIXED:
        e = dict(FIXED[key])
    else:
        name = pretty(d["name"])
        desc = d.get("description") or (f"An open source {d['language']} project" if d.get("language") else "An open source project")
        tags = [TAGS[x] for x in d.get("topics", []) if x in TAGS][:3] or ([d["language"]] if d.get("language") else [])
        slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
        e = dict(name=name, lines=tuple(fit(desc)), tags=tags, art=lambda t, n=name: art_generic(n, t),
                 file=f"card-{slug}", alt=f"{name}: {desc.rstrip('.')}.")
    e["url"] = d["html_url"]
    return e


def main():
    items = repos()
    order = list(FIXED)
    items.sort(key=lambda d: (order.index(d["name"].lower()) if d["name"].lower() in order else len(order), d["created_at"]))
    cards = [entry(d) for d in items]
    keep = set()
    for c in cards:
        for theme, t in THEMES.items():
            path = os.path.join(ASSETS, f"{c['file']}-{theme}.svg")
            keep.add(os.path.basename(path))
            with open(path, "w", encoding="utf-8") as f:
                f.write(card(c["name"], c["lines"][0], c["lines"][1], c["tags"], c["art"], t))
    for f in os.listdir(ASSETS):
        if f.startswith("card-") and f not in keep:
            os.remove(os.path.join(ASSETS, f))
    rows = []
    for i in range(0, len(cards), 3):
        row = ['<p align="center">']
        for c in cards[i:i + 3]:
            alt = c["alt"].replace('"', "&quot;")
            row.append(f'  <a href="{c["url"]}"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/{c["file"]}-dark.svg">'
                       f'<img src="assets/{c["file"]}-light.svg" width="32%" alt="{alt}"></picture></a>')
        row.append("</p>")
        rows.append("\n".join(row))
    readme = os.path.join(ROOT, "README.md")
    text = open(readme, encoding="utf-8").read()
    a, b = text.index(START) + len(START), text.index(END)
    text = text[:a] + "\n" + "\n\n".join(rows) + "\n" + text[b:]
    with open(readme, "w", encoding="utf-8") as f:
        f.write(text)
    print(", ".join(c["name"] for c in cards))


if __name__ == "__main__":
    main()
