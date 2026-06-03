# GFW 环境下 AkShare 数据源可用性（腾讯云广州 43.136.67.239）

2026-06-03 实测记录。使用前先验证，因为 GFW 规则会变化。

## A 股 — 全部可用 ✅

| 函数 | 数据源 | 状态 |
|:---|---:|:---:|
| `stock_zh_a_hist` | 东方财富 | ✅ |
| `stock_financial_abstract_ths` | 同花顺 | ✅ |
| `stock_info_a_code_name` | 东方财富 | ✅ |
| `index_stock_cons` | 东方财富 | ✅ |

## 港股 — 有限可用 ⚠️

| 函数 | 数据源 | 状态 |
|:---|---:|:---:|
| `stock_hk_hist` | 东方财富 | ✅ 可用 |
| `stock_financial_hk_report_em` | 东方财富 | ✅ 可用 |
| `stock_hk_spot` | 东方财富 | ⚠️ 间歇性返回空（`Length mismatch`），已降级到硬编码字典 |
| `stock_hk_spot_em` | 东方财富 | ✅ 可用 |

## 美股 — 只有新浪源可用 ❌东方财富

| 函数 | 数据源 | 状态 | 说明 |
|:---|---:|:---|:---|
| `stock_us_daily` | **新浪** | ✅ | 用 `adjust=''` 未复权 + 自实现拆股修正。`adjust='qfq'` 不可用（负数价格 bug） |
| `stock_us_spot` | **新浪** | ✅ | 实时行情，支持多只逗号分隔 |
| `stock_financial_us_report_em` | 东方财富 | ✅ | 营收数据可用（财务数据请求路径不同） |
| `stock_us_hist` | 东方财富 | ❌ | `Connection aborted`，被墙 |
| `stock_us_spot_em` | 东方财富 | ❌ | `Remote end closed connection` |
| `stock_us_famous_spot_em` | 东方财富 | ❌ | 同上 |
| `stock_us_valuation_baidu` | 百度 | 未测试 | 理论上可用（百度未被墙） |

## 关键结论

1. **美股股价数据只能走新浪**。东方财富的美股行情接口全部被墙。新浪 `stock_us_daily` 用 `adjust=''` 原始数据 + 自实现拆股修正，`adjust='qfq'` 参数不可用（负数价格 bug）。
2. **美股财务数据能走东方财富**（`stock_financial_us_report_em`）——财务数据走的 API 路径不同
3. **`stock_us_daily(adjust='qfq')` 的新浪原生前复权不可依赖**——存在系统性 bug，对所有长历史股票都会产生早期年份负数价格。实测数据（2026-06-03）：
   - AAPL：6027 行负数，close 范围 -10.40 ~ 315.20
   - MSFT：5575 行负数，close 范围 -35.55 ~ 542.07
   - GE：2741 行负数，close 范围 -101.47 ~ 345.27
   - 不推荐使用 qfq 参数。正确做法：走 `adjust=''` 未复权数据 + `lib/data_us.py` 的 `adjust_for_splits()` 自实现双向拆股检测。
4. **`stock_us_hist` 的 `105.` 前缀格式**（如 `105.AAPL`）来自东方财富，虽不可用但标记备忘
5. **`adjust_for_splits()` 自2026-06-03起支持双向拆股检测**：正向（pct_change < -0.4, ÷ratio）和反向（pct_change > 2.0, ×ratio）。修复前仅检测正向拆股，导致 GE 1:8 逆拆股漏检，2019→2024 增长被算成 17.6x（真实值 2.20x）。
