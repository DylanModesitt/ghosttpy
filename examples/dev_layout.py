#!/usr/bin/env python3
"""Create a development workspace with an editor, runner, and shell pane."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ghosttpy import Ghostty


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="project directory (default: current directory)",
    )
    parser.add_argument(
        "--editor",
        default=os.environ.get("EDITOR", "vim"),
        help="editor command (default: $EDITOR or vim)",
    )
    parser.add_argument("--maximize", action="store_true", help="maximize the window")
    args = parser.parse_args()

    project_dir = str(Path(args.directory).resolve())

    g = Ghostty()
    if not g.is_running:
        sys.exit("Ghostty is not running.")

    w = g.new_window(working_directory=project_dir)
    editor = w.selected_tab.focused_terminal

    # Right pane: test runner (top) and shell (bottom)
    runner = editor.split("right", working_directory=project_dir)
    shell = runner.split("down", working_directory=project_dir)

    runner.input("# test runner")
    runner.send_key("enter")
    shell.input("git status")
    shell.send_key("enter")
    editor.input(f"{args.editor} .")
    editor.send_key("enter")

    editor.perform("equalize_splits")

    if args.maximize:
        w.maximize()

    editor.focus()
    print(f"Dev workspace created in {project_dir}")


if __name__ == "__main__":
    main()
