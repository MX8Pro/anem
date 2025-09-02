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

Any `.ttf` files placed under `assets/fonts` are registered automatically when the application starts. If Cairo or Tajawal files are present, that family becomes the interface default so the program can use the custom fonts even when packaged as an `.exe`. Should loading fail, the UI quietly falls back to the system fonts.
