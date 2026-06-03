# multiyears-growth-stock-screener · 多年增长选股工具

统一Pipeline，对任意指数逐只分析成分股的历史增长表现，输出结构化的 **DOCX 分析报告**。

**核心逻辑**：对指数内每只股票，计算 5 年滚动增长倍率，筛选出持续成长的优质标的，结合股价与营收双维度交叉验证。

---

## 数据源

| 市场 | 代码 | 股价数据 | 营收数据 |
|:---|:---|---:|:---:|
| **A 股** | `csi300` | AKShare `stock_zh_a_hist`（前复权） | AKShare `stock_financial_abstract`（年报营业总收入） |
| **港股** | `hsi` | AKShare `stock_hk_hist`（日线） | AKShare `stock_financial_hk_analysis_indicator`（年报营收） |
| **美股** | `sp500` | AKShare `stock_us_daily`（自实现前复权修正→拆股检测） | AKShare `stock_financial_us_report_em`（利润表营业总收入） |

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 默认分析（从YAML配置读取时间窗口）
python3 run.py --index sp500      # 标普500全部（股价+营收+双维度）
python3 run.py --index csi300     # 沪深300全部
python3 run.py --index hsi        # 恒生指数全部

# 3. 自定义时间窗口（自动推算年份）
python3 run.py --index sp500 --window-years 5 --num-windows 5
python3 run.py --index sp500 --window-years 3 --num-windows 4

# 4. 自定义基准年
python3 run.py --index sp500 --window-years 5 --num-windows 3 \
  --price-base-yyyymm 2026-03 --revenue-base-yyyy 2025

# 5. 分步运行
python3 run.py --index sp500 --mode price    # 仅股价分析
python3 run.py --index sp500 --mode revenue  # 仅营收分析
python3 run.py --index sp500 --mode dual     # 仅双维度（需先跑 price + revenue）
```

---

## CLI 参数

| 参数 | 默认值 | 说明 |
|:---|---:|:---|
| `--index` | 必填 | 指数名（sp500/csi300/hsi，对应 configs/&lt;名&gt;.yaml） |
| `--mode` | `all` | 运行模式：all/price/revenue/dual |
| `--window-years` | 从YAML读取（默认5） | 每个窗口跨几年（如5=5年增长倍率，3=3年） |
| `--num-windows` | 从YAML读取（默认3） | 从基准年往过去推几个窗口（如3=3个5年窗口） |
| `--price-base-yyyymm` | YYYY-MM | 股价基准年月（如 `2026-03`），默认今年3月 |
| `--revenue-base-yyyy` | 年份 | 营收基准年（如 `2026`），默认A股=今年，美股/港股=去年 |

> **时间窗口自动推算示例**：`--window-years 5 --num-windows 3 --price-base-yyyymm 2026-03`
> → 自动生成 3 个窗口：2026/2021, 2025/2020, 2024/2019（最近 5 年翻倍 × 最近 3 期）

---

## 时间窗口说明

### 股价（Price）

**基准**：每年 **3 月最后一个交易日**的收盘价。

**期数**：3 期，每期跨 5 年（默认值，可通过 YAML 或 CLI 调整）。

```text
 2026/3末  ÷  2021/3末  =  第1期 增长倍率  ← 最新
 2025/3末  ÷  2020/3末  =  第2期 增长倍率
 2024/3末  ÷  2019/3末  =  第3期 增长倍率  ← 最远
```

为什么选 3 月？A 股年报在次年 4 月底前完成披露，3 月末是市场对上年财报充分消化后的"后年报价格"。对港股/美股也统一为 3 月末，保持跨市场可比。

**美股前复权**：美股原始价格不含复权。本工具对每次拆股（单日跌幅 >40% 且前后价格比 >2 倍）自动检测并以拆股点为分界，**逆向修正之前所有历史价格**，使全部历史价格统一到最新股本口径。

### 营收（Revenue）

**基准**：**最新完整年报**的营业总收入（自然年）。

**期数**：3 期，每期跨 5 年（默认值）。

```text
 2025年报  ÷  2020年报  =  第1期 营收增长倍率  ← 最新
 2024年报  ÷  2019年报  =  第2期 营收增长倍率
 2023年报  ÷  2018年报  =  第3期 营收增长倍率  ← 最远
```

### 调整方法

编辑 `configs/<指数>.yaml` 中的 `defaults` 和 `periods` 字段即可：

```yaml
# 时间窗口
defaults:
  window_years: 5          # 每个窗口跨 5 年
  num_windows: 3           # 3 个窗口

# 筛选阈值（可选，不填则使用默认值 0.9 和 2.0）
screening:
  cond_a_min: 0.9
  cond_b_threshold: 2.0

# 显式时间窗口（如不填，由 defaults 自动生成）
periods:
  price: [[2024,2019],[2025,2020],[2026,2021]]
  revenue: [[2023,2018],[2024,2019],[2025,2020]]
  labels: ['24/19','25/20','26/21']
```

每对 `[终点年份, 起点年份]` 定义一期 5 年滚动增长倍率。不填 `periods` 时自动从 `defaults` 推算。`screening` 节控制保留条件的两个阈值（条件A = 全期≥ cond_a_min，条件B = 最新期 > cond_b_threshold）。

---

## 指数配置

### 内置指数

| 名称 | index 参数 | 成分股数 | 来源 | 原因 |
|:---|:---|:---|---:|:---|
| 标普 500 | `sp500` | 503 只 | SlickCharts CSV | AKShare 无标普500成分股接口，需从第三方网站导出为 CSV 维护 |
| 沪深 300 | `csi300` | 300 只 | AKShare `index_stock_cons` | AKShare 原生支持获取A股指数成分股，自动同步 |
| 恒生指数 | `hsi` | 93 只 | 硬编码列表 | AKShare 无恒指成分股接口，手动维护当前成分股列表 |

> **为什么三个市场来源不同？** 取决于 AKShare 对不同交易所的接口覆盖度。A 股有 `index_stock_cons()` 实时查询，标普 500 和恒指均无对应接口——前者用 CSV 文件定期从 SlickCharts 更新，后者直接硬编码成分股代码。成本最低、最稳定的做法，不用每次运行时依赖外部网页。

### 添加新指数

1. 在 `configs/` 下创建 `<name>.yaml`：
   - 市场类型：`cn`（A 股）、`hk`（港股）、`us`（美股）
   - 股票列表来源：`csv`（文件）、`index`（AKShare 指数代码）、`hardcoded`（列表）
2. 运行 `python3 run.py --index <name>`

示例——创业板指：

```yaml
index:
  name: "创业板指"
  code: "399006"
  market: "cn"
stock_codes:
  type: "index"
  source_func: "index_stock_cons"
  source_arg: "399006"
periods: ...  # 复制自现有配置
```

---

## 筛选规则

### 保留条件

对每只股票，保留条件为以下两条件的**并集**：

| 条件 | 规则 | 含义 | 默认值 |
|:---|:---|---:|---:|
| **A** | 所有窗口倍率 **均 ≥ `cond_a_min`** | 历史上没有过大幅衰退 | **0.9** |
| **B** | 最新窗口倍率 **> `cond_b_threshold`** | 最近 5 年增长翻倍（14.87% CAGR），跑赢大盘 | **2.0** |

**为什么是这个规则？**
- 条件 A 过滤掉了"曾经好过但后来不行了"的标的
- 条件 B 要求**最近 5 年持续强劲**，年均 14.87% 以上——高于大多数市场的长期平均回报

**默认窗口：5年×3期**（最近 3 个 5 年窗口，权重线性递减 1:2:3）
- 两者并集 = 持续成长型 + 新晋成长型

> 阈值可通过各指数 YAML 配置中 `screening` 节的 `cond_a_min` 和 `cond_b_threshold` 调整，默认值分别为 0.9 和 2.0。

### 评分方法

**线性递减权重**：越近的周期权重越高。

对 n 期，权重为 `1:2:3:...:n`，归一化后求和。

```python
# 3期权重示例（默认）
weights = [1, 2, 3]  →  归一化为 [0.167, 0.333, 0.5]
```

**分数 = Σ（每期倍率 × 该期权重）**，满分不限，越高越好。

**年均化增长率**：`平均倍率^(1/n) - 1`，反映跨周期的年复合增长率。

---

## 输出

### 三份报告

每次运行 `--mode all` 会生成三份 DOCX 报告：

| 报告 | 文件名 | 内容 |
|:---|---:|:---|
| **股价报告** | `{指数}_股价增长分析报告.docx` | 股价筛选结果 + TOP20 排名 + 5 张图表 |
| **营收报告** | `{指数}_营收增长分析报告.docx` | 营收筛选结果 + TOP20 排名 + 5 张图表 |
| **双维度报告** | `{指数}_双维度增长分析报告.docx` | 股价 vs 营收交叉验证 + 精选标的 |

### 图表集

每份报告包含五张标准图表：

1. **增长趋势图** — TOP20 各期倍率走势线图
2. **热力图** — TOP20 各期倍率热度呈现
3. **行业分析** — 各行业的平均增长对比
4. **箱线图** — 各期倍率的分布情况
5. **持续性 vs 分数** — 增长稳定性和绝对分数的关系

双维度报告额外包含：对比柱状图、散点图、精选趋势图。

---

## 项目结构

```
multiyears-growth-stock-screener/
├── run.py                 # 统一入口
├── requirements.txt       # 依赖
├── LICENSE                # MIT
├── .gitignore
├── configs/
│   ├── sp500.yaml         # 标普500配置
│   ├── csi300.yaml        # 沪深300配置
│   ├── hsi.yaml           # 恒生指数配置
│   └── sp500_constituents.csv  # 成分股列表（美股）
└── lib/
    ├── compute.py         # 评分逻辑、筛选规则、行业归类
    ├── charts.py          # 图表生成（matplotlib）
    ├── report.py          # DOCX 报告生成
    ├── data_cn.py         # A 股数据采集
    ├── data_hk.py         # 港股数据采集
    └── data_us.py         # 美股数据采集（含拆股前复权修正）
```

---

## 依赖

- `akshare` — 金融数据接口（A 股/港股/美股行情和财报）
- `pandas`, `numpy` — 数据处理
- `python-docx` — DOCX 报告生成
- `matplotlib` — 图表绘制
- `openpyxl` — Excel 支持（AKShare 间接依赖）
- `pyyaml` — YAML 配置读取

全部见 `requirements.txt`。

---

## License

MIT
