#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Dashboard 数据抓取脚本
从 yfinance 获取价格数据，从 Binance 获取 crypto 数据（作为 fallback）
"""

import json
import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 检查并安装依赖
try:
    import yfinance as yf
    import requests
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Please install required packages: pip install yfinance requests")
    exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketDataFetcher:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.timeout = 10
        self.max_retries = 3
        self._goldprice_cache = None  # Cache goldprice API response within a run
        
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def get_yahoo_data(self, symbol: str, name: str) -> Dict[str, Any]:
        """获取 Yahoo Finance 数据"""
        result = {
            'symbol': symbol,
            'name': name,
            'price': None,
            'change_percent_24h': None,
            'history': [],
            'error': None,
            'source': 'yahoo'
        }
        
        # 特殊处理镍的符号
        original_symbol = symbol
        if symbol == "^SPGSNI":
            # 尝试多个可能的镍符号
            symbols_to_try = ["^SPGSNI", "NI=F"]
        else:
            symbols_to_try = [symbol]
        
        for retry_count in range(self.max_retries):
            for attempt_symbol in symbols_to_try:
                try:
                    ticker = yf.Ticker(attempt_symbol)
                    
                    # 获取历史数据（8天，确保有足够数据）
                    hist = ticker.history(period="8d", interval="1d", timeout=self.timeout)
                    
                    if hist.empty:
                        logger.warning(f"No historical data for {attempt_symbol}")
                        continue
                    
                    # 获取当前价格（最新收盘价）
                    current_price = float(hist['Close'].iloc[-1])
                    
                    # 计算24h变化（与前一天比较）
                    if len(hist) >= 2:
                        prev_price = float(hist['Close'].iloc[-2])
                        change_percent = ((current_price - prev_price) / prev_price) * 100
                    else:
                        change_percent = 0.0
                    
                    # 获取最近7天的历史数据（用于sparkline）
                    history_prices = hist['Close'].tail(7).tolist()
                    history_prices = [float(p) for p in history_prices]
                    
                    result.update({
                        'price': current_price,
                        'change_percent_24h': change_percent,
                        'history': history_prices,
                        'symbol': attempt_symbol,  # 更新为实际使用的符号
                        'last_updated': datetime.now().isoformat()
                    })
                    
                    logger.info(f"✓ {name} ({attempt_symbol}): ${current_price:.4f} ({change_percent:+.2f}%)")
                    return result
                    
                except Exception as e:
                    logger.warning(f"Attempt {retry_count + 1} failed for {attempt_symbol}: {e}")
                    continue
            
            if retry_count < self.max_retries - 1:
                time.sleep(1)  # 重试前等待1秒
        
        # 如果所有尝试都失败，标记为不可用
        result['error'] = f"Failed to fetch data for {name} after {self.max_retries} retries"
        logger.error(result['error'])
        return result
    
    def get_binance_data(self, symbol: str, name: str) -> Dict[str, Any]:
        """获取 Binance 数据（作为 crypto 的 fallback）"""
        result = {
            'symbol': symbol,
            'name': name,
            'price': None,
            'change_percent_24h': None,
            'history': [],
            'error': None,
            'source': 'binance'
        }
        
        try:
            # 获取24小时价格统计
            ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            response = requests.get(ticker_url, timeout=self.timeout)
            response.raise_for_status()
            ticker_data = response.json()
            
            # 获取K线历史数据（最近7天）
            klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=7"
            klines_response = requests.get(klines_url, timeout=self.timeout)
            klines_response.raise_for_status()
            klines_data = klines_response.json()
            
            # 解析数据
            current_price = float(ticker_data['lastPrice'])
            change_percent = float(ticker_data['priceChangePercent'])
            
            # 历史价格（收盘价）
            history_prices = [float(kline[4]) for kline in klines_data]  # 收盘价是第5个元素
            
            result.update({
                'price': current_price,
                'change_percent_24h': change_percent,
                'history': history_prices,
                'last_updated': datetime.now().isoformat()
            })
            
            logger.info(f"✓ {name} ({symbol}): ${current_price:.4f} ({change_percent:+.2f}%)")
            
        except Exception as e:
            result['error'] = f"Failed to fetch Binance data: {e}"
            logger.error(result['error'])
        
        return result
    
    def get_eodhd_data(self, symbol: str, name: str, yahoo_symbol: str = None) -> Dict[str, Any]:
        """获取 EODHD 实时数据"""
        result = {
            'symbol': symbol,
            'name': name,
            'price': None,
            'change_percent_24h': None,
            'prev_close': None,
            'history': [],
            'error': None,
            'source': 'eodhd'
        }
        
        api_key_path = os.path.join('./.config/api_keys/eodhd')
        try:
            with open(api_key_path) as f:
                api_key = f.read().strip()
        except:
            result['error'] = "EODHD API key not found"
            logger.error(result['error'])
            return result
        
        for retry in range(self.max_retries):
            try:
                url = f"https://eodhd.com/api/real-time/{symbol}?api_token={api_key}&fmt=json"
                resp = requests.get(url, timeout=self.timeout, headers={'User-Agent': 'MarketDashboard/1.0'})
                resp.raise_for_status()
                data = resp.json()
                
                close_price = data.get('close')
                prev_close = data.get('previousClose')
                change_p = data.get('change_p')
                
                if close_price in (None, 'NA', 0) or prev_close in (None, 'NA', 0):
                    result['error'] = f"EODHD returned NA for {symbol}"
                    logger.warning(result['error'])
                    # Try Yahoo fallback
                    fallback_sym = yahoo_symbol or symbol
                    return self.get_yahoo_data(fallback_sym, name)
                
                result.update({
                    'price': float(close_price),
                    'change_percent_24h': float(change_p) if change_p not in (None, 'NA') else 0,
                    'prev_close': float(prev_close),
                    'last_updated': datetime.now().isoformat()
                })
                
                # Get history from Yahoo for sparkline
                if yahoo_symbol:
                    try:
                        ticker = yf.Ticker(yahoo_symbol)
                        hist = ticker.history(period="8d", interval="1d", timeout=self.timeout)
                        if not hist.empty:
                            result['history'] = [float(p) for p in hist['Close'].tail(7).tolist()]
                    except:
                        pass
                
                logger.info(f"✓ {name} ({symbol}): ${float(close_price):.4f} ({float(change_p):+.2f}%) [eodhd]")
                return result
                
            except Exception as e:
                logger.warning(f"EODHD attempt {retry + 1} failed for {symbol}: {e}")
                if retry < self.max_retries - 1:
                    time.sleep(1)
        
        # Fallback to Yahoo
        fallback_sym = yahoo_symbol or symbol
        logger.info(f"Falling back to Yahoo for {name} ({fallback_sym})")
        return self.get_yahoo_data(fallback_sym, name)

    def get_goldprice_data(self, symbol: str, name: str, yahoo_symbol: str = None) -> Dict[str, Any]:
        """获取 GoldPrice.org 贵金属现货数据（XAU/XAG）"""
        result = {
            'symbol': symbol,
            'name': name,
            'price': None,
            'change_percent_24h': None,
            'prev_close': None,
            'history': [],
            'error': None,
            'source': 'goldprice'
        }

        # Fetch from goldprice API (cache to avoid duplicate calls for XAU+XAG)
        if self._goldprice_cache is None:
            for retry in range(self.max_retries):
                try:
                    resp = requests.get(
                        'https://data-asg.goldprice.org/dbXRates/USD',
                        timeout=self.timeout,
                        headers={'User-Agent': 'MarketDashboard/1.0'}
                    )
                    resp.raise_for_status()
                    self._goldprice_cache = resp.json()
                    break
                except Exception as e:
                    logger.warning(f"GoldPrice API attempt {retry + 1} failed: {e}")
                    if retry < self.max_retries - 1:
                        time.sleep(1)

        if not self._goldprice_cache:
            result['error'] = f"Failed to fetch GoldPrice data after {self.max_retries} retries"
            logger.error(result['error'])
            return result

        try:
            items = self._goldprice_cache.get('items', [])
            if not items:
                result['error'] = "No items in GoldPrice response"
                logger.error(result['error'])
                return result

            item = items[0]

            # Map symbol to goldprice fields
            if symbol == 'XAUUSD':
                price = float(item['xauPrice'])
                change_pct = float(item['pcXau'])
                prev_close = float(item['xauClose'])
            elif symbol == 'XAGUSD':
                price = float(item['xagPrice'])
                change_pct = float(item['pcXag'])
                prev_close = float(item['xagClose'])
            else:
                result['error'] = f"Unknown goldprice symbol: {symbol}"
                logger.error(result['error'])
                return result

            result.update({
                'price': price,
                'change_percent_24h': change_pct,
                'prev_close': prev_close,
                'last_updated': datetime.now().isoformat()
            })

            # Get 7-day history from Yahoo (goldprice API has no historical data)
            fallback_sym = yahoo_symbol or ('GC=F' if symbol == 'XAUUSD' else 'SI=F')
            try:
                ticker = yf.Ticker(fallback_sym)
                hist = ticker.history(period="8d", interval="1d", timeout=self.timeout)
                if not hist.empty:
                    history_prices = hist['Close'].tail(7).tolist()
                    result['history'] = [float(p) for p in history_prices]
                    logger.info(f"  ↳ Yahoo history ({fallback_sym}): {len(result['history'])} points")
            except Exception as e:
                logger.warning(f"  ↳ Yahoo history fallback failed for {fallback_sym}: {e}")

            logger.info(f"✓ {name} ({symbol}): ${price:.4f} ({change_pct:+.2f}%) [goldprice.org]")

        except Exception as e:
            result['error'] = f"Failed to parse GoldPrice data: {e}"
            logger.error(result['error'])

        return result

    def fetch_all_data(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """获取所有品种的数据，返回 (latest_data, history_data)"""
        latest_data = {
            'updated_at': datetime.now().isoformat(),
            'assets': {}
        }
        
        history_data = {}
        
        meta = {
            'total_assets': 0,
            'successful_fetches': 0,
            'failed_fetches': 0
        }
        
        for category in self.config['categories']:
            for asset in category['assets']:
                symbol = asset['symbol']
                logger.info(f"Fetching data for {asset['name']} ({symbol})...")
                
                if asset['source'] == 'goldprice':
                    data = self.get_goldprice_data(symbol, asset['name'], asset.get('yahoo_symbol'))
                elif asset['source'] == 'eodhd':
                    data = self.get_eodhd_data(symbol, asset['name'], asset.get('yahoo_symbol'))
                elif asset['source'] == 'yahoo':
                    data = self.get_yahoo_data(symbol, asset['name'])
                elif asset['source'] == 'binance':
                    data = self.get_binance_data(symbol, asset['name'])
                else:
                    data = {
                        'symbol': symbol,
                        'name': asset['name'],
                        'price': None,
                        'change_percent_24h': None,
                        'history': [],
                        'error': f"Unknown source: {asset['source']}",
                        'source': asset['source']
                    }
                    logger.error(data['error'])
                
                # 构建 latest_data 按照 TDD.md 格式
                if data['error']:
                    latest_data['assets'][symbol] = {
                        'error': True,
                        'name': asset['name'],
                        'updated': datetime.now().isoformat()
                    }
                    meta['failed_fetches'] += 1
                else:
                    # 计算前收盘价（优先使用数据源提供的值）
                    prev_close = data.get('prev_close')
                    if prev_close is None:
                        if data['history'] and len(data['history']) >= 2:
                            prev_close = data['history'][-2]
                        elif data['price'] and data['change_percent_24h'] is not None:
                            prev_close = data['price'] / (1 + data['change_percent_24h'] / 100)
                    
                    final_price = data['price']
                    final_change = data['change_percent_24h']
                    final_prev = prev_close
                    
                    # Invert price for USD/EUR style display
                    if asset.get('invert') and final_price and final_price > 0:
                        final_price = 1 / final_price
                        if final_change is not None:
                            final_change = -final_change
                        if final_prev and final_prev > 0:
                            final_prev = 1 / final_prev
                    
                    latest_data['assets'][symbol] = {
                        'price': final_price,
                        'change_pct': final_change,
                        'prev_close': final_prev,
                        'name': asset['name'],
                        'updated': data.get('last_updated', datetime.now().isoformat()),
                        'unit': asset['unit'],
                        'icon': asset['icon'],
                        'category': category['id']
                    }
                    meta['successful_fetches'] += 1
                
                # 构建 history_data
                if data['history'] and len(data['history']) > 0:
                    # 生成日期序列（最近7天）
                    dates = []
                    for i in range(len(data['history'])):
                        date = (datetime.now() - timedelta(days=len(data['history'])-1-i)).strftime('%Y-%m-%d')
                        dates.append(date)
                    
                    history_data[symbol] = {
                        'dates': dates,
                        'prices': data['history']
                    }
                
                meta['total_assets'] += 1
        
        latest_data['meta'] = meta
        return latest_data, history_data
    
    def save_data(self, latest_data: Dict[str, Any], history_data: Dict[str, Any]) -> None:
        """保存数据到文件"""
        # 确保 data 目录存在
        os.makedirs('data', exist_ok=True)
        
        # 保存最新数据（按 TDD.md 格式）
        with open('data/latest.json', 'w', encoding='utf-8') as f:
            json.dump(latest_data, f, indent=2, ensure_ascii=False)
        
        # 保存历史数据（按品种分组的7天历史）
        with open('data/history.json', 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        logger.info("Data saved to data/latest.json and data/history.json")


def test_single_asset(symbol: str):
    """测试单个品种数据获取"""
    fetcher = MarketDataFetcher()
    
    # 查找品种配置
    asset_config = None
    for category in fetcher.config['categories']:
        for asset in category['assets']:
            if asset['symbol'] == symbol:
                asset_config = asset
                break
        if asset_config:
            break
    
    if not asset_config:
        logger.error(f"Symbol {symbol} not found in config.json")
        return False
    
    logger.info(f"Testing {asset_config['name']} ({symbol})...")
    
    try:
        if asset_config['source'] == 'goldprice':
            data = fetcher.get_goldprice_data(symbol, asset_config['name'], asset_config.get('yahoo_symbol'))
        elif asset_config['source'] == 'yahoo':
            data = fetcher.get_yahoo_data(symbol, asset_config['name'])
        elif asset_config['source'] == 'binance':
            data = fetcher.get_binance_data(symbol, asset_config['name'])
        else:
            logger.error(f"Unknown source: {asset_config['source']}")
            return False
        
        if data['error']:
            logger.error(f"❌ {symbol}: {data['error']}")
            return False
        else:
            logger.info(f"✅ {symbol}: ${data['price']:.4f} ({data['change_percent_24h']:+.2f}%) | History: {len(data['history'])} points")
            return True
            
    except Exception as e:
        logger.error(f"❌ {symbol}: Exception - {e}")
        return False


def main():
    """主函数"""
    import sys
    
    # 检查是否是测试模式
    if len(sys.argv) == 3 and sys.argv[1] == '--test':
        symbol = sys.argv[2]
        success = test_single_asset(symbol)
        exit(0 if success else 1)
    
    try:
        fetcher = MarketDataFetcher()
        logger.info("Starting market data fetch...")
        
        latest_data, history_data = fetcher.fetch_all_data()
        
        # 打印摘要
        meta = latest_data['meta']
        logger.info(f"Fetch completed: {meta['successful_fetches']}/{meta['total_assets']} successful")
        
        if meta['failed_fetches'] > 0:
            logger.warning(f"{meta['failed_fetches']} assets failed to fetch")
        
        fetcher.save_data(latest_data, history_data)
        logger.info("Market data fetch completed successfully!")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()