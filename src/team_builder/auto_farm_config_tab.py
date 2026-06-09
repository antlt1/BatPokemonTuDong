"""
auto_farm_config_tab.py — Tab 5: Auto Farm Configuration

Tính năng:
  1. Chọn 6 Pokemon từ pokemon_bag_inventory.json
  2. Xem chi tiết moves của mỗi con
  3. Lưu team farm vào team_farm.json
  4. Mode 1 & 3 sẽ đọc file này để farm
"""

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

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

ROOT        = Path(__file__).resolve().parent.parent.parent
BAG_PATH    = ROOT / "src" / "config" / "pokemon_bag_inventory.json"
TEAM_FARM_PATH = ROOT / "src" / "config" / "team_farm.json"
MAX_TEAM    = 6


# ═════════════════════════════════════════════════════════
class AutoFarmConfigTab:
    def __init__(self, parent, config):
        self.config = config
        self.bag_inventory = []      # Danh sách tất cả Pokemon từ bag
        self.team_farm = []          # 6 con được chọn để farm

        self.frame = tk.Frame(parent, bg=BG_DARK)
        self._load_data()
        self._build_ui()

    # ──────────────────────────────────────────────────────
    def _load_data(self):
        """Load danh sách Pokemon từ bag_inventory.json"""
        if BAG_PATH.exists():
            try:
                data = json.loads(BAG_PATH.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    self.bag_inventory = data
            except Exception as e:
                print(f"Lỗi load bag: {e}")

        # Load team farm hiện tại (nếu có)
        if TEAM_FARM_PATH.exists():
            try:
                data = json.loads(TEAM_FARM_PATH.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    self.team_farm = data
            except Exception:
                self.team_farm = []

    def _build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Status vars - tạo sớm trước khi dùng
        self.status_var = tk.StringVar(value="Chọn tối đa 6 Pokemon để farm")
        self.info_var = tk.StringVar(value="Team trống - chọn Pokemon từ bên trái để thêm")

        # Toolbar
        toolbar = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8)

        tk.Label(toolbar, text="⚙️  AUTO FARM CONFIG", font=F_TITLE,
                 bg=BG_DARK, fg=ACCENT).pack(side="left", padx=(0, 20))

        tk.Button(toolbar, text="🔄 Reload Bag",
                  command=self._reload_bag, font=F_LABEL,
                  bg=BG_MID, fg=TEXT_HI, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="💾 Lưu Team Farm",
                  command=self._save_team, font=F_LABEL,
                  bg=ACCENT2, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Button(toolbar, text="🗑️  Xóa Team",
                  command=self._clear_team, font=F_LABEL,
                  bg=WARN, fg=BG_DARK, relief="flat",
                  padx=10, pady=4).pack(side="left", padx=4)

        tk.Label(toolbar, textvariable=self.status_var, font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN).pack(side="left", padx=12)

        # Left panel: Danh sách Bag (có thể chọn)
        left_panel = tk.Frame(self.frame, bg=BG_DARK)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1)

        tk.Label(left_panel, text="📦 Bag Inventory", font=F_LABEL,
                 bg=BG_DARK, fg=ACCENT).pack(anchor="w", padx=4, pady=4)

        # Listbox Bag
        list_frame = tk.Frame(left_panel, bg=BG_MID, bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.bag_listbox = tk.Listbox(list_frame, font=F_LABEL,
                                       bg=BG_MID, fg=TEXT_HI,
                                       yscrollcommand=scrollbar.set,
                                       selectmode="single", bd=0,
                                       highlightthickness=0)
        self.bag_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.bag_listbox.yview)
        self.bag_listbox.bind("<<ListboxSelect>>", self._on_bag_select)

        # Button: Add selected
        add_btn = tk.Button(left_panel, text="➕ Add to Team (chọn 1 con rồi bấm)",
                           command=self._add_to_team, font=F_LABEL,
                           bg=ACCENT, fg=BG_DARK, relief="flat", padx=6, pady=4)
        add_btn.pack(fill="x", padx=4, pady=4)

        self._update_bag_list()

        # Right panel: Team Farm (6 slots)
        right_panel = tk.Frame(self.frame, bg=BG_DARK)
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)

        tk.Label(right_panel, text="🎯 Team Farm (6/6)", font=F_LABEL,
                 bg=BG_DARK, fg=ACCENT2).pack(anchor="w", padx=4, pady=4)

        # Team scroll area
        team_scroll = tk.Canvas(right_panel, bg=BG_DARK, highlightthickness=0)
        team_scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=team_scroll.yview)
        team_scroll.configure(yscrollcommand=team_scrollbar.set)
        team_scrollbar.pack(side="right", fill="y")
        team_scroll.pack(side="left", fill="both", expand=True)

        self.team_frame = tk.Frame(team_scroll, bg=BG_DARK)
        self.team_frame_id = team_scroll.create_window((0, 0), window=self.team_frame, anchor="nw")

        self.team_frame.bind("<Configure>",
            lambda e: team_scroll.configure(scrollregion=team_scroll.bbox("all")))
        team_scroll.bind("<Configure>",
            lambda e: team_scroll.itemconfig(self.team_frame_id, width=e.width))

        team_scroll.bind_all("<MouseWheel>",
            lambda e: team_scroll.yview_scroll(-1*(e.delta//120), "units"))

        # Các Pokemon trong team
        self.team_slots = []
        self._build_team_slots()
        self._update_team_display()

        # Status info
        info_frame = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        info_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8)

        tk.Label(info_frame, textvariable=self.info_var, font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN, justify="left").pack(anchor="w")

    # ──────────────────────────────────────────────────────
    def _build_team_slots(self):
        """Tạo 6 slot cho team farm"""
        for i in range(MAX_TEAM):
            slot = {
                "frame": tk.Frame(self.team_frame, bg=BG_CARD, padx=6, pady=4),
                "name_var": tk.StringVar(value="[Slot trống]"),
                "pokemon_data": None,
            }
            slot["frame"].pack(fill="x", padx=4, pady=2)

            # Header: #1  Tên
            header = tk.Frame(slot["frame"], bg=BG_CARD)
            header.pack(fill="x", pady=(0, 4))
            header.columnconfigure(1, weight=1)

            tk.Label(header, text=f"#{i+1}", font=("Consolas", 10, "bold"),
                     bg=BG_CARD, fg=ACCENT, width=3).pack(side="left", padx=2)

            tk.Label(header, textvariable=slot["name_var"], font=F_LABEL,
                     bg=BG_CARD, fg=TEXT_HI).pack(side="left", fill="x", expand=True, padx=6)

            tk.Button(header, text="✕", font=F_SMALL,
                     bg=WARN, fg=BG_DARK, relief="flat", padx=4,
                     command=lambda si=i: self._remove_slot(si)).pack(side="right", padx=2)

            # Moves list
            moves_frame = tk.Frame(slot["frame"], bg=BG_CARD)
            moves_frame.pack(fill="x", padx=4, pady=2)

            slot["moves_label"] = tk.Label(moves_frame, text="Chưa có moves",
                                            font=F_SMALL, bg=BG_CARD, fg="#888",
                                            justify="left")
            slot["moves_label"].pack(anchor="w")

            self.team_slots.append(slot)

    def _update_team_display(self):
        """Cập nhật hiển thị team trên UI"""
        for i, slot in enumerate(self.team_slots):
            if i < len(self.team_farm):
                pdata = self.team_farm[i]
                pname = pdata.get("name", "?")
                slot["name_var"].set(f"🔸 {pname}")
                slot["pokemon_data"] = pdata

                # Moves text
                moves = pdata.get("moves", [])
                moves_text = ""
                for move in moves:
                    if isinstance(move, dict):
                        mname = move.get("name", "?")
                        mpp = move.get("pp", "?")
                        moves_text += f"  • {mname} ({mpp})\n"
                    else:
                        moves_text += f"  • {move}\n"

                if moves_text:
                    slot["moves_label"].config(text=moves_text.rstrip(), fg=TEXT_MAIN)
                else:
                    slot["moves_label"].config(text="  [Chưa scan moves]", fg="#888")
            else:
                slot["name_var"].set("[Slot trống]")
                slot["pokemon_data"] = None
                slot["moves_label"].config(text="", fg="#888")

        # Update status
        self.status_var.set(f"Team Farm: {len(self.team_farm)}/{MAX_TEAM}")
        if len(self.team_farm) > 0:
            names = ", ".join([p.get("name", "?") for p in self.team_farm])
            self.info_var.set(f"Team hiện tại: {names}")
        else:
            self.info_var.set("Team trống - chọn Pokemon từ bên trái để thêm")

    def _update_bag_list(self):
        """Cập nhật danh sách bag listbox"""
        self.bag_listbox.delete(0, tk.END)
        for pdata in self.bag_inventory:
            pname = pdata.get("name", "?")
            move_count = len(pdata.get("moves", []))
            txt = f"  {pname}  ({move_count} moves)"
            self.bag_listbox.insert(tk.END, txt)

    def _on_bag_select(self, event=None):
        """Khi chọn Pokemon từ bag"""
        selection = self.bag_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.bag_inventory):
                pdata = self.bag_inventory[idx]
                pname = pdata.get("name", "?")
                move_count = len(pdata.get("moves", []))
                self.info_var.set(f"Chọn: {pname}  ({move_count} moves) → bấm '➕ Add to Team'")

    def _add_to_team(self):
        """Thêm Pokemon được chọn vào team farm"""
        if len(self.team_farm) >= MAX_TEAM:
            messagebox.showwarning("Đầy", f"Team đã đủ {MAX_TEAM} con rồi!")
            return

        selection = self.bag_listbox.curselection()
        if not selection:
            messagebox.showwarning("Chưa chọn", "Hãy chọn 1 Pokemon từ bên trái!")
            return

        idx = selection[0]
        if idx >= len(self.bag_inventory):
            return

        pdata = self.bag_inventory[idx]
        pname = pdata.get("name", "?")

        # Kiểm tra xem đã có trong team chưa
        if any(p.get("name") == pname for p in self.team_farm):
            messagebox.showwarning("Trùng", f"{pname} đã có trong team rồi!")
            return

        # Thêm vào team
        self.team_farm.append(pdata.copy())
        self._update_team_display()
        self.status_var.set(f"➕ Thêm {pname} vào team")

    def _remove_slot(self, slot_idx):
        """Xóa Pokemon ở slot thứ slot_idx"""
        if slot_idx < len(self.team_farm):
            removed = self.team_farm.pop(slot_idx)
            self._update_team_display()
            self.status_var.set(f"✕ Xóa {removed.get('name', '?')} khỏi team")

    def _save_team(self):
        """Lưu team farm vào JSON"""
        if not self.team_farm:
            messagebox.showwarning("Team trống", "Chưa chọn Pokemon nào để farm!")
            return

        TEAM_FARM_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            TEAM_FARM_PATH.write_text(
                json.dumps(self.team_farm, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            names = ", ".join([p.get("name", "?") for p in self.team_farm])
            messagebox.showinfo("✅ Lưu thành công",
                              f"Team Farm ({len(self.team_farm)}/6): {names}\n\n"
                              f"File: {TEAM_FARM_PATH}")
            self.status_var.set(f"💾 Đã lưu {len(self.team_farm)} Pokemon")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không lưu JSON: {e}")

    def _clear_team(self):
        """Xóa toàn bộ team"""
        if messagebox.askyesno("Xác nhận", "Xóa toàn bộ team farm?"):
            self.team_farm = []
            self._update_team_display()
            self.status_var.set("🗑️  Đã xóa team")

    def _reload_bag(self):
        """Reload danh sách bag từ file"""
        self._load_data()
        self._update_bag_list()
        messagebox.showinfo("✅ Reload", f"Đã load {len(self.bag_inventory)} Pokemon từ bag")
