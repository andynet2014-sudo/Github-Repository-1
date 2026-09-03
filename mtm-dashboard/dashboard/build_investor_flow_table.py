#!/usr/bin/env python3
"""data/investor_flow_stock.csv(자동 수집, 삼성전자/SK하이닉스 기관·외국인 순매매
수량+금액)에서 종목별 최근 거래일 표를 risk-console.html 의 DATA.investor_flow_stock
로 주입한다. 최근 10영업일은 기본 노출, 그 이전(최대 60영업일)은 "더보기"로 프론트에서
펼쳐 보여준다 — 몇 개나 보여줄지는 프론트 로직이 결정하고, 여기서는 최대 60행만 넘긴다.

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
        out[short] = [{
            'date': r['date'],
            'price': num(r['price']),
            'organ_qty': num(r['기관_수량']),
            'foreign_qty': num(r['외국인_수량']),
            'organ_amt': num(r['기관_금액']),
            'foreign_amt': num(r['외국인_금액']),
        } for r in trows]
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
