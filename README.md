# Market Dashboard 📈

A real-time market dashboard displaying precious metals, commodities, cryptocurrencies, and forex rates.

## Features

- **Real-time crypto prices** via Binance WebSocket
- **Automated data updates** for traditional assets every 15 minutes via GitHub Actions
- **Interactive sparklines** showing 7-day price trends
- **Responsive design** with zinc dark theme
- **Live connection status** indicator
- **Mobile-optimized** interface

## Data Sources

- **Cryptocurrencies**: Binance WebSocket (real-time)
- **Metals & Commodities**: Yahoo Finance (15-min intervals)
- **Forex**: Yahoo Finance (15-min intervals)

## Asset Categories

### 🥇 贵金属 (Precious Metals)
- 黄金 (Gold) - GC=F
- 白银 (Silver) - SI=F
- 铜 (Copper) - HG=F
- 镍 (Nickel) - ^SPGSNI
- 稀土ETF (Rare Earth ETF) - REMX

### 🛢️ 大宗商品 (Commodities)
- WTI原油 (WTI Crude Oil) - CL=F
- 布伦特原油 (Brent Crude Oil) - BZ=F

### ₿ 数字货币 (Cryptocurrencies)
- Bitcoin (BTC) - BTCUSDT
- Ethereum (ETH) - ETHUSDT

### 🌐 汇率 (Forex)
- USD/CNY - CNY=X
- USD/JPY - JPY=X
- EUR/USD - EURUSD=X

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   index.html    │    │  GitHub Actions  │    │  Binance API    │
│   (Frontend)    │◄──►│  (Data Fetcher)  │◄──►│  (WebSocket)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        │
┌─────────────────┐    ┌──────────────────┐               │
│  data/latest.   │    │   Yahoo Finance  │               │
│  json           │    │   (yfinance)     │               │
└─────────────────┘    └──────────────────┘               │
         │                                                 │
         └─────────────────────────────────────────────────┘
                    Real-time updates
```

## Configuration

The dashboard is driven by `config.json`, making it easy to add new assets:

```json
{
  "categories": [
    {
      "name": "Category Name",
      "id": "category_id",
      "assets": [
        {
          "name": "Asset Name",
          "symbol": "SYMBOL",
          "source": "yahoo|binance",
          "unit": "USD",
          "icon": "📊"
        }
      ]
    }
  ],
  "refresh_interval_seconds": 30,
  "history_days": 7
}
```

## Development

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/patrickdong16/market-dashboard.git
   cd market-dashboard
   ```

2. Install Python dependencies:
   ```bash
   pip install yfinance requests
   ```

3. Fetch initial data:
   ```bash
   python scripts/fetch_prices.py
   ```

4. Serve locally:
   ```bash
   python -m http.server 8000
   # Visit http://localhost:8000
   ```

### File Structure

```
market-dashboard/
├── index.html              # Single-page dashboard
├── config.json            # Asset configuration
├── scripts/
│   └── fetch_prices.py     # Data fetcher script
├── data/
│   ├── latest.json         # Current prices & changes
│   └── history.json        # Fetch history log
├── .github/
│   └── workflows/
│       └── update-prices.yml  # Auto-update workflow
└── README.md
```

## Deployment

This project is designed for **GitHub Pages** deployment:

1. Push to GitHub
2. Enable GitHub Pages (Settings → Pages → Source: Deploy from branch → main)
3. The GitHub Action will automatically update data every 15 minutes
4. Manual updates: Actions → Update Market Prices → Run workflow

## Data Update Flow

1. **GitHub Actions** runs every 15 minutes
2. **fetch_prices.py** queries Yahoo Finance and Binance APIs
3. **data/latest.json** is updated with current prices
4. **Frontend** polls latest.json every 30 seconds
5. **WebSocket** provides real-time crypto updates

## Error Handling

- Network timeouts (10s limit)
- API rate limiting with retries
- Fallback data for failed fetches
- Graceful degradation for offline periods
- Alternative symbols for problematic assets (e.g., Nickel: ^SPGSNI → NI=F)

## License

MIT License - Feel free to use and modify.

---

**Live Demo**: [Market Dashboard](https://patrickdong16.github.io/market-dashboard/)

**Built with** ❤️ by [Patrick Dong](https://github.com/patrickdong16)
