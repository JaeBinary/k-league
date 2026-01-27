# 여러 시즌 데이터 수집하기

여러 연도의 경기 데이터를 한 번에 수집하는 방법을 설명합니다.

## 문제 정의

분석이나 모델링을 위해 과거 여러 시즌의 데이터가 필요한 경우가 있습니다. 이 가이드에서는 연도 범위를 지정하여 여러 시즌 데이터를 효율적으로 수집하는 방법을 설명합니다.

## 해결 방법

### 연도 리스트로 범위 지정

`year` 파라미터에 리스트를 전달하면 시작 연도부터 끝 연도까지 모든 시즌 데이터를 수집합니다.

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data

# 2023년부터 2025년까지 K리그1 수집
# [2023, 2025] → 2023, 2024, 2025 모두 수집
data, filename = collect_kleague_match_data(
    year=[2023, 2025],
    league="K리그1"
)

print(f"총 수집 경기: {len(data)}")
print(f"파일명: {filename}")
```

**출력 결과:**
```
[2023년 K리그1 경기 데이터] (총 228경기)
수집 현황: 100%|████████████████| 228/228

[2024년 K리그1 경기 데이터] (총 228경기)
수집 현황: 100%|████████████████| 228/228

[2025년 K리그1 경기 데이터] (총 228경기)
수집 현황: 100%|████████████████| 228/228

✅ 수집 완료: 684경기, 파일명: kleague1_match_2023-2025
```

### 여러 리그 동시 수집

`league` 파라미터에 리스트를 전달하면 여러 리그를 동시에 수집합니다.

```python
# K리그1과 K리그2 동시 수집
data, filename = collect_kleague_match_data(
    year=2025,
    league=["K리그1", "K리그2"]
)

print(f"총 수집 경기: {len(data)}")
print(f"파일명: {filename}")
```

**출력 결과:**
```
[2025년 K리그1 경기 데이터] (총 228경기)
수집 현황: 100%|████████████████| 228/228

[2025년 K리그2 경기 데이터] (총 275경기)
수집 현황: 100%|████████████████| 275/275

✅ 수집 완료: 503경기, 파일명: kleague_match_2025
```

### 여러 연도 + 여러 리그 조합

연도와 리그를 조합하여 대규모 데이터셋을 생성할 수 있습니다.

```python
# 2023-2025년 K리그1 + K리그2 전체 수집
data, filename = collect_kleague_match_data(
    year=[2023, 2025],
    league=["K리그1", "K리그2"]
)

print(f"총 수집 경기: {len(data)}")
# 예상: K1 228*3 + K2 (236+236+275) = 684 + 747 = 1431경기
```

### J리그 여러 시즌 수집

J리그도 동일한 방식으로 여러 시즌을 수집합니다.

```python
from src.scraper.jleague_match_scraper import collect_jleague_match_data

# 2023-2025년 J리그1 수집
data, filename = collect_jleague_match_data(
    year=[2023, 2025],
    league="J리그1",
    parallel=True,  # 병렬 처리 활성화
    max_workers=4
)

print(f"총 수집 경기: {len(data)}")
```

## 주의사항

### 메모리 사용량

여러 시즌을 수집하면 메모리 사용량이 증가합니다. 대규모 수집 시 다음을 권장합니다.

```python
import pandas as pd

# 수집 후 즉시 파일로 저장
data, filename = collect_kleague_match_data(year=[2020, 2025], league="K리그1")
df = pd.DataFrame(data)
df.to_csv(f"data/{filename}.csv", index=False, encoding='utf-8-sig')

# 메모리 해제
del data
del df
```

### 수집 시간

- K리그: 경기당 약 0.5초 (HTTP 요청)
- J리그 (순차): 경기당 약 2초 (Selenium)
- J리그 (병렬, 4워커): 경기당 약 0.5초

| 데이터셋 | 예상 경기 수 | K리그 예상 시간 | J리그 예상 시간 (병렬) |
|---------|-------------|----------------|---------------------|
| 1시즌 K리그1 | 228 | 약 2분 | - |
| 1시즌 J리그1 | 306 | - | 약 3분 |
| 3시즌 K리그1 | 684 | 약 6분 | - |
| 3시즌 J리그1 | 918 | - | 약 8분 |

## 문제 해결 후 확인 방법

수집 완료 후 데이터의 연도와 리그 분포를 확인합니다.

```python
import pandas as pd

df = pd.DataFrame(data)

# 연도별 경기 수 확인
print(df.groupby('Meet_Year').size())

# 리그별 경기 수 확인
print(df.groupby('LEAGUE_NAME').size())

# 연도-리그 조합별 경기 수 확인
print(df.groupby(['Meet_Year', 'LEAGUE_NAME']).size())
```

## 관련 문서

- [병렬 처리 설정하기](./parallel-collection.md)
- [트러블슈팅](../troubleshooting.md)
