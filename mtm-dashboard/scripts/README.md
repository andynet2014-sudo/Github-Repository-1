# scripts/

**전부 "그대로 재실행 가능한 도구"가 아니라, 특정 시점에 실행됐던 스크립트를 참고용으로
남긴 것이다.** 재사용하려면 하드코딩된 값(날짜, 파일 경로, 그날의 서술형 텍스트 등)을
그 상황에 맞게 고쳐야 한다.

- **`rebuild_dashboard_reference.py`** — `dashboard/risk-console.html`의 `DATA` 블록을
  만드는 데 쓴 실제 스크립트(2026-08-20 실행분). `collect.py`의 `compute()` 결과를
  가져다 대시보드가 기대하는 JSON 스키마(`signals`/`positions`/`sector_rank`/`hero_by_account`/
  `full_eq`/`full_credit` 등)로 조립하는 전체 로직이 여기 있다 — 이 스키마를 처음부터
  또 만들 필요 없이 이 파일을 베껴서 날짜·경로만 갈아 끼우면 된다. `DATE`, `prior` 날짜,
  `DASH` 출력 경로, `view_summary`(그날의 패널 시황 요약 텍스트)는 매번 바꿔야 한다.
- **`backfill_history_reference.py`** — 2025-01~2026-08 국장/ISA 월말 백필에 실제 썼던
  스크립트. `MONTHLY` 딕셔너리에 그 시점 기준 확정값이 하드코딩돼 있어 이미 실행 완료된
  상태 — 재실행할 필요는 없고, "월말 스냅샷 + 신용값을 daily.csv에 병합하는 방식"의
  예시로만 참고할 것.
- **`build_ops_guide_pdf.py`** — `MtM_Dashboard_운영가이드_v1.0x.pdf`를 만든 스크립트.
  한글 폰트는 Google Fonts에서 받은 Nanum Gothic(레포엔 없음, 스크립트 상단에서
  런타임에 다운로드) 사용. CLAUDE.md/DECISIONS.md 내용이 바뀌면 이 스크립트의 본문
  텍스트도 같이 고치고 `VERSION`을 올려 재실행할 것.
