"""Colour palettes, DPI scaling and font selection."""

from tkinter import font as tkfont

THEMES = {
    "light": {
        "bg": "#f6f7fb", "card": "#ffffff", "list_bg": "#fbfcfe",
        "border": "#e3e7f0", "divider": "#edf0f6",
        "text": "#121722", "muted": "#5d6779", "faint": "#8b94a6",
        "accent": "#4f46e5", "accent_hi": "#4338ca", "accent_lo": "#eceafe",
        "chip": "#eef0f6", "chip_hi": "#e3e7f2",
        "success": "#046c50", "success_bg": "#e6f6ef",
        "danger": "#b42318", "danger_bg": "#fdeceb",
        "warn": "#a15c07", "warn_bg": "#fdf3e2",
        "drop_a": "#f4f5ff", "drop_b": "#e9ecff",
        "drop_hover_a": "#eeeffe", "drop_hover_b": "#dfe4ff",
        "drop_active_a": "#e3e6ff", "drop_active_b": "#ccd4ff",
        "row_hover": "#f7f8fd", "drop_border": "#c3c9e6",
    },
    "dark": {
        "bg": "#0e121a", "card": "#1a202c", "list_bg": "#141a24",
        "border": "#2a3242", "divider": "#242c3a",
        "text": "#eef2f9", "muted": "#a3adc0", "faint": "#768096",
        "accent": "#7c93ff", "accent_hi": "#95a8ff", "accent_lo": "#1e2742",
        "chip": "#242c3a", "chip_hi": "#2e3748",
        "success": "#3ddc9a", "success_bg": "#0f2a20",
        "danger": "#ff8785", "danger_bg": "#2f1719",
        "warn": "#fbbf24", "warn_bg": "#2d2312",
        "drop_a": "#171e2c", "drop_b": "#1c2437",
        "drop_hover_a": "#1b2436", "drop_hover_b": "#212c44",
        "drop_active_a": "#1f2b47", "drop_active_b": "#27375c",
        "row_hover": "#1f2634", "drop_border": "#3c4864",
    },
}

# Mutated in place on theme change so every widget sees the new palette.
C = dict(THEMES["light"])

_scale = 1.0


def set_scale(value):
    global _scale
    _scale = max(value, 1.0)


def PX(n):
    return int(round(n * _scale))


def apply_theme(name):
    C.clear()
    C.update(THEMES[name])


def pick_fonts(root, lang):
    """Return (heading, body) family names available on this machine."""
    families = set(tkfont.families(root))

    def pick(candidates, fallback):
        for c in candidates:
            if c in families:
                return c
        return fallback

    if lang == "ja":
        return (pick(["Yu Gothic UI Semibold", "Yu Gothic UI", "Meiryo UI"], "Segoe UI"),
                pick(["Yu Gothic UI", "Meiryo UI"], "Segoe UI"))
    return (pick(["Segoe UI Variable Display Semib", "Segoe UI Semibold",
                  "Segoe UI Variable Display"], "Segoe UI"),
            pick(["Segoe UI Variable Text", "Segoe UI"], "Segoe UI"))


def fonts(head, body):
    return {
        "h1": (head, 19, "bold"), "h2": (head, 12, "bold"), "h3": (body, 10, "bold"),
        "body": (body, 10), "small": (body, 9), "tiny": (body, 9),
        "badge": (body, 9, "bold"), "btn": (body, 10), "btn_lg": (head, 12, "bold"),
    }
