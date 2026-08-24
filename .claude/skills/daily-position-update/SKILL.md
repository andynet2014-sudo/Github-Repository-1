---
name: daily-position-update
description: >
  MtM-Dashboard 저장소(mtm-dashboard/)에서 하는 일일/종가 포지션 업데이트 워크플로.
  사용자가 "오늘 포지션 업데이트해줘", "종가 스냅샷 찍어줘", "collect.py 돌려줘",
  "positions.csv 반영해줘", "오늘 매매 반영", "예수금/신용잔고 바뀐 거 넣어줘"처럼
  거래일 마감 후 데이터 갱신을 요청할 때, 또는 daily.csv/cashflow.csv를 고쳐서
  대시보드 아티팩트에도 반영해야 할 때 반드시 이 스킬을 사용할 것. "포지션"이나
  "종가"라는 단어가 없어도 이 저장소에서 오늘자 계좌/종목 수치를 갱신·기록·검증하는
  요청이면 트리거해야 한다.
---

# 일일 포지션 업데이트

이 저장소는 **매일 입력을 0으로 만드는 것**이 목표다 (`mtm-dashboard/README.md` 1줄
요약). 이 스킬은 그 반복 작업을 실수 없이 빠르게 끝내기 위한 체크리스트다 — 계산
규칙 자체는 여기 옮겨적지 않는다. **작업 시작 전에 반드시
`mtm-dashboard/CLAUDE.md`와 `mtm-dashboard/README.md`를 읽어라.** 두 파일이
원본이고 이 스킬은 절차 안내일 뿐이다. 두 문서와 이 스킬이 어긋나면 문서가 맞다 —
스킬을 갱신해야 한다는 신호다.

## 0. 오늘 뭘 해야 하는지 먼저 판단한다

사용자 요청을 아래 세 갈래 중 어디에 해당하는지 먼저 분류한다. 여러 개가 겹칠 수
있다.

- **A. 거래/입출금/신용변동이 있었던 날** → `data/positions.csv` 사람이 직접 수정
  필요 (아래 1)
- **B. 그냥 오늘자 시세로 스냅샷만 찍는 날** (매매 없음) → positions.csv 수정 없이
  바로 `collect.py` 실행 (아래 2)
- **C. daily.csv/cashflow.csv가 바뀌어서 웹 대시보드 아티팩트도 갱신해야 하는 날**
  → 아래 4 "대시보드 반영 절차" 수행

거래가 없는 주말/공휴일에는 원칙적으로 새로 찍지 않는다 (직전 거래일 상태와
동일 — `CLAUDE.md` 날짜 규칙 참고). 사용자가 특정 날짜를 지정하면 그 규칙대로
월말 주말은 직전 금요일로 이동해서 기록한다.

## 1. positions.csv 갱신 (매매/입출금/신용변동이 있었던 날만)

`mtm-dashboard/data/positions.csv`가 사람이 직접 만지는 핵심 파일이다. 종목 행뿐
아니라 계좌별 예수금(`sector=현금`, `ticker=CASH_계좌명`)과 신용잔고
(`sector=신용`, `ticker=CREDIT_국장`)도 이 파일의 행이라는 걸 잊지 말 것.

사용자에게 바뀐 내용을 물어보거나 사용자가 이미 준 정보로 다음을 채운다:

- 신규/청산 종목: 종목명·티커·수량·평단·손절가·섹터·레버리지(`lev`, 레버리지
  ETF는 반드시 명시)
- 기존 종목 수량/평단 변동: 추가매수·일부매도 반영
- 예수금 변동: 해당 계좌의 `CASH_*` 행 값 갱신
- **신용(credit) 값을 바꿀 때는 반드시 사용자가 앱의 "신용융자금" 탭을 직접 보고
  불러준 값만 쓴다.** 월말잔고 PDF나 사용자 기억에 의존한 값은 쓰지 않는다 —
  `CLAUDE.md`에 최대 30% 오차 사례가 기록돼 있다. 출처가 불확실하면 그 자리에서
  사용자에게 재확인한다.
- `current_price_krw`는 사람이 손대는 칸이 아니다 — `collect.py`가 시세 조회 시
  자동 갱신한다. 건드리지 말 것.

수정 후 diff를 사용자에게 보여주고 확인받는다 (숫자 파일이라 조용히 틀리면 바로
안 보인다).

## 2. collect.py 실행 (스냅샷 기록)

```bash
cd mtm-dashboard
python3 collect.py                 # 오늘자 수집·기록 (시세 조회 포함)
python3 collect.py --dry           # 검증만, 저장 안 함 — positions.csv 수정 후 먼저 이걸로 확인 권장
python3 collect.py --no-fetch      # 시세 조회 없이 캐시로 재계산
python3 collect.py --date YYYY-MM-DD   # 특정 날짜로 기록 (백필 등)
python3 collect.py --emotion 탐욕       # 감정 태그를 daily.csv에 남길 때
```

같은 날 여러 번 돌려도 행이 늘지 않고 덮어쓰므로 재실행은 안전하다. 순서 원칙:

1. positions.csv를 고쳤다면 먼저 `--dry`로 계산 결과가 말이 되는지 확인
   (특히 순자산이 GROSS가 아니라 NET인지 — `총평가 - credit`).
2. 이상 없으면 옵션 없이 실행해 실제로 기록.
3. 시세 조회 실패 종목이 있으면 콘솔에 어떤 종목이 왜 실패했는지 뜬다 —
   무시하지 말고 `data/prices.csv`를 직접 채워야 하는지 판단한다.
4. 실행 후 `data/daily.csv`의 오늘 행과 `data/positions_history.csv`의 오늘
   스냅샷이 기대한 대로 들어갔는지 최소한 tail로 확인한다.

라이브 시세 실측치와 사용자가 앱 화면 보고 불러준 수기값이 갈리면, `CLAUDE.md`의
데이터 우선순위(수기값 > 파생계산값 > 추정값 금지)를 따른다 — 수기값이 있으면
그걸로 덮어쓰고 `daily.csv`의 `source` 칼럼에 `user(...)`로 남긴다.

## 3. (선택) 엑셀 종가 스냅샷

사용자가 "엑셀로도 뽑아줘"/"스냅샷 파일로 줘"처럼 파일 형태를 요청하면:

```bash
python3 export_to_xlsx.py                 # 오늘자
python3 export_to_xlsx.py --date YYYY-MM-DD
```

`collect.py`와 같은 계산 함수를 재사용하므로 숫자가 화면과 항상 일치한다.
생성물(`snapshot_*.xlsx`)은 git에 커밋하지 않는다(`.gitignore` 대상) — 필요하면
`SendUserFile`로 사용자에게 바로 전달한다.

## 4. 대시보드(아티팩트) 반영 절차 — daily.csv/cashflow.csv를 고쳤을 때만

이 단계는 웹 대시보드 아티팩트에 보이는 숫자가 바뀌어야 할 때만 필요하다 (단순
포지션 스냅샷 기록만으로는 불필요). `CLAUDE.md`의 "대시보드(아티팩트) 반영 절차"
섹션이 원본이며, 요약하면:

1. `python3 build_dash_data.py --date YYYY-MM-DD --prev-json data/dash_data.json
   --out data/dash_data.json` 로 `dash_data.json` 재생성 (`collect.py`의
   `compute()`/`judge()`를 재사용 — trades/view_*/ideas/notes/monthly 과거분 같은
   정성적 필드는 `--prev-json`에서 그대로 이어받는다).
2. `risk-console.html`의 `const DATA = {...}` 블록에 새 JSON을 주입한다. Python
   문자열 치환으로 할 경우 `re.sub`의 치환 문자열 인자에 백슬래시 이스케이프가
   해석되는 함정이 있다 — 인덱스 슬라이싱이나 `lambda` 치환을 써서 JSON 안의
   `\n`이 실제 줄바꿈으로 깨지는 걸 피한다.
3. jsdom으로 로드해 콘솔 에러 0건인지 확인한다.
4. Playwright로 라이트+다크 모드 스크린샷을 찍어 시각 확인한다.
5. 같은 아티팩트 URL로 재배포한다 — URL은 `CLAUDE.md`에 고정돼 있으니 새로
   만들지 말고 그 URL로 업데이트한다.
6. 커밋·푸시한다 (아래 5 참고).

이 절차나 CLAUDE.md의 규칙 자체를 바꾸는 작업이라면, CLAUDE.md와 짝을 이루는
운영 가이드 아티팩트(URL도 CLAUDE.md에 있음)도 같이 갱신하고 버전을 올린다.

## 5. 커밋

- `CLAUDE.md`에 따르면 검증 없이 큰 변경(계산 공식 변경, 대량 백필, 스키마 변경)은
  바로 커밋하지 않는다 — 위 절차로 검증한 뒤에만.
- 작은 수정(오늘자 positions.csv 한 줄, daily.csv 한 행처럼 이미 검증된 데이터
  추가)은 바로 커밋해도 된다.
- 어느 브랜치가 정식인지는 `CLAUDE.md` Git 섹션을 그때그때 확인한다 — 과거에
  다른 프로젝트(옵시디언 vault)가 실수로 이 저장소 main에 섞여 들어간 사고가
  있었으므로, 커밋 전에 `git status`/`git log`로 이상한 변경이 섞여 있지 않은지
  한 번 확인한다.
- 커밋 메시지는 무엇을(what) 나열하기보다 그날 있었던 일(매매/입출금/신용변동
  요약)을 한 줄로 남긴다.

## 자주 하는 실수 (재확인 포인트)

- 순자산을 GROSS(총평가)로 그대로 쓰고 credit을 안 뺐는지 — `국장_total`과
  `국장_equity`가 다른 칼럼이라는 것.
- credit 값 출처가 신용융자금 탭이 아니라 PDF/기억인지.
- 레버리지 ETF(`lev` 칼럼)를 안 채워서 Exposure가 축소 계산됐는지.
- 예수금/신용잔고를 `positions.csv`가 아니라 별도 파일에서 찾으려 했는지 —
  `accounts.csv`는 삭제됐다, 전부 `positions.csv` 행이다.
- cashflow.csv에 신용이자/강의구독비/수수료/매도세금/배당금을 principal(원금)로
  잘못 분류했는지 — 이 다섯은 원금 이동이 아니라 별도 누계다.
