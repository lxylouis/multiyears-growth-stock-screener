---
name: multiyears-growth-stock-screener
description: 多年增长选股器 — 指数成分股×年×倍率选股工具。对任意指数（标普500/沪深300/恒生指数）逐只分析股价+营收的X年滚动增长，输出DOCX报告
---

# 多年增长选股器 MultiYears Growth Stock Screener

指数成分股 **×年×倍率** 选股工具。以巴菲特"复利机器"为思想内核——寻找那些能够持续×年翻×倍的优质标的。

## 触发条件

以下关键词自动加载本 skill：
- 股票分析、选股、指数选股
- **复利、倍率、×年×倍**、长效增长
- 标普500、沪深300、恒生指数、sp500、csi300、hsi
- 股价筛选、营收筛选、双维度
- "跑一下" + 指数名

## 项目路径

```
~/.hermes/skills/multiyears-growth-stock-screener/
```

## 用法

```bash
cd ~/.hermes/skills/multiyears-growth-stock-screener
source ~/.hermes/hermes-agent/venv/bin/activate

# 默认：5年×5个窗口
python3 run.py --index sp500      # 标普500全部
python3 run.py --index csi300     # 沪深300全部
python3 run.py --index hsi        # 恒生指数全部

# 自定义：3年×4个窗口
python3 run.py --index sp500 --window-years 3 --num-windows 4

# 自定义基准
python3 run.py --index sp500 --window-years 5 --num-windows 5 \
  --price-base-yyyymm 2026-03 --revenue-base-yyyy 2025

# 分步运行
python3 run.py --index sp500 --mode price        # 仅股价
python3 run.py --index sp500 --mode revenue      # 仅营收
python3 run.py --index sp500 --mode dual         # 仅双维度
```

## CLI 参数

| 参数 | 默认值 | 格式 | 说明 |
|:---|---:|:---|:---|
| `--index` | 必填 | 名称 | 指数名（sp500 / csi300 / hsi，对应 configs/） |
| `--mode` | `all` | 选项 | all=全部, price=仅股价, revenue=仅营收, dual=仅双维度 |
| `--window-years` | 5 | 年 | 每个窗口跨几年 |
| `--num-windows` | 5 | 个 | 从基准年往过去推几个窗口 |
| `--price-base-yyyymm` | 今年3月 | `YYYY-MM` | 股价基准年月 |
| `--revenue-base-yyyy` | 因市场而异 | `YYYY` | 营收基准年 |

**时间窗口推算示例**：`--window-years 5 --num-windows 5 --price-base-yyyymm 2026-03`
→ 自动生成：2026/2021, 2025/2020, 2024/2019, 2023/2018, 2022/2017

## 筛选规则

**保留条件** = (所有窗口倍率 ≥ 0.9) ∪ (最新窗口倍率 > 1.5)

- 条件A：每一个×年窗口增长倍率均不低于 0.9（没有大幅衰退）
- 条件B：最新一个窗口倍率超过 1.5（最近×年增长强劲）

**评分**：线性递减权重 1:2:3:...:n（越近权重越高）

**年化增长率**：平均倍率^1/n - 1

## 输出

三份 DOCX 报告至 `~/.hermes/stock_cache/<指数>/`：

| 报告 | 内容 |
|:---|---:|
| 股价增长报告 | TOP20排名 + 5图表（趋势/热力/行业/箱线/持续性） |
| 营收增长报告 | TOP20排名 + 5图表 |
| 双维度报告 | 股价×营收交叉验证 + 精选标的 |

## 项目结构

```
~/.hermes/skills/multiyears-growth-stock-screener/
├── SKILL.md              ← Agent 指令书（本文件）
├── run.py                ← 统一入口
├── README.md             ← GitHub 项目文档
├── requirements.txt      ← 依赖声明
├── LICENSE               ← MIT
├── .gitignore
├── configs/
│   ├── sp500.yaml        ← 标普500配置（503只）
│   ├── csi300.yaml       ← 沪深300配置（300只）
│   ├── hsi.yaml          ← 恒生指数配置（93只）
│   └── sp500_constituents.csv
└── lib/
    ├── compute.py        ← 评分 & 筛选规则
    ├── charts.py         ← 7种图表（matplotlib）
    ├── report.py         ← DOCX 报告生成
    ├── data_cn.py        ← A股数据
    ├── data_hk.py        ← 港股数据
    └── data_us.py        ← 美股数据（含拆股复权修正）
```

## 数据源

详细数据源说明（API函数、复权策略、缓存管理、已知局限）见 `references/data-sources.md`

| 市场 | 股价 | 营收 |
|:---|---:|:---:|
| A股 | AKShare `stock_zh_a_hist`（前复权） | AKShare `stock_financial_abstract` |
| 港股 | AKShare `stock_hk_hist` | AKShare `stock_financial_hk_report_em` |
| 美股 | AKShare `stock_us_daily` + 自实现前复权 | AKShare `stock_financial_us_report_em` |

## 新增指数

1. 参考 `templates/new-index-config.yaml` 在 `configs/` 下创建 `<名>.yaml`
2. 运行 `python3 run.py --index <名>`

市场类型决定数据加载路径：`cn`=A股（AKShare指数接口），`hk`=港股，`us`=美股

## 参数命名约定

CLI 参数名末尾附带了可接受的**格式单位**，使用者看到参数名就知道该传什么值：
- `yyyymm` → 格式 `YYYY-MM`（年月）
- `yyyy` → 格式 `YYYY`（年份）
- `years` → 整数（年数）
- `windows` → 整数（窗口个数）

这是本项目的设计惯例，后续增加新参数时遵循同一原则。

## 注意事项

1. **缓存**：股价缓存 7 天，强制刷新则删 `~/.hermes/stock_cache/<指数>/march_closes.json`
2. **美股前复权**：自实现拆股检测+逆向修正，确保历史价格统一到最新股本口径
3. **GE 分拆**：标普500中 GE 因 2023 年分拆导致倍率虚高，需单独说明
4. **营收期数差异**：美股/港股最新年报通常到去年（慢于A股），双维度自动对齐较短期数
5. **新增指数**：在 configs/ 下创建 `<名>.yaml` 即可，参考 csi300.yaml 格式
6. **报告大表**：全量排名限 TOP100，超限会导致 python-docx 生成卡死
8. **子代理访问保护**：当通过 `delegate_task` 运行本 pipeline 时，必须在 context 中加入 `CONSTRAINT: Do NOT modify any .py, .yaml, .csv, .md, or .json files. Only run the command and report output.` 否则子代理可能擅自修改配置和核心逻辑文件。
9. **参数迁移必杀技**：做全局参数默认值迁移（如 6 期→5 期）时，单模式 grep 必漏。必须用**多模式组合 grep** 全面捕获所有可能的写法形态：
   ```bash
   # 必查模式清单
   grep -rn '\b6期\b\|第6期\|6 期\|6个窗口\|6个5年\|num_windows.*6\b\|num_windows=6\b\|--num-windows 6\b' .
   # 再加一轮：大段文本中的示例代码（YAML块、docstring、代码注释）人工检查
   grep -n '2021,2016\|2020,2015\|21/16\|20/15\|6期\b' README.md run.py
   ```
   然后逐文件打开README和run.py，目视扫描"调整方法"和"示例"段落中的代码块。代码块中的示例值不受 grep 约束（纯字符串）。用户对"漏扫"容忍度极低——被指出一次后必须**全仓库多模式+目视双重校验**，确保零残留。
