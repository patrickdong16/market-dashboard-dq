"""EODHD chart data endpoint for Market Dashboard detail pages.

Handles:
  - Intraday (5m) data for "today" view
  - EOD (daily) data for 3M / 1Y views
  - Yahoo Finance fallback

Query params:
  symbol    - EODHD symbol (e.g. GLD.US, BTC-USD.CC)
  range     - 1d | 5d | 3mo | 1y
  interval  - 5m | 1d (ignored for EODHD; inferred from range)
  yahoo_symbol - Optional Yahoo symbol for fallback
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from datetime import datetime, timedelta


EODHD_API_KEY = os.environ.get('EODHD_API_KEY', '')


# ─── EODHD helpers ───────────────────────────────────────────────

def fetch_eodhd_intraday(symbol):
    """Fetch intraday 5-minute bars from EODHD.
    
    Uses 'from' param (unix timestamp) to limit to last ~2 days of data,
    keeping the response small. Frontend filters to last trading day.
    """
    from_ts = int(time.time()) - 2 * 86400  # last 2 days
    url = (
        f"https://eodhd.com/api/intraday/{urllib.parse.quote(symbol, safe='')}"
        f"?api_token={EODHD_API_KEY}&interval=5m&fmt=json&from={from_ts}"
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'MarketDashboard/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = json.loads(resp.read())

    if not raw or not isinstance(raw, list):
        return []

    ohlcv = []
    for bar in raw:
        close = bar.get('close')
        if close is None or close == 'NA':
            continue
        ohlcv.append({
            'time': int(bar['timestamp']),
            'open': float(bar.get('open') or close),
            'high': float(bar.get('high') or close),
            'low': float(bar.get('low') or close),
            'close': float(close),
            'volume': int(bar.get('volume') or 0)
        })
    return ohlcv


def fetch_eodhd_eod(symbol, from_date):
    """Fetch daily OHLCV bars from EODHD EOD API.
    
    Returns date strings (YYYY-MM-DD) as time values for BusinessDay format.
    This eliminates timezone-related date offset issues in daily charts.
    
    Args:
        symbol: EODHD symbol (e.g. GLD.US)
        from_date: ISO date string YYYY-MM-DD
    """
    url = (
        f"https://eodhd.com/api/eod/{urllib.parse.quote(symbol, safe='')}"
        f"?api_token={EODHD_API_KEY}&fmt=json&from={from_date}"
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'MarketDashboard/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = json.loads(resp.read())

    if not raw or not isinstance(raw, list):
        return []

    ohlcv = []
    for bar in raw:
        close = bar.get('close')
        if close is None or close == 'NA':
            continue
        date_str = bar.get('date', '')
        if not date_str:
            continue
        # Validate date format
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            continue
        ohlcv.append({
            'time': date_str,
            'open': float(bar.get('open') or close),
            'high': float(bar.get('high') or close),
            'low': float(bar.get('low') or close),
            'close': float(close),
            'volume': int(bar.get('volume') or 0)
        })
    return ohlcv


def range_to_from_date(range_val):
    """Convert a range string to a 'from' date for EODHD EOD API."""
    now = datetime.utcnow()
    if range_val == '5d':
        delta = timedelta(days=10)  # extra buffer for weekends
    elif range_val in ('1mo', '1m'):
        delta = timedelta(days=35)
    elif range_val == '3mo':
        delta = timedelta(days=95)
    elif range_val == '6mo':
        delta = timedelta(days=185)
    elif range_val == '1y':
        delta = timedelta(days=370)
    elif range_val == '2y':
        delta = timedelta(days=740)
    else:
        delta = timedelta(days=95)
    return (now - delta).strftime('%Y-%m-%d')


# ─── Yahoo fallback ──────────────────────────────────────────────

def fetch_yahoo_chart(symbol, range_val, interval):
    """Fallback: fetch chart data from Yahoo Finance.
    
    For daily interval, returns date strings (YYYY-MM-DD) as time values.
    For intraday interval, returns Unix timestamps.
    """
    crumb, cj, opener = _get_yahoo_crumb()
    yahoo_url = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
        f"?range={range_val}&interval={interval}&crumb={urllib.parse.quote(crumb)}"
    )
    req = urllib.request.Request(yahoo_url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with opener.open(req, timeout=6) as resp:
        yahoo_data = json.loads(resp.read())

    chart_result = yahoo_data.get('chart', {}).get('result', [])
    if not chart_result:
        return []

    data = chart_result[0]
    timestamps = data.get('timestamp') or []
    quote = data.get('indicators', {}).get('quote', [{}])[0]
    opens = quote.get('open', [])
    highs = quote.get('high', [])
    lows = quote.get('low', [])
    closes = quote.get('close', [])
    volumes = quote.get('volume', [])

    use_date_strings = (interval == '1d')

    ohlcv = []
    for i in range(len(timestamps)):
        if i < len(closes) and closes[i] is not None:
            ts = timestamps[i]
            if use_date_strings:
                # Convert Unix timestamp to UTC date string
                # Yahoo daily timestamps are at market close or midnight UTC
                time_val = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
            else:
                time_val = ts
            ohlcv.append({
                'time': time_val,
                'open': opens[i] if i < len(opens) and opens[i] else closes[i],
                'high': highs[i] if i < len(highs) and highs[i] else closes[i],
                'low': lows[i] if i < len(lows) and lows[i] else closes[i],
                'close': closes[i],
                'volume': volumes[i] if i < len(volumes) and volumes[i] else 0
            })
    return ohlcv


def _get_yahoo_crumb():
    """Get Yahoo Finance crumb and cookies for authenticated API access."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')]
    opener.open('https://fc.yahoo.com', timeout=3)
    crumb_req = urllib.request.Request('https://query2.finance.yahoo.com/v1/test/getcrumb')
    crumb_req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    with opener.open(crumb_req, timeout=3) as resp:
        crumb = resp.read().decode('utf-8')
    return crumb, cj, opener


# ─── Main handler ────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            symbol = params.get('symbol', [''])[0]
            range_val = params.get('range', ['3mo'])[0]
            interval = params.get('interval', ['1d'])[0]
            yahoo_symbol = params.get('yahoo_symbol', [''])[0]

            if not symbol:
                self._respond(400, {'error': 'Missing symbol parameter'})
                return

            ohlcv = []
            source_used = 'none'

            # ── Try EODHD first ──
            if EODHD_API_KEY:
                try:
                    if interval == '5m':
                        ohlcv = fetch_eodhd_intraday(symbol)
                        source_used = 'eodhd_intraday'
                    else:
                        from_date = range_to_from_date(range_val)
                        ohlcv = fetch_eodhd_eod(symbol, from_date)
                        source_used = 'eodhd_eod'
                except Exception:
                    ohlcv = []

            # ── Fallback to Yahoo ──
            if not ohlcv:
                fallback_sym = yahoo_symbol or symbol
                try:
                    yahoo_range = range_val
                    if range_val == '3mo':
                        yahoo_range = '3mo'
                    elif range_val == '1y':
                        yahoo_range = '1y'

                    ohlcv = fetch_yahoo_chart(fallback_sym, yahoo_range, interval)
                    source_used = 'yahoo'
                except Exception:
                    pass

            # ── Fallback: unauthenticated Yahoo ──
            if not ohlcv and (yahoo_symbol or symbol):
                fallback_sym = yahoo_symbol or symbol
                try:
                    yahoo_url = (
                        f"https://query2.finance.yahoo.com/v8/finance/chart/"
                        f"{urllib.parse.quote(fallback_sym)}"
                        f"?range={range_val}&interval={interval}"
                    )
                    req = urllib.request.Request(yahoo_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    })
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        yahoo_data = json.loads(resp.read())
                    chart_result = yahoo_data.get('chart', {}).get('result', [])
                    use_date_strings = (interval == '1d')
                    if chart_result:
                        data = chart_result[0]
                        timestamps = data.get('timestamp') or []
                        quote = data.get('indicators', {}).get('quote', [{}])[0]
                        closes = quote.get('close', [])
                        opens = quote.get('open', [])
                        highs = quote.get('high', [])
                        lows = quote.get('low', [])
                        volumes = quote.get('volume', [])
                        for i in range(len(timestamps)):
                            if i < len(closes) and closes[i] is not None:
                                ts = timestamps[i]
                                if use_date_strings:
                                    time_val = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
                                else:
                                    time_val = ts
                                ohlcv.append({
                                    'time': time_val,
                                    'open': opens[i] if i < len(opens) and opens[i] else closes[i],
                                    'high': highs[i] if i < len(highs) and highs[i] else closes[i],
                                    'low': lows[i] if i < len(lows) and lows[i] else closes[i],
                                    'close': closes[i],
                                    'volume': volumes[i] if i < len(volumes) and volumes[i] else 0
                                })
                        source_used = 'yahoo_unauth'
                except Exception:
                    pass

            if not ohlcv:
                self._respond(404, {'error': 'No data from any source', 'symbol': symbol})
                return

            # Determine time_format based on interval
            # Daily data uses date strings, intraday uses Unix timestamps
            time_format = 'date' if interval == '1d' else 'timestamp'

            self._respond(200, {
                'symbol': symbol,
                'range': range_val,
                'interval': interval,
                'source': source_used,
                'time_format': time_format,
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
