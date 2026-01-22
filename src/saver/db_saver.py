import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.types import Integer, String, Float, Boolean, Date, DateTime, Text, UserDefinedType


class DateTimeNoMicro(UserDefinedType):
    """마이크로초 없이 저장하는 DATETIME 타입"""
    cache_ok = True

    def get_col_spec(self):
        return "DATETIME"

    # _dialect 인자는 사용되지 않음 (Python 관례: 언더스코어 접두사)
    def bind_processor(self, _dialect):
        def process(value):
            if value is not None and hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d %H:%M:%S')
            return value
        return process

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# pandas dtype → SQLAlchemy 타입 매핑
DTYPE_MAPPING = {
    'int64': Integer,
    'int32': Integer,
    'int': Integer,
    'float': Float,
    'bool': Boolean,
    'datetime': DateTime,
    'object': String,
}

# 날짜/시간 문자열 패턴
DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'  # YYYY-MM-DD
DATETIME_PATTERN = r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$'  # YYYY-MM-DD HH:MM:SS


def _detect_date_type(series: pd.Series) -> type | None:
    """문자열 컬럼이 DATE 또는 DATETIME 패턴인지 확인하여 해당 타입 반환"""
    if series.dtype != 'object':
        return None
    sample = series.dropna().head(5)
    if sample.empty:
        return None
    str_sample = sample.astype(str)
    if str_sample.str.match(DATETIME_PATTERN).all():
        return DateTimeNoMicro
    if str_sample.str.match(DATE_PATTERN).all():
        return Date
    return None


def _infer_sqlalchemy_type(dtype) -> type:
    """pandas dtype을 SQLAlchemy 타입으로 변환"""
    dtype_str = str(dtype).lower()
    for key, sql_type in DTYPE_MAPPING.items():
        if key in dtype_str:
            return sql_type
    return Text


def _build_dtype_map(df: pd.DataFrame) -> dict:
    """DataFrame 컬럼들의 SQLAlchemy 타입 맵 생성"""
    dtype_map = {}
    for col in df.columns:
        date_type = _detect_date_type(df[col])
        if date_type:
            dtype_map[col] = date_type
        else:
            dtype_map[col] = _infer_sqlalchemy_type(df[col].dtype)
    return dtype_map


def _convert_datetime_columns(df: pd.DataFrame, dtype_map: dict) -> pd.DataFrame:
    """Date/DateTime 컬럼을 datetime으로 변환"""
    df = df.copy()
    for col, sql_type in dtype_map.items():
        if sql_type == DateTimeNoMicro and df[col].dtype == 'object':
            df[col] = pd.to_datetime(df[col])
        elif sql_type == Date and df[col].dtype == 'object':
            df[col] = pd.to_datetime(df[col]).dt.date
    return df


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

    df = _convert_datetime_columns(df, dtype_map)

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
