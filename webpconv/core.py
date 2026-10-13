"""Image conversion and filesystem scanning - no UI code here."""

import os

from PIL import Image, ImageOps, UnidentifiedImageError

from .security import MAX_SCAN_FILES, is_within, unique_path

SUPPORTED_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp")

# key -> (output extension, Pillow format, supports alpha, supports animation)
FORMATS = {
    "webp": (".webp", "WEBP", True, True),
    "png": (".png", "PNG", True, False),
    "jpeg": (".jpg", "JPEG", False, False),
}


class ConversionError(Exception):
    pass


def human_size(n):
    if n is None:
        return "—"
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0


def is_supported(path):
    return path.lower().endswith(SUPPORTED_EXTS)


def scan_folder(folder, limit=MAX_SCAN_FILES):
    """Yield supported image paths under `folder`, skipping symlinked dirs."""
    found = 0
    for root, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for name in sorted(names):
            if not is_supported(name):
                continue
            yield os.path.join(root, name)
            found += 1
            if found >= limit:
                return


def destination_for(src, dest_dir, overwrite, fmt="webp"):
    """Resolve the output path, refusing anything outside `dest_dir`."""
    dest_dir = os.path.abspath(dest_dir)
    ext = FORMATS[fmt][0]
    name = os.path.basename(src)
    dest = os.path.join(dest_dir, os.path.splitext(name)[0] + ext)
    if not is_within(os.path.dirname(dest) or dest_dir, dest_dir):
        raise ConversionError("Refusing to write outside the output folder")
    if os.path.abspath(dest) == os.path.abspath(src):
        # Converting a file into its own format and location - never clobber the source.
        return unique_path(dest)
    return dest if overwrite else unique_path(dest)


def probe(path):
    """Read dimensions and byte size without decoding the full image."""
    size = os.path.getsize(path)
    with Image.open(path) as im:
        return im.width, im.height, size


def load_thumbnail_source(path, box=(200, 200)):
    with Image.open(path) as im:
        small = im.convert("RGB")
        small.thumbnail(box, Image.LANCZOS)
        return small.copy()


def _has_alpha(img):
    return img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info


def encode(img, fp, fmt, quality, lossless, method=5, animated=False, icc=None):
    pil_fmt = FORMATS[fmt][1]
    # Carry the colour profile across, or wide-gamut photos come out shifted.
    extra = {"icc_profile": icc} if icc else {}
    if pil_fmt == "WEBP":
        params = {"quality": quality, "lossless": lossless, "method": method}
        img.save(fp, pil_fmt, save_all=True, **params, **extra) if animated \
            else img.save(fp, pil_fmt, **params, **extra)
    elif pil_fmt == "PNG":
        img.save(fp, pil_fmt, optimize=True, **extra)
    else:
        img.save(fp, pil_fmt, quality=quality, optimize=True, progressive=True, **extra)


def convert_to(src, fp, quality, lossless, fmt="webp"):
    """Convert `src` into `fp` (a path or file object) using `fmt`."""
    if fmt not in FORMATS:
        raise ConversionError(f"Unsupported output format: {fmt}")
    if not os.path.isfile(src):
        raise ConversionError("File no longer exists")
    _, _, keeps_alpha, keeps_animation = FORMATS[fmt]
    try:
        with Image.open(src) as img:
            animated = getattr(img, "n_frames", 1) > 1 and keeps_animation
            icc = img.info.get("icc_profile")
            if animated:
                encode(img, fp, fmt, quality, lossless, animated=True, icc=icc)
            else:
                if getattr(img, "n_frames", 1) > 1:
                    img.seek(0)  # still formats keep the first frame only
                # Cameras record rotation in EXIF rather than in the pixels; bake
                # it in, otherwise portrait photos come out on their side.
                still = ImageOps.exif_transpose(img) or img
                if _has_alpha(still) and keeps_alpha:
                    flat = still.convert("RGBA")
                elif _has_alpha(still):
                    rgba = still.convert("RGBA")
                    flat = Image.new("RGB", rgba.size, (255, 255, 255))
                    flat.paste(rgba, mask=rgba.split()[3])
                else:
                    flat = still.convert("RGB")
                encode(flat, fp, fmt, quality, lossless, icc=icc)
    except UnidentifiedImageError:
        raise ConversionError("Not a readable image")
    except Image.DecompressionBombError:
        raise ConversionError("Image is too large to open safely")
    except (OSError, ValueError) as e:
        raise ConversionError(str(e))


def convert_file(src, dest, quality, lossless, fmt="webp"):
    """Convert one image to `fmt` on disk. Returns the output size in bytes."""
    convert_to(src, dest, quality, lossless, fmt)
    return os.path.getsize(dest)
