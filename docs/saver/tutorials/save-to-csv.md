# CSV 파일로 저장하기

이 튜토리얼에서는 수집된 경기 데이터를 CSV 파일로 저장하는 방법을 단계별로 배웁니다.

## 목표

이 튜토리얼을 완료하면 다음을 할 수 있습니다.

- 딕셔너리 리스트를 CSV 파일로 저장
- 저장 경로와 파일명 지정
- 엑셀에서 한글이 깨지지 않도록 인코딩 설정

## 사전 요구사항

- Python 3.8 이상
- pandas 패키지 설치 (`pip install pandas`)

## 단계별 가이드

### 1단계: 모듈 임포트

```python
from src.saver import save_to_csv
```

### 2단계: 저장할 데이터 준비

스크래퍼로 수집한 데이터 또는 직접 생성한 딕셔너리 리스트를 준비합니다.

```python
# 예시 데이터
data = [
    {
        'Meet_Year': 2025,
        'LEAGUE_NAME': 'K리그1',
        'HomeTeam': '울산',
        'AwayTeam': '포항',
        'Audience_Qty': '15234'
    },
    {
        'Meet_Year': 2025,
        'LEAGUE_NAME': 'K리그1',
        'HomeTeam': '전북',
        'AwayTeam': '수원',
        'Audience_Qty': '12500'
    }
]
```

### 3단계: CSV 파일로 저장

```python
# CSV로 저장
csv_path = save_to_csv(data, "kleague1_match_2025")
```

**실행 결과:**
```
📂 저장 경로: C:\GitHub\k-league\data\kleague1_match_2025.csv
```

### 4단계: 저장된 파일 확인

```python
import pandas as pd

# 저장된 파일 읽기
df = pd.read_csv(csv_path, encoding='utf-8-sig')
print(df.head())
```

**출력 결과:**
```
   Meet_Year LEAGUE_NAME HomeTeam AwayTeam Audience_Qty
0       2025       K리그1       울산       포항        15234
1       2025       K리그1       전북       수원        12500
```

## 스크래퍼와 함께 사용하기

실제 사용 시에는 스크래퍼와 함께 사용합니다.

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data
from src.saver import save_to_csv

# 데이터 수집
data, filename = collect_kleague_match_data(year=2025, league="K리그1")

# CSV로 저장
csv_path = save_to_csv(data, filename)

print(f"수집: {len(data)}경기")
print(f"저장: {csv_path}")
```

## 최종 결과 확인

저장된 CSV 파일은 다음 위치에 생성됩니다.

```
project/
└── data/
    └── kleague1_match_2025.csv
```

파일을 엑셀에서 열면 한글이 정상적으로 표시됩니다 (UTF-8 with BOM 인코딩).

## 다음 단계

- [데이터베이스 저장 튜토리얼](./save-to-database.md): SQLite DB로 저장하는 방법을 배웁니다.
- [CSV Saver API 레퍼런스](../reference/csv-saver-api.md): 함수 상세 사양을 확인합니다.

## FAQ

### Q: 파일이 저장되는 위치를 변경하고 싶습니다.

A: 현재 버전에서는 `data/` 디렉토리가 기본값입니다. 다른 위치에 저장하려면 반환된 DataFrame을 직접 저장하세요.

```python
import pandas as pd

df = pd.DataFrame(data)
df.to_csv("원하는/경로/파일명.csv", index=False, encoding='utf-8-sig')
```

### Q: 빈 데이터를 저장하면 어떻게 되나요?

A: 빈 리스트를 전달하면 경고 메시지가 출력되고 `None`이 반환됩니다.

```python
result = save_to_csv([], "empty_file")
# ⚠️  저장할 데이터가 없습니다.
# result = None
```
