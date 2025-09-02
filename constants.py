# constants.py
# يحتوي هذا الملف على الثوابت المستخدمة في جميع أنحاء التطبيق.
# *** تمت الإضافة: رابط API للتحقق من المواعيد ***
# *** تمت الإضافة: ثابت BATCH_STEP_DELAY_SECONDS ***

import os
import sys

# --- Constants ---
# اسم التطبيق المستخدم في مسار مجلد الإعدادات
APP_NAME = "خدمات وسيط - مع مطور عبد لمنعم"

# --- API URLs ---
# عناوين URL لنقاط نهاية الـ API المختلفة
EXTEND_API_URL = "https://wassitonline.anem.dz/api/extendMyDemandePublic"
REACTIVATE_API_URL = "https://wassitonline.anem.dz/api/CreateDemandeProlongation"
CERTIFICATE_API_URL = "https://wassitonline.anem.dz/api/FicheDemandeurOnline"
ALLOCATION_API_URL = "https://ac-controle.anem.dz/AllocationChomage/api/validateCandidate/query"
CHANGE_MOBILE_API_URL = "https://wassitonline.anem.dz/api/applicant/ChangerMobile" # URL for Changing Mobile
# *** تمت الإضافة: رابط API للتحقق من المواعيد ***
APPOINTMENT_DATES_API_URL = "https://ac-controle.anem.dz/AllocationChomage/api/RendezVous/GetAvailableDates"

# --- Referer URLs ---
# عناوين URL المستخدمة في ترويسة Referer للطلبات المختلفة
DEFAULT_REFERER_URL = "https://wassitonline.anem.dz/postulation/prolongationDemande" # Default referer for extend/reactivate/download
CHANGE_MOBILE_REFERER_URL = "https://wassitonline.anem.dz/postulation/ChangementMobile" # Specific referer for change mobile
ALLOCATION_REFERER = "https://minha.anem.dz/"

# --- Origin URLs ---
# عناوين URL المستخدمة في ترويسة Origin
DEFAULT_ORIGIN_URL = "https://wassitonline.anem.dz" # Default origin
ALLOCATION_ORIGIN = "https://minha.anem.dz"

# --- User Agent ---
# سلسلة وكيل المستخدم لتقليد متصفح ويب
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36" # Use a recent Chrome version

# --- Platform Check ---
# التحقق من نظام التشغيل (ويندوز أم لا)
IS_WINDOWS = sys.platform == "win32"

# --- Timing Constants ---
# *** تمت الإضافة: تأخير بين خطوات التجديد والتحميل في الدفعة ***
BATCH_STEP_DELAY_SECONDS = 0.5

# --- Function to Get Settings Path (Belongs here as it's a constant path logic) ---
def get_settings_directory() -> str:
    """Determines the appropriate directory for the settings file based on OS."""
    if IS_WINDOWS:
        # استخدام APPDATA بدلاً من Local/Roaming مباشرة لزيادة التوافقية
        app_data_dir = os.environ.get('APPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming'))
    elif sys.platform == "darwin": # macOS
        app_data_dir = os.path.expanduser('~/Library/Application Support')
    else: # Linux and other Unix-like systems
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        app_data_dir = xdg_config_home

    settings_dir = os.path.join(app_data_dir, APP_NAME)
    # لا تقم بإنشاء المجلد هنا، دعه يتم إنشاؤه عند الحفظ إذا لم يكن موجودًا
    # os.makedirs(settings_dir, exist_ok=True) # Removed folder creation here
    return settings_dir
# --- Settings File Path ---
SETTINGS_DIR = get_settings_directory()
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "app_settings.json")

print(f"Using settings file: {SETTINGS_FILE}") # Log the path being used

# --- Default values (used if settings file is missing/corrupt) ---
# *** UPDATED: Set the provided default cookie ***
# تم نقل القيم الافتراضية الأخرى إلى settings_manager.py
# أبقينا على الكوكي الافتراضية هنا كمثال، ولكن من الأفضل نقلها أيضًا أو إزالتها إذا لم تعد مستخدمة كقيمة افتراضية مباشرة هنا.
DEFAULT_COOKIE_VALUE = "cookiesession1=678B286B5A13AE349F102102FA0CABE3; _gid=GA1.2.1570168615.1745058866; _ga=GA1.2.1190300982.1733596516; _ga_Z5LSZFRGSZ=GS1.1.1745243450.5.0.1745243450.0.0.0; .AspNetCore.Antiforgery.ckC6Ki-zYXU=CfDJ8ASbLpDx_RBAockiBB1nqjjgXARzko5AU-Fu2OlYAbH2AQeBtcZDtw8b_Wc1UMQGyaSxXgbaQa1VreCiktMnnwMLz39BIR6-dBbKGPr2GXsyzWC6txLb9xP8FdY2mazWvOoIHK1mw8MU-qnEMA3LP8I; .AspNetCore.Mvc.CookieTempDataProvider=CfDJ8Hh1OQvfmtVAhrGoKEK5wsN4kGHRi75jgGY__qNlfP81p7cER1jx7YicfecD0Rso2sMvBN3SYTaBFcceLCz5Q7QLPYLj0yAin6rdq6opyHPx-RFpchQWdtelQLWNfeZiPZSlBrhMcPcQ6aWoiNqroiRAGFcxkykhnVq5F-4XK-X-; .AspNetCore.Cookies=chunks-2; .AspNetCore.CookiesC1=CfDJ8B-5n571KzdIqxHDgN6dulW3OuBZd7ROJ9XGCufKox-O6dL39DDl5H-2dbF_4h54St9GnneADuxkxlsY8yJFmSkY15rgVlL8U9VXgVNKLHN4J3BREfIOFSsKCPiLLmn5FOJSWXGRxxMzvVSuJOQAwgkq3PlxtmiGXNZ8NFTp25-ZBhryagyW129SXXxGzXPcS8pblg5xTyrtenWyF9XEkgfmOaNMBdxgpPj10o1ZYbfM5z3YrhErkniMJWHlNbwHSPWwqUvQXFG9gTcxkwunHecl-JndOmbQfbBkvwBkGEpZtboi6n5ukzQW6Ciih-qf5tuPPYB-t88Vydl_F9WalB1PonlWIaPE5ZPcccGcjCBt8h9ak8LLn5EPmcl2sMnQPSvDCADV84MVYz0SL-ZiGR4JwBilPIPWGwx-Bir83gGZdIabwmJTnR-NOmxsyUXvLBcdZ6d4FzwAx8HMRIsYzXL8BqfJbGNw2s9y0_GQE1SQhiKt5J0jY-x9kvssZ4wHqiTRJd7__g5_45WnOd_eDv-pCZgVbw1KUET5vU9_YmBoPcK3xu7rmU_yEwtR_FZ-wzWA_oSdRt0a4IRyNh80HazbA-Ngo0dC6CHHkdNr1YKuq5c7SS7-tD4RMzHN5vLVHCDnLH6gXKj1NVyiO6IKxe6gD95rbZjWHAXgvvLBhytIMmkF8WpNpl9vMtrbCRj3XIp9umruN5MeIV1hZXjC6XFqhmia6Me0YsHsPt9w45vwQ0g_cxNPvKu8iVRiGl5hCTVMh4o4byk2MXeB31eX1UFE3rB0lBR92h1Ln7nWCAeDjlAbM2I-_y4-M0Ysdby-G2zzAs4fyC6QnqhzleMuR1w5pOnRm0NDIat_sLc2cnDdC1G_6MnPOCCY1zj7n_fO5x3X7W8LOE0reYQtVwWLGGlO422OG4N8-jMti4px5YqV6n7Ua2DZ7kq8aENIC92AhjmBCtMnBxEmIotWAVTFahkZigp6Td8iLk7s8Vew5fZ_BaDtQBceah4211GJ9RDiM9EEqy1w85t9ZeoJTwumo8E3S5sA7Q0ieaSR2biK0jO8RhbnShppQWxC8_C3pEC7OsfS91LZ28dBtHbwQcyMm4e23EHOFOdVG_HEGjQt1QkF7na8AyUqUBcWwVKspPd31oGvBJskFQ7xPsrFnnAjS6S5um6dl5jj-fUXX6rXScW5mzntQxzyafMS5yWDcAubOrK84FpfXTYSJvRm6c1eVyo_dqaK_N_M00PKpE0Lon8ZtAKICiaoIVtJNYhQ0mvB8a4yNzxEkWJQDYXn-B1hB6D5oIDmWWJZr2w8ZxexJhlUkmZz76BA9nZlMfhCr2rtTz1GNtpEuCKOFSj6NB2dctFNww7ynO6ZZ9Vx3CbFUQQTRX_BOkc1X4I8GK67Q8nCVRd-rCMgX4sT62-lkkAxKVwBXuie33uBIX5mI6e_GcQ6LNzc1MowEWmeEwYIxSKbKJtuwYdgDFKwbeLHuFi5Hn5PCNnlee-DTh6BurgBCSL-560eb46SzO-RvBXn4_6HWxaPai-21hfi0eugn6xfHFQxyaMG-df4z8fgyLbi-ROqTaCjsAo2O9QB4uVr5LQhzbBf1LOtMMcvBpaYIC4PZwrMoGjwCA7ydSrNtBvn9VLP-T9PqaPlcrEsrgkxMyBJ_oiRnBA82AbRA3w-jdLBvteh3QQW0ztw4UU4xnRpHqyz5Us7-NtkzqUHDZcwgPy5IYn0Q-9vwCduK2MSxn-uHRd2JrzQ2my5V0c1VIxgRUJgY_tgnGYIrUylgv5mlx-osWemroAsB0gh4L1p6qXczO5_MkNoTsjiM5iGTJgGKW-aXudvQWe33lD3Q_J1wNUO6LB92wBlgbanAPJiBJZQM8DYqZxvkSbiK6znK4yC0cpSSD_XdFTExYn9L04eaAsrMLNbB3hbSuVB55g6T8AplEpP3JuJviv3sanw5YrXHGDBEpGGCx_kO1LpWBY1I2A50rlUx7xsO03pamE6_LUBe9lFUmuMqbMzvi_ay0W2o3qiQJ0DYUdQQcnXrRrGYWI-eXOVj2IukftdEaXjdyOR0SJiYVu9vc5QLHZNK5dA3f7VvYZtiu4p9baOC9zZGC6G39T8YkEonJ1QsJn_kwuQHJRlHlEBQcj86Kr-ct7MC6QjsDyNL95h21uR6JuR_RPY1U-CU7GKE_uiOT64M1U9_gyoBnP9AhtZelCtY7Neqjp2D6s_tIzDLp4WvaY9BwEnKkG-I_7Tz1mU2437Mc15dWnE-jjut8Q0jHCZQLm3Qo6PkeIMjzvsRbqFRCfDH3WSz241G1p4WLYURkcoiHsNKtKgW-XPX2oa5-CnHsb1HY1buDsgrBwy9b31N-GCA6ToeSplBL3fN89PdL8uQbUynxbH7Brr-lxbjpt0i3S8N-k26cBpSyEROUmQdcGIE-o0wUy1DxY3bcb2U3cx7BXKO-mktoCGMKOi5gMlW2z99vk4-HSe1NWk1pXSZo7NTNxjnnvuiHSQgGyf1G-_PsO2oniCCHx9cAY8zUDFZRc26gTTrFGDVozfG-TwuoOXDh_F17etFC02UTBmIZM_qgJzHecyBpg2iQKFdAU1TD6l6qUvu7Nv6YmkWreJiBpXu4bJxf5ol0G8ZVG0PJYtQNgVTbPZzSje9KhGHrS0BFLbwprT2_9tLB40I0siJ2FAuuAsoXapOhDlJ8x2UptS6P2JlJ3dJa98LBk_PfjV--mEkmG9jC2nWM3hgdtbVSihHEjXHYH_eSONmFrRcgbMSeFK0C2B5q9thmiheMGFEEJSUvIW-F8rGFNwLPrViJChFg68wcSIg26Y8IutMqmbR0-KA6VL7W5VbqdK6eRhcYKJMDjQ6ZhObW9_9LALhLFrDlpxLg__cK47xtHJ5p4H0QgvBzT3lPmxormsBYG1CUGs2CEbvCzGxTsuU7F3cEw8tJ6gHdYbzW8IVLk3XsavGd_XwYpa6K87pEh0Hymk3ui9I9BGk7eu-yCzAkSbNhtNHEIwRu9DTNLzfVEsghKZvdSWYlaW06CkeGdFNYfGSFRQ_YRCY5YlDGfnNWsazNxQMu4BDUTJsATW7swPhtNxm1GzwJRmb_Lrng6jMIjcst7Fe0cMnaH7UyEwjx9U0BxUgckWsj8Gs_iigKIChzQZpUSTlMyV0Q0gb9wOiyInmlUSdZN8yCqYOuCZzUVCZjYUPX3jPmeABV11irVAFq_I_Df8O0-Wtai7-6gVFNdQOIAfK4No0mr-0Ig1Rn_QHEW9zA9Ee75tmECMBoDZ6tBZyuppeuzYHFc8IvkkBqSuEtXR101d1LmUWiZdpst2iJ4KadM8pKDy4PDzkSRgLv78m15qnp0KEUqNSR41_aBKAgFxJHCnkxKBjgOwSD5O8r4EwwDsSFqTNQb7d0Zml2cYUgRILwFznk4lnc8LRKcvFLtCw16jnwTN7-wy2Zxj6B0eyXJVrpZ3VsgNuD13n01Qp4XLdUFk1av17xUKgt83LjyDcuF7QgKG5QNly364AJmwxYAfYmMXIW7L-Qr8kWaM1PgFbiBUBi01fLcGoBe5nHjGWV12aaLpxv2d_yOkmW0x9k-FQMlSMkFRh1m11luchLQdv4oo9EKRaOZIv0sh4FzKnpFy5YJjb3bi9sl0O1XNFrTEQZpOLoAAdG1A1wMwJDwM5zbP8GZm1ZX85bVywLgMVyexMHzxWwlY8Z3TWl8QKWXCPGwFOPnEsZ6UesaimBvwLrVBCmaFxMxEdFtRmx0ws6PsZs98I0DCrkcs9BUfuVVCU0f_94lPAZz_VZB1kgbbyI6vXUJ6t8EQKoEqfhmXf7s4NpEFOXJqjiiRSEpqI5Uf3xalNS2OK0zpDkRr61fYXYcldLh8697TkYebKDenrdppuUTRe6BzofPZezy244-Vb7Ip9ukTM_y_WxWn37Aa170UMsQE3diYIxBmEFP9LnBgv1MfdPT5hNLns2_TU9g6lN6jS9EedaC5oJx; .AspNetCore.CookiesC2=moP-It3NotjBQ3QSLuvz7sZ80lL6aJ3o6vI4SO4S90ZZVN3rCfx_Bl9snI8ppmfsl6Gs1AYHryj-Kq2JluQu8c_hcVcs10cFsYnRGq8riWk_lPHc98H876yfypa2i3lW5yw5Ya6pt2exVvVdW3F6tnkk17igm2G7pvx78g8L_yjvKF0ksJqYXXgKEYM8MNTiYSM9V90IDE0uOPWEjwcNe5EXdELDbe7ajSk0ZJVfDiYcA--f2VDBSZBdy3Lts4TPwMUGQHxE2Hw_VBRTdImVZ4FRSBhwOYVjP-5EHPPBt6tE1q5DvtIgBDuqkHfhEN0fQQSRG4HCfzAMciJhKLmwlL1mEfxtEmniMQByAz3CsciAr1E_EXe28l8_fTunzCzLWQ3yfee82tmJlFo8VzEAYFmXy77jbtk5Fx5RvxqtsWrZ-nHCvnX-xT_3HoZ8GOQ-Um0LFZfc6_hf0OFuvH8tRVIOda4B4sSM7eikA5nilUhprMDOxwrffKysTgcwEl2ZP_FjK5jMa6ThIBKyYv6q_iv0sGP4ucp-6DP3cqhngeED5N6BWXl-NIh8Ue0fsZgdT3Z_MregqSmyDnGZTkSuu_KdSv1UL_oOBjN-Ufd_jgDY4X8HIieoPPYDzdSx2FRoI0-VTwb3Y0lupuQdRdl0q5y1_1RUdkz_SJiKSLBL0Hz3xltz1JZ1_F1KtTp46fuaoOCKbTW_MvwMfyuASlsjHpfVBQHbgmfg8WDfyZaPMvJdOZygawOOanFamBTSarXehdBUsbC_h2wPiB91winssbEoblbqC0VHQaEn7kqXVXeh993VczCSibHneQ4gkvbdHbPBLy64MVbJDww0Cd1w4k-OR53b86i3oV9BtpJ4zTjXZ3OhCh2A60LrmJJHkgQlb9xGWHC1JoSZaJt0jOeECgguTi1i4dCV4i3roToeedtGYjAr2fGewyuBD5Ca-va1eDuTYmcSTo0gta1A6AWhe5dgOqOLqsXyoc-O-FEaOiaDYTv0b01qQjvlucORseQ1u-J9dGNUDt10rK8U77m4hseh7gCxsrH_-hLCJ6tyRZvUkoE0Ntc8x2ZrjzWqrsIOEw6KrURh_GPny9k2h1NoZXqMx48JQqkhWSp7pu36zRtqE3F63Jo4WIpW26Vzfk6qnZy7URMc-zFNdedRoFGbbXvF9EbNuDvEh6c_gla3WEgh9jGyTrVWtkUVFNZXdk9VhqmUcNZK-Zj7pyMtXrdzqjDOS2p95; .AspNetCore.Antiforgery.QLeDFMJ2E8c=CfDJ8B-5n571KzdIqxHDgN6dulVMpqib0GGppXLEHF6pYOk384Ugt3ZHG033ocaMePqOdq_f1EeF3-IJK3FkplaDC8wdoQb2Y1VSxnUtchdNzr19t3GhSqOfck_zbdMPkjc5RCftu3Vz6akztHN-kZQjyhc; _ga_2FNQXR2RT9=GS1.2.1745484787.227.1.1745486502.0.0.0; _ga_GF0PH4WJ7C=GS1.2.1745490611.210.1.1745490614.0.0.0; _ga_HCCJ015B9N=GS1.2.1745490551.477.1.1745490962.0.0.0" # Placeholder

# --- Default Downloads Path ---
# تحديد مسار التحميلات الافتراضي بشكل أكثر موثوقية
try:
    DEFAULT_DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(DEFAULT_DOWNLOADS_PATH):
        # Fallback to user's home directory if Downloads doesn't exist
        DEFAULT_DOWNLOADS_PATH = os.path.expanduser("~")
except Exception:
    # Final fallback to home directory in case of any error
    DEFAULT_DOWNLOADS_PATH = os.path.expanduser("~")
