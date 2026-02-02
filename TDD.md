# TDD.md — 技术设计文档 v2

## 架构概述

```
┌─ 用户手机/浏览器 ─────────────────────────┐
│                                             │
│  GitHub Pages (静态前端)                    │
│  ┌─────────────────────────────────────┐   │
│  │  index.html (SPA)                    │   │
│  │  ┌──────────┐  ┌─────────────────┐  │   │
│  │  │ 列表视图  │  │   详情视图       │  │   │
│  │  │ (Yahoo式) │→│  (K线图)        │  │   │
│  │  └──────────┘  └─────────────────┘  │   │
│  └──────────┬──────────────┬───────────┘   │
│             │              │                │
│      30s 轮询          WebSocket           │
│             ↓              ↓                │
│  ┌──────────────┐  ┌──────────────┐        │
│  │ Vercel API   │  │  Binance WS  │        │
│  │ (代理Yahoo)  │  │  (直连)      │        │
│  └──────┬───────┘  └──────────────┘        │
│         ↓                                   │
│  Yahoo Finance API                          │
└─────────────────────────────────────────────┘
```

## 组件设计

### 1. Vercel Serverless API (`api/`)

#### `api/quotes.py`
- **GET** `/api/quotes?symbols=GC=F,SI=F,HG=F,CNY=X,...`
- 代理 Yahoo Finance quote API
- 返回：每个 symbol 的 price, change_pct, prev_close
- CORS headers: `Access-Control-Allow-Origin: *`
- 超时 10 秒

#### `api/chart.py`
- **GET** `/api/chart?symbol=GC=F&range=3mo&interval=1d`
- 代理 Yahoo Finance chart API
- 返回：OHLCV 数据（给 K 线图用）
- range 支持: 5d, 1mo, 3mo, 1y
- interval 支持: 1d

**Vercel 函数不用 yfinance**，直接代理 Yahoo Finance REST API（`query1.finance.yahoo.com`），避免冷启动慢。

### 2. 前端 (`index.html`)

**单文件 SPA**，hash 路由：
- `#/` → 列表视图
- `#/detail/{symbol}` → K 线详情视图

#### 列表视图
- 加载 `config.json` 获取品种配置
- 调用 Vercel `/api/quotes` 获取所有 Yahoo 品种报价
- Binance WebSocket 获取 crypto 实时价格
- 30 秒定时轮询非 crypto 数据
- 每行渲染：icon + name + price + change% + sparkline (Canvas)
- 点击行 → `location.hash = '#/detail/{symbol}'`

#### 详情视图
- 显示品种名 + 当前价格 + 涨跌幅
- 调用 `/api/chart?symbol={symbol}&range=3mo&interval=1d`
- 用 TradingView Lightweight Charts 渲染日 K 线
- 时间范围切换按钮：1W / 1M / 3M / 1Y
- 返回按钮 → `location.hash = '#/'`

#### 铜价转换
- HG=F 原始单位：USD/lb
- 前端检测 symbol === 'HG=F' 时：`price * 2204.62`（1吨 = 2204.62 磅）
- 显示单位改为 USD/吨

#### Sparkline
- Canvas 绘制，50×20 像素
- 数据源：quotes API 中附带的 5 日走势
- 涨 emerald / 跌 red

### 3. Binance WebSocket
- 连接 `wss://stream.binance.com:9443/ws`
- 订阅 `btcusdt@ticker` + `ethusdt@ticker`
- 实时更新列表中的 crypto 行
- 在详情页：如果是 crypto，用 Binance Klines REST API 获取 K 线数据
- 自动重连（3 秒延迟）

### 4. PWA 配置

#### `manifest.json`
```json
{
  "name": "Market Dashboard",
  "short_name": "Markets",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#09090b",
  "theme_color": "#09090b",
  "icons": [...]
}
```

#### `<meta>` 标签
```html
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="manifest.json">
```

### 5. Vercel 部署配置

#### `vercel.json`
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" }
  ],
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Cache-Control", "value": "s-maxage=15" }
      ]
    }
  ]
}
```

Vercel 项目独立部署（只含 api/ 目录），前端留在 GitHub Pages。

## 文件结构
```
market-dashboard/                    # GitHub Pages (前端)
├── index.html                       # SPA 主页面
├── manifest.json                    # PWA 配置
├── config.json                      # 品种配置
├── REQUIREMENTS.md
├── TDD.md
├── TESTING.md
├── CLAUDE.md
└── README.md

market-dashboard-api/                # Vercel (API 代理)
├── api/
│   ├── quotes.py                    # 报价代理
│   └── chart.py                     # K线数据代理
├── vercel.json
├── requirements.txt                 # requests
└── README.md
```

或者 API 放在同一个 repo 的 `api/` 目录，Vercel 从同一 repo 部署。

## 依赖
- **前端 CDN**: TradingView Lightweight Charts v4
- **Vercel Python**: requests（标准库 urllib 也行，不需要 yfinance）
- **无构建步骤**

## 已知限制
- Yahoo Finance 非官方 API，可能变更（但多年稳定）
- 镍数据可能不完整，需测试多个 symbol
- Binance WS 在部分网络环境可能受限
- Vercel 免费版有冷启动延迟（~500ms），可接受
