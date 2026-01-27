# 트러블슈팅

Saver 모듈 사용 중 발생할 수 있는 오류와 해결 방법을 정리한 문서입니다.

## CSV Saver 오류

### 빈 데이터 경고

#### 증상

```
⚠️  저장할 데이터가 없습니다.
```

함수가 `None`을 반환합니다.

#### 원인

- 빈 리스트 `[]`가 전달됨
- 스크래퍼가 데이터를 수집하지 못함

#### 해결 방법

저장 전 데이터 존재 여부를 확인합니다.

```python
data, filename = collect_kleague_match_data(year=2025, league="K리그1")

if data:
    save_to_csv(data, filename)
else:
    print("수집된 데이터가 없습니다.")
```

---

### 엑셀에서 한글 깨짐

#### 증상

CSV 파일을 엑셀에서 열었을 때 한글이 `?????` 또는 이상한 문자로 표시됩니다.

#### 원인

- 엑셀이 파일 인코딩을 잘못 인식
- 수동으로 CSV를 생성했을 때 인코딩 미지정

#### 해결 방법

`save_to_csv`는 `utf-8-sig` (UTF-8 with BOM) 인코딩을 사용하므로 이 문제가 발생하지 않습니다.

수동으로 CSV를 저장하는 경우:

```python
df.to_csv("file.csv", encoding='utf-8-sig', index=False)
```

---

### 파일 경로 오류

#### 증상

```
FileNotFoundError: [Errno 2] No such file or directory
```

#### 원인

- 저장 디렉토리가 존재하지 않음 (자동 생성 실패)
- 권한 문제

#### 해결 방법

`data/` 디렉토리가 자동 생성되지만, 권한 문제가 있으면 수동으로 생성합니다.

```bash
mkdir data
```

---

## DB Saver 오류

### 지원하지 않는 데이터 타입

#### 증상

```
⚠️  지원하지 않는 데이터 타입: <class 'tuple'>
```

함수가 `None`을 반환합니다.

#### 원인

지원하지 않는 타입의 데이터가 전달됨 (DataFrame, list[dict], str 외).

#### 해결 방법

지원되는 형식으로 변환합니다.

```python
# 튜플 리스트 → 딕셔너리 리스트로 변환
tuple_data = [('울산', '포항'), ('전북', '수원')]
dict_data = [{'HomeTeam': h, 'AwayTeam': a} for h, a in tuple_data]

save_to_db(dict_data, table_name="matches")
```

---

### 날짜 타입 인식 실패

#### 증상

날짜 컬럼이 DATETIME이 아닌 TEXT로 저장됩니다.

#### 원인

날짜 문자열 형식이 자동 인식 패턴과 일치하지 않음.

지원 패턴:
- `YYYY-MM-DD` (Date)
- `YYYY-MM-DD HH:MM:SS` (DateTime)

#### 해결 방법

**방법 1: 데이터 형식 변환**

```python
import pandas as pd

df = pd.DataFrame(data)
# 다른 형식을 표준 형식으로 변환
df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M:%S')
save_to_db(df, table_name="matches")
```

**방법 2: dtype_map 직접 지정**

```python
from sqlalchemy.types import DateTime

save_to_db(data, table_name="matches", dtype_map={'date': DateTime})
```

---

### 테이블 스키마 불일치 (append 모드)

#### 증상

```
sqlite3.OperationalError: table matches has X columns but Y values were supplied
```

#### 원인

`if_exists='append'` 모드에서 새 데이터의 컬럼이 기존 테이블과 다름.

#### 해결 방법

**방법 1: 컬럼 맞추기**

```python
import pandas as pd

# 기존 테이블 컬럼 확인
from sqlalchemy import create_engine, inspect
engine = create_engine("sqlite:///data/match.db")
columns = [col['name'] for col in inspect(engine).get_columns("matches")]

# 새 데이터에서 기존 컬럼만 선택
df = pd.DataFrame(new_data)
df = df[columns]  # 기존 컬럼만 유지

save_to_db(df, table_name="matches", if_exists='append')
```

**방법 2: 테이블 재생성**

```python
# replace 모드로 전체 데이터 저장
all_data = existing_data + new_data
save_to_db(all_data, table_name="matches", if_exists='replace')
```

---

### DB 파일 잠금

#### 증상

```
sqlite3.OperationalError: database is locked
```

#### 원인

- 다른 프로세스가 DB 파일을 사용 중
- DB Browser 같은 도구에서 DB를 열어놓음

#### 해결 방법

1. DB 파일을 사용하는 다른 프로그램 종료
2. 잠시 후 재시도

```python
import time

for attempt in range(3):
    try:
        save_to_db(data, table_name="matches")
        break
    except Exception as e:
        if "locked" in str(e):
            time.sleep(1)
        else:
            raise
```

---

### 메모리 부족

#### 증상

대용량 데이터 저장 시 메모리 오류 발생.

```
MemoryError
```

#### 해결 방법

데이터를 분할하여 저장합니다.

```python
import pandas as pd

# 대용량 데이터를 청크로 분할
df = pd.DataFrame(large_data)
chunk_size = 10000

for i, chunk in enumerate(range(0, len(df), chunk_size)):
    chunk_df = df.iloc[chunk:chunk + chunk_size]
    mode = 'replace' if i == 0 else 'append'
    save_to_db(chunk_df, table_name="matches", if_exists=mode)
```

---

## 공통 오류

### 모듈 임포트 실패

#### 증상

```
ModuleNotFoundError: No module named 'src.saver'
```

#### 해결 방법

프로젝트 루트에서 실행하거나 PYTHONPATH를 설정합니다.

```bash
# 프로젝트 루트에서 실행
cd /path/to/project
python -c "from src.saver import save_to_csv"

# 또는 PYTHONPATH 설정
export PYTHONPATH=/path/to/project:$PYTHONPATH
```

---

### pandas 또는 sqlalchemy 미설치

#### 증상

```
ModuleNotFoundError: No module named 'pandas'
ModuleNotFoundError: No module named 'sqlalchemy'
```

#### 해결 방법

필요한 패키지를 설치합니다.

```bash
pip install pandas sqlalchemy
```

---

## 도움 요청

위 해결 방법으로 문제가 해결되지 않으면 다음 정보와 함께 이슈를 제출해 주세요.

- 사용한 코드
- 전체 오류 메시지
- 입력 데이터 샘플 (민감 정보 제외)
- Python 버전 (`python --version`)
- pandas, sqlalchemy 버전 (`pip show pandas sqlalchemy`)
