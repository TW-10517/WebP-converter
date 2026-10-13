"""User settings, stored per-user under %APPDATA%.

Everything read back from disk is validated - the file is user-writable, so it
is treated as untrusted input rather than trusted state.
"""

import json
import os

from .core import FORMATS

APP_NAME = "WebPConverter"

DEFAULTS = {
    "lang": "en",
    "theme": "light",
    "quality": 80,
    "lossless": False,
    "out_format": "webp",
    "dest_mode": "same",
    "output_dir": "",
    "overwrite": False,
}


def config_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def config_path():
    return os.path.join(config_dir(), "settings.json")


def _clean(raw):
    out = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return out
    if raw.get("lang") in ("en", "ja"):
        out["lang"] = raw["lang"]
    if raw.get("theme") in ("light", "dark"):
        out["theme"] = raw["theme"]
    if isinstance(raw.get("quality"), int) and 1 <= raw["quality"] <= 100:
        out["quality"] = raw["quality"]
    if isinstance(raw.get("lossless"), bool):
        out["lossless"] = raw["lossless"]
    if isinstance(raw.get("overwrite"), bool):
        out["overwrite"] = raw["overwrite"]
    if raw.get("out_format") in FORMATS:
        out["out_format"] = raw["out_format"]
    if raw.get("dest_mode") in ("same", "custom"):
        out["dest_mode"] = raw["dest_mode"]
    path = raw.get("output_dir")
    if isinstance(path, str) and os.path.isdir(path):
        out["output_dir"] = path
    return out


def load():
    try:
        with open(config_path(), encoding="utf-8") as fh:
            return _clean(json.load(fh))
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save(settings):
    data = _clean(settings)
    try:
        os.makedirs(config_dir(), exist_ok=True)
        tmp = config_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, config_path())
    except OSError:
        pass
