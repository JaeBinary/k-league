import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def parse_jleague_selenium_only():
    url = "https://www.jleague.jp/match/j1/2025/021401/live/#live"
    print(f"🌐 [Selenium] 페이지 접속 중: {url}")

    # 1. 브라우저 옵션
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(url)

        # 2. 데이터 로딩 대기
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "liveTopTable"))
            )
            print("✅ 데이터 로딩 완료!")
        except:
            print("⚠️ 시간 초과: 테이블이 아직 안 떴을 수 있음")
            return

        # -----------------------------------------------------------
        # [핵심 변경] BS4 대신 Selenium으로 직접 요소 찾기
        # -----------------------------------------------------------
        
        # 1. '스타디움' 텍스트를 포함한 td의 조상 table 찾기 (XPATH 사용)
        # BS4의 find_parent와 같은 역할입니다.
        try:
            # XPATH 설명: 텍스트에 'スタジアム'가 있는 td를 찾고(/..), 그 부모의 부모(...)를 타고 올라가 table을 찾아라
            # 혹은 간단히 ancestor::table 사용
            table = driver.find_element(By.XPATH, "//td[contains(text(), 'スタジアム')]/ancestor::table")
        except:
            print("❌ 'スタジアム'이 포함된 테이블을 찾을 수 없습니다.")
            return

        # 2. 테이블 안의 모든 td 가져오기
        cells = table.find_elements(By.TAG_NAME, "td")

        # 3. 데이터 매핑 (기존 로직 동일)
        TARGET_MAP = {
            "入場者数": "Attendance",
            "天候 / 気温 / 湿度": "Weather_Info",
        }

        data = {}

        # Selenium의 .text는 자동으로 공백을 strip 해줍니다.
        for i in range(0, len(cells), 2):
            if i + 1 >= len(cells): break
            
            label = cells[i].text
            value = cells[i+1].text
            
            if label in TARGET_MAP:
                data[TARGET_MAP[label]] = value

        # 4. 데이터 정제 (Python 로직은 동일)
        if "Attendance" in data:
            clean_num = data["Attendance"].replace(",", "").replace("人", "")
            data["Attendance"] = int(clean_num) if clean_num.isdigit() else 0

        if "Weather_Info" in data:
            parts = data.pop("Weather_Info").split("/")
            if len(parts) >= 3:
                data["Weather"] = parts[0].strip()
                data["Temperature"] = parts[1].strip()
                data["Humidity"] = parts[2].strip()

        # 출력
        print("\n📊 추출 결과:")
        for k, v in data.items():
            print(f"{k}: {v}")

    finally:
        driver.quit()

if __name__ == "__main__":
    parse_jleague_selenium_only()
