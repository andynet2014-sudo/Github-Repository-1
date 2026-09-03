"""시세 조회 + 가격 마스터 테이블(price_history.csv) 관리.

보유 포지션이든 관심종목(워치리스트)이든, 시세가 필요한 티커는 전부 여기
한 곳에서만 조회·기록한다. positions.csv/watchlist.csv 는 "무엇을 추적할지"만
정의하고, 실제 날짜별 가격은 price_history.csv 에 티커당 하루 한 행으로 쌓인다.
같은 종목이 국내 상장(KRX:000660)과 미국 ADR(SKHY)처럼 다른 티커로 따로
등록돼 있으면 서로 다른 상품이므로 각각 별도 행으로 쌓인다.
"""
import csv
import datetime
import os

from base import DATA, num, read_csv, write_csv, _get_json

NONMARKET = ('현금', '신용')   # positions.csv 안에서 시세 조회 대상이 아닌 섹터

PRICE_HISTORY_COLS = ['date', 'ticker', 'name', 'quote_symbol', 'quote_ccy',
                      'price', 'price_krw', 'open', 'high', 'low', 'source']
# open/high/low 는 price_krw 와 같은 통화(KRW 환산 완료)로 저장한다 — 캔들차트가
# price_krw(종가)와 곧바로 같이 쓸 수 있도록. USD 종목도 그날의 fx로 환산해서 넣는다.


def fetch_krx(code):
    """네이버 우선, 실패하면 야후(.KS -> .KQ)."""
    try:
        d = _get_json('https://polling.finance.naver.com/api/realtime/domestic/stock/' + code)
        item = d['datas'][0]
        return float(str(item['closePrice']).replace(',', '')), 'naver'
    except Exception:
        pass
    for suffix in ('.KS', '.KQ'):
        try:
            d = _get_json('https://query1.finance.yahoo.com/v8/finance/chart/'
                          + code + suffix + '?range=1d&interval=1d')
            return float(d['chart']['result'][0]['meta']['regularMarketPrice']), 'yahoo' + suffix
        except Exception:
            continue
    raise RuntimeError('시세 조회 실패: ' + code)


def fetch_yahoo(symbol):
    d = _get_json('https://query1.finance.yahoo.com/v8/finance/chart/'
                  + symbol + '?range=1d&interval=1d')
    return float(d['chart']['result'][0]['meta']['regularMarketPrice']), 'yahoo'


def fetch_yahoo_history(symbol, start, end):
    """야후 차트 API의 일봉 구간 조회. {'YYYY-MM-DD': {'o','h','l','c'}} 반환
    (당일 진행 중인 마지막 봉은 h/l이 그 시점까지의 값이라 장중엔 계속 바뀔 수 있음 —
    장 마감 후 재조회하면 확정값으로 덮인다). o/h/l이 없는(구버전 응답 등) 봉은
    c 값으로 채워 넣어 최소한 종가 기준 라인은 항상 그릴 수 있게 한다."""
    period1 = int(datetime.datetime.strptime(start, '%Y-%m-%d').timestamp())
    period2 = int(datetime.datetime.strptime(end, '%Y-%m-%d').timestamp()) + 86400
    d = _get_json('https://query1.finance.yahoo.com/v8/finance/chart/%s'
                  '?period1=%d&period2=%d&interval=1d' % (symbol, period1, period2))
    result = d['chart']['result'][0]
    ts = result.get('timestamp') or []
    quote = result['indicators']['quote'][0]
    opens = quote.get('open') or [None] * len(ts)
    highs = quote.get('high') or [None] * len(ts)
    lows = quote.get('low') or [None] * len(ts)
    closes = quote.get('close') or [None] * len(ts)
    out = {}
    for t, o, h, l, c in zip(ts, opens, highs, lows, closes):
        if c is None:
            continue
        day = datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
        out[day] = {'o': o if o is not None else c, 'h': h if h is not None else c,
                    'l': l if l is not None else c, 'c': c}
    return out


def instrument_list(positions):
    """positions.csv(현금/신용 제외) + watchlist.csv 를 합쳐 시세 조회 대상
    티커 목록을 만든다. 같은 티커가 양쪽에 있으면 하나로 합친다(포지션 쪽 이름 우선)."""
    seen = {}
    for w in read_csv('watchlist.csv'):
        seen[w['ticker']] = {'ticker': w['ticker'], 'name': w['name'],
                             'quote_symbol': w['quote_symbol'], 'quote_ccy': w['quote_ccy']}
    for p in positions:
        if p['sector'] in NONMARKET:
            continue
        seen[p['ticker']] = {'ticker': p['ticker'], 'name': p['name'],
                             'quote_symbol': p['quote_symbol'], 'quote_ccy': p['quote_ccy']}
    return list(seen.values())


def fetch_price_table(instruments, do_fetch, asof):
    """{ticker: (원화가격, 출처)} 를 한 번의 조회로 채운다. 실패한 티커는
    price_history.csv 의 가장 최근 값으로 대체하고 실패 목록을 함께 돌려준다."""
    last = {}
    for r in read_csv('price_history.csv'):        # 날짜순 파일이라 마지막 값이 최신
        last[r['ticker']] = r

    fx = None
    if do_fetch and any(i['quote_ccy'] == 'USD' for i in instruments):
        try:
            fx, _ = fetch_yahoo('USDKRW=X')
        except Exception:
            pass   # 실패해도 KRW 종목은 계속 조회한다 — USD 쪽만 캐시로 대체됨

    out, failed, rows = {}, [], []
    for i in instruments:
        t = i['ticker']
        price = price_krw = src = None
        if do_fetch:
            try:
                if i['quote_ccy'] == 'KRW':
                    price, src = fetch_krx(i['quote_symbol'])
                    price_krw = price
                else:
                    if fx is None:
                        raise RuntimeError('환율 없음')
                    price, src = fetch_yahoo(i['quote_symbol'])
                    price_krw, src = price * fx, '%s×FX%.1f' % (src, fx)
            except Exception as e:
                failed.append((t, str(e)[:60]))
        if price is None:
            if t in last:
                price = num(last[t]['price'])
                price_krw = num(last[t]['price_krw'])
                src = 'cache(%s)' % last[t].get('date', '?')
            else:
                failed.append((t, '시세도 캐시도 없음'))
                continue
        out[t] = (round(price_krw, 4), src)
        rows.append({'date': asof, 'ticker': t, 'name': i['name'],
                     'quote_symbol': i['quote_symbol'], 'quote_ccy': i['quote_ccy'],
                     'price': round(price, 4), 'price_krw': round(price_krw, 4), 'source': src})
    return out, failed, rows


def upsert_price_history(date, rows):
    keep = [r for r in read_csv('price_history.csv') if r['date'] != date]
    keep.extend(rows)
    keep.sort(key=lambda r: (r['date'], r['ticker']))
    write_csv('price_history.csv', keep, PRICE_HISTORY_COLS)


def backfill_prices(start_date, end_date=None):
    """과거 구간의 일별 OHLC를 야후에서 소급 조회해 price_history.csv 에 채워 넣는다.
    이미 있는 (날짜,티커) 행의 종가(price/price_krw)는 절대 덮어쓰지 않는다(실측/라이브
    값 보존) — 다만 open/high/low가 비어 있으면(구버전 행, 라이브 수집 당시 조회 실패
    등) 그 칸만 채워 넣는다. 국내 종목은 야후에 .KS/.KQ 로 걸려있어 둘 다 시도한다."""
    end_date = end_date or datetime.date.today().isoformat()
    positions = read_csv('positions.csv')
    instruments = instrument_list(positions)
    existing = read_csv('price_history.csv')
    existing_by_key = {(r['date'], r['ticker']): r for r in existing}

    fx_hist = {}
    if any(i['quote_ccy'] == 'USD' for i in instruments):
        try:
            fx_hist = fetch_yahoo_history('USDKRW=X', start_date, end_date)
        except Exception as e:
            print('  환율 이력 조회 실패: %s' % str(e)[:80])

    new_rows, patched = [], 0
    for i in instruments:
        t = i['ticker']
        try:
            if i['quote_ccy'] == 'KRW':
                hist, used = {}, None
                for suffix in ('.KS', '.KQ'):
                    try:
                        hist = fetch_yahoo_history(i['quote_symbol'] + suffix, start_date, end_date)
                        if hist:
                            used = suffix
                            break
                    except Exception:
                        continue
                if not hist:
                    print('  스킵(과거 시세 없음): %s' % t)
                    continue
                for day, ohlc in hist.items():
                    existing_row = existing_by_key.get((day, t))
                    if existing_row is not None:
                        if not existing_row.get('open'):
                            existing_row['open'] = round(ohlc['o'], 4)
                            existing_row['high'] = round(ohlc['h'], 4)
                            existing_row['low'] = round(ohlc['l'], 4)
                            patched += 1
                        continue
                    new_rows.append({'date': day, 'ticker': t, 'name': i['name'],
                                     'quote_symbol': i['quote_symbol'], 'quote_ccy': 'KRW',
                                     'price': round(ohlc['c'], 4), 'price_krw': round(ohlc['c'], 4),
                                     'open': round(ohlc['o'], 4), 'high': round(ohlc['h'], 4),
                                     'low': round(ohlc['l'], 4), 'source': 'backfill(yahoo%s)' % used})
            else:
                hist = fetch_yahoo_history(i['quote_symbol'], start_date, end_date)
                for day, ohlc in hist.items():
                    fx = fx_hist.get(day, {}).get('c') if fx_hist else None
                    existing_row = existing_by_key.get((day, t))
                    if existing_row is not None:
                        if not existing_row.get('open') and fx is not None:
                            existing_row['open'] = round(ohlc['o'] * fx, 4)
                            existing_row['high'] = round(ohlc['h'] * fx, 4)
                            existing_row['low'] = round(ohlc['l'] * fx, 4)
                            patched += 1
                        continue
                    if fx is None:
                        continue
                    new_rows.append({'date': day, 'ticker': t, 'name': i['name'],
                                     'quote_symbol': i['quote_symbol'], 'quote_ccy': 'USD',
                                     'price': round(ohlc['c'], 4), 'price_krw': round(ohlc['c'] * fx, 4),
                                     'open': round(ohlc['o'] * fx, 4), 'high': round(ohlc['h'] * fx, 4),
                                     'low': round(ohlc['l'] * fx, 4), 'source': 'backfill(yahoo×fx)'})
        except Exception as e:
            print('  실패: %s (%s)' % (t, str(e)[:80]))

    all_rows = existing + new_rows
    all_rows.sort(key=lambda r: (r['date'], r['ticker']))
    write_csv('price_history.csv', all_rows, PRICE_HISTORY_COLS)
    print('과거 시세 %d행 추가, 기존 %d행 open/high/low 보완 (price_history.csv 총 %d행)'
          % (len(new_rows), patched, len(all_rows)))


def update_positions_current_price(prices):
    """positions.csv 의 current_price_krw 열을 오늘 시세로 덮어쓴다.

    사람이 입력한 나머지 칸(qty·avg_price_krw·손절가 등)은 그대로 두고
    이 열만 갱신한다 — CSV 를 다시 읽어서 그대로 다시 쓰는 방식이라,
    서식(콤마 표기 등)도 손대지 않는다.
    """
    path = os.path.join(DATA, 'positions.csv')
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    if 'current_price_krw' not in fieldnames:
        idx = fieldnames.index('avg_price_krw') + 1 if 'avg_price_krw' in fieldnames else len(fieldnames)
        fieldnames = fieldnames[:idx] + ['current_price_krw'] + fieldnames[idx:]
    for row in rows:
        t = row['ticker']
        if t in prices:
            row['current_price_krw'] = '{:,.0f}'.format(prices[t][0])
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
