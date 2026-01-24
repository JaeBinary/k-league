import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# .env 파일 로드
load_dotenv()

# 환경 변수에서 헤더 가져오기
USER_AGENT = {
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
    headers = headers or USER_AGENT

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')

    except requests.exceptions.HTTPError as e:
        print(f"⛔ HTTP 에러 발생: {e}")
    except requests.exceptions.RequestException as e:
        print(f"⛔ 네트워크 에러 발생: {e}")

    return None


def setup_chrome_driver() -> webdriver.Chrome:
    """
    Chrome WebDriver를 설정하고 초기화합니다.

    헤드리스 모드로 실행되며, 샌드박스 비활성화 및 User-Agent 설정을 포함합니다.

    Returns:
        webdriver.Chrome: 설정이 완료된 Chrome WebDriver 인스턴스
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 백그라운드 실행
    chrome_options.add_argument("--no-sandbox")  # 리눅스 환경 호환성
    chrome_options.add_argument("--disable-dev-shm-usage")  # 메모리 최적화
    chrome_options.add_argument(f"user-agent={USER_AGENT}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver
