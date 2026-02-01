import os
import subprocess
import logging
import zipfile
import requests
import re
import csv
import base64
import json
from urllib.parse import urlparse, quote, unquote

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Tester")

def get_flag_emoji(country_code):
    """تبدیل کد کشور (مثلا US) به ایموجی پرچم"""
    if not country_code or country_code.lower() == "unknown" or len(country_code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def download_xray_knife():
    if os.path.exists("xray-knife"): return
    url = "https://github.com/lilendian0x00/xray-knife/releases/latest/download/Xray-knife-linux-64.zip"
    logger.info("در حال دانلود xray-knife...")
    r = requests.get(url)
    with open("xray-knife.zip", "wb") as f: f.write(r.content)
    with zipfile.ZipFile("xray-knife.zip", 'r') as zip_ref:
        zip_ref.extractall("xray-knife-dir")
    for root, dirs, files in os.walk("xray-knife-dir"):
        for file in files:
            if file == "xray-knife":
                os.rename(os.path.join(root, file), "xray-knife")
                break
    os.chmod("xray-knife", 0o755)

def rename_with_flag(link, country_code):
    """اضافه کردن پرچم به نام کانفیگ بر اساس پروتکل"""
    flag = get_flag_emoji(country_code)
    prefix = f"{flag} {country_code} | "
    
    try:
        if link.startswith("vmess://"):
            # پروتکل VMess (Base64 JSON)
            v2_json_str = base64.b64decode(link[8:]).decode('utf-8')
            data = json.loads(v2_json_str)
            data['ps'] = prefix + data.get('ps', 'Server')
            return "vmess://" + base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
        
        elif any(link.startswith(p) for p in ["vless://", "trojan://", "ss://", "ssr://"]):
            # پروتکل‌های دارای Remark بعد از #
            if "#" in link:
                base, remark = link.split("#", 1)
                new_remark = prefix + unquote(remark)
                return f"{base}#{quote(new_remark)}"
            else:
                return f"{link}#{quote(prefix + 'Server')}"
        
        # برای لینک‌های تلگرام (tg) تغییر نام استاندارد وجود ندارد
        return link
    except:
        return link

def test_and_flag_configs():
    input_file = "sub/all/mixed.txt"
    output_dir = "sub/tested"
    temp_csv = "temp_results.csv"
    
    if not os.path.exists(input_file):
        logger.error("فایل ورودی یافت نشد.")
        return

    os.makedirs(output_dir, exist_ok=True)
    download_xray_knife()

    logger.info("شروع تست و مکان‌یابی کانفیگ‌ها...")
    
    try:
        # اجرای تست با خروجی CSV (گزینه -x csv و -o برای فایل خروجی)
        cmd = [
            "./xray-knife", "http",
            "-f", input_file,
            "--thread", "100",
            "-o", temp_csv,
            "-x", "csv"
        ]
        subprocess.run(cmd, check=True)

        if os.path.exists(temp_csv):
            verified_links = []
            with open(temp_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # در xray-knife معمولا ستونی به نام 'Config' یا 'Link' و 'Country' وجود دارد
                    # با توجه به راهنما، ستون‌ها را بررسی می‌کنیم
                    link = row.get('Config') or row.get('Link')
                    country = row.get('Country Code') or row.get('Country', 'Unknown')
                    
                    if link:
                        new_link = rename_with_flag(link, country)
                        verified_links.append(new_link)

            # ذخیره خروجی نهایی
            with open(os.path.join(output_dir, "verified.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(verified_links))
            
            logger.info(f"✅ تعداد {len(verified_links)} کانفیگ سالم همراه با پرچم ذخیره شد.")
            os.remove(temp_csv)
        
    except Exception as e:
        logger.error(f"خطا در تست: {e}")

if __name__ == "__main__":
    test_and_flag_configs()
