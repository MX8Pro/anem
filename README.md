# anem

Modern Tkinter application styled with [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap).

## Requirements

- Python 3
- `ttkbootstrap` (required for modern theme)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

```bash
python main_app.py
```

The interface supports light and dark themes and uses Bootstrap-inspired styling for a more professional look.
The latest redesign introduces a sidebar-driven layout, animated status updates, and a collapsible results panel for a more dynamic experience.

### Fonts

The UI loads the bundled [Cairo](https://fonts.google.com/specimen/Cairo) font from `assets/fonts/Cairo-Regular.ttf` at startup and applies it to all widgets. If loading fails, standard system fonts are used.
