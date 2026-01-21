# ② Third-party Library
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

def build_driver(headless: bool = False) -> WebDriver:

    """Chrome WebDriver 생성 및 기본 설정 적용
    
    Args:
        headless: True면 headless 모드, False면 일반 모드 (기본값: False)
    """

    # ChromeDriver 서비스 구성 (Path 객체를 문자열로 변환)
    service = Service()

    # Chrome 옵션 구성 (자동화 배너, 로그 메시지 숨김 및 창 최대화)
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
    else:
        options.add_argument("--start-maximized")

    # WebDriver 생성
    driver = webdriver.Chrome(service=service, options=options)

    # 대기 정책 설정 (페이지 로드 20초, 요소 검색 5초)
    driver.set_page_load_timeout(20)
    driver.implicitly_wait(5)

    return driver
