import os
import re
import base64
import logging

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Extractor")

# لیست پروتکل‌ها برای تشخیص مرز (Lookahead)
PROTOCOLS = [
    'vmess', 'vless', 'trojan', 'ss', 'ssr', 'tuic', 'hysteria', 'hysteria2', 
    'hy2', 'juicity', 'snell', 'mieru', 'anytls', 'ssh', 'wireguard', 'wg', 
    'warp', 'socks', 'socks4', 'socks5', 'tg', 'https'
]

# ساخت یک الگوی نگاه به جلو (Lookahead) برای تشخیص شروع کانفیگ بعدی
# این باعث می‌شود اگر دو کانفیگ پشت سر هم باشند، اولی قبل از شروع دومی متوقف شود.
NEXT_CONFIG_LOOKAHEAD = r'(?=' + '|'.join([rf'{p}:\/\/' for p in PROTOCOLS]) + r'|https:\/\/t\.me\/proxy\?|tg:\/\/proxy\?)'

def get_flexible_pattern(protocol_prefix):
    """
    ایجاد یک الگوی منعطف:
    شروع با پروتکل، سپس هر چیزی به جز خط جدید و بیش از 4 فاصله، 
    تا زمانی که به مرز بعدی (خط بعد، 4 فاصله، یا کانفیگ بعدی) برسیم.
    """
    # برای تلگرام پروکسی ها که ساختار متفاوتی دارند
    if protocol_prefix in ['tg', 'https']:
        prefix = rf'(?:tg:\/\/proxy\?|https:\/\/t\.me\/proxy\?)'
    else:
        prefix = rf'{protocol_prefix}:\/\/'

    # منطق: 
    # [^\s\n]+ : حداقل یک کاراکتر غیر از فاصله و خط جدید
    # (?:(?!\s{4,}).)* : ادامه بده تا جایی که با 4 فاصله متوالی روبرو نشدی
    # (?=\n|$) : یا تا انتهای خط یا انتهای کل متن
    return rf'{prefix}(?:(?!\s{{4,}}).)+?(?=\s{{4,}}|\n|{NEXT_CONFIG_LOOKAHEAD}|$)'

# تولید داینامیک الگوها بر اساس لیست پروتکل‌ها
PATTERNS = {p: get_flexible_pattern(p) for p in PROTOCOLS}

def write_files(data_map, output_dir):
    """ذخیره کانفیگ‌ها در فرمت‌های Normal و Base64 و Mixed"""
    if not any(data_map.values()):
        return

    os.makedirs(output_dir, exist_ok=True)
    
    mixed_content = set()
    
    for proto, lines in data_map.items():
        if not lines: continue
        
        mixed_content.update(lines)
        content_sorted = sorted(list(lines))
        content_str = "\n".join(content_sorted)
        
        # 1. فایل متنی ساده
        with open(os.path.join(output_dir, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write(content_str)
            
        # 2. فایل بیس۶۴
        b64_str = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        with open(os.path.join(output_dir, f"{proto}_base64.txt"), "w", encoding="utf-8") as f:
            f.write(b64_str)

    if mixed_content:
        mixed_sorted = sorted(list(mixed_content))
        mixed_str = "\n".join(mixed_sorted)
        
        with open(os.path.join(output_dir, "mixed.txt"), "w", encoding="utf-8") as f:
            f.write(mixed_str)
            
        mixed_b64 = base64.b64encode(mixed_str.encode("utf-8")).decode("utf-8")
        with open(os.path.join(output_dir, "mixed_base64.txt"), "w", encoding="utf-8") as f:
            f.write(mixed_b64)

def main():
    src_dir = "src/telegram"
    out_dir = "sub"
    
    global_collection = {k: set() for k in PATTERNS.keys()}
    
    if not os.path.exists(src_dir):
        logger.error(f"دایرکتوری منبع {src_dir} یافت نشد.")
        return

    for channel_name in os.listdir(src_dir):
        channel_path = os.path.join(src_dir, channel_name)
        md_file = os.path.join(channel_path, "messages.md")
        
        if not os.path.isfile(md_file): continue
        
        logger.info(f"در حال استخراج منعطف از: {channel_name}")
        
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            channel_collection = {k: set() for k in PATTERNS.keys()}
            total_found = 0
            
            for proto, pattern in PATTERNS.items():
                # استفاده از re.IGNORECASE برای امنیت بیشتر در نام پروتکل‌ها
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    clean_conf = match.group(0).strip()
                    if clean_conf:
                        channel_collection[proto].add(clean_conf)
                        global_collection[proto].add(clean_conf)
                        total_found += 1
            
            if total_found > 0:
                write_files(channel_collection, os.path.join(out_dir, channel_name))
                logger.info(f"   -> {total_found} کانفیگ استخراج شد.")

        except Exception as e:
            logger.error(f"خطا در پردازش {channel_name}: {e}")

    logger.info("="*30)
    logger.info("در حال ساخت سابسکرایب جامع...")
    total_global = sum(len(v) for v in global_collection.values())
    
    if total_global > 0:
        write_files(global_collection, os.path.join(out_dir, "all"))
        logger.info(f"✅ پایان عملیات. مجموع {total_global} کانفیگ در sub/all ذخیره شد.")
    else:
        logger.warning("⚠️ هیچ کانفیگی یافت نشد.")

if __name__ == "__main__":
    main()
