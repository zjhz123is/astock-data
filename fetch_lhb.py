#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⑥ 龙虎榜抓取脚本 v4
数据源: Tushare top_list + top_inst
游资匹配: V3 标准化核心地点匹配（已验证 93% 命中率）
缓存: I:\lhb_cache\{trade_date}\n"""
import os, sys, json, time, re
from datetime import datetime

CACHE_DIR = r'I:\lhb_cache'
TOKEN = '***'
YOUZI_DB = r'I:\主线跟踪\游资参考资料\youzi_db.json'

stderr = sys.stderr
def log(s):
    print('[lhb] %s %s' % (datetime.now().strftime('%H:%M:%S'), s), file=stderr)

# ── 券商前缀 & 后缀（用于标准化营业部全称 → 核心地点）──
BROKER_PREFIXES = sorted([
    '国泰海通证券股份有限公司', '中国中金财富证券有限公司', '中国银河证券股份有限公司',
    '中信证券(山东)有限责任公司', '中信证券华南股份有限公司', '中信建投证券股份有限公司',
    '华泰证券股份有限公司', '中信证券股份有限公司', '东方财富证券股份有限公司',
    '申万宏源西部证券有限公司', '国联民生证券股份有限公司', '光大证券股份有限公司',
    '招商证券股份有限公司', '平安证券股份有限公司', '华福证券有限责任公司',
    '浙商证券股份有限公司', '中泰证券股份有限公司', '国金证券股份有限公司',
    '兴业证券股份有限公司', '方正证券股份有限公司', '国盛证券有限责任公司',
    '财通证券股份有限公司', '长城证券股份有限公司', '国信证券股份有限公司',
    '东北证券股份有限公司', '华宝证券股份有限公司', '广发证券股份有限公司',
    '华西证券股份有限公司', '申万宏源证券有限公司', '华创证券有限责任公司',
    '国元证券股份有限公司', '东莞证券股份有限公司', '华林证券股份有限公司',
    '华安证券股份有限公司', '中航证券有限公司', '天风证券股份有限公司',
    '财达证券股份有限公司', '联储证券股份有限公司', '南京证券股份有限公司',
    '万联证券股份有限公司', '海通证券股份有限公司', '东方证券股份有限公司',
    '东海证券股份有限公司', '国投证券股份有限公司', '国新证券股份有限公司',
    '国海证券股份有限公司', '湘财证券股份有限公司', '开源证券股份有限公司',
    '西南证券股份有限公司', '世纪证券有限责任公司', '民生证券股份有限公司',
    '华源证券股份有限公司', '甬兴证券有限公司', '中金财富证券有限公司',
    '爱建证券有限责任公司', '银泰证券有限责任公司', '中山证券有限责任公司',
    '瑞银证券有限责任公司', '摩根大通证券(中国)有限公司', '高盛(中国)证券有限责任公司',
    '粤开证券股份有限公司', '申港证券股份有限公司', '万和证券股份有限公司',
    '东亚前海证券有限责任公司', '金融街证券股份有限公司', '太平洋证券股份有限公司',
    '山西证券股份有限公司', '川财证券有限责任公司', '麦高证券有限责任公司',
    '信达证券股份有限公司', '中原证券股份有限公司', '华金证券股份有限公司',
    '华鑫证券有限责任公司', '上海证券有限责任公司', '中国国际金融股份有限公司',
], key=len, reverse=True)

SUFFIXES = sorted(['证券营业部', '营业部', '证券分公司', '分公司', '老营业部'], key=len, reverse=True)

def normalize_seat(name):
    """剥离券商前缀+后缀，返回核心地点名"""
    n = name.strip()
    for p in BROKER_PREFIXES:
        if n.startswith(p):
            n = n[len(p):].strip()
            break
    for s in SUFFIXES:
        if n.endswith(s):
            n = n[:-len(s)].strip()
            break
    return n

def extract_keywords_from_youzi_seats(seat_text):
    """从游资席位列提取关键词"""
    parts = re.split(r'[、，,。.；;\n\s()（）]+', seat_text)
    keywords = []
    for part in parts:
        part = part.strip()
        if not part or len(part) < 2:
            continue
        core = normalize_seat(part)
        if core and len(core) >= 2:
            keywords.append(core)
        keywords.append(part)
    return list(set(keywords))

def build_seat_matchers(youzi_db):
    """预计算每个游资的关键词"""
    matchers = []
    for yz in youzi_db:
        seat_text = yz.get('席位', '')
        keywords = extract_keywords_from_youzi_seats(seat_text)
        if keywords:
            matchers.append({
                'name': yz['游资名称'].strip(),
                'style': yz.get('手法特点', '')[:40],
                'keywords': keywords,
            })
    return matchers

def match_seat(full_seat_name, matchers):
    """匹配一个营业部全称 → 返回命中的游资列表"""
    full_core = normalize_seat(full_seat_name)
    if not full_core:
        return []
    matches = []
    for m in matchers:
        for kw in m['keywords']:
            if kw in full_seat_name or full_core in kw:
                matches.append({
                    'youzi_name': m['name'],
                    'style': m['style'],
                    'keyword': kw,
                })
                break
    return matches

def fetch_lhb_day(date_str):
    import tushare as ts
    pro = ts.pro_api(TOKEN)
    youzi_db = json.load(open(YOUZI_DB, 'r', encoding='utf-8'))
    matchers = build_seat_matchers(youzi_db)

    log('Matchers built: %d youzi, %s seat keywords' % (
        len(matchers), sum(len(m['keywords']) for m in matchers)))

    result = {
        'trade_date': date_str,
        'top_list': [],
        'top_inst': [],
        'youzi_active': {},
        'youzi_matches_detail': [],
    }

    # 1. top_list
    df_top = pro.top_list(trade_date=date_str)
    if df_top is not None and len(df_top) > 0:
        result['top_list'] = df_top.to_dict('records')

    # 2. top_inst
    df_inst = pro.top_inst(trade_date=date_str)
    if df_inst is not None and len(df_inst) > 0:
        result['top_inst'] = df_inst.to_dict('records')

        for inst in result['top_inst']:
            exalter = inst.get('exalter', '')
            if not exalter:
                continue
            matched = match_seat(exalter, matchers)
            if matched:
                detail = {
                    'ts_code': inst.get('ts_code', ''),
                    'name': inst.get('name', ''),
                    'exalter': exalter,
                    'buy': float(inst.get('buy', 0) or 0),
                    'sell': float(inst.get('sell', 0) or 0),
                    'net_buy': float(inst.get('net_buy', 0) or 0),
                    'side': inst.get('side', ''),
                    'rank': int(inst.get('rank', 0) or 0),
                    'youzi_matches': matched,
                }
                result['youzi_matches_detail'].append(detail)

                for mt in matched:
                    yz_name = mt['youzi_name']
                    if yz_name not in result['youzi_active']:
                        result['youzi_active'][yz_name] = []
                    result['youzi_active'][yz_name].append(detail)

    return result

def save_lhb_day(data):
    day_dir = os.path.join(CACHE_DIR, data['trade_date'])
    os.makedirs(day_dir, exist_ok=True)

    fp = os.path.join(day_dir, 'full.json')
    json.dump(data, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, default=str)

    # youzi summary
    summary = {}
    for yz_name, details in data['youzi_active'].items():
        total_buy = sum(d['buy'] for d in details)
        total_sell = sum(d['sell'] for d in details)
        total_net = sum(d['net_buy'] for d in details)
        stocks = list(set(d['name'] for d in details))
        summary[yz_name] = {
            'stocks_count': len(stocks),
            'seat_count': len(details),
            'total_buy': round(total_buy, 2),
            'total_sell': round(total_sell, 2),
            'total_net': round(total_net, 2),
            'stocks': stocks,
        }

    if summary:
        sy = os.path.join(day_dir, 'youzi_summary.json')
        json.dump(summary, open(sy, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    # Aggregate all-day summary
    sy_all = os.path.join(CACHE_DIR, 'youzi_summary.json')
    if os.path.exists(sy_all):
        all_summary = json.load(open(sy_all, 'r', encoding='utf-8'))
    else:
        all_summary = {}
    all_summary[data['trade_date']] = summary
    json.dump(all_summary, open(sy_all, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    return len(data['top_list']), len(data['top_inst']), len(data['youzi_active'])

def main():
    log('=== LHB v4 启动 ===')
    os.makedirs(CACHE_DIR, exist_ok=True)

    dates = sys.argv[1:] if len(sys.argv) > 1 else [datetime.now().strftime('%Y%m%d')]

    for date in dates:
        day_dir = os.path.join(CACHE_DIR, date)
        fp = os.path.join(day_dir, 'full.json')
        if os.path.exists(fp) and os.path.getsize(fp) > 100:
            log('%s: 已有缓存, 跳过' % date)
            continue

        data = fetch_lhb_day(date)
        nt, ni, ny = save_lhb_day(data)
        log('%s: top=%d inst=%d youzi_active=%d' % (date, nt, ni, ny))
        time.sleep(1.5)

    log('=== 完成 ===')

if __name__ == '__main__':
    main()
