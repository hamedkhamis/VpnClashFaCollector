import os
import subprocess
import logging
import zipfile
import requests
import csv
import base64
import json
import yaml
import shutil
from urllib.parse import quote, unquote

# --- بارگذاری تنظیمات از YAML ---
def load_config(config_path="config.yaml"):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        exit(1)

CONFIG = load_config()

# استخراج متغیرها
INPUT_FILE = CONFIG['paths']['mixed_input']
TESTED_DIR = CONFIG['paths']['tested_dir']
ENGINE_BIN = CONFIG['paths']['engine_path']

# تنظیمات پینگ
PING_THREADS = str(CONFIG['ping_test']['threads'])
PING_OUT = CONFIG['ping_test']['output_name']

# تنظیمات سرعت
SPEED_THREADS = str(CONFIG['speed_test']['threads'])
SPEED_LIMIT = CONFIG['speed_test']['max_candidates']
SPEED_URL = CONFIG['speed_test']['test_url']
SPEED_OUT = CONFIG['speed_test']['output_name']

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("ProxyLab")

def to_base64(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_flag(cc):
    cc = str(cc).upper()
    return "".join(chr(127397 + ord(c)) for c in cc) if len(cc) == 2 else "🌐"

def download_engine():
    if os.path.exists(ENGINE_BIN): return
    logger.info("Downloading engine...")
    try:
        r = requests.get(CONFIG['engine']['url'], timeout=30)
        with open("engine.zip", "wb") as f: f.write(r.content)
        with zipfile.ZipFile("engine.zip", 'r') as z: z.extractall("temp_dir")
        for root, _, files in os.walk("temp_dir"):
            for file in files:
                if file == ENGINE_BIN:
                    os.rename(os.path.join(root, file), ENGINE_BIN)
        os.chmod(ENGINE_BIN, 0o755)
        if os.path.exists("engine.zip"): os.remove("engine.zip")
        if os.path.exists("temp_dir"): shutil.rmtree("temp_dir")
    except Exception as e:
        logger.error(f"Failed to download engine: {e}")

def rename_config(link, info, rank=None):
    try:
        cc = info.get('cc', 'UN')
        ping = info.get('ping', '?')
        speed = info.get('speed')
        tag_parts = [get_flag(cc), cc, f"{ping}ms"]
        if speed and "Low" not in str(speed): tag_parts.append(speed)
        prefix = f"[{rank}] " if rank else ""
        tag = prefix + " | ".join(tag_parts) + " | "
        
        if link.startswith("vmess://"):
            data = json.loads(base64.b64decode(link[8:]).decode('utf-8'))
            data['ps'] = tag + data.get('ps', 'Server')
            return "vmess://" + base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
        elif "#" in link:
            base, remark = link.split("#", 1)
            return f"{base}#{quote(tag + unquote(remark))}"
        return f"{link}#{quote(tag + 'Server')}"
    except: return link

def test_process():
    raw_dir = os.path.join(TESTED_DIR, "raw_results")
    os.makedirs(raw_dir, exist_ok=True)
    download_engine()

    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file {INPUT_FILE} not found!")
        return

    # --- مرحله ۱: تست پینگ ---
    logger.info(f"--- Phase 1: Ping Test (Threads: {PING_THREADS}) ---")
    p_csv = os.path.join(raw_dir, "ping_raw.csv")
    subprocess.run([f"./{ENGINE_BIN}", "http", "-f", INPUT_FILE, "-t", PING_THREADS, "-o", p_csv, "-x", "csv"], stdout=subprocess.DEVNULL)

    top_candidates = []
    if os.path.exists(p_csv):
        with open(p_csv, "r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
            valid_rows = [r for r in reader if r.get('delay') and str(r['delay']).isdigit() and int(r['delay']) > 0]
            valid_rows.sort(key=lambda x: int(x['delay']))
            
            ping_passed_list = [rename_config(r.get('link') or r.get('Config'), {'cc': r.get('location', 'UN'), 'ping': r.get('delay')}) for r in valid_rows]
            ping_text = "\n".join(filter(None, ping_passed_list))
            
            with open(os.path.join(TESTED_DIR, f"{PING_OUT}.txt"), "w", encoding="utf-8") as f: f.write(ping_text)
            with open(os.path.join(TESTED_DIR, f"{PING_OUT}_base64.txt"), "w", encoding="utf-8") as f: f.write(to_base64(ping_text))
            
            logger.info(f"Ping test complete. {len(valid_rows)} configs passed.")
            top_candidates = [r.get('link') or r.get('Config') for r in valid_rows[:SPEED_LIMIT]]

    # --- مرحله ۲: تست سرعت ---
    if top_candidates:
        tmp_txt = "speed_temp.txt"
        with open(tmp_txt, "w") as f: f.write("\n".join(filter(None, top_candidates)))
        
        logger.info(f"--- Phase 2: Speed Test (Threads: {SPEED_THREADS}, Candidates: {len(top_candidates)}) ---")
        s_csv = os.path.join(raw_dir, "speed_raw.csv")
        
        subprocess.run([f"./{ENGINE_BIN}", "http", "-f", tmp_txt, "-t", SPEED_THREADS, "-o", s_csv, "-x", "csv", "-p", "-u", SPEED_URL, "-a", "10000"], stdout=subprocess.DEVNULL)

        if os.path.exists(s_csv):
            speed_results = []
            with open(s_csv, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    raw_down = float(row.get('download') or 0)
                    speed_results.append({
                        'link': row.get('link') or row.get('Config'),
                        'speed_val': raw_down,
                        'delay': row.get('delay') or "0",
                        'cc': row.get('location') or "UN"
                    })
            
            speed_results.sort(key=lambda x: x['speed_val'], reverse=True)
            final_list = []
            for i, res in enumerate(speed_results, 1):
                spd = res['speed_val']
                f_speed = f"{spd / 1024:.1f}MB" if spd >= 1024 else (f"{int(spd)}KB" if spd > 0 else "Low")
                final_list.append(rename_config(res['link'], {'cc': res['cc'], 'ping': res['delay'], 'speed': f_speed}, rank=i))

            s_text = "\n".join(filter(None, final_list))
            with open(os.path.join(TESTED_DIR, f"{SPEED_OUT}.txt"), "w", encoding="utf-8") as f: f.write(s_text)
            with open(os.path.join(TESTED_DIR, f"{SPEED_OUT}_base64.txt"), "w", encoding="utf-8") as f: f.write(to_base64(s_text))
            logger.info(f"Speed test complete.")

    if os.path.exists("speed_temp.txt"): os.remove("speed_temp.txt")
    logger.info("Done.")

if __name__ == "__main__":
    test_process()
