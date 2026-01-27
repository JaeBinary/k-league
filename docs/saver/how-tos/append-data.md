# 기존 데이터에 추가하기

기존 데이터베이스 테이블에 새로운 데이터를 추가하는 방법을 설명합니다.

## 문제 정의

새 시즌 데이터를 수집했을 때 기존 테이블을 유지하면서 데이터를 추가해야 하는 경우가 있습니다. 기본 동작(`if_exists='replace'`)은 테이블을 완전히 덮어쓰므로 기존 데이터가 삭제됩니다.

## 해결 방법

### if_exists='append' 옵션 사용

`if_exists` 파라미터를 `'append'`로 설정하면 기존 테이블에 데이터를 추가합니다.

```python
from src.saver import save_to_db

# 2024년 데이터 저장 (새 테이블 생성)
data_2024 = [...]  # 2024년 데이터
save_to_db(data_2024, table_name="kleague_matches", if_exists='replace')

# 2025년 데이터 추가 (기존 테이블에 추가)
data_2025 = [...]  # 2025년 데이터
save_to_db(data_2025, table_name="kleague_matches", if_exists='append')
```

**실행 결과:**
```
✅ 'data/match.db' → 'kleague_matches' 테이블 (228건)
✅ 'data/match.db' → 'kleague_matches' 테이블 (228건)
```

### 여러 시즌 데이터 누적 저장

반복문을 사용하여 여러 시즌 데이터를 누적 저장합니다.

```python
from src.scraper.kleague_match_scraper import collect_kleague_match_data
from src.saver import save_to_db

years = [2023, 2024, 2025]

for i, year in enumerate(years):
    data, _ = collect_kleague_match_data(year=year, league="K리그1")

    # 첫 번째 연도는 replace, 이후는 append
    mode = 'replace' if i == 0 else 'append'
    save_to_db(data, table_name="kleague_all", if_exists=mode)

print("전체 시즌 데이터 저장 완료")
```

### if_exists 옵션 비교

| 옵션 | 동작 | 사용 상황 |
|-----|------|---------|
| `'replace'` | 기존 테이블 삭제 후 새로 생성 | 데이터 전체 갱신 |
| `'append'` | 기존 테이블에 행 추가 | 증분 데이터 추가 |
| `'fail'` | 테이블이 존재하면 오류 발생 | 중복 저장 방지 |

## 주의사항

### 스키마 일치 필요

`append` 모드에서는 새 데이터의 컬럼이 기존 테이블과 일치해야 합니다.

```python
# 기존 테이블 스키마: Meet_Year, LEAGUE_NAME, HomeTeam, AwayTeam

# OK: 동일한 컬럼 구조
new_data = [{'Meet_Year': 2025, 'LEAGUE_NAME': 'K리그1', 'HomeTeam': '울산', 'AwayTeam': '포항'}]
save_to_db(new_data, table_name="matches", if_exists='append')

# 주의: 컬럼이 다르면 오류 발생 가능
bad_data = [{'Year': 2025, 'League': 'K1'}]  # 컬럼명 불일치
```

### 중복 데이터 확인

`append` 모드는 중복 검사를 하지 않습니다. 필요시 직접 처리하세요.

```python
import pandas as pd
from sqlalchemy import create_engine

# 기존 데이터 확인
engine = create_engine("sqlite:///data/match.db")
existing_df = pd.read_sql("SELECT * FROM matches", engine)

# 새 데이터에서 중복 제거
new_df = pd.DataFrame(new_data)
combined = pd.concat([existing_df, new_df]).drop_duplicates()

# 전체 교체
save_to_db(combined, table_name="matches", if_exists='replace')
```

## 문제 해결 후 확인 방법

저장 후 데이터 건수를 확인합니다.

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("sqlite:///data/match.db")

# 총 건수 확인
count = pd.read_sql("SELECT COUNT(*) as cnt FROM kleague_all", engine)
print(f"총 데이터: {count['cnt'][0]}건")

# 연도별 분포 확인
dist = pd.read_sql("""
    SELECT Meet_Year, COUNT(*) as cnt
    FROM kleague_all
    GROUP BY Meet_Year
""", engine)
print(dist)
```

## 관련 문서

- [데이터베이스 저장 튜토리얼](../tutorials/save-to-database.md)
- [DB Saver API 레퍼런스](../reference/db-saver-api.md)
