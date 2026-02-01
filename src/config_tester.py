import os, subprocess, logging, zipfile, requests, csv, base64, json, sys, re
from urllib.parse import quote, unquote

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("ProxyLab")

def to_base64(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_flag(cc):
    cc = str(cc).upper()
    return "".join(chr(127397 + ord(c)) for c in cc) if len(cc) == 2 else "🌐"

def cleanup_remark(remark):
    # حذف آدرس‌های طولانی تلگرام و کاراکترهای اضافه برای تمیزی نام
    remark = unquote(remark)
    remark = re.sub(r'https?://\S+', '', remark)
    remark = re.sub(r'@[A-Za-z0-9_]+', '', remark)
    return remark.strip()[:20] # محدودیت ۲۰ کاراکتر برای نام اصلی

def download_engine():
    if os.path.exists("xray-knife"): return
    logger.info("Downloading Xray-knife Engine...")
    url = "https://github.com/lilendian0x00/xray-knife/releases/latest/download/Xray-knife-linux-64.zip"
    r = requests.get(url, timeout=30)
    with open("engine.zip", "wb") as f: f.write(r.content)
    with zipfile.ZipFile("engine.zip", 'r') as z: z.extractall("dir")
    for root, _, files in os.walk("dir"):
        for file in files:
            if file == "xray-knife": os.rename(os.path.join(root, file), "xray-knife")
    os.chmod("xray-knife", 0o755)

def rename_config(link, info):
    try:
        cc = info.get('cc', 'UN')
        ping = info.get('ping', '?')
        speed = info.get('speed')
        
        # ساخت تگ مشخصات: 🇺🇸 US | 120ms | 1.5MB
        tag_parts = [get_flag(cc), cc, f"{ping}ms"]
        if speed and "Low" not in str(speed):
            tag_parts.append(speed)
        
        tag = " | ".join(tag_parts) + " | "
        
        if link.startswith("vmess://"):
            data = json.loads(base64.b64decode(link[8:]).decode('utf-8'))
            data['ps'] = tag + cleanup_remark(data.get('ps', 'Server'))
            return "vmess://" + base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
        elif "#" in link:
            base, remark = link.split("#", 1)
            return f"{base}#{quote(tag + cleanup_remark(remark))}"
        return f"{link}#{quote(tag + 'Server')}"
    except: return link

def test_process():
    input_file = "sub/all/mixed.txt"
    base_dir = "sub/tested"
    raw_dir = os.path.join(base_dir, "raw_results")
    os.makedirs(raw_dir, exist_ok=True)
    download_engine()

    # --- فاز ۱: پینگ ---
    logger.info("--- Phase 1: Latency Test (100 Threads) ---")
    p_csv = os.path.join(raw_dir, "ping_raw.csv")
    subprocess.run(["./xray-knife", "http", "-f", input_file, "-t", "100", "-o", p_csv, "-x", "csv"], stdout=subprocess.DEVNULL)

    top_candidates = []
    if os.path.exists(p_csv):
        with open(p_csv, "r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
            valid_rows = [r for r in reader if r.get('delay') and str(r['delay']).isdigit() and int(r['delay']) > 0]
            valid_rows.sort(key=lambda x: int(x['delay']))
            
            ping_passed = [rename_config(r.get('link') or r.get('Config'), {'cc': r.get('location', 'UN'), 'ping': r.get('delay')}) for r in valid_rows]
            p_text = "\n".join(filter(None, ping_passed))
            with open(os.path.join(base_dir, "ping_passed.txt"), "w", encoding="utf-8") as f: f.write(p_text)
            with open(os.path.join(base_dir, "ping_passed_base64.txt"), "w", encoding="utf-8") as f: f.write(to_base64(p_text))
            
            top_candidates = [r.get('link') or r.get('Config') for r in valid_rows[:400]]
            logger.info(f"Phase 1 finished. {len(valid_rows)} alive. Top 400 selected.")

    # --- فاز ۲: تست سرعت واقعی ---
    if top_candidates:
        tmp_txt = "top400_tmp.txt"
        with open(tmp_txt, "w") as f: f.write("\n".join(filter(None, top_candidates)))
        
        logger.info("--- Phase 2: Speed Test (5 Threads, 5MB Payload) ---")
        s_csv = os.path.join(raw_dir, "speed_raw.csv")
        speed_url = "https://speed.cloudflare.com/__down?bytes=5000000"
        
        cmd = ["./xray-knife", "http", "-f", tmp_txt, "-t", "5", "-o", s_csv, "-x", "csv", "-p", "-u", speed_url, "-a", "5000"]
        
        # اجرا و مانیتورینگ زنده
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if "Real Delay" in line: print(f"  {line.strip()}")

        speed_final = []
        if os.path.exists(s_csv):
            with open(s_csv, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    lnk = row.get('link') or row.get('Config')
                    raw_down = row.get('download') or row.get('speed') or "0"
                    dly = row.get('delay') or "0"
                    cc = row.get('location') or "UN"
                    
                    try:
                        spd_val = float(raw_down)
                        if spd_val > 0.5:
                            if spd_val >= 1024:
                                f_speed = f"{spd_val / 1024:.1f}MB"
                            else:
                                f_speed = f"{int(spd_val)}KB"
                            speed_final.append(rename_config(lnk, {'cc': cc, 'ping': dly, 'speed': f_speed}))
                        else:
                            speed_final.append(rename_config(lnk, {'cc': cc, 'ping': dly, 'speed': "LowSpeed"}))
                    except:
                        if lnk: speed_final.append(rename_config(lnk, {'cc': cc, 'ping': dly}))

        s_text = "\n".join(filter(None, speed_final))
        with open(os.path.join(base_dir, "speed_passed.txt"), "w", encoding="utf-8") as f: f.write(s_text)
        with open(os.path.join(base_dir, "speed_passed_base64.txt"), "w", encoding="utf-8") as f: f.write(to_base64(s_text))

    if os.path.exists(tmp_txt): os.remove(tmp_txt)
    logger.info("All operations completed successfully.")

if __name__ == "__main__":
    test_process()
