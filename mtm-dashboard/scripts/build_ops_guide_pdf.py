# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                 ListFlowable, ListItem, HRFlowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = '/tmp/claude-0/-home-user-260731-/b712c619-9f83-5eb1-85a3-154aeacff8b0/scratchpad'
pdfmetrics.registerFont(TTFont('NanumGothic', f'{FONT_DIR}/NanumGothic-Regular.ttf'))
pdfmetrics.registerFont(TTFont('NanumGothic-Bold', f'{FONT_DIR}/NanumGothic-Bold.ttf'))

BOLD = 'NanumGothic-Bold'
REG = 'NanumGothic'

VERSION = 'v1.02'
DATE = '2026-08-23'

OUT = f'/tmp/claude-0/-home-user-260731-/b712c619-9f83-5eb1-85a3-154aeacff8b0/scratchpad/output/MtM_Dashboard_운영가이드_{VERSION}.pdf'

styles = {
    'title': ParagraphStyle('title', fontName=BOLD, fontSize=17, leading=21,
                             textColor=colors.HexColor('#1a2b4a'), spaceAfter=2),
    'subtitle': ParagraphStyle('subtitle', fontName=REG, fontSize=9, leading=12,
                                textColor=colors.HexColor('#666666'), spaceAfter=10),
    'h1': ParagraphStyle('h1', fontName=BOLD, fontSize=12.5, leading=16,
                          textColor=colors.HexColor('#1a2b4a'), spaceBefore=10, spaceAfter=5),
    'h2': ParagraphStyle('h2', fontName=BOLD, fontSize=10, leading=13,
                          textColor=colors.HexColor('#2f5496'), spaceBefore=6, spaceAfter=3),
    'body': ParagraphStyle('body', fontName=REG, fontSize=8.3, leading=12.2,
                            textColor=colors.HexColor('#222222')),
    'bullet': ParagraphStyle('bullet', fontName=REG, fontSize=8.3, leading=12,
                              textColor=colors.HexColor('#222222'), leftIndent=0),
    'small': ParagraphStyle('small', fontName=REG, fontSize=7.3, leading=10.5,
                             textColor=colors.HexColor('#777777')),
    'cell': ParagraphStyle('cell', fontName=REG, fontSize=7.6, leading=10.2,
                            textColor=colors.HexColor('#222222')),
    'cellhead': ParagraphStyle('cellhead', fontName=BOLD, fontSize=7.8, leading=10,
                                textColor=colors.white),
}

def P(text, style='body'):
    return Paragraph(text, styles[style])

def bullets(items, style='bullet'):
    return ListFlowable(
        [ListItem(P(t, style), leftIndent=10, spaceBefore=1.5) for t in items],
        bulletType='bullet', bulletFontSize=6, bulletColor=colors.HexColor('#2f5496'),
        leftIndent=12,
    )

story = []

story.append(P('MtM Dashboard 운영 가이드', 'title'))
story.append(P(f'개인 트레이딩 리스크관리 대시보드 · 버전 {VERSION} · {DATE} 기준 · 0.01 단위로 계속 갱신', 'subtitle'))
story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#1a2b4a'), spaceAfter=8))

# ── 1. 시스템 개요 ──
story.append(P('1. 시스템 개요', 'h1'))
story.append(P(
    '저장소: <b>andynet2014-sudo/Github-Repository-1</b> (구 260731-, 자동 리다이렉트됨) · '
    '폴더: <b>mtm-dashboard/</b> · 브랜치: <b>main</b> + <b>claude/google-drive-connector-folders-lu7bxq</b> (항상 두 곳에 동시 push) · '
    '핵심 엔진: <b>collect.py</b> (data/ 아래 csv들을 읽어 리스크 지표를 계산하고 daily.csv에 한 줄씩 기록).',
    'body'))
story.append(P(
    '추적 대상 계좌 3개만: <b>국장</b>(삼성증권 7089239210-01) · <b>ISA</b>(삼성증권 7156461048-14) · '
    '<b>미장</b>(나무증권 209-01-920722). 삼성증권 CMA/IRP/DC 등 나머지 계좌는 명시적으로 추적 범위 밖. '
    '중국/업비트 계좌는 daily.csv 순자산 추적 대상은 아니고, cashflow.csv에서 자금 이동 출발/도착지로만 등장.',
    'body'))

# ── 2. 핵심 규칙 ──
story.append(P('2. 핵심 규칙 · 반드시 지킬 컨벤션', 'h1'))

story.append(P('순자산 계산 공식', 'h2'))
story.append(bullets([
    '<b>equity(순자산) = 총평가금액(GROSS, 주식+예수금) - credit(신용대출)</b>. 브로커 리포트의 "총평가"가 '
    '이미 신용 차감된 값인지 GROSS인지 매번 확인할 것 — 2026-08 세션에서 이걸 착각해 국장 순자산이 '
    '실제의 약 2배로 잘못 들어간 적 있음(사용자 수기 실측치로 발견·수정).',
    'GROSS 값은 <b>국장_total</b> 칼럼에, 신용 차감 후 NET 값은 <b>국장_equity</b> 칼럼에 분리 저장.',
]))

story.append(P('데이터 우선순위', 'h2'))
story.append(bullets([
    '<b>사용자 수기 직접 입력 &gt; PDF/문서에서 파생 계산한 값</b>. 두 값이 있으면 항상 사용자 실측치로 덮어쓴다 '
    '— 라이브 collect.py 실측치보다도 사용자가 앱 화면에서 직접 옮긴 값을 우선한다.',
    '<b>신용(credit) 값은 반드시 앱의 "신용융자금" 탭에서 직접 읽은 값을 쓴다.</b> 월말잔고 PDF의 "대출" 컬럼이나 '
    '요약 형태로 재구성한 파일은 신뢰도가 낮을 수 있음 — 2026-08 세션에서 월별 요약 파일 기준 신용값이 실제 '
    '신용융자금 탭 값과 최대 30%까지 벌어진 사례를 확인, 신용융자금 탭 실측으로 전량 교체.',
    '근거 없는 값은 절대 추정해서 채우지 않는다 — 모르면 공란으로 둔다("원금이 조용히 틀리면 안 된다").',
    '월말이 주말인 스냅샷(예: 2026-01-31 토)은 <b>직전 금요일 날짜로 이동</b>해서 저장 — 거래 없는 주말의 '
    '계좌 상태는 직전 거래일과 동일하다는 원칙.',
    '라이브 실측과 사용자 수기값(평가손익추이 화면)은 D+2 예수금 인정 여부 차이로 며칠간 1~5%대 갭이 날 수 있음 '
    '— 정상 범위, 별도 조치 불필요.',
]))

story.append(P('cashflow.csv 항목 분류', 'h2'))
story.append(bullets([
    '<b>원금(principal) 이동으로 취급</b>: 개시잔액·외부입금·외부출금·계좌간이체 → 계좌 원금 기준을 바꿈.',
    '<b>원금 이동 아님, 별도 누계로만 집계</b>: 신용이자·강의구독비·수수료·매도세금·배당금 → collect.py의 '
    'load_cashflow_totals()가 principal 계산에서 제외하고 cum_interest/cum_course_fees/cum_trade_fees/'
    'cum_sec_tax/cum_dividend로 따로 합산. (이유: 이미 계좌 잔고 변동에 반영된 비용/수익을 원금에서도 '
    '빼면 손익이 이중으로 왜곡됨.)',
    '신용이자·수수료·매도세금·배당금은 사용자 요청으로 <b>일별이 아닌 월말 값만</b> 입력 — 효율성 우선.',
]))

story.append(P('daily.csv source 컬럼 표기', 'h2'))
story.append(bullets([
    '<font face="Courier">cache</font> / 실측 없음 = collect.py 라이브 실행 결과',
    '<font face="Courier">backfill(...)</font> = PDF·문서 기반으로 역산/추정한 과거값',
    '<font face="Courier">user</font>(수기 키인·...) = 사용자가 Numbers 템플릿에 직접 입력해 병합한 실측값 (가장 신뢰도 높음)',
]))

story.append(P('3. 데이터 파일 현황', 'h1'))

data_rows = [
    [P('파일', 'cellhead'), P('내용', 'cellhead'), P('형식', 'cellhead'), P('최신 반영 시점', 'cellhead')],
    [P('data/daily.csv', 'cell'), P('일별 순자산·레버리지·리스크 신호 스냅샷 (33칼럼)', 'cell'),
     P('CSV, 날짜별 1행', 'cell'),
     P('국장/ISA: 2026-01-02~08-21 거의 매일 수기(앱 평가손익추이+신용융자금 탭 기준, 최우선 신뢰) · '
       '라이브 collect.py: 2026-08-20까지 · 2025-01~2025-12은 월말 스냅샷만', 'cell')],
    [P('data/cashflow.csv', 'cell'), P('입출금·계좌이체·이자·수수료·세금·배당금 원장', 'cell'),
     P('CSV, 거래별 1행', 'cell'), P('2025-11-18(개시잔액)부터 2026-08-13까지 + 2026-01~07 월말 비용 항목', 'cell')],
    [P('data/journal.csv', 'cell'), P('매매일지(현재 SOXL·MRVL만 상세 기록)', 'cell'), P('CSV', 'cell'),
     P('미장 143개 종목 상세 백필은 사용자 요청으로 보류 중', 'cell')],
    [P('data/positions.csv\ndata/prices.csv', 'cell'), P('현재 보유 포지션·시세 (라이브 스냅샷)', 'cell'),
     P('CSV', 'cell'), P('collect.py 실행 시점 기준', 'cell')],
    [P('data/common.csv', 'cell'), P('계좌별 원금 시드값·급여·세금 추정치 등 고정 파라미터', 'cell'),
     P('CSV, key-value', 'cell'), P('principal_*은 이제 cashflow.csv에서 자동 파생(수정 불필요)', 'cell')],
    [P('data/viewtracker.csv\ndata/actions.csv', 'cell'), P('패널 시황 톤 로그 / 할 일 액션 아이템', 'cell'),
     P('CSV', 'cell'), P('수시 업데이트', 'cell')],
    [P('collect.py', 'cell'), P('리스크 엔진 — daily.csv 등을 읽어 지표 계산', 'cell'), P('Python', 'cell'),
     P('load_cashflow_totals()에 수수료/매도세금/배당금 반영(이번 세션)', 'cell')],
]
t = Table(data_rows, colWidths=[27*mm, 55*mm, 22*mm, 66*mm])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f5496')),
    ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f5fa')]),
    ('TOPPADDING', (0, 0), (-1, -1), 3.5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
]))
story.append(t)

story.append(P('4. 대시보드 아티팩트', 'h1'))
story.append(P(
    'URL: <font face="Courier">https://claude.ai/code/artifact/66481dfc-fea9-4c7e-8051-5adf12384a77</font> '
    '(고정 링크, 데이터 갱신 시 같은 URL에 재배포). daily.csv/cashflow.csv를 고치면 반드시 collect.py 기반 '
    'rebuild 스크립트로 dash_data.json을 재생성하고 risk-console.html에 주입 → jsdom 오류 0건 확인 → 재배포 → '
    'git commit·push 순서를 지킬 것.',
    'body'))

story.append(P('5. 사용자 To-Do', 'h1'))
story.append(bullets([
    '<b>2026-08-22 이후분 국장/ISA 일별 잔고를 Numbers 템플릿에 계속 키인</b>(1~8/21 완료) — 매달 신용이자/'
    '수수료/매도세금/배당금은 월말 값만 입력하면 됨. 신용은 반드시 "신용융자금" 탭 값으로.',
    '<b>국장 입금고/출금고 칼럼</b>: 이제 1~8월 데이터가 쌓여 기존 cashflow.csv 계좌간이체·외부입금 기록과의 '
    '날짜 차이(D+2 추정) 패턴 분석이 가능 — 다음 세션에서 진행 예정, 아직 cashflow.csv에는 미반영.',
    '삼성증권(국장/ISA)에서 계좌별 진짜 일별 잔고 export가 가능한지 계속 확인 — 가능해지면 수기 입력 대체.',
    '미장 143개 종목 매매일지(journal.csv) 상세 백필 여부 추후 결정.',
]))

story.append(Spacer(1, 6))
story.append(HRFlowable(width='100%', thickness=0.6, color=colors.HexColor('#cccccc')))
story.append(Spacer(1, 3))
_next_ver = 'v' + format(float(VERSION[1:]) + 0.01, '.2f')
story.append(P(f'{VERSION} · {DATE} 기준 · 다음 갱신 시 {_next_ver}로 버전업', 'small'))

doc = SimpleDocTemplate(OUT, pagesize=A4,
                         topMargin=16*mm, bottomMargin=14*mm, leftMargin=16*mm, rightMargin=16*mm,
                         title='MtM Dashboard 운영 가이드')
doc.build(story)
print('saved', OUT)
