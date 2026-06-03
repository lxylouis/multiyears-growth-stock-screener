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

# 默认：5年×3个窗口（3期）
python3 run.py --index sp500      # 标普500全部
python3 run.py --index csi300     # 沪深300全部
python3 run.py --index hsi        # 恒生指数全部

# 自定义窗口
python3 run.py --index sp500 --window-years 5 --num-windows 5

# 自定义基准
python3 run.py --index sp500 --window-years 5 --num-windows 5 \
  --price-base-yyyymm 2026-03 --revenue-base-yyyy 2025

# 分步运行
python3 run.py --index sp500 --mode price        # 仅股价
python3 run.py --index sp500 --mode revenue      # 仅营收
python3 run.py --index sp500 --mode dual         # 仅双维度
```

## 配置架构

整个 Pipeline 由 YAML 配置驱动。每个指数一个配置文件（`configs/<指数>.yaml`），主要节：

| 配置节 | 说明 | 默认值 |
|:------|:----|:-----:|
| `defaults` | 窗口参数：`window_years`、`num_windows` | 5年, 3期 |
| `screening` | 筛选阈值：`cond_a_min`（条件A）、`cond_b_threshold`（条件B） | 0.9, 2.0 |
| `periods` | 时间窗口硬编码（有 defaults 时自动覆盖） | — |
| `index` | 指数名称、代码、市场类型（cn/hk/us） | — |
| `stock_codes` | 成分股获取方式（index/csv/hardcoded） | — |

**配置优先顺序**：CLI 参数 > YAML defaults > YAML periods 硬编码

> 文档和代码注释中**使用配置项变量名（如 `cond_b_threshold`），而非硬编码数字**。默认值统一在表格中注明。这一惯例适用于本项目所有配置文档。

## CLI 参数

| 参数 | 默认值 | 格式 | 说明 |
|:---|---:|:---|:---|
| `--index` | 必填 | 名称 | 指数名（sp500 / csi300 / hsi，对应 configs/） |
| `--mode` | `all` | 选项 | all=全部, price=仅股价, revenue=仅营收, dual=仅双维度 |
| `--window-years` | 5 | 年 | 每个窗口跨几年 |
| `--num-windows` | 3 | 个 | 从基准年往过去推几个窗口（YAML defaults 优先，默认3期） |
| `--price-base-yyyymm` | 今年3月 | `YYYY-MM` | 股价基准年月 |
| `--revenue-base-yyyy` | 因市场而异 | `YYYY` | 营收基准年 |

**时间窗口推算**：当 YAML 的 `defaults` 节配置了 `window_years` 或 `num_windows`，无需 CLI 参数即可自动生成 periods。示例：

```bash
# 默认从 YAML 读取：5年×3期 → 2026/2021, 2025/2020, 2024/2019
python3 run.py --index csi300

# 自定义覆盖
python3 run.py --index sp500 --window-years 5 --num-windows 5
```

## 筛选规则

**保留条件** = (所有窗口倍率 ≥ `cond_a_min`) ∪ (最新窗口倍率 > `cond_b_threshold`)

| 参数 | 默认值 | 含义 |
|:---|---:|:---|
| `cond_a_min` | **0.9** | 条件A：所有窗口倍率不低于此值（防大幅衰退） |
| `cond_b_threshold` | **2.0** | 条件B：最新窗口倍率超过此值（5年翻倍 ≈ 14.87% CAGR） |

两个条件取并集（OR），满足其一即保留：
- 条件A → 长期稳健型，各期都没跌过
- 条件B → 近5年强势型，哪怕以前跌过但最近翻倍了也留

> 阈值通过各指数 YAML 配置的 `screening` 节设置，可逐个指数独立调整。

**默认窗口**：5年×3期（最近3个5年窗口）

**评分**：线性递减权重 1:2:3（越近权重越高，归一化后为 [0.167, 0.333, 0.5]）

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

## 为什么不同市场用不同的成分股获取方式

AKShare 对不同市场的接口覆盖度不同：

| 市场 | 方式 | 原因 |
|:---|---:|:---|
| A股（csi300） | 动态 API（`index_stock_cons`） | AKShare 原生提供A股指数成分股接口，自动同步 |
| 美股（sp500） | CSV 文件（SlickCharts） | AKShare **没有**标普500成分股接口。业界惯例从 SlickCharts 导出 CSV 维护 |
| 港股（hsi） | 硬编码列表 | AKShare **没有**恒指成分股接口。手动维护当前 93 只 |

> **重要**：这不是设计偏好。新增指数时，先确认 AKShare 是否有该指数成分股接口。有则用 `type: index`，没有则选 CSV 或硬编码。详见 `references/data-sources.md`。

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
9. **参数迁移必杀技**：做全局参数默认值迁移（如 5 期→3 期、num_windows 变更等）时，单模式 grep 必漏。必须用**多模式组合 grep** 全面捕获所有可能的写法形态：
   ```bash
   # 必查模式清单
   grep -rn '\b6期\b\|第6期\|6 期\|6个窗口\|6个5年\|num_windows.*6\b\|num_windows=6\b\|--num-windows 6\b' .
   # 再加一轮：大段文本中的示例代码（YAML块、docstring、代码注释）人工检查
   grep -n '2021,2016\|2020,2015\|21/16\|20/15\|6期\b' README.md run.py
   ```
   然后逐文件打开README和run.py，目视扫描"调整方法"和"示例"段落中的代码块。代码块中的示例值不受 grep 约束（纯字符串）。用户对"漏扫"容忍度极低——被指出一次后必须**全仓库多模式+目视双重校验**，确保零残留。

10. **文档"为什么"前置**：当用户问"为什么某做法"且你做出解释后，**必须同步更新项目文档/脚本注释**把原因写明白。口头解释+不做文档=用户回头问"你写清楚了没"。具体做法：README表格加原因列、代码函数加docstring说明动机。

12. **港股API不稳定与后备方案**：`ak.stock_hk_spot()` 在腾讯云GFW环境下经常返回空数据（`Length mismatch` 错误）。`lib/data_hk.py` 中的 `fetch_hk_names()` 已实现自动降级——失败时回退到 `HSI_NAMES` 硬编码字典。如果添加新港股指数，需要在 `HSI_NAMES` 中补充对应名称。也可直接运行（仅影响名称显示不报错）。

13. **阈值可配化 & 文档约定**：`filter_by_growth()` 接受 `cond_a_min` 和 `cond_b_threshold` 两个参数（取代旧版单一 `latest_threshold`）。阈值从 YAML `screening` 节读取，默认 0.9 和 2.0。**文档和代码注释中必须使用变量名而非具体数字**，默认值统一在表格中注明。这是本项目的文档约定——读者看到的是规则结构，默认值在另一处独立呈现。

14. **双维度左连接遗漏**：dual 分析从 `price_df` 做 `left join rev_df`，因此**只有同时有股价数据的股票才进入双维度分析**。营收筛选通过的股票如果缺少完整5年股价历史（如科创板/创业板次新股上市不足5年），会被静默排除。这不是bug，但解读双维度通过数时需要了解——营收通过236只 ≠ 双维度营收侧182只。详见 `references/dual-analysis-pitfalls.md`。

15. **阈值调整后必跑三市对比**：修改筛选规则后必须跑完所有三个指数（sp500/csi300/hsi）并做新旧对比，因为不同市场的通过率响应差异很大（美股强→降幅小，港股弱→降幅大）。仅跑一个指数无法判断新阈值是否合理。

16. **全覆盖检查——改配置必改所有文件类型**：做阈值、窗口等参数的修改时，必须检查并更新以下所有文件类型——`.py`（含函数签名、docstring）、`.md`（含SKILL.md和README.md）、`.yaml`（含注释描述和数组值）、`templates/`（模板必须同步）。用 `grep -rn` 多模式组合搜索确保零残留，然后逐文件目视检查代码块中的示例值（grep 搜不到纯字符串示例）。

15. **Git多作者署名**：Agent和人协作的项目，committer应为人类，Co-authored-by标注Agent。当Repo首次推送后用户要求修正时，全部commit squash为一个重设作者：
    ```bash
    # 首次设置
    git config user.name "用户名"
    git config user.email "邮箱"
    
    # 合并已有commit + 重写作者
    ROOT=$(git rev-list --max-parents=0 HEAD)
    git reset --soft "$ROOT"
    git commit --amend --author="用户名 <邮箱>" \\
      -m "feat: 描述" \\
      -m "Co-authored-by: Hermes <hermes@hermes-agent.ai>"
    
    # 新仓库可接受force push
    git push --force-with-lease
    ```
