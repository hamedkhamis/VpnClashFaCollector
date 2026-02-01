import os
import subprocess
import logging
import zipfile
import requests
import csv
import base64
import json
from urllib.parse import quote, unquote

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Tester")

def get_flag_emoji(country_code):
    if not country_code or len(str(country_code)) != 2: return "🌐"
    return "".join(chr(127397 + ord(c)) for c in str(country_code).upper())

def download_xray_knife():
    if os.path.exists("xray-knife"): return
    url = "https://github.com/lilendian0x00/xray-knife/releases/latest/download/Xray-knife-linux-64.zip"
    r = requests.get(url, timeout=30)
    with open("xray-knife.zip", "wb") as f: f.write(r.content)
    with zipfile.ZipFile("xray-knife.zip", 'r') as z: z.extractall("xray-knife-dir")
    for root, _, files in os.walk("xray-knife-dir"):
        for file in files:
            if file == "xray-knife":
                os.rename(os.path.join(root, file), "xray-knife")
    os.chmod("xray-knife", 0o755)

def rename_config(link, info):
    if not link: return None
    flag = get_flag_emoji(info.get('cc', 'UN'))
    tag = f"{flag} {info.get('cc', 'UN')} | {info.get('ping', '?')}ms"
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

def run_test(infile, outfile, threads=50, speed=False):
    # پاک کردن فایل قدیمی اگر وجود داشت
    if os.path.exists(outfile): os.remove(outfile)
    cmd = ["./xray-knife", "http", "-f", infile, "-t", str(threads), "-o", outfile, "-x", "csv"]
    if speed: cmd.append("-p")
    subprocess.run(cmd, check=False)

def test_process():
    input_file = "sub/all/mixed.txt"
    output_dir = "sub/tested"
    os.makedirs(output_dir, exist_ok=True)
    download_xray_knife()

    logger.info("--- Phase 1: Latency Test ---")
    run_test(input_file, "res_ping.csv", threads=40) # کاهش ترد برای پایداری

    ping_ok = []
    top_list = []

    if os.path.exists("res_ping.csv"):
        with open("res_ping.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # چاپ نام ستون‌ها برای دیباگ در لاگ گیت‌هاب
            logger.info(f"Columns found: {reader.fieldnames}")
            
            for row in reader:
                # پیدا کردن لینک و پینگ فارغ از نام ستون (جستجوی منعطف)
                link = next((v for k, v in row.items() if k in ['Config', 'Link', 'URL']), None)
                delay = next((v for k, v in row.items() if 'Delay' in k or 'Real' in k), '0')
                cc = next((v for k, v in row.items() if 'Country' in k or 'CC' in k), 'UN')
                
                if link and str(delay).isdigit() and int(delay) > 0:
                    ping_ok.append(rename_config(link, {'cc': cc, 'ping': delay}))
                    row['sort_key'] = int(delay)
                    top_list.append(row)

    if ping_ok:
        with open(os.path.join(output_dir, "ping_passed.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(ping_ok))
        
        # انتخاب ۳۰۰ تای برتر
        top_list.sort(key=lambda x: x['sort_key'])
        with open("top300.txt", "w", encoding="utf-8") as f:
            f.write("\n".join([next((v for k, v in r.items() if k in ['Config', 'Link']), '') for r in top_list[:300]]))

        logger.info(f"--- Phase 2: Speed Test on {len(top_list[:300])} configs ---")
        run_test("top300.txt", "res_speed.csv", threads=5, speed=True)

        speed_ok = []
        if os.path.exists("res_speed.csv"):
            with open("res_speed.csv", "r", encoding="utf-8-sig") as f:
                for s_row in csv.DictReader(f):
                    s_link = next((v for k, v in s_row.items() if k in ['Config', 'Link']), None)
                    s_speed = next((v for k, v in s_row.items() if 'Speed' in k), '0')
                    s_delay = next((v for k, v in s_row.items() if 'Delay' in k or 'Real' in k), '0')
                    s_cc = next((v for k, v in s_row.items() if 'Country' in k or 'CC' in k), 'UN')
                    
                    try:
                        if s_link and float(s_speed) > 0:
                            mbps = f"{float(s_speed)/1024:.1f}MB"
                            speed_ok.append(rename_config(s_link, {'cc': s_cc, 'ping': s_delay, 'speed': mbps}))
                    except: continue

            with open(os.path.join(output_dir, "speed_passed.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(speed_ok))

    logger.info("Done!")

if __name__ == "__main__":
    test_process()
