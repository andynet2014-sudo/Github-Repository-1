# dashboard/

이 폴더 전까지는 이 저장소 어디에도 대시보드 자체의 소스 코드가 없었다(전부 세션
스크래치패드에서만 작업하고 Artifact로만 배포했음) — 2026-08-24에 처음 커밋.

- **`risk-console.html`** — MtM Dashboard 아티팩트의 실제 소스.
  https://claude.ai/code/artifact/66481dfc-fea9-4c7e-8051-5adf12384a77 에 배포된 것과
  거의 동일하지만, 파일 안의 `const DATA = {...}` 블록은 커밋 시점(2026-08-24 국장 데이터
  기준) 스냅샷이라 곧 stale해진다 — 최신 데이터를 반영하려면 루트의 `build_dash_data.py`로
  dash_data.json을 새로 만들고 이 파일의 DATA 블록에 주입한 뒤 Artifact로
  재배포해야 한다. **주입 시 Python `re.sub`의 문자열 치환 인자를 쓰면 안 된다** —
  백슬래시가 이스케이프로 해석돼 JSON이 깨진다(CLAUDE.md 참고). 인덱스 슬라이싱이나
  `lambda` 치환을 쓸 것.
- **`ops-guide.html`** — 운영 가이드 아티팩트의 소스.
  https://claude.ai/code/artifact/0d916ba7-e554-4d0e-bdf1-798c11331094 에 배포된 것.
  CLAUDE.md/DECISIONS.md 내용이 바뀌면 이 파일도 같이 갱신하고 버전(v1.02 등)을 올릴 것.
