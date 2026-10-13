"""The help window: what every control does, in English and Japanese."""

import tkinter as tk

from .i18n import HELP, tr
from .theme import C, PX
from .widgets import Button, Scrollbar, Segmented


class HelpWindow(tk.Toplevel):
    """A scrolling explanation of the UI, with its own language switch.

    The switch is local to this window: you can read the help in either
    language without changing the language of the app behind it.
    """

    def __init__(self, app):
        super().__init__(app, bg=C["bg"])
        self.app = app
        self.lang = tk.StringVar(value=app.lang)
        self.title(tr(app.lang, "help_title"))
        self.transient(app)
        self.resizable(True, True)
        self.minsize(PX(430), PX(340))
        self._place_over(app, PX(600), PX(660))

        self._build_header()
        self._build_body()
        self._render()

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<MouseWheel>", self._wheel)  # beats the app-wide binding
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(10, self.focus_set)

    def _place_over(self, app, w, h):
        h = min(h, app.winfo_screenheight() - PX(120))
        x = app.winfo_rootx() + max((app.winfo_width() - w) // 2, 0)
        y = app.winfo_rooty() + PX(30)
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def _build_header(self):
        head = tk.Frame(self, bg=C["bg"])
        head.pack(fill="x", padx=PX(22), pady=(PX(18), PX(10)))
        self.h_title = tk.Label(head, bg=C["bg"], fg=C["text"], font=self.app.F("h1"))
        self.h_title.pack(anchor="w")
        self.h_sub = tk.Label(head, bg=C["bg"], fg=C["muted"], font=self.app.F("small"))
        self.h_sub.pack(anchor="w", pady=(PX(2), PX(10)))
        self.lang_seg = Segmented(head, ["English", "日本語"], ["en", "ja"], self.lang,
                                  command=lambda _v: self._render(),
                                  font=self.app.F("small"))
        self.lang_seg.pack(anchor="w")

    def _build_body(self):
        wrap = tk.Frame(self, bg=C["border"])
        wrap.pack(fill="both", expand=True, padx=PX(22))
        inner = tk.Frame(wrap, bg=C["card"])
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        self.canvas = tk.Canvas(inner, bg=C["card"], highlightthickness=0, bd=0,
                                height=PX(200))
        bar = Scrollbar(inner, self.canvas.yview, bg=C["card"])
        self.body = tk.Frame(self.canvas, bg=C["card"])
        self.body.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self._resize)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        foot = tk.Frame(self, bg=C["bg"])
        foot.pack(fill="x", padx=PX(22), pady=(PX(12), PX(16)))
        self.close_btn = Button(foot, "", self.destroy, kind="primary", height=38,
                                font=self.app.F("btn"))
        self.close_btn.pack(side="right")

    def set_language(self, lang):
        self.lang.set(lang)
        self.lang_seg.draw()
        self._render()

    def _resize(self, event):
        self.canvas.itemconfig(self._win, width=event.width)
        self._rewrap(event.width)

    def _rewrap(self, width):
        for label in getattr(self, "_bodies", ()):
            label.config(wraplength=max(width - PX(40), PX(220)))

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _render(self):
        lang = self.lang.get()
        self.h_title.config(text=tr(lang, "help_title"))
        self.h_sub.config(text=tr(lang, "help_sub"))
        self.close_btn.set_text(tr(lang, "close"))

        for child in self.body.winfo_children():
            child.destroy()
        self._bodies = []
        for i, (heading, text) in enumerate(HELP[lang]):
            block = tk.Frame(self.body, bg=C["card"])
            block.pack(fill="x", padx=PX(20), pady=(PX(16) if i == 0 else PX(4), 0))
            tk.Label(block, text=heading, bg=C["card"], fg=C["text"],
                     font=self.app.F("h3"), anchor="w", justify="left").pack(anchor="w")
            body = tk.Label(block, text=text, bg=C["card"], fg=C["muted"],
                            font=self.app.F("small"), anchor="w", justify="left",
                            wraplength=PX(500))
            body.pack(anchor="w", pady=(PX(3), 0))
            self._bodies.append(body)
            if i < len(HELP[lang]) - 1:
                tk.Frame(self.body, bg=C["divider"], height=1).pack(
                    fill="x", padx=PX(20), pady=(PX(14), 0))
        tk.Frame(self.body, bg=C["card"], height=PX(18)).pack(fill="x")

        self.update_idletasks()
        self._rewrap(self.canvas.winfo_width())
        # Only after the new scrollregion is known, or the view keeps the old offset.
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(0)
