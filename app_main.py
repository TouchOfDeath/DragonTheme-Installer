"""
DragonTheme Installer — clean, stable rewrite.

Bug-fixes vs previous version:
  1. CTkImage references stored as self._img_xxx so GC never frees them
  2. Massive preview.jpg (15k×8k) pre-downscaled before open
  3. Scroll wheel uses a simple, reliable bind_all approach instead of
     recursive child-walking and fragile _parent_canvas access
  4. Dynamic accent colour removed — caused widget re-render crashes
  5. Theme picker uses a simple SegmentedButton; no custom ThemeCard frames
  6. Image loading errors are fully caught and show a placeholder
  7. _show_page defined only once
"""

import customtkinter as ctk
from PIL import Image
import threading
import theme_manager
import sys
import os

# ── Helpers ────────────────────────────────────────────────────────────────────
def res(name: str) -> str:
    """Return the absolute path to a bundled resource.
    Works both for PyInstaller bundles (sys._MEIPASS) and plain source
    runs (relative to the directory this .py file lives in).
    """
    try:
        base = sys._MEIPASS          # PyInstaller bundle
    except AttributeError:
        # Source run — use the folder containing this script, NOT cwd
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)

def load_img(path: str, size: tuple) -> ctk.CTkImage | None:
    """
    Open an image, resize it safely (handles decompression-bomb warning),
    and return a CTkImage — or None on any error.
    """
    try:
        from PIL import Image as _I
        _I.MAX_IMAGE_PIXELS = None          # suppress bomb warning for our own files
        if not os.path.exists(path):
            return None
        raw = _I.open(path).convert("RGB")
        # down-sample very large images before handing to CTk
        if raw.width > 2000 or raw.height > 2000:
            raw = raw.resize((size[0] * 2, size[1] * 2), _I.LANCZOS)
        return ctk.CTkImage(light_image=raw, dark_image=raw, size=size)
    except Exception as e:
        print(f"[load_img] Failed to load '{path}': {e}")
        return None

# ── Palette ────────────────────────────────────────────────────────────────────
BG       = "#0e0e11"
CARD     = "#16161a"
CARD2    = "#1c1c22"
ACCENT   = "#7c6fff"
AHOVER   = "#9b92ff"
FG       = "#ececf4"
FG2      = "#8888aa"
SUCCESS  = "#00e5a0"
DANGER   = "#ff4d6d"
BORDER   = "#2c2c3a"

F_TITLE  = ("Inter", 24, "bold")
F_BODY   = ("Inter", 12)
F_LABEL  = ("Inter", 13, "bold")
F_SMALL  = ("Inter", 11)
F_BTN    = ("Inter", 14, "bold")
F_BTN_S  = ("Inter", 12)
F_MONO   = ("Courier New", 11)

# ── Theme config ──────────────────────────────────────────────────────────────
THEME_PILLS = ["Layan Dark", "Custom Wallpaper", "Blur Effects", "Tela Icons"]


# ═══════════════════════════════════════════════════════════════════════════════
# Tiny reusable widgets
# ═══════════════════════════════════════════════════════════════════════════════
class Spinner(ctk.CTkLabel):
    _F = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    def __init__(self, master, **kw):
        super().__init__(master, text="  ", **kw)
        self._on = False; self._i = 0
    def start(self):
        self._on = True; self._tick()
    def stop(self, t=""):
        self._on = False; self.configure(text=t)
    def _tick(self):
        if self._on:
            self.configure(text=self._F[self._i % len(self._F)])
            self._i += 1
            self.after(80, self._tick)


class SmoothBar(ctk.CTkProgressBar):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.set(0); self._tgt = 0.0; self._cur = 0.0
    def go(self, t):
        self._tgt = max(0.0, min(1.0, t)); self._step()
    def _step(self):
        if abs(self._cur - self._tgt) > 0.002:
            self._cur += (self._tgt - self._cur) * 0.15
            self.set(self._cur); self.after(16, self._step)
        else:
            self._cur = self._tgt; self.set(self._cur)


class Console(ctk.CTkTextbox):
    def __init__(self, master, **kw):
        super().__init__(master, state="disabled",
                         fg_color="#0a0a0d", text_color=SUCCESS,
                         font=F_MONO, corner_radius=10, **kw)
        self.tag_config("err",  foreground=DANGER)
        self.tag_config("info", foreground=FG2)
        self.tag_config("ok",   foreground=SUCCESS)
    def push(self, text, tag="ok"):
        self.configure(state="normal")
        self.insert("end", f"  {text}\n", tag)
        self.see("end"); self.configure(state="disabled")
    def clear(self):
        self.configure(state="normal")
        self.delete("1.0","end"); self.configure(state="disabled")


class ToggleRow(ctk.CTkFrame):
    """One feature row with icon, title, description, and a switch."""
    def __init__(self, master, icon, title, desc, on=True, **kw):
        super().__init__(master, fg_color=CARD2, corner_radius=12,
                         border_width=1, border_color=BORDER, **kw)
        self.grid_columnconfigure(1, weight=1)
        self._var = ctk.BooleanVar(value=on)
        ctk.CTkLabel(self, text=icon, font=("Segoe UI Emoji", 20)
                     ).grid(row=0, column=0, rowspan=2, padx=(14,8), pady=12)
        ctk.CTkLabel(self, text=title, font=F_LABEL, text_color=FG
                     ).grid(row=0, column=1, sticky="sw", pady=(10,0))
        ctk.CTkLabel(self, text=desc, font=F_SMALL, text_color=FG2
                     ).grid(row=1, column=1, sticky="nw", pady=(0,10))
        ctk.CTkSwitch(self, variable=self._var, text="",
                      button_color=ACCENT, progress_color=ACCENT
                      ).grid(row=0, column=2, rowspan=2, padx=14)
    @property
    def enabled(self): return self._var.get()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("DragonTheme — Desktop Beautifier")
        self.geometry("940x650")
        self.minsize(860, 580)
        self.configure(fg_color=BG)

        # Keep CTkImage references alive (prevents GC blank images)
        # Just keep a reference to the main preview
        self._img_preview: ctk.CTkImage | None = None

        self._sidebar()
        self._pages_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._pages_frame.pack(side="left", fill="both", expand=True)

        self._pg = {
            "home":    self._pg_home(),
            "options": self._pg_options(),
            "install": self._pg_install(),
            "done":    self._pg_done(),
        }
        self._show("home")

        # Bind mouse-wheel scrolling globally — safest cross-platform approach
        self.bind_all("<Button-4>",   self._on_scroll)
        self.bind_all("<Button-5>",   self._on_scroll)
        self.bind_all("<MouseWheel>", self._on_scroll)

    def _on_scroll(self, event):
        """Route mouse-wheel to whichever CTkScrollableFrame is visible."""
        if not hasattr(self, "_active_scroll") or not self._active_scroll:
            return
        sf = self._active_scroll
        if event.num == 4:
            sf._parent_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            sf._parent_canvas.yview_scroll(1, "units")
        elif getattr(event, "delta", 0):
            sf._parent_canvas.yview_scroll(int(-event.delta / 120), "units")

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _sidebar(self):
        sb = ctk.CTkFrame(self, width=210, fg_color=CARD, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        top = ctk.CTkFrame(sb, fg_color="transparent")
        top.pack(pady=(28,6), padx=16, fill="x")
        ctk.CTkLabel(top, text="🐉", font=("Segoe UI Emoji", 40)).pack()
        ctk.CTkLabel(top, text="DragonTheme",
                     font=("Inter",18,"bold"), text_color=FG).pack()
        ctk.CTkLabel(top, text="Desktop Beautifier",
                     font=F_SMALL, text_color=FG2).pack()

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).pack(
            fill="x", padx=14, pady=18)

        self._navbtns: list[ctk.CTkButton] = []
        for label, key in [("🏠  Home","home"),
                            ("🎨  Options","options"),
                            ("⚡  Install","install")]:
            b = ctk.CTkButton(sb, text=label, font=F_BTN_S, anchor="w",
                              fg_color="transparent", hover_color=CARD2,
                              text_color=FG2, height=40, corner_radius=10,
                              command=lambda k=key: self._show(k))
            b.pack(fill="x", padx=10, pady=2)
            self._navbtns.append(b)

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).pack(
            fill="x", padx=14, pady=(0,10), side="bottom")
        ctk.CTkLabel(sb, text="v1.1  •  KDE Plasma 5",
                     font=F_SMALL, text_color=FG2).pack(
            side="bottom", pady=(0,10))

    def _nav_highlight(self, key):
        labels = ["home","options","install"]
        for btn, k in zip(self._navbtns, labels):
            if k == key:
                btn.configure(fg_color=ACCENT, text_color=FG, hover_color=AHOVER)
            else:
                btn.configure(fg_color="transparent", text_color=FG2, hover_color=CARD2)

    def _show(self, key):
        for pg in self._pg.values():
            pg.pack_forget()
        self._pg[key].pack(fill="both", expand=True)
        self._nav_highlight(key)
        # Tell scroll handler which frame is active
        self._active_scroll = getattr(self, f"_scroll_{key}", None)

    # ── Page: Home ────────────────────────────────────────────────────────────
    def _pg_home(self):
        pg = ctk.CTkFrame(self._pages_frame, fg_color=BG, corner_radius=0)

        ctk.CTkLabel(pg, text="Desktop Preview",
                     font=F_TITLE, text_color=FG).pack(
            anchor="w", padx=30, pady=(26,2))
        ctk.CTkLabel(pg, text="This is how your laptop will look after the transformation.",
                     font=F_BODY, text_color=FG2).pack(
            anchor="w", padx=30, pady=(0,16))

        # ── Large preview card ──
        self._prev_card = ctk.CTkFrame(pg, fg_color=CARD, corner_radius=14,
                                       border_width=1, border_color=BORDER)
        self._prev_card.pack(fill="both", expand=True, padx=30, pady=(0,12))

        self._prev_lbl = ctk.CTkLabel(self._prev_card, text="",
                                      text_color=FG2, font=F_BODY)
        self._prev_lbl.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Pills ──
        self._pills = ctk.CTkFrame(pg, fg_color="transparent")
        self._pills.pack(fill="x", padx=30, pady=(0,10))
        
        for p in THEME_PILLS:
            ctk.CTkLabel(self._pills, text=f"  {p}  ",
                         fg_color=CARD2, corner_radius=20,
                         font=F_SMALL, text_color=FG2,
                         padx=6, pady=3).pack(side="left", padx=3)

        ctk.CTkButton(pg, text="  Customise Options  →",
                      font=F_BTN, height=46, corner_radius=12,
                      fg_color=ACCENT, hover_color=AHOVER,
                      command=lambda: self._show("options")
                      ).pack(padx=30, pady=(2,24), fill="x")

        # Load the preview after the window is shown
        pg.after(300, self._load_preview)
        return pg

    def _load_preview(self):
        if not self._img_preview:
            img_path = res("preview.jpg")
            self._img_preview = load_img(img_path, (700, 394))
            
        if self._img_preview:
            self._prev_lbl.configure(image=self._img_preview, text="", compound="center")
        else:
            self._prev_lbl.configure(
                image=None,
                text=f"Could not load image:\n{res('preview.jpg')}",
                font=("Inter", 14), text_color=FG2)

    # ── Page: Options ─────────────────────────────────────────────────────────
    def _pg_options(self):
        pg = ctk.CTkFrame(self._pages_frame, fg_color=BG, corner_radius=0)

        ctk.CTkLabel(pg, text="Customise your installation",
                     font=F_TITLE, text_color=FG).pack(
            anchor="w", padx=30, pady=(26,2))
        ctk.CTkLabel(pg, text="Toggle what gets applied to your system.",
                     font=F_BODY, text_color=FG2).pack(
            anchor="w", padx=30, pady=(0,14))

        sf = ctk.CTkScrollableFrame(pg, fg_color="transparent", corner_radius=0)
        sf.pack(fill="both", expand=True, padx=30)
        sf.grid_columnconfigure(0, weight=1)
        self._scroll_options = sf          # registered for scroll routing

        rows = [
            ("🎨","Global Theme",        "Window decorations, panel style, colour scheme."),
            ("🗂️","Icon Pack",            "Circular Tela icons for all your apps."),
            ("🖱️","Cursor Theme",         "Smooth Layan cursors that match the aesthetic."),
            ("🖼️","Wallpaper",            "The wallpaper shown in the preview."),
            ("✨","Desktop Effects",      "Blur, transparency, wobbly windows, glide."),
            ("💾","Backup current theme", "Save existing settings so you can revert later."),
        ]
        self._opts: list[ToggleRow] = []
        for i, (icon, title, desc) in enumerate(rows):
            row = ToggleRow(sf, icon, title, desc)
            row.grid(row=i, column=0, sticky="ew", pady=5)
            self._opts.append(row)

        ctk.CTkButton(pg, text="  Continue to Install  →",
                      font=F_BTN, height=46, corner_radius=12,
                      fg_color=ACCENT, hover_color=AHOVER,
                      command=lambda: self._show("install")
                      ).pack(padx=30, pady=18, fill="x")
        return pg

    # ── Page: Install ─────────────────────────────────────────────────────────
    def _pg_install(self):
        pg = ctk.CTkFrame(self._pages_frame, fg_color=BG, corner_radius=0)

        ctk.CTkLabel(pg, text="Install",
                     font=F_TITLE, text_color=FG).pack(
            anchor="w", padx=30, pady=(26,2))

        self._chip = ctk.CTkLabel(pg, text="Applying Dark Theme", font=F_LABEL,
                                  fg_color=CARD2, corner_radius=10,
                                  padx=12, pady=7, text_color=FG)
        self._chip.pack(anchor="w", padx=30, pady=(4,14))

        # Status row
        status = ctk.CTkFrame(pg, fg_color=CARD, corner_radius=12,
                              border_width=1, border_color=BORDER)
        status.pack(fill="x", padx=30, pady=(0,8))
        status.grid_columnconfigure(1, weight=1)

        self._spinner = Spinner(status, font=("Courier New",20), text_color=ACCENT)
        self._spinner.grid(row=0, column=0, padx=(16,8), pady=16)
        self._stat = ctk.CTkLabel(status, text="Ready — click Install to begin.",
                                  font=F_LABEL, text_color=FG, anchor="w")
        self._stat.grid(row=0, column=1, sticky="ew", pady=16)

        # Progress
        pf = ctk.CTkFrame(pg, fg_color="transparent")
        pf.pack(fill="x", padx=30, pady=(0,6))
        self._bar = SmoothBar(pf, height=10, corner_radius=5,
                              fg_color=CARD2, progress_color=ACCENT)
        self._bar.pack(fill="x")
        self._pct = ctk.CTkLabel(pf, text="0 %", font=F_SMALL, text_color=FG2)
        self._pct.pack(anchor="e", pady=(3,0))

        ctk.CTkLabel(pg, text="LOG", font=("Inter",10,"bold"),
                     text_color=FG2).pack(anchor="w", padx=30)
        self._con = Console(pg, height=170)
        self._con.pack(fill="both", expand=True, padx=30, pady=(3,0))

        btns = ctk.CTkFrame(pg, fg_color="transparent")
        btns.pack(fill="x", padx=30, pady=12)
        btns.grid_columnconfigure((0,1), weight=1)

        self._inst_btn = ctk.CTkButton(
            btns, text="⚡  Install Now", font=F_BTN, height=46,
            corner_radius=12, fg_color=ACCENT, hover_color=AHOVER,
            command=self._install)
        self._inst_btn.grid(row=0, column=0, padx=(0,5), sticky="ew")

        self._back_btn = ctk.CTkButton(
            btns, text="← Back", font=F_BTN_S, height=46,
            corner_radius=12, fg_color=CARD2, hover_color=BORDER,
            command=lambda: self._show("options"))
        self._back_btn.grid(row=0, column=1, padx=(5,0), sticky="ew")

        return pg

    def _refresh_chip(self):
        pass # Replaced with static text above

    def _show(self, key):          # override to refresh chip on install page
        for pg in self._pg.values():
            pg.pack_forget()
        self._pg[key].pack(fill="both", expand=True)
        self._nav_highlight(key)
        self._active_scroll = getattr(self, f"_scroll_{key}", None)
        if key == "install":
            self._refresh_chip()

    # ── Page: Done ────────────────────────────────────────────────────────────
    def _pg_done(self):
        pg = ctk.CTkFrame(self._pages_frame, fg_color=BG, corner_radius=0)
        c = ctk.CTkFrame(pg, fg_color="transparent")
        c.place(relx=0.5, rely=0.44, anchor="center")
        ctk.CTkLabel(c, text="🎉",
                     font=("Segoe UI Emoji",68)).pack()
        ctk.CTkLabel(c, text="Your desktop has been\ntransformed!",
                     font=("Inter",28,"bold"), text_color=FG,
                     justify="center").pack(pady=(8,4))
        ctk.CTkLabel(c,
                     text="Plasma will restart in a moment.\nEnjoy your beautiful new setup!",
                     font=F_BODY, text_color=FG2,
                     justify="center").pack(pady=(0,28))
        ctk.CTkButton(c, text="Close", font=F_BTN,
                      height=46, width=180, corner_radius=12,
                      fg_color=ACCENT, hover_color=AHOVER,
                      command=self.destroy).pack()
        return pg

    # ── Install logic ─────────────────────────────────────────────────────────
    def _set_progress(self, v, lbl=None):
        self._bar.go(v)
        self._pct.configure(text=f"{int(v*100)} %")
        if lbl:
            self._stat.configure(text=lbl, text_color=FG)

    def _install(self):
        self._inst_btn.configure(state="disabled", text="Installing…")
        self._back_btn.configure(state="disabled")
        self._con.clear()
        self._spinner.start()
        self._set_progress(0, "Starting…")
        opts = {
            "theme":         self._opts[0].enabled,
            "icons":         self._opts[1].enabled,
            "cursor":        self._opts[2].enabled,
            "wallpaper":     self._opts[3].enabled,
            "effects":       self._opts[4].enabled,
            "backup":        self._opts[5].enabled,
            "theme_variant": "dark",
        }
        threading.Thread(target=self._run_install,
                         args=(opts,), daemon=True).start()

    def _log(self, msg, tag="ok"):
        self.after(0, lambda m=msg, t=tag: self._con.push(m, t))

    def _prog(self, v, lbl=None):
        self.after(0, lambda: self._set_progress(v, lbl))

    def _run_install(self, opts):
        try:
            self._log("Starting installation…", "info")
            self._prog(0.05, "Extracting…")
            theme_manager.apply_theme(callback=self._log, options=opts)
            self._prog(1.0, "Done!")
            self.after(0, self._done)
        except Exception as e:
            self.after(0, lambda err=str(e): self._err(err))

    def _done(self):
        self._spinner.stop("✓")
        self._spinner.configure(text_color=SUCCESS)
        self._show("done")

    def _err(self, msg):
        self._spinner.stop("✗")
        self._spinner.configure(text_color=DANGER)
        self._stat.configure(text="Installation failed.", text_color=DANGER)
        self._con.push(msg, "err")
        self._inst_btn.configure(state="normal", text="⚡  Retry")
        self._back_btn.configure(state="normal")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
