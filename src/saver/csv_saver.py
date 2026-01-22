from datetime import datetime
import os
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def save_to_csv(year: int, dataset: list[dict]) -> str | None:
    """
    데이터셋을 CSV 파일로 저장합니다.

    Args:
        dataset (list): 경기 정보 딕셔너리 리스트

    Returns:
        str: 저장된 파일명, 실패 시 None
    """
    if not dataset:
        print("⚠️  저장할 데이터가 없습니다.")
        return None

    today = datetime.now().strftime("%Y%m%d")

    df = pd.DataFrame(dataset)
    csv_filename = os.path.join(DATA_DIR, f"kleague_match_info_{year}.csv")
    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"📂 저장 경로: {csv_filename}")

    return csv_filename
