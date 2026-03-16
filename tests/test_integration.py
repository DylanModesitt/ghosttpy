"""Integration tests for ghosttpy — requires a running Ghostty instance."""

from __future__ import annotations

import subprocess
import time

import pytest

pytestmark = pytest.mark.integration

from ghosttpy import (
    Bounds,
    Ghostty,
    Screen,
    ScreenRegion,
    Surface,
    Tab,
    Terminal,
    Window,
)


@pytest.fixture(scope="session")
def g() -> Ghostty:
    app = Ghostty()
    if not app.is_running:
        subprocess.run(["open", "-a", "Ghostty"])
        for _ in range(50):
            time.sleep(0.1)
            if app.is_running:
                break
        else:
            pytest.skip("Could not start Ghostty")
    return app


def test_app_properties(g: Ghostty) -> None:
    assert g.name == "Ghostty"
    assert g.version
    assert isinstance(g.frontmost, bool)


def test_front_window(g: Ghostty) -> None:
    w = g.new_window()
    try:
        fw = g.front_window
        assert isinstance(fw, Window)
        assert fw.id
    finally:
        w.close()


def test_window_lifecycle(g: Ghostty) -> None:
    w = g.new_window(working_directory="/tmp")
    try:
        assert isinstance(w, Window)
        assert w in g.windows
        assert w.name is not None

        tab = w.new_tab()
        assert isinstance(tab, Tab)
        assert tab in w.tabs
        tab.close()
    finally:
        w.close()
    assert w not in g.windows


def test_terminal_split_and_input(g: Ghostty) -> None:
    w = g.new_window()
    try:
        term = w.selected_tab.focused_terminal
        assert isinstance(term, Terminal)

        bottom = term.split("down")
        assert isinstance(bottom, Terminal)
        assert bottom.id != term.id

        bottom.input("echo test\n")
        bottom.send_key("c", modifiers="control")
        bottom.close()
    finally:
        w.close()


def test_tab_navigation(g: Ghostty) -> None:
    w = g.new_window()
    try:
        t1 = w.selected_tab
        t2 = w.new_tab()
        assert t2.selected

        t1.select()
        assert t1.selected
    finally:
        w.close()


def test_surface_config_reuse(g: Ghostty) -> None:
    cfg = Surface(font_size=16.0, working_directory="/tmp")
    w1 = g.new_window(config=cfg)
    w2 = g.new_window(config=cfg)
    try:
        assert w1.id != w2.id
    finally:
        w1.close()
        w2.close()


def test_terminal_working_directory(g: Ghostty) -> None:
    w = g.new_window()
    try:
        term = w.selected_tab.focused_terminal
        # Shell may need a moment to report cwd
        for _ in range(20):
            if term.working_directory:
                break
            time.sleep(0.1)
        assert term.working_directory
    finally:
        w.close()


def test_window_terminals_flat(g: Ghostty) -> None:
    w = g.new_window()
    try:
        term = w.selected_tab.focused_terminal
        term.split("down")
        terms = w.terminals
        assert len(terms) >= 2
    finally:
        w.close()


def test_perform_action(g: Ghostty) -> None:
    w = g.new_window()
    try:
        term = w.selected_tab.focused_terminal
        result = term.perform("reset")
        assert isinstance(result, bool)
    finally:
        w.close()


def test_window_bounds_roundtrip(g: Ghostty) -> None:
    w = g.new_window()
    try:
        target = Bounds(100, 100, 900, 700)
        w.bounds = target
        time.sleep(0.2)
        got = w.bounds
        assert got == target
    finally:
        w.close()


def test_window_move_and_resize(g: Ghostty) -> None:
    w = g.new_window()
    try:
        w.move_to(200, 150)
        time.sleep(0.1)
        assert w.position.x == 200
        assert w.position.y == 150

        w.resize_to(800, 600)
        time.sleep(0.1)
        assert w.size.width == 800
        assert w.size.height == 600
    finally:
        w.close()


def test_main_screen(g: Ghostty) -> None:
    scr = g.main_screen()
    assert isinstance(scr, Screen)
    assert scr.size.width > 0
    assert scr.size.height > 0


def test_window_tile_left_right(g: Ghostty) -> None:
    w1 = g.new_window()
    w2 = g.new_window()
    try:
        scr = g.main_screen()
        w1.tile(ScreenRegion.left_half, screen=scr)
        w2.tile(ScreenRegion.right_half, screen=scr)
        time.sleep(0.2)
        b1 = w1.bounds
        b2 = w2.bounds
        # Left window's right edge should meet right window's left edge
        assert b1.right == b2.left
    finally:
        w1.close()
        w2.close()


def test_window_maximize(g: Ghostty) -> None:
    w = g.new_window()
    try:
        scr = g.main_screen()
        w.maximize(screen=scr)
        time.sleep(0.2)
        assert w.bounds == scr.bounds
    finally:
        w.close()
