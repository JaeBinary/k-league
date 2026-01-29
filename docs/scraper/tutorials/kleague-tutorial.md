# K리그 경기 데이터 수집하기

이 튜토리얼에서는 K리그 공식 웹사이트에서 경기 데이터를 수집하는 방법을 단계별로 배웁니다.

## 목표

이 튜토리얼을 완료하면 다음을 할 수 있습니다.

- K리그 단일 시즌 데이터 수집
- K리그1, K리그2, 승강 플레이오프 데이터 수집
- 수집된 데이터를 분석용 파일로 저장

## 사전 요구사항

- Python 3.8 이상
- 필수 패키지 설치 완료 (`beautifulsoup4`, `rich`, `requests`)

> K리그 스크래퍼는 정적 HTML 파싱을 사용하므로 Selenium이나 ChromeDriver가 필요하지 않습니다.

## 단계별 가이드

### 1단계: 모듈 임포트

K리그 스크래퍼 모듈을 임포트합니다.

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data
```

### 2단계: 단일 시즌 수집

2025년 K리그1 전체 시즌을 수집합니다.

```python
# 2025년 K리그1 수집
data, filename = collect_kleague_match_data(
    year=2025,
    league="K리그1"
)

print(f"수집된 경기 수: {len(data)}")
print(f"파일명: {filename}")
```

**실행 결과:**
```
[2025년 K리그1 경기 데이터] (총 228경기)
수집 현황: 100%|████████████████| 228/228
✅ 수집 완료: 228경기, 파일명: kleague1_match_2025
```

### 3단계: 수집된 데이터 확인

수집된 데이터는 딕셔너리 리스트 형태입니다.

```python
# 첫 번째 경기 데이터 확인
first_match = data[0]
print(first_match)
```

**출력 예시:**
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

    # API 통계 데이터 (일부)
    'home_possession': 55,
    'away_possession': 45,
    'home_attempts': 15,
    'away_attempts': 8,
    'home_on_target': 6,
    'away_on_target': 3,
    'home_fouls': 12,
    'away_fouls': 14,
    # ... 시간대별 점유율 등 추가 필드
}
```

> **참고**: K리그 공식 API를 통해 점유율, 슈팅, 파울, 카드 등 약 30개의 추가 통계 필드가 자동으로 수집됩니다. 자세한 내용은 [데이터 스키마](../explanations/data-schema.md)를 참고하세요.

### 4단계: 다른 리그 수집

K리그2나 승강 플레이오프도 동일한 방법으로 수집합니다.

```python
# K리그2 수집
k2_data, k2_filename = collect_kleague_match_data(
    year=2025,
    league="K리그2"
)
print(f"K리그2: {len(k2_data)}경기")

# 승강 플레이오프 수집
po_data, po_filename = collect_kleague_match_data(
    year=2025,
    league="승강PO"
)
print(f"승강PO: {len(po_data)}경기")
```

### 5단계: pandas DataFrame으로 변환

데이터 분석을 위해 pandas DataFrame으로 변환합니다.

```python
import pandas as pd

df = pd.DataFrame(data)
print(df.head())
print(f"\n컬럼 목록: {df.columns.tolist()}")
```

### 6단계: CSV 파일로 저장

```python
# CSV 파일로 저장
df.to_csv(f"data/{filename}.csv", index=False, encoding='utf-8-sig')
print(f"저장 완료: data/{filename}.csv")
```

## 최종 결과 확인

전체 코드를 실행하면 다음과 같은 결과를 얻습니다.

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data
import pandas as pd

# 데이터 수집
data, filename = collect_kleague_match_data(year=2025, league="K리그1")

# DataFrame 변환 및 저장
df = pd.DataFrame(data)
df.to_csv(f"data/{filename}.csv", index=False, encoding='utf-8-sig')

print(f"수집 완료: {len(data)}경기")
print(f"저장 위치: data/{filename}.csv")
```

## 다음 단계

- [여러 시즌 수집하기](../how-tos/collect-multi-season.md): 연도 범위를 지정하여 여러 시즌 데이터를 수집합니다.
- [K리그 API 레퍼런스](../reference/kleague-api.md): 상세한 함수 사용법을 확인합니다.
- [데이터 스키마](../explanations/data-schema.md): 수집되는 데이터 필드의 의미를 이해합니다.

## FAQ

### Q: 일부 경기 데이터가 누락됩니다.

A: 경기가 아직 진행되지 않았거나 취소된 경우 해당 경기 데이터는 수집되지 않습니다. 시즌 종료 후 전체 데이터를 수집하는 것을 권장합니다.

### Q: 지원하지 않는 리그 오류가 발생합니다.

A: 지원되는 리그는 `K리그1`, `K리그2`, `승강PO`, `슈퍼컵`입니다. 리그명을 정확히 입력했는지 확인하세요.

### Q: 특정 연도의 경기 수가 예상과 다릅니다.

A: K리그는 팀 수 변동에 따라 시즌별 경기 수가 달라질 수 있습니다. 2025년부터 K리그2는 275경기로 증가했습니다.
