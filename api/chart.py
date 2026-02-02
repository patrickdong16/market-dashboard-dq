import json
import urllib.request
import urllib.parse
import urllib.error


def handler(request):
    """Vercel Serverless Function: proxy Yahoo Finance chart data for K-line."""
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(request.url if hasattr(request, 'url') else f"http://localhost{request.get('path', '/')}")
    params = parse_qs(parsed.query)

    symbol = params.get('symbol', [''])[0]
    range_val = params.get('range', ['3mo'])[0]
    interval = params.get('interval', ['1d'])[0]

    if not symbol:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Missing symbol parameter'})
        }

    # Validate range
    valid_ranges = ['5d', '1mo', '3mo', '6mo', '1y', '2y']
    if range_val not in valid_ranges:
        range_val = '3mo'

    try:
        yahoo_url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
            f"?range={range_val}&interval={interval}&includePrePost=false"
        )

        req = urllib.request.Request(yahoo_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        with urllib.request.urlopen(req, timeout=10) as resp:
            yahoo_data = json.loads(resp.read())

        chart_result = yahoo_data.get('chart', {}).get('result', [])
        if not chart_result:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'No data found'})
            }

        data = chart_result[0]
        timestamps = data.get('timestamp', [])
        indicators = data.get('indicators', {})
        quote = indicators.get('quote', [{}])[0]

        opens = quote.get('open', [])
        highs = quote.get('high', [])
        lows = quote.get('low', [])
        closes = quote.get('close', [])
        volumes = quote.get('volume', [])

        # Build OHLCV array for TradingView Lightweight Charts
        ohlcv = []
        for i in range(len(timestamps)):
            if closes[i] is not None:
                ohlcv.append({
                    'time': timestamps[i],
                    'open': opens[i] or closes[i],
                    'high': highs[i] or closes[i],
                    'low': lows[i] or closes[i],
                    'close': closes[i],
                    'volume': volumes[i] if i < len(volumes) else 0
                })

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
                'Cache-Control': 's-maxage=60'
            },
            'body': json.dumps({
                'symbol': symbol,
                'range': range_val,
                'interval': interval,
                'data': ohlcv
            })
        }

    except urllib.error.URLError:
        return {
            'statusCode': 504,
            'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'timeout'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
