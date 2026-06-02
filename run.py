#!/usr/bin/env python3
"""
multiyears-growth-stock-screener/run.py — 多年增长选股统一Pipeline

用法：
  python3 run.py --index hsi
  python3 run.py --index sp500 --mode revenue --window-years 3 --num-windows 4
  python3 run.py --index csi300 --window-years 5 --num-windows 5 \
    --price-base-yyyymm 2026-03 --revenue-base-yyyy 2026

参数详解见 README.md
"""
import os, sys, argparse, yaml, datetime, re
from pathlib import Path

BASE = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE / 'lib'))

from compute import (period_mult_cols, make_weights, filter_by_growth,
                     industry_hk, industry_us)
from charts import (chart_trend, chart_heatmap, chart_industry, chart_boxplot,
                    chart_sustainability, chart_dual_bar, chart_dual_scatter,
                    chart_dual_trend)
from report import build_price_report, build_dual_report


def parse_year_month(val: str):
    """解析 '2026-03' → (year=2026, month=3)"""
    m = re.match(r'^(\d{4})-(\d{2})$', val)
    if not m:
        raise ValueError(f"格式错误：'{val}'，应为 YYYY-MM（如 2026-03）")
    return int(m.group(1)), int(m.group(2))


def auto_periods(base_year: int, window_years: int, num_windows: int):
    """
    自动生成时间窗口对。
    例：base_year=2026, window_years=5, num_windows=5
    → [(2022,2017), (2023,2018), (2024,2019), (2025,2020), (2026,2021)]
    """
    return [[base_year - i, base_year - i - window_years]
            for i in range(num_windows - 1, -1, -1)]


def auto_labels(periods: list, month: int = None) -> list:
    """从periods生成标签。
    无month：'21/16'；有month：'26M3→21M3'"""
    if month is None:
        return [f'{e % 100}/{s % 100}' for e, s in periods]
    return [f'{e % 100}M{month}→{s % 100}M{month}' for e, s in periods]


def load_config(index: str) -> dict:
    cf = BASE / 'configs' / f'{index}.yaml'
    if not cf.exists():
        raise FileNotFoundError(f'Config not found: {cf}')
    with open(cf) as f:
        return yaml.safe_load(f)


def load_us_names(config):
    """从CSV加载美股名称字典"""
    import pandas as pd
    csv_path = os.path.join(str(BASE), config['stock_codes']['csv_path'])
    df = pd.read_csv(csv_path)
    return dict(zip(df[config['stock_codes']['ticker_col']].str.strip(),
                    df[config['stock_codes']['name_col']]))


def main():
    this_year = datetime.date.today().year  # 2026

    parser = argparse.ArgumentParser(description='股票增长分析统一Pipeline')
    parser.add_argument('--index', required=True,
                        help='指数名称（如 sp500, csi300, hsi）')
    parser.add_argument('--mode', default='all',
                        choices=['all', 'price', 'revenue', 'dual'],
                        help='运行模式')
    parser.add_argument('--window-years', type=int, default=None,
                        help='每个窗口跨多少年（如 5=5年增长倍率，默认从YAML读取）')
    parser.add_argument('--num-windows', type=int, default=None,
                        help='从基准年往过去推几个窗口（如 5=5个5年窗口，默认从YAML读取）')
    parser.add_argument('--price-base-yyyymm', type=str, default=None,
                        help='股价基准年月，格式 YYYY-MM（如 2026-03），默认今年3月')
    parser.add_argument('--revenue-base-yyyy', type=int, default=None,
                        help='营收基准年（如 2026），默认A股=今年，美股/港股=去年')
    args = parser.parse_args()

    config = load_config(args.index)
    index_name = config['index']['name']
    market = config['index']['market']
    out_dir = os.path.expanduser(config.get('output_dir'))
    os.makedirs(out_dir, exist_ok=True)

    # ── 确定时间窗口 ──
    window_years = args.window_years or config.get('defaults', {}).get('window_years', 5)
    num_windows = args.num_windows or config.get('defaults', {}).get('num_windows',
                     len(config.get('periods', {}).get('price', [])))

    # 股价基准：解析 YYYY-MM
    if args.price_base_yyyymm:
        py_base, pm = parse_year_month(args.price_base_yyyymm)
        if pm != 3:
            print(f'⚠️  当前数据层仅支持3月末（M03），您指定了M{pm:02d}，将使用M03代替')
            pm = 3
    else:
        py_base = this_year
        pm = 3

    # 营收基准：纯年份
    if args.revenue_base_yyyy:
        ry_base = args.revenue_base_yyyy
    elif market == 'cn':
        ry_base = this_year - 1  # 最新年报为去年
    else:
        ry_base = this_year - 1  # 最新年报为去年 - 1

    # ── 生成/加载 periods 和 labels ──
    if args.window_years or args.num_windows or args.price_base_yyyymm or args.revenue_base_yyyy:
        price_periods = auto_periods(py_base, window_years, num_windows)
        rev_periods = auto_periods(ry_base, window_years, num_windows)
        price_labels = auto_labels(price_periods, month=pm)
        revenue_labels = auto_labels(rev_periods)
        print(f'📐 自动生成时间窗口: {window_years}年×{num_windows}个窗口')
        print(f'   股价: {py_base}年{pm}月 → {py_base - num_windows + 1}年{pm}月 倒推')
        print(f'   营收: {ry_base}年年报 → {ry_base - num_windows + 1}年年报')
    else:
        price_periods = config['periods']['price']
        rev_periods = config['periods']['revenue']
        price_labels = config['periods'].get('price_labels', config['periods'].get('labels', []))
        revenue_labels = config['periods'].get('revenue_labels', config['periods'].get('labels', []))

    if len(price_labels) < len(price_periods):
        price_labels = auto_labels(price_periods)
    if len(revenue_labels) < len(rev_periods):
        revenue_labels = auto_labels(rev_periods)

    n_common = min(len(price_periods), len(rev_periods))
    common_labels = revenue_labels[:n_common]

    import numpy as np
    import pandas as pd

    # ═══ 股价 ═══
    if args.mode in ('all', 'price'):
        print(f'\n{"="*50}\n📈 {index_name} 股价分析\n{"="*50}')
        p_periods = price_periods
        p_mc = period_mult_cols(p_periods)
        p_w = make_weights(len(p_periods))

        if market == 'hk':
            from data_hk import fetch_hk_codes, fetch_hk_names, fetch_hk_price
            codes = fetch_hk_codes(config)
            names = fetch_hk_names(codes)
            raw = fetch_hk_price(codes, out_dir, p_periods)
            ind_fn = industry_hk
        elif market == 'us':
            from data_us import fetch_us_codes, fetch_us_price
            codes = fetch_us_codes(config)
            names = load_us_names(config)
            raw = fetch_us_price(codes, out_dir, p_periods)
            ind_fn = industry_us
        else:
            from data_cn import fetch_codes_from_index, fetch_cn_price
            codes = fetch_codes_from_index(config['stock_codes']['source_arg'])
            raw = fetch_cn_price(codes, out_dir, p_periods)
            names = {c: c for c in codes}
            ind_fn = industry_hk

        rows = []
        for c in codes:
            p = raw.get(c, {})
            if not p: continue
            yrs = set()
            for e, s in p_periods:
                yrs.add(str(e)); yrs.add(str(s))
            if not all(y in p for y in yrs): continue
            row = {'代码': c, '名称': names.get(c, c), '行业': ind_fn(names.get(c, ''))}
            mults = []
            for e, s in p_periods:
                m = p[str(e)] / p[str(s)]
                row[f'{e}/{s}倍率'] = round(m, 4)
                mults.append(m)
            row['平均倍率'] = round(float(np.mean(mults)), 4) if mults else 0
            row['分数'] = round(sum(m * w for m, w in zip(mults, p_w)), 4)
            row['波动'] = round(float(np.std(mults)), 4) if len(mults) > 1 else 0
            rows.append(row)

        fp_df = pd.DataFrame(rows)
        print(f'  ✅ {len(fp_df)} 只有效数据')

        pp = filter_by_growth(fp_df, p_mc)
        t20 = pp.head(min(20, len(pp)))
        print(f'  ✅ 筛选通过: {len(pp)}/{len(fp_df)} 只 (保留条件：全期≥0.9 ∪ 最新期>1.5)')

        fp_df.to_csv(os.path.join(out_dir, 'all_stocks_price.csv'), index=False, encoding='utf-8-sig')

        chart_dir = os.path.join(out_dir, 'charts')
        os.makedirs(chart_dir, exist_ok=True)
        ch = {}
        if len(t20) >= 2:
            chart_trend(t20, p_mc, price_labels,
                       f'{index_name} TOP20 · 股价增长', f'{chart_dir}/chart1_trend.png')
            chart_heatmap(t20, p_mc, price_labels,
                         f'{index_name} TOP20 · 热力图', f'{chart_dir}/chart2_heatmap.png')
            ch = {'trend': f'{chart_dir}/chart1_trend.png', 'heatmap': f'{chart_dir}/chart2_heatmap.png'}
        if len(pp) >= 5:
            chart_industry(pp, f'{index_name} · 各行业平均增长', f'{chart_dir}/chart3_industry.png')
            chart_boxplot(pp, p_mc, price_labels,
                         f'{index_name} · 各周期分布', f'{chart_dir}/chart4_boxplot.png')
            chart_sustainability(pp, p_mc, f'{index_name} · 持续性 vs 分数',
                                f'{chart_dir}/chart5_sustainability.png')
            ch.update({'industry': f'{chart_dir}/chart3_industry.png',
                       'boxplot': f'{chart_dir}/chart4_boxplot.png',
                       'sustainability': f'{chart_dir}/chart5_sustainability.png'})

        build_price_report(index_name, len(fp_df), len(pp), t20, pp, fp_df,
                          p_mc, price_labels, ch,
                          os.path.join(out_dir, f'{index_name}_股价增长分析报告.docx'))
        print(f'  ✅ 股价完成')

    # ═══ 营收 ═══
    if args.mode in ('all', 'revenue'):
        print(f'\n{"="*50}\n💰 {index_name} 营收分析\n{"="*50}')
        r_periods = rev_periods
        r_mc = period_mult_cols(r_periods)
        r_w = make_weights(len(r_periods))

        if market == 'hk':
            from data_hk import fetch_hk_codes, fetch_hk_names, fetch_hk_revenue
            codes = fetch_hk_codes(config)
            names = fetch_hk_names(codes)
            raw = fetch_hk_revenue(codes, out_dir, r_periods)
            ind_fn = industry_hk
        elif market == 'us':
            from data_us import fetch_us_codes, fetch_us_revenue
            codes = fetch_us_codes(config)
            names = load_us_names(config)
            raw = fetch_us_revenue(codes, out_dir, r_periods)
            ind_fn = industry_us
        else:
            from data_cn import fetch_codes_from_index, fetch_cn_revenue
            codes = fetch_codes_from_index(config['stock_codes']['source_arg'])
            raw = fetch_cn_revenue(codes, out_dir)
            names = {c: c for c in codes}
            ind_fn = industry_hk

        rows = []
        for c in codes:
            rev = raw.get(c, {})
            if not rev: continue
            yrs = set()
            for e, s in r_periods:
                yrs.add(str(e)); yrs.add(str(s))
            if not all(y in rev for y in yrs): continue
            row = {'代码': c, '名称': names.get(c, c), '行业': ind_fn(names.get(c, ''))}
            mults = []
            for e, s in r_periods:
                m = rev[str(e)] / rev[str(s)]
                row[f'{e}/{s}倍率'] = round(m, 4)
                mults.append(m)
            row['平均倍率'] = round(float(np.mean(mults)), 4)
            row['分数'] = round(sum(m * w for m, w in zip(mults, r_w)), 4)
            row['波动'] = round(float(np.std(mults)), 4) if len(mults) > 1 else 0
            rows.append(row)

        fp_df = pd.DataFrame(rows)
        print(f'  ✅ {len(fp_df)} 只有效营收数据')
        pp = filter_by_growth(fp_df, r_mc)
        t20 = pp.head(min(20, len(pp)))
        print(f'  ✅ 营收筛选通过: {len(pp)}/{len(fp_df)} 只 (保留条件：全期≥0.9 ∪ 最新期>1.5)')

        fp_df.to_csv(os.path.join(out_dir, 'all_stocks_revenue.csv'), index=False, encoding='utf-8-sig')

        chart_dir = os.path.join(out_dir, 'charts_revenue')
        os.makedirs(chart_dir, exist_ok=True)
        ch = {}
        if len(t20) >= 2:
            chart_trend(t20, r_mc, revenue_labels,
                       f'{index_name} TOP20 · 营收增长', f'{chart_dir}/chart1_revenue_trend.png')
            chart_heatmap(t20, r_mc, revenue_labels,
                         f'{index_name} TOP20 · 热力图', f'{chart_dir}/chart2_revenue_heatmap.png',
                         vmax_cap=50)
            ch = {'trend': f'{chart_dir}/chart1_revenue_trend.png',
                  'heatmap': f'{chart_dir}/chart2_revenue_heatmap.png'}
        if len(pp) >= 5:
            chart_industry(pp, f'{index_name} · 各行业平均营收增长',
                          f'{chart_dir}/chart3_revenue_industry.png')
            chart_boxplot(pp, r_mc, revenue_labels,
                         f'{index_name} · 营收各周期分布', f'{chart_dir}/chart4_revenue_boxplot.png')
            chart_sustainability(pp, r_mc, f'{index_name} · 营收持续性 vs 分数',
                                f'{chart_dir}/chart5_revenue_sustainability.png')
            ch.update({'industry': f'{chart_dir}/chart3_revenue_industry.png',
                       'boxplot': f'{chart_dir}/chart4_revenue_boxplot.png',
                       'sustainability': f'{chart_dir}/chart5_revenue_sustainability.png'})

        build_price_report(index_name, len(fp_df), len(pp), t20, pp, fp_df,
                          r_mc, revenue_labels, ch,
                          os.path.join(out_dir, f'{index_name}_营收增长分析报告.docx'))
        print(f'  ✅ 营收完成')

    # ═══ 双维度 ═══
    if args.mode in ('all', 'dual'):
        print(f'\n{"="*50}\n🏆 {index_name} 双维度分析\n{"="*50}')

        p_mc = period_mult_cols(price_periods[:n_common])
        r_mc = period_mult_cols(rev_periods[:n_common])
        cw = make_weights(n_common)

        price_csv = os.path.join(out_dir, 'all_stocks_price.csv')
        rev_csv = os.path.join(out_dir, 'all_stocks_revenue.csv')

        if not os.path.exists(price_csv) or not os.path.exists(rev_csv):
            print('⚠️  需要先运行 price + revenue 模式，再跑 dual')
            return

        price_df = pd.read_csv(price_csv, encoding='utf-8-sig')
        rev_df = pd.read_csv(rev_csv, encoding='utf-8-sig')

        for c in p_mc: price_df[c] = pd.to_numeric(price_df[c], errors='coerce')
        for c in r_mc: rev_df[c] = pd.to_numeric(rev_df[c], errors='coerce')
        price_df['分数'] = sum(price_df[c]*w for c,w in zip(p_mc, cw))
        rev_df['分数'] = sum(rev_df[c]*w for c,w in zip(r_mc, cw))

        price_pp = filter_by_growth(price_df, p_mc)
        rev_pp = filter_by_growth(rev_df, r_mc)

        merged = price_df[['代码','名称','行业','分数']].rename(columns={'分数':'股价分数'}).copy()
        merged = merged.merge(rev_df[['代码','分数']].rename(columns={'分数':'营收分数'}),
                             on='代码', how='left')
        merged['综合分数'] = merged[['股价分数','营收分数']].mean(axis=1)
        merged['双通过'] = merged['代码'].isin(price_pp['代码']) & merged['代码'].isin(rev_pp['代码'])
        merged['仅股价'] = merged['代码'].isin(price_pp['代码']) & ~merged['代码'].isin(rev_pp['代码'])
        merged['仅营收'] = ~merged['代码'].isin(price_pp['代码']) & merged['代码'].isin(rev_pp['代码'])
        merged = merged.sort_values('综合分数', ascending=False).reset_index(drop=True)

        print(f'  双通过: {merged["双通过"].sum()}  仅股价: {merged["仅股价"].sum()}  仅营收: {merged["仅营收"].sum()}')

        chart_dir = os.path.join(out_dir, 'charts_dual')
        os.makedirs(chart_dir, exist_ok=True)
        ch = {}
        pt20 = price_pp.head(20)
        rt20 = rev_pp.head(20)
        chart_dual_bar(pt20, rt20, price_pp, rev_pp,
                      f'{index_name} · 股价 vs 营收 对比', f'{chart_dir}/chart1_dual_bar.png')
        chart_dual_scatter(merged, f'{index_name} · 双维度散点图',
                          f'{chart_dir}/chart2_dual_scatter.png')
        ch['dual_bar'] = f'{chart_dir}/chart1_dual_bar.png'
        ch['dual_scatter'] = f'{chart_dir}/chart2_dual_scatter.png'

        elite_df = merged[merged['双通过']].sort_values('综合分数', ascending=False).head(min(20, merged['双通过'].sum()))
        if len(elite_df) >= 2:
            chart_dual_trend(elite_df, price_df, rev_df, p_mc, r_mc,
                            common_labels, f'{index_name}',
                            f'{chart_dir}/chart3_dual_trend.png')
            ch['dual_trend'] = f'{chart_dir}/chart3_dual_trend.png'

        build_dual_report(index_name, price_pp, rev_pp, price_df, rev_df, merged,
                         p_mc, r_mc, common_labels, ch,
                         os.path.join(out_dir, f'{index_name}_双维度增长分析报告.docx'))
        print(f'  ✅ 双维度完成')


if __name__ == '__main__':
    main()
