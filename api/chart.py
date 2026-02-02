from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import time

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # CORS headers
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 's-maxage=60')
        self.end_headers()
        
        try:
            # Parse query parameters
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            symbol = query_params.get('symbol', [''])[0]
            range_param = query_params.get('range', ['3mo'])[0]
            interval = query_params.get('interval', ['1d'])[0]
            
            if not symbol:
                response = json.dumps({'error': 'Missing symbol parameter'})
                self.wfile.write(response.encode())
                return
            
            # Map range to periods
            range_mapping = {
                '5d': 5,
                '1mo': 30,
                '3mo': 90,
                '1y': 365
            }
            
            if range_param not in range_mapping:
                response = json.dumps({'error': 'Invalid range parameter'})
                self.wfile.write(response.encode())
                return
            
            days = range_mapping[range_param]
            period1 = int(time.time()) - (days * 24 * 60 * 60)
            period2 = int(time.time())
            
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
                response = json.dumps({'error': 'No chart data found'})
                self.wfile.write(response.encode())
                return
            
            chart = chart_data[0]
            timestamps = chart.get('timestamp', [])
            quotes = chart.get('indicators', {}).get('quote', [])
            
            if not quotes:
                response = json.dumps({'error': 'No quote data found'})
                self.wfile.write(response.encode())
                return
            
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
            
            response = json.dumps(ohlcv_data)
            self.wfile.write(response.encode())
            
        except urllib.error.URLError:
            response = json.dumps({'error': 'timeout'})
            self.wfile.write(response.encode())
        except Exception as e:
            response = json.dumps({'error': str(e)})
            self.wfile.write(response.encode())
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()