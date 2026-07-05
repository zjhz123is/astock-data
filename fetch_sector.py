#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
④ 板块概念对照表 抓取 v2 - 改用index_classify+ths_member
数据源: Tushare index_classify(申万行业) + ths_member(概念成分)
缓存: I:\sector_cache\
"""
import os, sys, json, time
import tushare as ts
from datetime import datetime

CACHE_DIR = r'I:\sector_cache'
TOKEN = '2fd2af5f3068c933bd1f05b1846c153b7d26842f8768319d257e6e1d'
SLEEP = 0.35

stderr = sys.stderr
def log(s):
    print('[sector] %s %s' % (datetime.now().strftime('%H:%M:%S'), s), file=stderr)

ts.set_token(TOKEN)
pro = ts.pro_api()

def safe_dict(df):
    if df is not None and len(df) > 0:
        return df.to_dict('records')
    return None

def main():
    log('=== 启动 ===')
    os.makedirs(CACHE_DIR, exist_ok=True)

    # 1. 申万行业分类
    fp_ind = os.path.join(CACHE_DIR, 'sw_industry.json')
    if not os.path.exists(fp_ind):
        log('拉取申万行业分类...')
        try:
            df = pro.query(api_name='index_classify', exchange='SW')
            rec = safe_dict(df)
            if rec:
                json.dump(rec, open(fp_ind, 'w', encoding='utf-8'), ensure_ascii=False)
                log('申万行业分类 %d 条' % len(rec))
        except Exception as e:
            log('申万行业分类失败: %s' % e)
    else:
        log('申万行业分类已缓存')

    # 2. 概念板块成分股（ths_member）
    # 需要先知道概念code... 只能通过stock_basic查
    # 换思路: 直接拉所有stock_basic, 然后用ths_member查每个的成分关系
    fp_members = os.path.join(CACHE_DIR, 'ths_members.json')
    if not os.path.exists(fp_members):
        log('拉取概念成分股(ths_member)...')
        try:
            df = pro.query(api_name='ths_member')
            rec = safe_dict(df)
            if rec:
                json.dump(rec, open(fp_members, 'w', encoding='utf-8'), ensure_ascii=False)
                log('概念成分 %d 条' % len(rec))
        except Exception as e:
            log('ths_member失败: %s' % e)
    else:
        log('ths_member已缓存 %d 条' % len(json.load(open(fp_members, 'r', encoding='utf-8'))))

    # 3. 每日行业指数行情(申万一级)
    fp_daily = os.path.join(CACHE_DIR, 'index_daily_latest.json')
    if not os.path.exists(fp_daily):
        log('拉取申万一级指数行情...')
        try:
            # 申万一级行业指数 code: 801010.SI ~ 801980.SI
            today = datetime.now().strftime('%Y%m%d')
            import pandas as pd
            dfs = []
            for sw_code in ['801010.SI','801020.SI','801030.SI','801040.SI','801050.SI',
                           '801080.SI','801110.SI','801120.SI','801130.SI','801140.SI',
                           '801150.SI','801160.SI','801170.SI','801180.SI','801200.SI',
                           '801210.SI','801230.SI','801710.SI','801720.SI','801730.SI',
                           '801740.SI','801750.SI','801760.SI','801770.SI','801780.SI',
                           '801790.SI','801880.SI','801890.SI','801200.SI','801210.SI']:
                try:
                    df = pro.query(api_name='index_daily', ts_code=sw_code, start_date='20260601', end_date=today)
                    if df is not None and len(df) > 0:
                        dfs.append(df)
                except:
                    pass
                time.sleep(SLEEP)
            if dfs:
                combined = pd.concat(dfs)
                json.dump(combined.to_dict('records'), open(fp_daily, 'w', encoding='utf-8'), ensure_ascii=False)
                log('指数行情 %d 条' % len(combined))
        except Exception as e:
            log('指数行情失败: %s' % e)

    log('完成')

if __name__ == '__main__':
    main()