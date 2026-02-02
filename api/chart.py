import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler
import time

def handler(request):
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json',
        'Cache-Control': 's-maxage=60'
    }
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return ('', 200, headers)
    
    if request.method != 'GET':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        # Parse query parameters
        symbol = request.args.get('symbol', '')
        range_param = request.args.get('range', '3mo')
        interval = request.args.get('interval', '1d')
        
        if not symbol:
            return (json.dumps({'error': 'Missing symbol parameter'}), 400, headers)
        
        # Map range to periods
        range_mapping = {
            '5d': ('5d', '1d'),
            '1mo': ('1mo', '1d'),
            '3mo': ('3mo', '1d'),
            '1y': ('1y', '1d')
        }
        
        if range_param not in range_mapping:
            return (json.dumps({'error': 'Invalid range parameter'}), 400, headers)
        
        period1 = int(time.time()) - (365 * 24 * 60 * 60)  # 1 year ago
        period2 = int(time.time())
        
        # Adjust period1 based on range
        if range_param == '5d':
            period1 = int(time.time()) - (5 * 24 * 60 * 60)
        elif range_param == '1mo':
            period1 = int(time.time()) - (30 * 24 * 60 * 60)
        elif range_param == '3mo':
            period1 = int(time.time()) - (90 * 24 * 60 * 60)
        
        # Build Yahoo Finance chart API URL
        symbol_encoded = urllib.parse.quote(symbol)
        yahoo_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol_encoded}?period1={period1}&period2={period2}&interval={interval}"
        
        # Request to Yahoo Finance with timeout
        req = urllib.request.Request(yahoo_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        with urllib.request.urlopen(req, timeout=10) as response:
            yahoo_data = json.loads(response.read())
        
        # Process response
        chart_data = yahoo_data.get('chart', {}).get('result', [])
        if not chart_data:
            return (json.dumps({'error': 'No chart data found'}), 404, headers)
        
        chart = chart_data[0]
        timestamps = chart.get('timestamp', [])
        quotes = chart.get('indicators', {}).get('quote', [])
        
        if not quotes:
            return (json.dumps({'error': 'No quote data found'}), 404, headers)
        
        quote = quotes[0]
        opens = quote.get('open', [])
        highs = quote.get('high', [])
        lows = quote.get('low', [])
        closes = quote.get('close', [])
        volumes = quote.get('volume', [])
        
        # Build OHLCV array for TradingView Lightweight Charts
        ohlcv_data = []
        for i in range(len(timestamps)):
            # Skip if any required value is None
            if (i < len(opens) and opens[i] is not None and
                i < len(highs) and highs[i] is not None and
                i < len(lows) and lows[i] is not None and
                i < len(closes) and closes[i] is not None):
                
                ohlcv_data.append({
                    'time': timestamps[i],
                    'open': opens[i],
                    'high': highs[i],
                    'low': lows[i],
                    'close': closes[i],
                    'volume': volumes[i] if i < len(volumes) and volumes[i] is not None else 0
                })
        
        return (json.dumps(ohlcv_data), 200, headers)
        
    except urllib.error.URLError:
        return (json.dumps({'error': 'timeout'}), 504, headers)
    except Exception as e:
        return (json.dumps({'error': str(e)}), 500, headers)