"""Process hardening and safe filesystem helpers.

This application is entirely offline. Nothing here reaches the network, and
`block_network()` enforces that at runtime so a future dependency cannot
quietly start phoning home.
"""

import os
import socket

from PIL import Image

# A 40000x40000 PNG decodes to ~6 GB in memory. Cap decoded pixels so a
# malicious or corrupt image cannot exhaust RAM.
MAX_IMAGE_PIXELS = 256_000_000

# Upper bound on a single "Add folder" walk, so a huge tree cannot hang the UI.
MAX_SCAN_FILES = 5000


def enable_dpi_awareness():
    """Must run before Tk loads, or Windows bitmap-stretches the window."""
    try:
        import ctypes
    except ImportError:
        return
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


APP_ID = "Local.WebPConverter"


def set_app_id(app_id=APP_ID):
    """Give the process its own taskbar identity.

    Without this, Windows attributes the window to pythonw.exe and the taskbar
    button shows the generic Python icon instead of the app's own.
    """
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def harden_pillow():
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def block_network():
    """Make outbound connections impossible for the lifetime of the process."""
    def refuse(*_args, **_kwargs):
        raise OSError("WebP Converter runs fully offline; network access is disabled.")

    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse
    socket.create_connection = refuse


def is_within(path, parent):
    """True if `path` resolves inside `parent` - blocks traversal via crafted names."""
    try:
        path = os.path.realpath(path)
        parent = os.path.realpath(parent)
    except OSError:
        return False
    return os.path.commonpath([path, parent]) == parent


def unique_path(path):
    """Return `path`, or `name (2).ext` etc. if it already exists."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    for i in range(2, 1000):
        candidate = f"{stem} ({i}){ext}"
        if not os.path.exists(candidate):
            return candidate
    raise OSError("Could not find a free filename")
