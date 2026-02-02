# REQUIREMENTS.md — 实时市场看板 v2

## 产品概述
轻量级实时市场行情终端，覆盖贵金属、大宗商品、数字货币和外汇。Yahoo Finance 风格的紧凑列表 + 点击进入 K 线详情。手机优先，PWA 适配。

## 用户
DQ — 常用手机查看，需要随时掌握核心资产价格和走势。

## v1 → v2 改动
| v1 | v2 |
|---|---|
| 价格卡片 | Yahoo 风格紧凑列表 |
| 只有 sparkline | 点击进入日 K 线详情 |
| GitHub Actions 15 分钟更新 | Vercel 代理 + 30 秒轮询 |
| 普通网页 | PWA Web App 适配 |

## 核心需求

### 1. 品种覆盖（可配置）
`config.json` 定义品种，新增只改配置。

| 类别 | 品种 | 数据源 |
|------|------|--------|
| 贵金属 | 黄金、白银、铜（USD/吨）、镍、稀土ETF(REMX) | Yahoo Finance via Vercel |
| 大宗商品 | WTI 原油 | Yahoo Finance via Vercel |
| 数字货币 | BTC、ETH | Binance WebSocket |
| 汇率 | USD/CNY、USD/JPY、EUR/USD | Yahoo Finance via Vercel |

- **铜**：原始 HG=F 是 USD/lb，前端显示时转换为 **USD/吨**（×2204.62）
- **镍**：测试 JJN / NICK.L / ^SPGSNI，选有数据的

### 2. 数据实时性
- **数字货币**：Binance WebSocket 真实时
- **其他品种**：Vercel Serverless 代理 Yahoo Finance API，前端 30 秒轮询
- 不再依赖 GitHub Actions 定时抓取

### 3. 列表页（主页）
Yahoo Finance 风格紧凑行情列表：
```
贵金属
───────────────────────────────
🥇 黄金    $4,729.50   +0.33%  ╱╲╱─
🥈 白银    $80.32      +2.60%  ╱╲──
🔶 铜      $12,710/吨  -2.20%  ──╲╱
```
- 按类别分组，每组标题
- 每行：icon + 名称 + 价格 + 涨跌% + 迷你 sparkline
- 涨绿跌红
- 点击任一行 → 进入详情页

### 4. 详情页
点击品种后进入：
- 品种名 + 当前价格（大字）+ 涨跌幅
- **日 K 线图**（TradingView Lightweight Charts，开源无水印）
- 默认 3 个月，可切换 1 周 / 1 月 / 3 月 / 1 年
- 返回按钮回列表

### 5. PWA Web App 适配
- `manifest.json`：名称、图标、主题色
- 手机 "添加到主屏幕" 后：
  - 全屏显示，无浏览器地址栏
  - 独立应用体验
  - 暗色系启动画面
- viewport 适配，禁止缩放

### 6. 视觉风格
- zinc 暗色系（与 Guru Tracker 一致）
- Inter 字体
- 紧凑布局，信息密度高
- 手机优先设计

## 技术约束
- 前端：纯静态 HTML/JS，部署 GitHub Pages
- 数据代理：Vercel Serverless Function（Python），代理 Yahoo Finance API
- K 线图：TradingView Lightweight Charts（CDN 引入）
- Crypto：Binance WebSocket（浏览器直连）

## 非需求
- 不做交易功能
- 不做用户登录
- 不做价格提醒（v2 不做）
- 不做分时图（只做日 K）

## 成功标准
1. 手机打开 2 秒内显示列表
2. BTC/ETH 价格实时跳动
3. 非 crypto 数据延迟 ≤30 秒
4. 点击进入 K 线图流畅，1 秒内渲染
5. 添加到手机主屏后像原生 App
6. 新增品种只改 config.json
