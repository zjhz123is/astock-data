#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股战法选股 + 资金流分析 — 综合选股引擎 v2 (多数据源版)
=========================================================
数据源：新浪(列表/实时) + QQ(实时) + 东方财富历史K线 + 东方财富资金流向
战法：B点买点 + 三钻突破 + 三底狙击 + 龙头战法 + 资金流入分析

用法：
  python stock_screener.py quick        # 快速选股（前300只大盘股）
  python stock_screener.py sector <板块名> # 按板块选股
  python stock_screener.py focus 600519,000858  # 指定股票
  python stock_screener.py full        # 全市场扫描（耗时较长）
"""

import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import urllib3
import warnings
import time
import json
import os
import sys
import re
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings()
warnings.filterwarnings("ignore")

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "PingFang SC"]
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_DIR = Path(__file__).parent / "astock_output"
OUTPUT_DIR.mkdir(exist_ok=True)

NOW = datetime.now()

# ═══════════════════════════════════
# 通用HTTP
# ═══════════════════════════════════

_EM_SESSION = None

def _em_session():
    global _EM_SESSION
    if _EM_SESSION is None:
        s = requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://quote.eastmoney.com/"})
        s.verify = False
        retries = Retry(total=2, backoff_factor=1, status_forcelist=[500,502,503])
        s.mount("https://", HTTPAdapter(max_retries=retries))
        for _ in range(3):
            try:
                s.get("https://push2his.eastmoney.com/ping.html", timeout=5)
                break
            except:
                time.sleep(1)
        _EM_SESSION = s
    return _EM_SESSION

def _sina_session():
    s = requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0"})
    s.verify = False
    return s

def _qq_session():
    s = requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0"})
    return s

def _safe_json(text):
    """Parse non-standard JSON (Sina returns JS-like format)"""
    text = text.strip()
    if text.startswith("["):
        return json.loads(text)
    # Some responses have leading variable name
    idx = text.find("[")
    if idx >= 0:
        return json.loads(text[idx:])
    return None


# ═══════════════════════════════════
# 一、获取股票列表（新浪）
# ═══════════════════════════════════

def get_stock_list_sina(max_count=5000):
    """从新浪获取A股全部股票列表"""
    print("[股票列表] 新浪...")
    s = _sina_session()
    try:
        r = s.get(
            "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            "Market_Center.getHQNodeData",
            params={"page":"1","num":str(max_count),"sort":"symbol","asc":"1",
                    "node":"hs_a","symbol":"","_s_r_a":"init"},
            timeout=20
        )
        data = _safe_json(r.text)
        if not data:
            print("  [FAIL] 解析失败")
            return pd.DataFrame()
        
        records = []
        for item in data:
            code = item.get("code","")
            name = item.get("name","").strip()
            if not code or not name:
                continue
            # Filter ST/退市
            if "ST" in name or "退" in name:
                continue
            records.append({
                "代码": code,
                "名称": name,
                "最新价": float(item.get("trade",0) or 0),
                "涨跌幅": float(item.get("changepercent",0) or 0) / 100 * 100,
                "昨收": float(item.get("settlement",0) or 0),
                "今开": float(item.get("open",0) or 0),
                "最高": float(item.get("high",0) or 0),
                "最低": float(item.get("low",0) or 0),
                "成交量": int(item.get("volume",0) or 0),
                "成交额": float(item.get("amount",0) or 0),
                "换手率": float(item.get("turnoverratio",0) or 0),
                "市盈率": float(item.get("per",0) or 0),
                "市净率": float(item.get("pb",0) or 0),
            })
        df = pd.DataFrame(records)
        print(f"  [OK] {len(df)} 只")
        return df
    except Exception as e:
        print(f"  [FAIL] {e}")
        return pd.DataFrame()


def get_qq_realtime(codes):
    """批量获取QQ实时行情"""
    if isinstance(codes, list):
        codes = ",".join(codes)
    s = _qq_session()
    prefix_map = {}
    parts = codes.split(",")
    qq_parts = []
    for c in parts:
        c = c.strip().replace("sh","").replace("sz","").replace("SH","").replace("SZ","")
        if c.startswith("6"):
            qq_parts.append(f"sh{c}")
        else:
            qq_parts.append(f"sz{c}")
    
    results = {}
    batch_size = 50
    for i in range(0, len(qq_parts), batch_size):
        batch = qq_parts[i:i+batch_size]
        try:
            r = s.get(f"http://qt.gtimg.cn/q={'/'.join(batch)}", timeout=10)
            for line in r.text.strip().split("\n"):
                if "=" not in line:
                    continue
                parts_line = line.split("~")
                if len(parts_line) < 10:
                    continue
                code = parts_line[2]
                results[code] = {
                    "名称": parts_line[1],
                    "最新价": float(parts_line[3]) if parts_line[3] else 0,
                    "涨跌幅": float(parts_line[32]) if len(parts_line)>32 and parts_line[32] else 0,
                    "涨跌额": float(parts_line[31]) if len(parts_line)>31 and parts_line[31] else 0,
                    "今开": float(parts_line[5]) if parts_line[5] else 0,
                    "昨收": float(parts_line[4]) if parts_line[4] else 0,
                    "最高": float(parts_line[33]) if len(parts_line)>33 and parts_line[33] else 0,
                    "最低": float(parts_line[34]) if len(parts_line)>34 and parts_line[34] else 0,
                    "成交量": int(parts_line[6]) if parts_line[6] else 0,
                    "成交额": float(parts_line[37]) if len(parts_line)>37 and parts_line[37] else 0,
                    "换手率": float(parts_line[38]) if len(parts_line)>38 and parts_line[38] else 0,
                    "市盈率": float(parts_line[39]) if len(parts_line)>39 and parts_line[39] else 0,
                    "总市值": float(parts_line[45]) if len(parts_line)>45 and parts_line[45] else 0,
                    "流通市值": float(parts_line[44]) if len(parts_line)>44 and parts_line[44] else 0,
                }
        except Exception as e:
            print(f"  [WARN] QQ batch error: {e}")
            continue
    return results


# ═══════════════════════════════════
# 二、获取K线数据（东方财富历史）
# ═══════════════════════════════════

def get_kline(symbol, days=120):
    """获取日K线（前复权）"""
    secid = f"1.{symbol}" if symbol.startswith("6") else f"0.{symbol}"
    s = _em_session()
    try:
        r = s.get("https://push2his.eastmoney.com/api/qt/stock/kline/get", {
            "secid": secid,
            "klt": "101", "fqt": "1", "lmt": str(days),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }, timeout=15)
        data = r.json()
        klines = data.get("data", {}).get("klines", [])
        if not klines:
            return None
    except:
        return None
    
    records = []
    for k in klines:
        p = k.split(",")
        records.append({
            "日期": p[0], "开盘": float(p[1]), "收盘": float(p[2]),
            "最高": float(p[3]), "最低": float(p[4]),
            "成交量": int(p[5]), "成交额": float(p[6]),
            "振幅": float(p[7]), "涨跌幅": float(p[8]),
            "涨跌额": float(p[9]), "换手率": float(p[10]),
        })
    df = pd.DataFrame(records)
    df["日期"] = pd.to_datetime(df["日期"])
    return df.sort_values("日期").reset_index(drop=True)


# ═══════════════════════════════════
# 三、技术指标计算
# ═══════════════════════════════════

def calc_indicators(df):
    """一次性计算所有技术指标"""
    df = df.copy()
    close = df["收盘"]
    high = df["最高"]
    low = df["最低"]
    vol = df["成交量"]
    
    for w in [5,10,20,30,60]:
        df[f"MA{w}"] = close.rolling(w).mean()
    
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df["DIF"] = ema12 - ema26
    df["DEA"] = df["DIF"].ewm(span=9).mean()
    df["MACD"] = 2 * (df["DIF"] - df["DEA"])
    
    ll = low.rolling(9).min()
    hh = high.rolling(9).max()
    rsv = (close - ll) / (hh - ll) * 100
    df["K"] = rsv.ewm(com=2).mean()
    df["D"] = df["K"].ewm(com=2).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]
    
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    for p in [6, 12, 24]:
        ag = gain.rolling(p).mean()
        al = loss.rolling(p).mean()
        rs = ag / al.replace(0, np.nan)
        df[f"RSI{p}"] = 100 - 100 / (1 + rs)
    
    df["VOL_MA5"] = vol.rolling(5).mean()
    df["VOL_MA20"] = vol.rolling(20).mean()
    df["涨跌幅"] = close.pct_change() * 100
    
    return df


# ═══════════════════════════════════
# 四、资金流向（东方财富历史）
# ═══════════════════════════════════

def get_money_flow_individual(stock, days=30):
    """个股资金流向历史"""
    secid = f"1.{stock}" if stock.startswith("6") else f"0.{stock}"
    s = _em_session()
    try:
        r = s.get("https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get", {
            "secid": secid, "lmt": str(days),
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        }, timeout=15)
        klines = r.json().get("data", {}).get("klines", [])
        if not klines:
            return None
    except:
        return None
    
    records = []
    for k in klines:
        p = k.split(",")
        records.append({
            "日期": p[0],
            "主力净流入": float(p[1]), "小单净流入": float(p[2]),
            "中单净流入": float(p[3]), "大单净流入": float(p[4]),
            "超大单净流入": float(p[5]),
            "主力净额": float(p[6]),
            "主力净占比": float(p[11]),
        })
    df = pd.DataFrame(records)
    df["日期"] = pd.to_datetime(df["日期"])
    return df.sort_values("日期").reset_index(drop=True)


# ═══════════════════════════════════
# 五、战法选股引擎
# ═══════════════════════════════════

class StrategyEngine:
    """战法选股引擎"""

    @staticmethod
    def strategy_B点(df):
        """
        B点买点：多因子买点共振
        - MACD金叉(DIF上穿DEA)
        - KDJ金叉(K上穿D 或 J<20拐头)
        - 站上MA20
        - 放量(>MA5均量1.5倍)
        - RSI6<50 非超买
        - 底部企稳(近5日不创新低)
        """
        if len(df) < 30:
            return None
        df = calc_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        signals = []
        score = 0
        
        if prev["DIF"] < prev["DEA"] and last["DIF"] >= last["DEA"]:
            signals.append("MACD金叉"); score += 20
        elif abs(last["DIF"] - last["DEA"]) < 0.15 and last["DIF"] > last["DEA"]:
            signals.append("MACD趋近金叉"); score += 10
        
        if prev["K"] < prev["D"] and last["K"] >= last["D"]:
            signals.append("KDJ金叉"); score += 15
        if last["J"] < 20 and last["J"] > prev["J"]:
            signals.append("KDJ超卖拐头"); score += 15
        elif last["J"] < 20:
            signals.append("KDJ超卖区"); score += 5
        
        if not np.isnan(last["MA20"]) and last["收盘"] > last["MA20"]:
            signals.append("站上MA20"); score += 15
        if len(df) >= 3:
            d3 = df.iloc[-3]
            if d3["MA5"] < d3["MA10"] and prev["MA5"] >= prev["MA10"]:
                signals.append("MA5金叉MA10"); score += 10
        
        vol_ratio = last["成交量"] / df["VOL_MA5"].iloc[-1] if df["VOL_MA5"].iloc[-1] > 0 else 1
        if vol_ratio > 2:
            signals.append("放倍量"); score += 15
        elif vol_ratio > 1.5:
            signals.append("放量"); score += 10
        
        if last["RSI6"] < 50:
            signals.append(f"RSI6安全{last['RSI6']:.0f}"); score += 10
        elif last["RSI6"] < 70:
            signals.append(f"RSI6温和{last['RSI6']:.0f}"); score += 5
        
        recent_min = df.tail(5)["最低"].min()
        prev_min = df.tail(10).head(5)["最低"].min()
        if recent_min >= prev_min:
            signals.append("底部企稳"); score += 10
        
        if -5 < last["涨跌幅"] < 7:
            score += 5
        
        return {
            "score": score,
            "level": "强B点" if score >= 60 else ("弱B点" if score >= 40 else "待观察"),
            "signals": "|".join(signals),
            "vol_ratio": round(vol_ratio, 2),
            "rsi6": round(last["RSI6"], 1) if not np.isnan(last["RSI6"]) else 0,
            "j_value": round(last["J"], 1),
        }

    @staticmethod
    def strategy_三钻(df):
        """
        三钻突破：连续收阳+量能递增+突破均线+MACD多头
        """
        if len(df) < 30:
            return None
        df = calc_indicators(df)
        last3 = df.tail(3)
        last = df.iloc[-1]
        signals = []
        score = 0
        
        yang_cnt = sum(1 for _, r in last3.iterrows() if r["收盘"] > r["开盘"])
        if yang_cnt >= 2:
            signals.append(f"{yang_cnt}日收阳"); score += 15
        if yang_cnt == 3:
            signals.append("三连阳"); score += 10
        
        vol_trend = all(last3.iloc[i]["成交量"] >= last3.iloc[i-1]["成交量"] for i in range(1,len(last3)))
        if vol_trend:
            signals.append("量能递增"); score += 15
        
        if not np.isnan(last["MA20"]) and last["收盘"] > last["MA20"]:
            signals.append(f">MA20({last['MA20']:.0f})"); score += 15
        if len(df) >= 20:
            high_20d = df.tail(20).head(-3)["最高"].max()
            if last["收盘"] > high_20d:
                signals.append("突破20日高"); score += 15
        
        if last["DIF"] > last["DEA"]:
            signals.append("MACD多头"); score += 10
            if last["DIF"] > 0:
                signals.append("DIF>0"); score += 10
        
        if 40 < last["RSI6"] < 80:
            signals.append(f"RSI6={last['RSI6']:.0f}"); score += 10
        if last["涨跌幅"] > 3:
            signals.append("中阳"); score += 10
        elif last["涨跌幅"] > 0:
            score += 5
        
        return {
            "score": score,
            "level": "三钻确认" if score >= 60 else ("三钻初现" if score >= 40 else "待确认"),
            "signals": "|".join(signals),
            "yang_count": yang_cnt,
            "vol_trend": vol_trend,
        }

    @staticmethod
    def strategy_三底狙击(df):
        """
        三底狙击+主力建仓：底部反转信号
        """
        if len(df) < 60:
            return None
        df = calc_indicators(df)
        last = df.iloc[-1]
        signals = []
        score = 0
        
        high_60d = df.tail(60)["最高"].max()
        drawdown = (last["收盘"] - high_60d) / high_60d * 100
        if drawdown < -20:
            signals.append(f"回撤{drawdown:.0f}%"); score += 15
        elif drawdown < -10:
            signals.append(f"回撤{drawdown:.0f}%"); score += 10
        
        recent = df.tail(10)
        amp = (recent["最高"].max() - recent["最低"].min()) / recent["最低"].min() * 100 if recent["最低"].min() > 0 else 100
        if amp < 8:
            signals.append(f"横盘振幅{amp:.1f}%"); score += 10
        
        vol_5d_avg = df.tail(5)["成交量"].mean()
        vol_20d_avg = df.tail(20)["成交量"].mean()
        if vol_20d_avg > 0 and vol_5d_avg < vol_20d_avg * 0.6:
            signals.append("地量"); score += 10
        if last["成交量"] > df["VOL_MA5"].iloc[-1] * 1.8:
            signals.append("放量启动"); score += 15
        
        if len(df) >= 30:
            if last["DIF"] > df["DEA"].iloc[-1] and df.tail(30)["DIF"].min() < -1:
                signals.append("MACD低位金叉"); score += 15
        
        if last["J"] < 20:
            signals.append(f"J超卖{last['J']:.0f}"); score += 10
        elif last["J"] < 30:
            signals.append(f"J低位{last['J']:.0f}"); score += 5
        
        if not np.isnan(last["MA60"]):
            ma60_dist = (last["收盘"] - last["MA60"]) / last["MA60"] * 100
            if ma60_dist < -10:
                signals.append(f"远MA60({ma60_dist:.0f}%)"); score += 10
        
        if len(df) >= 5 and last["RSI6"] > df.tail(5)["RSI6"].min():
            signals.append("RSI回升"); score += 5
        
        return {
            "score": score,
            "level": "三底狙击" if score >= 50 else ("底部观察" if score >= 30 else "否"),
            "signals": "|".join(signals),
            "drawdown": round(drawdown, 1),
        }

    @staticmethod
    def strategy_龙头战法(df):
        """
        龙头战法：涨停后回落企稳+二次启动
        模拟"5天2板"和"3天1板"逻辑
        """
        if len(df) < 20:
            return None
        df = calc_indicators(df)
        last = df.iloc[-1]
        signals = []
        score = 0
        
        # 寻找近期涨停信号（涨跌幅>9%）
        recent20 = df.tail(20)
        limit_ups = recent20[recent20["涨跌幅"] >= 9]
        
        if len(limit_ups) >= 2:
            signals.append(f"近期{len(limit_ups)}次涨停"); score += 25
            # 涨停后回调企稳
            last_limit_idx = limit_ups.index[-1]
            last_limit_pos = len(df) - 1 - last_limit_idx
            if last_limit_pos >= 2 and last_limit_pos <= 8:
                signals.append(f"涨停{last_limit_pos}日前"); score += 15
        elif len(limit_ups) >= 1:
            signals.append("近期涨停"); score += 10
            # 涨停后不深跌
            last_limit_idx = limit_ups.index[-1]
            close_since = df.loc[last_limit_idx:, "收盘"]
            max_drawdown_since = (close_since.min() - close_since.iloc[0]) / close_since.iloc[0] * 100
            if max_drawdown_since > -10:
                signals.append(f"涨停后回撤{max_drawdown_since:.1f}%"); score += 10
        
        # 站上均线
        if not np.isnan(last["MA5"]) and last["收盘"] > last["MA5"]:
            signals.append(">MA5"); score += 5
        
        # 量能回升
        if df.iloc[-1]["成交量"] > df.iloc[-3:-1]["成交量"].mean():
            signals.append("量能回升"); score += 10
        
        return {
            "score": score,
            "level": "龙头初现" if score >= 40 else "观察",
            "signals": "|".join(signals),
        }

    @staticmethod
    def money_flow_score(flow_df):
        """资金流向评分"""
        if flow_df is None or len(flow_df) < 5:
            return 0, "无资金数据"
        
        signals = []
        score = 0
        recent5 = flow_df.tail(5)
        net_main = recent5["主力净流入"].sum()
        
        if net_main > 1e7:
            signals.append(f"近5日主力净{net_main/1e8:.2f}亿"); score += 25
        elif net_main > 0:
            signals.append(f"近5日主力净{net_main/1e4:.0f}万"); score += 15
        else:
            signals.append(f"近5日主力净{-net_main/1e4:.0f}万"); score -= 10
        
        last_flow = recent5.iloc[-1]["主力净流入"]
        if last_flow > 1e6:
            signals.append(f"今日主力净{last_flow/1e4:.0f}万"); score += 15
        elif last_flow > 0:
            score += 5
        else:
            score -= 5
        
        avg_ratio = recent5["主力净占比"].mean()
        if avg_ratio > 5:
            signals.append(f"净占比{avg_ratio:.1f}%"); score += 10
        elif avg_ratio > 0:
            score += 5
        
        return score, " | ".join(signals)


# ═══════════════════════════════════
# 六、综合选股主循环
# ═══════════════════════════════════

def comprehensive_screen(stock_df, max_stocks=100):
    """综合选股"""
    
    results = []
    total = min(len(stock_df), max_stocks)
    print(f"\n[分析] 扫描{total}只...")
    
    for idx in range(total):
        row = stock_df.iloc[idx]
        code = str(row["代码"]).strip()
        name = str(row["名称"]).strip()
        
        if (idx + 1) % 10 == 0:
            print(f"  进度 {idx+1}/{total}")
        
        try:
            df = get_kline(code, days=120)
            if df is None or len(df) < 30:
                continue
            
            b = StrategyEngine.strategy_B点(df)
            d = StrategyEngine.strategy_三钻(df)
            s = StrategyEngine.strategy_三底狙击(df)
            l = StrategyEngine.strategy_龙头战法(df)
            
            flow = get_money_flow_individual(code, days=20)
            mf_score, mf_sig = StrategyEngine.money_flow_score(flow)
            
            strategies = []
            total_score = 0
            
            for name_strat, obj, thresh, label in [
                ("B点", b, 40, "B点买点"),
                ("三钻", d, 40, "三钻突破"),
                ("三底", s, 30, "三底狙击"),
                ("龙头", l, 40, "龙头战法"),
            ]:
                if obj and obj["score"] >= thresh:
                    strategies.append(f"{label}({obj['score']})")
                    total_score += obj["score"]
            
            total_score += mf_score
            
            if total_score < 30:
                continue
            
            results.append({
                "代码": code,
                "名称": name,
                "最新价": round(df.iloc[-1]["收盘"], 2),
                "涨跌幅%": round(df.iloc[-1]["涨跌幅"], 2),
                "综合评分": total_score,
                "B点": b["score"] if b else 0,
                "三钻": d["score"] if d else 0,
                "三底": s["score"] if s else 0,
                "龙头": l["score"] if l else 0,
                "资金评分": mf_score,
                "战法": " | ".join(strategies) if strategies else "资金流入",
                "信号": " | ".join([
                    (b["signals"] if b else ""),
                    (d["signals"] if d else ""),
                    (s["signals"] if s else ""),
                    (l["signals"] if l else ""),
                    mf_sig
                ])[:100],
            })
            
        except Exception as e:
            continue
    
    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.sort_values("综合评分", ascending=False).reset_index(drop=True)
    return result_df


# ═══════════════════════════════════
# 七、输出
# ═══════════════════════════════════

def export_html(results):
    """生成HTML报告"""
    now_str = NOW.strftime("%Y-%m-%d %H:%M")
    
    top3_html = ""
    for i in range(min(3, len(results))):
        r = results.iloc[i]
        medals = ["🥇", "🥈", "🥉"]
        chg_c = "#D32F2F" if r["涨跌幅%"] > 0 else "#2E7D32"
        top3_html += f"""
        <div class="top-card">
            <div class="medal">{medals[i]}</div>
            <h3>{r['名称']}<small>{r['代码']}</small></h3>
            <div class="top-info">
                <span style="color:{chg_c};font-weight:bold">{r['涨跌幅%']:+.2f}%</span>
                <span>评分: <b>{r['综合评分']}</b></span>
            </div>
        </div>"""
    
    rows = ""
    for i, (_, r) in enumerate(results.iterrows()):
        chg_c = "#D32F2F" if r["涨跌幅%"] > 0 else "#2E7D32"
        tags = ""
        for s in str(r["战法"]).split(" | "):
            tag_cls = {"B点买点":"blue","三钻突破":"gold","三底狙击":"green","龙头战法":"purple","资金流入":"red"}
            cls = "tag"
            for k,v in tag_cls.items():
                if k in s:
                    cls = f"tag tag-{v}"; break
            tags += f'<span class="{cls}">{s}</span> '
        rows += f"""<tr>
            <td>{i+1}</td>
            <td><b>{r['名称']}</b><br><small>{r['代码']}</small></td>
            <td style="font-weight:bold">{r['最新价']}</td>
            <td style="color:{chg_c}">{r['涨跌幅%']:+.2f}%</td>
            <td><b>{r['综合评分']}</b></td>
            <td>{r['B点']}</td><td>{r['三钻']}</td><td>{r['三底']}</td><td>{r['龙头']}</td><td>{r['资金评分']}</td>
            <td style="font-size:12px">{tags}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>左脑战法选股</title>
<style>
* {{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
body {{background:#f5f5f5;padding:20px}}
.header {{background:linear-gradient(135deg,#1a237e,#283593);color:white;padding:25px 30px;border-radius:12px;margin-bottom:20px}}
.header h1 {{font-size:24px}}
.sub {{font-size:13px;opacity:.8;margin-top:5px}}
.top3 {{display:flex;gap:15px;margin-bottom:20px}}
.top-card {{flex:1;background:white;border-radius:10px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.08);text-align:center}}
.medal {{font-size:32px;margin-bottom:5px}}
.top-card h3 {{font-size:16px}}
.top-card h3 small {{font-size:12px;color:#999;margin-left:5px}}
.top-info {{display:flex;justify-content:space-around;margin-top:10px;font-size:14px}}
table {{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
th {{background:#1a237e;color:white;padding:10px 8px;font-size:12px;text-align:center}}
td {{padding:8px;text-align:center;border-bottom:1px solid #eee;font-size:13px}}
tr:hover {{background:#f0f4ff}}
.tag {{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;background:#eee;color:#333;margin:1px}}
.tag-blue {{background:#E3F2FD;color:#1565C0}}
.tag-gold {{background:#FFF8E1;color:#F57F17}}
.tag-green {{background:#E8F5E9;color:#2E7D32}}
.tag-red {{background:#FFEBEE;color:#C62828}}
.tag-purple {{background:#F3E5F5;color:#7B1FA2}}
.summary {{display:flex;gap:15px;margin:20px 0;font-size:13px}}
.summary-item {{background:white;padding:12px 18px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
@media (max-width:768px) {{.top3 {{flex-direction:column}}}}
</style></head><body>
<div class="header">
    <h1>🧠 左脑 · A股战法选股报告</h1>
    <div class="sub">时间: {now_str} | 数据: 新浪/QQ/东方财富 | 战法: B点+三钻+三底+龙头+资金</div>
</div>
<div class="summary">
    <div class="summary-item">📊 共 <b>{len(results)}</b> 只</div>
    <div class="summary-item">🥇 最高 <b>{results.iloc[0]['综合评分'] if len(results)>0 else 0}</b></div>
    <div class="summary-item">📈 涨跌幅中位 <b>{results['涨跌幅%'].median():+.2f}%</b></div>
</div>
<div class="top3">{top3_html}</div>
<table><thead><tr>
    <th>#</th><th>名称</th><th>现价</th><th>涨跌%</th><th>总分</th><th>🅱B点</th><th>💎三钻</th><th>🎯三底</th><th>🐉龙头</th><th>💰资金</th><th>战法</th>
</tr></thead><tbody>{rows}</tbody></table>
<p style="text-align:center;color:#999;font-size:12px;margin-top:15px">左脑 v3.12-OC · 仅供研究参考</p>
</body></html>"""
    
    path = OUTPUT_DIR / f"选股报告_{NOW.strftime('%Y%m%d_%H%M')}.html"
    path.write_text(html, encoding="utf-8")
    print(f"\n[HTML] {path}")
    return str(path)


# ═══════════════════════════════════
# 八、主入口
# ═══════════════════════════════════

def main():
    print("=" * 60)
    print("  🧠 左脑 · A股战法选股引擎 v2")
    print("  数据: 新浪列表 + QQ实时 + 东方财富K线/资金流")
    print("  战法: B点买点 + 三钻 + 三底 + 龙头 + 资金流入")
    print("=" * 60)
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "quick"
    
    # 获取股票池
    if mode == "full":
        pool = get_stock_list_sina(5000)
        label = f"全市场({len(pool)})"
        max_scan = 300
    elif mode == "quick":
        pool = get_stock_list_sina(500)
        label = f"前{len(pool)}只"
        max_scan = 150
    elif mode == "focus" and len(sys.argv) > 2:
        codes = [c.strip() for c in sys.argv[2].split(",")]
        pool = pd.DataFrame({"代码": codes, "名称": [""]*len(codes)})
        label = f"自定义{len(codes)}只"
        max_scan = len(codes)
    else:
        pool = get_stock_list_sina(500)
        label = f"前{len(pool)}只"
        max_scan = 150
    
    if pool.empty:
        print("[错误] 未获取到股票数据")
        return
    
    print(f"\n[股票池] {label}, 计划分析{max_scan}只")
    
    results = comprehensive_screen(pool, max_scan)
    
    if results.empty:
        print("\n[结果] 当前无符合条件的标的")
        return
    
    # 控制台输出
    print(f"\n{'='*60}")
    print(f"  📊 选股结果 — 共{len(results)}只")
    print(f"{'='*60}")
    print(f"{'#':<3} {'代码':<8} {'名称':<8} {'现价':<8} {'涨幅%':<8} {'总分':<5} {'战法':<30}")
    print("-" * 65)
    
    for i in range(min(20, len(results))):
        r = results.iloc[i]
        chg_mk = "🔴" if r["涨跌幅%"] > 5 else ("🟢" if r["涨跌幅%"] > 0 else ("🔵" if r["涨跌幅%"] > -3 else "⚪"))
        strategy_text = str(r["战法"])[:28]
        print(f"{i+1:<3} {r['代码']:<8} {r['名称']:<8} {r['最新价']:<8.2f} {chg_mk}{r['涨跌幅%']:<+6.2f}% {r['综合评分']:<4} {strategy_text}")
    
    print()
    
    # CSV
    csv_path = OUTPUT_DIR / f"选股结果_{NOW.strftime('%Y%m%d_%H%M')}.csv"
    results.to_csv(csv_path, index=False, encoding="utf_8_sig")
    print(f"[CSV] {csv_path}")
    
    # HTML
    html_path = export_html(results)
    
    print(f"\n✅ 完成！{label} → 筛选出{len(results)}只")
    return results


if __name__ == "__main__":
    main()