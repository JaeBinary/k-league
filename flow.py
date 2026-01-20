from selenium import webdriver
import time

# 설정 변수
year = 2025
start_game = 1
end_game = 228

driver = webdriver.Chrome()
driver.maximize_window()
driver.get("https://www.kleague.com/index.do")

try:
    for current_game in range(start_game, end_game + 1):
        
        url = f"https://www.kleague.com/match.do?year={year}&meetSeq=1&gameId={current_game}&leagueId=1&startTabNum=1"
        driver.get(url)
        print(f"Currently processing Game ID: {current_game} / {end_game}")

        # 3. 페이지 로딩 대기 (중요: 너무 빠르면 데이터 수집 불가)
        time.sleep(1)  # 2초 대기 (인터넷 속도에 따라 조절)

        # -------------------------------------------------
        # [이곳에 데이터 수집 코드를 작성하세요]
        # 예: score = driver.find_element(...)
        # -------------------------------------------------

except Exception as e:
    print(f"에러 발생: {e}")

finally:
    # 모든 작업이 끝나면 종료
    print("모든 작업이 완료되었습니다.")
    input("종료하려면 Enter를 누르세요...") # 결과 확인용
    driver.quit()