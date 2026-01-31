import os
import yaml
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import time

def load_settings():
    if not os.path.exists('config/settings.yaml'):
        return {'scraping': {'lookback_days': 7}, 'storage': {'base_path': 'src/telegram'}}
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_channels():
    if not os.path.exists('config/channels.txt'):
        return []
    with open('config/channels.txt', 'r', encoding='utf-8') as f:
        usernames = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # استخراج یوزرنیم از لینک یا متن ساده
                username = line.split('/')[-1].replace('@', '').split('?')[0]
                usernames.append(username)
        return usernames

def html_to_md(element):
    if not element: return ""
    for b in element.find_all('b'): b.replace_with(f"**{b.get_text()}**")
    for i in element.find_all('i'): i.replace_with(f"*{i.get_text()}*")
    for code in element.find_all('code'): code.replace_with(f"`{code.get_text()}`")
    for a in element.find_all('a'):
        href = a.get('href', '')
        a.replace_with(f"[{a.get_text()}]({href})")
    return element.get_text(separator='\n').strip()

def scrape_channel(username, lookback_days, base_path):
    print(f"--- شروع پردازش کانال: @{username} ---")
    
    # پوشه بر اساس آیدی کانال ساخته می‌شود
    channel_dir = os.path.join(base_path, username)
    os.makedirs(channel_dir, exist_ok=True)
    
    time_threshold = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    all_messages = []
    
    # پارامتر برای پیمایش به عقب در زمان
    last_msg_id = None
    reached_end = False
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    while not reached_end:
        url = f"https://t.me/s/{username}"
        if last_msg_id:
            url += f"?before={last_msg_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200: break

            soup = BeautifulSoup(response.text, 'lxml')
            messages = soup.find_all('div', class_='tgme_widget_message')
            
            if not messages: break

            current_page_messages = []
            for msg in reversed(messages):
                # استخراج ID پیام برای پیمایش به عقب
                msg_id_attr = msg.get('data-post')
                if msg_id_attr:
                    last_msg_id = msg_id_attr.split('/')[-1]

                time_element = msg.find('time', class_='time')
                if not time_element: continue
                
                msg_date = datetime.fromisoformat(time_element.get('datetime').replace('Z', '+00:00'))
                
                # اگر پیام قدیمی‌تر از بازه ما بود، توقف کن
                if msg_date < time_threshold:
                    reached_end = True
                    break
                
                # استخراج محتوا
                text_area = msg.find('div', class_='tgme_widget_message_text')
                content = html_to_md(text_area) if text_area else ""
                
                if content:
                    is_forwarded = msg.find('div', class_='tgme_widget_message_forwarded_from')
                    current_page_messages.append({
                        'date': msg_date,
                        'content': content,
                        'forwarded': is_forwarded is not None
                    })
            
            if not current_page_messages and not reached_end:
                # اگر در این صفحه پیامی نبود ولی هنوز به محدودیت زمانی نرسیدیم، ادامه بده
                pass
            else:
                all_messages.extend(current_page_messages)

            # جلوگیری از بلاک شدن: وقفه بین صفحات
            time.sleep(2)
            
            # اگر تعداد پیام‌های دریافتی در این صفحه خیلی کم بود یا پیام جدیدی یافت نشد
            if not messages or len(current_page_messages) == 0 and reached_end:
                break

        except Exception as e:
            print(f"Error: {e}")
            break

    # ذخیره نهایی پیام‌ها (مرتب شده از جدید به قدیم)
    if all_messages:
        # حذف پیام‌های تکراری احتمالی بر اساس متن و تاریخ
        unique_messages = []
        seen = set()
        for m in all_messages:
            identifier = f"{m['date']}_{m['content'][:50]}"
            if identifier not in seen:
                unique_messages.append(m)
                seen.add(identifier)

        with open(os.path.join(channel_dir, "messages.md"), "w", encoding="utf-8") as f:
            f.write(f"# آرشیو کانال: @{username}\n")
            f.write(f"بازه زمانی: {lookback_days} روز گذشته\n\n")
            
            for m in unique_messages:
                f.write(f"### 🕒 {m['date'].strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
                if m['forwarded']:
                    f.write(f"> ↪️ **Forwarded Message**\n\n")
                f.write(f"{m['content']}\n\n")
                f.write("---\n\n")
        
        print(f"تعداد {len(unique_messages)} پیام در پوشه '{username}' ذخیره شد.")

def main():
    settings = load_settings()
    usernames = load_channels()
    lookback_days = settings['scraping'].get('lookback_days', 7)
    base_path = settings['storage'].get('base_path', 'src/telegram')
    
    for username in usernames:
        scrape_channel(username, lookback_days, base_path)
        time.sleep(5) # وقفه بین کانال‌ها

if __name__ == "__main__":
    main()
