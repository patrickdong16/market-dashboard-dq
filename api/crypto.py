from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            symbols = params.get('symbols', [''])[0]

            if not symbols:
                self._respond(400, {'error': 'Missing symbols parameter'})
                return

            symbol_list = [s.strip().upper() for s in symbols.split(',') if s.strip()]
            results = {}

            for symbol in symbol_list:
                try:
                    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={urllib.parse.quote(symbol)}"
                    req = urllib.request.Request(url, headers={
                        'User-Agent': 'Mozilla/5.0'
                    })
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                        price = float(data.get('lastPrice', 0))
                        change_pct = float(data.get('priceChangePercent', 0))
                        prev_close = float(data.get('prevClosePrice', 0))
                        results[symbol] = {
                            'price': price,
                            'change_pct': round(change_pct, 4),
                            'prev_close': prev_close,
                            'sparkline': []
                        }
                except Exception as e:
                    results[symbol] = {'error': str(e)}

            self._respond(200, results)

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
        self.send_header('Cache-Control', 's-maxage=30')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
