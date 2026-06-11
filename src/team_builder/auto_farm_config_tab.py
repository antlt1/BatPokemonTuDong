"""
auto_farm_config_tab.py — Tab 5: Auto Farm Configuration

Tính năng:
  1. Chọn 6 Pokemon từ pokemon_bag_inventory.json
  2. Kéo từ Bag sang Team / kéo đổi thứ tự slot
  3. Lưu team farm vào team_farm.json (đúng 6 con)
  4. Menu 3 đọc file này để auto farm
"""

import copy
import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

BG_DARK  = "#1e2127"
BG_MID   = "#282c34"
BG_CARD  = "#2d3139"
BG_DROP  = "#3d4a5c"
ACCENT   = "#61afef"
ACCENT2  = "#98c379"
WARN     = "#e06c75"
TEXT_MAIN= "#abb2bf"
TEXT_HI  = "#e5c07b"
F_TITLE  = ("Consolas", 12, "bold")
F_LABEL  = ("Consolas", 10)
F_SMALL  = ("Consolas", 9)

ROOT           = Path(__file__).resolve().parent.parent.parent
BAG_PATH       = ROOT / "src" / "config" / "pokemon_bag_inventory.json"
TEAM_FARM_PATH = ROOT / "src" / "config" / "team_farm.json"
MAX_TEAM       = 6


def _format_bag_line(pdata: dict) -> str:
    pid = pdata.get("id", "?")
    pname = pdata.get("name", "?")
    move_names = []
    for m in pdata.get("moves", []):
        if isinstance(m, dict):
            move_names.append(m.get("name", "?"))
        else:
            move_names.append(str(m))
    moves_str = "/".join(move_names) if move_names else "(no moves)"
    return f"[{pid}] {pname} - {moves_str}"


def _copy_pokemon(pdata: dict) -> dict:
    return copy.deepcopy(pdata)


# ═════════════════════════════════════════════════════════
class AutoFarmConfigTab:
    def __init__(self, parent, config):
        self.config = config
        self.bag_inventory = []
        self.team_farm = []
        self._drag = None          # {"kind": "bag"|"team", "idx": int}
        self._drag_moved = False

        self.frame = tk.Frame(parent, bg=BG_DARK)
        self._load_data()
        self._build_ui()

    # ──────────────────────────────────────────────────────
    def _load_data(self):
        if BAG_PATH.exists():
            try:
                data = json.loads(BAG_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.bag_inventory = data
            except Exception as e:
                print(f"Lỗi load bag: {e}")

        if TEAM_FARM_PATH.exists():
            try:
                data = json.loads(TEAM_FARM_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.team_farm = data[:MAX_TEAM]
            except Exception:
                self.team_farm = []

    def _build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="Chọn đủ 6 Pokemon để farm")
        self.info_var = tk.StringVar(
            value="Kéo từ Bag → Team | Double-click Bag để thêm | Kéo slot để đổi thứ tự"
        )

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

        # Left: Bag
        left_panel = tk.Frame(self.frame, bg=BG_DARK)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1)

        tk.Label(left_panel, text="📦 Bag Inventory", font=F_LABEL,
                 bg=BG_DARK, fg=ACCENT).pack(anchor="w", padx=4, pady=4)

        list_frame = tk.Frame(left_panel, bg=BG_MID, bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.bag_listbox = tk.Listbox(list_frame, font=F_SMALL,
                                       bg=BG_MID, fg=TEXT_HI,
                                       yscrollcommand=scrollbar.set,
                                       selectmode="single", bd=0,
                                       highlightthickness=0)
        self.bag_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.bag_listbox.yview)

        self.bag_listbox.bind("<<ListboxSelect>>", self._on_bag_select)
        self.bag_listbox.bind("<ButtonPress-1>", self._on_bag_press)
        self.bag_listbox.bind("<B1-Motion>", self._on_bag_motion)
        self.bag_listbox.bind("<Double-Button-1>", self._on_bag_double_click)
        self.bag_listbox.bind("<ButtonRelease-1>", self._on_global_release)

        tk.Label(left_panel,
                 text="Kéo Pokemon sang Team bên phải, hoặc double-click để thêm",
                 font=F_SMALL, bg=BG_DARK, fg="#888").pack(anchor="w", padx=4)

        self._update_bag_list()

        # Right: Team slots
        right_panel = tk.Frame(self.frame, bg=BG_DARK)
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)

        tk.Label(right_panel, text="🎯 Team Farm (6/6)", font=F_LABEL,
                 bg=BG_DARK, fg=ACCENT2).pack(anchor="w", padx=4, pady=4)

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
            lambda e: team_scroll.yview_scroll(-1 * (e.delta // 120), "units"))

        self.team_slots = []
        self._build_team_slots()
        self._update_team_display()

        info_frame = tk.Frame(self.frame, bg=BG_DARK, pady=6)
        info_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8)
        tk.Label(info_frame, textvariable=self.info_var, font=F_SMALL,
                 bg=BG_DARK, fg=TEXT_MAIN, justify="left").pack(anchor="w")

    # ──────────────────────────────────────────────────────
    def _build_team_slots(self):
        for i in range(MAX_TEAM):
            slot = {
                "index": i,
                "frame": tk.Frame(self.team_frame, bg=BG_CARD, padx=6, pady=4),
                "name_var": tk.StringVar(value="[Slot trống]"),
            }
            slot["frame"].pack(fill="x", padx=4, pady=2)

            header = tk.Frame(slot["frame"], bg=BG_CARD)
            header.pack(fill="x", pady=(0, 4))

            tk.Label(header, text=f"#{i + 1}", font=("Consolas", 10, "bold"),
                     bg=BG_CARD, fg=ACCENT, width=3).pack(side="left", padx=2)

            tk.Label(header, textvariable=slot["name_var"], font=F_LABEL,
                     bg=BG_CARD, fg=TEXT_HI).pack(side="left", fill="x", expand=True, padx=6)

            tk.Button(header, text="✕", font=F_SMALL,
                      bg=WARN, fg=BG_DARK, relief="flat", padx=4,
                      command=lambda si=i: self._remove_slot(si)).pack(side="right", padx=2)

            moves_frame = tk.Frame(slot["frame"], bg=BG_CARD)
            moves_frame.pack(fill="x", padx=4, pady=2)
            slot["moves_label"] = tk.Label(moves_frame, text="",
                                           font=F_SMALL, bg=BG_CARD, fg="#888",
                                           justify="left")
            slot["moves_label"].pack(anchor="w")

            for widget in (slot["frame"], header):
                widget.bind("<ButtonPress-1>", lambda e, si=i: self._on_team_press(si, e))
                widget.bind("<ButtonRelease-1>", lambda e, si=i: self._on_team_release(si, e))
                widget.bind("<Enter>", lambda e, si=i: self._on_slot_enter(si))
                widget.bind("<Leave>", lambda e, si=i: self._on_slot_leave(si))

            self.team_slots.append(slot)

    def _reset_slot_highlight(self):
        for slot in self.team_slots:
            slot["frame"].config(bg=BG_CARD)

    def _on_slot_enter(self, slot_idx):
        if self._drag:
            self.team_slots[slot_idx]["frame"].config(bg=BG_DROP)

    def _on_slot_leave(self, slot_idx):
        if self._drag:
            self.team_slots[slot_idx]["frame"].config(bg=BG_CARD)

    # ── Drag: Bag ─────────────────────────────────────────
    def _on_bag_press(self, event):
        idx = self.bag_listbox.nearest(event.y)
        if 0 <= idx < len(self.bag_inventory):
            self._drag = {"kind": "bag", "idx": idx}
            self._drag_moved = False

    def _on_bag_motion(self, event):
        if self._drag and self._drag["kind"] == "bag":
            self._drag_moved = True

    def _on_bag_double_click(self, event):
        idx = self.bag_listbox.nearest(event.y)
        if 0 <= idx < len(self.bag_inventory):
            self._insert_at_slot(len(self.team_farm), self.bag_inventory[idx])

    # ── Drag: Team reorder ──────────────────────────────────
    def _on_team_press(self, slot_idx, event):
        if slot_idx < len(self.team_farm):
            self._drag = {"kind": "team", "idx": slot_idx}
            self._drag_moved = False

    def _on_team_release(self, slot_idx, event):
        if not self._drag:
            return

        kind = self._drag["kind"]
        from_idx = self._drag["idx"]

        if kind == "bag":
            if 0 <= from_idx < len(self.bag_inventory):
                self._insert_at_slot(slot_idx, self.bag_inventory[from_idx])
        elif kind == "team":
            self._reorder_team(from_idx, slot_idx)

        self._drag = None
        self._drag_moved = False
        self._reset_slot_highlight()

    def _on_global_release(self, event):
        if self._drag and self._drag["kind"] == "bag" and not self._drag_moved:
            self._drag = None
        self._reset_slot_highlight()

    # ── Team ops ──────────────────────────────────────────
    def _is_duplicate(self, pdata: dict) -> bool:
        pid = pdata.get("id")
        if pid is not None:
            return any(p.get("id") == pid for p in self.team_farm)
        return any(p.get("name") == pdata.get("name") for p in self.team_farm)

    def _insert_at_slot(self, slot_idx: int, pdata: dict) -> bool:
        if self._is_duplicate(pdata):
            pid = pdata.get("id", "?")
            messagebox.showwarning("Trùng", f"Pokemon [ID {pid}] đã có trong team!")
            return False

        entry = _copy_pokemon(pdata)
        pname = entry.get("name", "?")

        if len(self.team_farm) >= MAX_TEAM:
            if slot_idx < MAX_TEAM:
                self.team_farm[slot_idx] = entry
                self.status_var.set(f"↔ Thay slot #{slot_idx + 1} bằng {pname}")
            else:
                messagebox.showwarning("Đầy", f"Team đã đủ {MAX_TEAM} con!")
                return False
        elif slot_idx >= len(self.team_farm):
            self.team_farm.append(entry)
            self.status_var.set(f"➕ Thêm {pname} vào slot #{len(self.team_farm)}")
        else:
            self.team_farm.insert(slot_idx, entry)
            if len(self.team_farm) > MAX_TEAM:
                self.team_farm = self.team_farm[:MAX_TEAM]
            self.status_var.set(f"➕ Chèn {pname} vào slot #{slot_idx + 1}")

        self._update_team_display()
        return True

    def _reorder_team(self, from_idx: int, to_idx: int):
        if from_idx == to_idx:
            return
        if from_idx >= len(self.team_farm) or to_idx >= MAX_TEAM:
            return
        item = self.team_farm.pop(from_idx)
        to_idx = min(to_idx, len(self.team_farm))
        self.team_farm.insert(to_idx, item)
        self._update_team_display()
        self.status_var.set(f"↕ Đổi thứ tự: slot #{from_idx + 1} → #{to_idx + 1}")

    def _update_team_display(self):
        for i, slot in enumerate(self.team_slots):
            if i < len(self.team_farm):
                pdata = self.team_farm[i]
                pid = pdata.get("id", "?")
                pname = pdata.get("name", "?")
                slot["name_var"].set(f"[{pid}] {pname}")

                moves_text = ""
                for move in pdata.get("moves", []):
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
                slot["moves_label"].config(text="Kéo Pokemon vào đây", fg="#888")

        self.status_var.set(f"Team Farm: {len(self.team_farm)}/{MAX_TEAM}")
        if self.team_farm:
            names = ", ".join(f"[{p.get('id','?')}] {p.get('name','?')}" for p in self.team_farm)
            self.info_var.set(f"Team hiện tại: {names}")
        else:
            self.info_var.set("Team trống — kéo Pokemon từ Bag sang")

    def _update_bag_list(self):
        self.bag_listbox.delete(0, tk.END)
        for pdata in self.bag_inventory:
            self.bag_listbox.insert(tk.END, _format_bag_line(pdata))

    def _on_bag_select(self, event=None):
        selection = self.bag_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.bag_inventory):
                pdata = self.bag_inventory[idx]
                self.info_var.set(
                    f"Chọn: {_format_bag_line(pdata)} → kéo sang Team hoặc double-click"
                )

    def _remove_slot(self, slot_idx):
        if slot_idx < len(self.team_farm):
            removed = self.team_farm.pop(slot_idx)
            self._update_team_display()
            self.status_var.set(f"✕ Xóa [{removed.get('id', '?')}] {removed.get('name', '?')}")

    def _save_team(self):
        if len(self.team_farm) != MAX_TEAM:
            messagebox.showwarning(
                "Chưa đủ 6 con",
                f"Cần chọn đúng {MAX_TEAM} Pokemon mới lưu được!\n"
                f"Hiện tại: {len(self.team_farm)}/{MAX_TEAM}"
            )
            return

        TEAM_FARM_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            output = [_copy_pokemon(p) for p in self.team_farm]
            TEAM_FARM_PATH.write_text(
                json.dumps(output, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            names = ", ".join(
                f"[{p.get('id', '?')}] {p.get('name', '?')}" for p in self.team_farm
            )
            messagebox.showinfo(
                "✅ Lưu thành công",
                f"Team Farm ({MAX_TEAM}/{MAX_TEAM}):\n{names}\n\nFile: {TEAM_FARM_PATH}",
            )
            self.status_var.set(f"💾 Đã lưu {MAX_TEAM} Pokemon")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không lưu JSON: {e}")

    def _clear_team(self):
        if messagebox.askyesno("Xác nhận", "Xóa toàn bộ team farm?"):
            self.team_farm = []
            self._update_team_display()
            self.status_var.set("🗑️  Đã xóa team")

    def _reload_bag(self):
        self._load_data()
        self._update_bag_list()
        self._update_team_display()
        messagebox.showinfo("✅ Reload", f"Đã load {len(self.bag_inventory)} Pokemon từ bag")
