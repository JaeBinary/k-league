# 병렬 처리로 빠르게 수집하기

J리그 스크래퍼의 병렬 처리 옵션을 조정하여 수집 속도를 최적화하는 방법을 설명합니다.

## 문제 정의

J리그 스크래퍼는 Selenium을 사용하여 동적 페이지를 크롤링합니다. 순차 처리 시 경기당 약 2초가 소요되어 시즌 전체 수집에 10분 이상 걸릴 수 있습니다. 병렬 처리를 활용하면 수집 시간을 크게 단축할 수 있습니다.

> K리그 스크래퍼는 정적 HTML 파싱을 사용하므로 이미 충분히 빠릅니다. 이 가이드는 J리그 스크래퍼에만 해당합니다.

## 해결 방법

### 병렬 처리 활성화

`parallel=True` 옵션으로 병렬 처리를 활성화합니다.

```python
from src.scraper.jleague_match_scraper import collect_jleague_match_data

# 병렬 처리 활성화 (기본값)
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=True,      # 병렬 처리 활성화
    max_workers=4       # 동시 실행 스레드 수
)
```

### 워커 수 조정

`max_workers` 파라미터로 동시 실행 스레드 수를 조정합니다.

```python
# 더 많은 워커로 속도 향상
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=True,
    max_workers=6  # 기본값: 4
)
```

### 순차 처리 사용

안정성이 중요하거나 디버깅이 필요한 경우 순차 처리를 사용합니다.

```python
# 순차 처리 (더 안정적)
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=False  # 순차 처리
)
```

## 워커 수 선택 가이드

| 환경 | 권장 워커 수 | 설명 |
|-----|-------------|------|
| 일반 데스크톱 (8GB RAM) | 2-4 | 메모리와 CPU 부하를 고려 |
| 고성능 데스크톱 (16GB+ RAM) | 4-6 | 더 많은 워커로 속도 향상 가능 |
| 서버/클라우드 | 6-8 | 충분한 리소스 시 최대 성능 |
| 안정성 우선 | 2 | 오류 발생률 최소화 |

### 성능 비교

J리그1 단일 시즌 (306경기) 수집 기준:

| 모드 | 워커 수 | 예상 시간 | 속도 비율 |
|-----|--------|----------|----------|
| 순차 | - | 약 10분 | 1x |
| 병렬 | 2 | 약 5분 | 2x |
| 병렬 | 4 | 약 3분 | 3.3x |
| 병렬 | 6 | 약 2분 | 5x |

## 주의사항

### 메모리 사용량

각 워커는 독립적인 Chrome 인스턴스를 실행합니다. 워커 수가 증가하면 메모리 사용량도 증가합니다.

```
워커 수 × Chrome 메모리(약 200-300MB) = 총 추가 메모리
예: 4 워커 × 250MB = 1GB 추가 메모리 사용
```

### 네트워크 부하

과도한 병렬 요청은 대상 서버에 부하를 줄 수 있습니다. 권장 워커 수(4-6개)를 초과하지 않는 것이 좋습니다.

### 실패 경기 재수집

병렬 처리 중 일부 경기 수집이 실패하면 자동으로 재수집을 시도합니다.

```
[2025년 J리그1 경기 데이터] (총 306경기)
수집 현황: 100%|████████████████| 306/306

실패한 5경기 재수집 시작...
재수집 현황: 100%|████████████████| 5/5
재수집 완료: 5/5건 성공
```

## 환경별 최적 설정

### Windows

```python
# Windows에서는 안정성을 위해 워커 수 제한 권장
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=True,
    max_workers=4
)
```

### macOS/Linux

```python
# macOS/Linux에서는 더 많은 워커 사용 가능
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=True,
    max_workers=6
)
```

### Docker/서버 환경

```python
# 충분한 리소스가 있는 서버에서
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=True,
    max_workers=8
)
```

## 문제 해결

### SessionNotCreatedException 발생 시

ChromeDriver 세션 생성 실패 시 자동으로 최대 3회 재시도합니다. 지속적으로 발생하면 워커 수를 줄이세요.

```python
# 워커 수 줄이기
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=True,
    max_workers=2  # 워커 수 감소
)
```

### 메모리 부족 오류 발생 시

순차 처리로 전환하거나 연도를 분할하여 수집합니다.

```python
# 옵션 1: 순차 처리
data, filename = collect_jleague_match_data(
    year=2025,
    league="J리그1",
    parallel=False
)

# 옵션 2: 연도 분할 수집
for year in [2023, 2024, 2025]:
    data, filename = collect_jleague_match_data(
        year=year,
        league="J리그1",
        parallel=True,
        max_workers=2
    )
    # 즉시 저장하여 메모리 해제
    pd.DataFrame(data).to_csv(f"data/{filename}.csv", index=False)
```

## 관련 문서

- [여러 시즌 수집하기](./collect-multi-season.md)
- [트러블슈팅](../troubleshooting.md)
- [J리그 API 레퍼런스](../reference/jleague-api.md)
