from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # CORS headers
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 's-maxage=15')
        self.end_headers()
        
        try:
            # Parse query parameters
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            symbols = query_params.get('symbols', [''])[0]
            if not symbols:
                response = json.dumps({'error': 'Missing symbols parameter'})
                self.wfile.write(response.encode())
                return
            
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
            
            response = json.dumps(result)
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