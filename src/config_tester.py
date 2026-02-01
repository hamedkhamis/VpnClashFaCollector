import os, subprocess, logging, zipfile, requests, csv, base64, json, sys
from urllib.parse import quote, unquote

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("ProxyLab")

def to_base64(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_flag(cc):
    cc = str(cc).upper()
    if len(cc) != 2: return "🌐"
    return "".join(chr(127397 + ord(c)) for c in cc)

def download_engine():
    if os.path.exists("xray-knife"): return
    logger.info("Downloading Xray-knife Engine...")
    url = "https://github.com/lilendian0x00/xray-knife/releases/latest/download/Xray-knife-linux-64.zip"
    r = requests.get(url, timeout=30)
    with open("engine.zip", "wb") as f: f.write(r.content)
    with zipfile.ZipFile("engine.zip", 'r') as z: z.extractall("engine_dir")
    for root, _, files in os.walk("engine_dir"):
        for file in files:
            if file == "xray-knife": os.rename(os.path.join(root, file), "xray-knife")
    os.chmod("xray-knife", 0o755)

def rename_config(link, info):
    try:
        cc = info.get('cc', 'UN')
        tag = f"{get_flag(cc)} {cc} | {info.get('ping', '?')}ms"
        if info.get('speed'): tag += f" | {info.get('speed')}"
        tag += " | "
        
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

    # --- فاز ۱: تست پینگ ---
    logger.info("Phase 1: Ping Testing...")
    p_csv = os.path.join(raw_dir, "ping_raw.csv")
    subprocess.run(["./xray-knife", "http", "-f", input_file, "-t", "60", "-o", p_csv, "-x", "csv"], stdout=subprocess.DEVNULL)

    ping_list = []
    top_300_raw = []
    if os.path.exists(p_csv):
        with open(p_csv, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                lnk = next((v for k, v in row.items() if k and k.lower() in ['config', 'link']), None)
                dly = next((v for k, v in row.items() if k and ('delay' in k.lower() or 'real' in k.lower())), '0')
                cc = next((v for k, v in row.items() if k and 'country' in k.lower()), 'UN')
                if lnk and str(dly).isdigit() and int(dly) > 0:
                    ping_list.append(rename_config(lnk, {'cc': cc, 'ping': dly}))
                    top_300_raw.append({'link': lnk, 'delay': int(dly)})

    # ذخیره خروجی پینگ
    p_text = "\n".join(ping_list)
    with open(os.path.join(base_dir, "ping_passed.txt"), "w", encoding="utf-8") as f: f.write(p_text)
    with open(os.path.join(base_dir, "ping_passed_base64.txt"), "w", encoding="utf-8") as f: f.write(to_base64(p_text))
    logger.info(f"Ping phase done. Saved {len(ping_list)} configs.")

    # --- فاز ۲: تست سرعت ---
    if top_300_raw:
        top_300_raw.sort(key=lambda x: x['delay'])
        tmp_top = "top300_tmp.txt"
        with open(tmp_top, "w") as f: f.write("\n".join([x['link'] for x in top_300_raw[:300]]))

        logger.info("Phase 2: Speed Testing (Top 300)...")
        s_csv = os.path.join(raw_dir, "speed_raw.csv")
        # تست با ترد کمتر و مهلت بیشتر برای جلوگیری از LowSpeed
        subprocess.run(["./xray-knife", "http", "-f", tmp_top, "-t", "5", "-o", s_csv, "-x", "csv", "-p", "-a", "15000"], stdout=subprocess.DEVNULL)

        speed_list = []
        if os.path.exists(s_csv):
            with open(s_csv, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    lnk = next((v for k, v in row.items() if k and k.lower() in ['config', 'link']), None)
                    spd = next((v for k, v in row.items() if k and 'speed' in k.lower()), '0')
                    dly = next((v for k, v in row.items() if k and 'delay' in k.lower()), '0')
                    cc = next((v for k, v in row.items() if k and 'country' in k.lower()), 'UN')
                    if lnk:
                        try:
                            s_val = float(str(spd).split()[0])
                            tag_spd = f"{s_val/1024:.1f}MB" if s_val > 0 else "LowSpeed"
                            speed_list.append(rename_config(lnk, {'cc': cc, 'ping': dly, 'speed': tag_spd}))
                        except: pass

        # ذخیره خروجی سرعت
        s_text = "\n".join(speed_list)
        with open(os.path.join(base_dir, "speed_passed.txt"), "w", encoding="utf-8") as f: f.write(s_text)
        with open(os.path.join(base_dir, "speed_passed_base64.txt"), "w", encoding="utf-8") as f: f.write(to_base64(s_text))
        logger.info(f"Speed phase done. Saved {len(speed_list)} configs.")

    if os.path.exists(tmp_top): os.remove(tmp_top)
    logger.info("All files updated successfully.")

if __name__ == "__main__":
    test_process()
