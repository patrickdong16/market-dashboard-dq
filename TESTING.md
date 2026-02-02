# TESTING.md — 测试策略 v2

## 1. Vercel API 代理测试

### quotes API
```bash
# 本地测试（vercel dev）
curl "http://localhost:3000/api/quotes?symbols=GC=F,SI=F,BTCUSDT"
# 验证：
# - 每个 symbol 有 price, change_pct
# - 响应 < 3 秒
# - CORS header 存在

# 部署后测试
curl "https://market-dashboard-api.vercel.app/api/quotes?symbols=GC=F"
```

### chart API
```bash
curl "http://localhost:3000/api/chart?symbol=GC=F&range=3mo&interval=1d"
# 验证：
# - 返回 OHLCV 数组
# - 数据点约 60+ 个（3个月交易日）
# - 每个点有 time, open, high, low, close

# 不同 range
curl "http://localhost:3000/api/chart?symbol=GC=F&range=5d&interval=1d"
curl "http://localhost:3000/api/chart?symbol=GC=F&range=1y&interval=1d"
```

### 错误处理
- 无效 symbol → 返回 `{"error": "..."}`, status 400
- Yahoo API 超时 → 返回 `{"error": "timeout"}`, status 504
- 缺少参数 → 返回 `{"error": "missing symbols"}`, status 400

### 铜价转换验证
```bash
# 获取 HG=F 原始价格
curl "https://market-dashboard-api.vercel.app/api/quotes?symbols=HG=F"
# 手动计算：price * 2204.62 应该 ≈ 合理的铜价/吨（当前约 $9000-12000/吨）
```

## 2. 前端功能测试

### 列表视图
- [ ] 页面 2 秒内渲染完成
- [ ] 4 个分类标题显示
- [ ] 所有品种行都渲染
- [ ] 价格正确（千位分隔符）
- [ ] 涨跌颜色正确
- [ ] Sparkline 绘制
- [ ] 30 秒自动刷新（观察价格变化）
- [ ] 铜显示 USD/吨（转换后数值合理）

### 详情视图
- [ ] 点击品种行 → 进入详情
- [ ] K 线图 1 秒内渲染
- [ ] 默认显示 3 个月
- [ ] 切换 1W/1M/3M/1Y 正常
- [ ] 返回按钮回列表
- [ ] 浏览器后退也能回列表

### Binance WebSocket
- [ ] BTC/ETH 价格实时跳动
- [ ] 断网后重连
- [ ] Crypto 详情页 K 线显示

### PWA
- [ ] manifest.json 加载（Chrome DevTools → Application）
- [ ] iPhone Safari "添加到主屏幕" → 独立窗口打开
- [ ] 全屏无地址栏
- [ ] 暗色主题色

### 响应式
- [ ] iPhone SE（375px）：列表紧凑可用
- [ ] iPhone 14（390px）：列表舒适
- [ ] iPad（768px）：更宽的布局
- [ ] 桌面（1200px+）：合理利用空间

## 3. 数据准确性

### 交叉验证
对比 Market Dashboard 显示值与以下来源：
- Yahoo Finance 网页/App
- Google "gold price"
- Binance App（BTC/ETH）
- 误差应 < 0.1%

### 镍数据验证
测试以下 symbol，哪个返回有效数据：
- JJN（iPath 镍 ETN）
- NICK.L（WisdomTree 镍 ETC）
- ^SPGSNI（S&P GSCI 镍指数）
- NI=F

## 4. 端到端验证

### 部署检查
- [ ] GitHub Pages 前端可访问
- [ ] Vercel API 可访问
- [ ] 前端成功调用 Vercel API（无 CORS 错误）
- [ ] 所有品种有数据

### 性能
- [ ] 首次加载 < 3 秒（Lighthouse 测试）
- [ ] API 响应 < 2 秒
- [ ] K 线图渲染 < 1 秒

## 验收标准
1. ✅ Yahoo 风格列表，点击进入 K 线
2. ✅ 数据延迟 ≤30 秒（非 crypto）
3. ✅ BTC/ETH 实时
4. ✅ PWA 添加到主屏可用
5. ✅ 铜显示 USD/吨
6. ✅ 手机体验优先
