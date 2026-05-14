import os
import re
import time
import socket
from concurrent.futures import ThreadPoolExecutor

# ===================== 配置 =====================
PING_TIMEOUT = 2
KEEP_TOP_NUM = 5
SRC_DIR = "sources"
OUT_DIR = "output"

ALLOW_KEYWORDS = [
    "CCTV", "央视", "卫视", "北京卫视", "上海卫视", "广东卫视",
    "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "安徽卫视",
    "山东卫视", "辽宁卫视", "湖北卫视", "四川卫视"
]
# ================================================

channel_dict = {}

def ping_url(url):
    try:
        domain = re.findall(r"https?://([^/]+)", url)[0]
        socket.setdefaulttimeout(PING_TIMEOUT)
        start = time.time()
        socket.gethostbyname(domain)
        cost = round((time.time() - start) * 1000, 2)
        return url, cost
    except:
        return url, 9999

def parse_txt_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except:
        return

    for line in lines:
        line = line.strip()
        if not line or "," not in line:
            continue
        parts = line.split(",", 1)
        if len(parts) != 2:
            continue
        name, urls_str = parts
        url_list = [u.strip() for u in urls_str.split("#") 
                    if u.strip().startswith("http")]
        if not url_list:
            continue
        if name not in channel_dict:
            channel_dict[name] = []
        channel_dict[name].extend(url_list)

def scan_all_txt():
    os.makedirs(SRC_DIR, exist_ok=True)
    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            if f.lower().endswith(".txt"):
                parse_txt_file(os.path.join(root, f))

def filter_cctv_weishi():
    new_dict = {}
    for name in channel_dict:
        for kw in ALLOW_KEYWORDS:
            if kw in name:
                new_dict[name] = channel_dict[name]
                break
    return new_dict

def speed_test_and_sort(channel_data):
    res = {}
    with ThreadPoolExecutor(max_workers=20) as exe:
        task_map = {}
        for name, urls in channel_data.items():
            for u in set(urls):
                task_map[exe.submit(ping_url, u)] = (name, u)

        name_url_cost = {}
        for future in task_map:
            name, url = task_map[future]
            u, cost = future.result()
            if name not in name_url_cost:
                name_url_cost[name] = []
            name_url_cost[name].append((url, cost))

    for name, lst in name_url_cost.items():
        sort_lst = sorted(lst, key=lambda x: x[1])
        top = sort_lst[:KEEP_TOP_NUM]
        res[name] = top
    return res

def generate_html(best_data):
    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>央视卫视优选直播源</title>
<style>
body{padding:20px;font-family:微软雅黑;}
.item{margin:8px 0;padding:8px;border:1px #eee solid;border-radius:6px;}
a{margin:0 10px;color:#0066cc;text-decoration:none;}
</style>
</head>
<body>
<h2>自动测速优选 - 央视卫视频道（每频道最快{num}条）</h2>
<p>更新时间：{now_time}</p>
{content}
</body>
</html>
"""
    content = ""
    now_time = time.strftime("%Y-%m-%d %H:%M:%S")
    for name, url_list in best_data.items():
        content += f'<div class="item"><b>{name}</b> '
        for url, delay in url_list:
            content += f'<a href="{url}" target="_blank">线路({delay}ms)</a>'
        content += "</div>\n"
    html = html_template.format(num=KEEP_TOP_NUM, now_time=now_time, content=content)
    out_path = os.path.join(OUT_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

def generate_m3u(best_data):
    m3u = "#EXTM3U\n"
    for name, url_list in best_data.items():
        for url, _ in url_list:
            m3u += f'#EXTINF:-1,{name}\n{url}\n'
    out_path = os.path.join(OUT_DIR, "live.m3u")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(m3u)

def main():
    # 强制建目录，不怕不存在
    os.makedirs(SRC_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    
    scan_all_txt()
    if not channel_dict:
        print("未扫描到任何直播源txt内容")
        return

    filter_data = filter_cctv_weishi()
    if not filter_data:
        print("过滤后无央视卫视频道")
        return

    best_data = speed_test_and_sort(filter_data)
    generate_html(best_data)
    generate_m3u(best_data)
    print("✅ 完成：扫描->测速->择优->生成网页成功")

if __name__ == "__main__":
    main()
