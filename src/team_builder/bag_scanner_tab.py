"""
bag_scanner_tab.py — Tab 4: Bag/Inventory Scanner (REWRITE)

Workflow:
  1. Paste ảnh túi
  2. Kéo ROI quanh 1 tên Pokemon → OCR → box "Pokemon Name"
  3. Kéo ROI quanh 4 moves → OCR → 4 move boxes
  4. Bấm "➕ Add Pokemon" → thêm vào list (id, name, moves=[])
  5. Sau quét moves → update moves vào item
  6. 💾 Save JSON (có ID)
"""

import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk, simpledialog

try:
    from PIL import Image, ImageTk, ImageGrab
    import pytesseract
    import cv2
    import numpy as np
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

# ─────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent.parent
BAG_PATH     = ROOT / "src" / "config" / "pokemon_bag_inventory.json"

CANVAS_W = 700
CANVAS_H = 520

BG_DARK  = "#1e2127"
BG_MID   = "#282c34"
BG_CARD  = "#2d3139"
ACCENT   = "#61afef"
ACCENT2  = "#98c379"
WARN     = "#e06c75"
TEXT_MAIN= "#abb2bf"
TEXT_HI  = "#e5c07b"
F_TITLE  = ("Consolas", 12, "bold")
F_LABEL  = ("Consolas", 10)
F_SMALL  = ("Consolas", 9)


# ═════════════════════════════════════════════════════════
class BagScannerTab:
    def __init__(self, parent, config):
        self.config      = config
        self.img_pil     = None
        self.img_tk      = None
        self.img_scale   = 1.0
        self.img_offset  = (0, 0)

        # Chế độ kéo ROI
        self._mode       = None      # "name" | "moves"
        self._drag_start = None
        self._drag_rect  = None

        # Danh sách Pokemon (từ bag_inventory.json)
        self.inventory   = []        # [{"id": 1, "name": "...", "moves": [...]}, ...]
        self.next_id     = 1

        # UI state
        self.selected_pokemon_idx = None  # Index của Pokemon đang chọn để add moves

        self.frame = tk.Frame(parent, bg=BG_DARK)
        self._load_inventory()
        self._build_ui()

    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        self.frame.columnconfigure(0, weight=2)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # ===== TOOLBAR 1 =====
        toolbar = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8)

        tk.Label(toolbar, text="🎒 BAG SCANNER", font=F_TITLE,
                 bg=BG_DARK, fg=ACCENT).pack(side="left", padx=(0, 20))

        tk.Button(toolbar, text="📂 Mở ảnh",
                  command=self._browse_image, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="📋 Dán ảnh Ctrl+V",
                  command=self._paste_clipboard, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="Dán ảnh → Kéo tên → Kéo moves → Add")
        tk.Label(toolbar, textvariable=self.status_var, font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN).pack(side="left", padx=12)

        # ===== TOOLBAR 2 (Quét) =====
        toolbar2 = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        toolbar2.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8)

        tk.Label(toolbar2, text="Quét:", font=F_LABEL,
                 bg=BG_DARK, fg=TEXT_HI).pack(side="left", padx=(0, 10))

        tk.Button(toolbar2, text="🎯 Kéo tên Pokemon",
                  command=self._activate_scan_name, font=F_LABEL,
                  bg=ACCENT, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar2, text="🎯 Kéo 4 moves",
                  command=self._activate_scan_moves, font=F_LABEL,
                  bg=ACCENT2, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar2, text="🗑️ Clear All",
                  command=self._clear_all, font=F_LABEL,
                  bg=WARN, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        # Bind Ctrl+V
        self.frame.bind_all("<Control-v>", lambda e: self._paste_clipboard())

        # ===== CANVAS (LEFT) =====
        canvas_frame = tk.Frame(self.frame, bg=BG_MID, bd=1, relief="solid")
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)

        self.canvas = tk.Canvas(canvas_frame, bg="#111316",
                                width=CANVAS_W, height=CANVAS_H,
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(CANVAS_W//2, CANVAS_H//2,
            text="Ctrl+V để dán ảnh", font=("Consolas", 12), 
            fill="#3e4451", justify="center", tags="hint")

        self.canvas.bind("<Button-1>",        self._drag_press)
        self.canvas.bind("<B1-Motion>",       self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_release)

        # ===== RIGHT PANEL =====
        right = tk.Frame(self.frame, bg=BG_DARK)
        right.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        # --- Input Section ---
        input_box = tk.Frame(right, bg=BG_CARD, bd=1, relief="solid", padx=6, pady=6)
        input_box.pack(fill="x", padx=4, pady=4)
        input_box.columnconfigure(1, weight=1)

        tk.Label(input_box, text="Pokemon Name:", font=F_LABEL,
                 bg=BG_CARD, fg=TEXT_HI).grid(row=0, column=0, sticky="w", pady=2)
        self.name_entry = tk.Entry(input_box, font=F_LABEL, bg=BG_MID, fg=TEXT_HI,
                                    insertbackground=TEXT_HI, bd=0)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Moves section
        tk.Label(input_box, text="Moves & PP:", font=F_LABEL,
                 bg=BG_CARD, fg=TEXT_HI).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 2))

        # Move 1 & 2 row
        self.move1_entry = tk.Entry(input_box, font=F_SMALL, bg=BG_MID, fg=TEXT_HI, bd=0)
        self.move1_entry.grid(row=2, column=0, sticky="ew", padx=(0, 2))

        self.pp1_entry = tk.Entry(input_box, font=F_SMALL, bg=BG_MID, fg=TEXT_HI, bd=0, width=8)
        self.pp1_entry.grid(row=2, column=1, sticky="e", padx=(2, 0))

        # Move 2 & PP
        self.move2_entry = tk.Entry(input_box, font=F_SMALL, bg=BG_MID, fg=TEXT_HI, bd=0)
        self.move2_entry.grid(row=3, column=0, sticky="ew", padx=(0, 2), pady=2)

        self.pp2_entry = tk.Entry(input_box, font=F_SMALL, bg=BG_MID, fg=TEXT_HI, bd=0, width=8)
        self.pp2_entry.grid(row=3, column=1, sticky="e", padx=(2, 0), pady=2)

        # Move 3 & PP
        self.move3_entry = tk.Entry(input_box, font=F_SMALL, bg=BG_MID, fg=TEXT_HI, bd=0)
        self.move3_entry.grid(row=4, column=0, sticky="ew", padx=(0, 2), pady=2)

        self.pp3_entry = tk.Entry(input_box, font=F_SMALL, bg=BG_MID, fg=TEXT_HI, bd=0, width=8)
        self.pp3_entry.grid(row=4, column=1, sticky="e", padx=(2, 0), pady=2)

        # Move 4 & PP
        self.move4_entry = tk.Entry(input_box, font=F_SMALL, bg=BG_MID, fg=TEXT_HI, bd=0)
        self.move4_entry.grid(row=5, column=0, sticky="ew", padx=(0, 2), pady=2)

        self.pp4_entry = tk.Entry(input_box, font=F_SMALL, bg=BG_MID, fg=TEXT_HI, bd=0, width=8)
        self.pp4_entry.grid(row=5, column=1, sticky="e", padx=(2, 0), pady=2)

        # --- Buttons ---
        btn_frame = tk.Frame(right, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=4, pady=4)
        btn_frame.columnconfigure([0, 1, 2], weight=1)

        tk.Button(btn_frame, text="➕ Add Pokemon",
                  command=self._add_pokemon, font=F_LABEL,
                  bg=ACCENT2, fg=BG_DARK, relief="flat", padx=6, pady=4).grid(row=0, column=0, sticky="ew", padx=2)

        tk.Button(btn_frame, text="🔄 Clear",
                  command=self._clear_inputs, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat", padx=6, pady=4).grid(row=0, column=1, sticky="ew", padx=2)

        tk.Button(btn_frame, text="💾 Save JSON",
                  command=self._save_json, font=F_LABEL,
                  bg=ACCENT, fg=BG_DARK, relief="flat", padx=6, pady=4).grid(row=0, column=2, sticky="ew", padx=2)

        # --- Pokemon List (scrollable) ---
        list_label = tk.Label(right, text="📦 Pokemon List", font=F_LABEL,
                              bg=BG_DARK, fg=ACCENT2)
        list_label.pack(fill="x", padx=4, pady=(8, 4))

        scroll_canvas = tk.Canvas(right, bg=BG_DARK, highlightthickness=0, height=150)
        scrollbar = ttk.Scrollbar(right, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        self.list_frame = tk.Frame(scroll_canvas, bg=BG_DARK)
        self.list_frame_id = scroll_canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        self.list_frame.bind("<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind("<Configure>",
            lambda e: scroll_canvas.itemconfig(self.list_frame_id, width=e.width))

        scroll_canvas.bind_all("<MouseWheel>",
            lambda e: scroll_canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._update_list()

    # ──────────────────────────────────────────────────────
    def _load_inventory(self):
        """Load từ JSON"""
        if BAG_PATH.exists():
            try:
                data = json.loads(BAG_PATH.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    self.inventory = data
                    # Find max ID
                    if data:
                        self.next_id = max(p.get("id", 0) for p in data) + 1
                    else:
                        self.next_id = 1
            except Exception as e:
                print(f"Lỗi load JSON: {e}")
                self.inventory = []
                self.next_id = 1

    def _activate_scan_name(self):
        """Kích hoạt mode quét tên"""
        if not self.img_pil:
            messagebox.showwarning("Chưa có ảnh", "Dán ảnh trước!")
            return
        self._mode = "name"
        self._drag_start = None
        self.canvas.config(cursor="tcross")
        self.status_var.set("🖱️ Kéo bao quanh tên 1 Pokemon rồi thả")

    def _activate_scan_moves(self):
        """Kích hoạt mode quét moves"""
        if not self.img_pil:
            messagebox.showwarning("Chưa có ảnh", "Dán ảnh trước!")
            return
        self._mode = "moves"
        self._drag_start = None
        self.canvas.config(cursor="tcross")
        self.status_var.set("🖱️ Kéo bao quanh bảng 4 MOVES rồi thả")

    def _drag_press(self, event):
        if self._mode is None:
            print(f"[DEBUG] drag_press: mode is None, ignoring")
            return
        print(f"[DEBUG] drag_press at ({event.x}, {event.y}), mode={self._mode}")
        self._drag_start = (event.x, event.y)
        if self._drag_rect:
            self.canvas.delete(self._drag_rect)

    def _drag_move(self, event):
        if self._drag_start is None or self._mode is None:
            return
        if self._drag_rect:
            self.canvas.delete(self._drag_rect)
        x0, y0 = self._drag_start
        self._drag_rect = self.canvas.create_rectangle(
            x0, y0, event.x, event.y,
            outline=WARN, width=2, dash=(5, 3))

    def _drag_release(self, event):
        if self._drag_start is None or self._mode is None:
            print(f"[DEBUG] drag_release: drag_start={self._drag_start}, mode={self._mode}")
            return

        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y
        print(f"[DEBUG] drag_release: ({x0},{y0}) to ({x1},{y1}), mode={self._mode}")
        
        ox, oy  = self.img_offset
        scale   = self.img_scale

        rx = int((min(x0, x1) - ox) / scale)
        ry = int((min(y0, y1) - oy) / scale)
        rw = int(abs(x1 - x0) / scale)
        rh = int(abs(y1 - y0) / scale)

        iw, ih = self.img_pil.size
        rx = max(0, min(rx, iw - 1))
        ry = max(0, min(ry, ih - 1))
        rw = max(1, min(rw, iw - rx))
        rh = max(1, min(rh, ih - ry))

        print(f"[DEBUG] ROI after calc: rx={rx}, ry={ry}, rw={rw}, rh={rh}, img_size={iw}x{ih}")

        if self._mode == "name":
            self._process_name_roi(rx, ry, rw, rh)
        elif self._mode == "moves":
            self._process_moves_roi(rx, ry, rw, rh)

        self._mode = None
        self._drag_start = None
        if self._drag_rect:
            self.canvas.delete(self._drag_rect)
            self._drag_rect = None
        self.canvas.config(cursor="crosshair")

    def _process_name_roi(self, rx, ry, rw, rh):
        """OCR tên Pokemon từ ROI"""
        crop = self.img_pil.crop((rx, ry, rx + rw, ry + rh))
        name = self._ocr_name(crop)
        print(f"[DEBUG] OCR result: '{name}'")
        
        if name:
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, name)
            self.status_var.set(f"✅ Quét tên: {name} (edit nếu sai)")
        else:
            response = tk.simpledialog.askstring("Manual Input", "Nhập tên Pokemon:")
            if response:
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, response.title())
                self.status_var.set(f"📝 Manual: {response.title()}")

    def _process_moves_roi(self, rx, ry, rw, rh):
        """OCR 4 moves từ ROI"""
        row_h = rh // 4
        moves_data = []

        for i in range(4):
            y_start = ry + i * row_h
            y_end = ry + (i + 1) * row_h if i < 3 else ry + rh
            crop = self.img_pil.crop((rx, y_start, rx + rw, y_end))
            move_name, move_pp = self._ocr_move_and_pp(crop)
            if move_name:
                moves_data.append((move_name, move_pp))
            else:
                moves_data.append(("", ""))

        # Fill vào entries
        entries = [
            (self.move1_entry, self.pp1_entry),
            (self.move2_entry, self.pp2_entry),
            (self.move3_entry, self.pp3_entry),
            (self.move4_entry, self.pp4_entry),
        ]

        for i, (move_name, move_pp) in enumerate(moves_data):
            if i < len(entries):
                entries[i][0].delete(0, tk.END)
                entries[i][0].insert(0, move_name)
                entries[i][1].delete(0, tk.END)
                entries[i][1].insert(0, move_pp)

        found = sum(1 for name, _ in moves_data if name)
        self.status_var.set(f"✅ Quét {found}/4 moves (manual edit nếu cần)")
        
        # Nếu all fail, show dialog help
        if found == 0:
            messagebox.showinfo("Manual Edit", 
                "OCR moves thất bại.\nVui lòng manual edit trong boxes bên phải.\n\nFormat: 'Move Name' và 'PP/PP'")


    # ──────────────────────────────────────────────────────
    def _ocr_name(self, image_pil):
        """OCR tên Pokemon"""
        if not HAS_OCR:
            return ""
        try:
            # Preprocess mạnh hơn
            img_np = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            
            # Upscale lớn hơn (crop nhỏ)
            scaled = cv2.resize(gray, None, fx=5, fy=5, interpolation=cv2.INTER_CUBIC)
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(scaled)
            
            # Threshold
            thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Denoise
            denoised = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
            
            # OCR
            config = "--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-"
            text = pytesseract.image_to_string(Image.fromarray(denoised), config=config).strip()
            
            # Clean
            text = re.sub(r"[^a-zA-Z\-]", "", text).strip()
            print(f"[DEBUG] OCR after clean: '{text}'")
            if len(text) >= 2:  # Giảm từ 3 xuống 2 (vì crop nhỏ)
                return text.title()
            return ""
        except Exception as e:
            print(f"[DEBUG] OCR exception: {e}")
            return ""

    def _ocr_move_and_pp(self, image_pil):
        """OCR move + PP"""
        if not HAS_OCR:
            return "", ""
        try:
            img_np = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            
            # Upscale
            scaled = cv2.resize(gray, None, fx=5, fy=5, interpolation=cv2.INTER_CUBIC)
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(scaled)
            
            # Threshold
            thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Denoise
            denoised = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
            
            config = "--psm 6 --oem 3"
            text = pytesseract.image_to_string(Image.fromarray(denoised), config=config).strip()
            print(f"[DEBUG] OCR move raw: '{text}'")

            # Parse: "Dragon Dance 15/15" or similar
            match = re.search(r"([a-zA-Z\s\-]+?)\s+(\d+/\d+)", text)
            if match:
                move_name = match.group(1).strip().title()
                move_pp = match.group(2).strip()
                print(f"[DEBUG] OCR move parsed: '{move_name}' '{move_pp}'")
                return move_name, move_pp

            # Fallback: chỉ tên move
            move_name = re.sub(r"[^a-zA-Z\s\-]", "", text).strip()
            if len(move_name) >= 2:
                print(f"[DEBUG] OCR move fallback: '{move_name}'")
                return move_name.title(), ""

            return "", ""
        except Exception as e:
            print(f"[DEBUG] OCR move exception: {e}")
            return "", ""

    # ──────────────────────────────────────────────────────
    def _browse_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")])
        if path:
            try:
                self.img_pil = Image.open(path).convert("RGB")
                self._render_image()
                self.status_var.set(f"✅ {Path(path).name}  ({self.img_pil.width}×{self.img_pil.height})")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không mở: {e}")

    def _paste_clipboard(self):
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                self.status_var.set("⚠️ Clipboard không có ảnh")
                return
            if isinstance(img, list) and img:
                img = Image.open(img[0]).convert("RGB")
            elif not isinstance(img, Image.Image):
                self.status_var.set("⚠️ Clipboard không phải ảnh")
                return
            else:
                img = img.convert("RGB")
            self.img_pil = img
            self._render_image()
            self.status_var.set(f"📋 Dán từ clipboard  ({self.img_pil.width}×{self.img_pil.height})")
        except Exception as e:
            self.status_var.set(f"❌ Lỗi: {e}")

    def _render_image(self):
        if not self.img_pil:
            return
        cw = self.canvas.winfo_width() or CANVAS_W
        ch = self.canvas.winfo_height() or CANVAS_H
        iw, ih = self.img_pil.size
        scale = min(cw / iw, ch / ih, 1.0)
        nw, nh = int(iw * scale), int(ih * scale)
        self.img_scale = scale
        self.img_offset = ((cw - nw) // 2, (ch - nh) // 2)
        resized = self.img_pil.resize((nw, nh), Image.LANCZOS)
        self.img_tk = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        ox, oy = self.img_offset
        self.canvas.create_image(ox, oy, anchor="nw", image=self.img_tk)

    # ──────────────────────────────────────────────────────
    def _add_pokemon(self):
        """Add Pokemon từ input boxes"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Thiếu tên", "Nhập tên Pokemon!")
            return

        # Kiểm tra trùng
        if any(p["name"].lower() == name.lower() for p in self.inventory):
            messagebox.showwarning("Trùng", f"{name} đã có rồi!")
            return

        # Lấy moves từ entries
        moves = []
        entries = [
            (self.move1_entry, self.pp1_entry),
            (self.move2_entry, self.pp2_entry),
            (self.move3_entry, self.pp3_entry),
            (self.move4_entry, self.pp4_entry),
        ]

        for move_entry, pp_entry in entries:
            move_name = move_entry.get().strip()
            move_pp = pp_entry.get().strip()
            if move_name:
                moves.append({"name": move_name, "pp": move_pp if move_pp else "?/?"})

        # Add vào inventory
        pokemon = {
            "id": self.next_id,
            "name": name,
            "moves": moves
        }
        self.inventory.append(pokemon)
        self.next_id += 1

        self.status_var.set(f"✅ Add {name} ({len(moves)} moves)")
        self._clear_inputs()
        self._update_list()

    def _clear_inputs(self):
        """Xóa tất cả input boxes"""
        self.name_entry.delete(0, tk.END)
        for entry in [self.move1_entry, self.move2_entry, self.move3_entry, self.move4_entry,
                      self.pp1_entry, self.pp2_entry, self.pp3_entry, self.pp4_entry]:
            entry.delete(0, tk.END)

    def _clear_all(self):
        """Xóa tất cả (confirm)"""
        if messagebox.askyesno("Xác nhận", f"Xóa tất cả {len(self.inventory)} Pokemon?"):
            self.inventory = []
            self.next_id = 1
            self._clear_inputs()
            self._update_list()
            self.status_var.set("🗑️ Đã xóa tất cả")

    def _update_list(self):
        """Cập nhật danh sách hiển thị"""
        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.inventory:
            tk.Label(self.list_frame, text="Chưa có Pokemon",
                     font=F_LABEL, bg=BG_DARK, fg=TEXT_MAIN).pack(padx=4, pady=8)
            return

        for pokemon in self.inventory:
            self._build_item_card(pokemon)

    def _build_item_card(self, pokemon):
        """Tạo card hiển thị 1 Pokemon"""
        card = tk.Frame(self.list_frame, bg=BG_CARD, bd=0, padx=4, pady=3)
        card.pack(fill="x", padx=2, pady=1)

        # Header: #ID Tên (X moves) [Delete]
        header = tk.Frame(card, bg=BG_CARD)
        header.pack(fill="x")
        header.columnconfigure(1, weight=1)

        pid = pokemon.get("id", "?")
        pname = pokemon.get("name", "?")
        move_count = len(pokemon.get("moves", []))

        tk.Label(header, text=f"#{pid}", font=F_SMALL,
                 bg=BG_CARD, fg=ACCENT, width=3).pack(side="left", padx=2)

        tk.Label(header, text=f"{pname} ({move_count} moves)", font=F_SMALL,
                 bg=BG_CARD, fg=TEXT_HI).pack(side="left", fill="x", expand=True, padx=2)

        tk.Button(header, text="❌", font=F_SMALL,
                 bg=WARN, fg=BG_DARK, relief="flat", padx=3, pady=0,
                 command=lambda id_val=pid: self._delete_pokemon(id_val)).pack(side="right", padx=2)

    def _delete_pokemon(self, pokemon_id):
        """Xóa Pokemon by ID"""
        self.inventory = [p for p in self.inventory if p.get("id") != pokemon_id]
        self._update_list()
        self.status_var.set(f"✕ Xóa Pokemon #{pokemon_id}")

    def _save_json(self):
        """Lưu vào JSON"""
        if not self.inventory:
            messagebox.showwarning("Trống", "Chưa có Pokemon để lưu!")
            return

        BAG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            BAG_PATH.write_text(json.dumps(self.inventory, indent=2, ensure_ascii=False),
                               encoding='utf-8')
            messagebox.showinfo("✅ Thành công", 
                              f"Đã lưu {len(self.inventory)} Pokemon vào:\n{BAG_PATH}")
            self.status_var.set(f"💾 Lưu xong {len(self.inventory)} Pokemon")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không lưu: {e}")
