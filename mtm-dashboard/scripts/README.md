# scripts/

**전부 "그대로 재실행 가능한 도구"가 아니라, 특정 시점에 실행됐던 스크립트를 참고용으로
남긴 것이다.** 재사용하려면 하드코딩된 값(날짜, 파일 경로, 그날의 서술형 텍스트 등)을
그 상황에 맞게 고쳐야 한다.

- **`backfill_history_reference.py`** — 2025-01~2026-08 국장/ISA 월말 백필에 실제 썼던
  스크립트. `MONTHLY` 딕셔너리에 그 시점 기준 확정값이 하드코딩돼 있어 이미 실행 완료된
  상태 — 재실행할 필요는 없고, "월말 스냅샷 + 신용값을 daily.csv에 병합하는 방식"의
  예시로만 참고할 것.
- **`build_ops_guide_pdf.py`** — `MtM_Dashboard_운영가이드_v1.0x.pdf`를 만든 스크립트.
  한글 폰트는 Google Fonts의 Nanum Gothic을 스크립트 실행 시 자동 다운로드(레포엔
  폰트 파일 없음, `pip install reportlab` 필요). CLAUDE.md/DECISIONS.md 내용이 바뀌면
  이 스크립트의 본문 텍스트도 같이 고치고 `VERSION`을 올려 재실행할 것. 실행 검증 완료
  (2026-08-24).
- **`build_numbers_template.py`** — 사용자가 국장/ISA 일별 잔고를 수기로 채워 넣는
  Numbers 템플릿 생성 스크립트(`pip install numbers_parser` 필요). `START`/`END`
  날짜 범위만 바꿔서 다음 분기용 템플릿을 새로 뽑을 때 재사용. 실행 검증 완료
  (2026-08-24).
