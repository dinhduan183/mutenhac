#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mute Nhạc - Desktop App
Tự động xử lý MP3 / video theo chu kỳ bằng ffmpeg. Mặc định: 3 giây bật tiếng, 8 giây tắt tiếng.
Đoạn tắt tiếng có thể: tắt hẳn, giảm xuống một mức dB, hoặc chêm một file âm thanh phụ vào.
"""

import os
import re
import sys
import math
import shutil
import subprocess
import threading
import queue
import platform
import json
import ssl
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import (
    Tk, Canvas, Frame, StringVar, IntVar, DoubleVar, END, DISABLED, NORMAL,
    filedialog, messagebox
)
from tkinter import ttk, font as tkfont
from tkinter.scrolledtext import ScrolledText


APP_TITLE = "Mute Nhạc - Auto Unmute/Mute MP3"
APP_VERSION = "2.2"
GITHUB_REPO = "dinhduan183/mutenhac"
RELEASES_URL = "https://github.com/{}/releases/latest".format(GITHUB_REPO)

# Định dạng đầu vào hỗ trợ
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm", ".flv", ".wmv"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}

# ---------- Bảng màu (theo tone slate/indigo của Nối Nhạc Pro) ----------
BG = "#0F172A"          # slate-900
PANEL = "#131C30"       # slate-900/50
BORDER = "#1E293B"      # slate-800
FIELD = "#1E293B"       # slate-800
FIELD_BORDER = "#334155"  # slate-700
TEXT = "#F8FAFC"        # slate-50
TEXT_DIM = "#CBD5E1"    # slate-300
MUTED = "#94A3B8"       # slate-400
FAINT = "#64748B"       # slate-500
INDIGO = "#6366F1"      # indigo-500
INDIGO_LIGHT = "#818CF8"  # indigo-400
PURPLE = "#9333EA"      # purple-600
EMERALD = "#34D399"     # emerald-400
ROSE = "#F43F5E"        # rose-500
ROSE_LIGHT = "#FB7185"  # rose-400
AMBER = "#FBBF24"       # amber-400
SKY = "#38BDF8"         # sky-400
LOG_BG = "#0B1220"      # slate-950


def resource_path(rel: str) -> str:
    """Trả về path tài nguyên (hỗ trợ chạy từ PyInstaller bundle)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def find_ffmpeg():
    """Tìm ffmpeg: ưu tiên bản đi kèm trong bundle, sau đó PATH."""
    bundled_names = ["ffmpeg.exe", "ffmpeg"]
    for name in bundled_names:
        p = resource_path(name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
        p2 = resource_path(os.path.join("bin", name))
        if os.path.isfile(p2) and os.access(p2, os.X_OK):
            return p2

    found = shutil.which("ffmpeg")
    if found:
        return found

    common = [
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in common:
        if os.path.isfile(c):
            return c
    return None


def _version_tuple(v):
    """'v2.10' → (2, 10). Bỏ qua ký tự không phải số."""
    return tuple(int(x) for x in re.findall(r"\d+", v))


def _is_newer(latest, current):
    a, b = list(_version_tuple(latest)), list(_version_tuple(current))
    n = max(len(a), len(b))
    return a + [0] * (n - len(a)) > b + [0] * (n - len(b))


def fetch_latest_release():
    """Hỏi GitHub bản release mới nhất. Trả về (tag, url) hoặc None nếu lỗi/không có mạng."""
    try:
        import certifi  # bản build có kèm certifi → không phụ thuộc chứng chỉ SSL của máy
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
    req = urllib.request.Request(
        "https://api.github.com/repos/{}/releases/latest".format(GITHUB_REPO),
        headers={"Accept": "application/vnd.github+json", "User-Agent": "MuteNhac/" + APP_VERSION},
    )
    try:
        with urllib.request.urlopen(req, timeout=6, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["tag_name"], data.get("html_url") or RELEASES_URL
    except Exception:
        return None


def _mix(c1, c2, t):
    """Nội suy 2 màu hex theo tỉ lệ t (0..1)."""
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(*(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def _mono_family():
    fams = set(tkfont.families())
    for c in ("SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono", "Courier New"):
        if c in fams:
            return c
    return "Courier"


class MuteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("{} v{}".format(APP_TITLE, APP_VERSION))
        self.root.geometry("1040x780")
        self.root.minsize(900, 620)
        self.root.configure(bg=BG)

        # State
        self.input_paths = []
        self.output_dir = None
        self.unmute_var = DoubleVar(value=3.0)
        self.mute_var = DoubleVar(value=8.0)
        # Âm lượng đoạn bật tiếng (hát gốc), dB, 0 = giữ nguyên
        self.on_db_var = DoubleVar(value=0.0)
        # Chế độ: "mute" = tắt tiếng như cũ, "insert" = chêm file phụ vào đoạn tắt tiếng
        self.mode_var = StringVar(value="mute")
        self.sub_path = None
        self.sub_duration = None
        self.sub_len_var = DoubleVar(value=5.0)
        self.sub_info_var = StringVar(value="Chưa chọn")
        # Âm lượng file phụ khi chêm (dB, 0 = giữ nguyên)
        self.sub_db_var = DoubleVar(value=0.0)
        # Đoạn tắt tiếng ở chế độ mute: "off" = im lặng hẳn, "duck" = giảm còn duck_db
        self.off_kind_var = StringVar(value="off")
        self.duck_db_var = DoubleVar(value=-30.0)
        self.suffix_var = StringVar(value=self._format_suffix(3.0, 8.0))
        self._suffix_auto = True
        self.suffix_var.trace_add("write", self._on_suffix_edited)
        self.unmute_var.trace_add("write", self._on_times_changed)
        self.mute_var.trace_add("write", self._on_times_changed)
        self.sub_len_var.trace_add("write", self._on_times_changed)
        self.mode_var.trace_add("write", self._on_mode_changed)
        self.off_kind_var.trace_add("write", self._on_off_kind_changed)
        self.duck_db_var.trace_add("write", self._on_times_changed)
        self.on_db_var.trace_add("write", lambda *_: self._draw_cycle_preview())
        self.sub_db_var.trace_add("write", lambda *_: self._draw_cycle_preview())
        self.status_var = StringVar(value="Sẵn sàng.")
        self.substatus_var = StringVar(value="Chọn file hoặc thư mục để bắt đầu")
        self.out_audio_var = StringVar(value="")
        self.out_video_var = StringVar(value="")
        self.suffix_var.trace_add("write", lambda *_: self._update_output_preview())
        self.cycle_var = StringVar(value="")
        self.percent_var = StringVar(value="")
        self.progress_var = IntVar(value=0)
        self.progress_var.trace_add("write", self._on_progress)
        self.is_running = False
        self.cancel_flag = False
        self.log_queue = queue.Queue()

        self.ffmpeg_path = find_ffmpeg()

        self._build_ui()
        self._poll_log_queue()
        threading.Thread(target=self._check_update, daemon=True).start()

        if not self.ffmpeg_path:
            self.log(
                "[CẢNH BÁO] Không tìm thấy ffmpeg trên máy.\n"
                "  • macOS: cài bằng 'brew install ffmpeg'\n"
                "  • Windows: tải tại https://www.gyan.dev/ffmpeg/builds/ "
                "rồi thêm vào PATH hoặc đặt ffmpeg.exe cạnh app.\n"
            )
        else:
            self.log("[OK] ffmpeg: {}".format(self.ffmpeg_path))

    # ---------- UI ----------
    def _setup_styles(self):
        # Font hệ thống (macOS: SF Pro qua TkDefaultFont, Windows: Segoe UI)
        fam = tkfont.nametofont("TkDefaultFont").actual("family")
        mono = _mono_family()
        self.f_title = (fam, 17, "bold")
        self.f_sub = (fam, 11)
        self.f_tiny = (fam, 10)
        self.f_label = (fam, 10, "bold")
        self.f_body = (fam, 12)
        self.f_small = (fam, 11)
        self.f_btn = (fam, 12, "bold")
        self.f_mono = (mono, 11)

        st = ttk.Style(self.root)
        if "clam" in st.theme_names():
            st.theme_use("clam")

        st.configure("Panel.TFrame", background=PANEL)
        st.configure("Bg.TFrame", background=BG)

        st.configure("Panel.TLabel", background=PANEL, foreground=TEXT_DIM, font=self.f_body)
        st.configure("PanelHead.TLabel", background=PANEL, foreground=FAINT, font=self.f_label)
        st.configure("PanelMuted.TLabel", background=PANEL, foreground=FAINT, font=self.f_small)
        st.configure("Section.TLabel", background=BG, foreground=FAINT, font=self.f_label)
        st.configure("Status.TLabel", background=BG, foreground=TEXT_DIM, font=self.f_body)
        st.configure("SubStatus.TLabel", background=BG, foreground=FAINT, font=self.f_tiny)
        st.configure("Percent.TLabel", background=BG, foreground=INDIGO_LIGHT, font=(mono, 11))

        # Nút chính
        st.configure("Accent.TButton", background=INDIGO, foreground="#FFFFFF",
                     font=self.f_btn, borderwidth=0, relief="flat", padding=(22, 9),
                     focuscolor=INDIGO)
        st.map("Accent.TButton",
               background=[("disabled", BORDER), ("pressed", INDIGO), ("active", INDIGO_LIGHT)],
               foreground=[("disabled", FAINT)])

        # Nút huỷ
        st.configure("Danger.TButton", background=ROSE, foreground="#FFFFFF",
                     font=self.f_btn, borderwidth=0, relief="flat", padding=(18, 9),
                     focuscolor=ROSE)
        st.map("Danger.TButton",
               background=[("disabled", BORDER), ("pressed", ROSE), ("active", ROSE_LIGHT)],
               foreground=[("disabled", FAINT)])

        # Nút phụ
        st.configure("Ghost.TButton", background=FIELD, foreground=MUTED,
                     font=self.f_small, borderwidth=0, relief="flat", padding=(14, 7),
                     focuscolor=FIELD)
        st.map("Ghost.TButton",
               background=[("pressed", FIELD), ("active", FIELD_BORDER)],
               foreground=[("active", TEXT)])

        # Nút phụ cỡ nhỏ (đặt cùng hàng với lựa chọn chế độ, không làm hàng cao thêm)
        st.configure("GhostSm.TButton", background=FIELD, foreground=MUTED,
                     font=self.f_small, borderwidth=0, relief="flat", padding=(12, 1),
                     focuscolor=FIELD)
        st.map("GhostSm.TButton",
               background=[("pressed", FIELD), ("active", FIELD_BORDER)],
               foreground=[("active", TEXT)])

        # Ô nhập
        for name in ("Field.TEntry", "Field.TSpinbox", "FieldSm.TSpinbox"):
            st.configure(name, fieldbackground=FIELD, background=FIELD, foreground=TEXT,
                         bordercolor=FIELD_BORDER, lightcolor=FIELD_BORDER, darkcolor=FIELD_BORDER,
                         insertcolor=TEXT, arrowcolor=MUTED, arrowsize=12,
                         borderwidth=1, relief="flat", padding=(7, 6), font=self.f_small)
            st.map(name,
                   bordercolor=[("focus", INDIGO)],
                   lightcolor=[("focus", INDIGO)],
                   darkcolor=[("focus", INDIGO)],
                   arrowcolor=[("disabled", FIELD_BORDER), ("active", TEXT)],
                   foreground=[("disabled", FAINT)],
                   fieldbackground=[("disabled", PANEL)])

        for name in ("Panel.TRadiobutton", "Mode.TRadiobutton"):
            st.configure(name, background=PANEL, foreground=TEXT_DIM, font=self.f_body,
                         indicatorbackground=FIELD, indicatorforeground=INDIGO_LIGHT,
                         indicatormargin=(0, 0, 6, 0), focuscolor=PANEL)
        st.configure("Mode.TRadiobutton", font=(self.f_body[0], self.f_body[1] + 1, "bold"))
        for name in ("Panel.TRadiobutton", "Mode.TRadiobutton"):
            # Option đang chọn sáng rõ, option không chọn mờ đi
            st.map(name,
                   background=[("active", PANEL)],
                   foreground=[("selected", TEXT), ("active", TEXT_DIM), ("!selected", FAINT)],
                   indicatorbackground=[("selected", INDIGO), ("active", FIELD_BORDER)])

        st.configure("FieldSm.TSpinbox", padding=(6, 1))

        st.configure("Accent.Horizontal.TProgressbar", troughcolor=BORDER, background=INDIGO,
                     bordercolor=BORDER, lightcolor=INDIGO, darkcolor=INDIGO,
                     thickness=6, borderwidth=0)

    def _section(self, parent, text):
        ttk.Label(parent, text=text.upper(), style="Section.TLabel").pack(anchor="w", pady=(0, 6))

    def _panel(self, parent, **pack_kw):
        """Panel nền tối, viền 1px."""
        outer = Frame(parent, bg=BORDER, bd=0, highlightthickness=0)
        outer.pack(fill=pack_kw.pop("fill", "x"), expand=pack_kw.pop("expand", False), **pack_kw)
        inner = Frame(outer, bg=PANEL, bd=0, highlightthickness=0)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        return inner

    def _build_ui(self):
        self._setup_styles()

        # ───── Header ─────
        header = Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 12))

        logo = Canvas(header, width=36, height=36, bg=BG, highlightthickness=0, bd=0)
        logo.pack(side="left")
        for k in range(0, 72):
            logo.create_line(k, 0, 0, k, fill=_mix(INDIGO, PURPLE, k / 72.0))
        logo.create_text(17, 19, text="♪", fill="#FFFFFF", font=(self.f_title[0], 18, "bold"))
        # Gạch chéo như icon ngoài (nốt nhạc bị gạch = tắt tiếng)
        logo.create_line(8, 7, 28, 27, fill="#FFFFFF", width=4, capstyle="round")

        titles = Frame(header, bg=BG)
        titles.pack(side="left", padx=(12, 0))
        ttk.Label(titles, text="Mute Nhạc", background=BG, foreground=INDIGO_LIGHT,
                  font=self.f_title).pack(anchor="w")
        ttk.Label(titles, text="Tự động bật/tắt tiếng theo chu kỳ  ·  v{}".format(APP_VERSION),
                  background=BG, foreground=FAINT, font=self.f_tiny).pack(anchor="w", pady=(1, 0))

        self.cv_ffmpeg = Canvas(header, height=28, width=170, bg=BG, highlightthickness=0, bd=0)
        self.cv_ffmpeg.pack(side="right")
        self._draw_ffmpeg_chip()

        # Chip báo bản mới (chỉ hiện khi GitHub có release mới hơn)
        self.cv_update = Canvas(header, height=28, width=10, bg=BG, highlightthickness=0, bd=0, cursor="hand2")
        self._update_url = RELEASES_URL
        self.cv_update.bind("<Button-1>", lambda _e: webbrowser.open(self._update_url))

        Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # ───── Footer (pack trước body để luôn được cấp chỗ khi cửa sổ hẹp) ─────
        footer = Frame(self.root, bg=BG)
        footer.pack(side="bottom", fill="x", padx=20, pady=12)
        Frame(self.root, bg=BORDER, height=1).pack(side="bottom", fill="x")

        left = Frame(footer, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w")
        ttk.Label(left, textvariable=self.substatus_var, style="SubStatus.TLabel").pack(anchor="w", pady=(2, 0))

        self.btn_start = ttk.Button(footer, text="▶  Bắt đầu xử lý", style="Accent.TButton", command=self.start)
        self.btn_start.pack(side="right")
        self.btn_cancel = ttk.Button(footer, text="■  Huỷ", style="Danger.TButton",
                                     command=self.cancel, state=DISABLED)
        self.btn_cancel.pack(side="right", padx=(10, 10))
        ttk.Button(footer, text="Mở thư mục output", style="Ghost.TButton",
                   command=self.open_output_dir).pack(side="right", padx=(10, 0))
        ttk.Label(footer, textvariable=self.percent_var, style="Percent.TLabel",
                  width=5, anchor="e").pack(side="right", padx=(8, 0))
        self.progress = ttk.Progressbar(footer, variable=self.progress_var, maximum=100,
                                        length=150, style="Accent.Horizontal.TProgressbar")
        self.progress.pack(side="right")

        # ───── Body ─────
        body = Frame(self.root, bg=BG)
        body.pack(side="top", fill="both", expand=True, padx=20, pady=(16, 0))

        # Đầu vào
        self._section(body, "Đầu vào")
        p_in = self._panel(body, pady=(0, 14))
        row = Frame(p_in, bg=PANEL)
        row.pack(fill="x", padx=14, pady=(12, 0))
        # Pack nút trước để luôn giữ chỗ, nhãn đường dẫn dài không đẩy nút ra khỏi khung
        ttk.Button(row, text="Chọn thư mục…", style="Ghost.TButton",
                   command=self.choose_folder).pack(side="right", padx=(8, 0))
        ttk.Button(row, text="Chọn file…", style="Ghost.TButton",
                   command=self.choose_files).pack(side="right")
        self.lbl_input = ttk.Label(row, text="Chưa chọn file/thư mục.", style="Panel.TLabel")
        self.lbl_input.configure(foreground=FAINT)
        self.lbl_input.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Giải thích đầu ra theo loại file
        Frame(p_in, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(12, 0))
        outbox = Frame(p_in, bg=PANEL)
        outbox.pack(fill="x", padx=14, pady=(10, 12))
        ttk.Label(outbox, text="KẾT QUẢ SẼ TẠO RA", style="PanelHead.TLabel").pack(anchor="w")
        self.lbl_out_audio = ttk.Label(outbox, textvariable=self.out_audio_var, style="PanelMuted.TLabel")
        self.lbl_out_audio.pack(anchor="w", pady=(6, 0))
        self.lbl_out_video = ttk.Label(outbox, textvariable=self.out_video_var, style="PanelMuted.TLabel")
        self.lbl_out_video.pack(anchor="w", pady=(3, 0))

        # Thông số
        self._section(body, "Thông số chu kỳ")
        p_opt = self._panel(body, pady=(0, 16))
        # Hàng trên cùng: 2 chế độ chính
        moderow = Frame(p_opt, bg=PANEL)
        moderow.pack(fill="x", padx=14, pady=(12, 0))
        ttk.Radiobutton(moderow, text="Tắt tiếng on/off", value="mute", variable=self.mode_var,
                        style="Mode.TRadiobutton").pack(side="left")
        ttk.Radiobutton(moderow, text="Chêm file phụ vào đoạn tắt tiếng", value="insert",
                        variable=self.mode_var, style="Mode.TRadiobutton").pack(side="left", padx=(24, 0))
        ttk.Label(moderow, textvariable=self.cycle_var, style="PanelMuted.TLabel").pack(side="right")

        grid = Frame(p_opt, bg=PANEL)
        grid.pack(fill="x", padx=14, pady=(12, 0))

        ttk.Label(grid, text="Bật tiếng (giây)", style="PanelMuted.TLabel").grid(row=0, column=0, sticky="w")
        on_box = Frame(grid, bg=PANEL)
        ttk.Spinbox(on_box, from_=0.1, to=600, increment=0.5, textvariable=self.unmute_var,
                    width=6, style="Field.TSpinbox").pack(side="left")
        ttk.Spinbox(on_box, from_=-60, to=20, increment=1, textvariable=self.on_db_var,
                    width=5, style="FieldSm.TSpinbox").pack(side="left", padx=(10, 0))
        ttk.Label(on_box, text="dB", style="PanelMuted.TLabel").pack(side="left", padx=(6, 0))
        on_box.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.lbl_mute = ttk.Label(grid, text="Tắt tiếng (giây)", style="PanelMuted.TLabel")
        self.lbl_mute.grid(row=0, column=1, sticky="w", padx=(16, 0))
        # Ô thời lượng file phụ thế vào đúng chỗ ô Tắt tiếng khi ở chế độ chêm
        self.lbl_sub_len = ttk.Label(grid, text="Lấy file phụ (giây)", style="PanelMuted.TLabel")
        self.lbl_sub_len.grid(row=0, column=1, sticky="w", padx=(16, 0))
        self.spn_sub_len = ttk.Spinbox(grid, from_=0.1, to=600, increment=0.5,
                                       textvariable=self.sub_len_var, width=6, style="Field.TSpinbox")
        self.spn_sub_len.grid(row=1, column=1, sticky="w", padx=(16, 0), pady=(4, 0))
        self.lbl_sub_len.grid_remove()
        self.spn_sub_len.grid_remove()
        self.spn_mute = ttk.Spinbox(grid, from_=0.1, to=600, increment=0.5, textvariable=self.mute_var,
                                    width=6, style="Field.TSpinbox")
        self.spn_mute.grid(row=1, column=1, sticky="w", padx=(16, 0), pady=(4, 0))

        # Option phụ theo chế độ (cột 2): kiểu đoạn tắt tiếng / file phụ
        self.lbl_off = ttk.Label(grid, text="Đoạn tắt tiếng", style="PanelMuted.TLabel")
        self.lbl_off.grid(row=0, column=2, sticky="w", padx=(24, 0))
        self.off_box = Frame(grid, bg=PANEL)
        ttk.Radiobutton(self.off_box, text="Tắt hẳn", value="off", variable=self.off_kind_var,
                        style="Panel.TRadiobutton").pack(side="left")
        ttk.Radiobutton(self.off_box, text="Chỉnh âm lượng", value="duck", variable=self.off_kind_var,
                        style="Panel.TRadiobutton").pack(side="left", padx=(14, 8))
        self.spn_duck = ttk.Spinbox(self.off_box, from_=-60, to=20, increment=1,
                                    textvariable=self.duck_db_var, width=5, style="FieldSm.TSpinbox")
        self.spn_duck.pack(side="left")
        self.lbl_db = ttk.Label(self.off_box, text="dB", style="PanelMuted.TLabel")
        self.lbl_db.pack(side="left", padx=(6, 0))
        self.off_box.grid(row=1, column=2, sticky="w", padx=(24, 0), pady=(4, 0))

        self.lbl_subfile = ttk.Label(grid, text="File phụ", style="PanelMuted.TLabel")
        self.lbl_subfile.grid(row=0, column=2, sticky="w", padx=(24, 0))
        self.sub_box = Frame(grid, bg=PANEL)
        ttk.Button(self.sub_box, text="Chọn file phụ…", style="GhostSm.TButton",
                   command=self.choose_sub_file).pack(side="left")
        ttk.Spinbox(self.sub_box, from_=-60, to=20, increment=1,
                    textvariable=self.sub_db_var, width=5, style="FieldSm.TSpinbox").pack(side="left", padx=(10, 0))
        ttk.Label(self.sub_box, text="dB", style="PanelMuted.TLabel").pack(side="left", padx=(6, 0))
        self.lbl_sub = ttk.Label(self.sub_box, textvariable=self.sub_info_var, style="Panel.TLabel")
        self.lbl_sub.configure(foreground=FAINT)
        self.lbl_sub.pack(side="left", padx=(10, 0))
        self.sub_box.grid(row=1, column=2, sticky="w", padx=(24, 0), pady=(4, 0))
        self.lbl_subfile.grid_remove()
        self.sub_box.grid_remove()


        prev = Frame(p_opt, bg=PANEL)
        prev.pack(fill="x", padx=14, pady=(12, 0))
        self.cv_cycle = Canvas(prev, height=74, bg=PANEL, highlightthickness=0, bd=0)
        self.cv_cycle.pack(fill="x")
        self.cv_cycle.bind("<Configure>", self._draw_cycle_preview)

        outrow = Frame(p_opt, bg=PANEL)
        outrow.pack(fill="x", padx=14, pady=(14, 12))
        ttk.Label(outrow, text="Thư mục lưu", style="PanelMuted.TLabel").pack(side="left")
        ttk.Button(outrow, text="Đổi…", style="Ghost.TButton",
                   command=self.choose_output_dir).pack(side="right")
        ttk.Entry(outrow, textvariable=self.suffix_var, width=18,
                  style="Field.TEntry").pack(side="right", padx=(0, 16))
        ttk.Label(outrow, text="Hậu tố tên file", style="PanelMuted.TLabel").pack(side="right", padx=(0, 8))
        self.lbl_outdir = ttk.Label(outrow, text="mặc định: cùng thư mục với file gốc", style="Panel.TLabel")
        self.lbl_outdir.configure(foreground=MUTED)
        self.lbl_outdir.pack(side="left", fill="x", expand=True, padx=(12, 10))

        # Nhật ký
        self._section(body, "Nhật ký")
        p_log = self._panel(body, fill="both", expand=True, pady=(0, 16))
        self.txt_log = ScrolledText(
            p_log, height=6, wrap="word", font=self.f_mono,
            bg=LOG_BG, fg=MUTED, insertbackground=TEXT,
            selectbackground=INDIGO, selectforeground="#FFFFFF",
            relief="flat", bd=0, highlightthickness=0, padx=12, pady=10,
        )
        self.txt_log.pack(fill="both", expand=True, padx=1, pady=1)
        self.txt_log.tag_config("ok", foreground=EMERALD)
        self.txt_log.tag_config("err", foreground=ROSE_LIGHT)
        self.txt_log.tag_config("warn", foreground=AMBER)
        self.txt_log.tag_config("info", foreground=SKY)
        self.txt_log.tag_config("head", foreground=INDIGO_LIGHT)

        self._on_off_kind_changed()
        self._update_output_preview()

    def _check_update(self):
        res = fetch_latest_release()
        if res and _is_newer(res[0], APP_VERSION):
            self.root.after(0, self._show_update_chip, res[0], res[1])

    def _show_update_chip(self, tag, url):
        self._update_url = url
        c = self.cv_update
        label = "Có bản {} — Tải về".format(tag)
        tw = tkfont.Font(font=self.f_small).measure(label)
        w = tw + 36
        c.configure(width=w)
        c.delete("all")
        c.create_rectangle(1, 2, w - 1, 26, fill=PANEL, outline=AMBER)
        c.create_text(12, 14, anchor="w", text="↑", fill=AMBER, font=self.f_small)
        c.create_text(26, 14, anchor="w", text=label, fill=AMBER, font=self.f_small)
        c.pack(side="right", padx=(0, 10))
        self.log("[INFO] Có bản mới {} (đang dùng v{}). Tải tại: {}".format(tag, APP_VERSION, url))

    def _draw_ffmpeg_chip(self):
        c = self.cv_ffmpeg
        c.delete("all")
        ok = bool(self.ffmpeg_path)
        label = "ffmpeg sẵn sàng" if ok else "chưa có ffmpeg"
        color = EMERALD if ok else ROSE_LIGHT
        w = c.winfo_reqwidth()
        tw = tkfont.Font(font=self.f_small).measure(label)
        x0 = w - (tw + 34)
        c.create_rectangle(x0, 2, w, 26, fill=PANEL, outline=BORDER)
        c.create_oval(x0 + 12, 11, x0 + 18, 17, fill=color, outline="")
        c.create_text(x0 + 24, 14, anchor="w", text=label, fill=color, font=self.f_small)

    def _draw_cycle_preview(self, _evt=None):
        """Vẽ dải sóng minh hoạ: đoạn có tiếng = sóng indigo, đoạn tắt tiếng = đường phẳng."""
        c = getattr(self, "cv_cycle", None)
        if c is None:
            return
        w, h = c.winfo_width(), c.winfo_height()
        if w < 40:
            return
        insert = self.mode_var.get() == "insert"
        try:
            u = max(0.1, float(self.unmute_var.get()))
            m = max(0.1, float(self.sub_len_var.get() if insert else self.mute_var.get()))
            duck = (float(self.duck_db_var.get())
                    if not insert and self.off_kind_var.get() == "duck" else None)
        except Exception:
            return

        def db_of(var):
            try:
                return float(var.get())
            except Exception:
                return 0.0
        on_db, sub_db = db_of(self.on_db_var), db_of(self.sub_db_var)

        def db_scale(db):
            # Chiều cao sóng theo dB (tuyến tính theo dB): 0dB ≈ 55%, +20dB = đầy khung, -20dB ≈ 10%
            return min(1.0, max(0.03, 0.55 + db * 0.0225))
        on_scale = db_scale(on_db)
        sub_scale = db_scale(sub_db)
        duck_scale = db_scale(duck) if duck is not None else 0

        c.delete("all")
        cycle = u + m
        self.cycle_var.set("Chu kỳ {:g}s".format(cycle))

        n = 3                      # số chu kỳ hiển thị
        wave_h = h - 22            # chừa 22px dưới cho nhãn
        mid = wave_h / 2.0
        px = w / (cycle * n)       # pixel cho mỗi giây

        def on_at(t):
            return (t % cycle) < u

        # Nền: đoạn tắt tiếng tối hơn đoạn có tiếng
        c.create_rectangle(0, 0, w, wave_h, outline="", fill=BORDER)
        seg = 0
        while seg < cycle * n:
            c.create_rectangle(seg * px, 0, min(w, (seg + u) * px), wave_h,
                               outline="", fill="#1B2545")
            seg += cycle

        # Đường tâm
        c.create_line(0, mid, w, mid, fill=FIELD_BORDER)

        # Sóng
        step = 3
        for i, x in enumerate(range(2, int(w) - 1, step)):
            t = x / px
            if on_at(t):
                a = abs(math.sin(i * 0.63) * math.cos(i * 0.21) + 0.35 * math.sin(i * 1.71))
                amp = max(1.0, min(1.0, a) * (mid - 3) * on_scale)
                c.create_line(x, mid - amp, x, mid + amp, fill=INDIGO, width=2)
            elif duck is not None:
                a = abs(math.sin(i * 0.63) * math.cos(i * 0.21) + 0.35 * math.sin(i * 1.71))
                amp = max(1.0, min(1.0, a) * (mid - 3) * duck_scale)
                c.create_line(x, mid - amp, x, mid + amp, fill=INDIGO, width=2)
            elif insert:
                a = abs(math.cos(i * 0.47) * math.sin(i * 0.29) + 0.3 * math.cos(i * 1.33))
                amp = max(1.0, min(1.0, a) * (mid - 3) * sub_scale)
                c.create_line(x, mid - amp, x, mid + amp, fill=AMBER, width=2)
            else:
                c.create_line(x, mid, x, mid + 1, fill=FAINT)

        # Vạch mốc chu kỳ
        k = 0
        while k <= n:
            x = k * cycle * px
            if x <= w:
                c.create_line(x, 0, x, wave_h, fill=FIELD_BORDER)
                if k < n:
                    c.create_text(x + 5, wave_h - 8, anchor="w",
                                  text="{:g}s".format(k * cycle), fill=FAINT, font=self.f_tiny)
            k += 1

        # Nhãn cho chu kỳ đầu tiên
        y = wave_h + 11
        f_on = tkfont.Font(font=self.f_tiny)
        on_w, off_w = u * px, m * px
        def db_txt(db):
            return " {:+g}dB".format(db) if db else ""
        lbl_on = "bật tiếng {:g}s{}".format(u, db_txt(on_db))
        if insert:
            lbl_off = "file phụ {:g}s{}".format(m, db_txt(sub_db))
        elif duck is not None:
            lbl_off = "{} {:g}dB {:g}s".format("tăng" if duck > 0 else "giảm", abs(duck), m)
        else:
            lbl_off = "tắt tiếng {:g}s".format(m)
        if on_w > f_on.measure(lbl_on) + 8:
            c.create_text(on_w / 2, y, text=lbl_on, fill=INDIGO_LIGHT, font=self.f_tiny)
        if off_w > f_on.measure(lbl_off) + 8:
            c.create_text(on_w + off_w / 2, y, text=lbl_off, fill=AMBER if insert else FAINT,
                          font=self.f_tiny)
        c.create_text(w, y, anchor="e", text="lặp lại đến hết bài", fill=FAINT, font=self.f_tiny)

    def _update_output_preview(self):
        """Cập nhật khối 'kết quả sẽ tạo ra' theo loại file đang chọn."""
        if not hasattr(self, "lbl_out_audio"):
            return
        suffix = self.suffix_var.get() or "_processed"
        n_aud = sum(1 for f in self.input_paths if f.suffix.lower() in AUDIO_EXTS)
        n_vid = sum(1 for f in self.input_paths if f.suffix.lower() in VIDEO_EXTS)

        if self.input_paths:
            a = "{} file audio  →  {} file .mp3 đã xử lý tiếng      vd: ten-bai{}.mp3".format(
                n_aud, n_aud, suffix)
            v = ("{} file video  →  {} video giữ nguyên hình (chỉ tiếng bị xử lý)  +  {} file .mp3 "
                 "âm thanh gốc      vd: clip{}.mp4  ·  clip_goc.mp3").format(n_vid, n_vid, n_vid, suffix)
            self.lbl_out_audio.configure(foreground=SKY if n_aud else FAINT)
            self.lbl_out_video.configure(foreground=INDIGO_LIGHT if n_vid else FAINT)
        else:
            a = "File audio (mp3, wav, m4a, aac, flac…)  →  1 file .mp3 đã xử lý tiếng      vd: ten-bai{}.mp3".format(suffix)
            v = ("File video (mp4, mov, mkv, avi…)  →  1 video giữ nguyên hình (chỉ tiếng bị xử lý)  +  "
                 "1 file .mp3 âm thanh gốc chưa xử lý")
            self.lbl_out_audio.configure(foreground=FAINT)
            self.lbl_out_video.configure(foreground=FAINT)

        self.out_audio_var.set("•  " + a)
        self.out_video_var.set("•  " + v)

    def _on_progress(self, *_):
        try:
            v = int(self.progress_var.get())
        except Exception:
            return
        self.percent_var.set("{}%".format(v) if v else "")

    # ---------- helpers ----------
    @staticmethod
    def _format_suffix(unmute, mute, insert=False, duck_db=None):
        def fmt(v):
            return ("{:g}".format(round(float(v), 2)))
        if insert:
            return "_{}s-on-{}s-chen".format(fmt(unmute), fmt(mute))
        if duck_db is not None:
            return "_{}s-on-{}s-{}{}dB".format(fmt(unmute), fmt(mute),
                                                "tang" if duck_db > 0 else "giam", fmt(abs(duck_db)))
        return "_{}s-on-{}s-off".format(fmt(unmute), fmt(mute))

    def _on_times_changed(self, *_):
        self._draw_cycle_preview()
        if not getattr(self, "_suffix_auto", True):
            return
        insert = self.mode_var.get() == "insert"
        try:
            u = float(self.unmute_var.get())
            m = float(self.sub_len_var.get() if insert else self.mute_var.get())
            duck = float(self.duck_db_var.get()) if self.off_kind_var.get() == "duck" else None
        except Exception:
            return
        new_suffix = self._format_suffix(u, m, insert, duck)
        if self.suffix_var.get() != new_suffix:
            self._suffix_auto_writing = True
            self.suffix_var.set(new_suffix)
            self._suffix_auto_writing = False

    def _on_mode_changed(self, *_):
        if self.mode_var.get() == "insert":
            self.lbl_off.grid_remove()
            self.off_box.grid_remove()
            self.lbl_subfile.grid()
            self.sub_box.grid()
            self.lbl_mute.grid_remove()
            self.spn_mute.grid_remove()
            self.lbl_sub_len.grid()
            self.spn_sub_len.grid()
        else:
            self.lbl_subfile.grid_remove()
            self.sub_box.grid_remove()
            self.lbl_off.grid()
            self.off_box.grid()
            self.lbl_sub_len.grid_remove()
            self.spn_sub_len.grid_remove()
            self.lbl_mute.grid()
            self.spn_mute.grid()
        self._on_times_changed()

    def _on_off_kind_changed(self, *_):
        """Chọn 'Tắt hẳn' thì ô dB mờ đi và không sửa được."""
        duck = self.off_kind_var.get() == "duck"
        self.spn_duck.state(["!disabled"] if duck else ["disabled"])
        self.lbl_db.configure(foreground=MUTED if duck else FIELD_BORDER)
        self._on_times_changed()

    def _on_suffix_edited(self, *_):
        if getattr(self, "_suffix_auto_writing", False):
            return
        self._suffix_auto = False

    def log(self, msg):
        self.log_queue.put(msg)

    @staticmethod
    def _log_tag(msg):
        s = msg.lstrip()
        if s.startswith("✗") or s.startswith("!"):
            return "err"
        if s.startswith("✓") or s.startswith("[OK]"):
            return "ok"
        if s.startswith("[CẢNH BÁO]"):
            return "warn"
        if s.startswith("[BẮT ĐẦU]") or s.startswith("[KẾT THÚC]"):
            return "head"
        if s.startswith("[INFO]") or s.startswith("[HUỶ]"):
            return "info"
        return ""

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                text = msg + ("\n" if not msg.endswith("\n") else "")
                tag = self._log_tag(msg)
                self.txt_log.insert(END, text, tag if tag else ())
                self.txt_log.see(END)
        except queue.Empty:
            pass
        self.root.after(80, self._poll_log_queue)

    @staticmethod
    def _short_path(path, keep=58):
        """Rút gọn đường dẫn ở giữa để nhãn không đẩy nút ra khỏi khung."""
        text = str(path)
        if len(text) <= keep:
            return text
        head = keep // 4
        tail = keep - head - 1
        return text[:head] + "…" + text[-tail:]

    def choose_files(self):
        audio_pat = " ".join("*" + e for e in sorted(AUDIO_EXTS))
        video_pat = " ".join("*" + e for e in sorted(VIDEO_EXTS))
        files = filedialog.askopenfilenames(
            title="Chọn 1 hoặc nhiều file MP3 / Video",
            filetypes=[
                ("MP3 & Video", audio_pat + " " + video_pat),
                ("MP3 / Audio", audio_pat),
                ("Video", video_pat),
                ("Tất cả", "*.*"),
            ],
        )
        if files:
            self.input_paths = [Path(f) for f in files]
            n_vid = sum(1 for f in self.input_paths if f.suffix.lower() in VIDEO_EXTS)
            self.lbl_input.config(text="Đã chọn {} file ({} video)".format(len(self.input_paths), n_vid),
                                  foreground=TEXT_DIM)
            self.substatus_var.set("{} file đang chờ xử lý".format(len(self.input_paths)))
            self._update_output_preview()
            self.log("[INFO] Đã chọn {} file ({} video).".format(len(self.input_paths), n_vid))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa MP3 / Video")
        if folder:
            p = Path(folder)
            supported = AUDIO_EXTS | VIDEO_EXTS
            items = sorted([f for f in p.iterdir() if f.is_file() and f.suffix.lower() in supported])
            if not items:
                messagebox.showwarning(APP_TITLE, "Thư mục không có file MP3/Video nào được hỗ trợ.")
                return
            self.input_paths = items
            n_vid = sum(1 for f in items if f.suffix.lower() in VIDEO_EXTS)
            self.lbl_input.config(text="Thư mục: {}  ({} file, {} video)".format(
                                      self._short_path(folder), len(items), n_vid),
                                  foreground=TEXT_DIM)
            self.substatus_var.set("{} file đang chờ xử lý".format(len(items)))
            self._update_output_preview()
            self.log("[INFO] Thư mục: {} — tìm thấy {} file ({} video).".format(folder, len(items), n_vid))

    def _probe_duration(self, path):
        """Đọc thời lượng (giây) từ dòng 'Duration:' của ffmpeg -i. Trả về None nếu không đọc được."""
        kwargs = {}
        if platform.system() == "Windows":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        try:
            r = subprocess.run([self.ffmpeg_path, "-hide_banner", "-i", str(path)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", **kwargs)
        except Exception:
            return None
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
        if not m:
            return None
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

    def choose_sub_file(self):
        if not self.ffmpeg_path:
            messagebox.showerror(APP_TITLE, "Không tìm thấy ffmpeg. Vui lòng cài ffmpeg trước.")
            return
        audio_pat = " ".join("*" + e for e in sorted(AUDIO_EXTS))
        f = filedialog.askopenfilename(
            title="Chọn file âm thanh phụ",
            filetypes=[("MP3 / Audio", audio_pat), ("Tất cả", "*.*")],
        )
        if not f:
            return
        dur = self._probe_duration(f)
        if not dur:
            messagebox.showerror(APP_TITLE, "Không đọc được thời lượng file phụ:\n{}".format(f))
            return
        self.sub_path = Path(f)
        self.sub_duration = dur
        mins, secs = divmod(dur, 60)
        self.sub_info_var.set("{} · dài {}:{:04.1f}".format(
            self._short_path(self.sub_path.name, 20), int(mins), secs))
        self.lbl_sub.configure(foreground=TEXT_DIM)
        self.spn_sub_len.configure(to=round(dur, 2))
        self.sub_len_var.set(round(dur, 2))
        self.log("[INFO] File phụ: {} ({:g}s)".format(self.sub_path.name, round(dur, 2)))

    def choose_output_dir(self):
        folder = filedialog.askdirectory(title="Chọn thư mục output")
        if folder:
            self.output_dir = Path(folder)
            self.lbl_outdir.config(text=str(self.output_dir), foreground=TEXT_DIM)

    def open_output_dir(self):
        target = self.output_dir
        if not target and self.input_paths:
            target = self.input_paths[0].parent
        if not target:
            messagebox.showinfo(APP_TITLE, "Chưa có thư mục output để mở.")
            return
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", str(target)])
            elif platform.system() == "Windows":
                os.startfile(str(target))
            else:
                subprocess.run(["xdg-open", str(target)])
        except Exception as e:
            messagebox.showerror(APP_TITLE, "Không mở được thư mục:\n{}".format(e))

    # ---------- processing ----------
    def start(self):
        if self.is_running:
            return
        if not self.ffmpeg_path:
            messagebox.showerror(APP_TITLE, "Không tìm thấy ffmpeg. Vui lòng cài ffmpeg trước.")
            return
        if not self.input_paths:
            messagebox.showwarning(APP_TITLE, "Vui lòng chọn file hoặc thư mục MP3.")
            return
        try:
            unmute = float(self.unmute_var.get())
            mute = float(self.mute_var.get())
            if unmute <= 0 or mute <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror(APP_TITLE, "Thời gian unmute/mute phải là số dương.")
            return
        try:
            on_db = float(self.on_db_var.get())
            if on_db > 20:
                raise ValueError
        except Exception:
            messagebox.showerror(APP_TITLE, "Âm lượng đoạn bật tiếng phải là số ≤ 20 (dB), ví dụ -3 hoặc 6.")
            return

        sub = None
        if self.mode_var.get() == "insert":
            if not self.sub_path:
                messagebox.showwarning(APP_TITLE, "Vui lòng chọn file phụ để chêm.")
                return
            try:
                sub_len = float(self.sub_len_var.get())
                if sub_len <= 0:
                    raise ValueError
            except Exception:
                messagebox.showerror(APP_TITLE, "Thời lượng lấy từ file phụ phải là số dương.")
                return
            sub_len = min(sub_len, self.sub_duration)
            try:
                sub_db = float(self.sub_db_var.get())
                if sub_db > 20:
                    raise ValueError
            except Exception:
                messagebox.showerror(APP_TITLE, "Âm lượng file phụ phải là số ≤ 20 (dB), ví dụ -6 hoặc 6.")
                return
            sub = (self.sub_path, sub_len, sub_db)
            mute = sub_len

        duck_db = None
        if sub is None and self.off_kind_var.get() == "duck":
            try:
                duck_db = float(self.duck_db_var.get())
                if duck_db > 20:
                    raise ValueError
            except Exception:
                messagebox.showerror(APP_TITLE, "Mức âm lượng đoạn tắt tiếng phải là số ≤ 20 (dB), ví dụ -30.")
                return

        self.is_running = True
        self.cancel_flag = False
        self.btn_start.config(state=DISABLED)
        self.btn_cancel.config(state=NORMAL)
        self.progress_var.set(0)
        self.status_var.set("Đang xử lý…")

        t = threading.Thread(target=self._run_batch, args=(unmute, mute, sub, duck_db, on_db), daemon=True)
        t.start()

    def cancel(self):
        if self.is_running:
            self.cancel_flag = True
            self.log("[INFO] Đã yêu cầu huỷ. Sẽ dừng sau khi file hiện tại kết thúc…")

    def _run_ffmpeg(self, cmd, tag):
        """Chạy 1 lệnh ffmpeg, stream log realtime. Trả về (returncode, last_line)."""
        kwargs = {}
        if platform.system() == "Windows":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
        last_line = ""
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if line.startswith("size=") or line.startswith("frame="):
                last_line = line
                self.substatus_var.set("{} — {}".format(tag, line[:80]))
            elif "Error" in line or "error" in line or "Invalid" in line:
                self.log("  ! " + line)
        proc.wait()
        return proc.returncode, last_line

    @staticmethod
    def _insert_filter(unmute, sub_len, sample_rate, sub_db=0.0, on_db=0.0):
        """filter_complex chêm file phụ: bài gốc tắt tiếng ở đoạn off, file phụ (đã đệm im lặng
        bằng đoạn on ở đầu) lặp lại theo đúng chu kỳ rồi trộn đè lên → độ dài giữ nguyên."""
        cycle = unmute + sub_len
        fmt = "aresample={sr},aformat=sample_fmts=fltp:channel_layouts=stereo".format(sr=sample_rate)
        return (
            "[0:a:0]volume=enable='lt(mod(t,{cycle}),{unmute})':volume={on_db:g}dB,"
            "volume=enable='gte(mod(t,{cycle}),{unmute})':volume=0,{fmt}[m];"
            "[1:a:0]atrim=0:{sub_len},asetpts=PTS-STARTPTS,{fmt},volume={sub_db:g}dB,apad=whole_dur={sub_len},"
            "adelay={delay}:all=1,aloop=loop=-1:size={size}[s];"
            "[m][s]amix=inputs=2:duration=first:normalize=0[out]"
        ).format(cycle=cycle, unmute=unmute, sub_len=sub_len, fmt=fmt, sub_db=sub_db, on_db=on_db,
                 delay=int(round(unmute * 1000)), size=int(round(cycle * sample_rate)))

    def _run_batch(self, unmute, mute, sub=None, duck_db=None, on_db=0.0):
        cycle = unmute + mute
        suffix = self.suffix_var.get() or "_processed"
        level = "{:g}dB".format(duck_db) if duck_db is not None else "0"
        af = ("volume=enable='lt(mod(t,{cycle}),{unmute})':volume={on_db:g}dB,"
              "volume=enable='gte(mod(t,{cycle}),{unmute})':volume={level}").format(
            cycle=cycle, unmute=unmute, level=level, on_db=on_db)
        total = len(self.input_paths)
        ok, fail = 0, 0

        if sub:
            self.log("[BẮT ĐẦU] {} file • bật tiếng={}s ({:g}dB), chêm {} ({}s, {:g}dB), cycle={}s".format(
                total, unmute, on_db, sub[0].name, mute, sub[2], cycle))
        else:
            self.log("[BẮT ĐẦU] {} file • unmute={}s ({:g}dB), {}={}s, cycle={}s".format(
                total, unmute, on_db, "{} {}".format("tăng" if duck_db > 0 else "giảm", level) if duck_db is not None else "mute", mute, cycle))

        for idx, src in enumerate(self.input_paths, start=1):
            if self.cancel_flag:
                self.log("[HUỶ] Đã dừng theo yêu cầu.")
                break

            out_dir = self.output_dir if self.output_dir else src.parent
            out_dir.mkdir(parents=True, exist_ok=True)
            is_video = src.suffix.lower() in VIDEO_EXTS

            try:
                if is_video:
                    # Video: giữ nguyên hình (copy), chỉ xử lý tiếng → 1 video mới
                    #        + tách âm thanh gốc (chưa xử lý) → 1 mp3
                    out_video = out_dir / "{}{}{}".format(src.stem, suffix, src.suffix)
                    out_audio = out_dir / "{}_goc.mp3".format(src.stem)
                    self.log("[{}/{}] {} (video)".format(idx, total, src.name))
                    self.log("    → video đã xử lý: {}".format(out_video.name))
                    self.log("    → âm thanh gốc:   {}".format(out_audio.name))

                    if sub:
                        cmd_v = [
                            self.ffmpeg_path, "-y",
                            "-i", str(src), "-i", str(sub[0]),
                            "-filter_complex", self._insert_filter(unmute, mute, 48000, sub[2], on_db),
                            "-map", "0:v:0?", "-map", "[out]",
                            "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "192k",
                            str(out_video),
                        ]
                    else:
                        cmd_v = [
                            self.ffmpeg_path, "-y",
                            "-i", str(src),
                            "-af", af,
                            "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "192k",
                            str(out_video),
                        ]
                    rc_v, last_v = self._run_ffmpeg(cmd_v, "[{}/{}] video".format(idx, total))

                    if self.cancel_flag:
                        self.log("  ! Bỏ qua tách mp3 gốc do đã huỷ.")
                        rc_a = 1
                    else:
                        cmd_a = [
                            self.ffmpeg_path, "-y",
                            "-i", str(src),
                            "-vn",
                            "-c:a", "libmp3lame", "-q:a", "2",
                            str(out_audio),
                        ]
                        rc_a, _ = self._run_ffmpeg(cmd_a, "[{}/{}] mp3 gốc".format(idx, total))

                    if rc_v == 0 and rc_a == 0:
                        ok += 1
                        self.log("  ✓ Xong: {} + {}".format(out_video.name, out_audio.name))
                    else:
                        fail += 1
                        self.log("  ✗ Lỗi (video code {}, mp3 code {}). {}".format(rc_v, rc_a, last_v))
                else:
                    # Audio: xử lý như cũ → 1 mp3
                    out_file = out_dir / "{}{}.mp3".format(src.stem, suffix)
                    self.log("[{}/{}] {}  →  {}".format(idx, total, src.name, out_file.name))
                    if sub:
                        cmd = [
                            self.ffmpeg_path, "-y",
                            "-i", str(src), "-i", str(sub[0]),
                            "-filter_complex", self._insert_filter(unmute, mute, 44100, sub[2], on_db),
                            "-map", "[out]",
                            str(out_file),
                        ]
                    else:
                        cmd = [
                            self.ffmpeg_path, "-y",
                            "-i", str(src),
                            "-af", af,
                            str(out_file),
                        ]
                    rc, last_line = self._run_ffmpeg(cmd, "[{}/{}] {}".format(idx, total, src.name))
                    if rc == 0:
                        ok += 1
                        self.log("  ✓ Xong: {}".format(out_file.name))
                    else:
                        fail += 1
                        self.log("  ✗ ffmpeg lỗi (code {}). {}".format(rc, last_line))
            except FileNotFoundError:
                fail += 1
                self.log("  ✗ Không gọi được ffmpeg.")
                break
            except Exception as e:
                fail += 1
                self.log("  ✗ Lỗi: {}".format(e))

            self.progress_var.set(int(idx * 100 / total))

        self.log("[KẾT THÚC] Thành công: {} • Lỗi: {} • Tổng: {}".format(ok, fail, total))
        self.status_var.set("Hoàn tất. Thành công {}/{}.".format(ok, total))
        self.substatus_var.set("Lỗi: {} • Tổng: {}".format(fail, total))
        self.is_running = False
        self.cancel_flag = False
        self.btn_start.config(state=NORMAL)
        self.btn_cancel.config(state=DISABLED)


def main():
    root = Tk()
    try:
        if platform.system() == "Darwin":
            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(size=12)
    except Exception:
        pass
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    MuteApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
