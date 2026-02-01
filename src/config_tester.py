import os
import subprocess
import logging
import zipfile
import requests
import csv
import base64
import json
import sys
from urllib.parse import quote, unquote

# تنظیم لاگ حرفه‌ای و تمیز
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ProxyTester")

def print_progress(current, total, prefix=''):
    """نمایش نوار پیشرفت در لاگ"""
    percent = ("{0:.1f}").format(100 * (current / float(total)))
    filled_length = int(50 * current // total)
    bar = '█' * filled_length + '-' * (50 - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% Complete')
    sys.stdout.flush()
    if current == total: sys.stdout.write('\n')

def download_xray_knife():
    if os.path.exists("xray-knife"): return
    logger.info("Initializing: Downloading tester engine...")
    url = "https://github.com/lilendian0x00/xray-knife/releases/latest/download/Xray-knife-linux-64.zip"
    try:
        r = requests.get(url, timeout=30)
        with open("xray-knife.zip", "wb") as f: f.write(r.content)
        with zipfile.ZipFile("xray-knife.zip", 'r') as z: z.extractall("xray-knife-dir")
        for root, _, files in os.walk("xray-knife-dir"):
            for file in files:
                if file == "xray-knife":
                    os.rename(os.path.join(root, file), "xray-knife")
        os.chmod("xray-knife", 0o755)
        logger.info("Engine ready.")
    except Exception as e:
        logger.error(f"Failed to download engine: {e}")
        sys.exit(1)

def rename_config(link, info):
    if not link: return None
    cc = str(info.get('cc', 'UN')).upper()
    flag = "".join(chr(127397 + ord(c)) for c in cc) if len(cc)==2 else "🌐"
    ping = info.get('ping', '?')
    tag = f"{flag} {cc} | {ping}ms"
    if info.get('speed'): tag += f" | {info.get('speed')}"
    tag += " | "
    
    try:
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
    input_file = "sub/all/mixed.txt"
    output_dir = "sub/tested"
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_file):
        logger.error(f"Source file {input_file} not found!")
        return

    download_xray_knife()

    # --- مرحله ۱: تست پینگ ---
    logger.info("Phase 1: Starting Latency Test (Multi-threaded)...")
    ping_csv = "res_ping.csv"
    if os.path.exists(ping_csv): os.remove(ping_csv)
    
    # اجرای ابزار در حالت Silent
    subprocess.run(
        ["./xray-knife", "http", "-f", input_file, "-t", "100", "-o", ping_csv, "-x", "csv"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    ping_ok = []
    top_list = []

    if os.path.exists(ping_csv):
        with open(ping_csv, "r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            total_rows = len(rows)
            for i, row in enumerate(rows):
                link = next((v for k, v in row.items() if k and k.lower() in ['config', 'link']), None)
                delay = next((v for k, v in row.items() if k and ('delay' in k.lower() or 'real' in k.lower())), '0')
                cc = next((v for k, v in row.items() if k and ('country' in k.lower() or 'cc' in k.lower())), 'UN')
                
                if link and str(delay).isdigit() and int(delay) > 0:
                    labeled = rename_config(link, {'cc': cc, 'ping': delay})
                    ping_ok.append(labeled)
                    top_list.append({'link': link, 'delay': int(delay), 'cc': cc})
                
                if i % 100 == 0: print_progress(i + 1, total_rows, prefix='Filtering')
            print_progress(total_rows, total_rows, prefix='Filtering')

    with open(os.path.join(output_dir, "ping_passed.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(ping_ok))
    
    logger.info(f"Phase 1 Results: Found {len(ping_ok)} active configs.")

    # --- مرحله ۲: تست سرعت ---
    if top_list:
        top_list.sort(key=lambda x: x['delay'])
        top300_links = [x['link'] for x in top_list[:300]]
        
        with open("top300.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(top300_links))

        logger.info(f"Phase 2: Speed Testing top {len(top300_links)} candidates...")
        speed_csv = "res_speed.csv"
        if os.path.exists(speed_csv): os.remove(speed_csv)
        
        # اجرای تست سرعت
        subprocess.run(
            ["./xray-knife", "http", "-f", "top300.txt", "-t", "20", "-o", speed_csv, "-x", "csv", "-p", "-a", "10000"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        speed_ok = []
        if os.path.exists(speed_csv):
            with open(speed_csv, "r", encoding="utf-8-sig") as f:
                s_rows = list(csv.DictReader(f))
                for i, s_row in enumerate(s_rows):
                    s_link = next((v for k, v in s_row.items() if k and k.lower() in ['config', 'link']), None)
                    s_speed = next((v for k, v in s_row.items() if k and 'speed' in k.lower()), '0')
                    s_delay = next((v for k, v in s_row.items() if k and 'delay' in k.lower()), '0')
                    s_cc = next((v for k, v in s_row.items() if k and 'cc' in k.lower()), 'UN')
                    
                    try:
                        speed_val = float(str(s_speed).split()[0])
                        mbps = f"{speed_val/1024:.1f}MB" if speed_val > 0 else "LowSpeed"
                        labeled = rename_config(s_link, {'cc': s_cc, 'ping': s_delay, 'speed': mbps})
                        if labeled: speed_ok.append(labeled)
                    except: continue
                    print_progress(i + 1, len(s_rows), prefix='SpeedTest')

            with open(os.path.join(output_dir, "speed_passed.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(speed_ok))
        
        logger.info(f"Phase 2 Results: {len(speed_ok)} high-speed configs verified.")

    logger.info("Process completed successfully. Check sub/tested/ directory.")

if __name__ == "__main__":
    test_process()
