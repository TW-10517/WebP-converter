"""Custom Tk widgets - flat, theme-aware, drawn on canvases."""

import os
import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageTk

from .core import human_size
from .graphics import flatten, knob, pill
from .theme import C, PX


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class Button(tk.Canvas):
    KINDS = {
        "primary": ("accent", "accent_hi", "#ffffff", None),
        "secondary": ("card", "chip", "text", "border"),
        "chip": ("chip", "chip_hi", "muted", "border"),
        "danger": ("card", "danger_bg", "danger", "border"),
        "stop": ("danger_bg", "danger_bg", "danger", "danger"),
    }

    def __init__(self, parent, text, command, kind="secondary", height=36, font=None,
                 pad=34, image=None):
        self.kind = kind
        self.font = font or ("Segoe UI", 10)
        self._text = text
        self._image = image
        self._command = command
        self._enabled = True
        self._hover = False
        self._pad = PX(pad)
        self._h = PX(height)
        super().__init__(parent, width=self._measure(text), height=self._h,
                         highlightthickness=0, bd=0, bg=parent.cget("bg"), cursor="hand2")
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", self._click)
        self._draw()

    def _measure(self, text):
        if self._image is not None:
            return self._image.width() + self._pad
        try:
            return tkfont.Font(font=self.font).measure(text) + self._pad
        except Exception:
            return PX(90)

    def _set_hover(self, on):
        self._hover = on
        self._draw()

    def _click(self, _):
        if self._enabled and self._command:
            self._command()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or self._measure(self._text)
        h = self._h
        fk, hk, fg, bk = self.KINDS[self.kind]
        fill = C[hk] if (self._hover and self._enabled) else C[fk]
        fg = fg if fg.startswith("#") else C[fg]
        border = C[bk] if bk else fill
        if not self._enabled:
            fill, fg, border = C["chip"], C["faint"], C["chip"]
        round_rect(self, 1, 1, w - 1, h - 1, PX(10), fill=fill, outline=border, width=1)
        if self._image is not None:
            self.create_image(w / 2, h / 2, image=self._image)
        else:
            self.create_text(w / 2, h / 2 + 1, text=self._text, fill=fg, font=self.font)

    def set_text(self, text):
        self._text = text
        self.config(width=self._measure(text))
        self._draw()

    def set_kind(self, kind):
        self.kind = kind
        self._draw()

    def set_enabled(self, on):
        self._enabled = on
        self.config(cursor="hand2" if on else "arrow")
        self._draw()


class Segmented(tk.Canvas):
    def __init__(self, parent, labels, values, variable, command=None, height=32, font=None):
        self.labels, self.values = labels, values
        self.var, self.command = variable, command
        self.font = font or ("Segoe UI", 9)
        self._h = PX(height)
        measure = tkfont.Font(font=self.font)
        self._seg_w = [measure.measure(t) + PX(26) for t in labels]
        super().__init__(parent, width=sum(self._seg_w) + PX(8), height=self._h,
                         highlightthickness=0, bd=0, bg=parent.cget("bg"), cursor="hand2")
        self._enabled = True
        self.bind("<Button-1>", self._click)
        self.bind("<Configure>", lambda e: self.draw())
        self.draw()

    def set_enabled(self, on):
        self._enabled = on
        self.config(cursor="hand2" if on else "arrow")
        self.draw()

    def _click(self, event):
        if not self._enabled:
            return
        x = PX(4)
        for w, v in zip(self._seg_w, self.values):
            if x <= event.x < x + w:
                self.var.set(v)
                self.draw()
                if self.command:
                    self.command(v)
                return
            x += w

    def draw(self):
        self.delete("all")
        w = self.winfo_width() or sum(self._seg_w) + PX(8)
        round_rect(self, 0, 0, w, self._h, PX(9), fill=C["chip"], outline=C["chip"])
        x = PX(4)
        accent = C["accent"] if self._enabled else C["faint"]
        for label, seg_w, value in zip(self.labels, self._seg_w, self.values):
            on = self.var.get() == value
            if on:
                round_rect(self, x, PX(4), x + seg_w, self._h - PX(4), PX(7),
                           fill=C["card"], outline=accent, width=1)
            self.create_text(x + seg_w / 2, self._h / 2 + 1, text=label,
                             fill=accent if on else C["faint"] if not self._enabled
                             else C["muted"],
                             font=(self.font[0], self.font[1], "bold") if on else self.font)
            x += seg_w


class Scrollbar(tk.Canvas):
    """Slim rounded scrollbar that hides itself when everything already fits."""

    def __init__(self, parent, command, width=11, bg=None):
        # NB: not self._w - Tk's Misc uses that name for the widget path.
        self._bar_w = PX(width)
        # height=1: the bar always fills its parent, so its own request must not
        # inflate the row it sits in.
        super().__init__(parent, width=self._bar_w, height=1, highlightthickness=0, bd=0,
                         bg=bg or C["list_bg"])
        self.command = command
        self._bg = bg or C["list_bg"]
        self._first, self._last = 0.0, 1.0
        self._hover = False
        self._drag_from = None
        self._thumbs = {}
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag_from", None))

    def set(self, first, last):
        self._first, self._last = float(first), float(last)
        self._draw()

    def _set_hover(self, on):
        self._hover = on
        self._draw()

    def _span(self):
        h = self.winfo_height()
        top = self._first * h
        length = max((self._last - self._first) * h, PX(28))
        return top, min(length, h)

    def _press(self, event):
        top, length = self._span()
        if top <= event.y <= top + length:
            self._drag_from = (event.y, self._first)
        else:
            h = max(self.winfo_height(), 1)
            frac = min(max((event.y - length / 2) / h, 0.0), 1.0)
            self.command("moveto", frac)

    def _drag(self, event):
        if not self._drag_from:
            return
        y0, first0 = self._drag_from
        h = max(self.winfo_height(), 1)
        self.command("moveto", min(max(first0 + (event.y - y0) / h, 0.0), 1.0))

    def _thumb(self, length, color):
        key = (length, color)
        img = self._thumbs.get(key)
        if img is None:
            if len(self._thumbs) > 12:      # only grows while the list is resized
                self._thumbs.clear()
            img = ImageTk.PhotoImage(
                pill(self._bar_w - PX(4), length, color, self._bg))
            self._thumbs[key] = img
        return img

    def _draw(self):
        self.delete("all")
        if self._first <= 0.0 and self._last >= 1.0:
            return
        top, length = self._span()
        pad = PX(2)
        length = max(int(length) - 2 * pad, PX(14))
        color = C["muted"] if self._hover else C["faint"]
        self.create_image(pad, int(top) + pad, image=self._thumb(length, color), anchor="nw")


class Slider(tk.Canvas):
    def __init__(self, parent, variable, from_=1, to=100, height=36, command=None):
        self._h = PX(height)
        super().__init__(parent, height=self._h, highlightthickness=0, bd=0,
                         bg=parent.cget("bg"), cursor="hand2")
        self.var, self.lo, self.hi, self.command = variable, from_, to, command
        self._bg = parent.cget("bg")
        self._hover = False
        self._enabled = True
        self._knobs = {}
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._press)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<MouseWheel>", self._wheel)

    def set_enabled(self, on):
        self._enabled = on
        self.config(cursor="hand2" if on else "arrow")
        self.draw()

    def _set_hover(self, on):
        self._hover = on and self._enabled
        self.draw()

    def _wheel(self, event):
        if not self._enabled:
            return "break"
        step = 1 if event.delta > 0 else -1
        self.var.set(min(max(self.var.get() + step, self.lo), self.hi))
        self._emit()
        return "break"

    def _press(self, event):
        if not self._enabled:
            return
        pad, w = PX(14), max(self.winfo_width(), PX(60))
        frac = min(max((event.x - pad) / max(w - 2 * pad, 1), 0.0), 1.0)
        self.var.set(round(self.lo + frac * (self.hi - self.lo)))
        self._emit()

    def _emit(self):
        self.draw()
        if self.command:
            self.command(self.var.get())

    def _knob(self, r, accent):
        key = (r, accent, self._enabled)
        img = self._knobs.get(key)
        if img is None:
            self._knobs.clear()
            img = knob(r, C["card"], accent, PX(3),
                       halo=PX(3) if self._enabled else 0, halo_color=C["accent_lo"])
            self._knobs[key] = img
        return img

    def draw(self):
        self.delete("all")
        pad, w = PX(14), max(self.winfo_width(), PX(60))
        h = self._h
        cy = h / 2
        frac = (self.var.get() - self.lo) / (self.hi - self.lo)
        x = pad + frac * (w - 2 * pad)
        t = PX(4)
        accent = C["accent"] if self._enabled else C["faint"]

        base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        top = int(cy - t)
        base.alpha_composite(pill(w - 2 * pad, 2 * t, C["chip"]), (pad, top))
        if x > pad + 1:
            base.alpha_composite(pill(int(x - pad), 2 * t, accent), (pad, top))
        k = self._knob(PX(12 if self._hover else 10), accent)
        base.alpha_composite(k, (int(x - k.width / 2), int(cy - k.height / 2)))

        self._photo = ImageTk.PhotoImage(flatten(base, self._bg))
        self.create_image(0, 0, image=self._photo, anchor="nw")


class Spinner(tk.Canvas):
    def __init__(self, parent, size=16, bg=None):
        self.size = PX(size)
        super().__init__(parent, width=self.size, height=self.size, highlightthickness=0,
                         bd=0, bg=bg or parent.cget("bg"))
        self.angle = 0
        self.running = False

    def start(self):
        if not self.running:
            self.running = True
            self._tick()

    def stop(self):
        self.running = False
        self.delete("all")

    def _tick(self):
        if not self.running or not self.winfo_exists():
            return
        self.delete("all")
        pad = PX(2)
        self.create_arc(pad, pad, self.size - pad, self.size - pad, start=self.angle,
                        extent=95, style="arc", outline=C["accent"], width=PX(2))
        self.angle = (self.angle - 30) % 360
        self.after(70, self._tick)


class FileRow(tk.Frame):
    """One image: thumbnail, name, before/after size and a savings badge."""

    def __init__(self, parent, path, app):
        super().__init__(parent, bg=C["card"], highlightbackground=C["border"],
                         highlightthickness=1, bd=0)
        self.path, self.app = path, app
        self.thumb_img = None
        self.orig_size = None
        self.src_kind = os.path.splitext(path)[1].lstrip(".").upper()
        self._dims = None
        t = app.thumb_px

        holder = tk.Frame(self, width=t, height=t, bg=C["chip"])
        holder.grid(row=0, column=0, rowspan=2, padx=(PX(12), PX(14)), pady=PX(13))
        holder.grid_propagate(False)
        self.thumb = tk.Label(holder, bg=C["chip"], bd=0)
        self.thumb.place(relx=0.5, rely=0.5, anchor="center")

        # The label names the file this row will produce, not the one it reads.
        self.name = tk.Label(self, text=app.output_name(path), bg=C["card"], fg=C["text"],
                             font=app.F("body"), anchor="w")
        self.name.grid(row=0, column=1, sticky="w", pady=(PX(14), 0))
        self.detail = tk.Label(self, text="", bg=C["card"], fg=C["muted"],
                               font=app.F("small"), anchor="w")
        self.detail.grid(row=1, column=1, sticky="w", pady=(PX(2), PX(14)))

        self.actions = tk.Frame(self, bg=C["card"])
        self.actions.grid(row=0, column=2, rowspan=2, padx=(PX(6), PX(2)))
        self.open_lbl = tk.Label(self.actions, text=app.t("open_img"), bg=C["card"],
                                 fg=C["accent"], font=app.F("small"), cursor="hand2",
                                 padx=PX(8))
        self.open_lbl.pack(side="left")
        self.open_lbl.bind("<Button-1>", lambda e: app.open_row(self.path))

        self.spinner = Spinner(self, 16, bg=C["card"])
        self.spinner.grid(row=0, column=3, rowspan=2, padx=PX(2))
        # Blends into the row until a state actually gives it a colour.
        self.badge = tk.Label(self, text="", bg=C["card"], fg=C["muted"],
                              font=app.F("badge"), padx=PX(10), pady=PX(4))
        self.badge.grid(row=0, column=4, rowspan=2, padx=(PX(4), PX(8)))
        self.remove = tk.Label(self, text="✕", bg=C["card"], fg=C["faint"],
                               font=(app.font_body, 11), cursor="hand2", padx=PX(8))
        self.remove.grid(row=0, column=5, rowspan=2, padx=(0, PX(8)))
        self.remove.bind("<Button-1>", lambda e: app.remove_file(self.path))
        self.remove.bind("<Enter>", lambda e: self.remove.config(fg=C["danger"]))
        self.remove.bind("<Leave>", lambda e: self.remove.config(fg=C["faint"]))

        self.columnconfigure(1, weight=1)
        self.actions.grid_remove()
        for w in (self, self.name, self.detail, self.thumb, holder, self.badge):
            w.bind("<Enter>", lambda e: self._hover(True))
            w.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, on):
        if on:
            self.actions.grid()
        else:
            x, y = self.winfo_pointerxy()
            if self.winfo_containing(x, y) not in self._descendants():
                self.actions.grid_remove()
        self._tint(C["row_hover"] if on else C["card"])

    def _descendants(self):
        out, stack = [], [self]
        while stack:
            w = stack.pop()
            out.append(w)
            stack.extend(w.winfo_children())
        return out

    def _tint(self, color):
        for w in (self, self.name, self.detail, self.remove, self.actions,
                  self.open_lbl, self.spinner):
            w.config(bg=color)

    def set_output(self, name):
        self.name.config(text=name)

    def set_meta(self, photo, dims, size):
        if photo is not None:
            self.thumb_img = photo
            self.thumb.config(image=photo)
        self.orig_size = size
        self._dims = dims
        # The source format goes here since the label above now names the output.
        self.detail.config(text=f"{self.src_kind}   ·   {dims}   ·   {human_size(size)}",
                           fg=C["muted"])

    def set_waiting(self):
        self.spinner.stop()
        self.badge.config(text=self.app.t("row_wait"), bg=C["chip"], fg=C["faint"])

    def set_busy(self):
        self.badge.config(text=self.app.t("row_busy"), bg=C["accent_lo"], fg=C["accent"])
        self.spinner.start()

    def set_result(self, new_size, error=None):
        self.spinner.stop()
        if error:
            self.badge.config(text=self.app.t("failed_row"), bg=C["danger_bg"], fg=C["danger"])
            self.detail.config(text=str(error)[:70], fg=C["danger"])
            return
        pct = 0 if not self.orig_size else (1 - new_size / self.orig_size) * 100
        self.detail.config(text=f"{human_size(self.orig_size)}   →   {human_size(new_size)}",
                           fg=C["muted"])
        if pct >= 0:
            self.badge.config(text=f"▼ {pct:.0f}%", bg=C["success_bg"], fg=C["success"])
        else:
            self.badge.config(text=f"▲ {-pct:.0f}%", bg=C["warn_bg"], fg=C["warn"])
