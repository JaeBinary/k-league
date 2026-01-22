import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.types import Integer, BigInteger, String, Float, Boolean, DateTime, Text

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# pandas dtype → SQLAlchemy 타입 매핑
DTYPE_MAPPING = {
    'int64': BigInteger,
    'int32': Integer,
    'int': Integer,
    'float': Float,
    'bool': Boolean,
    'datetime': DateTime,
    'object': String,
}


def _infer_sqlalchemy_type(dtype) -> type:
    """pandas dtype을 SQLAlchemy 타입으로 변환"""
    dtype_str = str(dtype).lower()
    for key, sql_type in DTYPE_MAPPING.items():
        if key in dtype_str:
            return sql_type
    return Text


def _build_dtype_map(df: pd.DataFrame) -> dict:
    """DataFrame 컬럼들의 SQLAlchemy 타입 맵 생성"""
    return {col: _infer_sqlalchemy_type(df[col].dtype) for col in df.columns}


def _to_dataframe(data: pd.DataFrame | list[dict] | str) -> pd.DataFrame | None:
    """다양한 입력 타입을 DataFrame으로 변환"""
    if isinstance(data, pd.DataFrame):
        return data

    if isinstance(data, str):
        print(f"📂 CSV 파일을 읽는 중: {data}")
        return pd.read_csv(data, encoding='utf-8-sig')

    if isinstance(data, list):
        if not data:
            return None
        return pd.DataFrame(data)

    print(f"⚠️  지원하지 않는 데이터 타입: {type(data)}")
    return None


def save_to_db(
    data: pd.DataFrame | list[dict] | str,
    table_name: str,
    db_path: str = None,
    if_exists: str = 'replace',
    dtype_map: dict = None
) -> str | None:
    """
    데이터를 SQLite 데이터베이스로 저장합니다.

    Args:
        data: DataFrame, list[dict], 또는 CSV 파일 경로
        table_name: 테이블 이름
        db_path: DB 파일 경로 (기본값: data/kleague.db)
        if_exists: 'replace' | 'append' | 'fail'
        dtype_map: 컬럼별 타입 지정 (None이면 자동 추론)

    Returns:
        저장된 DB 파일 경로, 실패 시 None
    """
    db_path = db_path or os.path.join(DATA_DIR, "kleague.db")

    df = _to_dataframe(data)
    if df is None or df.empty:
        print("⚠️  저장할 데이터가 없습니다.")
        return None

    if dtype_map is None:
        dtype_map = _build_dtype_map(df)

    engine = create_engine(f"sqlite:///{db_path}")
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists=if_exists,
        index=False,
        dtype=dtype_map
    )

    print(f"✅ '{db_path}' → '{table_name}' 테이블 ({len(df)}건)")
    return db_path
