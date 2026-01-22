from scraper.kleague_scraper import collect_kleague_data
from saver.csv_saver import save_to_csv

def main() -> None:
    """
    메인 실행 함수
    """

    year, dataset = collect_kleague_data(2024, "K리그1")
    save_to_csv(year, dataset)


if __name__ == "__main__":
    main()
