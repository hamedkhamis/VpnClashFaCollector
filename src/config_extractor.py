import os
import re
import base64
import logging

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Extractor")

# --- الگوهای REGEX جامع و دقیق ---
# نکته: بخش Remark (بعد از #) فقط کاراکترهای مجاز فارسی/انگلیسی/فاصله را قبول می‌کند.
COMMON_REMARK = r'(?:#[\u0600-\u06FF\w\s.-]*)?'

PATTERNS = {
    # 1. Base64 encoded protocols
    'vmess': rf'vmess:\/\/[a-zA-Z0-9+\/]+={{0,2}}{COMMON_REMARK}',
    'ssr': rf'ssr:\/\/[a-zA-Z0-9+\/=_]+{COMMON_REMARK}',

    # 2. URI-Standard (UUID based)
    'vless': rf'vless:\/\/[a-fA-F0-9-]{{36}}@[\w\-\.]+(?::\d+)?(?:\?[\w=&%.-]*)?{COMMON_REMARK}',
    'trojan': rf'trojan:\/\/[a-fA-F0-9-]{{36}}@[\w\-\.]+(?::\d+)?(?:\?[\w=&%.-]*)?{COMMON_REMARK}',
    'tuic': rf'tuic:\/\/[a-fA-F0-9-]{{36}}@[\w\-\.]+(?::\d+)?(?:\?[\w=&%.-]*)?{COMMON_REMARK}',

    # 3. Shadowsocks variants
    'ss': rf'ss:\/\/([a-zA-Z0-9+\/]+={{0,2}}|[\w\-\.!@#$%^&*()]+:[\w\-\.!@#$%^&*()]+@[\w\-\.]+(?::\d+)?){COMMON_REMARK}',

    # 4. Hysteria Family
    'hysteria': rf'hysteria:\/\/[\w\-\.]+(?::\d+)?\?(?:[\w=&.-]*&)?auth=[\w-]+(?:&[\w=&.-]*)?{COMMON_REMARK}', # Hysteria 1
    'hysteria2': rf'(?:hysteria2|hy2):\/\/[\w\-\.]+@[\w\-\.]+(?::[\d,\-]+)?(?:\?[\w=&.-]*)?{COMMON_REMARK}', # Hysteria 2

    # 5. Specialized QUIC & Others
    'juicity': rf'juicity:\/\/[a-fA-F0-9-]+:[\w\-\.]+@[\w\-\.]+(?::\d+)?\?[\w=&.-]*congestion_control=(?:bbr|cubic|new_reno)(?:&[\w=&.-]*)?{COMMON_REMARK}',
    'snell': rf'snell:\/\/[\w\-\.]+(?::\d+)?\?(?:[\w=&.-]*&)?psk=[\w-]+(?:&[\w=&.-]*)?{COMMON_REMARK}',
    'mieru': rf'mieru:\/\/[\w\-\.]+:[^@]+@[\w\-\.]+(?::\d+)?(?:\?[\w=&%.-]*)?{COMMON_REMARK}',
    'anytls': rf'anytls:\/\/[\w\-\.!@#$%^&*()]+@[\w\-\.]+(?::\d+)?(?:\?[\w=&%.-]*)?{COMMON_REMARK}',

    # 6. Proxy & Tunneling
    'ssh': rf'ssh:\/\/[\w\-\.]+(?::[\w\-\.]+)?@[\w\-\.]+(?::\d+)?(?:\?[\w=&%.-]*)?{COMMON_REMARK}',
    'wireguard': rf'(?:wireguard|wg|warp):\/\/[\w\-\.\/=@+]+(?::\d+)?(?:\?[\w=&.-]*)?{COMMON_REMARK}',
    'socks': rf'socks[45]?:\/\/(?:[\w\-\.]+(?::[\w\-\.]+)?@)?[\w\-\.]+(?::\d+)?',

    # 7. Telegram MTProto
    'mtproto': rf'(?:tg:\/\/proxy\?|https:\/\/t\.me\/proxy\?)server=[\w\-\.]+(?:&port=\d+)?(?:&secret=(?:dd)?[a-fA-F0-9]{{32}})(?:&[\w=&.-]*)?'
}

def write_files(data_map, output_dir):
    """ذخیره کانفیگ‌ها در فرمت‌های Normal و Base64 و Mixed"""
    if not any(data_map.values()):
        return

    os.makedirs(output_dir, exist_ok=True)
    
    mixed_content = set()
    
    # پردازش هر پروتکل به صورت جداگانه
    for proto, lines in data_map.items():
        if not lines: continue
        
        # افزودن به لیست Mixed کلی
        mixed_content.update(lines)
        
        # آماده‌سازی محتوا (مرتب‌سازی الفبایی برای نظم)
        content_sorted = sorted(list(lines))
        content_str = "\n".join(content_sorted)
        
        # 1. فایل متنی ساده (مثلاً vless.txt)
        with open(os.path.join(output_dir, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write(content_str)
            
        # 2. فایل بیس۶۴ (مثلاً vless_base64.txt)
        b64_str = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        with open(os.path.join(output_dir, f"{proto}_base64.txt"), "w", encoding="utf-8") as f:
            f.write(b64_str)

    # پردازش فایل Mixed (تجمیع همه پروتکل‌ها)
    if mixed_content:
        mixed_sorted = sorted(list(mixed_content))
        mixed_str = "\n".join(mixed_sorted)
        
        # mixed.txt
        with open(os.path.join(output_dir, "mixed.txt"), "w", encoding="utf-8") as f:
            f.write(mixed_str)
            
        # mixed_base64.txt
        mixed_b64 = base64.b64encode(mixed_str.encode("utf-8")).decode("utf-8")
        with open(os.path.join(output_dir, "mixed_base64.txt"), "w", encoding="utf-8") as f:
            f.write(mixed_b64)

def main():
    src_dir = "src/telegram"
    out_dir = "sub"
    
    # مخزن سراسری برای همه کانفیگ‌ها از همه کانال‌ها
    global_collection = {k: set() for k in PATTERNS.keys()}
    
    if not os.path.exists(src_dir):
        logger.error(f"دایرکتوری منبع {src_dir} یافت نشد. لطفاً ابتدا اسکرپر را اجرا کنید.")
        return

    # پیمایش پوشه هر کانال
    for channel_name in os.listdir(src_dir):
        channel_path = os.path.join(src_dir, channel_name)
        md_file = os.path.join(channel_path, "messages.md")
        
        if not os.path.isfile(md_file): continue
        
        logger.info(f"در حال استخراج از کانال: {channel_name}")
        
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # مخزن موقت برای کانال جاری
            channel_collection = {k: set() for k in PATTERNS.keys()}
            
            # جستجو برای هر پروتکل با Regex اختصاصی
            total_found = 0
            for proto, pattern in PATTERNS.items():
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    clean_conf = match.group(0).strip()
                    if clean_conf:
                        channel_collection[proto].add(clean_conf)
                        global_collection[proto].add(clean_conf)
                        total_found += 1
            
            # ذخیره خروجی‌های این کانال (فقط اگر چیزی پیدا شده باشد)
            if total_found > 0:
                write_files(channel_collection, os.path.join(out_dir, channel_name))
                logger.info(f"   -> {total_found} کانفیگ استخراج شد.")
            else:
                logger.info("   -> هیچ کانفیگ معتبری یافت نشد.")

        except Exception as e:
            logger.error(f"خطا در پردازش {channel_name}: {e}")

    # ذخیره خروجی سراسری (Subscription اصلی)
    logger.info("="*30)
    logger.info("در حال ساخت سابسکرایب جامع (sub/all)...")
    total_global = sum(len(v) for v in global_collection.values())
    
    if total_global > 0:
        write_files(global_collection, os.path.join(out_dir, "all"))
        logger.info(f"✅ پایان عملیات. مجموع {total_global} کانفیگ در sub/all ذخیره شد.")
    else:
        logger.warning("⚠️ هیچ کانفیگی در کل پروژه یافت نشد.")

if __name__ == "__main__":
    main()
