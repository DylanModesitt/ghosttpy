#!/usr/bin/env python3
"""Tile all open Ghostty windows into equal-width columns."""

from __future__ import annotations

import argparse
import sys

from ghosttpy import Ghostty


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--columns",
        type=int,
        default=None,
        help="number of columns (default: one per window)",
    )
    parser.add_argument(
        "--gap", type=int, default=0, help="pixel gap between windows (default: 0)"
    )
    parser.add_argument(
        "--screen",
        type=int,
        default=None,
        help="screen index for multi-monitor setups (default: main screen)",
    )
    args = parser.parse_args()

    g = Ghostty()
    if not g.is_running:
        sys.exit("Ghostty is not running.")

    windows = g.windows
    if not windows:
        sys.exit("No open windows to tile.")

    screen = g.screens()[args.screen] if args.screen is not None else g.main_screen()
    columns = args.columns or len(windows)

    g.tile_windows(windows, columns=columns, gap=args.gap, screen=screen)
    print(f"Tiled {len(windows)} window(s) into {columns} column(s).")


if __name__ == "__main__":
    main()
