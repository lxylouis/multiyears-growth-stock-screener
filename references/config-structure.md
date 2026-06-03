# YAML 配置结构

## 总览

每个指数一个 `.yaml` 文件，位置 `configs/<指数名>.yaml`。所有运行时行为由 YAML 配置驱动。

## 配置节概览

```yaml
# ── 窗口参数（CLI 参数可覆盖） ──
defaults:
  window_years: 5     # 每个窗口跨几年（--window-years 覆盖）
  num_windows: 3      # 从基准年往过去推几个窗口（--num-windows 覆盖）

# ── 筛选阈值（当前无 CLI 覆盖） ──
screening:
  cond_a_min: 0.9         # 条件A：所有窗口倍率不低于此值
  cond_b_threshold: 2.0   # 条件B：最新窗口倍率超过此值（≈ 14.87% CAGR）

# ── 指数基本信息 ──
index:
  name: "沪深300"         # 显示名称
  code: "000300"          # 指数代码
  market: "cn"            # 市场：cn=沪深A股, hk=港股, us=美股

# ── 成分股来源 ──
stock_codes:
  # A股：从 AKShare 指数成分股接口动态获取
  type: "index"
  source_func: "index_stock_cons"
  source_arg: "000300"
  
  # 美股：从本地 CSV 读取（AKShare 无标普成分股接口）
  # type: "csv"
  # csv_path: "configs/sp500_constituents.csv"
  # ticker_col: "Ticker"
  # name_col: "Company Name"
  
  # 港股：硬编码列表（AKShare 无恒指成分股接口）
  # type: "hardcoded"
  # codes: ["00700", "09988", ...]

# ── 时间窗口硬编码（有 defaults 时自动覆盖） ──
periods:
  price: [[2024,2019],[2025,2020],[2026,2021]]
  revenue: [[2023,2018],[2024,2019],[2025,2020]]
  labels: ['24/19','25/20','26/21']

# ── 输出目录 ──
output_dir: "~/.hermes/stock_cache/csi300_analysis"
```

## 配置优先顺序

```
CLI 参数（最高） → YAML defaults → YAML periods 硬编码（最低）
```

具体逻辑见 run.py：

```python
window_years = args.window_years or config.get('defaults', {}).get('window_years', 5)
num_windows = args.num_windows or config.get('defaults', {}).get('num_windows', 
                 len(config.get('periods', {}).get('price', [])))

# 当 YAML 有 defaults 或传入 CLI 参数 → 自动生成 periods
use_auto = (args.window_years is not None or args.num_windows is not None
            or args.price_base_yyyymm or args.revenue_base_yyyy
            or config.get('defaults', {}).get('window_years')
            or config.get('defaults', {}).get('num_windows'))
if use_auto:
    price_periods = auto_periods(py_base, window_years, num_windows)
    rev_periods = auto_periods(ry_base, window_years, num_windows)
else:
    price_periods = config['periods']['price']
```

## `screening` 节详解

| 字段 | 默认值 | 含义 | 历史 |
|:----|:-----:|:-----|:----|
| `cond_a_min` | 0.9 | 条件A：所有窗口倍率不低于此值（防大幅衰退） | 曾硬编码在 `compute.py` |
| `cond_b_threshold` | 2.0 | 条件B：最新窗口倍率超过此值（5年翻倍 ≈ 14.87% CAGR） | 曾叫 `latest_threshold`，参数传递 |

`compute.py` 中对应函数签名：

```python
def filter_by_growth(df: pd.DataFrame, mult_cols: list,
                     cond_a_min: float = 0.9,
                     cond_b_threshold: float = 2.0) -> pd.DataFrame:
```

## 修改阈值时的全覆盖检查清单

因为阈值影响了 `.py`、`.md`、`.yaml`、`templates/` 四种文件类型，修改时必须检查：

1. **compute.py**: 函数签名的默认值 + docstring
2. **run.py**: 各 `filter_by_growth()` 调用 + print 语句
3. **configs/<指数>.yaml**: `screening` 节 + `periods` 数组
4. **templates/new-index-config.yaml**: 同步模板
5. **SKILL.md**: 筛选规则表 + 注意事项
6. **README.md**: 筛选规则表 + 说明段落
7. **references/threshold-calibration.md**: 实际跑测数据表

**文档约定**：正文中使用变量名（`cond_a_min`、`cond_b_threshold`）而非数字，默认值统一在表格中注明。
