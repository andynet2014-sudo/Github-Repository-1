#!/usr/bin/env python3
"""SK하이닉스(000660)·삼성전자(005930) 일별 종가 9개월치를 받아
dashboard/price_history.csv 로 저장한다.

이 저장소가 돌아가는 샌드박스 환경은 야후/네이버 금융 접근이 막혀 있어서,
이 스크립트는 네트워크가 열려있는 사용자 로컬 환경에서 직접 실행해야 한다.

    cd mtm-dashboard
    python3 dashboard/fetch_price_history.py

실행 후 dashboard/price_history.csv 가 생기면 그 내용을 Claude 에게
전달(또는 git add/commit)하면 대시보드 차트에 반영한다.
"""
import csv
import datetime
import json
import os
import urllib.error
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
TIMEOUT = 10
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'price_history.csv')

TICKERS = [
    ('000660', 'SK하이닉스'),
    ('005930', '삼성전자'),
]


def fetch_yahoo_history(code, range_='9mo'):
    for suffix in ('.KS', '.KQ'):
        url = ('https://query1.finance.yahoo.com/v8/finance/chart/'
               + code + suffix + f'?range={range_}&interval=1d')
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                d = json.loads(r.read())
            result = d['chart']['result'][0]
            ts = result['timestamp']
            closes = result['indicators']['quote'][0]['close']
            out = []
            for t, c in zip(ts, closes):
                if c is None:
                    continue
                date = datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
                out.append((date, round(float(c), 2)))
            if out:
                return out
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError) as e:
            print(f'  {code}{suffix} 실패: {e}')
            continue
    raise RuntimeError(f'{code} 조회 실패 (야후 .KS/.KQ 모두 실패)')


def main():
    rows = []
    for code, name in TICKERS:
        print(f'{name}({code}) 조회 중...')
        history = fetch_yahoo_history(code)
        print(f'  {len(history)}일치 확보 ({history[0][0]} ~ {history[-1][0]})')
        for date, close in history:
            rows.append({'ticker': code, 'name': name, 'date': date, 'close': close})

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['ticker', 'name', 'date', 'close'])
        w.writeheader()
        w.writerows(rows)
    print(f'\n{OUT} 저장 완료 — {len(rows)}행')


if __name__ == '__main__':
    main()
