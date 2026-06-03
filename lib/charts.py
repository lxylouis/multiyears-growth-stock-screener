"""
multiyears-growth-stock-screener/lib/charts.py
共享图表生成：5张标准图表 + 2张双维度图
调用方提供数据即可，图表样式统一
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches

FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if os.path.exists(FONT_PATH):
    fontManager.addfont(FONT_PATH)
    FP = FontProperties(fname=FONT_PATH, size=10)
    plt.rcParams['font.sans-serif'] = [FP.get_name(), 'DejaVu Sans']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False


def _fp(s=10):
    return FontProperties(fname=FONT_PATH, size=s) if os.path.exists(FONT_PATH) else None


def chart_trend(t20: pd.DataFrame, mult_cols: list, period_labels: list,
                title: str, save_path: str):
    """Chart 1: TOP20增长趋势（对数坐标，线末端标名称）"""
    fig, ax = plt.subplots(figsize=(20, 13))
    colors = plt.cm.tab20(np.linspace(0, 1, 20))
    for i, (_, r) in enumerate(t20.iterrows()):
        vals = [r[c] if pd.notna(r[c]) else None for c in mult_cols]
        ax.plot(period_labels, vals, marker='o', lw=2.2, ms=6, color=colors[i], zorder=3)
        lv = vals[-1]
        if lv is not None and i < len(t20):
            name = r.get('名称', f'#{i+1}')
            if lv > 2:
                ax.annotate(name, (4.9, lv), (5.2, lv), fontsize=8, color=colors[i],
                            fontweight='bold', fontproperties=_fp(8), va='center',
                            arrowprops=dict(arrowstyle='-', color=colors[i], lw=0.8))
            else:
                ax.annotate(name, (0.1, lv), (-0.8, lv), fontsize=8, color=colors[i],
                            fontweight='bold', fontproperties=_fp(8), va='center',
                            arrowprops=dict(arrowstyle='-', color=colors[i], lw=0.8))
    ax.axhline(y=1, c='gray', ls='--', alpha=0.4, lw=1)
    ax.axhline(y=2, c='orange', ls=':', alpha=0.4, lw=1)
    ax.set_yscale('log')
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1fx'))
    ax.set_xlabel('滚动周期', fontproperties=_fp(14))
    ax.set_ylabel('增长倍率（对数）', fontproperties=_fp(14))
    ax.set_title(title, fontproperties=_fp(18))
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-1.5, 6.8)
    cap = "图注：纵轴=对数坐标；虚线=1x基准，点线=2x翻倍；标签标于线末端"
    ax.text(0.5, -0.1, cap, fontsize=10, fontproperties=_fp(10),
            ha='center', va='top', transform=ax.transAxes, linespacing=1.6)
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def chart_heatmap(t20: pd.DataFrame, mult_cols: list, period_labels: list,
                  title: str, save_path: str, vmax_cap: float = 15.0):
    """Chart 2: 热力图"""
    n = len(t20)
    hm = np.array([[r[c] if pd.notna(r[c]) else 0 for c in mult_cols] for _, r in t20.iterrows()])
    fig, ax = plt.subplots(figsize=(15, 10))
    vmax = min(hm.max(), vmax_cap)
    im = ax.imshow(hm, aspect='auto', cmap='RdYlGn', vmin=0, vmax=vmax)
    ax.set_xticks(range(len(period_labels)))
    ax.set_xticklabels(period_labels, fontproperties=_fp(13))
    ax.set_yticks(range(n))
    ax.set_yticklabels([r['名称'] for _, r in t20.iterrows()], fontproperties=_fp(11))
    for i in range(n):
        for j in range(len(mult_cols)):
            v = hm[i, j]
            if v > 0:
                ax.text(j, i, f'{v:.1f}x', ha='center', va='center', fontsize=8.5,
                        color='white' if v > vmax_cap * 0.4 else 'black', fontproperties=_fp(8))
    ax.set_xlabel('滚动周期', fontproperties=_fp(14))
    ax.set_title(title, fontproperties=_fp(18))
    cbar_ax = fig.add_axes([0.88, 0.16, 0.018, 0.76])
    plt.colorbar(im, cax=cbar_ax).set_label('倍率', fontproperties=_fp(11))
    ax.text(0.5, -0.08, "图注：绿=>高增长 黄=中间 红=<1x(萎缩)",
            fontsize=10, fontproperties=_fp(10), ha='center', va='top', transform=ax.transAxes)
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def chart_industry(pp: pd.DataFrame, title: str, save_path: str):
    """Chart 3: 行业平均增长"""
    ind = pp.groupby('行业').agg(avg=('分数', 'mean'), cnt=('代码', 'count')).sort_values('avg')
    fig, ax = plt.subplots(figsize=(14, 9))
    cmin, cmax = ind['avg'].min(), ind['avg'].max()
    bars_c = plt.cm.RdYlGn((ind['avg'] - cmin) / max(cmax - cmin, 0.01))
    ax.barh(range(len(ind)), ind['avg'], color=bars_c, edgecolor='white', height=0.6)
    for i, (idx, r) in enumerate(ind.iterrows()):
        ax.text(r['avg'] + 0.03, i, f"{r['avg']:.2f}pt ({int(r['cnt'])}只)",
                va='center', fontsize=9, fontproperties=_fp(9))
    ax.set_yticks(range(len(ind)))
    ax.set_yticklabels(ind.index, fontproperties=_fp(12))
    ax.axvline(x=1.0, color='red', ls='--', alpha=0.5)
    ax.set_xlabel('加权分数（线性递减）', fontproperties=_fp(13))
    ax.set_title(title, fontproperties=_fp(18))
    ax.grid(True, alpha=0.3, axis='x')
    ax.text(0.5, -0.12, "图注：颜色=红低绿高；括号内=入选数；红线=1.0基准",
            fontsize=10, fontproperties=_fp(10), ha='center', va='top', transform=ax.transAxes)
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def chart_boxplot(pp: pd.DataFrame, mult_cols: list, period_labels: list,
                  title: str, save_path: str):
    """Chart 4: 箱线图"""
    data = [pp[c].dropna().values for c in mult_cols]
    fig, ax = plt.subplots(figsize=(16, 12))
    try:
        bp = ax.boxplot(data, tick_labels=period_labels, patch_artist=True, showmeans=True,
                        meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
    except:
        bp = ax.boxplot(data, labels=period_labels, patch_artist=True, showmeans=True,
                        meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
    box_c = ['#4CAF50', '#8BC34A', '#FFC107', '#FF9800', '#FF5722', '#E91E63']
    for patch, c in zip(bp['boxes'], box_c[:len(period_labels)]):
        patch.set_facecolor(c); patch.set_alpha(0.65)
    for i, d in enumerate(data, 1):
        m, md = float(d.mean()), float(np.median(d))
        ax.annotate(f'μ={m:.2f}x', (i, m), (i+0.4, m+1.5), ha='center', fontsize=9,
                    arrowprops=dict(arrowstyle='->', color='red', lw=1.8), fontproperties=_fp(9))
        ax.annotate(f'M={md:.2f}x', (i, md), (i+0.4, md-1.8), ha='center', fontsize=8, color='blue',
                    arrowprops=dict(arrowstyle='->', color='blue', lw=1.5), fontproperties=_fp(8))
    ax.axhline(y=1, color='red', ls='--', alpha=0.5, lw=1.5)
    ax.set_xlabel('滚动周期', fontproperties=_fp(14))
    ax.set_ylabel('增长倍率', fontproperties=_fp(14))
    ax.set_title(title, fontproperties=_fp(18))
    ax.grid(True, alpha=0.3, axis='y')
    leg = [
        Line2D([0],[0], marker='D', color='w', markerfacecolor='red', markersize=8, label='均值(μ)'),
        Line2D([0],[0], color='#222', lw=2, label='中位数(M)'),
        mpatches.Patch(facecolor='#FFC107', alpha=0.65, label='中间50%'),
        Line2D([0],[0], color='#333', lw=1.5, label='正常范围'),
        Line2D([0],[0], marker='o', color='w', markerfacecolor='#666', markersize=5, label='异常值'),
    ]
    ax.legend(handles=leg, loc='upper right', fontsize=9, prop=_fp(9))
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def chart_sustainability(pp: pd.DataFrame, mult_cols: list, title: str, save_path: str):
    """Chart 5: 持续性散点图"""
    pp = pp.copy()
    pp['strong_count'] = sum((pp[c] > 2).astype(int) for c in mult_cols)
    fig, ax = plt.subplots(figsize=(18, 13))
    sc = ax.scatter(pp['strong_count'], pp['分数'], c=pp['波动'], s=pp['分数']*20,
                    cmap='viridis_r', alpha=0.7, edgecolors='white', linewidth=0.5, zorder=2)
    for _, r in pp.iterrows():
        ax.annotate(r['名称'], (r['strong_count'], r['分数']),
                    (r['strong_count']+0.08, r['分数']+0.08),
                    fontsize=6.5, fontproperties=_fp(6.5), alpha=0.85, zorder=3)
    ax.set_xlabel('增长>2x的周期数', fontproperties=_fp(14))
    ax.set_ylabel('加权分数', fontproperties=_fp(14))
    ax.set_title(title, fontproperties=_fp(18))
    ax.set_xticks(range(0, len(mult_cols)+1))
    ax.grid(True, alpha=0.3)
    cbar = plt.colorbar(sc, ax=ax, pad=0.01)
    cbar.set_label('增长波动', fontproperties=_fp(11))
    ax.text(0.5, -0.1, "图注：横轴=几期>2x；纵轴=加权分数；颜色=波动(暗=稳)",
            fontsize=10, fontproperties=_fp(10), ha='center', va='top', transform=ax.transAxes)
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def chart_dual_bar(price_t20, rev_t20, price_pp, rev_pp, title, save_path):
    """双维度横向对比柱状图"""
    all_top_names = list(dict.fromkeys(list(price_t20['名称']) + list(rev_t20['名称'])))
    fig, ax = plt.subplots(figsize=(16, 12))
    y_pos = np.arange(len(all_top_names))
    p_scores, r_scores = [], []
    for name in all_top_names:
        ps = price_pp[price_pp['名称']==name]['分数'].values
        rs = rev_pp[rev_pp['名称']==name]['分数'].values
        p_scores.append(ps[0] if len(ps) else 0)
        r_scores.append(rs[0] if len(rs) else 0)
    ax.barh(y_pos-0.2, p_scores, 0.35, label='股价分数', color='#2196F3', alpha=0.85)
    ax.barh(y_pos+0.2, r_scores, 0.35, label='营收分数', color='#FF9800', alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(all_top_names, fontproperties=_fp(11))
    ax.axvline(x=1.5, color='red', ls='--', alpha=0.4)
    ax.set_xlabel('加权分数', fontproperties=_fp(13))
    ax.set_title(title, fontproperties=_fp(18))
    ax.legend(fontsize=11, prop=_fp(11)); ax.grid(True, alpha=0.3, axis='x')
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def chart_dual_scatter(merged, title, save_path):
    """双维度散点图"""
    fig, ax = plt.subplots(figsize=(16, 12))
    colors_list = []
    for _, r in merged.iterrows():
        if r.get('双通过'): colors_list.append('#4CAF50')
        elif r.get('仅股价'): colors_list.append('#2196F3')
        elif r.get('仅营收'): colors_list.append('#FF9800')
        else: colors_list.append('#cccccc')
    ax.scatter(merged['股价分数'], merged['营收分数'], c=colors_list, s=40,
               alpha=0.7, edgecolors='white', linewidth=0.5)
    for _, r in merged.iterrows():
        cond = r.get('双通过', False) or r.get('股价分数', 0) > 3 or r.get('营收分数', 0) > 3
        if cond:
            ax.annotate(r['名称'], (r['股价分数'], r['营收分数']),
                        (r['股价分数']+0.15, r['营收分数']+0.15),
                        fontsize=6.5, fontproperties=_fp(6.5), alpha=0.85)
    ax.axhline(y=1.5, color='orange', ls='--', alpha=0.4)
    ax.axvline(x=1.5, color='orange', ls='--', alpha=0.4)
    ax.set_xlabel('股价分数', fontproperties=_fp(14))
    ax.set_ylabel('营收分数', fontproperties=_fp(14))
    ax.set_title(title, fontproperties=_fp(18)); ax.grid(True, alpha=0.3)
    from matplotlib.patches import Patch
    leg = [
        Patch(facecolor='#4CAF50', alpha=0.7, label='双维度通过'),
        Patch(facecolor='#2196F3', alpha=0.7, label='仅股价通过'),
        Patch(facecolor='#FF9800', alpha=0.7, label='仅营收通过'),
        Patch(facecolor='#ccc', alpha=0.7, label='均未通过'),
    ]
    ax.legend(handles=leg, fontsize=10, prop=_fp(10))
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def chart_dual_trend(elite_df, price_df, rev_df, price_mc, rev_mc, period_labels,
                     title_prefix, save_path):
    """双维度精选趋势（上=股价 下=营收）"""
    fig, axes = plt.subplots(2, 1, figsize=(20, 16))
    for idx, (df_src, mc, title, ax) in enumerate([
        (price_df, price_mc, '股价增长趋势', axes[0]),
        (rev_df, rev_mc, '营收增长趋势', axes[1]),
    ]):
        colors = plt.cm.tab20(np.linspace(0, 1, len(elite_df)))
        for i, (_, r) in enumerate(elite_df.iterrows()):
            vals = [df_src[df_src['代码']==r['代码']][c].values[0] for c in mc]
            ax.plot(period_labels, vals, marker='o', lw=2.2, ms=6, color=colors[i], zorder=3)
            ax.annotate(r['名称'], (4.9, vals[-1]), (5.2, vals[-1]), fontsize=7.5, color=colors[i],
                       fontweight='bold', fontproperties=_fp(7.5), va='center',
                       arrowprops=dict(arrowstyle='-', color=colors[i], lw=0.8))
        ax.axhline(y=1, c='gray', ls='--', alpha=0.4, lw=1)
        ax.axhline(y=2, c='orange', ls=':', alpha=0.4, lw=1)
        ax.set_yscale('log')
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1fx'))
        ax.set_ylabel('增长倍率（对数）', fontproperties=_fp(13))
        ax.set_title(f'{title_prefix} · {title}', fontproperties=_fp(16))
        ax.grid(True, alpha=0.3); ax.set_xlim(-1.5, 6.8)
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
