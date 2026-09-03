"""매크로 지표(코스피·코스닥·나스닥·SOX·환율·금 등) 수집 및 macro.csv 관리."""
import datetime

from base import num, read_csv, write_csv
from pricing import fetch_yahoo_history

# 야후 파이낸스 티커. ^TNX(미국채10y)는 regularMarketPrice가 이미 %값 그대로 나온다
# (예: 4.7 = 4.7%). 배율로 나누지 않는다 — 2026-08-24 실측으로 확인.
MACRO_TICKERS = {
    'us10y': ('^TNX', 1),
    'wti': ('CL=F', 1),
    'kospi': ('^KS11', 1),
    'kosdaq': ('^KQ11', 1),
    'nasdaq': ('^IXIC', 1),
    'nasdaq_futures': ('NQ=F', 1),
    'sox': ('^SOX', 1),           # 필라델피아반도체지수 (SOXX는 이 지수를 추종하는 ETF, watchlist에 별도)
    'usdkrw': ('USDKRW=X', 1),
    'usdjpy': ('JPY=X', 1),
    'gold': ('GC=F', 1),
}
MACRO_OHLC_SUFFIXES = ('_open', '_high', '_low')
MACRO_COLS = (['date']
              + [c for k in MACRO_TICKERS for c in [k] + [k + s for s in MACRO_OHLC_SUFFIXES]]
              + ['source'])


def load_macro(do_fetch, asof):
    """매크로 지표를 야후에서 조회(그날 OHLC 포함). 실패하면 macro.csv의 가장
    최근 값으로 대체한다(이때는 종가만 채워지고 open/high/low는 빈 칸 —
    나중에 --backfill-macro 로 채워진다)."""
    hist = read_csv('macro.csv')
    last = hist[-1] if hist else {}
    out, failed = {}, []
    for key, (symbol, div) in MACRO_TICKERS.items():
        if do_fetch:
            try:
                today = fetch_yahoo_history(symbol, asof, asof)
                ohlc = today.get(asof)
                if ohlc is None:
                    raise RuntimeError('오늘자 봉 없음')
                out[key] = {'c': ohlc['c'] / div, 'o': ohlc['o'] / div,
                           'h': ohlc['h'] / div, 'l': ohlc['l'] / div}
                continue
            except Exception as e:
                failed.append((symbol, str(e)[:60]))
        if key in last and last[key] not in ('', None):
            out[key] = {'c': num(last[key])}
    return out, failed


def upsert_macro(date, values):
    rows = [r for r in read_csv('macro.csv') if r['date'] != date]
    row = {'date': date, 'source': 'live'}
    for k in MACRO_TICKERS:
        v = values.get(k) or {}
        row[k] = round(v['c'], 4) if v.get('c') is not None else ''
        for suf, field in zip(MACRO_OHLC_SUFFIXES, ('o', 'h', 'l')):
            row[k + suf] = round(v[field], 4) if v.get(field) is not None else ''
    rows.append(row)
    rows.sort(key=lambda r: r['date'])
    write_csv('macro.csv', rows, MACRO_COLS)
    return row


def backfill_macro(start_date, end_date=None):
    """MACRO_TICKERS 전체를 야후에서 소급 조회해 macro.csv 를 채운다.
    없는 날짜는 새 행을 만들고, 이미 있는 날짜는 **빈 칸인 항목만** 채운다
    (예: 나중에 새 지표가 추가되기 전 날짜라 그 칸만 비어 있는 경우) —
    이미 값이 있는 칸은 절대 덮어쓰지 않는다."""
    end_date = end_date or datetime.date.today().isoformat()
    existing = read_csv('macro.csv')
    by_date = {r['date']: dict(r) for r in existing}

    hist_by_key = {}
    for key, (symbol, div) in MACRO_TICKERS.items():
        try:
            h = fetch_yahoo_history(symbol, start_date, end_date)
            hist_by_key[key] = {d: {f: v / div for f, v in ohlc.items()} for d, ohlc in h.items()}
            print('  %-16s %d일치 조회' % (key, len(h)))
        except Exception as e:
            print('  실패: %s (%s)' % (key, str(e)[:80]))
            hist_by_key[key] = {}

    all_dates = set()
    for h in hist_by_key.values():
        all_dates |= set(h.keys())

    added, filled = 0, 0
    for d in sorted(all_dates):
        if d not in by_date:
            by_date[d] = {'date': d, 'source': 'backfill(yahoo)'}
            for key in MACRO_TICKERS:
                by_date[d][key] = ''
                for suf in MACRO_OHLC_SUFFIXES:
                    by_date[d][key + suf] = ''
            added += 1
        row = by_date[d]
        for key in MACRO_TICKERS:
            ohlc = hist_by_key.get(key, {}).get(d)
            if ohlc is None:
                continue
            if row.get(key) in ('', None):
                row[key] = round(ohlc['c'], 4)
                filled += 1
            for suf, field in zip(MACRO_OHLC_SUFFIXES, ('o', 'h', 'l')):
                if row.get(key + suf) in ('', None):
                    row[key + suf] = round(ohlc[field], 4)
                    filled += 1

    all_rows = sorted(by_date.values(), key=lambda r: r['date'])
    write_csv('macro.csv', all_rows, MACRO_COLS)
    print('과거 매크로: 새 날짜 %d행 추가, 기존 행 빈 칸 %d개 보완 (macro.csv 총 %d행)'
          % (added, filled, len(all_rows)))
