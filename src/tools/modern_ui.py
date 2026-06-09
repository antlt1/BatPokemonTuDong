"""
modern_ui.py - GUI chính dùng CustomTkinter
Giao diện hiện đại với Dark Mode, sidebar navigation, tabs

Cấu trúc:
  - Sidebar (trái): Dashboard, Team Builder, Calibrate ROI, Settings
  - Main Content (phải): Nội dung tab hiện tại
  - Threading: Background worker chạy farm_battle.py
  - Hotkey F8: Start/Stop auto farm
"""

import customtkinter as ctk
import tkinter as tk
import json
import threading
import queue
import time
import keyboard
from pathlib import Path
from datetime import datetime
import sys

# Import modules khác
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
TARGETS_PATH = ROOT / "src" / "config" / "target_pokemon.json"
TEAM_PATH = ROOT / "src" / "config" / "team_party.json"
FEEDBACK_LOG_PATH = ROOT / "src" / "runtime" / "feedback_log.txt"

# ======================= Theme Settings =======================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ModernPokemonUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎮 PokemonPRO Auto Tool - v2.0")
        self.root.geometry("1600x900")
        self.root.resizable(True, True)
        
        # Load config
        self.config = self._load_config()
        
        # Threading
        self.worker_thread = None
        self.worker_running = False
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.selected_mode = tk.StringVar(value="Auto Farm")
        
        # Hotkey
        self.hotkey_registered = False
        
        # Setup UI
        self._setup_ui()
        self._register_hotkey()
        self._start_log_listener()
        
    def _load_config(self):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def _setup_ui(self):
        """Tạo giao diện chính: Sidebar + Main Content"""
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # ===== SIDEBAR (Trái) =====
        self.sidebar = ctk.CTkFrame(self.root, width=200, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_propagate(False)
        
        # Header sidebar
        header = ctk.CTkLabel(
            self.sidebar,
            text="🎮 PokemonPRO",
            text_color="#00bfff",
            font=("Arial", 16, "bold")
        )
        header.pack(pady=15, padx=10)
        
        # Separator
        ctk.CTkLabel(self.sidebar, text="", fg_color="#333333", height=2).pack(fill="x", pady=5)
        
        # Menu buttons
        self.buttons = {}
        menu_items = [
            ("Dashboard", "📊"),
            ("Team Builder", "👥"),
            ("Bag Scanner", "🎒"),
            ("Auto Farm Config", "⚙️🎯"),
            ("Calibrate ROI", "🎯"),
            ("Settings", "⚙️")
        ]
        
        for name, emoji in menu_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{emoji} {name}",
                text_color="#ffffff",
                fg_color="#2a2a2a",
                hover_color="#3a3a3a",
                corner_radius=8,
                height=50,
                font=("Arial", 12, "bold"),
                command=lambda n=name: self._switch_tab(n)
            )
            btn.pack(pady=8, padx=10, fill="x")
            self.buttons[name] = btn
        
        # Separator
        ctk.CTkLabel(self.sidebar, text="", fg_color="#333333", height=2).pack(fill="x", pady=15)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="🔴 Stopped",
            text_color="#ff6b6b",
            font=("Arial", 11, "bold")
        )
        self.status_label.pack(pady=10, padx=10)
        
        # Mode label
        self.mode_label = ctk.CTkLabel(
            self.sidebar,
            text="Mode: Auto Farm",
            text_color="#4ecdc4",
            font=("Arial", 10)
        )
        self.mode_label.pack(pady=5, padx=10)
        
        # ===== MAIN CONTENT (Phải) =====
        self.main_frame = ctk.CTkFrame(self.root, fg_color="#0d0d0d")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Content container (dùng để switch tab)
        self.content_container = ctk.CTkFrame(self.main_frame, fg_color="#0d0d0d")
        self.content_container.grid(row=0, column=0, sticky="nsew")
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)
        
        # Tabs
        self.tabs = {}
        self._create_dashboard_tab()
        self._create_team_builder_tab()
        self._create_bag_scanner_tab()
        self._create_auto_farm_config_tab()
        self._create_calibrate_roi_tab()
        self._create_settings_tab()
        
        # Show dashboard by default
        self._switch_tab("Dashboard")
    
    def _create_dashboard_tab(self):
        """Tab Dashboard: Start/Stop, hiển thị mode, log panel"""
        frame = ctk.CTkFrame(self.content_container, fg_color="#0d0d0d")
        self.tabs["Dashboard"] = frame
        
        # Header
        header = ctk.CTkLabel(
            frame,
            text="📊 Dashboard - Auto Farm Control",
            text_color="#00bfff",
            font=("Arial", 18, "bold")
        )
        header.pack(pady=15, padx=10)
        
        # Control panel
        control_frame = ctk.CTkFrame(frame, fg_color="#1a1a1a", corner_radius=10)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Mode info
        self.mode_label = ctk.CTkLabel(
            control_frame,
            text="Mode: None\nHotkey: Alt+F8 to Start/Stop",
            text_color="#4ecdc4",
            font=("Arial", 11)
        )
        self.mode_label.pack(pady=10, padx=10, anchor="w")
        
        # Mode selector + Buttons frame
        control_buttons_frame = ctk.CTkFrame(control_frame, fg_color="#1a1a1a")
        control_buttons_frame.pack(fill="x", padx=10, pady=10)
        
        # Mode selector (dropdown)
        mode_label = ctk.CTkLabel(
            control_buttons_frame,
            text="Select Mode:",
            text_color="#ffffff",
            font=("Arial", 11)
        )
        mode_label.pack(side="left", padx=5)
        
        mode_options = ["Auto Farm", "Scan Pokemon"]
        self.mode_dropdown = ctk.CTkComboBox(
            control_buttons_frame,
            values=mode_options,
            variable=self.selected_mode,
            state="readonly",
            width=150,
            fg_color="#2a2a2a",
            text_color="#ffffff",
            button_color="#0099ff",
            border_color="#0099ff"
        )
        self.mode_dropdown.pack(side="left", padx=5)
        
        # Start button
        self.start_btn = ctk.CTkButton(
            control_buttons_frame,
            text="▶️ START (Alt+F8)",
            text_color="#ffffff",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            height=40,
            font=("Arial", 12, "bold"),
            command=self.start_farm,
            width=150
        )
        self.start_btn.pack(side="left", padx=10, fill="x", expand=False)
        
        # Stop button
        self.stop_btn = ctk.CTkButton(
            control_buttons_frame,
            text="⏹️ STOP (Alt+F8)",
            text_color="#ffffff",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            height=40,
            font=("Arial", 12, "bold"),
            command=self.stop_farm,
            state="disabled",
            width=150
        )
        self.stop_btn.pack(side="left", padx=10, fill="x", expand=False)
        
        # Log panel
        log_frame = ctk.CTkFrame(frame, fg_color="#1a1a1a", corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        log_title = ctk.CTkLabel(
            log_frame,
            text="📝 Live Log",
            text_color="#ffff00",
            font=("Arial", 12, "bold")
        )
        log_title.pack(pady=5, padx=10, anchor="w")
        
        # Text widget cho log
        self.log_text = ctk.CTkTextbox(
            log_frame,
            text_color="#00ff00",
            fg_color="#0d0d0d",
            corner_radius=5,
            font=("Courier", 12)
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_text.configure(state="disabled")
        
        self.tabs["Dashboard"] = frame
    
    def _create_team_builder_tab(self):
        """Tab Team Builder: Placeholder (sẽ chuyển UI tkinter cũ)"""
        frame = ctk.CTkFrame(self.content_container, fg_color="#0d0d0d")
        
        header = ctk.CTkLabel(
            frame,
            text="👥 Team Builder",
            text_color="#00bfff",
            font=("Arial", 18, "bold")
        )
        header.pack(pady=15, padx=10)
        
        info = ctk.CTkLabel(
            frame,
            text="[Team Builder UI coming soon]\nLoad team from screenshots and edit moves.",
            text_color="#4ecdc4",
            font=("Arial", 12)
        )
        info.pack(pady=20, padx=10)
        
        self.tabs["Team Builder"] = frame
    
    def _create_bag_scanner_tab(self):
        """Tab Bag Scanner: Scan all Pokemon in bag"""
        try:
            from src.team_builder.bag_scanner_tab import BagScannerTab
            
            frame = ctk.CTkFrame(self.content_container, fg_color="#0d0d0d")
            self.tabs["Bag Scanner"] = frame
            
            # Embed Tkinter frame vào CustomTkinter
            # Cách đơn giản: tạo tk.Frame và embed nó
            embedded_tk_frame = tk.Frame(frame, bg="#1e2127")
            embedded_tk_frame.pack(fill="both", expand=True, padx=0, pady=0)
            
            # Tạo BagScannerTab
            scanner = BagScannerTab(embedded_tk_frame, self.config)
            scanner.frame.pack(fill="both", expand=True)
            
        except ImportError as e:
            frame = ctk.CTkFrame(self.content_container, fg_color="#0d0d0d")
            header = ctk.CTkLabel(
                frame,
                text="🎒 Bag Scanner",
                text_color="#ff6b6b",
                font=("Arial", 18, "bold")
            )
            header.pack(pady=15, padx=10)
            
            info = ctk.CTkLabel(
                frame,
                text=f"Error loading Bag Scanner: {e}",
                text_color="#ff6b6b",
                font=("Arial", 12)
            )
            info.pack(pady=20, padx=10)
            
            self.tabs["Bag Scanner"] = frame
    
    def _create_auto_farm_config_tab(self):
        """Tab Auto Farm Config: Choose 6 Pokemon to farm"""
        try:
            from src.team_builder.auto_farm_config_tab import AutoFarmConfigTab
            
            frame = ctk.CTkFrame(self.content_container, fg_color="#0d0d0d")
            self.tabs["Auto Farm Config"] = frame
            
            # Embed Tkinter frame vào CustomTkinter
            embedded_tk_frame = tk.Frame(frame, bg="#1e2127")
            embedded_tk_frame.pack(fill="both", expand=True, padx=0, pady=0)
            
            # Tạo AutoFarmConfigTab
            config = AutoFarmConfigTab(embedded_tk_frame, self.config)
            config.frame.pack(fill="both", expand=True)
            
        except ImportError as e:
            frame = ctk.CTkFrame(self.content_container, fg_color="#0d0d0d")
            header = ctk.CTkLabel(
                frame,
                text="⚙️🎯 Auto Farm Config",
                text_color="#ff6b6b",
                font=("Arial", 18, "bold")
            )
            header.pack(pady=15, padx=10)
            
            info = ctk.CTkLabel(
                frame,
                text=f"Error loading Auto Farm Config: {e}",
                text_color="#ff6b6b",
                font=("Arial", 12)
            )
            info.pack(pady=20, padx=10)
            
            self.tabs["Auto Farm Config"] = frame
    
    def _create_calibrate_roi_tab(self):
        """Tab Calibrate ROI: Placeholder"""
        frame = ctk.CTkFrame(self.content_container, fg_color="#0d0d0d")
        
        header = ctk.CTkLabel(
            frame,
            text="🎯 Calibrate ROI",
            text_color="#00bfff",
            font=("Arial", 18, "bold")
        )
        header.pack(pady=15, padx=10)
        
        info = ctk.CTkLabel(
            frame,
            text="[Calibrate ROI UI coming soon]\nDrag and adjust ROI regions for template matching.",
            text_color="#4ecdc4",
            font=("Arial", 12)
        )
        info.pack(pady=20, padx=10)
        
        self.tabs["Calibrate ROI"] = frame
    
    def _create_settings_tab(self):
        """Tab Settings: Config"""
        frame = ctk.CTkFrame(self.content_container, fg_color="#0d0d0d")
        
        header = ctk.CTkLabel(
            frame,
            text="⚙️ Settings",
            text_color="#00bfff",
            font=("Arial", 18, "bold")
        )
        header.pack(pady=15, padx=10)
        
        info = ctk.CTkLabel(
            frame,
            text="[Settings UI coming soon]\nConfigure timing, ROI, OCR settings.",
            text_color="#4ecdc4",
            font=("Arial", 12)
        )
        info.pack(pady=20, padx=10)
        
        self.tabs["Settings"] = frame
    
    def _switch_tab(self, tab_name):
        """Chuyển tab"""
        # Ẩn tất cả tab
        for frame in self.tabs.values():
            frame.grid_remove()
        
        # Hiện tab được chọn
        self.tabs[tab_name].grid(row=0, column=0, sticky="nsew")
        
        # Cập nhật nút menu
        for btn_name, btn in self.buttons.items():
            if btn_name == tab_name:
                btn.configure(fg_color="#0099ff")
            else:
                btn.configure(fg_color="#2a2a2a")
    
    def start_farm(self):
        """Bắt đầu farm mode được chọn (Auto Farm hoặc Scan Pokemon)"""
        if self.worker_running:
            return
        
        mode = self.selected_mode.get()
        self.worker_running = True
        self.stop_event.clear()  # Reset stop signal
        self.start_btn.configure(state="disabled")
        self.mode_dropdown.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="🟢 Running", text_color="#2ecc71")
        self.mode_label.configure(text=f"Mode: {mode}")
        
        self._add_log(f"✅ {mode} started!")
        self._add_log("🎮 Press Alt+F8 to stop.")
        
        # Chạy worker thread
        self.worker_thread = threading.Thread(target=self._farm_worker, daemon=True)
        self.worker_thread.start()
    
    def stop_farm(self):
        """Dừng auto farm"""
        self.worker_running = False
        self.stop_event.set()  # Signal to worker thread
        self.start_btn.configure(state="normal")
        self.mode_dropdown.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="🔴 Stopped", text_color="#ff6b6b")
        
        self._add_log("⏹️ Tool stopped!")
    
    def _farm_worker(self):
        """Background worker - chạy farm logic based on selected mode"""
        try:
            from src.farm.farm_gui_adapter import run_farm_mode_with_gui_logging
            
            mode = self.selected_mode.get()
            # Chạy mode được chọn với log callback
            run_farm_mode_with_gui_logging(self.config, mode, self._add_log, self.stop_event)
        except Exception as e:
            self._add_log(f"❌ Error: {str(e)}")
            import traceback
            self._add_log(f"Traceback:\n{traceback.format_exc()}")
        finally:
            self.worker_running = False
            self.start_btn.configure(state="normal")
            self.mode_dropdown.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.status_label.configure(text="🔴 Stopped", text_color="#ff6b6b")
    
    def log_callback(self, message):
        """Callback từ farm_battle.py để add log"""
        self.log_queue.put(message)
    
    def _add_log(self, message):
        """Thêm dòng log vào log text widget"""
        self.log_queue.put(message)
    
    def _start_log_listener(self):
        """Listener để đọc log từ queue"""
        def update_log():
            try:
                while True:
                    message = self.log_queue.get_nowait()
                    
                    # Update log text widget
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
                    self.log_text.see("end")  # Auto scroll to bottom
                    self.log_text.configure(state="disabled")
                    
                    # Cũng ghi vào feedback_log.txt
                    try:
                        FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                        with FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
                    except:
                        pass
            except queue.Empty:
                pass
            
            # Gọi lại sau 100ms
            self.root.after(100, update_log)
        
        self.root.after(100, update_log)
    
    def _register_hotkey(self):
        """Đăng ký Alt+F8 hotkey"""
        def on_alt_f8():
            if self.worker_running:
                self.stop_farm()
            else:
                self.start_farm()
        
        try:
            keyboard.add_hotkey('alt+f8', on_alt_f8)
            self._add_log("🎮 Alt+F8 hotkey registered!")
            self.hotkey_registered = True
        except Exception as e:
            self._add_log(f"⚠️ Failed to register Alt+F8 hotkey: {e}")
    
    def run(self):
        """Chạy ứng dụng"""
        self.root.mainloop()


def main():
    root = ctk.CTk()
    app = ModernPokemonUI(root)
    app.run()


if __name__ == "__main__":
    main()
