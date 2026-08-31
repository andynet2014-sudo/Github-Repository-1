#!/usr/bin/env python3
"""data/macro.csv(KOSPI·코스닥·나스닥·SOX·미국10년물·환율·금 등)를
DATA.macro_series로 주입한다. View/Index 탭의 매크로 지표 카드에 쓰인다.
CSV에 있는 숫자 컬럼(date/source 제외)을 전부 그대로 넣으므로, macro.csv에
새 컬럼을 추가하면 다음 실행부터 자동으로 반영된다 — 프론트는 값이 있는
컬럼만 카드로 그리고, 값이 아예 없는 컬럼은 "자료 없음" 플레이스홀더를 그린다.

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
SKIP_COLS = ('date', 'source')


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    series = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            cols = [c for c in reader.fieldnames if c not in SKIP_COLS]
            for r in reader:
                point = {'date': r['date']}
                for c in cols:
                    point[c] = num(r.get(c))
                series.append(point)
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
