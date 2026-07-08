#!/usr/bin/env python3
"""Generate SEE 生命印迹 app icons for PWA / mobile home screen."""

from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Icon sizes (px)
SIZES = {
    'favicon-16.png': 16,
    'favicon-32.png': 32,
    'icon-72.png': 72,
    'icon-96.png': 96,
    'icon-128.png': 128,
    'icon-144.png': 144,
    'icon-152.png': 152,
    'apple-touch-icon.png': 180,
    'icon-192.png': 192,
    'icon-384.png': 384,
    'icon-512.png': 512,
}

# Match brand colors from index.html
BG_COLOR_TOP = (22, 22, 52)      # #161634 (brighter --bg)
BG_COLOR_BOTTOM = (34, 46, 78)   # #222e4e (brighter hero gradient)
ACCENT = (107, 150, 172)         # #6b96ac (--accent)
GOLD = (184, 160, 128)           # #b8a080 (--gold)
BRONZE = (160, 136, 104)         # #a08868 (--accent2)
MUTED = (138, 133, 144)          # #8a8590 (--muted)
TEXT_WARM = (240, 236, 226)      # #f0ece2 (hero title)

def _try_font(size, bold=False):
    """Find a CJK-capable font, falling back gracefully."""
    if bold:
        candidates = [
            ('/System/Library/Fonts/PingFang.ttc', 1),   # Semibold
            ('/System/Library/Fonts/STHeiti Medium.ttc', 0),
            ('/Library/Fonts/Arial Unicode.ttf', 0),
        ]
    else:
        candidates = [
            ('/System/Library/Fonts/PingFang.ttc', 0),   # Regular
            ('/System/Library/Fonts/STHeiti Light.ttc', 0),
            ('/Library/Fonts/Arial Unicode.ttf', 0),
        ]
    for path, index in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except Exception:
                continue
    return ImageFont.load_default()

def _draw_gradient(draw, w, h):
    """Vertical gradient from deep blue to deep purple."""
    for y in range(h):
        r = int(BG_COLOR_TOP[0] + (BG_COLOR_BOTTOM[0] - BG_COLOR_TOP[0]) * y / h)
        g = int(BG_COLOR_TOP[1] + (BG_COLOR_BOTTOM[1] - BG_COLOR_TOP[1]) * y / h)
        b = int(BG_COLOR_TOP[2] + (BG_COLOR_BOTTOM[2] - BG_COLOR_TOP[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

def _add_glow_effect(draw, w, h, size):
    """Subtle radial glow in the center."""
    cx, cy = w / 2, h * 0.4
    max_r = w * 0.55
    for i in range(int(max_r), 0, -1):
        alpha = int(30 * (1 - i / max_r))
        if alpha <= 0:
            break
        r = min(int(80 + 40 * i / max_r), 120)
        g = min(int(60 + 40 * i / max_r), 100)
        b = min(int(140 + 60 * i / max_r), 200)
        draw.ellipse(
            [(cx - i, cy - i * 0.7), (cx + i, cy + i * 0.7)],
            fill=(r, g, b, alpha) if hasattr(draw, 'ellipse') else None
        )

def _draw_decorative_dots(draw, w, h, size):
    """Tiny star-like dots scattered around."""
    import random
    rng = random.Random(42)
    positions = [
        (w * 0.15, h * 0.25), (w * 0.85, h * 0.20),
        (w * 0.10, h * 0.65), (w * 0.88, h * 0.70),
        (w * 0.20, h * 0.85), (w * 0.78, h * 0.82),
    ]
    for px, py in positions:
        r = max(2, int(size / 180 * 4))
        draw.ellipse([(px - r, py - r), (px + r, py + r)], fill=(180, 160, 220, 120))

def generate_icon(size, filename):
    """Generate a single icon PNG."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: rounded corners simulation via gradient fill
    _draw_gradient(draw, size, size)

    # Subtle center glow (warm gold, matching brand accent)
    cx, cy = size / 2, size * 0.38
    max_r = size * 0.5
    for i in range(int(max_r), 0, -1):
        alpha = int(20 * (1 - i / max_r))
        if alpha <= 0:
            break
        r = GOLD[0] + int((255 - GOLD[0]) * i / max_r) * 0.3
        g = GOLD[1] + int((255 - GOLD[1]) * i / max_r) * 0.2
        b = GOLD[2] + int((255 - GOLD[2]) * i / max_r) * 0.15
        draw.ellipse(
            [(cx - i, cy - i * 0.65), (cx + i, cy + i * 0.65)],
            fill=(int(r), int(g), int(b), alpha)
        )

    # --- "SEE" large text in white ---
    see_size = int(size * 0.38)
    see_font = _try_font(see_size, bold=True)
    see_text = "SEE"
    see_bbox = draw.textbbox((0, 0), see_text, font=see_font)
    see_w = see_bbox[2] - see_bbox[0]
    see_h = see_bbox[3] - see_bbox[1]
    see_x = (size - see_w) / 2
    see_y = size * 0.22
    draw.text((see_x, see_y), see_text, fill=TEXT_WARM, font=see_font)

    # --- "生命印迹" subtitle in accent blue ---
    sub_size = int(size * 0.12)
    sub_font = _try_font(sub_size)
    sub_text = "生命印迹"
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_x = (size - sub_w) / 2
    sub_y = see_y + see_h + size * 0.04
    draw.text((sub_x, sub_y), sub_text, fill=(180, 210, 225), font=sub_font)

    # --- Bottom thin line separator in muted bronze ---
    line_y = int(size * 0.78)
    line_w = int(size * 0.3)
    line_x1 = int((size - line_w) / 2)
    line_x2 = line_x1 + line_w
    draw.line([(line_x1, line_y), (line_x2, line_y)], fill=BRONZE + (80,), width=max(1, int(size / 180)))

    # --- Bottom tagline in muted gray ---
    tag_size = int(size * 0.065)
    tag_font = _try_font(tag_size, bold=True)
    tag_text = "让思维看见 · 让理解发生"
    tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_w = tag_bbox[2] - tag_bbox[0]
    tag_x = (size - tag_w) / 2
    tag_y = size * 0.82
    draw.text((tag_x, tag_y), tag_text, fill=(240, 220, 160), font=tag_font)

    # Save
    path = os.path.join(OUT_DIR, filename)
    img.save(path, 'PNG')
    print(f'  ✓ {filename} ({size}×{size})')
    return path

if __name__ == '__main__':
    print('Generating SEE icons...')
    for fname, sz in SIZES.items():
        generate_icon(sz, fname)
    # Also create favicon.ico (multi-size)
    favicon_32 = Image.open(os.path.join(OUT_DIR, 'favicon-32.png'))
    favicon_16 = Image.open(os.path.join(OUT_DIR, 'favicon-16.png'))
    favicon_32.save(os.path.join(OUT_DIR, 'favicon.ico'), format='ICO', sizes=[(32, 32), (16, 16)])
    print('  ✓ favicon.ico (32+16)')
    print('Done!')
