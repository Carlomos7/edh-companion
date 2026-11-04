"""Report colours from the commander's artwork, a saved theme, the color identity or neutral, resolved at build time.

Extraction (needs Pillow): the art crop downsampled to 64 px, quantized to 16 colours, each scored by chroma and the
share of pixels near its hue (Material's colour scoring, with OKLCH standing in for HCT). Roles for light and dark
mode keep the seed hue and change lightness only; every text role is pushed until it has 4.5:1 on bg, surface and
surface2 (UI roles therefore 3:1+), and on_accent is black or white, whichever reads on the accent. Status colours
are fixed in the template, never derived. Pure Python maths (OKLab, Ottosson); no network unless art_file is asked to
fetch, and a missing or unreadable image is a fallback, never an error.
"""
import math, os

ROLES = ("bg", "surface", "surface2", "border", "text", "muted", "accent", "accent2", "on_accent", "focus", "art_wash")
# lightness per role (light mode, dark mode); chroma is a faint tint of the seed except accents
L_LIGHT = {"bg": .98, "surface": .955, "surface2": .92, "border": .86, "text": .22, "muted": .44, "accent": .52}
L_DARK = {"bg": .17, "surface": .215, "surface2": .26, "border": .36, "text": .95, "muted": .76, "accent": .74}
WASH_ALPHA = "26"  # ~15%: decoration behind the hero, never under text


def _lin(c):
    c /= 255
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4


def _gam(x):
    return 12.92 * x if x <= .0031308 else 1.055 * x ** (1 / 2.4) - .055


def rgb_to_oklch(rgb):
    r, g, b = (_lin(x) for x in rgb)
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (.4122214708 * r + .5363325363 * g + .0514459929 * b,
                                                             .2119034982 * r + .6806995451 * g + .1073969566 * b,
                                                             .0883024619 * r + .2817188376 * g + .6299787005 * b))
    L, A, B = (.2104542553 * l + .7936177850 * m - .0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + .4505937099 * s,
               .0259040371 * l + .7827717662 * m - .8086757660 * s)
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360


def _oklch_lin(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l, m, s = ((L + .3963377774 * a + .2158037573 * b) ** 3, (L - .1055613458 * a - .0638541728 * b) ** 3,
               (L - .0894841775 * a - 1.2914855480 * b) ** 3)
    return (4.0767416621 * l - 3.3077115913 * m + .2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s,
            -.0041960863 * l - .7034186147 * m + 1.7076147010 * s)


def oklch_hex(L, C, h):
    """sRGB hex; chroma is reduced until the colour is inside the sRGB gamut (hue and lightness kept)."""
    L = min(max(L, 0), 1)
    lo, hi = 0.0, C
    if not all(-1e-6 <= x <= 1 + 1e-6 for x in _oklch_lin(L, C, h)):
        for _ in range(24):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if all(-1e-6 <= x <= 1 + 1e-6 for x in _oklch_lin(L, mid, h)) else (lo, mid)
        C = lo
    return "#" + "".join(f"{round(min(max(_gam(min(max(x, 0), 1)), 0), 1) * 255):02x}" for x in _oklch_lin(L, C, h))


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(h):
    r, g, b = (_lin(x) for x in hex_rgb(h))
    return .2126 * r + .7152 * g + .0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + .05) / (lo + .05)


def fit(L, C, h, against, ratio, dark):
    """Move lightness (darker in light mode, lighter in dark mode) until the colour has `ratio` on every background."""
    step = .005 if dark else -.005
    while 0 <= L <= 1:
        c = oklch_hex(L, C, h)
        if min(contrast(c, b) for b in against) >= ratio:
            return c
        L += step
    return "#ffffff" if dark else "#000000"


def roles(seed, seed2=None, dark=False):
    """Light or dark role set from seed hex colours: surfaces tinted with the seed hue, accents at the seed's hue and
    chroma, all contrast-checked."""
    _, C1, h1 = rgb_to_oklch(hex_rgb(seed))
    _, C2, h2 = rgb_to_oklch(hex_rgb(seed2 or seed))
    Ls, tint = (L_DARK if dark else L_LIGHT), min(C1 * .25, .02)
    r = {k: oklch_hex(Ls[k], tint, h1) for k in ("bg", "surface", "surface2", "border")}
    bgs = [r["bg"], r["surface"], r["surface2"]]
    r["text"] = fit(Ls["text"], min(tint, .01), h1, bgs, 4.5, dark)
    r["muted"] = fit(Ls["muted"], tint, h1, bgs, 4.5, dark)
    r["accent"] = fit(Ls["accent"], C1, h1, bgs, 4.5, dark)
    r["accent2"] = fit(Ls["accent"], C2, h2, bgs, 4.5, dark)
    r["on_accent"] = max(("#ffffff", "#000000"), key=lambda c: contrast(c, r["accent"]))
    r["focus"] = r["accent"]
    r["art_wash"] = oklch_hex(Ls["accent"], C1, h1) + WASH_ALPHA
    return {k: r[k] for k in ROLES}


def build(source, accent, accent2=None):
    """{source, l, d}: source is theme, artwork, identity or neutral."""
    return {"source": source, "l": roles(accent, accent2, False), "d": roles(accent, accent2, True)}


def _hue_gap(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def art_seeds(path):
    """(accent, accent2) hex from an image file, or None when it can't be read or has no usable colour."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            small = im.convert("RGB").resize((64, 64), Image.Resampling.BOX)
        q = small.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
        pal, total = q.getpalette(), 64 * 64
        cols = [(n / total, *rgb_to_oklch(tuple(pal[i * 3:i * 3 + 3]))) for n, i in q.getcolors()]
    except Exception:  # noqa: BLE001  missing, truncated or not an image: fall back
        return None
    chroma = [c for c in cols if c[2] >= .03]
    excited = lambda c: sum(p for p, _, _, h in chroma if _hue_gap(h, c[3]) <= 15)  # share of pixels near this hue
    ranked = sorted((c for c in chroma if excited(c) > .01), key=lambda c: excited(c) * 70 + (c[2] * 400 - 48) * (.1 if c[2] * 400 < 48 else .3), reverse=True)
    if not ranked:
        return None
    seed = ranked[0]
    alt = next((c for gap in (60, 45, 30) for c in ranked[1:] if _hue_gap(c[3], seed[3]) >= gap), None)
    hexs = lambda c: oklch_hex(c[1], c[2], c[3])
    return hexs(seed), hexs(alt) if alt else oklch_hex(seed[1], seed[2], (seed[3] + 35) % 360)


def art_file(url, raw_dir=None):
    """Cached local copy of an art crop (shared image cache, written atomically), or None when it can't be fetched."""
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import atlas  # shared download client and image check
    from edhcore.cache import cache_dir
    raw_dir = raw_dir or os.path.join(cache_dir(), "img")
    dst = os.path.join(raw_dir, "art_" + os.path.basename(url.split("?")[0]).rsplit(".", 1)[0] + ".jpg")
    if atlas.valid(dst):
        return dst
    tmp = f"{dst}.{os.getpid()}.tmp"
    try:
        os.makedirs(raw_dir, exist_ok=True)
        data = open(url[7:], "rb").read() if url.startswith("file://") else atlas.http_get(url)
        with open(tmp, "wb") as h:
            h.write(data)
        if not atlas.valid(tmp):
            raise ValueError("not an image")
        os.replace(tmp, dst)
        return dst
    except Exception:  # noqa: BLE001  offline or bad download: the caller falls back
        if os.path.exists(tmp):
            os.remove(tmp)
        return None


def resolve(theme=None, art=None, identity=None, neutral="#5a6678"):
    """Precedence: explicit theme {accent, accent2} > artwork (image path) > identity hues (a1, a2) > neutral.
    Explicit accents keep their hue; only their lightness is fixed for contrast."""
    if theme:
        return build("theme", theme["accent"], theme.get("accent2"))
    seeds = art_seeds(art) if art else None
    if seeds:
        return build("artwork", *seeds)
    if identity:
        return build("identity", *identity)
    return build("neutral", neutral)
