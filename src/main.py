from scraper.kleague_match_scraper import collect_kleague_match_data
from scraper.kleague_preview_scraper import collect_kleague_preview_data
from saver.csv_saver import save_to_csv

def main() -> None:
    """
    메인 실행 함수
    """

    # match 데이터 수집 및 CSV 저장
    dataset, file_name = collect_kleague_match_data([2023, 2025], "K리그1")
    save_to_csv(dataset, file_name)

    # preview 데이터 수집 및 CSV 저장
    dataset, file_name = collect_kleague_preview_data([2023, 2025], "K리그1")
    save_to_csv(dataset, file_name)

if __name__ == "__main__":
    main()
