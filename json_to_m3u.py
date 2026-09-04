#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON to M3U Converter
兼容 Python 2.7 和 Python 3.x
"""

from __future__ import print_function
from __future__ import unicode_literals
import json
import sys
import os

PY3 = sys.version_info[0] == 3

if PY3:
    import urllib.request as urllib2
    from datetime import datetime, timezone
    text_type = str
    tz = timezone.utc
else:
    import urllib2
    from datetime import datetime, tzinfo, timedelta
    
    class UTC(tzinfo):
        def utcoffset(self, dt):
            return timedelta(0)
        def tzname(self, dt):
            return "UTC"
        def dst(self, dt):
            return timedelta(0)
    
    tz = UTC()
    text_type = unicode

CHANNELS_URL = u"http://gxtvepg.taipan.jda.bcs.ottcn.com:8080/ysten-lvoms-epg/epg/getChannels.shtml?deviceGroupId=4747&districtCode=450000"
EPG_URL = u"https://down.nigx.cn/epg.112114.xyz/pp.xml.gz"


def to_text(val):
    if val is None:
        return u""
    if isinstance(val, text_type):
        return val
    if isinstance(val, bytes):
        return val.decode('utf-8', 'replace')
    return text_type(val)


def log(msg):
    now = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(u"[{0}] {1}".format(now, to_text(msg)))


def is_valid_url(url):
    if not url:
        return False
    url = to_text(url)
    return url.startswith((u"http://", u"https://")) and len(url) > 8


def get_sort_key(item):
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
    log(u"正在获取数据: " + to_text(url))
    
    req = urllib2.Request(
        to_text(url),
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'http://gxtvepg.taipan.jda.bcs.ottcn.com:8080/',
        }
    )
    
    try:
        response = urllib2.urlopen(req, timeout=timeout)
        status = response.getcode() if hasattr(response, 'getcode') else response.status
        if status != 200:
            reason = getattr(response, 'reason', 'Unknown')
            raise Exception(u"HTTP {0}: {1}".format(status, reason))
        
        raw_data = response.read()
        
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
            text = raw_data.decode('utf-8', 'replace')
        
        data = json.loads(text)
        log(u"数据获取成功")
        return data
        
    except Exception as e:
        error_msg = to_text(e)
        if hasattr(e, 'code'):
            reason = getattr(e, 'reason', '')
            log(u"HTTP错误: {0} {1}".format(e.code, reason))
        elif hasattr(e, 'reason'):
            log(u"网络错误: " + to_text(e.reason))
        else:
            log(u"错误: " + error_msg)
        sys.exit(1)


def json_to_m3u(data, output_file='channels.m3u'):
    if not isinstance(data, list):
        log(u"错误: JSON数据应为列表格式")
        sys.exit(1)
    
    log(u"共获取 " + to_text(len(data)) + u" 个频道")
    
    data = sorted(data, key=get_sort_key)
    
    lines = []
    lines.append(u'#EXTM3U url-tvg="' + EPG_URL + u'"')
    
    converted_count = 0
    skipped_count = 0
    
    for item in data:
        if item.get('usable') == 0:
            skipped_count += 1
            continue
        
        channel_name = to_text(item.get('channelName', u'Unknown'))
        logo = to_text(item.get('logo', u''))
        channel_icon = to_text(item.get('channelIcon', u''))
        tvg_id = to_text(item.get('uuid', u'') or item.get('urlid', u''))
        chno = to_text(item.get('no', u''))
        play_url = to_text(item.get('livePlayUrl', u''))
        
        tvg_logo = u''
        if is_valid_url(logo):
            tvg_logo = logo
        elif is_valid_url(channel_icon):
            tvg_logo = channel_icon
        
        extinf_parts = [u'#EXTINF:-1']
        
        if tvg_id:
            extinf_parts.append(u'tvg-id="' + tvg_id + u'"')
        
        extinf_parts.append(u'tvg-name="' + channel_name + u'"')
        
        if tvg_logo:
            extinf_parts.append(u'tvg-logo="' + tvg_logo + u'"')
        
        if chno:
            extinf_parts.append(u'tvg-chno="' + chno + u'"')
        
        extinf_line = u' '.join(extinf_parts) + u',' + channel_name
        lines.append(extinf_line)
        lines.append(play_url)
        converted_count += 1
    
    try:
        content = u"\n".join(lines) + u"\n"
        with open(output_file, 'wb') as f:
            f.write(content.encode('utf-8'))
        log(u"转换成功！已生成文件: " + to_text(output_file))
        log(u"有效频道: " + to_text(converted_count) + u" 个")
        if skipped_count > 0:
            log(u"跳过不可用: " + to_text(skipped_count) + u" 个")
        log(u"EPG: " + EPG_URL)
    except IOError as e:
        log(u"写入文件失败: " + to_text(e))
        sys.exit(1)


def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'channels.m3u'
    data = fetch_json(CHANNELS_URL)
    json_to_m3u(data, output_file)


if __name__ == '__main__':
    main()
