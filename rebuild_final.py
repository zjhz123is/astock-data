# -*- coding: utf-8 -*-
"""最终版v4: 修复匹配 - docx简称 vs Tushare全称"""
import json, re, docx, os
from datetime import datetime

LOG = r'I:\主线跟踪\日志\master_log.md'
DB  = r'I:\主线跟踪\游资参考资料\youzi_db.json'
DOCX = r'C:\Users\LENOVO\.openclaw\media\inbound\游资名称---e5589718-df1a-43ed-86e2-9206f5b01023.docx'
LHB  = r'I:\lhb_cache\20260703\full.json'
OUT  = r'I:\主线跟踪\输出'

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {msg}')
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] {msg}\n')

def clean_name(raw):
    name = raw
    for suffix in ['席位匹配', '席位标准化整理', '席位标准化整理：', '席位标准化整理:',
                   '标准化席位', '标准化席位：', '标准化席位:',
                   '标准化整理', '标准化整理：', '标准化整理:',
                   '席位：', '席位:', '席位']:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    name = re.sub(r'^游资\s*', '', name).strip()
    m = re.match(r'^【(.+?)】$', name)
    if m:
        name = m.group(1).strip()
    else:
        name = re.sub(r'^【(.+)$', r'\1', name).strip()
        name = re.sub(r'^(.+?)】', r'\1', name).strip()
    name = name.strip()
    name = re.sub(r'[：:]$', '', name).strip()
    return name

def clean_title(raw):
    """Remove numbering from title"""
    return re.sub(r'^\d+[.．]?\s*', '', raw).strip()

# ── Read paragraphs ──
doc = docx.Document(DOCX)
lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
log(f'总段落数: {len(lines)}')

# ── Find sections ──
section_indices = []
for i, line in enumerate(lines):
    if re.match(r'^\d+[.．]', line) or re.match(r'^\d+游资', line):
        section_indices.append(i)
log(f'检测到 {len(section_indices)} 个游资章节')

# ── Parse each section ──
youzi_list = []
for idx, start_i in enumerate(section_indices):
    end_i = section_indices[idx+1] if idx+1 < len(section_indices) else len(lines)
    raw_title = clean_title(lines[start_i])
    name = clean_name(raw_title)
    section_lines = lines[start_i+1:end_i]
    seats, notes = [], []
    in_notes = False
    for line in section_lines:
        if line in ('注释', '注释：', '注释:', '注释：'):
            in_notes = True; continue
        skip = ['匹配注意事项', '券商名称兼容逻辑', '席位权重规则', '风险统一标注',
                '纯文本入库总清单', '标准化席位整理：', '券商更名', '文字纠错',
                '风险提示', '席位仅为概率匹配', '注意', '所有席位仅为概率',
                '标准化席位', '标准化席位：', '标准化席位:', '标准化整理', '标准化整理：',
                '席位匹配']
        if any(line.startswith(s) for s in skip):
            in_notes = False; continue
        if in_notes:
            notes.append(line)
        elif len(line) >= 4:
            seats.append(line)
    youzi_list.append({
        '游资名称': name,
        '原始标题': lines[start_i],
        '席位': seats,
        '注释': '\n'.join(notes),
    })

# ── Broker short-to-full mapping ──
BROKER_SHORT_TO_KEY = [
    ('国泰海通证券', '国泰海通'),
    ('中国中金财富证券', '中金财富'),
    ('中金财富证券', '中金财富'),
    ('中国银河证券', '中国银河'),
    ('中信建投证券', '中信建投'),
    ('中信证券', '中信证券'),
    ('东方财富证券', '东方财富'),
    ('东方证券', '东方证券'),
    ('光大证券', '光大证券'),
    ('招商证券', '招商证券'),
    ('平安证券', '平安证券'),
    ('浙商证券', '浙商证券'),
    ('中泰证券', '中泰证券'),
    ('国金证券', '国金证券'),
    ('兴业证券', '兴业证券'),
    ('方正证券', '方正证券'),
    ('国盛证券', '国盛证券'),
    ('财通证券', '财通证券'),
    ('长城证券', '长城证券'),
    ('国信证券', '国信证券'),
    ('东北证券', '东北证券'),
    ('华宝证券', '华宝证券'),
    ('广发证券', '广发证券'),
    ('华西证券', '华西证券'),
    ('申万宏源证券', '申万宏源'),
    ('华创证券', '华创证券'),
    ('国元证券', '国元证券'),
    ('东莞证券', '东莞证券'),
    ('华林证券', '华林证券'),
    ('华安证券', '华安证券'),
    ('中航证券', '中航证券'),
    ('天风证券', '天风证券'),
    ('财达证券', '财达证券'),
    ('联储证券', '联储证券'),
    ('南京证券', '南京证券'),
    ('万联证券', '万联证券'),
    ('海通证券', '海通证券'),
    ('东海证券', '东海证券'),
    ('国投证券', '国投证券'),
    ('国新证券', '国新证券'),
    ('国海证券', '国海证券'),
    ('湘财证券', '湘财证券'),
    ('开源证券', '开源证券'),
    ('西南证券', '西南证券'),
    ('世纪证券', '世纪证券'),
    ('民生证券', '民生证券'),
    ('华源证券', '华源证券'),
    ('甬兴证券', '甬兴证券'),
    ('爱建证券', '爱建证券'),
    ('银泰证券', '银泰证券'),
    ('中山证券', '中山证券'),
    ('瑞银证券', '瑞银证券'),
    ('粤开证券', '粤开证券'),
    ('申港证券', '申港证券'),
    ('万和证券', '万和证券'),
    ('东亚前海证券', '东亚前海'),
    ('太平洋证券', '太平洋证券'),
    ('山西证券', '山西证券'),
    ('川财证券', '川财证券'),
    ('麦高证券', '麦高证券'),
    ('信达证券', '信达证券'),
    ('中原证券', '中原证券'),
    ('华金证券', '华金证券'),
    ('华鑫证券', '华鑫证券'),
    ('上海证券', '上海证券'),
    ('长江证券', '长江证券'),
    ('东吴证券', '东吴证券'),
    ('东兴证券', '东兴证券'),
    ('国联证券', '国联证券'),
    ('财信证券', '财信证券'),
    ('金元证券', '金元证券'),
    ('中银国际证券', '中银国际'),
    ('恒泰证券', '恒泰证券'),
    ('第一创业证券', '第一创业'),
    ('首创证券', '首创证券'),
    ('华龙证券', '华龙证券'),
    ('大同证券', '大同证券'),
    ('英大证券', '英大证券'),
    ('德邦证券', '德邦证券'),
    ('宏信证券', '宏信证券'),
    ('国都证券', '国都证券'),
    ('九州证券', '九州证券'),
    ('新时代证券', '新时代证券'),
    ('安信证券', '安信证券'),
    ('华融证券', '华融证券'),
    ('西藏东方财富证券', '西藏东财'),
    ('国联民生证券', '国联民生'),
    ('申万宏源西部证券', '申万宏源西部'),
    ('华福证券', '华福证券'),
    ('中国中投证券', '中投证券'),
    ('国泰海通', '国泰海通'),  # catch both
] + sorted([(b, b.replace('证券','').replace('有限','').replace('责任','').replace('公司',''))
            for b in ['方正证券','华鑫证券','光大证券','兴业证券','中国银河证券',
                       '华泰证券','中信证券','东方财富证券','国金证券','平安证券',
                       '招商证券','浙商证券']
            if len(b.replace('证券','').replace('有限','').replace('责任','').replace('公司','')) >= 2],
           key=lambda x: -len(x[0]))

def extract_loc(name):
    """从营业部名称提取位置关键词（去券商前缀、去后缀）"""
    n = name.strip()
    n = re.sub(r'[（(][^）)]*[）)]', '', n).strip()
    for short, _ in sorted(BROKER_SHORT_TO_KEY, key=lambda x: -len(x[0])):
        if n.startswith(short):
            n = n[len(short):].strip()
            break
    for s in sorted(['证券营业部','营业部','证券分公司','分公司','老营业部'], key=len, reverse=True):
        if n.endswith(s):
            n = n[:-len(s)].strip()
            break
    n = re.sub(r'\s+', '', n).strip()
    return n

# ── Build seats_core ──
for yz in youzi_list:
    yz['seats_core'] = []
    seen = set()
    for seat in yz['席位']:
        loc = extract_loc(seat)
        # Store both the original seat (abbreviated) and its core location
        entry = {'full': seat, 'loc': loc}
        if loc and len(loc) >= 2 and loc not in seen:
            seen.add(loc)
            yz['seats_core'].append(entry)

# ── Save DB ──
os.makedirs(os.path.dirname(DB), exist_ok=True)
with open(DB, 'w', encoding='utf-8') as f:
    json.dump(youzi_list, f, ensure_ascii=False, indent=2)

log(f'\n=== 最终解析结果 ===')
log(f'游资数: {len(youzi_list)}')
total_s = sum(len(y['席位']) for y in youzi_list)
total_c = sum(len(y['seats_core']) for y in youzi_list)
for yz in youzi_list:
    locs = [sc['loc'] for sc in yz['seats_core'][:5]]
    log(f'  {yz["游资名称"][:24]:24s} | {len(yz["席位"]):2d}席 -> {len(yz["seats_core"]):2d}地点 | {" ".join(locs)}')
log(f'总原始席位: {total_s}, 总核心: {total_c}')

# ── Match ──
log(f'\n=== 匹配测试 (2026-07-03) ===')
lhb_data = json.load(open(LHB, 'r', encoding='utf-8'))
all_seats = sorted(set(i['exalter'] for i in lhb_data['top_inst'] if i.get('exalter')))

matched_seats = 0
matched_youzi = set()
seat_matches = {}

for seat in all_seats:
    lhb_loc = extract_loc(seat)
    if not lhb_loc or len(lhb_loc) < 2:
        continue
    found = []
    for yz in youzi_list:
        for sc in yz['seats_core']:
            # Match: check if the LHB location contains the docx location OR vice versa
            docx_loc = sc['loc']
            if len(docx_loc) >= 2:
                # Use substring match between normalized locations
                if docx_loc in lhb_loc or lhb_loc in docx_loc:
                    found.append(yz['游资名称'])
                    break
    if found:
        matched_seats += 1
        for y in set(found):
            matched_youzi.add(y)
        seat_matches[seat] = list(set(found))

log(f'总营业部: {len(all_seats)}')
log(f'匹配到: {matched_seats}/{len(all_seats)} ({matched_seats/len(all_seats)*100:.1f}%)')
log(f'覆盖游资: {len(matched_youzi)}/{len(youzi_list)}')

log('\n--- 已匹配 (按匹配数降序) ---')
for y in sorted(matched_youzi, key=lambda y: -sum(1 for ms in seat_matches.values() if y in ms)):
    cnt = sum(1 for ms in seat_matches.values() if y in ms)
    log(f'  + {y[:24]:24s} -> {cnt:3d} 营业部')

log('\n--- 未匹配 ---')
for yz in youzi_list:
    if yz['游资名称'] not in matched_youzi:
        # Check if they have candidates in today's data
        has_candidate = False
        for sc in yz['seats_core']:
            for seat in all_seats:
                lhb_loc = extract_loc(seat)
                if sc['loc'] in lhb_loc or lhb_loc in sc['loc']:
                    has_candidate = True
                    break
            if has_candidate:
                break
        if has_candidate:
            log(f'  - {yz["游资名称"][:24]:24s} (有候选但未匹配)')
        else:
            log(f'  - {yz["游资名称"][:24]:24s} (今日未上榜)')

# ── Save everything ──
match_out = {
    'date': '20260703',
    'total_broker_seats': len(all_seats),
    'matched_seats': matched_seats,
    'match_rate': f'{matched_seats/len(all_seats)*100:.1f}%',
    'matched_youzi_count': len(matched_youzi),
    'total_youzi': len(youzi_list),
    'total_raw_seats': total_s,
    'total_cores': total_c,
    'matched_youzi': sorted(matched_youzi),
    'unmatched_youzi': sorted([y['游资名称'] for y in youzi_list if y['游资名称'] not in matched_youzi]),
}
with open(os.path.join(OUT, 'match_result_20260703.json'), 'w', encoding='utf-8') as f:
    json.dump(match_out, f, ensure_ascii=False, indent=2)

log(f'\n已保存:')
log(f'  youzi_db.json -> {DB} ({len(youzi_list)}游资, {total_c}核心地点)')
log(f'  match  -> {os.path.join(OUT, "match_result_20260703.json")}')
log(f'  log    -> {LOG}')
log('=== 完成 ===')