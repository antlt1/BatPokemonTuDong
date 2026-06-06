"""
party_scanner_tab.py — Tab Party Scanner v3

Tính năng:
  1. Kéo 1 vùng 6 tên → auto chia 6 dải ngang → OCR 6 tên
  2. Kéo 1 vùng 4 move mỗi con → auto chia 2×2 → OCR tên + PP
  3. Ctrl+V paste từ clipboard
  4. Reset PP về đầy (pp_max)
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
ROOT      = Path(__file__).resolve().parent.parent.parent
TEAM_PATH = ROOT / "src" / "config" / "team_party.json"
MAX_SLOT  = 6
MOVE_COUNT = 4

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
class PartyScannnerTab:
    def __init__(self, parent, config):
        self.config     = config
        self.img_pil    = None
        self.img_tk     = None
        self.img_scale  = 1.0
        self.img_offset = (0, 0)

        # Chế độ kéo ROI
        self._mode      = None      # "party" | "moves" | None
        self._mode_pi   = None      # pokemon index (chỉ khi mode=="moves")
        self._mode_lbl  = None      # Label cập nhật ROI
        self._drag_start = None
        self._drag_rect  = None

        # 6 Pokemon slots
        self.slots = []
        self.party_roi = None   # ROI chung 6 tên

        self.frame = tk.Frame(parent, bg=BG_DARK)
        self._build_ui()

    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        self.frame.columnconfigure(0, weight=3)
        self.frame.columnconfigure(1, weight=2)
        self.frame.rowconfigure(1, weight=1)

        # Toolbar
        toolbar = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8)

        tk.Label(toolbar, text="📸  PARTY SCANNER", font=F_TITLE,
                 bg=BG_DARK, fg=ACCENT).pack(side="left", padx=(0, 20))

        tk.Button(toolbar, text="📂 Mở ảnh",
                  command=self._browse_image, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="📋 Dán ảnh  Ctrl+V",
                  command=self._paste_clipboard, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="💾 Lưu team_party.json",
                  command=self._save_json, font=F_LABEL,
                  bg=ACCENT2, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="🔄 Reset PP",
                  command=self._reset_pp, font=F_LABEL,
                  bg="#e09c6e", fg=BG_DARK, relief="flat",
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

        # Hint
        self.canvas.create_text(CANVAS_W//2, CANVAS_H//2,
            text="Ctrl+V để dán ảnh\nhoặc bấm  📂 Mở ảnh",
            font=("Consolas", 14), fill="#3e4451", justify="center", tags="hint")

        # Events
        self.canvas.bind("<Button-1>",        self._drag_press)
        self.canvas.bind("<B1-Motion>",       self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_release)

        # Panel phải (scroll)
        right = tk.Frame(self.frame, bg=BG_DARK)
        right.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.columnconfigure(0, weight=1)

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

        # Nút kéo party (chung)
        party_btn_frame = tk.Frame(self.list_frame, bg=BG_DARK)
        party_btn_frame.pack(fill="x", padx=4, pady=6)

        self.party_roi_lbl = tk.Label(party_btn_frame, text="[ — ]", font=F_SMALL,
                                       bg=BG_DARK, fg="#4b5263", width=18)
        self.party_roi_lbl.pack(side="right", padx=4)

        tk.Label(party_btn_frame, text="Party ROI:", font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN).pack(side="right", padx=4)

        tk.Button(party_btn_frame, text="🎯 Kéo vùng 6 tên Pokemon", font=F_SMALL,
                  bg=ACCENT, fg=BG_DARK, relief="flat", padx=6,
                  command=lambda: self._activate_roi("party", lbl=self.party_roi_lbl)
                  ).pack(side="left", padx=4)

        # Divider
        tk.Frame(self.list_frame, height=1, bg="#333842").pack(fill="x", padx=4)

        # 6 cards
        self._build_slot_cards()

    # ──────────────────────────────────────────────────────
    def _build_slot_cards(self):
        for i in range(MAX_SLOT):
            name_var  = tk.StringVar(value=f"Pokemon {i+1}")
            move_vars = [tk.StringVar(value="") for _ in range(MOVE_COUNT)]
            pp_vars   = [tk.StringVar(value="")  for _ in range(MOVE_COUNT)]

            self.slots.append({
                "name":      name_var,
                "moves":     move_vars,
                "move_pp":   pp_vars,
                "moves_roi": None,
            })

            self._build_one_card(self.list_frame, i)

    def _build_one_card(self, parent, idx):
        card = tk.Frame(parent, bg=BG_CARD, bd=0, padx=8, pady=6)
        card.pack(fill="x", padx=4, pady=4)
        card.columnconfigure(1, weight=1)

        # Header: #1  Tên: [Entry]
        header = tk.Frame(card, bg=BG_CARD)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        header.columnconfigure(1, weight=1)

        tk.Label(header, text=f"#{idx+1}", font=("Consolas", 11, "bold"),
                 bg=BG_CARD, fg=ACCENT, width=3).pack(side="left", padx=(0, 6))

        tk.Label(header, text="Tên:", font=F_LABEL,
                 bg=BG_CARD, fg=TEXT_MAIN).pack(side="left")

        tk.Entry(header, textvariable=self.slots[idx]["name"], font=F_LABEL,
                 bg=BG_MID, fg=TEXT_HI, insertbackground=ACCENT,
                 relief="flat", bd=4).pack(side="left", fill="x", expand=True, padx=6)

        # Kéo move ROI
        moves_roi_frame = tk.Frame(card, bg=BG_CARD)
        moves_roi_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        moves_roi_lbl = tk.Label(moves_roi_frame, text="[ — ]", font=F_SMALL,
                                 bg=BG_CARD, fg="#4b5263", width=18)
        moves_roi_lbl.pack(side="right", padx=(0, 2))

        tk.Label(moves_roi_frame, text="Move ROI:", font=F_SMALL,
                 bg=BG_CARD, fg="#7f848e").pack(side="right", padx=4)

        tk.Button(moves_roi_frame, text="🎯 Kéo vùng 4 move", font=F_SMALL,
                  bg=ACCENT, fg=BG_DARK, relief="flat", padx=6,
                  command=lambda lbl=moves_roi_lbl: self._activate_roi("moves", idx, lbl)
                  ).pack(side="left", padx=4)

        # 4 Move rows
        for mi in range(MOVE_COUNT):
            self._build_move_row(card, idx, mi)

        # Divider
        tk.Frame(parent, height=1, bg="#333842").pack(fill="x", padx=4)

    def _build_move_row(self, card, pi, mi):
        row = tk.Frame(card, bg=BG_CARD)
        row.grid(row=2+mi, column=0, columnspan=2, sticky="ew", pady=2)
        row.columnconfigure(1, weight=1)

        tk.Label(row, text=f"M{mi+1}:", font=F_SMALL,
                 bg=BG_CARD, fg="#7f848e", width=3).pack(side="left", padx=2)

        # Tên move
        tk.Entry(row, textvariable=self.slots[pi]["moves"][mi], font=F_SMALL,
                 bg=BG_MID, fg=TEXT_MAIN, insertbackground=ACCENT,
                 relief="flat", bd=3).pack(side="left", fill="x", expand=True, padx=2)

        # PP
        tk.Label(row, text="PP:", font=F_SMALL,
                 bg=BG_CARD, fg="#7f848e", width=3).pack(side="left", padx=2)

        tk.Entry(row, textvariable=self.slots[pi]["move_pp"][mi], font=F_SMALL,
                 bg=BG_MID, fg=TEXT_MAIN, insertbackground=ACCENT,
                 relief="flat", bd=3, width=8).pack(side="left", padx=2)

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
        if mode == "party":
            self.status_var.set("🖱  Kéo bao quanh CỘT 6 TÊN bên trái rồi thả")
        else:
            pname = self.slots[pi]["name"].get()
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

        if self._mode == "party":
            self._process_party_roi(rx, ry, rw, rh)
        elif self._mode == "moves":
            self._process_moves_roi(self._mode_pi, rx, ry, rw, rh)

        self._mode = self._mode_pi = self._mode_lbl = None
        self._drag_start = None
        self.canvas.config(cursor="crosshair")

    # ──────────────────────────────────────────────────────
    def _process_party_roi(self, rx, ry, rw, rh):
        self.party_roi = [rx, ry, rw, rh]
        if self._mode_lbl:
            self._mode_lbl.config(text=f"[{rx},{ry} {rw}×{rh}]", fg=ACCENT2)

        slot_h = rh // MAX_SLOT

        found = 0
        for i in range(MAX_SLOT):
            y_start = ry + i * slot_h
            y_end   = ry + (i+1) * slot_h if i < MAX_SLOT-1 else ry + rh
            crop = self.img_pil.crop((rx, y_start, rx+rw, y_end))
            name = self._ocr_name(crop)
            if name:
                self.slots[i]["name"].set(name)
                found += 1

        self.status_var.set(f"✅ Quét party xong — nhận {found}/6 tên. Sửa tay nếu cần.")

    def _process_moves_roi(self, pi, rx, ry, rw, rh):
        slot = self.slots[pi]
        slot["moves_roi"] = [rx, ry, rw, rh]
        if self._mode_lbl:
            self._mode_lbl.config(text=f"[{rx},{ry} {rw}×{rh}]", fg=ACCENT2)

        row_h = rh // MOVE_COUNT

        for mi in range(MOVE_COUNT):
            y_start = ry + mi * row_h
            y_end   = ry + (mi+1) * row_h if mi < MOVE_COUNT-1 else ry + rh
            crop = self.img_pil.crop((rx, y_start, rx+rw, y_end))
            move_name, move_pp = self._ocr_move_and_pp(crop)
            if move_name:
                slot["moves"][mi].set(move_name)
            if move_pp:
                slot["move_pp"][mi].set(move_pp)

        pname = slot["name"].get()
        self.status_var.set(f"✅ 4 move của [{pname}] đã quét. Sửa tay nếu cần.")

    # ──────────────────────────────────────────────────────
    def _ocr_name(self, crop_pil) -> str:
        if not HAS_OCR:
            return ""
        tcmd = self.config.get("ocr",{}).get("tesseract_cmd","").strip()
        if tcmd:
            pytesseract.pytesseract.tesseract_cmd = tcmd
        lang = self.config.get("ocr",{}).get("language","eng")

        arr  = np.array(crop_pil)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        big  = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        thr  = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
        raw  = pytesseract.image_to_string(
                   Image.fromarray(thr), lang=lang, config="--psm 7").strip()
        cleaned = re.sub(r"[^A-Za-z0-9 '\-]", " ", raw)
        cleaned = re.sub(r"\s+", " ", cleaned).strip().title()
        return cleaned

    def _ocr_move_and_pp(self, crop_pil) -> tuple:
        if not HAS_OCR:
            return "", ""
        tcmd = self.config.get("ocr",{}).get("tesseract_cmd","").strip()
        if tcmd:
            pytesseract.pytesseract.tesseract_cmd = tcmd
        lang = self.config.get("ocr",{}).get("language","eng")

        arr  = np.array(crop_pil)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        big  = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        thr  = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
        raw  = pytesseract.image_to_string(
                   Image.fromarray(thr), lang=lang, config="--psm 6").strip()

        pp_match = re.search(r"(\d{1,3}/\d{1,3})", raw)
        pp_str   = pp_match.group(1) if pp_match else ""

        name_part  = raw[:pp_match.start()] if pp_match else raw
        name_clean = re.sub(r"[^A-Za-z '\-]", " ", name_part)
        name_clean = re.sub(r"\s+", " ", name_clean).strip().title()

        return name_clean, pp_str

    # ──────────────────────────────────────────────────────
    def _reset_pp(self):
        """Khôi phục PP về đầy từ JSON"""
        if not TEAM_PATH.exists():
            messagebox.showwarning("Không có dữ liệu", "Chưa có team_party.json")
            return
        try:
            data = json.loads(TEAM_PATH.read_text(encoding="utf-8"))
            reset_count = 0
            for entry in data:
                i = entry.get("slot", 1) - 1
                if not (0 <= i < MAX_SLOT):
                    continue
                for mi, mv in enumerate(entry.get("moves", [])[:MOVE_COUNT]):
                    if isinstance(mv, dict):
                        pp_max = mv.get("pp_max")
                        if pp_max is not None:
                            self.slots[i]["move_pp"][mi].set(f"{pp_max}/{pp_max}")
                            reset_count += 1
            self.status_var.set(f"✅ Khôi phục {reset_count} move về PP đầy")
            messagebox.showinfo("OK", f"Khôi phục {reset_count} move về PP đầy!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể khôi phục: {e}")

    # ──────────────────────────────────────────────────────
    def _save_json(self):
        team = []
        for i, slot in enumerate(self.slots):
            name = slot["name"].get().strip()
            if not name or name == f"Pokemon {i+1}":
                continue
            moves = []
            for mi in range(MOVE_COUNT):
                entry = {"name": slot["moves"][mi].get().strip()}
                pp = slot["move_pp"][mi].get().strip()
                if pp:
                    parts = pp.split("/")
                    if len(parts) == 2:
                        try:
                            entry["pp_current"] = int(parts[0])
                            entry["pp_max"] = int(parts[1])
                        except ValueError:
                            pass
                moves.append(entry)
            team.append({
                "slot":       i+1,
                "name":       name,
                "party_roi":  self.party_roi,
                "moves":      moves,
                "moves_roi":  slot["moves_roi"],
            })
        if not team:
            messagebox.showwarning("Trống", "Chưa có Pokemon nào để lưu.")
            return
        TEAM_PATH.parent.mkdir(parents=True, exist_ok=True)
        TEAM_PATH.write_text(
            json.dumps(team, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_var.set(f"💾 Đã lưu {len(team)} Pokemon")
        messagebox.showinfo("OK", f"Lưu {len(team)} Pokemon thành công!")

    def load_existing(self):
        if not TEAM_PATH.exists():
            return
        try:
            data = json.loads(TEAM_PATH.read_text(encoding="utf-8"))
            if data and data[0].get("party_roi"):
                self.party_roi = data[0]["party_roi"]
            for entry in data:
                i = entry.get("slot", 1) - 1
                if not (0 <= i < MAX_SLOT):
                    continue
                slot = self.slots[i]
                slot["name"].set(entry.get("name", ""))
                slot["moves_roi"] = entry.get("moves_roi")
                for mi, mv in enumerate(entry.get("moves", [])[:MOVE_COUNT]):
                    if isinstance(mv, dict):
                        slot["moves"][mi].set(mv.get("name",""))
                        pp_current = mv.get("pp_current")
                        pp_max = mv.get("pp_max")
                        if pp_current is not None and pp_max is not None:
                            slot["move_pp"][mi].set(f"{pp_current}/{pp_max}")
                        elif mv.get("pp"):
                            slot["move_pp"][mi].set(mv.get("pp",""))
        except Exception:
            pass


# ═════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Party Scanner – Test")
    root.configure(bg=BG_DARK)
    root.geometry("1280x700")
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)
    dummy_config = {"ocr": {"language": "eng", "tesseract_cmd": ""}}
    tab = PartyScannnerTab(nb, dummy_config)
    nb.add(tab.frame, text="  📸 Party Scanner  ")
    tab.load_existing()
    root.mainloop()
