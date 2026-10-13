"""PIL drawing helpers for backgrounds, icons and thumbnails."""

from PIL import Image, ImageDraw


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def pill(w, h, color, bg=None):
    """A smooth rounded bar, RGBA unless `bg` is given to flatten against.

    Tk's canvas has no antialiasing, so a rounded polygon drawn there comes out
    with visibly stepped edges. Drawing it here at 4x and downsampling gives the
    clean edge the canvas can't produce.
    """
    w, h = max(int(w), 1), max(int(h), 1)
    ss = 4
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle(
        [0, 0, w * ss - 1, h * ss - 1], radius=min(w, h) * ss / 2,
        fill=hex_rgb(color) + (255,))
    small = big.resize((w, h), Image.LANCZOS)
    if bg is None:
        return small
    return flatten(small, bg)


def bulb_icon(h, color, bg):
    """A light-bulb glyph for the help button."""
    ss = 4
    w = h
    img = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = hex_rgb(color) + (255,)
    hole = hex_rgb(bg) + (255,)
    # glass
    d.ellipse([w * .20 * ss, h * .06 * ss, w * .80 * ss, h * .66 * ss], fill=col)
    # neck into the screw base
    d.polygon([(w * .37 * ss, h * .58 * ss), (w * .63 * ss, h * .58 * ss),
               (w * .59 * ss, h * .74 * ss), (w * .41 * ss, h * .74 * ss)], fill=col)
    d.rounded_rectangle([w * .38 * ss, h * .72 * ss, w * .62 * ss, h * .95 * ss],
                        radius=w * .07 * ss, fill=col)
    # two grooves knocked out of the base
    for t in (.80, .88):
        d.rectangle([w * .38 * ss, h * t * ss, w * .62 * ss, (h * t + h * .045) * ss],
                    fill=hole)
    return img.resize((w, h), Image.LANCZOS)


def radio_mark(n, on, accent, border, bg):
    """A radio dot, drawn at 4x so the circles come out smooth.

    Tk's canvas draws `create_oval` with no antialiasing, which is very visible
    on a small ring that changes colour under the pointer.
    """
    ss = 4
    big = Image.new("RGBA", (n * ss, n * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    ring = hex_rgb(accent if on else border) + (255,)
    width = max(int((2 if on else 1) * ss), 1)
    inset = width / 2
    d.ellipse([inset, inset, n * ss - 1 - inset, n * ss - 1 - inset],
              fill=hex_rgb(bg) + (255,), outline=ring, width=width)
    if on:
        d.ellipse([n * .30 * ss, n * .30 * ss, n * .70 * ss, n * .70 * ss],
                  fill=hex_rgb(accent) + (255,))
    return flatten(big.resize((n, n), Image.LANCZOS), bg)


def check_mark(n, on, accent, border, bg, tick="#ffffff"):
    """A checkbox: rounded box plus a tick, both antialiased by PIL."""
    ss = 4
    big = Image.new("RGBA", (n * ss, n * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    edge = hex_rgb(accent if on else border) + (255,)
    d.rounded_rectangle([ss / 2, ss / 2, n * ss - 1 - ss / 2, n * ss - 1 - ss / 2],
                        radius=n * ss * .28, fill=hex_rgb(accent if on else bg) + (255,),
                        outline=edge, width=ss)
    if on:
        pts = [(n * .27 * ss, n * .52 * ss), (n * .43 * ss, n * .69 * ss),
               (n * .74 * ss, n * .32 * ss)]
        w = int(2.2 * ss)
        d.line(pts, fill=hex_rgb(tick) + (255,), width=w)
        for x, y in pts:  # round the cap and the elbow, which `line` leaves square
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2],
                      fill=hex_rgb(tick) + (255,))
    return flatten(big.resize((n, n), Image.LANCZOS), bg)


def knob(r, face, ring, width, halo=0, halo_color=None):
    """Circular slider handle with an optional soft outer halo, as RGBA."""
    size = max(int(2 * (r + halo)), 2)
    ss = 4
    big = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    c = size * ss / 2
    if halo and halo_color:
        hr = (r + halo) * ss
        d.ellipse([c - hr, c - hr, c + hr, c + hr], fill=hex_rgb(halo_color) + (255,))
    rr = r * ss
    d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=hex_rgb(face) + (255,),
              outline=hex_rgb(ring) + (255,), width=max(int(width * ss), 1))
    return big.resize((size, size), Image.LANCZOS)


def flatten(img, bg):
    out = Image.new("RGB", img.size, hex_rgb(bg))
    out.paste(img, mask=img.getchannel("A"))
    return out


def gradient_card(w, h, top, bottom, radius, bg):
    w, h = max(w, 2), max(h, 2)
    grad = Image.new("RGB", (1, h))
    t, b = hex_rgb(top), hex_rgb(bottom)
    px = grad.load()
    for y in range(h):
        f = y / max(h - 1, 1)
        px[0, y] = tuple(round(t[i] + (b[i] - t[i]) * f) for i in range(3))
    grad = grad.resize((w, h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    out = Image.new("RGB", (w, h), hex_rgb(bg))
    out.paste(grad, (0, 0), mask)
    return out


def rounded_cover(pil, w, h, radius, bg):
    """Center-crop to the target aspect ratio, resize, then round the corners."""
    target = w / h
    source = pil.width / pil.height
    if source > target:
        new_w = max(int(pil.height * target), 1)
        box = ((pil.width - new_w) // 2, 0, (pil.width + new_w) // 2, pil.height)
    else:
        new_h = max(int(pil.width / target), 1)
        box = (0, (pil.height - new_h) // 2, pil.width, (pil.height + new_h) // 2)
    pil = pil.crop(box).convert("RGB").resize((w, h), Image.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    out = Image.new("RGB", (w, h), hex_rgb(bg))
    out.paste(pil, (0, 0), mask)
    return out


def stack_illustration(h, accent, card, muted):
    """A stack of image cards, drawn at 4x and downsampled for clean edges."""
    s = 4
    w = int(h * 1.25)
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    a, cd, mu = hex_rgb(accent), hex_rgb(card), hex_rgb(muted)
    d.rounded_rectangle([int(w * .16 * s), int(h * .10 * s), int(w * .84 * s), int(h * .30 * s)],
                        radius=4 * s, fill=cd + (255,), outline=mu + (90,), width=s)
    d.rounded_rectangle([int(w * .10 * s), int(h * .22 * s), int(w * .90 * s), int(h * .92 * s)],
                        radius=6 * s, fill=cd + (255,), outline=a + (150,), width=int(1.6 * s))
    base = h * .80 * s
    d.polygon([(w * .24 * s, base), (w * .45 * s, h * .46 * s), (w * .62 * s, base)],
              fill=a + (210,))
    d.polygon([(w * .50 * s, base), (w * .66 * s, h * .56 * s), (w * .82 * s, base)],
              fill=a + (130,))
    d.ellipse([w * .66 * s, h * .32 * s, w * .78 * s, h * .44 * s], fill=a + (170,))
    return img.resize((w, h), Image.LANCZOS)
