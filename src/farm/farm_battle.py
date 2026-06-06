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
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

# Import từ run_pokemon_tool (cùng ROOT)
ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
TEAM_PATH = ROOT / "src" / "config" / "team_party.json"
TYPE_CHART_PATH = ROOT / "src" / "data" / "type_chart.json"
BATTLE_STATE_PATH = ROOT / "src" / "runtime" / "battle_state.json"
FEEDBACK_LOG_PATH = ROOT / "src" / "runtime" / "feedback_log.txt"
TEMPLATE_DIR = ROOT / "src" / "template" / "cap_gamedefault"

FIGHT_TEMPLATE = TEMPLATE_DIR / "rightBarButtomFight.png"
POKEMON_TEMPLATE = TEMPLATE_DIR / "rightBarButtomPokemon.png"
RUN_TEMPLATE = TEMPLATE_DIR / "rightBarButtomRun.png"


# ==================== Helpers ====================

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


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
    with FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)


def open_team_json_editor(reason: str):
    try:
        import tkinter as tk
        from tkinter import messagebox, scrolledtext
    except Exception as exc:
        feedback_log(f"Khong mo duoc UI sua JSON: {exc}")
        return

    TEAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not TEAM_PATH.exists():
        TEAM_PATH.write_text("[]", encoding="utf-8")

    root = tk.Tk()
    root.title("Sua team_party.json")
    root.geometry("900x700")

    tk.Label(root, text=reason, anchor="w", justify="left").pack(fill="x", padx=8, pady=6)
    text = scrolledtext.ScrolledText(root, wrap="none", font=("Consolas", 10))
    text.pack(fill="both", expand=True, padx=8, pady=6)
    text.insert("1.0", TEAM_PATH.read_text(encoding="utf-8"))

    def save():
        raw = text.get("1.0", "end").strip()
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            messagebox.showerror("JSON loi", str(exc))
            return
        save_json(TEAM_PATH, parsed)
        messagebox.showinfo("Saved", f"Da luu {TEAM_PATH}")
        root.destroy()

    tk.Button(root, text="Save team_party.json", command=save).pack(pady=8)
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

def load_team() -> list:
    if not TEAM_PATH.exists():
        return []
    data = load_json(TEAM_PATH)
    if not isinstance(data, list) or len(data) == 0:
        return []
    return data


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
    eff = get_type_effectiveness(move_type, enemy_types) if enemy_types else 1.0

    use_zero_eff = config.get("farm", {}).get("use_zero_effectiveness", False)
    if eff == 0 and not use_zero_eff:
        return 0.0

    return base * stab * eff


def pick_best_move(moves: list, my_types: list, enemy_types: list, config: dict) -> int:
    """
    Trả về index (0-3) của move tốt nhất có PP > 0.
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

        # Bỏ qua power check vì moves từ JSON chưa có OCR
        # Chỉ yêu cầu pp_current > 0

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
    """Kiểm tra tất cả move đã hết PP chưa. Bỏ qua power check vì JSON chưa có OCR."""
    for move in moves:
        pp_current = move.get("pp_current")
        if pp_current is not None and pp_current > 0:
            return False
    return True


# ==================== OCR Move Panel ====================

def preprocess_for_ocr(img_bgr, scale=3):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def ocr_crop(img_bgr, config, psm=6) -> str:
    processed = preprocess_for_ocr(img_bgr)
    pil = Image.fromarray(processed)
    lang = config.get("ocr", {}).get("language", "eng")
    return pytesseract.image_to_string(pil, lang=lang, config=f"--psm {psm}").strip()


def parse_pp_from_text(text: str):
    m = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def parse_move_name_ocr(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 '\-]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _guess_move_data_from_name(name: str) -> dict:
    """Tra cứu move data từ bảng tĩnh trong team_builder_ui"""
    from src.team_builder.team_builder_ui import KNOWN_MOVES
    key = name.strip().lower()
    if key in KNOWN_MOVES:
        return dict(KNOWN_MOVES[key])
    for k, v in KNOWN_MOVES.items():
        if key in k or k in key:
            return dict(v)
    return {"type": "normal", "power": 0, "accuracy": 100}


def ocr_move_slots(image_bgr, config) -> list:
    """
    OCR 4 ô move từ ảnh screenshot toàn màn hình.
    Dùng ROI move_slots từ config.
    Trả về list 4 dict {name, type, power, accuracy, pp_current, pp_max}.
    """
    # Import fuzzy fix để sửa tên move nếu OCR sai nhẹ
    from run_pokemon_tool import fuzzy_fix_name
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


def wait_for_move_panel(screenshot_fn, config, save_debug_fn, timeout=2.0, interval=0.25):
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
    x, y, w, h = roi_list[0]
    cell = image_bgr[y:y+h, x:x+w]
    raw = ocr_crop(cell, config, psm=7)
    name = parse_move_name_ocr(raw.splitlines()[0] if raw.splitlines() else raw)
    return bool(re.search(r"[A-Za-z]{3,}", name))


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
    return parse_move_name_ocr(raw).lower().strip()


def verify_pokemon_name(image_bgr, config, current_pokemon) -> bool:
    """
    Verify pokemon hiện tại match với tên OCR từ battle.
    Trả về True nếu tên match, False nếu mismatch (có thể đã swap pokemon).
    """
    ocr_pokemon_name = ocr_pokemon_name_in_battle(image_bgr, config)
    if not ocr_pokemon_name:
        # Nếu OCR không đọc được, cho qua (không fail)
        return True

    json_pokemon_name = normalize(current_pokemon.get("name", ""))
    if json_pokemon_name != ocr_pokemon_name:
        feedback_log(
            f"⚠ Pokemon mismatch! JSON: '{json_pokemon_name}' vs OCR: '{ocr_pokemon_name}'. "
            f"Có thể đã swap Pokemon, skip lượt này."
        )
        return False

    return True


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
                  move_mouse_away_fn, save_debug_fn):
    """
    Mode 3: Auto farm tiền.

    win_api_module: dict với các hàm từ run_pokemon_tool.py:
      - set_cursor(x, y)
      - click(x, y, config)
      - focus_window_by_title(title)
    """
    import keyboard

    team = load_team()
    if not team:
        print("Chưa có team_party.json. Hãy chạy Menu 4 để đọc team trước!")
        feedback_log("ERROR: team_party.json rỗng hoặc không tồn tại.")
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
                # Vừa thoát battle → reset state
                feedback_log("Battle kết thúc. Reset state.")
                battle_state = reset_battle_state()
                current_slot = battle_state["current_slot"]
                depleted_slots = set()
                in_battle = False
                current_moves = []
                # Lưu lại team vào file khi kết thúc battle để đồng bộ PP
                from src.team_builder.team_builder_ui import save_team
                save_team(team)
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
            # Vừa vào battle mới
            in_battle = True
            # Đợi animation vào trận (header xuất hiện xong mới đến lượt nút Fight hiện ra)
            wait_time = config["timing"].get("battle_start_wait_seconds", 3.5)
            feedback_log(f"Mới vào trận, đợi {wait_time}s animation...")
            time.sleep(wait_time)

            image = screenshot_fn()
            enemy_name = read_enemy_name_fn(image, config)
            battle_state["enemy_name"] = enemy_name
            save_battle_state(battle_state)
            feedback_log(f"Vào battle với: {enemy_name or 'unknown'}")

        # Lấy Pokemon hiện tại
        pokemon = get_pokemon_by_slot(team, current_slot)
        if pokemon is None:
            feedback_log(f"Không tìm thấy Pokemon slot {current_slot} trong team!")
            print("Lỗi team JSON. Dừng.")
            return

        my_types = get_pokemon_types(pokemon)
        enemy_types = []  # Không fetch PokeAPI; dùng type chart chung

        # Đọc moves từ team (lần đầu vào battle hoặc sau swap)
        if not current_moves:
            current_moves = list(pokemon.get("moves", []))
            if not current_moves:
                feedback_log(f"Pokemon slot {current_slot} không có moves trong team JSON!")
                print("Chưa có moves. Dừng.")
                return
            # Reset PP theo team (hoặc pp_max nếu có)
            feedback_log(
                f"Check JSON slot {current_slot}: "
                f"{[(m.get('name'), m.get('pp_current'), m.get('power', 0)) for m in current_moves]}"
            )

        # Kiểm tra xem tất cả move tấn công có còn PP không
        if all_attack_moves_depleted(current_moves):
            feedback_log(f"Slot {current_slot} hết PP tấn công. Thử swap Pokemon.")
            depleted_slots.add(current_slot)
            battle_state["depleted_slots"] = list(depleted_slots)

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
                # Kiểm tra xem candidate có ít nhất 1 move còn PP hay không
                cand_moves = list(candidate.get("moves", []))
                has_attack_pp = False
                for mv in cand_moves:
                    pp_current = mv.get("pp_current")
                    if pp_current is not None and pp_current > 0:
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
            pokemon_threshold = config["template_matching"].get("pokemon_button_threshold", 0.55)
            pokemon_offset = config.get("click_offsets", {}).get("pokemon_button", [0, 0]) # This offset is applied after finding the center of the template
            clicked = _click_template(
                image, POKEMON_TEMPLATE, pokemon_threshold,
                config["roi"].get("pokemon_button_roi"), # Use specific ROI for Pokemon button
                pokemon_offset, config, win_api_module
            )
            if not clicked:
                feedback_log("Không click được nút Pokemon!")
                time.sleep(1)
                continue

            time.sleep(config["timing"].get("swap_menu_wait_seconds", 0.8))

            # Click slot Pokemon mới (0-indexed)
            click_pokemon_slot(new_slot - 1, config, win_api_module)
            time.sleep(config["timing"].get("swap_menu_wait_seconds", 0.8))

            current_slot = new_slot
            battle_state["current_slot"] = current_slot
            battle_state["depleted_slots"] = list(depleted_slots)
            save_battle_state(battle_state)
            current_moves = []  # Load lại moves của Pokemon mới
            feedback_log(f"Đã swap sang slot {current_slot}.")
            time.sleep(config["timing"].get("after_swap_wait_seconds", 2.0))
            continue

        # Click nút Fight
        move_mouse_away_fn(config)
        fight_threshold = config["template_matching"].get("fight_button_threshold", 0.55)
        fight_offset = config.get("click_offsets", {}).get("fight_button", [0, 0])

        clicked_fight = False
        # Retry 3 lần tìm nút Fight vì animation game có thể làm nút hiện ra chậm
        for attempt in range(3):
            image = screenshot_fn()
            clicked_fight = _click_template(
                image, FIGHT_TEMPLATE, fight_threshold,
                config["roi"].get("right_action_bar"),
                fight_offset, config, win_api_module
            )
            if clicked_fight:
                break

            # Kiểm tra nhanh: Nếu không thấy nút Fight, liệu có phải đã thoát Battle không?
            if not is_battle_fn(image, config):
                break # Thoát vòng lặp retry ngay lập tức

            feedback_log(f"Thử tìm nút Fight lần {attempt+1} (vẫn trong trận, chờ hiện)...")
            time.sleep(1.5)

        if not clicked_fight:
            # Nếu thực sự vẫn còn trong trận mà không thấy nút mới báo lỗi ROI
            if is_battle_fn(screenshot_fn(), config):
                feedback_log("Không tìm thấy nút Fight sau 3 lần thử. Hãy kiểm tra lại ROI trong Menu 4.")
                save_debug_fn(config, image, "fight_not_found_farm")
                time.sleep(config["timing"].get("battle_anim_wait_seconds", 3.0))
            else:
                feedback_log("Nút Fight biến mất do trận đấu đã kết thúc.")
                in_battle = False
            continue

        time.sleep(config["timing"].get("after_fight_click_seconds", 0.6))

        # Đợi move panel mở và OCR move
        if not wait_for_move_panel(screenshot_fn, config, save_debug_fn, timeout=2.0, interval=0.25):
            feedback_log("Move panel chưa sẵn sàng sau khi click Fight.")
            image = screenshot_fn()
            debug_move_slots(image, config, save_debug_fn)
        image = screenshot_fn()
        debug_move_slots(image, config, save_debug_fn)
        ocr_moves = ocr_move_slots(image, config)
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

        current_moves, valid_pp_reads = merge_pp_from_ocr_by_slot(current_moves, ocr_moves)
        pokemon["moves"] = current_moves
        if valid_pp_reads == 0:
            feedback_log("OCR PP khong doc duoc so hop le; giu PP trong team JSON, khong override move.")

        # === Verify Pokemon name match ===
        image_for_verify = screenshot_fn()
        if not verify_pokemon_name(image_for_verify, config, pokemon):
            feedback_log("Verify Pokemon thất bại. Skip lượt này để tránh click sai move.")
            time.sleep(config["timing"].get("battle_anim_wait_seconds", 3.0))
            continue

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
        
        from src.team_builder.team_builder_ui import save_team

        # Giảm PP
        if current_moves[best_idx].get("pp_current") is not None:
            old_pp = current_moves[best_idx]["pp_current"]
            current_moves[best_idx]["pp_current"] -= 1
            feedback_log(f"Đã trừ PP '{current_moves[best_idx]['name']}': {old_pp} -> {current_moves[best_idx]['pp_current']}")
            # Lưu lại file JSON ngay lập tức để người dùng kiểm tra
            save_team(team)

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
