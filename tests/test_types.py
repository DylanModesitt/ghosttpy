"""Tests for pure data types, helpers, and descriptors."""

from __future__ import annotations

import pytest

from ghosttpy import (
    Bounds,
    Ghostty,
    GhosttyError,
    InputAction,
    MouseButton,
    Point,
    Screen,
    ScreenRegion,
    ScrollMomentum,
    Size,
    SplitDirection,
    Surface,
    Tab,
    Terminal,
    Window,
    _auto_columns,
    _escape,
)


def test_escape_quotes() -> None:
    assert _escape('say "hello"') == 'say \\"hello\\"'


def test_escape_backslash() -> None:
    assert _escape("path\\to") == "path\\\\to"


def test_escape_mixed() -> None:
    assert _escape('a\\b"c') == 'a\\\\b\\"c'


def test_config_lines_empty() -> None:
    assert Surface()._lines() == ["set cfg to (new surface configuration)"]


def test_config_lines_font_size() -> None:
    lines = Surface(font_size=14.0)._lines()
    assert "set font size of cfg to 14.0" in lines


def test_config_lines_working_directory() -> None:
    lines = Surface(working_directory="/tmp")._lines()
    assert 'set initial working directory of cfg to "/tmp"' in lines


def test_config_lines_command() -> None:
    lines = Surface(command="/bin/bash")._lines()
    assert 'set command of cfg to "/bin/bash"' in lines


def test_config_lines_initial_input() -> None:
    lines = Surface(initial_input="hello\n")._lines()
    assert 'set initial input of cfg to "hello\n"' in lines


def test_config_lines_wait_after_command() -> None:
    lines = Surface(wait_after_command=True)._lines()
    assert "set wait after command of cfg to true" in lines


def test_config_lines_wait_after_command_false() -> None:
    lines = Surface(wait_after_command=False)._lines()
    assert "set wait after command of cfg to false" in lines


def test_config_lines_environment() -> None:
    lines = Surface(environment={"FOO": "bar", "BAZ": "qux"})._lines()
    assert 'set environment variables of cfg to {"FOO=bar", "BAZ=qux"}' in lines


def test_config_lines_custom_var() -> None:
    lines = Surface(font_size=10.0)._lines(var="c")
    assert lines[0] == "set c to (new surface configuration)"
    assert "set font size of c to 10.0" in lines


def test_config_lines_full() -> None:
    cfg = Surface(
        font_size=14.0,
        working_directory="/tmp",
        command="/bin/bash",
        initial_input="hi",
        wait_after_command=True,
        environment={"A": "1"},
    )
    lines = cfg._lines()
    assert len(lines) == 7  # 1 create + 6 properties


def test_resolve_config_none() -> None:
    assert Surface.resolve(None, {}) is None


def test_resolve_config_passthrough() -> None:
    cfg = Surface(font_size=12.0)
    assert Surface.resolve(cfg, {}) is cfg


def test_resolve_config_from_kwargs() -> None:
    cfg = Surface.resolve(None, {"font_size": 14.0})
    assert cfg == Surface(font_size=14.0)


def test_resolve_config_conflict() -> None:
    with pytest.raises(TypeError, match="cannot combine"):
        Surface.resolve(Surface(), {"font_size": 14.0})


def test_split_direction_from_string() -> None:
    assert SplitDirection("down") is SplitDirection.down


def test_input_action_values() -> None:
    assert InputAction.press.value == "press"
    assert InputAction.release.value == "release"


def test_mouse_button_values() -> None:
    assert MouseButton.left.value == "left button"
    assert MouseButton.right.value == "right button"
    assert MouseButton.middle.value == "middle button"


def test_scroll_momentum_values() -> None:
    assert ScrollMomentum.may_begin.value == "may begin"
    assert ScrollMomentum.none.value == "none"


def test_base_repr(g: Ghostty) -> None:
    t = Terminal(id="abc", specifier='terminal id "abc"', app=g)
    assert repr(t) == "Terminal('abc')"


def test_base_id_property(g: Ghostty) -> None:
    t = Terminal(id="abc", specifier='terminal id "abc"', app=g)
    assert t.id == "abc"


def test_base_eq(g: Ghostty) -> None:
    t1 = Terminal(id="abc", specifier='terminal id "abc"', app=g)
    t2 = Terminal(id="abc", specifier='terminal id "abc"', app=g)
    assert t1 == t2


def test_base_neq(g: Ghostty) -> None:
    t1 = Terminal(id="abc", specifier='terminal id "abc"', app=g)
    t2 = Terminal(id="xyz", specifier='terminal id "xyz"', app=g)
    assert t1 != t2


def test_base_neq_different_types(g: Ghostty) -> None:
    t = Terminal(id="abc", specifier='terminal id "abc"', app=g)
    w = Window(id="abc", specifier='window id "abc"', app=g)
    assert t != w


def test_base_hash(g: Ghostty) -> None:
    t1 = Terminal(id="abc", specifier='terminal id "abc"', app=g)
    t2 = Terminal(id="abc", specifier='terminal id "abc"', app=g)
    assert hash(t1) == hash(t2)
    assert len({t1, t2}) == 1


def test_property_auto_naming() -> None:
    assert Terminal.working_directory._as_name == "working directory"
    assert Tab.focused_terminal._as_name == "focused terminal"
    assert Ghostty.front_window._as_name == "front window"
    assert Ghostty.name._as_name == "name"


def test_elements_auto_naming() -> None:
    assert Window.tabs._as_name == "tab"
    assert Window.terminals._as_name == "terminal"
    assert Ghostty.windows._as_name == "window"


def test_ghostty_error_with_code() -> None:
    e = GhosttyError("something broke", -1728)
    assert str(e) == "something broke"
    assert e.code == -1728


def test_ghostty_error_without_code() -> None:
    e = GhosttyError("oops")
    assert str(e) == "oops"
    assert e.code is None


def test_ghostty_repr() -> None:
    g = Ghostty(transport=lambda s: "")
    assert repr(g) == "Ghostty()"


def test_point_fields() -> None:
    p = Point(10, 20)
    assert p.x == 10 and p.y == 20


def test_size_fields() -> None:
    s = Size(800, 600)
    assert s.width == 800 and s.height == 600


def test_bounds_position() -> None:
    b = Bounds(100, 200, 900, 700)
    assert b.position == Point(100, 200)


def test_bounds_size() -> None:
    b = Bounds(100, 200, 900, 700)
    assert b.size == Size(800, 500)


def test_bounds_from_position_size() -> None:
    b = Bounds.from_position_size(Point(50, 60), Size(400, 300))
    assert b == Bounds(50, 60, 450, 360)


def test_screen_bounds() -> None:
    scr = Screen(origin=Point(0, 25), size=Size(1920, 1055))
    assert scr.bounds == Bounds(0, 25, 1920, 1080)


def test_screen_bounds_negative_origin() -> None:
    scr = Screen(origin=Point(-1920, 0), size=Size(1920, 1080))
    assert scr.bounds == Bounds(-1920, 0, 0, 1080)


_TEST_SCREEN = Screen(origin=Point(0, 25), size=Size(1920, 1055))


def test_region_full() -> None:
    assert ScreenRegion.full.compute(_TEST_SCREEN) == Bounds(0, 25, 1920, 1080)


def test_region_left_half() -> None:
    assert ScreenRegion.left_half.compute(_TEST_SCREEN) == Bounds(0, 25, 960, 1080)


def test_region_right_half() -> None:
    assert ScreenRegion.right_half.compute(_TEST_SCREEN) == Bounds(960, 25, 1920, 1080)


def test_region_top_half() -> None:
    b = ScreenRegion.top_half.compute(_TEST_SCREEN)
    assert b == Bounds(0, 25, 1920, 552)


def test_region_bottom_half() -> None:
    b = ScreenRegion.bottom_half.compute(_TEST_SCREEN)
    assert b == Bounds(0, 552, 1920, 1080)


def test_region_top_left() -> None:
    b = ScreenRegion.top_left.compute(_TEST_SCREEN)
    assert b == Bounds(0, 25, 960, 552)


def test_region_top_right() -> None:
    b = ScreenRegion.top_right.compute(_TEST_SCREEN)
    assert b == Bounds(960, 25, 1920, 552)


def test_region_bottom_left() -> None:
    b = ScreenRegion.bottom_left.compute(_TEST_SCREEN)
    assert b == Bounds(0, 552, 960, 1080)


def test_region_bottom_right() -> None:
    b = ScreenRegion.bottom_right.compute(_TEST_SCREEN)
    assert b == Bounds(960, 552, 1920, 1080)


def test_region_left_third() -> None:
    b = ScreenRegion.left_third.compute(_TEST_SCREEN)
    assert b == Bounds(0, 25, 640, 1080)


def test_region_center_third() -> None:
    b = ScreenRegion.center_third.compute(_TEST_SCREEN)
    assert b == Bounds(640, 25, 1280, 1080)


def test_region_right_third() -> None:
    b = ScreenRegion.right_third.compute(_TEST_SCREEN)
    assert b == Bounds(1280, 25, 1920, 1080)


def test_region_left_two_thirds() -> None:
    b = ScreenRegion.left_two_thirds.compute(_TEST_SCREEN)
    assert b == Bounds(0, 25, 1280, 1080)


def test_region_right_two_thirds() -> None:
    b = ScreenRegion.right_two_thirds.compute(_TEST_SCREEN)
    assert b == Bounds(640, 25, 1920, 1080)


def test_region_first_fourth() -> None:
    b = ScreenRegion.first_fourth.compute(_TEST_SCREEN)
    assert b == Bounds(0, 25, 480, 1080)


def test_region_second_fourth() -> None:
    b = ScreenRegion.second_fourth.compute(_TEST_SCREEN)
    assert b == Bounds(480, 25, 960, 1080)


def test_region_third_fourth() -> None:
    b = ScreenRegion.third_fourth.compute(_TEST_SCREEN)
    assert b == Bounds(960, 25, 1440, 1080)


def test_region_last_fourth() -> None:
    b = ScreenRegion.last_fourth.compute(_TEST_SCREEN)
    assert b == Bounds(1440, 25, 1920, 1080)


def test_region_left_three_fourths() -> None:
    b = ScreenRegion.left_three_fourths.compute(_TEST_SCREEN)
    assert b == Bounds(0, 25, 1440, 1080)


def test_region_right_three_fourths() -> None:
    b = ScreenRegion.right_three_fourths.compute(_TEST_SCREEN)
    assert b == Bounds(480, 25, 1920, 1080)


def test_region_first_sixth() -> None:
    b = ScreenRegion.first_sixth.compute(_TEST_SCREEN)
    assert b == Bounds(0, 25, 320, 1080)


def test_region_last_sixth() -> None:
    b = ScreenRegion.last_sixth.compute(_TEST_SCREEN)
    assert b == Bounds(1600, 25, 1920, 1080)


def test_region_gap() -> None:
    b = ScreenRegion.left_half.compute(_TEST_SCREEN, gap=10)
    assert b == Bounds(10, 35, 950, 1070)


def test_region_all_members_have_specs() -> None:
    for member in ScreenRegion:
        b = member.compute(_TEST_SCREEN)
        assert isinstance(b, Bounds)


def test_auto_columns() -> None:
    assert _auto_columns(1) == 1
    assert _auto_columns(2) == 2
    assert _auto_columns(3) == 2
    assert _auto_columns(4) == 2
    assert _auto_columns(5) == 3
    assert _auto_columns(6) == 3
    assert _auto_columns(9) == 3
