"""
FocusFlow — A Material-inspired multi-timer desktop app
Built with Tkinter only. No external dependencies.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import json
import os
import random
import math

# ─────────────────────────────────────────────
#  CONSTANTS & THEMES
# ─────────────────────────────────────────────

SAVE_FILE = os.path.join(os.path.expanduser("~"), ".focusflow_data.json")

THEMES = {
    "light": {
        "bg":           "#F8F9FA",
        "surface":      "#FFFFFF",
        "surface2":     "#F1F3F4",
        "accent":       "#1A73E8",
        "accent2":      "#34A853",
        "warn":         "#EA4335",
        "text":         "#202124",
        "text2":        "#5F6368",
        "border":       "#DADCE0",
        "timer_bg":     "#EAF1FB",
        "timer_done":   "#FCE8E6",
        "btn_fg":       "#FFFFFF",
        "btn_flat":     "#F1F3F4",
        "btn_flat_fg":  "#1A73E8",
        "tab_sel":      "#1A73E8",
        "tab_sel_fg":   "#FFFFFF",
        "tab_unsel":    "#F1F3F4",
        "tab_unsel_fg": "#5F6368",
    },
    "dark": {
        "bg":           "#121212",
        "surface":      "#1E1E1E",
        "surface2":     "#2D2D2D",
        "accent":       "#8AB4F8",
        "accent2":      "#81C995",
        "warn":         "#F28B82",
        "text":         "#E8EAED",
        "text2":        "#9AA0A6",
        "border":       "#3C4043",
        "timer_bg":     "#1A2540",
        "timer_done":   "#3C1E1C",
        "btn_fg":       "#202124",
        "btn_flat":     "#2D2D2D",
        "btn_flat_fg":  "#8AB4F8",
        "tab_sel":      "#8AB4F8",
        "tab_sel_fg":   "#202124",
        "tab_unsel":    "#2D2D2D",
        "tab_unsel_fg": "#9AA0A6",
    }
}

QUOTES = [
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("Don't watch the clock; do what it does. Keep going.", "Sam Levenson"),
    ("You don't have to be great to start, but you have to start to be great.", "Zig Ziglar"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Hard work beats talent when talent doesn't work hard.", "Tim Notke"),
    ("Focus on being productive instead of busy.", "Tim Ferriss"),
    ("Energy and persistence conquer all things.", "Benjamin Franklin"),
    ("Small steps every day lead to big results over time.", "Anonymous"),
    ("Success is the sum of small efforts repeated day in and day out.", "Robert Collier"),
    ("Push yourself, because no one else is going to do it for you.", "Anonymous"),
]

FONT_FAMILY = "Segoe UI" if os.name == "nt" else "SF Pro Display" if os.name == "posix" and "darwin" in os.sys.platform else "Ubuntu"

# ─────────────────────────────────────────────
#  STORAGE
# ─────────────────────────────────────────────

class Storage:
    @staticmethod
    def load():
        if not os.path.exists(SAVE_FILE):
            return {"timers": [], "task": "", "theme": "light"}
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                if "timers" not in data:
                    data["timers"] = []
                if "task" not in data:
                    data["task"] = ""
                if "theme" not in data:
                    data["theme"] = "light"
                return data
        except Exception:
            return {"timers": [], "task": "", "theme": "light"}

    @staticmethod
    def save(data: dict):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


# ─────────────────────────────────────────────
#  TIMER MODEL
# ─────────────────────────────────────────────

class TimerModel:
    def __init__(self, name: str, total_seconds: int,
                 elapsed: float = 0.0, running: bool = False,
                 started_at: float = None):
        self.name = name
        self.total_seconds = total_seconds
        self.elapsed = elapsed          # seconds already counted before last start
        self.running = running
        self.started_at = started_at    # wall-clock when last started

    def remaining(self) -> float:
        if self.running and self.started_at:
            elapsed_now = self.elapsed + (time.time() - self.started_at)
        else:
            elapsed_now = self.elapsed
        return max(0.0, self.total_seconds - elapsed_now)

    def start(self):
        if not self.running and self.remaining() > 0:
            self.started_at = time.time()
            self.running = True

    def pause(self):
        if self.running:
            self.elapsed += time.time() - self.started_at
            self.started_at = None
            self.running = False

    def reset(self):
        self.elapsed = 0.0
        self.running = False
        self.started_at = None

    def is_done(self) -> bool:
        return self.remaining() <= 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_seconds": self.total_seconds,
            "elapsed": self.elapsed + (
                (time.time() - self.started_at) if self.running and self.started_at else 0
            ),
            "running": self.running,
            "started_at": self.started_at if self.running else None,
        }

    @staticmethod
    def from_dict(d: dict) -> "TimerModel":
        return TimerModel(
            name=d.get("name", "Timer"),
            total_seconds=d.get("total_seconds", 60),
            elapsed=d.get("elapsed", 0.0),
            running=d.get("running", False),
            started_at=d.get("started_at"),
        )

    @staticmethod
    def fmt(seconds: float) -> str:
        s = int(seconds)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{sec:02d}"


# ─────────────────────────────────────────────
#  SINGLE TIMER CARD WIDGET
# ─────────────────────────────────────────────

class TimerCard(tk.Frame):
    def __init__(self, parent, model: TimerModel, theme: dict,
                 on_delete, on_save, **kwargs):
        super().__init__(parent, **kwargs)
        self.model = model
        self.theme = theme
        self.on_delete = on_delete
        self.on_save = on_save
        self._after_id = None
        self._build()
        self._apply_theme()
        self._schedule()

    def _build(self):
        self.configure(padx=10, pady=8)

        top = tk.Frame(self)
        top.pack(fill="x")

        self.lbl_name = tk.Label(top, text=self.model.name,
                                 font=(FONT_FAMILY, 11, "bold"))
        self.lbl_name.pack(side="left")

        self.btn_del = tk.Button(top, text="✕", width=2,
                                 font=(FONT_FAMILY, 9),
                                 relief="flat", bd=0, cursor="hand2",
                                 command=self._delete)
        self.btn_del.pack(side="right")

        self.lbl_time = tk.Label(self, text="00:00:00",
                                 font=(FONT_FAMILY, 24, "bold"))
        self.lbl_time.pack(pady=(4, 6))

        # Progress bar
        self.canvas_bar = tk.Canvas(self, height=4, bd=0,
                                    highlightthickness=0)
        self.canvas_bar.pack(fill="x", padx=4, pady=(0, 6))

        btns = tk.Frame(self)
        btns.pack(fill="x")

        self.btn_start = tk.Button(btns, text="▶  Start", width=8,
                                   font=(FONT_FAMILY, 9, "bold"),
                                   relief="flat", bd=0, cursor="hand2",
                                   command=self._toggle)
        self.btn_start.pack(side="left", padx=(0, 4))

        self.btn_reset = tk.Button(btns, text="↺  Reset",
                                   font=(FONT_FAMILY, 9),
                                   relief="flat", bd=0, cursor="hand2",
                                   command=self._reset)
        self.btn_reset.pack(side="left")

    def _apply_theme(self):
        t = self.theme
        done = self.model.is_done() and self.model.elapsed > 0
        bg = t["timer_done"] if done else t["timer_bg"]
        self.configure(bg=bg)
        for w in (self.lbl_name, self.lbl_time):
            w.configure(bg=bg, fg=t["text"])
        self.canvas_bar.configure(bg=t["border"])

        # start/pause button
        if self.model.running:
            self.btn_start.configure(
                text="⏸  Pause",
                bg=t["warn"], fg=t["btn_fg"],
                activebackground=t["warn"])
        else:
            self.btn_start.configure(
                text="▶  Start",
                bg=t["accent"], fg=t["btn_fg"],
                activebackground=t["accent"])

        self.btn_reset.configure(
            bg=t["btn_flat"], fg=t["btn_flat_fg"],
            activebackground=t["btn_flat"])
        self.btn_del.configure(
            bg=bg, fg=t["text2"],
            activebackground=bg)

        for f in self.winfo_children():
            if isinstance(f, tk.Frame):
                f.configure(bg=bg)
                for w in f.winfo_children():
                    if isinstance(w, (tk.Button, tk.Label)):
                        pass  # already configured above

    def _draw_bar(self):
        w = self.canvas_bar.winfo_width()
        if w < 2:
            return
        rem = self.model.remaining()
        ratio = rem / self.model.total_seconds if self.model.total_seconds > 0 else 0
        self.canvas_bar.delete("all")
        t = self.theme
        done = self.model.is_done() and self.model.elapsed > 0
        fill = t["warn"] if done else t["accent"]
        if ratio > 0:
            self.canvas_bar.create_rectangle(0, 0, int(w * ratio), 4,
                                             fill=fill, outline="")

    def _toggle(self):
        if self.model.running:
            self.model.pause()
        else:
            if self.model.is_done():
                return
            self.model.start()
        self._apply_theme()
        self.on_save()

    def _reset(self):
        self.model.reset()
        self._apply_theme()
        self.lbl_time.configure(text=TimerModel.fmt(self.model.total_seconds))
        self.on_save()

    def _delete(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self.on_delete(self)

    def _schedule(self):
        self._tick()

    def _tick(self):
        rem = self.model.remaining()
        self.lbl_time.configure(text=TimerModel.fmt(rem))
        self._draw_bar()

        if self.model.running and rem <= 0:
            self.model.pause()
            self.model.elapsed = self.model.total_seconds  # clamp
            self._apply_theme()
            self.on_save()

        self._after_id = self.after(200, self._tick)

    def update_theme(self, theme: dict):
        self.theme = theme
        self._apply_theme()


# ─────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────

class FocusFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FocusFlow")
        self.resizable(False, False)
        self.geometry("420x580")
        self.minsize(400, 520)

        self._data = Storage.load()
        self._theme_name = self._data.get("theme", "light")
        self._theme = THEMES[self._theme_name]
        self._timer_models: list[TimerModel] = [
            TimerModel.from_dict(d) for d in self._data.get("timers", [])
        ]
        self._timer_cards: list[TimerCard] = []

        # Stopwatch state
        self._sw_running = False
        self._sw_elapsed = 0.0
        self._sw_started_at = None
        self._sw_after = None

        self._build_ui()
        self._apply_theme_all()
        self._load_timers()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── BUILD ──────────────────────────────────

    def _build_ui(self):
        # Header bar
        self.header = tk.Frame(self, height=52)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.lbl_app = tk.Label(self.header, text="FocusFlow",
                                font=(FONT_FAMILY, 16, "bold"))
        self.lbl_app.pack(side="left", padx=16)

        self.btn_theme = tk.Button(
            self.header, text="☀  Light", font=(FONT_FAMILY, 9),
            relief="flat", bd=0, cursor="hand2",
            command=self._toggle_theme, padx=10, pady=4)
        self.btn_theme.pack(side="right", padx=10)

        # Tab bar
        self.tab_bar = tk.Frame(self, height=40)
        self.tab_bar.pack(fill="x")
        self.tab_bar.pack_propagate(False)

        self._tabs = {}
        self._active_tab = tk.StringVar(value="timers")
        for key, label in [("timers", "Timers"), ("stopwatch", "Stopwatch"),
                            ("focus", "Focus"), ("quotes", "Quotes")]:
            btn = tk.Button(
                self.tab_bar, text=label, font=(FONT_FAMILY, 9, "bold"),
                relief="flat", bd=0, cursor="hand2",
                command=lambda k=key: self._switch_tab(k))
            btn.pack(side="left", fill="y", padx=2, pady=4)
            self._tabs[key] = btn

        # Content area
        self.content = tk.Frame(self)
        self.content.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self._pages = {}
        for key in ("timers", "stopwatch", "focus", "quotes"):
            page = tk.Frame(self.content)
            self._pages[key] = page

        self._build_timers_page(self._pages["timers"])
        self._build_stopwatch_page(self._pages["stopwatch"])
        self._build_focus_page(self._pages["focus"])
        self._build_quotes_page(self._pages["quotes"])

        self._switch_tab("timers")

    def _build_timers_page(self, parent):
        # Add timer form
        form = tk.Frame(parent)
        form.pack(fill="x", pady=(4, 8))

        self.entry_name = tk.Entry(form, font=(FONT_FAMILY, 10), width=12,
                                   relief="flat", bd=0)
        self.entry_name.insert(0, "Timer name")
        self.entry_name.bind("<FocusIn>", lambda e: self._clear_placeholder(
            self.entry_name, "Timer name"))
        self.entry_name.bind("<FocusOut>", lambda e: self._restore_placeholder(
            self.entry_name, "Timer name"))
        self.entry_name.pack(side="left", padx=(0, 4), ipady=4, ipadx=4)

        for attr, ph, w in [("entry_h", "HH", 3), ("entry_m", "MM", 3),
                             ("entry_s", "SS", 3)]:
            e = tk.Entry(form, font=(FONT_FAMILY, 10), width=w,
                         justify="center", relief="flat", bd=0)
            e.insert(0, ph)
            e.bind("<FocusIn>", lambda ev, en=e, p=ph: self._clear_placeholder(en, p))
            e.bind("<FocusOut>", lambda ev, en=e, p=ph: self._restore_placeholder(en, p))
            e.pack(side="left", padx=2, ipady=4)
            setattr(self, attr, e)

        self.btn_add = tk.Button(form, text="＋ Add",
                                 font=(FONT_FAMILY, 9, "bold"),
                                 relief="flat", bd=0, cursor="hand2",
                                 padx=10, pady=4,
                                 command=self._add_timer)
        self.btn_add.pack(side="left", padx=(6, 0))

        # Scrollable timers list
        outer = tk.Frame(parent)
        outer.pack(fill="both", expand=True)

        self.canvas_timers = tk.Canvas(outer, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical",
                                 command=self.canvas_timers.yview)
        self.canvas_timers.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas_timers.pack(side="left", fill="both", expand=True)

        self.timers_inner = tk.Frame(self.canvas_timers)
        self._canvas_win = self.canvas_timers.create_window(
            (0, 0), window=self.timers_inner, anchor="nw")

        self.timers_inner.bind("<Configure>", self._on_timers_configure)
        self.canvas_timers.bind("<Configure>", self._on_canvas_resize)
        self.canvas_timers.bind("<MouseWheel>", self._on_mousewheel)
        self.timers_inner.bind("<MouseWheel>", self._on_mousewheel)

    def _build_stopwatch_page(self, parent):
        spacer = tk.Frame(parent, height=30)
        spacer.pack()

        self.lbl_sw = tk.Label(parent, text="00:00:00",
                               font=(FONT_FAMILY, 48, "bold"))
        self.lbl_sw.pack(pady=(0, 8))

        self.lbl_sw_sub = tk.Label(parent, text="STOPWATCH",
                                   font=(FONT_FAMILY, 9))
        self.lbl_sw_sub.pack()

        btns = tk.Frame(parent)
        btns.pack(pady=24)

        self.btn_sw_toggle = tk.Button(
            btns, text="▶  Start", font=(FONT_FAMILY, 11, "bold"),
            relief="flat", bd=0, cursor="hand2", padx=20, pady=10,
            command=self._sw_toggle)
        self.btn_sw_toggle.pack(side="left", padx=6)

        self.btn_sw_reset = tk.Button(
            btns, text="↺  Reset", font=(FONT_FAMILY, 11),
            relief="flat", bd=0, cursor="hand2", padx=16, pady=10,
            command=self._sw_reset)
        self.btn_sw_reset.pack(side="left", padx=6)

    def _build_focus_page(self, parent):
        spacer = tk.Frame(parent, height=20)
        spacer.pack()

        tk.Label(parent, text="Current Task",
                 font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", padx=4)

        self.entry_task = tk.Entry(parent, font=(FONT_FAMILY, 13),
                                   relief="flat", bd=0)
        self.entry_task.pack(fill="x", padx=4, pady=(6, 4), ipady=8, ipadx=8)

        self.btn_save_task = tk.Button(
            parent, text="Save Task", font=(FONT_FAMILY, 9, "bold"),
            relief="flat", bd=0, cursor="hand2", padx=14, pady=6,
            command=self._save_task)
        self.btn_save_task.pack(anchor="e", padx=4)

        self.lbl_task_display = tk.Label(
            parent, text="", font=(FONT_FAMILY, 15, "bold"),
            wraplength=360, justify="center")
        self.lbl_task_display.pack(pady=20, padx=8)

        self.lbl_task_sub = tk.Label(
            parent, text="Stay focused. One task at a time.",
            font=(FONT_FAMILY, 9))
        self.lbl_task_sub.pack()

        # Pre-fill saved task
        saved = self._data.get("task", "")
        if saved:
            self.entry_task.insert(0, saved)
            self.lbl_task_display.configure(text=f"📌 {saved}")

    def _build_quotes_page(self, parent):
        spacer = tk.Frame(parent, height=20)
        spacer.pack()

        self.lbl_quote_icon = tk.Label(parent, text="❝",
                                       font=(FONT_FAMILY, 36))
        self.lbl_quote_icon.pack()

        self.lbl_quote_text = tk.Label(
            parent, text="Press the button to get inspired.",
            font=(FONT_FAMILY, 12), wraplength=360, justify="center")
        self.lbl_quote_text.pack(padx=16, pady=12)

        self.lbl_quote_author = tk.Label(parent, text="",
                                         font=(FONT_FAMILY, 9, "italic"))
        self.lbl_quote_author.pack()

        self.btn_quote = tk.Button(
            parent, text="✨ New Quote", font=(FONT_FAMILY, 10, "bold"),
            relief="flat", bd=0, cursor="hand2", padx=18, pady=9,
            command=self._new_quote)
        self.btn_quote.pack(pady=24)

    # ── TAB SWITCHING ──────────────────────────

    def _switch_tab(self, key: str):
        for k, page in self._pages.items():
            page.pack_forget()
        self._pages[key].pack(fill="both", expand=True)
        self._active_tab.set(key)
        self._refresh_tabs()

    def _refresh_tabs(self):
        t = self._theme
        active = self._active_tab.get()
        for key, btn in self._tabs.items():
            if key == active:
                btn.configure(bg=t["tab_sel"], fg=t["tab_sel_fg"],
                              activebackground=t["tab_sel"])
            else:
                btn.configure(bg=t["tab_unsel"], fg=t["tab_unsel_fg"],
                              activebackground=t["tab_unsel"])

    # ── THEME ──────────────────────────────────

    def _toggle_theme(self):
        self._theme_name = "dark" if self._theme_name == "light" else "light"
        self._theme = THEMES[self._theme_name]
        self._apply_theme_all()
        self._save()

    def _apply_theme_all(self):
        t = self._theme
        self.configure(bg=t["bg"])
        self.header.configure(bg=t["surface"])
        self.lbl_app.configure(bg=t["surface"], fg=t["accent"])
        self.btn_theme.configure(
            bg=t["btn_flat"], fg=t["btn_flat_fg"],
            activebackground=t["btn_flat"],
            text="🌙 Dark" if self._theme_name == "light" else "☀ Light")

        self.tab_bar.configure(bg=t["surface2"])
        self.content.configure(bg=t["bg"])

        for key, page in self._pages.items():
            page.configure(bg=t["bg"])

        # Timers page
        tp = self._pages["timers"]
        for w in tp.winfo_children():
            if isinstance(w, tk.Frame):
                w.configure(bg=t["bg"])
                for c in w.winfo_children():
                    if isinstance(c, tk.Entry):
                        c.configure(bg=t["surface"], fg=t["text"],
                                    insertbackground=t["text"],
                                    disabledbackground=t["surface2"])
                    elif isinstance(c, tk.Button):
                        c.configure(bg=t["accent"], fg=t["btn_fg"],
                                    activebackground=t["accent"])

        self.entry_name.configure(bg=t["surface"], fg=t["text2"],
                                  insertbackground=t["text"])
        self.entry_h.configure(bg=t["surface"], fg=t["text2"],
                               insertbackground=t["text"])
        self.entry_m.configure(bg=t["surface"], fg=t["text2"],
                               insertbackground=t["text"])
        self.entry_s.configure(bg=t["surface"], fg=t["text2"],
                               insertbackground=t["text"])
        self.btn_add.configure(bg=t["accent"], fg=t["btn_fg"],
                               activebackground=t["accent"])

        self.canvas_timers.configure(bg=t["bg"])
        self.timers_inner.configure(bg=t["bg"])

        # Stopwatch page
        sp = self._pages["stopwatch"]
        sp.configure(bg=t["bg"])
        for w in sp.winfo_children():
            if isinstance(w, (tk.Frame,)):
                w.configure(bg=t["bg"])
                for c in w.winfo_children():
                    if isinstance(c, tk.Button):
                        pass
            elif isinstance(w, tk.Label):
                w.configure(bg=t["bg"], fg=t["text"] if w != self.lbl_sw_sub else t["text2"])
        self.lbl_sw.configure(bg=t["bg"], fg=t["accent"])
        self.lbl_sw_sub.configure(bg=t["bg"], fg=t["text2"])
        self.btn_sw_toggle.configure(bg=t["accent"], fg=t["btn_fg"],
                                     activebackground=t["accent"])
        self.btn_sw_reset.configure(bg=t["btn_flat"], fg=t["btn_flat_fg"],
                                    activebackground=t["btn_flat"])

        # Focus page
        fp = self._pages["focus"]
        fp.configure(bg=t["bg"])
        for w in fp.winfo_children():
            if isinstance(w, tk.Label):
                w.configure(bg=t["bg"],
                            fg=t["text"] if w != self.lbl_task_sub else t["text2"])
            elif isinstance(w, tk.Frame):
                w.configure(bg=t["bg"])
        self.entry_task.configure(bg=t["surface"], fg=t["text"],
                                  insertbackground=t["text"])
        self.btn_save_task.configure(bg=t["accent2"], fg=t["btn_fg"],
                                     activebackground=t["accent2"])
        self.lbl_task_display.configure(bg=t["bg"], fg=t["accent"])
        self.lbl_task_sub.configure(bg=t["bg"], fg=t["text2"])

        # Quotes page
        qp = self._pages["quotes"]
        qp.configure(bg=t["bg"])
        for w in qp.winfo_children():
            if isinstance(w, tk.Label):
                w.configure(bg=t["bg"], fg=t["text"])
        self.lbl_quote_icon.configure(bg=t["bg"], fg=t["accent"])
        self.lbl_quote_text.configure(bg=t["bg"], fg=t["text"])
        self.lbl_quote_author.configure(bg=t["bg"], fg=t["text2"])
        self.btn_quote.configure(bg=t["accent"], fg=t["btn_fg"],
                                 activebackground=t["accent"])

        # Timer cards
        for card in self._timer_cards:
            card.update_theme(t)

        self._refresh_tabs()

    # ── TIMER LOGIC ────────────────────────────

    def _load_timers(self):
        for model in self._timer_models:
            self._create_card(model)

    def _add_timer(self):
        name = self.entry_name.get().strip()
        if not name or name == "Timer name":
            name = "Timer"

        def _parse(entry, placeholder, label):
            v = entry.get().strip()
            if v == placeholder or not v:
                return 0
            try:
                n = int(v)
                if n < 0:
                    raise ValueError
                return n
            except ValueError:
                messagebox.showerror("Invalid input",
                                     f"{label} must be a non-negative integer.")
                return None

        h = _parse(self.entry_h, "HH", "Hours")
        if h is None:
            return
        m = _parse(self.entry_m, "MM", "Minutes")
        if m is None:
            return
        s = _parse(self.entry_s, "SS", "Seconds")
        if s is None:
            return

        total = h * 3600 + m * 60 + s
        if total <= 0:
            messagebox.showerror("Invalid time", "Please enter a time greater than 0.")
            return

        model = TimerModel(name=name, total_seconds=total)
        self._timer_models.append(model)
        self._create_card(model)
        self._save()

        # Reset fields
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, "Timer name")
        self.entry_name.configure(fg=self._theme["text2"])
        for entry, ph in [(self.entry_h, "HH"), (self.entry_m, "MM"),
                          (self.entry_s, "SS")]:
            entry.delete(0, "end")
            entry.insert(0, ph)
            entry.configure(fg=self._theme["text2"])

    def _create_card(self, model: TimerModel):
        card = TimerCard(
            self.timers_inner, model=model, theme=self._theme,
            on_delete=self._remove_card,
            on_save=self._save,
            bg=self._theme["timer_bg"],
            relief="flat",
        )
        card.pack(fill="x", padx=4, pady=4)
        self._timer_cards.append(card)
        self._update_canvas_scroll()
        card.bind("<MouseWheel>", self._on_mousewheel)

    def _remove_card(self, card: TimerCard):
        model = card.model
        if model in self._timer_models:
            self._timer_models.remove(model)
        if card in self._timer_cards:
            self._timer_cards.remove(card)
        card.destroy()
        self._update_canvas_scroll()
        self._save()

    def _on_timers_configure(self, event):
        self._update_canvas_scroll()

    def _on_canvas_resize(self, event):
        self.canvas_timers.itemconfig(self._canvas_win, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas_timers.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _update_canvas_scroll(self):
        self.timers_inner.update_idletasks()
        self.canvas_timers.configure(
            scrollregion=self.canvas_timers.bbox("all"))

    # ── STOPWATCH ──────────────────────────────

    def _sw_toggle(self):
        if self._sw_running:
            self._sw_elapsed += time.time() - self._sw_started_at
            self._sw_started_at = None
            self._sw_running = False
            self.btn_sw_toggle.configure(text="▶  Start")
        else:
            self._sw_started_at = time.time()
            self._sw_running = True
            self.btn_sw_toggle.configure(text="⏸  Pause")
            self._sw_tick()

    def _sw_reset(self):
        if self._sw_after:
            self.after_cancel(self._sw_after)
        self._sw_running = False
        self._sw_elapsed = 0.0
        self._sw_started_at = None
        self.lbl_sw.configure(text="00:00:00")
        self.btn_sw_toggle.configure(text="▶  Start")

    def _sw_tick(self):
        if not self._sw_running:
            return
        elapsed = self._sw_elapsed + (time.time() - self._sw_started_at)
        self.lbl_sw.configure(text=TimerModel.fmt(elapsed))
        self._sw_after = self.after(100, self._sw_tick)

    # ── FOCUS ──────────────────────────────────

    def _save_task(self):
        task = self.entry_task.get().strip()
        self.lbl_task_display.configure(
            text=f"📌 {task}" if task else "")
        self._data["task"] = task
        self._save()

    # ── QUOTES ─────────────────────────────────

    def _new_quote(self):
        quote, author = random.choice(QUOTES)
        self.lbl_quote_text.configure(text=f'"{quote}"')
        self.lbl_quote_author.configure(text=f"— {author}")

    # ── HELPERS ────────────────────────────────

    def _clear_placeholder(self, entry: tk.Entry, placeholder: str):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.configure(fg=self._theme["text"])

    def _restore_placeholder(self, entry: tk.Entry, placeholder: str):
        if not entry.get():
            entry.insert(0, placeholder)
            entry.configure(fg=self._theme["text2"])

    # ── PERSISTENCE ────────────────────────────

    def _save(self):
        self._data["timers"] = [m.to_dict() for m in self._timer_models]
        self._data["theme"] = self._theme_name
        Storage.save(self._data)

    def _on_close(self):
        self._save()
        self.destroy()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = FocusFlowApp()

    # Center window
    app.update_idletasks()
    w, h = app.winfo_width(), app.winfo_height()
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    app.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    app.mainloop()
