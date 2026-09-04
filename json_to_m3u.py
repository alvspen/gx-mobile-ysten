#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON to M3U Converter
从网络获取JSON直播源数据，转换为标准M3U播放列表文件（按频道号排序，含EPG）
兼容 Python 2.7 和 Python 3.x

用法:
    python json_to_m3u.py [输出文件.m3u]
    不指定输出文件则默认保存为 channels.m3u
"""

from __future__ import print_function
import json
import sys
import os
from datetime import datetime

# Python 2/3 兼容
PY3 = sys.version_info[0] == 3
if PY3:
    import urllib.request as urllib2
    import urllib.error
    import socket
else:
    import urllib2
    import socket

# 直播源JSON数据URL
CHANNELS_URL = "http://gxtvepg.taipan.jda.bcs.ottcn.com:8080/ysten-lvoms-epg/epg/getChannels.shtml?deviceGroupId=4747&districtCode=450000"

# EPG 电子节目指南链接
EPG_URL = "https://down.nigx.cn/epg.112114.xyz/pp.xml.gz"


def log(msg):
    """打印带时间戳的日志"""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    print("[{0}] {1}".format(now, msg))


def is_valid_url(url):
    """检查是否为有效的http/https URL"""
    if not url or not isinstance(url, str if PY3 else basestring):
        return False
    return url.startswith(('http://', 'https://')) and len(url) > 8


def get_sort_key(item):
    """
    获取排序用的key值
    按 no 字段从小到大排序，没有 no 的放最后
    """
    no = item.get('no')
    if no is None:
        return float('inf')
    try:
        return int(no)
    except (ValueError, TypeError):
        try:
            return float(no)
        except (ValueError, TypeError):
            return float('inf')


def fetch_json(url, timeout=30):
    """从网络获取JSON数据"""
    log("正在获取数据: " + url)

    req = urllib2.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'http://gxtvepg.taipan.jda.bcs.ottcn.com:8080/',
        }
    )

    try:
        if PY3:
            response = urllib2.urlopen(req, timeout=timeout)
        else:
            response = urllib2.urlopen(req, timeout=timeout)

        if hasattr(response, 'status') and response.status != 200:
            raise Exception("HTTP {0}: {1}".format(response.status, response.reason))

        raw_data = response.read()

        # Python 3 需要解码，Python 2 已经是 str
        if PY3:
            for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    text = raw_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = raw_data.decode('utf-8', errors='replace')
        else:
            text = raw_data

        data = json.loads(text)
        log("数据获取成功")
        return data

    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'code'):
            log("HTTP错误: {0} {1}".format(e.code, e.reason if hasattr(e, 'reason') else ''))
        elif hasattr(e, 'reason'):
            log("网络错误: " + str(e.reason))
        elif 'timeout' in error_msg.lower():
            log("请求超时（" + str(timeout) + "秒）")
        else:
            log("错误: " + error_msg)
        sys.exit(1)


def json_to_m3u(data, output_file='channels.m3u'):
    """将JSON数据转换为M3U格式并写入文件"""
    if not isinstance(data, list):
        log("错误: JSON数据应为列表格式")
        sys.exit(1)

    log("共获取 " + str(len(data)) + " 个频道")

    data = sorted(data, key=get_sort_key)

    lines = []
    lines.append('#EXTM3U url-tvg="' + EPG_URL + '"')

    converted_count = 0
    skipped_count = 0

    for item in data:
        if item.get('usable') == 0:
            skipped_count += 1
            continue

        channel_name = item.get('channelName', 'Unknown')
        logo = item.get('logo', '')
        channel_icon = item.get('channelIcon', '')
        tvg_id = item.get('uuid', '') or item.get('urlid', '')
        chno = item.get('no', '')
        play_url = item.get('livePlayUrl', '')

        tvg_logo = ''
        if is_valid_url(logo):
            tvg_logo = logo
        elif is_valid_url(channel_icon):
            tvg_logo = channel_icon

        extinf_parts = ['#EXTINF:-1']

        if tvg_id:
            extinf_parts.append('tvg-id="' + str(tvg_id) + '"')

        extinf_parts.append('tvg-name="' + str(channel_name) + '"')

        if tvg_logo:
            extinf_parts.append('tvg-logo="' + str(tvg_logo) + '"')

        if chno:
            extinf_parts.append('tvg-chno="' + str(chno) + '"')

        extinf_line = ' '.join(extinf_parts) + ',' + str(channel_name)
        lines.append(extinf_line)
        lines.append(play_url)
        converted_count += 1

    try:
        content = os.linesep.join(lines) + os.linesep
        with open(output_file, 'wb') as f:
            f.write(content.encode('utf-8'))
        log("转换成功！已生成文件: " + output_file)
        log("有效频道: " + str(converted_count) + " 个")
        if skipped_count > 0:
            log("跳过不可用: " + str(skipped_count) + " 个")
        log("EPG: " + EPG_URL)
    except IOError as e:
        log("写入文件失败: " + str(e))
        sys.exit(1)


def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'channels.m3u'
    data = fetch_json(CHANNELS_URL)
    json_to_m3u(data, output_file)


if __name__ == '__main__':
    main()
