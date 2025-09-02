import tkinter as tk
from tkinter import ttk, scrolledtext, Menu, font as tkFont, messagebox, simpledialog
import threading
import os
import time

# Local modules
import constants
import settings_manager
import gui_utils
import file_handler
import api_client


# Globals (widgets/state)
root: tk.Tk | None = None
nin_entry: ttk.Entry | None = None
numero_entry: ttk.Entry | None = None
status_text: scrolledtext.ScrolledText | None = None
status_bar: ttk.Label | None = None
progress_bar: ttk.Progressbar | None = None

action_buttons: list[ttk.Button] = []
cancel_retry_button: ttk.Button | None = None
cancel_retry_flag: tk.BooleanVar | None = None
batch_cancel_all_flag: tk.BooleanVar | None = None


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
}


def current_palette():
    theme = settings_manager.get_ui_theme() if hasattr(settings_manager, 'get_ui_theme') else 'light'
    return PALETTE_DARK if theme == 'dark' else PALETTE_LIGHT


def apply_theme(theme: str | None = None):
    pal = current_palette() if not theme else (PALETTE_DARK if theme == 'dark' else PALETTE_LIGHT)
    try:
        if theme:
            if hasattr(settings_manager, 'set_ui_theme'):
                settings_manager.set_ui_theme(theme)
                settings_manager.save_settings()
        # Sync gui_utils palette keys used there
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
        })
    except Exception as e:
        print(f"Palette sync warning: {e}")

    # ttk styles
    style = ttk.Style()
    try:
        # pick a native theme as base
        if 'clam' in style.theme_names():
            style.theme_use('clam')
    except Exception:
        pass

    # fonts
    try:
        entry_ff, entry_fs, entry_fw = settings_manager.get_entry_font_config()
        status_ff, status_fs, status_fw = settings_manager.get_status_font_config()
    except Exception:
        entry_ff, entry_fs, entry_fw = ('Segoe UI', 12, 'bold')
        status_ff, status_fs, status_fw = ('Tahoma', 11, 'bold')

    default_font = tkFont.Font(family='Segoe UI', size=10)
    label_font = tkFont.Font(family=entry_ff, size=10)
    button_font = tkFont.Font(family='Segoe UI', size=9, weight='bold')
    statusbar_font = tkFont.Font(family=status_ff, size=max(8, status_fs - 1))

    style.configure('.', background=pal['PRIMARY_BG'], foreground=pal['TEXT'], font=default_font)
    style.configure('TFrame', background=pal['PRIMARY_BG'])
    style.configure('Card.TFrame', background=pal['CARD_BG'], relief='solid', borderwidth=1)
    style.configure('TLabel', background=pal['PRIMARY_BG'], foreground=pal['TEXT_MUTED'], font=label_font)
    style.configure('Title.TLabel', background=pal['PRIMARY_BG'], foreground=pal['ACCENT'], font=('Segoe UI', 12, 'bold'))
    style.configure('TButton', background=pal['CARD_BG'], padding=(10, 6), relief='raised')
    style.map('TButton', background=[('active', pal['BTN_HOVER'])])
    style.configure('Accent.TButton', background=pal['ACCENT'], foreground=pal['CARD_BG'])
    style.map('Accent.TButton', background=[('active', pal['ACCENT_DARK'])])
    style.configure('Status.TLabel', background=pal['STATUS_BG'], foreground=pal['TEXT_MUTED'], font=statusbar_font, padding=(8, 3))
    style.configure('Status.TFrame', background=pal['STATUS_BG'])
    style.configure('TLabelframe', background=pal['CARD_BG'])
    style.configure('TLabelframe.Label', background=pal['CARD_BG'], foreground=pal['ACCENT'])

    if root:
        root.configure(bg=pal['PRIMARY_BG'])


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
        e_ff, e_fs, e_fw = ('Segoe UI', 12, 'bold')
        s_ff, s_fs, s_fw = ('Tahoma', 11, 'bold')
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
        cancel_retry_button.grid_remove()


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
        cancel_retry_button.grid(row=0, column=5, padx=5, pady=6, sticky='ew')
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
                    cancel_retry_button.grid_remove()
                except Exception:
                    pass
            root.after(0, enable_actions)

    threading.Thread(target=worker, daemon=True).start()


def build_ui(root_win: tk.Tk):
    global nin_entry, numero_entry, status_text, status_bar, progress_bar
    global cancel_retry_button, cancel_retry_flag, batch_cancel_all_flag
    global action_buttons

    pal = current_palette()

    # Top frame (content)
    container = ttk.Frame(root_win, padding=10)
    container.pack(expand=True, fill=tk.BOTH)

    # Input card
    input_card = ttk.LabelFrame(container, text=' بيانات الدخول ', padding=10)
    input_card.pack(fill=tk.X)

    ttk.Label(input_card, text='الرقم الوطني (NIN):').grid(row=0, column=0, sticky='e', padx=(0, 8), pady=6)
    nin_entry = ttk.Entry(input_card, justify='right', width=30)
    nin_entry.grid(row=0, column=1, sticky='ew', pady=6)
    nin_entry.insert(0, settings_manager.get_last_nin() if hasattr(settings_manager, 'get_last_nin') else '')
    try:
        nin_entry.configure(validate='key', validatecommand=(root_win.register(gui_utils.validate_nin_input), '%P'))
    except Exception:
        pass

    ttk.Label(input_card, text='رقم الوسيط:').grid(row=1, column=0, sticky='e', padx=(0, 8), pady=6)
    numero_entry = ttk.Entry(input_card, justify='right', width=30)
    numero_entry.grid(row=1, column=1, sticky='ew', pady=6)
    numero_entry.insert(0, settings_manager.get_last_numero() if hasattr(settings_manager, 'get_last_numero') else '')

    input_card.columnconfigure(1, weight=1)

    # Actions card
    actions_card = ttk.LabelFrame(container, text=' العمليات ', padding=10)
    actions_card.pack(fill=tk.X, pady=(10, 0))

    action_buttons.clear()
    btn_change_mobile = ttk.Button(actions_card, text='تغيير رقم الهاتف 📱', command=lambda b=None: start_request('change_mobile', btn_change_mobile))
    btn_alloc = ttk.Button(actions_card, text='حالة منحة البطالة 📊', command=lambda b=None: start_request('allocation_status', btn_alloc))
    btn_extend_dl = ttk.Button(actions_card, text='تجديد + تحميل + طباعة ✨', style='Accent.TButton', command=lambda b=None: start_request('extend_and_download', btn_extend_dl))
    btn_download = ttk.Button(actions_card, text='تحميل الشهادة 📄', command=lambda b=None: start_request('download_pdf', btn_download))
    btn_extend = ttk.Button(actions_card, text='تجديد/إعادة تفعيل ⏳', command=lambda b=None: start_request('extend', btn_extend))

    btn_change_mobile.grid(row=0, column=0, padx=5, pady=6, sticky='ew'); action_buttons.append(btn_change_mobile)
    btn_alloc.grid(row=0, column=1, padx=5, pady=6, sticky='ew'); action_buttons.append(btn_alloc)
    btn_extend_dl.grid(row=0, column=2, padx=5, pady=6, sticky='ew'); action_buttons.append(btn_extend_dl)
    btn_download.grid(row=0, column=3, padx=5, pady=6, sticky='ew'); action_buttons.append(btn_download)
    btn_extend.grid(row=0, column=4, padx=5, pady=6, sticky='ew'); action_buttons.append(btn_extend)

    cancel_retry_flag = tk.BooleanVar(value=False)
    batch_cancel_all_flag = tk.BooleanVar(value=False)
    cancel_retry_button = ttk.Button(actions_card, text='إلغاء المحاولات ✖️', style='TButton', command=on_cancel_retry)
    cancel_retry_button.grid(row=0, column=5, padx=5, pady=6, sticky='ew')
    cancel_retry_button.grid_remove()

    for i in range(6):
        actions_card.columnconfigure(i, weight=1)

    # Status area
    status_card = ttk.LabelFrame(container, text=' الحالة والنتائج ', padding=10)
    status_card.pack(expand=True, fill=tk.BOTH, pady=(10, 0))

    header = ttk.Frame(status_card)
    header.pack(fill=tk.X)
    ttk.Label(header, text='سجل العمليات', style='Title.TLabel').pack(side=tk.LEFT)
    ttk.Button(header, text='تنظيف', command=clear_status).pack(side=tk.RIGHT)

    status_text = scrolledtext.ScrolledText(status_card, wrap=tk.WORD, height=14, relief='solid', borderwidth=1)
    status_text.pack(expand=True, fill=tk.BOTH, pady=(8, 0))

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
    progress_bar = ttk.Progressbar(status_bar_frame, mode='indeterminate', length=160)
    progress_bar.pack(side=tk.RIGHT, padx=6, pady=3)


def main():
    global root
    root = tk.Tk()
    root.title(f"{constants.APP_NAME if hasattr(constants, 'APP_NAME') else 'خدمات وسيط'} - واجهة حديثة")
    root.minsize(900, 640)

    apply_theme()  # configure palette + styles
    build_menu(root)
    build_ui(root)
    apply_fonts()

    # Auto-delete on startup (non-blocking)
    threading.Thread(target=lambda: file_handler.perform_auto_delete(root, None, None), daemon=True).start()

    root.mainloop()


if __name__ == '__main__':
    main()
