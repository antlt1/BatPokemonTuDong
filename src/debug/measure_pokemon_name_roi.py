"""
Script để đo ROI tên Pokemon trong battle header.
Click 2 lần: điểm trên-trái -> điểm dưới-phải.
ROI sẽ được lưu vào tool_config.json.
"""

import cv2
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"

# State global
roi_points = []
current_image = None
window_name = "Measure Pokemon Name ROI - Click on 'Milolic' name (dưới trái) - Click top-left, then bottom-right"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def mouse_callback(event, x, y, flags, param):
    global roi_points, current_image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points.append((x, y))
        print(f"Point {len(roi_points)}: ({x}, {y})")

        if len(roi_points) == 1:
            print("Click điểm dưới-phải để kết thúc ROI")
        elif len(roi_points) == 2:
            # Tính toán ROI (x, y, w, h)
            x1, y1 = roi_points[0]
            x2, y2 = roi_points[1]
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)

            print(f"\n✓ ROI: ({x}, {y}, {w}, {h})")

            # Lưu vào config
            config = load_config()
            if "roi" not in config:
                config["roi"] = {}
            config["roi"]["pokemon_name_in_battle"] = [x, y, w, h]
            save_config(config)
            print(f"Đã lưu ROI vào tool_config.json!")
            print("Đóng window để thoát.")


def main():
    global current_image
    # Screenshot từ màn hình
    import pyautogui

    print("Capturing screenshot...")
    screenshot = pyautogui.screenshot()
    current_image = cv2.cvtColor(cv2.numpy.array(screenshot), cv2.COLOR_RGB2BGR)

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)

    print("Click điểm trên-trái của tên Pokemon (dưới trái battle area, bên cạnh HP)")
    print("Sau đó click điểm dưới-phải")

    while True:
        display = current_image.copy()
        if len(roi_points) >= 1:
            cv2.circle(display, roi_points[0], 5, (0, 255, 0), -1)
        if len(roi_points) >= 2:
            cv2.circle(display, roi_points[1], 5, (0, 255, 0), -1)
            cv2.rectangle(display, roi_points[0], roi_points[1], (0, 255, 0), 2)

        cv2.imshow(window_name, display)
        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
