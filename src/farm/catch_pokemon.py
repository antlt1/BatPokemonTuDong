import json
import re
import time
import cv2
import numpy as np
import keyboard

from pathlib import Path
from threading import Event
from src.ocr_utils import ocr_text_variants, crop_roi, normalize_text

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
TEAM_PARTY_PATH = ROOT / "src" / "config" / "team_party.json"
TEAM_FARM_PATH = ROOT / "src" / "config" / "team_farm.json"
TARGETS_PATH = ROOT / "src" / "config" / "target_pokemon.json"


def catch_pokemon_mode(config, add_log, stop_event: Event):
    add_log("✅ Initializing Catch Pokemon mode...")

    from run_pokemon_tool import (
        screenshot_bgr, is_battle, read_enemy_name,
        focus_window, find_window, move_mouse_away,
        ensure_runtime, _make_win_api_module,
        move_until_next_scan, save_debug,
        click_run, wait_until_battle_exits,
        release_move_keys,
        read_ability_with_retry,
    )

    def focus_and_run(cfg):
        """Focus window rồi click Run, retry 1 lần nếu không tìm thấy nút."""
        hwnd = find_window(cfg.get("window_title", "PROClient"))
        if hwnd:
            focus_window(hwnd)
        move_mouse_away(cfg)
        time.sleep(0.15)
        success = click_run(cfg)
        if not success:
            add_log("⚠️ Không tìm thấy nút Run, thử lại sau 0.8s...")
            time.sleep(0.8)
            hwnd2 = find_window(cfg.get("window_title", "PROClient"))
            if hwnd2:
                focus_window(hwnd2)
            move_mouse_away(cfg)
            time.sleep(0.15)
            success = click_run(cfg)
        return success

    if not ensure_runtime(config):
        add_log("❌ Missing dependencies.")
        return

    win_api = _make_win_api_module(config)
    focus_window(find_window(config.get("window_title", "PROClient")))

    catch_cfg = config.get("catch", {})
    breloom_name = catch_cfg.get("breloom_name", "Breloom")
    breloom_slot_raw = catch_cfg.get("breloom_slot", "Auto (tự tìm)")
    breloom_slot = None if "Auto" in breloom_slot_raw else int(breloom_slot_raw.replace("Slot ", ""))
    ball_prio_raw = catch_cfg.get("ball_priority", "Poke → Great → Ultra")
    ball_order = [b.strip() for b in ball_prio_raw.split("→")]
    max_balls = catch_cfg.get("max_balls", 999)

    add_log(f"🎯 Bắt Pokemon với {breloom_name}")
    add_log(f"🔴 Ball order: {ball_order}")

    team = _load_team()
    if team:
        breloom_found = _find_breloom(team, breloom_name)
        if breloom_found:
            if "Auto" in breloom_slot_raw:
                breloom_slot = breloom_found
            add_log(f"🍄 Found {breloom_name} at slot {breloom_found}")
        else:
            add_log(f"⚠️ {breloom_name} không có trong team!")
            add_log("⚠️ Cần có Breloom với False Swipe + Spore")

    balls_used = 0
    while not stop_event.is_set():
        try:
            img = screenshot_bgr()
            if not is_battle(img, config):
                move_until_next_scan(config)
                continue

            add_log("⚔️ Battle detected!")
            # Di chuột ra xa ngay khi phát hiện battle để tránh hover làm đổi màu nút
            hwnd = find_window(config.get("window_title", "PROClient"))
            if hwnd:
                focus_window(hwnd)
            move_mouse_away(config)

            # Check Shiny/Pink popup
            if _check_and_accept_shiny(config, win_api, add_log):
                add_log("✅ Đã accept Shiny/Pink!")

            time.sleep(config.get("timing", {}).get("ability_wait_seconds", 3.5))
            img = screenshot_bgr()
            enemy = read_enemy_name(img, config)

            if not enemy:
                add_log("⚠️ Không đọc được tên Pokemon")
                save_debug(config, img, "debug_catch_no_name")
                focus_and_run(config)
                wait_until_battle_exits(config)
                continue

            add_log(f"🎯 Enemy: {enemy}")

            allowed_abilities = _get_target_abilities(enemy)
            if allowed_abilities is not None:
                if "none" in allowed_abilities:
                    add_log(f"✨ Gặp target: {enemy} (không yêu cầu ability)")
                    _execute_catch_sequence(config, add_log, stop_event, win_api, breloom_slot, breloom_name, ball_order)
                    wait_until_battle_exits(config)
                else:
                    add_log(f"🔍 Đang check ability cho {enemy} (Yêu cầu: {', '.join(allowed_abilities)})...")
                    actual_ability, raw_log = read_ability_with_retry(config)
                    add_log(f"📋 Log đọc được: '{actual_ability or 'unknown'}'")
                    
                    actual_norm = normalize_text(actual_ability) if actual_ability else ""
                    if actual_norm in allowed_abilities:
                        add_log(f"🎉 Khớp ability '{actual_ability}'! Bắt đầu bắt...")
                        _execute_catch_sequence(config, add_log, stop_event, win_api, breloom_slot, breloom_name, ball_order)
                        wait_until_battle_exits(config)
                    else:
                        add_log(f"⏭ Ability '{actual_ability or 'unknown'}' không khớp. Bỏ qua {enemy}.")
                        focus_and_run(config)
                        wait_until_battle_exits(config)
            else:
                add_log(f"⏭ Bỏ qua {enemy}, không phải target")
                focus_and_run(config)
                wait_until_battle_exits(config)

        except Exception as e:
            add_log(f"❌ Catch error: {e}")
            time.sleep(2)


def _load_team():
    for path in [TEAM_FARM_PATH, TEAM_PARTY_PATH]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) >= 1:
                return data
        except:
            continue
    return []


def _find_breloom(team, name):
    for i, slot in enumerate(team):
        if isinstance(slot, dict) and name.lower() in slot.get("name", "").lower():
            return i + 1
    return None


def _check_and_accept_shiny(config, win_api, add_log=None):
    try:
        from run_pokemon_tool import screenshot_bgr
        roi = config.get("roi", {}).get("shiny_popup_area", [400, 250, 1120, 400])
        img = screenshot_bgr()
        if img is None:
            return False
        h_img, w_img = img.shape[:2]
        x, y, w, h = [int(v) for v in roi]
        if x + w > w_img or y + h > h_img:
            return False
        region = img[y:y+h, x:x+w]

        import pytesseract
        data = pytesseract.image_to_data(region, output_type=pytesseract.Output.DICT)
        for i, text in enumerate(data['text']):
            if text and text.strip().lower() == 'ok':
                ok_x = data['left'][i] + data['width'][i] // 2
                ok_y = data['top'][i] + data['height'][i] // 2
                cx = x + ok_x
                cy = y + ok_y
                if add_log:
                    add_log(f"✨ Click OK tai ({cx}, {cy})")
                win_api["set_cursor"](cx, cy)
                time.sleep(0.05)
                win_api["click"](cx, cy, config)
                time.sleep(2.0)
                return True
    except:
        pass
    return False


def _get_target_abilities(enemy_name):
    if not enemy_name:
        return None
    try:
        with open(TARGETS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not data:
            return None
        targets = data if isinstance(data, list) else [data]
        allowed_abilities = []
        found_pokemon = False
        
        enemy_norm = normalize_text(enemy_name)
        for entry in targets:
            if not isinstance(entry, dict):
                continue
            name = entry.get("pokemonname") or entry.get("name", "")
            if not name:
                continue
            name_norm = normalize_text(name)
            if enemy_norm == name_norm or name_norm in enemy_norm or enemy_norm in name_norm:
                found_pokemon = True
                ability = entry.get("ability") or "none"
                allowed_abilities.append(normalize_text(ability))
        if not found_pokemon:
            return None
        return allowed_abilities
    except Exception as e:
        print(f"Error loading target abilities: {e}")
        return None


def _get_active_pokemon_name(config):
    try:
        from run_pokemon_tool import screenshot_bgr
        roi = config.get("roi", {}).get("pokemon_name_in_battle")
        if not roi:
            return ""
        img = screenshot_bgr()
        h, w = img.shape[:2]
        x, y, rw, rh = [int(v) for v in roi]
        if x + rw > w or y + rh > h:
            return ""
        cell = img[y:y+rh, x:x+rw]
        text = ocr_text_variants(cell, config, psm=7)
        cleaned = re.sub(r"[^a-z\s]", "", text.strip().lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:15]
    except:
        return ""


def _wait_until_turn_ready(config, timeout=12.0, add_log=None):
    from run_pokemon_tool import screenshot_bgr, locate_template
    template_path = ROOT / "src" / "template" / "cap_gamedefault" / "rightBarButtomFight.png"
    threshold = config.get("template_matching", {}).get("fight_button_threshold", 0.55)
    roi = config.get("roi", {}).get("right_action_bar", [1261, 257, 299, 603])
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        img = screenshot_bgr()
        if img is not None:
            point, score = locate_template(img, template_path, threshold, roi=roi)
            if point is not None:
                return True
        time.sleep(0.4)
    return False


def _execute_catch_sequence(config, add_log, stop_event, win_api, breloom_slot, breloom_name, ball_order):
    add_log("🔄 Bắt đầu chuỗi bắt...")

    from run_pokemon_tool import find_window, wait_until_battle_exits, focus_window

    hwnd = find_window(config.get("window_title", "PROClient"))
    if hwnd:
        focus_window(hwnd)

    # 1. Swap to Breloom nếu cần
    if breloom_slot:
        _wait_until_turn_ready(config, timeout=10.0, add_log=add_log)
        active = _get_active_pokemon_name(config)
        breloom_lower = breloom_name.lower()
        if breloom_lower in active or "breloom" in active:
            add_log(f"🍄 {breloom_name} đã trên sân, bỏ qua swap")
        else:
            _swap_to_slot(config, breloom_slot, win_api, add_log)
            # Chờ ra sân xong (nút Fight xuất hiện lại)
            _wait_until_turn_ready(config, timeout=12.0, add_log=add_log)

    # 2. Vòng lặp False Swipe trước cho đến khi HP thấp (màu đỏ hoặc cạn)
    for attempt in range(10):
        if stop_event.is_set():
            return
        _wait_until_turn_ready(config, timeout=10.0, add_log=add_log)
        hp_low = _check_enemy_hp_low(config)
        if hp_low:
            if attempt == 0:
                add_log("✅ HP đã thấp, không cần False Swipe")
            else:
                add_log(f"✅ HP thấp sau {attempt} lần False Swipe")
            break
        _use_false_swipe(config, win_api, add_log)
    else:
        add_log("⚠️ Hết 10 lượt False Swipe mà HP chưa thấp!")
        return

    # 3. Dùng Spore (Ru ngủ) sau khi HP đã thấp
    _wait_until_turn_ready(config, timeout=10.0, add_log=add_log)
    _use_spore(config, win_api, add_log)
    
    # 4. Đợi lượt mới sau Spore để ném Ball
    add_log("⏳ Đang đợi lượt mới để ném Ball...")
    _wait_until_turn_ready(config, timeout=12.0, add_log=add_log)
    _throw_ball(config, ball_order, win_api, add_log)
    
    wait_until_battle_exits(config)


def _click_roi_center(config, roi_key, slot_idx, win_api, add_log=None):
    roi_raw = config.get("roi", {}).get(roi_key)
    if not roi_raw:
        if add_log:
            add_log(f"⚠️ ROI {roi_key} not found in config")
        return False
    if isinstance(roi_raw[0], (list, tuple)):
        roi_list = roi_raw
        if slot_idx >= len(roi_list):
            if add_log:
                add_log(f"⚠️ Slot {slot_idx} out of range for {roi_key}")
            return False
        x, y, w, h = roi_list[slot_idx]
    else:
        x, y, w, h = roi_raw
    cx, cy = x + w//2, y + h//2

    # Focus window
    from run_pokemon_tool import find_window, focus_window
    hwnd = find_window(config.get("window_title", "PROClient"))
    if hwnd:
        focus_window(hwnd)

    repeat = config.get("mouse", {}).get("click_repeat", 2)
    gap = config.get("mouse", {}).get("click_gap_seconds", 0.25)

    win_api["set_cursor"](int(cx), int(cy))
    time.sleep(0.05)
    for idx in range(repeat):
        win_api["click"](cx, cy, config)
        if idx < repeat - 1:
            time.sleep(gap)
    return True


def _swap_to_slot(config, slot, win_api, add_log=None):
    if add_log:
        add_log(f"🔄 Swapping to slot {slot}...")
    _click_roi_center(config, "pokemon_button_roi", 0, win_api, add_log)
    time.sleep(0.8)
    _click_roi_center(config, "pokemon_swap_slots", slot - 1, win_api, add_log)
    time.sleep(1.5)


def _use_spore(config, win_api, add_log=None):
    if add_log:
        add_log("💤 Dùng Spore...")
    _click_roi_center(config, "fight_button_roi", 0, win_api, add_log)
    time.sleep(0.7)
    _click_roi_center(config, "move_slots", 1, win_api, add_log)
    time.sleep(config.get("timing", {}).get("ability_wait_seconds", 3.5))


def _use_false_swipe(config, win_api, add_log=None):
    if add_log:
        add_log("⚔️ Dùng False Swipe...")
    _click_roi_center(config, "fight_button_roi", 0, win_api, add_log)
    time.sleep(0.7)
    _click_roi_center(config, "move_slots", 0, win_api, add_log)
    time.sleep(config.get("timing", {}).get("ability_wait_seconds", 3.5))


def _check_enemy_hp_low(config):
    hp_roi = config.get("roi", {}).get("enemy_hp_bar", [520, 333, 247, 45])
    try:
        from run_pokemon_tool import screenshot_bgr
        img = screenshot_bgr()
        if img is None:
            return False
        h_img, w_img = img.shape[:2]
        x, y, rw, rh = [int(v) for v in hp_roi]
        if x + rw > w_img or y + rh > h_img:
            return False
        hp_region = img[y:y+rh, x:x+rw]
        
        # Convert to HSV to count green and yellow pixels
        hsv = cv2.cvtColor(hp_region, cv2.COLOR_BGR2HSV)
        
        # Green & Yellow Hue with high Saturation/Value to filter out green forest backgrounds
        lower_green_yellow = np.array([20, 180, 180])
        upper_green_yellow = np.array([85, 255, 255])
        
        mask = cv2.inRange(hsv, lower_green_yellow, upper_green_yellow)
        green_yellow_count = np.sum(mask > 0)
        total_pixels = rw * rh
        ratio = green_yellow_count / total_pixels
        
        # If green/yellow pixels are less than 3% of the ROI, HP is low (red or empty)
        return ratio < 0.03
    except:
        return False


def _find_ball_in_bag(config, ball_name, win_api, add_log=None):
    try:
        from run_pokemon_tool import screenshot_bgr
        bag_roi = config.get("roi", {}).get("items_bag_area", [1278, 290, 250, 360])
        x, y, w, h = [int(v) for v in bag_roi]
        img = screenshot_bgr()
        if img is None:
            return False
        h_img, w_img = img.shape[:2]
        if x + w > w_img or y + h > h_img:
            return False
        bag_region = img[y:y+h, x:x+w]
        bag_gray = cv2.cvtColor(bag_region, cv2.COLOR_BGR2GRAY)
        _, bag_thresh = cv2.threshold(bag_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        bag_big = cv2.resize(bag_thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        import pytesseract
        from PIL import Image
        lang = config.get("ocr", {}).get("language", "eng")
        raw_text = pytesseract.image_to_string(Image.fromarray(bag_big), lang=lang, config="--psm 6").strip()
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

        if add_log:
            add_log(f"📋 OCR Bag lines: {lines}")

        ball_key = ball_name.lower().replace(" ball", "").replace("ball", "")
        target_idx = -1
        for i, line in enumerate(lines):
            cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip().lower()
            if ball_key in cleaned:
                target_idx = i
                break

        if target_idx < 0:
            if add_log:
                add_log(f"⚠️ Không thấy {ball_name} trong bag (OCR)")
            return False

        # PROClient battle items bag is a vertical list of items (1 column).
        # We divide the height h by the number of detected lines.
        num_rows = len(lines)
        row_height = h / num_rows
        cx = x + w // 2
        cy = y + int(target_idx * row_height + row_height // 2)

        if add_log:
            add_log(f"🎯 Found {ball_name} at row {target_idx+1}/{num_rows}, clicking ({cx}, {cy})")

        win_api["set_cursor"](cx, cy)
        time.sleep(0.05)
        win_api["click"](cx, cy, config)
        return True
    except Exception as e:
        if add_log:
            add_log(f"⚠️ Lỗi OCR ball: {e}")
        return False


def _throw_ball(config, ball_order, win_api, add_log=None):
    if add_log:
        add_log(f"🔴 Ném {ball_order[0]}...")
    _click_roi_center(config, "items_button_roi", 0, win_api, add_log)
    time.sleep(1.0)
    if ball_order:
        found = _find_ball_in_bag(config, ball_order[0], win_api, add_log)
        if not found:
            ball_name = ball_order[0].lower()
            
            # Fallback to vertical list slots
            right_action_bar = config.get("roi", {}).get("right_action_bar", [1261, 257, 299, 603])
            rx, ry, rw, rh = right_action_bar
            bx = rx + rw // 2
            
            # Estimate slot centers: First slot center at ry + 73, slot height is ~70.
            ball_slot_map = {"poke": 0, "great": 1, "ultra": 2, "master": 3}
            idx = ball_slot_map.get(ball_name, 0)
            by = ry + 73 + idx * 70
            
            if add_log:
                add_log(f"⚠️ Fallback click {ball_name} at ({bx}, {by})")
            win_api["set_cursor"](bx, by)
            time.sleep(0.05)
            win_api["click"](bx, by, config)

        time.sleep(1.0)
        _click_roi_center(config, "enemy_hp_bar", 0, win_api, add_log)
        time.sleep(2.5)


def _run_away(config, win_api, add_log=None):
    if add_log:
        add_log("🏃 Chạy...")
    _click_roi_center(config, "run_button_roi", 0, win_api, add_log)
    time.sleep(config.get("timing", {}).get("after_run_wait_seconds", 4.0))
