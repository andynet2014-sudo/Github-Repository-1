"""투자자별 순매수(기관/외국인/개인) 수집.

네이버 시세 페이지를 스크레이핑한다(공식 API 아님, 화면이 바뀌면 파서가 깨질 수 있음).
  - 코스피 시장 전체: 개인/외국인/기관계/기관 세부(6종)/기타법인 순매수 "금액"
    (네이버 원본 표기 단위 그대로 저장 — 백만원으로 추정되나 공식 단위 라벨을
    스크레이핑하지 않았으므로 화면과 대조해 확인할 것)
  - 개별 종목(삼성전자/SK하이닉스 등): 기관/외국인 순매매 "수량"(주)만 제공됨 —
    기타법인 별도 분리는 개별 종목 단위로는 무료로 확인 불가(2026-09 조사 결론,
    KRX 공식 API는 로그인 세션 필요해서 막힘). 수량에 그날 종가를 곱해 금액으로
    환산해서 같이 저장한다.
"""
import datetime
import re

from base import num, read_csv, write_csv, _get_text, _table_rows

INVESTOR_MARKET_KEYS = ['개인', '외국인', '기관계', '금융투자', '보험', '투신사모',
                        '은행', '기타금융기관', '연기금등', '기타법인']
INVESTOR_MARKET_COLS = ['date'] + INVESTOR_MARKET_KEYS + ['source']
INVESTOR_STOCK_COLS = ['date', 'ticker', 'name', 'price',
                       '기관_수량', '외국인_수량', '기관_금액', '외국인_금액', 'source']

STOCK_FLOW_TICKERS = {'KRX:005930': '005930', 'KRX:000660': '000660'}  # 삼성전자, SK하이닉스


def fetch_investor_flow_market(date):
    """코스피 시장 전체 투자자별 순매수 금액을 네이버에서 조회. date: 'YYYY-MM-DD'.
    해당 날짜 행을 못 찾으면 None."""
    bizdate = date.replace('-', '')
    html = _get_text('https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate=' + bizdate)
    tables = _table_rows(html, 'type_1')
    if not tables:
        return None
    for row in tables[0]:
        if not re.match(r'\d{2}\.\d{2}\.\d{2}', row[0]):
            continue
        d = '20' + row[0].replace('.', '-')
        if d != date or len(row) < 11:
            continue
        vals = [num(c) for c in row[1:11]]
        return dict(zip(INVESTOR_MARKET_KEYS, vals))
    return None


def upsert_investor_flow_market(date, values):
    keep = [r for r in read_csv('investor_flow_market.csv') if r['date'] != date]
    row = {'date': date, 'source': 'naver'}
    row.update({k: round(v, 2) for k, v in values.items()})
    keep.append(row)
    keep.sort(key=lambda r: r['date'])
    write_csv('investor_flow_market.csv', keep, INVESTOR_MARKET_COLS)


def fetch_investor_flow_stock_recent(code):
    """개별 종목의 최근 거래일(약 10일치) 종가·기관/외국인 순매매 수량(주)을 네이버에서
    조회. {'YYYY-MM-DD': {'price', '기관_수량', '외국인_수량'}}."""
    html = _get_text('https://finance.naver.com/item/frgn.naver?code=' + code)
    tables = _table_rows(html, 'type2')
    if len(tables) < 2:
        return {}
    out = {}
    for row in tables[1]:
        if not re.match(r'\d{4}\.\d{2}\.\d{2}', row[0]) or len(row) < 7:
            continue
        d = row[0].replace('.', '-')
        out[d] = {'price': num(row[1]), '기관_수량': num(row[5]), '외국인_수량': num(row[6])}
    return out


def upsert_investor_flow_stock(rows):
    """rows: [{'date','ticker','name','price','기관_수량','외국인_수량','기관_금액','외국인_금액'}]
    같은 (date,ticker) 행은 덮어쓴다."""
    existing = read_csv('investor_flow_stock.csv')
    key = lambda r: (r['date'], r['ticker'])
    keep = {key(r): r for r in existing}
    for r in rows:
        row = dict(r)
        row['source'] = 'naver'
        keep[key(row)] = row
    out = sorted(keep.values(), key=lambda r: (r['date'], r['ticker']))
    write_csv('investor_flow_stock.csv', out, INVESTOR_STOCK_COLS)


def fetch_investor_flow_market_range(start_date, end_date=None):
    """start_date~end_date 구간의 코스피 시장 전체 투자자 순매수를 조회.
    bizdate 요청 한 번이 그 날짜 포함 최근 10거래일치를 돌려주는 걸 이용해
    ~10거래일 간격으로 점프하며 요청 수를 최소화한다(전체 구간을 매일 따로
    요청하지 않음). {date: {키: 값}} 반환."""
    end_date = end_date or datetime.date.today().isoformat()
    out = {}
    cursor = end_date
    seen = set()
    while True:
        bizdate = cursor.replace('-', '')
        html = _get_text('https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate=' + bizdate)
        tables = _table_rows(html, 'type_1')
        if not tables or not tables[0]:
            break
        page_dates = []
        for row in tables[0]:
            if not re.match(r'\d{2}\.\d{2}\.\d{2}', row[0]) or len(row) < 11:
                continue
            d = '20' + row[0].replace('.', '-')
            page_dates.append(d)
            if start_date <= d <= end_date and d not in out:
                vals = [num(c) for c in row[1:11]]
                out[d] = dict(zip(INVESTOR_MARKET_KEYS, vals))
        if not page_dates:
            break
        oldest = min(page_dates)
        if oldest <= start_date or oldest in seen:
            break
        seen.add(oldest)
        cursor = oldest
    return out


def fetch_investor_flow_stock_range(code, start_date, end_date=None):
    """개별 종목의 start_date~end_date 구간 기관/외국인 순매매 수량(주)을
    frgn.naver의 페이지네이션(&page=N, 페이지당 20거래일)으로 조회.
    {date: {'price','기관_수량','외국인_수량'}} 반환."""
    end_date = end_date or datetime.date.today().isoformat()
    out = {}
    page = 1
    while page <= 60:   # 안전장치 — 60페이지(약 4.6년치)면 충분
        html = _get_text('https://finance.naver.com/item/frgn.naver?code=%s&page=%d' % (code, page))
        tables = _table_rows(html, 'type2')
        if len(tables) < 2 or not tables[1]:
            break
        rows = [r for r in tables[1] if re.match(r'\d{4}\.\d{2}\.\d{2}', r[0]) and len(r) >= 7]
        if not rows:
            break
        for row in rows:
            d = row[0].replace('.', '-')
            if start_date <= d <= end_date:
                out[d] = {'price': num(row[1]), '기관_수량': num(row[5]), '외국인_수량': num(row[6])}
        oldest = min(row[0].replace('.', '-') for row in rows)
        if oldest < start_date:
            break
        page += 1
    return out


def backfill_investor_flow(start_date, end_date=None):
    """start_date~end_date 구간을 소급 조회해 investor_flow_market.csv /
    investor_flow_stock.csv 에 채운다. 이미 있는 (날짜) / (날짜,티커) 행은
    덮어쓰지 않는다(실측/라이브 값 보존)."""
    end_date = end_date or datetime.date.today().isoformat()
    existing_market = {r['date'] for r in read_csv('investor_flow_market.csv')}
    existing_stock = {(r['date'], r['ticker']) for r in read_csv('investor_flow_stock.csv')}

    market_range = fetch_investor_flow_market_range(start_date, end_date)
    added_market = 0
    for d, vals in sorted(market_range.items()):
        if d in existing_market:
            continue
        upsert_investor_flow_market(d, vals)
        added_market += 1

    added_stock = 0
    for ticker, code in STOCK_FLOW_TICKERS.items():
        name = '삼성전자' if code == '005930' else 'SK하이닉스'
        stock_range = fetch_investor_flow_stock_range(code, start_date, end_date)
        rows = []
        for d, r in stock_range.items():
            if (d, ticker) in existing_stock:
                continue
            price = r['price']
            rows.append({'date': d, 'ticker': ticker, 'name': name, 'price': price,
                        '기관_수량': r['기관_수량'], '외국인_수량': r['외국인_수량'],
                        '기관_금액': round(r['기관_수량'] * price, 0),
                        '외국인_금액': round(r['외국인_수량'] * price, 0)})
        if rows:
            upsert_investor_flow_stock(rows)
            added_stock += len(rows)
    print('투자자 순매수 소급 백필: 코스피 전체 %d행, 개별 종목 %d행 추가'
          % (added_market, added_stock))


def collect_investor_flow(date):
    """코스피 시장 전체 + 삼성전자/SK하이닉스 개별 종목 투자자 순매수를 조회해서
    저장한다. 실패해도 예외를 던지지 않고 (성공목록, 실패목록)을 돌려준다 —
    본 수집(daily.csv)을 막지 않기 위해서."""
    ok, failed = [], []
    try:
        m = fetch_investor_flow_market(date)
        if m:
            upsert_investor_flow_market(date, m)
            ok.append('코스피 전체')
        else:
            failed.append(('코스피 전체', '해당 날짜 행 없음(휴장일 등)'))
    except Exception as e:
        failed.append(('코스피 전체', str(e)[:80]))

    stock_rows = []
    for ticker, code in STOCK_FLOW_TICKERS.items():
        try:
            recent = fetch_investor_flow_stock_recent(code)
            r = recent.get(date)
            if not r:
                failed.append((ticker, '해당 날짜 행 없음(휴장일 등)'))
                continue
            price = r['price']
            stock_rows.append({
                'date': date, 'ticker': ticker,
                'name': '삼성전자' if code == '005930' else 'SK하이닉스',
                'price': price,
                '기관_수량': r['기관_수량'], '외국인_수량': r['외국인_수량'],
                '기관_금액': round(r['기관_수량'] * price, 0),
                '외국인_금액': round(r['외국인_수량'] * price, 0),
            })
            ok.append(ticker)
        except Exception as e:
            failed.append((ticker, str(e)[:80]))
    if stock_rows:
        upsert_investor_flow_stock(stock_rows)
    return ok, failed
