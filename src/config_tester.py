import os, subprocess, logging, zipfile, requests, csv, base64, json, sys, re
from urllib.parse import quote, unquote

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("ProxyLab")

def to_base64(text):
    """تبدیل متن به فرمت بیس۶۴"""
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_flag(cc):
    """تبدیل کد کشور به ایموجی پرچم"""
    cc = str(cc).upper()
    return "".join(chr(127397 + ord(c)) for c in cc) if len(cc) == 2 else "🌐"

def download_engine():
    """دانلود موتور ایکس‌ری نایف در صورت عدم وجود"""
    if os.path.exists("xray-knife"): return
    url = "https://github.com/lilendian0x00/xray-knife/releases/latest/download/Xray-knife-linux-64.zip"
    try:
        r = requests.get(url, timeout=30)
        with open("engine.zip", "wb") as f: f.write(r.content)
        with zipfile.ZipFile("engine.zip", 'r') as z: z.extractall("dir")
        for root, _, files in os.walk("dir"):
            for file in files:
                if file == "xray-knife": os.rename(os.path.join(root, file), "xray-knife")
        os.chmod("xray-knife", 0o755)
        if os.path.exists("engine.zip"): os.remove("engine.zip")
        if os.path.exists("dir"): subprocess.run(["rm", "-rf", "dir"])
    except Exception as e:
        logger.error(f"Failed to download engine: {e}")

def rename_config(link, info, rank=None):
    """تغییر نام و برچسب‌گذاری کانفیگ بر اساس نتایج تست"""
    try:
        cc = info.get('cc', 'UN')
        ping = info.get('ping', '?')
        speed = info.get('speed')
        
        tag_parts = [get_flag(cc), cc, f"{ping}ms"]
        if speed and "Low" not in str(speed):
            tag_parts.append(speed)
        
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
    input_file = "sub/all/mixed.txt"
    base_dir = "sub/tested"
    raw_dir = os.path.join(base_dir, "raw_results")
    os.makedirs(raw_dir, exist_ok=True)
    download_engine()

    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} not found!")
        return

    # --- Phase 1: Latency Test ---
    # تغییر: Threads به 100 افزایش یافت
    logger.info("--- Phase 1: Latency Test (Threads: 100) ---")
    p_csv = os.path.join(raw_dir, "ping_raw.csv")
    subprocess.run(["./xray-knife", "http", "-f", input_file, "-t", "100", "-o", p_csv, "-x", "csv"], stdout=subprocess.DEVNULL)

    top_candidates = []
    if os.path.exists(p_csv):
        with open(p_csv, "r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
            valid_rows = [r for r in reader if r.get('delay') and str(r['delay']).isdigit() and int(r['delay']) > 0]
            valid_rows.sort(key=lambda x: int(x['delay']))
            
            ping_passed_list = [rename_config(r.get('link') or r.get('Config'), {'cc': r.get('location', 'UN'), 'ping': r.get('delay')}) for r in valid_rows]
            ping_passed_text = "\n".join(filter(None, ping_passed_list))
            
            with open(os.path.join(base_dir, "ping_passed.txt"), "w", encoding="utf-8") as f: 
                f.write(ping_passed_text)
            
            with open(os.path.join(base_dir, "ping_passed_base64.txt"), "w", encoding="utf-8") as f:
                f.write(to_base64(ping_passed_text))
            
            logger.info(f"Ping test complete. {len(valid_rows)} configs passed.")
            top_candidates = [r.get('link') or r.get('Config') for r in valid_rows[:300]]

    # --- Phase 2: Speed Test ---
    if top_candidates:
        tmp_txt = "top_candidates_tmp.txt"
        with open(tmp_txt, "w") as f: f.write("\n".join(filter(None, top_candidates)))
        
        # تغییر: Threads به 2 افزایش یافت
        logger.info("--- Phase 2: Speed Test (5MB - Threads: 2) ---")
        s_csv = os.path.join(raw_dir, "speed_raw.csv")
        speed_url = "https://speed.cloudflare.com/__down?bytes=5000000"
        
        # پارامتر -t به 2 تغییر کرد
        subprocess.run(["./xray-knife", "http", "-f", tmp_txt, "-t", "2", "-o", s_csv, "-x", "csv", "-p", "-u", speed_url, "-a", "10000"], stdout=subprocess.DEVNULL)

        speed_results = []
        if os.path.exists(s_csv):
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
                if spd >= 1024:
                    f_speed = f"{spd / 1024:.1f}MB"
                elif spd > 0:
                    f_speed = f"{int(spd)}KB"
                else:
                    f_speed = "Low"
                
                final_list.append(rename_config(res['link'], {'cc': res['cc'], 'ping': res['delay'], 'speed': f_speed}, rank=i))

            s_text = "\n".join(filter(None, final_list))
            with open(os.path.join(base_dir, "speed_passed.txt"), "w", encoding="utf-8") as f: f.write(s_text)
            with open(os.path.join(base_dir, "speed_passed_base64.txt"), "w", encoding="utf-8") as f: f.write(to_base64(s_text))
            
            logger.info(f"Speed test complete. {len(speed_results)} configs ranked.")

    if os.path.exists(tmp_txt): os.remove(tmp_txt)
    logger.info("All tests finished successfully.")

if __name__ == "__main__":
    test_process()
