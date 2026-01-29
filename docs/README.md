# K-League & J-League 데이터 수집 프로젝트 문서

이 문서는 K리그와 J리그 경기 데이터를 자동으로 수집하고 저장하는 프로젝트의 기술 문서입니다.

## 프로젝트 개요

이 프로젝트는 공식 웹사이트에서 축구 경기 데이터를 자동으로 수집하여 분석 가능한 형태로 저장합니다.

```
┌─────────────────────────────────────────────────────────────┐
│                      데이터 파이프라인                        │
│                                                             │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│   │ K리그   │     │         │     │  CSV    │              │
│   │ 웹사이트 │ ──> │ Scraper │ ──> │  파일   │              │
│   └─────────┘     │         │     └─────────┘              │
│                   │         │                               │
│   ┌─────────┐     │         │     ┌─────────┐              │
│   │ J리그   │ ──> │         │ ──> │ SQLite  │              │
│   │ 웹사이트 │     │         │     │   DB    │              │
│   └─────────┘     └─────────┘     └─────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 빠른 시작

### 설치

```bash
# 필수 패키지 설치
pip install pandas beautifulsoup4 selenium rich requests sqlalchemy
```

### K리그 데이터 수집 및 저장

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data
from src.saver import save_to_csv, save_to_db

# 데이터 수집
data, filename = collect_kleague_match_data(year=2025, league="K리그1")

# CSV로 저장
save_to_csv(data, filename)

# 또는 SQLite DB로 저장
save_to_db(data, table_name="kleague1_2025")
```

### J리그 데이터 수집 및 저장

```python
from src.scraper.jleague_match_scraper import collect_jleague_match_data
from src.saver import save_to_csv, save_to_db

# 데이터 수집 (병렬 처리)
data, filename = collect_jleague_match_data(year=2025, league="J리그1")

# 저장
save_to_csv(data, filename)
```

## 문서 구조

### Scraper 모듈

웹사이트에서 경기 데이터를 자동으로 수집하는 모듈입니다.

| 문서 | 설명 |
|-----|------|
| [시작하기](./scraper/get-started.md) | 스크래퍼 빠른 시작 가이드 |
| [K리그 튜토리얼](./scraper/tutorials/kleague-tutorial.md) | K리그 데이터 수집 단계별 가이드 |
| [J리그 튜토리얼](./scraper/tutorials/jleague-tutorial.md) | J리그 데이터 수집 단계별 가이드 |
| [여러 시즌 수집](./scraper/how-tos/collect-multi-season.md) | 다년도 데이터 수집 방법 |
| [병렬 처리 설정](./scraper/how-tos/parallel-collection.md) | J리그 병렬 수집 최적화 |
| [아키텍처](./scraper/explanations/architecture.md) | 스크래퍼 내부 동작 원리 |
| [데이터 스키마](./scraper/explanations/data-schema.md) | 수집 데이터 필드 정의 |
| [K리그 API](./scraper/reference/kleague-api.md) | K리그 스크래퍼 API 레퍼런스 |
| [J리그 API](./scraper/reference/jleague-api.md) | J리그 스크래퍼 API 레퍼런스 |
| [트러블슈팅](./scraper/troubleshooting.md) | 오류 해결 가이드 |
| [용어 사전](./scraper/glossary.md) | 스크래퍼 관련 용어 정의 |

### Saver 모듈

수집된 데이터를 파일 또는 데이터베이스로 저장하는 모듈입니다.

| 문서 | 설명 |
|-----|------|
| [시작하기](./saver/get-started.md) | Saver 빠른 시작 가이드 |
| [CSV 저장](./saver/tutorials/save-to-csv.md) | CSV 파일 저장 튜토리얼 |
| [DB 저장](./saver/tutorials/save-to-database.md) | SQLite DB 저장 튜토리얼 |
| [데이터 추가](./saver/how-tos/append-data.md) | 기존 데이터에 추가하기 |
| [커스텀 타입](./saver/how-tos/custom-dtype.md) | DB 컬럼 타입 직접 지정 |
| [아키텍처](./saver/explanations/architecture.md) | Saver 모듈 내부 구조 |
| [타입 추론](./saver/explanations/type-inference.md) | 자동 타입 추론 메커니즘 |
| [CSV API](./saver/reference/csv-saver-api.md) | save_to_csv 레퍼런스 |
| [DB API](./saver/reference/db-saver-api.md) | save_to_db 레퍼런스 |
| [트러블슈팅](./saver/troubleshooting.md) | 오류 해결 가이드 |
| [용어 사전](./saver/glossary.md) | Saver 관련 용어 정의 |

## 지원 리그

### K리그

| 리그 | 파라미터 | 설명 |
|-----|---------|------|
| K리그1 | `"K리그1"` | 1부 리그 (12팀) |
| K리그2 | `"K리그2"` | 2부 리그 |
| 승강 플레이오프 | `"승강PO"` | 승강 결정전 |
| 슈퍼컵 | `"슈퍼컵"` | FA컵 vs K리그 우승팀 |

### J리그

| 리그 | 파라미터 | 설명 |
|-----|---------|------|
| J리그1 | `"J리그1"` | 1부 리그 (20팀) |
| J리그2 | `"J리그2"` | 2부 리그 (22팀) |
| J리그3 | `"J리그3"` | 3부 리그 |
| J1 플레이오프 | `"J리그1PO"` | J1 승격 플레이오프 |
| J2 플레이오프 | `"J리그2PO"` | J2 승격 플레이오프 |

## 수집 데이터

### 공통 필드

| 필드 | 설명 | 예시 |
|-----|------|------|
| `Meet_Year` | 시즌 연도 | `2025` |
| `LEAGUE_NAME` | 리그명 | `"K리그1"`, `"J리그1"` |
| `Round` | 라운드 | `"1R"`, `1` |
| `Game_Datetime` | 경기 일시 | `"2025-02-15 14:00:00"` |
| `Day` | 요일 | `"토"` |
| `HomeTeam` | 홈팀 | `"울산"`, `"浦和レッズ"` |
| `AwayTeam` | 어웨이팀 | `"포항"`, `"鹿島アントラーズ"` |
| `Audience_Qty` | 관중 수 | `15234` |
| `Weather` | 날씨 | `"맑음"` |
| `Temperature` | 온도 (°C) | `"18"` |
| `Humidity` | 습도 (%) | `"55"` |

### K리그 전용 필드

#### 기본 필드

| 필드 | 설명 |
|-----|------|
| `Game_id` | 경기 ID |
| `HomeRank` | 홈팀 순위 |
| `AwayRank` | 어웨이팀 순위 |
| `HomePoints` | 홈팀 승점 |
| `AwayPoints` | 어웨이팀 승점 |
| `Field_Name` | 경기장명 |

#### API 통계 데이터

K리그 공식 API를 통해 수집되는 추가 통계 데이터:

**기본 기록**
- 점유율 (`home_possession`, `away_possession`)
- 슈팅 (`home_attempts`, `away_attempts`, `home_on_target`, `away_on_target`)
- 파울 (`home_fouls`, `away_fouls`)
- 카드 (`home_yellow_cards`, `away_yellow_cards`, `home_red_cards`, `away_red_cards`, `home_double_yellow_cards`, `away_double_yellow_cards`)
- 코너킥 (`home_corners`, `away_corners`)
- 프리킥 (`home_free_kicks`, `away_free_kicks`)
- 오프사이드 (`home_offsides`, `away_offsides`)

**시간대별 점유율**
- 전반: `home_first_15_possession`, `home_first_30_possession`, `home_first_45_possession`
- 후반: `home_second_15_possession`, `home_second_30_possession`, `home_second_45_possession`
- 어웨이팀도 동일한 구조

### J리그 전용 필드 (트래킹 데이터)

| 필드 | 설명 |
|-----|------|
| `HomeDistance` | 홈팀 총 주행거리 (km) |
| `AwayDistance` | 어웨이팀 총 주행거리 (km) |
| `HomeSprint` | 홈팀 스프린트 횟수 |
| `AwaySprint` | 어웨이팀 스프린트 횟수 |

## 프로젝트 구조

```
k-league/
├── src/
│   ├── scraper/                 # 데이터 수집 모듈
│   │   ├── kleague_match_scraper.py
│   │   ├── jleague_match_scraper.py
│   │   └── scraper.py           # 공통 유틸리티
│   └── saver/                   # 데이터 저장 모듈
│       ├── csv_saver.py
│       └── db_saver.py
├── data/                        # 저장된 데이터
│   ├── *.csv
│   └── match.db
├── docs/                        # 문서
│   ├── README.md                # 이 파일
│   ├── scraper/                 # 스크래퍼 문서
│   └── saver/                   # Saver 문서
└── notebooks/                   # 분석 노트북
```

## 기술 스택

| 도구 | 용도 |
|-----|------|
| **Python 3.8+** | 기본 언어 |
| **pandas** | 데이터 처리 및 변환 |
| **BeautifulSoup4** | HTML 파싱 (K리그) |
| **Selenium** | 동적 페이지 크롤링 (J리그) |
| **SQLAlchemy** | 데이터베이스 연동 |
| **Rich** | 콘솔 진행률 표시 |

## 라이선스

이 프로젝트의 코드는 교육 및 개인 분석 목적으로 사용할 수 있습니다. 수집된 데이터의 저작권은 각 리그(K리그, J리그)에 있습니다.

## 기여

버그 리포트, 기능 제안, 문서 개선 등 모든 기여를 환영합니다.
