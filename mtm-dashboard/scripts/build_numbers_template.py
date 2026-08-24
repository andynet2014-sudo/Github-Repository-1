"""사용자가 국장/ISA 일별 잔고를 수기로 채워 넣을 .numbers 템플릿을 만드는 스크립트.

패턴 참고용 — 실행하려면 아래를 먼저 손봐야 한다:
  - pip install numbers_parser (표준 의존성 아님, 이 스크립트 실행 세션에서만 설치)
  - START/END 날짜 범위를 원하는 기간으로 변경
  - daily.csv에서 이미 채워진 값(known)을 어디까지 회색으로 보여줄지 KNOWN_FIELDS 확인

핵심 기법:
  - numbers_parser.Style(font_size=...)에 정수(11)를 넘기면 TypeError 남 —
    반드시 float(11.0)로 넘길 것.
  - 평일만 넣되, 월말 스냅샷이 주말인 날짜는 예외로 살려서 포함(daily.csv의
    Friday-shift 컨벤션과 일치시키려면 애초에 데이터 쪽에서 이미 금요일로
    옮겨져 있어야 함 — CLAUDE.md의 날짜 규칙 참고).
"""
import csv
import datetime
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from numbers_parser import Document, Style, Alignment

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data')

START = datetime.date(2026, 9, 1)
END = datetime.date(2026, 12, 31)
OUT_PATH = '/tmp/mtm_daily_template.numbers'

rows = list(csv.DictReader(open(os.path.join(DATA, 'daily.csv'))))
known = {r['date']: r for r in rows}

dates = []
d = START
while d <= END:
    if d.weekday() < 5:  # 평일만
        dates.append(d.isoformat())
    d += datetime.timedelta(days=1)
# 이미 daily.csv에 실측치가 있는 날짜(주말 포함)는 빠지지 않게 챙긴다
for ds, r in known.items():
    if START.isoformat() <= ds <= END.isoformat() and ds not in dates:
        if r.get('국장_equity') or r.get('credit') or r.get('ISA_equity'):
            dates.append(ds)
dates.sort()

data = []
for ds in dates:
    r = known.get(ds, {})
    data.append((ds, r.get('국장_equity') or None, r.get('credit') or None, r.get('ISA_equity') or None))

FONT = 'Arial'
doc = Document(sheet_name='일별 잔고', table_name='daily',
                num_header_rows=4, num_rows=4 + len(data), num_cols=4)
table = doc.sheets[0].tables[0]

title_style = Style(font_name=FONT, bold=True, font_size=13.0)
note_style = Style(font_name=FONT, italic=True, font_size=9.0, font_color=(128, 128, 128))
header_style = Style(font_name=FONT, bold=True, font_size=11.0, font_color=(255, 255, 255),
                      bg_color=(47, 84, 150), alignment=Alignment('center', 'middle'))
known_style = Style(font_name=FONT, font_size=10.0, font_color=(89, 89, 89), bg_color=(242, 242, 242))
blank_style = Style(font_name=FONT, font_size=10.0, bg_color=(255, 242, 204))
date_style = Style(font_name=FONT, font_size=10.0)

table.write(0, 0, 'MtM Dashboard — 일별 잔고 수기 입력용', style=title_style)
table.write(1, 0, '주말 제외(평일만) · 월말이 주말인 경우 직전 금요일 값으로 반영됨 · '
                   '회색 셀=기존값(참고용) · 노란 셀=채워주세요 · ISA는 신용 없음', style=note_style)
headers = ['날짜', '국장 총평가금액', '국장 신용금액', 'ISA 총평가금액']
for col, h in enumerate(headers):
    table.write(3, col, h, style=header_style)

row = 4
for ds, kr_eq, credit, isa_eq in data:
    table.write(row, 0, ds, style=date_style)
    for col, val in ((1, kr_eq), (2, credit), (3, isa_eq)):
        if val:
            table.write(row, col, int(float(val)), style=known_style)
        else:
            table.write(row, col, '', style=blank_style)
    row += 1

table.col_width(0, 100)
table.col_width(1, 140)
table.col_width(2, 130)
table.col_width(3, 130)

doc.save(OUT_PATH)
print('saved', OUT_PATH, '-', len(data), 'rows')
