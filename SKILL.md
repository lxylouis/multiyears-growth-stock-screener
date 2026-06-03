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

# 默认：{window_years=3} × {num_windows=5}
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
| `defaults` | 窗口参数：`window_years`、`num_windows` | window_years=3, num_windows=5 |
| `screening` | 筛选阈值：`cond_a_min`（条件A）、`cond_b_threshold`（条件B） | cond_a_min=1.3, cond_b_threshold=1.5 |
| `periods` | 时间窗口硬编码（有 defaults 时自动覆盖） | — |
| `index` | 指数名称、代码、市场类型（cn/hk/us） | — |
| `stock_codes` | 成分股获取方式（index/csv/hardcoded） | — |

**配置优先顺序**：CLI 参数 > YAML defaults > YAML periods 硬编码

> 文档和代码注释中**使用配置项变量名（如 `cond_b_threshold`），而非硬编码数字**。默认值统一在表格中注明。这一惯例适用于本项目所有配置文档。

## 并集筛选的行为陷阱

本筛选器规则为 **A ∪ B**（OR 并集）。实测发现一个重要行为特征：

> **当条件A较宽松而条件B较严格时，条件A是实际主导筛子，改变条件B的阈值几乎不影响结果。**

详细分析见 `references/union-filter-dominance.md`。

**对本项目的实际影响**：将 `cond_b_threshold` 从 2.0 升至 2.5 后，三市通过率几乎没有变化（双通过数完全相同）。这不是bug，而是 A∪B 逻辑的数学特性——条件B只在其专有的子集（条件B满足但条件A不满足）上产生增量，而这个子集非常小。

**调整阈值时，需理解实际控制松紧的是条件A还是条件B，而非仅看阈值数字。** 详细实证分析见 `references/or-dominance-analysis.md`。

### 有效调参经验（2026-06-03 实测）

| cond_a_min | cond_b_threshold | 标普500通过 | 沪深300通过 | 效果 |
|:---|---:|---:|---:|:---|
| 0.9 | 2.0 | 72% | 59% | 太松，几乎全过 |
| **1.5** | **2.0** | **34%** | **32%** | **推荐：开始有效筛选**（旧：5年×3期） |
| 1.5 | 2.5 | 33% | 31% | 和1.5/2.0几乎一样（B无效） |

**结论**：OR逻辑下 `cond_a_min=1.3` 是有效的筛选起点（每 `window_years` 年至少增长 `cond_a_min` 倍 ≈ 9.1% CAGR/窗口），`cond_b_threshold` 从1.5往上提几乎没有效果。如需更严的筛选，提高 `cond_a_min` 而非 `cond_b_threshold`。

## CLI 参数

| 参数 | 默认值 | 格式 | 说明 |
|:---|---:|:---|:---|
| `--index` | 必填 | 名称 | 指数名（sp500 / csi300 / hsi，对应 configs/） |
| `--mode` | `all` | 选项 | all=全部, price=仅股价, revenue=仅营收, dual=仅双维度 |
| `--window-years` | 3 | 年 | 每个窗口跨几年 |
| `--num-windows` | 5 | 个 | 从基准年往过去推几个窗口（YAML defaults 优先，默认5期） |
| `--price-base-yyyymm` | 今年3月 | `YYYY-MM` | 股价基准年月 |
| `--revenue-base-yyyy` | 因市场而异 | `YYYY` | 营收基准年 |

**时间窗口推算**：当 YAML 的 `defaults` 节配置了 `window_years` 或 `num_windows`，无需 CLI 参数即可自动生成 periods。示例：

```bash
# 默认从 YAML 读取：{window_years=3} × {num_windows=5} → 自动推算各窗口起止年
python3 run.py --index csi300

# 自定义覆盖
python3 run.py --index sp500 --window-years 5 --num-windows 5
```

## 筛选规则

**保留条件** = (所有窗口倍率 ≥ `cond_a_min`) ∪ (最新窗口倍率 > `cond_b_threshold`)

| 参数 | 默认值 | 含义 |
|:---|---:|:---|
| `cond_a_min` | **1.3** | 条件A：所有窗口倍率不低于此值（每 `window_years` 年至少增长 `cond_a_min` 倍 ≈ 9.1% CAGR/窗口） |
| `cond_b_threshold` | **1.5** | 条件B：最新窗口倍率超过此值（`window_years` 年增长 `cond_b_threshold` 倍 ≈ 14.5% CAGR） |

两个条件取并集（OR），满足其一即保留：
- 条件A → 长期稳健型，各期都没跌过
- 条件B → 近 `window_years` 年强势型，哪怕以前跌过但最近翻倍了也留

> 阈值通过各指数 YAML 配置的 `screening` 节设置，可逐个指数独立调整。

**默认窗口**：`{window_years=3}` 年 × `{num_windows=5}` 期（最近 5 个 3 年窗口）

**评分**：线性递减权重 1:2:...:`num_windows`（越近权重越高，归一化后权重之和为1）

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

## 参考文档（references/）

| 文件 | 内容 |
|:-----|:-----|
| `config-structure.md` | YAML 配置结构详解（所有节字段说明） |
| `data-sources.md` | 各市场数据源 API、复权策略、缓存管理 |
| `dual-analysis-pitfalls.md` | 双维度左连接静默排除的深层分析 |
| `threshold-calibration.md` | 阈值选择方法论：倍率→CAGR、通过率期望 |
| `union-filter-dominance.md` | A∪B 并集的行为陷阱：条件A主导效应 |
| `or-dominance-analysis.md` | OR 并集定量分析：调整 cond_b 几乎无效的实证 |
| `caching-patterns.md` | 缓存策略与强制刷新方法 |

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
7. **子代理访问保护**：当通过 `delegate_task` 运行本 pipeline 时，必须在 context 中加入 `CONSTRAINT: Do NOT modify any .py, .yaml, .csv, .md, or .json files. Only run the command and report output.` 否则子代理可能擅自修改配置和核心逻辑文件。
8. **参数全局迁移完整流程**（2026-06-03 精炼版）：做参数默认值、窗口、阈值等全局修改时，按此顺序执行：
   ```
   Step 1  grep 全仓库   多模式组合捕获所有写法（数字、注释、示例代码块）
   Step 2  改 configs/    三个指数的 YAML + 模板
   Step 3  改 lib/*.py    函数签名默认值 + docstring 示例
   Step 4  改 run.py      fallback 默认值 + CLI help 文字 + docstring 示例
   Step 5  改 README.md    参数表 + 示例段落（目视检查代码块中的硬编码）
   Step 6  改 SKILL.md     自身注意事项中的旧数值
   Step 7  改 references/  历史数据标注"旧配置"、默认值表格刷新
   Step 8  grep 全仓库验证  确认无残留（排除 references/ 中的历史标注）
   ```
   **grep 多模式必查清单**（Step 1 & Step 8）：
   ```bash
   grep -rn '14\.87\|8\.45\|cond_b_threshold: 2\.0\|cond_a_min: 1\.5\|window_years: 5\|num_windows: 3' \
     --include='*.py' --include='*.md' --include='*.yaml' . | grep -v references/
   ```
   **代码块目视检查**（最后一步）：YAML 块、docstring 示例、`>>` 引用中的示例值不受 grep 约束。打开 README.md 和 run.py 手动扫描"示例"段落的代码块。
   **模板同步**：`templates/new-index-config.yaml` 的 periods 和 defaults 会独立于 configs/ 存在，改 configs/ 时模板容易被遗漏。必须手动检查。

9. **文档"为什么"前置**：当用户问"为什么某做法"且你做出解释后，**必须同步更新项目文档/脚本注释**把原因写明白。口头解释+不做文档=用户回头问"你写清楚了没"。具体做法：README表格加原因列、代码函数加docstring说明动机。

10. **报告方法论参数动态化**：`lib/report.py` 中的 `build_price_report()` 和 `build_dual_report()` 接收 `cond_a_min`、`cond_b_threshold`、`window_years`、`num_windows` 参数，所有方法论描述（封面统计、筛选规则、条件解释、评分说明）均动态填充。**修改YAML配置后无需改 report.py，方法论描述自动同步。** `run.py` 的三个调用点（股价/营收/双维度）均已传入运行时值。注意中文CAGR格式使用 `.1%` 而非 `.0%`，避免四舍五入成整数（如 `15%` 而非 `14.9%`）。

11. **港股API不稳定与后备方案**：`ak.stock_hk_spot()` 在腾讯云GFW环境下经常返回空数据（`Length mismatch` 错误）。`lib/data_hk.py` 中的 `fetch_hk_names()` 已实现自动降级——失败时回退到 `HSI_NAMES` 硬编码字典。如果添加新港股指数，需要在 `HSI_NAMES` 中补充对应名称。也可直接运行（仅影响名称显示不报错）。

12. **文档约定——用参数名而非硬编码**：`filter_by_growth()` 接受 `cond_a_min` 和 `cond_b_threshold` 两个参数。阈值从 YAML `screening` 节读取。**文档和代码注释中必须使用变量名（如 `cond_b_threshold`）而非具体数字**，默认值统一在表格中注明。这是本项目的文档约定——读者看到的是规则结构，默认值在另一处独立呈现。

13. **A股名称获取陷阱**：A股报告曾出现股票名显示为代码的问题。修复要点：
    - 必须使用 `fetch_cn_names()` 从 `ak.stock_info_a_code_name()` 获取A股中文名，而非 `{c: c for c in codes}`
    - **该API的列名是英文 `code` / `name`，不是中文 `代码` / `名称`**。写错列名会导致 JSON decode 失败或 KeyError，回退到代码显示
    - `run.py` 中股价和营收两个分支都需要调用 `fetch_cn_names()`，漏一个则对应报告的股票名仍然是代码
    - **名称空格问题**：`ak.stock_info_a_code_name()` 返回的名称可能包含多余空格（如「五 粮 液」）。`fetch_cn_names()` 必须调用 `.replace(' ', '').replace('\\u3000', '')` 清理后再返回。
    - **代码前导0问题**：A股6位数字代码在 pandas DataFrame 中可能被转为 int（如 `000001` → `1`），写入 DOCX 时前导0丢失。`run.py` 中构建完 DataFrame 后必须执行 `fp_df['代码'] = fp_df['代码'].astype(str).str.zfill(6)`，股价和营收两个分支各做一次。

14. **双维度左连接遗漏**：dual 分析从 `price_df` 做 `left join rev_df`，因此**只有同时有股价数据的股票才进入双维度分析**。营收筛选通过的股票如果缺少完整 window_years 年股价历史（如次新股上市不足），会被静默排除。这不是bug，但解读双维度通过数时需要了解。详见 `references/dual-analysis-pitfalls.md`。

15. **阈值调整后必跑三市对比 + 并行加速**：修改筛选规则后必须跑完所有三个指数（sp500/csi300/hsi）并做新旧对比，因为不同市场的通过率响应差异很大。用 `delegate_task` 并行跑三个市场（各需~60s），总耗时约70s（而非串行180s）。并行 context 中必须加入 `CONSTRAINT: Do NOT modify any .py, .yaml, .csv, .md, or .json files. Only run the command and report output.` 防止子代理修改配置。

17. **3档提案模式**：当用户问"换一种窗口/阈值怎么定"时，不要只给一个数字。先做定量分析（CAGR折算），然后给出3档选项并推荐方案A（等价CAGR）：等价 | 宽松（补偿窗口波动） | 严格（提高标准）。先说"先跑方案A看看"——用户想先看数据再做决定，不是你替他选。详见 `references/threshold-calibration.md` 第三步。

16. **Git多作者署名**：Agent和人协作的项目，committer应为人类，Co-authored-by标注Agent。当Repo首次推送后用户要求修正时，全部commit squash为一个重设作者：
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
