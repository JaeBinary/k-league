import time
import csv
from typing import Dict

# ② Third-party Library
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

# --- 상수 설정 ---
year = 2023
game = 5
BASE_URL = "https://www.kleague.com/index.do"
XPATH_TEMPLATE = "//ul[contains(@class, 'game-sub-info')]//li[contains(text(), '{}')]"
CSS_DATE_SELECTOR = "div.versus > p"
CSV_FILENAME = f"kleague_match_info_{year}.csv" # 파일명 변경

# ---------------------------------------------------------
# 1. 데이터 정제 및 추출 함수들
# ---------------------------------------------------------
def get_clean_info(driver: WebDriver, keyword: str) -> str:
    """기호(°C, %, ,)를 제거하고 순수 데이터만 추출"""
    try:
        target_elem = driver.find_element(By.XPATH, XPATH_TEMPLATE.format(keyword))
        value = target_elem.text.split(":")[-1].strip()

        replacements = {"온도": "°C", "습도": "%", "관중수": ","}
        if keyword in replacements:
            value = value.replace(replacements[keyword], "")
        
        return value.strip()
    except:
        return "" 

def get_match_datetime(driver: WebDriver) -> str:
    """일시 추출 및 DB 포맷 변환"""
    try:
        date_text = driver.find_element(By.CSS_SELECTOR, CSS_DATE_SELECTOR).text
        parts = date_text.split()
        return f"{parts[0]} {parts[-1]}".replace("/", "-") + ":00"
    except:
        return ""

def get_teams(driver: WebDriver) -> tuple:
    """[추가됨] 홈팀과 원정팀 이름 추출"""
    try:
        # id가 gameId인 select 태그에서 현재 선택된 option의 텍스트 추출
        full_text = driver.find_element(By.CSS_SELECTOR, "#gameId option:checked").text
        # "포항vs대전 (02/15)" -> "포항", "대전" 분리
        teams_only = full_text.split("(")[0].strip() # 날짜 제거
        
        if "vs" in teams_only:
            home, away = teams_only.split("vs")
            return home.strip(), away.strip()
        return "Unknown", "Unknown"
    except:
        return "Unknown", "Unknown"

def extract_game_data(driver: WebDriver, game_id: int) -> Dict[str, str]:
    """페이지 이동 후 데이터 수집"""
    url = f"https://www.kleague.com/match.do?year={year}&meetSeq=1&gameId={game_id}&leagueId=1&startTabNum=1"
    driver.get(url)
    time.sleep(1) 

    # 홈/원정 팀 가져오기
    home_team, away_team = get_teams(driver)

    return {
        "game_id": game_id,
        "datetime": get_match_datetime(driver),
        "home_team": home_team,  # 추가됨
        "away_team": away_team,  # 추가됨
        "stadium": get_clean_info(driver, "경기장"),
        "audience": get_clean_info(driver, "관중수"),
        "weather": get_clean_info(driver, "날씨"),
        "temp": get_clean_info(driver, "온도"),
        "humidity": get_clean_info(driver, "습도"),
        "broadcast": get_clean_info(driver, "중계정보")
    }

# ---------------------------------------------------------
# 2. 메인 실행 함수
# ---------------------------------------------------------
def main():
    print("🚀 브라우저를 실행합니다...")
    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get(BASE_URL)
    time.sleep(2)

    try:
        with open(CSV_FILENAME, mode='w', encoding='utf-8-sig', newline='') as file:
            # 헤더에 home_team, away_team 추가
            fieldnames = ['game_id', 'datetime', 'home_team', 'away_team', 'stadium', 'audience', 'weather', 'temp', 'humidity', 'broadcast']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            
            print(f"📂 '{CSV_FILENAME}' 생성 완료. 수집 시작...")

            for game_id in range(1, game+1):
                try:
                    data = extract_game_data(driver, game_id)
                    writer.writerow(data)
                    print(f"✅ [{game_id}/{game}] {data['home_team']} vs {data['away_team']} | {data['datetime']}")
                
                except Exception as e:
                    print(f"⚠️ [{game_id}] 에러 발생: {e}")

    except Exception as e:
        print(f"❌ 오류: {e}")
    
    finally:
        print("🏁 작업 완료.")
        driver.quit()

if __name__ == "__main__":
    main()