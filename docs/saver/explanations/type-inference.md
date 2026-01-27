# 타입 자동 추론

이 문서에서는 DB Saver의 타입 자동 추론 메커니즘을 설명합니다.

## 개념 소개

`save_to_db` 함수는 `dtype_map`을 지정하지 않으면 pandas DataFrame의 컬럼 타입을 분석하여 적절한 SQLAlchemy 타입을 자동으로 결정합니다. 이를 통해 별도 설정 없이도 올바른 데이터베이스 스키마가 생성됩니다.

## 타입 추론 흐름

```
┌─────────────────────┐
│  DataFrame 컬럼     │
│  (pandas dtype)     │
└──────────┬──────────┘
           │
           ↓
    ┌──────────────┐
    │ object 타입? │
    └──────┬───────┘
           │
     ┌─────┴─────┐
     │           │
    Yes          No
     │           │
     ↓           ↓
┌─────────────┐  ┌─────────────┐
│ 날짜 패턴   │  │ dtype 매핑  │
│ 검사        │  │ 테이블 참조 │
└──────┬──────┘  └──────┬──────┘
       │                │
       ↓                ↓
┌─────────────┐  ┌─────────────┐
│ Date 또는   │  │ Integer,    │
│ DateTime    │  │ Float, etc. │
└─────────────┘  └─────────────┘
```

## pandas dtype → SQLAlchemy 타입 매핑

기본 매핑 테이블입니다.

| pandas dtype | SQLAlchemy 타입 | SQLite 타입 |
|--------------|----------------|-------------|
| `int64`, `int32`, `int` | `Integer` | INTEGER |
| `float64`, `float` | `Float` | REAL |
| `bool` | `Boolean` | INTEGER (0/1) |
| `datetime64` | `DateTime` | DATETIME |
| `object` | `String` 또는 날짜 타입 | TEXT 또는 DATE/DATETIME |

### 코드 구현

```python
DTYPE_MAPPING = {
    'int64': Integer,
    'int32': Integer,
    'int': Integer,
    'float': Float,
    'bool': Boolean,
    'datetime': DateTime,
    'object': String,
}

def _infer_sqlalchemy_type(dtype) -> type:
    dtype_str = str(dtype).lower()
    for key, sql_type in DTYPE_MAPPING.items():
        if key in dtype_str:
            return sql_type
    return Text  # 기본값
```

## 날짜 문자열 패턴 감지

`object` 타입 컬럼 중 날짜 형식의 문자열을 자동으로 감지합니다.

### 지원 패턴

| 패턴 | 정규식 | 예시 | 변환 타입 |
|-----|-------|------|----------|
| DATE | `^\d{4}-\d{2}-\d{2}$` | `2025-02-15` | `Date` |
| DATETIME | `^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$` | `2025-02-15 14:00:00` | `DateTimeNoMicro` |

### 감지 로직

```python
DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'
DATETIME_PATTERN = r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$'

def _detect_date_type(series: pd.Series) -> type | None:
    if series.dtype != 'object':
        return None

    # 상위 5개 샘플로 패턴 검사
    sample = series.dropna().head(5)
    if sample.empty:
        return None

    str_sample = sample.astype(str)

    # DATETIME 패턴 우선 검사
    if str_sample.str.match(DATETIME_PATTERN).all():
        return DateTimeNoMicro

    # DATE 패턴 검사
    if str_sample.str.match(DATE_PATTERN).all():
        return Date

    return None
```

## DateTimeNoMicro 커스텀 타입

SQLite의 DATETIME은 마이크로초를 지원하지만, 경기 데이터에는 불필요합니다. `DateTimeNoMicro` 커스텀 타입은 마이크로초 없이 `YYYY-MM-DD HH:MM:SS` 형식으로 저장합니다.

```python
class DateTimeNoMicro(UserDefinedType):
    """마이크로초 없이 저장하는 DATETIME 타입"""
    cache_ok = True

    def get_col_spec(self):
        return "DATETIME"

    def bind_processor(self, _dialect):
        def process(value):
            if value is not None and hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d %H:%M:%S')
            return value
        return process
```

## 타입 추론 예시

### 입력 데이터

```python
data = [
    {
        'Meet_Year': 2025,           # int → Integer
        'HomeTeam': '울산',           # str → String
        'Audience_Qty': 15234.0,     # float → Float
        'Game_Datetime': '2025-02-15 14:00:00',  # 패턴 감지 → DateTime
        'Game_Date': '2025-02-15'    # 패턴 감지 → Date
    }
]
```

### 추론된 타입 맵

```python
dtype_map = {
    'Meet_Year': Integer,
    'HomeTeam': String,
    'Audience_Qty': Float,
    'Game_Datetime': DateTimeNoMicro,
    'Game_Date': Date
}
```

### 생성된 테이블 스키마

```sql
CREATE TABLE matches (
    Meet_Year INTEGER,
    HomeTeam TEXT,
    Audience_Qty REAL,
    Game_Datetime DATETIME,
    Game_Date DATE
);
```

## 자동 추론의 한계

### 감지되지 않는 경우

1. **다른 날짜 형식**: `2025/02/15`, `15-02-2025` 등은 감지되지 않음
2. **혼합 데이터**: 일부 행만 날짜 형식인 경우
3. **숫자 문자열**: `"15234"` 같은 숫자 문자열은 String으로 처리

### 해결 방법

직접 `dtype_map`을 지정하거나, 저장 전 데이터를 변환합니다.

```python
import pandas as pd
from sqlalchemy.types import Integer, Date

# 방법 1: dtype_map 직접 지정
dtype_map = {'Audience_Qty': Integer}
save_to_db(data, "matches", dtype_map=dtype_map)

# 방법 2: 데이터 변환 후 저장
df = pd.DataFrame(data)
df['Audience_Qty'] = df['Audience_Qty'].astype(int)
save_to_db(df, "matches")
```

## 관련 문서

- [커스텀 타입 지정하기](../how-tos/custom-dtype.md)
- [DB Saver API 레퍼런스](../reference/db-saver-api.md)
