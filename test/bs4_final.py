import requests
import pandas as pd
from bs4 import BeautifulSoup

from rich.console import Console
from rich.progress import track

def extract_value(text, remove_char=""):
    """
    문자열에서 콜론(:) 뒤의 값을 추출하고, 특정 문자를 제거한 후 공백을 정리합니다.
    
    Args:
        text (str): '항목 : 값' 형태의 원본 문자열 (예: "관중수 : 10,519")
        remove_char (str, optional): 값에서 제거할 특정 문자나 기호 (예: "%", "°C"). 
                                     기본값은 빈 문자열("")입니다.
    
    Returns:
        str: 추출 및 전처리가 완료된 깔끔한 문자열
    """
    #if not text: return None

    # 1. : 기준으로 자르고 뒷부분 가져오기
    value = text.split(':')[-1]
    
    # 2. 특정 문자 제거 (값이 있을 때만 실행)
    if remove_char:
        value = value.replace(remove_char, '')
    
    # 3. 앞뒤백 제거 후 반환
    return value.strip()

# ---------------------------------------------------------
year = 2025 # 연도 (2013 ~ 현재 연도)
meetSeq = 1 # 1: K리그1, 2: K리그2
games = range(1, 229)  # 1 ~ 228 (총 38라운드)
startTabNum = 3  # 1: 경기결과, 2: 라인업, 3: 프리매치, 4: 경기영상, 5: 경기통계
# HTTP 요청 시 사용자 에이전트 설정
headers = {
    # 사용하고 있는 브라우저에 "my user agent" 검색하여 확인
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}
# 데이터 저장용 리스트
dataset = []

console = Console()
console.print(f"\n[bold magenta][{year}년 K리그 경기 데이터][/bold magenta] (총 {len(games)}경기)", style="bold")

for gameId in track(games, description="[cyan]수집 중...[/cyan]"):
    url = f"https://www.kleague.com/match.do?year={year}&meetSeq={meetSeq}&gameId={gameId}&leagueId=&startTabNum={startTabNum}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # 상태 코드 검사 (200번대가 아니면 여기서 에러 발생 -> except로 점프)

        soup = BeautifulSoup(response.text, 'html.parser')

        # 초기 데이터 구조
        data = {
            "Meet_Year": year,     # STRING
            "LEAGUE_NAME": None,   # STRING
            "Round": None,         # STRING
            "Game_id": gameId,     # STRING
            "Game_Datetime": None, # DATETIME
            "Day": None,           # STRING
            "HomeTeam": None,      # STRING
            "AwayTeam": None,      # STRING
            "Field_Name": None,    # STRING
            "Audience_Qty": None,  # INT64
            "Weather": None,       # STRING
            "Temperature": None,   # FLOAT
            "Humidity": None       # INT64
        }

        # 리그명 (K리그1, K리그2, 승강PO, 슈퍼컵)
        tag = soup.select_one('#meetSeq option[selected]')
        if tag:
            data["LEAGUE_NAME"] = tag.text.strip()
        else:
            print("❌ 리그명 정보를 찾을 수 없습니다.")

        # 라운드 (1~38)
        tag = soup.select_one('#roundId option[selected]')
        if tag:
            data["Round"] = tag.text.strip()
        else:
            print("❌ 라운드 정보를 찾을 수 없습니다.")

        # 일시 (YYYY/MM/DD (Day) HH:MM)
        tag = soup.select_one('div.versus p')
        if tag:
            parts = tag.text.split()
            data["Game_Datetime"] = f"{parts[0]} {parts[-1]}:00".replace("/", "-")
            data["Day"] = parts[1].strip("()")
        else:
            print("❌ 일시 정보를 찾을 수 없습니다.")

        # 홈vs어웨이 (MM/DD)
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
                print("⚠️ 올바르지 않은 정보: {tag.text}")

        dataset.append(data)

    except requests.exceptions.HTTPError as e:
        # 404 Not Found, 500 Server Error 등
        print(f"⛔ HTTP 에러 발생: {e}")

    except requests.exceptions.RequestException as e:
        # 인터넷 연결 끊김 등 기타 모든 에러
        print(f"⛔ 네트워크 에러 발생: {e}")

    except Exception as e:
        # 파이썬 코드 에러 (변수명 오타 등)
        print(f"⛔ 알 수 없는 에러 발생: {e}")

if dataset:
    # 데이터프레임 생성
    df = pd.DataFrame(dataset)

    # CSV 파일로 저장
    csv_filename = f"kleague_match_info_{year}.csv"
    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"✅ 데이터가 '{csv_filename}' 파일로 저장되었습니다.")
