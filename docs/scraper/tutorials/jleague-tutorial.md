# J리그 경기 데이터 수집하기

이 튜토리얼에서는 J리그 공식 웹사이트에서 경기 데이터를 수집하는 방법을 단계별로 배웁니다.

## 목표

이 튜토리얼을 완료하면 다음을 할 수 있습니다.

- J리그 단일 시즌 데이터 수집
- 병렬 처리로 빠른 데이터 수집
- 트래킹 데이터(주행거리, 스프린트) 포함 수집

## 사전 요구사항

- Python 3.8 이상
- Chrome 브라우저 및 ChromeDriver 설치
- 필수 패키지 설치 완료 (`selenium`, `rich`, `beautifulsoup4`)

## 단계별 가이드

### 1단계: 모듈 임포트

먼저 J리그 스크래퍼 모듈을 임포트합니다.

```python
from src.scraper.jleague_match_scraper import collect_jleague_match_data
```

### 2단계: 단일 시즌 수집

가장 기본적인 사용법입니다. 2025년 J리그1 전체 시즌을 수집합니다.

```python
# 2025년 J리그1 수집 (병렬 모드 기본 활성화)
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1"
)

print(f"수집된 경기 수: {len(data)}")
print(f"파일명: {filename}")
```

**실행 결과:**
```
[2025년 J리그1 경기 데이터] (총 306경기)
수집 현황: 100%|████████████████| 306/306
수집된 경기 수: 306
파일명: j1_match_2025
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

### 4단계: pandas DataFrame으로 변환

데이터 분석을 위해 pandas DataFrame으로 변환할 수 있습니다.

```python
import pandas as pd

df = pd.DataFrame(data)
print(df.head())
print(f"\n데이터 shape: {df.shape}")
```

### 5단계: CSV 파일로 저장

수집된 데이터를 CSV 파일로 저장합니다.

```python
# CSV 파일로 저장
df.to_csv(f"data/{filename}.csv", index=False, encoding='utf-8-sig')
print(f"저장 완료: data/{filename}.csv")
```

## 최종 결과 확인

전체 코드를 실행하면 다음과 같은 결과를 얻습니다.

```python
from src.scraper.jleague_match_scraper import collect_jleague_match_data
import pandas as pd

# 데이터 수집
data, filename = collect_jleague_match_data(year=2025, league="J리그1")

# DataFrame 변환 및 저장
df = pd.DataFrame(data)
df.to_csv(f"data/{filename}.csv", index=False, encoding='utf-8-sig')

print(f"수집 완료: {len(data)}경기")
print(f"저장 위치: data/{filename}.csv")
```

## 다음 단계

- [여러 시즌 수집하기](../how-tos/collect-multi-season.md): 연도 범위를 지정하여 여러 시즌 데이터를 수집합니다.
- [병렬 처리 설정하기](../how-tos/parallel-collection.md): 병렬 처리 옵션을 조정하여 수집 속도를 최적화합니다.
- [J리그 API 레퍼런스](../reference/jleague-api.md): 상세한 함수 사용법을 확인합니다.

## FAQ

### Q: 트래킹 데이터가 None으로 나옵니다.

A: 트래킹 데이터는 2019년 이후 경기부터 제공됩니다. 또한 일부 경기장이나 취소된 경기에서는 트래킹 데이터가 없을 수 있습니다.

### Q: 수집 중 TimeoutException이 발생합니다.

A: 네트워크 환경에 따라 페이지 로딩이 느릴 수 있습니다. [트러블슈팅 가이드](../troubleshooting.md#timeoutexception)를 참고하세요.
