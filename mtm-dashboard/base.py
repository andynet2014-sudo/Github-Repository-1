"""공용 저수준 유틸 — CSV 입출력, 숫자 파싱, HTTP 조회.

collect.py/pricing.py/macro.py/rules.py/report.py 가 전부 여기서만 가져다 쓴다
(순환 import 방지를 위해 이 파일은 다른 프로젝트 모듈을 import하지 않는다).
"""
import csv
import json
import os
import re
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
TIMEOUT = 10


def read_csv(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(name, rows, cols):
    with open(os.path.join(DATA, name), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def num(v, default=0.0):
    try:
        return float(str(v).replace(',', ''))
    except (TypeError, ValueError):
        return default


def _get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def _get_text(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode('euc-kr', errors='replace')


def _table_rows(html, table_class):
    """<table class="...">...</table> 안의 각 <tr>을 텍스트 셀 리스트로 뽑아낸다."""
    tables = re.findall(r'<table[^>]*class="%s"[^>]*>(.*?)</table>' % table_class, html, re.S)
    out = []
    for t in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
        table_cells = []
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
            cells = [re.sub('<[^>]+>', '', c).strip() for c in cells]
            cells = [c for c in cells if c]
            if cells:
                table_cells.append(cells)
        out.append(table_cells)
    return out
