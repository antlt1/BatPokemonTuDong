"""
target_pokemon_tab.py — Tab 4.5/New: Target Pokémon Configuration

Quản lý danh sách Pokémon mục tiêu cần bắt (đọc/ghi target_pokemon.json).
Hỗ trợ:
  1. Xem danh sách các target Pokémon hiện tại.
  2. Dán ảnh (Ctrl+V) hoặc mở file ảnh túi/game, kéo chuột quét tên để tự động OCR điền vào tên Pokémon.
  3. Lọc danh sách Ability bằng ô tìm kiếm và Listbox để thao tác nhanh.
  4. Nếu Ability để trống hoặc chọn "none", mặc định là "none" (bắt tất cả abilities).
  5. Nút xóa nhanh từng target.
  6. Tự động lưu và cho phép lưu thủ công/tải lại.
  7. Khắc phục lỗi lệch vị trí cuộn khi chuyển tab.
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

ROOT = Path(__file__).resolve().parent.parent.parent
TARGETS_PATH = ROOT / "src" / "config" / "target_pokemon.json"
BAG_PATH = ROOT / "src" / "config" / "pokemon_bag_inventory.json"

BG_DARK  = "#1e2127"
BG_MID   = "#282c34"
BG_CARD  = "#2d3139"
BG_DROP  = "#3d4a5c"
ACCENT   = "#61afef"
ACCENT2  = "#98c379"
WARN     = "#e06c75"
TEXT_MAIN= "#abb2bf"
TEXT_SECONDARY = "#8888a0"
TEXT_HI  = "#e5c07b"

F_TITLE  = ("Consolas", 12, "bold")
F_LABEL  = ("Consolas", 10)
F_SMALL  = ("Consolas", 9)

ALL_ABILITIES = [
    "none", "Adaptability", "Aftermath", "Air Lock", "Analytic", "Anger Point",
    "Anticipation", "Arena Trap", "Aroma Veil", "Aura Break", "Bad Dreams",
    "Battle Armor", "Big Pecks", "Blaze", "Bulletproof", "Chlorophyll",
    "Clear Body", "Cloud Nine", "Color Change", "Competitive", "Compound Eyes",
    "Contrary", "Cursed Body", "Cute Charm", "Damp", "Dark Aura",
    "Defeatist", "Defiant", "Download", "Drizzle", "Drought", "Dry Skin",
    "Early Bird", "Effect Spore", "Fairy Aura", "Filter", "Flame Body",
    "Flare Boost", "Flash Fire", "Flower Gift", "Flower Veil", "Forecast",
    "Forewarn", "Friend Guard", "Frisk", "Fur Coat", "Gale Wings",
    "Gluttony", "Gooey", "Grass Pelt", "Guts", "Harvest", "Healer",
    "Heatproof", "Heavy Metal", "Honey Gather", "Huge Power", "Hustle",
    "Hydration", "Hyper Cutter", "Ice Body", "Illuminate", "Illusion",
    "Immunity", "Imposter", "Infiltrator", "Inner Focus", "Insomnia",
    "Intimidate", "Iron Barbs", "Iron Fist", "Justified", "Keen Eye",
    "Klutz", "Leaf Guard", "Levitate", "Light Metal", "Lightning Rod",
    "Limber", "Liquid Ooze", "Magic Bounce", "Magic Guard", "Magician",
    "Magma Armor", "Magnet Pull", "Marvel Scale", "Mega Launcher", "Minus",
    "Mold Breaker", "Moody", "Motor Drive", "Moxie", "Multiscale",
    "Multitype", "Mummy", "Natural Cure", "No Guard", "Normalize",
    "Oblivious", "Overcoat", "Overgrow", "Own Tempo", "Pickpocket",
    "Pickup", "Pixilate", "Plus", "Poison Heal", "Poison Point",
    "Poison Touch", "Prankster", "Pressure", "Protean", "Pure Power",
    "Quick Feet", "Rain Dish", "Rattled", "Reckless", "Refrigerate",
    "Regenerator", "Rivalry", "Rock Head", "Rough Skin", "Run Away",
    "Sand Force", "Sand Rush", "Sand Stream", "Sand Veil", "Sap Sipper",
    "Scrappy", "Serene Grace", "Shadow Tag", "Shed Skin", "Sheer Force",
    "Shell Armor", "Shield Dust", "Simple", "Skill Link", "Slow Start",
    "Sniper", "Snow Cloak", "Snow Warning", "Solar Power", "Solid Rock",
    "Soundproof", "Speed Boost", "Stall", "Stance Change", "Static",
    "Steadfast", "Stench", "Sticky Hold", "Storm Drain", "Strong Jaw",
    "Sturdy", "Suction Cups", "Super Luck", "Swarm", "Sweet Veil",
    "Swift Swim", "Symbiosis", "Synchronize", "Tangled Feet", "Technician",
    "Telepathy", "Teravolt", "Thick Fat", "Tinted Lens", "Torrent",
    "Tough Claws", "Toxic Boost", "Trace", "Truant", "Turboblaze",
    "Unaware", "Unburden", "Unnerve", "Victory Star", "Vital Spirit",
    "Volt Absorb", "Water Absorb", "Water Veil", "Weak Armor", "White Smoke",
    "Wonder Guard", "Wonder Skin", "Zen Mode"
]


class TargetPokemonTab:
    def __init__(self, parent, config):
        self.config = config
        self.targets = []

        # Image state
        self.img_pil = None
        self.img_tk = None
        self.img_scale = 1.0
        self.img_offset = (0, 0)

        # Drag state
        self._drag_start = None
        self._drag_rect = None

        self.frame = tk.Frame(parent, bg=BG_DARK)
        self._load_targets()
        self._build_ui()

    def _load_targets(self):
        """Đọc danh sách target từ JSON"""
        if TARGETS_PATH.exists():
            try:
                data = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.targets = data
                else:
                    self.targets = []
            except Exception as e:
                print(f"Error loading targets: {e}")
                self.targets = []
        else:
            self.targets = []

    def _build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.info_var = tk.StringVar(value="Ctrl+V để dán ảnh túi/game -> Kéo quét tên")

        # ----- TOOLBAR -----
        toolbar = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8)

        tk.Label(toolbar, text="🎯 TARGET POKEMON", font=F_TITLE,
                 bg=BG_DARK, fg=ACCENT).pack(side="left", padx=(0, 20))

        tk.Button(toolbar, text="🔄 Reload",
                  command=self._reload_targets, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="💾 Lưu JSON",
                  command=self._save_targets, font=F_LABEL,
                  bg=ACCENT2, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Label(toolbar, textvariable=self.status_var, font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN).pack(side="left", padx=12)

        # Bind Control-v to frame (only works if active tab)
        self.frame.bind_all("<Control-v>", self._paste_clipboard)

        # ----- LEFT: ADD FORM + OCR CANVAS -----
        left_panel = tk.Frame(self.frame, bg=BG_DARK)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left_panel.columnconfigure(0, weight=1)

        tk.Label(left_panel, text="➕ Thêm Pokémon Mục Tiêu", font=F_LABEL,
                 bg=BG_DARK, fg=ACCENT).pack(anchor="w", padx=4, pady=4)

        # Compact Canvas for image pasting and scanning
        canvas_frame = tk.Frame(left_panel, bg=BG_MID, bd=1, relief="solid")
        canvas_frame.pack(fill="x", padx=4, pady=4)

        self.canvas = tk.Canvas(canvas_frame, bg="#111316", width=400, height=220,
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="x", expand=True)
        self.canvas.create_text(200, 110, text="Ctrl+V để dán ảnh quét tên", font=F_LABEL,
                                fill=TEXT_SECONDARY, justify="center", tags="hint")

        self.canvas.bind("<Button-1>",        self._drag_press)
        self.canvas.bind("<B1-Motion>",       self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_release)

        # Canvas tools
        canvas_tools = tk.Frame(left_panel, bg=BG_DARK)
        canvas_tools.pack(fill="x", padx=4, pady=2)

        tk.Button(canvas_tools, text="📋 Dán ảnh (Ctrl+V)", command=self._paste_clipboard,
                  font=F_SMALL, bg=BG_MID, fg=TEXT_HI, relief="flat", padx=8, pady=2).pack(side="left", padx=2)
        
        tk.Button(canvas_tools, text="📂 Chọn ảnh...", command=self._browse_image,
                  font=F_SMALL, bg=BG_MID, fg=TEXT_HI, relief="flat", padx=8, pady=2).pack(side="left", padx=2)

        # Form fields frame
        form_box = tk.Frame(left_panel, bg=BG_CARD, bd=1, relief="solid", padx=10, pady=10)
        form_box.pack(fill="both", expand=True, padx=4, pady=4)
        form_box.columnconfigure(1, weight=1)

        # Tên Pokemon Entry
        tk.Label(form_box, text="Tên Pokemon:", font=F_LABEL,
                 bg=BG_CARD, fg=TEXT_HI).grid(row=0, column=0, sticky="w", pady=4)
        
        self.name_entry = tk.Entry(form_box, font=F_LABEL, bg=BG_MID, fg=TEXT_HI,
                                   insertbackground=TEXT_HI, bd=1, relief="solid")
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)

        # Ability Tìm kiếm & Listbox
        tk.Label(form_box, text="Tìm Ability:", font=F_LABEL,
                 bg=BG_CARD, fg=TEXT_HI).grid(row=1, column=0, sticky="w", pady=4)
        
        self.ability_search_var = tk.StringVar()
        self.ability_search_entry = tk.Entry(form_box, textvariable=self.ability_search_var, font=F_LABEL,
                                             bg=BG_MID, fg=TEXT_HI, insertbackground=TEXT_HI, bd=1, relief="solid")
        self.ability_search_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.ability_search_entry.bind("<KeyRelease>", self._on_ability_search)

        # Listbox danh sách abilities
        listbox_frame = tk.Frame(form_box, bg=BG_CARD)
        listbox_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=4)
        listbox_frame.columnconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.ability_listbox = tk.Listbox(listbox_frame, font=F_SMALL, bg=BG_MID, fg=TEXT_HI,
                                          height=4, selectmode="single", bd=1, relief="solid",
                                          highlightthickness=0, yscrollcommand=scrollbar.set)
        self.ability_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.ability_listbox.yview)

        self.ability_listbox.bind("<<ListboxSelect>>", self._on_ability_select)

        # Selected Ability Label
        self.selected_ability_var = tk.StringVar(value="none")
        lbl_select_title = tk.Label(form_box, text="Ability đã chọn:", font=F_SMALL, bg=BG_CARD, fg=TEXT_SECONDARY)
        lbl_select_title.grid(row=3, column=0, sticky="w", pady=(4, 2))
        
        self.selected_ability_lbl = tk.Label(form_box, textvariable=self.selected_ability_var, font=("Consolas", 10, "bold"),
                                             bg=BG_CARD, fg=ACCENT2, anchor="w")
        self.selected_ability_lbl.grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(4, 2))

        # Fill listbox ban đầu
        self._fill_ability_listbox(ALL_ABILITIES)

        # Add Button
        add_btn = tk.Button(form_box, text="➕ Thêm Target",
                            command=self._add_target, font=F_LABEL,
                            bg=ACCENT2, fg=BG_DARK, relief="flat", padx=12, pady=6)
        add_btn.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # ----- RIGHT: TARGET LIST -----
        right_panel = tk.Frame(self.frame, bg=BG_DARK)
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)

        tk.Label(right_panel, text="📋 Danh Sách Pokémon Cần Bắt", font=F_LABEL,
                 bg=BG_DARK, fg=ACCENT2).pack(anchor="w", padx=4, pady=8)

        # Scrollable area
        self.scroll_canvas = tk.Canvas(right_panel, bg=BG_DARK, highlightthickness=0)
        self.right_scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.right_scrollbar.set)

        self.right_scrollbar.pack(side="right", fill="y")
        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        self.list_frame = tk.Frame(self.scroll_canvas, bg=BG_DARK)
        self.list_frame_id = self.scroll_canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        self.list_frame.bind("<Configure>",
            lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        self.scroll_canvas.bind("<Configure>",
            lambda e: self.scroll_canvas.itemconfig(self.list_frame_id, width=e.width))

        # Localised Mouse Wheel bindings (no bind_all)
        self.scroll_canvas.bind("<MouseWheel>", self._on_right_mousewheel)
        self.list_frame.bind("<MouseWheel>", self._on_right_mousewheel)

        self._update_list_display()

        # Status text at bottom
        info_frame = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        info_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8)
        tk.Label(info_frame, textvariable=self.info_var, font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN, justify="left").pack(anchor="w")

    # ----- IMAGE PASTE & OCR SCANNING -----
    def _browse_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")])
        if path:
            try:
                self.img_pil = Image.open(path).convert("RGB")
                self._render_image()
                self.status_var.set(f"✅ Đã mở {Path(path).name}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không mở được ảnh: {e}")

    def _paste_clipboard(self, event=None):
        # Only run if tab is visible to prevent cross-tab clashes
        if not self.frame.winfo_viewable():
            return
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
            self.status_var.set(f"📋 Đã dán ảnh ({self.img_pil.width}×{self.img_pil.height})")
        except Exception as e:
            self.status_var.set(f"❌ Lỗi dán ảnh: {e}")

    def _render_image(self):
        if not self.img_pil:
            return
        self.canvas.delete("all")
        cw = self.canvas.winfo_width() or 400
        ch = self.canvas.winfo_height() or 220
        iw, ih = self.img_pil.size
        scale = min(cw / iw, ch / ih, 1.0)
        nw, nh = int(iw * scale), int(ih * scale)
        self.img_scale = scale
        self.img_offset = ((cw - nw) // 2, (ch - nh) // 2)
        resized = self.img_pil.resize((nw, nh), Image.LANCZOS)
        self.img_tk = ImageTk.PhotoImage(resized)
        ox, oy = self.img_offset
        self.canvas.create_image(ox, oy, anchor="nw", image=self.img_tk)

    def _drag_press(self, event):
        if not self.img_pil:
            return
        self._drag_start = (event.x, event.y)
        if self._drag_rect:
            self.canvas.delete(self._drag_rect)

    def _drag_move(self, event):
        if self._drag_start is None:
            return
        if self._drag_rect:
            self.canvas.delete(self._drag_rect)
        x0, y0 = self._drag_start
        self._drag_rect = self.canvas.create_rectangle(
            x0, y0, event.x, event.y,
            outline=WARN, width=2, dash=(5, 3))

    def _drag_release(self, event):
        if self._drag_start is None:
            return

        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y
        
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

        self._process_name_roi(rx, ry, rw, rh)

        self._drag_start = None
        if self._drag_rect:
            self.canvas.delete(self._drag_rect)
            self._drag_rect = None

    def _process_name_roi(self, rx, ry, rw, rh):
        crop = self.img_pil.crop((rx, ry, rx + rw, ry + rh))
        name = self._ocr_name(crop)
        
        if name:
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, name)
            self.status_var.set(f"✅ Quét tên: {name}")
        else:
            self.status_var.set("⚠️ Không nhận diện được tên")

    def _ocr_name(self, image_pil):
        if not HAS_OCR:
            return ""
        try:
            img_np = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            scaled = cv2.resize(gray, None, fx=5, fy=5, interpolation=cv2.INTER_CUBIC)
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(scaled)
            
            thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            denoised = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
            
            config = "--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-"
            text = pytesseract.image_to_string(Image.fromarray(denoised), config=config).strip()
            
            text = re.sub(r"[^a-zA-Z\-]", "", text).strip()
            if len(text) >= 2:
                return text.title()
            return ""
        except Exception as e:
            print(f"[DEBUG] OCR exception: {e}")
            return ""

    # ----- MOUSE WHEEL SCROLLING CONSTRAINTS -----
    def _on_right_mousewheel(self, event):
        canvas_h = self.scroll_canvas.winfo_height()
        bbox = self.scroll_canvas.bbox("all")
        if bbox:
            content_h = bbox[3] - bbox[1]
            if content_h > canvas_h:
                self.scroll_canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # ----- ABILITY SELECTION & SEARCH -----
    def _fill_ability_listbox(self, items):
        self.ability_listbox.delete(0, tk.END)
        for val in items:
            self.ability_listbox.insert(tk.END, val)
        if items and items[0] == "none":
            self.ability_listbox.select_set(0)

    def _on_ability_search(self, event=None):
        query = self.ability_search_var.get().strip().lower()
        if not query:
            self._fill_ability_listbox(ALL_ABILITIES)
            curr = self.selected_ability_var.get()
            if curr in ALL_ABILITIES:
                idx = ALL_ABILITIES.index(curr)
                self.ability_listbox.select_set(idx)
                self.ability_listbox.see(idx)
        else:
            filtered = [ab for ab in ALL_ABILITIES if query in ab.lower()]
            self._fill_ability_listbox(filtered)
            curr = self.selected_ability_var.get()
            match_indices = [i for i, val in enumerate(filtered) if val.lower() == curr.lower()]
            if match_indices:
                self.ability_listbox.select_set(match_indices[0])
                self.ability_listbox.see(match_indices[0])

    def _on_ability_select(self, event=None):
        selection = self.ability_listbox.curselection()
        if selection:
            idx = selection[0]
            val = self.ability_listbox.get(idx)
            self.selected_ability_var.set(val)

    # ----- TARGET ADD / DELETE -----
    def _add_target(self):
        """Thêm target từ form vào list"""
        name = self.name_entry.get().strip()
        ability = self.selected_ability_var.get().strip().lower()

        if not name:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập hoặc quét tên Pokémon!")
            return

        if not ability:
            ability = "none"

        # Chuẩn hóa tên Pokémon (Viết hoa chữ cái đầu)
        name = name.title()

        # Kiểm tra trùng tên + ability
        duplicate = False
        for t in self.targets:
            if t.get("pokemonname", "").lower() == name.lower() and t.get("ability", "").lower() == ability:
                duplicate = True
                break

        if duplicate:
            messagebox.showwarning("Trùng lặp", f"Pokémon {name} với ability '{ability}' đã có trong danh sách!")
            return

        # Thêm mới
        self.targets.append({
            "pokemonname": name,
            "ability": ability
        })

        self.status_var.set(f"✅ Đã thêm {name} ({ability})")
        self.name_entry.delete(0, tk.END)
        
        # Reset Ability selection to none
        self.selected_ability_var.set("none")
        self.ability_search_var.set("")
        self._fill_ability_listbox(ALL_ABILITIES)

        self._update_list_display()
        self._auto_save()

    def _delete_target(self, idx):
        """Xóa target theo index"""
        if 0 <= idx < len(self.targets):
            removed = self.targets.pop(idx)
            name = removed.get("pokemonname", "?")
            self.status_var.set(f"✕ Đã xóa {name}")
            self._update_list_display()
            self._auto_save()

    def _update_list_display(self):
        """Render lại danh sách bên phải"""
        # Reset scroll to top to fix positioning bug
        self.scroll_canvas.yview_moveto(0)

        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.targets:
            tk.Label(self.list_frame, text="Chưa có Pokémon mục tiêu nào.\nVui lòng thêm ở khung bên trái.",
                     font=F_LABEL, bg=BG_DARK, fg=TEXT_MAIN, justify="center").pack(padx=4, pady=20)
            return

        for i, item in enumerate(self.targets):
            self._build_target_row(i, item)

    def _build_target_row(self, index, item):
        """Tạo hàng thông tin cho 1 target"""
        row_frame = tk.Frame(self.list_frame, bg=BG_CARD, bd=0, padx=8, pady=6)
        row_frame.pack(fill="x", padx=4, pady=2)
        row_frame.columnconfigure(1, weight=1)

        name = item.get("pokemonname", "?")
        ability = item.get("ability", "none")

        # Stt
        tk.Label(row_frame, text=f"#{index+1}", font=("Consolas", 10, "bold"),
                 bg=BG_CARD, fg=ACCENT, width=3).pack(side="left", padx=2)

        # Name
        tk.Label(row_frame, text=name, font=("Consolas", 10, "bold"),
                 bg=BG_CARD, fg=TEXT_HI, anchor="w", width=15).pack(side="left", padx=10)

        # Ability
        if ability == "none":
            ability_text = "Bắt tất cả (none)"
            ability_color = ACCENT2
        else:
            ability_text = f"Ability: {ability}"
            ability_color = ACCENT

        lbl = tk.Label(row_frame, text=ability_text, font=F_SMALL,
                       bg=BG_CARD, fg=ability_color, anchor="w")
        lbl.pack(side="left", fill="x", expand=True)

        # Delete Button
        btn = tk.Button(row_frame, text="✕", font=F_SMALL,
                        bg=WARN, fg=BG_DARK, relief="flat", padx=6, pady=2,
                        command=lambda idx=index: self._delete_target(idx))
        btn.pack(side="right", padx=2)

        # Bind mousewheel to row items
        for widget in (row_frame, lbl, btn):
            widget.bind("<MouseWheel>", self._on_right_mousewheel)

    def _auto_save(self):
        """Tự động lưu vào target_pokemon.json"""
        try:
            TARGETS_PATH.parent.mkdir(parents=True, exist_ok=True)
            TARGETS_PATH.write_text(json.dumps(self.targets, indent=2, ensure_ascii=False), encoding="utf-8")
            self.status_var.set("💾 Auto-saved")
        except Exception as e:
            self.status_var.set(f"❌ Auto-save error: {e}")

    def _save_targets(self):
        """Lưu thủ công (có thông báo)"""
        try:
            TARGETS_PATH.parent.mkdir(parents=True, exist_ok=True)
            TARGETS_PATH.write_text(json.dumps(self.targets, indent=2, ensure_ascii=False), encoding="utf-8")
            self.status_var.set("💾 Saved targets")
            messagebox.showinfo("Thành công", f"Đã lưu {len(self.targets)} target vào:\n{TARGETS_PATH}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def _reload_targets(self):
        """Tải lại danh sách từ file"""
        self._load_targets()
        self.name_entry.delete(0, tk.END)
        self.selected_ability_var.set("none")
        self.ability_search_var.set("")
        self._fill_ability_listbox(ALL_ABILITIES)
        self._update_list_display()
        self.status_var.set("🔄 Đã tải lại")
        messagebox.showinfo("Reloaded", "Đã tải lại danh sách từ target_pokemon.json!")
