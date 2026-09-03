#!/usr/bin/env python3
"""data/priority.csv → DATA.priority. Summ. 탭 상단 "Priority" 카드 4개
(루틴/원칙/계획/룩백)의 소스 — 매일 상기할 것들을 한두 줄씩 적어두는 공간.
사용자가 채팅으로 "루틴에 ~~ 추가해줘"처럼 말하면 이 CSV를 고치고
재실행한다.

사용:
    python3 dashboard/build_priority.py
"""
import csv
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
HTML_PATH = os.path.join(BASE, 'risk-console.html')
CSV_PATH = os.path.join(REPO, 'data', 'priority.csv')


def main():
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    priority = [{'section': r['section'], 'text': r['text'], 'updated': r.get('updated') or None} for r in rows]

    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
    marker = 'const DATA = '
    i = html.index(marker) + len(marker)
    j = html.index(';\n', i)
    data = json.loads(html[i:j])
    data['priority'] = priority
    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_html = html[:i] + new_json + html[j:]
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f'priority {len(priority)}건 갱신 완료: ' + ', '.join(p['section'] for p in priority))


if __name__ == '__main__':
    main()
