import requests
import pandas as pd
from bs4 import BeautifulSoup

from rich.console import Console
from rich.progress import track

# 기본 HTTP 헤더
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}


def extract_value(text: str, remove_char: str = "") -> str:
    """
    문자열에서 콜론(:) 뒤의 값을 추출하고, 특정 문자를 제거한 후 공백을 정리합니다.

    Args:
        text (str): '항목 : 값' 형태의 원본 문자열 (예: "관중수 : 10,519")
        remove_char (str, optional): 값에서 제거할 특정 문자나 기호 (예: "%", "°C")
                                     기본값은 빈 문자열("")

    Returns:
        str: 추출 및 전처리가 완료된 깔끔한 문자열
    """
    value = text.split(':')[-1]
    if remove_char:
        value = value.replace(remove_char, '')
    return value.strip()


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


def parse_game_info(soup: BeautifulSoup, year: int, game_id: int) -> dict:
    """
    BeautifulSoup 객체에서 경기 정보를 파싱합니다.

    Args:
        soup (BeautifulSoup): 파싱된 HTML 객체
        year (int): 시즌 연도
        game_id (int): 경기 ID

    Returns:
        dict: 경기 정보 딕셔너리
    """
    data = {
        "Meet_Year": year,
        "LEAGUE_NAME": None,
        "Round": None,
        "Game_id": game_id,
        "Game_Datetime": None,
        "Day": None,
        "HomeTeam": None,
        "AwayTeam": None,
        "Field_Name": None,
        "Audience_Qty": None,
        "Weather": None,
        "Temperature": None,
        "Humidity": None
    }

    # 리그명
    tag = soup.select_one('#meetSeq option[selected]')
    if tag:
        data["LEAGUE_NAME"] = tag.text.strip()
    else:
        print("❌ 리그명 정보를 찾을 수 없습니다.")

    # 라운드
    tag = soup.select_one('#roundId option[selected]')
    if tag:
        data["Round"] = tag.text.strip()
    else:
        print("❌ 라운드 정보를 찾을 수 없습니다.")

    # 일시
    tag = soup.select_one('div.versus p')
    if tag:
        parts = tag.text.split()
        data["Game_Datetime"] = f"{parts[0]} {parts[-1]}:00".replace("/", "-")
        data["Day"] = parts[1].strip("()")
    else:
        print("❌ 일시 정보를 찾을 수 없습니다.")

    # 홈 vs 어웨이
    tag = soup.select_one('#gameId option[selected]')
    if tag:
        teams = tag.text.split(' ')[0].strip()
        if 'vs' in teams:
            data["HomeTeam"], data["AwayTeam"] = teams.split('vs')
    else:
        print("❌ 팀 정보를 찾을 수 없습니다.")

    # 관중수, 경기장, 날씨, 온도, 습도
    tags = soup.select('ul.game-sub-info.sort-box li')
    for tag in tags:
        text = tag.text
        if "관중수" in text:
            data["Audience_Qty"] = extract_value(text, ',')
        elif "경기장" in text:
            data["Field_Name"] = extract_value(text)
        elif "날씨" in text:
            data["Weather"] = extract_value(text)
        elif "온도" in text:
            data["Temperature"] = extract_value(text, '°C')
        elif "습도" in text:
            data["Humidity"] = extract_value(text, '%')
        else:
            print(f"⚠️ 올바르지 않은 정보: {tag.text}")

    return data


def collect_kleague_match_data(year: int | list[int], league: str = "K리그1") -> tuple[str, list[dict]]:
    """
    K리그 경기 데이터를 수집합니다.

    Args:
        year (int | list[int]): 시즌 연도 (2013 ~ 현재) 또는 년도 범위 리스트
                                예: 2025 → 2025년만 수집
                                    [2023, 2025] → 2023~2025년 모두 수집
        league (str): 리그명 ("K리그1", "K리그2", "승강PO", "슈퍼컵")

    Returns:
        str: 년도 레이블 (예: "2025" 또는 "2023-2025")
        list: 수집된 경기 정보 리스트
    """

    # 리그 코드 매핑
    LEAGUE_CODE = {
        "K리그1": 1,
        "K리그2": 2,
        "승강PO": 3,
        "슈퍼컵": 4
    }

    meet_seq = LEAGUE_CODE.get(league)
    if meet_seq is None:
        print(f"⛔ 잘못된 리그명: {league} (가능한 값: {list(LEAGUE_CODE.keys())})")
        return "", []

    # 년도 처리: int → [int], list → 범위 확장
    if isinstance(year, int):
        years = [year]
        year_label = str(year)
    else:
        years = list(range(min(year), max(year) + 1))
        year_label = f"{min(year)}-{max(year)}"

    games = range(1, 229)
    start_tab_num = 3
    console = Console()

    dataset = []

    for year in years:
        console.print(f"\n[bold magenta][{year}년 {league} 경기 데이터][/bold magenta] (총 {len(games)}경기)", style="bold")

        for game_id in track(games, description=f"[cyan]수집 현황: [/cyan]"):
            url = f"https://www.kleague.com/match.do?year={year}&meetSeq={meet_seq}&gameId={game_id}&leagueId=&startTabNum={start_tab_num}"
            try:
                soup = fetch_page(url)
                if soup:
                    data = parse_game_info(soup, year, game_id)
                    dataset.append(data)

            except Exception as e:
                print(f"⛔ 알 수 없는 에러 발생 (year={year}, gameId={game_id}): {e}")

    return year_label, dataset
