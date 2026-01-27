# 용어 사전

Saver 모듈 문서에서 사용되는 주요 용어를 정의합니다.

## 일반 용어

### 데이터셋 (Dataset)

저장 또는 분석 대상이 되는 데이터의 집합. 이 모듈에서는 딕셔너리 리스트(`list[dict]`) 형태로 표현됩니다.

### 영구 저장 (Persistent Storage)

프로그램 종료 후에도 데이터가 유지되는 저장 방식. CSV 파일과 SQLite 데이터베이스가 해당됩니다.

---

## 파일 형식

### CSV (Comma-Separated Values)

쉼표로 값을 구분하는 텍스트 기반 데이터 형식. 엑셀, 구글 시트 등에서 열 수 있습니다.

```csv
Meet_Year,HomeTeam,AwayTeam
2025,울산,포항
2025,전북,수원
```

### SQLite

서버 없이 파일 하나로 동작하는 경량 관계형 데이터베이스. `.db` 확장자 파일에 저장됩니다.

### UTF-8 with BOM (utf-8-sig)

UTF-8 인코딩에 BOM(Byte Order Mark)을 추가한 형식. Microsoft Excel에서 한글을 정상 표시하기 위해 사용합니다.

---

## pandas 용어

### DataFrame

pandas의 2차원 테이블 데이터 구조. 행과 열로 구성되며, 각 열은 다른 데이터 타입을 가질 수 있습니다.

```python
import pandas as pd
df = pd.DataFrame([{'a': 1, 'b': 2}, {'a': 3, 'b': 4}])
```

### dtype

pandas 컬럼의 데이터 타입. `int64`, `float64`, `object`, `datetime64` 등이 있습니다.

```python
df['column'].dtype  # dtype('int64')
```

### Series

pandas의 1차원 데이터 구조. DataFrame의 각 컬럼은 Series입니다.

---

## SQLAlchemy 용어

### SQLAlchemy

Python의 SQL 툴킷 및 ORM(Object-Relational Mapping) 라이브러리. 데이터베이스와의 상호작용을 추상화합니다.

### Engine

SQLAlchemy에서 데이터베이스 연결을 관리하는 객체.

```python
from sqlalchemy import create_engine
engine = create_engine("sqlite:///data/match.db")
```

### 타입 매핑 (Type Mapping)

Python/pandas 데이터 타입과 SQL 데이터 타입 간의 대응 관계.

| Python/pandas | SQLAlchemy | SQLite |
|---------------|------------|--------|
| `int` | `Integer` | INTEGER |
| `float` | `Float` | REAL |
| `str` | `String` | TEXT |
| `datetime` | `DateTime` | DATETIME |

---

## SQL 용어

### 테이블 (Table)

데이터베이스에서 데이터를 저장하는 기본 단위. 행(레코드)과 열(필드)로 구성됩니다.

### 스키마 (Schema)

테이블의 구조를 정의하는 것. 컬럼 이름, 데이터 타입, 제약 조건 등을 포함합니다.

### 쿼리 (Query)

데이터베이스에 데이터를 요청하거나 조작하는 명령어.

```sql
SELECT * FROM matches WHERE Meet_Year = 2025;
```

---

## 저장 모드

### replace

기존 테이블을 삭제하고 새로 생성. 데이터를 완전히 갱신할 때 사용합니다.

### append

기존 테이블에 새 행을 추가. 증분 데이터를 저장할 때 사용합니다.

### fail

테이블이 이미 존재하면 오류 발생. 실수로 덮어쓰는 것을 방지합니다.

---

## 인코딩 용어

### UTF-8

유니코드 문자를 인코딩하는 가변 길이 문자 인코딩 방식. 한글, 일본어 등 다국어를 지원합니다.

### BOM (Byte Order Mark)

파일의 인코딩을 나타내는 특수 바이트. UTF-8 BOM은 `EF BB BF`입니다.

### utf-8-sig

Python에서 UTF-8 with BOM을 나타내는 인코딩 이름.

```python
df.to_csv("file.csv", encoding='utf-8-sig')
```

---

## 타입 추론 용어

### 타입 추론 (Type Inference)

데이터의 값을 분석하여 적절한 데이터 타입을 자동으로 결정하는 과정.

### 패턴 매칭 (Pattern Matching)

정규 표현식을 사용하여 문자열이 특정 형식(예: 날짜)과 일치하는지 확인하는 방법.

### 정규 표현식 (Regular Expression, Regex)

문자열 패턴을 정의하는 특수 문법.

```python
import re
pattern = r'^\d{4}-\d{2}-\d{2}$'  # YYYY-MM-DD 형식
re.match(pattern, "2025-02-15")  # 매칭 성공
```

---

## 기타 용어

### 딕셔너리 리스트 (list[dict])

Python에서 테이블 형태의 데이터를 표현하는 일반적인 형식. 각 딕셔너리가 하나의 행을 나타냅니다.

```python
data = [
    {'name': '울산', 'score': 3},
    {'name': '포항', 'score': 1}
]
```

### 청크 (Chunk)

대용량 데이터를 처리할 때 나누는 작은 단위.

### 인덱스 (Index)

DataFrame의 각 행을 식별하는 레이블. 기본값은 0부터 시작하는 정수입니다.
