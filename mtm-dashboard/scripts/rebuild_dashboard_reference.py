import sys, csv, json
sys.path.insert(0, '/home/user/260731-/mtm-dashboard')
import collect

BASE = '/home/user/260731-/mtm-dashboard'
collect.BASE = BASE
collect.DATA = BASE + '/data'

DATE = '2026-08-20'

common = {r['key']: r['value'] for r in collect.read_csv('common.csv')}
common = collect.load_cashflow_totals(common)
rules = collect.read_csv('rules.csv')
positions = collect.read_csv('positions.csv')
price_rows = collect.read_csv('prices.csv')
prices = {r['ticker']: (collect.num(r['price_krw']), r['source']) for r in price_rows}

m, stock_rows = collect.compute(positions, prices, common)

WARN = {'R01': 3.0, 'R02': 0.2, 'R03': 0.2, 'R04': 1.0, 'R05': 0.15, 'R06': 0.5}
PRINCIPLE = {
    'R01': '내 돈(순수 Equity)의 몇 배로 베팅하고 있는가 — 레버리지 총량',
    'R02': '몇 % 더 빠지면 반대매매인가',
    'R03': '현금도 포지션이다. 현금은 생명줄',
    'R04': '손절가를 정했고, 지키고 있는가',
    'R05': '전 종목이 동시에 손절선에 닿으면 자기자본의 몇 %가 사라지는가',
    'R06': '한 섹터에 계좌 전체가 걸려 있지 않은가',
}
mm = dict(m)
mm['stop_violations'] = mm['stop_missing'] + mm['stop_below']
signals = []
for rid in ('R01', 'R02', 'R03', 'R04', 'R05', 'R06'):
    key, direction, label = collect.RULE_MAP[rid]
    thr = next(collect.num(r['threshold']) for r in rules if r['id'] == rid)
    warn = WARN[rid]
    cur = mm[key]
    if direction == 'max':
        bad = cur > thr
        tier = 'red' if bad else ('yellow' if cur > warn else 'green')
    else:
        bad = cur < thr
        tier = 'red' if bad else ('yellow' if cur < warn else 'green')
    signals.append({
        'id': rid, 'label': label, 'value': cur, 'threshold': thr, 'warn': warn,
        'direction': direction, 'tier': tier, 'signal': '🔴 위반' if bad else '🟢 준수',
        'fallback': False, 'key': key, 'principle': PRINCIPLE[rid],
    })

denom = m['expo_real'] + m['cash']
pos_out = []
for r in stock_rows:
    stop = r['stop_price_krw']
    stop = collect.num(stop) if stop not in ('', None) else None
    pos_out.append({
        'name': r['name'], 'account': r['account'], 'sector': r['sector'], 'lev': r['lev'],
        'real': r['real'], 'weight': r['real'] / denom, 'qty': r['qty'],
        'avg': collect.num(r['avg_price_krw']), 'cur': r['price'], 'stop': stop,
        'cash': False, 'pnl': (r['price'] - collect.num(r['avg_price_krw'])) * r['qty'],
        'nominal': r['nominal'], 'ticker': r['ticker'], 'quote_ccy': r['quote_ccy'],
    })
for acct in ('국장', '미장', 'ISA'):
    cash_rows = [p for p in positions if p['account'] == acct and p['sector'] == '현금']
    for p in cash_rows:
        val = prices[p['ticker']][0]
        pos_out.append({
            'name': p['name'], 'account': acct, 'sector': '현금', 'lev': 1,
            'real': val, 'weight': val / denom, 'qty': 1.0, 'avg': val, 'cur': val,
            'stop': None, 'cash': True, 'pnl': 0, 'nominal': val,
        })

sector_totals = {}
for r in stock_rows:
    sector_totals[r['sector']] = sector_totals.get(r['sector'], 0) + r['real']
sector_rank = sorted(
    [{'name': k, 'value': v, 'pct': v / m['expo_real']} for k, v in sector_totals.items()],
    key=lambda x: -x['value'])

lev_breakdown = sorted(
    [{'name': r['name'], 'value': r['nominal']} for r in stock_rows if r['lev'] > 1],
    key=lambda x: -x['value'])

acct_expo = {}
for acct in ('국장', '미장', 'ISA'):
    acct_expo[acct] = sum(r['real'] for r in stock_rows if r['account'] == acct)

daily_rows = collect.read_csv('daily.csv')
daily_by_date = {r['date']: r for r in daily_rows}
prior = daily_by_date['2026-08-19']

DASH = '/tmp/claude-0/-home-user-260731-/b712c619-9f83-5eb1-85a3-154aeacff8b0/scratchpad/dash_data.json'
d = json.load(open(DASH))

# ---- 2025-01-01 ~ 오늘까지 영업일(월~금) 전체 배열을 새로 만든다 ----
# (daily.csv 에 2025-01~2025-11 국장+ISA 월말 백필이 추가되면서 기존 2026-01-01 시작
#  business-day 배열로는 범위가 안 맞아 통째로 재생성한다)
import datetime as _dt
_start = _dt.date(2025, 1, 1)
_end = _dt.date.fromisoformat(DATE)
_bdays = []
_cur = _start
while _cur <= _end:
    if _cur.weekday() < 5:
        _bdays.append(_cur.isoformat())
    _cur += _dt.timedelta(days=1)
# 월말이 주말인 달(5월/8월/11월 말일 등)도 있어 daily.csv 에 실제 데이터가 있는
# 날짜는 주말이라도 배열에서 빠지지 않게 챙긴다.
_bdays_set = set(_bdays)
for _dte in daily_by_date:
    if _start.isoformat() <= _dte <= DATE and _dte not in _bdays_set:
        _bdays.append(_dte)
        _bdays_set.add(_dte)
_bdays.sort()

def _series(field):
    out = []
    for dte in _bdays:
        r = daily_by_date.get(dte)
        v = collect.num(r[field]) if r and r.get(field) not in (None, '') else None
        out.append({'date': dte, 'v': v})
    return out

d['full_pnl'] = _series('surface_pnl')
d['full_eq'] = _series('equity')
d['full_expo'] = _series('expo_real')
d['full_credit'] = _series('credit')
d['full_lev_real'] = _series('lev_real')
for arr, key in ((d['full_pnl'], 'surface_pnl'), (d['full_eq'], 'equity'),
                 (d['full_expo'], 'expo_real'), (d['full_credit'], 'credit'),
                 (d['full_lev_real'], 'lev_real')):
    if arr and arr[-1]['date'] == DATE:
        arr[-1]['v'] = m[key]

d['series'][-1] = {
    'date': DATE, 'equity': m['equity'], 'kr_eq': m['국장_equity'],
    'liq_room': m['liq_room'], 'cash_ratio': m['cash_ratio'],
    'debt_to_salary': m['debt_to_salary'], 'lev_real': m['lev_real'],
    'expo_real': m['expo_real'], 'credit': m['credit'],
}

mon = d['monthly'][-1]
assert mon['month'] == '2026-08'
prev_month_pnl = d['monthly'][-2]['pnl_vs_principal']
mon['asof'] = DATE
mon['equity'] = m['equity']
mon['own_equity'] = m['own_equity']
mon['pnl_vs_principal'] = m['surface_pnl']
mon['change_vs_prev'] = m['surface_pnl'] - prev_month_pnl
mon['in_progress'] = True
for a in mon['accounts']:
    acct = a['account']
    a['equity'] = m[acct + '_equity']
    a['principal'] = collect.num(common.get('principal_' + acct, a['principal']))
    a['pnl'] = a['equity'] - a['principal']

prior_acct_equity = {'국장': collect.num(prior['국장_equity']),
                      '미장': collect.num(prior['미장_equity']),
                      'ISA': collect.num(prior['ISA_equity'])}
hero = []
for acct in ('국장', '미장', 'ISA'):
    surface = m[acct + '_equity'] - collect.num(common.get('principal_' + acct, 0))
    if acct == '미장':
        net = surface - m['cum_tax_est']
        tax_applied = True
    else:
        net = surface
        tax_applied = False
    dod = m[acct + '_equity'] - prior_acct_equity[acct]
    hero.append({'account': acct, 'surface_pnl': surface, 'net_pnl': net,
                 'tax_applied': tax_applied, 'dod': dod})
hero_net_total = sum(h['net_pnl'] for h in hero) - m['cum_course_fees']
hero_total_dod = m['equity'] - collect.num(prior['equity'])

trades = collect.read_csv('journal.csv')
for t in trades:
    for k in ('qty', 'price', 'amount', 'realized_pnl'):
        t[k] = collect.num(t[k], None) if t[k] not in ('', None) else None
view_log = collect.read_csv('viewtracker.csv')
for v in view_log:
    v['score'] = collect.num(v['score'])

cashflow = collect.read_csv('cashflow.csv')
for c in cashflow:
    c['amount'] = collect.num(c['amount'])
cashflow.sort(key=lambda r: r['date'])

actions = collect.read_csv('actions.csv')

d['date'] = DATE
d['prior_date'] = '2026-08-19'
d['asof'] = {'credit': DATE, 'positions': DATE, 'cash': DATE}
d['metrics'] = m
d['signals'] = signals
d['positions'] = pos_out
d['sector_rank'] = sector_rank
d['lev_breakdown'] = lev_breakdown
d['acct_expo'] = acct_expo
d['hero_by_account'] = hero
d['hero_net_total'] = hero_net_total
d['hero_total_dod'] = hero_total_dod
d['trades'] = trades
d['view_log'] = view_log
d['cashflow'] = cashflow
d['actions'] = actions
d['view_summary'] = (
    "8/17을 기점으로 데일리 패널(알상무·김기훈) 둘 다 Bull(+1)에서 중립~신중 쪽으로 톤다운됐습니다. "
    "8/19엔 김기훈이 -0.5로 전환하며 이란·유가·금리 부담을 이유로 '20% 정도 익절' 권고, "
    "알상무도 같은 날 '오늘은 관망'으로 물러섰습니다. 서재형은 장기·저빈도 스탠스라 변화 없음. "
    "최근 패널 톤이 신중 쪽으로 수렴한 시점이라 — 신규 레버리지 확대보다는 관망이나 일부 차익실현 쪽이 패널 컨센서스에 더 가깝습니다."
)

json.dump(d, open(DASH, 'w'), ensure_ascii=False)
print('OK, equity', m['equity'], 'lev_real', m['lev_real'], 'liq_room', m['liq_room'])
print('violations', [s['id'] for s in signals if s['signal'].startswith('🔴')])
print('cashflow rows', len(cashflow))
