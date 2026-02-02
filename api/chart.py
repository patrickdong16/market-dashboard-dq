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
            symbol = params.get('symbol', [''])[0]
            range_val = params.get('range', ['3mo'])[0]
            interval = params.get('interval', ['1d'])[0]

            if not symbol:
                self._respond(400, {'error': 'Missing symbol parameter'})
                return

            valid_ranges = ['1d', '2d', '5d', '1mo', '3mo', '6mo', '1y', '2y']
            if range_val not in valid_ranges:
                range_val = '3mo'

            valid_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1d', '5d', '1wk', '1mo']
            if interval not in valid_intervals:
                interval = '1d'

            yahoo_url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
                f"?range={range_val}&interval={interval}"
            )

            req = urllib.request.Request(yahoo_url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })

            with urllib.request.urlopen(req, timeout=10) as resp:
                yahoo_data = json.loads(resp.read())

            chart_result = yahoo_data.get('chart', {}).get('result', [])
            if not chart_result:
                self._respond(404, {'error': 'No data found', 'raw': str(yahoo_data)[:500]})
                return

            data = chart_result[0]
            timestamps = data.get('timestamp') or []
            quote = data.get('indicators', {}).get('quote', [{}])[0]

            opens = quote.get('open', [])
            highs = quote.get('high', [])
            lows = quote.get('low', [])
            closes = quote.get('close', [])
            volumes = quote.get('volume', [])

            ohlcv = []
            for i in range(len(timestamps)):
                if i < len(closes) and closes[i] is not None:
                    ohlcv.append({
                        'time': timestamps[i],
                        'open': opens[i] if i < len(opens) and opens[i] else closes[i],
                        'high': highs[i] if i < len(highs) and highs[i] else closes[i],
                        'low': lows[i] if i < len(lows) and lows[i] else closes[i],
                        'close': closes[i],
                        'volume': volumes[i] if i < len(volumes) and volumes[i] else 0
                    })

            self._respond(200, {
                'symbol': symbol,
                'range': range_val,
                'interval': interval,
                'data': ohlcv
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
        self.send_header('Cache-Control', 's-maxage=30')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
