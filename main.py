#!/usr/bin/env python3
"""
Run the full local data refresh pipeline:
1) robinhood_accessor.py
2) data_merger.py
3) db_updater.py (DB updater)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def run_step(script_name: str) -> None:
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Missing script: {script_path}")

    print(f"\n=== Running {script_name} ===")
    # Inherit stdin/stdout so robinhood login prompts work interactively.
    completed = subprocess.run([sys.executable, str(script_path)], check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{script_name} failed with exit code {completed.returncode}")


def main() -> None:
    run_step("robinhood_accessor.py")
    run_step("data_merger.py")
    run_step("db_updater.py")
    print("\nPipeline complete: robinhood -> merge -> sqlite DB update")


if __name__ == "__main__":
    main()
