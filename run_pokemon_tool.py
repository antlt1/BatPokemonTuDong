import ctypes
import json
import random
import re
import shutil
import subprocess
import sys
import time
import winsound
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Optional

import copy
import difflib

import cv2
import keyboard
import mss
import numpy as np
import pytesseract
from PIL import Image

from src.ocr_utils import (
    normalize_text,
    preprocess_for_ocr,
    ocr_text,
    ocr_text_variants,
    fuzzy_fix_name as _fuzzy_fix_name,
    get_known_pokemon_names,
    crop_roi,
    set_tesseract_path,
)

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
TARGETS_PATH = ROOT / "src" / "config" / "target_pokemon.json"
TEAM_PATH = ROOT / "src" / "config" / "team_party.json"
TEMPLATE_DIR = ROOT / "src" / "template" / "cap_gamedefault"
RUN_TEMPLATE_PATH = TEMPLATE_DIR / "rightBarButtomRun.png"

VK_A = 0x41
VK_D = 0x44
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

user32 = ctypes.windll.user32

# Cấu trúc INPUT và MOUSEINPUT để gửi sự kiện chuột qua SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

# INPUT_UNION để hỗ trợ nhiều loại input khác nhau, ở đây chỉ dùng MOUSEINPUT
class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

# INPUT để gửi đến SendInput, có thể mở rộng để hỗ trợ bàn phím nếu cần
class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)





def ensure_runtime(config):
    missing = []
    for module_name in ("cv2", "mss", "PIL", "pytesseract", "keyboard"):
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)

    tesseract_cmd = config["ocr"].get("tesseract_cmd", "").strip()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        pytesseract.get_tesseract_version()
    except Exception:
        missing.append("tesseract.exe")

    if missing:
        print("Thiếu dependency:", ", ".join(sorted(set(missing))))
        print("Cài Python package: pip install -r requirements.txt")
        print("Thiếu tesseract.exe, cài Tesseract Windows và thêm vào PATH")
        print("hoặc điền đường dẫn vào src/config/tool_config.json -> ocr.tesseract_cmd")
        return False

    return True

# tìm cửa sổ game dựa trên một phần của tiêu đề, trả về handle cửa sổ nếu tìm thấy, hoặc None nếu không tìm thấy
def find_window(title_part):
    handles = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if title_part.lower() in buffer.value.lower():
            handles.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    return handles[0] if handles else None


def focus_window(hwnd):
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)


def screenshot_bgr():
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        shot = np.array(sct.grab(monitor))
    return cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)





def save_debug(config, image, label):
    if not config["debug"].get("save_failed_ocr", True):
        return
    debug_dir = ROOT / config["debug"]["directory"]
    debug_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = debug_dir / f"{stamp}_{label}.png"
    cv2.imwrite(str(path), image)


def clear_debug(config):
    debug_dir = ROOT / config["debug"]["directory"]
    if not debug_dir.exists():
        print("Chua co thu muc debug de xoa.")
        return
    removed = 0
    for path in debug_dir.glob("*.png"):
        path.unlink()
        removed += 1
    print(f"Da xoa {removed} anh debug.")





def extract_enemy_name(text):
    normalized = normalize_text(text)
    patterns = [
        r"vs\.?\s+wild\s+([a-z0-9 '\-]+)",
        r"a\s+wild\s+([a-z0-9 '\-]+?)\s+attacks",
        r"sends\s+out\s+([a-z0-9 '\-]+)",
        r"opposing\s+([a-z0-9 '\-]+?)\s+attacks",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            name = match.group(1)
            name = re.split(r"\s{2,}| lvl? | lv | attacks| ability|!|\n", name)[0]
            return normalize_text(name)
    # Nếu không match các pattern trên, thử match dạng 'Name Lv. 16' với OCR lỗi phổ biến
    lv_patterns = [r"([a-z'\- ]{3,}?)\s*(?:lv|l v|l\.v|lv\.|slv|sllv|lv)\s*\d+",
                   r"([a-z'\- ]{3,}?)\s*\u00b7?\s*Lv\.?\s*\d+"]
    for p in lv_patterns:
        m = re.search(p, normalized)
        if m:
            name = m.group(1)
            name = re.split(r"\s{2,}| ability|!|\n", name)[0]
            return normalize_text(name)
    return ""





def is_battle(image, config):
    header = crop_roi(image, config["roi"]["battle_header"])
    text = ocr_text_variants(header, config, psm=6)
    # In raw OCR header để debug
    # print("[DEBUG] OCR_HEADER_RAW:", repr(text))
    norm = normalize_text(text)
    # Chuẩn hóa chỉ giữ chữ thường và khoảng trắng
    letters_spaces = re.sub(r"[^a-z\s]", " ", norm)
    # Tìm 'vs' hoặc 'wild' để xác định đang trong trận
    if (re.search(r"\bv\s*s\b", letters_spaces) or 
        "vs" in letters_spaces.replace(" ", "") or 
        "wild" in letters_spaces):
        return True
    # Nếu header không rõ, thử OCR vùng tên đối thủ trực tiếp
    try:
        enemy_roi = crop_roi(image, config["roi"]["enemy_name"])
        enemy_text = ocr_text_variants(enemy_roi, config, psm=7)
        enemy_norm = normalize_text(enemy_text)
        # Chỉ chấp nhận là battle nếu có chữ cái (tên) VÀ dấu hiệu Level (lv, số, hoặc dấu chấm của Lv.)
        if re.search(r"[a-z]{3,}", enemy_norm) and re.search(r"lv|\d+|\.", enemy_norm):
            return True
    except Exception:
        pass
    save_debug(config, header, "no_vs_header")
    return False


def read_enemy_name(image, config):
    header = crop_roi(image, config["roi"]["battle_header"])
    header_text = ocr_text_variants(header, config, psm=6)
    header_name = extract_enemy_name(header_text)
    if header_name:
        return fuzzy_fix_name(header_name)

    log_image = crop_roi(image, config["roi"]["battle_log"])
    log_text = ocr_text_variants(log_image, config, psm=6)
    log_name = extract_enemy_name(log_text)
    if log_name:
        return fuzzy_fix_name(log_name)

    roi_image = crop_roi(image, config["roi"]["enemy_name"])
    text = ocr_text_variants(roi_image, config, psm=7)
    cleaned = re.sub(r"[^A-Za-z0-9 '\\-]", " ", text)
    cleaned = normalize_text(cleaned)
    if not cleaned:
        # Lưu ảnh debug cho cả header, log và roi tên để phân tích
        save_debug(config, header, "debug_header_no_name")
        save_debug(config, log_image, "debug_log_no_name")
        save_debug(config, roi_image, "debug_enemy_name_empty")
        # print("[DEBUG] OCR_HEADER_RAW:", repr(header_text))
        # print("[DEBUG] OCR_LOG_RAW:", repr(log_text))
        # print("[DEBUG] OCR_ROI_RAW:", repr(text))
    # Try fuzzy fix against known names
    return fuzzy_fix_name(cleaned)

# đọc ability từ log battle, trả về ability đã chuẩn hóa nếu tìm thấy, hoặc chuỗi rỗng nếu không tìm thấy. Cũng trả về raw log để debug nếu cần
def read_ability(image, config):
    roi_image = crop_roi(image, config["roi"]["battle_log"])
    text = ocr_text(roi_image, config, psm=6)
    normalized = normalize_text(text)
    match = re.search(r"ability\s+is\s+now\s+([a-z0-9 '\\-]+)", normalized)
    if not match:
        save_debug(config, roi_image, "missing_ability_log")
        return "", text
    ability = match.group(1).split("!")[0].strip()
    ability = re.sub(r"\s+", " ", ability)
    return ability, text

# đọc ability với retry nếu không đọc được ở lần đầu, trả về ability đã chuẩn hóa và raw log. Nếu sau retry vẫn không đọc được, trả về kết quả cuối cùng (có thể là rỗng) để debug
def read_ability_with_retry(config):
    retry_count = config["timing"].get("ability_retry_count", 2)
    retry_seconds = config["timing"].get("ability_retry_seconds", 1.5)
    last_ability = ""
    last_log = ""
    for attempt in range(retry_count + 1):
        image = screenshot_bgr()
        ability, raw_log = read_ability(image, config)
        last_ability = ability
        last_log = raw_log
        if ability:
            return ability, raw_log
        if attempt < retry_count:
            print(f"Chua doc duoc ability, doi them {retry_seconds:.1f}s...")
            time.sleep(retry_seconds)
    return last_ability, last_log


def fuzzy_fix_name(name: str):
    """Wrapper using extended Pokemon names from targets + team JSON."""
    known = get_known_pokemon_names(
        targets_path=TARGETS_PATH if TARGETS_PATH.exists() else None,
        team_path=TEAM_PATH if TEAM_PATH.exists() else None,
    )
    return _fuzzy_fix_name(name, known_names=known)


def build_targets(targets):
    result = {}
    for item in targets:
        name = normalize_text(item.get("pokemonname", ""))
        ability = normalize_text(item.get("ability", "none"))
        if name:
            result[name] = ability
    return result


def match_target(enemy_name, targets):
    if not enemy_name:
        return None, None
    for target_name, ability in targets.items():
        if enemy_name == target_name or target_name in enemy_name or enemy_name in target_name:
            return target_name, ability
    return None, None

# tìm template trên ảnh, trả về tọa độ trung tâm của template nếu tìm thấy với score cao hơn threshold, hoặc None nếu không tìm thấy
def locate_template(image, template_path, threshold, roi=None):
    search_image = image
    offset_x = 0
    offset_y = 0
    if roi:
        offset_x, offset_y, w, h = roi
        search_image = crop_roi(image, roi)

    template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if template is None:
        raise FileNotFoundError(template_path)
    # Guard: if template larger than search area, scale template down to fit
    th, tw = template.shape[:2]
    sh, sw = search_image.shape[:2]
    if th > sh or tw > sw:
        scale = min(sh / th, sw / tw)
        if scale <= 0:
            return None, 0.0
        template = cv2.resize(template, (max(1, int(tw * scale)), max(1, int(th * scale))), interpolation=cv2.INTER_AREA)

    result = cv2.matchTemplate(search_image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < threshold:
        return None, max_val
    h, w = template.shape[:2]
    return (offset_x + max_loc[0] + w // 2, offset_y + max_loc[1] + h // 2), max_val


def send_mouse_input(flags):
    extra = wintypes.ULONG(0)
    mouse_input = MOUSEINPUT(0, 0, 0, flags, 0, ctypes.pointer(extra))
    input_data = INPUT(0, INPUT_UNION(mi=mouse_input))
    return user32.SendInput(1, ctypes.byref(input_data), ctypes.sizeof(input_data))


def click_at(x, y, config):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    winsound.MessageBeep(winsound.MB_OK)
    send_mouse_input(MOUSEEVENTF_LEFTDOWN)
    time.sleep(config.get("mouse", {}).get("mouse_down_seconds", 0.12))
    send_mouse_input(MOUSEEVENTF_LEFTUP)


def move_mouse_away(config):
    point = config.get("mouse", {}).get("away_point", [100, 100])
    user32.SetCursorPos(int(point[0]), int(point[1]))
    time.sleep(0.12)


def click_run(config):
    hwnd = find_window(config["window_title"])
    if hwnd:
        focus_window(hwnd)
    move_mouse_away(config)
    image = screenshot_bgr()
    threshold = config["template_matching"]["run_button_threshold"]
    point, score = locate_template(
        image,
        RUN_TEMPLATE_PATH,
        threshold,
        roi=config["roi"].get("right_action_bar"),
    )
    if point is None:
        save_debug(config, image, f"run_not_found_{score:.2f}")
        print(f"Khong tim thay nut Run. Score cao nhat: {score:.2f}")
        return False
    offset = config.get("click_offsets", {}).get("run_button", [0, 0])
    point = (point[0] + offset[0], point[1] + offset[1])
    repeat = config.get("mouse", {}).get("click_repeat", 2)
    gap = config.get("mouse", {}).get("click_gap_seconds", 0.25)
    for index in range(repeat):
        click_at(*point, config=config)
        if index < repeat - 1:
            time.sleep(gap)
    move_mouse_away(config)
    print(f"Da click Run tai {point}, score {score:.2f}, repeat {repeat}")
    return True


def wait_until_battle_exits(config):
    deadline = time.time() + config["timing"].get("run_exit_timeout_seconds", 8.0)
    while time.time() < deadline:
        time.sleep(0.5)
        image = screenshot_bgr()
        try:
            if not is_battle(image, config):
                return True
        except Exception:
            return True
    return False


def key_down(vk):
    user32.keybd_event(vk, 0, 0, 0)


def key_up(vk):
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def release_move_keys():
    key_up(VK_A)
    key_up(VK_D)


def move_until_next_scan(config):
    end_at = time.time() + config["timing"]["scan_interval_seconds"]
    keys = [VK_A, VK_D]
    index = 0
    try:
        while time.time() < end_at:
            if keyboard.is_pressed("q"):
                return False
            vk = keys[index % 2]
            other = keys[(index + 1) % 2]
            key_up(other)
            key_down(vk)
            hold = random.uniform(
                config["timing"]["move_hold_min_seconds"],
                config["timing"]["move_hold_max_seconds"],
            )
            time.sleep(min(hold, max(0, end_at - time.time())))
            index += 1
    finally:
        release_move_keys()
    return True

def _resolve_found_sound_path(config) -> Optional[Path]:
    """Tìm file âm thanh báo tìm thấy Pokemon (ưu tiên config, rồi fallback)."""
    candidates = []
    configured = config.get("audio", {}).get("found_sound", "").strip()
    if configured:
        candidates.append(ROOT / configured)
    candidates.extend([
        ROOT / "src" / "data" / "audio" / "quick-ting.mp3",
        ROOT / "src" / "template" / "audio" / "quick-ting.mp3",
    ])
    seen = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            return path.resolve()
    return None


def play_found_sound(config):
    """Phát quick-ting.mp3 khi bắt đúng Pokemon (Mode 1 / Scan Pokemon)."""
    sound_path = _resolve_found_sound_path(config)
    if sound_path:
        try:
            file_url = sound_path.as_uri()
            command = (
                "$p=New-Object -ComObject WMPlayer.OCX; "
                f'$p.URL="{file_url}"; '
                "$p.controls.play(); Start-Sleep -Milliseconds 1200"
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"🔔 Phat am thanh: {sound_path.name}")
            return
        except Exception:
            pass
    winsound.MessageBeep(winsound.MB_ICONASTERISK)


def stop_found(config, pokemon, ability):
    play_found_sound(config)
    print("")
    print("FOUND:", pokemon, "-", ability if ability != "none" else "any ability")
    print("Tool da dung. Ban tu bat Pokemon trong game.")
    print("Nghe tieng 'ting' = da tim dung con can bat.")


def run_manual_mode(config, targets):
    hwnd = find_window(config["window_title"])
    if not hwnd:
        print(f"Khong tim thay cua so game: {config['window_title']}")
        return

    focus_window(hwnd)
    target_map = build_targets(targets)
    print("Dang chay mode 1. Bam Q de dung.")

    while True:
        if keyboard.is_pressed("q"):
            release_move_keys()
            print("Da dung tool bang phim Q.")
            return

        image = screenshot_bgr()
        try:
            battle = is_battle(image, config)
        except Exception as exc:
            save_debug(config, image, "battle_check_error")
            print("Loi OCR header:", exc)
            return

        if not battle:
            print("Chua vao battle, dang di chuyen A/D...")
            if not move_until_next_scan(config):
                print("Da dung tool bang phim Q.")
                return
            continue

        print("Da vao battle. Doi log ability neu can...")
        time.sleep(config["timing"]["ability_wait_seconds"])
        image = screenshot_bgr()
        enemy_name = read_enemy_name(image, config)
        target_name, wanted_ability = match_target(enemy_name, target_map)
        print(f"Pokemon doc duoc: '{enemy_name or 'unknown'}'")

        if not target_name:
            print("Khong nam trong JSON, Run.")
            if click_run(config):
                if not wait_until_battle_exits(config):
                    print("Da click Run nhung van thay battle. Tam dung de tranh click sai.")
                    return
                time.sleep(config["timing"]["after_run_wait_seconds"])
            continue

        if wanted_ability == "none":
            stop_found(config, target_name, wanted_ability)
            return

        actual_ability, raw_log = read_ability_with_retry(config)
        print(f"Ability can: '{wanted_ability}', log doc duoc: '{actual_ability or 'unknown'}'")
        if actual_ability and normalize_text(actual_ability) == wanted_ability:
            stop_found(config, target_name, actual_ability)
            return

        print("Ability khong dung hoac chua doc duoc, Run.")
        if click_run(config):
            if not wait_until_battle_exits(config):
                print("Da click Run nhung van thay battle. Tam dung de tranh click sai.")
                return
            time.sleep(config["timing"]["after_run_wait_seconds"])


def print_menu():
    print("")
    print("PokemonPRO Tool")
    print("0. Clear debug screenshots")
    print("1. Tim Pokemon, gap dung thi dung de tu bat")
    print("2. Tu bat Pokemon (chua code)")
    print("3. Auto Farm tien (danh quai tu dong)")
    print("4. Tools (Calibrate ROI + Team Builder)")
    print("Q. Thoat")


def run_tabbed_tools():
    """Run tabbed UI with Calibrate ROI + Team Builder."""
    try:
        from src.tools.ui_main import main as run_ui
        run_ui()
    except Exception as e:
        print(f"Error launching tools UI: {e}")


def _make_win_api_module(config):
    """Tạo dict các hàm Win32 API để truyền cho farm_battle module."""
    def _set_cursor(x, y):
        user32.SetCursorPos(int(x), int(y))

    def _click(x, y, cfg):
        click_at(x, y, config=cfg)

    return {
        "set_cursor": _set_cursor,
        "click": _click,
    }


def run_farm_mode_wrapper(config):
    """Wrapper để chạy farm mode từ menu chính."""
    if not ensure_runtime(config):
        return

    from src.farm.farm_battle import run_farm_mode
    # Use original config for detection (same logic as menu 1).
    win_api = _make_win_api_module(config)

    run_farm_mode(
        config=config,
        win_api_module=win_api,
        screenshot_fn=screenshot_bgr,
        is_battle_fn=is_battle,
        read_enemy_name_fn=read_enemy_name,
        move_until_next_scan_fn=move_until_next_scan,
        wait_until_battle_exits_fn=wait_until_battle_exits,
        focus_window_fn=focus_window,
        find_window_fn=find_window,
        move_mouse_away_fn=move_mouse_away,
        save_debug_fn=save_debug,
    )



def main():
    config = load_json(CONFIG_PATH)
    targets = load_json(TARGETS_PATH)

    while True:
        print_menu()
        choice = input("Chon: ").strip().lower()
        if choice == "0":
            clear_debug(config)
        elif choice == "1":
            if ensure_runtime(config):
                run_manual_mode(config, targets)
        elif choice == "2":
            print("Mode 2 se code sau.")
        elif choice == "3":
            run_farm_mode_wrapper(config)
        elif choice == "4":
            run_tabbed_tools()
        elif choice == "q":
            print("Thoat.")
            return
        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        release_move_keys()
        print("\nDa dung bang Ctrl+C.")
    except Exception as exc:
        release_move_keys()
        print(f"\nLoi: {exc}")
        sys.exit(1)
