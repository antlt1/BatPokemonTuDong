"""Test OCR pokemon name from battle."""

import cv2
import pyautogui
from pathlib import Path
from src.farm.farm_battle import ocr_pokemon_name_in_battle, load_json

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"

config = load_json(CONFIG_PATH)

# Screenshot
print("Capturing screenshot...")
screenshot = pyautogui.screenshot()
image = cv2.cvtColor(cv2.numpy.array(screenshot), cv2.COLOR_RGB2BGR)

# OCR pokemon name
pokemon_name = ocr_pokemon_name_in_battle(image, config)
print(f"OCR Pokemon Name: '{pokemon_name}'")

# Show ROI
roi = config.get("roi", {}).get("pokemon_name_in_battle")
if roi:
    x, y, w, h = roi
    cell = image[y:y+h, x:x+w]
    cv2.imshow("Pokemon Name ROI", cell)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
