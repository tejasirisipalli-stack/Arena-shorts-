"""JANASEVA NEWS — 60-second faceless Telugu housing bulletin, 1080x1920.

A small broadcast-style compositor built directly on Pillow plus HarfBuzz, so the
Telugu copy is shaped and laid out correctly instead of being handed to a drawing
library that cannot join Telugu clusters (which is what distorts the script).

Design rules enforced here:
  * Telugu is drawn only through `textimg`, which shapes a whole word at a time.
  * Nothing important is placed outside the Shorts safe band (y 88..1600).
  * The panel area never shows black: the backdrop is a lit studio gradient.
  * The current 3 lakh allocation and any future allocation are drawn in visibly
    different styles (solid/confirmed vs dashed/clock) and never share a total.
"""
import functools, math, json, os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

import news_timeline as TL

W, H, FPS = 1080, 1920, TL.FPS
M = 60                                   # side margin
SAFE_TOP, SAFE_BOTTOM = 88, 1600

FONT = 'assets/Merged.ttf'
LATIN = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

BG0, BG1, BG2 = '#040a16', '#0b1a33', '#030610'
CYAN, GOLD, WHITE = '#5fe3ff', '#ffd166', '#f4f9ff'
MUTED, RED, GREEN = '#9dbccd', '#e8253f', '#4ddb9a'
INK = '#04101f'

BRAND_Y = 88
PROG_Y = 178
CHIP_Y = 204
HEAD1_Y, HEAD2_Y = 268, 414
RULE_Y = 596
PANEL = (56, 620, 1024, 1300)
MAPBOX = (10, 606, 1070, 1290)
FOOT_Y = 1316
SUB_BOX = (48, 1392, 1032, 1584)
BRAND_TEXT = TL.BRAND

# --- Telugu text shaping -----------------------------------------------------
_HB_FACE = None


def _hb_face():
    global _HB_FACE
    if _HB_FACE is None:
        import uharfbuzz as hb
        _HB_FACE = (hb.Face(open(FONT, 'rb').read()), FONT)
    return _HB_FACE


@functools.lru_cache(maxsize=4000)
def textimg(text, size, color=WHITE):
    """Shape and rasterise one run of text. Returns a tightly cropped RGBA image."""
    import uharfbuzz as hb, freetype
    face, path = _hb_face()
    font = hb.Font(face)
    font.scale = (size * 64, size * 64)
    hb.ot_font_set_funcs(font)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf)

    ft = freetype.Face(path)
    ft.set_pixel_sizes(0, size)
    width = int(sum(p.x_advance for p in buf.glyph_positions) / 64) + size
    # Telugu needs more headroom than Latin: vowel signs and the అక్షర శిరోరేఖ
    # rise well above the em box, and base glyphs descend below it.
    box_h = size * 4
    im = Image.new('RGBA', (max(width, size), box_h))
    x = size // 2
    baseline = size * 1.9
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        ft.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
        bmp = ft.glyph.bitmap
        if bmp.width and bmp.rows:
            mask = Image.frombytes('L', (bmp.width, bmp.rows), bytes(bmp.buffer))
            tile = Image.new('RGBA', mask.size, color)
            tile.putalpha(mask)
            im.alpha_composite(tile, (int(x + pos.x_offset / 64 + ft.glyph.bitmap_left),
                                      int(baseline - pos.y_offset / 64 - ft.glyph.bitmap_top)))
        x += pos.x_advance / 64
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def tw(text, size):
    """Rendered width of a run, including the shape cache."""
    return textimg(text, size).width


def fit(text, size, color=WHITE, max_w=None):
    """Shape text, shrinking until it fits `max_w`."""
    img = textimg(text, size, color)
    if max_w and img.width > max_w:
        img = img.resize((int(max_w), max(1, round(img.height * max_w / img.width))),
                         Image.Resampling.LANCZOS)
    return img


def put(im, text, y, size=44, color=WHITE, max_w=None, x=None, center=True, alpha=1.0):
    img = fit(text, size, color, max_w)
    if alpha < 1.0:
        img = img.copy()
        img.putalpha(img.getchannel('A').point(lambda a: int(a * alpha)))
    if x is None:
        x = (W - img.width) // 2 if center else M
    im.alpha_composite(img, (int(x), int(y)))
    return img


def put_run(im, text, y, size, color, x, max_w=None, alpha=1.0):
    """Left-aligned single run; returns the advance width used."""
    img = fit(text, size, color, max_w)
    if alpha < 1.0:
        img = img.copy()
        img.putalpha(img.getchannel('A').point(lambda a: int(a * alpha)))
    im.alpha_composite(img, (int(x), int(y)))
    return img.width


def rich(im, text, highlights, y, size, base=WHITE, hi=GOLD, max_w=None,
         x=None, center=True, alpha=1.0):
    """Draw `text` centred, painting any substring listed in `highlights` in `hi`."""
    if not highlights:
        return put(im, text, y, size, base, max_w, x, center, alpha)
    runs, i = [], 0
    marks = []
    for h in highlights:
        j = text.find(h, i)
        if j < 0:
            continue
        if j > i:
            runs.append((text[i:j], False))
        runs.append((text[j:j + len(h)], True))
        marks.append((j, j + len(h)))
        i = j + len(h)
    if i < len(text):
        runs.append((text[i:], False))
    # A run's own leading/trailing spaces are trimmed away when the glyph image is
    # cropped, so spaces have to be re-added as explicit gaps or the words collide.
    space_w = tw('| |', size) - tw('||', size)
    parts = []
    for t, is_hi in runs:
        if not t:
            continue
        lead = 1 if t[:1] == ' ' else 0
        trail = 1 if t[-1:] == ' ' else 0
        core = t.strip()
        img = fit(core, size, hi if is_hi else base, None) if core else None
        parts.append((img, lead * space_w, trail * space_w))
    total = sum((p.width if p else 0) + a + b for p, a, b in parts)
    scale = min(1.0, max_w / total) if max_w and total > max_w else 1.0
    if scale < 1.0:
        parts = [(p.resize((int(p.width * scale), max(1, round(p.height * scale))),
                           Image.Resampling.LANCZOS) if p else None, a * scale, b * scale)
                 for p, a, b in parts]
        total = sum((p.width if p else 0) + a + b for p, a, b in parts)
    cx = (W - total) // 2 if center else (x or M)
    for p, a, b in parts:
        cx += a
        if p is not None:
            if alpha < 1.0:
                p = p.copy()
                p.putalpha(p.getchannel('A').point(lambda q: int(q * alpha)))
            im.alpha_composite(p, (int(cx), int(y)))
            cx += p.width
        cx += b
    return total


def wrap2(text, size, max_w):
    """Naive 2-line wrap on spaces. Cues are written short enough that this is rare."""
    if tw(text, size) <= max_w:
        return [text]
    words = text.split(' ')
    best, best_diff = None, 1e18
    for k in range(1, len(words)):
        a, b = ' '.join(words[:k]), ' '.join(words[k:])
        diff = abs(tw(a, size) - tw(b, size)) + max(0, tw(a, size) - max_w) * 4 + \
            max(0, tw(b, size) - max_w) * 4
        if diff < best_diff:
            best, best_diff = (a, b), diff
    return list(best) if best else [text]


# --- easing ------------------------------------------------------------------
def clamp01(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def eout(p, k=3.0):
    return 1 - (1 - clamp01(p)) ** k


def einout(p):
    p = clamp01(p)
    return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2


def lerp(a, b, p):
    return a + (b - a) * p


def count(t, start, end, t0, dur, ease=True):
    p = clamp01((t - t0) / dur)
    p = eout(p, 3.0) if ease else p
    return start + (end - start) * p


def inr(n):
    """Indian digit grouping: 3600 -> '3,600'; 300000 -> '3,00,000'."""
    s = str(int(round(n)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ','.join(parts) + ',' + tail


# --- backdrop ----------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def _backdrop():
    im = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        p = y / H
        if p < .5:
            k = p / .5
            c = tuple(int(lerp(int(BG0[i:i + 2], 16), int(BG1[i:i + 2], 16), k * .9))
                      for i in (1, 3, 5))
        else:
            k = (p - .5) / .5
            c = tuple(int(lerp(int(BG1[i:i + 2], 16), int(BG2[i:i + 2], 16), k))
                      for i in (1, 3, 5))
        d.line((0, y, W, y), fill=c)
    # Soft studio glow behind the headline and the media panel.
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((110, 150, 970, 760), fill=(38, 122, 190, 58))
    gd.ellipse((-120, 780, 620, 1500), fill=(150, 26, 54, 34))
    gd.ellipse((520, 880, 1250, 1620), fill=(24, 96, 150, 40))
    im = Image.alpha_composite(im.convert('RGBA'), glow.filter(ImageFilter.GaussianBlur(150)))
    # Faint perspective grid for a studio-floor feel.
    gd = ImageDraw.Draw(im)
    for k in range(15):
        gd.line((-400 + k * 120, 1180, -1400 + k * 300, 1920), fill=(46, 116, 152, 26), width=2)
    for k in range(9):
        y = 1200 + k * 46
        gd.line((0, y, W, y), fill=(46, 116, 152, 18), width=1)
    return im.convert('RGB')


def particles(im, absolute):
    """Slow drifting specks so the backdrop is never static."""
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(46):
        x = (k * 233 + absolute * (11 + k % 5)) % W
        y = 120 + ((k * 317 - absolute * (13 + k % 4)) % 1500)
        a = 40 + int(46 * (math.sin(k * 1.7 + absolute * .8) ** 2))
        r = 1 + (k % 3)
        d.ellipse((x, y, x + r, y + r), fill=(110, 220, 255, a))
    im.alpha_composite(lay)


# --- furniture ---------------------------------------------------------------
def glass(im, box, radius=22, fill=(7, 19, 36, 232), edge='#2f5c78', accent=None,
          drawn=True):
    x, y, r, b = box
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=edge, width=2)
    if accent:
        d.rounded_rectangle((x, y, x + 10, b), radius=radius, fill=accent)
        d.rectangle((x + 5, y + radius // 2, x + 10, b - radius // 2), fill=accent)
    return im


def brand_badge(im, t):
    """Persistent JANASEVA NEWS lockup, top-left, inside the safe band."""
    d = ImageDraw.Draw(im)
    label = fit(BRAND_TEXT, 40, WHITE)
    bw = label.width + 112
    d.rounded_rectangle((M, BRAND_Y, M + bw, BRAND_Y + 76), radius=14, fill=(226, 32, 58))
    # Vector mark: a rounded play/eye shape, not a copied broadcaster logo.
    cx, cy, r = M + 40, BRAND_Y + 38, 17
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline='#ffffff', width=4)
    d.polygon([(cx - 5, cy - 9), (cx + 9, cy), (cx - 5, cy + 9)], fill='#ffffff')
    im.alpha_composite(label, (M + 66, BRAND_Y + 18))
    return M + bw


def top_chips(im, scene, idx):
    """Scene label on the left, AP/state tag on the right."""
    d = ImageDraw.Draw(im)
    tag = fit('ఆంధ్రప్రదేశ్ • తాజా వార్త', 32, CYAN)
    x = W - M - tag.width - 34
    d.rounded_rectangle((x, BRAND_Y + 8, W - M, BRAND_Y + 68), radius=12,
                        fill=(6, 22, 40, 220), outline='#2b5772', width=2)
    im.alpha_composite(tag, (x + 17, BRAND_Y + 16))

    # Scene progress meter: one segment per scene.
    n = len(TL.SCHEDULE)
    gap = 8
    seg_w = (W - 2 * M - gap * (n - 1)) / n
    y = PROG_Y
    for k in range(n):
        x0 = M + k * (seg_w + gap)
        d.rounded_rectangle((x0, y, x0 + seg_w, y + 10), radius=5, fill='#1b3448')
        if k < idx:
            d.rounded_rectangle((x0, y, x0 + seg_w, y + 10), radius=5, fill=CYAN)
        elif k == idx:
            d.rounded_rectangle((x0, y, x0 + seg_w, y + 10), radius=5, fill=RED)
            d.rounded_rectangle((x0, y, x0 + seg_w * clamp01(0), y + 10), radius=5, fill=RED)


def scene_chip(im, scene, t):
    """Small chapter label above the headline; slides in from the left."""
    d = ImageDraw.Draw(im)
    p = eout(t / .45, 3.0)
    lab = fit(scene['label'], 36, WHITE)
    w = lab.width + 74
    x = M - 60 * (1 - p)
    d.rounded_rectangle((x, CHIP_Y, x + w, CHIP_Y + 58), radius=12,
                        fill=(12, 38, 60, 238), outline='#3d7ea0', width=2)
    d.rounded_rectangle((x, CHIP_Y, x + 9, CHIP_Y + 58), radius=4, fill=RED)
    lay = lab.copy()
    lay.putalpha(lay.getchannel('A').point(lambda a: int(a * p)))
    im.alpha_composite(lay, (int(x + 30), CHIP_Y + 11))


@functools.lru_cache(maxsize=200)
def _extrude(text, size, accent):
    """Kinetic headline treatment: drop shadow, offset depth, shaded metal face."""
    mask = textimg(text, size, 'white').getchannel('A')
    w, h = mask.size
    pad = 26
    im = Image.new('RGBA', (w + pad * 2, h + pad * 2))
    shadow = Image.new('RGBA', im.size)
    shadow.paste((0, 0, 0, 235), (pad + 8, pad + 12, pad + 8 + w, pad + 12 + h), mask)
    im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur(7)))
    deep = (104, 40, 8) if accent else (8, 46, 84)
    for z in range(11, 0, -1):
        k = 1 - z / 12
        col = tuple(int(c * (0.55 + 0.85 * k)) for c in deep) + (255,)
        im.paste(col, (pad + z, pad + z, pad + z + w, pad + z + h), mask)
    rim = mask.filter(ImageFilter.MaxFilter(3))
    im.paste((255, 245, 214, 255) if accent else (176, 244, 255, 255),
             (pad, pad, pad + w, pad + h), rim)
    face = Image.new('RGBA', (w, h))
    fd = ImageDraw.Draw(face)
    for y in range(h):
        k = y / max(1, h - 1)
        if accent:
            fd.line((0, y, w, y), fill=(255, int(249 - 92 * k), int(168 - 132 * k), 255))
        else:
            fd.line((0, y, w, y), fill=(int(254 - 74 * k), int(255 - 40 * k), 255, 255))
    face.putalpha(mask)
    im.alpha_composite(face, (pad + 1, pad + 1))
    return im


def kinetic_line(im, text, y, t, delay, size, accent=False, max_w=None):
    """Word-by-word reveal: each word slides up, fades in and settles.

    Fitting is done on the *ink* width of each word, not on the padded canvas the
    extrusion needs, so a long line is only shrunk by as much as it has to be.
    """
    max_w = max_w or (W - 2 * M - 40)
    words = text.split(' ')
    layers = [_extrude(w, size, accent) for w in words]
    pad = 26                                     # must match _extrude
    inks = [l.width - 2 * pad for l in layers]
    gap = size * 0.17
    total = sum(inks) + gap * (len(words) - 1)
    scale = min(1.0, max_w / total) if total > 0 else 1.0
    x = (W - total * scale) / 2
    for k, lay in enumerate(layers):
        p = clamp01((t - delay - k * 0.055) / 0.42)
        if p > 0:
            e = eout(p, 3.2)
            s = (0.80 + 0.20 * e) * scale
            img = lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))),
                             Image.Resampling.BICUBIC)
            img = img.copy()
            img.putalpha(img.getchannel('A').point(lambda a: int(a * e)))
            im.alpha_composite(img, (int(x - pad * s), int(y + (1 - e) * 34)))
        x += (inks[k] + gap) * scale


@functools.lru_cache(maxsize=1)
def map_data():
    """Normalised Andhra Pradesh outline + district rings (see build_map_assets.py)."""
    return json.load(open('assets/map/ap_outline.json'))


def map_xform(box, zoom=1.0, focus=(0.5, 0.5), fit=0.94):
    """Map-normalised coords -> screen pixels for a box, with zoom about `focus`."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    d = map_data()
    base = min(bw * fit / 1.0, bh * fit / (1.0 / d['aspect']))
    s = base * zoom
    cx = x0 + bw / 2 + (0.5 - focus[0]) * s
    cy = y0 + bh / 2 + (0.5 - focus[1]) * s
    return (lambda nx, ny: (cx + (nx - 0.5) * s, cy + (ny - 0.5) * s)), s


# --- map helpers -----------------------------------------------------------------------------------------------------------------------
LINKS = None


def _inside(pt, ring):
    x, y = pt
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def pin_points(n):
    """Deterministic pin positions that actually fall inside Andhra Pradesh.

    Rejection-samples the state bounding box against the district rings, so the
    house pins never land in the sea or in a neighbouring state.
    """
    global LINKS
    if LINKS is None:
        d = map_data()
        cand = []
        seed = 12345
        while len(cand) < 700 and seed < 10 ** 9:
            seed = (seed * 1103515245 + 12345) % 2147483648
            nx = seed / 2147483648
            seed = (seed * 1103515245 + 12345) % 2147483648
            ny = seed / 2147483648
            for dist in d['districts']:
                if _inside((nx, ny), dist['rings']):
                    cand.append((nx, ny))
                    break
        cand.sort(key=lambda p: (round(p[0], 2), p[1]))
        LINKS = cand
    if not LINKS:
        return []
    k = max(1, n)
    step = len(LINKS) / k
    return [LINKS[int(i * step)] for i in range(k)]


@functools.lru_cache(maxsize=16)
def _photo(name):
    return Image.open(f'assets/ap_housing/{name}').convert('RGB')


def house_icon(im, x, y, s, color):
    """Tiny vector house. No emoji, so it can never fall back to a blank box."""
    if s <= 0.6:
        return
    d = ImageDraw.Draw(im)
    w = s * 1.25
    d.rectangle((x - w / 2, y - w * .12, x + w / 2, y + w * .5), fill=color)
    d.polygon([(x - w * .62, y - w * .1), (x, y - w * .66), (x + w * .62, y - w * .1)],
              fill=color)


def media(im, box, name, t, dur, zoom=0.06, pan=(0.5, 0.5), radius=20, wash=0.0,
          ai_badge=True):
    """Ken-Burns photo window clipped to a rounded box, with a broadcast frame."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    src = _photo(name)
    prog = clamp01(t / dur)
    z = 1.02 + zoom * prog
    fx = clamp01(pan[0] + .04 * math.sin(t * .3))
    fy = clamp01(pan[1] + .05 * math.sin(t * .24 + 1.1))
    img = ImageOps.fit(src, (int(w * z), int(h * z)), method=Image.Resampling.LANCZOS,
                       centering=(fx, fy))
    img = img.crop(((img.width - w) // 2, (img.height - h) // 2,
                    (img.width - w) // 2 + w, (img.height - h) // 2 + h)).convert('RGBA')
    if wash:
        img = Image.alpha_composite(img, Image.new('RGBA', img.size,
                                                   (3, 12, 26, int(255 * wash))))
    shade = Image.new('RGBA', (w, h))
    sd = ImageDraw.Draw(shade)
    band = int(h * .42)
    for j in range(band):
        sd.line((0, h - band + j, w, h - band + j),
                fill=(2, 8, 18, int(205 * (j / band) ** 1.7)))
    img = Image.alpha_composite(img, shade)
    mask = Image.new('L', (w, h))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    img.putalpha(mask)
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((x0 - 3, y0 - 3, x1 + 3, y1 + 3),
                                           radius=radius + 4, fill=(70, 214, 255, 92))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16)))
    im.alpha_composite(img, (x0, y0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, radius=radius, outline='#7fe9ff', width=2)
    for sx, sy, dx, dy in ((x0 + 16, y0 + 16, 1, 1), (x1 - 16, y0 + 16, -1, 1),
                           (x0 + 16, y1 - 16, 1, -1), (x1 - 16, y1 - 16, -1, -1)):
        d.line((sx, sy, sx + dx * 32, sy), fill=RED, width=4)
        d.line((sx, sy, sx, sy + dy * 32), fill=RED, width=4)
    sweep = (t * .22) % 1.0
    gx = x0 + int(40 + sweep * (w - 80))
    d.line((gx, y0 + 60, gx - 60, y0 + 150), fill=(200, 255, 255, 66), width=3)
    if ai_badge:
        badge = fit(TL.AI_LABEL, 25, '#dfeaf2')
        bx, by = x0 + (w - badge.width) // 2, y1 - 40
        d.rounded_rectangle((bx - 12, by - 6, bx + badge.width + 12, by + badge.height + 6),
                            radius=9, fill=(3, 14, 26, 232))
        im.alpha_composite(badge, (bx, by))


def draw_map(im, box, zoom=1.0, focus=(0.5, 0.5), hin='Guntur', marker=None,
             houses=None, glow=True, dim=0.0, pulse=0.0, clip=True, radius=26,
             border=True):
    """Vector Andhra Pradesh with district rings, drawn into a clipped map window.

    The layer is masked to the box so a deep zoom cannot bleed into the headline
    or caption areas; that keeps the safe bands clean at every zoom level.
    """
    d = map_data()
    tf, s = map_xform(box, zoom, focus)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    if glow:
        for wd, al in ((10, 26), (6, 44), (3, 74)):
            for dist in d['districts']:
                pts = [tf(px, py) for px, py in dist['rings']]
                ld.line(pts + [pts[0]], fill=(96, 226, 255, al), width=wd, joint='curve')
    for dist in d['districts']:
        pts = [tf(px, py) for px, py in dist['rings']]
        hot = dist['name'] == hin
        ld.polygon(pts, fill=(214, 38, 68, 246) if hot else (26, 96, 138, 244))
        ld.line(pts + [pts[0]], fill=(255, 218, 226, 255) if hot else (126, 214, 245, 255),
                width=4 if hot else 2, joint='curve')
    if houses is not None:                       # pins sit on top of the state
        drawn, total, tt = houses
        for k, (nx, ny) in enumerate(pin_points(total)[:max(0, drawn)]):
            pk = clamp01((tt - k * 0.045) / .3)
            if pk <= 0:
                continue
            x, y = tf(nx, ny)
            house_icon(lay, x, y, 18 * eout(pk, 3.0), (255, 209, 102, int(245 * pk)))
    if dim:
        lay = Image.alpha_composite(lay, Image.new('RGBA', (W, H),
                                                   (2, 8, 18, int(255 * dim))))
    if marker:
        x, y = tf(*marker)
        md = ImageDraw.Draw(lay)
        for k in range(3):
            rr = 24 + k * 17 + 5 * math.sin(pulse * 3.4 + k)
            md.ellipse((x - rr, y - rr, x + rr, y + rr),
                       outline=(255, 60, 84, max(0, 160 - k * 48)), width=3)
        md.ellipse((x - 14, y - 14, x + 14, y + 14), fill=RED, outline=WHITE, width=3)
    if clip:
        mask = Image.new('L', (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
        lay.putalpha(ImageChops.multiply(lay.getchannel('A'), mask))
    im.alpha_composite(lay)
    if clip and border:
        bd = ImageDraw.Draw(im)
        bd.rounded_rectangle(box, radius=radius, outline='#3f7f9e', width=2)
    return tf, s


# --- scenes ------------------------------------------------------------------
def scene_hook(im, t, sc, dur):
    """Scene 1 - state map with pins lighting up, then the sanctioned total."""
    draw_map(im, MAPBOX, zoom=lerp(1.0, 1.10, eout(t / dur)), focus=(0.5, 0.5),
             hin=None, dim=0.14,
             houses=(int(count(t, 1, 52, 0.15, 2.0) + 0.5), 52, 0.15))
    p = eout((t - 1.05) / .6, 3.0)
    if p <= 0:
        return
    cx0, cy0, cx1, cy1 = 250, 1000, 830, 1220
    y = int(cy0 + (1 - p) * 90)
    card = (cx0, y, cx1, y + (cy1 - cy0))
    glass(im, card, radius=22, fill=(6, 18, 34, 244), edge='#63d9f5', accent=RED)
    n = int(count(t, 0, 300000, 0.5, 2.1) + 0.5)
    put(im, inr(n), y + 24, 92, '#ffffff', max_w=480)
    put(im, 'ఇళ్లు మంజూరు', y + 146, 34, GOLD, max_w=500)


def scene_place(im, t, sc, dur):
    """Scene 2 - zoom from the state down to Tenali / Burripalem."""
    d = map_data()
    p = einout(t / (dur * .84))
    ten = d['tenali']
    focus = (lerp(0.5, ten[0], p), lerp(0.5, ten[1], p))
    zoom = lerp(1.04, 4.4, p)
    draw_map(im, MAPBOX, zoom=zoom, focus=focus, hin='Guntur',
             marker=(ten[0], ten[1]) if p > .42 else None, dim=0.06, pulse=t)
    tf, s = map_xform(MAPBOX, zoom, focus)
    cx = MAPBOX[0] + (MAPBOX[2] - MAPBOX[0]) / 2 + (ten[0] - focus[0]) * s
    cy = MAPBOX[1] + (MAPBOX[3] - MAPBOX[1]) / 2 + (ten[1] - focus[1]) * s
    dd = ImageDraw.Draw(im)
    for k in range(3):
        rr = (74 - k * 21) * (1 - p * .5) + 6 * math.sin(t * 3.2 - k)
        dd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr),
                   outline=(130, 234, 255, 96 - k * 24), width=3)
    if p > .3:
        tag = fit('బుర్రిపాలెం • తెనాలి', 34, WHITE)
        tx = 1030 - (tag.width + 36)
        dd.line((cx + 40, cy - 40, tx + 24, 690), fill=(255, 60, 84, 200), width=3)
        dd.rounded_rectangle((tx, 668, tx + tag.width + 36, 668 + tag.height + 20),
                             radius=11, fill=(176, 26, 52, 244))
        im.alpha_composite(tag, (tx + 18, 678))

    # Location breadcrumb builds up as the camera falls in.
    steps = [('ఆంధ్రప్రదేశ్', 0.02), ('గుంటూరు జిల్లా', 0.30),
             ('తెనాలి నియోజకవర్గం', 0.56), ('బుర్రిపాలెం గ్రామం', 0.80)]
    x0 = 78
    ys = [892, 964, 1036, 1108]
    dd.line((x0 + 13, ys[0] + 38, x0 + 13, ys[-1] + 38), fill=(70, 150, 185, 210), width=3)
    for (text, at), y in zip(steps, ys):
        pp = eout((t / dur - at) / .22, 3.0)
        if pp <= 0:
            continue
        img = fit(text, 40, WHITE, 460)
        plate = (x0, y, x0 + img.width + 78, y + 76)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(lay)
        pd.rounded_rectangle(plate, radius=13, fill=(6, 20, 38, 232), outline='#5fd6f2',
                             width=2)
        pd.ellipse((x0 + 4, y + 25, x0 + 24, y + 45), fill='#0d4a68')
        pd.ellipse((x0 + 9, y + 30, x0 + 19, y + 40), fill=CYAN)
        lay.putalpha(lay.getchannel('A').point(lambda a: int(a * pp)))
        im.alpha_composite(lay)
        img = img.copy()
        img.putalpha(img.getchannel('A').point(lambda a: int(a * pp)))
        im.alpha_composite(img, (x0 + 40 + int((1 - pp) * 26), y + 15))


def scene_event(im, t, sc, dur):
    """Scene 3 - the function venue, with the two participants named in text.

    No politician is depicted. The brief rules out AI-generated politicians and
    no rights-cleared photograph of the actual event is available, so the people
    are introduced typographically over a generic venue illustration, which is
    labelled on screen as AI-made.
    """
    box = (56, 620, 1024, 1052)
    media(im, box, sc['image'], t, dur, zoom=0.07, pan=(0.5, 0.58))
    put(im, 'కార్యక్రమ వేదిక — బుర్రిపాలెం', box[1] + 20, 32, '#eaf6ff', x=box[0] + 26,
        center=False)
    cards = [('కేంద్ర మంత్రి', 'శివరాజ్ సింగ్ చౌహాన్', 0.55, (24, 86, 148)),
             ('ముఖ్యమంత్రి', 'చంద్రబాబు నాయుడు', 1.75, (176, 26, 52))]
    y = 1076
    for role, name, delay, col in cards:
        p = eout((t - delay) / .5, 3.0)
        if p <= 0:
            y += 96
            continue
        x = 56 - (1 - p) * 70
        plate = (x, y, 984, y + 84)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle(plate, radius=14, fill=col + (242,))
        lay.putalpha(lay.getchannel('A').point(lambda a: int(a * p)))
        im.alpha_composite(lay)
        nm = fit(name, 46, WHITE, 640)
        nm = nm.copy()
        nm.putalpha(nm.getchannel('A').point(lambda a: int(a * p)))
        im.alpha_composite(nm, (int(x + 224), y + 16))
        put_run(im, role, y + 28, 29, '#d6e9f7', x + 26, max_w=180)
        y += 96


def scene_numbers(im, t, sc, dur):
    """Scene 4 - the 76,000 entitlement growing to the sanctioned 3,00,000."""
    box = PANEL
    glass(im, box, radius=22, fill=(6, 17, 32, 244), edge='#2f5c78', accent=RED)
    n = count(t, 76000, 300000, 0.9, 4.4)
    shown = int(round(n / 1000.0) * 1000)
    put(im, 'అర్హత నుంచి మంజూరుకు', box[1] + 24, 36, CYAN, x=box[0] + 30, center=False)
    ImageDraw.Draw(im).line((box[0] + 30, box[1] + 76, box[2] - 30, box[1] + 76),
                            fill=(58, 108, 138), width=2)
    put(im, inr(shown) if t > 0.75 else '—', box[1] + 96, 126, '#ffffff', max_w=860)
    put(im, 'ఇళ్లు', box[1] + 246, 42, GOLD)
    cols, rows = 15, 3
    x0, y0 = box[0] + 66, box[1] + 356
    dx = (box[2] - box[0] - 132) / cols
    dy = 66
    prog = clamp01((n - 76000) / (300000 - 76000))
    lit = int(round(cols * rows * (0.253 + 0.747 * prog)))
    for k in range(cols * rows):
        cx, cy = x0 + dx * ((k % cols) + .5), y0 + dy * (k // cols)
        on = k < lit
        house_icon(im, cx, cy, 30, (255, 209, 102, 242) if on else (42, 70, 92, 225))
    ry = box[1] + 590
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((box[0] + 34, ry, box[2] - 34, ry + 12), radius=6, fill='#17324a')
    d.rounded_rectangle((box[0] + 34, ry, box[0] + 34 + int((box[2] - box[0] - 68) *
                                                           (0.253 + 0.747 * prog)),
                         ry + 12), radius=6, fill=GOLD)
    mx = box[0] + 34 + int((box[2] - box[0] - 68) * 0.253)
    d.line((mx, ry - 14, mx, ry + 28), fill=RED, width=4)
    put_run(im, '76 వేలు', ry + 34, 30, '#9fb8c8', box[0] + 34)
    put_run(im, '3 లక్షలు', ry + 34, 30, GOLD, box[2] - 190)


def scene_printing(im, t, sc, dur):
    """Scene 5 - the 177-house 3D printing pilot and its budget."""
    box = (56, 620, 1024, 1116)
    media(im, box, sc['image'], t, dur, zoom=0.09, pan=(0.52, 0.62))
    chip = fit('3D కాంక్రీట్ ప్రింటింగ్', 34, WHITE, 520)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((box[0] + 20, box[1] + 18, box[0] + 20 + chip.width + 44,
                         box[1] + 18 + chip.height + 20), radius=12,
                        fill=(4, 16, 30, 238), outline='#7fe9ff', width=2)
    im.alpha_composite(chip, (box[0] + 42, box[1] + 28))
    cards = [((56, 1140, 540, 1286), '177', 'ఇళ్లు', 'పైలట్ ప్రాజెక్ట్', GOLD, 2.4),
             ((556, 1140, 1024, 1286), '₹14 కోట్లు', '', 'అంచనా వ్యయం', CYAN, 3.9)]
    for (card, val, unit, sub, col, delay) in cards:
        p = eout((t - delay) / .55, 3.0)
        if p <= 0:
            continue
        y = int(card[1] + (1 - p) * 56)
        bx = (card[0], y, card[2], y + card[3] - card[1])
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        glass(lay, bx, radius=18, fill=(6, 18, 34, 246), edge=col, accent=col)
        lay.putalpha(lay.getchannel('A').point(lambda a: int(a * p)))
        im.alpha_composite(lay)
        v = fit(val, 66, col, card[2] - card[0] - 40)
        v = v.copy()
        v.putalpha(v.getchannel('A').point(lambda a: int(a * p)))
        im.alpha_composite(v, (card[0] + 24, y + 16))
        if unit:
            put_run(im, unit, y + 30, 32, '#e7f4ff', card[0] + 30 + v.width, max_w=140)
        sb = fit(sub, 26, MUTED)
        sb = sb.copy()
        sb.putalpha(sb.getchannel('A').point(lambda a: int(a * p)))
        im.alpha_composite(sb, (card[0] + 24, y + 112))


    # Texture inset inside the photo, so the number cards stay unobstructed.
    p = eout((t - 5.4) / .5, 3.0)
    if p > 0:
        ib = (604, 800, 1000, 1092)
        media(im, ib, 'printed_wall.jpg', t, dur, zoom=0.06, radius=14, ai_badge=False)
        put(im, 'ప్రింటెడ్ గోడ నిర్మాణం', ib[3] + 4, 25, MUTED, x=ib[0] + 4, center=False)


def scene_target(im, t, sc, dur):
    """Scene 6 - the six-month completion target, drawn as a target."""
    box = (56, 620, 1024, 1080)
    media(im, box, sc['image'], t, dur, zoom=0.06, pan=(0.45, 0.5), wash=0.22)
    d = ImageDraw.Draw(im)
    tag = fit('నిర్మాణ లక్ష్యం', 32, WHITE)
    d.rounded_rectangle((box[0] + 20, box[1] + 16, box[0] + 20 + tag.width + 40,
                         box[1] + 16 + tag.height + 18), radius=11, fill=(176, 26, 52, 242))
    im.alpha_composite(tag, (box[0] + 40, box[1] + 25))
    # A plan timeline, not a progress bar: every month stays hollow so nothing on
    # screen can read as "these houses are already finished". A cursor sweeps the
    # months and stops on month six under a target flag.
    bx0, by0, bx1 = 96, 1096, 984
    cw = (bx1 - bx0) / 6
    sweep = clamp01((t - 0.9) / (dur * .62))
    cursor = sweep * 6
    for k in range(6):
        x = bx0 + k * cw
        cell = (x + 6, by0, x + cw - 6, by0 + 118)
        reached = cursor >= k + .5
        d.rounded_rectangle(cell, radius=12, fill=(10, 30, 50, 232),
                            outline=CYAN if reached else '#2e5468', width=3)
        lab = fit(f'{k + 1}', 52, '#dff2fb' if reached else '#5d7d92')
        im.alpha_composite(lab, (int(x + cw / 2 - lab.width / 2), by0 + 16))
        u = fit('నెల', 24, '#9dc2d6' if reached else '#4c6d80')
        im.alpha_composite(u, (int(x + cw / 2 - u.width / 2), by0 + 78))
    # Target flag rises over the sixth month as the cursor arrives.
    if cursor > 5.2:
        fx = bx0 + 5 * cw + cw / 2
        d.line((fx, by0 - 12, fx, by0 - 62), fill=GOLD, width=5)
        d.polygon([(fx, by0 - 62), (fx + 34, by0 - 50), (fx, by0 - 38)], fill=GOLD)
    put(im, 'ఇది లక్ష్యం — పూర్తయిన గడువు కాదు', 1216, 28, GOLD, max_w=940)
    put(im, 'సుమారు 6 నెలల్లో పూర్తి చేయాలనే లక్ష్యం', 1266, 30, WHITE, max_w=940)


def scene_future(im, t, sc, dur):
    """Scene 7 - sanctioned today vs a possible future allocation.

    The two blocks are deliberately unequal: the current allocation is solid with
    a tick, the proposal is dashed with a clock, and the two are never summed.
    """
    d = ImageDraw.Draw(im)
    a = (56, 888, 1024, 1112)
    glass(im, a, radius=20, fill=(9, 30, 50, 248), edge=GOLD, accent=GOLD)
    put_run(im, 'ప్రస్తుతం మంజూరు', 910, 32, GOLD, 90, max_w=360)
    val = fit('3 లక్షల ఇళ్లు', 76, '#ffffff', 520)
    im.alpha_composite(val, (92, 944))
    d.ellipse((690, 932, 762, 1004), outline=GREEN, width=6)
    d.line((709, 968, 725, 985, 745, 950), fill=GREEN, width=7)
    put_run(im, 'కేంద్ర మంత్రి ప్రకటన ప్రకారం ఖాయం', 1040, 27, '#cfe6f2', 92,
            max_w=760)

    b = (56, 620, 1024, 868)
    p2 = eout((t - 1.3) / .6, 3.0)
    if p2 > 0:
        yoff = int((1 - p2) * 36)
        bx = (b[0], b[1] + yoff, b[2], b[3] + yoff)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle(bx, radius=20, fill=(10, 22, 36, 238))
        step = 18
        for cx in range(bx[0] + 16, bx[2] - 10, step):
            ld.line((cx, bx[1], min(cx + 10, bx[2] - 10), bx[1]), fill=(152, 180, 198), width=3)
            ld.line((cx, bx[3], min(cx + 10, bx[2] - 10), bx[3]), fill=(152, 180, 198), width=3)
        for cy in range(bx[1] + 16, bx[3] - 10, step):
            ld.line((bx[0], cy, bx[0], min(cy + 10, bx[3] - 10)), fill=(152, 180, 198), width=3)
            ld.line((bx[2], cy, bx[2], min(cy + 10, bx[3] - 10)), fill=(152, 180, 198), width=3)
        lay.putalpha(lay.getchannel('A').point(lambda a: int(a * p2)))
        im.alpha_composite(lay)
        for item, yy, sz, col in (('భవిష్యత్ దశ • అవకాశం', bx[1] + 22, 29, '#bcd2e0'),
                                  ('మరో 3 లక్షలు', bx[1] + 66, 66, '#d3e3ee'),
                                  ('నిర్మాణం పూర్తయిన తర్వాత మాత్రమే', bx[1] + 156, 27,
                                   '#9fb8c8')):
            img = fit(item, sz, col, 700)
            img = img.copy()
            img.putalpha(img.getchannel('A').point(lambda a: int(a * p2)))
            im.alpha_composite(img, (92, yy))
        ccx, ccy = 930, bx[1] + 88
        d.ellipse((ccx - 30, ccy - 30, ccx + 30, ccy + 30), outline='#9fb8c8', width=5)
        ang = t * 1.5
        d.line((ccx, ccy, ccx + 19 * math.sin(ang), ccy - 19 * math.cos(ang)),
               fill='#9fb8c8', width=5)

    c = (56, 1126, 1024, 1284)
    p3 = eout((t - 2.9) / .55, 3.0)
    if p3 > 0:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        glass(lay, c, radius=18, fill=(11, 26, 44, 240), edge='#3c6a8c', accent='#5fd6f2')
        lay.putalpha(lay.getchannel('A').point(lambda a: int(a * p3)))
        im.alpha_composite(lay)
        for item, yy, sz, col in (('సీఎం అభ్యర్థన', c[1] + 22, 28, CYAN),
                                  ('మరో 6 లక్షల ఇళ్లు కోరినట్లు', c[1] + 60, 36, WHITE),
                                  ('కేంద్ర మంత్రి వెల్లడి', c[1] + 112, 26, MUTED)):
            img = fit(item, sz, col, 820)
            img = img.copy()
            img.putalpha(img.getchannel('A').point(lambda a: int(a * p3)))
            im.alpha_composite(img, (92, yy))


def scene_cta(im, t, sc, dur):
    """Scene 8 - the branded sign-off, ending on a two-second logo lockup."""
    box = PANEL
    lock = t >= dur - 2.0
    if not lock:
        media(im, box, 'finished_house.jpg', t, dur, zoom=0.08, pan=(0.5, 0.55), wash=0.28)
        put(im, 'పక్కా ఇళ్లు', box[1] + 20, 32, '#eaf6ff', x=box[0] + 26,
            center=False)
        p = eout((t - .3) / .55, 3.0)
        if p > 0:
            pill = (140, 1100, 940, 1210)
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lay).rounded_rectangle(pill, radius=22, fill=(226, 32, 58, 242),
                                                  outline='#ffb3bf', width=3)
            lay.putalpha(lay.getchannel('A').point(lambda a: int(a * p)))
            im.alpha_composite(lay)
            img = fit('ఫాలో అవ్వండి', 46, WHITE)
            img = img.copy()
            img.putalpha(img.getchannel('A').point(lambda a: int(a * p)))
            im.alpha_composite(img, (W // 2 - img.width // 2, 1126))
        return

    glass(im, box, radius=22, fill=(5, 15, 30, 250), edge='#63d9f5', accent=RED)
    p = eout((t - (dur - 2.0)) / .55, 3.0)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    moon = Image.new('RGBA', (216, 216), (0, 0, 0, 0))
    md = ImageDraw.Draw(moon)
    md.ellipse((10, 10, 206, 206), outline=(226, 32, 58, 255), width=12)
    md.ellipse((50, 50, 166, 166), outline=(95, 227, 255, 255), width=6)
    md.polygon([(88, 76), (150, 108), (88, 140)], fill=(255, 255, 255, 255))
    lay.alpha_composite(moon, (W // 2 - 108, 636))
    lay.putalpha(lay.getchannel('A').point(lambda a: int(a * p)))
    im.alpha_composite(lay)
    for text, y, size, col in ((BRAND_TEXT, 908, 92, WHITE),
                               (TL.PAYOFF, 1038, 36, GOLD),
                               ('మరిన్ని AP వార్తల కోసం', 1236, 30, MUTED)):
        img = fit(text, size, col, 900)
        img = img.copy()
        img.putalpha(img.getchannel('A').point(lambda a: int(a * p)))
        im.alpha_composite(img, (W // 2 - img.width // 2, y))
    pill = (300, 1112, 780, 1204)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle(pill, radius=20, fill=(226, 32, 58),
                                          outline='#ffb3bf', width=3)
    lay.putalpha(lay.getchannel('A').point(lambda a: int(a * p)))
    im.alpha_composite(lay)
    img = fit('ఫాలో అవ్వండి', 44, WHITE)
    img = img.copy()
    img.putalpha(img.getchannel('A').point(lambda a: int(a * p)))
    im.alpha_composite(img, (W // 2 - img.width // 2, 1126))


# --- subtitles ---------------------------------------------------------------
def subtitle_bar(im, cue):
    """Bottom caption plate: at most two Telugu lines, figures highlighted."""
    x0, y0, x1, y1 = SUB_BOX
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle((x0, y0, x1, y1), radius=20, fill=(4, 13, 25, 232),
                                          outline='#2c5b76', width=2)
    im.alpha_composite(lay)
    ImageDraw.Draw(im).rounded_rectangle((x0, y0, x0 + 9, y1), radius=4, fill=RED)
    if not cue:
        return
    text, hi = cue
    size = 44
    lines = wrap2(text, size, (x1 - x0) - 96)
    y = y0 + (64 if len(lines) == 1 else 38)
    for ln in lines:
        rich(im, ln, hi, y, size, base='#f4f9ff', hi=GOLD, max_w=(x1 - x0) - 90)
        y += 62


# --- frame assembly ----------------------------------------------------------
SCENE_FN = {
    'map_overview': scene_hook, 'map_zoom': scene_place, 'photo': scene_event,
    'counter': scene_numbers, 'split': scene_printing, 'time': scene_target,
    'compare': scene_future, 'cta': scene_cta,
}


def frame(idx, t, absolute, active_cue=None):
    im = _backdrop().convert('RGBA')
    particles(im, absolute + idx * 3.3)
    sc = TL.SCENES[idx]
    dur = TL.SCHEDULE[idx] / FPS

    # Scene transition: a fast diagonal light wipe, never a black gap.
    if t < 0.34:
        p = t / 0.34
        wl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        wd = ImageDraw.Draw(wl)
        x = int(-700 + p * 2500)
        wd.polygon([(x - 150, 0), (x, 0), (x - 560, H), (x - 750, H)],
                   fill=(86, 226, 255, 64))
        wd.polygon([(x, 0), (x + 30, 0), (x - 530, H), (x - 560, H)],
                   fill=(240, 255, 255, 120))
        im = Image.alpha_composite(im, wl)

    brand_badge(im, t)
    top_chips(im, sc, idx)
    scene_chip(im, sc, t)
    for (htext, hacc, hsize), hy, hdelay in ((sc['head'][0], HEAD1_Y, 0.06),
                                             (sc['head'][1], HEAD2_Y, 0.30)):
        kinetic_line(im, htext, hy, t, hdelay, hsize, hacc, max_w=920)

    d = ImageDraw.Draw(im)
    p = eout((t - .55) / .55, 3.0)
    d.rectangle((M, RULE_Y, M + 300, RULE_Y + 6), fill='#22405a')
    d.rectangle((M, RULE_Y, M + int(300 * p), RULE_Y + 6), fill=RED)

    SCENE_FN[sc['visual']](im, t, sc, dur)
    put_run(im, sc['footnote'], FOOT_Y, 27, MUTED, M + 4, max_w=960)
    subtitle_bar(im, active_cue)

    # A gentle top/bottom vignette; the picture itself is never crushed to black.
    vig = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig)
    vd.rectangle((0, 0, W, 56), fill=(0, 0, 0, 140))
    vd.rectangle((0, H - 110, W, H), fill=(0, 0, 0, 160))
    im = Image.alpha_composite(im, vig.filter(ImageFilter.GaussianBlur(60)))
    return im.convert('RGB')
