# ghosttpy

A Python interface for scripting [Ghostty](https://ghostty.org) on macOS via AppleScript.

## Requirements

- macOS
- Python >= 3.13
- [Ghostty](https://ghostty.org) >= 1.3.0 (when AppleScript support was introduced)

## Install

```
pip install ghosttpy
```

Or with [uv](https://docs.astral.sh/uv/):

```
uv add ghosttpy
```

## Quick start

```python
from ghosttpy import Ghostty

g = Ghostty()
w = g.new_window(working_directory="/tmp")
term = w.selected_tab.focused_terminal
term.input("echo hello\n")
```

Accessing `w.name` or `term.working_directory` queries Ghostty to read the current state.

## Object model

Ghostty's scripting hierarchy is `Ghostty` > `Window` > `Tab` > `Terminal`. Each object has a stable `id` and can be compared or used in sets.

```python
g = Ghostty()

g.windows           # all open windows
g.front_window      # the frontmost window
g.name              # "Ghostty"
g.version           # e.g. "1.3.1"
g.frontmost         # True if Ghostty is the active app
g.is_running        # True if the Ghostty process is running

w = g.front_window
w.tabs              # tabs in this window
w.terminals         # all terminals across all tabs
w.selected_tab      # the active tab

tab = w.selected_tab
tab.index           # 1-based position in the tab bar
tab.selected        # True if this tab is active
tab.focused_terminal
tab.terminals       # terminals (split panes) in this tab

term = tab.focused_terminal
term.name
term.working_directory
```

## Creating windows, tabs, and splits

```python
w = g.new_window()
tab = w.new_tab()
right = term.split("right")   # returns the new Terminal
below = term.split("down")
```

Split directions are `"right"`, `"left"`, `"down"`, and `"up"` (or use the `SplitDirection` enum).

Resize or equalize splits:

```python
term.resize_split("left", 10)   # grow 10 cells to the left
term.resize_split("down")       # grow 1 cell downward (default)
term.equalize_splits()          # equalize all splits in the tab
tab.equalize_splits()           # convenience — delegates to focused terminal
```

Close any object with `.close()`. Bring a window to the front with `w.activate()`, select a tab with `tab.select()`, or focus a terminal with `term.focus()`.

## Configuration

Windows, tabs, and splits accept keyword arguments to configure the terminal surface:

```python
w = g.new_window(font_size=14.0, working_directory="/tmp")
tab = w.new_tab(command="/bin/bash", environment={"EDITOR": "vim"})
new_term = term.split("right", initial_input="ls\n", wait_after_command=True)
```

Available options: `font_size`, `working_directory`, `command`, `initial_input`, `wait_after_command`, `environment`.

To reuse the same configuration across multiple calls, pass a `Surface` object:

```python
from ghosttpy import Surface

cfg = Surface(font_size=14.0, working_directory="/tmp")
w1 = g.new_window(config=cfg)
w2 = g.new_window(config=cfg)
```

## Terminal input

`input()` sends text as if pasted. `send_key()` sends individual key events.

```python
term.input("ls -la\n")
term.send_key("c", modifiers="control")
term.send_key("enter")
term.send_key("a", modifiers=["control", "shift"], action="release")
```

`perform()` executes a [Ghostty action](https://ghostty.org/docs/config/keybind/reference) string and returns whether it succeeded:

```python
term.perform("copy_to_clipboard")
term.perform("reset")
```

Mouse events are also available:

```python
term.send_mouse_position(x=100.0, y=200.0)
term.send_mouse_button("left button")
term.send_mouse_scroll(x=0, y=-3.0, precision=True)
```

## Window management

Read or set a window's geometry:

```python
from ghosttpy import Bounds, Point, Size

w.bounds                        # Bounds(left, top, right, bottom)
w.bounds = Bounds(0, 0, 960, 540)

w.position                      # Point(x, y)
w.size                          # Size(width, height)

w.move_to(100, 100)
w.resize_to(800, 600)
```

### Tiling

Tile a window into a predefined screen region with `ScreenRegion`:

```python
from ghosttpy import ScreenRegion

w.tile(ScreenRegion.left_half)
w.tile(ScreenRegion.top_right, gap=10)
```

Available regions:

| Halves | Quarters | Thirds | Fourths | Sixths |
|--------|----------|--------|---------|--------|
| `left_half` | `top_left` | `left_third` | `first_fourth` | `first_sixth` |
| `right_half` | `top_right` | `center_third` | `second_fourth` | `second_sixth` |
| `top_half` | `bottom_left` | `right_third` | `third_fourth` | `third_sixth` |
| `bottom_half` | `bottom_right` | `left_two_thirds` | `last_fourth` | `fourth_sixth` |
| | | `right_two_thirds` | `left_three_fourths` | `fifth_sixth` |
| | | | `right_three_fourths` | `last_sixth` |

There is also `full`, which is equivalent to `maximize()`.

### Maximize, center, and grid

```python
w.maximize()
w.center()

# Tile all windows in an auto-sized grid
g.tile_windows()

# Tile specific windows in a 3-column grid with gaps
g.tile_windows([w1, w2, w3], columns=3, gap=10)
```

All layout methods accept an optional `screen` parameter. When omitted, they use the main display.

## Screen geometry

```python
scr = g.main_screen()      # Screen for the primary display
scr.origin                  # Point -- top-left corner of usable area
scr.size                    # Size -- usable width and height (excludes menu bar and Dock)
scr.bounds                  # Bounds -- computed from origin and size

all_screens = g.screens()   # list[Screen] for every display
```

## Raw AppleScript

For anything the library doesn't wrap, two escape hatches are available:

```python
# Runs inside `tell application "Ghostty" ... end tell`
g.tell('get name of front window')

# Runs raw AppleScript with no wrapping
g.run('tell application "Finder" to get name of front window')
```

## Error handling

Failed AppleScript calls raise `GhosttyError`, which includes the error message and an optional numeric `code`:

```python
from ghosttpy import GhosttyError

try:
    term.perform("nonexistent_action")
except GhosttyError as e:
    print(e, e.code)
```

## Enums

String arguments like `"right"`, `"press"`, and `"left button"` are accepted everywhere, but typed enum alternatives are available if you prefer:

- `SplitDirection` -- `right`, `left`, `down`, `up`
- `InputAction` -- `press`, `release`
- `MouseButton` -- `left`, `right`, `middle`
- `ScrollMomentum` -- `none`, `began`, `changed`, `ended`, `cancelled`, `may_begin`, `stationary`

## Examples

The [`examples/`](examples/) directory contains a few demo programs:

| Script | Description |
|--------|-------------|
| [`tile_columns.py`](examples/tile_columns.py) | Tile open windows into equal columns |
| [`dev_layout.py`](examples/dev_layout.py) | Create a development workspace with splits |
| [`broadcast.py`](examples/broadcast.py) | Broadcast input to multiple terminal panes |
| [`window_info.py`](examples/window_info.py) | Print a tree of windows, tabs, and terminals |

Run any example with `--help` for options, e.g.:

```
python examples/tile_columns.py --columns 3 --gap 10
```
