# anem

Modern Tkinter application styled with [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap).

## Requirements

- Python 3
- `ttkbootstrap` (optional but recommended for modern theme)

Install dependencies:

```bash
pip install ttkbootstrap
```

## Running

```bash
python main_app.py
```

The interface supports light and dark themes and uses Bootstrap-inspired styling for a more professional look.
The latest redesign introduces a sidebar-driven layout, animated status updates, and a collapsible results panel for a more dynamic experience.

### Fonts

The UI attempts to load the bundled [Cairo](https://fonts.google.com/specimen/Cairo) font from `assets/fonts/Cairo-Regular.ttf` on startup. This allows the application to use Cairo without requiring it to be installed on the system. If the font cannot be loaded, the interface gracefully falls back to standard system fonts.
