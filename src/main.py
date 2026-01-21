from scaper.kleague_scarper import collect_kleague_data
from saver.csv_saver import save_to_csv

def main():
    """
    메인 실행 함수
    """

    dataset = collect_kleague_data(2025, "K리그1")
    save_to_csv(dataset)


if __name__ == "__main__":
    main()
