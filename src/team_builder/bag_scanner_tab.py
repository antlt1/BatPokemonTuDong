"""
bag_scanner_tab.py — Tab 4: Bag/Inventory Scanner

Tính năng:
  1. Kéo vùng tên Pokemon nhiều con → auto chia thành từng slot → OCR tên
  2. Kéo vùng 4 move cho mỗi con → auto chia 2×2 → OCR move + PP
  3. Ctrl+V paste từ clipboard
  4. Lưu tất cả vào pokemon_bag_inventory.json
  5. Pagination: Page 1, 2, 3... cho tối đa ~100 Pokemon
"""

import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

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
MAX_PER_PAGE = 6
MOVE_COUNT   = 4

CANVAS_W = 780
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
        self._mode       = None      # "pokemon_names" | "moves" | None
        self._mode_pi    = None      # pokemon index (khi mode=="moves")
        self._mode_lbl   = None      # Label cập nhật ROI
        self._drag_start = None
        self._drag_rect  = None

        # Danh sách Pokemon quét được
        self.bag_inventory = []      # List[{"name": str, "moves": [...]}]
        self.current_page = 0

        self.frame = tk.Frame(parent, bg=BG_DARK)
        self._build_ui()
        self._load_inventory()

    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        self.frame.columnconfigure(0, weight=3)
        self.frame.columnconfigure(1, weight=2)
        self.frame.rowconfigure(1, weight=1)

        # Toolbar
        toolbar = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8)

        tk.Label(toolbar, text="🎒  BAG SCANNER", font=F_TITLE,
                 bg=BG_DARK, fg=ACCENT).pack(side="left", padx=(0, 20))

        tk.Button(toolbar, text="📂 Mở ảnh",
                  command=self._browse_image, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="📋 Dán ảnh  Ctrl+V",
                  command=self._paste_clipboard, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="💾 Lưu JSON",
                  command=self._save_json, font=F_LABEL,
                  bg=ACCENT2, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="🗑️  Xóa All",
                  command=self._clear_inventory, font=F_LABEL,
                  bg=WARN, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="Mở ảnh hoặc Ctrl+V → rồi kéo vùng")
        tk.Label(toolbar, textvariable=self.status_var, font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN).pack(side="left", padx=12)

        # Bind Ctrl+V
        self.frame.bind_all("<Control-v>", lambda e: self._paste_clipboard())

        # Canvas (trái)
        canvas_frame = tk.Frame(self.frame, bg=BG_MID, bd=1, relief="solid")
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)

        self.canvas = tk.Canvas(canvas_frame, bg="#111316",
                                width=CANVAS_W, height=CANVAS_H,
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(CANVAS_W//2, CANVAS_H//2,
            text="Ctrl+V để dán ảnh\nhoặc bấm 📂 Mở ảnh",
            font=("Consolas", 14), fill="#3e4451", justify="center", tags="hint")

        self.canvas.bind("<Button-1>",        self._drag_press)
        self.canvas.bind("<B1-Motion>",       self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_release)

        # Panel phải (scroll list + pagination)
        right = tk.Frame(self.frame, bg=BG_DARK)
        right.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        # List
        scroll_canvas = tk.Canvas(right, bg=BG_DARK, highlightthickness=0)
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

        # Pagination footer
        footer = tk.Frame(right, bg=BG_DARK, pady=6)
        footer.pack(fill="x", side="bottom")
        footer.columnconfigure(0, weight=1)

        self.pagination_var = tk.StringVar(value="Page 0/0")
        tk.Label(footer, textvariable=self.pagination_var, font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN).pack(side="left", padx=6)

        self.prev_btn = tk.Button(footer, text="< Prev", command=self._prev_page,
                                   font=F_SMALL, bg=BG_MID, fg=TEXT_HI, relief="flat", padx=6)
        self.prev_btn.pack(side="left", padx=2)

        self.next_btn = tk.Button(footer, text="Next >", command=self._next_page,
                                   font=F_SMALL, bg=BG_MID, fg=TEXT_HI, relief="flat", padx=6)
        self.next_btn.pack(side="left", padx=2)

        self._update_list()

    # ──────────────────────────────────────────────────────
    def _load_inventory(self):
        """Load danh sách Pokemon từ JSON"""
        if BAG_PATH.exists():
            try:
                data = json.loads(BAG_PATH.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    self.bag_inventory = data
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không đọc JSON: {e}")
        self._update_list()



    def _update_list(self):
        """Cập nhật danh sách Pokemon trên page hiện tại"""
        # Xóa toàn bộ items cũ
        for w in self.list_frame.winfo_children():
            w.destroy()

        total_pages = (len(self.bag_inventory) + MAX_PER_PAGE - 1) // MAX_PER_PAGE
        if total_pages == 0:
            total_pages = 1
        
        # Giới hạn page
        self.current_page = max(0, min(self.current_page, total_pages - 1))

        # Hiển thị page info
        page_num = self.current_page + 1
        self.pagination_var.set(f"Page {page_num}/{total_pages}  ({len(self.bag_inventory)} tổng)")

        # Items cho page này
        start_idx = self.current_page * MAX_PER_PAGE
        end_idx = start_idx + MAX_PER_PAGE
        items = self.bag_inventory[start_idx:end_idx]

        if not items:
            tk.Label(self.list_frame, text="Chưa có Pokemon nào",
                     font=F_LABEL, bg=BG_DARK, fg=TEXT_MAIN).pack(padx=4, pady=12)
            return

        for item in items:
            self._build_item_card(item)

        # Update button states
        self.prev_btn.config(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.config(state="normal" if page_num < total_pages else "disabled")

    def _build_item_card(self, item):
        """Tạo card hiển thị 1 Pokemon"""
        card = tk.Frame(self.list_frame, bg=BG_CARD, bd=0, padx=6, pady=4)
        card.pack(fill="x", padx=4, pady=2)

        # Tên Pokemon (đậm)
        pname = item.get("name", "Unknown")
        tk.Label(card, text=f"🔸 {pname}", font=("Consolas", 10, "bold"),
                 bg=BG_CARD, fg=ACCENT).pack(anchor="w", padx=2)

        # Moves
        moves = item.get("moves", [])
        for move in moves:
            if isinstance(move, dict):
                mname = move.get("name", "?")
                mpp = move.get("pp", "?")
                txt = f"  • {mname}  ({mpp})"
            else:
                txt = f"  • {move}"
            tk.Label(card, text=txt, font=F_SMALL,
                     bg=BG_CARD, fg=TEXT_MAIN).pack(anchor="w", padx=4)

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_list()

    def _next_page(self):
        total = (len(self.bag_inventory) + MAX_PER_PAGE - 1) // MAX_PER_PAGE
        if self.current_page < total - 1:
            self.current_page += 1
            self._update_list()

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
                self.status_var.set("⚠️  Clipboard không có ảnh")
                return
            if isinstance(img, list) and img:
                img = Image.open(img[0]).convert("RGB")
            elif not isinstance(img, Image.Image):
                self.status_var.set("⚠️  Clipboard không phải ảnh")
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
        cw = self.canvas.winfo_width()  or CANVAS_W
        ch = self.canvas.winfo_height() or CANVAS_H
        iw, ih = self.img_pil.size
        scale = min(cw/iw, ch/ih, 1.0)
        nw, nh = int(iw*scale), int(ih*scale)
        self.img_scale  = scale
        self.img_offset = ((cw-nw)//2, (ch-nh)//2)
        resized = self.img_pil.resize((nw, nh), Image.LANCZOS)
        self.img_tk = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        ox, oy = self.img_offset
        self.canvas.create_image(ox, oy, anchor="nw", image=self.img_tk)

    # ──────────────────────────────────────────────────────
    def _activate_roi(self, mode, pi=None, lbl=None):
        if not self.img_pil:
            messagebox.showwarning("Chưa có ảnh", "Hãy tải ảnh trước!")
            return
        self._mode     = mode
        self._mode_pi  = pi
        self._mode_lbl = lbl
        self._drag_start = None
        self.canvas.config(cursor="tcross")
        if mode == "pokemon_names":
            self.status_var.set("🖱  Kéo bao quanh CỘT TÊN POKEMON (có thể nhiều con) rồi thả")
        else:
            if pi is not None:
                pname = self.bag_inventory[pi]["name"] if pi < len(self.bag_inventory) else "?"
                self.status_var.set(f"🖱  Kéo bao quanh BẢNG 4 MOVE của [{pname}] rồi thả")

    def _drag_press(self, event):
        if self._mode is None:
            return
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
            return

        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y
        ox, oy  = self.img_offset
        scale   = self.img_scale

        rx = int((min(x0,x1) - ox) / scale)
        ry = int((min(y0,y1) - oy) / scale)
        rw = int(abs(x1-x0) / scale)
        rh = int(abs(y1-y0) / scale)
        iw, ih = self.img_pil.size
        rx = max(0, min(rx, iw-1))
        ry = max(0, min(ry, ih-1))
        rw = max(1, min(rw, iw-rx))
        rh = max(1, min(rh, ih-ry))

        if self._mode == "pokemon_names":
            self._process_pokemon_names(rx, ry, rw, rh)
        elif self._mode == "moves":
            self._process_moves_roi(self._mode_pi, rx, ry, rw, rh)

        self._mode = self._mode_pi = self._mode_lbl = None
        self._drag_start = None
        self.canvas.config(cursor="crosshair")

    # ──────────────────────────────────────────────────────
    def _process_pokemon_names(self, rx, ry, rw, rh):
        """Quét danh sách tên Pokemon từ vùng được kéo"""
        # Chia thành nhiều slot (không cố định như Party Scanner)
        # Giả sử: kéo 1 cột dài chứa tên Pokemon → auto chia thành các dòng
        # Trick: dùng height/tính toán để tìm ~15-20 con (nếu bag có ~100)
        
        crop = self.img_pil.crop((rx, ry, rx+rw, ry+rh))
        
        # Heuristic: giả sử mỗi tên Pokemon cao ~40-50px khi quét
        estimated_per_pokemon = 45
        num_pokemon = max(1, rh // estimated_per_pokemon)
        
        found = 0
        for i in range(num_pokemon):
            y_start = ry + (i * rh // num_pokemon)
            y_end   = ry + ((i+1) * rh // num_pokemon)
            slot_crop = self.img_pil.crop((rx, y_start, rx+rw, y_end))
            name = self._ocr_name(slot_crop)
            if name:
                # Kiểm tra xem đã có chưa
                existing = [p["name"].lower() for p in self.bag_inventory]
                if name.lower() not in existing:
                    self.bag_inventory.append({
                        "name": name,
                        "moves": []
                    })
                    found += 1

        self.status_var.set(f"✅ Quét xong — thêm {found} Pokemon mới.")
        self._update_list()

    def _process_moves_roi(self, pi, rx, ry, rw, rh):
        """Quét 4 move của Pokemon thứ pi"""
        if pi is None or pi >= len(self.bag_inventory):
            return

        slot = self.bag_inventory[pi]
        row_h = rh // MOVE_COUNT

        slot["moves"] = []  # Reset
        for mi in range(MOVE_COUNT):
            y_start = ry + mi * row_h
            y_end   = ry + (mi+1) * row_h if mi < MOVE_COUNT-1 else ry + rh
            crop = self.img_pil.crop((rx, y_start, rx+rw, y_end))
            move_name, move_pp = self._ocr_move_and_pp(crop)
            if move_name:
                slot["moves"].append({
                    "name": move_name,
                    "pp": move_pp if move_pp else "?/?"
                })

        pname = slot.get("name", "?")
        self.status_var.set(f"✅ Quét moves của [{pname}]")
        self._update_list()

    # ──────────────────────────────────────────────────────
    def _ocr_name(self, image_pil):
        """OCR tên Pokemon từ ảnh (PIL Image)"""
        if not HAS_OCR:
            return ""
        try:
            # Preprocess
            img_np = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # OCR
            config = "--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- "
            text = pytesseract.image_to_string(Image.fromarray(thresh), config=config).strip()
            
            # Clean
            text = re.sub(r"[^a-zA-Z\- ]", "", text).strip()
            if len(text) >= 3:
                return text.title()
            return ""
        except Exception:
            return ""

    def _ocr_move_and_pp(self, image_pil):
        """OCR tên move + PP (e.g., 'Dragon Dance 15/15')"""
        if not HAS_OCR:
            return "", ""
        try:
            img_np = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            config = "--psm 6 --oem 3"
            text = pytesseract.image_to_string(Image.fromarray(thresh), config=config).strip()
            
            # Parse: "Dragon Dance 15/15" or similar
            match = re.search(r"([a-zA-Z\s\-]+?)\s+(\d+/\d+)", text)
            if match:
                move_name = match.group(1).strip().title()
                move_pp = match.group(2).strip()
                return move_name, move_pp
            
            # Fallback: chỉ tên move
            move_name = re.sub(r"[^a-zA-Z\s\-]", "", text).strip()
            if len(move_name) >= 3:
                return move_name.title(), ""
            
            return "", ""
        except Exception:
            return "", ""

    # ──────────────────────────────────────────────────────
    def _save_json(self):
        """Lưu danh sách Pokemon vào JSON"""
        BAG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            BAG_PATH.write_text(json.dumps(self.bag_inventory, indent=2, ensure_ascii=False), 
                               encoding='utf-8')
            messagebox.showinfo("✅ Thành công", f"Đã lưu {len(self.bag_inventory)} Pokemon vào:\n{BAG_PATH}")
            self.status_var.set(f"💾 Đã lưu {len(self.bag_inventory)} Pokemon")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không lưu JSON: {e}")

    def _clear_inventory(self):
        """Xóa toàn bộ danh sách"""
        if messagebox.askyesno("Xác nhận", f"Xóa tất cả {len(self.bag_inventory)} Pokemon?"):
            self.bag_inventory = []
            self.current_page = 0
            self._update_list()
            self.status_var.set("🗑️  Đã xóa tất cả")
