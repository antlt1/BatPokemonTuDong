"""
Standalone tool: Calibrate Move Slots ROI bằng drag & drop.
Chạy: python src/tools/calibrate_move_slots.py
"""

import sys
import json
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.team_builder.team_builder_ui import CalibrateMoveROIApp, load_config

CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"

def main():
    config = load_config()

    window = tk.Tk()
    window.title("Calibrate Move Slots ROI")
    window.geometry("1200x700")

    app = CalibrateMoveROIApp(window, config)
    app.pack(fill="both", expand=True)

    window.mainloop()

if __name__ == "__main__":
    main()
