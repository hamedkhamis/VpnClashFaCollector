import os
import re
import base64
import logging
import html

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Extractor")

PROTOCOLS = [
    'vmess', 'vless', 'trojan', 'ss', 'ssr', 'tuic', 'hysteria', 'hysteria2', 
    'hy2', 'juicity', 'snell', 'mieru', 'anytls', 'ssh', 'wireguard', 'wg', 
    'warp', 'socks', 'socks4', 'socks5', 'tg'
]

# نشانگرهای توقف استخراج: پرانتز، کروشه، کوتیشن و فضای خالی
NEXT_CONFIG_LOOKAHEAD = r'(?=' + '|'.join([rf'{p}:\/\/' for p in PROTOCOLS if p != 'tg']) + r'|https:\/\/t\.me\/proxy\?|tg:\/\/proxy\?|[()\[\]"\'\s])'

def clean_telegram_link(link):
    """
    پاکسازی لینک‌های تلگرام از کاراکترهای مزاحم انتهای لینک و اصلاح HTML Entities
    """
    # 1. تبدیل &amp; به & برای سازگاری با ویندوز
    link = html.unescape(link)
    
    # 2. حذف کاراکترهای مزاحم از انتهای لینک (پرانتز، کروشه، نقطه، ویرگول و غیره)
    # این رگکس از سمت راست، هر چه کاراکتر غیرمجاز باشد را می‌برد
    link = re.sub(r'[()\[\]\s!.,;\'"]+$', '', link)
    
    return link

def get_flexible_pattern(protocol_prefix):
    if protocol_prefix == 'tg':
        prefix = rf'(?:tg:\/\/proxy\?|https:\/\/t\.me\/proxy\?)'
    else:
        prefix = rf'{protocol_prefix}:\/\/'

    # استخراج اولیه تا رسیدن به یکی از نشانگرهای توقف
    return rf'{prefix}(?:(?!\s{{4,}}|[()\[\]]).)+?(?={NEXT_CONFIG_LOOKAHEAD}|$)'

def is_windows_compatible(link):
    secret_match = re.search(r"secret=([a-zA-Z0-9]+)", link)
    if not secret_match:
        return True
    secret = secret_match.group(1).lower()
    # محدودیت ee و طول برای ویندوز
    if secret.startswith('ee') or len(secret) > 64:
        return False
    return True

def save_content(directory, filename, content_list):
    if not content_list:
        return
    content_sorted = sorted(list(set(content_list))) # حذف تکراری‌های احتمالی بعد از Clean
    content_str = "\n".join(content_sorted)
    with open(os.path.join(directory, f"{filename}.txt"), "w", encoding="utf-8") as f:
        f.write(content_str)
    b64_str = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    with open(os.path.join(directory, f"{filename}_base64.txt"), "w", encoding="utf-8") as f:
        f.write(b64_str)

def write_files(data_map, output_dir):
    if not any(data_map.values()):
        return
    os.makedirs(output_dir, exist_ok=True)
    mixed_content = set()
    for proto, lines in data_map.items():
        if not lines: continue
        mixed_content.update(lines)
        if proto == 'tg':
            windows_tg = {l for l in lines if is_windows_compatible(l)}
            save_content(output_dir, "tg", lines)
            save_content(output_dir, "tg_windows", windows_tg)
            save_content(output_dir, "tg_android", lines)
        else:
            save_content(output_dir, proto, lines)
    if mixed_content:
        save_content(output_dir, "mixed", mixed_content)

def main():
    src_dir = "src/telegram"
    out_dir = "sub"
    global_collection = {k: set() for k in PROTOCOLS}
    
    if not os.path.exists(src_dir):
        return

    # تولید پترن‌ها یکبار برای بهینگی
    patterns = {p: get_flexible_pattern(p) for p in PROTOCOLS}

    for channel_name in os.listdir(src_dir):
        channel_path = os.path.join(src_dir, channel_name)
        md_file = os.path.join(channel_path, "messages.md")
        if not os.path.isfile(md_file): continue
        
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            channel_collection = {k: set() for k in PROTOCOLS}
            for proto, pattern in patterns.items():
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    raw_link = match.group(0).strip()
                    # اعمال پاکسازی نهایی
                    clean_link = clean_telegram_link(raw_link) if proto == 'tg' else raw_link
                    
                    if clean_link:
                        channel_collection[proto].add(clean_link)
                        global_collection[proto].add(clean_link)
            
            write_files(channel_collection, os.path.join(out_dir, channel_name))
        except Exception as e:
            logger.error(f"Error in {channel_name}: {e}")

    if sum(len(v) for v in global_collection.values()) > 0:
        write_files(global_collection, os.path.join(out_dir, "all"))

if __name__ == "__main__":
    main()
