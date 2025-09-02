# gui_utils.py
# يحتوي على دوال مساعدة عامة لواجهة المستخدم الرسومية.
# *** تم التعديل: تصحيح النص المعروض لحالة الموعد المحجوز مسبقًا ***
# *** تم التصحيح: تعريف الألوان محليًا بدلاً من استدعائها من settings_manager ***
# *** تم التعديل: دالة لتحديث ليبل حالة المواعيد ليشمل حالة منحة البطالة ***
# *** تمت الإضافة: دالة لسؤال المستخدم وفتح متصفح حجز المواعيد مع نسخ البيانات ***

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Menu, font as tkFont
from tkinter import scrolledtext # Import scrolledtext directly
import datetime
import socket # For internet check
import sys # For error logging
import os # Needed for path operations in select_default_save_path_setting
from tkinter import filedialog # Needed for save/printer dialogs
import time # For status bar reset timer
import webbrowser # *** تمت الإضافة: لفتح المتصفح ***
from typing import Optional, Any # For type hinting, Added Any

# --- Local Imports ---
import settings_manager # Import settings manager

# --- Global variable to store last error details ---
LAST_ERROR_DETAILS = {"title": "", "message": ""}
# --- Global variable for status bar reset timer ---
status_bar_reset_timer = None

# --- Color Palette (Mirrored from main_app.py for tag configuration) ---
COLOR_PRIMARY_BG = "#f5f7fb"
COLOR_SECONDARY_BG = "#ffffff"
COLOR_TEXT = "#212529"
COLOR_TEXT_SECONDARY = "#6c757d"
COLOR_ACCENT = "#0d6efd"
COLOR_ACCENT_DARK = "#0a58ca"
COLOR_SUCCESS = "#198754"
COLOR_SUCCESS_BG = "#d1e7dd"  # Lighter green background
COLOR_SUCCESS_FG = "#0f5132"  # Darker green text
COLOR_WARNING = "#d39e00"
COLOR_WARNING_BG = "#fff3cd"  # Lighter yellow background
COLOR_WARNING_FG = "#664d03"  # Darker yellow text
COLOR_ERROR = "#dc3545"
COLOR_ERROR_BG = "#f8d7da"  # Lighter red background
COLOR_ERROR_FG = "#842029"  # Darker red text
COLOR_INFO_BG = "#cff4fc"
COLOR_API_BG = "#f1f3f5"
COLOR_BORDER = "#dee2e6"
COLOR_ALLOCATION_HEADER_BG = "#e0e0e0"
COLOR_STATUS_DEFAULT_BG = '#e9ecef'
# --------------------------------------------------------------------

# --- Theme palette update ---
def set_theme_palette(palette: dict):
    """Updates module-level color constants to match the given palette.
    Expected keys: COLOR_PRIMARY_BG, COLOR_SECONDARY_BG, COLOR_TEXT, COLOR_TEXT_SECONDARY,
    COLOR_ACCENT, COLOR_ACCENT_DARK, COLOR_SUCCESS, COLOR_SUCCESS_BG, COLOR_SUCCESS_FG,
    COLOR_WARNING, COLOR_WARNING_BG, COLOR_WARNING_FG, COLOR_ERROR, COLOR_ERROR_BG, COLOR_ERROR_FG,
    COLOR_INFO_BG, COLOR_API_BG, COLOR_BORDER, COLOR_ALLOCATION_HEADER_BG, COLOR_STATUS_DEFAULT_BG
    """
    globals_map = globals()
    for key, value in palette.items():
        if key in globals_map:
            globals_map[key] = value
    # No immediate UI updates here; callers should reconfigure tags/styles as needed.


# --- Lightweight Tooltip Helper ---
class _Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind('<Enter>', self.show)
        widget.bind('<Leave>', self.hide)

    def show(self, event=None):
        if self.tipwindow or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self.tipwindow = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            frame = tk.Frame(tw, background=COLOR_SECONDARY_BG, borderwidth=1, relief='solid')
            label = tk.Label(frame, text=self.text, background=COLOR_SECONDARY_BG, foreground=COLOR_TEXT, justify=tk.RIGHT, padx=6, pady=3)
            label.pack()
            frame.pack()
        except tk.TclError:
            pass

    def hide(self, event=None):
        if self.tipwindow:
            try:
                self.tipwindow.destroy()
            except tk.TclError:
                pass
            self.tipwindow = None

def attach_tooltip(widget, text: str):
    """Attach a small tooltip to a widget."""
    try:
        _Tooltip(widget, text)
    except Exception as e:
        print(f"Tooltip attach failed: {e}")


def add_hover_cursor(widget):
    """Show a hand cursor when hovering over a widget."""
    try:
        widget.bind("<Enter>", lambda e: widget.configure(cursor="hand2"))
        widget.bind("<Leave>", lambda e: widget.configure(cursor=""))
    except Exception as e:
        print(f"Hover cursor binding failed: {e}")


# --- Toast Notification ---
def show_toast(root, text: str, duration_ms: int = 2500):
    """Shows a small transient toast message at bottom-right of the root window."""
    if not root or not root.winfo_exists():
        return
    def _show():
        try:
            toast = tk.Toplevel(root)
            toast.wm_overrideredirect(True)
            toast.attributes('-topmost', True)
            frame = tk.Frame(toast, background=COLOR_SECONDARY_BG, borderwidth=1, relief='solid')
            label = tk.Label(frame, text=text, background=COLOR_SECONDARY_BG, foreground=COLOR_TEXT, padx=10, pady=6, justify=tk.RIGHT)
            label.pack()
            frame.pack()

            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            tw = toast.winfo_reqwidth()
            th = toast.winfo_reqheight()
            x = rx + rw - tw - 20
            y = ry + rh - th - 40
            toast.geometry(f"+{x}+{y}")
            root.after(duration_ms, lambda: (toast.destroy() if toast and toast.winfo_exists() else None))
        except tk.TclError:
            pass
    schedule_gui_update(root, _show)

# --- GUI Update Function (Thread-safe) ---
def schedule_gui_update(root, func, *args, **kwargs):
    """Schedules a function to be run in the main GUI thread, passing args and kwargs."""
    if root and isinstance(root, (tk.Tk, tk.Toplevel)) and root.winfo_exists():
        try:
            root.after(0, lambda f=func, a=args, k=kwargs: f(*a, **k))
        except tk.TclError as e:
            print(f"TclError scheduling GUI update (window likely destroyed): {e}")

# --- Centering Dialog Utility ---
def center_dialog(dialog, parent):
    """Centers a Toplevel dialog over its parent window."""
    if not dialog or not dialog.winfo_exists() or not parent or not parent.winfo_exists():
        print("Warning: Cannot center dialog, window(s) destroyed.")
        return
    try:
        dialog.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        x = max(0, x)
        y = max(0, y)
        dialog.geometry(f"+{x}+{y}")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.focus_force()
    except tk.TclError as e:
        print(f"TclError centering dialog: {e}")


# --- Function to set widget state (Thread-safe) ---
def set_widget_state(root, widget, state):
    """Sets the state (e.g., tk.NORMAL, tk.DISABLED) of a widget safely."""
    def _set_state(w, s):
        if w and w.winfo_exists():
            try:
                if isinstance(w, ttk.Combobox) and s == 'readonly':
                    w.config(state=s)
                elif isinstance(w, (tk.Text, scrolledtext.ScrolledText)):
                     w.config(state=tk.NORMAL if s == tk.NORMAL else tk.DISABLED)
                else:
                    w.config(state=s)
            except tk.TclError as e:
                print(f"TclError setting widget state for {w}: {e}")
            except Exception as e:
                print(f"Unexpected error setting widget state for {w}: {e}")
    schedule_gui_update(root, _set_state, widget, state)

# --- Function to show widget using grid (Thread-safe) ---
def show_widget(root, widget, **grid_options):
    """Shows a widget using grid layout manager safely."""
    def _show(w, options):
        if w and w.winfo_exists():
            try:
                if not w.winfo_viewable():
                    w.grid(**options)
            except tk.TclError as e:
                print(f"TclError showing widget {w} with grid: {e}")
            except Exception as e:
                print(f"Unexpected error showing widget {w} with grid: {e}")
    schedule_gui_update(root, _show, widget, grid_options)

# --- Function to hide widget using grid (Thread-safe) ---
def hide_widget(root, widget):
    """Hides a widget managed by grid layout manager safely."""
    def _hide(w):
        if w and w.winfo_exists():
            try:
                if w.winfo_manager() == 'grid':
                    w.grid_remove()
            except tk.TclError as e:
                print(f"TclError hiding widget {w} with grid: {e}")
            except Exception as e:
                print(f"Unexpected error hiding widget {w} with grid: {e}")
    schedule_gui_update(root, _hide, widget)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip('#')
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _fade_tag(widget, tag, start_color, end_color, start_idx, end_idx, steps: int = 10, delay: int = 30):
    """Gradually transitions a tag's foreground from start_color to end_color."""
    start_rgb = _hex_to_rgb(start_color)
    end_rgb = _hex_to_rgb(end_color)
    delta = [(e - s) / steps for s, e in zip(start_rgb, end_rgb)]

    def _step(i: int = 0):
        if not widget.winfo_exists():
            return
        rgb = [int(start_rgb[j] + delta[j] * i) for j in range(3)]
        widget.tag_configure(tag, foreground=_rgb_to_hex(tuple(rgb)))
        if i < steps:
            widget.after(delay, _step, i + 1)
        else:
            widget.tag_remove(tag, start_idx, end_idx)

    _step()


# --- Function to enable/disable buttons ---
def set_buttons_state(root, state, buttons):
    """Sets the state (normal/disabled) of a list of buttons (thread-safe)."""
    for button in buttons:
        set_widget_state(root, button, state)


# --- Function to Restore Button State After API Call ---
def restore_button_state(root, buttons_list, clicked_button, original_text, cancel_button=None):
    """Restores the state of all buttons, the original text of the clicked button,
       and hides the cancel button if provided."""
    def _restore(all_buttons, active_button, text_to_restore, cancel_btn):
        is_batch_mode = False
        if hasattr(root, 'batch_mode_active') and isinstance(root.batch_mode_active, tk.BooleanVar):
            try:
                is_batch_mode = root.batch_mode_active.get()
            except tk.TclError:
                print("Warning: TclError getting batch_mode_active state in restore_button_state.")
                is_batch_mode = False

        if not is_batch_mode:
            for button in all_buttons:
                if button and button.winfo_exists():
                    set_widget_state(root, button, tk.NORMAL)

        if active_button and active_button.winfo_exists():
            try:
                active_button.config(text=text_to_restore)
            except tk.TclError as e:
                print(f"TclError restoring button text: {e}")
            except Exception as e:
                print(f"Unexpected error restoring button text: {e}")

        if cancel_btn and cancel_btn.winfo_exists():
            hide_widget(root, cancel_btn)

    schedule_gui_update(root, _restore, buttons_list, clicked_button, original_text, cancel_button)


# --- Function to update status text area (Thread-safe) ---
def update_status_text(root, status_text_widget, text, clear=False, tags=None, add_newline=True):
    """Updates the status text area safely from any thread, adding icons based on tags."""
    def _update(widget, text_content, clear_flag, tag_list, newline_flag):
        if not widget or not widget.winfo_exists():
            print("Warning: Status text widget does not exist in _update.")
            return

        current_tags = tag_list if isinstance(tag_list, (list, tuple)) else (tag_list,) if tag_list else ()
        final_tags = list(current_tags)

        icon = ""
        msg_type_for_statusbar = 'info'
        # Prioritize more specific tags first
        if "appointment_error" in final_tags or "api_error" in final_tags or "error" in final_tags or "allocation_error" in final_tags or "allocation_control_fail" in final_tags or "batch_summary_error" in final_tags:
            icon = "❌ "
            msg_type_for_statusbar = 'error'
        elif "appointment_unavailable" in final_tags or "api_warning" in final_tags or "warning" in final_tags or "allocation_warning" in final_tags or "batch_summary_warning" in final_tags:
            icon = "⚠️ "
            msg_type_for_statusbar = 'warning'
        elif "appointment_available" in final_tags or "api_success" in final_tags or "success" in final_tags or "allocation_success" in final_tags or "allocation_control_success" in final_tags or "batch_summary_success" in final_tags:
            icon = "✅ "
            msg_type_for_statusbar = 'success'
        elif "api_start" in final_tags:
            icon = "🚀 "
            msg_type_for_statusbar = 'info'
        elif "allocation_note" in final_tags:
            icon = "📝 "
            msg_type_for_statusbar = 'info'
        elif "api_info" in final_tags:
            icon = "⏳ "
            msg_type_for_statusbar = 'info'
        elif "api_retry" in final_tags:
             icon = "🔁 "
             msg_type_for_statusbar = 'warning'
        elif "filepath" in final_tags:
             icon = "💾 "
             msg_type_for_statusbar = 'info'
        elif "batch_summary" in final_tags:
             icon = "🏁 "
             msg_type_for_statusbar = 'info'
        elif "info" in final_tags:
            icon = "ℹ️ "
            msg_type_for_statusbar = 'info'
        elif "🖨️" in text_content:
             icon = "🖨️ "
             text_content = text_content.replace("🖨️","").strip()
             msg_type_for_statusbar = 'info'
        elif "📂" in text_content:
             icon = "📂 "
             text_content = text_content.replace("📂","").strip()
             msg_type_for_statusbar = 'info'
        elif "🗑️" in text_content:
             icon = "🗑️ "
             text_content = text_content.replace("🗑️","").strip()
             msg_type_for_statusbar = 'info'
        elif "🧹" in text_content:
             icon = "🧹 "
             text_content = text_content.replace("🧹","").strip()
             msg_type_for_statusbar = 'info'


        if not any(t in ["separator", "allocation_header", "center"] for t in final_tags) and any('\u0600' <= char <= '\u06FF' for char in text_content):
            if "right_align" not in final_tags:
                 final_tags.append("right_align")

        final_text = f"{icon}{text_content}" + ("\n" if newline_flag else "")
        cleaned_tags = tuple(t for t in final_tags if t not in ["right_align", "center"])


        try:
            is_disabled = widget.cget('state') == tk.DISABLED
            if is_disabled:
                 widget.config(state=tk.NORMAL)

            if clear_flag:
                widget.delete('1.0', tk.END)
            start_index = widget.index(tk.END)
            widget.insert(tk.END, final_text, cleaned_tags)
            end_index = widget.index(tk.END)
            widget.see(tk.END)

            # Fade-in animation for new text
            try:
                widget.tag_add('fade_tmp', start_index, end_index)
                widget.tag_configure('fade_tmp', foreground=COLOR_STATUS_DEFAULT_BG)
                final_fg = COLOR_TEXT
                for t in reversed(cleaned_tags):
                    fg = widget.tag_cget(t, 'foreground')
                    if fg:
                        final_fg = fg
                        break
                _fade_tag(widget, 'fade_tmp', COLOR_STATUS_DEFAULT_BG, final_fg, start_index, end_index)
            except Exception as e:
                print(f"Fade-in error: {e}")

            if is_disabled:
                 widget.config(state=tk.DISABLED)

            status_bar_widget = None
            if root and hasattr(root, 'status_bar') and root.status_bar and root.status_bar.winfo_exists():
                status_bar_widget = root.status_bar

            if status_bar_widget:
                 if msg_type_for_statusbar != 'info' or "جاري" in text_content or "محاولة" in text_content:
                     update_status_bar(root, status_bar_widget, text_content.strip(), msg_type=msg_type_for_statusbar)

        except tk.TclError as e:
            print(f"TclError updating status text: {e}")
        except Exception as e:
            print(f"Unexpected error updating status text: {e}")

    schedule_gui_update(root, _update, status_text_widget, text, clear, tags, add_newline)


# --- Function to show messages (Thread-safe) ---
def show_message(root, msg_type, title, message, show_in_batch=False):
    """Shows a messagebox safely from any thread and stores the last error.
       Can be suppressed during batch mode unless show_in_batch is True.
    """
    global LAST_ERROR_DETAILS

    is_batch_mode = False
    if root and hasattr(root, 'batch_mode_active') and isinstance(root.batch_mode_active, tk.BooleanVar):
        try:
            is_batch_mode = root.batch_mode_active.get()
        except tk.TclError:
            pass # Keep is_batch_mode as False

    if is_batch_mode and not show_in_batch:
        print(f"Message suppressed in batch mode: [{title}] {message}")
        if msg_type in ["error", "warning"]:
            LAST_ERROR_DETAILS["title"] = title
            LAST_ERROR_DETAILS["message"] = message
        return

    def _store_error_and_show():
        icon = ""
        if msg_type == "error": icon = "❌"
        elif msg_type == "warning": icon = "⚠️"
        elif msg_type == "info": icon = "ℹ️"
        elif msg_type == "question": icon = "❓"
        full_title = f"{icon} {title}" if icon else title

        if msg_type in ["error", "warning"]:
            LAST_ERROR_DETAILS["title"] = title
            LAST_ERROR_DETAILS["message"] = message
        if root and root.winfo_exists():
            getattr(messagebox, f"show{msg_type}")(full_title, message, icon=msg_type, parent=root)
        else:
            print(f"Messagebox not shown because parent window is destroyed: {title} - {message}")

    schedule_gui_update(root, _store_error_and_show)

# --- Function to update status bar (Thread-safe) ---
def update_status_bar(root, status_bar_label, text_to_display, msg_type='default', reset_after_ms=5000):
    """Updates the status bar label safely from any thread, centered, and colored by type."""
    global status_bar_reset_timer

    def _update(widget, current_text, message_type):
        global status_bar_reset_timer
        if widget and widget.winfo_exists():
            modified_text = current_text
            if ("جاري" in modified_text or "محاولة" in modified_text) and not modified_text.endswith("..."):
                modified_text += "..."

            style_name = "Status.TLabel"
            if message_type == 'success': style_name = "Success.Status.TLabel"
            elif message_type == 'warning': style_name = "Warning.Status.TLabel"
            elif message_type == 'error': style_name = "Error.Status.TLabel"
            elif message_type == 'info': style_name = "Info.Status.TLabel"

            try:
                widget.config(text=modified_text, anchor=tk.CENTER, style=style_name)
            except tk.TclError as e:
                 print(f"Error applying style '{style_name}' to status bar: {e}")
                 widget.config(text=modified_text, anchor=tk.CENTER, style="Status.TLabel") # Fallback to default style

            if status_bar_reset_timer:
                try: root.after_cancel(status_bar_reset_timer)
                except tk.TclError as e: print(f"TclError cancelling status bar timer: {e}")
                status_bar_reset_timer = None

            is_ongoing = "جاري" in modified_text or "محاولة" in modified_text
            should_reset = not is_ongoing and message_type != 'default'

            if should_reset and reset_after_ms > 0:
                if root and root.winfo_exists():
                    try:
                        status_bar_reset_timer = root.after(reset_after_ms, lambda: reset_status_bar(root, widget))
                    except tk.TclError as e:
                        print(f"TclError setting status bar reset timer: {e}")

    schedule_gui_update(root, _update, status_bar_label, text_to_display, msg_type)

# --- Function to Reset Status Bar ---
def reset_status_bar(root, status_bar_label):
    """Resets the status bar to its default 'جاهز' state and style."""
    global status_bar_reset_timer
    status_bar_reset_timer = None # Clear the timer ID
    if root and root.winfo_exists() and status_bar_label and status_bar_label.winfo_exists():
        update_status_bar(root, status_bar_label, "جاهز", msg_type='default', reset_after_ms=0)


# --- Progress Bar Control Functions ---
def start_progressbar(root, progress_bar_widget, status_label_widget):
    """Shows and starts the indeterminate progress bar."""
    def _start(pb, lbl):
        if pb and pb.winfo_exists() and lbl and lbl.master and lbl.master.winfo_exists():
            try:
                pb.grid(row=0, column=1, sticky="ew", padx=(5,0))
                lbl.master.columnconfigure(0, weight=0) # Status label takes less space
                lbl.master.columnconfigure(1, weight=1) # Progress bar takes more
                pb.start(10) # Start animation
                print("Progress bar started.")
            except tk.TclError as e:
                print(f"Error starting progress bar: {e}")
    schedule_gui_update(root, _start, progress_bar_widget, status_label_widget)

def stop_progressbar(root, progress_bar_widget, status_label_widget):
    """Stops and hides the progress bar."""
    def _stop(pb, lbl):
        if pb and pb.winfo_exists() and lbl and lbl.master and lbl.master.winfo_exists():
            try:
                pb.stop() # Stop animation
                pb.grid_remove() # Hide it
                lbl.master.columnconfigure(0, weight=1) # Status label takes full width again
                lbl.master.columnconfigure(1, weight=0) # Progress bar takes no space
                print("Progress bar stopped.")
            except tk.TclError as e:
                 print(f"Error stopping progress bar: {e}")
    schedule_gui_update(root, _stop, progress_bar_widget, status_label_widget)


# --- Context Menu for ScrolledText and Entry Widgets ---
def show_context_menu(event, widget):
    """Displays a context menu for the text/entry widget."""
    if not widget or not widget.winfo_exists(): return

    try: menu_font = tkFont.Font(family="Segoe UI", size=10)
    except tk.TclError: menu_font = tkFont.Font(size=10) # Fallback

    context_menu = Menu(widget, tearoff=0, font=menu_font)
    is_text_widget = isinstance(widget, (tk.Text, scrolledtext.ScrolledText))
    is_entry_widget = isinstance(widget, (tk.Entry, ttk.Entry))

    has_selection = False
    try:
        if widget.selection_get(): has_selection = True
    except tk.TclError: has_selection = False # No selection

    can_copy = has_selection
    can_cut = has_selection and (is_entry_widget or (is_text_widget and widget.cget('state') == tk.NORMAL))
    can_paste = False
    try:
        if widget.clipboard_get(): can_paste = (is_entry_widget or (is_text_widget and widget.cget('state') == tk.NORMAL))
    except tk.TclError: can_paste = False # Clipboard empty or not text

    can_select_all = False
    if is_text_widget: can_select_all = widget.index("end-1c") != "1.0" # If not empty
    elif is_entry_widget: can_select_all = bool(widget.get()) # If not empty

    can_clear = False
    if is_text_widget: can_clear = widget.index("end-1c") != "1.0" # If not empty

    root_window = None
    try: root_window = widget.winfo_toplevel()
    except tk.TclError: print("Error getting root window for context menu."); return

    if is_entry_widget or (is_text_widget and widget.cget('state') == tk.NORMAL):
        context_menu.add_command(label="قص ✂️", state=tk.NORMAL if can_cut else tk.DISABLED, command=lambda w=widget: w.event_generate("<<Cut>>"))
    context_menu.add_command(label="نسخ 📋", state=tk.NORMAL if can_copy else tk.DISABLED, command=lambda w=widget: w.event_generate("<<Copy>>"))
    if is_entry_widget or (is_text_widget and widget.cget('state') == tk.NORMAL):
        context_menu.add_command(label="لصق 📄", state=tk.NORMAL if can_paste else tk.DISABLED, command=lambda w=widget: w.event_generate("<<Paste>>"))

    context_menu.add_separator()
    if is_text_widget: cmd_select_all = lambda w=widget: w.tag_add(tk.SEL, "1.0", tk.END)
    elif is_entry_widget: cmd_select_all = lambda w=widget: w.select_range(0, tk.END)
    else: cmd_select_all = None # Should not happen

    if cmd_select_all:
        context_menu.add_command(label="تحديد الكل ✨", state=tk.NORMAL if can_select_all else tk.DISABLED, command=cmd_select_all)

    if is_text_widget and widget.cget('state') == tk.NORMAL : # Only allow clear if editable
        context_menu.add_separator()
        context_menu.add_command(label="مسح الكل 🗑️", state=tk.NORMAL if can_clear else tk.DISABLED, command=lambda r=root_window, w=widget: clear_status_log(r, w))

    try: context_menu.tk_popup(event.x_root, event.y_root)
    except tk.TclError as e: print(f"Error displaying context menu: {e}")

# gui_utils.py (النصف الثاني)
# ... (الكود من النصف الأول) ...

# --- Function to Clear Status Log ---
def clear_status_log(root, text_widget):
    """Clears the content of the status text widget."""
    def _clear(widget):
        if widget and widget.winfo_exists():
            try:
                widget.config(state=tk.NORMAL)
                widget.delete('1.0', tk.END)
                widget.insert(tk.END, "🗑️ تم مسح السجل.\n", ("info", "right_align"))
                widget.config(state=tk.DISABLED)
            except tk.TclError as e: print(f"TclError clearing status log: {e}")
            except Exception as e: print(f"Unexpected error clearing status log: {e}")
    schedule_gui_update(root, _clear, text_widget)


# --- Function to show last error details ---
def show_last_error(root):
    """Displays the last recorded error message in a Toplevel window."""
    global LAST_ERROR_DETAILS
    if not LAST_ERROR_DETAILS.get("message"):
        show_message(root, "info", "لا يوجد خطأ", "لم يتم تسجيل أي أخطاء في هذه الجلسة.", show_in_batch=True)
        return
    if not root or not root.winfo_exists():
        print("Cannot show last error, root window destroyed.")
        return

    dialog = tk.Toplevel(root)
    dialog.title(f"⚠️ تفاصيل آخر خطأ: {LAST_ERROR_DETAILS.get('title', 'خطأ')}")
    dialog.geometry("500x300")
    dialog.configure(bg='#f0f0f0') # Light grey background

    text_frame = ttk.Frame(dialog)
    text_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    error_scrollbar = ttk.Scrollbar(text_frame)
    error_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    try: error_font = tkFont.Font(family="Segoe UI", size=10)
    except tk.TclError: error_font = tkFont.Font(size=10) # Fallback
    error_text = tk.Text(text_frame, wrap=tk.WORD, font=error_font, relief="solid", borderwidth=1, padx=5, pady=5, state=tk.NORMAL, yscrollcommand=error_scrollbar.set)
    error_text.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
    error_scrollbar.config(command=error_text.yview)
    error_text.tag_configure("right_align", justify=tk.RIGHT) # For Arabic text
    error_text.insert(tk.END, LAST_ERROR_DETAILS.get("message", "لا توجد تفاصيل."), "right_align")
    error_text.config(state=tk.DISABLED) # Make it read-only
    close_button = ttk.Button(dialog, text="إغلاق", command=dialog.destroy)
    close_button.pack(pady=10)
    center_dialog(dialog, root)

# --- Function to check internet connection ---
def check_internet_connection(timeout=1):
    """Tries to connect to Google's public DNS server to check for internet."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except (socket.error, OSError) as e:
        print(f"Internet check failed: {e}")
        return False

# --- Input Validation Functions ---
def validate_nin_input(P):
    """Validation function for NIN entry: allow only digits and max length 18."""
    if P == "": return True # Allow empty for initial state or clearing
    if P.isdigit() and len(P) <= 18: return True
    else: return False

# --- Function to ask for new mobile number ---
def ask_new_mobile(root):
    """Asks the user for a new mobile number using a custom, larger dialog."""
    if not root or not root.winfo_exists():
        print("Cannot ask for mobile number, root window destroyed.")
        return None

    dialog = tk.Toplevel(root)
    dialog.title("📱 تغيير رقم الهاتف")
    dialog.geometry("400x200") # Adjusted size
    dialog.resizable(False, False)
    dialog.configure(bg='#f0f0f0')
    result = {"value": None} # Dictionary to store result, for modification in callbacks
    main_frame = ttk.Frame(dialog, padding=20)
    main_frame.pack(expand=True, fill="both")
    main_frame.columnconfigure(0, weight=1)
    try:
        label_font = tkFont.Font(family="Segoe UI", size=11)
        entry_font = tkFont.Font(family="Segoe UI", size=12)
        button_font = tkFont.Font(family="Segoe UI", size=10, weight="bold")
    except tk.TclError:
        label_font = tkFont.Font(size=11) # Fallback
        entry_font = tkFont.Font(size=12) # Fallback
        button_font = tkFont.Font(size=10, weight="bold") # Fallback
    instruction_label = ttk.Label(main_frame, text="الرجاء إدخال رقم الهاتف الجديد:", font=label_font, background='#f0f0f0', anchor='center')
    instruction_label.grid(row=0, column=0, pady=(0, 5), sticky="ew")
    sub_instruction_label = ttk.Label(main_frame, text="(10 أرقام تبدأ بـ 05 أو 06 أو 07)", font=(label_font.cget("family"), 9), background='#f0f0f0', foreground='#555555', anchor='center')
    sub_instruction_label.grid(row=1, column=0, pady=(0, 15), sticky="ew")
    mobile_entry = ttk.Entry(main_frame, font=entry_font, width=25, justify=tk.CENTER)
    mobile_entry.grid(row=2, column=0, pady=(0, 20), ipady=5)
    mobile_entry.focus_set()

    def validate_mobile(mobile_str):
        if not mobile_str:
            show_message(dialog, "error", "خطأ", "لم يتم إدخال رقم هاتف.", show_in_batch=True)
            return False, "لم يتم إدخال رقم هاتف."
        if not (mobile_str.isdigit() and len(mobile_str) == 10 and mobile_str.startswith(('05', '06', '07'))):
            proceed = messagebox.askyesno(
                "❓ تنسيق غير صحيح؟",
                f"تنسيق رقم الهاتف المدخل '{mobile_str}' يبدو غير صحيح.\n"
                "يجب أن يتكون من 10 أرقام ويبدأ بـ 05/06/07.\n\n"
                "هل تريد المتابعة بهذا الرقم على أي حال؟",
                icon='warning',
                parent=dialog)
            return proceed, "تنسيق غير صحيح ولكن المستخدم وافق." if proceed else "تنسيق غير صحيح ورفض المستخدم."
        return True, "صيغة صحيحة."

    def on_ok():
        mobile_value = mobile_entry.get().strip()
        is_valid, _ = validate_mobile(mobile_value)
        if is_valid:
            result["value"] = mobile_value
            dialog.destroy()
        else:
             mobile_entry.focus_set() # Keep focus on entry if invalid
    def on_cancel():
        result["value"] = None
        dialog.destroy()

    button_frame = ttk.Frame(main_frame) # No style needed, it's just a container
    button_frame.grid(row=3, column=0, pady=(10, 0))
    ok_button = ttk.Button(button_frame, text="موافق", command=on_ok, style="Accent.TButton", width=10)
    ok_button.pack(side=tk.LEFT, padx=10)
    cancel_button = ttk.Button(button_frame, text="إلغاء", command=on_cancel, width=10) # Default TButton style
    cancel_button.pack(side=tk.LEFT, padx=10)
    dialog.bind("<Return>", lambda event=None: on_ok()) # Bind Enter key
    dialog.bind("<Escape>", lambda event=None: on_cancel()) # Bind Escape key
    center_dialog(dialog, root)
    root.wait_window(dialog) # Make it modal
    return result["value"]


# --- Function to ask initial print preference ---
def ask_initial_print_preference(root, is_windows_printing_enabled, request_type):
    """Asks the user if they want to print the certificate using standard messagebox,
       unless auto-print for extend+download is enabled for that specific request type.
    """
    if not root or not root.winfo_exists():
        print("Cannot ask print preference, root window destroyed.")
        return False

    is_batch_mode = False
    if hasattr(root, 'batch_mode_active') and isinstance(root.batch_mode_active, tk.BooleanVar):
        try: is_batch_mode = root.batch_mode_active.get()
        except tk.TclError: pass # Keep is_batch_mode as False

    if is_batch_mode: # In batch mode, rely on settings
        print("Skipping print preference question during batch mode.")
        return request_type == 'extend_and_download' and settings_manager.get_auto_print_extend_download()

    # Check for auto-print setting specifically for 'extend_and_download'
    if request_type == 'extend_and_download' and settings_manager.get_auto_print_extend_download():
        print("Auto-print for extend+download is enabled, skipping confirmation.")
        return True

    if not is_windows_printing_enabled: # If printing is not available, don't ask
        return False

    root.focus_force() # Ensure dialog is on top
    print_pref = messagebox.askyesno(
        "🖨️ تأكيد الطباعة",
        "هل تود طباعة الشهادة تلقائيًا فور حفظها بنجاح؟\n\n"
        "(ملاحظة: تأكد من اختيار الطابعة الصحيحة في قائمة 'الإعدادات' أولاً.)",
        icon='question',
        parent=root
    )
    return print_pref if print_pref is not None else False # Return False if dialog is closed

# --- Function to change the cookie ---
def change_cookie_setting(root, status_bar_label):
    """Asks the user for a new cookie and updates the setting."""
    if not root or not root.winfo_exists():
        print("Cannot change cookie, root window destroyed.")
        return
    # import settings_manager # Already imported at the top
    root.focus_force()
    current_cookie = settings_manager.get_cookie()
    current_cookie_short = (current_cookie[:30] + '...') if len(current_cookie) > 30 else current_cookie

    new_cookie = simpledialog.askstring(
        "🍪 تغيير الكوكي الحالية",
        f"الكوكي المستخدمة حاليًا (بدايتها):\n{current_cookie_short}\n\n"
        "الرجاء لصق الكوكي الجديدة بالكامل هنا.\n"
        "سيتم حفظها لاستخدامها في المرات القادمة.",
        parent=root,
    )

    if new_cookie is not None: # User clicked OK
        new_cookie_stripped = new_cookie.strip()
        if new_cookie_stripped:
            if new_cookie_stripped != current_cookie:
                settings_manager.set_cookie(new_cookie_stripped)
                settings_manager.save_settings()
                show_message(root, "info", "تم الحفظ", "تم تحديث وحفظ الكوكي بنجاح.", show_in_batch=True)
                if status_bar_label and status_bar_label.winfo_exists():
                    update_status_bar(root, status_bar_label, "تم تحديث وحفظ الكوكي", msg_type='info')
                print(f"Cookie updated and saved: {settings_manager.get_cookie()[:30]}...")
            else:
                 show_message(root, "warning", "لم يتغير شيء", "الكوكي الجديدة مطابقة للكوكي الحالية.", show_in_batch=True)
        else: # User entered an empty string
            show_message(root, "error", "خطأ", "لم يتم إدخال كوكي جديدة.", show_in_batch=True)
    # If new_cookie is None, user clicked Cancel, do nothing.

# --- Function to select default printer ---
def select_default_printer_setting(root, status_bar_label, is_windows_printing_enabled):
    """Opens a dialog to select the default printer for the application."""
    if not root or not root.winfo_exists():
        print("Cannot select printer, root window destroyed.")
        return
    # import settings_manager # Already imported
    if not is_windows_printing_enabled:
        show_message(root, "error", "ميزة غير متاحة", "ميزة اختيار الطابعة تتطلب مكتبة pywin32 (ويندوز فقط) وهي غير مثبتة أو غير متاحة على نظامك.", show_in_batch=True)
        return

    try:
        import win32print # Local import as it's Windows-specific
        printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
        if not printers:
            show_message(root, "info", "لا توجد طابعات", "لم يتم العثور على أي طابعات مثبتة على هذا الجهاز.", show_in_batch=True)
            return

        dialog = tk.Toplevel(root)
        dialog.title("🖨️ اختيار الطابعة الافتراضية للبرنامج")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.configure(bg='#f0f0f0')

        try:
            label_font = tkFont.Font(family="Segoe UI", size=10)
            listbox_font = tkFont.Font(family="Segoe UI", size=11)
        except tk.TclError:
            label_font = tkFont.Font(size=10) # Fallback
            listbox_font = tkFont.Font(size=11) # Fallback

        ttk.Label(dialog, text="اختر الطابعة التي سيتم استخدامها للطباعة التلقائية:", font=label_font, background='#f0f0f0', anchor='e').pack(pady=(15,5), padx=15, fill=tk.X)
        listbox_frame = ttk.Frame(dialog) # No style needed
        listbox_frame.pack(padx=15, pady=5, fill=tk.BOTH, expand=True)
        listbox_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        listbox = tk.Listbox(listbox_frame, height=8, exportselection=False, yscrollcommand=listbox_scrollbar.set, font=listbox_font, relief=tk.SOLID, borderwidth=1, selectbackground='#0078D7', selectforeground='white', justify=tk.RIGHT) # Right justify for Arabic printer names
        listbox_scrollbar.config(command=listbox.yview)
        listbox_scrollbar.pack(side=tk.LEFT, fill=tk.Y) # Scrollbar on the left for RTL
        listbox.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True) # Listbox on the right
        current_selection_index = -1
        current_default_printer = settings_manager.get_default_printer()
        for i, printer in enumerate(printers):
            listbox.insert(tk.END, printer)
            if printer == current_default_printer: current_selection_index = i
        if current_selection_index != -1: listbox.selection_set(current_selection_index); listbox.activate(current_selection_index); listbox.see(current_selection_index)
        elif printers: listbox.selection_set(0); listbox.activate(0) # Select first if no default

        def on_select():
            selected_indices = listbox.curselection()
            if selected_indices:
                new_printer = listbox.get(selected_indices[0])
                if new_printer != settings_manager.get_default_printer():
                    settings_manager.set_default_printer(new_printer)
                    settings_manager.save_settings()
                    if status_bar_label and status_bar_label.winfo_exists(): update_status_bar(root, status_bar_label, f"الطابعة الافتراضية: {new_printer}", msg_type='info')
                    show_message(root, "info", "تم التحديد", f"تم تعيين الطابعة الافتراضية للبرنامج إلى:\n{new_printer}", show_in_batch=True)
                dialog.destroy()
            else:
                 show_message(dialog, "warning", "لم يتم التحديد", "الرجاء اختيار طابعة من القائمة أولاً.", show_in_batch=True)

        button_frame = ttk.Frame(dialog) # No style needed
        button_frame.pack(pady=(10,15))
        cancel_button = ttk.Button(button_frame, text="إلغاء", command=dialog.destroy, style='TButton')
        cancel_button.pack(side=tk.RIGHT, padx=10) # Standard order for buttons
        select_button = ttk.Button(button_frame, text="اختيار وتعيين", command=on_select, style='Accent.TButton')
        select_button.pack(side=tk.RIGHT, padx=10)
        center_dialog(dialog, root)

    except ImportError:
         show_message(root, "error", "خطأ", "فشل في استيراد مكتبة pywin32. لا يمكن الوصول لميزات الطباعة.", show_in_batch=True)
         if status_bar_label and status_bar_label.winfo_exists(): update_status_bar(root, status_bar_label, "خطأ: pywin32 غير موجودة", msg_type='error')
    except Exception as e: # Catch any other win32print errors
        show_message(root, "error", "خطأ", f"فشل في الحصول على قائمة الطابعات:\n{e}", show_in_batch=True)
        if status_bar_label and status_bar_label.winfo_exists(): update_status_bar(root, status_bar_label, "خطأ في جلب الطابعات", msg_type='error')

# --- Function to select default save path ---
def select_default_save_path_setting(root, status_bar_label):
    """Opens a dialog to select the default save directory."""
    if not root or not root.winfo_exists():
        print("Cannot select save path, root window destroyed.")
        return
    # import settings_manager # Already imported

    current_path = settings_manager.get_default_save_path()
    initial_dir = current_path if current_path and os.path.isdir(current_path) else os.path.expanduser("~")

    root.focus_force()
    chosen_dir = filedialog.askdirectory(
        title="📂 اختر مجلد الحفظ الافتراضي لملفات PDF",
        initialdir=initial_dir,
        parent=root
    )

    if chosen_dir: # User selected a directory
        if chosen_dir != current_path:
            settings_manager.set_default_save_path(chosen_dir)
            settings_manager.save_settings()
            base_dir_name = os.path.basename(chosen_dir) if chosen_dir else "غير محدد"
            if status_bar_label and status_bar_label.winfo_exists(): update_status_bar(root, status_bar_label, f"مسار الحفظ: ...{os.sep}{base_dir_name}", msg_type='info')
            show_message(root, "info", "تم التحديد", f"تم تعيين مجلد الحفظ الافتراضي لملفات PDF إلى:\n{chosen_dir}", show_in_batch=True)
    # If chosen_dir is None, user cancelled, do nothing.


# --- Function to open Font Settings Dialog ---
def open_font_settings_dialog(root, apply_settings_callback):
    """Opens a dialog to configure font settings."""
    if not root or not root.winfo_exists():
        print("Cannot open font settings, root window destroyed.")
        return

    dialog = tk.Toplevel(root)
    dialog.title("⚙️ إعدادات الخطوط")
    dialog.resizable(False, False)
    dialog.configure(bg='#f0f0f0')
    main_frame = ttk.Frame(dialog, padding=15)
    main_frame.pack(expand=True, fill="both")
    font_sizes = [8, 9, 10, 11, 12, 13, 14, 16, 18, 20]
    font_weights = ["normal", "bold"]
    font_weights_arabic = {"normal": "عادي", "bold": "غامق"}
    font_weights_map_rev = {v: k for k, v in font_weights_arabic.items()} # Reverse mapping
    current_entry_font = settings_manager.get_entry_font_config()
    current_status_font = settings_manager.get_status_font_config()
    entry_frame = ttk.LabelFrame(main_frame, text=" خط حقول الإدخال (NIN/Numero) ", padding=10)
    entry_frame.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
    entry_frame.columnconfigure(1, weight=1)
    ttk.Label(entry_frame, text="الحجم:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    entry_size_var = tk.IntVar(value=current_entry_font[1])
    entry_size_combo = ttk.Combobox(entry_frame, textvariable=entry_size_var, values=font_sizes, width=5, state="readonly")
    entry_size_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(entry_frame, text="النمط:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    entry_weight_var = tk.StringVar(value=font_weights_arabic[current_entry_font[2]])
    entry_weight_combo = ttk.Combobox(entry_frame, textvariable=entry_weight_var, values=list(font_weights_arabic.values()), width=8, state="readonly")
    entry_weight_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    status_frame = ttk.LabelFrame(main_frame, text=" خط منطقة الحالة والنتائج ", padding=10)
    status_frame.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
    status_frame.columnconfigure(1, weight=1)
    ttk.Label(status_frame, text="الحجم:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    status_size_var = tk.IntVar(value=current_status_font[1])
    status_size_combo = ttk.Combobox(status_frame, textvariable=status_size_var, values=font_sizes, width=5, state="readonly")
    status_size_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(status_frame, text="النمط:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    status_weight_var = tk.StringVar(value=font_weights_arabic[current_status_font[2]])
    status_weight_combo = ttk.Combobox(status_frame, textvariable=status_weight_var, values=list(font_weights_arabic.values()), width=8, state="readonly")
    status_weight_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    button_frame = ttk.Frame(main_frame) # No style needed
    button_frame.grid(row=2, column=0, pady=(15, 5))

    def on_apply():
        try:
            new_entry_size = entry_size_var.get(); new_entry_weight = font_weights_map_rev[entry_weight_var.get()]
            new_status_size = status_size_var.get(); new_status_weight = font_weights_map_rev[status_weight_var.get()]
            settings_manager.set_entry_font_config(current_entry_font[0], new_entry_size, new_entry_weight) # Assuming family doesn't change here
            settings_manager.set_status_font_config(current_status_font[0], new_status_size, new_status_weight) # Assuming family doesn't change
            settings_manager.save_settings()
            if apply_settings_callback: apply_settings_callback()
            show_message(dialog, "info", "تم الحفظ", "تم حفظ إعدادات الخطوط وتطبيقها.", show_in_batch=True)
        except Exception as e: show_message(dialog, "error", "خطأ", f"حدث خطأ أثناء تطبيق الإعدادات: {e}", show_in_batch=True)
    def on_ok(): on_apply(); dialog.destroy()

    ok_button = ttk.Button(button_frame, text="موافق", command=on_ok, style="Accent.TButton")
    ok_button.pack(side=tk.LEFT, padx=10)
    apply_button = ttk.Button(button_frame, text="تطبيق", command=on_apply)
    apply_button.pack(side=tk.LEFT, padx=10)
    cancel_button = ttk.Button(button_frame, text="إلغاء", command=dialog.destroy)
    cancel_button.pack(side=tk.LEFT, padx=10)
    center_dialog(dialog, root)

# --- Function to open Advanced Settings Dialog ---
def open_advanced_settings_dialog(root):
    """Opens a dialog to configure advanced settings like auto-delete and auto-print."""
    if not root or not root.winfo_exists():
        print("Cannot open advanced settings, root window destroyed.")
        return

    dialog = tk.Toplevel(root)
    dialog.title("⚙️ إعدادات متقدمة")
    dialog.resizable(False, False)
    dialog.configure(bg='#f0f0f0')
    main_frame = ttk.Frame(dialog, padding=15)
    main_frame.pack(expand=True, fill="both")
    main_frame.columnconfigure(0, weight=1) # Allow content to expand
    delete_frame = ttk.LabelFrame(main_frame, text=" الحذف التلقائي لملفات PDF القديمة ", padding=10)
    delete_frame.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
    delete_frame.columnconfigure(1, weight=1) # Allow spinbox to align nicely
    auto_delete_var = tk.BooleanVar(value=settings_manager.get_auto_delete_enabled())
    auto_delete_check = ttk.Checkbutton(delete_frame, text="تفعيل الحذف التلقائي", variable=auto_delete_var)
    auto_delete_check.grid(row=0, column=0, columnspan=3, padx=5, pady=(5, 10), sticky="w")
    ttk.Label(delete_frame, text="حذف الملفات الأقدم من:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    auto_delete_days_var = tk.StringVar(value=str(settings_manager.get_auto_delete_days()))
    auto_delete_days_spinbox = ttk.Spinbox(delete_frame, from_=1, to=365, increment=1, textvariable=auto_delete_days_var, width=5, justify=tk.CENTER, state=tk.NORMAL if auto_delete_var.get() else tk.DISABLED)
    auto_delete_days_spinbox.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(delete_frame, text="يوم").grid(row=1, column=2, padx=(0, 5), pady=5, sticky="w")
    def toggle_spinbox_state(): auto_delete_days_spinbox.config(state=tk.NORMAL if auto_delete_var.get() else tk.DISABLED)
    auto_delete_check.config(command=toggle_spinbox_state) # Link checkbutton to spinbox state
    print_frame = ttk.LabelFrame(main_frame, text=" الطباعة التلقائية ", padding=10)
    print_frame.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
    auto_print_var = tk.BooleanVar(value=settings_manager.get_auto_print_extend_download())
    auto_print_check = ttk.Checkbutton(print_frame, text="طباعة تلقائية عند استخدام زر 'تمديد وتحميل معًا'", variable=auto_print_var)
    auto_print_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    button_frame = ttk.Frame(main_frame) # No style needed
    button_frame.grid(row=2, column=0, pady=(15, 5))

    def on_save_advanced():
        """Saves the advanced settings and closes the dialog."""
        try:
            settings_manager.set_auto_delete_enabled(auto_delete_var.get())
            if auto_delete_var.get(): # Only save days if auto-delete is enabled
                try:
                    days = int(auto_delete_days_var.get())
                    if days <= 0: show_message(dialog, "error", "خطأ", "الرجاء إدخال عدد أيام أكبر من صفر للحذف التلقائي.", show_in_batch=True); return
                    settings_manager.set_auto_delete_days(days)
                except ValueError: show_message(dialog, "error", "خطأ", "الرجاء إدخال عدد أيام صحيح للحذف التلقائي.", show_in_batch=True); return
            else: # If disabled, still save the current (potentially valid) number of days or default
                try:
                    current_days_value = int(auto_delete_days_var.get())
                    if current_days_value > 0: settings_manager.set_auto_delete_days(current_days_value)
                    else: settings_manager.set_auto_delete_days(settings_manager.DEFAULT_AUTO_DELETE_DAYS) # type: ignore[attr-defined]
                except ValueError: settings_manager.set_auto_delete_days(settings_manager.DEFAULT_AUTO_DELETE_DAYS) # type: ignore[attr-defined]
            settings_manager.set_auto_print_extend_download(auto_print_var.get())
            settings_manager.save_settings()
            show_message(dialog, "info", "تم الحفظ", "تم حفظ الإعدادات المتقدمة بنجاح.", show_in_batch=True)
            dialog.destroy()
        except Exception as e: show_message(dialog, "error", "خطأ", f"حدث خطأ أثناء حفظ الإعدادات: {e}", show_in_batch=True)

    save_button = ttk.Button(button_frame, text="حفظ وإغلاق", command=on_save_advanced, style="Accent.TButton")
    save_button.pack(side=tk.LEFT, padx=10)
    cancel_button = ttk.Button(button_frame, text="إلغاء", command=dialog.destroy)
    cancel_button.pack(side=tk.LEFT, padx=10)
    center_dialog(dialog, root)

# --- Function to ask for cancel scope ---
def ask_cancel_scope(parent_window):
    """Asks the user if they want to cancel only the current retry or the whole batch/queue."""
    if not parent_window or not parent_window.winfo_exists():
        print("Cannot ask cancel scope, parent window destroyed.")
        return None # Indicate no choice made or error
    parent_window.focus_force() # Ensure dialog is on top
    result = messagebox.askyesno( # Returns True for Yes, False for No
        "❓ إلغاء المحاولة",
        "هل تريد إلغاء محاولة الطلب الحالي فقط؟\n\n"
        "   - نعم: إلغاء المحاولة الحالية والانتقال للتالي (إن وجد).\n"
        "   - لا: إلغاء المحاولة الحالية وإيقاف جميع الطلبات في الانتظار.",
        icon='question', # Standard question icon
        parent=parent_window
    )
    return result # True if "Yes" (cancel current only), False if "No" (cancel all)

# --- Function to add result to batch results table ---
def add_batch_result_to_table(root, tree_widget, nin, numero, status_msg, success):
    """Adds a result row to the batch results Treeview safely."""
    def _add_row(tree, nin_val, num_val, msg, is_success):
        if tree and tree.winfo_exists():
            try:
                tag = ""
                status_display = "فشل" # Default status
                if "إلغاء" in msg: # Check for cancellation message
                    tag = "result_warning"
                    status_display = "تم الإلغاء"
                elif is_success:
                    tag = "result_success"
                    status_display = "نجح"
                else: # General failure
                    tag = "result_error"

                item_id = tree.insert("", tk.END, values=(nin_val, num_val, status_display, msg), tags=(tag,))
                tree.see(item_id) # Scroll to the new item
            except tk.TclError as e:
                print(f"TclError adding row to batch results tree: {e}")
            except Exception as e:
                print(f"Unexpected error adding row to batch results tree: {e}")

    schedule_gui_update(root, _add_row, tree_widget, nin, numero, status_msg, success)

# --- Function to Configure Status Tags ---
def configure_status_tags(text_widget, status_font_config):
    """Configures the tags for the status ScrolledText widget."""
    if not text_widget or not text_widget.winfo_exists():
        return

    status_font_family = status_font_config[0]
    status_font_size = status_font_config[1]
    status_font_weight = status_font_config[2]

    try:
        status_font_obj = tkFont.Font(family=status_font_family, size=status_font_size, weight=status_font_weight)
        bold_status_font = tkFont.Font(family=status_font_family, size=status_font_size, weight='bold')
        small_status_font = tkFont.Font(family=status_font_family, size=max(8, status_font_size-1), weight=status_font_weight)
        alloc_header_font = tkFont.Font(family=status_font_family, size=status_font_size+1, weight='bold')
        alloc_subheader_font = tkFont.Font(family=status_font_family, size=status_font_size, weight='bold')
    except tk.TclError: # Fallback if font family is not found
        print(f"Warning: Using fallback fonts (Tahoma) for status tags due to TclError loading '{status_font_family}'.")
        fallback_family = "Tahoma"
        status_font_obj = tkFont.Font(family=fallback_family, size=10, weight='normal')
        bold_status_font = tkFont.Font(family=fallback_family, size=10, weight='bold')
        small_status_font = tkFont.Font(family=fallback_family, size=9, weight='normal')
        alloc_header_font = tkFont.Font(family=fallback_family, size=11, weight='bold')
        alloc_subheader_font = tkFont.Font(family=fallback_family, size=10, weight='bold')

    block_padding = 5 # Padding for block-like tags
    line_spacing = 3 # Spacing after lines for some tags

    # General tags
    text_widget.tag_configure("right_align", justify=tk.RIGHT)
    text_widget.tag_configure("center", justify=tk.CENTER)
    text_widget.tag_configure("info", foreground=COLOR_TEXT_SECONDARY, font=status_font_obj, justify=tk.RIGHT, spacing3=line_spacing)
    text_widget.tag_configure("warning", foreground=COLOR_WARNING, font=status_font_obj, justify=tk.RIGHT, spacing3=line_spacing)
    text_widget.tag_configure("error", foreground=COLOR_ERROR, font=status_font_obj, justify=tk.RIGHT, spacing3=line_spacing)
    text_widget.tag_configure("success", foreground=COLOR_SUCCESS, font=status_font_obj, justify=tk.RIGHT, spacing3=line_spacing)
    text_widget.tag_configure("filepath", foreground=COLOR_ACCENT_DARK, underline=True, font=status_font_obj) # Clickable filepath
    text_widget.tag_configure("separator", foreground=COLOR_BORDER, font=small_status_font, justify=tk.CENTER, spacing1=10, spacing3=10) # For visual separation

    # API specific tags (block style)
    text_widget.tag_configure("api_info", foreground="#17a2b8", background=COLOR_API_BG, font=status_font_obj, justify=tk.RIGHT, lmargin1=block_padding, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("api_start", foreground=COLOR_ACCENT_DARK, font=bold_status_font, justify=tk.RIGHT, lmargin1=block_padding, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("api_success", foreground=COLOR_SUCCESS_FG, background=COLOR_SUCCESS_BG, font=bold_status_font, justify=tk.RIGHT, relief=tk.SOLID, borderwidth=1, lmargin1=block_padding, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("api_warning", foreground=COLOR_WARNING_FG, background=COLOR_WARNING_BG, font=bold_status_font, justify=tk.RIGHT, relief=tk.SOLID, borderwidth=1, lmargin1=block_padding, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("api_error", foreground=COLOR_ERROR_FG, background=COLOR_ERROR_BG, font=bold_status_font, justify=tk.RIGHT, relief=tk.SOLID, borderwidth=1, lmargin1=block_padding, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("api_retry", foreground=COLOR_WARNING_FG, background=COLOR_WARNING_BG, font=bold_status_font, justify=tk.RIGHT, relief=tk.SOLID, borderwidth=1, lmargin1=block_padding, rmargin=block_padding, spacing3=line_spacing)

    # Allocation status specific tags
    text_widget.tag_configure("allocation_header", foreground=COLOR_TEXT, background=COLOR_ALLOCATION_HEADER_BG, font=alloc_header_font, justify=tk.CENTER, relief=tk.RAISED, borderwidth=1, spacing1=5, spacing3=5)
    text_widget.tag_configure("allocation_subheader", foreground=COLOR_ACCENT_DARK, font=alloc_subheader_font, justify=tk.RIGHT, spacing1=5, spacing3=line_spacing)
    text_widget.tag_configure("allocation_data", foreground=COLOR_TEXT, font=status_font_obj, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("allocation_success", foreground=COLOR_SUCCESS_FG, font=bold_status_font, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("allocation_warning", foreground=COLOR_WARNING_FG, font=bold_status_font, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("allocation_error", foreground=COLOR_ERROR_FG, font=bold_status_font, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("allocation_info", foreground="#17a2b8", font=bold_status_font, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing) # For neutral but important allocation info
    text_widget.tag_configure("allocation_note", foreground=COLOR_TEXT_SECONDARY, font=small_status_font, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("allocation_control_success", foreground=COLOR_SUCCESS_FG, font=status_font_obj, justify=tk.RIGHT, lmargin1=20, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("allocation_control_fail", foreground=COLOR_ERROR_FG, font=status_font_obj, justify=tk.RIGHT, lmargin1=20, rmargin=block_padding, spacing3=line_spacing)

    # Batch processing tags
    text_widget.tag_configure("batch_summary", font=bold_status_font, justify=tk.RIGHT, spacing1=10, spacing3=10, lmargin1=block_padding, rmargin=block_padding)
    text_widget.tag_configure("batch_summary_success", foreground=COLOR_SUCCESS_FG, font=bold_status_font)
    text_widget.tag_configure("batch_summary_error", foreground=COLOR_ERROR_FG, font=bold_status_font)
    text_widget.tag_configure("batch_summary_warning", foreground=COLOR_WARNING_FG, font=bold_status_font)
    text_widget.tag_configure("result_success", foreground=COLOR_SUCCESS_FG) # For batch results table
    text_widget.tag_configure("result_error", foreground=COLOR_ERROR_FG)   # For batch results table
    text_widget.tag_configure("result_warning", foreground=COLOR_WARNING_FG) # For batch results table

    # Appointment status tags (for status text area, if needed, distinct from label styles)
    text_widget.tag_configure("appointment_available", foreground=COLOR_SUCCESS_FG, font=bold_status_font, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("appointment_unavailable", foreground=COLOR_WARNING_FG, font=bold_status_font, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing)
    text_widget.tag_configure("appointment_error", foreground=COLOR_ERROR_FG, font=bold_status_font, justify=tk.RIGHT, lmargin1=15, rmargin=block_padding, spacing3=line_spacing)

# --- *** تمت الإضافة: دالة لسؤال المستخدم وفتح متصفح حجز المواعيد *** ---
def ask_to_open_booking_website(root: tk.Tk, nin: str, numero_wassit: str, status_bar_label: Optional[ttk.Label]):
    """
    Asks the user if they want to open the appointment booking website.
    If yes, opens the website and copies NIN/Numero to clipboard.
    """
    if not root or not root.winfo_exists():
        print("Cannot ask to open booking website, root window destroyed.")
        return

    # رابط صفحة حجز المواعيد (يمكن تعديله إذا تغير)
    # هذا الرابط هو لصفحة تسجيل الدخول، حيث يمكن للمستخدم إدخال بياناته
    booking_url = "https://minha.anem.dz/rendezVous"

    # سؤال المستخدم
    user_response = messagebox.askyesno(
        "📅 حجز موعد",
        "لا يوجد لديك موعد محجوز حاليًا.\n"
        "هل ترغب في فتح الموقع الإلكتروني لحجز موعد الآن؟\n\n"
        f"(سيتم نسخ رقم التعريف الوطني: {nin} ورقم وسيط: {numero_wassit} إلى الحافظة لتسهيل الإدخال)",
        icon='question',
        parent=root
    )

    if user_response:
        try:
            # نسخ البيانات إلى الحافظة
            clipboard_text = f"NIN: {nin}\nNumero Wassit: {numero_wassit}"
            root.clipboard_clear()
            root.clipboard_append(clipboard_text)
            root.update() # ensure clipboard is updated
            if status_bar_label and status_bar_label.winfo_exists():
                update_status_bar(root, status_bar_label, "تم نسخ NIN و Numero إلى الحافظة.", msg_type='info', reset_after_ms=3000)
            show_message(root, "info", "تم النسخ", "تم نسخ رقم التعريف الوطني ورقم وسيط إلى الحافظة.", show_in_batch=True)

            # فتح الموقع في المتصفح الافتراضي
            webbrowser.open(booking_url, new=2) # new=2 opens in a new tab if possible
            if status_bar_label and status_bar_label.winfo_exists():
                update_status_bar(root, status_bar_label, "جاري فتح موقع حجز المواعيد...", msg_type='info', reset_after_ms=3000)
            print(f"Opening booking website: {booking_url}")

        except Exception as e:
            error_msg = f"فشل فتح الموقع أو نسخ البيانات: {e}"
            print(error_msg, file=sys.stderr)
            show_message(root, "error", "خطأ", error_msg, show_in_batch=True)
            if status_bar_label and status_bar_label.winfo_exists():
                update_status_bar(root, status_bar_label, "خطأ في فتح الموقع/النسخ", msg_type='error')
# --------------------------------------------------------------------

# --- *** تم التعديل: تحديث ليبل حالة المواعيد ليشمل حالة المنحة *** ---
def update_appointment_status_label(root: tk.Tk, label_widget: ttk.Label,
                                    appointment_status: Optional[bool],
                                    benefit_status_code: Optional[int],
                                    benefit_status_text: Optional[str]):
    """Updates the dedicated appointment status label with appointment and benefit status."""
    def _update(widget, appt_stat, ben_code, ben_text):
        if widget and widget.winfo_exists():
            full_text = "📅 المواعيد: "
            appt_text = ""
            ben_display_text = "" # النص النهائي لعرض حالة المنحة
            final_style_name = "AppointmentStatus.TLabel" # النمط الافتراضي

            # تحديد نص حالة الموعد
            if appt_stat is True:
                appt_text = "لديك موعد ✅"
                # لا نغير النمط هنا بناءً على الموعد فقط، سنعطي الأولوية لحالة المنحة
            elif appt_stat is False:
                appt_text = "لا يوجد موعد ⚠️"
            else: # None or other
                appt_text = "غير معروف ؟"

            full_text += appt_text

            # تحديد نص ولون حالة المنحة
            if ben_code is not None and ben_text is not None:
                ben_display_text = f" | 💳 المنحة: {ben_text}"
                if ben_code == 1: # نشطة
                    final_style_name = "Success.AppointmentStatus.TLabel"
                elif ben_code == 0: # موقوفة
                    final_style_name = "Warning.AppointmentStatus.TLabel"
                elif ben_code == 2: # ملغاة
                    final_style_name = "Error.AppointmentStatus.TLabel"
                # إذا كانت حالة الموعد هي الخطأ الرئيسي (appt_stat is None)، فقد نرغب في إظهار ذلك
                if appt_stat is None and ben_code is not None : # إذا كان الموعد غير معروف ولكن المنحة معروفة
                     pass # النمط سيتم تحديده بناءً على المنحة
                elif appt_stat is None : # إذا كان كلاهما غير معروف أو الموعد فقط
                     final_style_name = "Error.AppointmentStatus.TLabel"


            full_text += ben_display_text

            try:
                # التأكد من أن الأنماط معرفة (يمكن نقل هذا إلى دالة تهيئة الأنماط الرئيسية)
                style = ttk.Style()
                try:
                    default_font = tkFont.Font(family="Segoe UI", size=9)
                except tk.TclError:
                    default_font = tkFont.Font(size=9) # Fallback

                style.configure("AppointmentStatus.TLabel", padding=(5, 2), font=default_font, anchor=tk.CENTER, borderwidth=1, relief='solid', bordercolor=COLOR_BORDER)
                style.configure("Success.AppointmentStatus.TLabel", foreground=COLOR_SUCCESS_FG, background=COLOR_SUCCESS_BG, bordercolor=COLOR_SUCCESS)
                style.configure("Warning.AppointmentStatus.TLabel", foreground=COLOR_WARNING_FG, background=COLOR_WARNING_BG, bordercolor=COLOR_WARNING)
                style.configure("Error.AppointmentStatus.TLabel", foreground=COLOR_ERROR_FG, background=COLOR_ERROR_BG, bordercolor=COLOR_ERROR)

                widget.config(text=full_text, style=final_style_name)
            except tk.TclError as e:
                print(f"TclError configuring/applying style for appointment/benefit label: {e}")
                widget.config(text=full_text) # Fallback to default style if error
            except Exception as e:
                print(f"Unexpected error updating appointment/benefit label: {e}")
                widget.config(text=full_text) # Fallback

    if label_widget:
        schedule_gui_update(root, _update, label_widget, appointment_status, benefit_status_code, benefit_status_text)
    else:
        print("Warning: Appointment status label widget is None, cannot update.")
# ------------------------------------------------------
