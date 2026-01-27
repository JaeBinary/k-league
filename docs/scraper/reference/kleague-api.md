# K리그 스크래퍼 API 레퍼런스

K리그 경기 데이터 스크래퍼의 API 상세 문서입니다.

## 개요

`kleague_match_scraper` 모듈은 K리그 공식 웹사이트(www.kleague.com)에서 경기 정보를 자동으로 수집합니다. BeautifulSoup을 사용하여 정적 HTML을 파싱합니다.

## 주요 함수

### collect_kleague_match_data

K리그 경기 데이터를 수집하는 최상위 공개 API입니다.

#### 시그니처

```python
def collect_kleague_match_data(
    year: int | List[int],
    league: str | List[str] = "K리그1"
) -> Tuple[List[Dict[str, Any]], str]
```

#### 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `year` | `int \| List[int]` | (필수) | 수집 시즌 연도. 리스트 전달 시 범위 확장 |
| `league` | `str \| List[str]` | `"K리그1"` | 수집 리그명 |

#### 지원 리그

| 리그명 | API 코드 | 설명 |
|-------|---------|------|
| `"K리그1"` | `1` | 하나원큐 K리그1 (1부 리그) |
| `"K리그2"` | `2` | 하나원큐 K리그2 (2부 리그) |
| `"승강PO"` | `3` | 승강 플레이오프 |
| `"슈퍼컵"` | `4` | FA컵 우승팀 vs K리그 우승팀 |

#### 반환값

```python
Tuple[List[Dict[str, Any]], str]
```

- **첫 번째 요소**: 수집된 경기 데이터 리스트
- **두 번째 요소**: 파일 저장용 파일명 (확장자 제외)

#### 파일명 생성 규칙

| 조건 | 파일명 예시 |
|-----|-----------|
| 단일 연도, K리그1 | `kleague1_match_2025` |
| 단일 연도, K리그2 | `kleague2_match_2025` |
| 연도 범위, 단일 리그 | `kleague1_match_2023-2025` |
| 단일 연도, 여러 리그 | `kleague_match_2025` |

#### 사용 예제

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data

# 기본 사용법: 2025년 K리그1
data, filename = collect_kleague_match_data(year=2025)

# K리그2 수집
data, filename = collect_kleague_match_data(
    year=2025,
    league="K리그2"
)

# 여러 시즌 수집
data, filename = collect_kleague_match_data(
    year=[2023, 2025],
    league="K리그1"
)

# 여러 리그 수집
data, filename = collect_kleague_match_data(
    year=2025,
    league=["K리그1", "K리그2"]
)

# 승강 플레이오프 수집
data, filename = collect_kleague_match_data(
    year=2024,
    league="승강PO"
)
```

#### 예외

지원하지 않는 리그명 전달 시 경고 메시지를 출력하고 해당 리그를 건너뜁니다.

```
⛔ 지원하지 않는 리그: K리그3
   지원 리그: ['K리그1', 'K리그2', '승강PO', '슈퍼컵']
```

---

### parse_game_info

BeautifulSoup 객체에서 K리그 경기 정보를 파싱합니다.

#### 시그니처

```python
def parse_game_info(
    soup: BeautifulSoup,
    year: int,
    game_id: int
) -> Dict[str, Any]
```

#### 파라미터

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `soup` | `BeautifulSoup` | 파싱된 HTML 객체 |
| `year` | `int` | 시즌 연도 |
| `game_id` | `int` | K리그 경기 ID (1부터 시작) |

#### 반환값

추출된 경기 정보 딕셔너리. 필드 누락 시 해당 값은 `None`.

#### 사용 예제

```python
from bs4 import BeautifulSoup
from src.scraper.kleague_match_scraper import parse_game_info
from src.scraper.scraper import fetch_page

# URL에서 HTML 가져오기
url = "https://www.kleague.com/match.do?year=2025&meetSeq=1&gameId=1&startTabNum=3"
soup = fetch_page(url)

# 경기 정보 파싱
if soup:
    data = parse_game_info(soup, 2025, 1)
    print(data['HomeTeam'], 'vs', data['AwayTeam'])
```

---

### extract_value

레이블-값 형식의 문자열에서 값을 추출하고 정제합니다.

#### 시그니처

```python
def extract_value(text: str, remove_char: str = "") -> str
```

#### 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `text` | `str` | (필수) | `'항목 : 값'` 형태의 원본 문자열 |
| `remove_char` | `str` | `""` | 값에서 제거할 단위 문자 |

#### 반환값

정제된 값 문자열

#### 사용 예제

```python
from src.scraper.kleague_match_scraper import extract_value

# 관중 수 추출
extract_value("관중수 : 10,519", ",")  # "10519"

# 온도 추출
extract_value("온도 : 25°C", "°C")  # "25"

# 습도 추출
extract_value("습도 : 60%", "%")  # "60"
```

---

## 상수 클래스

### URLConfig

K리그 웹사이트 URL 템플릿

```python
class URLConfig:
    BASE_URL = "https://www.kleague.com"
    MATCH_DETAIL = "{BASE_URL}/match.do?year={year}&meetSeq={meet_seq}&gameId={game_id}&startTabNum={start_tab_num}"
```

### LeagueCode

K리그 API 파라미터 코드 매핑

| 상수 | 값 | 설명 |
|-----|---|------|
| `K_LEAGUE_1` | 1 | K리그1 (1부 리그) |
| `K_LEAGUE_2` | 2 | K리그2 (2부 리그) |
| `PLAYOFF` | 3 | 승강 플레이오프 |
| `SUPER_CUP` | 4 | 슈퍼컵 |

### MatchDataKeys

반환 데이터 딕셔너리의 키 상수

```python
class MatchDataKeys:
    MEET_YEAR = "Meet_Year"
    LEAGUE_NAME = "LEAGUE_NAME"
    ROUND = "Round"
    GAME_ID = "Game_id"
    GAME_DATETIME = "Game_Datetime"
    DAY = "Day"
    HOME_TEAM = "HomeTeam"
    AWAY_TEAM = "AwayTeam"
    HOME_RANK = "HomeRank"
    AWAY_RANK = "AwayRank"
    FIELD_NAME = "Field_Name"
    AUDIENCE_QTY = "Audience_Qty"
    WEATHER = "Weather"
    TEMPERATURE = "Temperature"
    HUMIDITY = "Humidity"
```

### CSSSelectors

BeautifulSoup CSS 선택자 패턴

| 상수 | 값 | 용도 |
|-----|---|------|
| `LEAGUE_NAME` | `#meetSeq option[selected]` | 리그명 추출 |
| `ROUND` | `#roundId option[selected]` | 라운드 추출 |
| `MATCH_DATETIME` | `div.versus p` | 경기 일시 추출 |
| `TEAM_INFO` | `#gameId option[selected]` | 팀 정보 추출 |
| `TEAM_RANK` | `#tab03 ul.compare > li` | 팀 순위 추출 |
| `STADIUM_INFO` | `ul.game-sub-info.sort-box li` | 경기장/날씨 정보 추출 |

---

## 시즌별 경기 수 데이터

K리그는 경기 ID가 1부터 순차 할당되므로 총 경기 수 정보가 필요합니다.

### SEASON_MATCH_COUNT

```python
SEASON_MATCH_COUNT = {
    # K리그1: 12팀 기준 228경기
    ("K리그1", 2023): 228,
    ("K리그1", 2024): 228,
    ("K리그1", 2025): 228,

    # K리그2: 팀 수 변동에 따라 경기 수 다름
    ("K리그2", 2023): 236,
    ("K리그2", 2024): 236,
    ("K리그2", 2025): 275,  # 2025년부터 팀 수 증가

    # 승강 플레이오프: 고정 4경기
    ("승강PO", 2023): 4,
    ("승강PO", 2024): 4,
    ("승강PO", 2025): 4,
}
```

### LEAGUE_NAME_TO_CODE

리그명 → API 코드 변환 테이블

```python
LEAGUE_NAME_TO_CODE = {
    "K리그1": 1,
    "K리그2": 2,
    "승강PO": 3,
    "슈퍼컵": 4,
}
```

## 관련 문서

- [K리그 튜토리얼](../tutorials/kleague-tutorial.md)
- [데이터 스키마](../explanations/data-schema.md)
- [여러 시즌 수집하기](../how-tos/collect-multi-season.md)
