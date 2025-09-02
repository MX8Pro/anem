# api_client.py
# يحتوي على الدوال المسؤولة عن إجراء طلبات الـ API المختلفة.
# *** تم التعديل: إضافة محاولات إعادة اتصال لانهائية قابلة للإلغاء ***
# *** تم التعديل: إضافة معالجة لخطأ (State: error, Code: 2) في تغيير الهاتف ***
# *** تم التعديل: فصل التحقق من المواعيد إلى عملية منفصلة تبدأ من main_app ***
# *** تمت الإضافة: دالة _get_validation_and_ids لجلب البيانات الأولية للمواعيد ***
# *** تم التعديل: _check_appointment_availability لتحديث ليبل مخصص ***
# *** تمت الإضافة: دالة _check_existing_appointment_status للتحقق من وجود موعد مسبق وتحديث حالة المنحة ***
# *** تم التعديل: استيراد BATCH_STEP_DELAY_SECONDS من constants.py وإزالة التعريف المحلي ***
# *** تمت الإضافة: دالة fetch_initial_cookie لجلب الكوكيز عند بدء التشغيل ***
# *** تم التعديل: تغيير رسالة الخطأ للرمز 7 في عملية التجديد ***

import requests
import json
import base64
import warnings
import threading # Needed for saving PDF in background
import time # For potential retries or delays
import sys # Needed for logging detailed errors
import tkinter as tk # Needed for BooleanVar type hinting and default values
from tkinter import ttk # لاستخدام ttk.Label في تلميحات النوع
from typing import Tuple, Optional, Dict, Any # لتحديد نوع الإرجاع tuple و Optional و Dict

# --- Local Imports ---
from constants import (
    EXTEND_API_URL, REACTIVATE_API_URL, CERTIFICATE_API_URL, ALLOCATION_API_URL,
    CHANGE_MOBILE_API_URL, APPOINTMENT_DATES_API_URL,
    DEFAULT_REFERER_URL, CHANGE_MOBILE_REFERER_URL, ALLOCATION_REFERER,
    DEFAULT_ORIGIN_URL, ALLOCATION_ORIGIN, USER_AGENT,
    DEFAULT_COOKIE_VALUE, # قيمة افتراضية في حالة عدم وجود كوكي
    BATCH_STEP_DELAY_SECONDS
)
import settings_manager # To get cookie, save last input
import gui_utils # To update GUI safely, control progress bar, show/hide widgets
import file_handler # To save PDF

# --- Constants ---
RETRY_DELAY_SECONDS = 5 # Delay between retries in seconds
MAX_PROCESSING_RETRIES = 2 # Maximum number of retries for specific *processing* errors like non-JSON response

# --- *** تمت الإضافة: دالة جلب الكوكيز الأولية *** ---
def fetch_initial_cookie(root: Optional[tk.Tk],
                         status_text_widget: Optional[tk.Text],
                         status_bar_label: Optional[ttk.Label]) -> Tuple[bool, str]:
    """
    Attempts to fetch initial cookies by making a GET request to DEFAULT_REFERER_URL.
    Saves the fetched cookies using settings_manager.
    Updates GUI elements if provided.

    Returns:
        Tuple[bool, str]: (success_status, status_message)
    """
    target_url = DEFAULT_REFERER_URL #  https://wassitonline.anem.dz/postulation/prolongationDemande
    session = None
    status_message = "فشل جلب الكوكيز الأولية (سبب غير معروف)"
    success = False

    # رسالة بدء التشغيل للواجهة (إذا كانت متاحة)
    if root and status_text_widget:
        gui_utils.update_status_text(root, status_text_widget, "محاولة جلب الكوكيز الأولية...", tags="api_info", clear=True)
    if root and status_bar_label:
        gui_utils.update_status_bar(root, status_bar_label, "جاري جلب الكوكيز...", msg_type='info')

    try:
        # تجاهل تحذيرات SSL غير الآمنة (إذا لزم الأمر، ولكن يفضل استخدام verify=True في الإنتاج)
        warnings.filterwarnings('ignore', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

        # استخدام جلسة جديدة لضمان عدم إرسال كوكيز قديمة
        session = requests.Session()
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8', # تفضيل الإنجليزية ثم العربية
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1' # طلب ترقية الاتصال إلى HTTPS
        }

        print(f"Fetching initial cookies from: {target_url}")
        response = session.get(target_url, headers=headers, timeout=20, verify=False) # verify=False لتجاوز مشاكل SSL مؤقتًا
        response.raise_for_status() # التحقق من أخطاء HTTP

        # استخلاص الكوكيز من الاستجابة
        if session.cookies:
            cookie_dict = requests.utils.dict_from_cookiejar(session.cookies)
            formatted_cookies = "; ".join([f"{name}={value}" for name, value in cookie_dict.items()])


            if formatted_cookies:
                settings_manager.set_cookie(formatted_cookies)
                settings_manager.save_settings()
                status_message = "تم جلب وحفظ الكوكيز الأولية بنجاح."
                success = True
                print(f"Cookies fetched and saved: {formatted_cookies[:100]}...") # طباعة جزء من الكوكي للتأكيد
                if root and status_text_widget:
                    gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_success")
                if root and status_bar_label:
                    gui_utils.update_status_bar(root, status_bar_label, "تم جلب الكوكيز", msg_type='success')
            else:
                status_message = "تم استقبال استجابة ناجحة ولكن لم يتم العثور على كوكيز."
                success = False
                if root and status_text_widget:
                    gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
        else:
            status_message = "لم يتم إرجاع أي كوكيز من الخادم."
            success = False
            if root and status_text_widget:
                gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")

    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        status_message = f"خطأ HTTP {status_code} أثناء جلب الكوكيز: {http_err}"
        success = False
        print(f"HTTPError fetching cookies: {status_message}", file=sys.stderr)
        if root and status_text_widget:
            gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
        status_message = f"فشل الاتصال بالخادم لجلب الكوكيز: {conn_err}"
        success = False
        print(f"Connection error fetching cookies: {status_message}", file=sys.stderr)
        if root and status_text_widget:
            gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
    except requests.exceptions.RequestException as req_e:
        status_message = f"خطأ عام في الطلب أثناء جلب الكوكيز: {req_e}"
        success = False
        print(f"RequestException fetching cookies: {status_message}", file=sys.stderr)
        if root and status_text_widget:
            gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
    except Exception as e:
        status_message = f"خطأ غير متوقع أثناء جلب الكوكيز: {type(e).__name__} - {e}"
        success = False
        print(f"Unexpected error fetching cookies: {status_message}", file=sys.stderr)
        if root and status_text_widget:
            gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
    finally:
        if session:
            session.close()
        warnings.filterwarnings('default', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)
        if root and status_bar_label and not success: # تحديث شريط الحالة فقط في حالة الفشل هنا
            gui_utils.update_status_bar(root, status_bar_label, "فشل جلب الكوكيز", msg_type='error')

    return success, status_message
# ----------------------------------------------------


# --- Helper: Perform Reactivate Request ---
def _perform_reactivate(session: requests.Session, headers: dict, reactivation_payload: dict,
                        root: tk.Tk, status_text_widget: tk.Text, status_bar_label: ttk.Label,
                        cancel_retry_flag: tk.BooleanVar, cancel_retry_button: ttk.Button,
                        batch_cancel_all_flag: tk.BooleanVar) -> Tuple[bool, str]:
    """
    Sends the reactivate request with infinite connection retries.
    Returns: (bool: success status, str: detailed status message)
    """
    is_success = False
    response = None
    status_message = "فشل إعادة التفعيل (سبب غير معروف)" # Default status message
    connection_retry_count = 0

    while True:
        processing_retry_count = 0

        if batch_cancel_all_flag and batch_cancel_all_flag.get():
            status_message = "تم إلغاء الدفعة"
            gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
            is_success = False; break
        if cancel_retry_flag and cancel_retry_flag.get():
            status_message = "تم إلغاء المحاولة"
            gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
            is_success = False; break

        try:
            reactivate_headers = headers.copy()
            reactivate_headers['Content-Type'] = 'application/json'
            reactivate_headers['Referer'] = DEFAULT_REFERER_URL

            current_status = "جاري إعادة التفعيل..."
            if connection_retry_count > 0: current_status = f"جاري إعادة التفعيل (محاولة اتصال {connection_retry_count + 1})..."

            if connection_retry_count == 0:
                gui_utils.update_status_text(root, status_text_widget, "إرسال طلب إعادة التفعيل...", tags="api_info")
            gui_utils.update_status_bar(root, status_bar_label, current_status, msg_type='info')

            response = session.post(REACTIVATE_API_URL, headers=reactivate_headers, json=reactivation_payload, timeout=30, verify=False)
            response.raise_for_status()

            while processing_retry_count <= MAX_PROCESSING_RETRIES:
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; is_success = False; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; is_success = False; break

                try:
                    response_data = response.json()
                    response_state = response_data.get("State", "").lower()
                    response_code = response_data.get("Code")

                    if response_state == "success" and response_code == 1:
                        status_message = "تمت إعادة التفعيل بنجاح"
                        gui_utils.update_status_text(root, status_text_widget, status_message + ".", tags="api_success")
                        gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='success')
                        is_success = True; break
                    elif response_state == "success":
                        status_message = f"إعادة تفعيل ناجحة (رمز غير متوقع: {response_code})"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
                        gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
                        is_success = True; break
                    else:
                        error_msg = "فشل إعادة التفعيل"
                        errors_list = response_data.get("Errors", [])
                        error_details_str = ""
                        if errors_list and isinstance(errors_list, list) and len(errors_list) > 0:
                            error_details = [str(err.get('Message', err)) for err in errors_list if err]
                            if any("cookie" in str(err).lower() or "authentification" in str(err).lower() for err in error_details): error_details_str = " (الكوكي غير صالحة؟)"
                            else: error_details_str = f" ({error_details[0]})" if error_details else ""
                        else: error_details_str = f" (State: {response_state}, Code: {response_code})"
                        status_message = error_msg + error_details_str
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, error_msg, msg_type='error')
                        is_success = False; break

                except json.JSONDecodeError:
                    status_message = f"خطأ: رد الخادم غير صالح (ليس JSON) - رمز الحالة: {response.status_code}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1
                        gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                        gui_utils.update_status_bar(root, status_bar_label, f"رد غير صالح، محاولة معالجة {processing_retry_count}...", msg_type='warning')
                        if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        gui_utils.update_status_text(root, status_text_widget, status_message + "\n   فشلت جميع محاولات المعالجة.", tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: رد إعادة التفعيل غير صالح", msg_type='error')
                        is_success = False; break

                except Exception as json_e:
                    status_message = f"خطأ في معالجة رد إعادة التفعيل: {type(json_e).__name__}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1
                        gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                        gui_utils.update_status_bar(root, status_bar_label, f"خطأ معالجة، محاولة {processing_retry_count}...", msg_type='warning')
                        if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        gui_utils.update_status_text(root, status_text_widget, status_message + f"\n   التفاصيل: {json_e}\n   فشلت جميع محاولات المعالجة.", tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: فشل معالجة رد إعادة التفعيل", msg_type='error')
                        is_success = False; break
            break
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
            connection_retry_count += 1
            error_type = type(conn_err).__name__
            status_message = f"فشل الاتصال ({error_type})، محاولة {connection_retry_count + 1}..."
            gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
            gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
            if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
            time.sleep(RETRY_DELAY_SECONDS)
            if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
            if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
            continue
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            if status_code >= 500:
                connection_retry_count += 1
                status_message = f"خطأ خادم ({status_code})، محاولة {connection_retry_count + 1}..."
                gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
                gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
                if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                time.sleep(RETRY_DELAY_SECONDS)
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
                continue
            else:
                if status_code in [401, 403]: status_message = f"خطأ مصادقة ({status_code}) (الكوكي؟)"
                else: status_message = f"خطأ HTTP {status_code}"
                gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية: {http_err}", tags="api_error")
                gui_utils.update_status_bar(root, status_bar_label, f"خطأ HTTP {status_code}", msg_type='error')
                is_success = False; break
        except requests.exceptions.RequestException as req_e:
            error_type = type(req_e).__name__
            status_message = f"خطأ في الطلب ({error_type})"
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية: {req_e}", tags="api_error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ في الطلب", msg_type='error')
            is_success = False; break
        except Exception as e:
            error_type = type(e).__name__
            status_message = f"خطأ غير متوقع ({error_type}) أثناء إعادة التفعيل"
            print(f"Unexpected error during reactivate: {e}", file=sys.stderr)
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل: {e}", tags="api_error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ غير متوقع (إعادة تفعيل)", msg_type='error')
            is_success = False; break
        finally:
            if response is not None:
                try: response.close()
                except Exception: pass

    if cancel_retry_button: gui_utils.hide_widget(root, cancel_retry_button)
    if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; is_success = False
    if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; is_success = False
    return is_success, status_message


# --- Helper: Perform Extend Request ---
def _perform_extend_or_reactivate(session: requests.Session, headers: dict, nin: str, numero_wassit: str,
                                  root: tk.Tk, status_text_widget: tk.Text, status_bar_label: ttk.Label,
                                  cancel_retry_flag: tk.BooleanVar, cancel_retry_button: ttk.Button,
                                  batch_cancel_all_flag: tk.BooleanVar) -> Tuple[bool, str]:
    """
    Sends the extend request with infinite connection retries. If expired (Code 5), triggers reactivate.
    Returns: (bool: success status, str: detailed status message)
    """
    is_success = False
    response = None
    status_message = "فشل التجديد/الفحص (سبب غير معروف)" # Default
    connection_retry_count = 0

    while True:
        processing_retry_count = 0

        if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; is_success = False; break
        if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; is_success = False; break

        try:
            extend_headers = headers.copy()
            extend_headers['Content-Type'] = 'application/json'
            extend_headers['Referer'] = DEFAULT_REFERER_URL
            payload = {"nin": nin, "numeroWassit": numero_wassit}

            current_status = "جاري التجديد/الفحص..."
            if connection_retry_count > 0: current_status = f"جاري التجديد/الفحص (محاولة اتصال {connection_retry_count + 1})..."

            if connection_retry_count == 0:
                gui_utils.update_status_text(root, status_text_widget, "الخطوة 1: إرسال طلب التجديد/الفحص...", tags="api_info")
            gui_utils.update_status_bar(root, status_bar_label, current_status, msg_type='info')

            response = session.put(EXTEND_API_URL, headers=extend_headers, json=payload, timeout=30, verify=False)
            response.raise_for_status()

            while processing_retry_count <= MAX_PROCESSING_RETRIES:
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; is_success = False; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; is_success = False; break

                try:
                    response_data = response.json()
                    response_state = response_data.get("State", "").lower()
                    response_code = response_data.get("Code")

                    if response_code == 8:
                        status_message = "فشل: طلب منتهي ومهنة غير مفعلة"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='error')
                        is_success = False; break
                    elif response_code == 1:
                        status_message = "فشل: المعلومات المدخلة خاطئة (NIN/Numero)"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='error')
                        is_success = False; break
                    elif response_state == "success" and response_code == 4:
                        status_message = "تم التجديد بنجاح"
                        gui_utils.update_status_text(root, status_text_widget, status_message + ".", tags="api_success")
                        gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='success')
                        is_success = True; break
                    elif response_state == "success" and response_code == 5:
                        status_message = "الطلب منتهي، جاري محاولة إعادة التفعيل..."
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
                        gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
                        reactivation_payload = response_data.get("Result")
                        if reactivation_payload and isinstance(reactivation_payload, dict):
                            is_success, status_message = _perform_reactivate(session, headers, reactivation_payload, root, status_text_widget, status_bar_label, cancel_retry_flag, cancel_retry_button, batch_cancel_all_flag)
                            break
                        else:
                            status_message = "خطأ: بيانات إعادة التفعيل غير صالحة أو مفقودة بعد رد انتهاء الصلاحية"
                            gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                            gui_utils.update_status_bar(root, status_bar_label, "خطأ: بيانات إعادة التفعيل غير صالحة", msg_type='error')
                            is_success = False; break
                    # --- *** تم التعديل: معالجة الرمز 7 *** ---
                    elif response_state == "success" and response_code == 7:
                        status_message = "انتهت صلاحية طلبك ولا يمكن تمديده. يجب عليك التوجه إلى وكالة ANEM لإعادة التسجيل أو تقديم طلب جديد عبر موقع Wassit Online."
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
                        gui_utils.update_status_bar(root, status_bar_label, "انتهاء صلاحية الطلب (Code 7)", msg_type='warning')
                        is_success = False # يعتبر فشل منطقيًا
                        break
                    # --- *** نهاية التعديل *** ---
                    elif response_state != "success":
                         error_msg = "فشل التجديد/الفحص"
                         errors_list = response_data.get("Errors", []); error_details_str = ""
                         if errors_list and isinstance(errors_list, list) and len(errors_list) > 0:
                             error_details = [str(err.get('Message', err)) for err in errors_list if err]
                             if any("cookie" in str(err).lower() or "authentification" in str(err).lower() for err in error_details): error_details_str = " (الكوكي؟)"
                             else: error_details_str = f" ({error_details[0]})" if error_details else ""
                         else: error_details_str = f" (State: {response_state}, Code: {response_code})"
                         status_message = error_msg + error_details_str
                         gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                         gui_utils.update_status_bar(root, status_bar_label, f"فشل التجديد/الفحص (Code: {response_code})", msg_type='error')
                         is_success = False; break
                    else: # Success state but unexpected code (other than 4, 5, 7)
                         status_message = f"تجديد/فحص ناجح (رمز غير متوقع: {response_code})"
                         gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
                         gui_utils.update_status_bar(root, status_bar_label, "تنبيه: رد غير متوقع", msg_type='warning')
                         is_success = False; break # Consider failure for unexpected codes

                except json.JSONDecodeError:
                    status_message = f"خطأ: رد الخادم غير صالح (ليس JSON) - رمز الحالة: {response.status_code}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1
                        gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                        gui_utils.update_status_bar(root, status_bar_label, f"رد غير صالح، محاولة معالجة {processing_retry_count}...", msg_type='warning')
                        if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        gui_utils.update_status_text(root, status_text_widget, status_message + "\n   فشلت جميع محاولات المعالجة.", tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: رد التجديد/الفحص غير صالح", msg_type='error')
                        is_success = False; break

                except Exception as json_e:
                    status_message = f"خطأ في معالجة رد التجديد/الفحص: {type(json_e).__name__}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1
                        gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                        gui_utils.update_status_bar(root, status_bar_label, f"خطأ معالجة، محاولة {processing_retry_count}...", msg_type='warning')
                        if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        gui_utils.update_status_text(root, status_text_widget, status_message + f"\n   التفاصيل: {json_e}\n   فشلت جميع محاولات المعالجة.", tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: فشل معالجة رد التجديد/الفحص", msg_type='error')
                        is_success = False; break
            break
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
            connection_retry_count += 1
            error_type = type(conn_err).__name__
            status_message = f"فشل الاتصال ({error_type})، محاولة {connection_retry_count + 1}..."
            gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
            gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
            if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
            time.sleep(RETRY_DELAY_SECONDS)
            if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
            if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
            continue
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            if status_code >= 500:
                connection_retry_count += 1
                status_message = f"خطأ خادم ({status_code})، محاولة {connection_retry_count + 1}..."
                gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
                gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
                if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                time.sleep(RETRY_DELAY_SECONDS)
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
                continue
            else:
                if status_code in [401, 403]: status_message = f"خطأ مصادقة ({status_code}) (الكوكي؟)"; is_success = False
                else: status_message = f"خطأ HTTP {status_code}"; is_success = False
                gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية: {http_err}", tags="api_error")
                gui_utils.update_status_bar(root, status_bar_label, f"خطأ HTTP {status_code}", msg_type='error')
                break
        except requests.exceptions.RequestException as req_e:
            error_type = type(req_e).__name__
            status_message = f"خطأ في الطلب ({error_type})"
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية: {req_e}", tags="api_error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ في الطلب", msg_type='error')
            is_success = False; break
        except Exception as e:
            error_type = type(e).__name__
            status_message = f"خطأ غير متوقع ({error_type}) أثناء التجديد/الفحص"
            print(f"Unexpected error during extend/reactivate: {e}", file=sys.stderr)
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل: {e}", tags="api_error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ غير متوقع (تجديد/فحص)", msg_type='error')
            is_success = False; break
        finally:
            if response is not None:
                try: response.close()
                except Exception: pass

    if cancel_retry_button: gui_utils.hide_widget(root, cancel_retry_button)
    if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; is_success = False
    if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; is_success = False
    return is_success, status_message
# api_client.py (الجزء الثاني)
# ... (الكود من النصف الأول) ...

# --- Helper: Perform Download PDF Request ---
def _perform_download(session: requests.Session, headers: dict, nin: str, numero_wassit: str, print_pref: bool,
                      root: tk.Tk, status_text_widget: tk.Text, status_bar_label: ttk.Label,
                      cancel_retry_flag: tk.BooleanVar, cancel_retry_button: ttk.Button,
                      batch_cancel_all_flag: tk.BooleanVar) -> Tuple[bool, str]:
    """
    Sends the download request with infinite connection retries, decodes Base64, and schedules save/print.
    Returns: (bool: success status (save/dialog initiated), str: detailed status message)
    """
    response = None
    pdf_save_initiated = False
    status_message = "فشل التحميل (سبب غير معروف)" # Default
    saved_filepath = None
    connection_retry_count = 0

    while True:
        processing_retry_count = 0

        if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; pdf_save_initiated = False; break
        if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; pdf_save_initiated = False; break

        try:
            download_headers = headers.copy()
            download_headers['Referer'] = DEFAULT_REFERER_URL
            params = {'nin': nin, 'numeroWassit': numero_wassit}
            step_num_str = "الخطوة 2" if "الخطوة 1" in status_text_widget.get("1.0", "end-1c") else "الخطوة 1"

            current_status = "جاري تحميل الشهادة..."
            if connection_retry_count > 0: current_status = f"جاري تحميل الشهادة (محاولة اتصال {connection_retry_count + 1})..."

            if connection_retry_count == 0:
                gui_utils.update_status_text(root, status_text_widget, f"{step_num_str}: إرسال طلب تحميل الشهادة...", tags="api_info")
            gui_utils.update_status_bar(root, status_bar_label, current_status, msg_type='info')

            response = session.get(CERTIFICATE_API_URL, headers=download_headers, params=params, timeout=60, verify=False)
            response.raise_for_status() # Check HTTP errors first

            while processing_retry_count <= MAX_PROCESSING_RETRIES:
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; pdf_save_initiated = False; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; pdf_save_initiated = False; break

                base64_string = None; response_data = None
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = response.text
                    if isinstance(response_data, str) and (len(response_data) < 100 or '<html' in response_data.lower()):
                         if processing_retry_count < MAX_PROCESSING_RETRIES:
                             processing_retry_count += 1
                             status_message = f"خطأ: رد التحميل غير صالح (ليس JSON/Base64) - رمز الحالة: {response.status_code}"
                             gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                             gui_utils.update_status_bar(root, status_bar_label, f"رد تحميل غير صالح، محاولة معالجة {processing_retry_count}...", msg_type='warning')
                             if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                             time.sleep(RETRY_DELAY_SECONDS)
                             continue
                         else:
                             status_message = f"خطأ: رد التحميل غير صالح (ليس JSON/Base64) - رمز الحالة: {response.status_code}\n   فشلت جميع محاولات المعالجة."
                             gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                             gui_utils.update_status_bar(root, status_bar_label, "خطأ: رد التحميل غير صالح", msg_type='error')
                             pdf_save_initiated = False; break
                    elif isinstance(response_data, str) and len(response_data) > 100:
                        base64_string = response_data
                if isinstance(response_data, dict):
                    if isinstance(response_data.get('Result'), str) and len(response_data['Result']) > 100: base64_string = response_data['Result']
                    elif isinstance(response_data.get('result'), str) and len(response_data['result']) > 100: base64_string = response_data['result']
                    else:
                        errors_list = response_data.get("Errors", []); error_details_str = ""
                        if errors_list and isinstance(errors_list, list) and len(errors_list) > 0:
                            error_details = [str(err.get('Message', err)) for err in errors_list if err]
                            error_details_str = f" ({error_details[0]})" if error_details else ""
                        status_message = f"فشل التحميل: لم يتم العثور على بيانات الشهادة في الرد{error_details_str}"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "فشل: لم يتم العثور على بيانات الشهادة", msg_type='error')
                        pdf_save_initiated = False; break
                elif isinstance(response_data, str) and not base64_string:
                    if len(response_data) > 100: base64_string = response_data
                    else:
                        status_message = f"خطأ: رد التحميل نص قصير جدًا وغير صالح ({len(response_data)} حرف)"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: رد التحميل قصير جدًا", msg_type='error')
                        pdf_save_initiated = False; break
                elif not base64_string:
                     status_message = f"خطأ: نوع رد التحميل غير متوقع ({type(response_data)})"
                     gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                     gui_utils.update_status_bar(root, status_bar_label, "خطأ: نوع رد التحميل غير متوقع", msg_type='error')
                     pdf_save_initiated = False; break

                if base64_string:
                    status_message = "جاري فك تشفير الشهادة..."
                    gui_utils.update_status_text(root, status_text_widget, status_message, tags="info")
                    gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='info')
                    try:
                        cleaned_base64_string = base64_string
                        if isinstance(cleaned_base64_string, str) and cleaned_base64_string.startswith('"') and cleaned_base64_string.endswith('"'):
                            cleaned_base64_string = cleaned_base64_string[1:-1]
                        pdf_bytes = base64.b64decode(cleaned_base64_string)

                        if pdf_bytes.startswith(b'%PDF-'):
                            status_message = "البيانات صالحة (PDF)"
                            gui_utils.update_status_text(root, status_text_widget, status_message, tags="info")
                            default_filename = f"شهادة_تسجيل_{numero_wassit}.pdf"
                            default_save_path = settings_manager.get_default_save_path()

                            if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; pdf_save_initiated = False; break
                            if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; pdf_save_initiated = False; break

                            if default_save_path and file_handler.os.path.isdir(default_save_path):
                                filepath = file_handler.os.path.join(default_save_path, default_filename)
                                gui_utils.update_status_text(root, status_text_widget, f"استخدام مسار الحفظ الافتراضي: ", tags="info", add_newline=False)
                                gui_utils.update_status_text(root, status_text_widget, filepath, tags=("filepath", "info"), add_newline=True)
                                gui_utils.update_status_bar(root, status_bar_label, "جاري الحفظ في المسار الافتراضي...", msg_type='info')
                                save_success, status_message, saved_filepath = file_handler.write_pdf_to_file_sync(filepath, pdf_bytes, print_pref, root, status_text_widget, status_bar_label)
                                pdf_save_initiated = save_success
                                break
                            else:
                                if default_save_path and not file_handler.os.path.isdir(default_save_path):
                                    gui_utils.update_status_text(root, status_text_widget, f"تنبيه: مسار الحفظ الافتراضي '{default_save_path}' غير موجود. سيتم طلب مسار جديد.", tags="warning")
                                status_message = "في انتظار اختيار مسار الحفظ..."
                                gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='info')
                                gui_utils.schedule_gui_update(root, file_handler.ask_save_pdf_dialog_and_save, root, status_text_widget, status_bar_label, pdf_bytes, default_filename, print_pref)
                                pdf_save_initiated = True
                                status_message = "تم طلب مسار الحفظ من المستخدم"
                                break
                        else:
                            status_message = "خطأ: البيانات بعد فك التشفير ليست PDF صالح"
                            gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                            gui_utils.update_status_bar(root, status_bar_label, "خطأ: بيانات الشهادة غير صالحة", msg_type='error')
                            pdf_save_initiated = False; break
                    except base64.binascii.Error as b64_error:
                        status_message = f"فشل فك تشفير Base64: {b64_error}"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: فشل فك تشفير Base64", msg_type='error')
                        pdf_save_initiated = False; break
                    except Exception as decode_err:
                        status_message = f"خطأ غير متوقع أثناء معالجة الشهادة: {decode_err}"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: فشل معالجة الشهادة", msg_type='error')
                        pdf_save_initiated = False; break
                else:
                    pdf_save_initiated = False; break
            break
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
            connection_retry_count += 1
            error_type = type(conn_err).__name__
            status_message = f"فشل الاتصال ({error_type})، محاولة {connection_retry_count + 1}..."
            gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
            gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
            if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
            time.sleep(RETRY_DELAY_SECONDS)
            if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
            if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
            continue
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            if status_code >= 500:
                connection_retry_count += 1
                status_message = f"خطأ خادم ({status_code})، محاولة {connection_retry_count + 1}..."
                gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
                gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
                if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                time.sleep(RETRY_DELAY_SECONDS)
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
                continue
            else:
                if status_code in [401, 403]: status_message = f"خطأ مصادقة ({status_code}) (الكوكي؟)"; pdf_save_initiated = False
                else: status_message = f"خطأ HTTP {status_code}"; pdf_save_initiated = False
                gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية: {http_err}", tags="api_error")
                gui_utils.update_status_bar(root, status_bar_label, f"خطأ HTTP {status_code}", msg_type='error')
                break
        except requests.exceptions.RequestException as req_e:
            error_type = type(req_e).__name__
            status_message = f"خطأ في الطلب ({error_type})"
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية: {req_e}", tags="api_error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ في الطلب", msg_type='error')
            pdf_save_initiated = False; break
        except Exception as e:
            error_type = type(e).__name__
            status_message = f"خطأ غير متوقع ({error_type}) أثناء التحميل"
            print(f"Unexpected error during download: {e}", file=sys.stderr)
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل: {e}", tags="api_error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ غير متوقع (تحميل)", msg_type='error')
            pdf_save_initiated = False; break
        finally:
            if response is not None:
                try: response.close()
                except Exception: pass

    if cancel_retry_button: gui_utils.hide_widget(root, cancel_retry_button)
    if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; pdf_save_initiated = False
    if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; pdf_save_initiated = False
    return pdf_save_initiated, status_message


# --- *** تمت الإضافة: دالة جلب بيانات التحقق والمعرفات للمواعيد *** ---
def _get_validation_and_ids(session: requests.Session, nin: str, numero_wassit: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Sends the validateCandidate request to get IDs and status for appointment check.
    Returns: (bool: request success, str: status message, dict: {'structureId': Optional[str], 'preInscriptionId': Optional[str], 'eligible': Optional[bool], 'haveAllocation': Optional[bool], 'rejetAllocation': Optional[bool], 'haveRendezVous': Optional[bool], 'detailsAllocation': Optional[dict]})
    """
    response = None
    request_successful = False
    result_data = {
        'structureId': None,
        'preInscriptionId': None,
        'eligible': None,
        'haveAllocation': None,
        'rejetAllocation': None,
        'haveRendezVous': None,
        'detailsAllocation': None # لإضافة تفاصيل المنحة
    }
    status_message = "فشل جلب بيانات التحقق الأولية"
    connection_retry_count = 0
    processing_retry_count = 0

    while True:
        if connection_retry_count > 0: time.sleep(RETRY_DELAY_SECONDS)

        try:
            params = {'wassitNumber': numero_wassit, 'identityDocNumber': nin}
            allocation_headers = {'Accept': 'application/json, text/plain, */*', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.9,ar-DZ;q=0.8', 'Connection': 'keep-alive', 'Host': 'ac-controle.anem.dz', 'Origin': ALLOCATION_ORIGIN, 'Referer': ALLOCATION_REFERER, 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'User-Agent': USER_AGENT, 'Sec-Ch-Ua': '"Chromium";v="135", "Not-A.Brand";v="8"', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Ch-Ua-Platform': '"Windows"'}

            print(f"[_get_validation_and_ids] Sending request (Attempt: {connection_retry_count + 1})...")
            response = requests.get(ALLOCATION_API_URL, headers=allocation_headers, params=params, timeout=20, verify=False)
            response.raise_for_status()

            while processing_retry_count <= MAX_PROCESSING_RETRIES:
                try:
                    response_data = response.json()
                    if response_data.get("validInput") is False:
                        status_message = "فشل التحقق الأولي: إدخال غير صالح (NIN/Numero؟)"
                        request_successful = False; break
                    else:
                        result_data['structureId'] = response_data.get("structureId")
                        result_data['preInscriptionId'] = response_data.get("preInscriptionId")
                        result_data['eligible'] = response_data.get("eligible")
                        result_data['haveAllocation'] = response_data.get("haveAllocation")
                        result_data['rejetAllocation'] = response_data.get('rejetAllocation', False)
                        result_data['haveRendezVous'] = response_data.get('haveRendezVous')
                        result_data['detailsAllocation'] = response_data.get('detailsAllocation') # جلب تفاصيل المنحة
                        status_message = "تم جلب بيانات التحقق الأولية بنجاح."
                        request_successful = True; break

                except json.JSONDecodeError:
                    status_message = f"خطأ في التحقق الأولي: رد غير صالح (ليس JSON) - {response.status_code}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1; time.sleep(1); continue
                    else: request_successful = False; break
                except Exception as json_e:
                    status_message = f"خطأ في معالجة رد التحقق الأولي: {type(json_e).__name__}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1; time.sleep(1); continue
                    else: request_successful = False; break
            break
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
            connection_retry_count += 1
            status_message = f"فشل الاتصال للتحقق الأولي ({type(conn_err).__name__}), محاولة {connection_retry_count + 1}..."
            print(f"[_get_validation_and_ids] {status_message}")
            continue
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            if status_code >= 500:
                connection_retry_count += 1
                status_message = f"خطأ خادم ({status_code}) في التحقق الأولي، محاولة {connection_retry_count + 1}..."
                print(f"[_get_validation_and_ids] {status_message}")
                continue
            else:
                status_message = f"خطأ HTTP {status_code} في التحقق الأولي."
                print(f"[_get_validation_and_ids] {status_message} - {http_err}")
                request_successful = False; break
        except requests.exceptions.RequestException as req_e:
            status_message = f"خطأ في طلب التحقق الأولي ({type(req_e).__name__})"
            print(f"[_get_validation_and_ids] {status_message} - {req_e}")
            request_successful = False; break
        except Exception as e:
            status_message = f"خطأ غير متوقع ({type(e).__name__}) في التحقق الأولي"
            print(f"[_get_validation_and_ids] {status_message} - {e}", file=sys.stderr)
            request_successful = False; break
        finally:
            if response is not None:
                try: response.close()
                except Exception: pass

    print(f"[_get_validation_and_ids] Result: Success={request_successful}, Msg='{status_message}', Data={result_data}")
    return request_successful, status_message, result_data
# --------------------------------------------------------------------


# --- *** تم التعديل: دالة للتحقق من حالة الموعد الحالي وحالة المنحة وتحديث الواجهة *** ---
def _check_existing_appointment_status(root: tk.Tk, nin: str, numero_wassit: str,
                                       appointment_status_label_widget: ttk.Label,
                                       cancel_retry_flag: tk.BooleanVar,
                                       batch_cancel_all_flag: tk.BooleanVar):
    """
    Gets validation data and updates the appointment status label based on 'haveRendezVous'
    and unemployment benefit status from 'detailsAllocation'.
    Runs independently and updates the GUI.
    """
    if not root or not root.winfo_exists(): print("Error: Root window destroyed (_check_existing_appointment_status)."); return
    if not appointment_status_label_widget or not appointment_status_label_widget.winfo_exists(): print("Error: Appointment label destroyed (_check_existing_appointment_status)."); return

    print(f"[_check_existing_appointment_status] Starting check for NIN: {nin[-4:]}")
    # تم تمرير None كقيمة ابتدائية لحالة المنحة أيضاً
    gui_utils.update_appointment_status_label(root, appointment_status_label_widget, None, None, None)


    session = requests.Session()
    try:
        success, msg, data = _get_validation_and_ids(session, nin, numero_wassit)

        if batch_cancel_all_flag and batch_cancel_all_flag.get():
            print("[_check_existing_appointment_status] Batch cancelled during check.")
            gui_utils.update_appointment_status_label(root, appointment_status_label_widget, None, None, None)
            return
        if cancel_retry_flag and cancel_retry_flag.get():
            print("[_check_existing_appointment_status] Retry cancelled during check.")
            gui_utils.update_appointment_status_label(root, appointment_status_label_widget, None, None, None)
            return

        if success:
            have_appointment = data.get('haveRendezVous')
            details_allocation = data.get('detailsAllocation')
            benefit_status_code = None
            benefit_status_text = "غير متوفرة" # نص افتراضي لحالة المنحة

            if isinstance(details_allocation, dict):
                benefit_status_code = details_allocation.get('etat') # 1: نشطة, 0: موقوفة, 2: ملغاة
                # يمكنك إضافة المزيد من التفاصيل هنا إذا أردت، مثل سبب الإيقاف أو الإلغاء
                # benefit_status_text = f"رمز الحالة: {benefit_status_code}"
                if benefit_status_code == 1:
                    benefit_status_text = "نشطة"
                elif benefit_status_code == 0:
                    benefit_status_text = "موقوفة مؤقتًا"
                elif benefit_status_code == 2:
                    benefit_status_text = "ملغاة"
                else:
                    benefit_status_text = f"غير معروفة ({benefit_status_code})"

            if have_appointment is True:
                print("[_check_existing_appointment_status] Appointment found (haveRendezVous=True).")
                gui_utils.update_appointment_status_label(root, appointment_status_label_widget, True, benefit_status_code, benefit_status_text)
            elif have_appointment is False:
                print("[_check_existing_appointment_status] No appointment found (haveRendezVous=False).")
                gui_utils.update_appointment_status_label(root, appointment_status_label_widget, False, benefit_status_code, benefit_status_text)
            else: # have_appointment is None or not present
                print("[_check_existing_appointment_status] Appointment status unknown (haveRendezVous missing or null).")
                gui_utils.update_appointment_status_label(root, appointment_status_label_widget, None, benefit_status_code, benefit_status_text)
        else:
            print(f"[_check_existing_appointment_status] Failed to get validation data: {msg}")
            gui_utils.update_appointment_status_label(root, appointment_status_label_widget, None, None, None) # تمرير None لحالة المنحة عند الفشل

    except Exception as e:
        print(f"[_check_existing_appointment_status] Unexpected error: {type(e).__name__} - {e}", file=sys.stderr)
        gui_utils.update_appointment_status_label(root, appointment_status_label_widget, None, None, None) # تمرير None لحالة المنحة عند الخطأ
    finally:
        session.close()
        print(f"[_check_existing_appointment_status] Finished check for NIN: {nin[-4:]}")
# --------------------------------------------------------------------------


# --- Helper: Perform Allocation Status Request ---
def _perform_allocation_status(session: requests.Session, headers_ignored: dict, nin: str, numero_wassit: str,
                               root: tk.Tk, status_text_widget: tk.Text, status_bar_label: ttk.Label,
                               cancel_retry_flag: tk.BooleanVar, cancel_retry_button: ttk.Button,
                               batch_cancel_all_flag: tk.BooleanVar) -> Tuple[bool, str]:
    """
    Sends the request to get allocation status with infinite connection retries.
    Returns: (bool: success status of allocation query, str: detailed status message of allocation query)
    """
    response = None
    request_successful = False
    status_message = "فشل الاستعلام عن المنحة (سبب غير معروف)"
    connection_retry_count = 0
    control_name_map = {"validityDemande": "صلاحية الطلب", "matchIdentity": "مطابقة الهوية", "situationServiceMilitaire": "وضعية الخدمة الوطنية", "validityAge": "صلاحية السن", "Controle ANEM": "تحقق ANEM الداخلي"}
    final_status_bar_msg_type = 'error'

    def format_date(date_str):
        if isinstance(date_str, str) and "T" in date_str:
            try: return date_str.split("T")[0]
            except: return "غير متوفر"
        return date_str if date_str else "غير متوفر"
    def add_detail_line(label, value, tag="allocation_data"):
        gui_utils.update_status_text(root, status_text_widget, f"  {label}: {value}", tags=tag)

    while True:
        processing_retry_count = 0
        if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; request_successful = False; break
        if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; request_successful = False; break

        try:
            params = {'wassitNumber': numero_wassit, 'identityDocNumber': nin}
            allocation_headers = {'Accept': 'application/json, text/plain, */*', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.9,ar-DZ;q=0.8', 'Connection': 'keep-alive', 'Host': 'ac-controle.anem.dz', 'Origin': ALLOCATION_ORIGIN, 'Referer': ALLOCATION_REFERER, 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'User-Agent': USER_AGENT, 'Sec-Ch-Ua': '"Chromium";v="135", "Not-A.Brand";v="8"', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Ch-Ua-Platform': '"Windows"'}

            current_status = "جاري الاستعلام عن حالة المنحة..."
            if connection_retry_count > 0: current_status = f"جاري الاستعلام عن حالة المنحة (محاولة اتصال {connection_retry_count + 1})..."

            if connection_retry_count == 0:
                 gui_utils.update_status_text(root, status_text_widget, "إرسال طلب الاستعلام عن حالة المنحة...", tags="api_info")
            gui_utils.update_status_bar(root, status_bar_label, current_status, msg_type='info')

            response = session.get(ALLOCATION_API_URL, headers=allocation_headers, params=params, timeout=30, verify=False)
            response.raise_for_status()

            while processing_retry_count <= MAX_PROCESSING_RETRIES:
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; request_successful = False; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; request_successful = False; break

                try:
                    response_data = response.json()

                    if response_data.get("validInput") is False:
                        status_message = "لا يمكن معالجة تسجيلك في الوقت الحالي ! الرجاء إعادة المحاولة لاحقا"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        final_status_bar_msg_type = 'error'
                        request_successful = False
                        break

                    gui_utils.update_status_text(root, status_text_widget, "", tags="separator")
                    gui_utils.update_status_text(root, status_text_widget, "--- 📊 حالة منحة البطالة 📊 ---", tags=("allocation_header", "center"))

                    eligible = response_data.get("eligible")
                    have_allocation = response_data.get("haveAllocation")
                    rejet_allocation = response_data.get('rejetAllocation', False)
                    details = response_data.get("detailsAllocation")
                    motif_rejet = response_data.get("motifRejet", "") if rejet_allocation else ""
                    controls = response_data.get("controls", [])

                    gui_utils.update_status_text(root, status_text_widget, "الأهلية والحالة العامة:", tags=("allocation_subheader"))
                    add_detail_line("هل أنت مؤهل للمنحة؟", 'نعم' if eligible else 'لا', tag="allocation_info" if eligible else "allocation_warning")
                    add_detail_line("هل لديك منحة نشطة حاليًا؟", 'نعم' if have_allocation else 'لا', tag="allocation_success" if have_allocation else "allocation_info")

                    current_status_summary = ""
                    if rejet_allocation: current_status_summary = f"مرفوض (السبب: {motif_rejet})" if motif_rejet else "مرفوض (سبب غير محدد)"; status_tag = "allocation_error"; final_status_bar_msg_type = 'error'
                    elif eligible and have_allocation: current_status_summary = "نشطة ومستمرة"; status_tag = "allocation_success"; final_status_bar_msg_type = 'success'
                    elif eligible and not have_allocation: current_status_summary = "مؤهل ولكن غير نشطة (قيد الدراسة؟)"; status_tag = "allocation_warning"; final_status_bar_msg_type = 'warning'
                    elif not eligible: current_status_summary = "غير مؤهل"; status_tag = "allocation_error"; final_status_bar_msg_type = 'error'
                    else: current_status_summary = "حالة غير محددة"; status_tag = "allocation_info"; final_status_bar_msg_type = 'info'
                    add_detail_line("وضع طلب المنحة", current_status_summary, tag=status_tag)

                    if isinstance(details, dict):
                        gui_utils.update_status_text(root, status_text_widget, "التفاصيل الشخصية وتفاصيل المنحة:", tags=("allocation_subheader"))
                        add_detail_line("الاسم (لاتيني)", f"{details.get('nomFr', '-')} {details.get('prenomFr', '')}")
                        add_detail_line("الاسم (عربي)", f"{details.get('nomAr', '-')} {details.get('prenomAr', '')}")
                        add_detail_line("تاريخ الميلاد", format_date(details.get("dateNaissance")))
                        add_detail_line("NIN المستخدم", details.get("nin", nin))
                        etat_code = details.get("etat"); motif_ar = details.get("motifAr", "سبب غير محدد")
                        etat_str_map = { 1: "نشطة ✅", 0: "موقوفة مؤقتًا ⛔", 2: "ملغاة ❌" }; etat_str = etat_str_map.get(etat_code, f"غير معروف ({etat_code}) ❓")
                        etat_tag = "allocation_success" if etat_code == 1 else "allocation_warning" if etat_code == 0 else "allocation_error" if etat_code == 2 else "allocation_info"
                        add_detail_line("وضعية المنحة الحالية", etat_str, tag=etat_tag)
                        if etat_code == 1: add_detail_line("تاريخ بداية الصرف", format_date(details.get("dateDebut")))
                        if etat_code == 0: add_detail_line("سبب الإيقاف المؤقت", motif_ar, tag="allocation_warning")
                        elif etat_code == 2: add_detail_line("سبب الإلغاء", motif_ar, tag="allocation_error")
                        add_detail_line("الوكالة المحلية للتشغيل (ALEM)", details.get("intituleAlemAr", "غير متوفر"))
                        add_detail_line("رمز الوكالة", details.get("codeAlem", "غير متوفر"))
                        motif_rejet_details = details.get("motifRejet", "")
                        if rejet_allocation and motif_rejet_details and motif_rejet_details != motif_rejet: add_detail_line("سبب الرفض (تفاصيل إضافية)", motif_rejet_details, tag="allocation_error")

                    elif not eligible: gui_utils.update_status_text(root, status_text_widget, "ملاحظة: بما أنك غير مؤهل، لا توجد تفاصيل إضافية لعرضها.", tags="allocation_note")
                    else: gui_utils.update_status_text(root, status_text_widget, "ملاحظة: لا توجد تفاصيل إضافية متاحة حاليًا (قد يكون الطلب قيد الدراسة أو لم يتم التقديم).", tags="allocation_note")

                    if isinstance(controls, list) and controls:
                        gui_utils.update_status_text(root, status_text_widget, "--- 🔍 تفاصيل عمليات التحقق 🔍 ---", tags=("allocation_subheader", "center"))
                        for control in controls:
                            control_name = control.get("name", "تحقق غير معروف"); control_result = control.get("result", False); control_source = control.get("source", "")
                            arabic_name = control_name_map.get(control_name, control_name)
                            result_str = "تم بنجاح ✅" if control_result else "فشل ❌"; result_tag = "allocation_control_success" if control_result else "allocation_control_fail"
                            source_info = f" (المصدر: {control_source})" if control_source else ""
                            gui_utils.update_status_text(root, status_text_widget, f"  - {arabic_name}{source_info}: {result_str}", tags=(result_tag,))

                    gui_utils.update_status_text(root, status_text_widget, "", tags="separator")
                    gui_utils.update_status_text(root, status_text_widget, "اكتمل الاستعلام عن حالة المنحة بنجاح.", tags="api_success")

                    status_message = f"تم الاستعلام عن المنحة بنجاح ({current_status_summary})"
                    request_successful = True
                    break

                except json.JSONDecodeError:
                    status_message = f"خطأ: رد الخادم غير صالح (ليس JSON) - رمز الحالة: {response.status_code}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1
                        gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                        gui_utils.update_status_bar(root, status_bar_label, f"رد غير صالح، محاولة معالجة {processing_retry_count}...", msg_type='warning')
                        if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        gui_utils.update_status_text(root, status_text_widget, status_message + "\n   فشلت جميع محاولات المعالجة.", tags="api_error")
                        final_status_bar_msg_type = 'error'
                        request_successful = False; break

                except Exception as json_e:
                    status_message = f"خطأ في معالجة رد حالة المنحة: {type(json_e).__name__}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1
                        gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                        gui_utils.update_status_bar(root, status_bar_label, f"خطأ معالجة، محاولة {processing_retry_count}...", msg_type='warning')
                        if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        gui_utils.update_status_text(root, status_text_widget, status_message + f"\n   التفاصيل: {json_e}\n   فشلت جميع محاولات المعالجة.", tags="api_error")
                        final_status_bar_msg_type = 'error'
                        request_successful = False; break
            break
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
            connection_retry_count += 1
            error_type = type(conn_err).__name__
            status_message = f"فشل الاتصال ({error_type})، محاولة {connection_retry_count + 1}..."
            gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
            gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
            if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
            time.sleep(RETRY_DELAY_SECONDS)
            if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
            if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
            continue
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code; error_msg_detail = ""
            try: error_data = http_err.response.json(); errors_list = error_data.get("Errors", [])
            except (json.JSONDecodeError, Exception): error_msg_detail = f"\n  (لم يتمكن من قراءة تفاصيل إضافية من رد الخطأ)"
            else:
                if errors_list and isinstance(errors_list, list) and len(errors_list) > 0: error_details = [str(err.get('Message', err)) for err in errors_list if err]; error_msg_detail = f" ({error_details[0]})" if error_details else ""
                elif error_data: error_msg_detail = f"\n  رد الخادم: {json.dumps(error_data, ensure_ascii=False)}"

            if status_code >= 500:
                connection_retry_count += 1
                status_message = f"خطأ خادم ({status_code})، محاولة {connection_retry_count + 1}..."
                gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
                gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
                if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                time.sleep(RETRY_DELAY_SECONDS)
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
                continue
            else:
                if status_code in [401, 403]: status_message = f"خطأ مصادقة أو صلاحية ({status_code})"; request_successful = False
                elif status_code == 400: status_message = f"خطأ في الطلب ({status_code}) (NIN/Numero؟)"; request_successful = False
                elif status_code == 404: status_message = f"خطأ: نقطة النهاية غير موجودة ({status_code})"; request_successful = False
                else: status_message = f"خطأ HTTP {status_code}"; request_successful = False
                status_message += error_msg_detail
                gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية للطلب: {http_err}", tags="api_error")
                final_status_bar_msg_type = 'error'
                break
        except requests.exceptions.RequestException as req_e:
            error_type = type(req_e).__name__
            status_message = f"خطأ في الطلب ({error_type})"
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية: {req_e}", tags="api_error")
            final_status_bar_msg_type = 'error'
            request_successful = False; break
        except Exception as e:
            error_type = type(e).__name__
            status_message = f"خطأ غير متوقع ({error_type}) أثناء الاستعلام عن المنحة"
            print(f"Unexpected error during allocation status: {e}", file=sys.stderr)
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل: {e}", tags="api_error")
            final_status_bar_msg_type = 'error'
            request_successful = False; break
        finally:
            if response is not None:
                try: response.close()
                except Exception: pass

    if cancel_retry_button: gui_utils.hide_widget(root, cancel_retry_button)
    if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; request_successful = False
    if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; request_successful = False

    gui_utils.update_status_bar(root, status_bar_label, status_message.split('(')[0].strip(), msg_type=final_status_bar_msg_type)

    return request_successful, status_message


# --- Helper: Perform Change Mobile Request ---
def _perform_change_mobile(session: requests.Session, headers: dict, nin: str, numero_wassit: str, new_mobile: str,
                           root: tk.Tk, status_text_widget: tk.Text, status_bar_label: ttk.Label,
                           cancel_retry_flag: tk.BooleanVar, cancel_retry_button: ttk.Button,
                           batch_cancel_all_flag: tk.BooleanVar) -> Tuple[bool, str]:
    """
    Sends the request to change the mobile number with infinite connection retries.
    Returns: (bool: success status, str: detailed status message)
    """
    response = None
    is_success = False
    status_message = "فشل تغيير الهاتف (سبب غير معروف)"
    connection_retry_count = 0

    while True:
        processing_retry_count = 0

        if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; is_success = False; break
        if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; is_success = False; break

        try:
            change_headers = headers.copy()
            change_headers['Content-Type'] = 'application/json'
            change_headers['Referer'] = CHANGE_MOBILE_REFERER_URL
            change_headers['Origin'] = DEFAULT_ORIGIN_URL
            payload = {"nin": nin, "numeroWassit": numero_wassit, "mobile": new_mobile}

            current_status = "جاري تغيير رقم الهاتف..."
            if connection_retry_count > 0: current_status = f"جاري تغيير رقم الهاتف (محاولة اتصال {connection_retry_count + 1})..."

            if connection_retry_count == 0:
                gui_utils.update_status_text(root, status_text_widget, "إرسال طلب تغيير رقم الهاتف...", tags="api_info")
            gui_utils.update_status_bar(root, status_bar_label, current_status, msg_type='info')

            response = session.post(CHANGE_MOBILE_API_URL, headers=change_headers, json=payload, timeout=30, verify=False)
            response.raise_for_status()

            while processing_retry_count <= MAX_PROCESSING_RETRIES:
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; is_success = False; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; is_success = False; break

                try:
                    response_data = response.json()
                    response_state = response_data.get("State", "").lower()
                    response_code = response_data.get("Code")

                    if response_code == 5:
                        status_message = f"فشل: رقم الهاتف ({new_mobile}) مطابق للقديم"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
                        gui_utils.update_status_bar(root, status_bar_label, "فشل: رقم الهاتف مطابق", msg_type='warning')
                        is_success = False; break
                    elif response_code == 4:
                        status_message = f"فشل: رقم الهاتف ({new_mobile}) مستخدم"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "فشل: رقم الهاتف مستخدم", msg_type='error')
                        is_success = False; break
                    elif response_state == "error" and response_code == 2:
                        status_message = "فشل: المعلومات المدخلة خاطئة (NIN/Numero؟)"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "فشل: معلومات خاطئة", msg_type='error')
                        is_success = False; break
                    elif response_state == "success" and response_code == 1:
                        status_message = f"تم تغيير رقم الهاتف بنجاح إلى {new_mobile}"
                        gui_utils.update_status_text(root, status_text_widget, status_message + ".", tags="api_success")
                        gui_utils.update_status_bar(root, status_bar_label, "تم تغيير رقم الهاتف بنجاح", msg_type='success')
                        is_success = True; break
                    elif response_state == "success":
                        status_message = f"تغيير ناجح (رمز غير متوقع: {response_code})"
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_warning")
                        gui_utils.update_status_bar(root, status_bar_label, f"نجح تغيير الهاتف (Code: {response_code})", msg_type='warning')
                        is_success = True; break
                    else:
                        error_msg = "فشل تغيير الهاتف"
                        errors_list = response_data.get("Errors", []); error_details_str = ""
                        if errors_list and isinstance(errors_list, list) and len(errors_list) > 0:
                            error_details = [str(err.get('Message', err)) for err in errors_list if err]
                            if any("cookie" in str(err).lower() or "authentification" in str(err).lower() for err in error_details): error_details_str = " (الكوكي؟)"
                            else: error_details_str = f" ({error_details[0]})" if error_details else ""
                        else: error_details_str = f" (State: {response_state}, Code: {response_code})"
                        status_message = error_msg + error_details_str
                        gui_utils.update_status_text(root, status_text_widget, status_message, tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, error_msg, msg_type='error')
                        is_success = False; break

                except json.JSONDecodeError:
                    status_message = f"خطأ: رد الخادم غير صالح (ليس JSON) - رمز الحالة: {response.status_code}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1
                        gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                        gui_utils.update_status_bar(root, status_bar_label, f"رد غير صالح، محاولة معالجة {processing_retry_count}...", msg_type='warning')
                        if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        gui_utils.update_status_text(root, status_text_widget, status_message + "\n   فشلت جميع محاولات المعالجة.", tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: رد تغيير الهاتف غير صالح", msg_type='error')
                        is_success = False; break

                except Exception as json_e:
                    status_message = f"خطأ في معالجة رد تغيير الهاتف: {type(json_e).__name__}"
                    if processing_retry_count < MAX_PROCESSING_RETRIES:
                        processing_retry_count += 1
                        gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   محاولة معالجة {processing_retry_count}/{MAX_PROCESSING_RETRIES} بعد {RETRY_DELAY_SECONDS} ثواني...", tags="api_retry")
                        gui_utils.update_status_bar(root, status_bar_label, f"خطأ معالجة، محاولة {processing_retry_count}...", msg_type='warning')
                        if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        gui_utils.update_status_text(root, status_text_widget, status_message + f"\n   التفاصيل: {json_e}\n   فشلت جميع محاولات المعالجة.", tags="api_error")
                        gui_utils.update_status_bar(root, status_bar_label, "خطأ: فشل معالجة رد تغيير الهاتف", msg_type='error')
                        is_success = False; break
            break
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
            connection_retry_count += 1
            error_type = type(conn_err).__name__
            status_message = f"فشل الاتصال ({error_type})، محاولة {connection_retry_count + 1}..."
            gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
            gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
            if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
            time.sleep(RETRY_DELAY_SECONDS)
            if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
            if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
            continue
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code; error_msg_detail = ""
            try: error_data = http_err.response.json(); errors_list = error_data.get("Errors", [])
            except (json.JSONDecodeError, Exception): error_msg_detail = f"\n  (لم يتمكن من قراءة تفاصيل إضافية من رد الخطأ)"
            else:
                if errors_list and isinstance(errors_list, list) and len(errors_list) > 0: error_details = [str(err.get('Message', err)) for err in errors_list if err]; error_msg_detail = f" ({error_details[0]})" if error_details else ""
                elif error_data: error_msg_detail = f"\n  رد الخادم: {json.dumps(error_data, ensure_ascii=False)}"

            if status_code >= 500:
                connection_retry_count += 1
                status_message = f"خطأ خادم ({status_code})، محاولة {connection_retry_count + 1}..."
                gui_utils.update_status_text(root, status_text_widget, f"⚠️ {status_message}\n   (انتظار {RETRY_DELAY_SECONDS} ثواني... اضغط 'إلغاء المحاولة' للإيقاف)", tags="api_retry")
                gui_utils.update_status_bar(root, status_bar_label, status_message, msg_type='warning')
                if cancel_retry_button: gui_utils.show_widget(root, cancel_retry_button)
                time.sleep(RETRY_DELAY_SECONDS)
                if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; break
                if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; break
                continue
            else:
                if status_code in [401, 403]: status_message = f"خطأ مصادقة ({status_code}) (الكوكي؟)"; is_success = False
                else: status_message = f"خطأ HTTP {status_code}"; is_success = False
                status_message += error_msg_detail
                gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية للطلب: {http_err}", tags="api_error")
                gui_utils.update_status_bar(root, status_bar_label, f"خطأ HTTP {status_code}", msg_type='error')
                break
        except requests.exceptions.RequestException as req_e:
            error_type = type(req_e).__name__
            status_message = f"خطأ في الطلب ({error_type})"
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل الفنية: {req_e}", tags="api_error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ في الطلب", msg_type='error')
            is_success = False; break
        except Exception as e:
            error_type = type(e).__name__
            status_message = f"خطأ غير متوقع ({error_type}) أثناء تغيير الهاتف"
            print(f"Unexpected error during change mobile: {e}", file=sys.stderr)
            gui_utils.update_status_text(root, status_text_widget, f"❌ {status_message}\n   التفاصيل: {e}", tags="api_error")
            gui_utils.update_status_bar(root, status_bar_label, "خطأ غير متوقع (تغيير الهاتف)", msg_type='error')
            is_success = False; break
        finally:
            if response is not None:
                try: response.close()
                except Exception: pass

    if cancel_retry_button: gui_utils.hide_widget(root, cancel_retry_button)
    if batch_cancel_all_flag and batch_cancel_all_flag.get(): status_message = "تم إلغاء الدفعة"; is_success = False
    if cancel_retry_flag and cancel_retry_flag.get(): status_message = "تم إلغاء المحاولة"; is_success = False
    return is_success, status_message

# --- Main API Request Function (Orchestrator) ---
def make_api_request(root: tk.Tk, request_type: str, nin: str, numero_wassit: str,
                     status_text_widget: tk.Text, status_bar_label: ttk.Label, progress_bar_widget: ttk.Progressbar,
                     buttons_list: list, clicked_button: Optional[ttk.Button], original_text: str,
                     new_mobile: Optional[str] = None, print_pref: bool = False,
                     cancel_retry_flag: Optional[tk.BooleanVar] = None, cancel_retry_button: Optional[ttk.Button] = None,
                     batch_cancel_all_flag: Optional[tk.BooleanVar] = None) -> Tuple[bool, str]:
    """
    Orchestrates the API requests based on request_type. Runs in a separate thread.
    Relies on helper functions which now contain infinite retry logic.
    Returns: (bool: overall success status, str: final status message)
    """
    if cancel_retry_flag is None: cancel_retry_flag = tk.BooleanVar(value=False)
    if batch_cancel_all_flag is None: batch_cancel_all_flag = tk.BooleanVar(value=False)

    final_status_message = f"فشل عملية '{request_type}' (سبب غير معروف)"
    overall_success = False

    if not root or not root.winfo_exists(): print("Error: Root window destroyed."); return False, "خطأ: النافذة مغلقة"
    if not status_text_widget or not status_text_widget.winfo_exists(): print("Error: Status text widget destroyed."); return False, "خطأ: عنصر الحالة غير متاح"
    if not status_bar_label or not status_bar_label.winfo_exists(): print("Error: Status bar label destroyed."); return False, "خطأ: شريط الحالة غير متاح"

    gui_utils.update_status_text(root, status_text_widget, f"بدء عملية: {request_type}...", clear=True, tags="api_start")
    gui_utils.update_status_bar(root, status_bar_label, f"جاري {request_type}...", msg_type='info')

    warnings.filterwarnings('ignore', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)
    current_cookie = settings_manager.get_cookie()

    if not current_cookie or not current_cookie.strip():
         final_status_message = "خطأ: الكوكي فارغة أو غير معرفة"
         error_msg = "الكوكي فارغة أو غير معرفة. لا يمكن متابعة الطلبات.\n"
         error_msg += "1. تأكد من أن البرنامج استطاع جلب الكوكيز عند بدء التشغيل.\n"
         error_msg += "2. إذا فشل الجلب التلقائي، يمكنك إضافتها يدويًا عبر قائمة 'الإعدادات > تغيير الكوكي الحالية'."
         gui_utils.update_status_text(root, status_text_widget, error_msg, tags="api_error")
         gui_utils.update_status_bar(root, status_bar_label, final_status_message, msg_type='error')
         if clicked_button and buttons_list: gui_utils.restore_button_state(root, buttons_list, clicked_button, original_text, cancel_retry_button)
         if progress_bar_widget and progress_bar_widget.winfo_exists(): gui_utils.stop_progressbar(root, progress_bar_widget, status_bar_label)
         return False, final_status_message

    common_headers = {
        'Accept': 'application/json, text/plain, */*', 'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'fr-FR,fr;q=0.9,ar-DZ;q=0.8,ar;q=0.7,en-US;q=0.6,en;q=0.5', 'Cache-Control': 'no-cache',
        'Connection': 'keep-alive', 'Cookie': current_cookie.strip(), 'Host': DEFAULT_ORIGIN_URL.split('//')[1],
        'Origin': DEFAULT_ORIGIN_URL, 'Pragma': 'no-cache', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin', 'User-Agent': USER_AGENT,
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"',
    }

    session = requests.Session()
    request_successful_for_saving_input = False

    try:
        if progress_bar_widget and progress_bar_widget.winfo_exists():
            gui_utils.start_progressbar(root, progress_bar_widget, status_bar_label)
        else:
            print("Warning: Progress bar widget not available when starting request.")

        if batch_cancel_all_flag.get(): raise InterruptedError("تم إلغاء الدفعة قبل البدء")
        if cancel_retry_flag.get(): raise InterruptedError("تم إلغاء المحاولة قبل البدء")

        if request_type == 'extend':
            overall_success, final_status_message = _perform_extend_or_reactivate(session, common_headers, nin, numero_wassit, root, status_text_widget, status_bar_label, cancel_retry_flag, cancel_retry_button, batch_cancel_all_flag)
            request_successful_for_saving_input = overall_success
        elif request_type == 'download_pdf':
            overall_success, final_status_message = _perform_download(session, common_headers, nin, numero_wassit, print_pref, root, status_text_widget, status_bar_label, cancel_retry_flag, cancel_retry_button, batch_cancel_all_flag)
            request_successful_for_saving_input = overall_success
        elif request_type == 'allocation_status':
            overall_success, final_status_message = _perform_allocation_status(session, common_headers, nin, numero_wassit, root, status_text_widget, status_bar_label, cancel_retry_flag, cancel_retry_button, batch_cancel_all_flag)
            request_successful_for_saving_input = overall_success
        elif request_type == 'change_mobile':
            if new_mobile is None: raise ValueError("New mobile number is required for 'change_mobile' request.")
            overall_success, final_status_message = _perform_change_mobile(session, common_headers, nin, numero_wassit, new_mobile, root, status_text_widget, status_bar_label, cancel_retry_flag, cancel_retry_button, batch_cancel_all_flag)
            request_successful_for_saving_input = overall_success
        elif request_type == 'extend_and_download':
            gui_utils.update_status_text(root, status_text_widget, "بدء عملية التجديد/إعادة التفعيل والتحميل المتسلسلة...", tags="api_info")
            gui_utils.update_status_bar(root, status_bar_label, "جاري التجديد/إعادة التفعيل (1/2)...", msg_type='info')
            extend_success, extend_message = _perform_extend_or_reactivate(session, common_headers, nin, numero_wassit, root, status_text_widget, status_bar_label, cancel_retry_flag, cancel_retry_button, batch_cancel_all_flag)
            request_successful_for_saving_input = extend_success
            download_success = False
            final_status_message = extend_message

            if batch_cancel_all_flag.get() or cancel_retry_flag.get():
                 final_status_message = "تم إلغاء العملية أثناء التجديد/إعادة التفعيل"
                 gui_utils.update_status_bar(root, status_bar_label, "تم إلغاء العملية", msg_type='warning')
                 overall_success = False
            elif extend_success:
                try:
                    cancel_retry_flag.set(False)
                    gui_utils.update_status_text(root, status_text_widget, "نجح التجديد/إعادة التفعيل.", tags="api_success")
                    gui_utils.update_status_text(root, status_text_widget, f"انتظار قصير ({BATCH_STEP_DELAY_SECONDS} ثانية) قبل بدء التحميل...", tags="info")
                    time.sleep(BATCH_STEP_DELAY_SECONDS)

                    gui_utils.update_status_text(root, status_text_widget, "", tags="separator")
                    gui_utils.update_status_bar(root, status_bar_label, "جاري تحميل الشهادة (2/2)...", msg_type='info')
                    download_success, download_message = _perform_download(session, common_headers, nin, numero_wassit, print_pref, root, status_text_widget, status_bar_label, cancel_retry_flag, cancel_retry_button, batch_cancel_all_flag)
                    overall_success = extend_success and download_success

                    if download_success:
                        if "جاري الطباعة" in download_message: final_status_message = f"{extend_message}؛ تم الحفظ + جاري الطباعة"
                        elif "تم طلب مسار الحفظ" in download_message: final_status_message = f"{extend_message}؛ تم طلب مسار الحفظ"
                        elif "تم الحفظ بنجاح" in download_message: final_status_message = f"{extend_message}؛ تم الحفظ بنجاح"
                        else: final_status_message = f"{extend_message}؛ {download_message}"
                    elif "إلغاء" in download_message: final_status_message = f"{extend_message}؛ {download_message}"
                    else: final_status_message = f"{extend_message}؛ ثم فشل التحميل/الطباعة ({download_message})"

                except Exception as download_err:
                    error_type = type(download_err).__name__
                    print(f"Error during download/print step within extend_and_download: {error_type} - {download_err}", file=sys.stderr)
                    final_status_message = f"{extend_message}؛ ثم حدث خطأ ({error_type}) أثناء التحميل/الطباعة"
                    overall_success = False
                    gui_utils.update_status_bar(root, status_bar_label, f"خطأ أثناء التحميل/الطباعة ({error_type})", msg_type='error')
            else:
                 gui_utils.update_status_bar(root, status_bar_label, "فشل التجديد/إعادة التفعيل، تم إيقاف التحميل", msg_type='error')
                 overall_success = False

        if request_successful_for_saving_input:
            if nin != settings_manager.get_last_nin() or numero_wassit != settings_manager.get_last_numero():
                settings_manager.set_last_nin(nin)
                settings_manager.set_last_numero(numero_wassit)
                settings_manager.save_settings()

    except InterruptedError as ie:
        print(f"Operation interrupted before starting: {ie}")
        final_status_message = str(ie)
        overall_success = False
    except Exception as e:
        error_type = type(e).__name__
        final_status_message = f"خطأ عام غير متوقع ({error_type}): {e}"
        error_details = f"حدث خطأ عام غير متوقع أثناء تنسيق وتنفيذ الطلب ({request_type}).\n   النوع: {error_type}\n   التفاصيل: {e}"
        print(f"Orchestration error for {request_type}: {e}", file=sys.stderr)
        if status_text_widget and status_text_widget.winfo_exists(): gui_utils.update_status_text(root, status_text_widget, f"❌ {error_details}", tags="api_error")
        if status_bar_label and status_bar_label.winfo_exists(): gui_utils.update_status_bar(root, status_bar_label, f"خطأ عام: {error_type}", msg_type='error')
        overall_success = False
    finally:
        if progress_bar_widget and progress_bar_widget.winfo_exists():
            gui_utils.stop_progressbar(root, progress_bar_widget, status_bar_label)

        session.close()
        warnings.filterwarnings('default', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

        is_batch_mode = False
        if root and hasattr(root, 'batch_mode_active') and isinstance(root.batch_mode_active, tk.BooleanVar):
            try: is_batch_mode = root.batch_mode_active.get()
            except tk.TclError: pass

        if not is_batch_mode and clicked_button and buttons_list:
            gui_utils.restore_button_state(root, buttons_list, clicked_button, original_text, cancel_retry_button)

        final_status_bar_text = ""
        if status_bar_label and status_bar_label.winfo_exists():
            try: final_status_bar_text = status_bar_label.cget("text")
            except tk.TclError: pass

        is_cancelled = (batch_cancel_all_flag and batch_cancel_all_flag.get()) or \
                       (cancel_retry_flag and cancel_retry_flag.get())
        is_ongoing_retry = "محاولة" in final_status_bar_text

        if not is_cancelled and not is_ongoing_retry:
             pass
        elif is_cancelled:
             gui_utils.update_status_bar(root, status_bar_label, "تم الإلغاء", msg_type='warning')

    if batch_cancel_all_flag and batch_cancel_all_flag.get():
        overall_success = False
        if "إلغاء" not in final_status_message: final_status_message = "تم إلغاء الدفعة"
    elif cancel_retry_flag and cancel_retry_flag.get():
         overall_success = False
         if "إلغاء" not in final_status_message: final_status_message = "تم إلغاء المحاولة"

    return overall_success, final_status_message
