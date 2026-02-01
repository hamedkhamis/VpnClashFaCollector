import os
import requests
import time
import subprocess
import json
import logging
from urllib.parse import quote

# تنظیمات لاگ برای مشاهده وضعیت اجرا
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SubConverter_Generator")

def run_subconverter():
    """دانلود، نصب و اجرای سرویس ساب‌کانورتر در پس‌زمینه"""
    if not os.path.exists("subconverter/subconverter"):
        logger.info("در حال دانلود موتور ساب‌کانورتر...")
        # لینک نسخه لینوکس 64 بیتی
        url = "https://github.com/MetaCubeX/subconverter/releases/latest/download/subconverter_linux64.tar.gz"
        try:
            subprocess.run(["wget", url, "-O", "subconverter.tar.gz"], check=True)
            subprocess.run(["tar", "-xvf", "subconverter.tar.gz"], check=True)
            # اعطای دسترسی اجرایی به فایل اصلی
            os.chmod("subconverter/subconverter", 0o755)
        except Exception as e:
            logger.error(f"خطا در دانلود یا استخراج ساب‌کانورتر: {e}")
            return None
    
    logger.info("در حال اجرای سرویس ساب‌کانورتر...")
    # اجرای ساب‌کانورتر روی پورت پیش‌فرض 25500
    try:
        proc = subprocess.Popen(
            ["./subconverter/subconverter"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        # زمان دادن به سرویس برای بالا آمدن کامل
        time.sleep(3)
        return proc
    except Exception as e:
        logger.error(f"خطا در اجرای سرویس ساب‌کانورتر: {e}")
        return None

def generate_all_subs():
    """تولید تمامی کانفیگ‌ها بر اساس پارامترهای فایل JSON"""
    source_file = "sub/tested/speed_passed_base64.txt"
    config_path = "config/sub_params.json"
    output_dir = "sub/final"
    
    # اطمینان از وجود پوشه خروجی
    os.makedirs(output_dir, exist_ok=True)

    # بررسی وجود فایل منبع
    if not os.path.exists(source_file):
        logger.error(f"فایل منبع یافت نشد: {source_file}")
        return

    # بررسی وجود فایل تنظیمات در پوشه config
    if not os.path.exists(config_path):
        logger.error(f"فایل تنظیمات در مسیر {config_path} یافت نشد!")
        return

    # خواندن لینک‌های خام تست شده
    with open(source_file, "r", encoding="utf-8") as f:
        raw_links = f.read().strip()
    
    # خواندن تنظیمات اختصاصی هر کلاینت
    with open(config_path, "r", encoding="utf-8") as f:
        client_configs = json.load(f)

    base_api = "http://127.0.0.1:25500/sub"

    for client_name, params in client_configs.items():
        logger.info(f"در حال پردازش کلاینت: {client_name}")
        
        # استخراج نام فایل خروجی و حذف آن از پارامترهای ارسالی به API
        target_filename = params.pop("filename", f"{client_name}.txt")
        
        # کپی پارامترها و اضافه کردن لینک منبع
        payload = params.copy()
        payload["url"] = raw_links
        
        # ساخت Query String با رعایت URLEncode برای تمامی مقادیر
        # مقادیر خالی نادیده گرفته می‌شوند
        query_string = "&".join([f"{k}={quote(str(v))}" for k, v in payload.items() if v != ""])
        final_request_url = f"{base_api}?{query_string}"

        try:
            # ارسال درخواست به سرویس محلی ساب‌کانورتر
            # افزایش تایم‌اوت به 120 ثانیه برای لیست‌های حجیم
            response = requests.get(final_request_url, timeout=120)
            
            if response.status_code == 200:
                full_output_path = os.path.join(output_dir, target_filename)
                with open(full_output_path, "w", encoding="utf-8") as out_file:
                    out_file.write(response.text)
                logger.info(f"فایل با موفقیت ذخیره شد: {target_filename}")
            else:
                logger.error(f"خطا در تبدیل برای {client_name}: کد وضعیت {response.status_code}")
                
        except Exception as e:
            logger.error(f"خطای ارتباطی برای کلاینت {client_name}: {e}")

if __name__ == "__main__":
    subconverter_process = None
    try:
        # ۱. اجرای موتور تبدیل
        subconverter_process = run_subconverter()
        
        if subconverter_process:
            # ۲. شروع فرآیند تولید فایل‌ها
            generate_all_subs()
        else:
            logger.error("سرویس ساب‌کانورتر اجرا نشد. توقف عملیات.")
            
    except KeyboardInterrupt:
        logger.info("عملیات توسط کاربر متوقف شد.")
    finally:
        # ۳. بستن سرویس ساب‌کانورتر پس از اتمام کار
        if subconverter_process:
            logger.info("در حال بستن سرویس ساب‌کانورتر...")
            subconverter_process.terminate()
            subconverter_process.wait()
            logger.info("سرویس با موفقیت بسته شد.")
