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


def setup_chrome_driver(optimized: bool = False) -> webdriver.Chrome:
    """
    Chrome WebDriver를 설정하고 초기화합니다.

    헤드리스 모드로 실행되며, 샌드박스 비활성화 및 User-Agent 설정을 포함합니다.

    Args:
        optimized: True일 경우 성능 최적화 옵션 적용 (이미지, CSS 차단 등)

    Returns:
        webdriver.Chrome: 설정이 완료된 Chrome WebDriver 인스턴스
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 백그라운드 실행
    chrome_options.add_argument("--no-sandbox")  # 리눅스 환경 호환성
    chrome_options.add_argument("--disable-dev-shm-usage")  # 메모리 최적화
    chrome_options.add_argument(f"user-agent={USER_AGENT}")

    # 성능 최적화 옵션
    if optimized:
        # GPU 비활성화 (헤드리스에서 불필요)
        chrome_options.add_argument("--disable-gpu")

        # 확장 프로그램 비활성화
        chrome_options.add_argument("--disable-extensions")

        # 자동화 제어 플래그 비활성화 (약간의 성능 향상)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # 이미지만 차단 (CSS와 JavaScript는 유지)
        prefs = {
            "profile.managed_default_content_settings.images": 2,  # 이미지 차단
            "profile.default_content_setting_values.notifications": 2,  # 알림 차단
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # 페이지 로드 전략: eager (DOM 준비되면 바로 진행, 이미지 대기 안 함)
        chrome_options.page_load_strategy = 'eager'

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver
