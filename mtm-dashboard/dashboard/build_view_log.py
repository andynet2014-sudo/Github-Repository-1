#!/usr/bin/env python3
"""data/viewtracker.csv → DATA.view_log 재주입. View 탭 "이번 주 투자 기조"의
전문가별 카드가 이 배열을 소스로 쓴다. 지금까지는 이 필드를 채우는 반복
가능한 스크립트가 없어서 viewtracker.csv가 갱신돼도 DATA.view_log가 stale한
채로 남아있었다 — 앞으로 viewtracker.csv를 고치면 이 스크립트를 재실행한다.

사용:
    python3 dashboard/build_view_log.py
"""
import csv
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
HTML_PATH = os.path.join(BASE, 'risk-console.html')
CSV_PATH = os.path.join(REPO, 'data', 'viewtracker.csv')


def num(v):
    if v is None or str(v).strip() == '':
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main():
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r['date'])

    view_log = [{
        'date': r['date'], 'source': r['source'], 'cycle': r['cycle'],
        'stance': r['stance'], 'score': num(r['score']), 'comment': r['comment'],
        'keyword': r.get('keyword') or None, 'entry_via': r.get('entry_via') or None,
    } for r in rows]

    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
    marker = 'const DATA = '
    i = html.index(marker) + len(marker)
    j = html.index(';\n', i)
    data = json.loads(html[i:j])
    data['view_log'] = view_log
    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_html = html[:i] + new_json + html[j:]
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)

    by_source = {}
    for v in view_log:
        by_source[v['source']] = by_source.get(v['source'], 0) + 1
    print(f'view_log {len(view_log)}건 갱신 완료 ({rows[0]["date"]} ~ {rows[-1]["date"]})')
    for src, n in sorted(by_source.items()):
        print(f'  {src}: {n}건')


if __name__ == '__main__':
    main()
