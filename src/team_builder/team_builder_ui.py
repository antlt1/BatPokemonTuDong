"""
team_builder_ui.py – Menu 4: UI tkinter để đọc team 6 Pokemon từ ảnh chụp.

Workflow:
  1. Paste/load ảnh team tổng (6 con) → OCR tên từng slot.
  2. Với mỗi Pokemon, paste/load ảnh màn hình Fight → OCR 4 move (tên + type + PP).
  3. Cho chỉnh sửa thủ công qua Text widget.
  4. Bấm Save → ghi src/config/team_party.json.

Format team_party.json:
[
  {
    "slot": 1,
    "name": "Gardevoir",
    "types": ["psychic", "fairy"],
    "moves": [
      {"name": "Surf", "type": "water", "power": 90, "accuracy": 100, "pp_current": 14, "pp_max": 15},
      ...
    ]
  },
  ...
]
"""

import json
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageTk

from src.ocr_utils import (
    POKEMON_NAMES,
    KNOWN_MOVES,
    normalize_text as normalize,
    preprocess_for_ocr as preprocess,
    ocr_text as ocr_block,
    parse_move_name,
    parse_pp,
    guess_move_data,
    ocr_variants,
    fuzzy_match_pokemon,
    extract_pokemon_name_from_ocr,
    load_image_cv2,
    set_tesseract_path as init_tesseract,
)

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
TEAM_PATH = ROOT / "src" / "config" / "team_party.json"
DATA_DIR = ROOT / "src" / "data"
POKEMON_CACHE_DIR = DATA_DIR / "pokeapi_cache" / "pokemon"
MOVE_CACHE_DIR = DATA_DIR / "pokeapi_cache" / "moves"

for _d in (POKEMON_CACHE_DIR, MOVE_CACHE_DIR, ROOT / "src" / "runtime"):
    _d.mkdir(parents=True, exist_ok=True)


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_team() -> list:
    if TEAM_PATH.exists():
        with TEAM_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_team(team: list):
    TEAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TEAM_PATH.open("w", encoding="utf-8") as f:
        json.dump(team, f, indent=2, ensure_ascii=False)


def ocr_single_line(img_bgr, config, psm=7) -> str:
    processed = preprocess(img_bgr)
    pil = Image.fromarray(processed)
    lang = config.get("ocr", {}).get("language", "eng")
    return pytesseract.image_to_string(pil, lang=lang, config=f"--psm {psm}").strip()


def ocr_team_from_image(img_bgr, config) -> list:
    """
    OCR ảnh team panel (6 slot dọc).
    Layout mỗi slot: [sprite trái ~45%] [tên Pokemon + Lv.xx bên phải]
    Dùng whitelist chỉ chữ cái + fuzzy match với danh sách Pokemon.
    """
    h, w = img_bgr.shape[:2]
    slot_h = h // 6
    names = []

    for i in range(6):
        y_start = i * slot_h
        y_end   = min((i + 1) * slot_h, h)

        # Sprite chiếm ~45% bên trái → lấy từ 45% trở đi cho tên
        x_start = int(w * 0.45)
        slot_crop = img_bgr[y_start:y_end, x_start:]

        # Tên thường ở phần trên mỗi slot (50-60% cao)
        sh = slot_crop.shape[0]
        name_row = slot_crop[:max(int(sh * 0.55), 1), :]

        # OCR với whitelist chữ cái
        text = ocr_variants(name_row, config, psm=7, name_mode=True)
        if not text.strip():
            text = ocr_variants(slot_crop, config, psm=7, name_mode=True)

        raw_name = extract_pokemon_name_from_ocr(text)
        # Fuzzy match với danh sách Pokemon thật
        matched = fuzzy_match_pokemon(raw_name)
        names.append(normalize(matched))

    return names


def ocr_moves_from_fight_image(img_bgr, config) -> list:
    """
    OCR ảnh panel Fight (4 dòng dọc).
    Layout thực tế: mỗi dòng = [Tên move (trái)] [PP current/max (phải)]
    Ví dụ:  Surf       15/15
            Ice Beam   16/16
            Toxic      10/10
            Recover     8/8
    Chia ảnh thành 4 strip ngang bằng nhau, mỗi strip OCR riêng.
    """
    h, w = img_bgr.shape[:2]
    row_h = h // 4

    moves = []
    for i in range(4):
        y1 = i * row_h
        y2 = min((i + 1) * row_h, h)
        row = img_bgr[y1:y2, :]

        rh, rw = row.shape[:2]
        # Cột tên: 65% bên trái (tránh bị nhiễu bởi số PP)
        name_cell = row[:, : int(rw * 0.65)]
        # Cột PP: 35% bên phải
        pp_cell   = row[:, int(rw * 0.60):]

        # OCR tên move (psm=7 = single line)
        name_text = ocr_single_line(name_cell, config, psm=7)
        move_name = parse_move_name(name_text)

        # OCR PP (psm=7)
        pp_text = ocr_single_line(pp_cell, config, psm=7)
        # fallback: OCR toàn dòng để tìm PP nếu cột PP trống
        if not re.search(r"\d+/\d+", pp_text):
            full_text = ocr_single_line(row, config, psm=7)
            pp_text = full_text

        pp_current, pp_max = parse_pp(pp_text)

        # Tra cứu data move từ bảng tĩnh
        data = guess_move_data(move_name)

        moves.append({
            "name": normalize(move_name) if move_name else f"Move{i+1}",
            "type": data.get("type", "normal"),
            "power": data.get("power", 0),
            "accuracy": data.get("accuracy", 100),
            "pp_current": pp_current if pp_current is not None else pp_max,
            "pp_max": pp_max,
        })

    return moves


# ========================= GUI =========================

class TeamBuilderApp(tk.Frame):
    def __init__(self, master, config):
        super().__init__(master, bg="#1e1e2e")
        self.config_data = config
        self.master_window = master if isinstance(master, tk.Tk) else master.winfo_toplevel()
        
        # State
        self.current_pokemon_index = 0  # 0..5
        self.team = load_team()
        # Đảm bảo team có đủ 6 slot
        while len(self.team) < 6:
            slot = len(self.team) + 1
            self.team.append({
                "slot": slot, "name": "", "types": [], "moves": []
            })

        self._build_ui()
        self._refresh_team_panel()
        self._load_pokemon_editor(0)

    # ---------- UI BUILD ----------

    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # --- Left panel: Team list ---
        left = tk.Frame(self, bg="#181825", width=200)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        left.grid_propagate(False)

        tk.Label(left, text="🎮 Team 6 Pokemon", bg="#181825", fg="#cdd6f4",
                 font=("Segoe UI", 11, "bold")).pack(pady=(10, 4))

        self.team_listbox = tk.Listbox(left, bg="#313244", fg="#cdd6f4",
                                        selectbackground="#89b4fa", activestyle="none",
                                        font=("Segoe UI", 10), borderwidth=0,
                                        highlightthickness=0)
        self.team_listbox.pack(fill="both", expand=True, padx=6, pady=4)
        self.team_listbox.bind("<<ListboxSelect>>", self._on_team_select)

        btn_frame = tk.Frame(left, bg="#181825")
        btn_frame.pack(fill="x", padx=6, pady=4)
        tk.Button(btn_frame, text="💾 Save Team", command=self._save_team,
                  bg="#a6e3a1", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2").pack(fill="x", pady=2)
        tk.Button(btn_frame, text="🔄 Reset Slot", command=self._reset_slot,
                  bg="#f38ba8", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2").pack(fill="x", pady=2)

        # --- Right panel: Editor ---
        right = tk.Frame(self, bg="#1e1e2e")
        right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)

        # Pokemon name row
        name_row = tk.Frame(right, bg="#1e1e2e")
        name_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tk.Label(name_row, text="Tên Pokemon:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left")
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(name_row, textvariable=self.name_var,
                                   bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                                   font=("Segoe UI", 11), relief="flat", width=25)
        self.name_entry.pack(side="left", padx=6)

        # Types row
        types_row = tk.Frame(right, bg="#1e1e2e")
        types_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        tk.Label(types_row, text="Type (vd: psychic,fairy):", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left")
        self.types_var = tk.StringVar()
        tk.Entry(types_row, textvariable=self.types_var,
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 font=("Segoe UI", 11), relief="flat", width=30).pack(side="left", padx=6)

        # --- Image buttons ---
        img_row = tk.Frame(right, bg="#1e1e2e")
        img_row.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        tk.Button(img_row, text="📷 Load ảnh Team tổng",
                  command=self._load_team_image,
                  bg="#89dceb", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2", padx=8).pack(side="left", padx=(0, 6))

        tk.Button(img_row, text="⚔️ Load ảnh Fight (4 move)",
                  command=self._load_fight_image,
                  bg="#f9e2af", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2", padx=8).pack(side="left", padx=(0, 6))

        tk.Button(img_row, text="🔍 OCR Tên Pokemon",
                  command=self._ocr_name_only,
                  bg="#cba6f7", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2", padx=8).pack(side="left")

        # --- Move editor (JSON text) ---
        tk.Label(right, text="Moves JSON (4 move – sửa trực tiếp):",
                 bg="#1e1e2e", fg="#a6adc8", font=("Segoe UI", 9)).grid(
                 row=3, column=0, sticky="w")

        self.moves_text = scrolledtext.ScrolledText(
            right, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
            font=("Consolas", 10), relief="flat", height=18
        )
        self.moves_text.grid(row=4, column=0, sticky="nsew", pady=(2, 4))
        right.rowconfigure(4, weight=1)

        # Status bar
        self.status_var = tk.StringVar(value="Sẵn sàng.")
        tk.Label(right, textvariable=self.status_var, bg="#1e1e2e", fg="#6c7086",
                 font=("Segoe UI", 9), anchor="w").grid(row=5, column=0, sticky="ew")

    # ---------- Team panel ----------

    def _refresh_team_panel(self):
        self.team_listbox.delete(0, "end")
        for i, poke in enumerate(self.team):
            name = poke.get("name") or f"(Slot {i+1})"
            prefix = "▶" if i == self.current_pokemon_index else "  "
            self.team_listbox.insert("end", f"{prefix} Slot {i+1}: {name}")
        self.team_listbox.selection_clear(0, "end")
        self.team_listbox.selection_set(self.current_pokemon_index)

    def _on_team_select(self, event):
        sel = self.team_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx == self.current_pokemon_index:
            return
        self._commit_current()
        self._load_pokemon_editor(idx)

    def _load_pokemon_editor(self, idx: int):
        self.current_pokemon_index = idx
        poke = self.team[idx]
        self.name_var.set(poke.get("name", ""))
        self.types_var.set(",".join(poke.get("types", [])))
        moves = poke.get("moves", [])
        self.moves_text.delete("1.0", "end")
        self.moves_text.insert("1.0", json.dumps(moves, indent=2, ensure_ascii=False))
        self._refresh_team_panel()
        self.status_var.set(f"Đang chỉnh Slot {idx+1}.")

    def _commit_current(self):
        """Lưu dữ liệu từ editor vào self.team tại current index"""
        idx = self.current_pokemon_index
        self.team[idx]["name"] = normalize(self.name_var.get())
        self.team[idx]["types"] = [
            t.strip().lower()
            for t in self.types_var.get().split(",")
            if t.strip()
        ]
        try:
            moves_json = self.moves_text.get("1.0", "end").strip()
            if moves_json:
                self.team[idx]["moves"] = json.loads(moves_json)
        except json.JSONDecodeError:
            pass  # Giữ nguyên nếu JSON sai

    # ---------- Image OCR actions ----------

    def _load_team_image(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh team tổng quan",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        img = load_image_cv2(path)
        if img is None:
            messagebox.showerror("Lỗi", "Không load được ảnh!")
            return
        names = ocr_team_from_image(img, self.config_data)
        # Cập nhật tên vào team
        for i, name in enumerate(names):
            if name:
                self.team[i]["name"] = name
        self._refresh_team_panel()
        self._load_pokemon_editor(self.current_pokemon_index)
        self.status_var.set(f"OCR team xong: {names}")

    def _load_fight_image(self):
        path = filedialog.askopenfilename(
            title=f"Chọn ảnh panel Fight của Slot {self.current_pokemon_index+1}",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        img = load_image_cv2(path)
        if img is None:
            messagebox.showerror("Lỗi", "Không load được ảnh!")
            return
        moves = ocr_moves_from_fight_image(img, self.config_data)
        self.moves_text.delete("1.0", "end")
        self.moves_text.insert("1.0", json.dumps(moves, indent=2, ensure_ascii=False))
        self.status_var.set(
            f"OCR moves Slot {self.current_pokemon_index+1} xong. Kiểm tra và sửa nếu cần."
        )

    def _ocr_name_only(self):
        """Load ảnh bất kỳ và OCR tên Pokemon (dòng đầu tiên)"""
        path = filedialog.askopenfilename(
            title="Chọn ảnh để OCR tên Pokemon",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        img = load_image_cv2(path)
        if img is None:
            messagebox.showerror("Lỗi", "Không load được ảnh!")
            return
        text = ocr_single_line(img, self.config_data, psm=7)
        name = parse_move_name(text)
        if name:
            self.name_var.set(normalize(name))
            self.status_var.set(f"OCR tên: '{name}'")
        else:
            self.status_var.set("Không OCR được tên, hãy nhập thủ công.")

    # ---------- Save / Reset ----------

    def _save_team(self):
        self._commit_current()
        # Kiểm tra có slot nào còn trống không
        empty_slots = [i+1 for i, p in enumerate(self.team) if not p.get("name")]
        if empty_slots:
            ok = messagebox.askyesno(
                "Cảnh báo",
                f"Slot {empty_slots} chưa có tên Pokemon. Vẫn lưu?"
            )
            if not ok:
                return
        # Đánh lại slot index
        for i, p in enumerate(self.team):
            p["slot"] = i + 1
        save_team(self.team)
        self._refresh_team_panel()
        messagebox.showinfo("Đã lưu", f"Đã lưu team vào:\n{TEAM_PATH}")
        self.status_var.set(f"Đã lưu {TEAM_PATH}")

    def _reset_slot(self):
        idx = self.current_pokemon_index
        ok = messagebox.askyesno("Xác nhận", f"Reset Slot {idx+1}?")
        if not ok:
            return
        self.team[idx] = {"slot": idx+1, "name": "", "types": [], "moves": []}
        self._load_pokemon_editor(idx)
        self.status_var.set(f"Đã reset Slot {idx+1}.")


def run_team_builder():
    """Mở Team Builder trong window riêng (standalone mode)"""
    config = load_config()
    init_tesseract(config)
    window = tk.Tk()
    window.title("Team Builder – Menu 4")
    window.geometry("980x700")
    window.resizable(True, True)
    
    app = TeamBuilderApp(window, config)
    app.pack(fill="both", expand=True)
    window.mainloop()


class CalibrateMoveROIApp(tk.Frame):
    """Tab để calibrate 4 move slot ROI bằng drag & drop"""
    def __init__(self, master, config):
        super().__init__(master, bg="#1e1e2e")
        self.config_data = config
        self.image_cv = None
        self.image_tk = None
        self.roi_list = list(config.get("roi", {}).get("move_slots", [
            [1252, 308, 237, 58],
            [1252, 386, 243, 55],
            [1254, 452, 242, 61],
            [1257, 522, 243, 65]
        ]))
        self.dragging_slot = None
        self.drag_start = None

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # Top: Instructions
        top_frame = tk.Frame(self, bg="#1e1e2e")
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

        tk.Label(top_frame, text="📋 Calibrate Move Slots ROI",
                bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 12, "bold")).pack(side="left")

        tk.Button(top_frame, text="📸 Load Screenshot", command=self._load_screenshot,
                 bg="#89dceb", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                 relief="flat", cursor="hand2", padx=8).pack(side="left", padx=(20, 0))

        tk.Button(top_frame, text="💾 Save ROI", command=self._save_roi,
                 bg="#a6e3a1", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                 relief="flat", cursor="hand2", padx=8).pack(side="left", padx=6)

        # Main: Canvas + ROI info
        main_frame = tk.Frame(self, bg="#1e1e2e")
        main_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=8)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Canvas for image
        self.canvas = tk.Canvas(main_frame, bg="#313244", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Right: ROI info
        info_frame = tk.Frame(main_frame, bg="#181825", width=200)
        info_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        info_frame.grid_propagate(False)

        tk.Label(info_frame, text="Move Slots ROI", bg="#181825", fg="#cdd6f4",
                font=("Segoe UI", 11, "bold")).pack(pady=(10, 4))

        self.roi_text = tk.Text(info_frame, bg="#313244", fg="#cdd6f4",
                               font=("Consolas", 9), height=10, width=22,
                               relief="flat", highlightthickness=0)
        self.roi_text.pack(fill="both", expand=True, padx=6, pady=4)

        self.status_var = tk.StringVar(value="Load ảnh screenshot để bắt đầu.")
        tk.Label(info_frame, textvariable=self.status_var, bg="#181825", fg="#6c7086",
                font=("Segoe UI", 8), wraplength=180, justify="left").pack(padx=6, pady=4)

    def _load_screenshot(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh battle fight panel",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        self.image_cv = load_image_cv2(path)
        if self.image_cv is None:
            messagebox.showerror("Lỗi", "Không load được ảnh!")
            return
        self._display_image()
        self.status_var.set("Nhấn + kéo để adjust ROI từng move slot")

    def _display_image(self):
        """Hiển thị ảnh + các hình chữ nhật ROI lên canvas"""
        if self.image_cv is None:
            return

        h, w = self.image_cv.shape[:2]
        # Scale để fit canvas
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w, canvas_h = 800, 600

        scale = min(canvas_w / w, canvas_h / h, 1.0)
        new_w = int(w * scale)
        new_h = int(h * scale)

        img_small = cv2.resize(self.image_cv, (new_w, new_h))
        img_bgr = img_small.copy()

        # Vẽ ROI rectangles
        for i, roi in enumerate(self.roi_list):
            x, y, roi_w, roi_h = roi
            x, y = int(x * scale), int(y * scale)
            roi_w, roi_h = int(roi_w * scale), int(roi_h * scale)
            color = (0, 255, 0) if i != self.dragging_slot else (0, 0, 255)
            cv2.rectangle(img_bgr, (x, y), (x + roi_w, y + roi_h), color, 2)
            cv2.putText(img_bgr, f"M{i+1}", (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (0, 255, 0), 1)

        # Convert to PhotoImage
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        from PIL import Image as PILImage, ImageTk as PILImageTk
        pil_img = PILImage.fromarray(img_rgb)
        self.image_tk = PILImageTk.PhotoImage(pil_img)
        self.scale_factor = scale

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.image_tk, anchor="nw")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        self._update_roi_text()

    def _on_canvas_click(self, event):
        """Detect click trên ROI nào"""
        if self.image_cv is None:
            return
        x, y = event.x, event.y
        for i, roi in enumerate(self.roi_list):
            rx, ry, rw, rh = roi
            rx, ry = int(rx * self.scale_factor), int(ry * self.scale_factor)
            rw, rh = int(rw * self.scale_factor), int(rh * self.scale_factor)
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                self.dragging_slot = i
                self.drag_start = (x, y)
                break

    def _on_canvas_drag(self, event):
        """Drag ROI"""
        if self.dragging_slot is None or self.drag_start is None:
            return
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]

        # Update ROI position
        roi = self.roi_list[self.dragging_slot]
        roi[0] = int(roi[0] + dx / self.scale_factor)
        roi[1] = int(roi[1] + dy / self.scale_factor)

        self.drag_start = (event.x, event.y)
        self._display_image()

    def _on_canvas_release(self, event):
        """Stop dragging"""
        self.dragging_slot = None
        self.drag_start = None

    def _update_roi_text(self):
        """Update text widget với ROI data"""
        self.roi_text.delete("1.0", "end")
        for i, roi in enumerate(self.roi_list):
            self.roi_text.insert("end", f"Move {i+1}: {roi}\n")

    def _save_roi(self):
        """Lưu ROI vào tool_config.json"""
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            config = json.load(f)
        config.setdefault("roi", {})["move_slots"] = self.roi_list
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("✓ Lưu thành công", f"ROI đã lưu vào:\n{CONFIG_PATH}")
        self.status_var.set("✓ Đã lưu ROI!")


def create_team_builder_widget(master, config):
    """Tạo Team Builder widget để embed vào tab"""
    init_tesseract(config)
    return TeamBuilderApp(master, config)


if __name__ == "__main__":
    run_team_builder()
