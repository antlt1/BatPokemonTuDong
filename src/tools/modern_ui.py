"""
modern_ui.py - GUI chính dùng CustomTkinter
Giao diện hiện đại với Dark Mode, sidebar navigation, tabs

Cấu trúc:
  - Sidebar (trái): Dashboard, Team Builder, Bắt Pokemon, Settings
  - Main Content (phải): Nội dung tab hiện tại
  - Threading: Background worker chạy farm_battle.py
  - Hotkey F8: Start/Stop auto farm
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import threading
import queue
import time
import keyboard
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
TARGETS_PATH = ROOT / "src" / "config" / "target_pokemon.json"
TEAM_PATH = ROOT / "src" / "config" / "team_party.json"
FEEDBACK_LOG_PATH = ROOT / "src" / "runtime" / "feedback_log.txt"

# ======================= Pokemon Theme Colors =======================
POKE_BLUE = "#3b82f6"
POKE_RED = "#ef4444"
POKE_GREEN = "#22c55e"
POKE_YELLOW = "#eab308"
POKE_PURPLE = "#a855f7"
POKE_CYAN = "#06b6d4"
POKE_ORANGE = "#f97316"
POKE_PINK = "#ec4899"

BG_DARK = "#0a0a0f"
BG_CARD = "#13131a"
BG_CARD_HOVER = "#1a1a24"
BG_SIDEBAR = "#0d0d14"
BORDER_SUBTLE = "#1e1e2a"
TEXT_PRIMARY = "#e8e8f0"
TEXT_SECONDARY = "#8888a0"
TEXT_MUTED = "#555570"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ModernPokemonUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PokemonPRO Auto Tool")
        self.root.geometry("1600x900")
        self.root.resizable(True, True)
        self.root.configure(fg=BG_DARK)
        try:
            icon_path = ROOT / "src" / "template" / "app_icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass

        self.config = self._load_config()

        self.worker_thread = None
        self.worker_running = False
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.selected_mode = tk.StringVar(value="Auto Farm")

        self.stats = {"battles": 0, "pokemon": 0, "xp": 0, "runtime": "00:00:00"}
        self.hotkey_registered = False

        self._setup_ui()
        self._register_hotkey()
        self._start_log_listener()

    def _load_config(self):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            cfg = {}
        # Ensure defaults for catch feature
        cfg.setdefault("template_matching", {}).setdefault("items_button_threshold", 0.55)
        cfg.setdefault("roi", {}).setdefault("enemy_hp_bar", [520, 370, 200, 14])
        cfg.setdefault("hotkey", {}).setdefault("stop_hotkey", "alt+f8")
        cfg.setdefault("roi", {}).setdefault("my_pokemon_slots", [[10, 350, 160, 40], [10, 400, 160, 40], [10, 450, 160, 40], [10, 500, 160, 40], [10, 550, 160, 40], [10, 600, 160, 40]])
        cfg.setdefault("roi", {}).setdefault("shiny_popup_area", [400, 250, 1120, 400])
        cfg.setdefault("timing", {}).setdefault("after_swap_wait_seconds", 8.0)
        return cfg

    def _save_config(self):
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def _setup_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self._create_sidebar()

        self.main_frame = ctk.CTkFrame(self.root, fg_color=BG_DARK, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.content_container = ctk.CTkFrame(self.main_frame, fg_color=BG_DARK, corner_radius=0)
        self.content_container.grid(row=0, column=0, sticky="nsew")
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        self.tabs = {}
        self._create_dashboard_tab()
        self._create_bag_scanner_tab()
        self._create_auto_farm_config_tab()
        self._create_catch_pokemon_tab()
        self._create_target_pokemon_tab()
        self._create_calibrate_roi_tab()
        self._create_settings_tab()

        self._switch_tab("Dashboard")

    # ===================== SIDEBAR =====================
    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.root, width=220, corner_radius=0, fg_color=BG_SIDEBAR,
            border_width=0
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=80)
        brand_frame.pack(fill="x", pady=(15, 5))
        brand_frame.pack_propagate(False)

        brand = ctk.CTkLabel(
            brand_frame, text="⚡ POKEPRO",
            text_color=POKE_CYAN, font=("Segoe UI", 20, "bold")
        )
        brand.pack(expand=True)

        subtitle = ctk.CTkLabel(
            brand_frame, text="Auto Farm Tool",
            text_color=TEXT_SECONDARY, font=("Segoe UI", 10)
        )
        subtitle.pack()

        self._draw_divider(self.sidebar, pady=(5, 15))

        self.buttons = {}
        menu_items = [
            ("Dashboard",      "⬡", POKE_CYAN),
            ("Bag Scanner",    "◉", POKE_GREEN),
            ("Auto Farm Config", "◎", POKE_ORANGE),
            ("Bắt Pokemon",    "◐", POKE_YELLOW),
            ("Target Pokemon",  "🎯", POKE_RED),
            ("Calibrate ROI",  "◇", POKE_PINK),
            ("Settings",       "⚙", TEXT_SECONDARY),
        ]

        for name, icon, color in menu_items:
            self._create_menu_button(name, icon, color)

        ctk.CTkLabel(self.sidebar, text="", fg_color="transparent").pack(expand=True)

        self._draw_divider(self.sidebar, pady=(0, 10))

        status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_frame.pack(fill="x", padx=12, pady=(0, 15))

        dot_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        dot_frame.pack(fill="x", pady=2)

        self.status_dot = ctk.CTkLabel(
            dot_frame, text="●", text_color=POKE_RED,
            font=("Segoe UI", 14), width=20
        )
        self.status_dot.pack(side="left")

        self.status_label = ctk.CTkLabel(
            dot_frame, text="Stopped",
            text_color=TEXT_SECONDARY, font=("Segoe UI", 12, "bold")
        )
        self.status_label.pack(side="left", padx=(5, 0))

        self.mode_label = ctk.CTkLabel(
            status_frame, text="Mode: Auto Farm",
            text_color=TEXT_MUTED, font=("Segoe UI", 10)
        )
        self.mode_label.pack(fill="x", padx=(24, 0), pady=(2, 0))

    def _create_menu_button(self, name, icon, color):
        btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=52)
        btn_frame.pack(fill="x", padx=8, pady=3)
        btn_frame.pack_propagate(False)

        indicator = ctk.CTkLabel(btn_frame, text="", fg_color="transparent", width=4, height=32, corner_radius=2)
        indicator.pack(side="left", padx=(0, 10))
        indicator.configure(fg_color="transparent")

        icon_lbl = ctk.CTkLabel(btn_frame, text=icon, text_color=color, font=("Segoe UI", 18), width=28)
        icon_lbl.pack(side="left")

        text_lbl = ctk.CTkLabel(btn_frame, text=name, text_color=TEXT_SECONDARY, font=("Segoe UI", 14, "bold"))
        text_lbl.pack(side="left", padx=(10, 0), fill="x", expand=True)

        btn_frame.bind("<Button-1>", lambda e, n=name: self._switch_tab(n))
        icon_lbl.bind("<Button-1>", lambda e, n=name: self._switch_tab(n))
        text_lbl.bind("<Button-1>", lambda e, n=name: self._switch_tab(n))
        btn_frame.bind("<Enter>", lambda e, b=btn_frame: b.configure(fg_color="#181825") if b.cget("fg_color") != POKE_BLUE else None)
        btn_frame.bind("<Leave>", lambda e, b=btn_frame: b.configure(fg_color="transparent") if b.cget("fg_color") != POKE_BLUE else None)

        self.buttons[name] = {"frame": btn_frame, "indicator": indicator, "text": text_lbl, "color": color, "icon": icon_lbl}

    def _draw_divider(self, parent, pady=(10, 10)):
        ctk.CTkLabel(parent, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=20, pady=pady)

    # ===================== DASHBOARD TAB =====================
    def _create_dashboard_tab(self):
        frame = ctk.CTkFrame(self.content_container, fg_color=BG_DARK, corner_radius=0)
        self.tabs["Dashboard"] = frame

        scroll = ctk.CTkScrollableFrame(frame, fg_color=BG_DARK, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # === HEADER ===
        ctk.CTkLabel(
            scroll, text="Dashboard", text_color=TEXT_PRIMARY,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            scroll, text="Điều khiển tự động farm Pokemon", text_color=TEXT_SECONDARY,
            font=("Segoe UI", 11)
        ).pack(anchor="w", pady=(0, 16))

        # === STAT CARDS ===
        cards_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 16))

        stat_items = [
            ("⚔️ Battles", "0", POKE_RED),
            ("🎯 Pokemon", "0", POKE_GREEN),
            ("✨ XP Gained", "0", POKE_PURPLE),
            ("⏱ Runtime", "00:00:00", POKE_CYAN),
        ]
        self.stat_labels = {}
        for i, (label, val, color) in enumerate(stat_items):
            card = self._create_stat_card(cards_frame, label, val, color)
            card.pack(side="left", fill="x", expand=True, padx=(0 if i == 0 else 6, 6 if i < 3 else 0))

        # === CONTROL ===
        control_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        control_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            control_card, text="Farm Control", text_color=TEXT_PRIMARY,
            font=("Segoe UI", 14, "bold")
        ).pack(padx=18, pady=(14, 8))

        ctk.CTkLabel(control_card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        ctrl_row = ctk.CTkFrame(control_card, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(ctrl_row, text="Chế độ:", text_color=TEXT_SECONDARY, font=("Segoe UI", 11)).pack(side="left")

        self.mode_dropdown = ctk.CTkComboBox(
            ctrl_row, values=["Auto Farm", "Scan Pokemon", "Bắt Pokemon"],
            variable=self.selected_mode, state="readonly",
            width=160, fg_color=BG_DARK, text_color=TEXT_PRIMARY,
            button_color=POKE_BLUE, border_color=BORDER_SUBTLE,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
            dropdown_hover_color=BG_CARD_HOVER, font=("Segoe UI", 11)
        )
        self.mode_dropdown.pack(side="left", padx=(10, 20))

        self.start_btn = ctk.CTkButton(
            ctrl_row, text="▶ START", text_color="#ffffff",
            fg_color=POKE_GREEN, hover_color="#16a34a",
            height=38, font=("Segoe UI", 12, "bold"),
            command=self.start_farm, width=130, corner_radius=8
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            ctrl_row, text="■ STOP", text_color="#ffffff",
            fg_color=POKE_RED, hover_color="#dc2626",
            height=38, font=("Segoe UI", 12, "bold"),
            command=self.stop_farm, state="disabled",
            width=130, corner_radius=8
        )
        self.stop_btn.pack(side="left", padx=5)

        ctk.CTkLabel(ctrl_row, text="", fg_color=BORDER_SUBTLE, width=1, height=30).pack(side="left", padx=15)
        self.hotkey_display_lbl = ctk.CTkLabel(ctrl_row, text=self.config.get("hotkey", {}).get("stop_hotkey", "alt+f8"), text_color=TEXT_MUTED, font=("Segoe UI", 11, "italic"))
        self.hotkey_display_lbl.pack(side="left", padx=5)

        # === LOG ===
        log_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        log_card.pack(fill="both", expand=True)

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=18, pady=(14, 8))

        ctk.CTkLabel(log_header, text="📝 Live Log", text_color=TEXT_PRIMARY, font=("Segoe UI", 14, "bold")).pack(side="left")

        clear_btn = ctk.CTkButton(
            log_header, text="Xoá", text_color=TEXT_MUTED,
            fg_color="transparent", hover_color=BG_CARD_HOVER,
            font=("Segoe UI", 10), width=50, height=24,
            corner_radius=6, command=self._clear_log
        )
        clear_btn.pack(side="right")

        ctk.CTkLabel(log_card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        self.log_text = ctk.CTkTextbox(
            log_card, text_color=TEXT_PRIMARY, fg_color=BG_DARK,
            corner_radius=8, font=("Cascadia Code", 12), border_width=0
        )
        self.log_text.pack(fill="both", expand=True, padx=18, pady=14)
        self.log_text.configure(state="disabled")

        self.tabs["Dashboard"] = frame

    def _create_stat_card(self, parent, label, value, color):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1, height=100)
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="", fg_color=color, height=3, corner_radius=2).pack(fill="x")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=16, pady=16)

        ctk.CTkLabel(content, text=label, text_color=TEXT_SECONDARY, font=("Segoe UI", 11)).pack(anchor="w")

        val_lbl = ctk.CTkLabel(content, text=value, text_color=color, font=("Segoe UI", 22, "bold"))
        val_lbl.pack(anchor="w", pady=(2, 0))
        self.stat_labels[label] = val_lbl
        return card

    # ===================== BAG SCANNER TAB =====================
    def _create_bag_scanner_tab(self):
        try:
            from src.team_builder.bag_scanner_tab import BagScannerTab

            frame = ctk.CTkFrame(self.content_container, fg_color=BG_DARK, corner_radius=0)
            self.tabs["Bag Scanner"] = frame

            ctk.CTkLabel(frame, text="Bag Scanner", text_color=TEXT_PRIMARY,
                         font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
            ctk.CTkLabel(frame, text="Quét tất cả Pokemon trong túi", text_color=TEXT_SECONDARY,
                         font=("Segoe UI", 11)).pack(anchor="w", padx=16, pady=(0, 12))

            embedded = tk.Frame(frame, bg=BG_CARD)
            embedded.pack(fill="both", expand=True, padx=16, pady=(0, 16))

            BagScannerTab(embedded, self.config).frame.pack(fill="both", expand=True)

        except Exception as e:
            self._error_tab("Bag Scanner", "🎒", str(e))

    # ===================== AUTO FARM CONFIG TAB =====================
    def _create_auto_farm_config_tab(self):
        try:
            from src.team_builder.auto_farm_config_tab import AutoFarmConfigTab

            frame = ctk.CTkFrame(self.content_container, fg_color=BG_DARK, corner_radius=0)
            self.tabs["Auto Farm Config"] = frame

            ctk.CTkLabel(frame, text="Auto Farm Config", text_color=TEXT_PRIMARY,
                         font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
            ctk.CTkLabel(frame, text="Chọn 6 Pokemon để auto farm", text_color=TEXT_SECONDARY,
                         font=("Segoe UI", 11)).pack(anchor="w", padx=16, pady=(0, 12))

            embedded = tk.Frame(frame, bg=BG_CARD)
            embedded.pack(fill="both", expand=True, padx=16, pady=(0, 16))

            AutoFarmConfigTab(embedded, self.config).frame.pack(fill="both", expand=True)

        except Exception as e:
            self._error_tab("Auto Farm Config", "⚙️🎯", str(e))

    # ===================== CATCH POKEMON TAB =====================
    def _create_catch_pokemon_tab(self):
        frame = ctk.CTkFrame(self.content_container, fg_color=BG_DARK, corner_radius=0)
        self.tabs["Bắt Pokemon"] = frame

        saved = self.config.get("catch", {})

        scroll = ctk.CTkScrollableFrame(frame, fg_color=BG_DARK, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(scroll, text="Bắt Pokemon Tự Động", text_color=TEXT_PRIMARY,
                     font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(scroll, text="Tự động dùng False Swipe → Spore → Ball",
                     text_color=TEXT_SECONDARY, font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 20))

        # === Pokémon mục tiêu (load từ target_pokemon.json + team_party.json) ===
        targets = self._load_target_names()

        target_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        target_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(target_card, text="🎯 Pokémon Mục Tiêu", text_color=POKE_YELLOW,
                     font=("Segoe UI", 14, "bold")).pack(padx=18, pady=(14, 4))
        ctk.CTkLabel(target_card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        target_body = ctk.CTkFrame(target_card, fg_color="transparent")
        target_body.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(target_body, text="Bắt:", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(side="left")
        self.catch_target_var = ctk.StringVar(value="Any (bắt tất cả)")
        self.catch_target_combo = ctk.CTkComboBox(
            target_body, width=240, variable=self.catch_target_var, state="readonly",
            values=["Any (bắt tất cả)"] + targets,
            fg_color=BG_DARK, text_color=TEXT_PRIMARY, button_color=POKE_BLUE,
            border_color=BORDER_SUBTLE, dropdown_fg_color=BG_CARD,
            dropdown_text_color=TEXT_PRIMARY, dropdown_hover_color=BG_CARD_HOVER,
            font=("Segoe UI", 11)
        )
        self.catch_target_combo.pack(side="left", padx=(10, 0))

        ctk.CTkCheckBox(
            target_body, text="Chỉ bắt target trong target_pokemon.json",
            variable=tk.BooleanVar(value=True), text_color=TEXT_SECONDARY,
            font=("Segoe UI", 10), fg_color=POKE_BLUE, hover_color=POKE_BLUE,
            checkbox_width=16, checkbox_height=16
        ).pack(side="left", padx=(20, 0))

        # === Breloom Slot ===
        breloom_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        breloom_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(breloom_card, text="🍄 Pokemon False Swipe + Sleep", text_color=POKE_GREEN,
                     font=("Segoe UI", 14, "bold")).pack(padx=18, pady=(14, 4))
        ctk.CTkLabel(breloom_card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        breloom_body = ctk.CTkFrame(breloom_card, fg_color="transparent")
        breloom_body.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(breloom_body, text="Pokemon:", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(side="left")

        party_names = self._load_party_names()
        self.breloom_name_var = ctk.StringVar(value="Breloom")
        ctk.CTkComboBox(
            breloom_body, width=180, variable=self.breloom_name_var, state="readonly",
            values=party_names if party_names else ["Breloom"],
            fg_color=BG_DARK, text_color=TEXT_PRIMARY, button_color=POKE_BLUE,
            border_color=BORDER_SUBTLE, dropdown_fg_color=BG_CARD,
            dropdown_text_color=TEXT_PRIMARY, dropdown_hover_color=BG_CARD_HOVER,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(breloom_body, text="Slot trong team:", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(side="left", padx=(20, 0))
        self.breloom_slot_var = tk.StringVar(value="Auto (tự tìm)")
        ctk.CTkComboBox(
            breloom_body, width=150, variable=self.breloom_slot_var, state="readonly",
            values=["Auto (tự tìm)", "Slot 1", "Slot 2", "Slot 3", "Slot 4", "Slot 5", "Slot 6"],
            fg_color=BG_DARK, text_color=TEXT_PRIMARY, button_color=POKE_BLUE,
            border_color=BORDER_SUBTLE, dropdown_fg_color=BG_CARD,
            dropdown_text_color=TEXT_PRIMARY, dropdown_hover_color=BG_CARD_HOVER,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=(10, 0))

        # === Kỹ năng ===
        skill_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        skill_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(skill_card, text="⚔️ Chiến Thuật Ra Chiêu", text_color=POKE_CYAN,
                     font=("Segoe UI", 14, "bold")).pack(padx=18, pady=(14, 4))
        ctk.CTkLabel(skill_card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        skill_body = ctk.CTkFrame(skill_card, fg_color="transparent")
        skill_body.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(skill_body, text="Thứ tự:", text_color=TEXT_PRIMARY,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        steps = [
            "1. Swap → Pokemon False Swipe (nếu chưa ra)",
            "2. Spore (gây ngủ) nếu địch còn thức",
            "3. False Swipe nếu HP địch cao (để lại 1 HP)",
            "4. Spore lại nếu địch tỉnh",
            "5. Items → Ball nếu HP = 1 + ngủ",
        ]
        for s in steps:
            ctk.CTkLabel(skill_body, text=s, text_color=TEXT_SECONDARY,
                         font=("Segoe UI", 11), anchor="w").pack(anchor="w", pady=1)

        # === Ball ===
        ball_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        ball_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(ball_card, text="🔴 Chiến Thuật Ball", text_color=POKE_PINK,
                     font=("Segoe UI", 14, "bold")).pack(padx=18, pady=(14, 4))
        ctk.CTkLabel(ball_card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        ball_body = ctk.CTkFrame(ball_card, fg_color="transparent")
        ball_body.pack(fill="x", padx=18, pady=14)

        self.ball_priority_var = tk.StringVar(value="Poke → Great → Ultra")
        ctk.CTkLabel(ball_body, text="Ưu tiên Ball:", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(side="left")
        ctk.CTkComboBox(
            ball_body, width=200, variable=self.ball_priority_var, state="readonly",
            values=["Poke → Great → Ultra", "Great → Ultra → Poke", "Ultra → Great → Poke", "Master Ball"],
            fg_color=BG_DARK, text_color=TEXT_PRIMARY, button_color=POKE_BLUE,
            border_color=BORDER_SUBTLE, dropdown_fg_color=BG_CARD,
            dropdown_text_color=TEXT_PRIMARY, dropdown_hover_color=BG_CARD_HOVER,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(ball_body, text="Số Ball tối đa:", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(side="left", padx=(20, 0))
        self.max_balls_var = ctk.StringVar(value="999")
        ctk.CTkEntry(
            ball_body, width=80, textvariable=self.max_balls_var,
            fg_color=BG_DARK, text_color=TEXT_PRIMARY, border_color=BORDER_SUBTLE,
            font=("Segoe UI", 11), justify="center"
        ).pack(side="left", padx=(8, 0))

        # === HP Detection ===
        hp_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        hp_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(hp_card, text="❤️ Phát Hiện HP Địch", text_color=POKE_RED,
                     font=("Segoe UI", 14, "bold")).pack(padx=18, pady=(14, 4))
        ctk.CTkLabel(hp_card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        hp_body = ctk.CTkFrame(hp_card, fg_color="transparent")
        hp_body.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(hp_body, text="Phương pháp:", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(side="left")
        self.hp_detect_var = ctk.StringVar(value="Màu thanh HP (xanh → đỏ)")
        ctk.CTkComboBox(
            hp_body, width=220, variable=self.hp_detect_var, state="readonly",
            values=["Màu thanh HP (xanh → đỏ)", "OCR chữ HP"],
            fg_color=BG_DARK, text_color=TEXT_PRIMARY, button_color=POKE_BLUE,
            border_color=BORDER_SUBTLE, dropdown_fg_color=BG_CARD,
            dropdown_text_color=TEXT_PRIMARY, dropdown_hover_color=BG_CARD_HOVER,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=(10, 0))

        # === Điều kiện dừng ===
        stop_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        stop_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(stop_card, text="⏹ Điều Kiện Dừng", text_color=POKE_ORANGE,
                     font=("Segoe UI", 14, "bold")).pack(padx=18, pady=(14, 4))
        ctk.CTkLabel(stop_card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        stop_body = ctk.CTkFrame(stop_card, fg_color="transparent")
        stop_body.pack(fill="x", padx=18, pady=14)

        self.stop_on_shiny_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            stop_body, text="Dừng khi gặp Shiny", variable=self.stop_on_shiny_var,
            text_color=TEXT_PRIMARY, font=("Segoe UI", 12), fg_color=POKE_BLUE,
            hover_color=POKE_BLUE, checkbox_width=20, checkbox_height=20
        ).pack(anchor="w", pady=4)

        self.stop_on_catch_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            stop_body, text="Dừng sau khi bắt được 1 Pokemon",
            variable=self.stop_on_catch_var,
            text_color=TEXT_PRIMARY, font=("Segoe UI", 12), fg_color=POKE_BLUE,
            hover_color=POKE_BLUE, checkbox_width=20, checkbox_height=20
        ).pack(anchor="w", pady=4)

        self.stop_on_full_party_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            stop_body, text="Dừng khi team đầy (6 Pokemon)",
            variable=self.stop_on_full_party_var,
            text_color=TEXT_PRIMARY, font=("Segoe UI", 12), fg_color=POKE_BLUE,
            hover_color=POKE_BLUE, checkbox_width=20, checkbox_height=20
        ).pack(anchor="w", pady=4)

        # === Nút Lưu ===
        ctk.CTkButton(
            scroll, text="💾 Lưu Cấu Hình Bắt Pokemon",
            fg_color=POKE_GREEN, hover_color="#16a34a",
            text_color="#ffffff", font=("Segoe UI", 13, "bold"),
            height=42, corner_radius=8, command=self._save_catch_config
        ).pack(pady=(16, 4), fill="x")

        ctk.CTkLabel(
            scroll, text="Lưu vào tool_config.json — sẵn sàng dùng từ Dashboard mode Bắt Pokemon",
            text_color=TEXT_MUTED, font=("Segoe UI", 10)
        ).pack(anchor="center", pady=(0, 16))

        # Load saved values
        if saved:
            self.catch_target_var.set(saved.get("target", "Any (bắt tất cả)"))
            self.breloom_name_var.set(saved.get("breloom_name", "Breloom"))
            self.breloom_slot_var.set(saved.get("breloom_slot", "Auto (tự tìm)"))
            self.ball_priority_var.set(saved.get("ball_priority", "Poke → Great → Ultra"))
            self.max_balls_var.set(str(saved.get("max_balls", 999)))
            self.hp_detect_var.set(saved.get("hp_detect_method", "Màu thanh HP (xanh → đỏ)"))
            self.stop_on_shiny_var.set(saved.get("stop_on_shiny", True))
            self.stop_on_catch_var.set(saved.get("stop_on_catch", False))
            self.stop_on_full_party_var.set(saved.get("stop_on_full_party", True))

    def _save_catch_config(self):
        catch_cfg = {
            "target": self.catch_target_var.get(),
            "breloom_name": self.breloom_name_var.get(),
            "breloom_slot": self.breloom_slot_var.get(),
            "ball_priority": self.ball_priority_var.get(),
            "max_balls": int(self.max_balls_var.get() or "999"),
            "hp_detect_method": self.hp_detect_var.get(),
            "stop_on_shiny": self.stop_on_shiny_var.get(),
            "stop_on_catch": self.stop_on_catch_var.get(),
            "stop_on_full_party": self.stop_on_full_party_var.get(),
        }
        self.config["catch"] = catch_cfg
        self._save_config()
        self._add_log("✅ Đã lưu cấu hình Bắt Pokemon!")
        messagebox.showinfo("Thành công", "Đã lưu cấu hình Bắt Pokemon!")

    def _load_target_names(self):
        try:
            with open(TARGETS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            names = set()
            for entry in data if isinstance(data, list) else data.values():
                if isinstance(entry, dict):
                    n = entry.get("pokemonname", "") or entry.get("name", "")
                    if n:
                        names.add(n)
                elif isinstance(entry, str):
                    names.add(entry)
            return sorted(names)
        except:
            return []

    def _load_party_names(self):
        try:
            with open(TEAM_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            names = []
            for slot in data if isinstance(data, list) else data.values():
                if isinstance(slot, dict):
                    n = slot.get("name", "")
                    if n:
                        names.append(f"{n}")
            return names
        except:
            return []

    # ===================== TARGET POKEMON TAB =====================
    def _create_target_pokemon_tab(self):
        try:
            from src.team_builder.target_pokemon_tab import TargetPokemonTab

            frame = ctk.CTkFrame(self.content_container, fg_color=BG_DARK, corner_radius=0)
            self.tabs["Target Pokemon"] = frame

            ctk.CTkLabel(frame, text="Target Pokemon", text_color=TEXT_PRIMARY,
                         font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
            ctk.CTkLabel(frame, text="Danh sách Pokemon và Ability cần bắt", text_color=TEXT_SECONDARY,
                         font=("Segoe UI", 11)).pack(anchor="w", padx=16, pady=(0, 12))

            embedded = tk.Frame(frame, bg=BG_CARD)
            embedded.pack(fill="both", expand=True, padx=16, pady=(0, 16))

            self.target_pokemon_tab_obj = TargetPokemonTab(embedded, self.config)
            self.target_pokemon_tab_obj.frame.pack(fill="both", expand=True)

        except Exception as e:
            self._error_tab("Target Pokemon", "🎯", str(e))

    # ===================== CALIBRATE ROI TAB =====================
    def _create_calibrate_roi_tab(self):
        frame = ctk.CTkFrame(self.content_container, fg_color=BG_DARK, corner_radius=0)
        self.tabs["Calibrate ROI"] = frame

        ctk.CTkLabel(frame, text="Calibrate ROI", text_color=TEXT_PRIMARY,
                     font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(frame, text="Kéo thả để điều chỉnh vùng nhận diện", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(anchor="w", padx=16, pady=(0, 12))

        embedded = tk.Frame(frame, bg=BG_CARD)
        embedded.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        try:
            from src.tools.ui_main import TabbedToolUI
            TabbedToolUI(parent=embedded)
        except Exception as e:
            ctk.CTkLabel(embedded, text=f"⚠ Không tải được Calibrate UI:\n{e}\n\nChạy Menu 4 từ CMD để dùng.",
                         text_color=POKE_RED, font=("Segoe UI", 12)).pack(expand=True)

    # ===================== SETTINGS TAB (FORM TIẾNG VIỆT) =====================
    def _create_settings_tab(self):
        frame = ctk.CTkFrame(self.content_container, fg_color=BG_DARK, corner_radius=0)
        self.tabs["Settings"] = frame

        scroll = ctk.CTkScrollableFrame(frame, fg_color=BG_DARK, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(scroll, text="Cài Đặt", text_color=TEXT_PRIMARY,
                     font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(scroll, text="Chỉnh sửa cấu hình tool — lưu tự động", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 20))

        self._settings_widgets = {}

        # ===== CÀI ĐẶT CHUNG =====
        self._settings_section(scroll, "Cài Đặt Chung", [
            ("debug.save_failed_ocr", "Lưu ảnh lỗi OCR", "toggle", True),
            ("ocr.tesseract_cmd", "Đường dẫn Tesseract", "text", "C:/Program Files/Tesseract-OCR/tesseract.exe"),
        ])

        # ===== HOTKEY =====
        self._settings_hotkey_section(scroll)

        # ===== THỜI GIAN =====
        self._settings_section(scroll, "Thời Gian (giây)", [
            ("timing.scan_interval_seconds", "Khoảng cách quét", "number", 3.0),
            ("timing.ability_wait_seconds", "Chờ dùng kỹ năng", "number", 3.5),
            ("timing.ability_retry_seconds", "Chờ hồi chiêu", "number", 1.5),
            ("timing.ability_retry_count", "Số lần thử kỹ năng lại", "number", 2),
            ("timing.after_run_wait_seconds", "Chờ sau khi chạy", "number", 4.0),
            ("timing.run_exit_timeout_seconds", "Thời gian chờ thoát", "number", 8.0),
            ("timing.battle_anim_wait_seconds", "Chờ hiệu ứng đánh nhau", "number", 7.5),
            ("timing.after_swap_wait_seconds", "Chờ sau khi swap", "number", 8.0),
            ("timing.move_hold_min_seconds", "Giữ phím tối thiểu", "number", 0.18),
            ("timing.move_hold_max_seconds", "Giữ phím tối đa", "number", 0.42),
        ])

        # ===== NHẬN DIỆN =====
        self._settings_section(scroll, "Nhận Diện (Template Matching)", [
            ("template_matching.run_button_threshold", "Ngưỡng nút Run", "slider", 0.58),
            ("template_matching.fight_button_threshold", "Ngưỡng nút Fight", "slider", 0.55),
            ("template_matching.pokemon_button_threshold", "Ngưỡng nút Pokemon", "slider", 0.5),
        ])

        # ===== CHUỘT =====
        self._settings_section(scroll, "Chuột", [
            ("mouse.click_repeat", "Số lần click lại", "number", 2),
            ("mouse.click_gap_seconds", "Khoảng cách giữa các click", "number", 0.25),
            ("mouse.mouse_down_seconds", "Thời gian giữ chuột", "number", 0.12),
        ])

        # ===== FARM =====
        self._settings_section(scroll, "Farm", [
            ("farm.stab_multiplier", "STAB Multiplier", "number", 1.5),
            ("farm.use_zero_effectiveness", "Dùng kỹ năng 0 hiệu quả", "toggle", False),
        ])

        # Save button
        ctk.CTkButton(
            scroll, text="💾 Lưu Tất Cả Cài Đặt",
            fg_color=POKE_GREEN, hover_color="#16a34a",
            text_color="#ffffff", font=("Segoe UI", 13, "bold"),
            height=40, corner_radius=8, command=self._save_all_settings
        ).pack(pady=(8, 4), fill="x")

        ctk.CTkLabel(
            scroll, text="Cài đặt sẽ được lưu vào tool_config.json", text_color=TEXT_MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="center", pady=(0, 16))

    def _settings_hotkey_section(self, parent):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(card, text="⌨ Phím Tắt", text_color=TEXT_PRIMARY,
                     font=("Segoe UI", 14, "bold")).pack(padx=18, pady=(14, 4))
        ctk.CTkLabel(card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(body, text="Phím dừng tool:", text_color=TEXT_SECONDARY,
                     font=("Segoe UI", 11)).pack(side="left")

        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", {}).get("stop_hotkey", "alt+f8"))
        self.hotkey_entry = ctk.CTkEntry(
            body, width=180, textvariable=self.hotkey_var,
            fg_color=BG_DARK, text_color=TEXT_PRIMARY,
            border_color=BORDER_SUBTLE, font=("Segoe UI", 12, "bold"), justify="center"
        )
        self.hotkey_entry.pack(side="left", padx=(10, 10))

        def apply_hotkey():
            new_key = self.hotkey_var.get().strip()
            if not new_key:
                return
            self.config.setdefault("hotkey", {})["stop_hotkey"] = new_key
            self._save_config()
            try:
                keyboard.remove_hotkey(new_key)
            except:
                pass
            self._register_hotkey()
            if hasattr(self, 'hotkey_display_lbl'):
                self.hotkey_display_lbl.configure(text=new_key)
            self._add_log(f"🎮 Hotkey changed to {new_key}")
            messagebox.showinfo("Thành công", f"Đã đổi hotkey thành: {new_key}")

        ctk.CTkButton(
            body, text="Áp dụng", command=apply_hotkey,
            fg_color=POKE_BLUE, hover_color="#2563eb",
            text_color="#ffffff", font=("Segoe UI", 11, "bold"),
            height=30, width=80, corner_radius=6
        ).pack(side="left")

        ctk.CTkLabel(
            body, text="VD: alt+f8, ctrl+shift+s, f12",
            text_color=TEXT_MUTED, font=("Segoe UI", 10)
        ).pack(anchor="w", padx=(0, 0), pady=(8, 0))

    def _settings_section(self, parent, title, fields):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(card, text=title, text_color=TEXT_PRIMARY,
                     font=("Segoe UI", 14, "bold")).pack(padx=18, pady=(14, 4))
        ctk.CTkLabel(card, text="", fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=18)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=6)

        for key, label, ctrl_type, default in fields:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(row, text=label, text_color=TEXT_SECONDARY,
                         font=("Segoe UI", 11), width=220, anchor="w").pack(side="left")

            self._settings_widgets[key] = self._create_setting_control(row, key, ctrl_type, default)

    def _create_setting_control(self, parent, key, ctrl_type, default):
        # Navigate nested key like "timing.scan_interval_seconds"
        parts = key.split(".")
        val = self.config
        try:
            for p in parts:
                val = val[p]
        except (KeyError, TypeError):
            val = default

        if ctrl_type == "toggle":
            var = tk.BooleanVar(value=bool(val))
            chk = ctk.CTkCheckBox(
                parent, text="Bật" if var.get() else "Tắt",
                variable=var, text_color=TEXT_PRIMARY, font=("Segoe UI", 10),
                fg_color=POKE_BLUE, hover_color=POKE_BLUE,
                checkbox_width=22, checkbox_height=22,
                command=lambda k=key, v=var: self._on_toggle(k, v)
            )
            chk.pack(side="left")
            self._on_toggle(key, var)
            return var

        elif ctrl_type == "number":
            var = tk.StringVar(value=str(val))
            entry = ctk.CTkEntry(
                parent, width=100, textvariable=var,
                fg_color=BG_DARK, text_color=TEXT_PRIMARY,
                border_color=BORDER_SUBTLE, font=("Segoe UI", 11), justify="center"
            )
            entry.pack(side="left")
            entry.bind("<KeyRelease>", lambda e, k=key, v=var: self._on_number_change(k, v))
            return var

        elif ctrl_type == "slider":
            var = tk.DoubleVar(value=float(val))
            slider = ctk.CTkSlider(
                parent, from_=0.0, to=1.0, number_of_steps=100,
                variable=var, fg_color=BG_DARK, progress_color=POKE_BLUE,
                button_color=POKE_BLUE, button_hover_color="#2563eb",
                width=180, command=lambda v, k=key: self._on_slider_change(k, v)
            )
            slider.pack(side="left")
            val_lbl = ctk.CTkLabel(parent, text=f"{float(val):.2f}", text_color=POKE_CYAN,
                                   font=("Segoe UI", 11, "bold"), width=50)
            val_lbl.pack(side="left", padx=(8, 0))
            # Update label on move
            slider.configure(command=lambda v, k=key, l=val_lbl: (l.configure(text=f"{float(v):.2f}"), self._on_slider_change(k, v)))
            return var

        else:  # text
            var = tk.StringVar(value=str(val))
            entry = ctk.CTkEntry(
                parent, width=300, textvariable=var,
                fg_color=BG_DARK, text_color=TEXT_PRIMARY,
                border_color=BORDER_SUBTLE, font=("Segoe UI", 11)
            )
            entry.pack(side="left", fill="x", expand=True)
            entry.bind("<KeyRelease>", lambda e, k=key, v=var: self._on_text_change(k, v))
            return var

    def _on_toggle(self, key, var):
        parts = key.split(".")
        d = self.config
        for p in parts[:-1]:
            d = d[p]
        d[parts[-1]] = var.get()
        # Update label text
        self._add_log(f"⚙ {key}: {'Bật' if var.get() else 'Tắt'}")

    def _on_number_change(self, key, var):
        try:
            parts = key.split(".")
            d = self.config
            for p in parts[:-1]:
                d = d[p]
            raw = var.get().strip()
            if "." in raw:
                d[parts[-1]] = float(raw)
            else:
                d[parts[-1]] = int(raw)
        except ValueError:
            pass

    def _on_slider_change(self, key, val):
        parts = key.split(".")
        d = self.config
        for p in parts[:-1]:
            d = d[p]
        d[parts[-1]] = float(val)

    def _on_text_change(self, key, var):
        parts = key.split(".")
        d = self.config
        for p in parts[:-1]:
            d = d[p]
        d[parts[-1]] = var.get()

    def _save_all_settings(self):
        try:
            self._save_config()
            self._add_log("✅ Đã lưu tất cả cài đặt!")
            messagebox.showinfo("Thành công", "Đã lưu cài đặt vào tool_config.json")
        except Exception as e:
            self._add_log(f"❌ Lỗi lưu: {e}")
            messagebox.showerror("Lỗi", str(e))

    # ===================== ERROR HELPER =====================
    def _error_tab(self, name, icon, err_msg):
        frame = ctk.CTkFrame(self.content_container, fg_color=BG_DARK, corner_radius=0)
        self.tabs[name] = frame

        scroll = ctk.CTkScrollableFrame(frame, fg_color=BG_DARK, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(scroll, text=f"{icon} {name}", text_color=TEXT_PRIMARY,
                     font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(scroll, text=f"⚠ {err_msg}", text_color=POKE_ORANGE,
                     font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 16))

        ctk.CTkLabel(
            scroll,
            text="Module này chưa được cài đặt hoặc bị lỗi.\n"
                 "Hãy kiểm tra dependencies hoặc chạy từ CMD menu.",
            text_color=TEXT_MUTED, font=("Segoe UI", 11), justify="left"
        ).pack(anchor="w")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._add_log("🧹 Đã xoá log")

    # ===================== TAB SWITCHING =====================
    def _switch_tab(self, tab_name):
        if tab_name == "Bắt Pokemon" and hasattr(self, "catch_target_combo"):
            updated_targets = self._load_target_names()
            self.catch_target_combo.configure(values=["Any (bắt tất cả)"] + updated_targets)
        elif tab_name == "Target Pokemon" and hasattr(self, "target_pokemon_tab_obj"):
            try:
                self.target_pokemon_tab_obj._load_targets()
                self.target_pokemon_tab_obj._update_list_display()
            except Exception as e:
                print(f"Error refreshing Target Pokemon tab: {e}")

        for frame in self.tabs.values():
            frame.grid_remove()
        self.tabs[tab_name].grid(row=0, column=0, sticky="nsew")

        for btn_name, btn_data in self.buttons.items():
            f = btn_data["frame"]
            f.configure(fg_color=BG_CARD_HOVER if btn_name == tab_name else "transparent")
            btn_data["indicator"].configure(fg_color=btn_data["color"] if btn_name == tab_name else "transparent")
            btn_data["text"].configure(text_color=TEXT_PRIMARY if btn_name == tab_name else TEXT_SECONDARY)

    # ===================== FARM CONTROL =====================
    def start_farm(self):
        if self.worker_running:
            return
        mode = self.selected_mode.get()
        self.worker_running = True
        self.stop_event.clear()
        self.start_btn.configure(state="disabled")
        self.mode_dropdown.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="Running", text_color=POKE_GREEN)
        self.status_dot.configure(text_color=POKE_GREEN)
        self._add_log(f"✅ {mode} started!")
        hk = self.config.get("hotkey", {}).get("stop_hotkey", "alt+f8")
        self._add_log(f"🎮 Nhấn {hk} để dừng.")
        self.worker_thread = threading.Thread(target=self._farm_worker, daemon=True)
        self.worker_thread.start()

    def stop_farm(self):
        self.worker_running = False
        self.stop_event.set()
        self.start_btn.configure(state="normal")
        self.mode_dropdown.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="Stopped", text_color=TEXT_SECONDARY)
        self.status_dot.configure(text_color=POKE_RED)
        self._add_log("⏹ Đã dừng tool!")

    def _farm_worker(self):
        try:
            from src.farm.farm_gui_adapter import run_farm_mode_with_gui_logging
            run_farm_mode_with_gui_logging(self.config, self.selected_mode.get(), self._add_log, self.stop_event)
        except Exception as e:
            self._add_log(f"❌ Lỗi: {str(e)}")
            import traceback
            self._add_log(traceback.format_exc())
        finally:
            self.worker_running = False
            self.start_btn.configure(state="normal")
            self.mode_dropdown.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.status_label.configure(text="Stopped", text_color=TEXT_SECONDARY)
            self.status_dot.configure(text_color=POKE_RED)

    # ===================== LOGGING =====================
    def _add_log(self, message):
        self.log_queue.put(message)

    def _start_log_listener(self):
        def update_log():
            try:
                while True:
                    msg = self.log_queue.get_nowait()
                    ts = datetime.now().strftime("%H:%M:%S")

                    self.log_text.configure(state="normal")

                    tag = None
                    if msg.startswith("✅") or msg.startswith("✔"):
                        tag = "success"
                    elif msg.startswith("❌") or msg.startswith("⚠") or msg.startswith("✖"):
                        tag = "error"
                    elif msg.startswith("⏹") or msg.startswith("🔴") or msg.startswith("✋"):
                        tag = "stop"
                    elif msg.startswith("🎮") or msg.startswith("▶") or msg.startswith("⚡"):
                        tag = "action"
                    elif msg.startswith("🧹"):
                        tag = "clear"

                    self.log_text.insert("end", f"[{ts}] ", "timestamp")
                    self.log_text.insert("end", f"{msg}\n", tag)
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")

                    try:
                        FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                        with FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as f:
                            f.write(f"[{ts}] {msg}\n")
                    except:
                        pass
            except queue.Empty:
                pass
            self.root.after(100, update_log)

        self.log_text.tag_config("timestamp", foreground=TEXT_MUTED)
        self.log_text.tag_config("success", foreground=POKE_GREEN)
        self.log_text.tag_config("error", foreground=POKE_RED)
        self.log_text.tag_config("stop", foreground=POKE_ORANGE)
        self.log_text.tag_config("action", foreground=POKE_CYAN)
        self.log_text.tag_config("clear", foreground=POKE_YELLOW)
        self.root.after(100, update_log)

    # ===================== HOTKEY =====================
    def _register_hotkey(self):
        hotkey_str = self.config.get("hotkey", {}).get("stop_hotkey", "alt+f8")

        def toggle():
            if self.worker_running:
                self.stop_farm()
            else:
                self.start_farm()
        try:
            keyboard.add_hotkey(hotkey_str, toggle)
            self._add_log(f"🎮 {hotkey_str} hotkey registered!")
            self.hotkey_registered = True
        except Exception as e:
            self._add_log(f"⚠ Không đăng ký được {hotkey_str}: {e}")

    def run(self):
        def on_close():
            if self.worker_running:
                self.stop_farm()
            try:
                keyboard.unhook_all()
            except:
                pass
            try:
                self.root.destroy()
            except:
                pass
            import os
            os._exit(0)
        self.root.protocol("WM_DELETE_WINDOW", on_close)
        self.root.mainloop()


def main():
    root = ctk.CTk()
    app = ModernPokemonUI(root)
    app.run()


if __name__ == "__main__":
    main()
