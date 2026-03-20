"""ghosttpy"""

from __future__ import annotations

import re
import subprocess
import dataclasses
import enum
from typing import Annotated, Any, Callable, ClassVar, get_type_hints

__all__ = [
    "Ghostty",
    "GhosttyError",
    "Window",
    "Tab",
    "Terminal",
    "Surface",
    "SplitDirection",
    "InputAction",
    "MouseButton",
    "ScrollMomentum",
    "Point",
    "Size",
    "Bounds",
    "Screen",
    "ScreenRegion",
]


class _Base:
    """Base for Ghostty scriptable objects identified by a stable ID."""

    _kind: ClassVar[str]
    _scoped: ClassVar[bool] = False

    def __init_subclass__(cls, **kw: Any) -> None:
        super().__init_subclass__(**kw)
        cls._kind = cls.__name__.lower()

    def __init__(self, id: str, specifier: str, app: Ghostty) -> None:
        self._id = id
        self._specifier: str = specifier
        self._app: Ghostty = app

    @property
    def id(self) -> str:
        """The stable identifier for this object."""
        return self._id

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._id!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._id))

    @classmethod
    def child(cls, id: str, parent: _Base | Ghostty) -> _Base:
        """Construct a child object with the correct AppleScript specifier."""
        specifier = f'{cls._kind} id "{id}"'
        if cls._scoped and parent._specifier is not None:
            specifier = f"{specifier} of {parent._specifier}"
        app = parent if isinstance(parent, Ghostty) else parent._app
        return cls(id=id, specifier=specifier, app=app)


class AsProp:
    """Descriptor mapping a Python attribute to a live AppleScript property."""

    def __init__(self, ty: type = str) -> None:
        self._ty = ty

    def __set_name__(self, owner: type, name: str) -> None:
        self._as_name = name.replace("_", " ")

    def __get__(self, obj: _Base | Ghostty | None, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        is_obj = isinstance(self._ty, type) and issubclass(self._ty, _Base)
        expr = f"id of {self._as_name}" if is_obj else self._as_name
        if obj._specifier is not None:
            script = f"get {expr} of {obj._specifier}"
        else:
            script = f"get {expr}"
        raw = obj._app.tell(script)
        if self._ty is bool:
            return raw == "true"
        if self._ty is int:
            return int(raw)
        if is_obj:
            return self._ty.child(raw, obj)
        return raw


class Elements:
    """Descriptor mapping a Python attribute to an AppleScript element collection."""

    def __init__(self, ty: type[_Base]) -> None:
        self._ty = ty

    def __set_name__(self, owner: type, name: str) -> None:
        self._as_name = name.rstrip("s")

    def __get__(
        self, obj: _Base | Ghostty | None, objtype: type | None = None
    ) -> list[Any]:
        if obj is None:
            return self  # type: ignore[return-value]
        if obj._specifier is not None:
            script = f"get id of every {self._as_name} of {obj._specifier}"
        else:
            script = f"get id of every {self._as_name}"
        raw = obj._app.tell(script)
        if not raw:
            return []
        return [self._ty.child(s.strip(), obj) for s in raw.split(", ")]


class SplitDirection(enum.StrEnum):
    right = "right"
    left = "left"
    down = "down"
    up = "up"


class InputAction(enum.StrEnum):
    press = "press"
    release = "release"


class Terminal(_Base):
    name = AsProp()
    working_directory = AsProp()

    def input(self, text: str) -> None:
        """Input text to this terminal as if pasted."""
        self._app.tell(f'input text "{_escape(text)}" to ({self._specifier})')

    def send_key(
        self,
        key: str,
        *,
        modifiers: str | list[str] | None = None,
        action: InputAction | str = InputAction.press,
    ) -> None:
        """Send a keyboard event to this terminal."""
        parts = [f'send key "{_escape(key)}"']
        action = InputAction(action)
        if action is not InputAction.press:
            parts.append(f"action {action.value}")
        if modifiers is not None:
            m = ", ".join(modifiers) if isinstance(modifiers, list) else modifiers
            parts.append(f'modifiers "{m}"')
        parts.append(f"to ({self._specifier})")
        self._app.tell(" ".join(parts))

    def send_mouse_button(
        self,
        button: MouseButton | str,
        *,
        action: InputAction | str = InputAction.press,
        modifiers: str | None = None,
    ) -> None:
        """Send a mouse button event to this terminal."""
        button = MouseButton(button)
        parts = [f"send mouse button {button.value}"]
        action = InputAction(action)
        if action is not InputAction.press:
            parts.append(f"action {action.value}")
        if modifiers is not None:
            parts.append(f'modifiers "{modifiers}"')
        parts.append(f"to ({self._specifier})")
        self._app.tell(" ".join(parts))

    def send_mouse_position(
        self, *, x: float, y: float, modifiers: str | None = None
    ) -> None:
        """Send a mouse position event to this terminal."""
        parts = [f"send mouse position x {x} y {y}"]
        if modifiers is not None:
            parts.append(f'modifiers "{modifiers}"')
        parts.append(f"to ({self._specifier})")
        self._app.tell(" ".join(parts))

    def send_mouse_scroll(
        self,
        *,
        x: float,
        y: float,
        precision: bool = False,
        momentum: ScrollMomentum | str | None = None,
        modifiers: str | None = None,
    ) -> None:
        """Send a mouse scroll event to this terminal."""
        parts = [f"send mouse scroll x {x} y {y}"]
        if precision:
            parts.append("precision true")
        if momentum is not None:
            parts.append(f"momentum {ScrollMomentum(momentum).value}")
        if modifiers is not None:
            parts.append(f'modifiers "{modifiers}"')
        parts.append(f"to ({self._specifier})")
        self._app.tell(" ".join(parts))

    def split(
        self,
        direction: SplitDirection | str = SplitDirection.right,
        *,
        config: Surface | None = None,
        **kwargs: Any,
    ) -> Terminal:
        """Split this terminal, returning the newly created one."""
        config = Surface.resolve(config, kwargs)
        direction = SplitDirection(direction)
        spec = self._specifier
        lines: list[str] = []
        if config is not None:
            lines.extend(config._lines())
            cmd = f"set t to (split ({spec}) direction {direction} with configuration cfg)"
            lines.append(cmd)
        else:
            cmd = f"set t to (split ({spec}) direction {direction})"
            lines.append(cmd)
        lines.append("return id of t")
        tid = self._app.tell(*lines)
        return Terminal(id=tid, specifier=f'terminal id "{tid}"', app=self._app)

    def focus(self) -> None:
        """Focus this terminal, bringing its window to the front."""
        self._app.tell(f"focus ({self._specifier})")

    def close(self) -> None:
        """Close this terminal."""
        self._app.tell(f"close ({self._specifier})")

    def resize_split(self, direction: SplitDirection | str, amount: int = 1) -> bool:
        """Resize this split in the given direction by *amount* cells."""
        direction = SplitDirection(direction)
        return self.perform(f"resize_split:{direction},{amount}")

    def equalize_splits(self) -> bool:
        """Equalize all split sizes in this terminal's tab."""
        return self.perform("equalize_splits")

    def perform(self, action: str) -> bool:
        """Perform a Ghostty action string on this terminal."""
        act = _escape(action)
        raw = self._app.tell(f'perform action "{act}" on ({self._specifier})')
        return raw == "true"


class Tab(_Base):
    _scoped = True

    name = AsProp()
    index = AsProp(ty=int)
    selected = AsProp(ty=bool)
    focused_terminal = AsProp(ty=Terminal)
    terminals = Elements(Terminal)

    def select(self) -> None:
        """Select this tab in its window."""
        self._app.tell(f"select tab ({self._specifier})")

    def close(self) -> None:
        """Close this tab."""
        self._app.tell(f"close tab ({self._specifier})")

    def equalize_splits(self) -> bool:
        """Equalize all split sizes in this tab."""
        return self.focused_terminal.equalize_splits()


class Window(_Base):
    name = AsProp()
    selected_tab = AsProp(ty=Tab)
    tabs = Elements(Tab)
    terminals = Elements(Terminal)

    def _window_index(self) -> int:
        """Find this window's 1-based index in the System Events window list."""
        raw = self._app.tell("get id of every window")
        ids = [s.strip() for s in raw.split(", ")]
        return ids.index(self._id) + 1

    @property
    def bounds(self) -> Bounds:
        """Get the window bounds as (left, top, right, bottom)."""
        idx = self._window_index()
        raw = self._app.run(
            'tell application "System Events" to tell process "Ghostty"\n'
            f"  return {{position, size}} of window {idx}\n"
            "end tell"
        )
        parts = [int(x.strip()) for x in raw.split(", ")]
        return Bounds(parts[0], parts[1], parts[0] + parts[2], parts[1] + parts[3])

    @bounds.setter
    def bounds(self, value: Bounds) -> None:
        """Set the window bounds."""
        idx = self._window_index()
        b = value
        self._app.run(
            'tell application "System Events" to tell process "Ghostty"\n'
            f"  set position of window {idx} to {{{b.left}, {b.top}}}\n"
            f"  set size of window {idx} to "
            f"{{{b.right - b.left}, {b.bottom - b.top}}}\n"
            "end tell"
        )

    @property
    def position(self) -> Point:
        """Get the window's top-left corner position."""
        return self.bounds.position

    @position.setter
    def position(self, value: Point) -> None:
        """Move the window, keeping its current size."""
        self.bounds = Bounds.from_position_size(value, self.bounds.size)

    @property
    def size(self) -> Size:
        """Get the window's width and height."""
        return self.bounds.size

    @size.setter
    def size(self, value: Size) -> None:
        """Resize the window, keeping its current position."""
        self.bounds = Bounds.from_position_size(self.bounds.position, value)

    def move_to(self, x: int, y: int) -> None:
        """Move this window to the given screen coordinates."""
        self.position = Point(x, y)

    def resize_to(self, width: int, height: int) -> None:
        """Resize this window to the given dimensions."""
        self.size = Size(width, height)

    def maximize(self, screen: Screen | None = None) -> None:
        """Fill the given screen (or the main screen)."""
        scr = screen or self._app.main_screen()
        self.bounds = scr.bounds

    def center(self, screen: Screen | None = None) -> None:
        """Center this window on the given screen, keeping its current size."""
        scr = screen or self._app.main_screen()
        ws = self.bounds.size
        x = scr.origin.x + (scr.size.width - ws.width) // 2
        y = scr.origin.y + (scr.size.height - ws.height) // 2
        self.position = Point(x, y)

    def tile(
        self, region: ScreenRegion, screen: Screen | None = None, *, gap: int = 0
    ) -> None:
        """Position this window in a named screen region."""
        scr = screen or self._app.main_screen()
        self.bounds = region.compute(scr, gap=gap)

    def activate(self) -> None:
        """Activate this window, bringing it to the front."""
        self._app.tell(f"activate window ({self._specifier})")

    def close(self) -> None:
        """Close this window."""
        self._app.tell(f"close window ({self._specifier})")

    def new_tab(self, config: Surface | None = None, **kwargs: Any) -> Tab:
        """Create a new tab in this window."""
        config = Surface.resolve(config, kwargs)
        spec = self._specifier
        lines: list[str] = []
        if config is not None:
            lines.extend(config._lines())
            cmd = f"set t to (new tab in ({spec}) with configuration cfg)"
            lines.append(cmd)
        else:
            lines.append(f"set t to (new tab in ({spec}))")
        lines.append("return id of t")
        tid = self._app.tell(*lines)
        return Tab(id=tid, specifier=f'tab id "{tid}" of {spec}', app=self._app)


class Ghostty:
    """Entry point for scripting Ghostty via AppleScript."""

    _specifier = None

    def __init__(self, *, transport: Callable[[str], str] | None = None) -> None:
        self._app = self
        self._transport = transport or _osascript

    name = AsProp()
    version = AsProp()
    frontmost = AsProp(ty=bool)
    front_window = AsProp(ty=Window)
    windows = Elements(Window)
    terminals = Elements(Terminal)

    @property
    def is_running(self) -> bool:
        """Check whether Ghostty is currently running."""
        try:
            raw = self._transport(
                'tell application "System Events" to '
                '(name of processes) contains "Ghostty"'
            )
            return raw == "true"
        except GhosttyError:
            return False

    def new_window(self, config: Surface | None = None, **kwargs: Any) -> Window:
        """Create a new Ghostty window."""
        config = Surface.resolve(config, kwargs)
        lines: list[str] = []
        if config is not None:
            lines.extend(config._lines())
            lines.append("set w to (new window with configuration cfg)")
        else:
            lines.append("set w to (new window)")
        lines.append("return id of w")
        wid = self.tell(*lines)
        return Window(id=wid, specifier=f'window id "{wid}"', app=self)

    def tell(self, *lines: str) -> str:
        """Execute AppleScript lines within a tell application block."""
        body = "\n    ".join(lines)
        return self._transport(f'tell application "Ghostty"\n    {body}\nend tell')

    def run(self, source: str) -> str:
        """Execute raw AppleScript without the Ghostty tell block."""
        return self._transport(source)

    def main_screen(self) -> Screen:
        """Return the visible area of the main display (top-left origin)."""
        raw = self._transport(_MAIN_SCREEN_SCRIPT)
        parts = [int(round(float(x.strip()))) for x in raw.split(", ")]
        return Screen(origin=Point(parts[0], parts[1]), size=Size(parts[2], parts[3]))

    def screens(self) -> list[Screen]:
        """Return the visible area of every display (top-left origin)."""
        raw = self._transport(_ALL_SCREENS_SCRIPT)
        result: list[Screen] = []
        for entry in raw.split(";"):
            parts = [int(round(float(x.strip()))) for x in entry.split(",")]
            origin = Point(parts[0], parts[1])
            size = Size(parts[2], parts[3])
            result.append(Screen(origin=origin, size=size))
        return result

    def tile_windows(
        self,
        windows: list[Window] | None = None,
        *,
        screen: Screen | None = None,
        columns: int | None = None,
        gap: int = 0,
    ) -> None:
        """Arrange windows in a grid on the given screen."""
        wins = self.windows if windows is None else windows
        if not wins:
            return
        scr = screen or self.main_screen()
        n = len(wins)
        cols = columns or _auto_columns(n)
        rows = (n + cols - 1) // cols
        ox, oy = scr.origin.x, scr.origin.y
        sw, sh = scr.size.width, scr.size.height
        cell_w = sw // cols
        cell_h = sh // rows
        for i, win in enumerate(wins):
            col = i % cols
            row = i // cols
            win.bounds = Bounds(
                ox + col * cell_w + gap,
                oy + row * cell_h + gap,
                ox + (col + 1) * cell_w - gap,
                oy + (row + 1) * cell_h - gap,
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class GhosttyError(Exception):
    """An error from Ghostty or its AppleScript bridge."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


@dataclasses.dataclass(frozen=True, slots=True)
class Surface:
    """Reusable settings applied when creating a terminal surface."""

    font_size: Annotated[float | None, "font size"] = None
    working_directory: Annotated[str | None, "initial working directory"] = None
    command: Annotated[str | None, "command"] = None
    initial_input: Annotated[str | None, "initial input"] = None
    wait_after_command: Annotated[bool | None, "wait after command"] = None
    environment: Annotated[dict[str, str] | None, "environment variables"] = None

    def _lines(self, var: str = "cfg") -> list[str]:
        """Generate AppleScript lines to create and configure a surface."""
        hints = get_type_hints(type(self), include_extras=True)
        out = [f"set {var} to (new surface configuration)"]
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)
            if value is None:
                continue
            prop = hints[f.name].__metadata__[0]
            if isinstance(value, dict):
                escaped = [f'"{_escape(f"{k}={v}")}"' for k, v in value.items()]
                items = "{" + ", ".join(escaped) + "}"
                out.append(f"set {prop} of {var} to {items}")
            elif isinstance(value, bool):
                out.append(f"set {prop} of {var} to {str(value).lower()}")
            elif isinstance(value, (int, float)):
                out.append(f"set {prop} of {var} to {value}")
            else:
                out.append(f'set {prop} of {var} to "{_escape(str(value))}"')
        return out

    @classmethod
    def resolve(cls, config: Surface | None, kwargs: dict[str, Any]) -> Surface | None:
        """Build a Surface from either an explicit object or keyword args."""
        if config is not None and kwargs:
            raise TypeError("cannot combine config and keyword arguments")
        return cls(**kwargs) if kwargs else config


class MouseButton(enum.StrEnum):
    left = "left button"
    right = "right button"
    middle = "middle button"


class ScrollMomentum(enum.StrEnum):
    none = "none"
    began = "began"
    changed = "changed"
    ended = "ended"
    cancelled = "cancelled"
    may_begin = "may begin"
    stationary = "stationary"


@dataclasses.dataclass(frozen=True, slots=True)
class Point:
    """A screen coordinate."""

    x: int
    y: int


@dataclasses.dataclass(frozen=True, slots=True)
class Size:
    """A width/height pair."""

    width: int
    height: int


@dataclasses.dataclass(frozen=True, slots=True)
class Bounds:
    """Window bounds as (left, top, right, bottom) matching AppleScript convention."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def position(self) -> Point:
        return Point(self.left, self.top)

    @property
    def size(self) -> Size:
        return Size(self.right - self.left, self.bottom - self.top)

    @classmethod
    def from_position_size(cls, position: Point, size: Size) -> Bounds:
        return cls(
            position.x,
            position.y,
            position.x + size.width,
            position.y + size.height,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class Screen:
    """Display geometry.  *origin* is the top-left usable point; *size* is the usable area."""

    origin: Point
    size: Size

    @property
    def bounds(self) -> Bounds:
        return Bounds(
            self.origin.x,
            self.origin.y,
            self.origin.x + self.size.width,
            self.origin.y + self.size.height,
        )


class ScreenRegion(enum.Enum):
    """Named regions of a screen for window tiling."""

    left_half = "left_half"
    right_half = "right_half"
    top_half = "top_half"
    bottom_half = "bottom_half"
    top_left = "top_left"
    top_right = "top_right"
    bottom_left = "bottom_left"
    bottom_right = "bottom_right"
    left_third = "left_third"
    center_third = "center_third"
    right_third = "right_third"
    left_two_thirds = "left_two_thirds"
    right_two_thirds = "right_two_thirds"
    first_fourth = "first_fourth"
    second_fourth = "second_fourth"
    third_fourth = "third_fourth"
    last_fourth = "last_fourth"
    left_three_fourths = "left_three_fourths"
    right_three_fourths = "right_three_fourths"
    first_sixth = "first_sixth"
    second_sixth = "second_sixth"
    third_sixth = "third_sixth"
    fourth_sixth = "fourth_sixth"
    fifth_sixth = "fifth_sixth"
    last_sixth = "last_sixth"
    full = "full"

    def compute(self, screen: Screen, *, gap: int = 0) -> Bounds:
        """Compute the bounds for this region on the given screen."""
        x_frac, y_frac = _REGION_SPECS[self]
        return _compute_region(screen, gap, x_frac, y_frac)


def _compute_region(
    screen: Screen,
    gap: int,
    x_frac: tuple[float, float],
    y_frac: tuple[float, float],
) -> Bounds:
    ox, oy = screen.origin.x, screen.origin.y
    sw, sh = screen.size.width, screen.size.height
    return Bounds(
        ox + int(sw * x_frac[0]) + gap,
        oy + int(sh * y_frac[0]) + gap,
        ox + int(sw * x_frac[1]) - gap,
        oy + int(sh * y_frac[1]) - gap,
    )


_REGION_SPECS: dict[ScreenRegion, tuple[tuple[float, float], tuple[float, float]]] = {
    ScreenRegion.left_half: ((0, 0.5), (0, 1)),
    ScreenRegion.right_half: ((0.5, 1), (0, 1)),
    ScreenRegion.top_half: ((0, 1), (0, 0.5)),
    ScreenRegion.bottom_half: ((0, 1), (0.5, 1)),
    ScreenRegion.top_left: ((0, 0.5), (0, 0.5)),
    ScreenRegion.top_right: ((0.5, 1), (0, 0.5)),
    ScreenRegion.bottom_left: ((0, 0.5), (0.5, 1)),
    ScreenRegion.bottom_right: ((0.5, 1), (0.5, 1)),
    ScreenRegion.left_third: ((0, 1 / 3), (0, 1)),
    ScreenRegion.center_third: ((1 / 3, 2 / 3), (0, 1)),
    ScreenRegion.right_third: ((2 / 3, 1), (0, 1)),
    ScreenRegion.left_two_thirds: ((0, 2 / 3), (0, 1)),
    ScreenRegion.right_two_thirds: ((1 / 3, 1), (0, 1)),
    ScreenRegion.first_fourth: ((0, 0.25), (0, 1)),
    ScreenRegion.second_fourth: ((0.25, 0.5), (0, 1)),
    ScreenRegion.third_fourth: ((0.5, 0.75), (0, 1)),
    ScreenRegion.last_fourth: ((0.75, 1), (0, 1)),
    ScreenRegion.left_three_fourths: ((0, 0.75), (0, 1)),
    ScreenRegion.right_three_fourths: ((0.25, 1), (0, 1)),
    ScreenRegion.first_sixth: ((0, 1 / 6), (0, 1)),
    ScreenRegion.second_sixth: ((1 / 6, 2 / 6), (0, 1)),
    ScreenRegion.third_sixth: ((2 / 6, 3 / 6), (0, 1)),
    ScreenRegion.fourth_sixth: ((3 / 6, 4 / 6), (0, 1)),
    ScreenRegion.fifth_sixth: ((4 / 6, 5 / 6), (0, 1)),
    ScreenRegion.last_sixth: ((5 / 6, 1), (0, 1)),
    ScreenRegion.full: ((0, 1), (0, 1)),
}

# NSScreen AppleScript-ObjC scripts.  Cocoa uses bottom-left origin;
# we convert to the top-left origin used by AppleScript bounds.
_MAIN_SCREEN_SCRIPT = (
    'use framework "AppKit"\n'
    "set s to current application's NSScreen's mainScreen()\n"
    "set f to s's frame()\n"
    "set vf to s's visibleFrame()\n"
    "set screenH to item 2 of item 2 of f\n"
    "set vx to item 1 of item 1 of vf\n"
    "set vy to item 2 of item 1 of vf\n"
    "set vw to item 1 of item 2 of vf\n"
    "set vh to item 2 of item 2 of vf\n"
    "set topY to screenH - vy - vh\n"
    "return {vx, topY, vw, vh}"
)

_ALL_SCREENS_SCRIPT = (
    'use framework "AppKit"\n'
    "set mainF to current application's NSScreen's mainScreen()'s frame()\n"
    "set mainH to item 2 of item 2 of mainF\n"
    "set screenList to current application's NSScreen's screens()\n"
    "set out to {}\n"
    "repeat with s in screenList\n"
    "  set f to s's frame()\n"
    "  set vf to s's visibleFrame()\n"
    "  set screenH to item 2 of item 2 of f\n"
    "  set vx to item 1 of item 1 of vf\n"
    "  set vy to item 2 of item 1 of vf\n"
    "  set vw to item 1 of item 2 of vf\n"
    "  set vh to item 2 of item 2 of vf\n"
    "  set topY to screenH - vy - vh\n"
    '  set end of out to ("" & vx & "," & topY & "," & vw & "," & vh)\n'
    "end repeat\n"
    'set AppleScript\'s text item delimiters to ";"\n'
    "return out as text"
)


def _auto_columns(n: int) -> int:
    """Pick a sensible column count for *n* windows."""
    if n <= 2:
        return n
    if n <= 4:
        return 2
    if n <= 6:
        return 3
    return int(n**0.5 + 0.5)


def _osascript(source: str) -> str:
    """Execute an AppleScript source string and return its stdout."""
    proc = subprocess.run(
        ["/usr/bin/osascript"],
        input=source,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        msg = proc.stderr.strip()
        match = re.search(r"execution error: (.+?) \((-?\d+)\)", msg)
        if match:
            raise GhosttyError(match.group(1), int(match.group(2)))
        raise GhosttyError(msg or "unknown AppleScript error")
    return proc.stdout.strip()


def _escape(s: str) -> str:
    """Escape a string for embedding in an AppleScript double-quoted literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')
