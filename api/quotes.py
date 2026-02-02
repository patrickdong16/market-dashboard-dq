import json
import urllib.request
import urllib.parse
import urllib.error


def handler(request):
    """Vercel Serverless Function: proxy Yahoo Finance quotes."""
    # Parse query parameters
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(request.url if hasattr(request, 'url') else f"http://localhost{request.get('path', '/')}")
    params = parse_qs(parsed.query)

    symbols = params.get('symbols', [''])[0]
    if not symbols:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'Missing symbols parameter'})
        }

    try:
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

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
                'Cache-Control': 's-maxage=15'
            },
            'body': json.dumps(result)
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
