import os
import yaml
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import time

# ۱. بارگذاری تنظیمات
def load_settings():
    if not os.path.exists('config/settings.yaml'):
        return {'scraping': {'lookback_days': 7}, 'storage': {'base_path': 'src/telegram'}}
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# ۲. بارگذاری لیست کانال‌ها
def load_channels():
    if not os.path.exists('config/channels.txt'):
        return []
    with open('config/channels.txt', 'r', encoding='utf-8') as f:
        # استخراج نام کاربری از لینک (مثلا از https://t.me/akharinkhabar نام akharinkhabar را می‌گیرد)
        channels = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                username = line.split('/')[-1].replace('@', '')
                channels.append(username)
        return channels

# ۳. تبدیل HTML تلگرام به Markdown
def html_to_md(element):
    if not element:
        return ""
    
    # جایگزینی تگ‌های متداول با معادل Markdown
    for b in element.find_all('b'):
        b.replace_with(f"**{b.get_text()}**")
    for i in element.find_all('i'):
        i.replace_with(f"*{i.get_text()}*")
    for code in element.find_all('code'):
        code.replace_with(f"`{code.get_text()}`")
    for a in element.find_all('a'):
        href = a.get('href', '')
        a.replace_with(f"[{a.get_text()}]({href})")
    
    return element.get_text(separator='\n').strip()

def scrape_channel(username, lookback_days, base_path):
    print(f"--- Processing Channel: @{username} ---")
    url = f"https://t.me/s/{username}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Error: Could not access @{username}. Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'lxml')
        messages = soup.find_all('div', class_='tgme_widget_message')
        
        if not messages:
            print(f"No public messages found for @{username}.")
            return

        channel_title = soup.find('div', class_='tgme_channel_info_header_title').get_text().strip()
        safe_title = "".join([c for c in channel_title if c.isalnum() or c in (' ', '_')]).rstrip()
        
        channel_dir = os.path.join(base_path, safe_title)
        os.makedirs(channel_dir, exist_ok=True)
        
        time_threshold = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        
        count = 0
        with open(os.path.join(channel_dir, "messages.md"), "w", encoding="utf-8") as f:
            f.write(f"# Archive: {channel_title} (@{username})\n\n")
            
            # معکوس کردن لیست برای ذخیره از قدیم به جدید (یا حذف سورت برای جدید به قدیم)
            for msg in reversed(messages):
                try:
                    # استخراج زمان
                    time_element = msg.find('time', class_='time')
                    if not time_element: continue
                    
                    msg_date = datetime.fromisoformat(time_element.get('datetime').replace('Z', '+00:00'))
                    
                    if msg_date < time_threshold:
                        continue

                    # استخراج متن
                    text_area = msg.find('div', class_='tgme_widget_message_text')
                    content = html_to_md(text_area) if text_area else "[No text content]"
                    
                    # بررسی فوروارد
                    is_forwarded = msg.find('div', class_='tgme_widget_message_forwarded_from')
                    
                    f.write(f"### 🕒 {msg_date.strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
                    if is_forwarded:
                        f.write(f"> ↪️ **Forwarded Message**\n\n")
                    f.write(f"{content}\n\n")
                    f.write("---\n\n")
                    count += 1
                except Exception as e:
                    continue
        
        print(f"Successfully saved {count} messages for @{username}.")

    except Exception as e:
        print(f"Scraping failed for @{username}: {e}")

def main():
    settings = load_settings()
    usernames = load_channels()
    lookback_days = settings['scraping'].get('lookback_days', 7)
    base_path = settings['storage'].get('base_path', 'src/telegram')
    
    for username in usernames:
        scrape_channel(username, lookback_days, base_path)
        # وقفه کوتاه برای جلوگیری از حساسیت تلگرام
        time.sleep(5)

if __name__ == "__main__":
    main()
