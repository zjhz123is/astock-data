#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, time
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta

CACHE_DIR = r"I:\limit_cache"
TOKEN = "2fd2af5f3068c933bd1f05b1846c153b7d26842f8768319d257e6e1d"
SLEEP = 0.35

stderr = sys.stderr
def log(s):
    print("[limit] %s %s" % (datetime.now().strftime("%H:%M:%S"), s), file=stderr)

ts.set_token(TOKEN)
pro = ts.pro_api()

def fetch_limit(date):
    try:
        df = pro.query(api_name="stk_limit", trade_date=date)
        if df is not None and len(df) > 0:
            return df
    except:
        pass
    return None

def fetch_daily(date):
    try:
        df = pro.query(api_name="daily", trade_date=date)
        if df is not None and len(df) > 0:
            return df
    except:
        pass
    return None

def main():
    log("=== 启动 ===")
    os.makedirs(CACHE_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    existing = sorted([f.replace(".json","") for f in os.listdir(CACHE_DIR) if f.endswith(".json") and f[:8].isdigit()])
    if existing:
        last = existing[-1]
        start = (datetime.strptime(last, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        log("已有缓存最后 %s, 从 %s 开始" % (last, start))
    else:
        start = "20260601"
        log("无缓存, 从 %s 开始" % start)
    dt = datetime.strptime(start, "%Y%m%d")
    ok = 0; skip = 0
    while True:
        date = dt.strftime("%Y%m%d")
        if date > today: break
        fp = os.path.join(CACHE_DIR, "%s.json" % date)
        if os.path.exists(fp) and os.path.getsize(fp) > 50:
            dt += timedelta(days=1)
            continue
        limit_df = fetch_limit(date)
        if limit_df is None or len(limit_df) == 0:
            skip += 1; dt += timedelta(days=1); continue
        daily_df = fetch_daily(date)
        limit_df["close"] = 0.0
        if daily_df is not None and len(daily_df) > 0:
            dm = daily_df.set_index("ts_code")["close"].to_dict()
            limit_df["close"] = limit_df["ts_code"].map(dm).fillna(0.0)
        recs = limit_df.to_dict("records")
        for r in recs:
            c = r.get("close",0) or 0
            u = r.get("up_limit",0) or 0
            d = r.get("down_limit",0) or 0
            r["zt"] = 1 if (c>0 and u>0 and abs(c-u)/u<0.003) else 0
            r["dt"] = 1 if (c>0 and d>0 and abs(c-d)/d<0.003) else 0
        if recs:
            json.dump(recs, open(fp,"w",encoding="utf-8"), ensure_ascii=False)
            ok += 1
            zc = sum(1 for r in recs if r.get("zt"))
            dc = sum(1 for r in recs if r.get("dt"))
            log("OK %s: %d只(涨停%d/跌停%d)" % (date, len(recs), zc, dc))
        else:
            skip += 1
        time.sleep(SLEEP)
        dt += timedelta(days=1)
        if ok>0 and ok%20==0:
            log("进度: OK=%d SKIP=%d" % (ok, skip))
    log("完成: OK=%d天 SKIP=%d天" % (ok, skip))

if __name__ == "__main__":
    main()