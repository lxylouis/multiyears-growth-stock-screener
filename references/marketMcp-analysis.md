# marketMcp 分析备忘

仓库：https://github.com/qiupo/marketMcp（~3⭐，2026-06）

## 定位
AkShare 的 MCP Server 封装。TypeScript MCP Server → PythonShell → AkShare。

## 对选股器项目的参考价值：低

| 方面 | 选股器现状 | marketMcp | 对比 |
|:---|---:|:---|:---|
| A股K线 | `stock_zh_a_hist` | 同一个函数 | 无差异 |
| 美股数据 | `stock_us_daily`（新浪） | `stock_us_spot`（新浪同源） | 不如选股器（选股器有自实现复权修正） |
| 港股数据 | `stock_hk_hist` | 无定义港股历史工具 | 不如选股器 |
| 营收数据 | 三市场各自财务接口 | 无营收相关工具定义 | 不如选股器 |
| 架构 | Python 直接调用 | MCP Server → Python 子进程 | 多一层无增益 |

## 有价值的地方

1. 代码前缀规范化：雪球需要 SH/SZ 前缀，东方财富不需要——mcp 的 `_prepare_individual_basic_info_params` 做了自动映射
2. 参数清洗：日期格式、limit 参数等统一处理——但我们的项目已经自己封装了这些

## 结论

mcp 服务器的**所有数据能力已被选股器项目覆盖**。它对选股器的价值是"参考架构模式"而非"可复用的数据层"。
