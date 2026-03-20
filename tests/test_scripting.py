"""Tests for AppleScript generation — verifies the scripts produced by each method."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ghosttpy import (
    Bounds,
    Ghostty,
    GhosttyError,
    MouseButton,
    Point,
    Screen,
    ScreenRegion,
    Size,
    Surface,
    Tab,
    Terminal,
    Window,
)

if TYPE_CHECKING:
    from conftest import ScriptRecorder


def test_tell_wraps_in_application_block(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("ok")
    g.name
    script = rec.last
    assert script.startswith('tell application "Ghostty"')
    assert script.endswith("end tell")


def test_ghostty_name(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("Ghostty")
    assert g.name == "Ghostty"
    assert "get name" in rec.last


def test_ghostty_version(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("1.3.1")
    assert g.version == "1.3.1"


def test_ghostty_frontmost_true(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("true")
    assert g.frontmost is True


def test_ghostty_frontmost_false(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("false")
    assert g.frontmost is False


def test_ghostty_front_window(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("win-123")
    w = g.front_window
    assert isinstance(w, Window)
    assert w.id == "win-123"
    assert w._specifier == 'window id "win-123"'
    assert "get id of front window" in rec.last


def test_ghostty_windows(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("w1, w2, w3")
    ws = g.windows
    assert len(ws) == 3
    assert all(isinstance(w, Window) for w in ws)
    assert [w.id for w in ws] == ["w1", "w2", "w3"]
    assert "get id of every window" in rec.last


def test_ghostty_windows_empty(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("")
    assert g.windows == []


def test_ghostty_terminals(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("t1, t2")
    ts = g.terminals
    assert len(ts) == 2
    assert all(isinstance(t, Terminal) for t in ts)


def test_ghostty_is_running_true(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("true")
    assert g.is_running is True
    assert "System Events" in rec.last


def test_ghostty_is_running_false(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("false")
    assert g.is_running is False


def test_ghostty_is_running_error() -> None:
    def failing_transport(source: str) -> str:
        raise GhosttyError("no access")

    g = Ghostty(transport=failing_transport)
    assert g.is_running is False


def test_new_window(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("new-win-id")
    w = g.new_window()
    assert isinstance(w, Window)
    assert w.id == "new-win-id"
    assert "set w to (new window)" in rec.last
    assert "return id of w" in rec.last


def test_new_window_with_kwargs(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("new-win-id")
    g.new_window(font_size=14.0, command="/bin/bash")
    script = rec.last
    assert "set cfg to (new surface configuration)" in script
    assert "set font size of cfg to 14.0" in script
    assert 'set command of cfg to "/bin/bash"' in script
    assert "new window with configuration cfg" in script


def test_new_window_with_config(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("new-win-id")
    cfg = Surface(working_directory="/tmp")
    g.new_window(config=cfg)
    assert 'set initial working directory of cfg to "/tmp"' in rec.last


def test_window_name(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("My Window")
    assert w.name == "My Window"
    assert 'get name of window id "w1"' in rec.last


def test_window_selected_tab(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("tab-1")
    t = w.selected_tab
    assert isinstance(t, Tab)
    assert t.id == "tab-1"
    assert t._specifier == 'tab id "tab-1" of window id "w1"'


def test_window_tabs(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("t1, t2")
    tabs = w.tabs
    assert len(tabs) == 2
    assert tabs[0]._specifier == 'tab id "t1" of window id "w1"'
    assert tabs[1]._specifier == 'tab id "t2" of window id "w1"'


def test_window_terminals(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("tm1, tm2")
    terms = w.terminals
    assert terms[0]._specifier == 'terminal id "tm1"'
    assert terms[1]._specifier == 'terminal id "tm2"'


def test_window_activate(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    w.activate()
    assert 'activate window (window id "w1")' in rec.last


def test_window_close(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    w.close()
    assert 'close window (window id "w1")' in rec.last


def test_window_new_tab(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("new-tab-id")
    t = w.new_tab()
    assert t.id == "new-tab-id"
    assert t._specifier == 'tab id "new-tab-id" of window id "w1"'
    assert 'new tab in (window id "w1")' in rec.last


def test_window_new_tab_with_config(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("new-tab-id")
    w.new_tab(command="/bin/bash")
    script = rec.last
    assert "set cfg to (new surface configuration)" in script
    assert "with configuration cfg" in script


def test_tab_index(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Tab(id="t1", specifier='tab id "t1" of window id "w1"', app=g)
    rec.respond("3")
    assert t.index == 3


def test_tab_selected(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Tab(id="t1", specifier='tab id "t1" of window id "w1"', app=g)
    rec.respond("true")
    assert t.selected is True


def test_tab_focused_terminal(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Tab(id="t1", specifier='tab id "t1" of window id "w1"', app=g)
    rec.respond("term-1")
    term = t.focused_terminal
    assert isinstance(term, Terminal)
    assert term._specifier == 'terminal id "term-1"'


def test_tab_terminals(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Tab(id="t1", specifier='tab id "t1" of window id "w1"', app=g)
    rec.respond("tm1")
    terms = t.terminals
    assert len(terms) == 1
    assert terms[0]._specifier == 'terminal id "tm1"'


def test_tab_select(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Tab(id="t1", specifier='tab id "t1" of window id "w1"', app=g)
    t.select()
    assert 'select tab (tab id "t1" of window id "w1")' in rec.last


def test_tab_close(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Tab(id="t1", specifier='tab id "t1" of window id "w1"', app=g)
    t.close()
    assert 'close tab (tab id "t1" of window id "w1")' in rec.last


def test_terminal_input(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.input("echo hello\n")
    assert 'input text "echo hello\n" to (terminal id "t1")' in rec.last


def test_terminal_input_escaping(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.input('say "hi"')
    assert 'input text "say \\"hi\\"" to (terminal id "t1")' in rec.last


def test_terminal_send_key_simple(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_key("enter")
    assert 'send key "enter" to (terminal id "t1")' in rec.last


def test_terminal_send_key_with_modifiers_string(
    g: Ghostty, rec: ScriptRecorder
) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_key("c", modifiers="control")
    assert 'send key "c" modifiers "control" to (terminal id "t1")' in rec.last


def test_terminal_send_key_with_modifiers_list(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_key("c", modifiers=["control", "shift"])
    assert 'modifiers "control, shift"' in rec.last


def test_terminal_send_key_with_action(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_key("a", action="release")
    assert "action release" in rec.last


def test_terminal_send_key_default_action_omitted(
    g: Ghostty, rec: ScriptRecorder
) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_key("a")
    assert "action" not in rec.last


def test_terminal_send_mouse_button(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_mouse_button("left button")
    assert "send mouse button left button" in rec.last
    assert "to (terminal id" in rec.last


def test_terminal_send_mouse_button_with_modifiers(
    g: Ghostty, rec: ScriptRecorder
) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_mouse_button(MouseButton.right, modifiers="shift")
    assert "send mouse button right button" in rec.last
    assert 'modifiers "shift"' in rec.last


def test_terminal_send_mouse_position(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_mouse_position(x=100.0, y=200.0)
    assert "send mouse position x 100.0 y 200.0" in rec.last


def test_terminal_send_mouse_position_with_modifiers(
    g: Ghostty, rec: ScriptRecorder
) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_mouse_position(x=10.0, y=20.0, modifiers="option")
    assert 'modifiers "option"' in rec.last


def test_terminal_send_mouse_scroll(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_mouse_scroll(x=0, y=-3.0)
    assert "send mouse scroll x 0 y -3.0" in rec.last


def test_terminal_send_mouse_scroll_full(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.send_mouse_scroll(
        x=0, y=-3.0, precision=True, momentum="began", modifiers="command"
    )
    script = rec.last
    assert "precision true" in script
    assert "momentum began" in script
    assert 'modifiers "command"' in script


def test_terminal_split(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("new-term-id")
    new = t.split("down")
    assert new.id == "new-term-id"
    assert new._specifier == 'terminal id "new-term-id"'
    script = rec.last
    assert 'split (terminal id "t1") direction down' in script
    assert "return id of t" in script


def test_terminal_split_default_direction(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("new-id")
    t.split()
    assert "direction right" in rec.last


def test_terminal_split_with_config(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("new-id")
    t.split("right", font_size=12.0)
    script = rec.last
    assert "set cfg to (new surface configuration)" in script
    assert "set font size of cfg to 12.0" in script
    assert "with configuration cfg" in script


def test_terminal_focus(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.focus()
    assert 'focus (terminal id "t1")' in rec.last


def test_terminal_close(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    t.close()
    assert 'close (terminal id "t1")' in rec.last


def test_terminal_perform_true(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("true")
    assert t.perform("copy_to_clipboard") is True
    assert 'perform action "copy_to_clipboard" on (terminal id "t1")' in rec.last


def test_terminal_perform_false(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("false")
    assert t.perform("unknown_action") is False


def test_terminal_resize_split(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("true")
    assert t.resize_split("right", 5) is True
    assert 'perform action "resize_split:right,5" on (terminal id "t1")' in rec.last


def test_terminal_resize_split_default_amount(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("true")
    t.resize_split("down")
    assert 'perform action "resize_split:down,1" on (terminal id "t1")' in rec.last


def test_terminal_resize_split_string_direction(
    g: Ghostty, rec: ScriptRecorder
) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("true")
    t.resize_split("left", 3)
    assert 'perform action "resize_split:left,3" on (terminal id "t1")' in rec.last


def test_terminal_equalize_splits(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Terminal(id="t1", specifier='terminal id "t1"', app=g)
    rec.respond("true")
    assert t.equalize_splits() is True
    assert 'perform action "equalize_splits" on (terminal id "t1")' in rec.last


def test_tab_equalize_splits(g: Ghostty, rec: ScriptRecorder) -> None:
    t = Tab(id="t1", specifier='tab id "t1" of window id "w1"', app=g)
    rec.respond("term-1", "true")
    assert t.equalize_splits() is True
    assert 'perform action "equalize_splits" on (terminal id "term-1")' in rec.last


def test_window_get_bounds(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1", "100, 200, 800, 500")
    b = w.bounds
    assert b == Bounds(100, 200, 900, 700)
    assert "System Events" in rec.last
    assert "position, size" in rec.last


def test_window_set_bounds(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1")
    w.bounds = Bounds(0, 0, 800, 600)
    assert "set position of window 1 to {0, 0}" in rec.last
    assert "set size of window 1 to {800, 600}" in rec.last


def test_window_set_bounds_from_args(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1")
    w.bounds = Bounds(10, 20, 810, 620)
    assert "set position of window 1 to {10, 20}" in rec.last
    assert "set size of window 1 to {800, 600}" in rec.last


def test_window_get_position(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1", "100, 200, 800, 500")
    assert w.position == Point(100, 200)


def test_window_set_position(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1", "100, 200, 800, 500", "w1")  # get index, get bounds, set index
    w.position = Point(50, 50)
    # Size was 800x500, so new bounds = (50, 50, 850, 550)
    assert "set position of window 1 to {50, 50}" in rec.last
    assert "set size of window 1 to {800, 500}" in rec.last


def test_window_get_size(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1", "100, 200, 800, 500")
    assert w.size == Size(800, 500)


def test_window_set_size(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1", "100, 200, 800, 500", "w1")  # get index, get bounds, set index
    w.size = Size(400, 300)
    # Position was (100, 200), so new bounds = (100, 200, 500, 500)
    assert "set position of window 1 to {100, 200}" in rec.last
    assert "set size of window 1 to {400, 300}" in rec.last


def test_window_move_to(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1", "0, 0, 800, 600", "w1")  # get index, get bounds, set index
    w.move_to(50, 25)
    assert "set position of window 1 to {50, 25}" in rec.last
    assert "set size of window 1 to {800, 600}" in rec.last


def test_window_resize_to(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1", "100, 200, 800, 500", "w1")  # get index, get bounds, set index
    w.resize_to(1000, 800)
    assert "set position of window 1 to {100, 200}" in rec.last
    assert "set size of window 1 to {1000, 800}" in rec.last


def test_window_maximize(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1")  # set index
    scr = Screen(origin=Point(0, 25), size=Size(1920, 1055))
    w.maximize(screen=scr)
    assert "set position of window 1 to {0, 25}" in rec.last
    assert "set size of window 1 to {1920, 1055}" in rec.last


def test_window_center(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    # center() reads bounds for size, then position setter reads bounds again
    rec.respond("w1", "0, 0, 800, 600", "w1", "0, 0, 800, 600", "w1")
    scr = Screen(origin=Point(0, 25), size=Size(1920, 1055))
    w.center(screen=scr)
    # center x = 0 + (1920 - 800) // 2 = 560
    # center y = 25 + (1055 - 600) // 2 = 252
    assert "set position of window 1 to {560, 252}" in rec.last
    assert "set size of window 1 to {800, 600}" in rec.last


def test_window_tile_region(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1")
    scr = Screen(origin=Point(0, 25), size=Size(1920, 1055))
    w.tile(ScreenRegion.left_half, screen=scr)
    assert "set position of window 1 to {0, 25}" in rec.last
    assert "set size of window 1 to {960, 1055}" in rec.last


def test_window_tile_region_with_gap(g: Ghostty, rec: ScriptRecorder) -> None:
    w = Window(id="w1", specifier='window id "w1"', app=g)
    rec.respond("w1")
    scr = Screen(origin=Point(0, 25), size=Size(1920, 1055))
    w.tile(ScreenRegion.left_half, screen=scr, gap=5)
    assert "set position of window 1 to {5, 30}" in rec.last
    assert "set size of window 1 to {950, 1045}" in rec.last


def test_ghostty_run(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("hello")
    result = g.run('return "hello"')
    assert result == "hello"
    # Should NOT be wrapped in tell application block
    assert "tell application" not in rec.last


def test_main_screen(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("0, 25, 1920, 1055")
    scr = g.main_screen()
    assert scr == Screen(origin=Point(0, 25), size=Size(1920, 1055))
    assert "NSScreen" in rec.last
    assert "tell application" not in rec.last


def test_screens(g: Ghostty, rec: ScriptRecorder) -> None:
    rec.respond("0,25,1920,1055;-1920,0,1920,1080")
    result = g.screens()
    assert len(result) == 2
    assert result[0] == Screen(origin=Point(0, 25), size=Size(1920, 1055))
    assert result[1] == Screen(origin=Point(-1920, 0), size=Size(1920, 1080))


def test_tile_windows_grid(g: Ghostty, rec: ScriptRecorder) -> None:
    w1 = Window(id="w1", specifier='window id "w1"', app=g)
    w2 = Window(id="w2", specifier='window id "w2"', app=g)
    scr = Screen(origin=Point(0, 0), size=Size(1000, 800))
    rec.respond("w1, w2", "", "w1, w2", "")
    g.tile_windows([w1, w2], screen=scr)
    # 2 windows -> 2 columns, 1 row; cell = 500x800
    # Each bounds set = 2 scripts (index lookup + System Events set)
    assert len(rec.scripts) == 4
    assert "set position of window 1 to {0, 0}" in rec.scripts[1]
    assert "set size of window 1 to {500, 800}" in rec.scripts[1]
    assert "set position of window 2 to {500, 0}" in rec.scripts[3]
    assert "set size of window 2 to {500, 800}" in rec.scripts[3]


def test_tile_windows_four(g: Ghostty, rec: ScriptRecorder) -> None:
    wins = [Window(id=f"w{i}", specifier=f'window id "w{i}"', app=g) for i in range(4)]
    scr = Screen(origin=Point(0, 0), size=Size(1000, 800))
    ids = "w0, w1, w2, w3"
    rec.respond(ids, "", ids, "", ids, "", ids, "")
    g.tile_windows(wins, screen=scr)
    # 4 windows -> 2 cols, 2 rows; cell = 500x400
    assert len(rec.scripts) == 8
    assert "set position of window 1 to {0, 0}" in rec.scripts[1]
    assert "set size of window 1 to {500, 400}" in rec.scripts[1]
    assert "set position of window 2 to {500, 0}" in rec.scripts[3]
    assert "set size of window 2 to {500, 400}" in rec.scripts[3]
    assert "set position of window 3 to {0, 400}" in rec.scripts[5]
    assert "set size of window 3 to {500, 400}" in rec.scripts[5]
    assert "set position of window 4 to {500, 400}" in rec.scripts[7]
    assert "set size of window 4 to {500, 400}" in rec.scripts[7]


def test_tile_windows_with_gap(g: Ghostty, rec: ScriptRecorder) -> None:
    w1 = Window(id="w1", specifier='window id "w1"', app=g)
    w2 = Window(id="w2", specifier='window id "w2"', app=g)
    scr = Screen(origin=Point(0, 0), size=Size(1000, 800))
    rec.respond("w1, w2", "", "w1, w2", "")
    g.tile_windows([w1, w2], screen=scr, gap=10)
    assert "set position of window 1 to {10, 10}" in rec.scripts[1]
    assert "set size of window 1 to {480, 780}" in rec.scripts[1]
    assert "set position of window 2 to {510, 10}" in rec.scripts[3]
    assert "set size of window 2 to {480, 780}" in rec.scripts[3]


def test_tile_windows_empty(g: Ghostty, rec: ScriptRecorder) -> None:
    scr = Screen(origin=Point(0, 0), size=Size(1000, 800))
    g.tile_windows([], screen=scr)
    assert len(rec.scripts) == 0


def test_tile_windows_custom_columns(g: Ghostty, rec: ScriptRecorder) -> None:
    wins = [Window(id=f"w{i}", specifier=f'window id "w{i}"', app=g) for i in range(3)]
    scr = Screen(origin=Point(0, 0), size=Size(900, 600))
    ids = "w0, w1, w2"
    rec.respond(ids, "", ids, "", ids, "")
    g.tile_windows(wins, screen=scr, columns=3)
    # 3 cols, 1 row; cell = 300x600
    assert len(rec.scripts) == 6
    assert "set position of window 1 to {0, 0}" in rec.scripts[1]
    assert "set size of window 1 to {300, 600}" in rec.scripts[1]
    assert "set position of window 2 to {300, 0}" in rec.scripts[3]
    assert "set size of window 2 to {300, 600}" in rec.scripts[3]
    assert "set position of window 3 to {600, 0}" in rec.scripts[5]
    assert "set size of window 3 to {300, 600}" in rec.scripts[5]
