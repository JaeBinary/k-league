import time
import csv
from typing import Dict

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

# Rich (시각화)
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.theme import Theme

# --- 상수 설정 ---
YEAR = 2023
TARGET_GAMES = 228
BASE_URL = "https://www.kleague.com/index.do"
MATCH_URL_TEMPLATE = "https://www.kleague.com/match.do?year={}&meetSeq=1&gameId={}&leagueId=1&startTabNum=1"
CSV_FILENAME = f"kleague_match_info_{YEAR}.csv"

XPATH_TEMPLATE = "//ul[contains(@class, 'game-sub-info')]//li[contains(text(), '{}')]"
CSS_DATE_SELECTOR = "div.versus > p"

# 테마 설정 (색상 예쁘게)
custom_theme = Theme({
    "id": "bold cyan",
    "date": "dim white",
    "team": "bold yellow",
    "vs": "dim white",
    "stadium": "green",
    "audience": "bold magenta",
})
console = Console(theme=custom_theme)

# ---------------------------------------------------------
# [기능 1] 브라우저 내부 로그 차단 (TensorFlow 경고 삭제)
# ---------------------------------------------------------
def get_silent_driver():
    options = webdriver.ChromeOptions()
    # 불필요한 로그 숨기기
    options.add_argument("--log-level=3") 
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    return driver

# ---------------------------------------------------------
# [기능 2] 데이터 추출 함수들 (로직 동일)
# ---------------------------------------------------------
def get_clean_info(driver: WebDriver, keyword: str) -> str:
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
    try:
        date_text = driver.find_element(By.CSS_SELECTOR, CSS_DATE_SELECTOR).text
        parts = date_text.split()
        return f"{parts[0]} {parts[-1]}".replace("/", "-") + ":00"
    except:
        return ""

def get_teams(driver: WebDriver) -> tuple:
    try:
        full_text = driver.find_element(By.CSS_SELECTOR, "#gameId option:checked").text
        teams_only = full_text.split("(")[0].strip()
        if "vs" in teams_only:
            home, away = teams_only.split("vs")
            return home.strip(), away.strip()
        return "Unknown", "Unknown"
    except:
        return "Unknown", "Unknown"

def extract_game_data(driver: WebDriver, game_id: int) -> Dict[str, str]:
    url = MATCH_URL_TEMPLATE.format(YEAR, game_id)
    driver.get(url)
    time.sleep(1) # 페이지 로딩 대기

    home_team, away_team = get_teams(driver)

    return {
        "game_id": game_id,
        "datetime": get_match_datetime(driver),
        "home_team": home_team,
        "away_team": away_team,
        "stadium": get_clean_info(driver, "경기장"),
        "audience": get_clean_info(driver, "관중수"),
        "weather": get_clean_info(driver, "날씨"),
        "temp": get_clean_info(driver, "온도"),
        "humidity": get_clean_info(driver, "습도"),
        "broadcast": get_clean_info(driver, "중계정보")
    }

# ---------------------------------------------------------
# [기능 3] 메인 실행 (디자인 업그레이드)
# ---------------------------------------------------------
def main():
    driver = None
    
    # 1. 깔끔한 시작
    console.clear()
    console.rule(f"[bold blue]K-League {YEAR} Data Scraper")
    
    with console.status("[bold green]브라우저 실행 중 (로그 차단 모드)...", spinner="dots"):
        driver = get_silent_driver() # 조용한 드라이버 호출
        driver.get(BASE_URL)
        time.sleep(2)
    
    console.print(f"[bold blue]🚀 준비 완료! (대상: 1~{TARGET_GAMES}경기)[/]\n")

    # 2. 헤더 출력 (표 처럼 보이게)
    # ID(4칸) | 날짜(20칸) | 홈팀(6칸) vs 원정팀(6칸) | 관중(10칸) | 경기장
    header = f" {'ID':^3} │ {'Date Time':^19} │ {'Matchup':^18} │ {'Audience':^8} │ {'Stadium'}"
    console.print(f"[dim]{header}[/]")
    console.print("[dim]─────┼─────────────────────┼────────────────────┼──────────┼──────────────────────[/]")

    try:
        with open(CSV_FILENAME, mode='w', encoding='utf-8-sig', newline='') as file:
            fieldnames = ['game_id', 'datetime', 'home_team', 'away_team', 'stadium', 'audience', 'weather', 'temp', 'humidity', 'broadcast']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            
            # Progress Bar 디자인 개선
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Game {task.fields[game_id]}", justify="right"),
                BarColumn(bar_width=30, style="dim white", complete_style="green"),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console,
                transient=False # 완료 후에도 바 유지
            ) as progress:
                
                task_id = progress.add_task("Processing", total=TARGET_GAMES, game_id="Wait")

                for game_id in range(1, TARGET_GAMES + 1):
                    progress.update(task_id, game_id=str(game_id))
                    
                    try:
                        data = extract_game_data(driver, game_id)
                        writer.writerow(data)
                        
                        # [핵심] 줄 맞춤 포맷팅 (f-string의 정렬 기능 활용)
                        # :^6 (가운데 정렬 6칸), :>8 (오른쪽 정렬 8칸) 등 사용
                        if data['home_team'] == "Unknown":
                            progress.console.print(f" {game_id:03d} │ [red]데이터 없음 (Pass)[/]")
                        else:
                            # 예쁘게 한 줄 출력
                            row_str = (
                                f" [id]{game_id:03d}[/] │ "
                                f"[date]{data['datetime']}[/] │ "
                                f"[team]{data['home_team']:>5}[/] [vs]vs[/] [team]{data['away_team']:<5}[/] │ "
                                f"[audience]{data['audience']:>6}명[/] │ "
                                f"[stadium]{data['stadium']}[/]"
                            )
                            progress.console.print(row_str)
                    
                    except Exception as e:
                        progress.console.print(f"[bold red]❌ Error [{game_id}]: {e}[/]")

                    progress.update(task_id, advance=1)

    except Exception as e:
        console.print_exception()
    
    finally:
        console.rule("[bold green]작업 완료")
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
