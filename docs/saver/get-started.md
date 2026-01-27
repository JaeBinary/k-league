# 데이터 저장 모듈 시작하기

이 문서는 수집된 경기 데이터를 CSV 파일이나 SQLite 데이터베이스로 저장하는 방법을 안내합니다.

## 개요

saver 모듈은 스크래퍼로 수집한 데이터를 영구 저장하는 기능을 제공합니다.

| 함수 | 저장 형식 | 용도 |
|-----|---------|------|
| `save_to_csv` | CSV 파일 | 엑셀 호환, 간편한 데이터 공유 |
| `save_to_db` | SQLite DB | SQL 쿼리, 대용량 데이터 관리 |

## 사전 요구사항

### 패키지 설치

```bash
pip install pandas sqlalchemy
```

### 저장 디렉토리

데이터는 기본적으로 프로젝트 루트의 `data/` 디렉토리에 저장됩니다. 디렉토리가 없으면 자동으로 생성됩니다.

```
project/
├── data/              # 저장 디렉토리 (자동 생성)
│   ├── *.csv          # CSV 파일
│   └── match.db       # SQLite DB
└── src/
    └── saver/
```

## 빠른 시작

### CSV 파일로 저장

```python
from src.saver import save_to_csv
from src.scraper.kleague_match_scraper import collect_kleague_match_data

# 데이터 수집
data, filename = collect_kleague_match_data(year=2025, league="K리그1")

# CSV로 저장
csv_path = save_to_csv(data, filename)
print(f"저장 완료: {csv_path}")
```

### SQLite DB로 저장

```python
from src.saver import save_to_db
from src.scraper.kleague_match_scraper import collect_kleague_match_data

# 데이터 수집
data, filename = collect_kleague_match_data(year=2025, league="K리그1")

# DB로 저장
db_path = save_to_db(data, table_name="kleague1_2025")
print(f"저장 완료: {db_path}")
```

## 다음 단계

- [CSV 저장 튜토리얼](./tutorials/save-to-csv.md): CSV 저장의 상세한 사용법을 배웁니다.
- [데이터베이스 저장 튜토리얼](./tutorials/save-to-database.md): SQLite DB 저장 방법을 배웁니다.
- [데이터 추가하기](./how-tos/append-data.md): 기존 데이터에 새 데이터를 추가합니다.
- [API 레퍼런스](./reference/csv-saver-api.md): 함수 상세 사양을 확인합니다.
