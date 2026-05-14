import os
import re
import time
import subprocess
import socket
from concurrent.futures import ThreadPoolExecutor

# ===================== 配置项 可自行修改 =====================
# 超时秒数
PING_TIMEOUT = 2
# 每个频道保留最快线路数量
KEEP_TOP_NUM = 5
# 扫描目录、输出目录
SRC_DIR = "sources"
OUT_DIR = "output"
# 只保留包含这些关键词的频道（央视、卫视）
ALLOW_KEYWORDS = [
    "CCTV", "央视", "卫视", "北京卫视", "上海卫视", "广东卫视",
    "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "安徽卫视",
    "山东卫视", "辽宁卫视", "湖北卫视", "四川卫视"
]
# ============================================================

# 存储所有频道：{频道名: [(url, 延迟), ...]}
channel_dict = {}

def ping_url(url):
    """测速：取域名ping延迟"""
    try:
        # 提取域名
        domain = re.findall(r"https?://([^/]+)", url)[0]
        start = time.time()
        socket.gethostbyname(domain)
        cost = round((time.time() - start) * 1000, 2)
        return url, cost
    except:
        return url, 9999

def parse_txt_file(file_path):
    """解析txt直播源 格式：频道名,url1#url2#url3"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line or "," not in line:
            continue
        name, urls_str = line.split(",", 1)
        url_list = [u.strip() for u in urls_str.split("#") if u.strip().startswith("http")]
        if not url_list:
            continue
        # 合并同频道
        if name not in channel_dict:
            channel_dict[name] = []
        for u in url_list:
            channel_dict[name].append(u)

def scan_all_txt():
    """扫描sources下所有txt"""
    if not os.path.exists(SRC_DIR):
        os.mkdir(SRC_DIR)
    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            if f.lower().endswith(".txt"):
                parse_txt_file(os.path.join(root, f))

def filter_cctv_weishi():
    """只保留央视卫视频道"""
    new_dict = {}
    for name in channel_dict:
        for kw in ALLOW_KEYWORDS:
            if kw in name:
                new_dict[name] = channel_dict[name]
                break
    return new_dict

def speed_test_and_sort(channel_data):
    """多线程测速，每个频道取最快KEEP_TOP_NUM条"""
    res = {}
    with ThreadPoolExecutor(max_workers=50) as exe:
        task_map = {}
        for name, urls in channel_data.items():
            for u in urls:
                task_map[exe.submit(ping_url, u)] = (name, u)
        # 收集结果
        name_url_cost = {}
        for future in task_map:
            name, url = task_map[future]
            u, cost = future.result()
            if name not in name_url_cost:
                name_url_cost[name] = []
            name_url_cost[name].append((url, cost))
    # 每个频道按延迟升序，取前N条
    for name, lst in name_url_cost.items():
        sort_lst = sorted(lst, key=lambda x: x[1])
        top = sort_lst[:KEEP_TOP_NUM]
        res[name] = top
    return res

def generate_html(best_data):
    """生成播放网页"""
    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>央视卫视优选直播源</title>
<style>
body{padding:20px;}
.item{margin:8px 0;padding:8px;border:1px #eee solid;}
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
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def generate_m3u(best_data):
    """生成m3u直播源"""
    m3u = "#EXTM3U\n"
    for name, url_list in best_data.items():
        for url, _ in url_list:
            m3u += f'#EXTINF:-1,{name}\n{url}\n'
    with open(os.path.join(OUT_DIR, "live.m3u"), "w", encoding="utf-8") as f:
        f.write(m3u)

def main():
    if not os.path.exists(OUT_DIR):
        os.mkdir(OUT_DIR)
    # 1.扫描所有txt
    scan_all_txt()
    # 2.过滤只留央视卫视
    filter_data = filter_cctv_weishi()
    # 3.测速择优
    best_data = speed_test_and_sort(filter_data)
    # 4.生成网页和m3u
    generate_html(best_data)
    generate_m3u(best_data)
    print("完成：扫描->测速->择优->生成网页成功")

if __name__ == "__main__":
    main()
