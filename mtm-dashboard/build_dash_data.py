#!/usr/bin/env python3
"""웹 대시보드 아티팩트의 `const DATA = {...}` JSON을 재생성한다.

collect.py 의 compute()/judge() 를 그대로 재사용해서 숫자가 콘솔 출력과
항상 일치하게 만든다. trades/view_*/ideas/notes/principles/actions/
cashflow/trend/monthly(과거분)처럼 사람이 구글시트·채팅으로 직접 쌓는
정성적 내용은 이전 아티팩트 JSON에서 그대로 들고 온다 — 이 스크립트가
새로 만드는 건 날짜가 바뀌면 갱신돼야 하는 숫자 부분(metrics/signals/
positions/sector_rank/lev_breakdown/acct_expo/hero_*/asof/series 최신
포인트/full_* 최신 포인트/monthly 당월 항목/date/prior_date)뿐이다.

  python3 build_dash_data.py --date 2026-08-21 --prev-json old_dash_data.json --out dash_data.json
"""
import argparse, json, os
import collect

BASE = os.path.dirname(os.path.abspath(__file__))


def build_positions(rows_all):
    out = []
    for r in rows_all:
        cash = r['sector'] in ('현금', '신용')
        item = {
            'name': r['name'], 'account': r['account'], 'sector': r['sector'],
            'lev': r['lev'], 'qty': r['qty'], 'avg': collect.num(r['avg_price_krw']),
            'cur': r['price'], 'stop': collect.num(r['stop_price_krw']) if r['stop_price_krw'] not in ('', None) else None,
            'cash': r['sector'] == '현금', 'nominal': r['nominal'], 'real': r['real'],
        }
        if r['sector'] == '신용':
            continue  # 신용잔고는 포지션 목록에 안 보인다 — compute()과 동일 취급
        item['pnl'] = 0 if item['cash'] else (r['price'] - item['avg']) * r['qty']
        if not item['cash']:
            item['ticker'] = r['ticker']
            item['quote_ccy'] = r['quote_ccy']
        out.append(item)
    expo_real = sum(r['real'] for r in rows_all if r['sector'] not in ('현금', '신용'))
    for item in out:
        item['weight'] = item['real'] / expo_real if expo_real else 0.0
    return out


def build_sector_rank(rows):
    agg = {}
    for r in rows:
        agg[r['sector']] = agg.get(r['sector'], 0.0) + r['real']
    expo_real = sum(agg.values())
    ranked = sorted(agg.items(), key=lambda x: -x[1])
    return [{'name': k, 'value': v, 'pct': (v / expo_real if expo_real else 0.0)} for k, v in ranked]


def build_lev_breakdown(rows):
    lev_rows = [r for r in rows if r['lev'] > 1]
    lev_rows.sort(key=lambda r: -r['nominal'])
    return [{'name': r['name'], 'value': r['nominal']} for r in lev_rows]


def build_acct_expo(rows):
    out = {}
    for acct in ('국장', '미장', 'ISA'):
        out[acct] = sum(r['real'] for r in rows if r['account'] == acct)
    return out


def signal_tier(direction, value, warn, threshold, bad):
    if bad:
        return 'red'
    if warn is None:
        return 'green'
    if direction == 'max':
        return 'yellow' if value > warn else 'green'
    return 'yellow' if value < warn else 'green'


def build_signals(m, rules):
    metrics = dict(m)
    metrics['stop_violations'] = (metrics['stop_missing'] + metrics['stop_at_cost']
                                  + metrics['stop_below'])
    out = []
    for r in rules:
        rid = r['id']
        if rid not in collect.RULE_MAP:
            continue
        key, direction, label = collect.RULE_MAP[rid]
        thr = collect.num(r['threshold'], None) if r['threshold'] not in ('', None) else None
        fallback = thr is None and rid in collect.FALLBACK_THRESHOLD
        if fallback:
            thr = collect.FALLBACK_THRESHOLD[rid]
        warn = collect.num(r['warn'], None) if r['warn'] not in ('', None) else None
        cur = metrics.get(key)
        if thr is None:
            out.append({'id': rid, 'label': label, 'value': cur, 'threshold': None, 'warn': warn,
                        'direction': direction, 'tier': 'gray', 'signal': '⚪ 측정불가',
                        'fallback': False, 'key': key, 'principle': r['rule']})
            continue
        bad = cur > thr if direction == 'max' else cur < thr
        tier = signal_tier(direction, cur, warn, thr, bad)
        out.append({'id': rid, 'label': label, 'value': cur, 'threshold': thr, 'warn': warn,
                    'direction': direction, 'tier': tier,
                    'signal': '🔴 위반' if bad else '🟢 준수', 'fallback': fallback,
                    'key': key, 'principle': r['rule']})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--prev-json', required=True, help='직전 아티팩트에서 뽑아둔 DATA JSON (정성적 필드 원본)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    prev = json.load(open(a.prev_json, encoding='utf-8'))

    positions = collect.read_csv('positions.csv')
    common = {r['key']: r['value'] for r in collect.read_csv('common.csv')}
    common = collect.load_cashflow_totals(common)
    rules = collect.read_csv('rules.csv')
    instruments = collect.instrument_list(positions)
    prices, failed, price_rows = collect.fetch_price_table(instruments, False, a.date)
    for p in positions:
        if p['sector'] in collect.NONMARKET:
            prices[p['ticker']] = (collect.num(p['current_price_krw'] or p['avg_price_krw']),
                                   'manual(%s)' % p['sector'])
    m, rows_all = collect.compute(positions, prices, common)
    signals = build_signals(m, rules)
    pos_list = build_positions(rows_all)
    rows_stock = [r for r in rows_all if r['sector'] not in ('현금', '신용')]
    sector_rank = build_sector_rank(rows_stock)
    lev_breakdown = build_lev_breakdown(rows_stock)
    acct_expo = build_acct_expo(rows_stock)

    daily = {row['date']: row for row in collect.read_csv('daily.csv')}
    today_row = daily[a.date]
    prior_date = prev['date']
    prior_row = daily.get(prior_date, {})

    principal = {'국장': collect.num(common.get('principal_국장', 0)),
                 '미장': collect.num(common.get('principal_미장', 0)),
                 'ISA': collect.num(common.get('principal_ISA', 0))}
    tax_est = m['cum_tax_est']
    hero_by_account = []
    total_dod = 0.0
    for acct in ('국장', '미장', 'ISA'):
        eq = m[acct + '_equity']
        surface = eq - principal[acct]
        tax_applied = acct == '미장'
        net = surface - tax_est if tax_applied else surface
        prev_eq = collect.num(prior_row.get(acct + '_equity', '') or 0)
        dod = eq - prev_eq
        total_dod += dod
        hero_by_account.append({'account': acct, 'surface_pnl': surface, 'net_pnl': net,
                                'tax_applied': tax_applied, 'dod': dod})

    d = dict(prev)
    d['date'] = a.date
    d['prior_date'] = prior_date
    d['metrics'] = m
    d['signals'] = signals
    d['positions'] = pos_list
    d['sector_rank'] = sector_rank
    d['lev_breakdown'] = lev_breakdown
    d['acct_expo'] = acct_expo
    d['asof'] = {'credit': a.date, 'positions': a.date, 'cash': a.date}
    d['hero_by_account'] = hero_by_account
    d['hero_total_dod'] = total_dod
    d['hero_net_total'] = m['net_pnl']

    series_point = {'date': a.date, 'equity': m['equity'], 'kr_eq': m['국장_equity'],
                    'liq_room': m['liq_room'], 'cash_ratio': m['cash_ratio'],
                    'debt_to_salary': m['debt_to_salary'], 'lev_real': m['lev_real'],
                    'expo_real': m['expo_real'], 'credit': m['credit']}
    d['series'] = prev['series'] + [series_point]

    for key, val in (('full_pnl', m['net_pnl']), ('full_eq', m['equity']),
                     ('full_expo', m['expo_real']), ('full_credit', m['credit']),
                     ('full_lev_real', m['lev_real'])):
        d[key] = prev[key] + [{'date': a.date, 'v': val}]

    month = a.date[:7]
    monthly = list(prev['monthly'])
    prev_month_eq = None
    for entry in monthly:
        if entry['month'] < month:
            prev_month_eq = entry['equity']
    accounts = [{'account': acct, 'equity': m[acct + '_equity'], 'principal': principal[acct],
                'pnl': m[acct + '_equity'] - principal[acct]} for acct in ('국장', '미장', 'ISA')]
    new_month_entry = {
        'month': month, 'asof': a.date, 'equity': m['equity'], 'own_equity': m['own_equity'],
        'principal': m['principal_total'], 'pnl_vs_principal': m['surface_pnl'],
        'change_vs_prev': (m['equity'] - prev_month_eq) if prev_month_eq is not None else None,
        'accounts': accounts, 'in_progress': True,
    }
    if monthly and monthly[-1]['month'] == month:
        monthly[-1] = new_month_entry
    else:
        monthly.append(new_month_entry)
    d['monthly'] = monthly

    json.dump(d, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('written', a.out, 'equity=', m['equity'], 'net_pnl=', m['net_pnl'])
    if failed:
        print('시세 조회 실패(캐시 대체):', failed)


if __name__ == '__main__':
    main()
