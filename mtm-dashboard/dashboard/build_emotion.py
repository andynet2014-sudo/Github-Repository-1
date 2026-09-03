#!/usr/bin/env python3
"""data/emotion.csv → DATA.emotion. Lookback 탭 "감정 기록(공포·탐욕)" 추이 카드의
소스 — 매매/시장 상황에서 느낀 감정을 -5(극도의 공포) ~ +5(극도의 탐욕) 척도로
쌓아서 나중에 계량 분석(드로다운 구간과의 상관관계 등)에 쓴다.

점수 척도 (CNN Fear&Greed 아이디어를 단순화):
  -5 ~ -3  공포        -2 ~ -1  약한 공포
   0        중립
  +1 ~ +2  약한 탐욕   +3 ~ +5  탐욕

사용자가 채팅으로 "오늘 감정 -3, 이유: ~~"처럼 말하면 이 CSV에 행을 추가하고
재실행한다. label 칸이 비어있으면 score로 자동 채운다.

사용:
    python3 dashboard/build_emotion.py
"""
import csv
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
HTML_PATH = os.path.join(BASE, 'risk-console.html')
CSV_PATH = os.path.join(REPO, 'data', 'emotion.csv')


def auto_label(score):
    if score <= -3:
        return '공포'
    if score < 0:
        return '약한 공포'
    if score == 0:
        return '중립'
    if score <= 2:
        return '약한 탐욕'
    return '탐욕'


def main():
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r['date'])

    emotion = []
    for r in rows:
        score = int(r['score'])
        emotion.append({
            'date': r['date'], 'score': score,
            'label': r.get('label') or auto_label(score),
            'situation': r.get('situation') or None,
            'trigger': r.get('trigger') or None,
            'entry_via': r.get('entry_via') or None,
        })

    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
    marker = 'const DATA = '
    i = html.index(marker) + len(marker)
    j = html.index(';\n', i)
    data = json.loads(html[i:j])
    data['emotion'] = emotion
    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_html = html[:i] + new_json + html[j:]
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f'emotion {len(emotion)}건 갱신 완료')


if __name__ == '__main__':
    main()
