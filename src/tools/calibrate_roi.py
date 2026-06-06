"""
Calibrate Move ROI Tool - Menu item 4
Cho phép người dùng chọn và điều chỉnh vị trí move slot bằng giao diện visual.
"""

import json
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import mss
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"

class MoveROICalibrator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Move ROI Calibrator - Drag to Adjust")
        self.root.geometry("1400x900")
        
        # Lấy config hiện tại
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.move_slots = self.config.get("roi", {}).get("move_slots", [
            [900, 638, 130, 48],
            [900, 695, 130, 48],
            [900, 752, 130, 48],
            [900, 809, 130, 48],
        ])
        
        # Chụp ảnh hiện tại từ screenshot
        self.screenshot_original = self._take_screenshot()
        
        # Canvas frame
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="black", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = tk.Frame(self.root, bg="gray20", height=120)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Slot selector
        selector_frame = tk.Frame(control_frame, bg="gray20")
        selector_frame.pack(pady=10)
        
        tk.Label(selector_frame, text="Chon Slot:", bg="gray20", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.selected_slot = tk.IntVar(value=0)
        for i in range(4):
            tk.Radiobutton(selector_frame, text=f"Move {i+1}", variable=self.selected_slot, 
                          value=i, bg="gray30", fg="white", activebackground="blue",
                          command=self._on_slot_change).pack(side=tk.LEFT, padx=5)
        
        # Info display
        info_frame = tk.Frame(control_frame, bg="gray20")
        info_frame.pack(pady=5)
        
        self.info_label = tk.Label(info_frame, text="", bg="gray20", fg="white", font=("Arial", 10))
        self.info_label.pack(side=tk.LEFT, padx=10)
        
        # Buttons
        button_frame = tk.Frame(control_frame, bg="gray20")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save & Exit", command=self._save_config, 
                 bg="green", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Reset", command=self._reset_slots, 
                 bg="orange", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=self.root.quit, 
                 bg="red", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        # Mouse tracking
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        
        self.dragging_slot = None
        self.dragging_handle = None
        self.drag_start = None
        
        # Display image
        self._display_image()
    
    def _take_screenshot(self):
        """Chụp toàn màn hình."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGBA2BGR)
        except Exception as e:
            print(f"Cannot take screenshot: {e}")
            # Return blank image nếu không thể chụp
            return np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    def _on_slot_change(self):
        """Khi chọn slot khác."""
        self._display_image()
    
    def _display_image(self):
        """Hiển thị ảnh với ROI overlay."""
        img = self.screenshot_original.copy()
        
        # Vẽ tất cả ROI
        for i, (x, y, w, h) in enumerate(self.move_slots):
            # Màu khác nhau cho slot selected vs others
            if i == self.selected_slot.get():
                color = (0, 255, 0)  # Green for selected
                thickness = 3
            else:
                color = (100, 100, 100)  # Gray for others
                thickness = 1
            
            cv2.rectangle(img, (x, y), (x+w, y+h), color, thickness)
            cv2.putText(img, f"Move {i+1}", (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, color, 1)
            
            # Draw handles cho selected slot
            if i == self.selected_slot.get():
                handle_size = 8
                corners = [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]
                for cx, cy in corners:
                    cv2.circle(img, (cx, cy), handle_size, (0, 255, 255), -1)
        
        # Resize image to fit canvas
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
        
        # Convert to PIL and display
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        self.photo_image = ImageTk.PhotoImage(img_pil)
        
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo_image)
        
        # Update info label
        slot_idx = self.selected_slot.get()
        x, y, w, h = self.move_slots[slot_idx]
        self.info_label.config(text=f"Move {slot_idx+1}: X={x}, Y={y}, W={w}, H={h} | Drag handles to adjust")
    
    def _on_motion(self, event):
        """Theo dõi mouse."""
        pass
    
    def _on_click(self, event):
        """Detect nếu click vào handle."""
        slot_idx = self.selected_slot.get()
        x, y, w, h = self.move_slots[slot_idx]
        
        # Convert screen coords to image coords
        img_x = int(event.x / self.display_scale)
        img_y = int(event.y / self.display_scale)
        
        # Check handles (8px tolerance)
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
                self.dragging_slot = slot_idx
                self.dragging_handle = handle_name
                self.drag_start = (img_x, img_y)
                return
    
    def _on_drag(self, event):
        """Kéo chuột để điều chỉnh."""
        if self.dragging_slot is None or self.dragging_handle is None:
            return
        
        img_x = int(event.x / self.display_scale)
        img_y = int(event.y / self.display_scale)
        
        dx = img_x - self.drag_start[0]
        dy = img_y - self.drag_start[1]
        
        x, y, w, h = self.move_slots[self.dragging_slot]
        
        if self.dragging_handle == "tl":
            # Top-left
            self.move_slots[self.dragging_slot] = [x+dx, y+dy, w-dx, h-dy]
        elif self.dragging_handle == "tr":
            # Top-right
            self.move_slots[self.dragging_slot] = [x, y+dy, w+dx, h-dy]
        elif self.dragging_handle == "bl":
            # Bottom-left
            self.move_slots[self.dragging_slot] = [x+dx, y, w-dx, h+dy]
        elif self.dragging_handle == "br":
            # Bottom-right
            self.move_slots[self.dragging_slot] = [x, y, w+dx, h+dy]
        elif self.dragging_handle == "center":
            # Move entire box
            self.move_slots[self.dragging_slot] = [x+dx, y+dy, w, h]
        
        self.drag_start = (img_x, img_y)
        self._display_image()
    
    def _on_release(self, event):
        """Kết thúc kéo."""
        self.dragging_slot = None
        self.dragging_handle = None
        self.drag_start = None
    
    def _on_scroll(self, event):
        """Scroll để thay đổi size (không dùng trong phiên bản này)."""
        pass
    
    def _reset_slots(self):
        """Reset về ROI mặc định."""
        self.move_slots = [
            [900, 638, 130, 48],
            [900, 695, 130, 48],
            [900, 752, 130, 48],
            [900, 809, 130, 48],
        ]
        self._display_image()
    
    def _save_config(self):
        """Lưu vào config."""
        try:
            self.config["roi"]["move_slots"] = self.move_slots
            
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Success", f"Đã lưu ROI tới config:\n\n{json.dumps(self.move_slots, indent=2)}")
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi: {e}")
    
    def run(self):
        """Chạy."""
        self.root.after(100, lambda: self._display_image())
        self.root.mainloop()

def main():
    """Main entry point."""
    app = MoveROICalibrator()
    app.run()

if __name__ == "__main__":
    main()

