from scraper.kleague_match_scraper import collect_kleague_data
from saver.csv_saver import save_to_csv

def main() -> None:
    """
    메인 실행 함수
    """

    year_label, dataset = collect_kleague_data([2023, 2025], "K리그1")
    save_to_csv(year_label, dataset)


if __name__ == "__main__":
    main()
