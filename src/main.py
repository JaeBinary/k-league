from scraper.kleague_match_scraper import collect_kleague_match_data
from scraper.kleague_preview_scraper import collect_kleague_preview_data
from saver.csv_saver import save_to_csv

def main() -> None:
    """
    메인 실행 함수
    """


    #year_label, dataset = collect_kleague_match_data([2023, 2025], "K리그1")
    #save_to_csv(year_label, dataset)

    # preview 데이터 수집 및 CSV 저장
    year_label, preview_dataset = collect_kleague_preview_data([2023, 2025], "K리그1")
    save_to_csv(year_label, preview_dataset, data_type="preview")

if __name__ == "__main__":
    main()
