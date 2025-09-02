# file_handler.py
# مسؤول عن كتابة ملفات PDF، طلب مسار الحفظ، الطباعة (ويندوز)، وعرض وحذف الملفات.
# *** تم التصحيح: معالجة خطأ التحديث من خيط غير رئيسي في الحذف التلقائي ***
# *** تم التعديل: تحسين استخلاص مسار الملف عند النقر عليه في منطقة الحالة لتجاهل الأيقونات ***

import os
import sys
import base64
import threading
import datetime
import time # Needed for timestamp comparison
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk # Import ttk for Label type hint
from typing import Tuple, Callable # Added for type hinting
import re # *** تمت الإضافة: لاستخدام التعبيرات النمطية لتنظيف المسار ***

# --- Local Imports ---
from constants import IS_WINDOWS, DEFAULT_DOWNLOADS_PATH # Import default path
import settings_manager # To get default path/printer/settings
import gui_utils # For safe GUI updates

# --- Attempt to import Windows specific modules ---
WINDOWS_PRINTING_ENABLED = False
if IS_WINDOWS:
    try:
        import win32print
        import win32api
        WINDOWS_PRINTING_ENABLED = True
        print("Windows printing enabled.")
    except ImportError:
        print("تحذير: لم يتم العثور على مكتبة pywin32. سيتم تعطيل ميزات الطباعة.")
        print("لتفعيل الطباعة على ويندوز، قم بتثبيت المكتبة: pip install pywin32")
else:
    print("تحذير: ميزات الطباعة الخاصة بويندوز غير متاحة على هذا النظام.")


# --- Global variable to store last saved path ---
LAST_SAVED_PDF_PATH = None # Keep track of the last saved file for the specific button

# --- *** تعديل: دالة الطباعة لاستخدام ShellExecute مع printto *** ---
def print_pdf_file_threaded(filepath: str, printer_name: str | None,
                            root: tk.Tk, status_text_widget: tk.Text, status_bar_label: ttk.Label):
    """Prints the specified PDF file to the selected printer using ShellExecute 'printto' verb (Windows Only).
       Logs errors to status area. Runs in a separate thread.
    """
    # Check if GUI elements exist before proceeding
    if not root or not root.winfo_exists(): print("Error: Root window destroyed (print_pdf_file_threaded)."); return
    if not status_text_widget or not status_text_widget.winfo_exists(): print("Error: Status text widget destroyed (print_pdf_file_threaded)."); return
    if not status_bar_label or not status_bar_label.winfo_exists(): print("Error: Status bar label destroyed (print_pdf_file_threaded)."); return

    if not WINDOWS_PRINTING_ENABLED:
        gui_utils.update_status_text(root, status_text_widget, "❌ خطأ: الطباعة غير ممكنة. مكتبة pywin32 غير مثبتة أو أنك لا تستخدم ويندوز.\n", tags="error")
        gui_utils.update_status_bar(root, status_bar_label, "خطأ: الطباعة غير متاحة", msg_type='error')
        return

    printer_to_use = printer_name
    if not printer_to_use:
        try:
            gui_utils.update_status_text(root, status_text_widget, "🖨️ لم يتم تحديد طابعة، محاولة استخدام طابعة النظام الافتراضية...\n", tags="info")
            printer_to_use = win32print.GetDefaultPrinter()
            if not printer_to_use:
                gui_utils.update_status_text(root, status_text_widget, "❌ خطأ: لا توجد طابعة افتراضية للطباعة.\n", tags="error")
                gui_utils.update_status_bar(root, status_bar_label, "خطأ: لا توجد طابعة افتراضية", msg_type='error')
                return
            else:
                gui_utils.update_status_text(root, status_text_widget, f"✅ استخدام طابعة النظام الافتراضية: {printer_to_use}\n", tags="info")
        except Exception as e:
            gui_utils.update_status_text(root, status_text_widget, f"❌ خطأ في الحصول على الطابعة الافتراضية: {e}\n", tags="error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ: فشل الحصول على الطابعة الافتراضية", msg_type='error')
            return

    gui_utils.update_status_text(root, status_text_widget, f"\n⏳ جاري إرسال الملف '{os.path.basename(filepath)}' للطباعة على الطابعة '{printer_to_use}' باستخدام الأمر 'printto'...\n", tags="info")
    gui_utils.update_status_bar(root, status_bar_label, f"جاري إرسال الملف للطباعة على {printer_to_use}...", msg_type='info')

    # --- استخدام ShellExecute مع الأمر 'printto' ---
    try:
        print(f"Attempting ShellExecute with verb 'printto' for file '{filepath}' on printer '{printer_to_use}'")
        win32api.ShellExecute(0, "printto", filepath, f'"{printer_to_use}"', None, 0) 
        time.sleep(3) 
        gui_utils.update_status_text(root, status_text_widget, f"✅ تم إرسال أمر الطباعة 'printto' للملف إلى الطابعة '{printer_to_use}'.\n   (يعتمد النجاح الفعلي على التطبيق الافتراضي لـ PDF والطابعة)\n", tags="success")
        gui_utils.update_status_bar(root, status_bar_label, f"تم إرسال أمر الطباعة إلى {printer_to_use}", msg_type='success')
        print(f"ShellExecute 'printto' command sent for '{filepath}' to '{printer_to_use}'.")

    except Exception as e:
        error_msg = f"فشل إرسال أمر الطباعة 'printto' للطابعة '{printer_to_use}':\n{e}"
        print(f"Printing Error (printto): {error_msg}") 
        gui_utils.update_status_text(root, status_text_widget, f"\n❌ خطأ في الطباعة باستخدام 'printto': {e}\n   (قد يكون السبب عدم وجود قارئ PDF افتراضي أو مشكلة في الصلاحيات)\n", tags="error")
        gui_utils.update_status_bar(root, status_bar_label, "خطأ في إرسال أمر الطباعة", msg_type='error')
        gui_utils.update_status_text(root, status_text_widget, f"⏳ محاولة بديلة: استخدام الأمر 'print'...\n", tags="warning")
        try:
            print(f"Falling back to ShellExecute with verb 'print' for file '{filepath}'")
            win32api.ShellExecute(0, "print", filepath, None, ".", 0)
            time.sleep(2) 
            gui_utils.update_status_text(root, status_text_widget, f"⚠️ تم إرسال أمر الطباعة 'print'. (قد يتم الطباعة على الطابعة الافتراضية للنظام)\n", tags="warning")
            gui_utils.update_status_bar(root, status_bar_label, "تم إرسال أمر الطباعة (بديل)", msg_type='warning')
            print(f"ShellExecute 'print' command sent for '{filepath}'.")
        except Exception as e_print:
            error_msg_print = f"فشل إرسال أمر الطباعة 'print':\n{e_print}"
            print(f"Printing Error (print fallback): {error_msg_print}")
            gui_utils.update_status_text(root, status_text_widget, f"\n❌ فشلت المحاولة البديلة ('print') أيضًا: {e_print}\n", tags="error")
    # --------------------------------------


# --- دالة الحفظ المتزامنة (مع تعديل بدء الطباعة) ---
def write_pdf_to_file_sync(filepath: str, pdf_bytes: bytes, print_after_save: bool,
                           root: tk.Tk, status_text_widget: tk.Text, status_bar_label: ttk.Label) -> Tuple[bool, str, str | None]:
    """Writes PDF bytes to a file synchronously, optionally starts print thread, and returns status.
       Returns: (bool: success status, str: status message, str|None: saved filepath)
    """
    global LAST_SAVED_PDF_PATH
    save_success = False
    status_message = "فشل الحفظ (سبب غير معروف)"
    saved_filepath = None

    gui_elements_exist = root and root.winfo_exists() and \
                         status_text_widget and status_text_widget.winfo_exists() and \
                         status_bar_label and status_bar_label.winfo_exists()

    try:
        if gui_elements_exist:
            gui_utils.update_status_text(root, status_text_widget, f"⏳ جاري كتابة الملف إلى: ", tags="info", add_newline=False)
            gui_utils.update_status_text(root, status_text_widget, filepath, tags=("filepath", "info"), add_newline=False)
            gui_utils.update_status_text(root, status_text_widget, "...\n")
            gui_utils.update_status_bar(root, status_bar_label, f"جاري حفظ الملف: {os.path.basename(filepath)}...", msg_type='info')
        else:
            print(f"Attempting to save file (no GUI): {filepath}")

        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)

        save_success = True
        saved_filepath = filepath
        status_message = f"تم الحفظ بنجاح: {os.path.basename(filepath)}"
        LAST_SAVED_PDF_PATH = filepath 

        if gui_elements_exist:
            gui_utils.update_status_text(root, status_text_widget, f"✅ تم الحفظ بنجاح! المسار: ", tags="success", add_newline=False)
            gui_utils.update_status_text(root, status_text_widget, filepath, tags=("filepath", "success"), add_newline=False)
            gui_utils.update_status_text(root, status_text_widget, "\n")
            gui_utils.update_status_bar(root, status_bar_label, f"تم حفظ الملف: {os.path.basename(filepath)}", msg_type='success')

        if print_after_save:
            if WINDOWS_PRINTING_ENABLED:
                if gui_elements_exist:
                    gui_utils.update_status_text(root, status_text_widget, "🖨️ بدء عملية الطباعة التلقائية...\n", tags="info")
                    gui_utils.update_status_bar(root, status_bar_label, "بدء الطباعة التلقائية...", msg_type='info')
                print_thread = threading.Thread(
                    target=print_pdf_file_threaded, 
                    args=(filepath, settings_manager.get_default_printer(), root, status_text_widget, status_bar_label),
                    daemon=True,
                    name="PrintThread"
                )
                print_thread.start()
                status_message += " + جاري الطباعة" 
            else:
                status_message += " (الطباعة غير متاحة)"
                if gui_elements_exist:
                    gui_utils.update_status_text(root, status_text_widget, "⚠️ تم طلب الطباعة ولكنها غير متاحة على هذا النظام.\n", tags="warning")
                    gui_utils.update_status_bar(root, status_bar_label, "تم الحفظ (الطباعة غير متاحة)", msg_type='warning')
        else:
             if gui_elements_exist:
                 gui_utils.update_status_bar(root, status_bar_label, "اكتمل الحفظ بنجاح", msg_type='success')

    except OSError as oe:
        status_message = f"فشل الحفظ (OSError): {oe}"
        if gui_elements_exist:
            gui_utils.update_status_text(root, status_text_widget, f"\n❌ خطأ OSError: {oe}\n", tags="error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ في الحفظ (OSError)", msg_type='error')
        LAST_SAVED_PDF_PATH = None
        save_success = False
        saved_filepath = None
    except Exception as e:
        status_message = f"فشل الحفظ (خطأ غير متوقع): {e}"
        if gui_elements_exist:
            gui_utils.update_status_text(root, status_text_widget, f"\n❌ خطأ: فشل حفظ ملف PDF: {e}\n", tags="error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ في الحفظ", msg_type='error')
        LAST_SAVED_PDF_PATH = None
        save_success = False
        saved_filepath = None

    return save_success, status_message, saved_filepath


# --- دالة لعرض حوار الحفظ ثم الحفظ (لا تغيير هنا) ---
def ask_save_pdf_dialog_and_save(root: tk.Tk, status_text_widget: tk.Text, status_bar_label: ttk.Label,
                                 pdf_bytes: bytes, default_filename: str, print_pref: bool):
    if not root or not root.winfo_exists(): print("Error: Root window destroyed (ask_save_pdf_dialog_and_save)."); return
    if not status_text_widget or not status_text_widget.winfo_exists(): print("Error: Status text widget destroyed (ask_save_pdf_dialog_and_save)."); return
    if not status_bar_label or not status_bar_label.winfo_exists(): print("Error: Status bar label destroyed (ask_save_pdf_dialog_and_save)."); return

    gui_utils.update_status_text(root, status_text_widget, f"📂 عرض مربع حوار الحفظ...\n", tags=("info", "right_align"))
    gui_utils.update_status_bar(root, status_bar_label, "في انتظار اختيار مسار الحفظ...", msg_type='info')

    default_save_dir = settings_manager.get_default_save_path()
    initial_dir_ask = default_save_dir if default_save_dir and os.path.isdir(default_save_dir) else os.path.expanduser("~")

    filepath = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("ملفات PDF", "*.pdf"), ("جميع الملفات", "*.*")],
        initialfile=default_filename,
        initialdir=initial_dir_ask,
        title="حفظ شهادة التسجيل كـ PDF",
        parent=root
    )

    if filepath:
        chosen_dir = os.path.dirname(filepath)
        if chosen_dir != default_save_dir:
             settings_manager.set_default_save_path(chosen_dir)
             settings_manager.save_settings()
             gui_utils.update_status_text(root, status_text_widget, f"ℹ️ تم تحديث مسار الحفظ الافتراضي إلى: {chosen_dir}\n", tags=("info", "right_align"))

        gui_utils.update_status_text(root, status_text_widget, f"💾 تم اختيار المسار: {filepath}. بدء الحفظ...\n", tags=("info", "right_align"))
        gui_utils.update_status_bar(root, status_bar_label, "جاري الحفظ...", msg_type='info')
        
        save_success, save_msg, _ = write_pdf_to_file_sync(
            filepath, pdf_bytes, print_pref, root, status_text_widget, status_bar_label
        )
    else:
        gui_utils.update_status_text(root, status_text_widget, f"🚫 تم إلغاء عملية حفظ الملف.\n", tags=("warning", "right_align"))
        gui_utils.update_status_bar(root, status_bar_label, "تم إلغاء الحفظ", msg_type='warning')


# --- Function to view a specific PDF file (لا تغيير هنا) ---
def view_pdf(parent_window: tk.Tk | tk.Toplevel, status_bar_widget: ttk.Label | None, filepath: str):
    if not parent_window or not parent_window.winfo_exists():
        print(f"Cannot view PDF '{filepath}', parent window destroyed.")
        return

    if filepath and os.path.exists(filepath):
        try:
            if status_bar_widget and status_bar_widget.winfo_exists():
                gui_utils.update_status_bar(parent_window, status_bar_widget, f"جاري فتح الملف: {os.path.basename(filepath)}...", msg_type='info')
            abs_path = os.path.abspath(filepath)
            if IS_WINDOWS: os.startfile(abs_path)
            else: webbrowser.open(f"file:///{abs_path.replace(os.sep, '/')}")
            if status_bar_widget and status_bar_widget.winfo_exists():
                gui_utils.update_status_bar(parent_window, status_bar_widget, "تم فتح الملف في العارض الافتراضي", msg_type='info')
        except Exception as e:
            messagebox.showerror("خطأ في فتح الملف", f"لم يتمكن البرنامج من فتح الملف:\n{filepath}\n\nالسبب: {e}", icon="error", parent=parent_window) 
            if status_bar_widget and status_bar_widget.winfo_exists():
                gui_utils.update_status_bar(parent_window, status_bar_widget, "خطأ في فتح الملف", msg_type='error')
    else:
        messagebox.showerror("ملف غير موجود", f"الملف المحدد غير موجود أو لا يمكن الوصول إليه:\n{filepath}", icon="error", parent=parent_window) 
        if status_bar_widget and status_bar_widget.winfo_exists():
            gui_utils.update_status_bar(parent_window, status_bar_widget, "خطأ: الملف غير موجود", msg_type='error')

# --- Function to view the last saved PDF (لا تغيير هنا) ---
def view_last_pdf(root: tk.Tk, status_bar_label: ttk.Label):
    global LAST_SAVED_PDF_PATH
    if not root or not root.winfo_exists():
        print("Cannot view last PDF, root window destroyed.")
        return

    if LAST_SAVED_PDF_PATH and os.path.exists(LAST_SAVED_PDF_PATH):
         view_pdf(root, status_bar_label, LAST_SAVED_PDF_PATH)
    else:
         messagebox.showinfo("لا يوجد ملف", "لم يتم حفظ أي ملف PDF بنجاح في هذه الجلسة أو أن الملف المحفوظ لم يعد موجودًا.", icon="info", parent=root) 
         if status_bar_label and status_bar_label.winfo_exists():
             gui_utils.update_status_bar(root, status_bar_label, "لا يوجد ملف محفوظ لعرضه", msg_type='info')


# --- Function to handle clicks on the status text area ---
# *** تم التعديل: تحسين استخلاص مسار الملف لتجاهل الأيقونات ***
def handle_status_click(event: tk.Event, text_widget: tk.Text, status_bar_label: ttk.Label):
    """Checks if a filepath tag was clicked and opens the directory."""
    if not text_widget or not text_widget.winfo_exists(): return
    root_window = text_widget.winfo_toplevel()
    if not root_window or not root_window.winfo_exists(): return

    try:
        index = text_widget.index(f"@{event.x},{event.y}")
        tags = text_widget.tag_names(index)
        if "filepath" in tags:
            tag_range = text_widget.tag_prevrange("filepath", index + "+1c")
            if not tag_range: tag_range = text_widget.tag_nextrange("filepath", index)
            if tag_range and len(tag_range) == 2:
                original_filepath_text = text_widget.get(tag_range[0], tag_range[1])
                
                # --- *** بداية التعديل: تنظيف المسار من الأيقونات *** ---
                cleaned_filepath = original_filepath_text.strip() # إزالة المسافات البادئة واللاحقة
                
                # البحث عن بداية مسار ويندوز (مثل C:\) أو مسار يونكس (مثل /)
                match_windows = re.search(r'[a-zA-Z]:[\\/]', cleaned_filepath)
                match_unix = re.search(r'^/', cleaned_filepath) # ^ تعني بداية السلسلة

                if match_windows:
                    # إذا وجد تطابق لمسار ويندوز، استخلص المسار من بداية التطابق
                    cleaned_filepath = cleaned_filepath[match_windows.start():]
                    print(f"Cleaned Windows path: '{cleaned_filepath}' from '{original_filepath_text}'")
                elif match_unix:
                    # إذا وجد تطابق لمسار يونكس، استخلص المسار من بداية التطابق
                    cleaned_filepath = cleaned_filepath[match_unix.start():]
                    print(f"Cleaned Unix path: '{cleaned_filepath}' from '{original_filepath_text}'")
                else:
                    # إذا لم يتم العثور على نمط مسار واضح، حاول إزالة الأحرف غير المرغوب فيها الشائعة في البداية
                    # هذا أقل قوة ولكنه قد يساعد في بعض الحالات
                    # نزيل أي شيء قبل أول حرف أو رقم أو ":" أو "\" أو "/"
                    # هذا قد يكون أكثر تعقيدًا مما ينبغي إذا كانت هناك حالات كثيرة
                    # الحل الأبسط هو الاعتماد على أن المسار سيبدأ بشكل قياسي بعد الأيقونة
                    # ونقوم بإزالة عدد معين من الأحرف إذا كانت الأيقونة ثابتة
                    # لكن استخدام re للبحث عن بداية المسار هو الأفضل
                    print(f"Warning: Could not reliably clean filepath start for: '{original_filepath_text}'. Using stripped version: '{cleaned_filepath}'")
                # --- *** نهاية التعديل *** ---

                directory = os.path.dirname(cleaned_filepath) # استخدام المسار المنظف
                
                if os.path.isdir(directory):
                    if status_bar_label and status_bar_label.winfo_exists(): gui_utils.update_status_bar(root_window, status_bar_label, f"جاري فتح المجلد: {directory}...", msg_type='info')
                    try:
                        abs_path = os.path.abspath(directory)
                        if IS_WINDOWS: os.startfile(abs_path)
                        else: webbrowser.open(f"file:///{abs_path.replace(os.sep, '/')}")
                        if status_bar_label and status_bar_label.winfo_exists(): gui_utils.update_status_bar(root_window, status_bar_label, f"تم فتح المجلد: {os.path.basename(directory)}", msg_type='info')
                    except Exception as e:
                         messagebox.showerror("خطأ في فتح المجلد", f"لم نتمكن من فتح المجلد:\n{directory}\n\nالسبب: {e}", icon="error", parent=root_window) 
                         if status_bar_label and status_bar_label.winfo_exists(): gui_utils.update_status_bar(root_window, status_bar_label, "خطأ في فتح المجلد", msg_type='error')
                else:
                    messagebox.showwarning("المجلد غير موجود", f"المجلد المحدد لم يعد موجودًا أو المسار غير صحيح بعد التنظيف:\n{directory}\n(المسار الأصلي قبل التنظيف: '{original_filepath_text}')", icon="warning", parent=root_window) 
                    if status_bar_label and status_bar_label.winfo_exists(): gui_utils.update_status_bar(root_window, status_bar_label, "المجلد غير موجود", msg_type='warning')
                    print(f"Directory not found or invalid after cleaning: '{directory}'. Original text was: '{original_filepath_text}'")
    except tk.TclError: pass # قد يحدث إذا تم النقر على مكان لا يحتوي على وسم
    except Exception as e: print(f"Error handling status click: {type(e).__name__} - {e}")

# --- File Deletion Functions (لا تغيير هنا) ---
def delete_pdf_file(filepath: str, parent_window: tk.Toplevel, tree_widget: ttk.Treeview,
                    status_label_widget: ttk.Label | None, refresh_callback: Callable):
    if not parent_window or not parent_window.winfo_exists():
        print(f"Cannot delete file '{filepath}', parent window destroyed.")
        return
    if not filepath or not os.path.exists(filepath):
        messagebox.showerror("خطأ", "الملف المحدد غير موجود أو المسار غير صالح.", parent=parent_window)
        return
    filename = os.path.basename(filepath)
    confirm = messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد أنك تريد حذف الملف التالي نهائيًا؟\n\n{filename}\n\nلا يمكن التراجع عن هذا الإجراء.", icon='warning', parent=parent_window)
    if confirm:
        try:
            os.remove(filepath)
            messagebox.showinfo("تم الحذف", f"تم حذف الملف:\n{filename}", parent=parent_window)
            if refresh_callback: refresh_callback()
            global LAST_SAVED_PDF_PATH
            if LAST_SAVED_PDF_PATH == filepath: LAST_SAVED_PDF_PATH = None
        except OSError as e: messagebox.showerror("خطأ في الحذف", f"فشل حذف الملف:\n{filename}\n\nالسبب: {e}", parent=parent_window)
        except Exception as e: messagebox.showerror("خطأ غير متوقع", f"حدث خطأ غير متوقع أثناء حذف الملف:\n{filename}\n\nالسبب: {e}", parent=parent_window)

def delete_all_pdf_files(parent_window: tk.Toplevel, tree_widget: ttk.Treeview,
                         status_label_widget: ttk.Label | None, refresh_callback: Callable):
    if not parent_window or not parent_window.winfo_exists():
        print("Cannot delete all files, parent window destroyed.")
        return
    save_path = settings_manager.get_default_save_path()
    if not save_path or not os.path.isdir(save_path):
        messagebox.showerror("خطأ", f"مجلد التحميلات الافتراضي غير محدد أو غير موجود:\n{save_path}", parent=parent_window)
        return
    prefix = "شهادة_تسجيل_"; suffix = ".pdf"; files_to_delete = []
    try:
        for filename in os.listdir(save_path):
            if filename.startswith(prefix) and filename.endswith(suffix): files_to_delete.append(os.path.join(save_path, filename))
    except OSError as e: messagebox.showerror("خطأ في القراءة", f"فشل في قراءة محتويات المجلد:\n{save_path}\n\nالسبب: {e}", parent=parent_window); return
    if not files_to_delete: messagebox.showinfo("لا توجد ملفات", "لم يتم العثور على أي ملفات شهادات للحذف في المجلد الافتراضي.", parent=parent_window); return
    confirm = messagebox.askyesno("تأكيد الحذف الجماعي", f"هل أنت متأكد أنك تريد حذف جميع ملفات الشهادات ({len(files_to_delete)} ملف) الموجودة في المجلد التالي؟\n\n{save_path}\n\nلا يمكن التراجع عن هذا الإجراء.", icon='warning', parent=parent_window)
    if confirm:
        deleted_count = 0; errors = []
        for filepath_to_delete in files_to_delete: # تم تغيير اسم المتغير لتجنب التعارض
            try:
                os.remove(filepath_to_delete); deleted_count += 1
                global LAST_SAVED_PDF_PATH # تأكد من أن هذا المتغير معرف بشكل صحيح
                if LAST_SAVED_PDF_PATH == filepath_to_delete: LAST_SAVED_PDF_PATH = None
            except Exception as e: errors.append(f"{os.path.basename(filepath_to_delete)}: {e}")
        result_message = f"تم حذف {deleted_count} ملف بنجاح."
        if errors: result_message += "\n\nحدثت أخطاء أثناء حذف الملفات التالية:\n" + "\n".join(errors); messagebox.showerror("اكتمل الحذف مع أخطاء", result_message, parent=parent_window)
        else: messagebox.showinfo("اكتمل الحذف", result_message, parent=parent_window)
        if refresh_callback: refresh_callback()

# --- Auto Delete Function ---
# *** تم التصحيح: جدولة تحديث الواجهة بشكل آمن ***
def perform_auto_delete(root: tk.Tk, status_text_widget: tk.Text | None, status_bar_label: ttk.Label | None):
    if not settings_manager.get_auto_delete_enabled():
        print("Auto-delete is disabled.")
        return

    days_threshold = settings_manager.get_auto_delete_days()
    save_path = settings_manager.get_default_save_path()
    final_messages = [] 

    if not save_path or not os.path.isdir(save_path):
        msg = f"⚠️ الحذف التلقائي: مجلد التحميلات الافتراضي غير موجود أو غير محدد ({save_path})."
        print(msg)
        final_messages.append({"text": msg + "\n", "tags": "warning"})
        if root:
            gui_utils.schedule_gui_update(root, _update_auto_delete_status_on_main_thread, root, status_text_widget, final_messages)
        return

    print(f"Performing auto-delete for files older than {days_threshold} days in {save_path}...")
    now_ts = time.time()
    deleted_count = 0
    errors = []
    prefix = "شهادة_تسجيل_"
    suffix = ".pdf"

    try:
        for filename in os.listdir(save_path):
            if filename.startswith(prefix) and filename.endswith(suffix):
                filepath_to_check = os.path.join(save_path, filename) # تم تغيير اسم المتغير
                try:
                    file_mod_time = os.path.getmtime(filepath_to_check)
                    age_seconds = now_ts - file_mod_time
                    age_days = age_seconds / (60 * 60 * 24)
                    if age_days > days_threshold:
                        print(f"  Deleting '{filename}' (Age: {age_days:.1f} days)")
                        os.remove(filepath_to_check)
                        deleted_count += 1
                        global LAST_SAVED_PDF_PATH
                        if LAST_SAVED_PDF_PATH == filepath_to_check:
                            LAST_SAVED_PDF_PATH = None
                except FileNotFoundError:
                    continue 
                except Exception as e:
                    print(f"  Error processing file {filename} for auto-delete: {e}")
                    errors.append(f"{filename}: {e}")

        if deleted_count > 0:
            msg = f"🧹 الحذف التلقائي: تم حذف {deleted_count} ملف PDF أقدم من {days_threshold} يوم."
            print(msg)
            final_messages.append({"text": msg + "\n", "tags": "info"})
        else:
            print("Auto-delete: No old files found to delete.")
            
        if errors:
             error_msg = "⚠️ الحذف التلقائي: حدثت أخطاء أثناء معالجة بعض الملفات:\n" + "\n".join(errors)
             print(error_msg)
             final_messages.append({"text": error_msg + "\n", "tags": "warning"})

    except OSError as e:
        msg = f"❌ الحذف التلقائي: فشل في الوصول إلى المجلد {save_path}: {e}"
        print(msg)
        final_messages.append({"text": msg + "\n", "tags": "error"})
    except Exception as e:
        msg = f"❌ الحذف التلقائي: حدث خطأ غير متوقع: {e}"
        print(msg)
        final_messages.append({"text": msg + "\n", "tags": "error"})

    if root and final_messages:
        gui_utils.schedule_gui_update(root, _update_auto_delete_status_on_main_thread, root, status_text_widget, final_messages)

def _update_auto_delete_status_on_main_thread(root: tk.Tk, status_text_widget: tk.Text | None, messages: list[dict]):
    if root and root.winfo_exists() and status_text_widget and status_text_widget.winfo_exists():
        for msg_info in messages:
            gui_utils.update_status_text(root, status_text_widget, msg_info["text"], tags=msg_info["tags"])
    else:
        print("Auto-delete: Could not update GUI, window or widget destroyed.")


# --- Scan Download Directory Function (لا تغيير هنا) ---
def scan_download_directory() -> list[dict]:
    files_data = []; save_path = settings_manager.get_default_save_path(); prefix = "شهادة_تسجيل_"; suffix = ".pdf"
    if not save_path or not os.path.isdir(save_path): print(f"Download directory not found or not set: {save_path}"); return files_data
    try:
        for filename in os.listdir(save_path):
            if filename.startswith(prefix) and filename.endswith(suffix):
                full_path = os.path.join(save_path, filename)
                try:
                    numero_str = filename[len(prefix):-len(suffix)]
                    mod_timestamp = os.path.getmtime(full_path)
                    mod_date = datetime.datetime.fromtimestamp(mod_timestamp).strftime('%Y-%m-%d')
                    if numero_str.isdigit(): files_data.append({"filename": filename, "numero": numero_str, "path": full_path, "date": mod_date})
                except FileNotFoundError: print(f"File not found during scan: {filename}"); continue
                except Exception as e: print(f"Error parsing filename or getting date for {filename}: {e}")
    except OSError as e: print(f"Error scanning directory {save_path}: {e}")
    files_data.sort(key=lambda x: (x.get("date", "0000-00-00"), x.get("numero", "")), reverse=True)
    return files_data

