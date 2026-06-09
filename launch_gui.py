#!/usr/bin/env python3
"""
Launch Modern UI - PokemonPRO Auto Tool GUI
Khởi động giao diện CustomTkinter thay vì CMD menu
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.tools.modern_ui import main

if __name__ == "__main__":
    main()
