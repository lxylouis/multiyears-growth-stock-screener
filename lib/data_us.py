"""
multiyears-growth-stock-screener/lib/data_us.py
美股（S&P 500）数据采集函数
"""
import os, json, time
import akshare as ak
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_WORKERS = 12


def fetch_us_codes(config: dict) -> list:
    """从CSV获取S&P 500代码列表
    AKShare 没有标普500成分股接口，需从 SlickCharts CSV 定期维护。
    沪深300有 index_stock_cons() 可动态获取，写法不同是市场差异导致。"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base, config['stock_codes']['csv_path'])
    ticker_col = config['stock_codes']['ticker_col']
    name_col = config['stock_codes']['name_col']
    df = pd.read_csv(csv_path)
    codes = df[ticker_col].str.strip().tolist()
    print(f"  ✅ {len(codes)} 只成分股")
    return codes


def fetch_us_names_and_sectors(codes: list) -> dict:
    """从新浪获取美股名称和行业。sin字段名需确认。"""
    try:
        spot = ak.stock_us_spot()
        # Columns usually include: 名称, 最新价, etc. Need to check Chinese names
        info = {}
        for _, row in spot.iterrows():
            symbol = str(row.get('symbol', '')).strip()
            if symbol in codes:
                info[symbol] = {
                    'name': row.get('name', symbol),
                    'cname': row.get('cname', row.get('name', symbol)),
                }
        return info
    except Exception as e:
        print(f"  ⚠️ stock_us_spot failed: {e}")
        return {}


def fetch_us_price(codes: list, out_dir: str, periods: list) -> dict:
    """
    下载美股日线，提取每年3月末收盘价
    Returns: {symbol: {year_str: close_price}}
    """
    cache_p = os.path.join(out_dir, 'march_closes.json')
    if os.path.exists(cache_p) and os.path.getsize(cache_p) > 0 \
       and (time.time()-os.path.getmtime(cache_p))/86400 < 30:
        try:
            with open(cache_p) as f:
                data = json.load(f)
                if data:
                    print(f"📂 使用股价缓存 ({len(data)}只)")
                    return data
        except (json.JSONDecodeError, ValueError):
            print(f"⚠️  缓存文件损坏，重新下载")
            os.remove(cache_p)

    years_needed = set()
    for e, s in periods:
        years_needed.add(str(e))
        years_needed.add(str(s))

    def adjust_for_splits(df):
        """
        检测拆股并前复权修正。
        正向拆股（价格暴跌>40%）：将拆股点之前的所有close价格除以拆股比例。
        反向拆股（价格暴涨>300%）：将拆股点之前的所有close价格乘以拆股比例（1:8逆拆股后股数减为1/8，但每股价涨8倍）。
        从最新到最旧逆向处理，一次遍历完成。
        """
        df = df.sort_values('date').reset_index(drop=True)
        df['pct_chg'] = df['close'].pct_change()
        # 正向拆股：单日跌幅>40%（如 4:1 导致 -75%）
        forward_idx = df[df['pct_chg'] < -0.4].index.tolist()
        # 反向拆股：单日涨幅>200%（如 1:8 逆拆股导致 +700%）
        reverse_idx = df[df['pct_chg'] > 2.0].index.tolist()
        # 从新到旧逆向处理（先处理反向拆股，再处理正向拆股）
        for idx in reversed(reverse_idx):
            prev_close = df.loc[idx - 1, 'close'] if idx > 0 else 0
            curr_close = df.loc[idx, 'close']
            if curr_close > 0 and prev_close > 0:
                ratio = max(2, int(round(curr_close / prev_close)))
                # 反向拆股：将之前的价格乘以比例（1:8逆拆股后每股价涨8倍）
                df.loc[:idx-1, 'close'] = df.loc[:idx-1, 'close'] * ratio
        for idx in reversed(forward_idx):
            prev_close = df.loc[idx - 1, 'close'] if idx > 0 else 0
            curr_close = df.loc[idx, 'close']
            if curr_close > 0 and prev_close > 0:
                ratio = max(2, int(round(prev_close / curr_close)))
                # 正向拆股：将之前的价格除以比例
                df.loc[:idx-1, 'close'] = df.loc[:idx-1, 'close'] / ratio
        df = df.drop(columns=['pct_chg'], errors='ignore')
        return df

    def fetch_one(symbol):
        try:
            df = ak.stock_us_daily(symbol=symbol)
            if df is None or len(df) == 0:
                return symbol, {}
            df['date'] = df['date'].astype(str)
            # 前复权修正
            df_adj = adjust_for_splits(df.copy())
            closes = {}
            for y in years_needed:
                m = df_adj[df_adj['date'].str[:7] == f'{y}-03']
                if len(m) > 0:
                    closes[y] = float(m.iloc[-1]['close'])
            return symbol, closes
        except Exception as e:
            return symbol, {}

    print(f"📡 下载 {len(codes)} 只美股日线...")
    raw = {}
    done = 0
    with ThreadPoolExecutor(MAX_WORKERS) as tpe:
        futures = {tpe.submit(fetch_one, c): c for c in codes}
        for f in as_completed(futures):
            c, closes = f.result()
            raw[c] = closes
            done += 1
            if done % 100 == 0:
                print(f"  [{done}/{len(codes)}]")

    # Clean: only keep entries with data
    raw = {k: v for k, v in raw.items() if v}
    with open(cache_p, 'w') as fp_:
        json.dump(raw, fp_, ensure_ascii=False)
    print(f"  ✅ {done} 只完成, {len(raw)} 只有效数据")
    return raw


def fetch_us_revenue(codes: list, out_dir: str, periods: list) -> dict:
    """
    下载美股利润表，提取年报营收
    Returns: {symbol: {year_str: revenue_in_usd}}
    """
    cache_p = os.path.join(out_dir, 'us_revenue.json')
    if os.path.exists(cache_p) and os.path.getsize(cache_p) > 0 \
       and (time.time()-os.path.getmtime(cache_p))/86400 < 30:
        try:
            with open(cache_p) as f:
                data = json.load(f)
                if data:
                    print(f"📂 使用营收缓存 ({len(data)}只)")
                    return data
        except (json.JSONDecodeError, ValueError):
            print(f"⚠️  营收缓存损坏，重新下载")
            os.remove(cache_p)

    years_needed = set()
    for e, s in periods:
        years_needed.add(str(e))
        years_needed.add(str(s))

    def fetch_one(symbol):
        try:
            df = ak.stock_financial_us_report_em(stock=symbol, symbol='综合损益表', indicator='年报')
            if df is None or len(df) == 0:
                return symbol, {}
            # Try "主营收入" first, then "营业收入", then first STD_ITEM_CODE row
            rev_items = df[df['ITEM_NAME'].isin(['主营收入', '营业收入'])]
            rev = None
            if len(rev_items) > 0:
                rev = rev_items.copy()
            else:
                # Fallback: use the first item (by code) from latest year — typically top-line
                latest_date = df['REPORT_DATE'].max()
                latest_rows = df[df['REPORT_DATE'] == latest_date].sort_values('STD_ITEM_CODE')
                if len(latest_rows) > 0:
                    top_item = latest_rows.iloc[0]['ITEM_NAME']
                    rev = df[df['ITEM_NAME'] == top_item].copy()
            if rev is None or len(rev) == 0:
                return symbol, {}
            rev['year'] = rev['REPORT_DATE'].str[:4]
            rev['year_int'] = rev['year'].astype(int)
            rev = rev[rev['year_int'].between(2014, 2026)]
            result = {}
            for _, row in rev.iterrows():
                result[str(row['year_int'])] = float(row['AMOUNT'])
            return symbol, result
        except Exception:
            return symbol, {}

    print(f"📡 下载 {len(codes)} 只美股利润表...")
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

    raw = {k: v for k, v in raw.items() if v}
    with open(cache_p, 'w') as fp_:
        json.dump(raw, fp_, ensure_ascii=False)
    print(f"  ✅ {done} 只完成, {len(raw)} 只有效营收数据")
    return raw
