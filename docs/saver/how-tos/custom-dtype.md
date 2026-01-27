# 커스텀 타입 지정하기

데이터베이스 저장 시 컬럼 타입을 직접 지정하는 방법을 설명합니다.

## 문제 정의

기본적으로 `save_to_db`는 pandas dtype을 기반으로 SQLite 타입을 자동 추론합니다. 하지만 다음 상황에서는 직접 타입을 지정해야 할 수 있습니다.

- 특정 컬럼을 TEXT 대신 INTEGER로 저장하고 싶을 때
- 날짜 형식이 자동 인식되지 않을 때
- 정밀도가 중요한 숫자 데이터일 때

## 해결 방법

### dtype_map 파라미터 사용

`dtype_map` 딕셔너리로 컬럼별 타입을 지정합니다.

```python
from src.saver import save_to_db
from sqlalchemy.types import Integer, String, Float, Text

data = [
    {'id': '1', 'name': '울산', 'score': '3.5'},
    {'id': '2', 'name': '포항', 'score': '2.8'}
]

# 커스텀 타입 지정
dtype_map = {
    'id': Integer,      # 문자열 → 정수
    'name': String(50), # 최대 50자 문자열
    'score': Float      # 문자열 → 실수
}

save_to_db(data, table_name="teams", dtype_map=dtype_map)
```

### 지원되는 SQLAlchemy 타입

| SQLAlchemy 타입 | SQLite 타입 | 설명 |
|----------------|------------|------|
| `Integer` | INTEGER | 정수 |
| `Float` | REAL | 실수 |
| `String(n)` | VARCHAR(n) | 가변 문자열 (최대 n자) |
| `Text` | TEXT | 긴 문자열 |
| `Boolean` | INTEGER | 불리언 (0/1) |
| `Date` | DATE | 날짜 |
| `DateTime` | DATETIME | 날짜시간 |

### 날짜 타입 직접 지정

자동 인식되지 않는 날짜 형식은 직접 지정합니다.

```python
from sqlalchemy.types import Date, DateTime

data = [
    {'match_date': '2025/02/15', 'kickoff': '2025-02-15T14:00'},
]

dtype_map = {
    'match_date': Date,
    'kickoff': DateTime
}

# 주의: 데이터를 먼저 datetime으로 변환해야 함
import pandas as pd
df = pd.DataFrame(data)
df['match_date'] = pd.to_datetime(df['match_date'])
df['kickoff'] = pd.to_datetime(df['kickoff'])

save_to_db(df, table_name="matches", dtype_map=dtype_map)
```

### 부분 타입 지정

일부 컬럼만 지정하면 나머지는 자동 추론됩니다.

```python
from sqlalchemy.types import Integer

data = [
    {'Meet_Year': 2025, 'Audience_Qty': '15234', 'HomeTeam': '울산'}
]

# Audience_Qty만 Integer로 지정, 나머지는 자동 추론
dtype_map = {
    'Audience_Qty': Integer
}

save_to_db(data, table_name="matches", dtype_map=dtype_map)
```

## 자동 추론 vs 직접 지정

| 상황 | 권장 방식 |
|-----|---------|
| 일반적인 데이터 저장 | 자동 추론 (`dtype_map=None`) |
| 숫자가 문자열로 저장되는 경우 | 직접 지정 |
| 특정 날짜 형식 사용 | 직접 지정 |
| 외부 시스템과 스키마 일치 필요 | 직접 지정 |

## 문제 해결 후 확인 방법

테이블 스키마를 확인합니다.

```python
import pandas as pd
from sqlalchemy import create_engine, inspect

engine = create_engine("sqlite:///data/match.db")
inspector = inspect(engine)

# 컬럼 정보 확인
columns = inspector.get_columns("teams")
for col in columns:
    print(f"{col['name']}: {col['type']}")
```

**출력 예시:**
```
id: INTEGER
name: VARCHAR(50)
score: FLOAT
```

## 관련 문서

- [타입 자동 추론](../explanations/type-inference.md)
- [DB Saver API 레퍼런스](../reference/db-saver-api.md)
