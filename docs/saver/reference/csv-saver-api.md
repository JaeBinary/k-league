# CSV Saver API 레퍼런스

CSV 저장 모듈의 API 상세 문서입니다.

## 개요

`csv_saver` 모듈은 딕셔너리 리스트를 CSV 파일로 저장하는 기능을 제공합니다. pandas DataFrame을 사용하여 데이터를 변환하고, UTF-8 with BOM 인코딩으로 저장합니다.

## 함수

### save_to_csv

데이터셋을 CSV 파일로 저장합니다.

#### 시그니처

```python
def save_to_csv(
    dataset: list[dict],
    file_name: str
) -> str | None
```

#### 파라미터

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `dataset` | `list[dict]` | 저장할 데이터 (딕셔너리 리스트) |
| `file_name` | `str` | 저장할 파일명 (확장자 제외) |

#### 반환값

| 타입 | 설명 |
|-----|------|
| `str` | 저장된 파일의 전체 경로 |
| `None` | 저장 실패 (빈 데이터) |

#### 저장 위치

파일은 `data/{file_name}.csv` 경로에 저장됩니다.

```
project/
└── data/
    └── {file_name}.csv
```

#### 인코딩

`utf-8-sig` (UTF-8 with BOM) 인코딩을 사용합니다. 이 인코딩은 Microsoft Excel에서 한글이 깨지지 않고 정상 표시됩니다.

#### 사용 예제

```python
from src.saver import save_to_csv

# 기본 사용법
data = [
    {'HomeTeam': '울산', 'AwayTeam': '포항', 'Score': '2-1'},
    {'HomeTeam': '전북', 'AwayTeam': '수원', 'Score': '1-0'}
]

path = save_to_csv(data, "matches_2025")
print(path)  # data/matches_2025.csv
```

```python
# 스크래퍼와 함께 사용
from src.scraper.kleague_match_scraper import collect_kleague_match_data
from src.saver import save_to_csv

data, filename = collect_kleague_match_data(year=2025, league="K리그1")
csv_path = save_to_csv(data, filename)
```

```python
# 빈 데이터 처리
result = save_to_csv([], "empty")
# ⚠️  저장할 데이터가 없습니다.
print(result)  # None
```

#### 출력 메시지

| 상황 | 메시지 |
|-----|-------|
| 성공 | `📂 저장 경로: {경로}` |
| 빈 데이터 | `⚠️  저장할 데이터가 없습니다.` |

---

## 상수

### DATA_DIR

데이터 저장 디렉토리 경로입니다.

```python
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "..", "..", "data")
```

기본값: `project/data/`

디렉토리가 존재하지 않으면 자동으로 생성됩니다.

```python
os.makedirs(DATA_DIR, exist_ok=True)
```

---

## 내부 동작

### 1. 입력 검증

빈 리스트가 전달되면 조기 반환합니다.

```python
if not dataset:
    print("⚠️  저장할 데이터가 없습니다.")
    return None
```

### 2. DataFrame 변환

pandas DataFrame으로 변환합니다.

```python
df = pd.DataFrame(dataset)
```

### 3. 파일 저장

CSV 파일로 저장합니다.

```python
csv_file_path = os.path.join(DATA_DIR, f"{file_name}.csv")
df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
```

| 옵션 | 값 | 설명 |
|-----|---|------|
| `index` | `False` | 행 인덱스 저장 안 함 |
| `encoding` | `'utf-8-sig'` | UTF-8 with BOM |

---

## 관련 문서

- [CSV 저장 튜토리얼](../tutorials/save-to-csv.md)
- [Saver 아키텍처](../explanations/architecture.md)
