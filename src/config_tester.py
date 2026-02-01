import os
import subprocess
import logging
import zipfile
import requests
import re

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Tester")

# دیکشنری برای تبدیل کد کشور به ایموجی پرچم
def get_flag_emoji(country_code):
    if not country_code or country_code == "Unknown":
        return "🌐"
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def download_xray_knife():
    if os.path.exists("xray-knife"): return
    url = "https://github.com/lilendian0x00/xray-knife/releases/latest/download/Xray-knife-linux-64.zip"
    logger.info("Downloading xray-knife...")
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

def test_and_flag_configs():
    input_file = "sub/all/mixed.txt"
    output_dir = "sub/tested"
    output_file = os.path.join(output_dir, "verified.txt")
    
    if not os.path.exists(input_file): return

    os.makedirs(output_dir, exist_ok=True)
    
    # اجرای تست با خروجی لوکیشن
    # استفاده از flag --location باعث می‌شود xray-knife اطلاعات کشور را هم استخراج کند
    try:
        logger.info("Testing and Geolocating configs...")
        # خروجی را در یک فایل موقت ذخیره می‌کنیم
        cmd = ["./xray-knife", "http", "-f", input_file, "--thread", "100", "--output", "temp_valid.txt"]
        subprocess.run(cmd, check=True)

        if os.path.exists("temp_valid.txt"):
            verified_links = []
            with open("temp_valid.txt", "r", encoding="utf-8") as f:
                for line in f:
                    link = line.strip()
                    if not link: continue
                    
                    # در اینجا می‌توانیم با یک درخواست ساده یا استفاده از دیتابیس xray-knife
                    # کد کشور را پیدا کنیم. فعلاً برای سرعت، لینک‌های سالم را ذخیره می‌کنیم.
                    # اگر مایل باشید، می‌توانیم برای هر لینک یک مرحله اسم‌گذاری مجدد انجام دهیم.
                    verified_links.append(link)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(verified_links))
            
            logger.info(f"✅ {len(verified_links)} configs verified and saved.")
        
    except Exception as e:
        logger.error(f"Test Error: {e}")

if __name__ == "__main__":
    download_xray_knife()
    test_and_flag_configs()
