#!/usr/bin/env python3
"""2026년 매매 분석용 — 실제 보유했던 기간만 시세를 채운 가격 테이블.

data/raw/holding_windows_2026.csv (계좌·종목명·보유시작·보유종료)를 읽어
종목별로 2026년 중 실제 보유 활동이 있었던 최초~최후 구간만 야후에서
소급 조회한다. 전 종목의 연간 전체 시세를 받지 않기 위한 스코핑이다.

이름→티커 매핑은 ticker_mapping_국장.csv(KRX 6자리 코드) /
ticker_mapping_미장.csv(야후 심볼)에서 가져온다. 매핑이 없는 종목명은
건드리지 않고 실패 목록에 남긴다.

collect.py의 fetch_yahoo_history를 그대로 재사용한다 — 야후 조회 로직을
두 곳에서 따로 관리하지 않기 위함.

출력: data/raw/csv/holding_prices_2026.csv
      (date, account, name, ticker, quote_ccy, price, price_krw, source)
      data/raw/csv/holding_prices_2026_실패.csv (매핑 없거나 조회 실패한 종목명)

사용법: python3 backfill_holding_prices.py
"""
import csv
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect import fetch_yahoo_history  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, 'data', 'raw')
OUT_DIR = os.path.join(RAW, 'csv')
TODAY = datetime.date.today().isoformat()


def read_csv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_mapping():
    kr = {r['name']: r['code'] for r in read_csv(os.path.join(RAW, 'ticker_mapping_국장.csv'))}
    us = {r['name']: r['ticker'] for r in read_csv(os.path.join(RAW, 'ticker_mapping_미장.csv'))}
    return kr, us


def merged_windows(rows):
    """계좌+종목명별로 여러 보유구간을 하나(최초 시작~최후 종료)로 합친다.
    종료가 빈 값(NaN/공란)인 구간이 하나라도 있으면 오늘까지로 본다."""
    merged = {}
    for r in rows:
        key = (r['account'], r['ticker'])
        start = r['start']
        end = r['end'] or None
        if key not in merged:
            merged[key] = [start, end]
            continue
        cur_start, cur_end = merged[key]
        if start < cur_start:
            merged[key][0] = start
        if cur_end is None or end is None:
            merged[key][1] = None
        elif end > cur_end:
            merged[key][1] = end
    # 2026-01-01 이전 시작은 분석 범위(2026년)에 맞춰 자른다.
    # 종료는 항상 오늘까지 연장한다 — 완전청산 종목도 "매도 후 가격이
    # 어떻게 됐는지"를 봐야 매매 타이밍 평가가 가능하기 때문
    # (보유 안 한 기간의 가격도 일부 포함되지만, 종목 수가 적어 비용은 무시할 만함).
    out = []
    for (account, name), (start, end) in merged.items():
        start = max(start, '2026-01-01')
        out.append({'account': account, 'name': name, 'start': start, 'end': TODAY})
    return out


def fetch_krx_history(code, start, end):
    for suffix in ('.KS', '.KQ'):
        try:
            hist = fetch_yahoo_history(code + suffix, start, end)
            if hist:
                return hist, 'yahoo' + suffix
        except Exception:
            continue
    return {}, None


def main():
    windows = merged_windows(read_csv(os.path.join(RAW, 'holding_windows_2026.csv')))
    kr_map, us_map = load_mapping()

    fx_hist = {}
    need_fx = any(w['account'] == '미장' and us_map.get(w['name'], '').isalpha()
                  for w in windows)
    if need_fx:
        fx_hist = fetch_yahoo_history('USDKRW=X', '2026-01-01', TODAY)

    out_rows = []
    failures = []
    seen_tickers = set()

    for w in windows:
        account, name, start, end = w['account'], w['name'], w['start'], w['end']

        if account == '국장':
            code = kr_map.get(name)
            if not code:
                failures.append({'account': account, 'name': name, 'reason': '매핑 없음'})
                continue
            if code.startswith('KRX:'):
                code = code[4:]
            hist, source = fetch_krx_history(code, start, end)
            if not hist:
                failures.append({'account': account, 'name': name, 'reason': '시세 조회 실패(%s)' % code})
                continue
            for day, close in hist.items():
                out_rows.append({'date': day, 'account': account, 'name': name,
                                  'ticker': 'KRX:' + code, 'quote_ccy': 'KRW',
                                  'price': round(close, 4), 'price_krw': round(close, 4),
                                  'source': source})
            seen_tickers.add('KRX:' + code)

        else:  # 미장
            ticker = us_map.get(name)
            if not ticker:
                failures.append({'account': account, 'name': name, 'reason': '매핑 없음'})
                continue
            if ticker.startswith('KRX:'):
                code = ticker[4:]
                hist, source = fetch_krx_history(code, start, end)
                if not hist:
                    failures.append({'account': account, 'name': name, 'reason': '시세 조회 실패(%s)' % code})
                    continue
                for day, close in hist.items():
                    out_rows.append({'date': day, 'account': account, 'name': name,
                                      'ticker': ticker, 'quote_ccy': 'KRW',
                                      'price': round(close, 4), 'price_krw': round(close, 4),
                                      'source': source})
            else:
                try:
                    hist = fetch_yahoo_history(ticker, start, end)
                except Exception as e:
                    failures.append({'account': account, 'name': name,
                                      'reason': '시세 조회 실패(%s): %s' % (ticker, str(e)[:80])})
                    continue
                if not hist:
                    failures.append({'account': account, 'name': name, 'reason': '시세 없음(%s)' % ticker})
                    continue
                for day, close in hist.items():
                    fx = fx_hist.get(day)
                    price_krw = round(close * fx, 4) if fx else None
                    out_rows.append({'date': day, 'account': account, 'name': name,
                                      'ticker': ticker, 'quote_ccy': 'USD',
                                      'price': round(close, 4), 'price_krw': price_krw,
                                      'source': 'yahoo×fx' if fx else 'yahoo(fx없음)'})
            seen_tickers.add(ticker)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_rows.sort(key=lambda r: (r['account'], r['ticker'], r['date']))
    with open(os.path.join(OUT_DIR, 'holding_prices_2026.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'account', 'name', 'ticker', 'quote_ccy',
                                          'price', 'price_krw', 'source'])
        w.writeheader()
        w.writerows(out_rows)

    with open(os.path.join(OUT_DIR, 'holding_prices_2026_실패.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['account', 'name', 'reason'])
        w.writeheader()
        w.writerows(failures)

    print('종목 %d개, 시세 %d행 저장 (실패 %d건)' % (len(seen_tickers), len(out_rows), len(failures)))


if __name__ == '__main__':
    main()
