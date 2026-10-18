"""Venus day-vs-year Telugu short: animated space compositor.

Backgrounds are AI-generated still plates animated with procedural camera
moves and overlays (B-roll style footage); the presenter is chroma-keyed from
the uploaded green-screen photos (dark circles retouched) and kept in constant
motion with amplitude-driven lip movement.  Telugu kinetic typography is shaped
with uharfbuzz + freetype, same as make_video.py.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import math, functools
import numpy as np
import uharfbuzz as hb, freetype

W, H, FPS = 1080, 1920, 24
FONT = 'assets/Merged.ttf'
_fontdata = open(FONT, 'rb').read()
_face = hb.Face(_fontdata)
GOLD = '#ffd76a'; WHITE = '#f6fbff'; CYAN = '#8ef0ff'; DIM = '#cfe3ee'

# ---------------------------------------------------------------- text shaping
@functools.lru_cache(maxsize=512)
def textimg(text, size, color=WHITE):
    font = hb.Font(_face); font.scale = (size * 64, size * 64); hb.ot_font_set_funcs(font)
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(font, buf)
    ft = freetype.Face(FONT); ft.set_pixel_sizes(0, size)
    width = int(sum(p.x_advance for p in buf.glyph_positions) / 64) + 16
    im = Image.new('RGBA', (max(width, 1), size * 3)); x = 5; baseline = size * 1.6
    for info, p in zip(buf.glyph_infos, buf.glyph_positions):
        ft.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER); g = ft.glyph; b = g.bitmap
        if b.width and b.rows:
            mask = Image.frombytes('L', (b.width, b.rows), bytes(b.buffer))
            tile = Image.new('RGBA', mask.size, color); tile.putalpha(mask)
            im.alpha_composite(tile, (int(x + p.x_offset / 64 + g.bitmap_left),
                                      int(baseline - p.y_offset / 64 - g.bitmap_top)))
        x += p.x_advance / 64
    box = im.getbbox()
    return im.crop(box) if box else im

@functools.lru_cache(maxsize=512)
def glowtext(text, size, color=WHITE, glow=None):
    """Keyword chip: soft shadow + coloured halo + face, cached per word."""
    face = textimg(text, size, color)
    pad = int(size * 0.55)
    im = Image.new('RGBA', (face.width + pad * 2, face.height + pad * 2))
    sh = Image.new('RGBA', im.size); sh.paste((0, 0, 0, 125), (pad + 4, pad + 6, pad + 4 + face.width, pad + 6 + face.height), face.getchannel('A'))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(9)))
    gl = Image.new('RGBA', im.size); gl.paste(glow or color, (pad, pad, pad + face.width, pad + face.height), face.getchannel('A'))
    im = Image.alpha_composite(im, gl.filter(ImageFilter.GaussianBlur(int(size * 0.22))))
    im.alpha_composite(face, (pad, pad))
    return im

# ------------------------------------------------------------- presenter prep
LOOKS = 4
# normalised (x, y) in the source green-screen photos
EYES = {1: ((0.376, 0.217), (0.474, 0.216)), 2: ((0.374, 0.217), (0.472, 0.216)),
        3: ((0.387, 0.211), (0.484, 0.210)), 4: ((0.380, 0.170), (0.484, 0.169))}
MOUTH = {1: (0.426, 0.265), 2: (0.424, 0.265), 3: (0.436, 0.258), 4: (0.432, 0.231)}
AV_H = 760                      # small, zoomed-out presenter
AV_X, AV_Y = 86, 1080           # left side, top below centre, feet above bottom

def _key_green(im):
    a = np.asarray(im.convert('RGB')).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    over = g - (r + b) / 2.0                        # positive only on green spill
    alpha = np.clip(1.0 - (over - 10) / 50.0, 0, 1)
    alpha = (alpha * 255).astype(np.uint8)
    m = Image.fromarray(alpha, 'L').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.1))
    g2 = np.minimum(g, (r + b) / 2.0 + 16)          # despill
    rgb = np.stack([r, g2, b], -1).astype(np.uint8)
    return Image.fromarray(rgb, 'RGB'), m

def _retouch(rgb, mask, i):
    """Soften dark circles: feathered blend of a brightened blurred skin patch."""
    a = np.asarray(rgb).astype(np.float32)
    w, h = rgb.size
    blur = np.asarray(rgb.filter(ImageFilter.GaussianBlur(7))).astype(np.float32)
    blur = np.clip(blur * 1.17 + np.array([5, 3, 1]), 0, 255)
    m = np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for ex, ey in EYES[i]:
        cx, cy = ex * w, ey * h + 0.020 * h
        d = ((xx - cx) / (0.052 * w)) ** 2 + ((yy - cy) / (0.020 * h)) ** 2
        m = np.maximum(m, np.clip(1 - d, 0, 1))
    m = (m * (np.asarray(mask, np.float32) / 255.0))[..., None]
    out = a * (1 - m) + blur * m
    return Image.fromarray(out.astype(np.uint8), 'RGB')

AVATARS, MOUTH_PX = {}, {}
def _build_avatars():
    for i in range(1, LOOKS + 1):
        src = Image.open(f'assets/raw/look{i}.png')
        rgb, mask = _key_green(src)
        rgb = _retouch(rgb, mask, i)
        rgba = rgb.convert('RGBA'); rgba.putalpha(mask)
        s = AV_H / src.height
        rgba = rgba.resize((round(src.width * s), AV_H), Image.Resampling.LANCZOS)
        AVATARS[i] = rgba
        MOUTH_PX[i] = (MOUTH[i][0] * rgba.width, MOUTH[i][1] * rgba.height)

# ------------------------------------------------------------------- bg plates
PLATE_SZ = (1296, 2304)
def _plate(path, dim=1.0):
    im = Image.open(path).convert('RGB').resize(PLATE_SZ, Image.Resampling.LANCZOS)
    if dim != 1.0:
        im = Image.fromarray((np.asarray(im, np.float32) * dim).astype(np.uint8))
    return im

BG = {}
def _build_plates():
    BG['nebula'] = _plate('assets/gen/bg_nebula.jpg')
    BG['venus_space'] = _plate('assets/gen/bg_venus_space.jpg')
    BG['orbits'] = _plate('assets/gen/bg_orbits.jpg', 0.62)
    BG['surface'] = _plate('assets/gen/bg_venus_surface.jpg')
    BG['surface_dim'] = _plate('assets/gen/bg_venus_surface.jpg', 0.66)
    BG['galaxy'] = _plate('assets/gen/bg_galaxy.jpg')
    BG['nebula_dim'] = _plate('assets/gen/bg_nebula.jpg', 0.72)
    # spinning-planet texture: two interior crops cross-faded into one strip; an
    # oscillating window scrolls across it, so no wrap seam can appear on the disc
    A = np.asarray(BG['venus_space'].crop((330, 430, 1010, 1110))).astype(np.float32)
    B = np.asarray(BG['venus_space'].crop((250, 520, 930, 1200))).astype(np.float32)
    F = 200
    fade = np.linspace(0, 1, F)[None, :, None]
    J = A[:, -F:] * (1 - fade) + B[:, :F] * fade
    ta = np.concatenate([A[:, :-F], J, B[:, F:]], 1)
    wdt = hgt = 680
    xx, yy = np.mgrid[0:hgt, 0:wdt].astype(np.float32)
    cx = cy = (wdt - 1) / 2
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / cx
    shade = np.clip(1.18 - 0.62 * rr ** 2.1, 0.25, 1.18)
    shade *= np.clip(0.62 + 0.55 * np.clip(-(xx - cx) / cx, 0, 1) ** 1.2, 0, 1.25)  # key light from left
    BG['spin_shade'] = shade[..., None].astype(np.float32)
    BG['spin_tex'] = Image.fromarray(ta.astype(np.uint8))
    BG['spin_wh'] = (wdt, hgt)
    BG['spin_rng'] = ta.shape[1] - wdt
    disc = Image.new('L', (wdt, hgt))
    ImageDraw.Draw(disc).ellipse((0, 0, wdt - 1, hgt - 1), fill=255)
    BG['spin_mask'] = disc.filter(ImageFilter.GaussianBlur(3))

OILS = []
def _build_oils():
    for p in ('assets/gen/oil_paint_1.png', 'assets/gen/oil_paint_3.png'):
        OILS.append(Image.open(p).convert('RGB'))

VIGNETTE = None
def _build_vignette():
    global VIGNETTE
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.60)) ** 2)
    a = np.clip((d - 0.72) / 0.55, 0, 1) ** 1.6 * 120
    VIGNETTE = Image.fromarray(a.astype(np.uint8), 'L')

# ------------------------------------------------------------------- scene spec
# (bg, camera move, overlay kind, look, keywords[(text,t0,style,y,size,color)], oil)
SCENES = [
    dict(bg='nebula',     cam=('push', 1.06, 1.17, .5, .44, .5, .40, 0, 0),      fx='twinkle', look=1,
         kw=[('మీకు తెలుసా?', .55, 'pop', 300, 112, GOLD)]),
    dict(bg='venus_space', cam=('pan', 1.14, 1.14, .40, .45, .60, .45, 0, 0),     fx='streaks', look=2,
         kw=[('శుక్రగ్రహం', 1.0, 'pop', 246, 100, CYAN), ('ఒక రోజు > ఒక సంవత్సరం', 3.1, 'slide_up', 420, 72, WHITE)]),
    dict(bg='nebula_dim', cam=('dutch', 1.10, 1.16, .5, .46, .5, .46, -2.2, 2.2), fx='spin',    look=3,
         kw=[('తన చుట్టూ తిరుగుతూ', .4, 'slide_r', 250, 62, WHITE), ('243 భూమి రోజులు', 2.6, 'pop', 396, 90, GOLD)]),
    dict(bg='orbits',     cam=('rise', 1.08, 1.18, .5, .60, .5, .44, 0, 0),       fx='orbit',   look=4,
         kw=[('సూర్యుడి చుట్టూ ప్రదక్షిణ', .4, 'slide_up', 248, 60, WHITE), ('225 రోజులే!', 2.6, 'pop', 392, 94, GOLD)]),
    dict(bg='surface_dim', cam=('sweep', 1.12, 1.18, .5, .48, .5, .46, 2.6, -2.0), fx='rings',   look=2,
         kw=[('రోజు పూర్తికాక ముందే', .4, 'slide_r', 250, 64, WHITE), ('సంవత్సరం ముగిసింది!', 2.1, 'pop', 396, 86, GOLD)]),
    dict(bg='surface',    cam=('push', 1.18, 1.30, .5, .42, .5, .38, 0, 0),       fx='clock',   look=3,
         kw=[('అతి నెమ్మది భ్రమణం', .4, 'pop', 258, 82, CYAN), ('అదే కారణం', 2.5, 'slide_up', 408, 58, WHITE)], oil=(1, 3.0)),
    dict(bg='galaxy',     cam=('pull', 1.24, 1.06, .5, .46, .5, .50, 0, 0),       fx='shoot',   look=4,
         kw=[('విశ్వంలో అద్భుతాలు ఎన్నో!', .5, 'pop', 300, 84, GOLD)], oil=(1, 0.9)),
]

STARS = [(hash((k, 1)) % 1000 / 1000, hash((k, 2)) % 1000 / 1000, hash((k, 3)) % 628 / 100, 1 + hash((k, 4)) % 3) for k in range(90)]
DUST = [(hash((k, 5)) % 1000 / 1000, hash((k, 6)) % 1000 / 1000, hash((k, 7)) % 628 / 100) for k in range(42)]

ENV = None          # per-frame speech amplitude (lip sync)
DURS, STARTS = [], []

def setup(durs, starts, env):
    global DURS, STARTS, ENV
    DURS, STARTS, ENV = durs, starts, env
    if not AVATARS: _build_avatars()
    if not BG: _build_plates()
    if not OILS: _build_oils()
    if VIGNETTE is None: _build_vignette()

def _ease(u): return 1 - (1 - u) ** 3

def camera(spec, t, dur):
    kind, z0, z1, ax, ay, bx, by, r0, r1 = spec
    u = _ease(max(0, min(1, t / dur)))
    z = z0 + (z1 - z0) * u
    cx = (ax + (bx - ax) * u) * PLATE_SZ[0]
    cy = (ay + (by - ay) * u) * PLATE_SZ[1]
    rot = r0 + (r1 - r0) * u
    plate = BG[spec[0]]
    cw, ch = int(PLATE_SZ[0] / z), int(PLATE_SZ[1] / z)
    x = int(cx - cw / 2); y = int(cy - ch / 2)
    x = max(0, min(PLATE_SZ[0] - cw, x)); y = max(0, min(PLATE_SZ[1] - ch, y))
    im = plate.crop((x, y, x + cw, y + ch))
    if abs(rot) > 0.05:
        im = im.rotate(rot, Image.Resampling.BILINEAR, expand=False)
        mx, my = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((mx, my, mx + W, my + H))
    return im.resize((W, H), Image.Resampling.BILINEAR).convert('RGBA')

def _twinkle(d, t, n=90, amp=1.0):
    for fx, fy, ph, sz in STARS[:n]:
        a = int((35 + 60 * math.sin(t * 1.8 + ph) ** 2) * amp)
        x, y = fx * W, fy * H * 0.9
        d.ellipse((x, y, x + sz, y + sz), fill=(235, 245, 255, a))

def _dust(d, t):
    for fx, fy, ph in DUST:
        x = (fx * W + t * 26 + 14 * math.sin(t * .7 + ph)) % W
        y = (fy * H - t * 34) % H
        a = 40 + int(50 * math.sin(t + ph) ** 2)
        d.ellipse((x, y, x + 3, y + 3), fill=(255, 226, 170, a))

def fx_overlay(im, kind, t, dur):
    d = ImageDraw.Draw(im)
    if kind == 'twinkle':
        _twinkle(d, t); _dust(d, t)
    elif kind == 'streaks':
        _twinkle(d, t, 40, .8)

    elif kind == 'spin':
        _twinkle(d, t, 60)
        tex, mask, shade = BG['spin_tex'], BG['spin_mask'], BG['spin_shade']
        wdt, hgt = BG['spin_wh']
        u = (t % 18.0) / 18.0
        p = int(BG['spin_rng'] * (2 * u if u < 0.5 else 2 - 2 * u))
        strip = tex.crop((p, 0, p + wdt, hgt))
        arr = np.asarray(strip, np.float32) * shade
        disc = Image.fromarray(arr.astype(np.uint8), 'RGB').resize((640, 640), Image.Resampling.BILINEAR)
        glow = Image.new('RGBA', (740, 740), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow); gd.ellipse((30, 30, 710, 710), fill=(255, 205, 120, 60))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26)), (270, 710))
        disc = disc.convert('RGBA'); disc.putalpha(mask.resize((640, 640)))
        im.alpha_composite(disc, (300, 760))
        d = ImageDraw.Draw(im)
        d.arc((300, 760, 940, 1400), 0, 360, fill=(255, 214, 140, 120), width=3)
        _dust(d, t)
    elif kind == 'orbit':
        _twinkle(d, t, 50)
        cx, cy = 540, 1010
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        gd.ellipse((cx - 190, cy - 190, cx + 190, cy + 190), fill=(255, 214, 130, 120))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(40)))
        core = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(core).ellipse((cx - 80, cy - 80, cx + 80, cy + 80), fill=(255, 240, 190, 255))
        im.alpha_composite(core.filter(ImageFilter.GaussianBlur(12)))
        d = ImageDraw.Draw(im)
        for r, col in ((250, (255, 214, 140, 150)), (400, (140, 220, 255, 120))):
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=3)
        av = t / dur * 0.92 * 2 * math.pi - 1.2
        for k in range(14):                                  # Venus dot + trail
            a = av - k * 0.045
            x, y = cx + 250 * math.cos(a), cy + 250 * math.sin(a)
            d.ellipse((x - 9 + k * .3, y - 9 + k * .3, x + 9 - k * .3, y + 9 - k * .3), fill=(255, 205, 120, 235 - k * 15))
        ea = t / dur * 0.92 * (225 / 365) * 2 * math.pi + 2.4
        x, y = cx + 400 * math.cos(ea), cy + 400 * math.sin(ea)
        d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(140, 220, 255, 230))
        lbl = textimg('శుక్రగ్రహం', 30, GOLD); im.alpha_composite(lbl, (int(cx + 250 * math.cos(av)) + 14, int(cy + 250 * math.sin(av)) - 40))
        lbl = textimg('భూమి', 30, CYAN); im.alpha_composite(lbl, (int(cx + 400 * math.cos(ea)) + 14, int(cy + 400 * math.sin(ea)) - 40))
    elif kind == 'rings':
        _twinkle(d, t, 45)
        cx, cy = 620, 1010
        py = max(0, min(1, t / (dur * 0.68)))
        pd = py * (225 / 243) + max(0, t - dur * 0.68) / dur * 0.05
        d.ellipse((cx - 300, cy - 300, cx + 300, cy + 300), outline=(140, 220, 255, 38), width=12)
        d.arc((cx - 300, cy - 300, cx + 300, cy + 300), -90, -90 + int(360 * min(pd, 1)), fill=(140, 230, 255, 235), width=24)
        d.ellipse((cx - 210, cy - 210, cx + 210, cy + 210), outline=(255, 214, 140, 38), width=12)
        d.arc((cx - 210, cy - 210, cx + 210, cy + 210), -90, -90 + int(360 * py), fill=(255, 214, 140, 240), width=24)
        if py >= 1:                                          # year finishes first: flash
            k = int(60 * abs(math.sin(t * 5)))
            d.ellipse((cx - 214 - k // 4, cy - 214 - k // 4, cx + 214 + k // 4, cy + 214 + k // 4), outline=(255, 240, 190, 150), width=4)
        l1 = textimg('సంవత్సరం', 34, GOLD); im.alpha_composite(l1, (cx + 226, cy - 17))
        l2 = textimg('రోజు', 34, CYAN); im.alpha_composite(l2, (cx - 300 - l2.width - 16, cy - 17))
        pc = textimg(f'{int(pd * 100)}%', 44, WHITE); im.alpha_composite(pc, (cx - pc.width // 2, cy - 30))
    elif kind == 'clock':
        _dust(d, t); _twinkle(d, t, 35, .7)
        cx, cy, r = 700, 700, 200
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(8, 14, 26, 150), outline=(255, 226, 160, 200), width=5)
        for k in range(12):
            a = math.radians(k * 30)
            d.line((cx + (r - 26) * math.cos(a), cy + (r - 26) * math.sin(a), cx + (r - 8) * math.cos(a), cy + (r - 8) * math.sin(a)), fill=(255, 226, 160, 210), width=4)
        ha = t * 2.2 - 90                                    # painfully slow hand
        d.line((cx, cy, cx + (r - 90) * math.cos(math.radians(ha)), cy + (r - 90) * math.sin(math.radians(ha))), fill=(255, 240, 200, 240), width=9)
        ma = t * 0.55 - 90
        d.line((cx, cy, cx + (r - 45) * math.cos(math.radians(ma)), cy + (r - 45) * math.sin(math.radians(ma))), fill=(140, 230, 255, 220), width=5)
        d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=(255, 240, 200, 255))
    elif kind == 'shoot':
        _twinkle(d, t)
        for k, t0 in enumerate((0.5, 1.9, 3.2)):
            lt = t - t0
            if 0 < lt < 0.8:
                p = lt / 0.8
                x0, y0 = 180 + k * 300, 180 + k * 130
                x, y = x0 + p * 520, y0 + p * 300
                a = int(210 * (1 - p))
                d.line((x - 240, y - 138, x, y), fill=(255, 255, 255, a), width=4)
                d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(255, 255, 255, min(255, a + 40)))
    return im

def oil_card(im, idx, t, t0):
    p = _ease(max(0, min(1, (t - t0) / 0.8)))
    if p <= 0: return im
    src = OILS[idx]
    cw, ch = 400, 560
    card = ImageOps.fit(src, (cw, ch), method=Image.Resampling.LANCZOS).convert('RGBA')
    sway = 2.4 * math.sin(t * 1.1 + idx)
    card = card.rotate(sway, Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
    frameim = Image.new('RGBA', (card.width + 26, card.height + 26), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frameim)
    fd.rounded_rectangle((0, 0, frameim.width - 1, frameim.height - 1), radius=16, fill=(58, 38, 16, 255), outline=(214, 168, 84, 255), width=5)
    fd.rounded_rectangle((9, 9, frameim.width - 10, frameim.height - 10), radius=10, outline=(240, 208, 140, 220), width=2)
    frameim.alpha_composite(card, (13, 13))
    frameim.putalpha(frameim.getchannel('A').point(lambda a: int(a * p)))
    x = int(W - 60 - frameim.width + (1 - p) * 260)
    y = int(940 + 10 * math.sin(t * 0.9))
    sh = Image.new('RGBA', im.size); sh.paste((0, 0, 0, 150), (x + 14, y + 18, x + 14 + frameim.width, y + 18 + frameim.height), frameim.getchannel('A'))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(12)))
    im.alpha_composite(frameim, (x, y))
    return im

def keywords(im, kws, t, absolute):
    for text, t0, style, y, size, color in kws:
        words = text.split(' ')
        glows = [glowtext(w, size, color) for w in words]
        widths = [textimg(w, size, color).width for w in words]
        pad = int(size * 0.55)
        gap = int(size * 0.30)
        maxw = W - 120
        lines, cur, cw = [], [], 0
        for i, ww in enumerate(widths):                     # greedy wrap into lines
            add = ww + (gap if cur else 0)
            if cur and cw + add > maxw:
                lines.append((cur, cw)); cur, cw = [i], ww
            else:
                cur.append(i); cw += add
        lines.append((cur, cw))
        for li, (line, total) in enumerate(lines):
            ly = y + li * int(size * 1.42)
            x = (W - total) // 2
            for pos, i in enumerate(line):
                wi = glows[i]; ww = widths[i]
                lt = t - t0 - (pos + li * len(line)) * 0.11
                p = max(0, min(1, lt / 0.45))
                if p <= 0:
                    x += ww + gap; continue
                e = _ease(p)
                dx = dy = 0; sc = 1.0
                if style == 'pop': sc = 1.65 - 0.65 * e; dy = int((1 - e) * -26)
                elif style == 'slide_up': dy = int((1 - e) * 70)
                elif style == 'slide_r': dx = int(-(1 - e) * 90)
                dy += int(2.5 * math.sin(absolute * 1.35 + pos))
                layer = wi
                if abs(sc - 1) > 0.01:
                    layer = wi.resize((max(1, int(wi.width * sc)), max(1, int(wi.height * sc))), Image.Resampling.BICUBIC)
                if p < 1:
                    layer = layer.copy(); layer.putalpha(layer.getchannel('A').point(lambda a: int(a * p)))
                ox = int(x + dx - (layer.width - wi.width) // 2 - pad)
                oy = int(ly + dy - (layer.height - wi.height) // 2 - pad)
                im.alpha_composite(layer, (ox, oy))
                x += ww + gap
    return im

def avatar(im, look, t, gframe, absolute):
    amp = float(ENV[gframe]) if ENV is not None and gframe < len(ENV) else 0.0
    base = AVATARS[look]
    layer = base.copy()
    mx, my = MOUTH_PX[look]
    mo = Image.new('RGBA', layer.size, (0, 0, 0, 0))       # lip-sync mouth
    md = ImageDraw.Draw(mo)
    oh = 3 + 17 * amp; ow = 21 + 7 * amp
    md.ellipse((mx - ow, my - oh * 0.45, mx + ow, my + oh), fill=(46, 24, 22, int(120 + 120 * amp)))
    if amp > 0.42:
        md.ellipse((mx - ow * 0.62, my - oh * 0.35, mx + ow * 0.62, my + oh * 0.18), fill=(238, 232, 226, int(190 * amp)))
    mo = mo.filter(ImageFilter.GaussianBlur(1.6))
    layer.alpha_composite(mo)
    rot = 1.5 * math.sin(2 * math.pi * t / 3.6) + 0.5 * math.sin(2 * math.pi * t / 1.31)
    layer = layer.rotate(rot, Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
    sc = 1.0 + 0.011 * amp
    if sc > 1.001:
        layer = layer.resize((int(layer.width * sc), int(layer.height * sc)), Image.Resampling.BICUBIC)
    dx = 7 * math.sin(2 * math.pi * t / 2.8) + 3 * math.sin(2 * math.pi * t / 1.7)
    dy = 5 * math.sin(2 * math.pi * t / 0.95 + 1.3) + 3.5 * amp + 2 * math.sin(2 * math.pi * t / 4.4)
    x = int(AV_X + dx - (layer.width - base.width) / 2)
    y = int(AV_Y + dy - (layer.height - base.height))
    im.alpha_composite(layer, (x, y))
    return im

WIPE = None
def frame(idx, t, absolute, gframe):
    spec = SCENES[idx]
    im = camera((spec['bg'],) + spec['cam'][1:], t, DURS[idx])
    im = fx_overlay(im, spec['fx'], t, DURS[idx])
    if 'oil' in spec: im = oil_card(im, spec['oil'][0], t, spec['oil'][1])
    im.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), VIGNETTE)
    im = keywords(im, spec['kw'], t, absolute)
    im = avatar(im, spec['look'], t, gframe, absolute)
    if idx > 0 and t < 0.30:                               # diagonal light wipe cut
        wipe = Image.new('RGBA', (W, H)); wd = ImageDraw.Draw(wipe)
        x = int(-600 + t / 0.30 * 2400)
        wd.polygon([(x - 200, 0), (x, 0), (x - 620, H), (x - 820, H)], fill=(120, 235, 255, 130))
        wd.polygon([(x, 0), (x + 40, 0), (x - 580, H), (x - 620, H)], fill=(245, 255, 255, 210))
        im = Image.alpha_composite(im, wipe)
    return im.convert('RGB')
