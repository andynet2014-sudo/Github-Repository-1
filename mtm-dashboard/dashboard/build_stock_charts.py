#!/usr/bin/env python3
"""data/price_history.csv(자동 수집 종가+OHLC 이력, KRX:000660/KRX:005930)에서
20/60/120일 이동평균선을 계산해 risk-console.html 의 DATA.stock_charts 로 주입한다.

data/price_history.csv 는 collect.py 가 매일(GitHub Actions) 자동으로 채운다 —
과거 open/high/low 이 비어 있는 행(이 필드가 생기기 전 백필분)은 캔들 대신
종가 기준 얇은 도지(open=high=low=close)로 대체 렌더링된다(프론트 로직).

사용:
    python3 dashboard/build_stock_charts.py
"""
import csv
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
HTML_PATH = os.path.join(BASE, 'risk-console.html')
CSV_PATH = os.path.join(REPO, 'data', 'price_history.csv')
LEGACY_CSV_PATH = os.path.join(BASE, 'price_history.csv')
TICKERS = {'KRX:000660': 'SK하이닉스', 'KRX:005930': '삼성전자'}
LEGACY_TICKERS = {'000660': 'KRX:000660', '005930': 'KRX:005930'}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def moving_avg(values, window):
    out = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
        chunk = values[i + 1 - window:i + 1]
        out.append(round(sum(chunk) / window, 2))
    return out


def load_legacy_by_ticker():
    """dashboard/price_history.csv(2025-11 수동 1회성 fetch, 종가만) — data/
    price_history.csv(자동 수집, OHLC 포함하지만 2026-08~)로 커버 안 되는
    더 이전 구간을 메우는 용도로만 쓴다. 겹치는 날짜는 자동 수집 쪽을 우선한다."""
    out = {}
    if not os.path.exists(LEGACY_CSV_PATH):
        return out
    with open(LEGACY_CSV_PATH, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            t = LEGACY_TICKERS.get(r['ticker'])
            if not t:
                continue
            c = num(r.get('close'))
            if c is None:
                continue
            out.setdefault(t, {})[r['date']] = {
                'date': r['date'], 'price_krw': c, 'open': '', 'high': '', 'low': '',
            }
    return out


def main():
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    legacy_by_ticker = load_legacy_by_ticker()

    by_ticker = {}
    for r in rows:
        if r['ticker'] not in TICKERS:
            continue
        by_ticker.setdefault(r['ticker'], {})[r['date']] = r

    stock_charts = []
    for ticker, name in TICKERS.items():
        merged = dict(legacy_by_ticker.get(ticker, {}))
        merged.update(by_ticker.get(ticker, {}))  # 자동 수집(OHLC 있음)이 legacy를 덮어씀
        trows = sorted(merged.values(), key=lambda r: r['date'])
        if not trows:
            continue
        dates = [r['date'] for r in trows]
        closes = [num(r['price_krw']) for r in trows]
        opens = [num(r.get('open')) for r in trows]
        highs = [num(r.get('high')) for r in trows]
        lows = [num(r.get('low')) for r in trows]
        ma20 = moving_avg(closes, 20)
        ma60 = moving_avg(closes, 60)
        ma120 = moving_avg(closes, 120)
        series = []
        for d, c, o, h, l, a20, a60, a120 in zip(dates, closes, opens, highs, lows, ma20, ma60, ma120):
            series.append({
                'date': d, 'close': c,
                'open': o if o is not None else c,
                'high': h if h is not None else c,
                'low': l if l is not None else c,
                'ma20': a20, 'ma60': a60, 'ma120': a120,
            })
        short_ticker = ticker.split(':', 1)[-1]
        stock_charts.append({'ticker': short_ticker, 'name': name, 'series': series})
        n120 = sum(1 for p in series if p['ma120'] is not None)
        n_ohlc = sum(1 for r in trows if r.get('open'))
        print(f'{name}({short_ticker}): {len(series)}일치, ma120 유효 {n120}일, OHLC 있는 날 {n_ohlc}일')

    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
    marker = 'const DATA = '
    i = html.index(marker) + len(marker)
    j = html.index(';\n', i)
    data = json.loads(html[i:j])
    data['stock_charts'] = stock_charts
    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_html = html[:i] + new_json + html[j:]
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print('risk-console.html DATA.stock_charts 갱신 완료')


if __name__ == '__main__':
    main()
