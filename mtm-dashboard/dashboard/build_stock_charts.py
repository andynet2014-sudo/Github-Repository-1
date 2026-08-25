#!/usr/bin/env python3
"""dashboard/price_history.csv(종가 이력)에서 20/60/120일 이동평균선을 계산해
risk-console.html 의 DATA.stock_charts 로 주입한다.

price_history.csv 는 dashboard/fetch_price_history.py 를 네트워크가 열린
로컬 환경에서 실행해 만든 파일이다 (이 저장소 샌드박스는 야후/네이버 접근이
막혀 있어 직접 못 받아옴).

사용:
    python3 dashboard/build_stock_charts.py
"""
import csv
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE, 'risk-console.html')
CSV_PATH = os.path.join(BASE, 'price_history.csv')


def moving_avg(values, window):
    out = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
        chunk = values[i + 1 - window:i + 1]
        out.append(round(sum(chunk) / window, 2))
    return out


def main():
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    by_ticker = {}
    for r in rows:
        by_ticker.setdefault(r['ticker'], {'name': r['name'], 'rows': []})
        by_ticker[r['ticker']]['rows'].append((r['date'], float(r['close'])))

    stock_charts = []
    for ticker, info in by_ticker.items():
        info['rows'].sort(key=lambda x: x[0])
        dates = [d for d, _ in info['rows']]
        closes = [c for _, c in info['rows']]
        ma20 = moving_avg(closes, 20)
        ma60 = moving_avg(closes, 60)
        ma120 = moving_avg(closes, 120)
        series = [
            {'date': d, 'close': c, 'ma20': a20, 'ma60': a60, 'ma120': a120}
            for d, c, a20, a60, a120 in zip(dates, closes, ma20, ma60, ma120)
        ]
        stock_charts.append({'ticker': ticker, 'name': info['name'], 'series': series})
        n120 = sum(1 for p in series if p['ma120'] is not None)
        print(f"{info['name']}({ticker}): {len(series)}일치, ma120 유효 {n120}일")

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
