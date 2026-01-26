from scraper.jleague_match_scraper import collect_jleague_match_data
from scraper.kleague_match_scraper import collect_kleague_match_data
from scraper.kleague_preview_scraper import collect_kleague_preview_data
from saver.csv_saver import save_to_csv
from saver.db_saver import save_to_db

def main() -> None:
    """
    메인 실행 함수
    """

    # K리그 match 데이터 수집 후 CSV 저장 및 DB 변환
    """
    dataset, file_name = collect_kleague_match_data([2023, 2025], ["K리그1", "K리그2"])
    csv_file_path = save_to_csv(dataset, file_name)
    save_to_db(csv_file_path, table_name="kleague")
    """

    # K리그 preview 데이터 수집 후 CSV 저장 및 DB 변환
    """
    dataset, file_name = collect_kleague_preview_data([2023, 2025], ["K리그1", "K리그2"])
    csv_file_path = save_to_csv(dataset, file_name)
    save_to_db(csv_file_path, table_name="preview")
    """

    # J리그 match 데이터 수집 후 CSV 저장 및 DB 변환
    #"""
    dataset, file_name = collect_jleague_match_data([2023, 2025], ["J리그1"], parallel=True, max_workers=4)
    csv_file_path = save_to_csv(dataset, file_name)
    save_to_db(csv_file_path, table_name="jleague")
    #"""

if __name__ == "__main__":
    main()
