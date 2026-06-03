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
import re
from datetime import datetime, timedelta


EODHD_API_KEY = os.environ.get('EODHD_API_KEY', '')

# ─── GoldPrice.org helpers ───────────────────────────────────────

def fetch_goldprice_data():
    """Fetch real-time spot precious metals from GoldPrice.org.

    Single API call returns both XAU and XAG data.
    """
    url = 'https://data-asg.goldprice.org/dbXRates/USD'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'MarketDashboard/1.0'
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def parse_goldprice_symbol(data, symbol):
    """Parse goldprice API response for a specific symbol (XAUUSD/XAGUSD)."""
    items = data.get('items', [])
    if not items:
        return None

    item = items[0]

    if symbol == 'XAUUSD':
        price = float(item['xauPrice'])
        change_pct = float(item['pcXau'])
        prev_close = float(item['xauClose'])
    elif symbol == 'XAGUSD':
        price = float(item['xagPrice'])
        change_pct = float(item['pcXag'])
        prev_close = float(item['xagClose'])
    else:
        return None

    return {
        'price': price,
        'change_pct': round(change_pct, 4),
        'prev_close': prev_close,
        'sparkline': [],
        'source': 'goldprice'
    }



# ─── HKMA HIBOR helpers ─────────────────────────────────────────

def fetch_hkma_hibor_latest(symbol):
    """Fetch latest HKMA HIBOR fixing from the official HKMA public API.

    Supported synthetic symbols map to HKMA fields, e.g. HIBOR1M -> ir_1m.
    Returns rates in percent per annum.
    """
    tenor_map = {
        'HIBORON': 'ir_overnight',
        'HIBOR1W': 'ir_1w',
        'HIBOR1M': 'ir_1m',
        'HIBOR3M': 'ir_3m',
        'HIBOR6M': 'ir_6m',
        'HIBOR12M': 'ir_12m',
    }
    tenor = tenor_map.get(symbol, 'ir_1m')
    hkab_maturity_map = {
        'HIBORON': 'Overnight',
        'HIBOR1W': '1 Week',
        'HIBOR1M': '1 Month',
        'HIBOR3M': '3 Months',
        'HIBOR6M': '6 Months',
        'HIBOR12M': '12 Months',
    }
    url = (
        'https://api.hkma.gov.hk/public/market-data-and-statistics/'
        'monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily'
        '?segment=hibor.fixing&offset=0'
    )
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MarketDashboard/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read())

        records = raw.get('result', {}).get('records', [])
        records = [r for r in records if r.get(tenor) not in (None, 'NA')]
        if records:
            records = sorted(records, key=lambda r: r.get('end_of_day', ''))
            latest = records[-1]

            # HKMA has occasionally returned a stale page or timed out from Vercel.
            # Prefer the official HKAB fixing page when HKMA is unavailable/stale.
            latest_date = datetime.strptime(latest.get('end_of_day'), '%Y-%m-%d').date()
            if (datetime.utcnow().date() - latest_date).days <= 7:
                prev = records[-2] if len(records) >= 2 else None
                price = float(latest[tenor])
                prev_close = float(prev[tenor]) if prev else price
                change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

                return {
                    'price': price,
                    'change_pct': round(change_pct, 4),
                    'prev_close': prev_close,
                    'sparkline': [float(r[tenor]) for r in records[-7:]],
                    'source': 'hkma_hibor',
                    'as_of_date': latest.get('end_of_day')
                }
    except Exception:
        pass

    return fetch_hkab_hibor_latest(symbol, hkab_maturity_map.get(symbol, '1 Month'))


def fetch_hkab_hibor_latest(symbol, maturity):
    """Fetch latest HIBOR fixing from HKAB's official public rates page.

    HKAB is the fixing publisher. This is the production fallback when HKMA's
    monthly-statistical-bulletin API times out, returns 502, or serves stale rows.
    """
    url = 'https://www.hkab.org.hk/en/rates/hibor'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 MarketDashboard/1.0',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    last_error = None
    html = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode('utf-8', 'replace')
            break
        except Exception as exc:
            last_error = exc
    if html is None:
        raise last_error

    date_match = re.search(r'Rates as at 11:15a\.m\.<br/>Hong Kong Time on (\d{4})-(\d{1,2})-(\d{1,2})\.', html)
    as_of_date = None
    if date_match:
        y, m, d = map(int, date_match.groups())
        as_of_date = f'{y:04d}-{m:02d}-{d:02d}'

    pattern = (
        r'<div class="general_table_cell hibor_maturity"><div>' + re.escape(maturity) +
        r'</div></div><div class="general_table_cell last"><div>([0-9.]+)</div></div>'
    )
    rate_match = re.search(pattern, html)
    if not rate_match:
        raise ValueError(f'HKAB HIBOR rate not found for {maturity}')

    price = float(rate_match.group(1))
    return {
        'price': price,
        'change_pct': 0,
        'prev_close': price,
        'sparkline': [price],
        'source': 'hkab_hibor',
        'as_of_date': as_of_date
    }

# ─── EODHD / Yahoo helpers ──────────────────────────────────────


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


def fetch_eodhd_eod_latest(symbol):
    """Fetch the latest daily close from EODHD EOD API.

    Some index/yield symbols (for example US10Y.INDX and US30Y.INDX)
    do not expose a usable real-time close via EODHD, but their daily EOD
    endpoint is reliable. Return the latest close and day-over-day change.
    """
    from_date = (datetime.utcnow() - timedelta(days=20)).strftime('%Y-%m-%d')
    url = (
        f"https://eodhd.com/api/eod/{urllib.parse.quote(symbol, safe='')}"
        f"?api_token={EODHD_API_KEY}&fmt=json&from={from_date}"
    )
    req = urllib.request.Request(url, headers={
        'User-Agent': 'MarketDashboard/1.0'
    })
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = json.loads(resp.read())

    if not raw or not isinstance(raw, list):
        return None

    bars = [bar for bar in raw if bar.get('close') not in (None, 'NA', 0)]
    if not bars:
        return None

    latest = bars[-1]
    prev = bars[-2] if len(bars) >= 2 else None
    close_price = float(latest['close'])
    prev_close = float(prev['close']) if prev else close_price
    change_pct = ((close_price - prev_close) / prev_close * 100) if prev_close else 0
    sparkline = [float(bar['close']) for bar in bars]

    return {
        'price': close_price,
        'change_pct': round(change_pct, 4),
        'prev_close': prev_close,
        'sparkline': sparkline,
        'source': 'eodhd_eod'
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
    # previousClose is the true previous day close
    # chartPreviousClose is the close at the START of the requested range (wrong for daily change!)
    prev_close = meta.get('previousClose') or meta.get('regularMarketPreviousClose', 0)

    if not price:
        return None

    # If previousClose unavailable, try to compute from recent daily bars
    if not prev_close:
        closes = chart_result[0].get('indicators', {}).get('quote', [{}])[0].get('close', [])
        # Filter out None values and take the second-to-last as prev close
        valid_closes = [c for c in closes if c is not None]
        if len(valid_closes) >= 2:
            prev_close = valid_closes[-2]
        else:
            prev_close = meta.get('chartPreviousClose', 0)  # last resort

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
            sources_str = params.get('sources', [''])[0]

            if not symbols_str:
                self._respond(400, {'error': 'Missing symbols parameter'})
                return

            symbols_list = [s.strip() for s in symbols_str.split(',') if s.strip()]
            yahoo_list = [s.strip() for s in yahoo_symbols_str.split(',') if s.strip()]
            sources_list = [s.strip() for s in sources_str.split(',') if s.strip()]

            # Build per-symbol maps
            yahoo_map = {}
            source_map = {}
            for i, sym in enumerate(symbols_list):
                if i < len(yahoo_list) and yahoo_list[i]:
                    yahoo_map[sym] = yahoo_list[i]
                if i < len(sources_list) and sources_list[i]:
                    source_map[sym] = sources_list[i]

            result = {}
            errors = []

            # Pre-fetch goldprice data if any symbols need it (single API call)
            goldprice_raw = None
            goldprice_syms = [s for s in symbols_list if source_map.get(s) == 'goldprice']
            if goldprice_syms:
                try:
                    goldprice_raw = fetch_goldprice_data()
                except Exception as e:
                    errors.append(f"goldprice API error: {str(e)}")

            for sym in symbols_list:
                source = source_map.get(sym, '')

                # Try goldprice for precious metals
                if source == 'goldprice' and goldprice_raw:
                    try:
                        data = parse_goldprice_symbol(goldprice_raw, sym)
                        if data:
                            result[sym] = data
                            continue
                    except Exception as e:
                        errors.append(f"{sym}: goldprice parse error: {str(e)}")

                # Try HKMA HIBOR for Hong Kong interbank offered rates
                if source == 'hkma_hibor':
                    try:
                        data = fetch_hkma_hibor_latest(sym)
                        if data:
                            result[sym] = data
                            continue
                    except Exception as e:
                        errors.append(f"{sym}: HKMA HIBOR error: {str(e)}")

                # Try EODHD daily close for symbols without reliable real-time quotes
                if source == 'eodhd_eod' and EODHD_API_KEY:
                    try:
                        data = fetch_eodhd_eod_latest(sym)
                        if data:
                            result[sym] = data
                            continue
                    except Exception as e:
                        errors.append(f"{sym}: EODHD EOD error: {str(e)}")

                # Try EODHD
                if source != 'eodhd_eod' and EODHD_API_KEY:
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
        self.send_header('Cache-Control', 's-maxage=10, stale-while-revalidate=5')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
