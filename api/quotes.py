"""EODHD real-time quotes endpoint for Market Dashboard homepage.

Primary: EODHD real-time API
Fallback: Yahoo Finance v8 chart API
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.parse
import urllib.error
import traceback


EODHD_API_KEY = os.environ.get('EODHD_API_KEY', '')


def fetch_eodhd_realtime(symbol):
    """Fetch real-time quote from EODHD API."""
    url = (
        f"https://eodhd.com/api/real-time/{urllib.parse.quote(symbol, safe='')}"
        f"?api_token={EODHD_API_KEY}&fmt=json"
    )
    req = urllib.request.Request(url, headers={
        'User-Agent': 'MarketDashboard/1.0'
    })
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read())

    close_price = data.get('close')
    prev_close = data.get('previousClose')
    change_p = data.get('change_p')

    # Validate: EODHD sometimes returns "NA" for unavailable symbols
    if close_price in (None, 'NA', 0) or prev_close in (None, 'NA', 0):
        return None

    close_price = float(close_price)
    prev_close = float(prev_close)
    change_p = float(change_p) if change_p not in (None, 'NA') else 0

    return {
        'price': close_price,
        'change_pct': round(change_p, 4),
        'prev_close': prev_close,
        'sparkline': [],
        'source': 'eodhd'
    }


def fetch_yahoo_realtime(symbol):
    """Fallback: fetch quote from Yahoo Finance."""
    encoded = urllib.parse.quote(symbol)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?range=5d&interval=1d&includePrePost=false"
    )
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read())

    chart_result = data.get('chart', {}).get('result', [])
    if not chart_result:
        return None

    meta = chart_result[0].get('meta', {})
    price = meta.get('regularMarketPrice', 0)
    prev_close = meta.get('chartPreviousClose', 0)

    if not price:
        return None

    change_pct = 0
    if price and prev_close and prev_close != 0:
        change_pct = ((price - prev_close) / prev_close) * 100

    return {
        'price': price,
        'change_pct': round(change_pct, 4),
        'prev_close': prev_close or 0,
        'sparkline': [],
        'source': 'yahoo'
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            symbols_str = params.get('symbols', [''])[0]
            yahoo_symbols_str = params.get('yahoo_symbols', [''])[0]

            if not symbols_str:
                self._respond(400, {'error': 'Missing symbols parameter'})
                return

            symbols_list = [s.strip() for s in symbols_str.split(',') if s.strip()]
            yahoo_list = [s.strip() for s in yahoo_symbols_str.split(',') if s.strip()]

            # Build yahoo fallback map: eodhd_symbol -> yahoo_symbol
            yahoo_map = {}
            for i, sym in enumerate(symbols_list):
                if i < len(yahoo_list) and yahoo_list[i]:
                    yahoo_map[sym] = yahoo_list[i]

            result = {}
            errors = []

            for sym in symbols_list:
                # Try EODHD first
                if EODHD_API_KEY:
                    try:
                        data = fetch_eodhd_realtime(sym)
                        if data:
                            result[sym] = data
                            continue
                    except Exception as e:
                        errors.append(f"{sym}: EODHD error: {str(e)}")

                # Fallback to Yahoo
                yahoo_sym = yahoo_map.get(sym, sym)
                try:
                    data = fetch_yahoo_realtime(yahoo_sym)
                    if data:
                        result[sym] = data
                        continue
                except Exception as e:
                    errors.append(f"{sym}: Yahoo fallback error ({yahoo_sym}): {str(e)}")

                errors.append(f"{sym}: all sources failed")

            response = result
            if errors and not result:
                response = {'error': 'all symbols failed', 'details': errors}
                self._respond(502, response)
            else:
                if errors:
                    response['_errors'] = errors
                self._respond(200, response)

        except Exception as e:
            self._respond(500, {
                'error': str(e),
                'type': type(e).__name__,
                'trace': traceback.format_exc()
            })

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _respond(self, code, data):
        self.send_response(code)
        self._cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 's-maxage=20')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
