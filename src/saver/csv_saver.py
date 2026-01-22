import os
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def save_to_csv(dataset: list[dict], file_name: str) -> str | None:
    """
    데이터셋을 CSV 파일로 저장합니다.

    Args:
        year_label (str): 년도 레이블 (예: "2025" 또는 "2023-2025")
        dataset (list): 경기 정보 딕셔너리 리스트
        data_type (str): 데이터 타입 ("match" 또는 "preview")

    Returns:
        str: 저장된 파일명, 실패 시 None
    """
    if not dataset:
        print("⚠️  저장할 데이터가 없습니다.")
        return None

    df = pd.DataFrame(dataset)

    csv_filename = os.path.join(DATA_DIR, f"{file_name}.csv")

    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"📂 저장 경로: {csv_filename}")

    return csv_filename
