#!/usr/bin/env python3
"""Generate SEE 生命印迹 app icons for PWA / mobile home screen."""

from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Icon sizes (px)
SIZES = {
    'favicon-32.png': 32,
    'favicon-16.png': 16,
    'apple-touch-icon.png': 180,
    'icon-192.png': 192,
    'icon-512.png': 512,
}

# Deep blue-purple gradient start/end
BG_COLOR_TOP = (15, 15, 60)      # #0f0f3c
BG_COLOR_BOTTOM = (40, 20, 80)   # #281450

def _try_font(size, bold=False):
    """Find a CJK-capable font, falling back gracefully."""
    candidates = []
    if bold:
        candidates = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Medium.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
        ]
    candidates += [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
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

    # Subtle center glow
    cx, cy = size / 2, size * 0.38
    max_r = size * 0.5
    for i in range(int(max_r), 0, -1):
        alpha = int(25 * (1 - i / max_r))
        if alpha <= 0:
            break
        r = min(int(90 + 30 * i / max_r), 130)
        g = min(int(60 + 30 * i / max_r), 100)
        b = min(int(160 + 40 * i / max_r), 210)
        draw.ellipse(
            [(cx - i, cy - i * 0.65), (cx + i, cy + i * 0.65)],
            fill=(r, g, b, alpha)
        )

    # Small decorative dots
    _draw_decorative_dots(draw, size, size, size)

    # --- "SEE" large text ---
    see_size = int(size * 0.38)
    see_font = _try_font(see_size, bold=True)
    see_text = "SEE"
    see_bbox = draw.textbbox((0, 0), see_text, font=see_font)
    see_w = see_bbox[2] - see_bbox[0]
    see_h = see_bbox[3] - see_bbox[1]
    see_x = (size - see_w) / 2
    see_y = size * 0.22
    # Main text
    draw.text((see_x, see_y), see_text, fill=(220, 210, 180), font=see_font)
    # Subtle highlight overlay
    draw.text((see_x - 1, see_y - 1), see_text, fill=(255, 248, 220, 60), font=see_font)

    # --- "生命印迹" subtitle ---
    sub_size = int(size * 0.12)
    sub_font = _try_font(sub_size)
    sub_text = "生命印迹"
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_x = (size - sub_w) / 2
    sub_y = see_y + see_h + size * 0.04
    draw.text((sub_x, sub_y), sub_text, fill=(180, 170, 210), font=sub_font)

    # --- Bottom thin line separator ---
    line_y = int(size * 0.78)
    line_w = int(size * 0.3)
    line_x1 = int((size - line_w) / 2)
    line_x2 = line_x1 + line_w
    draw.line([(line_x1, line_y), (line_x2, line_y)], fill=(140, 130, 180, 100), width=max(1, int(size / 180)))

    # --- Bottom tagline ---
    tag_size = int(size * 0.065)
    tag_font = _try_font(tag_size)
    tag_text = "让思维看见 · 让理解发生"
    tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_w = tag_bbox[2] - tag_bbox[0]
    tag_x = (size - tag_w) / 2
    tag_y = size * 0.82
    draw.text((tag_x, tag_y), tag_text, fill=(140, 135, 175), font=tag_font)

    # --- Subtle ring decoration ---
    ring_r = int(size * 0.46)
    ring_y = int(size * 0.40)
    for offset in range(3):
        alpha = 40 - offset * 10
        r = ring_r + offset * 2
        draw.ellipse(
            [(cx - r, ring_y - r * 0.6), (cx + r, ring_y + r * 0.6)],
            outline=(160, 140, 200, alpha),
            width=max(1, int(size / 180))
        )

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
