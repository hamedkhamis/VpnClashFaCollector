import os
import requests
import time
import subprocess
import json
import logging
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Source_Specific_Generator")

def run_subconverter():
    if not os.path.exists("subconverter/subconverter"):
        logger.info("Downloading Subconverter binary...")
        url = "https://github.com/MetaCubeX/subconverter/releases/latest/download/subconverter_linux64.tar.gz"
        subprocess.run(["wget", url, "-O", "subconverter.tar.gz"], check=True)
        subprocess.run(["tar", "-xvf", "subconverter.tar.gz"], check=True)
        os.chmod("subconverter/subconverter", 0o755)
    
    proc = subprocess.Popen(["./subconverter/subconverter"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    return proc

def generate_subs():
    base_sub_dir = "sub"
    base_output_dir = "sub/final"
    config_path = "config/sub_params.json"
    base_api = "http://127.0.0.1:25500/sub"

    with open(config_path, "r", encoding="utf-8") as f:
        client_configs = json.load(f)

    for root, dirs, files in os.walk(base_sub_dir):
        if "final" in root: continue

        parent_folder = os.path.basename(root)
        
        # تشخیص پوشه‌های ویژه (که همه فایل‌هایشان باید تبدیل شود)
        is_special_folder = parent_folder in ["tested", "all"]

        for file in files:
            if not file.endswith("base64.txt"): continue
            
            # منطق فیلتر:
            # اگر در پوشه ویژه نیستیم، فقط فایل 'mixed_base64.txt' را پردازش کن
            if not is_special_folder and "mixed" not in file:
                continue

            source_path = os.path.abspath(os.path.join(root, file))
            file_clean_name = file.replace(".txt", "").replace("_base64", "")

            # نام‌گذاری پوشه مقصد
            if is_special_folder:
                dest_folder_name = f"{parent_folder}_{file_clean_name}"
            else:
                dest_folder_name = parent_folder

            dest_dir = os.path.join(base_output_dir, dest_folder_name)
            os.makedirs(dest_dir, exist_ok=True)

            logger.info(f"✨ Processing {'[SPECIAL]' if is_special_folder else '[MIXED-ONLY]'}: {parent_folder}/{file}")

            for client_name, params in client_configs.items():
                current_params = params.copy()
                target_filename = current_params.pop("filename", f"{client_name}.txt")
                current_params["url"] = source_path
                
                query = "&".join([f"{k}={quote(str(v), safe='')}" for k, v in current_params.items() if v])
                final_url = f"{base_api}?{query}"

                try:
                    response = requests.get(final_url, timeout=60)
                    if response.status_code == 200:
                        with open(os.path.join(dest_dir, target_filename), "w", encoding="utf-8") as f:
                            f.write(response.text)
                except Exception as e:
                    logger.error(f"  ❌ Error {client_name}: {e}")

if __name__ == "__main__":
    sub_proc = None
    try:
        sub_proc = run_subconverter()
        generate_subs()
    finally:
        if sub_proc:
            sub_proc.terminate()
            logger.info("Generation finished.")
