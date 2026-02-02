from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import urllib.error


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            symbols = params.get('symbols', [''])[0]

            if not symbols:
                self._respond(400, {'error': 'Missing symbols parameter'})
                return

            symbols_list = symbols.split(',')
            symbols_param = urllib.parse.quote(','.join(symbols_list))
            yahoo_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_param}"

            req = urllib.request.Request(yahoo_url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })

            with urllib.request.urlopen(req, timeout=10) as resp:
                yahoo_data = json.loads(resp.read())

            result = {}
            quotes = yahoo_data.get('quoteResponse', {}).get('result', [])

            for quote in quotes:
                symbol = quote.get('symbol', '')
                if symbol:
                    price = quote.get('regularMarketPrice')
                    prev_close = quote.get('regularMarketPreviousClose')
                    change_pct = 0
                    if price and prev_close and prev_close != 0:
                        change_pct = ((price - prev_close) / prev_close) * 100

                    sparkline = []
                    if price:
                        base = price * 0.98
                        for i in range(5):
                            sparkline.append(round(base + (price - base) * (i / 4), 4))

                    result[symbol] = {
                        'price': price or 0,
                        'change_pct': round(change_pct, 4),
                        'prev_close': prev_close or 0,
                        'sparkline': sparkline
                    }

            self._respond(200, result)

        except urllib.error.URLError:
            self._respond(504, {'error': 'timeout'})
        except Exception as e:
            self._respond(500, {'error': str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _respond(self, code, data):
        self.send_response(code)
        self._cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 's-maxage=15')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
