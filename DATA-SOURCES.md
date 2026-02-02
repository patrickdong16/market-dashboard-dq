# Market Dashboard 数据源参考

> 2026-02-03 实测总结。避免下次从头摸索。

## 数据源总览

| 数据源 | 费用 | 认证 | 实时报价 | 分时数据 | 日线数据 | 云端可用 |
|--------|------|------|---------|---------|---------|---------|
| **EODHD** (All-in-One) | ~$80/月 | API Key | ✅ | ⚠️ 滞后2天 | ✅ | ✅ |
| **Yahoo Finance** (认证) | 免费 | Crumb+Cookie | ✅ | ✅ 完整 | ✅ | ❌ 云IP被封 |
| **Yahoo Finance** (无认证) | 免费 | 无 | ⚠️ 部分 | ⚠️ 不完整 | ⚠️ 延迟 | ⚠️ 残缺数据 |
| **GoldPrice.org** | 免费 | 无需 | ✅ ~30秒 | ❌ | ❌ | ✅ |
| **Binance** | 免费 | 无需 | ✅ | ✅ | ✅ | ✅ |

---

## EODHD (eodhistoricaldata.com)

**DQ 套餐：All-in-One**（2026-02-03 从基本面升级）

### 能力

| 功能 | API 端点 | 状态 | 备注 |
|------|---------|------|------|
| US 股票/ETF 实时报价 | `/api/real-time/{SYM}.US` | ✅ | 价格、涨跌、前收、成交量 |
| Forex 实时报价 | `/api/real-time/{PAIR}.FOREX` | ✅ | EURUSD、USDCNY、USDJPY 等 |
| Crypto 实时报价 | `/api/real-time/{SYM}.CC` | ✅ | BTC-USD.CC、ETH-USD.CC |
| US 股票/ETF 日线 | `/api/eod/{SYM}.US` | ✅ | 完整历史，当日更新 |
| Forex 日线 | `/api/eod/{PAIR}.FOREX` | ✅ | |
| US 股票/ETF 分时 (5m) | `/api/intraday/{SYM}.US` | ⚠️ | **滞后约2天**（已发邮件问客服） |
| **贵金属现货** | XAUUSD.FOREX / XAGUSD.FOREX | ❌ | 返回 NA，客服确认不支持 |
| **COMEX 期货** | GC.COMEX / SI.COMEX / CL.COMEX | ❌ | 返回 NA，客服确认不支持 |
| 伦敦金属 | NICK.LSE 等 | ❌ | 未测试 |

### Symbol 格式
- US 股票/ETF: `AAPL.US`, `GLD.US`, `SLV.US`
- Forex: `EURUSD.FOREX`, `USDCNY.FOREX`
- Crypto: `BTC-USD.CC`, `ETH-USD.CC`

### 优势
- 付费数据，质量稳定
- 日线数据完整、当日更新
- 实时报价覆盖 US/Forex/Crypto
- 云端（Vercel）可用，无 IP 限制

### 劣势
- 分时数据滞后 ~2 天（可能是 All-in-One 的限制，待客服确认）
- 不支持贵金属现货和 COMEX 期货
- 客服域名是 `eodhistoricaldata.com`（不是 eodhd.com），搜邮件注意

### 客服联系
- 发件人: `supportlevel1@eodhistoricaldata.com`
- 收件人: `support@eodhistoricaldata.com`
- 付款方: Unicorn Data Services (Stripe)

---

## Yahoo Finance

### 认证 vs 无认证

| 特性 | 认证 (Crumb) | 无认证 |
|------|-------------|--------|
| 本地 (Mac mini) | ✅ 完整数据 | ✅ 完整数据 |
| 云端 (Vercel/AWS) | ❌ 获取 crumb 失败 | ⚠️ 残缺（少于一半数据点） |
| 分时数据 | 79 点 (完整 session) | 28 点 (最后几小时) |
| 日线数据 | 正常 | 延迟 2-3 天 |

### 能力

| 功能 | Symbol | 状态 |
|------|--------|------|
| US 股票/ETF | GLD, SLV, SPY | ✅ |
| COMEX 期货 | GC=F, SI=F, CL=F, HG=F | ✅ |
| 伦敦 ETC | NICK.L | ✅ |
| Forex | EURUSD=X, CNY=X | ✅ |
| Crypto | BTC-USD, ETH-USD | ✅ |
| **贵金属现货** | XAUUSD=X | ❌ 404 |

### ⚠️ 重要陷阱

1. **`chartPreviousClose` ≠ 昨日收盘价**
   - `chartPreviousClose` 是请求 range 起始日的收盘价（如 5d range → 5天前的价）
   - 真正的昨日收盘用 `previousClose`（但可能为 None）
   - **正确做法：** previousClose → 倒数第二根 bar 的 close → chartPreviousClose

2. **云 IP 限制**
   - Yahoo 对 Vercel/AWS/GCP 等云服务商 IP 返回严重残缺的数据
   - `query1` 和 `query2` 端点都一样，crumb 也无法解决
   - **结论：不能依赖 Yahoo 作为 Vercel serverless 的主数据源**

3. **GC=F 是期货不是现货**
   - instrumentType: FUTURE, Exchange: CMX
   - 与现货价差通常几十美元（contango/backwardation）

### 优势
- 免费，覆盖面极广
- 本地调用数据完整
- 期货、ETF、股票、Forex、Crypto 全有

### 劣势
- 云端不可用（IP 限制）
- 无官方 API，随时可能变
- 没有贵金属现货

---

## GoldPrice.org

**端点：** `https://data-asg.goldprice.org/dbXRates/USD`

### 能力

| 字段 | 说明 |
|------|------|
| xauPrice | 黄金现货 $/oz |
| xagPrice | 白银现货 $/oz |
| chgXau / chgXag | 日绝对变动 |
| pcXau / pcXag | 日涨跌幅 % |
| xauClose / xagClose | 前收盘价 |

### 特性
- **完全免费，无需 API Key，无请求限制**
- 更新频率：~30 秒
- 数据来源：银行间市场现货价
- **只有 XAU 和 XAG**，没有铂金、钯金、铜等
- **没有历史数据和分时数据**（只有当前价格快照）

### 优势
- 零成本、零认证
- 现货价格权威（银行间市场）
- 云端可用
- 更新频率足够（~30秒）

### 劣势
- 只有金银两个品种
- 无历史/分时数据（图表需要其他数据源补充）
- 非官方 API，无 SLA

---

## Binance

**端点：** `https://api.binance.com/api/v3/`

### 能力
- 24h 价格统计: `/ticker/24hr?symbol=BTCUSDT`
- K 线历史: `/klines?symbol=BTCUSDT&interval=1d&limit=7`
- 支持所有 Binance 上架的交易对

### 优势
- 免费，数据完整
- Crypto 最权威的数据源之一
- 云端可用

### 劣势
- 只有 Crypto
- 某些地区可能有访问限制

---

## 当前 Dashboard 数据源架构

```
首页报价 (latest.json, Mac mini 本地抓取):
├── 黄金/白银现货 → GoldPrice.org
├── ETF (GLD/SLV) → EODHD 实时
├── 期货 (铜/镍/原油) → Yahoo (本地认证)
├── Crypto (BTC/ETH) → EODHD 实时
└── Forex (CNY/JPY/EUR) → EODHD 实时

详情页图表 (Vercel API):
├── 日线 K 线 (1M/3M/1Y) → EODHD EOD 优先 → Yahoo fallback
└── 分时图 → 已移除（数据不可靠）

前端实时刷新 (Vercel API /api/quotes):
├── 金银现货 → GoldPrice.org
├── 其他品种 → EODHD 优先 → Yahoo fallback
```

---

## 待探索的数据源

| 数据源 | 用途 | 费用 | 备注 |
|--------|------|------|------|
| Metals-API.com | 贵金属 | $15/月起 | 有历史数据 |
| GoldAPI.io | 贵金属 | $10/月起 | |
| metals.dev | 贵金属 | $9/月起 | |
| CME Market Data | COMEX 期货 | 机构级 | 太贵 |
| LBMA API | 现货 fix price | 需认证 | 每日2次，非实时 |

---

*最后更新: 2026-02-03 by Pepper*
