"""Main application window."""

import io
import logging
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from . import config
from .core import (FORMATS, ConversionError, convert_file, convert_to,
                   destination_for, human_size, is_supported,
                   load_thumbnail_source, probe, scan_folder)
from .graphics import (bulb_icon, check_mark, flatten, gradient_card, pill,
                       radio_mark, rounded_cover, stack_illustration)
from .help import HelpWindow
from .i18n import tr
from .security import MAX_SCAN_FILES
from .theme import C, PX, apply_theme, fonts, pick_fonts, set_scale
from .widgets import Button, FileRow, Scrollbar, Segmented, Slider, round_rect

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

log = logging.getLogger(__name__)

# Frozen by PyInstaller the assets are unpacked beside the bundled modules,
# so _MEIPASS is the root rather than the folder above this package.
_ROOT = getattr(sys, "_MEIPASS", None) or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(_ROOT, "assets")
PRESETS = (("preset_small", 55), ("preset_balanced", 80), ("preset_high", 92))
FORMAT_KEYS = ("webp", "png", "jpeg")
FORMAT_LABELS = {"webp": "WebP", "png": "PNG", "jpeg": "JPEG"}

BaseTk = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk


class App(BaseTk):
    def __init__(self):
        super().__init__()
        set_scale(self.winfo_fpixels("1i") / 96.0)

        settings = config.load()
        self.lang = settings["lang"]
        self.theme = settings["theme"]
        apply_theme(self.theme)

        self.files = []
        self.meta = {}
        self.rows = {}
        self.quality = tk.IntVar(value=settings["quality"])
        self.lossless = tk.BooleanVar(value=settings["lossless"])
        self.overwrite = tk.BooleanVar(value=settings["overwrite"])
        self.out_format = tk.StringVar(value=settings["out_format"])
        self.dest_mode = tk.StringVar(value=settings["dest_mode"])
        self.output_dir = tk.StringVar(value=settings["output_dir"])

        self.cancel_flag = threading.Event()
        self._marks = {}
        self.help_win = None
        self.busy = False
        self.last_out_dir = None
        self._summary = None
        self._notice = None
        self.msgq = queue.Queue()
        self._preview_token = 0
        self._preview_photo = None
        self._drop_photo = None
        self._drop_state = "idle"

        self.thumb_px = PX(44)
        self.drop_h = PX(96)
        self.preview_w, self.preview_h = PX(136), PX(86)

        self.title(tr(self.lang, "title"))
        self.minsize(PX(820), PX(620))
        self.configure(bg=C["bg"])
        self._center(PX(940), PX(790))
        self._load_icons()
        self._apply_fonts()
        self._init_style()
        self._build()
        if self.theme == "dark":
            self._dark_titlebar(True)
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(60, self._pump)
        self.after(200, self.refresh_preview)

    # ---------- chrome ----------
    def _center(self, w, h):
        # Leave room for the title bar and the taskbar so the footer stays reachable.
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(w, sw - PX(40)), min(h, sh - PX(120))
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max((sh - h) // 2 - PX(24), 0)}")

    def _load_icons(self):
        self.logo_img = None
        self.logo_src = None
        ico = os.path.join(ASSETS, "icon.ico")
        try:
            # `default` also applies it to any dialog this window spawns.
            self.iconbitmap(ico, default=ico)
        except Exception:
            log.debug("window icon unavailable", exc_info=True)
        try:
            with Image.open(os.path.join(ASSETS, "logo.png")) as im:
                self.logo_src = im.copy()
        except Exception:
            log.debug("logo unavailable", exc_info=True)

    def _dark_titlebar(self, on, window=None):
        win = window or self
        try:
            import ctypes
            win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            val = ctypes.c_int(1 if on else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), 4)
        except Exception:
            log.debug("titlebar theming unavailable", exc_info=True)

    def _apply_fonts(self):
        self.font_head, self.font_body = pick_fonts(self, self.lang)
        self._fonts = fonts(self.font_head, self.font_body)

    def F(self, role):
        return self._fonts[role]

    def t(self, key, **kw):
        return tr(self.lang, key, **kw)

    def _init_style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("TFrame", background=C["bg"])

    def _bind_keys(self):
        self.bind("<Control-o>", lambda e: self.add_files())
        self.bind("<Control-Shift-O>", lambda e: self.add_folder())
        self.bind("<Control-Return>", lambda e: self.start())
        self.bind("<Escape>", lambda e: self.cancel_flag.set() if self.busy else None)

    def _settings(self):
        return {
            "lang": self.lang, "theme": self.theme,
            "quality": self.quality.get(), "lossless": self.lossless.get(),
            "overwrite": self.overwrite.get(), "out_format": self.out_format.get(),
            "dest_mode": self.dest_mode.get(), "output_dir": self.output_dir.get(),
        }

    def _on_close(self):
        self.cancel_flag.set()
        config.save(self._settings())
        self.destroy()

    # ---------- rebuild ----------
    def _rebuild(self):
        self._apply_fonts()
        apply_theme(self.theme)
        self._init_style()
        self.configure(bg=C["bg"])
        # The help window is a child toplevel: it would be destroyed below anyway,
        # and its colours are baked in, so close it now and bring it back after.
        reopen_help = None
        if self.help_win is not None:
            if self.help_win.winfo_exists():
                reopen_help = self.help_win.lang.get()
            self.help_win.destroy()
            self.help_win = None
        for w in self.winfo_children():
            w.destroy()
        self.rows.clear()
        self._build()
        if reopen_help:
            self.show_help()
            self.help_win.set_language(reopen_help)
        for path in self.files:
            self._make_row(path)
            if path in self.meta:
                self._apply_meta(path, self.meta[path])
        self._refresh_count()
        self.refresh_preview()

    def toggle_language(self):
        self.lang = "ja" if self.lang == "en" else "en"
        self.title(self.t("title"))
        self._rebuild()
        config.save(self._settings())

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self._dark_titlebar(self.theme == "dark")
        self._rebuild()
        config.save(self._settings())

    # ---------- layout ----------
    def _build(self):
        self._build_header()
        self._build_dropzone()
        self._build_toolbar()
        self._build_list()
        self._build_options()
        self._build_footer()
        self._sync_dest()
        self._sync_format()

    def _build_header(self):
        head = tk.Frame(self, bg=C["bg"])
        head.pack(fill="x", padx=PX(24), pady=(PX(18), PX(12)))
        if self.logo_src is not None:
            n = PX(42)
            self.logo_img = ImageTk.PhotoImage(self.logo_src.resize((n, n), Image.LANCZOS))
            tk.Label(head, image=self.logo_img, bg=C["bg"]).pack(side="left", padx=(0, PX(13)))
        tk.Label(head, text=self.t("title"), bg=C["bg"], fg=C["text"],
                 font=self.F("h1")).pack(side="left")
        # Kept on the far right so it reads as "ask about this window", not a setting.
        self.bulb_img = ImageTk.PhotoImage(bulb_icon(PX(17), C["accent"], C["chip"]))
        Button(head, "", self.show_help, kind="chip", height=32, pad=18,
               image=self.bulb_img).pack(side="right", padx=(PX(8), 0))
        Button(head, self.t("theme_alt") if self.theme == "dark" else self.t("theme"),
               self.toggle_theme, kind="chip", height=32, font=self.F("small"),
               pad=26).pack(side="right", padx=(PX(8), 0))
        Button(head, self.t("lang_btn"), self.toggle_language, kind="chip", height=32,
               font=self.F("small"), pad=26).pack(side="right")

    def show_help(self):
        """Open the explanation window, or raise it if it is already up."""
        if self.help_win is not None and self.help_win.winfo_exists():
            self.help_win.deiconify()
            self.help_win.lift()
            self.help_win.focus_set()
            return
        self.help_win = HelpWindow(self)
        self._dark_titlebar(self.theme == "dark", self.help_win)

    def _build_dropzone(self):
        self.drop = tk.Canvas(self, height=self.drop_h, bg=C["bg"], highlightthickness=0,
                              bd=0, cursor="hand2")
        self.drop.pack(fill="x", padx=PX(24))
        self.drop.bind("<Configure>", lambda e: self._draw_drop())
        self.drop.bind("<Button-1>", lambda e: self.add_files())
        self.drop.bind("<Enter>", lambda e: self._draw_drop("hover"))
        self.drop.bind("<Leave>", lambda e: self._draw_drop("idle"))
        if DND_AVAILABLE:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<DropEnter>>", lambda e: self._draw_drop("active"))
            self.drop.dnd_bind("<<DropLeave>>", lambda e: self._draw_drop("idle"))
            self.drop.dnd_bind("<<Drop>>", self._on_drop)

    def _draw_drop(self, state=None):
        if state:
            self._drop_state = state
        c = self.drop
        w = c.winfo_width()
        if w < 10:
            return
        h = self.drop_h
        st = self._drop_state
        top, bot = {"idle": ("drop_a", "drop_b"),
                    "hover": ("drop_hover_a", "drop_hover_b"),
                    "active": ("drop_active_a", "drop_active_b")}[st]
        card = gradient_card(w, h, C[top], C[bot], PX(16), C["bg"]).convert("RGBA")
        art = stack_illustration(PX(38 if st != "active" else 42), C["accent"], C["card"],
                                 C["muted"])
        # Stack art / heading / caption as one centred block so the zone can be
        # resized without the pieces colliding.
        main_h, sub_h, gap, tight = PX(21), PX(16), PX(7), PX(2)
        block = art.height + gap + main_h + tight + sub_h
        y = max((h - block) // 2, PX(4))
        card.alpha_composite(art, ((w - art.width) // 2, y))
        self._drop_photo = ImageTk.PhotoImage(card.convert("RGB"))
        c.delete("all")
        c.create_image(0, 0, image=self._drop_photo, anchor="nw")
        round_rect(c, 2, 2, w - 2, h - 2, PX(15), fill="", width=PX(2 if st == "idle" else 3),
                   outline=C["accent"] if st != "idle" else C["drop_border"],
                   dash=() if st == "active" else (7, 5))
        main_y = y + art.height + gap + main_h / 2
        c.create_text(w / 2, main_y,
                      text=self.t("drop_active") if st == "active" else self.t("drop_main"),
                      fill=C["accent"] if st == "active" else C["text"], font=self.F("h2"))
        c.create_text(w / 2, main_y + main_h / 2 + tight + sub_h / 2, text=self.t("drop_sub"),
                      fill=C["muted"], font=self.F("small"))

    def _build_toolbar(self):
        """Files come in through the drop zone; this row only reports and clears."""
        bar = tk.Frame(self, bg=C["bg"])
        bar.pack(fill="x", padx=PX(24), pady=(PX(10), PX(7)))
        self.count = tk.Label(bar, text="", bg=C["bg"], fg=C["muted"], font=self.F("small"))
        self.count.pack(side="left")
        self.clear_btn = Button(bar, self.t("clear"), self.clear_files, kind="danger",
                                height=30, font=self.F("small"), pad=24)
        self.clear_btn.pack(side="right")

    def _build_list(self):
        wrap = tk.Frame(self, bg=C["border"])
        wrap.pack(fill="both", expand=True, padx=PX(24))
        inner = tk.Frame(wrap, bg=C["list_bg"])
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.canvas = tk.Canvas(inner, bg=C["list_bg"], highlightthickness=0, bd=0,
                                height=PX(150))
        sb = Scrollbar(inner, self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=C["list_bg"])
        self.list_frame.bind("<Configure>",
                             lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _build_options(self):
        card = tk.Frame(self, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="x", padx=PX(24), pady=(PX(14), 0))

        top = tk.Frame(card, bg=C["card"])
        top.pack(fill="x", padx=PX(16), pady=(PX(14), PX(10)))

        pv = tk.Frame(top, bg=C["card"])
        pv.pack(side="left", padx=(0, PX(16)))
        self.preview_box = tk.Frame(pv, width=self.preview_w, height=self.preview_h, bg=C["chip"])
        self.preview_box.pack()
        self.preview_box.pack_propagate(False)
        self.preview_lbl = tk.Label(self.preview_box, bg=C["chip"], fg=C["faint"],
                                    font=self.F("small"), text=self.t("preview_empty"), bd=0)
        self.preview_lbl.place(relx=0.5, rely=0.5, anchor="center")

        right = tk.Frame(top, bg=C["card"])
        right.pack(side="left", fill="both", expand=True)

        line = tk.Frame(right, bg=C["card"])
        line.pack(fill="x")
        tk.Label(line, text=self.t("convert_to"), bg=C["card"], fg=C["text"],
                 font=self.F("h3")).pack(side="left", padx=(0, PX(10)))
        self.fmt_seg = Segmented(line, [FORMAT_LABELS[k] for k in FORMAT_KEYS],
                                 list(FORMAT_KEYS), self.out_format,
                                 command=self._on_format, font=self.F("small"))
        self.fmt_seg.pack(side="left", padx=(0, PX(22)))
        tk.Label(line, text=self.t("quality"), bg=C["card"], fg=C["text"],
                 font=self.F("h3")).pack(side="left")
        self.qval = tk.Label(line, text=str(self.quality.get()), bg=C["accent_lo"],
                             fg=C["accent"], font=self.F("badge"), padx=PX(9), pady=PX(2))
        self.qval.pack(side="left", padx=PX(9))
        self.est = tk.Label(line, text="", bg=C["card"], fg=C["muted"], font=self.F("small"))
        self.est.pack(side="left")
        self.lossless_box = self._checkbox(line, self.lossless, self.t("lossless"),
                                           self._schedule_preview)
        self.lossless_box.pack(side="right")

        self.slider = Slider(right, self.quality, 1, 100, command=self._on_quality)
        self.slider.pack(fill="x", pady=(PX(6), PX(8)))

        preset_row = tk.Frame(right, bg=C["card"])
        preset_row.pack(fill="x")
        self.presets = Segmented(preset_row, [self.t(k) for k, _ in PRESETS],
                                 [v for _, v in PRESETS], self.quality,
                                 command=self._on_preset, font=self.F("small"))
        self.presets.pack(side="left")
        self.fmt_note = tk.Label(preset_row, text="", bg=C["card"], fg=C["muted"],
                                 font=self.F("small"))
        self.fmt_note.pack(side="left", padx=PX(12))

        tk.Frame(card, bg=C["divider"], height=1).pack(fill="x", padx=PX(16))

        dest = tk.Frame(card, bg=C["card"])
        dest.pack(fill="x", padx=PX(16), pady=(PX(10), PX(13)))
        tk.Label(dest, text=self.t("save_to"), bg=C["card"], fg=C["text"],
                 font=self.F("h3")).pack(side="left", padx=(0, PX(12)))
        self.dest_same = self._radio(dest, "same", self.t("same_folder"))
        self.dest_same.pack(side="left")
        self.dest_custom = self._radio(dest, "custom", self.t("custom_folder"))
        self.dest_custom.pack(side="left", padx=(PX(14), PX(8)))
        self.choose_btn = Button(dest, self.t("choose"), self.choose_output_dir, height=28,
                                 font=self.F("small"), pad=22)
        self.choose_btn.pack(side="left")
        self.dest_label = tk.Label(dest, text="", bg=C["card"], fg=C["muted"],
                                   font=self.F("small"))
        self.dest_label.pack(side="left", padx=PX(9))
        self._checkbox(dest, self.overwrite, self.t("overwrite")).pack(side="right")

    def _build_footer(self):
        self.prog_row = tk.Frame(self, bg=C["bg"])
        self.prog_bar = tk.Canvas(self.prog_row, height=PX(8), highlightthickness=0, bd=0,
                                  bg=C["bg"])
        self.prog_bar.pack(fill="x", side="left", expand=True)
        self.prog_txt = tk.Label(self.prog_row, text="", bg=C["bg"], fg=C["muted"],
                                 font=self.F("small"))
        self.prog_txt.pack(side="left", padx=(PX(12), 0))

        foot = tk.Frame(self, bg=C["bg"])
        foot.pack(fill="x", padx=PX(24), pady=(PX(14), PX(16)))

        self.convert_btn = Button(foot, self.t("convert_to_fmt",
                                                fmt=FORMAT_LABELS[self.out_format.get()]),
                                  self.start, kind="primary",
                                  height=46, font=self.F("btn_lg"), pad=44)
        self.convert_btn.pack(side="right")
        self.open_btn = Button(foot, self.t("open_folder"), self.open_output, height=46,
                               font=self.F("btn"))
        self.status = tk.Label(foot, text="", bg=C["bg"], fg=C["muted"], font=self.F("small"))
        self.status.pack(side="right", padx=PX(14))
        if self.last_out_dir:
            self.open_btn.pack(side="right")
        if self._summary:
            self._render_summary()
        elif self._notice:
            self.status.config(text=self._notice, fg=C["warn"])

    def _render_summary(self):
        ok, fail, saved, pct, cancelled = self._summary
        if cancelled:
            text, key = self.t("cancelled"), "muted"
        elif fail:
            text = self.t("summary", ok=ok, fail=fail, saved=human_size(saved), pct=f"{pct:.0f}")
            key = "warn"
        else:
            text = self.t("summary_ok", ok=ok, saved=human_size(saved), pct=f"{pct:.0f}")
            key = "success"
        self.status.config(text=text, fg=C[key])

    def _draw_progress(self, frac):
        c = self.prog_bar
        c.delete("all")
        w = c.winfo_width()
        if w < 10:
            return
        h = PX(8)
        bar = pill(w, h, C["chip"])
        if frac > 0:
            bar.alpha_composite(pill(max(int(w * frac), PX(8)), h, C["accent"]))
        self._prog_photo = ImageTk.PhotoImage(flatten(bar, C["bg"]))
        c.create_image(0, 0, image=self._prog_photo, anchor="nw")

    def _mark_photo(self, draw, n, on, accent, border, bg):
        """Cached PIL-rendered tick/dot. Only a handful of variants ever exist,
        so the cache keeps clicking instant without redrawing at 4x each time."""
        key = (draw.__name__, n, on, accent, border, bg)
        photo = self._marks.get(key)
        if photo is None:
            photo = ImageTk.PhotoImage(draw(n, on, accent, border, bg))
            self._marks[key] = photo
        return photo

    def _checkbox(self, parent, var, text, command=None):
        box = tk.Frame(parent, bg=C["card"], cursor="hand2")
        state = {"on": True}
        n = PX(18)
        mark = tk.Canvas(box, width=n, height=n, highlightthickness=0, bd=0, bg=C["card"])
        mark.pack(side="left")
        lbl = tk.Label(box, text=text, bg=C["card"], fg=C["text"], font=self.F("small"))
        lbl.pack(side="left", padx=PX(6))

        def render():
            mark.delete("all")
            on = var.get()
            live = state["on"]
            accent = C["accent"] if live else C["faint"]
            mark.photo = self._mark_photo(check_mark, n, on, accent, C["border"], C["card"])
            mark.create_image(0, 0, image=mark.photo, anchor="nw")
            lbl.config(fg=C["text"] if live else C["faint"])

        def toggle(_=None):
            if not state["on"]:
                return
            var.set(not var.get())
            render()
            if command:
                command()

        def set_enabled(on):
            state["on"] = on
            box.config(cursor="hand2" if on else "arrow")
            render()

        for w in (box, mark, lbl):
            w.bind("<Button-1>", toggle)
        box.set_enabled = set_enabled
        render()
        return box

    def _radio(self, parent, value, text):
        box = tk.Frame(parent, bg=C["card"], cursor="hand2")
        n = PX(18)
        dot = tk.Canvas(box, width=n, height=n, highlightthickness=0, bd=0, bg=C["card"])
        dot.pack(side="left")
        lbl = tk.Label(box, text=text, bg=C["card"], fg=C["text"], font=self.F("small"))
        lbl.pack(side="left", padx=PX(6))

        def pick(_=None):
            self.dest_mode.set(value)
            self._sync_dest()

        for w in (box, dot, lbl):
            w.bind("<Button-1>", pick)
        box._dot, box._value, box._n = dot, value, n
        return box

    def _sync_dest(self):
        mode = self.dest_mode.get()
        for box in (self.dest_same, self.dest_custom):
            on = box._value == mode
            n, d = box._n, box._dot
            d.delete("all")
            d.photo = self._mark_photo(radio_mark, n, on, C["accent"], C["border"], C["card"])
            d.create_image(0, 0, image=d.photo, anchor="nw")
        self.choose_btn.set_enabled(mode == "custom")
        path = self.output_dir.get()
        self.dest_label.config(
            text=(os.path.basename(path.rstrip("/\\")) or path) if mode == "custom" and path else "")

    # ---------- files ----------
    def _on_drop(self, event):
        for p in self.tk.splitlist(event.data):
            if os.path.isdir(p):
                self._scan(p)
            else:
                self._add(p)
        self._draw_drop("idle")
        self._refresh_count()
        self.refresh_preview()

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _make_row(self, path):
        row = FileRow(self.list_frame, path, self)
        row.pack(fill="x", padx=PX(10), pady=PX(5))
        self.rows[path] = row
        return row

    def _apply_meta(self, path, m):
        row = self.rows.get(path)
        if not row:
            return
        photo = None
        if m.get("pil") is not None:
            t = self.thumb_px
            photo = ImageTk.PhotoImage(rounded_cover(m["pil"], t, t, PX(9), C["chip"]))
        row.set_meta(photo, m.get("dims", "—"), m.get("size"))
        if m.get("done"):
            if m.get("out_path"):
                row.set_output(os.path.basename(m["out_path"]))
            row.set_result(m.get("new_size"), m.get("error"))

    def _add(self, path):
        path = os.path.abspath(path)
        if not is_supported(path) or path in self.rows or not os.path.isfile(path):
            return
        self.files.append(path)
        self._make_row(path)
        threading.Thread(target=self._load_meta, args=(path,), daemon=True).start()

    def _load_meta(self, path):
        try:
            w, h, size = probe(path)
            self.msgq.put(("meta", path, load_thumbnail_source(path), f"{w}×{h}", size))
        except Exception as e:
            log.warning("could not read %s: %s", path, e)
            self.msgq.put(("meta", path, None, "—", None))

    def _scan(self, folder):
        count = 0
        for path in scan_folder(folder):
            self._add(path)
            count += 1
        if count >= MAX_SCAN_FILES:
            self._notice = self.t("scan_limit", n=MAX_SCAN_FILES)
            self.status.config(text=self._notice, fg=C["warn"])

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title=self.t("add_files"),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.tif *.tiff *.webp"),
                       ("All files", "*.*")])
        for p in paths:
            self._add(p)
        self._refresh_count()
        self.refresh_preview()

    def add_folder(self):
        d = filedialog.askdirectory(title=self.t("add_folder"))
        if d:
            self._scan(d)
        self._refresh_count()
        self.refresh_preview()

    def remove_file(self, path):
        if self.busy or path not in self.rows:
            return
        self.rows.pop(path).destroy()
        self.files.remove(path)
        self.meta.pop(path, None)
        self._refresh_count()
        self.refresh_preview()

    def clear_files(self):
        if self.busy:
            return
        for row in self.rows.values():
            row.destroy()
        self.rows.clear()
        self.files.clear()
        self.meta.clear()
        self._refresh_count()
        self.refresh_preview()

    def open_row(self, src):
        """Open the row's converted file once it exists, else the source."""
        out = self.meta.get(src, {}).get("out_path")
        self.open_path(out if out and os.path.isfile(out) else src)

    def open_path(self, path):
        """Open a file the user added, via the shell. Extension is whitelisted."""
        if os.path.isfile(path) and is_supported(path):
            try:
                os.startfile(path)
            except OSError as e:
                log.warning("could not open %s: %s", path, e)

    def _refresh_count(self):
        n = len(self.files)
        self.count.config(text="" if not n else
                          self.t("count_one" if n == 1 else "count_many", n=n))
        if n:
            self.clear_btn.pack(side="right")
        else:
            self.clear_btn.pack_forget()

    # ---------- output format ----------
    def _on_format(self, _value=None):
        if self.busy:
            return
        self._sync_format()
        self.refresh_preview()

    def output_name(self, path):
        """The file this source will produce, for display in its row."""
        stem = os.path.splitext(os.path.basename(path))[0]
        return stem + FORMATS[self.out_format.get()][0]

    def _sync_format(self):
        """PNG is always lossless, so its quality controls carry no meaning."""
        fmt = self.out_format.get()
        for path, row in self.rows.items():
            if not self.meta.get(path, {}).get("done"):
                row.set_output(self.output_name(path))
        graded = fmt != "png"
        self.slider.set_enabled(graded)
        self.presets.set_enabled(graded)
        self.lossless_box.set_enabled(fmt == "webp")
        self.qval.config(text=str(self.quality.get()) if graded else "—",
                         fg=C["accent"] if graded else C["faint"])
        self.fmt_note.config(text="" if graded else self.t("png_lossless"))
        self.convert_btn.set_text(self.t("convert_to_fmt", fmt=FORMAT_LABELS[fmt]))

    # ---------- quality preview ----------
    def _on_quality(self, v):
        self.qval.config(text=str(v))
        self.presets.draw()
        self._schedule_preview()

    def _on_preset(self, v):
        self.qval.config(text=str(v))
        self.slider.draw()
        self._schedule_preview()

    def _schedule_preview(self):
        if getattr(self, "_preview_job", None):
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(260, self.refresh_preview)

    def refresh_preview(self):
        self._preview_token += 1
        if not self.files:
            self._preview_photo = None
            self.preview_lbl.config(image="", text=self.t("preview_empty"))
            self.est.config(text="")
            return
        self.est.config(text=self.t("estimating"))
        threading.Thread(target=self._build_preview,
                         args=(self._preview_token, self.files[0], self.quality.get(),
                               self.lossless.get(), self.out_format.get()),
                         daemon=True).start()

    def _build_preview(self, token, src, quality, lossless, fmt):
        try:
            buf = io.BytesIO()
            convert_to(src, buf, quality, lossless, fmt)
            nbytes = buf.tell()
            buf.seek(0)
            with Image.open(buf) as dec:
                self.msgq.put(("preview", token, dec.convert("RGB"), nbytes))
        except Exception as e:
            log.debug("preview failed: %s", e)
            self.msgq.put(("preview", token, None, None))

    def _show_preview(self, token, pil, nbytes):
        if token != self._preview_token or pil is None:
            return
        out = rounded_cover(pil, self.preview_w, self.preview_h, PX(9), C["card"])
        self._preview_photo = ImageTk.PhotoImage(out)
        self.preview_lbl.config(image=self._preview_photo, text="")
        self.est.config(text=self.t("est_size", size=human_size(nbytes)))

    # ---------- conversion ----------
    def choose_output_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir.set(d)
            self.dest_mode.set("custom")
            self._sync_dest()

    def open_output(self):
        if self.last_out_dir and os.path.isdir(self.last_out_dir):
            try:
                os.startfile(self.last_out_dir)
            except OSError as e:
                log.warning("could not open folder: %s", e)

    def start(self):
        if self.busy:
            self.cancel_flag.set()
            return
        if not self.files:
            self.status.config(text=self.t("no_files"), fg=C["danger"])
            return
        if self.dest_mode.get() == "custom" and not os.path.isdir(self.output_dir.get()):
            self.status.config(text=self.t("no_outdir"), fg=C["danger"])
            return

        config.save(self._settings())
        self.busy = True
        self._notice = None
        self.cancel_flag.clear()
        self.open_btn.pack_forget()
        self.convert_btn.set_kind("stop")
        self.convert_btn.set_text(self.t("cancel"))
        self.status.config(text="")
        self.prog_row.pack(fill="x", padx=PX(24), pady=(PX(4), 0), before=self.status.master)
        self.update_idletasks()
        self._draw_progress(0)
        self.prog_txt.config(text=self.t("converting", i=0, n=len(self.files)))
        for row in self.rows.values():
            row.set_waiting()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        quality, lossless = self.quality.get(), self.lossless.get()
        fmt = self.out_format.get()
        same = self.dest_mode.get() == "same"
        out_dir = self.output_dir.get()
        overwrite = self.overwrite.get()
        ok = fail = before = after = 0
        last_dir = None

        for i, src in enumerate(list(self.files), 1):
            if self.cancel_flag.is_set():
                break
            self.msgq.put(("busy", src, i))
            try:
                dest_dir = os.path.dirname(src) if same else out_dir
                os.makedirs(dest_dir, exist_ok=True)
                dest = destination_for(src, dest_dir, overwrite, fmt)
                new_size = convert_file(src, dest, quality, lossless, fmt)
                before += os.path.getsize(src)
                after += new_size
                last_dir, ok = dest_dir, ok + 1
                self.msgq.put(("row", src, new_size, None, dest))
            except (ConversionError, OSError) as e:
                fail += 1
                log.warning("failed to convert %s: %s", src, e)
                self.msgq.put(("row", src, None, e, None))
            self.msgq.put(("prog", i))

        self.msgq.put(("done", ok, fail, before, after, last_dir, self.cancel_flag.is_set()))

    def _pump(self):
        try:
            while True:
                msg = self.msgq.get_nowait()
                kind = msg[0]
                if kind == "meta":
                    _, path, pil, dims, size = msg
                    self.meta.setdefault(path, {}).update(pil=pil, dims=dims, size=size)
                    self._apply_meta(path, self.meta[path])
                    if self.files and self.files[0] == path:
                        self.refresh_preview()
                elif kind == "preview":
                    self._show_preview(msg[1], msg[2], msg[3])
                elif kind == "busy":
                    if msg[1] in self.rows:
                        self.rows[msg[1]].set_busy()
                    self.prog_txt.config(text=self.t("converting", i=msg[2], n=len(self.files)))
                elif kind == "row":
                    _, path, new_size, err, out_path = msg
                    self.meta.setdefault(path, {}).update(
                        done=True, new_size=new_size, error=err, out_path=out_path)
                    if path in self.rows:
                        if out_path:
                            self.rows[path].set_output(os.path.basename(out_path))
                        self.rows[path].set_result(new_size, err)
                elif kind == "prog":
                    self._draw_progress(msg[1] / max(len(self.files), 1))
                elif kind == "done":
                    self._finish(*msg[1:])
        except queue.Empty:
            pass
        self.after(60, self._pump)

    def _finish(self, ok, fail, before, after, last_dir, cancelled):
        self.busy = False
        self.prog_row.pack_forget()
        self.convert_btn.set_kind("primary")
        self.convert_btn.set_text(
            self.t("convert_to_fmt", fmt=FORMAT_LABELS[self.out_format.get()]))
        saved = max(before - after, 0)
        pct = 0 if not before else saved / before * 100
        self._summary = (ok, fail, saved, pct, cancelled)
        self._render_summary()
        if last_dir:
            self.last_out_dir = last_dir
            self.open_btn.pack(side="right")
