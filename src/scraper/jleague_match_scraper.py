import requests
from bs4 import BeautifulSoup

from .scraper import fetch_page


def test_jleague_page():
    """J리그 페이지 접근 테스트"""
    url = "https://www.jleague.jp/match/j1/2025/021401/live/#trackingdata"

    # requests로 직접 가져오기
    response = requests.get(url)
    print(f"상태 코드: {response.status_code}")
    print(f"인코딩: {response.encoding}")
    print(f"내용 길이: {len(response.text)}자")

    # fetch_page로 가져오기
    soup = fetch_page(url)
    if soup:
        print(f"페이지 가져오기 성공")
        print(f"Title: {soup.title.string if soup.title else 'No title'}")
    else:
        print("페이지 가져오기 실패")


if __name__ == "__main__":
    test_jleague_page()
