# -*- coding: utf-8 -*-
"""数据管道共享配置"""
import os

TUSHARE_TOKEN = '2fd2af5f3068c933bd1f05b1846c153b7d26842f8768319d257e6e1d'

# Tushare API限速（分钟级200次/分钟）
API_SLEEP = 0.35  # 基础间隔
BATCH_API_SLEEP = 0.25  # 批量时稍快

# 缓存路径
CACHE_DIRS = {
    'day': r'I:\kline_cache_v4',
    'min5': r'I:\min5_cache',
    'lhb': r'I:\lhb_cache',
    'sector': r'I:\sector_cache',
    'limit': r'I:\limit_cache',
    'north': r'I:\north_flow',
}

# Python解释器路径
PYTHON = r'I:\OpenClaw\portable-env\python\python.exe'

# 脚本路径（本目录）
SCRIPT_DIR = r'C:\Users\LENOVO\.openclaw\workspace'