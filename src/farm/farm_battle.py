"""
farm_battle.py – Menu 3: Auto farm tiền bằng cách đánh quái tự động.

Workflow trong mỗi vòng lặp:
  1. Kiểm tra battle header VS. – nếu không có, di chuyển A/D.
  2. Nếu vào battle:
     a. Đọc tên enemy từ header.
     b. Click nut Fight.
     c. OCR 4 move (tên, type, PP).
     d. Tính điểm từng move (type_eff × STAB × power × accuracy).
     e. Click move tốt nhất.
     f. Đợi animation.
     g. Lặp lại cho đến khi battle kết thúc.
  3. Nếu Pokemon hết PP move tấn công → click Pokemon → swap sang slot tiếp theo hợp lệ.
  4. Nếu không còn slot hợp lệ → báo lỗi và dừng.
"""

import json
import re
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

from src.ocr_utils import (
    normalize_text as normalize,
    preprocess_for_ocr,
    ocr_text as ocr_crop_old,
    parse_move_name as parse_move_name_ocr,
    parse_pp as parse_pp_from_text,
    guess_move_data as _guess_move_data_from_name,
    crop_roi,
)

ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
TEAM_FARM_PATH = ROOT / "src" / "config" / "team_farm.json"
TEAM_PARTY_PATH = ROOT / "src" / "config" / "team_party.json"  # legacy: Menu 4 / Team Builder cũ
TYPE_CHART_PATH = ROOT / "src" / "data" / "type_chart.json"
BATTLE_STATE_PATH = ROOT / "src" / "runtime" / "battle_state.json"
FEEDBACK_LOG_PATH = ROOT / "src" / "runtime" / "feedback_log.txt"
FEEDBACK_LOCK = threading.Lock()
TEMPLATE_DIR = ROOT / "src" / "template" / "cap_gamedefault"

FIGHT_TEMPLATE = TEMPLATE_DIR / "rightBarButtomFight.png"
POKEMON_TEMPLATE = TEMPLATE_DIR / "rightBarButtomPokemon.png"
RUN_TEMPLATE = TEMPLATE_DIR / "rightBarButtomRun.png"


# ==================== Helpers ====================


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def feedback_log(message: str):
    FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {message}\n"
    print(line, end="")
    with FEEDBACK_LOCK:
        with FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)


def open_team_json_editor(reason: str):
    try:
        import tkinter as tk
        from tkinter import messagebox, scrolledtext
    except Exception as exc:
        feedback_log(f"Khong mo duoc UI sua JSON: {exc}")
        return

    TEAM_FARM_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not TEAM_FARM_PATH.exists():
        TEAM_FARM_PATH.write_text("[]", encoding="utf-8")

    root = tk.Tk()
    root.title("Sua team_farm.json")
    root.geometry("900x700")

    tk.Label(root, text=reason, anchor="w", justify="left").pack(fill="x", padx=8, pady=6)
    text = scrolledtext.ScrolledText(root, wrap="none", font=("Consolas", 10))
    text.pack(fill="both", expand=True, padx=8, pady=6)
    text.insert("1.0", TEAM_FARM_PATH.read_text(encoding="utf-8"))

    def save():
        raw = text.get("1.0", "end").strip()
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            messagebox.showerror("JSON loi", str(exc))
            return
        save_json(TEAM_FARM_PATH, parsed)
        messagebox.showinfo("Saved", f"Da luu {TEAM_FARM_PATH}")
        root.destroy()

    tk.Button(root, text="Save team_farm.json", command=save).pack(pady=8)
    root.mainloop()


# ==================== Battle State ====================

def load_battle_state() -> dict:
    if BATTLE_STATE_PATH.exists():
        try:
            return load_json(BATTLE_STATE_PATH)
        except Exception:
            pass
    return {
        "current_slot": 1,
        "depleted_slots": [],   # Các slot đã hết PP move tấn công
        "enemy_name": "",
    }


def save_battle_state(state: dict):
    save_json(BATTLE_STATE_PATH, state)


def reset_battle_state():
    state = {
        "current_slot": 1,
        "depleted_slots": [],
        "enemy_name": "",
    }
    save_battle_state(state)
    return state


# ==================== Team ====================

def normalize_team_for_farm(raw: list) -> list:
    """Chuyển team_farm.json (bag format) sang format nội bộ farm (có slot, pp_current)."""
    team = []
    for i, p in enumerate(raw[:6]):
        moves = []
        for m in p.get("moves", []):
            mv = dict(m) if isinstance(m, dict) else {"name": str(m)}
            mv = enrich_move_data(mv)
            moves.append(mv)
        team.append({
            "slot": i + 1,
            "id": p.get("id", i + 1),
            "name": p.get("name", ""),
            "types": p.get("types", []),
            "moves": moves,
        })
    return team


def team_to_farm_json(team: list) -> list:
    """Ghi ngược team nội bộ về bag format (id, name, moves[{name, pp}])."""
    output = []
    for p in team:
        moves_out = []
        for m in p.get("moves", []):
            cur = m.get("pp_current")
            mx = m.get("pp_max")
            if cur is not None and mx is not None:
                pp_str = f"{cur}/{mx}"
            elif m.get("pp"):
                pp_str = str(m["pp"])
            else:
                pp_str = "?/?"
            moves_out.append({"name": m.get("name", ""), "pp": pp_str})
        output.append({
            "id": p.get("id"),
            "name": p.get("name", ""),
            "moves": moves_out,
        })
    return output


def save_farm_team(team: list):
    save_json(TEAM_FARM_PATH, team_to_farm_json(team))


def load_team() -> list:
    if not TEAM_FARM_PATH.exists():
        return []
    data = load_json(TEAM_FARM_PATH)
    if not isinstance(data, list) or len(data) == 0:
        return []
    return normalize_team_for_farm(data)


def get_pokemon_by_slot(team: list, slot: int) -> Optional[dict]:
    for p in team:
        if p.get("slot") == slot:
            return p
    return None


def get_pokemon_types(pokemon: dict) -> list:
    return [t.lower() for t in pokemon.get("types", [])]


# ==================== Type Effectiveness ====================

_type_chart: dict = {}


def load_type_chart():
    global _type_chart
    if not _type_chart and TYPE_CHART_PATH.exists():
        _type_chart = load_json(TYPE_CHART_PATH)


def get_type_effectiveness(move_type: str, defender_types: list) -> float:
    load_type_chart()
    mt = move_type.lower()
    if mt not in _type_chart:
        return 1.0
    effectiveness = 1.0
    for dt in defender_types:
        dt = dt.lower()
        mult = _type_chart[mt].get(dt, 1.0)
        effectiveness *= mult
    return effectiveness


def score_move(move: dict, my_types: list, enemy_types: list, config: dict) -> float:
    """
    Tính điểm move:
      base = power × (accuracy/100)
      stab = 1.5 nếu move_type in my_types
      eff  = type_effectiveness(move_type vs enemy_types)
      score = base × stab × eff
    Move power=0 (status/heal) → score=0.
    Nếu eff=0 và config cho phép dùng 0x → score cực nhỏ nhưng không dùng.
    """
    power = move.get("power", 0) or 0
    accuracy = move.get("accuracy", 100) or 100
    move_type = normalize(move.get("type", "normal"))

    if power <= 0:
        return 0.0

    base = power * (accuracy / 100.0)
    stab = config.get("farm", {}).get("stab_multiplier", 1.5) if move_type in my_types else 1.0
    eff = get_type_effectiveness(move_type, defender_types=enemy_types) if enemy_types else 1.0

    use_zero_eff = config.get("farm", {}).get("use_zero_effectiveness", False)
    if eff == 0 and not use_zero_eff:
        return 0.0

    return base * stab * eff


def pick_best_move(moves: list, my_types: list, enemy_types: list, config: dict) -> int:
    """
    Trả về index (0-3) của move tốt nhất có PP > 0 và GÂY SÁT THƯƠNG (power > 0).
    Tiebreak: score cao → power cao → pp_current cao → slot nhỏ.
    Trả về -1 nếu không có move nào hợp lệ.
    """
    best_idx = -1
    best_score = -1.0

    for i, move in enumerate(moves):
        pp_current = move.get("pp_current")
        power = move.get("power", 0) or 0

        if pp_current is None or pp_current <= 0:
            continue  # Hết PP
            
        if power <= 0:
            continue  # Bỏ qua các move buff/heal/status

        s = score_move(move, my_types, enemy_types, config)
        pp_cur = move.get("pp_current") or 0

        if s > best_score or (
            s == best_score and (
                power > (moves[best_idx].get("power", 0) if best_idx >= 0 else 0) or
                (power == (moves[best_idx].get("power", 0) if best_idx >= 0 else 0) and pp_cur > (moves[best_idx].get("pp_current") or 0))
            )
        ):
            best_score = s
            best_idx = i

    return best_idx


def all_attack_moves_depleted(moves: list) -> bool:
    """Kiểm tra xem CÁC MOVE CÓ SÁT THƯƠNG (power > 0) đã hết PP chưa."""
    for move in moves:
        power = move.get("power", 0) or 0
        pp_current = move.get("pp_current")
        if power > 0 and pp_current is not None and pp_current > 0:
            return False
    return True


# ==================== OCR Move Panel ====================


def enrich_move_data(move: dict) -> dict:
    """Bổ sung type, power, accuracy, pp_current nếu thiếu từ JSON"""
    m = dict(move)
    if "pp" in m and m.get("pp_current") is None:
        cur, mx = parse_pp_from_text(str(m["pp"]))
        if cur is not None:
            m["pp_current"] = cur
            m["pp_max"] = mx
    if "power" not in m or "type" not in m:
        guess = _guess_move_data_from_name(m.get("name", ""))
        m["type"] = m.get("type", guess.get("type", "normal"))
        m["power"] = m.get("power", guess.get("power", 0))
        m["accuracy"] = m.get("accuracy", guess.get("accuracy", 100))
    return m


def ocr_move_slots(image_bgr, config) -> list:
    """
    OCR 4 ô move từ ảnh screenshot toàn màn hình.
    Dùng ROI move_slots từ config.
    Trả về list 4 dict {name, type, power, accuracy, pp_current, pp_max}.
    """
    roi_list = config.get("roi", {}).get("move_slots", [])
    pp_roi_list = config.get("roi", {}).get("move_pp_slots", [])
    moves = []

    for i in range(4):
        move = {"name": f"Move{i+1}", "type": "normal", "power": 0, "accuracy": 100,
                "pp_current": None, "pp_max": None}

        # OCR tên move
        if i < len(roi_list):
            x, y, w, h = roi_list[i]
            cell = image_bgr[y:y+h, x:x+w]
            raw = ocr_crop(cell, config, psm=7)
            name = parse_move_name_ocr(raw.splitlines()[0] if raw.splitlines() else raw)
            move["name"] = normalize(name) if name else f"Move{i+1}"
            # Tra cứu data
            try:
                data = _guess_move_data_from_name(move["name"])
                move["type"] = data.get("type", "normal")
                move["power"] = data.get("power", 0)
                move["accuracy"] = data.get("accuracy", 100)
            except Exception:
                pass

        # OCR PP
        if i < len(pp_roi_list):
            x, y, w, h = pp_roi_list[i]
            pp_cell = image_bgr[y:y+h, x:x+w]
            pp_text = ocr_crop(pp_cell, config, psm=7)
            cur, mx = parse_pp_from_text(pp_text)
            move["pp_current"] = cur
            move["pp_max"] = mx

        moves.append(move)

    return moves


def update_move_pp_from_ocr(moves_list: list, ocr_moves: list) -> list:
    """
    Merge PP từ OCR vào move data từ team_party.json.
    Cập nhật trực tiếp vào moves_list (in-place) để persist dữ liệu.
    """
    for i in range(min(len(moves_list), 4)):
        if i < len(ocr_moves):
            ocr = ocr_moves[i]
            # Chỉ cập nhật nếu OCR đọc được con số thực tế, tránh reset về None
            if ocr.get("pp_current") is not None:
                moves_list[i]["pp_current"] = ocr["pp_current"]
            if ocr.get("pp_max") is not None:
                moves_list[i]["pp_max"] = ocr["pp_max"]
    return moves_list


def merge_pp_from_ocr_by_slot(team_moves: list, ocr_moves: list) -> tuple:
    """
    Keep JSON move name/type/power as the source of truth.
    OCR is only trusted for PP, and only when it reads a valid number.
    Returns (merged_moves, valid_pp_reads).
    """
    merged = []
    valid_pp_reads = 0
    for i, team_move in enumerate(team_moves[:4]):
        move = dict(team_move)
        if i < len(ocr_moves):
            ocr = ocr_moves[i]
            if ocr.get("pp_current") is not None:
                move["pp_current"] = ocr["pp_current"]
                valid_pp_reads += 1
            if ocr.get("pp_max") is not None:
                move["pp_max"] = ocr["pp_max"]
        merged.append(move)
    return merged, valid_pp_reads


def wait_for_move_panel(screenshot_fn, config, save_debug_fn, timeout=4.0, interval=0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        image = screenshot_fn()
        if is_move_panel_open(image, config):
            return True
        time.sleep(interval)
    save_debug_fn(config, image, "move_panel_not_ready")
    return False


def is_move_panel_open(image_bgr, config) -> bool:
    roi_list = config.get("roi", {}).get("move_slots", [])
    if not roi_list:
        return False
    # Kiểm tra cả 4 slot, chỉ cần 1 slot có ít nhất 2 chữ cái là coi như đã mở
    for i in range(min(4, len(roi_list))):
        x, y, w, h = roi_list[i]
        cell = image_bgr[y:y+h, x:x+w]
        # Dùng PSM 11 (Sparse text) để nhận diện chữ trên nền màu tốt hơn
        raw = ocr_crop(cell, config, psm=11)
        # Đếm số lượng chữ cái (A-Z, a-z)
        letters = re.findall(r"[A-Za-z]", raw)
        if len(letters) >= 2:
            return True
    return False


def debug_move_slots(image_bgr, config, save_debug_fn):
    move_names = []
    roi_list = config.get("roi", {}).get("move_slots", [])
    for i, roi in enumerate(roi_list[:4]):
        x, y, w, h = roi
        cell = image_bgr[y:y+h, x:x+w]
        raw = ocr_crop(cell, config, psm=7)
        move_names.append((i + 1, raw.strip()))
        save_debug_fn(config, cell, f"move_slot_{i+1}")
    # print("[DEBUG] MOVE_SLOT_OCR:", move_names)


def ocr_pokemon_name_in_battle(image_bgr, config) -> str:
    """OCR tên Pokemon từ vị trí góc dưới trái (bên cạnh HP bar)."""
    roi = config.get("roi", {}).get("pokemon_name_in_battle")
    if not roi:
        return ""
    x, y, w, h = roi
    cell = image_bgr[y:y+h, x:x+w]
    raw = ocr_crop(cell, config, psm=7)
    return clean_pokemon_ocr_name(raw)


def clean_pokemon_ocr_name(raw: str) -> str:
    """Làm sạch tên Pokemon OCR (bỏ ký tự rác đầu như -, y, v...)."""
    s = parse_move_name_ocr(raw).lower().strip()
    s = re.sub(r"^[^a-z]+", "", s)
    return s


def find_slot_by_pokemon_name(team: list, ocr_name: str) -> Optional[int]:
    """Fuzzy match tên OCR với team, trả về slot hoặc None."""
    clean = clean_pokemon_ocr_name(ocr_name)
    if not clean:
        return None
    clean_alpha = re.sub(r"[^a-z]", "", clean)

    best_slot = None
    best_ratio = 0.0
    for p in team:
        json_name = re.sub(r"[^a-z]", "", normalize(p.get("name", "")))
        if not json_name:
            continue
        if json_name == clean_alpha or json_name in clean_alpha or clean_alpha in json_name:
            return p.get("slot")
        ratio = difflib.SequenceMatcher(None, json_name, clean_alpha).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_slot = p.get("slot")
    if best_ratio >= 0.65:
        return best_slot
    return None


def find_slot_by_move_ocr(team: list, ocr_moves: list, min_matches: int = 2) -> Optional[int]:
    """
    Xác định Pokemon đang ra sân bằng cách so khớp 4 move OCR với team JSON.
    Đáng tin hơn đọc tên khi menu Fight đã mở (ROI tên dễ bị che).
    """
    ocr_names = set()
    for m in ocr_moves:
        name = normalize(m.get("name", ""))
        if name and name not in ("move1", "move2", "move3", "move4"):
            ocr_names.add(name)
    if not ocr_names:
        return None

    best_slot = None
    best_score = 0
    for p in team:
        team_moves = {
            normalize(m.get("name", ""))
            for m in p.get("moves", [])
            if m.get("name")
        }
        score = len(ocr_names & team_moves)
        if score > best_score:
            best_score = score
            best_slot = p.get("slot")
    if best_score >= min_matches:
        return best_slot
    return None


# ==================== Click Helpers ====================

def _click_template(image, template_path, threshold, roi, offset, config,
                    win_api_module, repeat=1, gap=0.25):
    """Tìm template trong ROI và click. Trả về True nếu click được."""
    import ctypes
    from pathlib import Path as _Path

    template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if template is None:
        feedback_log(f"Template không tìm thấy: {template_path}")
        return False

    search = image
    ox, oy = 0, 0
    if roi:
        x, y, w, h = roi
        search = image[y:y+h, x:x+w]
        ox, oy = x, y

    # Ensure template is not larger than search; if it is, scale template down to fit
    th, tw = template.shape[:2]
    sh, sw = search.shape[:2]
    if th > sh or tw > sw:
        scale = min(sh / th, sw / tw)
        if scale <= 0:
            feedback_log(f"Template {template_path} too large for search area; skipping")
            return False
        new_w = max(1, int(tw * scale))
        new_h = max(1, int(th * scale))
        template = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)

    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        feedback_log(f"Không tìm thấy template {_Path(str(template_path)).name} (score={max_val:.2f})")
        return False

    th, tw = template.shape[:2]
    cx = ox + max_loc[0] + tw // 2 + offset[0]
    cy = oy + max_loc[1] + th // 2 + offset[1]

    win_api_module["set_cursor"](int(cx), int(cy))
    time.sleep(0.05)
    for idx in range(repeat):
        win_api_module["click"](cx, cy, config)
        if idx < repeat - 1:
            time.sleep(gap)

    feedback_log(f"Click {_Path(str(template_path)).name} tại ({cx},{cy}) score={max_val:.2f}")
    return True


def click_move_slot(slot_index: int, config, win_api_module, image):
    """
    Click vào ô move slot_index (0-3) dựa trên ROI move_slots từ config.
    """
    roi_list = config.get("roi", {}).get("move_slots", [])
    if slot_index >= len(roi_list):
        feedback_log(f"ROI move slot {slot_index} chưa có trong config!")
        return False

    x, y, w, h = roi_list[slot_index]
    cx = x + w // 2
    cy = y + h // 2

    win_api_module["set_cursor"](int(cx), int(cy))
    time.sleep(0.05)
    win_api_module["click"](cx, cy, config)
    feedback_log(f"Click move slot {slot_index+1} tại ({cx},{cy})")
    return True


def click_pokemon_slot(slot_index: int, config, win_api_module):
    """
    Click vào ô Pokemon swap slot_index (0-5) sau khi mở menu Pokemon.
    """
    roi_list = config.get("roi", {}).get("pokemon_swap_slots", [])
    if slot_index >= len(roi_list):
        feedback_log(f"ROI pokemon swap slot {slot_index} chưa có trong config!")
        return False

    x, y, w, h = roi_list[slot_index]
    cx = x + w // 2
    cy = y + h // 2

    win_api_module["set_cursor"](int(cx), int(cy))
    time.sleep(0.05)
    win_api_module["click"](cx, cy, config)
    feedback_log(f"Click Pokemon swap slot {slot_index+1} tại ({cx},{cy})")
    return True


# ==================== Main Farm Loop ====================

def run_farm_mode(config, win_api_module, screenshot_fn, is_battle_fn,
                  read_enemy_name_fn, move_until_next_scan_fn,
                  wait_until_battle_exits_fn, focus_window_fn, find_window_fn,
                  move_mouse_away_fn, save_debug_fn, stop_event=None):
    """
    Mode 3: Auto farm tiền.

    win_api_module: dict với các hàm từ run_pokemon_tool.py:
      - set_cursor(x, y)
      - click(x, y, config)
      - focus_window_by_title(title)
    
    stop_event: threading.Event để dừng farm từ GUI (optional)
    """
    import keyboard

    team = load_team()
    if not team:
        print("Chưa có team_farm.json. Hãy chạy Tab 5 Auto Farm Config trước!")
        feedback_log("ERROR: team_farm.json rỗng hoặc không tồn tại. Chạy Tab 5 để chọn 6 Pokemon.")
        return
    if len(team) < 6:
        feedback_log(f"ERROR: team_farm.json chỉ có {len(team)}/6 Pokemon. Chạy Tab 5 để chọn đủ 6.")
        return

    # Khởi tạo tesseract
    tess_cmd = config.get("ocr", {}).get("tesseract_cmd", "").strip()
    if tess_cmd:
        pytesseract.pytesseract.tesseract_cmd = tess_cmd

    load_type_chart()

    # Reset battle state khi bắt đầu
    battle_state = reset_battle_state()
    current_slot = battle_state.get("current_slot", 1)
    depleted_slots = set(battle_state.get("depleted_slots", []))

    in_battle = False
    current_moves: list = []  # Moves đang dùng (từ team + cập nhật PP)

    print(f"Dang chay mode 3 (Auto Farm). Bam Q de dung.")
    feedback_log("=== Bắt đầu Mode 3: Auto Farm ===")

    while True:
        # Check stop_event từ GUI (priority cao hơn)
        if stop_event and stop_event.is_set():
            feedback_log("Dừng tool từ GUI.")
            return
        
        # Fallback: keyboard check (cho backward compatibility)
        if keyboard.is_pressed("q"):
            print("Da dung tool bang phim Q.")
            feedback_log("Dừng tool bằng Q.")
            return

        # Delay nhỏ để tránh spam OCR gây lỗi WinError 32
        time.sleep(0.3)

        # Focus window
        hwnd = find_window_fn(config["window_title"])
        if hwnd:
            focus_window_fn(hwnd)

        image = screenshot_fn()

        # Kiểm tra battle
        try:
            battle_detected = is_battle_fn(image, config)
        except Exception as e:
            feedback_log(f"Lỗi OCR header: {e}")
            time.sleep(1)
            continue

        if not battle_detected:
            if in_battle:
                feedback_log("Battle kết thúc. Mặc định trận sau sẽ bắt đầu với Slot 1.")
                battle_state = reset_battle_state()
                current_slot = 1 # Luôn reset về 1 khi hết trận
                depleted_slots = set()
                in_battle = False
                current_moves = []

                save_farm_team(team)
                time.sleep(config["timing"].get("after_run_wait_seconds", 4.0))
                continue

            # Chưa vào battle → di chuyển A/D
            print("Chua vao battle, di chuyen A/D...")
            if not move_until_next_scan_fn(config):
                print("Da dung tool bang phim Q.")
                return
            continue

        # === Đang trong battle ===
        if not in_battle:
            # ... (giữ nguyên đoạn nhận diện enemy) ...
            in_battle = True
            wait_time = config.get("timing", {}).get("battle_start_wait_seconds", 5.0)
            feedback_log(f"Mới vào trận, đợi {wait_time}s animation...")
            time.sleep(wait_time)

        # Nhận diện Pokemon trên sân (chỉ tin ROI tên khi chưa mở menu Fight)
        image = screenshot_fn()
        on_field_name = ocr_pokemon_name_in_battle(image, config)
        found_slot = find_slot_by_pokemon_name(team, on_field_name) if on_field_name else None
        if found_slot and found_slot != current_slot:
            pname = get_pokemon_by_slot(team, found_slot)
            feedback_log(
                f"Phát hiện '{on_field_name}' trên sân → Slot {found_slot} "
                f"({pname.get('name', '?') if pname else '?'})"
            )
            current_slot = found_slot
            battle_state["current_slot"] = current_slot
            save_battle_state(battle_state)
            current_moves = []

        # Lấy Pokemon hiện tại dựa trên Slot đã được sync
        pokemon = get_pokemon_by_slot(team, current_slot)
        # ... (đoạn load moves, check PP bên dưới giữ nguyên) ...
        if pokemon is None:
            feedback_log(f"Không tìm thấy Pokemon slot {current_slot} trong team!")
            print("Lỗi team JSON. Dừng.")
            return

        my_types = get_pokemon_types(pokemon)
        enemy_types = []  # Không fetch PokeAPI; dùng type chart chung

        # Đọc moves từ team (lần đầu vào battle hoặc sau swap)
        if not current_moves:
            raw_moves = list(pokemon.get("moves", []))
            if not raw_moves:
                feedback_log(f"Pokemon slot {current_slot} không có moves trong team JSON!")
                print("Chưa có moves. Dừng.")
                return
            current_moves = [enrich_move_data(mv) for mv in raw_moves]
            feedback_log(
                f"Check JSON slot {current_slot}: "
                f"{[(m.get('name'), m.get('pp_current'), m.get('power', 0)) for m in current_moves]}"
            )

        if all_attack_moves_depleted(current_moves):
            feedback_log(f"Slot {current_slot} hết PP tấn công. Thử swap Pokemon.")
            depleted_slots.add(current_slot)
            battle_state["depleted_slots"] = list(depleted_slots)

            # --- In ra tình trạng PP của cả 6 slot để dễ debug ---
            feedback_log("--- TÌNH TRẠNG PP CỦA TEAM TRƯỚC KHI SWAP ---")
            for i in range(1, 7):
                pkm = get_pokemon_by_slot(team, i)
                if not pkm:
                    feedback_log(f"Slot {i}: Trống")
                    continue
                name = pkm.get("name", "Unknown")
                mvs = [enrich_move_data(m) for m in pkm.get("moves", [])]
                mv_str = ", ".join([f"{m.get('name')}({m.get('pp_current')}/{m.get('pp_max')} - Pwr:{m.get('power',0)})" for m in mvs])
                
                status = ""
                if i == current_slot:
                    status = "[Đang ra sân]"
                elif i in depleted_slots:
                    status = "[Đã hết PP]"
                else:
                    has_atk = any((m.get("power", 0) or 0) > 0 and (m.get("pp_current") or 0) > 0 for m in mvs)
                    if has_atk:
                        status = "[SẴN SÀNG]"
                    else:
                        status = "[Bỏ qua do ko có chiêu Sát thương còn PP]"
                feedback_log(f"Slot {i} {name} {status}: {mv_str}")
            feedback_log("-----------------------------------------------")

            # Tìm slot tiếp theo: chỉ chọn slot khác current, chưa bị đánh dấu depleted,
            # và có ít nhất 1 move tấn công còn PP (>0). Nếu không có thì trả None.
            new_slot = None
            for slot in range(1, 7):
                if slot == current_slot:
                    continue
                if slot in depleted_slots:
                    continue
                candidate = get_pokemon_by_slot(team, slot)
                if not candidate or not candidate.get("moves"):
                    continue
                # Kiểm tra xem candidate có ít nhất 1 move tấn công (power > 0) còn PP hay không
                cand_moves = [enrich_move_data(mv) for mv in list(candidate.get("moves", []))]
                has_attack_pp = False
                for mv in cand_moves:
                    power = mv.get("power", 0) or 0
                    pp_current = mv.get("pp_current")
                    if power > 0 and pp_current is not None and pp_current > 0:
                        has_attack_pp = True
                        break
                if has_attack_pp:
                    new_slot = slot
                    break

            if new_slot is None:
                feedback_log("Không còn slot Pokemon hợp lệ! Dừng farm.")
                print("Hết Pokemon để swap. Dừng tool.")
                return

            # Click nút Pokemon để mở menu swap
            move_mouse_away_fn(config)
            image = screenshot_fn()
            clicked = False

            # Ưu tiên click tọa độ ROI (Đã lấy từ Menu 4)
            p_roi = config["roi"].get("pokemon_button_roi")
            if p_roi:
                px, py, pw, ph = p_roi
                cx, cy = px + pw // 2, py + ph // 2
                win_api_module["set_cursor"](int(cx), int(cy))
                time.sleep(0.05)
                win_api_module["click"](cx, cy, config)
                feedback_log(f"Click Pokemon button (ROI) tại ({cx},{cy})")
                clicked = True
            else:
                pokemon_threshold = config["template_matching"].get("pokemon_button_threshold", 0.55)
                pokemon_offset = config.get("click_offsets", {}).get("pokemon_button", [0, 0])
                clicked = _click_template(image, POKEMON_TEMPLATE, pokemon_threshold, None, pokemon_offset, config, win_api_module)

            if not clicked:
                feedback_log("Không click được nút Pokemon!")
                time.sleep(1)
                continue
            # Đợi menu swap load. Có thể cấu hình trong config["timing"]:
            #  - "swap_menu_wait_seconds" (existing, default 0.8)
            #  - "swap_menu_extra_delay_seconds" (mới, default 2.0) để phòng trường hợp animation chậm
            base_wait = config["timing"].get("swap_menu_wait_seconds", 0.8)
            extra_wait = config["timing"].get("swap_menu_extra_delay_seconds", 2.0)
            total_wait = base_wait + (extra_wait if extra_wait and extra_wait > 0 else 0)
            feedback_log(f"Chờ menu swap load: {total_wait}s (base={base_wait}s, extra={extra_wait}s)")
            time.sleep(total_wait)

            # Click slot Pokemon mới (0-indexed)
            click_pokemon_slot(new_slot - 1, config, win_api_module)

            # Chỉ cần đợi một khoảng cố định đủ cho animation ra sân
            wait_swap = config["timing"].get("after_swap_wait_seconds", 3.0)
            feedback_log(f"Đã chọn slot {new_slot}. Chờ {wait_swap}s ra sân...")
            time.sleep(wait_swap)

            # Sau swap, xác nhận lại Pokemon trên sân bằng OCR để tránh lặp swap
            image_after_swap = screenshot_fn()
            on_field_name_after = ocr_pokemon_name_in_battle(image_after_swap, config)
            if on_field_name_after:
                detected_slot = find_slot_by_pokemon_name(team, on_field_name_after)

                if detected_slot is None:
                    feedback_log(f"Không xác định được Pokemon sau swap; OCR: '{on_field_name_after}'. Giữ slot mặc định {new_slot}.")
                    current_slot = new_slot
                elif detected_slot != new_slot:
                    feedback_log(f"Sau swap, phát hiện trên sân là slot {detected_slot} (OCR '{on_field_name_after}'), không phải slot {new_slot}. Cập nhật slot hiện tại.")
                    current_slot = detected_slot
                else:
                    current_slot = new_slot
            else:
                # Nếu OCR không đọc được tên, vẫn lấy new_slot làm slot hiện tại
                current_slot = new_slot

            # Cập nhật state và RESET moves để vòng lặp sau load lại từ đầu
            battle_state["current_slot"] = current_slot
            battle_state["depleted_slots"] = list(depleted_slots)
            save_battle_state(battle_state)
            current_moves = [] # Quan trọng: Reset để nhận diện chiêu thức con mới
            continue

        # --- CLICK FIGHT: Đơn giản hóa để không làm "hư" code ---
        move_mouse_away_fn(config)
        clicked_fight = False

        image = screenshot_fn()
        f_roi = config["roi"].get("fight_button_roi")
        if f_roi:
            # Click theo tọa độ bạn đã calibrate
            fx, fy, fw, fh = f_roi
            cx, cy = fx + fw // 2, fy + fh // 2
            win_api_module["set_cursor"](int(cx), int(cy))
            time.sleep(0.1)
            win_api_module["click"](cx, cy, config)
            feedback_log(f"Click Fight tại ({cx},{cy})")
            clicked_fight = True
        else:
        # Fallback nếu chưa calibrate
                fight_threshold = config["template_matching"].get("fight_button_threshold", 0.55)
                clicked_fight = _click_template(image, FIGHT_TEMPLATE, fight_threshold, None, [0,0], config, win_api_module)
        if not clicked_fight:
            feedback_log("Chưa thấy nút Fight, chờ lượt sau...")
            time.sleep(1.0)
            continue

        # Sau khi click Fight, đợi bảng Move hiện ra
        time.sleep(config["timing"].get("after_fight_click_seconds", 1.0))

        # Kiểm tra bảng Move có sẵn sàng để OCR không
        image_check = screenshot_fn()
        if not is_move_panel_open(image_check, config):
            # Đợi thêm 1s và check lại lần cuối (đề phòng lag)
            time.sleep(1.0)
            image_check = screenshot_fn()
            if not is_move_panel_open(image_check, config):
                feedback_log("Bảng chiêu thức vẫn chưa hiện theo OCR. Thử lại...")
                continue

        # --- TIẾP TỤC OCR VÀ ĐÁNH ---
        # Dùng luôn ảnh vừa check để tiết kiệm thời gian
        ocr_moves = ocr_move_slots(image_check, config)
        feedback_log(f"OCR Check PP: {[(m['name'], m.get('pp_current')) for m in ocr_moves]}")

        # Đồng bộ moves hiện tại với kết quả OCR: ưu tiên dùng tên/PP từ OCR
        def merge_moves_from_ocr(team_moves, ocr_moves):
            merged = []
            for i in range(4):
                ocr = ocr_moves[i] if i < len(ocr_moves) else {}
                ocr_name = ocr.get("name") or ""
                norm_ocr_name = normalize(ocr_name)

                # Thử khớp chính xác với move trong team (theo tên chuẩn hóa)
                matched = None
                for tm in team_moves:
                    if normalize(tm.get("name", "")) == norm_ocr_name and tm.get("power", 0) is not None:
                        matched = dict(tm)
                        break

                if matched is None:
                    # Nếu không khớp, đoán dữ liệu move theo tên OCR
                    guess = _guess_move_data_from_name(norm_ocr_name)
                    matched = {
                        "name": norm_ocr_name or f"Move{i+1}",
                        "type": guess.get("type", "normal"),
                        "power": guess.get("power", 0),
                        "accuracy": guess.get("accuracy", 100),
                        "pp_current": ocr.get("pp_current"),
                        "pp_max": ocr.get("pp_max"),
                    }
                else:
                    # Cập nhật PP từ OCR nếu có
                    if ocr.get("pp_current") is not None:
                        matched["pp_current"] = ocr.get("pp_current")
                    if ocr.get("pp_max") is not None:
                        matched["pp_max"] = ocr.get("pp_max")

                merged.append(matched)
            return merged

        # Đồng bộ slot theo moves OCR (đáng tin hơn đọc tên khi menu Fight đã mở)
        move_slot = find_slot_by_move_ocr(team, ocr_moves, min_matches=2)
        if move_slot and move_slot != current_slot:
            pokemon = get_pokemon_by_slot(team, move_slot)
            if pokemon:
                feedback_log(
                    f"Đồng bộ slot {move_slot} theo moves OCR "
                    f"({pokemon.get('name', '?')}): "
                    f"{[m.get('name') for m in ocr_moves]}"
                )
                current_slot = move_slot
                battle_state["current_slot"] = current_slot
                save_battle_state(battle_state)
                raw_moves = list(pokemon.get("moves", []))
                current_moves = [enrich_move_data(mv) for mv in raw_moves]
                my_types = get_pokemon_types(pokemon)

        current_moves, valid_pp_reads = merge_pp_from_ocr_by_slot(current_moves, ocr_moves)
        pokemon["moves"] = current_moves
        if valid_pp_reads == 0:
            feedback_log("OCR PP khong doc duoc so hop le; giu PP trong team JSON, khong override move.")

        # Chọn move tốt nhất
        best_idx = pick_best_move(current_moves, my_types, enemy_types, config)

        if best_idx == -1:
            feedback_log("Không có move hợp lệ (hết PP hoặc 0x effectiveness). Thử lần sau.")
            # Đóng menu Fight bằng cách chờ
            time.sleep(config["timing"].get("battle_anim_wait_seconds", 3.0))
            continue

        move_info = current_moves[best_idx]
        feedback_log(
            f"Chọn Move {best_idx+1}: '{move_info['name']}' "
            f"(type={move_info.get('type','?')}, "
            f"pwr={move_info.get('power','?')}, "
            f"pp={move_info.get('pp_current','?')}/{move_info.get('pp_max','?')})"
        )

        # Click move slot
        image = screenshot_fn()
        click_move_slot(best_idx, config, win_api_module, image)
        
        # Giảm PP
        if current_moves[best_idx].get("pp_current") is not None:
            old_pp = current_moves[best_idx]["pp_current"]
            current_moves[best_idx]["pp_current"] -= 1
            feedback_log(f"Đã trừ PP '{current_moves[best_idx]['name']}': {old_pp} -> {current_moves[best_idx]['pp_current']}")
            save_farm_team(team)

        # Đợi animation battle
        time.sleep(config["timing"].get("after_move_click_seconds", 1.0))
        # Delay thêm theo yêu cầu để check quái chết hay chưa
        feedback_log("Đang đợi animation chiêu thức...")
        time.sleep(config["timing"].get("battle_anim_wait_seconds", 3.0))

        # Kiểm tra nhanh xem còn trong battle không trước khi lặp lại tìm nút Fight
        image_after = screenshot_fn()
        if not is_battle_fn(image_after, config):
            feedback_log("Battle kết thúc sau lượt đánh (Quái đã chết hoặc chạy).")
            in_battle = False
            continue

