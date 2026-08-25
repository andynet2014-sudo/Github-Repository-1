#!/usr/bin/env python3
"""risk-console.html 에 박아넣는 DATA JSON 중 전체 이력 배열
(full_pnl/full_eq/full_expo/full_credit/full_lev_real)만 다시 계산해서
같은 파일 안의 값을 교체한다. 나머지 필드(metrics/signals/positions/trend/...)는
건드리지 않는다 — CLAUDE.md '대시보드 반영 절차' 1~2단계에 해당.

계산 방식은 collect.py 의 load_cashflow_totals() 와 동일한 원금 집계 로직을
날짜별 누적으로 확장한 것이다: 그 날짜까지의 cashflow.csv principal 이동만 누적해서
principal_total(date) 를 구하고, daily.csv 의 equity(그 날 전체 순자산)에서 빼면
그 날짜 기준 실질 누적 손익(pnl)이 된다.

리포지토리 루트의 build_dash_data.py 와는 역할이 다르다 — 그쪽은 매일 최신 포인트
하나만 이전 JSON에 append(과거 데이터를 손대지 않음), 이 스크립트는 daily.csv/
cashflow.csv 전체를 훑어 5개 배열 전체를 처음부터 다시 계산한다. daily.csv를
과거로 소급 수정(백필)했을 때만 이 스크립트를 다시 돌리면 된다 — 평소엔 안 써도 됨.

사용:
    python3 dashboard/build_full_history.py
"""
import csv
import datetime
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
DATA_DIR = os.path.join(REPO, 'data')
HTML_PATH = os.path.join(BASE, 'risk-console.html')

NON_PRINCIPAL = ('신용이자', '강의구독비', '수수료', '매도세금', '배당금')
TRACKED = ('국장', '미장', 'ISA')


def num(v):
    if v is None or str(v).strip() == '':
        return None
    try:
        return float(str(v).replace(',', ''))
    except ValueError:
        return None


def load_daily():
    path = os.path.join(DATA_DIR, 'daily.csv')
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    by_date = {}
    for r in rows:
        by_date[r['date']] = r
    return by_date


def load_cashflow_principal_events():
    """(date, account, signed_amount) 리스트 — 원금 이동에 해당하는 행만."""
    path = os.path.join(DATA_DIR, 'cashflow.csv')
    events = []
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r['type'] in NON_PRINCIPAL:
            continue
        amt = num(r['amount']) or 0.0
        if r['from_account'] in TRACKED:
            events.append((r['date'], r['from_account'], -amt))
        if r['to_account'] in TRACKED:
            events.append((r['date'], r['to_account'], amt))
    events.sort(key=lambda e: e[0])
    return events


def business_days(start, end):
    d = start
    out = []
    while d <= end:
        if d.weekday() < 5:
            out.append(d.strftime('%Y-%m-%d'))
        d += datetime.timedelta(days=1)
    return out


def main():
    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
    marker = 'const DATA = '
    i = html.index(marker) + len(marker)
    j = html.index(';\n', i)
    data = json.loads(html[i:j])

    daily = load_daily()
    principal_events = load_cashflow_principal_events()

    start = datetime.date(2025, 1, 1)
    end = datetime.datetime.strptime(data['date'], '%Y-%m-%d').date()
    dates = business_days(start, end)

    full_pnl, full_eq, full_expo, full_credit, full_lev_real = [], [], [], [], []
    ev_idx = 0
    principal_total = 0.0
    for d in dates:
        while ev_idx < len(principal_events) and principal_events[ev_idx][0] <= d:
            principal_total += principal_events[ev_idx][2]
            ev_idx += 1
        row = daily.get(d)
        eq = num(row['equity']) if row else None
        credit = num(row['credit']) if row else None
        expo = num(row['expo_real']) if row else None
        lev = num(row['lev_real']) if row else None
        pnl = (eq - principal_total) if eq is not None else None
        full_pnl.append({'date': d, 'v': pnl})
        full_eq.append({'date': d, 'v': eq})
        full_expo.append({'date': d, 'v': expo})
        full_credit.append({'date': d, 'v': credit})
        full_lev_real.append({'date': d, 'v': lev})

    n_pnl = sum(1 for p in full_pnl if p['v'] is not None)
    n_credit = sum(1 for p in full_credit if p['v'] is not None)
    print(f'날짜 범위 {dates[0]} ~ {dates[-1]} ({len(dates)}개 영업일)')
    print(f'full_pnl 실값 {n_pnl}개, full_credit 실값 {n_credit}개')
    y = str(end.year)
    n_pnl_y = sum(1 for p in full_pnl if p['date'].startswith(y) and p['v'] is not None)
    n_credit_y = sum(1 for p in full_credit if p['date'].startswith(y) and p['v'] is not None)
    print(f'{y}년만: full_pnl {n_pnl_y}개, full_credit {n_credit_y}개')

    data['full_pnl'] = full_pnl
    data['full_eq'] = full_eq
    data['full_expo'] = full_expo
    data['full_credit'] = full_credit
    data['full_lev_real'] = full_lev_real

    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_html = html[:i] + new_json + html[j:]
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print('risk-console.html DATA 갱신 완료')


if __name__ == '__main__':
    main()
