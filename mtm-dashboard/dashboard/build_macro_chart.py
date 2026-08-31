#!/usr/bin/env python3
"""data/macro.csv(KOSPI/코스닥/미국10년물/WTI)를 DATA.macro_series로 주입한다.
View/Index 탭의 매크로 지표 카드에 쓰인다. 나스닥은 아직 원본 데이터가 없어
프론트에서 "자료 없음" 플레이스홀더로만 비워둔다.

사용:
    python3 dashboard/build_macro_chart.py
"""
import csv
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
HTML_PATH = os.path.join(BASE, 'risk-console.html')
CSV_PATH = os.path.join(REPO, 'data', 'macro.csv')


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    series = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                series.append({
                    'date': r['date'],
                    'kospi': num(r.get('kospi')),
                    'us10y': num(r.get('us10y')),
                })
    series.sort(key=lambda p: p['date'])

    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
    marker = 'const DATA = '
    i = html.index(marker) + len(marker)
    j = html.index(';\n', i)
    data = json.loads(html[i:j])
    data['macro_series'] = series
    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_html = html[:i] + new_json + html[j:]
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f'macro_series {len(series)}행 갱신 완료 (data/macro.csv 기준)')


if __name__ == '__main__':
    main()
