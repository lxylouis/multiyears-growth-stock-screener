"""
multiyears-growth-stock-screener/lib/data_hk.py
港股数据采集函数
"""
import os, json, time
import akshare as ak
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

MAX_WORKERS = 8

# ── 恒指93只成分股（硬编码）
# AKShare 没有获取恒生指数实时成分股的接口，因此只能手动维护当前成分股列表。
# 若恒指官方开放免费接口可改为动态获取。 ──
HSI_CODES = [
    '00001','00002','00003','00005','00006','00011','00012','00016','00017',
    '00019','00027','00066','00083','00101','00175','00241','00267','00288',
    '00291','00316','00322','00388','00700','00762','00788','00823','00857',
    '00883','00939','00941','00981','00992','01038','01044','01057','01066',
    '01071','01088','01093','01099','01109','01113','01171','01209','01211',
    '01299','01347','01357','01378','01398','01810','01876','01898','01919',
    '01928','01929','01997','02007','02015','02018','02020','02269','02313',
    '02318','02319','02328','02331','02333','02338','02359','02382','02388',
    '02601','02628','02688','02899','03690','03968','03988','06060','06185',
    '06618','06690','06862','06969','09626','09633','09698','09888','09901',
    '09961','09987','09988','09992','09999',
]


def fetch_hk_codes(config: dict) -> list:
    """获取港股代码列表"""
    sc = config['stock_codes']
    if sc['type'] == 'hardcoded':
        # Flatten the code lists
        result = []
        for entry in sc['codes']:
            if isinstance(entry, str):
                # Could be comma-separated string
                for c in entry.replace("'", "").replace('"', '').split(','):
                    c = c.strip()
                    if c and c.isdigit():
                        result.append(c)
            elif isinstance(entry, list):
                result.extend(entry)
        return result or HSI_CODES
    return HSI_CODES


def fetch_hk_names(codes: list) -> dict:
    """获取港股名称字典 {code: name}"""
    spot = ak.stock_hk_spot()
    spot['代码'] = spot['代码'].astype(str).str.zfill(5)
    names = {}
    for _, r in spot[spot['代码'].isin(codes)].iterrows():
        names[r['代码']] = r['中文名称']
    return names


def fetch_hk_price(codes: list, out_dir: str, periods: list) -> dict:
    """
    下载港股日线数据，提取每年3月末收盘价
    periods: [(2021,2016), ...] — 需要其中所有年份
    Returns: {code: {year_str: close_price}}
    """
    cache_p = os.path.join(out_dir, 'march_closes.json')
    if os.path.exists(cache_p) and os.path.getsize(cache_p) > 0 \
       and (time.time()-os.path.getmtime(cache_p))/86400 < 7:
        try:
            with open(cache_p) as f:
                data = json.load(f)
                if data:
                    print(f"📂 使用缓存 ({len(data)}只)")
                    return data
        except (json.JSONDecodeError, ValueError):
            print(f"⚠️  缓存文件损坏，重新下载")
            os.remove(cache_p)

    # 获取名称
    names = fetch_hk_names(codes)
    # Build list of (code, name) pairs, keeping only those with names
    code_name_pairs = [(c, names.get(c, '')) for c in codes]
    code_name_pairs = [(c, n) for c, n in code_name_pairs if n]

    def fetch_one(code):
        try:
            df = ak.stock_hk_daily(symbol=code)
            if df is None or len(df) == 0:
                return code, {}
            df['date'] = df['date'].astype(str)
            closes = {}
            years_needed = set()
            for e, s in periods:
                years_needed.add(str(e))
                years_needed.add(str(s))
            for y in years_needed:
                m = df[df['date'].str[:7] == f'{y}-03']
                if len(m) > 0:
                    closes[y] = float(m.iloc[-1]['close'])
            return code, closes
        except Exception:
            return code, {}

    print(f"📡 下载 {len(code_name_pairs)} 只港股日线...")
    raw = {}
    done = 0
    with ThreadPoolExecutor(MAX_WORKERS) as tpe:
        futures = {tpe.submit(fetch_one, c): c for c, _ in code_name_pairs}
        for f in as_completed(futures):
            c, closes = f.result()
            raw[c] = closes
            done += 1
            if done % 20 == 0:
                print(f"  [{done}/{len(code_name_pairs)}]")

    with open(cache_p, 'w') as fp_:
        json.dump(raw, fp_, ensure_ascii=False)
    print(f"  ✅ {done} 只完成")
    return raw


def fetch_hk_revenue(codes: list, out_dir: str, periods: list) -> dict:
    """
    下载港股利润表，提取年报营收
    Returns: {code: {year_str: revenue_amount}}
    """
    cache_p = os.path.join(out_dir, 'hk_revenue.json')
    if os.path.exists(cache_p) and os.path.getsize(cache_p) > 0 \
       and (time.time()-os.path.getmtime(cache_p))/86400 < 7:
        try:
            with open(cache_p) as f:
                data = json.load(f)
                if data:
                    print(f"📂 使用营收缓存 ({len(data)}只)")
                    return data
        except (json.JSONDecodeError, ValueError):
            print(f"⚠️  营收缓存损坏，重新下载")
            os.remove(cache_p)

    names = fetch_hk_names(codes)
    code_name_pairs = [(c, names.get(c, '')) for c in codes]
    code_name_pairs = [(c, n) for c, n in code_name_pairs if n]

    years_needed = set()
    for e, s in periods:
        years_needed.add(str(e))
        years_needed.add(str(s))

    def fetch_one(code):
        try:
            df = ak.stock_financial_hk_report_em(stock=code, symbol='利润表', indicator='年度')
            if df is None or len(df) == 0:
                return code, {}
            # Try revenue items in priority order
            rev = None
            for item in ['营业额', '营业收入', '经营收入总额']:
                rev = df[df['STD_ITEM_NAME'] == item].copy()
                if len(rev) > 0:
                    break
            if rev is None or len(rev) == 0:
                return code, {}
            rev['year'] = rev['REPORT_DATE'].str[:4]
            rev['year_int'] = rev['year'].astype(int)
            rev = rev[rev['year_int'].between(2015, 2026)]
            result = {}
            for _, row in rev.iterrows():
                result[str(row['year_int'])] = float(row['AMOUNT'])
            return code, result
        except Exception:
            return code, {}

    print(f"📡 下载 {len(code_name_pairs)} 只利润表...")
    raw = {}
    done = 0
    with ThreadPoolExecutor(MAX_WORKERS) as tpe:
        futures = {tpe.submit(fetch_one, c): c for c, _ in code_name_pairs}
        for f in as_completed(futures):
            c, rev = f.result()
            raw[c] = rev
            done += 1
            if done % 20 == 0:
                print(f"  [{done}/{len(code_name_pairs)}]")

    with open(cache_p, 'w') as fp_:
        json.dump(raw, fp_, ensure_ascii=False)
    print(f"  ✅ {done} 只完成")
    return raw
