#!/usr/bin/env python3
"""collect.py 의 계산값을 v2.4.5 스프레드시트의 '④ 리스크 엔진' 셀과 대조한다.
원래 시트: ④ 리스크 엔진 (파이썬 이관 검증 전용, 1회성 스크립트)

스프레드시트가 자기 수식으로 계산해 둔 값 vs 파이썬이 독립적으로 계산한 값.
둘이 일치해야 '계산 위치만 옮겼고 정의는 그대로'라고 말할 수 있다.

  python3 verify_against_sheet.py v2.4.5.xlsx
"""
import sys
import openpyxl
import collect

# (라벨, 03_포지션 셀행, collect 지표키, 허용오차)
CHECKS = [
    ('주식평가 (명목)',        36, 'nominal_sum',    1.0),
    ('주식 Exposure (실질)',   37, 'expo_real',      1.0),
    ('예수금 합계',            38, 'cash',           1.0),
    ('총평가 (명목)',          39, 'total_val',      1.0),
    ('증권사 신용 합계',       40, 'credit',         1.0),
    ('계좌 순자산 (Equity)',   41, 'equity',         1.0),
    ('순수 자기자본',          43, 'own_equity',     1.0),
    ('내재 레버리지 금액',     44, 'implied_lev',    1.0),
    ('총 차입',                45, 'debt',           1.0),
    ('국장 총평가 (명목)',     46, 'kr_total',       1.0),
    ('국장 주식Expo (실질)',   47, 'kr_expo',        1.0),
    ('담보비율 (국장)',        51, 'margin_ratio',   1e-4),
    ('청산까지 하락여력',      52, 'liq_room',       1e-4),
    ('계좌 레버리지 배수',     53, 'lev_account',    1e-4),
    ('실질 레버리지 배수',     54, 'lev_real',       1e-4),
    ('차입 비중',              55, 'debt_ratio',     1e-4),
    ('현금 비중',              56, 'cash_ratio',     1e-4),
    ('보유 종목 수',           57, 'n_positions',    0),
    ('단일 종목 최대 비중',    58, 'max_pos',        1e-4),
    ('단일 섹터 최대 비중',    59, 'max_sector',     1e-4),
    ('손절가 미입력 종목 수',  60, 'stop_missing',   0),
    ('손절가 하회 종목 수',    61, 'stop_below',     0),
    ('신용 사용 종목 수',      62, 'n_credit',       0),
    ('전 종목 손절 시 총손실', 63, 'stop_loss',      1.0),
    ('총손실 ÷ 순수 자기자본', 64, 'stop_loss_ratio', 1e-4),
    ('총차입 ÷ 연봉',          65, 'debt_to_salary', 1e-4),
]


def main(path):
    ws = openpyxl.load_workbook(path, data_only=True)['03_포지션']

    positions = collect.read_csv('positions.csv')
    common = {r['key']: r['value'] for r in collect.read_csv('common.csv')}
    prices, _, _ = collect.load_prices(positions, False, '')
    mine, _ = collect.compute(positions, prices, common)

    print('%-26s %18s %18s   %s' % ('지표', '스프레드시트', 'collect.py', '판정'))
    print('─' * 78)
    bad = 0
    for label, row, key, tol in CHECKS:
        sheet = ws.cell(row, 2).value
        got = mine[key]
        ok = abs(float(sheet) - float(got)) <= tol
        if not ok:
            bad += 1
        f = (lambda v: '{:,.4f}'.format(v)) if tol and tol < 1 else (lambda v: '{:,.0f}'.format(v))
        print('%-26s %18s %18s   %s'
              % (label, f(float(sheet)), f(float(got)), 'OK' if ok else '*** 불일치 ***'))
    print('─' * 78)
    print('%d개 지표 대조 — 불일치 %d개' % (len(CHECKS), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'v2.4.5.xlsx'))
