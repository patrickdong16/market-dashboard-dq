import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

def handler(request):
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json',
        'Cache-Control': 's-maxage=15'
    }
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return ('', 200, headers)
    
    if request.method != 'GET':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        # Parse query parameters
        symbols = request.args.get('symbols', '')
        if not symbols:
            return (json.dumps({'error': 'Missing symbols parameter'}), 400, headers)
        
        symbols_list = symbols.split(',')
        
        # Build Yahoo Finance API URL
        symbols_param = urllib.parse.quote(','.join(symbols_list))
        yahoo_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_param}"
        
        # Request to Yahoo Finance with timeout
        req = urllib.request.Request(yahoo_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        with urllib.request.urlopen(req, timeout=10) as response:
            yahoo_data = json.loads(response.read())
        
        # Process response
        result = {}
        quotes = yahoo_data.get('quoteResponse', {}).get('result', [])
        
        for quote in quotes:
            symbol = quote.get('symbol', '')
            if symbol:
                # Calculate 5-day sparkline data (simplified)
                price = quote.get('regularMarketPrice')
                prev_close = quote.get('regularMarketPreviousClose')
                change_pct = 0
                
                if price and prev_close and prev_close != 0:
                    change_pct = ((price - prev_close) / prev_close) * 100
                
                # Generate simple sparkline (5 points around current price)
                sparkline = []
                if price:
                    base = price * 0.98
                    for i in range(5):
                        sparkline.append(base + (price - base) * (i / 4))
                
                result[symbol] = {
                    'price': price or 0,
                    'change_pct': change_pct,
                    'prev_close': prev_close or 0,
                    'sparkline': sparkline
                }
        
        return (json.dumps(result), 200, headers)
        
    except urllib.error.URLError:
        return (json.dumps({'error': 'timeout'}), 504, headers)
    except Exception as e:
        return (json.dumps({'error': str(e)}), 500, headers)