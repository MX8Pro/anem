# settings_manager.py
# مسؤول عن تحميل وحفظ إعدادات التطبيق من وإلى ملف JSON.

import json
import os
from typing import Tuple, Any # Added for type hinting

# --- Local Imports ---
# Import constants after defining defaults to avoid circular dependency issues if any
from constants import SETTINGS_FILE, DEFAULT_COOKIE_VALUE, DEFAULT_DOWNLOADS_PATH

# --- Default Values ---
# Moved default values here to be defined before use
DEFAULT_ENTRY_FONT_FAMILY = "Segoe UI"
DEFAULT_ENTRY_FONT_SIZE = 13
DEFAULT_ENTRY_FONT_WEIGHT = "bold"
DEFAULT_STATUS_FONT_FAMILY = "Tahoma"
DEFAULT_STATUS_FONT_SIZE = 11
DEFAULT_STATUS_FONT_WEIGHT = "bold"
DEFAULT_AUTO_DELETE_ENABLED = False
DEFAULT_AUTO_DELETE_DAYS = 30
DEFAULT_AUTO_PRINT_EXTEND_DOWNLOAD = False
DEFAULT_STATUS_AREA_VISIBLE = False # Default is hidden
DEFAULT_UI_THEME = "light"  # UI theme preference (light/dark)

# --- Global Variables loaded/saved by this manager ---
# These act as a cache for the loaded settings.
# Initialize with default values. load_settings() will overwrite them if a file exists.
app_settings: dict[str, Any] = {
    "cookie": DEFAULT_COOKIE_VALUE,
    "default_printer": None,
    "default_save_path": DEFAULT_DOWNLOADS_PATH,
    "last_nin": "",
    "last_numero": "",
    "entry_font_family": DEFAULT_ENTRY_FONT_FAMILY,
    "entry_font_size": DEFAULT_ENTRY_FONT_SIZE,
    "entry_font_weight": DEFAULT_ENTRY_FONT_WEIGHT,
    "status_font_family": DEFAULT_STATUS_FONT_FAMILY,
    "status_font_size": DEFAULT_STATUS_FONT_SIZE,
    "status_font_weight": DEFAULT_STATUS_FONT_WEIGHT,
    "auto_delete_enabled": DEFAULT_AUTO_DELETE_ENABLED,
    "auto_delete_days": DEFAULT_AUTO_DELETE_DAYS,
    "auto_print_extend_download": DEFAULT_AUTO_PRINT_EXTEND_DOWNLOAD,
    "status_area_visible": DEFAULT_STATUS_AREA_VISIBLE,
    "ui_theme": DEFAULT_UI_THEME,
}


# --- Function to Load Settings ---
def load_settings():
    """Loads settings from the JSON file into the app_settings dictionary."""
    global app_settings
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                # Update cache, falling back to defaults if keys are missing
                # Use .get() for safe access
                app_settings["cookie"] = loaded_data.get("cookie", DEFAULT_COOKIE_VALUE)
                app_settings["default_printer"] = loaded_data.get("default_printer", None)
                app_settings["default_save_path"] = loaded_data.get("default_save_path", DEFAULT_DOWNLOADS_PATH)
                app_settings["last_nin"] = loaded_data.get("last_nin", "")
                app_settings["last_numero"] = loaded_data.get("last_numero", "")
                # --- Load Font Settings ---
                app_settings["entry_font_family"] = loaded_data.get("entry_font_family", DEFAULT_ENTRY_FONT_FAMILY)
                app_settings["entry_font_size"] = loaded_data.get("entry_font_size", DEFAULT_ENTRY_FONT_SIZE)
                app_settings["entry_font_weight"] = loaded_data.get("entry_font_weight", DEFAULT_ENTRY_FONT_WEIGHT)
                app_settings["status_font_family"] = loaded_data.get("status_font_family", DEFAULT_STATUS_FONT_FAMILY)
                app_settings["status_font_size"] = loaded_data.get("status_font_size", DEFAULT_STATUS_FONT_SIZE)
                app_settings["status_font_weight"] = loaded_data.get("status_font_weight", DEFAULT_STATUS_FONT_WEIGHT)
                # --- Load Advanced Settings ---
                app_settings["auto_delete_enabled"] = loaded_data.get("auto_delete_enabled", DEFAULT_AUTO_DELETE_ENABLED)
                app_settings["auto_delete_days"] = loaded_data.get("auto_delete_days", DEFAULT_AUTO_DELETE_DAYS)
                app_settings["auto_print_extend_download"] = loaded_data.get("auto_print_extend_download", DEFAULT_AUTO_PRINT_EXTEND_DOWNLOAD)
                # --- Load Status Area Visibility ---
                app_settings["status_area_visible"] = loaded_data.get("status_area_visible", DEFAULT_STATUS_AREA_VISIBLE)
                # --- Load UI Theme ---
                app_settings["ui_theme"] = loaded_data.get("ui_theme", DEFAULT_UI_THEME)

                print(f"Settings loaded from {SETTINGS_FILE}")
        else:
            print(f"Settings file not found at {SETTINGS_FILE}, using defaults.")
            # If file doesn't exist, app_settings already holds the defaults initialized above.
            # No need to reset them here unless the defaults themselves changed.

    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"Error loading settings from {SETTINGS_FILE}: {e}. Using defaults.")
        # Reset to defaults on error to ensure a clean state
        app_settings = {
            "cookie": DEFAULT_COOKIE_VALUE,
            "default_printer": None,
            "default_save_path": DEFAULT_DOWNLOADS_PATH,
            "last_nin": "",
            "last_numero": "",
            "entry_font_family": DEFAULT_ENTRY_FONT_FAMILY,
            "entry_font_size": DEFAULT_ENTRY_FONT_SIZE,
            "entry_font_weight": DEFAULT_ENTRY_FONT_WEIGHT,
            "status_font_family": DEFAULT_STATUS_FONT_FAMILY,
            "status_font_size": DEFAULT_STATUS_FONT_SIZE,
            "status_font_weight": DEFAULT_STATUS_FONT_WEIGHT,
            "auto_delete_enabled": DEFAULT_AUTO_DELETE_ENABLED,
            "auto_delete_days": DEFAULT_AUTO_DELETE_DAYS,
            "auto_print_extend_download": DEFAULT_AUTO_PRINT_EXTEND_DOWNLOAD,
            "status_area_visible": DEFAULT_STATUS_AREA_VISIBLE,
        }

# --- Function to Save Settings ---
def save_settings():
    """Saves the current app_settings dictionary to the JSON file."""
    global app_settings
    try:
        # Ensure the directory exists before writing
        settings_dir = os.path.dirname(SETTINGS_FILE)
        if not os.path.exists(settings_dir):
            os.makedirs(settings_dir)
            print(f"Created settings directory: {settings_dir}")

        # --- Validate data types before saving ---
        # Ensure boolean values are actually boolean
        app_settings["auto_delete_enabled"] = bool(app_settings.get("auto_delete_enabled", DEFAULT_AUTO_DELETE_ENABLED))
        app_settings["auto_print_extend_download"] = bool(app_settings.get("auto_print_extend_download", DEFAULT_AUTO_PRINT_EXTEND_DOWNLOAD))
        app_settings["status_area_visible"] = bool(app_settings.get("status_area_visible", DEFAULT_STATUS_AREA_VISIBLE))

        # Ensure integer values are integers
        try:
            days = int(app_settings.get("auto_delete_days", DEFAULT_AUTO_DELETE_DAYS))
            app_settings["auto_delete_days"] = days if days > 0 else DEFAULT_AUTO_DELETE_DAYS
        except (ValueError, TypeError):
            app_settings["auto_delete_days"] = DEFAULT_AUTO_DELETE_DAYS

        try:
            app_settings["entry_font_size"] = int(app_settings.get("entry_font_size", DEFAULT_ENTRY_FONT_SIZE))
        except (ValueError, TypeError):
            app_settings["entry_font_size"] = DEFAULT_ENTRY_FONT_SIZE

        try:
            app_settings["status_font_size"] = int(app_settings.get("status_font_size", DEFAULT_STATUS_FONT_SIZE))
        except (ValueError, TypeError):
            app_settings["status_font_size"] = DEFAULT_STATUS_FONT_SIZE

        # Ensure string values are strings
        app_settings["cookie"] = str(app_settings.get("cookie", DEFAULT_COOKIE_VALUE))
        app_settings["default_save_path"] = str(app_settings.get("default_save_path", DEFAULT_DOWNLOADS_PATH))
        app_settings["last_nin"] = str(app_settings.get("last_nin", ""))
        app_settings["last_numero"] = str(app_settings.get("last_numero", ""))
        app_settings["entry_font_family"] = str(app_settings.get("entry_font_family", DEFAULT_ENTRY_FONT_FAMILY))
        app_settings["entry_font_weight"] = str(app_settings.get("entry_font_weight", DEFAULT_ENTRY_FONT_WEIGHT))
        app_settings["status_font_family"] = str(app_settings.get("status_font_family", DEFAULT_STATUS_FONT_FAMILY))
        app_settings["status_font_weight"] = str(app_settings.get("status_font_weight", DEFAULT_STATUS_FONT_WEIGHT))
        # Allow default_printer to be None or string
        printer = app_settings.get("default_printer")
        app_settings["default_printer"] = str(printer) if printer is not None else None


        # --- Create a temporary dictionary for saving (optional, but clean) ---
        settings_to_save = app_settings.copy()
        # Example if you wanted to exclude something temporarily:
        # if "some_temporary_key" in settings_to_save:
        #     del settings_to_save["some_temporary_key"]

        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_to_save, f, indent=4, ensure_ascii=False)
        print(f"Settings saved to {SETTINGS_FILE}")
    except Exception as e:
        print(f"Error saving settings to {SETTINGS_FILE}: {e}")

# --- Functions to Get/Set specific settings ---
# These functions interact with the cached 'app_settings' dictionary.
# Call save_settings() after using a set function if persistence is needed immediately.

def get_cookie() -> str:
    return app_settings.get("cookie", DEFAULT_COOKIE_VALUE)

def set_cookie(new_cookie: str | None):
    global app_settings
    app_settings["cookie"] = new_cookie.strip() if new_cookie else DEFAULT_COOKIE_VALUE

def get_default_printer() -> str | None:
    return app_settings.get("default_printer", None)

def set_default_printer(printer_name: str | None):
    global app_settings
    app_settings["default_printer"] = printer_name

def get_default_save_path() -> str:
    return app_settings.get("default_save_path", DEFAULT_DOWNLOADS_PATH)

def set_default_save_path(path: str | None):
    global app_settings
    app_settings["default_save_path"] = path if path else DEFAULT_DOWNLOADS_PATH

def get_last_nin() -> str:
    return app_settings.get("last_nin", "")

def set_last_nin(nin: str | None):
    global app_settings
    app_settings["last_nin"] = nin if nin else ""

def get_last_numero() -> str:
    return app_settings.get("last_numero", "")

def set_last_numero(numero: str | None):
    global app_settings
    app_settings["last_numero"] = numero if numero else ""

# --- Font Settings Getters/Setters ---
def get_entry_font_config() -> Tuple[str, int, str]:
    """Returns the entry font configuration as a tuple (family, size, weight)."""
    return (
        app_settings.get("entry_font_family", DEFAULT_ENTRY_FONT_FAMILY),
        app_settings.get("entry_font_size", DEFAULT_ENTRY_FONT_SIZE),
        app_settings.get("entry_font_weight", DEFAULT_ENTRY_FONT_WEIGHT)
    )

def set_entry_font_config(family: str, size: int, weight: str):
    """Sets the entry font configuration."""
    global app_settings
    app_settings["entry_font_family"] = family
    app_settings["entry_font_size"] = size
    app_settings["entry_font_weight"] = weight

def get_status_font_config() -> Tuple[str, int, str]:
    """Returns the status font configuration as a tuple (family, size, weight)."""
    return (
        app_settings.get("status_font_family", DEFAULT_STATUS_FONT_FAMILY),
        app_settings.get("status_font_size", DEFAULT_STATUS_FONT_SIZE),
        app_settings.get("status_font_weight", DEFAULT_STATUS_FONT_WEIGHT)
    )

def set_status_font_config(family: str, size: int, weight: str):
    """Sets the status font configuration."""
    global app_settings
    app_settings["status_font_family"] = family
    app_settings["status_font_size"] = size
    app_settings["status_font_weight"] = weight

# --- Advanced Settings Getters/Setters ---

def get_auto_delete_enabled() -> bool:
    """Gets the auto delete enabled status."""
    return app_settings.get("auto_delete_enabled", DEFAULT_AUTO_DELETE_ENABLED)

def set_auto_delete_enabled(enabled: bool):
    """Sets the auto delete enabled status."""
    global app_settings
    app_settings["auto_delete_enabled"] = bool(enabled)

def get_auto_delete_days() -> int:
    """Gets the number of days for auto deletion."""
    return app_settings.get("auto_delete_days", DEFAULT_AUTO_DELETE_DAYS)

def set_auto_delete_days(days: int):
    """Sets the number of days for auto deletion."""
    global app_settings
    try:
        app_settings["auto_delete_days"] = int(days) if int(days) > 0 else DEFAULT_AUTO_DELETE_DAYS
    except (ValueError, TypeError):
        app_settings["auto_delete_days"] = DEFAULT_AUTO_DELETE_DAYS

def get_auto_print_extend_download() -> bool:
    """Gets the auto print status for extend+download."""
    return app_settings.get("auto_print_extend_download", DEFAULT_AUTO_PRINT_EXTEND_DOWNLOAD)

def set_auto_print_extend_download(enabled: bool):
    """Sets the auto print status for extend+download."""
    global app_settings
    app_settings["auto_print_extend_download"] = bool(enabled)

# --- Status Area Visibility Getters/Setters ---

def get_status_area_visible() -> bool:
    """Gets the visibility status of the status area."""
    return app_settings.get("status_area_visible", DEFAULT_STATUS_AREA_VISIBLE)

def set_status_area_visible(visible: bool):
    """Sets the visibility status of the status area."""
    global app_settings
    app_settings["status_area_visible"] = bool(visible)


# --- UI Theme Getters/Setters ---
def get_ui_theme() -> str:
    """Gets the UI theme preference (e.g., 'light' or 'dark')."""
    return app_settings.get("ui_theme", DEFAULT_UI_THEME)

def set_ui_theme(theme: str):
    """Sets the UI theme preference."""
    global app_settings
    theme = (theme or "").strip().lower()
    if theme not in ("light", "dark"):
        theme = DEFAULT_UI_THEME
    app_settings["ui_theme"] = theme


# --- Load settings on module import ---
# Ensure this runs when the module is first imported
load_settings()
