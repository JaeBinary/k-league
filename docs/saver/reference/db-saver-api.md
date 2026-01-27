# DB Saver API 레퍼런스

데이터베이스 저장 모듈의 API 상세 문서입니다.

## 개요

`db_saver` 모듈은 다양한 형식의 데이터를 SQLite 데이터베이스로 저장하는 기능을 제공합니다. 자동 타입 추론, 날짜 패턴 감지, 다양한 저장 모드를 지원합니다.

## 주요 함수

### save_to_db

데이터를 SQLite 데이터베이스로 저장합니다.

#### 시그니처

```python
def save_to_db(
    data: pd.DataFrame | list[dict] | str,
    table_name: str,
    db_path: str = None,
    if_exists: str = 'replace',
    dtype_map: dict = None
) -> str | None
```

#### 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `data` | `DataFrame \| list[dict] \| str` | (필수) | 저장할 데이터 |
| `table_name` | `str` | (필수) | 테이블 이름 |
| `db_path` | `str` | `None` | DB 파일 경로 (기본: `data/match.db`) |
| `if_exists` | `str` | `'replace'` | 테이블 존재 시 동작 |
| `dtype_map` | `dict` | `None` | 컬럼별 타입 지정 (None이면 자동 추론) |

#### data 파라미터 상세

| 입력 타입 | 설명 | 예시 |
|----------|------|------|
| `pd.DataFrame` | pandas DataFrame 직접 전달 | `df` |
| `list[dict]` | 딕셔너리 리스트 | `[{'a': 1}, {'a': 2}]` |
| `str` | CSV 파일 경로 | `"data/matches.csv"` |

#### if_exists 옵션

| 값 | 동작 |
|---|------|
| `'replace'` | 기존 테이블 삭제 후 새로 생성 (기본값) |
| `'append'` | 기존 테이블에 행 추가 |
| `'fail'` | 테이블이 존재하면 예외 발생 |

#### 반환값

| 타입 | 설명 |
|-----|------|
| `str` | 저장된 DB 파일 경로 |
| `None` | 저장 실패 (빈 데이터 또는 변환 실패) |

#### 사용 예제

```python
from src.saver import save_to_db

# 딕셔너리 리스트 저장
data = [
    {'Meet_Year': 2025, 'HomeTeam': '울산', 'Game_Datetime': '2025-02-15 14:00:00'},
    {'Meet_Year': 2025, 'HomeTeam': '전북', 'Game_Datetime': '2025-02-15 16:00:00'}
]
db_path = save_to_db(data, table_name="matches")
```

```python
# CSV 파일을 DB로 변환
db_path = save_to_db(
    data="data/kleague1_match_2025.csv",
    table_name="kleague1_2025"
)
```

```python
# 기존 테이블에 데이터 추가
save_to_db(new_data, table_name="matches", if_exists='append')
```

```python
# 커스텀 타입 지정
from sqlalchemy.types import Integer, String

dtype_map = {
    'Meet_Year': Integer,
    'HomeTeam': String(50)
}
save_to_db(data, table_name="matches", dtype_map=dtype_map)
```

```python
# 다른 DB 파일에 저장
save_to_db(data, table_name="matches", db_path="my_data/custom.db")
```

#### 출력 메시지

| 상황 | 메시지 |
|-----|-------|
| 성공 | `✅ '{db_path}' → '{table_name}' 테이블 ({건수}건)` |
| 빈 데이터 | `⚠️  저장할 데이터가 없습니다.` |
| CSV 읽기 | `📂 CSV 파일을 읽는 중: {경로}` |
| 지원하지 않는 타입 | `⚠️  지원하지 않는 데이터 타입: {타입}` |

---

## 내부 함수

### _to_dataframe

다양한 입력 타입을 DataFrame으로 변환합니다.

```python
def _to_dataframe(data: pd.DataFrame | list[dict] | str) -> pd.DataFrame | None
```

| 입력 | 동작 |
|-----|------|
| `DataFrame` | 그대로 반환 |
| `list[dict]` | DataFrame으로 변환 |
| `str` | CSV 파일로 읽어서 DataFrame 반환 |
| 기타 | `None` 반환 |

---

### _build_dtype_map

DataFrame 컬럼들의 SQLAlchemy 타입 맵을 생성합니다.

```python
def _build_dtype_map(df: pd.DataFrame) -> dict
```

각 컬럼에 대해:
1. 날짜 패턴 감지 (`_detect_date_type`)
2. 날짜가 아니면 dtype 기반 추론 (`_infer_sqlalchemy_type`)

---

### _detect_date_type

문자열 컬럼이 DATE 또는 DATETIME 패턴인지 확인합니다.

```python
def _detect_date_type(series: pd.Series) -> type | None
```

| 패턴 | 반환 타입 |
|-----|----------|
| `YYYY-MM-DD HH:MM:SS` | `DateTimeNoMicro` |
| `YYYY-MM-DD` | `Date` |
| 해당 없음 | `None` |

---

### _infer_sqlalchemy_type

pandas dtype을 SQLAlchemy 타입으로 변환합니다.

```python
def _infer_sqlalchemy_type(dtype) -> type
```

---

### _convert_datetime_columns

Date/DateTime 컬럼을 datetime 객체로 변환합니다.

```python
def _convert_datetime_columns(df: pd.DataFrame, dtype_map: dict) -> pd.DataFrame
```

---

## 클래스

### DateTimeNoMicro

마이크로초 없이 저장하는 DATETIME 커스텀 타입입니다.

```python
class DateTimeNoMicro(UserDefinedType):
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

---

## 상수

### DTYPE_MAPPING

pandas dtype → SQLAlchemy 타입 매핑 테이블

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
```

### DATE_PATTERN, DATETIME_PATTERN

날짜 문자열 감지용 정규식

```python
DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'
DATETIME_PATTERN = r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$'
```

### DATA_DIR

기본 데이터 저장 디렉토리

```python
DATA_DIR = os.path.join(CURRENT_DIR, "..", "..", "data")
```

---

## 관련 문서

- [데이터베이스 저장 튜토리얼](../tutorials/save-to-database.md)
- [데이터 추가하기](../how-tos/append-data.md)
- [커스텀 타입 지정하기](../how-tos/custom-dtype.md)
- [타입 자동 추론](../explanations/type-inference.md)
