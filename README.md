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

The interface supports light and dark themes and uses a refined corporate palette for a professional feel.
The latest redesign introduces an accent-colored top bar with a quick theme toggle, a sidebar-driven layout, animated status updates, and a collapsible results panel for a modern, spacious experience.

### Fonts

Any `.ttf` files placed under `assets/fonts` are registered automatically when the application starts. If Cairo or Tajawal files are present, that family becomes the interface default so the program can use the custom fonts even when packaged as an `.exe`. Should loading fail, the UI quietly falls back to the system fonts.

### Sounds

Place audio clips under `assets/sound` named for their purpose (e.g., `success`, `warning`, `error`, `info`).
The application looks for a matching file with a `.wav`, `.mp3`, or `.ogg` extension and uses it when present.

If a file is missing the corresponding event simply plays without sound. WAV files use the Windows audio API when possible, while other formats fall back to `playsound`. The PyInstaller build bundles any files in `assets/sound` automatically.
If the folder contains no audio files, the build skips that directory so packaging still succeeds.
