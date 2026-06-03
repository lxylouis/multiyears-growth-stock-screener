"""
multiyears-growth-stock-screener/lib/compute.py
共享计算逻辑：增长评分、筛选规则、行业归类
"""
import numpy as np
import pandas as pd


def industry_hk(name: str) -> str:
    """港股行业归类"""
    for kw, ind in [
        ('银行','银行'),('证券','非银'),('保险','非银'),
        ('酒','白酒'),('饮料','饮料食品'),('食品','饮料食品'),
        ('医药','医药'),('药','医药'),('医疗','医药'),
        ('科技','科技'),('信息','科技'),('软件','科技'),('互联','科技'),
        ('通信','科技'),('电子','科技'),
        ('煤','煤炭'),('能源','能源'),('电力','电力'),('电','电力'),
        ('汽车','汽车'),('车','汽车'),
        ('地产','地产'),('置业','地产'),('基地','地产'),('置地','地产'),
        ('黄金','有色'),('有色','有色'),('矿业','有色'),
        ('航空','交通'),('海运','交通'),('港口','交通'),('铁路','交通'),
        ('消费','消费'),('啤酒','消费'),('食品','消费'),('奶','消费'),
        ('石油','石油'),('化工','化工'),('化学','化工'),
        ('基建','基建'),('建筑','基建'),('中铁','基建'),
    ]:
        if kw in name:
            return ind
    return '综合/其他'


def industry_us(name: str) -> str:
    """美股行业归类（基于英文名称关键字）"""
    name_lower = name.lower()
    for kw, ind in [
        ('bank', '银行'), ('bancorp', '银行'), ('financial', '非银'),
        ('insurance', '保险'), ('ins', '保险'), ('reinsurance', '保险'),
        ('broker', '非银'), ('asset management', '非银'), ('capital', '非银'),
        ('investment', '非银'), ('holdings', '综合/其他'),
        ('pharma', '医药'), ('biopharma', '医药'), ('biotech', '医药'),
        ('health', '医药'), ('medical', '医药'), ('diagnostic', '医药'),
        ('drug', '医药'), ('therapeutics', '医药'),
        ('technology', '科技'), ('software', '科技'), ('systems', '科技'),
        ('solutions', '科技'), ('digital', '科技'), ('data', '科技'),
        ('semiconductor', '科技'), ('chip', '科技'), ('electronic', '科技'),
        ('network', '科技'), ('computing', '科技'), ('cloud', '科技'),
        ('telecom', '科技'), ('communication', '科技'),
        ('oil', '石油'), ('gas', '石油'), ('energy', '能源'),
        ('coal', '煤炭'), ('mining', '有色'), ('mineral', '有色'),
        ('gold', '有色'), ('copper', '有色'), ('steel', '钢铁'),
        ('aluminum', '有色'), ('metal', '钢铁'),
        ('auto', '汽车'), ('motor', '汽车'), ('car', '汽车'),
        ('electric vehicle', '汽车'), ('tire', '汽车'),
        ('retail', '消费'), ('wholesale', '消费'), ('store', '消费'),
        ('supermarket', '消费'), ('grocery', '消费'), ('food', '消费'),
        ('beverage', '消费'), ('restaurant', '消费'), ('fast', '消费'),
        ('consumer', '消费'), ('apparel', '消费'), ('clothing', '消费'),
        ('footwear', '消费'), ('luxury', '消费'), ('cosmetic', '消费'),
        ('airline', '交通'), ('air', '交通'), ('airport', '交通'),
        ('rail', '交通'), ('railroad', '交通'), ('logistics', '交通'),
        ('shipping', '交通'), ('freight', '交通'), ('delivery', '交通'),
        ('real estate', '地产'), ('reality', '地产'), ('property', '地产'),
        ('home', '地产'), ('residential', '地产'), ('mortgage', '地产'),
        ('electric', '电力'), ('power', '电力'), ('utility', '电力'),
        ('chemical', '化工'), ('industrial', '工业'),
        ('manufacturing', '工业'), ('machinery', '工业'),
        ('defense', '工业'), ('aerospace', '工业'), ('engineering', '工业'),
        ('construction', '基建'), ('building', '基建'),
        ('internet', '科技'), ('social media', '科技'), ('search', '科技'),
        ('e-commerce', '科技'), ('payment', '科技'), ('fintech', '科技'),
    ]:
        if kw in name_lower:
            return ind
    # Try Chinese keywords too (some US stocks have Chinese names in AKShare)
    for kw, ind in [
        ('科技', '科技'), ('银行', '银行'), ('保险', '保险'),
        ('医药', '医药'), ('能源', '能源'), ('石油', '石油'),
        ('消费', '消费'), ('汽车', '汽车'), ('地产', '地产'),
        ('电力', '电力'), ('化工', '化工'),
    ]:
        if kw in name:
            return ind
    return '综合/其他'


def compute_scores(df: pd.DataFrame, mult_cols: list, weights: list) -> pd.DataFrame:
    """
    计算平均倍率、加权分数、波动率
    df: 包含 mult_cols 列的 DataFrame
    mult_cols: 倍率列名列表
    weights: 对应权重列表（归一化）
    """
    df = df.copy()
    for c in mult_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['平均倍率'] = df[mult_cols].mean(axis=1)
    df['分数'] = sum(df[c] * w for c, w in zip(mult_cols, weights))
    df['波动'] = df[mult_cols].std(axis=1)
    return df


def filter_by_growth(df: pd.DataFrame, mult_cols: list,
                     cond_a_min: float = 0.9,
                     cond_b_threshold: float = 2.0) -> pd.DataFrame:
    """
    增长筛选规则：
      保留条件 = (所有周期倍率 ≥ cond_a_min) ∪ (最新周期倍率 > cond_b_threshold)

    逻辑说明：
      - 条件A：过去每一期（从最早到最新）增长倍率均不低于 cond_a_min（即没有大幅衰退）
      - 条件B：最新一期增长倍率超过 cond_b_threshold（统一 2.0x，对应 14.87% CAGR）
      - 两个条件满足其一即保留，取并集

    参数:
      cond_a_min: 条件A阈值，所有窗口倍率均不低于此值（默认 0.9，防大幅衰退）
      cond_b_threshold: 条件B阈值，最新窗口倍率超过此值（默认 2.0x，5年翻倍 ≈ 14.87% CAGR）
    """
    cond_a = df.copy()
    for c in mult_cols:
        cond_a = cond_a[~(cond_a[c] < cond_a_min)]
    cond_b = df[df[mult_cols[-1]] > cond_b_threshold]
    result = pd.concat([cond_a, cond_b]).drop_duplicates(subset=['代码'])
    result = result.sort_values('分数', ascending=False).reset_index(drop=True)
    result['年均化'] = result['平均倍率'].apply(
        lambda x: round((x ** (1 / len(mult_cols)) - 1) * 100, 1)
    )
    return result


def make_weights(n_periods: int) -> list:
    """生成线性递减权重 1:2:3:...:n（越近权重越高）"""
    w = list(range(1, n_periods + 1))
    return [x / sum(w) for x in w]


def period_mult_cols(periods: list) -> list:
    """从periods [(e1,s1),...] 生成倍率列名"""
    return [f'{e}/{s}倍率' for e, s in periods]


def calc_mults_for_stock(closes: dict, periods: list) -> dict:
    """
    从 {year: price} 字典和periods计算每期倍率
    returns: {f'{e}/{s}倍率': float, ...}
    """
    result = {}
    for e, s in periods:
        se, ss = str(e), str(s)
        if se in closes and ss in closes and closes[ss] > 0:
            result[f'{e}/{s}倍率'] = round(closes[se] / closes[ss], 4)
    return result
