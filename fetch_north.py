#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⑥ 北向资金（沪深港通） 抓取 v1
数据源: Tushare moneyflow_hsgt / hsgt_top10
缓存: I:\north_flow\{date}.json
策略: 从2026-01-01开始逐日补, 补完后每天增量
"""
import os, sys, json, time
from datetime import datetime, timedelta

CACHE_DIR = r'I:\north_flow'
TOKEN = '2fd2af5f3068c933bd1f05b1846c153b7d26842f8768319d257e6e1d'
START_DATE = '20260101'
SLEEP = 0.5

stderr = sys.stderr
def log(s):
    print('[north] %s %s' % (datetime.now().strftime('%H:%M:%S'), s), file=stderr)

def fetch_hsgt_daily(date):
    """沪深港通每日资金流向"""
    import tushare as ts
    ts.set_token(TOKEN)
    try:
        df = ts.pro_api().moneyflow_hsgt(start_date=date, end_date=date)
        if df is not None and len(df) > 0:
            return df.to_dict('records')
    except Exception as e:
        log('Tushare moneyflow_hsgt失败 %s: %s' % (date, e))
    return None

def fetch_hsgt_top10(date, direction='south'):
    """沪深港通十大成交股
    direction: 'south' 南向(港股通), 'north' 北向(沪深股通)
    """
    import tushare as ts
    ts.set_token(TOKEN)
    try:
        df = ts.pro_api().hsgt_top10(trade_date=date, direction=direction)
        if df is not None and len(df) > 0:
            return df.to_dict('records')
    except:
        pass
    return None

def main():
    log('=== 启动 ===')
    os.makedirs(CACHE_DIR, exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')

    # 确定起始日期
    existing = sorted([f.replace('.json','') for f in os.listdir(CACHE_DIR) if f.endswith('.json') and f[:8].isdigit()])
    if existing:
        last = existing[-1]
        start = (datetime.strptime(last, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
        log('已有缓存最后 %s, 从 %s 开始' % (last, start))
    else:
        start = START_DATE
        log('无缓存, 从 %s 开始' % start)

    dt = datetime.strptime(start, '%Y%m%d')
    ok = 0; skip = 0
    while True:
        date = dt.strftime('%Y%m%d')
        if date > today:
            break

        fp = os.path.join(CACHE_DIR, '%s.json' % date)
        if os.path.exists(fp) and os.path.getsize(fp) > 50:
            dt += timedelta(days=1)
            continue

        rec = fetch_hsgt_daily(date)
        if rec and len(rec) > 0:
            # 追加十大成交股(北向+南向)
            top_n = fetch_hsgt_top10(date, 'north')
            top_s = fetch_hsgt_top10(date, 'south')
            result = {'hsgt_daily': rec}
            if top_n: result['hsgt_top_north'] = top_n
            if top_s: result['hsgt_top_south'] = top_s
            json.dump(result, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
            ok += 1
            log('OK %s' % date)
        else:
            skip += 1
        time.sleep(SLEEP)
        dt += timedelta(days=1)

        if ok > 0 and ok % 30 == 0:
            log('进度: OK=%d, SKIP=%d, 当前=%s' % (ok, skip, date))

    log('完成: OK=%d天, SKIP=%d天' % (ok, skip))

if __name__ == '__main__':
    main()