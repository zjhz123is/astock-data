#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
周末批量补历史数据 v2
按顺序: 北向资金 → 涨跌停 → 板块概念 → 5分钟K线
日线已追平跳过
"""
import os, sys, subprocess, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from fetch_config import PYTHON, SCRIPT_DIR

stderr = sys.stderr
def log(s):
    print('[周末补] %s %s' % (datetime.now().strftime('%H:%M:%S'), s), file=stderr)

def run_script(name, timeout=3600):
    fp = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(fp):
        log('[跳过] %s 不存在' % name)
        return True, ''
    log('[运行] %s' % name)
    try:
        r = subprocess.run([PYTHON, '-W', 'ignore', fp],
                         capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or '')[:200] + (r.stderr or '')[:200]
        if r.returncode == 0:
            log('[OK] %s' % name)
            return True, out
        else:
            log('[FAIL] %s 返回码%d' % (name, r.returncode))
            return False, out
    except subprocess.TimeoutExpired:
        log('[超时] %s %d秒' % (name, timeout))
        return False, 'timeout'
    except Exception as e:
        log('[错误] %s: %s' % (name, e))
        return False, str(e)

def main():
    log('=== 批量补历史启动 ===')
    start_time = datetime.now()
    log('时间: %s' % start_time.strftime('%Y-%m-%d %H:%M'))

    tasks = [
        ('北向资金(2026/01→now)',  'fetch_north.py',  600),
        ('涨跌停(2026/06→now)',    'fetch_limit.py',  600),
        ('板块概念/行业分类',       'fetch_sector.py', 900),
        ('5分钟K线(60天LT池+主线)','fetch_min5.py',   7200),
    ]

    results = []
    for name, script, timeout in tasks:
        log('--- %s ---' % name)
        ok, out = run_script(script, timeout)
        results.append((name, ok))
        log('  → %s' % ('OK' if ok else 'FAIL'))
        time.sleep(2)

    elapsed = (datetime.now() - start_time).total_seconds()
    log('=== 全部完成 ===')
    log('耗时: %d分%d秒' % (elapsed//60, elapsed%60))
    for name, ok in results:
        log('  %s: %s' % (name, 'OK' if ok else 'FAIL'))

if __name__ == '__main__':
    main()