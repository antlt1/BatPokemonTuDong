"""
farm_gui_adapter.py - Bridge giữa farm_battle.py và GUI
Cung cấp interface để chạy farm_battle trong background thread với log callback
"""

import sys
import time
import threading
from pathlib import Path
from threading import Event

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# Import hàm chính từ farm_battle
from src.farm.farm_battle import (
    run_farm_mode,
    load_json,
    load_team,
    CONFIG_PATH,
    TEAM_FARM_PATH,
    feedback_log
)

# Import target builder từ run_pokemon_tool
from run_pokemon_tool import (
    screenshot_bgr,
    is_battle,
    read_enemy_name,
    move_until_next_scan,
    wait_until_battle_exits,
    focus_window,
    find_window,
    move_mouse_away,
    save_debug,
    _make_win_api_module,
    ensure_runtime,
    run_manual_mode,
    build_targets,
    TARGETS_PATH,
)


def run_farm_mode_with_gui_logging(config, mode, gui_log_callback, stop_event: Event):
    """
    Wrapper để chạy farm hoặc scan based on mode
    
    Args:
        config: Tool config dict
        mode: "Auto Farm" hoặc "Scan Pokemon"
        gui_log_callback: Callback(message) để gửi log vào GUI
        stop_event: threading.Event để dừng
    """
    try:
        if mode == "Scan Pokemon":
            _run_scan_pokemon_with_gui_logging(config, gui_log_callback, stop_event)
        elif mode == "Bắt Pokemon":
            _run_catch_pokemon_with_gui_logging(config, gui_log_callback, stop_event)
        else:  # Auto Farm (default)
            _run_auto_farm_with_gui_logging(config, gui_log_callback, stop_event)
    except Exception as e:
        gui_log_callback(f"❌ Error: {str(e)}")
        import traceback
        gui_log_callback(f"📍 Traceback:\n{traceback.format_exc()}")


def _run_auto_farm_with_gui_logging(config, gui_log_callback, stop_event: Event):
    """
    Wrapper để chạy auto farm với log redirect vào GUI
    
    Args:
        config: Tool config dict
        gui_log_callback: Callback(message) để gửi log vào GUI
        stop_event: threading.Event để dừng farm
    """
    try:
        gui_log_callback("✅ Initializing Auto Farm...")
        gui_log_callback(f"📁 Config: {CONFIG_PATH}")
        gui_log_callback(f"👥 Team: {TEAM_FARM_PATH}\n")
        
        # Kiểm tra dependencies
        if not ensure_runtime(config):
            gui_log_callback("❌ Missing dependencies. Install from requirements.txt")
            return
        
        if not TEAM_FARM_PATH.exists():
            gui_log_callback("⚠️ team_farm.json chưa có! Chạy Tab 5 Auto Farm Config trước.")
            return
        
        team = load_team()
        if not team:
            gui_log_callback("⚠️ Team farm trống! Chọn ít nhất 1 Pokemon ở Auto Farm Config.")
            return
        if len(team) < 6:
            gui_log_callback(f"⚠️ Team farm chỉ có {len(team)}/6. Vẫn chạy nhưng thiếu slot.")
        
        gui_log_callback(f"✅ Team loaded: {len(team)} Pokemon\n")
        
        # Create Win API module
        win_api = _make_win_api_module(config)
        
        # Wrapper functions để capture log
        original_feedback = None
        
        def feedback_log_capture(msg):
            """Override feedback_log để gửi vào GUI"""
            gui_log_callback(msg)
        
        # Monkey-patch feedback_log temporarily
        import src.farm.farm_battle as fb_module
        original_feedback = fb_module.feedback_log
        fb_module.feedback_log = feedback_log_capture
        
        try:
            gui_log_callback("🎮 Starting farm loop...\n")
            
            # Gọi run_farm_mode từ farm_battle với stop_event
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
                stop_event=stop_event,  # Pass stop_event để farm_battle có thể check
            )
            
            gui_log_callback("\n✅ Farm session ended")
            
        finally:
            # Restore original feedback_log
            if original_feedback:
                fb_module.feedback_log = original_feedback
        
    except Exception as e:
        gui_log_callback(f"❌ Error: {str(e)}")
        import traceback
        gui_log_callback(f"📍 Traceback:\n{traceback.format_exc()}")


def _run_scan_pokemon_with_gui_logging(config, gui_log_callback, stop_event: Event):
    """
    Wrapper để chạy scan pokemon (Mode 1) với stop_event support
    
    Args:
        config: Tool config dict
        gui_log_callback: Callback(message) để gửi log vào GUI
        stop_event: threading.Event để dừng scan
    """
    try:
        gui_log_callback("✅ Initializing Scan Pokemon Mode...")
        gui_log_callback(f"📁 Config: {CONFIG_PATH}")
        gui_log_callback(f"🎯 Targets: {TARGETS_PATH}\n")
        
        # Kiểm tra dependencies
        if not ensure_runtime(config):
            gui_log_callback("❌ Missing dependencies. Install from requirements.txt")
            return
        
        # Load targets
        if not TARGETS_PATH.exists():
            gui_log_callback("⚠️ Targets config not found!")
            return
        
        targets = load_json(TARGETS_PATH)
        gui_log_callback(f"✅ Targets loaded: {len(targets)} Pokemon\n")
        
        # Monkey-patch keyboard.is_pressed để check stop_event
        import keyboard as kb_module
        original_is_pressed = kb_module.is_pressed
        
        def patched_is_pressed(key):
            """Check stop_event khi key=='q', fallback to original"""
            if key == "q" and stop_event.is_set():
                return True
            return original_is_pressed(key)
        
        kb_module.is_pressed = patched_is_pressed
        
        try:
            gui_log_callback("🎮 Starting scan loop...\n")
            gui_log_callback("Dang chay mode 1 (Scan Pokemon)...\n")
            
            # Gọi run_manual_mode (Mode 1)
            run_manual_mode(config, targets)
            
            gui_log_callback("\n✅ Scan session ended")
            
        finally:
            # Restore original keyboard.is_pressed
            kb_module.is_pressed = original_is_pressed
        
    except Exception as e:
        gui_log_callback(f"❌ Error: {str(e)}")
        import traceback
        gui_log_callback(f"📍 Traceback:\n{traceback.format_exc()}")


def _run_catch_pokemon_with_gui_logging(config, gui_log_callback, stop_event: Event):
    try:
        gui_log_callback("✅ Initializing Catch Pokemon Mode...")

        if not ensure_runtime(config):
            gui_log_callback("❌ Missing dependencies.")
            return

        import keyboard as kb_module
        original_is_pressed = kb_module.is_pressed

        def patched_is_pressed(key):
            if key == "q" and stop_event.is_set():
                return True
            return original_is_pressed(key)

        kb_module.is_pressed = patched_is_pressed

        try:
            from src.farm.catch_pokemon import catch_pokemon_mode
            gui_log_callback("🎯 Starting catch mode...")
            catch_pokemon_mode(config, gui_log_callback, stop_event)
            gui_log_callback("\n✅ Catch session ended")
        finally:
            kb_module.is_pressed = original_is_pressed

    except Exception as e:
        gui_log_callback(f"❌ Catch error: {str(e)}")
        import traceback
        gui_log_callback(traceback.format_exc())


if __name__ == "__main__":
    # Test
    def test_callback(msg):
        print(msg)
    
    from threading import Event
    event = Event()
    config = load_json(CONFIG_PATH)
    run_farm_mode_with_gui_logging(config, "Auto Farm", test_callback, event)
