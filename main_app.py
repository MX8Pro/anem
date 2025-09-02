import tkinter as tk
from tkinter import scrolledtext, Menu, font as tkFont, messagebox, simpledialog
import threading
import os
import time

try:
    import ttkbootstrap as ttkb
    from ttkbootstrap import ttk
except Exception:  # pragma: no cover - safe fallback when lib missing
    ttkb = None
    from tkinter import ttk

# Local modules
import constants
import settings_manager
import gui_utils
import file_handler
import api_client


# Globals (widgets/state)
root: tk.Tk | None = None
style: ttk.Style | None = None
nin_entry: ttk.Entry | None = None
numero_entry: ttk.Entry | None = None
status_text: scrolledtext.ScrolledText | None = None
status_bar: ttk.Label | None = None
progress_bar: ttk.Progressbar | None = None
status_body: ttk.Frame | None = None
toggle_button: ttk.Button | None = None
status_collapsed: tk.BooleanVar | None = None

action_buttons: list[ttk.Button] = []
cancel_retry_button: ttk.Button | None = None
cancel_retry_flag: tk.BooleanVar | None = None
batch_cancel_all_flag: tk.BooleanVar | None = None

# Default font family (will switch to Cairo if bundled font loads)
DEFAULT_FONT_FAMILY = "Segoe UI"


# Color palettes (light/dark)
PALETTE_LIGHT = {
    "PRIMARY_BG": "#f5f7fb",
    "CARD_BG": "#ffffff",
    "TEXT": "#212529",
    "TEXT_MUTED": "#6c757d",
    "ACCENT": "#0d6efd",
    "ACCENT_DARK": "#0a58ca",
    "BORDER": "#dee2e6",
    "API_BG": "#f1f3f5",
    "STATUS_BG": "#e9ecef",
    "BTN_HOVER": "#e7f1ff",
    "SUCCESS": "#198754",
    "SUCCESS_BG": "#d1e7dd",
    "SUCCESS_FG": "#0f5132",
    "WARNING": "#d39e00",
    "WARNING_BG": "#fff3cd",
    "WARNING_FG": "#664d03",
    "ERROR": "#dc3545",
    "ERROR_BG": "#f8d7da",
    "ERROR_FG": "#842029",
    "INFO_BG": "#cff4fc",
    "ALLOCATION_HEADER_BG": "#e0e0e0",
}
PALETTE_DARK = {
    "PRIMARY_BG": "#121212",
    "CARD_BG": "#1e1e1e",
    "TEXT": "#e6e6e6",
    "TEXT_MUTED": "#b0b0b0",
    "ACCENT": "#4da3ff",
    "ACCENT_DARK": "#2b7dd8",
    "BORDER": "#2c2f33",
    "API_BG": "#1f2327",
    "STATUS_BG": "#20252b",
    "BTN_HOVER": "#2a2e33",
    "SUCCESS": "#4ade80",
    "SUCCESS_BG": "#1d2b1f",
    "SUCCESS_FG": "#9ae6b4",
    "WARNING": "#ffdf70",
    "WARNING_BG": "#30290e",
    "WARNING_FG": "#ffec99",
    "ERROR": "#ff6b6b",
    "ERROR_BG": "#2d1f1f",
    "ERROR_FG": "#ffa8a8",
    "INFO_BG": "#1e2a38",
    "ALLOCATION_HEADER_BG": "#2e2e2e",
}


def current_palette():
    theme = settings_manager.get_ui_theme() if hasattr(settings_manager, 'get_ui_theme') else 'light'
    return PALETTE_DARK if theme == 'dark' else PALETTE_LIGHT


def load_cairo_font(root_win: tk.Tk) -> None:
    """Attempt to load bundled Cairo font; fall back silently if unavailable."""
    global DEFAULT_FONT_FAMILY
    font_path = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'Cairo-Regular.ttf')
    if not os.path.exists(font_path):
        return
    try:
        if os.name == 'nt':
            # On Windows, register the font privately for the session
            from ctypes import windll
            FR_PRIVATE = 0x10
            if windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0):
                DEFAULT_FONT_FAMILY = 'Cairo'
            else:
                print("Font load warning: AddFontResourceExW failed")
        else:
            # Attempt to create a Tk font using the file (may not be supported on all builds)
            root_win.tk.call('font', 'create', 'Cairo', '-file', font_path)
            DEFAULT_FONT_FAMILY = 'Cairo'
    except Exception as e:
        print(f"Font load warning: {e}")


def apply_theme(theme: str | None = None):
    """Apply a modern theme using ttkbootstrap when available."""
    global style
    pal = current_palette() if not theme else (PALETTE_DARK if theme == 'dark' else PALETTE_LIGHT)
    try:
        if theme and hasattr(settings_manager, 'set_ui_theme'):
            settings_manager.set_ui_theme(theme)
            settings_manager.save_settings()
        gui_utils.set_theme_palette({
            'COLOR_PRIMARY_BG': pal['PRIMARY_BG'],
            'COLOR_SECONDARY_BG': pal['CARD_BG'],
            'COLOR_TEXT': pal['TEXT'],
            'COLOR_TEXT_SECONDARY': pal['TEXT_MUTED'],
            'COLOR_ACCENT': pal['ACCENT'],
            'COLOR_ACCENT_DARK': pal['ACCENT_DARK'],
            'COLOR_API_BG': pal['API_BG'],
            'COLOR_BORDER': pal['BORDER'],
            'COLOR_STATUS_DEFAULT_BG': pal['STATUS_BG'],
            'COLOR_SUCCESS': pal['SUCCESS'],
            'COLOR_SUCCESS_BG': pal['SUCCESS_BG'],
            'COLOR_SUCCESS_FG': pal['SUCCESS_FG'],
            'COLOR_WARNING': pal['WARNING'],
            'COLOR_WARNING_BG': pal['WARNING_BG'],
            'COLOR_WARNING_FG': pal['WARNING_FG'],
            'COLOR_ERROR': pal['ERROR'],
            'COLOR_ERROR_BG': pal['ERROR_BG'],
            'COLOR_ERROR_FG': pal['ERROR_FG'],
            'COLOR_INFO_BG': pal['INFO_BG'],
            'COLOR_ALLOCATION_HEADER_BG': pal['ALLOCATION_HEADER_BG'],
        })
    except Exception as e:
        print(f"Palette sync warning: {e}")

    if ttkb and style:
        themename = 'darkly' if theme == 'dark' else 'flatly'
        try:
            style.theme_use(themename)
        except Exception:
            pass
    elif style:
        try:
            if 'clam' in style.theme_names():
                style.theme_use('clam')
        except Exception:
            pass

    try:
        entry_ff, entry_fs, entry_fw = settings_manager.get_entry_font_config()
        status_ff, status_fs, status_fw = settings_manager.get_status_font_config()
    except Exception:
        entry_ff, entry_fs, entry_fw = (DEFAULT_FONT_FAMILY, 12, 'bold')
        status_ff, status_fs, status_fw = (DEFAULT_FONT_FAMILY, 11, 'bold')
    default_font = tkFont.Font(family=DEFAULT_FONT_FAMILY, size=10)
    label_font = tkFont.Font(family=entry_ff, size=10)
    button_font = tkFont.Font(family=DEFAULT_FONT_FAMILY, size=9, weight='bold')
    statusbar_font = tkFont.Font(family=status_ff, size=max(8, status_fs - 1))

    if style:
        style.configure('.', background=pal['PRIMARY_BG'], foreground=pal['TEXT'], font=default_font)
        style.configure('TFrame', background=pal['PRIMARY_BG'])
        style.configure('Card.TFrame', background=pal['CARD_BG'], relief='solid', borderwidth=1)
        style.configure('TLabel', background=pal['PRIMARY_BG'], foreground=pal['TEXT_MUTED'], font=label_font)
        style.configure('Title.TLabel', background=pal['PRIMARY_BG'], foreground=pal['ACCENT'], font=(DEFAULT_FONT_FAMILY, 12, 'bold'))
        style.configure('TButton', background=pal['CARD_BG'], padding=(10, 6), relief='raised')
        style.map('TButton', background=[('active', pal['BTN_HOVER'])], bordercolor=[('active', pal['ACCENT'])])
        style.configure('Sidebar.TFrame', background=pal['CARD_BG'])
        style.configure('Content.TFrame', background=pal['PRIMARY_BG'])
        style.configure('Sidebar.TLabelframe', background=pal['CARD_BG'])
        style.configure('Sidebar.TLabelframe.Label', background=pal['CARD_BG'], foreground=pal['ACCENT'])
        style.configure('Sidebar.TButton', background=pal['CARD_BG'], foreground=pal['TEXT'], padding=(12, 8), relief='flat', borderwidth=1)
        style.map('Sidebar.TButton', background=[('active', pal['BTN_HOVER'])], bordercolor=[('active', pal['ACCENT'])])
        style.configure('Sidebar.Accent.TButton', background=pal['ACCENT'], foreground=pal['CARD_BG'], padding=(12, 8), relief='flat')
        style.map('Sidebar.Accent.TButton', background=[('active', pal['ACCENT_DARK'])])
        style.configure('Sidebar.Danger.TButton', background='#dc3545', foreground=pal['CARD_BG'], padding=(12, 8), relief='flat')
        style.map('Sidebar.Danger.TButton', background=[('active', '#b02a37')])
        style.configure('Status.TLabel', background=pal['STATUS_BG'], foreground=pal['TEXT_MUTED'],
                        font=statusbar_font, padding=(8, 3))
        style.configure('Success.Status.TLabel', background=pal['STATUS_BG'], foreground=pal['SUCCESS'],
                        font=statusbar_font, padding=(8, 3))
        style.configure('Warning.Status.TLabel', background=pal['STATUS_BG'], foreground=pal['WARNING'],
                        font=statusbar_font, padding=(8, 3))
        style.configure('Error.Status.TLabel', background=pal['STATUS_BG'], foreground=pal['ERROR'],
                        font=statusbar_font, padding=(8, 3))
        style.configure('Info.Status.TLabel', background=pal['STATUS_BG'], foreground=pal['ACCENT'],
                        font=statusbar_font, padding=(8, 3))
        style.configure('Status.TFrame', background=pal['STATUS_BG'])
        style.configure('TLabelframe', background=pal['CARD_BG'])
        style.configure('TLabelframe.Label', background=pal['CARD_BG'], foreground=pal['ACCENT'])
        style.configure('Accent.Horizontal.TProgressbar', background=pal['ACCENT'], troughcolor=pal['CARD_BG'])

    if root:
        root.configure(bg=pal['PRIMARY_BG'])
        if status_text:
            try:
                s_ff, s_fs, s_fw = settings_manager.get_status_font_config()
            except Exception:
                s_ff, s_fs, s_fw = (DEFAULT_FONT_FAMILY, 11, 'bold')
            gui_utils.configure_status_tags(status_text, (s_ff, s_fs, s_fw))


def build_menu(root_win: tk.Tk):
    menubar = Menu(root_win, tearoff=0)
    root_win.config(menu=menubar)

    view_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label='عرض', menu=view_menu)
    view_menu.add_command(label='فتح مجلد التحميلات', command=lambda: os.startfile(settings_manager.get_default_save_path()) if os.name == 'nt' else None)

    settings_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label='الإعدادات', menu=settings_menu)
    settings_menu.add_command(label='خطوط الواجهة...', command=lambda: gui_utils.open_font_settings_dialog(root_win, apply_fonts))
    settings_menu.add_command(label='إعدادات متقدمة...', command=lambda: gui_utils.open_advanced_settings_dialog(root_win))
    settings_menu.add_separator()
    settings_menu.add_command(label='اختيار طابعة افتراضية 🖨️', command=lambda: gui_utils.select_default_printer_setting(root_win, status_bar, file_handler.WINDOWS_PRINTING_ENABLED))
    settings_menu.add_command(label='اختيار مجلد حفظ افتراضي 📂', command=lambda: gui_utils.select_default_save_path_setting(root_win, status_bar))
    settings_menu.add_separator()
    settings_menu.add_command(label='تغيير الكوكي الحالية 🍪', command=lambda: gui_utils.change_cookie_setting(root_win, status_bar))
    settings_menu.add_separator()
    theme_menu = Menu(settings_menu, tearoff=0)
    settings_menu.add_cascade(label='المظهر', menu=theme_menu)
    theme_menu.add_radiobutton(label='فاتح', value='light', command=lambda: (apply_theme('light'), gui_utils.show_toast(root_win, 'تم اختيار الوضع الفاتح')))
    theme_menu.add_radiobutton(label='داكن', value='dark', command=lambda: (apply_theme('dark'), gui_utils.show_toast(root_win, 'تم اختيار الوضع الداكن')))
    settings_menu.add_separator()
    settings_menu.add_command(label='خروج', command=root_win.quit, accelerator='Alt+F4')


def apply_fonts():
    # entries
    try:
        e_ff, e_fs, e_fw = settings_manager.get_entry_font_config()
        s_ff, s_fs, s_fw = settings_manager.get_status_font_config()
    except Exception:
        e_ff, e_fs, e_fw = (DEFAULT_FONT_FAMILY, 12, 'bold')
        s_ff, s_fs, s_fw = (DEFAULT_FONT_FAMILY, 11, 'bold')
    if nin_entry:
        nin_entry.configure(font=(e_ff, e_fs, e_fw))
    if numero_entry:
        numero_entry.configure(font=(e_ff, e_fs, e_fw))
    if status_text:
        try:
            status_text.configure(font=(s_ff, s_fs, s_fw))
            gui_utils.configure_status_tags(status_text, (s_ff, s_fs, s_fw))
        except Exception as e:
            print(f"Status font apply warning: {e}")


def clear_status():
    if status_text:
        status_text.config(state=tk.NORMAL)
        status_text.delete('1.0', tk.END)
        status_text.config(state=tk.DISABLED)


def toggle_status_area():
    if not status_body or not toggle_button or not status_collapsed:
        return
    if status_collapsed.get():
        status_body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        toggle_button.config(text='إخفاء ▲')
        status_collapsed.set(False)
    else:
        status_body.pack_forget()
        toggle_button.config(text='إظهار ▼')
        status_collapsed.set(True)


def disable_actions():
    for b in action_buttons:
        try:
            b.configure(state=tk.DISABLED)
        except Exception:
            pass


def enable_actions():
    for b in action_buttons:
        try:
            b.configure(state=tk.NORMAL)
        except Exception:
            pass


def on_cancel_retry():
    if cancel_retry_flag:
        cancel_retry_flag.set(True)
    if cancel_retry_button:
        cancel_retry_button.pack_forget()


def start_request(request_type: str, clicked_btn: ttk.Button | None = None):
    if not root or not root.winfo_exists():
        return
    nin = nin_entry.get().strip() if nin_entry else ''
    numero = numero_entry.get().strip() if numero_entry else ''
    if not nin or not numero:
        messagebox.showwarning('تنبيه', 'يرجى إدخال رقم NIN ورقم الوسيط.', parent=root)
        return

    # Special input for change_mobile
    extra_mobile = None
    if request_type == 'change_mobile':
        extra_mobile = simpledialog.askstring('تغيير رقم الهاتف', 'أدخل الرقم الجديد:', parent=root)
        if not extra_mobile:
            return

    disable_actions()
    if cancel_retry_button:
        cancel_retry_button.pack(fill='x', pady=4)
    if cancel_retry_flag:
        cancel_retry_flag.set(False)

    original_text = clicked_btn.cget('text') if clicked_btn else ''

    def worker():
        try:
            print_pref = settings_manager.get_auto_print_extend_download() if hasattr(settings_manager, 'get_auto_print_extend_download') else False
            ok, msg = api_client.make_api_request(
                root,
                request_type,
                nin,
                numero,
                status_text,
                status_bar,
                progress_bar,
                action_buttons,
                clicked_btn,
                original_text,
                extra_mobile,
                print_pref if request_type == 'extend_and_download' else False,
                cancel_retry_flag,
                cancel_retry_button,
                batch_cancel_all_flag
            )
            # save last inputs if success
            if ok:
                try:
                    settings_manager.set_last_nin(nin)
                    settings_manager.set_last_numero(numero)
                    settings_manager.save_settings()
                except Exception:
                    pass
        finally:
            if cancel_retry_button:
                try:
                    cancel_retry_button.pack_forget()
                except Exception:
                    pass
            root.after(0, enable_actions)

    threading.Thread(target=worker, daemon=True).start()


def build_ui(root_win: tk.Tk):
    global nin_entry, numero_entry, status_text, status_bar, progress_bar
    global cancel_retry_button, cancel_retry_flag, batch_cancel_all_flag
    global action_buttons, status_body, toggle_button, status_collapsed

    pal = current_palette()

    container = ttk.Frame(root_win)
    container.pack(expand=True, fill=tk.BOTH)
    container.columnconfigure(1, weight=1)
    container.rowconfigure(0, weight=1)

    # Sidebar
    sidebar = ttk.Frame(container, style='Sidebar.TFrame', padding=15, width=280)
    sidebar.grid(row=0, column=0, sticky='ns')
    sidebar.grid_propagate(False)

    input_section = ttk.LabelFrame(sidebar, text=' بيانات الدخول ', padding=10, style='Sidebar.TLabelframe')
    input_section.pack(fill=tk.X)

    ttk.Label(input_section, text='الرقم الوطني (NIN):').pack(anchor='e', pady=(0, 4))
    nin_entry = ttk.Entry(input_section, justify='right')
    nin_entry.pack(fill=tk.X, pady=(0, 8))
    nin_entry.insert(0, settings_manager.get_last_nin() if hasattr(settings_manager, 'get_last_nin') else '')
    try:
        nin_entry.configure(validate='key', validatecommand=(root_win.register(gui_utils.validate_nin_input), '%P'))
    except Exception:
        pass

    ttk.Label(input_section, text='رقم الوسيط:').pack(anchor='e', pady=(0, 4))
    numero_entry = ttk.Entry(input_section, justify='right')
    numero_entry.pack(fill=tk.X, pady=(0, 8))
    numero_entry.insert(0, settings_manager.get_last_numero() if hasattr(settings_manager, 'get_last_numero') else '')

    # Actions
    actions_section = ttk.LabelFrame(sidebar, text=' العمليات ', padding=10, style='Sidebar.TLabelframe')
    actions_section.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

    action_buttons.clear()
    btn_change_mobile = ttk.Button(actions_section, text='تغيير رقم الهاتف 📱', style='Sidebar.TButton',
                                  command=lambda b=None: start_request('change_mobile', btn_change_mobile))
    btn_change_mobile.pack(fill=tk.X, pady=4); action_buttons.append(btn_change_mobile); gui_utils.add_hover_cursor(btn_change_mobile)
    btn_alloc = ttk.Button(actions_section, text='حالة منحة البطالة 📊', style='Sidebar.TButton',
                           command=lambda b=None: start_request('allocation_status', btn_alloc))
    btn_alloc.pack(fill=tk.X, pady=4); action_buttons.append(btn_alloc); gui_utils.add_hover_cursor(btn_alloc)
    btn_extend_dl = ttk.Button(actions_section, text='تجديد + تحميل + طباعة ✨', style='Sidebar.Accent.TButton',
                               command=lambda b=None: start_request('extend_and_download', btn_extend_dl))
    btn_extend_dl.pack(fill=tk.X, pady=4); action_buttons.append(btn_extend_dl); gui_utils.add_hover_cursor(btn_extend_dl)
    btn_download = ttk.Button(actions_section, text='تحميل الشهادة 📄', style='Sidebar.TButton',
                              command=lambda b=None: start_request('download_pdf', btn_download))
    btn_download.pack(fill=tk.X, pady=4); action_buttons.append(btn_download); gui_utils.add_hover_cursor(btn_download)
    btn_extend = ttk.Button(actions_section, text='تجديد/إعادة تفعيل ⏳', style='Sidebar.TButton',
                            command=lambda b=None: start_request('extend', btn_extend))
    btn_extend.pack(fill=tk.X, pady=4); action_buttons.append(btn_extend); gui_utils.add_hover_cursor(btn_extend)

    cancel_retry_flag = tk.BooleanVar(value=False)
    batch_cancel_all_flag = tk.BooleanVar(value=False)
    cancel_retry_button = ttk.Button(actions_section, text='إلغاء المحاولات ✖️', style='Sidebar.Danger.TButton',
                                    command=on_cancel_retry)
    cancel_retry_button.pack(fill=tk.X, pady=4)
    cancel_retry_button.pack_forget()
    gui_utils.add_hover_cursor(cancel_retry_button)

    # Main content
    content = ttk.Frame(container, style='Content.TFrame', padding=15)
    content.grid(row=0, column=1, sticky='nsew')

    status_frame = ttk.Frame(content, style='Card.TFrame', padding=10)
    status_frame.pack(expand=True, fill=tk.BOTH)

    header = ttk.Frame(status_frame, style='Card.TFrame')
    header.pack(fill=tk.X)
    ttk.Label(header, text='سجل العمليات', style='Title.TLabel').pack(side=tk.LEFT)
    clear_btn = ttk.Button(header, text='تنظيف', command=clear_status, style='Sidebar.TButton')
    clear_btn.pack(side=tk.RIGHT, padx=(4, 0))
    gui_utils.add_hover_cursor(clear_btn)
    toggle_button = ttk.Button(header, text='إخفاء ▲', command=toggle_status_area, style='Sidebar.TButton')
    toggle_button.pack(side=tk.RIGHT, padx=(4, 0))
    gui_utils.add_hover_cursor(toggle_button)

    status_collapsed = tk.BooleanVar(value=False)
    status_body = ttk.Frame(status_frame)
    status_body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    status_text = scrolledtext.ScrolledText(status_body, wrap=tk.WORD, height=14, relief='solid', borderwidth=1)
    status_text.pack(expand=True, fill=tk.BOTH)

    # Configure tags using gui_utils
    try:
        s_ff, s_fs, s_fw = settings_manager.get_status_font_config()
        gui_utils.configure_status_tags(status_text, (s_ff, s_fs, s_fw))
    except Exception as e:
        print(f"Status tags setup warning: {e}")

    # Status bar
    status_bar_frame = ttk.Frame(root_win, style='Status.TFrame')
    status_bar_frame.pack(fill=tk.X, side=tk.BOTTOM)
    status_bar = ttk.Label(status_bar_frame, text='جاهز', style='Status.TLabel')
    status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
    progress_bar = ttk.Progressbar(status_bar_frame, mode='indeterminate', length=160, style='Accent.Horizontal.TProgressbar')
    progress_bar.pack(side=tk.RIGHT, padx=6, pady=3)
    progress_bar.pack_forget()  # Hidden until a task starts


def main():
    global root, style
    current = settings_manager.get_ui_theme() if hasattr(settings_manager, 'get_ui_theme') else 'light'
    if ttkb:
        themename = 'darkly' if current == 'dark' else 'flatly'
        root = ttkb.Window(themename=themename)
        style = root.style
    else:
        root = tk.Tk()
        style = ttk.Style()
    root.title(f"{constants.APP_NAME if hasattr(constants, 'APP_NAME') else 'خدمات وسيط'} - واجهة حديثة")
    root.minsize(900, 640)

    load_cairo_font(root)
    apply_theme(current)  # configure palette + styles
    build_menu(root)
    build_ui(root)
    apply_fonts()

    # Auto-delete on startup (non-blocking)
    threading.Thread(target=lambda: file_handler.perform_auto_delete(root, None, None), daemon=True).start()

    root.mainloop()


if __name__ == '__main__':
    main()
