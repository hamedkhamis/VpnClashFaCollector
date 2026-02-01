import os
import datetime

def generate_web_page():
    base_dir = "sub/final"
    output_html = "index.html"
    repo_raw_url = "https://raw.githubusercontent.com/10ium/VpnClashFaCollector/main"
    
    client_icons = {
        "clash": "fa-circle-nodes", "v2ray": "fa-share-nodes", "ss": "fa-key",
        "surfboard": "fa-wind", "surge": "fa-bolt", "quan": "fa-gear", "base64": "fa-code"
    }

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>پنل پیشرفته VpnClashFa</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
            body {{ font-family: 'Vazirmatn', sans-serif; background: #0f172a; color: #f1f5f9; }}
            .glass {{ background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }}
            .accordion-content {{ max-height: 0; overflow: hidden; transition: max-height 0.4s cubic-bezier(0, 1, 0, 1); }}
            .open .accordion-content {{ max-height: 2000px; transition: max-height 1s ease-in-out; }}
            .proxy-box {{ font-family: monospace; background: #000; padding: 15px; border-radius: 12px; height: 180px; overflow-y: auto; }}
            .btn-action {{ transition: all 0.2s; cursor: pointer; }}
            .btn-action:hover {{ transform: translateY(-2px); }}
        </style>
    </head>
    <body class="p-4 md:p-10 bg-slate-950">
        <div class="max-w-6xl mx-auto">
            <header class="text-center mb-10">
                <h1 class="text-3xl font-black text-blue-400 mb-2">مدیریت اشتراک VpnClashFa</h1>
                <p class="text-slate-500 text-xs italic">Update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </header>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
                <div class="lg:col-span-2 space-y-4">
                    <h2 class="font-bold text-emerald-400 flex items-center"><i class="fa-solid fa-bolt ml-2"></i> لینک‌های طلایی</h2>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
    """

    # لینک‌های تست شده
    gold_links = [
        ("پینگ OK (Normal)", f"{repo_raw_url}/sub/tested/ping_passed.txt"),
        ("پینگ OK (Base64)", f"{repo_raw_url}/sub/tested/ping_passed_base64.txt"),
        ("سرعت OK (Normal)", f"{repo_raw_url}/sub/tested/speed_passed.txt"),
        ("سرعت OK (Base64)", f"{repo_raw_url}/sub/tested/speed_passed_base64.txt")
    ]
    for title, url in gold_links:
        html_content += f"""
                    <div class="glass p-3 rounded-xl flex justify-between items-center">
                        <span class="text-xs font-bold">{title}</span>
                        <div class="flex gap-2">
                            <i onclick="copyText('{url}')" class="fa-solid fa-copy btn-action text-blue-400 p-2 bg-blue-400/10 rounded-lg" title="کپی لینک"></i>
                            <i onclick="downloadFile('{url}', '{title}.txt')" class="fa-solid fa-download btn-action text-emerald-400 p-2 bg-emerald-400/10 rounded-lg" title="دانلود"></i>
                        </div>
                    </div>"""

    html_content += """
                    </div>
                </div>
                <div class="glass p-4 rounded-2xl border-r-4 border-sky-500">
                    <h2 class="font-bold text-sky-400 mb-3 text-sm italic">Telegram Proxies</h2>
                    <div class="proxy-box text-[10px] text-sky-300 mb-3" id="tg-box">در حال دریافت...</div>
                    <button onclick="copyRawFromElement('tg-box')" class="w-full bg-sky-600 hover:bg-sky-500 py-2 rounded-xl text-xs font-bold transition">کپی همه پروکسی‌ها</button>
                </div>
            </div>

            <div class="space-y-4">
    """

    # پیمایش پوشه‌ها برای تولید دکمه‌های سه‌گانه
    if os.path.exists(base_dir):
        for folder in sorted(os.listdir(base_dir)):
            folder_path = os.path.join(base_dir, folder)
            if not os.path.isdir(folder_path): continue

            html_content += f"""
            <div class="glass rounded-2xl overflow-hidden accordion-item border border-white/5">
                <button onclick="toggleAccordion(this)" class="w-full p-5 text-right flex justify-between items-center group bg-slate-900/20">
                    <span class="text-sm font-bold text-slate-300 group-hover:text-blue-400 transition"><i class="fa-solid fa-folder-open ml-3 text-slate-500"></i>{folder}</span>
                    <i class="fa-solid fa-plus text-xs text-slate-500 transition-transform"></i>
                </button>
                <div class="accordion-content">
                    <div class="p-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 bg-slate-900/40">
            """

            for file in sorted(os.listdir(folder_path)):
                f_url = f"{repo_raw_url}/sub/final/{folder}/{file}"
                icon = next((v for k, v in client_icons.items() if k in file.lower()), "fa-link")
                
                html_content += f"""
                <div class="bg-slate-800/50 border border-white/5 p-4 rounded-2xl shadow-inner">
                    <div class="flex items-center mb-4">
                        <i class="fa-solid {icon} text-blue-500 ml-3"></i>
                        <span class="text-[11px] font-bold text-slate-200 truncate">{file}</span>
                    </div>
                    <div class="grid grid-cols-3 gap-2">
                        <button onclick="copyText('{f_url}')" class="bg-slate-700 hover:bg-blue-600 p-2 rounded-lg text-[10px] btn-action" title="کپی لینک">لینک</button>
                        <button onclick="copyContent('{f_url}')" class="bg-slate-700 hover:bg-purple-600 p-2 rounded-lg text-[10px] btn-action" title="کپی محتوا">متن</button>
                        <button onclick="downloadFile('{f_url}', '{file}')" class="bg-slate-700 hover:bg-emerald-600 p-2 rounded-lg text-[10px] btn-action" title="دانلود فایل">دانلود</button>
                    </div>
                </div>"""

            html_content += "</div></div></div>"

    # جاوا اسکریپت برای عملیات سه‌گانه
    html_content += """
            </div>
        </div>

        <script>
            function toggleAccordion(btn) {{
                const item = btn.parentElement;
                item.classList.toggle('open');
                btn.querySelector('.fa-solid').classList.toggle('fa-plus');
                btn.querySelector('.fa-solid').classList.toggle('fa-minus');
            }}

            function copyText(text) {{
                navigator.clipboard.writeText(text);
                showToast('لینک کپی شد');
            }}

            async function copyContent(url) {{
                try {{
                    const res = await fetch(url);
                    const data = await res.text();
                    navigator.clipboard.writeText(data);
                    showToast('محتوای فایل کپی شد');
                }} catch(e) {{ showToast('خطا در دریافت فایل', 'bg-red-600'); }}
            }}

            async function downloadFile(url, name) {{
                try {{
                    const res = await fetch(url);
                    const blob = await res.blob();
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = name;
                    link.click();
                }} catch(e) {{ showToast('خطا در دانلود', 'bg-red-600'); }}
            }}

            function copyRawFromElement(id) {{
                const text = document.getElementById(id).innerText;
                navigator.clipboard.writeText(text);
                showToast('پروکسی‌ها کپی شدند');
            }}

            function showToast(msg, color='bg-blue-600') {{
                const t = document.createElement('div');
                t.className = `fixed bottom-5 left-5 ${color} text-white px-5 py-2 rounded-xl text-xs shadow-2xl animate-pulse`;
                t.innerText = msg;
                document.body.appendChild(t);
                setTimeout(() => t.remove(), 2000);
            }}

            // بارگذاری پروکسی‌های تلگرام
            async function loadTG() {{
                const res = await fetch('https://raw.githubusercontent.com/10ium/VpnClashFaCollector/main/sub/all/tg.txt');
                const text = await res.text();
                document.getElementById('tg-box').innerText = text.split('\\n').filter(l => l.trim()).join('\\n\\n');
            }}
            loadTG();
        </script>
    </body>
    </html>
    """
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    generate_web_page()
