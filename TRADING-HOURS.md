# Trading Hours Reference — Market Dashboard

> 权威来源：CME Group (cmegroup.com/trading-hours.html), NYSE, NASDAQ, LSE 官方文档
> 所有时间均为 Eastern Time (ET)，自动处理 EST/EDT 切换

## 资产交易时段

### CME 金属期货 (GC=F 黄金, SI=F 白银, HG=F 铜)
- **交易时段：** 周日 18:00 – 周五 17:00 ET
- **每日维护中断：** 17:00 – 18:00 ET（每个交易日）
- **来源：** CME Group COMEX Division
- **Yahoo symbol 特征：** `=F` 后缀

### CME 能源期货 (CL=F WTI原油)
- **交易时段：** 周日 18:00 – 周五 17:00 ET
- **每日维护中断：** 17:00 – 18:00 ET
- **来源：** CME Group NYMEX Division
- **Yahoo symbol 特征：** `=F` 后缀

### US 股票 & ETF (GLD, SLV, COPX 等)
- **常规交易：** 09:30 – 16:00 ET（周一至周五）
- **盘前交易：** 04:00 – 09:30 ET
- **盘后交易：** 16:00 – 20:00 ET
- **来源：** NYSE / NASDAQ
- **EODHD symbol 特征：** `.US` 后缀
- **注意：** 我们的 5m 分时数据通常只覆盖常规交易时段

### 加密货币 (BTC, ETH)
- **交易时段：** 24/7/365，全年无休
- **无维护中断**
- **EODHD symbol 特征：** `.CC` 后缀
- **图表展示：** 最近 24 小时，fitContent

### 外汇 (USDCNY, USDJPY, EURUSD)
- **交易时段：** 周日 17:00 – 周五 17:00 ET
- **实际上周内 24 小时连续交易**，无中断
- **EODHD symbol 特征：** `.FOREX` 后缀
- **图表展示：** 最近 24 小时，fitContent

### 伦敦交易所 ETC (NICK.L 镍)
- **交易时段：** 08:00 – 16:30 GMT（周一至周五）
- **对应 ET：** 03:00 – 11:30 ET (EST) / 04:00 – 12:30 ET (EDT)
- **来源：** London Stock Exchange
- **Yahoo symbol 特征：** `.L` 后缀

## Dashboard 分时图配置

| 资产类型 | symbol 判断 | 交易时段 (ET) | setVisibleRange |
|----------|------------|--------------|-----------------|
| US ETF/Stock | `.US` | 09:30–16:00 | 当日 09:30–16:00 ET |
| CME 期货 | `=F` | 前日 18:00–当日 17:00 | 前日 18:00–当日 17:00 ET |
| 加密货币 | `.CC` 或 `BTC/ETH` | 24/7 | fitContent (最近 24h) |
| 外汇 | `.FOREX` | ~24h (周内) | fitContent (最近 24h) |
| 伦敦 ETC | `.L` | 08:00–16:30 GMT | 当日对应 ET 时间 |

## 时区处理要点

1. **数据时间戳：** API 返回 UTC Unix 时间戳（分时）或日期字符串（日线）
2. **显示时区：** 分时图 X 轴显示 ET 时间（通过 `tickMarkFormatter` + `America/New_York`）
3. **BusinessDay：** 日线图用 `{year, month, day}` 格式，完全无时区问题
4. **DST 自动处理：** 使用 `Intl.DateTimeFormat` with `timeZone: 'America/New_York'`，EST/EDT 自动切换

## 假日

US 市场主要假日（休市）：
- New Year's Day, MLK Day, Presidents' Day, Good Friday
- Memorial Day, Juneteenth, Independence Day, Labor Day
- Thanksgiving, Christmas

CME 期货假日安排与股市不完全相同，具体以 CME Group 日历为准。

## 周末处理

- 周六/周日查看"今日"→ 显示上一个交易日的数据
- CME 期货周日 18:00 ET 重新开盘，在此之前显示周五数据
- 加密货币无此问题（24/7 交易）
