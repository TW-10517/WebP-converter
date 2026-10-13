import os
import shutil
import tempfile
import unittest

from PIL import Image

from webpconv.core import (ConversionError, convert_file, destination_for, human_size,
                           is_supported, scan_folder)
from webpconv.security import is_within, unique_path


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="webpconv-test-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def make_png(self, name="a.png", size=(60, 40), color=(200, 90, 40)):
        path = os.path.join(self.dir, name)
        Image.new("RGB", size, color).save(path)
        return path


class TestHumanSize(unittest.TestCase):
    def test_units(self):
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(999), "999 B")
        self.assertEqual(human_size(1536), "1.5 KB")
        self.assertEqual(human_size(None), "—")


class TestSupported(unittest.TestCase):
    def test_extensions(self):
        self.assertTrue(is_supported("photo.PNG"))
        self.assertTrue(is_supported("a.jpeg"))
        self.assertFalse(is_supported("notes.txt"))
        self.assertFalse(is_supported("run.exe"))


class TestConvert(TempDirTest):
    def test_converts_and_shrinks(self):
        src = self.make_png()
        dest = os.path.join(self.dir, "a.webp")
        size = convert_file(src, dest, 80, False)
        self.assertTrue(os.path.exists(dest))
        self.assertEqual(size, os.path.getsize(dest))
        with Image.open(dest) as im:
            self.assertEqual(im.format, "WEBP")

    def test_alpha_preserved(self):
        src = os.path.join(self.dir, "t.png")
        Image.new("RGBA", (30, 30), (10, 20, 30, 120)).save(src)
        dest = os.path.join(self.dir, "t.webp")
        convert_file(src, dest, 90, False)
        with Image.open(dest) as im:
            self.assertIn("A", im.convert("RGBA").getbands())

    def test_animated_gif_keeps_frames(self):
        src = os.path.join(self.dir, "anim.gif")
        frames = []
        for offset in (0, 6, 12):
            frame = Image.new("RGB", (24, 24), (255, 255, 255))
            frame.paste((10, 40, 200), (offset, offset, offset + 8, offset + 8))
            frames.append(frame.convert("P", palette=Image.ADAPTIVE))
        frames[0].save(src, save_all=True, append_images=frames[1:], duration=120, loop=0)
        with Image.open(src) as check:
            self.assertGreater(getattr(check, "n_frames", 1), 1, "fixture is not animated")
        dest = os.path.join(self.dir, "anim.webp")
        convert_file(src, dest, 80, False)
        with Image.open(dest) as im:
            self.assertGreater(getattr(im, "n_frames", 1), 1)

    def test_webp_back_to_png(self):
        src = os.path.join(self.dir, "src.webp")
        Image.new("RGBA", (40, 40), (10, 20, 30, 128)).save(src, "WEBP", lossless=True)
        dest = destination_for(src, self.dir, False, "png")
        self.assertTrue(dest.endswith(".png"))
        convert_file(src, dest, 80, False, "png")
        with Image.open(dest) as im:
            self.assertEqual(im.format, "PNG")
            self.assertIn("A", im.convert("RGBA").getbands())

    def test_webp_back_to_jpeg_flattens_alpha(self):
        src = os.path.join(self.dir, "src.webp")
        Image.new("RGBA", (40, 40), (0, 0, 0, 0)).save(src, "WEBP", lossless=True)
        dest = destination_for(src, self.dir, False, "jpeg")
        self.assertTrue(dest.endswith(".jpg"))
        convert_file(src, dest, 90, False, "jpeg")
        with Image.open(dest) as im:
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(im.mode, "RGB")
            self.assertEqual(im.convert("RGB").getpixel((20, 20)), (255, 255, 255))

    def test_animated_source_to_png_keeps_first_frame(self):
        src = os.path.join(self.dir, "anim.webp")
        frames = [Image.new("RGB", (20, 20), c) for c in
                  ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
        frames[0].save(src, "WEBP", save_all=True, append_images=frames[1:],
                       duration=100, lossless=True)
        dest = os.path.join(self.dir, "anim.png")
        convert_file(src, dest, 80, False, "png")
        with Image.open(dest) as im:
            self.assertEqual(getattr(im, "n_frames", 1), 1)
            self.assertEqual(im.convert("RGB").getpixel((10, 10)), (255, 0, 0))

    def test_unknown_format_rejected(self):
        src = self.make_png()
        with self.assertRaises(ConversionError):
            convert_file(src, os.path.join(self.dir, "a.tga"), 80, False, "tga")

    def test_same_format_never_clobbers_source(self):
        src = self.make_png("keep.png")
        dest = destination_for(src, self.dir, True, "png")
        self.assertNotEqual(os.path.abspath(dest), os.path.abspath(src))

    def test_exif_rotation_is_baked_in(self):
        """A phone photo stores rotation in EXIF; the pixels must come out upright."""
        src = os.path.join(self.dir, "rot.jpg")
        exif = Image.Exif()
        exif[274] = 6  # Orientation: rotate 90° CW to view
        Image.new("RGB", (120, 60), (20, 20, 200)).save(src, "JPEG", exif=exif)
        dest = os.path.join(self.dir, "rot.webp")
        convert_file(src, dest, 80, False)
        with Image.open(dest) as im:
            self.assertEqual(im.size, (60, 120))

    def test_icc_profile_survives(self):
        src = os.path.join(self.dir, "icc.jpg")
        profile = b"\x00\x00\x02\x0cfake-icc-profile" + b"\x00" * 500
        Image.new("RGB", (40, 40), (10, 120, 60)).save(src, "JPEG", icc_profile=profile)
        for fmt, ext in (("webp", ".webp"), ("png", ".png"), ("jpeg", ".jpg")):
            dest = os.path.join(self.dir, "icc" + ext)
            convert_file(src, dest, 80, False, fmt)
            with Image.open(dest) as im:
                self.assertEqual(im.info.get("icc_profile"), profile, fmt)

    def test_missing_file(self):
        with self.assertRaises(ConversionError):
            convert_file(os.path.join(self.dir, "nope.png"),
                         os.path.join(self.dir, "nope.webp"), 80, False)

    def test_non_image(self):
        src = os.path.join(self.dir, "fake.png")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("this is not an image")
        with self.assertRaises(ConversionError):
            convert_file(src, os.path.join(self.dir, "fake.webp"), 80, False)


class TestDestination(TempDirTest):
    def test_extension_swapped(self):
        dest = destination_for(os.path.join(self.dir, "pic.jpg"), self.dir, True)
        self.assertEqual(os.path.basename(dest), "pic.webp")

    def test_no_overwrite_makes_unique(self):
        existing = os.path.join(self.dir, "pic.webp")
        open(existing, "wb").close()
        dest = destination_for(os.path.join(self.dir, "pic.jpg"), self.dir, False)
        self.assertNotEqual(dest, existing)
        self.assertEqual(os.path.basename(dest), "pic (2).webp")

    def test_overwrite_reuses_path(self):
        existing = os.path.join(self.dir, "pic.webp")
        open(existing, "wb").close()
        dest = destination_for(os.path.join(self.dir, "pic.jpg"), self.dir, True)
        self.assertEqual(dest, existing)

    def test_traversal_name_stays_in_dest(self):
        # A crafted name must not escape the chosen output folder.
        dest = destination_for("../../evil.jpg", self.dir, True)
        self.assertTrue(is_within(dest, self.dir) or os.path.dirname(dest) == self.dir)
        self.assertEqual(os.path.dirname(os.path.abspath(dest)), os.path.abspath(self.dir))


class TestScan(TempDirTest):
    def test_finds_images_recursively(self):
        self.make_png("one.png")
        sub = os.path.join(self.dir, "sub")
        os.makedirs(sub)
        Image.new("RGB", (10, 10)).save(os.path.join(sub, "two.jpg"))
        with open(os.path.join(self.dir, "skip.txt"), "w", encoding="utf-8") as fh:
            fh.write("x")
        found = sorted(os.path.basename(p) for p in scan_folder(self.dir))
        self.assertEqual(found, ["one.png", "two.jpg"])

    def test_respects_limit(self):
        for i in range(5):
            self.make_png(f"img{i}.png")
        self.assertEqual(len(list(scan_folder(self.dir, limit=3))), 3)


class TestSecurityHelpers(TempDirTest):
    def test_is_within(self):
        inside = os.path.join(self.dir, "a", "b.txt")
        self.assertTrue(is_within(inside, self.dir))
        self.assertFalse(is_within(os.path.dirname(self.dir), self.dir))

    def test_unique_path(self):
        p = os.path.join(self.dir, "f.webp")
        self.assertEqual(unique_path(p), p)
        open(p, "wb").close()
        self.assertEqual(os.path.basename(unique_path(p)), "f (2).webp")


class TestNetworkBlocked(unittest.TestCase):
    def test_connect_refused(self):
        import socket

        from webpconv.security import block_network
        block_network()
        with self.assertRaises(OSError):
            socket.socket().connect(("127.0.0.1", 80))


if __name__ == "__main__":
    unittest.main()
