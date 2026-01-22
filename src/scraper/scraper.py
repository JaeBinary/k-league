import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수에서 헤더 가져오기
DEFAULT_HEADERS = {
    "User-Agent": os.getenv("USER_AGENT")
}


def fetch_page(url: str, headers: dict | None = None) -> BeautifulSoup | None:
    """
    URL에서 HTML 페이지를 가져옵니다.

    Args:
        url (str): 요청할 URL
        headers (dict, optional): HTTP 헤더

    Returns:
        BeautifulSoup: 파싱된 HTML 객체, 실패 시 None
    """
    headers = headers or DEFAULT_HEADERS

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')

    except requests.exceptions.HTTPError as e:
        print(f"⛔ HTTP 에러 발생: {e}")
    except requests.exceptions.RequestException as e:
        print(f"⛔ 네트워크 에러 발생: {e}")

    return None
