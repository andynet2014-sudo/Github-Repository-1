"""리스크 룰북 — 지표를 룰에 매핑하고 위반 여부를 판정한다."""
from base import num

# (지표키, 방향)  'max' = 기준 초과면 위반 / 'min' = 기준 미만이면 위반
RULE_MAP = {
    'R01': ('lev_real', 'max', '과레버리지'),
    'R02': ('liq_room', 'min', '청산임박'),
    'R03': ('cash_ratio', 'min', '현금고갈'),
    'R04': ('stop_violations', 'max', '손절방치'),
    'R05': ('stop_loss_ratio', 'max', '한방리스크'),
    'R06': ('max_sector', 'max', '섹터쏠림'),
    'R07': ('lev_etf_ratio', 'max', '레버ETF과다'),
    'R08': ('debt_to_salary', 'max', '빚과다'),
    'R10': ('max_pos', 'max', '단일종목쏠림'),
}
# 시트 R07 은 기준값 칸이 비어 있어 항상 '준수'로 판정됩니다. 경고값(0.05)이
# 상한으로 쓰기엔 지나치게 낮아, 계좌 순자산의 50%를 잠정 기준으로 둡니다.
# R10(단일종목 쏠림)은 rules.csv 에 근거 있는 기준값이 채워지기 전까지 잠정치를
# 두지 않습니다 — 임계값을 지어내는 대신 '측정불가'로 정직하게 비워 둡니다.
FALLBACK_THRESHOLD = {'R07': 0.5}


def judge(metrics, rules):
    metrics = dict(metrics)
    # stop_at_cost(본전가=손절가, 사실상 미설정)도 '손절 관리 위반'에 포함한다 —
    # 안 그러면 R04가 실제로는 손절선이 없는 종목들을 '준수'로 잘못 읽는다.
    metrics['stop_violations'] = (metrics['stop_missing'] + metrics['stop_at_cost']
                                  + metrics['stop_below'])
    out = []
    for r in rules:
        rid = r['id']
        if rid not in RULE_MAP:
            continue
        key, direction, label = RULE_MAP[rid]
        thr = num(r['threshold'], None) if r['threshold'] not in ('', None) else None
        fallback = thr is None and rid in FALLBACK_THRESHOLD
        if fallback:
            thr = FALLBACK_THRESHOLD[rid]
        if thr is None:
            out.append((rid, label, metrics.get(key), None, '⚪ 측정불가', False))
            continue
        cur = metrics.get(key)
        bad = cur > thr if direction == 'max' else cur < thr
        out.append((rid, label, cur, thr, '🔴 위반' if bad else '🟢 준수', fallback))
    return out
