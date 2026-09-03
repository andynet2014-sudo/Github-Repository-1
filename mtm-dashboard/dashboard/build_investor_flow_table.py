#!/usr/bin/env python3
"""data/investor_flow_stock.csv(자동 수집, 삼성전자/SK하이닉스 기관·외국인 순매매
수량+금액)에서 종목별 최근 거래일 "개인/외국인/기관" 순매수 금액 표를
risk-console.html 의 DATA.investor_flow_stock 로 주입한다. 최근 10영업일은 기본
노출, 그 이전(최대 60영업일)은 "더보기"로 프론트에서 펼쳐 보여준다.

개별 종목 단위로는 네이버가 개인 순매수를 따로 안 주기 때문에(기관/외국인 수량만
제공, 2026-09 조사 확인), 개인_금액은 -(기관_금액+외국인_금액) 잔여로 추정한다 —
그날 총 거래대금이 개인/외국인/기관 세 주체로 대략 나뉜다고 가정한 근사치다(기타법인
등 소수 주체 오차가 개인 쪽에 섞여 들어감). 원본 스크레이핑 값(기관/외국인)은
data/investor_flow_stock.csv 에 그대로 있고, 이 잔여 추정은 표시용으로만 계산한다.

data/investor_flow_stock.csv 는 collect.py 가 매일(GitHub Actions) 자동으로 채운다.

사용:
    python3 dashboard/build_investor_flow_table.py
"""
import csv
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
HTML_PATH = os.path.join(BASE, 'risk-console.html')
CSV_PATH = os.path.join(REPO, 'data', 'investor_flow_stock.csv')
MAX_ROWS = 60   # 프론트 "더보기"가 펼칠 수 있는 최대 과거 거래일 수


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    if not os.path.exists(CSV_PATH):
        print('data/investor_flow_stock.csv 없음 — 건너뜀')
        return
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    by_ticker = {}
    for r in rows:
        short = r['ticker'].split(':', 1)[-1]
        by_ticker.setdefault(short, []).append(r)

    out = {}
    for short, trows in by_ticker.items():
        trows.sort(key=lambda r: r['date'], reverse=True)   # 최신이 맨 앞
        trows = trows[:MAX_ROWS]
        rows_out = []
        for r in trows:
            organ_amt = num(r['기관_금액'])
            foreign_amt = num(r['외국인_금액'])
            individual_amt = None
            if organ_amt is not None and foreign_amt is not None:
                individual_amt = -(organ_amt + foreign_amt)
            rows_out.append({
                'date': r['date'],
                'individual_amt': individual_amt,
                'foreign_amt': foreign_amt,
                'organ_amt': organ_amt,
            })
        out[short] = rows_out
        print(f'{short}: {len(out[short])}일치 (최신 {out[short][0]["date"] if out[short] else "-"})')

    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
    marker = 'const DATA = '
    i = html.index(marker) + len(marker)
    j = html.index(';\n', i)
    data = json.loads(html[i:j])
    data['investor_flow_stock'] = out
    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_html = html[:i] + new_json + html[j:]
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print('risk-console.html DATA.investor_flow_stock 갱신 완료')


if __name__ == '__main__':
    main()
