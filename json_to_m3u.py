#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON to M3U Converter
从网络获取JSON直播源数据，转换为标准M3U播放列表文件（按频道号排序，含EPG）

用法:
    python json_to_m3u.py [输出文件.m3u]
    不指定输出文件则默认保存为 channels.m3u
"""

import json
import sys
import os
import urllib.request
import urllib.error
import socket
from datetime import datetime, timezone

# 直播源JSON数据URL
CHANNELS_URL = "http://gxtvepg.taipan.jda.bcs.ottcn.com:8080/ysten-lvoms-epg/epg/getChannels.shtml?deviceGroupId=4747&districtCode=450000"

# EPG 电子节目指南链接
EPG_URL = "https://down.nigx.cn/epg.112114.xyz/pp.xml.gz"


def log(msg):
    """打印带时间戳的日志"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now}] {msg}")


def is_valid_url(url):
    """检查是否为有效的http/https URL"""
    if not url or not isinstance(url, str):
        return False
    return url.startswith(("http://", "https://")) and len(url) > 8


def get_sort_key(item):
    """
    获取排序用的key值
    按 no 字段从小到大排序，没有 no 的放最后
    """
    no = item.get("no")
    if no is None:
        return float("inf")
    try:
        return int(no)
    except (ValueError, TypeError):
        try:
            return float(no)
        except (ValueError, TypeError):
            return float("inf")


def fetch_json(url, timeout=30):
    """从网络获取JSON数据"""
    log(f"正在获取数据: {url}")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "http://gxtvepg.taipan.jda.bcs.ottcn.com:8080/",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}: {response.reason}")

            raw_data = response.read()

            for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
                try:
                    text = raw_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = raw_data.decode("utf-8", errors="replace")

            data = json.loads(text)
            log("数据获取成功")
            return data

    except urllib.error.HTTPError as e:
        log(f"HTTP错误: {e.code} {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        log(f"网络错误: {e.reason}")
        sys.exit(1)
    except socket.timeout:
        log(f"请求超时（{timeout}秒）")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log(f"JSON解析失败: {e}")
        sys.exit(1)


def json_to_m3u(data, output_file="channels.m3u"):
    """将JSON数据转换为M3U格式并写入文件"""
    if not isinstance(data, list):
        log("错误: JSON数据应为列表格式")
        sys.exit(1)

    log(f"共获取 {len(data)} 个频道")

    data = sorted(data, key=get_sort_key)

    lines = []
    lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')

    converted_count = 0
    skipped_count = 0

    for item in data:
        if item.get("usable") == 0:
            skipped_count += 1
            continue

        channel_name = item.get("channelName", "Unknown")
        logo = item.get("logo", "")
        channel_icon = item.get("channelIcon", "")
        tvg_id = item.get("uuid", "") or item.get("urlid", "")
        chno = item.get("no", "")
        play_url = item.get("livePlayUrl", "")

        tvg_logo = ""
        if is_valid_url(logo):
            tvg_logo = logo
        elif is_valid_url(channel_icon):
            tvg_logo = channel_icon

        extinf_parts = ["#EXTINF:-1"]

        if tvg_id:
            extinf_parts.append(f'tvg-id="{tvg_id}"')

        extinf_parts.append(f'tvg-name="{channel_name}"')

        if tvg_logo:
            extinf_parts.append(f'tvg-logo="{tvg_logo}"')

        if chno:
            extinf_parts.append(f'tvg-chno="{chno}"')

        extinf_line = " ".join(extinf_parts) + f",{channel_name}"
        lines.append(extinf_line)
        lines.append(play_url)
        converted_count += 1

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        log(f"转换成功！已生成文件: {output_file}")
        log(f"有效频道: {converted_count} 个")
        if skipped_count > 0:
            log(f"跳过不可用: {skipped_count} 个")
        log(f"EPG: {EPG_URL}")
    except IOError as e:
        log(f"写入文件失败: {e}")
        sys.exit(1)


def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else "channels.m3u"
    data = fetch_json(CHANNELS_URL)
    json_to_m3u(data, output_file)


if __name__ == "__main__":
    main()
