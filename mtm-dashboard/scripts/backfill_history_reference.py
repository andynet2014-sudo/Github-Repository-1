import csv, json, sys

DATA = '/home/user/260731-/mtm-dashboard/data'
DAILY_COLS = ['date', 'equity', 'own_equity', 'expo_real', 'nominal_sum', 'cash',
              'credit', 'implied_lev', 'debt', 'lev_real', 'lev_account',
              'margin_ratio', 'liq_room', 'cash_ratio', 'debt_ratio',
              'max_sector', 'max_sector_name', 'max_pos', 'stop_below',
              'stop_missing', 'stop_loss', 'stop_loss_ratio', 'debt_to_salary',
              'surface_pnl', 'net_pnl', 'net_return',
              'violations', '국장_total', '국장_equity', '미장_equity', 'ISA_equity',
              'emotion', 'source']

# 삼성증권 월말잔고 리포트(2025-01~2026-07)의 '당월말평가금액(주식)+예수금' 합계 — 국장 7089239210-01, ISA 7156461048-14
# ('국장' 키는 신용대출 차감 전 총자산·GROSS다. 아래 row 생성부에서 credit을 빼 순자산(NET)을
#  국장_equity로 계산한다 — 사용자가 수기 입력한 2026-01-30 실측치와 대조해 이전에 이 GROSS값을
#  그대로 국장_equity에 넣었던 것이 버그였음을 확인함. 상세 근거는 아래 커밋 메시지 참고)
# credit = 사용자가 직접 제공한 "삼성증권 신용잔고 추이" 파일(25.10~26.07) 기준.
# 월말잔고 PDF의 '대출' 컬럼을 credit으로 오독했던 이전 값은 실제 신용잔고 추이와 최대 100배 이상
# 어긋나 전량 폐기했다(예: 26.01 PDF기준 0 vs 실제 339,363,189).
# 25.01~25.09는 사용자 확인: 신용을 2025년 10월부터 처음 사용 시작 → 그 이전은 실제 0.
# 월말일이 주말인 경우 그 주 금요일(직전 거래일) 값으로 간주해 날짜를 옮김:
# 2025-05-31(토)->05-30, 2025-08-31(일)->08-29, 2025-11-30(일)->11-28,
# 2026-01-31(토)->01-30, 2026-02-28(토)->02-27, 2026-05-31(일)->05-29.
MONTHLY = {
    '2025-01-31': {'국장': 141220654, 'ISA': 22006028, 'credit': 0},
    '2025-02-28': {'국장': 144235988, 'ISA': 21039974, 'credit': 0},
    '2025-03-31': {'국장': 118040977, 'ISA': 29484688, 'credit': 0},
    '2025-04-30': {'국장': 149173289, 'ISA': 29810467, 'credit': 0},
    '2025-05-30': {'국장': 111249338, 'ISA': 40246722, 'credit': 0},
    '2025-06-30': {'국장': 111684871, 'ISA': 38574028, 'credit': 0},
    '2025-07-31': {'국장': 128513574, 'ISA': 38277314, 'credit': 0},
    '2025-08-29': {'국장': 123581438, 'ISA': 36776363, 'credit': 0},
    '2025-09-30': {'국장': 143462136, 'ISA': 39230795, 'credit': 0},
    '2025-10-31': {'국장': 261829124, 'ISA': 46245520, 'credit': 88362500},
    '2025-11-28': {'국장': 342629300, 'ISA': 45930928, 'credit': 89824166},
    '2025-12-31': {'국장': 483915366, 'ISA': 44594086, '미장': 177430808, 'credit': 224428420},
    '2026-01-30': {'국장': 708276279, 'ISA': 50254696, 'credit': 339363189},
    '2026-02-27': {'국장': 843039989, 'ISA': 51022778, 'credit': 375235701},
    '2026-03-31': {'국장': 696979419, 'ISA': 44072417, 'credit': 370237852},
    '2026-04-30': {'국장': 759732225, 'ISA': 53449994, 'credit': 279591272},
    '2026-05-29': {'국장': 1090093493, 'ISA': 66581723, 'credit': 330571879},
    '2026-06-30': {'국장': 1192653262, 'ISA': 71273068, 'credit': 437072120},
    '2026-07-31': {'국장': 824979739, 'ISA': 43343078, 'credit': 437124010},
}

mijang_daily = json.load(open('/tmp/claude-0/-home-user-260731-/b712c619-9f83-5eb1-85a3-154aeacff8b0/scratchpad/mijang_daily.json'))
# 월말 날짜는 MONTHLY 딕셔너리가 이미 정확한 값을 갖고 있으니 daily series 에서는 제외
month_end_dates = set(MONTHLY.keys())

existing = {r['date']: r for r in csv.DictReader(open(f'{DATA}/daily.csv'))}
LIVE_CUTOFF = '2026-08-10'  # 이 날짜부터는 collect.py 로 실측된 데이터라 손대지 않는다

new_rows = {}

# 1) 국장+ISA 월말 스냅샷 (2025-01~2025-11: 미장 데이터 없음 / 2025-12~2026-07: 3계좌 다 있음 —
#    미장은 2025-12-31 은 수기값, 2026-01~07 월말은 나무증권 일별잔고 파일의 해당일 값을 그대로 사용)
for date, vals in MONTHLY.items():
    row = {c: '' for c in DAILY_COLS}
    row['date'] = date
    credit = vals['credit'] if vals['credit'] is not None else 0
    kr_gross = vals['국장']
    kr_net = kr_gross - credit
    row['국장_total'] = kr_gross
    row['국장_equity'] = kr_net
    row['ISA_equity'] = vals['ISA']
    row['credit'] = vals['credit'] if vals['credit'] is not None else ''
    mijang = vals.get('미장') or mijang_daily.get(date)
    if mijang is not None:
        row['미장_equity'] = mijang
        row['equity'] = kr_net + vals['ISA'] + mijang
        row['source'] = 'backfill(전체·월말잔고 PDF+나무증권)'
    else:
        row['source'] = 'backfill(국장+ISA만·월말잔고 PDF)'
    new_rows[date] = row

# 2) 미장 일별 시리즈 (2026-01-01~2026-08-23) — 월말이 아닌 날만, 그리고 실측 구간(8/10~) 이전만
for date, bal in mijang_daily.items():
    if date in month_end_dates:
        continue
    if date >= LIVE_CUTOFF:
        continue
    row = {c: '' for c in DAILY_COLS}
    row['date'] = date
    row['미장_equity'] = bal
    row['source'] = 'backfill(미장만·나무증권 일별잔고)'
    new_rows[date] = row

# 3) 기존 daily.csv 의 8/10 이후(실측) 행은 그대로 보존, 그 이전의 기존 monthly-snapshot(수기) 행은 새 값으로 대체
final = {}
for date, row in existing.items():
    if date >= LIVE_CUTOFF:
        final[date] = row
for date, row in new_rows.items():
    final[date] = row

rows = sorted(final.values(), key=lambda r: r['date'])
with open(f'{DATA}/daily.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=DAILY_COLS)
    w.writeheader()
    w.writerows(rows)

print('총', len(rows), '행 기록 완료')
print('2025년 행 수:', sum(1 for r in rows if r['date'].startswith('2025')))
print('2026년 행 수:', sum(1 for r in rows if r['date'].startswith('2026')))
