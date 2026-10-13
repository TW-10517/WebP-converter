"""Generates the app logo (assets/logo.png) and Windows icon (assets/icon.ico).

The mark is a photo glyph with a two-way arrow badge: an image, converted in
either direction. Everything is drawn at 4x and downsampled so the curves stay
clean at icon sizes.

    python tools/make_logo.py
"""

import os

from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
SS = 4  # supersampling factor
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

TOP = (58, 128, 247)
BOTTOM = (108, 75, 240)
WHITE = (255, 255, 255, 255)
ARROW = (61, 116, 240, 255)


def gradient_tile(s, radius):
    grad = Image.new("RGB", (s, s))
    d = ImageDraw.Draw(grad)
    for y in range(s):
        t = y / (s - 1)
        d.line([(0, y), (s, y)],
               fill=tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)))

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=255)

    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    tile.paste(grad, (0, 0), mask)

    # soft highlight sweeping the top edge
    gloss = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).ellipse([-s * 0.35, -s * 0.80, s * 1.35, s * 0.38],
                                  fill=(255, 255, 255, 34))
    gloss = gloss.filter(ImageFilter.GaussianBlur(s * 0.06))
    gloss.putalpha(Image.composite(gloss.getchannel("A"), Image.new("L", (s, s), 0), mask))
    tile.alpha_composite(gloss)
    return tile


def photo_glyph(s):
    """A rounded frame holding a sun and two peaks, in white."""
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = s * 0.155, s * 0.175, s * 0.700, s * 0.640
    stroke, radius = s * 0.050, s * 0.085
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=WHITE, width=round(stroke))

    # contents, clipped to the frame's inner opening
    inner = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    di = ImageDraw.Draw(inner)
    pad = stroke * 1.45
    di.ellipse([x0 + pad * 1.1, y0 + pad * 1.0,
                x0 + pad * 1.1 + s * 0.085, y0 + pad * 1.0 + s * 0.085], fill=WHITE)
    base = y1 - pad * 0.55
    di.polygon([(x0 + pad * 0.6, base), (x0 + s * 0.215, y0 + s * 0.230),
                (x0 + s * 0.360, base)], fill=WHITE)
    di.polygon([(x0 + s * 0.215, base), (x0 + s * 0.375, y0 + s * 0.300),
                (x1 - pad * 0.6, base)], fill=WHITE)

    clip = Image.new("L", (s, s), 0)
    ImageDraw.Draw(clip).rounded_rectangle(
        [x0 + stroke / 2, y0 + stroke / 2, x1 - stroke / 2, y1 - stroke / 2],
        radius=radius - stroke / 2, fill=255)
    inner.putalpha(Image.composite(inner.getchannel("A"), Image.new("L", (s, s), 0), clip))
    layer.alpha_composite(inner)
    return layer


def arrow(d, y, x0, x1, stroke, color, pointing_right):
    """One shaft with a solid head, drawn between x0 and x1."""
    head = stroke * 1.9
    tip, tail = (x1, x0) if pointing_right else (x0, x1)
    shaft_end = tip - head * 0.55 if pointing_right else tip + head * 0.55
    d.line([(tail, y), (shaft_end, y)], fill=color, width=round(stroke))
    d.ellipse([tail - stroke / 2, y - stroke / 2, tail + stroke / 2, y + stroke / 2], fill=color)
    d.polygon([(tip, y), (shaft_end, y - head * 0.78), (shaft_end, y + head * 0.78)], fill=color)


def swap_badge(s):
    """White disc carrying the two-way conversion arrows."""
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    cx, cy, r = s * 0.700, s * 0.700, s * 0.235

    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([cx - r, cy - r + s * 0.018, cx + r, cy + r + s * 0.018],
                                   fill=(24, 28, 70, 105))
    layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(s * 0.022)))

    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)

    stroke = s * 0.042
    span = r * 0.62
    gap = r * 0.30
    arrow(d, cy - gap, cx - span, cx + span, stroke, ARROW, True)
    arrow(d, cy + gap, cx - span, cx + span, stroke, ARROW, False)
    return layer


def full_mark(s):
    icon = gradient_tile(s, radius=round(s * 0.225))
    icon.alpha_composite(photo_glyph(s))
    icon.alpha_composite(swap_badge(s))
    return icon


def small_mark(s):
    """Below ~32px the frame and badge turn to mush, so show only the arrows."""
    icon = gradient_tile(s, radius=round(s * 0.225))
    d = ImageDraw.Draw(icon)
    stroke, span, gap = s * 0.100, s * 0.300, s * 0.190
    arrow(d, s * 0.5 - gap, s * 0.5 - span, s * 0.5 + span, stroke, WHITE, True)
    arrow(d, s * 0.5 + gap, s * 0.5 - span, s * 0.5 + span, stroke, WHITE, False)
    return icon


def render(mark, n):
    """Draw at n*SS and downsample, so each size keeps its own crisp geometry."""
    return mark(n * SS).resize((n, n), Image.LANCZOS)


def build():
    os.makedirs(OUT, exist_ok=True)
    render(full_mark, SIZE).save(os.path.join(OUT, "logo.png"))

    # One ICO, but the tiny entries carry the simplified mark.
    detailed = [256, 128, 64, 48]
    simple = [32, 24, 16]
    frames = [render(full_mark, n) for n in detailed]
    frames += [render(small_mark, n) for n in simple]
    sizes = [(n, n) for n in detailed + simple]
    frames[0].save(os.path.join(OUT, "icon.ico"), sizes=sizes, append_images=frames[1:])
    print("wrote", OUT)


if __name__ == "__main__":
    build()
