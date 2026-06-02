"""
multiyears-growth-stock-screener/lib/data_cn.py
A股（沪深300）数据采集函数
"""
import os, json, time
import akshare as ak
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_WORKERS = 12


def fetch_codes_from_index(index_code: str) -> list:
    """从指数代码获取成分股列表
    AKShare 原生提供 index_stock_cons()，A股指数可直接动态获取。
    标普500/恒指无此接口，需用 CSV / 硬编码。"""
    cons = ak.index_stock_cons(index_code)
    codes = cons['品种代码'].unique().tolist()
    print(f"  ✅ {len(codes)} 只成分股")
    return codes


def to_akshare_symbol(code: str) -> str:
    """转换代码格式：600519 → sh600519, 000001 → sz000001"""
    if code.startswith('6') or code.startswith('9'):
        return f'sh{code}'
    elif code.startswith('0') or code.startswith('3') or code.startswith('2'):
        return f'sz{code}'
    return code


def fetch_cn_price(codes: list, out_dir: str, periods: list) -> dict:
    """
    下载A股日线（前复权），提取每年3月末收盘价
    参照已有CSI300方案（数据路径：~/.hermes/stock_cache/csi300_analysis/）
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

    years_needed = set()
    for e, s in periods:
        years_needed.add(str(e))
        years_needed.add(str(s))

    def fetch_one(code):
        try:
            symbol = to_akshare_symbol(code)
            df = ak.stock_zh_a_daily(symbol=symbol, adjust='qfq')
            if df is None or len(df) == 0:
                return code, {}
            df['date'] = df['date'].astype(str)
            closes = {}
            for y in years_needed:
                m = df[df['date'].str[:7] == f'{y}-03']
                if len(m) > 0:
                    closes[y] = float(m.iloc[-1]['close'])
            return code, closes
        except Exception:
            return code, {}

    print(f"📡 下载 {len(codes)} 只A股日线...")
    raw = {}
    done = 0
    with ThreadPoolExecutor(MAX_WORKERS) as tpe:
        futures = {tpe.submit(fetch_one, c): c for c in codes}
        for f in as_completed(futures):
            c, closes = f.result()
            raw[c] = closes
            done += 1
            if done % 50 == 0:
                print(f"  [{done}/{len(codes)}]")

    with open(cache_p, 'w') as fp_:
        json.dump(raw, fp_, ensure_ascii=False)
    print(f"  ✅ {done} 只完成")
    return raw


def parse_financial_value(val) -> float:
    """解析 '547.03亿', '3.81万' 为 float（亿元）"""
    if val is None or val == '' or val is False or val == 'False':
        return None
    val = str(val).strip().replace(',', '').replace(' ', '')
    if '万亿' in val:
        return float(val.replace('万亿', '')) * 10000
    if '亿' in val:
        return float(val.replace('亿', ''))
    if '万' in val:
        return float(val.replace('万', '')) / 10000
    try:
        return float(val) / 100000000
    except:
        return None


def fetch_cn_revenue(codes: list, out_dir: str) -> dict:
    """
    下载A股年报营业总收入
    参照已有CSI300方案（数据路径：~/.hermes/stock_cache/csi300_revenue_analysis/）
    """
    cache_p = os.path.join(out_dir, 'revenue_data.json')
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

    def fetch_one(code):
        try:
            df = ak.stock_financial_abstract_ths(symbol=code)
            if df is None or len(df) == 0:
                return code, {}
            # 年报（12月31日）
            annual = df[df['报告期'].str.endswith('12-31')]
            revenues = {}
            for _, r in annual.iterrows():
                year = int(r['报告期'][:4])
                rev = parse_financial_value(r.get('营业总收入', None))
                if rev and rev > 0:
                    revenues[str(year)] = rev
            return code, revenues
        except Exception:
            return code, {}

    print(f"📡 下载 {len(codes)} 只A股利润表...")
    raw = {}
    done = 0
    with ThreadPoolExecutor(MAX_WORKERS) as tpe:
        futures = {tpe.submit(fetch_one, c): c for c in codes}
        for f in as_completed(futures):
            c, rev = f.result()
            raw[c] = rev
            done += 1
            if done % 100 == 0:
                print(f"  [{done}/{len(codes)}]")

    with open(cache_p, 'w') as fp_:
        json.dump(raw, fp_, ensure_ascii=False)
    print(f"  ✅ {done} 只完成")
    return raw
