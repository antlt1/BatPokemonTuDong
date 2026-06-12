"""
Tabbed UI - Gộp Calibrate ROI + Team Builder + Party Scanner
"""

import json
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import mss
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw
from src.team_builder.party_scanner_tab import PartyScannnerTab

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
POKEMON_TEMPLATE = ROOT / "src" / "template" / "cap_gamedefault" / "rightBarButtomPokemon.png"

class TabbedToolUI:
    def __init__(self, parent=None):
        if parent is not None:
            # Embedded mode: use parent frame directly
            self.root = parent.winfo_toplevel()
            self.tab_calibrate = parent
            self._setup_calibrate_tab()
        else:
            self.root = tk.Tk()
            self.root.title("PokemonPRO Tools")
            self.root.geometry("1400x900")
            
            self.notebook = ttk.Notebook(self.root)
            self.notebook.pack(fill=tk.BOTH, expand=True)
            
            # Tab 1: Calibrate ROI
            self.tab_calibrate = tk.Frame(self.notebook)
            self.notebook.add(self.tab_calibrate, text="Calibrate ROI")
            self._setup_calibrate_tab()
            
            # Tab 2: Team Builder
            self.tab_team = tk.Frame(self.notebook)
            self.notebook.add(self.tab_team, text="Team Builder")
            self._setup_team_tab()

            # Tab 3: Party Scanner (new)
            self.tab_party_scanner = tk.Frame(self.notebook)
            self.notebook.add(self.tab_party_scanner, text="  📸 Party Scanner  ")
            self._setup_party_scanner_tab()
    
    def _setup_calibrate_tab(self):
        """Setup tab Calibrate ROI."""
        # Load config
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # Initialize ROIs
        self.calibrating_roi_type = tk.StringVar(value="move_slots")
        self.selected_slot_idx = 0

        # Danh sách các ROI đơn lẻ (các nút bấm và vùng đọc text)
        self.template_button_types = ["pokemon_button_roi", "fight_button_roi", "items_button_roi", "run_button_roi"]
        self.single_roi_types = self.template_button_types + [
            "battle_header", "enemy_name", "pokemon_name_in_battle", 
            "right_action_bar", "battle_log", "enemy_hp_bar",
            "items_bag_area", "shiny_popup_area"
        ]
        
        self.rois = {
            "move_slots": self.config.get("roi", {}).get("move_slots", [[900, 638, 130, 48]] * 4),
            "pokemon_swap_slots": self.config.get("roi", {}).get("pokemon_swap_slots", [[1233, 638, 310, 48]] * 6),
            "my_pokemon_slots": self.config.get("roi", {}).get("my_pokemon_slots", [[10, 350, 160, 40], [10, 400, 160, 40], [10, 450, 160, 40], [10, 500, 160, 40], [10, 550, 160, 40], [10, 600, 160, 40]]),
            "pokemon_button_roi": [self.config.get("roi", {}).get("pokemon_button_roi", [1300, 700, 150, 50])],
            "fight_button_roi": [self.config.get("roi", {}).get("fight_button_roi", [1300, 600, 150, 50])],
            "items_button_roi": [self.config.get("roi", {}).get("items_button_roi", [1450, 600, 150, 50])],
            "run_button_roi": [self.config.get("roi", {}).get("run_button_roi", [1450, 700, 150, 50])],
            "battle_header": [self.config.get("roi", {}).get("battle_header", [400, 240, 1150, 90])],
            "enemy_name": [self.config.get("roi", {}).get("enemy_name", [520, 305, 360, 85])],
            "pokemon_name_in_battle": [self.config.get("roi", {}).get("pokemon_name_in_battle", [1022, 634, 79, 32])],
            "right_action_bar": [self.config.get("roi", {}).get("right_action_bar", [1230, 630, 330, 230])],
            "battle_log": [self.config.get("roi", {}).get("battle_log", [190, 745, 460, 225])],
            "enemy_hp_bar": [self.config.get("roi", {}).get("enemy_hp_bar", [520, 370, 200, 14])],
            "items_bag_area": [self.config.get("roi", {}).get("items_bag_area", [1278, 290, 250, 360])],
            "shiny_popup_area": [self.config.get("roi", {}).get("shiny_popup_area", [400, 250, 1120, 400])]
        }
        
        # Take screenshot
        self.screenshot_original = self._take_screenshot()
        
        # Canvas
        canvas_frame = tk.Frame(self.tab_calibrate)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="black", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = tk.Frame(self.tab_calibrate, bg="gray20", height=120)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Control frame - Thêm các RadioButton cho 4 nút
        selector_frame = tk.Frame(control_frame, bg="gray20")
        selector_frame.pack(pady=10)
        
        # Các nút chọn loại ROI
        row1_frame = tk.Frame(selector_frame, bg="gray20")
        row1_frame.pack(pady=2)
        
        row2_frame = tk.Frame(selector_frame, bg="gray20")
        row2_frame.pack(pady=2)

        modes_row1 = [
            ("Moves", "move_slots"),
            ("Swap Slots", "pokemon_swap_slots"),
            ("Fight Btn", "fight_button_roi"),
            ("Items Btn", "items_button_roi"),
            ("Pokemon Btn", "pokemon_button_roi"),
            ("Run Btn", "run_button_roi")
        ]

        modes_row2 = [
            ("Battle Header", "battle_header"),
            ("Enemy Name", "enemy_name"),
            ("Enemy HP Bar", "enemy_hp_bar"),
            ("My PKM Name", "pokemon_name_in_battle"),
            ("Action Bar", "right_action_bar"),
            ("Battle Log", "battle_log"),
            ("My Party", "my_pokemon_slots"),
            ("Items Bag", "items_bag_area"),
            ("Shiny Popup", "shiny_popup_area")
        ]

        for text, mode in modes_row1:
            tk.Radiobutton(row1_frame, text=text, variable=self.calibrating_roi_type,
                           value=mode, bg="gray30", fg="white", selectcolor="#3d59a1",
                           indicatoron=0, width=12,
                           command=self._on_calibration_type_change).pack(side=tk.LEFT, padx=2)
                           
        for text, mode in modes_row2:
            tk.Radiobutton(row2_frame, text=text, variable=self.calibrating_roi_type,
                           value=mode, bg="gray30", fg="white", selectcolor="#3d59a1",
                           indicatoron=0, width=15,
                           command=self._on_calibration_type_change).pack(side=tk.LEFT, padx=2)

        # Threshold entry (Dùng chung cho các nút đơn)
        self.threshold_var = tk.DoubleVar(value=0.55)
        self.threshold_frame = tk.Frame(selector_frame, bg="gray20")
        tk.Label(self.threshold_frame, text="Threshold:", bg="gray20", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Entry(self.threshold_frame, textvariable=self.threshold_var, width=5).pack(side=tk.LEFT)

        # Info label
        self.info_label = tk.Label(control_frame, text="", bg="gray20", fg="white", font=("Arial", 10), anchor="w")
        self.info_label.pack(fill=tk.X, padx=10, pady=5)

        # Buttons
        button_frame = tk.Frame(control_frame, bg="gray20")
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Save", command=self._save_calibrate,
                 bg="green", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Reload", command=self._reload_config,
                 bg="#6366f1", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Reset", command=self._reset_slots,
                 bg="orange", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="📷 Chụp lại", command=self._recapture,
                 bg="#3b82f6", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        # Mouse tracking
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release) # Corrected from _on_release
        self.canvas.bind("<MouseWheel>", self._on_scroll) # For changing selected_slot_idx

        self.dragging_slot = None
        self.dragging_handle = None
        self.drag_start = None

        # Display
        self._display_image()
    
    def _setup_team_tab(self):
        """Setup tab Team Builder."""
        try:
            from src.team_builder.team_builder_ui import create_team_builder_widget

            # Load config
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Create widget and embed
            app = create_team_builder_widget(self.tab_team, config)
            app.pack(fill=tk.BOTH, expand=True, padx=8, pady=8) # Use app.pack instead of self.app.pack
        except Exception as e:
            label = tk.Label(self.tab_team, text=f"Error loading Team Builder: {e}",
                            font=("Arial", 11), fg="red", justify=tk.CENTER)
            label.pack(pady=20)

    def _setup_party_scanner_tab(self):
        """Setup tab Party Scanner."""
        try:
            # Load config
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Create widget and embed
            scanner = PartyScannnerTab(self.tab_party_scanner, config)
            scanner.frame.pack(fill=tk.BOTH, expand=True)
            scanner.load_existing()
        except Exception as e:
            label = tk.Label(self.tab_party_scanner, text=f"Error loading Party Scanner: {e}",
                            font=("Arial", 11), fg="red", justify=tk.CENTER)
            label.pack(pady=20)

    def _take_screenshot(self):
        """Chụp toàn màn hình."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGBA2BGR)
        except Exception as e:
            print(f"Cannot take screenshot: {e}")
            return np.zeros((1080, 1920, 3), dtype=np.uint8)

    def _on_calibration_type_change(self):
        """Khi chọn loại ROI khác, cập nhật threshold tương ứng từ config."""
        curr = self.calibrating_roi_type.get()
        self.selected_slot_idx = 0

        # Mapping threshold từ config
        thresh_map = {
            "pokemon_button_roi": "pokemon_button_threshold",
            "fight_button_roi": "fight_button_threshold",
            "items_button_threshold": "items_button_threshold",
            "run_button_roi": "run_button_threshold"
        }

        if curr in self.template_button_types:
            key = thresh_map.get(curr, "fight_button_threshold")
            val = self.config.get("template_matching", {}).get(key, 0.55)
            self.threshold_var.set(val)
            self.threshold_frame.pack(side=tk.LEFT, padx=10)
        else:
            self.threshold_frame.pack_forget()

        self._display_image()

    def _display_image(self):
        """Hiển thị ảnh với ROI overlay."""
        img = self.screenshot_original.copy()

        current_roi_list = self.rois[self.calibrating_roi_type.get()]
        is_single_roi = self.calibrating_roi_type.get() in self.single_roi_types

        # Draw all ROIs
        for i, (x, y, w, h) in enumerate(current_roi_list):
            if is_single_roi:
                # Vẽ ROI cho nút bấm đơn lẻ
                color = (0, 255, 0)
                cv2.rectangle(img, (x, y), (x+w, y+h), color, 3)
                label = self.calibrating_roi_type.get().replace("_roi", "").upper()
                cv2.putText(img, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                # Vẽ các điểm neo (handles)
                for cx, cy in [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]:
                    cv2.circle(img, (cx, cy), 8, (0, 255, 255), -1)

                break

            if i == self.selected_slot_idx:
                color = (0, 255, 0)  # Green for selected
                thickness = 3
            else:
                color = (200, 200, 200)  # Light gray for others (more visible)
                thickness = 2

            cv2.rectangle(img, (x, y), (x+w, y+h), color, thickness)
            # Draw label with background for better contrast
            label = f"Slot {i+1}"
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            bg_tl = (x+2, y+2)
            bg_br = (x+2+text_w+6, y+2+text_h+4)
            cv2.rectangle(img, bg_tl, bg_br, (0, 0, 0), -1)
            cv2.putText(img, label, (x+5, y+2+text_h), cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (255, 255, 255), 2)

            # Draw handles
            if i == self.selected_slot_idx:
                handle_size = 8
                corners = [(x, y), (x+w, y), (x, y+h), (x+w, y+h)] # Top-left, Top-right, Bottom-left, Bottom-right
                for cx, cy in corners:
                    cv2.circle(img, (cx, cy), handle_size, (0, 255, 255), -1)

        # Resize to fit canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width > 1 and canvas_height > 1:
            scale = min(canvas_width / img.shape[1], canvas_height / img.shape[0])
            new_w = int(img.shape[1] * scale)
            new_h = int(img.shape[0] * scale)
            img_resized = cv2.resize(img, (new_w, new_h))
            self.display_scale = scale
        else:
            img_resized = img
            self.display_scale = 1.0

        # Convert to PIL
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        self.photo_image = ImageTk.PhotoImage(img_pil)

        self.canvas.create_image(0, 0, anchor="nw", image=self.photo_image)

        # Update info
        if current_roi_list and self.selected_slot_idx < len(current_roi_list):
            x, y, w, h = current_roi_list[self.selected_slot_idx]
            self.info_label.config(text=f"Selected ROI ({self.calibrating_roi_type.get()} Slot {self.selected_slot_idx+1}): X={x}, Y={y}, W={w}, H={h} | Drag handles to adjust")
        else:
            self.info_label.config(text="No ROI selected or list is empty.")

    def _on_motion(self, event):
        pass

    def _on_scroll(self, event):
        """Scroll to change selected_slot_idx for multi-item ROIs."""
        if self.calibrating_roi_type.get() not in self.single_roi_types and self.rois[self.calibrating_roi_type.get()]:
            self.selected_slot_idx = (self.selected_slot_idx - (1 if event.delta > 0 else -1) + len(self.rois[self.calibrating_roi_type.get()])) % len(self.rois[self.calibrating_roi_type.get()])
            self._display_image()

    def _on_click(self, event):
        """Detect nếu click vào handle."""
        current_roi_list = self.rois.get(self.calibrating_roi_type.get())
        if not current_roi_list or self.selected_slot_idx >= len(current_roi_list):
            return

        # If it's a single ROI, always target the first (and only) item
        slot_idx_to_check = 0 if self.calibrating_roi_type.get() in self.single_roi_types else self.selected_slot_idx
        x, y, w, h = current_roi_list[slot_idx_to_check]

        img_x = int(event.x / self.display_scale)
        img_y = int(event.y / self.display_scale)

        tol = 8
        handles = {
            "tl": (x, y),
            "tr": (x+w, y),
            "bl": (x, y+h),
            "br": (x+w, y+h),
            "center": (x+w//2, y+h//2)
        }

        for handle_name, (hx, hy) in handles.items():
            if abs(img_x - hx) < tol and abs(img_y - hy) < tol:
                self.dragging_slot = slot_idx_to_check
                self.dragging_handle = handle_name
                self.drag_start = (img_x, img_y)
                return
        # If clicked inside the slot rect (not on a handle), select it for dragging
        # Check all slots for multi-item ROI types
        if self.calibrating_roi_type.get() not in self.single_roi_types:
            for idx, (sx, sy, sw, sh) in enumerate(current_roi_list):
                if sx <= img_x <= sx+sw and sy <= img_y <= sy+sh:
                    self.selected_slot_idx = idx
                    # start dragging the center
                    self.dragging_slot = idx
                    self.dragging_handle = "center"
                    self.drag_start = (img_x, img_y)
                    self._display_image()
                    return

    def _on_drag(self, event):
        """Kéo chuột để điều chỉnh."""
        if self.dragging_slot is None or self.dragging_handle is None:
            return

        img_x = int(event.x / self.display_scale)
        img_y = int(event.y / self.display_scale)

        dx = img_x - self.drag_start[0]
        dy = img_y - self.drag_start[1]

        current_roi_list = self.rois[self.calibrating_roi_type.get()]
        x, y, w, h = current_roi_list[self.dragging_slot]

        if self.dragging_handle == "tl":
            current_roi_list[self.dragging_slot] = [x+dx, y+dy, w-dx, h-dy]
        elif self.dragging_handle == "tr":
            current_roi_list[self.dragging_slot] = [x, y+dy, w+dx, h-dy]
        elif self.dragging_handle == "bl":
            current_roi_list[self.dragging_slot] = [x+dx, y, w-dx, h+dy]
        elif self.dragging_handle == "br":
            current_roi_list[self.dragging_slot] = [x, y, w+dx, h+dy]
        elif self.dragging_handle == "center":
            current_roi_list[self.dragging_slot] = [x+dx, y+dy, w, h]

        self.drag_start = (img_x, img_y)
        self._display_image()

    def _on_release(self, event):
        """Kết thúc kéo."""
        # Ensure ROI dimensions are positive
        if self.dragging_slot is not None:
            current_roi_list = self.rois[self.calibrating_roi_type.get()]
            x, y, w, h = current_roi_list[self.dragging_slot]
            if w < 0:
                x, w = x + w, -w
            if h < 0:
                y, h = y + h, -h
            current_roi_list[self.dragging_slot] = [x, y, w, h]
        self.dragging_slot = None
        self.dragging_handle = None
        self.drag_start = None

    def _reset_slots(self):
        """Reset về default - yêu cầu xác nhận trước."""
        current_type = self.calibrating_roi_type.get()
        confirm = messagebox.askyesno(
            "Xác nhận Reset",
            f"Bạn có chắc muốn reset ROI '{current_type}' về giá trị mặc định không?\nHành động này không thể hoàn tác (chưa lưu vào file).",
            icon="warning"
        )
        if not confirm:
            return
        if current_type == "move_slots":
            self.rois["move_slots"] = [
            [900, 638, 130, 48],
            [900, 695, 130, 48],
            [900, 752, 130, 48],
            [900, 809, 130, 48],
            ]
        elif current_type == "pokemon_button_roi":
            self.rois["pokemon_button_roi"] = [[1300, 700, 150, 50]] # Default guess
            self.threshold_var.set(0.55)
        elif current_type == "fight_button_roi":
            self.rois["fight_button_roi"] = [[1300, 600, 150, 50]]
            self.threshold_var.set(0.55)
        elif current_type == "items_button_roi":
            self.rois["items_button_roi"] = [[1450, 600, 150, 50]]
            self.threshold_var.set(0.55)
        elif current_type == "run_button_roi":
            self.rois["run_button_roi"] = [[1450, 700, 150, 50]]
            self.threshold_var.set(0.55)
        elif current_type == "pokemon_swap_slots":
            self.rois["pokemon_swap_slots"] = [
                [1233, 638, 310, 48], [1233, 690, 310, 48], [1233, 742, 310, 48],
                [1233, 794, 310, 48], [1233, 846, 310, 48], [1233, 898, 310, 48]
            ]
        elif current_type == "battle_header":
            self.rois["battle_header"] = [[400, 240, 1150, 90]]
        elif current_type == "enemy_name":
            self.rois["enemy_name"] = [[520, 305, 360, 85]]
        elif current_type == "pokemon_name_in_battle":
            self.rois["pokemon_name_in_battle"] = [[1022, 634, 79, 32]]
        elif current_type == "right_action_bar":
            self.rois["right_action_bar"] = [[1230, 630, 330, 230]]
        elif current_type == "battle_log":
            self.rois["battle_log"] = [[190, 745, 460, 225]]
        elif current_type == "enemy_hp_bar":
            self.rois["enemy_hp_bar"] = [[520, 370, 200, 14]]
        elif current_type == "items_bag_area":
            self.rois["items_bag_area"] = [[1278, 290, 250, 360]]
        elif current_type == "shiny_popup_area":
            self.rois["shiny_popup_area"] = [[400, 250, 1120, 400]]
        elif current_type == "my_pokemon_slots":
            self.rois["my_pokemon_slots"] = [
                [10, 350, 160, 40], [10, 400, 160, 40], [10, 450, 160, 40],
                [10, 500, 160, 40], [10, 550, 160, 40], [10, 600, 160, 40]
            ]
        self._display_image()

    def _recapture(self):
        """Chụp lại screenshot và refresh canvas."""
        self.screenshot_original = self._take_screenshot()
        self._display_image()
        self.info_label.configure(text="📷 Đã chụp lại screenshot!")

    def _reload_config(self):
        """Reload config từ file và cập nhật lại tất cả ROI đang hiển thị."""
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            # Cập nhật lại các ROI từ config mới
            self.rois["move_slots"] = self.config.get("roi", {}).get("move_slots", [[900, 638, 130, 48]] * 4)
            self.rois["pokemon_swap_slots"] = self.config.get("roi", {}).get("pokemon_swap_slots", [[1233, 638, 310, 48]] * 6)
            self.rois["my_pokemon_slots"] = self.config.get("roi", {}).get("my_pokemon_slots", [[10, 350, 160, 40]] * 6)
            for key in self.single_roi_types:
                val = self.config.get("roi", {}).get(key)
                if val is not None:
                    self.rois[key] = [val]
            # Cập nhật threshold nếu đang chọn nút template
            curr = self.calibrating_roi_type.get()
            thresh_map = {
                "pokemon_button_roi": "pokemon_button_threshold",
                "fight_button_roi": "fight_button_threshold",
                "items_button_roi": "items_button_threshold",
                "run_button_roi": "run_button_threshold"
            }
            if curr in thresh_map:
                val = self.config.get("template_matching", {}).get(thresh_map[curr], 0.55)
                self.threshold_var.set(val)
            self._display_image()
            self.info_label.configure(text="✅ Đã reload config từ file thành công!")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi reload config: {e}")

    def _save_calibrate(self):
        """Lưu toàn bộ ROI và Threshold vào tool_config.json."""
        try:
            # Đọc lại config mới nhất từ file trước để không ghi đè các thứ khác
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                fresh_config = json.load(f)

            if "roi" not in fresh_config:
                fresh_config["roi"] = {}
            if "template_matching" not in fresh_config:
                fresh_config["template_matching"] = {}

            # Lưu ROIs
            for key in ["move_slots", "pokemon_swap_slots", "my_pokemon_slots"]:
                fresh_config["roi"][key] = self.rois[key]

            for key in self.single_roi_types:
                fresh_config["roi"][key] = self.rois[key][0]

            # Lưu Threshold hiện tại cho nút đang chọn
            curr = self.calibrating_roi_type.get()
            thresh_map = {
                "pokemon_button_roi": "pokemon_button_threshold",
                "fight_button_roi": "fight_button_threshold",
                "items_button_roi": "items_button_threshold",
                "run_button_roi": "run_button_threshold"
            }
            if curr in thresh_map:
                fresh_config["template_matching"][thresh_map[curr]] = self.threshold_var.get()

            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(fresh_config, f, indent=2, ensure_ascii=False)

            # Cập nhật self.config theo dữ liệu vừa lưu
            self.config = fresh_config

            self.info_label.configure(text="✅ Đã lưu cấu hình ROI vào file!")
            messagebox.showinfo("Thành công", "Đã lưu cấu hình ROI và Threshold!")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi lưu: {e}")
    
    def run(self):
        """Chạy."""
        self.root.after(100, lambda: self._display_image())
        self.root.mainloop()

def main():
    app = TabbedToolUI()
    app.run()

if __name__ == "__main__":
    main()

