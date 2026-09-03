#!/usr/bin/env python3
"""risk-console.html DATA.dod_breakdown 을 data/positions_history.csv 최근 2영업일
(date/prior_date) 종목별 pnl 델타로 재계산한다. Summ. 탭 히어로의
"전일比 요인" 칩에 쓰인다 — 종목별(신용/현금 합산) 표면손익 변동 상위 5개.

사용:
    python3 dashboard/build_dod_breakdown.py
"""
import csv
import json
import os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
HTML_PATH = os.path.join(BASE, 'risk-console.html')
CSV_PATH = os.path.join(REPO, 'data', 'positions_history.csv')
EXCLUDE_PREFIXES = ('CASH_', 'CREDIT_')
TOP_N = 5


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main():
    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
    marker = 'const DATA = '
    i = html.index(marker) + len(marker)
    j = html.index(';\n', i)
    data = json.loads(html[i:j])

    d1 = data['date']
    d0 = data.get('prior_date')
    if not d0:
        print('prior_date 없음 — dod_breakdown 건너뜀')
        return

    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    by_date = defaultdict(dict)
    for r in rows:
        if r['ticker'].startswith(EXCLUDE_PREFIXES):
            continue
        key = (r['account'], r['name'].replace('(신용)', ''))
        by_date[r['date']][key] = by_date[r['date']].get(key, 0.0) + num(r['pnl'])

    keys = set(by_date.get(d1, {})) | set(by_date.get(d0, {}))
    deltas = []
    for k in keys:
        v1 = by_date.get(d1, {}).get(k, 0.0)
        v0 = by_date.get(d0, {}).get(k, 0.0)
        delta = v1 - v0
        if abs(delta) < 1:
            continue
        deltas.append({'account': k[0], 'name': k[1], 'delta': delta})
    deltas.sort(key=lambda x: -abs(x['delta']))
    top = deltas[:TOP_N]

    data['dod_breakdown'] = top
    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_html = html[:i] + new_json + html[j:]
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f'dod_breakdown ({d0} -> {d1}) 상위 {len(top)}개:')
    for t in top:
        print(f"  {t['account']} {t['name']}: {t['delta']:+,.0f}원")


if __name__ == '__main__':
    main()
