# 数据源说明

## A股（csi300）

### 成分股获取
```python
ak.index_stock_cons("000300")
```
列名：`品种代码`（字符串）。

### 股价
```python
ak.stock_zh_a_daily(symbol="sh600519", adjust="qfq")
```
前复权日线。筛选每年3月末最后一个交易日收盘价。

### 营收
```python
ak.stock_financial_abstract_ths(symbol="600519")
```
年报（12-31）营业总收入。注意列名包含全角空格，`parse_financial_value()` 做了特殊解析。

### 股票名称（重要）
```python
ak.stock_info_a_code_name()  # 列名: code, name（英文）
```

**列名陷阱**：该API返回英文列名 `code` / `name`，不是中文 `代码` / `名称`。用错列名会导致 KeyError 或 JSON decode 失败。

**空格陷阱**：返回的名称可能包含多余空格（如「五 粮 液」→"五 粮 液"），必须清理 `.replace(' ', '').replace('\u3000', '')`。

**代码前导零**：A股代码为6位数字（000001），在pandas DataFrame中可能被转为int，写入CSV或DOCX时前导0丢失。必须在构建DataFrame后执行 `.astype(str).str.zfill(6)`。

**双分支需各做一次**：`run.py` 中股价和营收两个分支各自定义了自己的 `names` 字典，两个分支都需要调用 `fetch_cn_names()`，漏一个则对应报告的股票名仍是代码。

### 缓存
- 股价：`~/.hermes/stock_cache/<指数>_analysis/march_closes.json`，7天
- 营收：`~/.hermes/stock_cache/<指数>_analysis/revenue_data.json`，7天
- 股票名：不缓存，每次从API获取（轻量）

---

## 港股（hsi）

### 成分股
硬编码 `HSI_CODES` 列表（93只），无动态API。

### 股价
```python
ak.stock_hk_daily(symbol="00001")
```

### 营收
```python
ak.stock_financial_hk_report_em(stock="00001", symbol="利润表", indicator="年度")
```
营业总收入通过匹配 `营业额` / `营业收入` / `经营收入总额` 获取。

### 股票名称
```python
ak.stock_hk_spot()  # 列名: 代码, 中文名称
```

**GFW不稳定**：`stock_hk_spot()` 在腾讯云服务器上经常返回空数据导致 `ValueError: Length mismatch`。`fetch_hk_names()` 实现了自动降级——API失败时回退到 `HSI_NAMES` 硬编码字典。添加新港股指数需补充硬编码名称。

---

## 美股（sp500）

### 成分股
CSV文件 `configs/sp500_constituents.csv`（SlickCharts导出），503只。

### 股价
```python
ak.stock_us_daily(symbol="AAPL")
```
⚠️ **不推荐 `adjust='qfq'`**：新浪原生前复权存在系统性 bug，早期年份产生大量负数价格（AAPL 6027行、MSFT 5575行、GE 2741行）。必须用 `adjust=''` 获取未复权数据，再通过 `lib/data_us.py` 的 `adjust_for_splits()` 自实现拆股修正。

自实现拆股修正检测两种方向：
- **正向拆股**（如 4:1 前向拆分）：单日跌幅 >40% → 之前所有价格 **除以** 比例
- **反向拆股**（如 1:8 逆拆分）：单日涨幅 >200% → 之前所有价格 **乘以** 比例

反向拆股漏检会导致增长倍率严重虚高（GE 1:8 逆拆股漏检时 2019→2024 增长被算成 17.6x，实为 2.20x）。

### 营收
```python
ak.stock_financial_us_report_em(symbol="AAPL")
```
利润表营业总收入。

### 股票名称
从CSV的 `Company Name` 列读取。
