# ② Third-party Library
from selenium import webdriver
from selenium.webdriver.common.by import By

# ③ Local Modules
from src.driver.chrome_driver import build_driver

def get_info(driver, keyword):
    """
    '관중수', '날씨' 등의 키워드가 포함된 항목의 값을 가져오고,
    키워드에 따라 불필요한 기호(°C, %, 콤마)를 자동으로 제거함.
    """
    try:
        # 1. 요소 찾기 및 텍스트 추출
        xpath = f"//ul[contains(@class, 'game-sub-info')]//li[contains(text(), '{keyword}')]"
        text = driver.find_element(By.XPATH, xpath).text
        
        # 2. 데이터 값만 분리 ("온도 : 10.0°C" -> "10.0°C")
        value = text.split(":")[-1].strip()

        # 3. 키워드별 맞춤형 데이터 정제 (여기가 핵심!)
        if keyword == "온도":
            value = value.replace("°C", "")  # '°C' 제거
        elif keyword == "습도":
            value = value.replace("%", "")   # '%' 제거
        elif keyword == "관중수":
            value = value.replace(",", "")   # 쉼표(,) 제거

        # 4. 최종 결과 반환 (앞뒤 공백 한 번 더 제거)
        return value.strip()

    except:
        return "" # 데이터가 없으면 빈 문자열 반환

def main() -> None:

    """메인 자동화 프로세스 실행"""

    # 설정 로드 및 드라이버 초기화
    driver = build_driver()

    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get("https://www.kleague.com/index.do")
    url = f"https://www.kleague.com/match.do?year=2025&meetSeq=1&gameId=1&leagueId=1&startTabNum=1"
    driver.get(url)

    # --- 1. 관중수 추출 ---
    audience = get_info(driver, "관중수")
    print(f"관중수: {audience}")
    # 관중수: 10519

    # --- 2. 경기장 추출 ---
    stadium = get_info(driver, "경기장")
    print(f"경기장: {stadium}")
    # 경기장: 포항 스틸야드

    # --- 3. 날씨 추출 ---
    weather = get_info(driver, "날씨")
    print(f"날씨: {weather}")
    # 날씨: 맑음

    # --- 4. 온도(°C) 추출 ---
    temperature = get_info(driver, "온도")
    print(f"온도: {temperature}")
    # 온도: 10.0

    # --- 5. 습도(%) 추출 ---
    humidity = get_info(driver, "습도")
    print(f"습도: {humidity}")
    # 습도: 43

    # --- 6. 중계정보 ---
    broadcast = get_info(driver, "중계정보")
    print(f"중계정보: {broadcast}")
    # 중계정보: skySports, COUPANGPLAY

    # --- 7. 경기 일시 추출 및 DB용 포맷 변환 ---
    date_text = driver.find_element(By.CSS_SELECTOR, "div.versus > p").text
    parts = date_text.split()
    raw_datetime = f"{parts[0]} {parts[-1]}"
    db_date = raw_datetime.replace("/", "-") + ":00"
    print(f"DB용 날짜/시간: {db_date}")
    # DB용 날짜/시간: 2025-02-15 13:00:00

    # 작업 완료 및 브라우저 종료
    input("🔍 작업 완료! Enter 키를 누르면 브라우저가 종료됩니다...")
    driver.quit()

    return None
