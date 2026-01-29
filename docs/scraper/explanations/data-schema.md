# 데이터 스키마

이 문서에서는 K리그와 J리그 스크래퍼가 수집하는 데이터 필드의 의미와 형식을 설명합니다.

## 개념 소개

스크래퍼는 웹사이트에서 추출한 원본 데이터를 정제하여 일관된 스키마의 딕셔너리로 반환합니다. 각 경기는 하나의 딕셔너리로 표현되며, 전체 데이터셋은 딕셔너리 리스트입니다.

## K리그 데이터 스키마

K리그 스크래퍼가 수집하는 데이터 필드입니다.

### 필드 상세

| 필드명 | 타입 | 설명 | 예시 |
|-------|------|------|------|
| `Meet_Year` | int | 시즌 연도 | `2025` |
| `LEAGUE_NAME` | str | 리그명 | `"K리그1"` |
| `Round` | str | 라운드 | `"1R"`, `"최종전"` |
| `Game_id` | int | 경기 ID (시즌 내 고유) | `1` ~ `228` |
| `Game_Datetime` | str | 경기 일시 (ISO 8601) | `"2025-02-15 14:00:00"` |
| `Day` | str | 요일 | `"토"`, `"일"` |
| `HomeTeam` | str | 홈팀명 | `"울산"` |
| `AwayTeam` | str | 어웨이팀명 | `"포항"` |
| `HomeRank` | int | 홈팀 순위 | `1` ~ `12` |
| `AwayRank` | int | 어웨이팀 순위 | `1` ~ `12` |
| `HomePoints` | int | 홈팀 승점 | `7` |
| `AwayPoints` | int | 어웨이팀 승점 | `4` |
| `Field_Name` | str | 경기장명 | `"울산문수월드컵경기장"` |
| `Audience_Qty` | str | 관중 수 | `"15234"` |
| `Weather` | str | 날씨 | `"맑음"`, `"흐림"` |
| `Temperature` | str | 온도 (°C) | `"18"` |
| `Humidity` | str | 습도 (%) | `"55"` |

### 경기 통계 필드 (API)

K리그 공식 API에서 추가로 수집되는 경기 통계 데이터입니다.

#### 기본 기록 (matchRecord API)

| 필드명 | 타입 | 설명 | 예시 |
|-------|------|------|------|
| `home_possession` | int | 홈팀 점유율 (%) | `55` |
| `away_possession` | int | 어웨이팀 점유율 (%) | `45` |
| `home_attempts` | int | 홈팀 슈팅 시도 | `15` |
| `away_attempts` | int | 어웨이팀 슈팅 시도 | `8` |
| `home_on_target` | int | 홈팀 유효 슈팅 | `6` |
| `away_on_target` | int | 어웨이팀 유효 슈팅 | `3` |
| `home_fouls` | int | 홈팀 파울 | `12` |
| `away_fouls` | int | 어웨이팀 파울 | `14` |
| `home_yellow_cards` | int | 홈팀 옐로 카드 | `2` |
| `away_yellow_cards` | int | 어웨이팀 옐로 카드 | `3` |
| `home_red_cards` | int | 홈팀 레드 카드 | `0` |
| `away_red_cards` | int | 어웨이팀 레드 카드 | `1` |
| `home_double_yellow_cards` | int | 홈팀 경고누적 퇴장 | `0` |
| `away_double_yellow_cards` | int | 어웨이팀 경고누적 퇴장 | `0` |
| `home_corners` | int | 홈팀 코너킥 | `5` |
| `away_corners` | int | 어웨이팀 코너킥 | `3` |
| `home_free_kicks` | int | 홈팀 프리킥 | `18` |
| `away_free_kicks` | int | 어웨이팀 프리킥 | `15` |
| `home_offsides` | int | 홈팀 오프사이드 | `2` |
| `away_offsides` | int | 어웨이팀 오프사이드 | `1` |

#### 시간대별 점유율 (possession API)

| 필드명 | 타입 | 설명 | 예시 |
|-------|------|------|------|
| `home_first_15_possession` | float | 홈팀 전반 0~15분 점유율 (%) | `52.3` |
| `home_first_30_possession` | float | 홈팀 전반 0~30분 점유율 (%) | `54.1` |
| `home_first_45_possession` | float | 홈팀 전반 0~45분 점유율 (%) | `55.8` |
| `home_second_15_possession` | float | 홈팀 후반 0~15분 점유율 (%) | `48.2` |
| `home_second_30_possession` | float | 홈팀 후반 0~30분 점유율 (%) | `50.5` |
| `home_second_45_possession` | float | 홈팀 후반 0~45분 점유율 (%) | `53.7` |
| `away_first_15_possession` | float | 어웨이팀 전반 0~15분 점유율 (%) | `47.7` |
| `away_first_30_possession` | float | 어웨이팀 전반 0~30분 점유율 (%) | `45.9` |
| `away_first_45_possession` | float | 어웨이팀 전반 0~45분 점유율 (%) | `44.2` |
| `away_second_15_possession` | float | 어웨이팀 후반 0~15분 점유율 (%) | `51.8` |
| `away_second_30_possession` | float | 어웨이팀 후반 0~30분 점유율 (%) | `49.5` |
| `away_second_45_possession` | float | 어웨이팀 후반 0~45분 점유율 (%) | `46.3` |

### 예시 데이터

```python
{
    # 기본 메타데이터
    'Meet_Year': 2025,
    'LEAGUE_NAME': 'K리그1',
    'Round': '1R',
    'Game_id': 1,
    'Game_Datetime': '2025-02-15 14:00:00',
    'Day': '토',
    'HomeTeam': '울산',
    'AwayTeam': '포항',
    'HomeRank': 1,
    'AwayRank': 3,
    'HomePoints': 7,
    'AwayPoints': 4,
    'Field_Name': '울산문수월드컵경기장',
    'Audience_Qty': '15234',
    'Weather': '맑음',
    'Temperature': '8',
    'Humidity': '45',

    # API 통계 데이터 (기본 기록)
    'home_possession': 55,
    'away_possession': 45,
    'home_attempts': 15,
    'away_attempts': 8,
    'home_on_target': 6,
    'away_on_target': 3,
    'home_fouls': 12,
    'away_fouls': 14,
    'home_yellow_cards': 2,
    'away_yellow_cards': 3,
    'home_red_cards': 0,
    'away_red_cards': 1,
    'home_double_yellow_cards': 0,
    'away_double_yellow_cards': 0,
    'home_corners': 5,
    'away_corners': 3,
    'home_free_kicks': 18,
    'away_free_kicks': 15,
    'home_offsides': 2,
    'away_offsides': 1,

    # API 통계 데이터 (시간대별 점유율)
    'home_first_15_possession': 52.3,
    'home_first_30_possession': 54.1,
    'home_first_45_possession': 55.8,
    'home_second_15_possession': 48.2,
    'home_second_30_possession': 50.5,
    'home_second_45_possession': 53.7,
    'away_first_15_possession': 47.7,
    'away_first_30_possession': 45.9,
    'away_first_45_possession': 44.2,
    'away_second_15_possession': 51.8,
    'away_second_30_possession': 49.5,
    'away_second_45_possession': 46.3
}
```

## J리그 데이터 스키마

J리그 스크래퍼가 수집하는 데이터 필드입니다. K리그와 유사하나 트래킹 데이터가 추가됩니다.

### 필드 상세

| 필드명 | 타입 | 설명 | 예시 |
|-------|------|------|------|
| `Meet_Year` | int | 시즌 연도 | `2025` |
| `LEAGUE_NAME` | str | 리그명 | `"J리그1"` |
| `Round` | int \| None | 라운드 번호 | `1`, `25`, `None` |
| `Game_Datetime` | str \| None | 경기 일시 (ISO 8601) | `"2025-02-14 19:00:00"` |
| `Day` | str \| None | 요일 (한글) | `"금"`, `"토"` |
| `HomeTeam` | str \| None | 홈팀명 (일본어) | `"浦和レッズ"` |
| `AwayTeam` | str \| None | 어웨이팀명 (일본어) | `"鹿島アントラーズ"` |
| `Audience_Qty` | int | 관중 수 | `45123` |
| `Weather` | str | 날씨 (한글 번역) | `"맑음"`, `"흐림 후 비"` |
| `Temperature` | str | 온도 (°C) | `"12"` |
| `Humidity` | str | 습도 (%) | `"45"` |
| `HomeDistance` | str \| None | 홈팀 총 주행거리 (km) | `"115.2"` |
| `AwayDistance` | str \| None | 어웨이팀 총 주행거리 (km) | `"112.8"` |
| `HomeSprint` | str \| None | 홈팀 스프린트 횟수 | `"45"` |
| `AwaySprint` | str \| None | 어웨이팀 스프린트 횟수 | `"38"` |

### 예시 데이터

```python
{
    'Meet_Year': 2025,
    'LEAGUE_NAME': 'J리그1',
    'Round': 1,
    'Game_Datetime': '2025-02-14 19:00:00',
    'Day': '금',
    'HomeTeam': '浦和レッズ',
    'AwayTeam': '鹿島アントラーズ',
    'Audience_Qty': 45123,
    'Weather': '맑음',
    'Temperature': '12',
    'Humidity': '45',
    'HomeDistance': '115.2',
    'AwayDistance': '112.8',
    'HomeSprint': '45',
    'AwaySprint': '38'
}
```

## 데이터 타입 차이점

### K리그 vs J리그

| 필드 | K리그 | J리그 | 비고 |
|-----|-------|-------|------|
| `Audience_Qty` | str | int | K리그는 문자열, J리그는 정수 |
| `Round` | str | int \| None | K리그는 "1R" 형식, J리그는 숫자 |
| `HomeRank`, `AwayRank` | 있음 | 없음 | K리그만 제공 |
| `HomePoints`, `AwayPoints` | 있음 | 없음 | K리그만 제공 |
| `Field_Name` | 있음 | 없음 | K리그만 제공 |
| `Game_id` | 있음 | 없음 | K리그만 제공 |
| API 통계 데이터 | 있음 | 없음 | K리그만 제공 (점유율, 슈팅, 파울 등) |
| 트래킹 데이터 | 없음 | 있음 | J리그만 제공 (주행거리, 스프린트) |

## 날씨 번역 매핑

J리그 스크래퍼는 일본어 날씨 표현을 한글로 번역합니다.

### 기본 날씨

| 일본어 | 한글 |
|-------|------|
| 晴 | 맑음 |
| 曇 | 흐림 |
| 雨 | 비 |
| 雪 | 눈 |
| 霧 | 안개 |
| 屋内 | 실내 |

### 복합 날씨 패턴

| 일본어 | 한글 |
|-------|------|
| 晴一時雨 | 맑다가 일시 비 |
| 晴のち曇 | 맑음 후 흐림 |
| 曇時々雨 | 흐림 때때로 비 |
| 雨のち曇 | 비 후 흐림 |

> 번역 테이블에 없는 날씨 표현은 원본 일본어를 그대로 유지합니다.

## 요일 번역 매핑

J리그 스크래퍼는 일본어 요일을 한글로 번역합니다.

| 일본어 | 한글 |
|-------|------|
| 月 | 월 |
| 火 | 화 |
| 水 | 수 |
| 木 | 목 |
| 金 | 금 |
| 土 | 토 |
| 日 | 일 |

## 누락 데이터 처리

### None 값 발생 조건

| 필드 | None 조건 |
|-----|----------|
| `Round` | 정규 리그가 아닌 경기 (플레이오프, 컵 대회 등) |
| `Game_Datetime` | 날짜 파싱 실패 |
| `HomeTeam`, `AwayTeam` | 팀명 추출 실패 |
| `HomeDistance`, `AwayDistance` | 트래킹 데이터 미제공 (2019년 이전 또는 일부 경기장) |
| `HomeSprint`, `AwaySprint` | 트래킹 데이터 미제공 |

### pandas에서 결측치 처리

```python
import pandas as pd

df = pd.DataFrame(data)

# 결측치 확인
print(df.isnull().sum())

# 결측치가 있는 행 제거
df_clean = df.dropna()

# 특정 컬럼 결측치를 0으로 대체
df['Audience_Qty'] = df['Audience_Qty'].fillna(0)
```

## 관련 문서

- [아키텍처](./architecture.md)
- [K리그 API 레퍼런스](../reference/kleague-api.md)
- [J리그 API 레퍼런스](../reference/jleague-api.md)
