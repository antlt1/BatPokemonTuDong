"""
Tabbed UI - Gộp Calibrate ROI + Team Builder
"""

import json
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import mss
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
POKEMON_TEMPLATE = ROOT / "src" / "template" / "cap_gamedefault" / "rightBarButtomPokemon.png"

class TabbedToolUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PokemonPRO Tools")
        self.root.geometry("1400x900")
        
        # Tạo notebook (tab container)
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
    
    def _setup_calibrate_tab(self):
        """Setup tab Calibrate ROI."""
        # Load config
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # Initialize ROIs and thresholds
        self.calibrating_roi_type = tk.StringVar(value="move_slots") # Default to move slots
        self.selected_slot_idx = 0 # Index within the current ROI list
        self.rois = {
            "move_slots": self.config.get("roi", {}).get("move_slots", [
            [900, 638, 130, 48], # Default values for move slots
            [900, 695, 130, 48],
            [900, 752, 130, 48],
            [900, 809, 130, 48],
            ]),
            "pokemon_button_roi": [self.config.get("roi", {}).get("pokemon_button_roi", [1300, 700, 150, 50])],
            "pokemon_swap_slots": self.config.get("roi", {}).get("pokemon_swap_slots", [
                [1233, 638, 310, 48], [1233, 690, 310, 48], [1233, 742, 310, 48],
                [1233, 794, 310, 48], [1233, 846, 310, 48], [1233, 898, 310, 48]
            ])
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
        
        # Slot selector
        selector_frame = tk.Frame(control_frame, bg="gray20")
        selector_frame.pack(pady=10)
        
        tk.Label(selector_frame, text="Calibrate:", bg="gray20", fg="white").pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(selector_frame, text="Move Slots", variable=self.calibrating_roi_type,
                       value="move_slots", bg="gray30", fg="white", activebackground="blue",
                       command=self._on_calibration_type_change).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(selector_frame, text="Pokemon Button", variable=self.calibrating_roi_type,
                       value="pokemon_button_roi", bg="gray30", fg="white", activebackground="blue",
                       command=self._on_calibration_type_change).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(selector_frame, text="Pokemon Swap Slots", variable=self.calibrating_roi_type,
                       value="pokemon_swap_slots", bg="gray30", fg="white", activebackground="blue",
                       command=self._on_calibration_type_change).pack(side=tk.LEFT, padx=10)

        # Threshold for Pokemon Button
        self.pokemon_button_threshold_var = tk.DoubleVar(value=self.config.get("template_matching", {}).get("pokemon_button_threshold", 0.50)) # Default threshold
        self.threshold_frame = tk.Frame(selector_frame, bg="gray20")
        tk.Label(self.threshold_frame, text="Threshold:", bg="gray20", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Entry(self.threshold_frame, textvariable=self.pokemon_button_threshold_var, width=5,
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", font=("Segoe UI", 10), relief="flat").pack(side=tk.LEFT)
        
        # Info label
        self.info_label = tk.Label(control_frame, text="", bg="gray20", fg="white", font=("Arial", 10), anchor="w")
        self.info_label.pack(fill=tk.X, padx=10, pady=5)
        
        # Buttons
        button_frame = tk.Frame(control_frame, bg="gray20")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save", command=self._save_calibrate, 
                 bg="green", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Reset", command=self._reset_slots, 
                 bg="orange", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
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
        """Khi chọn loại ROI khác."""
        # Reset selected slot index for the new type
        self.selected_slot_idx = 0 # Reset to first item in the new list
        # Show/hide threshold entry based on selected type
        if self.calibrating_roi_type.get() == "pokemon_button_roi":
            self.threshold_frame.pack(side=tk.LEFT, padx=5)
        else:
            self.threshold_frame.pack_forget()
        self._display_image()
    
    def _display_image(self):
        """Hiển thị ảnh với ROI overlay."""
        img = self.screenshot_original.copy()
        
        current_roi_list = self.rois[self.calibrating_roi_type.get()]
        is_single_roi = self.calibrating_roi_type.get() == "pokemon_button_roi"

        # Draw all ROIs
        for i, (x, y, w, h) in enumerate(current_roi_list):
            if is_single_roi: # For single ROI like pokemon_button_roi, only draw the first (and only) item
                if i == 0:
                    color = (0, 255, 0)  # Green for selected
                    thickness = 3
                    cv2.rectangle(img, (x, y), (x+w, y+h), color, thickness)
                    cv2.putText(img, "Pokemon Button", (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, color, 1)
                    # Draw handles
                    handle_size = 8
                    corners = [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]
                    for cx, cy in corners:
                        cv2.circle(img, (cx, cy), handle_size, (0, 255, 255), -1)
                    # Draw template image for Pokemon button
                    template_img = cv2.imread(str(POKEMON_TEMPLATE), cv2.IMREAD_COLOR)
                    if template_img is not None:
                        th, tw = template_img.shape[:2]
                        # Overlay template at the center of the ROI
                        center_x, center_y = x + w // 2, y + h // 2
                        start_x, start_y = center_x - tw // 2, center_y - th // 2
                        end_x, end_y = start_x + tw, start_y + th
                        # Ensure it's within bounds and copy
                        img[max(0, start_y):min(img.shape[0], end_y), max(0, start_x):min(img.shape[1], end_x)] = template_img[max(0, -start_y):min(th, img.shape[0]-start_y), max(0, -start_x):min(tw, img.shape[1]-start_x)]
                continue # Skip drawing other items if it's a single ROI

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
        if self.calibrating_roi_type.get() != "pokemon_button_roi" and self.rois[self.calibrating_roi_type.get()]:
            self.selected_slot_idx = (self.selected_slot_idx - (1 if event.delta > 0 else -1) + len(self.rois[self.calibrating_roi_type.get()])) % len(self.rois[self.calibrating_roi_type.get()])
            self._display_image()

    def _on_click(self, event):
        """Detect nếu click vào handle."""
        current_roi_list = self.rois.get(self.calibrating_roi_type.get())
        if not current_roi_list or self.selected_slot_idx >= len(current_roi_list):
            return

        # If it's a single ROI, always target the first (and only) item
        slot_idx_to_check = 0 if self.calibrating_roi_type.get() == "pokemon_button_roi" else self.selected_slot_idx
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
        if self.calibrating_roi_type.get() != "pokemon_button_roi":
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
    
    def _reset_slots(self): # Renamed from _reset_slots to _reset_current_roi
        """Reset về default."""
        current_type = self.calibrating_roi_type.get() # Use .get() to retrieve the string value
        if current_type == "move_slots":
            self.rois["move_slots"] = [
            [900, 638, 130, 48],
            [900, 695, 130, 48],
            [900, 752, 130, 48],
            [900, 809, 130, 48],
            ]
        elif current_type == "pokemon_button_roi":
            self.rois["pokemon_button_roi"] = [[1300, 700, 150, 50]] # Default guess
            self.pokemon_button_threshold_var.set(0.50)
        elif current_type == "pokemon_swap_slots":
            self.rois["pokemon_swap_slots"] = [
                [1233, 638, 310, 48], [1233, 690, 310, 48], [1233, 742, 310, 48],
                [1233, 794, 310, 48], [1233, 846, 310, 48], [1233, 898, 310, 48]
            ]
        self._display_image()
    
    def _save_calibrate(self):
        """Lưu ROI."""
        try:
            self.config["roi"]["move_slots"] = self.rois["move_slots"]
            self.config["roi"]["pokemon_button_roi"] = self.rois["pokemon_button_roi"][0]
            self.config["roi"]["pokemon_swap_slots"] = self.rois["pokemon_swap_slots"]
            self.config["template_matching"]["pokemon_button_threshold"] = self.pokemon_button_threshold_var.get()
            
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Success", "Đã lưu ROI config")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi: {e}")
    
    def run(self):
        """Chạy."""
        self.root.after(100, lambda: self._display_image())
        self.root.mainloop()

def main():
    app = TabbedToolUI()
    app.run()

if __name__ == "__main__":
    main()
