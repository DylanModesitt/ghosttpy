#!/usr/bin/env python3
"""Broadcast typed input to multiple terminal panes simultaneously."""

from __future__ import annotations

import argparse
import sys

from ghosttpy import Ghostty


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-n", "--count", type=int, default=4, help="number of panes (default: 4)"
    )
    parser.add_argument("--command", help="initial command to send to all panes")
    parser.add_argument("--working-directory", help="starting directory for all panes")
    args = parser.parse_args()

    if args.count < 1:
        sys.exit("Count must be at least 1.")

    g = Ghostty()
    if not g.is_running:
        sys.exit("Ghostty is not running.")

    kwargs = {}
    if args.working_directory:
        kwargs["working_directory"] = args.working_directory

    w = g.new_window(**kwargs)
    first = w.selected_tab.focused_terminal
    terminals = [first]

    # Build a grid by alternating right/down splits.
    # First create columns, then split each column vertically.
    cols = round(args.count**0.5) or 1
    rows = (args.count + cols - 1) // cols

    # Create column roots by splitting rightward from the first terminal
    col_roots = [first]
    for _ in range(1, cols):
        col_roots.append(col_roots[0].split("right", **kwargs))
        terminals.append(col_roots[-1])

    # Split each column downward
    for col_root in col_roots:
        current = col_root
        for _ in range(1, rows):
            if len(terminals) >= args.count:
                break
            current = current.split("down", **kwargs)
            terminals.append(current)

    first.equalize_splits()

    if args.command:
        for t in terminals:
            t.input(args.command)
            t.send_key("enter")

    print(
        f"Broadcasting to {len(terminals)} pane(s). "
        "Type commands below (Ctrl-C to exit):"
    )
    try:
        while True:
            cmd = input("> ")
            for t in terminals:
                t.input(cmd)
                t.send_key("enter")
    except (KeyboardInterrupt, EOFError):
        print("\nDone.")


if __name__ == "__main__":
    main()
