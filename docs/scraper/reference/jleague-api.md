# J리그 스크래퍼 API 레퍼런스

J리그 경기 데이터 스크래퍼의 API 상세 문서입니다.

## 개요

`jleague_match_scraper` 모듈은 J리그 공식 웹사이트(www.jleague.jp)에서 경기 정보를 자동으로 수집합니다. Selenium WebDriver를 사용하여 동적 페이지를 렌더링하고 데이터를 추출합니다.

## 주요 함수

### collect_jleague_match_data

J리그 경기 데이터를 수집하는 최상위 공개 API입니다.

#### 시그니처

```python
def collect_jleague_match_data(
    year: int | List[int],
    league: str | List[str] = "J리그1",
    parallel: bool = True,
    max_workers: int = 4
) -> Tuple[List[Dict[str, Any]], str]
```

#### 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `year` | `int \| List[int]` | (필수) | 수집 시즌 연도. 리스트 전달 시 범위 확장 |
| `league` | `str \| List[str]` | `"J리그1"` | 수집 리그명 |
| `parallel` | `bool` | `True` | 병렬 처리 사용 여부 |
| `max_workers` | `int` | `4` | 동시 실행 스레드 수 (병렬 모드에서만 사용) |

#### 지원 리그

| 리그명 | URL 코드 | 설명 |
|-------|---------|------|
| `"J리그1"` | `j1` | 명치안전 J1리그 |
| `"J리그2"` | `j2` | 명치안전 J2리그 |
| `"J리그3"` | `j3` | 명치안전 J3리그 |
| `"J리그1PO"` | `playoff` | J1 승격 플레이오프 |
| `"J리그2PO"` | `2playoff` | J2 승격 플레이오프 |

#### 반환값

```python
Tuple[List[Dict[str, Any]], str]
```

- **첫 번째 요소**: 수집된 경기 데이터 리스트
- **두 번째 요소**: 파일 저장용 파일명 (확장자 제외)

#### 파일명 생성 규칙

| 조건 | 파일명 예시 |
|-----|-----------|
| 단일 연도, 단일 리그 | `j1_match_2025` |
| 연도 범위, 단일 리그 | `j1_match_2023-2025` |
| 단일 연도, J1+J2+J3 | `jleague_match_2025` |
| 단일 연도, J1+J2 | `jleague1,2_match_2025` |

#### 사용 예제

```python
from src.scraper.jleague_match_scraper import collect_jleague_match_data

# 기본 사용법: 2025년 J리그1
data, filename = collect_jleague_match_data(year=2025)

# 여러 시즌 수집
data, filename = collect_jleague_match_data(
    year=[2023, 2025],
    league="J리그1"
)

# 여러 리그 수집
data, filename = collect_jleague_match_data(
    year=2025,
    league=["J리그1", "J리그2"]
)

# 순차 처리 사용
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=False
)

# 병렬 처리 워커 수 조정
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=True,
    max_workers=6
)
```

#### 예외

| 예외 | 발생 조건 |
|-----|----------|
| `ValueError` | 지원하지 않는 리그명 전달 시 |

---

### scrape_season_matches

전체 시즌(1~12월) 경기 데이터를 순차적으로 수집합니다.

#### 시그니처

```python
def scrape_season_matches(
    league_category: str,
    year: int,
    league_display_name: str,
    include_tracking: bool = True
) -> List[Dict[str, Any]]
```

#### 파라미터

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `league_category` | `str` | 리그 URL 코드 (`j1`, `j2`, `j3`, `playoff`, `2playoff`) |
| `year` | `int` | 시즌 연도 |
| `league_display_name` | `str` | 사용자 표시용 리그명 |
| `include_tracking` | `bool` | 트래킹 데이터 포함 여부 (기본값: True) |

#### 사용 예제

```python
from src.scraper.jleague_match_scraper import scrape_season_matches

data = scrape_season_matches(
    league_category="j1",
    year=2025,
    league_display_name="J리그1",
    include_tracking=True
)
```

---

### scrape_season_matches_parallel

전체 시즌 경기 데이터를 병렬로 수집합니다.

#### 시그니처

```python
def scrape_season_matches_parallel(
    league_category: str,
    year: int,
    league_display_name: str,
    max_workers: int = 4,
    include_tracking: bool = True
) -> List[Dict[str, Any]]
```

#### 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `league_category` | `str` | (필수) | 리그 URL 코드 |
| `year` | `int` | (필수) | 시즌 연도 |
| `league_display_name` | `str` | (필수) | 사용자 표시용 리그명 |
| `max_workers` | `int` | `4` | 동시 실행 스레드 수 |
| `include_tracking` | `bool` | `True` | 트래킹 데이터 포함 여부 |

---

### scrape_single_match

단일 경기 데이터를 수집합니다 (독립 WebDriver 사용).

#### 시그니처

```python
def scrape_single_match(
    url: str,
    year: int,
    league_name: str,
    include_tracking: bool = True
) -> Optional[Dict[str, Any]]
```

#### 파라미터

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `url` | `str` | 경기 상세 페이지 URL |
| `year` | `int` | 시즌 연도 |
| `league_name` | `str` | 리그명 |
| `include_tracking` | `bool` | 트래킹 데이터 포함 여부 |

#### 반환값

- 성공 시: 경기 데이터 딕셔너리
- 실패 시: `None`

---

## 상수 클래스

### TimeoutConfig

Selenium WebDriver 대기 시간 설정 (단위: 초)

| 상수 | 값 | 설명 |
|-----|---|------|
| `MATCH_DETAIL_PAGE` | 10 | 경기 상세 페이지 로딩 |
| `MATCH_LIST_PAGE` | 5 | 월별 경기 목록 페이지 로딩 |
| `TRACKING_TAB` | 3 | 트래킹 데이터 탭 활성화 |

### LeagueCategory

J리그 카테고리 Enum

| Enum 값 | 한글명 | URL 코드 |
|--------|-------|---------|
| `J1` | J리그1 | j1 |
| `J2` | J리그2 | j2 |
| `J3` | J리그3 | j3 |
| `J1_PLAYOFF` | J리그1PO | playoff |
| `J2_PLAYOFF` | J리그2PO | 2playoff |

### MatchDataKeys

반환 데이터 딕셔너리의 키 상수

```python
class MatchDataKeys:
    MEET_YEAR = "Meet_Year"
    LEAGUE_NAME = "LEAGUE_NAME"
    ROUND = "Round"
    GAME_DATETIME = "Game_Datetime"
    DAY = "Day"
    HOME_TEAM = "HomeTeam"
    AWAY_TEAM = "AwayTeam"
    HOME_DISTANCE = "HomeDistance"
    AWAY_DISTANCE = "AwayDistance"
    HOME_SPRINT = "HomeSprint"
    AWAY_SPRINT = "AwaySprint"
    AUDIENCE_QTY = "Audience_Qty"
    WEATHER = "Weather"
    TEMPERATURE = "Temperature"
    HUMIDITY = "Humidity"
```

## 관련 문서

- [J리그 튜토리얼](../tutorials/jleague-tutorial.md)
- [데이터 스키마](../explanations/data-schema.md)
- [병렬 처리 설정하기](../how-tos/parallel-collection.md)
