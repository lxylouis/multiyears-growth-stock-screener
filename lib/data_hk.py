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

# ── 恒指成分股名称硬编码后备 ──
# AKShare 港股实时行情(stock_hk_spot)从腾讯云获取，在GFW环境不稳定。
# 当API失效时使用此硬编码列表作为后备。
HSI_NAMES = {
    '00001':'长和', '00002':'中电控股', '00003':'香港中华煤气', '00005':'汇丰控股',
    '00006':'电能实业', '00011':'恒生银行', '00012':'恒基地产', '00016':'新鸿基地产',
    '00017':'新世界发展', '00019':'太古股份公司A', '00027':'银河娱乐', '00066':'港铁公司',
    '00083':'信和置业', '00101':'恒隆地产', '00175':'吉利汽车', '00241':'阿里健康',
    '00267':'中信股份', '00288':'万洲国际', '00291':'华润啤酒', '00316':'东方海外国际',
    '00322':'康师傅控股', '00388':'香港交易所', '00700':'腾讯控股', '00762':'中国联通',
    '00788':'中国铁塔', '00823':'领展房产基金', '00857':'中国石油股份', '00883':'中国海洋石油',
    '00939':'中国建设银行', '00941':'中国移动', '00981':'中芯国际', '00992':'联想集团',
    '01038':'长江基建集团', '01044':'恒安国际', '01057':'浙江沪杭甬', '01066':'威高股份',
    '01071':'华电国际电力股份', '01088':'中国神华', '01093':'石药集团', '01099':'国药控股',
    '01109':'华润置地', '01113':'长实集团', '01171':'兖矿能源', '01209':'华润万象生活',
    '01211':'比亚迪股份', '01299':'友邦保险', '01347':'华虹半导体', '01357':'美图公司',
    '01378':'中国宏桥', '01398':'工商银行', '01810':'小米集团-W', '01876':'百威亚太',
    '01898':'中煤能源', '01919':'中远海控', '01928':'金沙中国有限公司', '01929':'周大福',
    '01997':'九龙仓置业', '02007':'碧桂园服务', '02015':'理想汽车-W', '02018':'瑞声科技',
    '02020':'安踏体育', '02269':'药明生物', '02313':'申洲国际', '02318':'中国平安',
    '02319':'蒙牛乳业', '02328':'中国财险', '02331':'李宁', '02333':'长城汽车',
    '02338':'潍柴动力', '02359':'药明康德', '02382':'舜宇光学科技', '02388':'中银香港',
    '02601':'中国太保', '02628':'中国人寿', '02688':'新奥能源', '02899':'紫金矿业',
    '03690':'美团-W', '03968':'招商银行', '03988':'中国银行', '06060':'众安在线',
    '06185':'康龙化成', '06618':'京东健康', '06690':'海尔智家', '06862':'海底捞',
    '06969':'思摩尔国际', '09626':'哔哩哔哩-W', '09633':'农夫山泉', '09698':'万国数据-SW',
    '09888':'百度集团-SW', '09901':'新东方-S', '09961':'携程集团-S', '09987':'百胜中国',
    '09988':'阿里巴巴-W', '09992':'泡泡玛特', '09999':'网易-S',
}


def fetch_hk_codes(config: dict) -> list:
    """获取港股代码列表"""
    sc = config['stock_codes']
    if sc['type'] == 'hardcoded':
        result = []
        for entry in sc['codes']:
            if isinstance(entry, str):
                for c in entry.replace("'", "").replace('"', '').split(','):
                    c = c.strip()
                    if c and c.isdigit():
                        result.append(c)
            elif isinstance(entry, list):
                result.extend(entry)
        return result or HSI_CODES
    return HSI_CODES


def fetch_hk_names(codes: list) -> dict:
    """
    获取港股名称字典 {code: name}
    优先使用 AKShare 实时行情 API，失败时回退到硬编码名称列表。
    """
    try:
        spot = ak.stock_hk_spot()
        spot['代码'] = spot['代码'].astype(str).str.zfill(5)
        names = {}
        for _, r in spot[spot['代码'].isin(codes)].iterrows():
            names[r['代码']] = r['中文名称']
        if names:
            print(f"  ✅ AKShare 获取 {len(names)} 只名称成功")
            return names
    except Exception as e:
        print(f"  ⚠️  stock_hk_spot 失败 ({e})，使用硬编码名称后备")
    # 后备：对没有硬编码名称的代码使用默认名称
    result = {}
    for c in codes:
        result[c] = HSI_NAMES.get(c, f'港股{c}')
    print(f"  ✅ 使用硬编码名称 ({len(result)}只)")
    return result


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
