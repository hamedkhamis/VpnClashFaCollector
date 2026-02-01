import os
import requests
import time
import subprocess
import json
import logging
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Auto_Discovery_Generator")

def run_subconverter():
    if not os.path.exists("subconverter/subconverter"):
        logger.info("Downloading Subconverter...")
        url = "https://github.com/MetaCubeX/subconverter/releases/latest/download/subconverter_linux64.tar.gz"
        subprocess.run(["wget", url, "-O", "subconverter.tar.gz"], check=True)
        subprocess.run(["tar", "-xvf", "subconverter.tar.gz"], check=True)
        os.chmod("subconverter/subconverter", 0o755)
    
    proc = subprocess.Popen(["./subconverter/subconverter"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    return proc

def discover_and_generate():
    base_sub_dir = "sub"
    base_output_dir = "sub/final"
    config_path = "config/sub_params.json"
    base_api = "http://127.0.0.1:25500/sub"

    # خواندن تنظیمات کلاینت‌ها
    with open(config_path, "r", encoding="utf-8") as f:
        client_configs = json.load(f)

    # اسکن تمام پوشه‌ها برای پیدا کردن فایل‌هایی که با base64.txt تمام می‌شوند
    for root, dirs, files in os.walk(base_sub_dir):
        # جلوگیری از اسکن کردن پوشه final (خروجی) برای جلوگیری از تکرار بی‌پایان
        if "final" in root:
            continue

        for file in files:
            if file.endswith("base64.txt"):
                source_file_path = os.path.join(root, file)
                # تبدیل مسیر فایل محلی به مسیر مطلق برای ساب‌کانورتر
                abs_source_path = os.path.abspath(source_file_path)
                
                # استخراج نام پوشه والد (مثلاً Capoit یا SOSkeyNET)
                parent_folder = os.path.basename(root)
                file_clean_name = file.replace("_base64.txt", "").replace(".txt", "")
                
                # نام نهایی پوشه خروجی
                if file_clean_name == "mixed":
                    final_folder_name = parent_folder
                else:
                    final_folder_name = f"{parent_folder}_{file_clean_name}"

                dest_dir = os.path.join(base_output_dir, final_folder_name)
                os.makedirs(dest_dir, exist_ok=True)

                logger.info(f"🔍 Found Source: {source_file_path} -> Folder: {final_folder_name}")

                for client_name, params in client_configs.items():
                    current_params = params.copy()
                    target_filename = current_params.pop("filename", f"{client_name}.txt")
                    
                    # استفاده از آدرس فایل محلی برای سرعت بالا و دور زدن محدودیت URL
                    current_params["url"] = abs_source_path
                    
                    query_string = "&".join([f"{k}={quote(str(v), safe='')}" for k, v in current_params.items() if v])
                    final_url = f"{base_api}?{query_string}"

                    try:
                        response = requests.get(final_url, timeout=60)
                        if response.status_code == 200:
                            output_path = os.path.join(dest_dir, target_filename)
                            with open(output_path, "w", encoding="utf-8") as f:
                                f.write(response.text)
                    except Exception as e:
                        logger.error(f"  ❌ Error {client_name} for {final_folder_name}: {e}")

if __name__ == "__main__":
    sub_proc = None
    try:
        sub_proc = run_subconverter()
        discover_and_generate()
    finally:
        if sub_proc:
            sub_proc.terminate()
            logger.info("Scan and Conversion completed.")
