#!/usr/bin/env python3
"""Print a tree of all Ghostty windows, tabs, and terminals."""

from __future__ import annotations

import argparse
import json
import sys

from ghosttpy import Ghostty


def collect(g: Ghostty, *, screens: bool = False) -> dict:
    """Gather the full Ghostty state as a dict."""
    data: dict = {
        "version": g.version,
        "frontmost": g.frontmost,
        "windows": [],
    }
    for w in g.windows:
        b = w.bounds
        win = {
            "id": w.id,
            "name": w.name,
            "bounds": {
                "left": b.left,
                "top": b.top,
                "right": b.right,
                "bottom": b.bottom,
            },
            "tabs": [],
        }
        for tab in w.tabs:
            t = {
                "id": tab.id,
                "index": tab.index,
                "selected": tab.selected,
                "terminals": [],
            }
            focused = tab.focused_terminal
            for term in tab.terminals:
                t["terminals"].append(
                    {
                        "id": term.id,
                        "name": term.name,
                        "working_directory": term.working_directory,
                        "focused": term == focused,
                    }
                )
            win["tabs"].append(t)
        data["windows"].append(win)

    if screens:
        data["screens"] = []
        for scr in g.screens():
            data["screens"].append(
                {
                    "origin": {"x": scr.origin.x, "y": scr.origin.y},
                    "size": {"width": scr.size.width, "height": scr.size.height},
                }
            )
    return data


def print_tree(data: dict) -> None:
    """Print the Ghostty state as a human-readable tree."""
    print(f"Ghostty {data['version']}  (frontmost: {data['frontmost']})")

    for scr in data.get("screens", []):
        o, s = scr["origin"], scr["size"]
        print(f"  Screen: ({o['x']}, {o['y']}) {s['width']}x{s['height']}")

    windows = data["windows"]
    print(f"\n{len(windows)} window(s):\n")

    for w in windows:
        b = w["bounds"]
        width = b["right"] - b["left"]
        height = b["bottom"] - b["top"]
        print(f"Window {w['id']}")
        print(f"  name: {w['name']}")
        print(f"  bounds: ({b['left']}, {b['top']}) {width}x{height}")
        for tab in w["tabs"]:
            sel = " *" if tab["selected"] else ""
            print(f"  Tab {tab['index']}{sel}")
            for term in tab["terminals"]:
                foc = " (focused)" if term["focused"] else ""
                print(f"    Terminal {term['id']}{foc}")
                print(f"      cwd: {term['working_directory']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="output as JSON")
    parser.add_argument(
        "--screens", action="store_true", help="include screen geometry"
    )
    args = parser.parse_args()

    g = Ghostty()
    if not g.is_running:
        sys.exit("Ghostty is not running.")

    data = collect(g, screens=args.screens)

    if args.json:
        json.dump(data, sys.stdout, indent=2)
        print()
    else:
        print_tree(data)


if __name__ == "__main__":
    main()
