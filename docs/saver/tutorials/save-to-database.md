# SQLite 데이터베이스로 저장하기

이 튜토리얼에서는 수집된 경기 데이터를 SQLite 데이터베이스로 저장하는 방법을 단계별로 배웁니다.

## 목표

이 튜토리얼을 완료하면 다음을 할 수 있습니다.

- 딕셔너리 리스트를 SQLite DB로 저장
- CSV 파일을 DB로 변환
- 자동 타입 추론 기능 활용
- SQL 쿼리로 데이터 조회

## 사전 요구사항

- Python 3.8 이상
- pandas, sqlalchemy 패키지 설치 (`pip install pandas sqlalchemy`)

## 단계별 가이드

### 1단계: 모듈 임포트

```python
from src.saver import save_to_db
```

### 2단계: 데이터를 DB로 저장

딕셔너리 리스트를 직접 저장합니다.

```python
# 예시 데이터
data = [
    {
        'Meet_Year': 2025,
        'LEAGUE_NAME': 'K리그1',
        'Game_Datetime': '2025-02-15 14:00:00',
        'HomeTeam': '울산',
        'AwayTeam': '포항'
    },
    {
        'Meet_Year': 2025,
        'LEAGUE_NAME': 'K리그1',
        'Game_Datetime': '2025-02-15 16:00:00',
        'HomeTeam': '전북',
        'AwayTeam': '수원'
    }
]

# DB로 저장
db_path = save_to_db(data, table_name="kleague1_2025")
```

**실행 결과:**
```
✅ 'data/match.db' → 'kleague1_2025' 테이블 (2건)
```

### 3단계: 저장된 데이터 확인

SQL 쿼리로 데이터를 조회합니다.

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(f"sqlite:///{db_path}")

# 전체 데이터 조회
df = pd.read_sql("SELECT * FROM kleague1_2025", engine)
print(df)
```

**출력 결과:**
```
   Meet_Year LEAGUE_NAME       Game_Datetime HomeTeam AwayTeam
0       2025       K리그1  2025-02-15 14:00:00       울산       포항
1       2025       K리그1  2025-02-15 16:00:00       전북       수원
```

### 4단계: CSV 파일을 DB로 변환

기존 CSV 파일을 DB로 변환할 수도 있습니다.

```python
# CSV 파일 경로를 직접 전달
db_path = save_to_db(
    data="data/kleague1_match_2025.csv",
    table_name="kleague1_2025"
)
```

### 5단계: SQL 쿼리 활용

저장된 데이터를 다양한 SQL 쿼리로 분석합니다.

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("sqlite:///data/match.db")

# 팀별 홈 경기 수
query1 = """
SELECT HomeTeam, COUNT(*) as home_games
FROM kleague1_2025
GROUP BY HomeTeam
ORDER BY home_games DESC
"""
print(pd.read_sql(query1, engine))

# 월별 경기 수
query2 = """
SELECT strftime('%Y-%m', Game_Datetime) as month, COUNT(*) as games
FROM kleague1_2025
GROUP BY month
"""
print(pd.read_sql(query2, engine))
```

## 스크래퍼와 함께 사용하기

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data
from src.saver import save_to_db

# 데이터 수집
data, filename = collect_kleague_match_data(year=2025, league="K리그1")

# DB로 저장
db_path = save_to_db(data, table_name="kleague1_2025")

print(f"수집: {len(data)}경기")
print(f"저장: {db_path}")
```

## 최종 결과 확인

저장된 DB 파일은 다음 위치에 생성됩니다.

```
project/
└── data/
    └── match.db
```

DB Browser for SQLite 같은 도구로 테이블 구조와 데이터를 확인할 수 있습니다.

## 다음 단계

- [데이터 추가하기](../how-tos/append-data.md): 기존 테이블에 새 데이터를 추가합니다.
- [커스텀 타입 지정하기](../how-tos/custom-dtype.md): 컬럼 타입을 직접 지정합니다.
- [타입 자동 추론](../explanations/type-inference.md): 타입 추론 원리를 이해합니다.

## FAQ

### Q: 테이블을 덮어쓰지 않고 추가하고 싶습니다.

A: `if_exists='append'` 옵션을 사용하세요.

```python
save_to_db(data, table_name="kleague1_2025", if_exists='append')
```

### Q: 다른 DB 파일에 저장하고 싶습니다.

A: `db_path` 파라미터로 경로를 지정하세요.

```python
save_to_db(data, table_name="matches", db_path="my_data/custom.db")
```

### Q: 날짜 컬럼이 문자열로 저장됩니다.

A: `save_to_db`는 `YYYY-MM-DD HH:MM:SS` 형식의 문자열을 자동으로 DATETIME 타입으로 인식합니다. 다른 형식인 경우 직접 변환이 필요합니다.
