#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日主控脚本 — 16:15 统一调用
按顺序: 北向(快) → 涨跌停(快) → 板块概念(每周) → 5分钟K线(慢)
日线由daily_fetch_v5独立处理(量大)
"""
import os, sys, subprocess, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from fetch_config import PYTHON, SCRIPT_DIR, CACHE_DIRS

stderr = sys.stderr
def log(s):
    print('[主控] %s %s' % (datetime.now().strftime('%H:%M:%S'), s), file=stderr)

def run_script(name, timeout=600):
    fp = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(fp):
        log('[跳过] %s 不存在' % name)
        return True, ''
    log('[运行] %s (超时%d秒)' % (name, timeout))
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
    log('=== 每日数据主控启动 ===')
    start_time = datetime.now()
    results = []

    # 1. 北向资金(最快,1个请求/天)
    log('--- 北向资金 ---')
    ok, out = run_script('fetch_north.py', timeout=60)
    results.append(('北向资金', ok))

    # 2. 涨跌停 (stk_limit+daily合并)
    log('--- 涨跌停 ---')
    ok, out = run_script('fetch_limit.py', timeout=120)
    results.append(('涨跌停', ok))

    # 3. 板块概念(每周一次, 仅周一或首次)
    log('--- 板块概念 ---')
    ok, out = run_script('fetch_sector.py', timeout=600)
    results.append(('板块概念', ok))

    # 4. 5分钟K线(量最大,放最后)
    log('--- 5分钟K线 ---')
    ok, out = run_script('fetch_min5.py', timeout=3600)
    results.append(('5分钟K线', ok))

    elapsed = (datetime.now() - start_time).total_seconds()
    log('=== 全部完成 === 耗时%.0f秒' % elapsed)
    for name, ok in results:
        log('  %s: %s' % (name, 'OK' if ok else 'FAIL'))

if __name__ == '__main__':
    main()