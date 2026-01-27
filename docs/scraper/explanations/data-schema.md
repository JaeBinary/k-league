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
| `Field_Name` | str | 경기장명 | `"울산문수월드컵경기장"` |
| `Audience_Qty` | str | 관중 수 | `"15234"` |
| `Weather` | str | 날씨 | `"맑음"`, `"흐림"` |
| `Temperature` | str | 온도 (°C) | `"18"` |
| `Humidity` | str | 습도 (%) | `"55"` |

### 예시 데이터

```python
{
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
    'Field_Name': '울산문수월드컵경기장',
    'Audience_Qty': '15234',
    'Weather': '맑음',
    'Temperature': '8',
    'Humidity': '45'
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
| `Field_Name` | 있음 | 없음 | K리그만 제공 |
| `Game_id` | 있음 | 없음 | K리그만 제공 |
| 트래킹 데이터 | 없음 | 있음 | J리그만 제공 |

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
