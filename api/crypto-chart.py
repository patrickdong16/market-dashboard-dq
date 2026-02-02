from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            symbol = params.get('symbol', [''])[0]
            range_val = params.get('range', ['3mo'])[0]

            if not symbol:
                self._respond(400, {'error': 'Missing symbol parameter'})
                return

            # Map range to Binance klines limit
            range_map = {
                '5d': 7,
                '1mo': 30,
                '3mo': 90,
                '6mo': 180,
                '1y': 365,
                '2y': 730
            }
            limit = range_map.get(range_val, 90)

            url = f"https://api.binance.com/api/v3/klines?symbol={urllib.parse.quote(symbol)}&interval=1d&limit={limit}"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0'
            })

            with urllib.request.urlopen(req, timeout=10) as resp:
                klines = json.loads(resp.read())

            data = []
            for k in klines:
                data.append({
                    'time': int(k[0]) // 1000,
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })

            self._respond(200, {
                'symbol': symbol,
                'range': range_val,
                'data': data
            })

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
        self.send_header('Cache-Control', 's-maxage=60')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
