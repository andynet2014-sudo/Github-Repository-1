"""콘솔 리포트 출력 — collect.py 실행 시 사람이 보는 화면."""
from rules import RULE_MAP

PCT = {'liq_room', 'cash_ratio', 'max_sector', 'stop_loss_ratio', 'lev_etf_ratio', 'max_pos'}
MULT = {'lev_real', 'debt_to_salary'}


def fmt(key, v):
    if v is None:
        return '—'
    if key in PCT:
        return '%.1f%%' % (v * 100)
    if key in MULT:
        return '%.2f배' % v
    return '{:,.0f}'.format(v)


def report(date, m, signals, failed, macro=None):
    W = 62
    print('\n━━━ %s ' % date + '━' * (W - len(date) - 5))
    print('  계좌 순자산 (Equity)   %20s' % '{:,.0f}'.format(m['equity']))
    print('  순수 자기자본          %20s   ← 회사대출 차감' % '{:,.0f}'.format(m['own_equity']))
    print('  실질 주식 Exposure     %20s' % '{:,.0f}'.format(m['expo_real']))
    print('  총차입                 %20s   (신용 %s + 내재레버 %s)'
          % ('{:,.0f}'.format(m['debt']), '{:,.0f}'.format(m['credit']),
             '{:,.0f}'.format(m['implied_lev'])))
    print('  실질 레버리지          %20s' % ('%.2f배' % m['lev_real']))
    print('  청산까지 여력          %20s   담보비율 %.2f'
          % ('%.1f%%' % (m['liq_room'] * 100), m['margin_ratio']))
    print('  현금 비중              %20s' % ('%.1f%%' % (m['cash_ratio'] * 100)))
    print('  최대 섹터              %20s   %s'
          % ('%.1f%%' % (m['max_sector'] * 100), m['max_sector_name']))
    print('  실질 누적 순손익       %20s   표면 %s − 강의비·세금'
          % ('{:,.0f}'.format(m['net_pnl']), '{:,.0f}'.format(m['surface_pnl'])))
    print()
    print('  %-8s %16s %16s' % ('계좌', '총평가', '순자산'))
    for a in ('국장', '미장', 'ISA'):
        print('  %-8s %16s %16s' % (a, '{:,.0f}'.format(m[a + '_total']),
                                    '{:,.0f}'.format(m[a + '_equity'])))
    print('\n━━━ 리스크 신호등 ' + '━' * (W - 18))
    for rid, label, cur, thr, sig, fallback in signals:
        key = RULE_MAP[rid][0]
        note = '  ※ 기준값 미설정, 잠정 %s' % fmt(key, thr) if fallback else ''
        print('  %-5s %-12s %10s  (기준 %8s)   %s%s'
              % (rid, label, fmt(key, cur), fmt(key, thr) if thr is not None else '—', sig, note))
    bad = sum(1 for s in signals if s[4].startswith('🔴'))
    print('\n  위반 %d건 / %d건' % (bad, len(signals)))
    if macro:
        print('\n━━━ 매크로 ' + '━' * (W - 10))
        MACRO_LABELS = [
            ('kospi', 'KOSPI', '{:,.2f}'),
            ('kosdaq', 'KOSDAQ', '{:,.2f}'),
            ('nasdaq', 'NASDAQ', '{:,.2f}'),
            ('nasdaq_futures', 'NASDAQ 선물', '{:,.2f}'),
            ('sox', '필라델피아반도체(SOX)', '{:,.2f}'),
            ('us10y', '미국채 10y금리', '%.2f%%'),
            ('usdkrw', '원/달러 환율', '{:,.2f}'),
            ('usdjpy', '엔/달러 환율', '{:,.2f}'),
            ('wti', 'WTI 선물', '$%.2f'),
            ('gold', 'GOLD', '$%.2f'),
        ]
        for key, label, fmt_str in MACRO_LABELS:
            if key in macro and macro[key].get('c') is not None:
                val = macro[key]['c']
                shown = fmt_str % val if '%' in fmt_str else fmt_str.format(val)
                print('  %-22s %19s' % (label, shown))
    if m['stop_at_cost']:
        print('  ※ %d종목은 손절가가 평단가와 동일 — 실손절가 미설정으로 간주해 R04에 포함,'
              % m['stop_at_cost'])
        print('    R05(한방리스크) 총손실 계산에서는 제외했습니다. positions.csv 의'
              ' stop_price_krw 를 실제 손절가로 바꾸면 반영됩니다.')
    if failed:
        print('\n  ⚠ 시세 조회 실패 — 캐시로 대체했습니다:')
        for t, e in failed:
            print('     %-12s %s' % (t, e))
    print()
