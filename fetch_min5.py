#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
② 5分钟K线抓取 v3 - 腾讯行情m5接口
不限速，一次拉482根(≈10个交易日)
缓存: I:\min5_cache\{ts_code}\{date}.json
"""
import os, sys, json, urllib.request
from datetime import datetime, timedelta

CACHE_DIR = r'I:\min5_cache'
TOKEN = '2fd2af…6e1d'
DAYS_BACK = 10

stderr = sys.stderr
def log(s):
    print('[min5] %s %s' % (datetime.now().strftime('%H:%M:%S'), s), file=stderr)

STOCKS = [
    '000001.SZ','300054.SZ', '300429.SZ', '300905.SZ', '301036.SZ',
    '001389.SZ', '301392.SZ', '301608.SZ', '301622.SZ',
    '603005.SH', '002371.SZ', '600584.SH',
    '600171.SH', '688012.SH', '002409.SZ',
    '688160.SH', '002896.SZ', '300124.SZ',
    '603662.SH', '300660.SZ',
    '600519.SH', '000858.SZ', '601127.SH',
    '300750.SZ', '000333.SZ', '002594.SZ',
    '688981.SH', '601012.SH', '600036.SH',
    '300059.SZ', '002415.SZ', '600276.SH',
]

def tx_code(code):
    """Convert ts_code to Tencent format: sh/sz + 6-digit code"""
    if code.endswith('.SH'):
        return 'sh' + code[:6]
    return 'sz' + code[:6]

def fetch_min5_by_code(code_str):
    """Fetch 5min kline from Tencent, returns {date: [bars...]}"""
    tx = tx_code(code_str)
    url = 'http://ifzq.gtimg.cn/appstock/app/kline/mkline?param=%s,m5,,,%d' % (tx, DAYS_BACK)
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    res = urllib.request.urlopen(req, timeout=10).read().decode('utf-8','ignore')
    data = json.loads(res)
    if data.get('code') != 0:
        return None
    for k in data.get('data', {}):
        v = data['data'][k]
        if isinstance(v, dict) and 'm5' in v:
            m5 = v['m5']
            # Group by date
            by_date = {}
            for item in m5:
                dt = item[0]  # '202607031500'
                date = dt[:8]
                if date not in by_date:
                    by_date[date] = []
                by_date[date].append({
                    'time': dt,
                    'open': float(item[1]) if item[1] else 0,
                    'close': float(item[2]) if item[2] else 0,
                    'high': float(item[3]) if item[3] else 0,
                    'low': float(item[4]) if item[4] else 0,
                    'volume': float(item[5]) if item[5] else 0,
                    'amount': float(item[7]) if len(item) > 7 and item[7] else 0,
                })
            return by_date
    return None

def main():
    log('=== 启动 ===')
    os.makedirs(CACHE_DIR, exist_ok=True)
    ok = 0; skip = 0

    for code in STOCKS:
        code_dir = os.path.join(CACHE_DIR, code.replace('.', '_'))
        os.makedirs(code_dir, exist_ok=True)

        by_date = fetch_min5_by_code(code)
        if not by_date:
            skip += 1
            log('%s: 无数据' % code)
            continue

        saved = 0
        for date, bars in sorted(by_date.items()):
            fp = os.path.join(code_dir, '%s.json' % date)
            if os.path.exists(fp) and os.path.getsize(fp) > 50:
                continue
            json.dump(bars, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
            saved += 1

        ok += 1
        log('%s: %d天/%d条K线 (新增%d天)' % (code, len(by_date), sum(len(v) for v in by_date.values()), saved))

    log('完成: OK=%d SKIP=%d' % (ok, skip))

if __name__ == '__main__':
    main()