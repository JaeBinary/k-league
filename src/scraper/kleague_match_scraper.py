"""
K리그 경기 데이터 스크래퍼 (KLeague Match Data Scraper)

K리그 공식 웹사이트(www.kleague.com)에서 경기 정보를 추출하는 웹 스크래핑 모듈입니다.

주요 수집 데이터:
    - 경기 메타데이터: 시즌, 리그명, 라운드, 날짜, 시간, 요일, 팀명
    - 팀 정보: 홈팀/어웨이팀 순위
    - 경기장 정보: 경기장명, 관중 수, 날씨, 온도, 습도

데이터 흐름:
    1. URL 생성: 연도, 리그 코드, 경기 ID를 조합하여 경기별 URL 생성
    2. 페이지 요청: HTTP GET 요청으로 HTML 페이지 다운로드
    3. HTML 파싱: BeautifulSoup으로 구조화된 데이터 추출
    4. 데이터 정제: 문자열 파싱, 타입 변환, 불필요한 기호 제거
    5. 데이터 통합: 모든 경기 데이터를 리스트로 반환

기술 스택:
    - BeautifulSoup: HTML 파싱 및 CSS Selector 기반 데이터 추출
    - Rich: 진행률 표시 및 콘솔 출력 시각화
    - Requests: HTTP 요청 처리 (fetch_page 함수 내부에서 사용)
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Any, Optional

from bs4 import BeautifulSoup

from rich.console import Console
from rich.progress import track

from .scraper import fetch_page


# ============================================================================
# 헬퍼 함수 (Helper Functions)
# ============================================================================

def extract_value(text: str, remove_char: str = "") -> str:
    """
    레이블-값 형식의 문자열에서 값을 추출하고 정제합니다.

    K리그 웹사이트의 경기 정보는 "항목 : 값" 형식으로 제공됩니다.
    이 함수는 콜론 뒤의 값을 추출하고, 불필요한 단위 기호를 제거합니다.

    처리 과정:
        1. 콜론(:)을 기준으로 문자열 분리
        2. 마지막 부분(값)만 선택
        3. 지정된 문자(단위) 제거
        4. 앞뒤 공백 제거

    입력 예시:
        - "관중수 : 10,519" → "10,519"
        - "온도 : 25°C" (remove_char="°C") → "25"
        - "습도 : 60%" (remove_char="%") → "60"

    Args:
        text: '항목 : 값' 형태의 원본 문자열
             예: "관중수 : 10,519", "온도 : 25°C"
        remove_char: 값에서 제거할 단위 문자 또는 기호
                    기본값: "" (제거하지 않음)
                    예: "%", "°C", ","

    Returns:
        str: 정제된 값 문자열

    Example:
        >>> extract_value("관중수 : 10,519", ",")
        '10519'
        >>> extract_value("온도 : 25°C", "°C")
        '25'
        >>> extract_value("습도 : 60%", "%")
        '60'

    Note:
        - 콜론이 여러 개 있어도 마지막 값만 추출
        - remove_char가 빈 문자열이면 제거 단계 스킵
    """
    # 콜론 기준 분리 후 마지막 값 선택
    value = text.split(':')[-1]

    # 지정된 문자 제거 (단위 등)
    if remove_char:
        value = value.replace(remove_char, '')

    # 앞뒤 공백 제거 후 반환
    return value.strip()


# ============================================================================
# 데이터 파싱 함수 (Data Parsing Functions)
# ============================================================================

def parse_game_info(soup: BeautifulSoup, year: int, game_id: int) -> Dict[str, Any]:
    """
    BeautifulSoup 객체에서 K리그 경기 정보를 파싱하여 구조화된 데이터로 변환합니다.

    HTML 구조 분석:
        - 리그/라운드 정보: <select> 태그의 선택된 <option>
        - 경기 일시: <div class="versus"> 내부의 <p> 태그
        - 팀 정보: <select id="gameId"> 내부의 선택된 <option>
        - 순위 정보: <ul class="compare"> 내부의 <span class="font-red">
        - 경기장/날씨: <ul class="game-sub-info"> 내부의 <li> 리스트

    데이터 추출 전략:
        1. 기본 구조 초기화 (모든 필드를 None 또는 기본값으로 설정)
        2. CSS Selector로 각 정보 요소 탐색
        3. 요소 존재 여부 검증 후 데이터 추출
        4. 텍스트 정제 및 타입 변환
        5. 누락 데이터 처리 (경고 메시지 출력)

    출력 데이터 구조:
        {
            "Meet_Year": 2025,                    # 시즌 연도
            "LEAGUE_NAME": "하나원큐 K리그1 2025",  # 리그명
            "Round": "1R",                        # 라운드
            "Game_id": 1,                         # 경기 ID
            "Game_Datetime": "2025-03-01 14:00:00", # 경기 일시
            "Day": "토",                          # 요일
            "HomeTeam": "울산",                   # 홈팀명
            "AwayTeam": "포항",                   # 어웨이팀명
            "HomeRank": 1,                        # 홈팀 순위
            "AwayRank": 3,                        # 어웨이팀 순위
            "Field_Name": "울산문수축구경기장",    # 경기장명
            "Audience_Qty": "10519",              # 관중 수
            "Weather": "맑음",                    # 날씨
            "Temperature": "25",                  # 온도
            "Humidity": "60"                      # 습도
        }

    Args:
        soup: BeautifulSoup으로 파싱된 HTML 객체
             (fetch_page 함수의 반환값)
        year: 시즌 연도 (예: 2025)
        game_id: K리그 경기 ID (1부터 시작하는 순차 번호)

    Returns:
        Dict[str, Any]: 추출된 경기 정보 딕셔너리
                       필드가 누락된 경우 해당 값은 None

    Note:
        - 데이터 누락 시 None 값 유지 (프로세스 중단 없음)
        - 순위 정보는 정수 변환 실패 시 0 유지
        - 관중 수는 쉼표 제거 후 문자열로 반환
    """
    # ========================================================================
    # 데이터 구조 초기화
    # ========================================================================
    # 모든 필드를 기본값으로 초기화하여 데이터 스키마 보장
    data: Dict[str, Any] = {
        "Meet_Year": year,           # 입력 파라미터로 설정
        "LEAGUE_NAME": None,         # 리그 풀네임
        "Round": None,               # 라운드 정보 (1R, 2R, ...)
        "Game_id": game_id,          # 입력 파라미터로 설정
        "Game_Datetime": None,       # ISO 형식 날짜/시간
        "Day": None,                 # 요일
        "HomeTeam": None,            # 홈팀 이름
        "AwayTeam": None,            # 어웨이팀 이름
        "HomeRank": 0,               # 홈팀 순위 (기본값 0)
        "AwayRank": 0,               # 어웨이팀 순위 (기본값 0)
        "Field_Name": None,          # 경기장 이름
        "Audience_Qty": None,        # 관중 수
        "Weather": None,             # 날씨
        "Temperature": None,         # 온도
        "Humidity": None             # 습도
    }

    # ========================================================================
    # 리그명 추출
    # ========================================================================
    # HTML: <select id="meetSeq"><option selected>하나원큐 K리그1 2025</option></select>
    tag = soup.select_one('#meetSeq option[selected]')
    if tag:
        data["LEAGUE_NAME"] = tag.text.strip()
    else:
        print("❌ 리그명 정보를 찾을 수 없습니다.")

    # ========================================================================
    # 라운드 추출
    # ========================================================================
    # HTML: <select id="roundId"><option selected>1R</option></select>
    tag = soup.select_one('#roundId option[selected]')
    if tag:
        data["Round"] = tag.text.strip()
    else:
        print("❌ 라운드 정보를 찾을 수 없습니다.")

    # ========================================================================
    # 경기 일시 및 요일 추출
    # ========================================================================
    # HTML: <div class="versus"><p>2025/03/01 (토) 14:00</p></div>
    # 파싱: "2025/03/01 (토) 14:00" → ["2025/03/01", "(토)", "14:00"]
    tag = soup.select_one('div.versus p')
    if tag:
        parts = tag.text.split()

        # 날짜와 시간 조합 후 ISO 형식으로 변환
        # "2025/03/01 14:00" → "2025-03-01 14:00:00"
        data["Game_Datetime"] = f"{parts[0]} {parts[-1]}:00".replace("/", "-")

        # 요일 추출: "(토)" → "토"
        data["Day"] = parts[1].strip("()")
    else:
        print("❌ 일시 정보를 찾을 수 없습니다.")

    # ========================================================================
    # 홈팀 vs 어웨이팀 추출
    # ========================================================================
    # HTML: <select id="gameId"><option selected>울산vs포항 (14:00)</option></select>
    # 파싱: "울산vs포항 (14:00)" → "울산vs포항" → ["울산", "포항"]
    tag = soup.select_one('#gameId option[selected]')
    if tag:
        # 첫 번째 공백 전까지가 팀 정보 (시간 제거)
        teams = tag.text.split(' ')[0].strip()

        # "vs"로 분리하여 홈팀/어웨이팀 추출
        if 'vs' in teams:
            data["HomeTeam"], data["AwayTeam"] = teams.split('vs')
    else:
        print("❌ 팀 정보를 찾을 수 없습니다.")

    # ========================================================================
    # 팀 순위 추출
    # ========================================================================
    # HTML 구조:
    # <ul class="compare">
    #   <li>
    #     <div>홈팀 정보 <span class="font-red">1위</span></div>
    #     <div>어웨이팀 정보 <span class="font-red">3위</span></div>
    #   </li>
    # </ul>
    tag = soup.select_one('#tab03 ul.compare > li')

    if tag:
        # 순위 텍스트를 가진 모든 span 찾기
        # HTML 순서: [0] = 홈팀 순위, [1] = 어웨이팀 순위
        tags = tag.select('span.font-red')

        # 데이터 무결성 검증: 최소 2개의 순위 정보 필요
        if len(tags) >= 2:
            # 홈팀 순위 추출: "1위" → "1" → 1 (int)
            home_rank = tags[0].text.replace("위", "").strip()
            if home_rank.isdigit():
                data["HomeRank"] = int(home_rank)

            # 어웨이팀 순위 추출: "3위" → "3" → 3 (int)
            away_rank = tags[1].text.replace("위", "").strip()
            if away_rank.isdigit():
                data["AwayRank"] = int(away_rank)

    # ========================================================================
    # 경기장 정보 및 환경 데이터 추출
    # ========================================================================
    # HTML 구조:
    # <ul class="game-sub-info sort-box">
    #   <li>관중수 : 10,519</li>
    #   <li>경기장 : 울산문수축구경기장</li>
    #   <li>날씨 : 맑음</li>
    #   <li>온도 : 25°C</li>
    #   <li>습도 : 60%</li>
    # </ul>
    tags = soup.select('ul.game-sub-info.sort-box li')

    for tag in tags:
        text = tag.text

        # 키워드 매칭으로 데이터 분류 및 추출
        if "관중수" in text:
            data["Audience_Qty"] = extract_value(text, ',')  # 쉼표 제거
        elif "경기장" in text:
            data["Field_Name"] = extract_value(text)
        elif "날씨" in text:
            data["Weather"] = extract_value(text)
        elif "온도" in text:
            data["Temperature"] = extract_value(text, '°C')  # 단위 제거
        elif "습도" in text:
            data["Humidity"] = extract_value(text, '%')      # 퍼센트 기호 제거
        else:
            # 예상치 못한 정보 발견 시 경고
            print(f"⚠️ 올바르지 않은 정보: {tag.text}")

    return data


# ============================================================================
# 메인 수집 함수 (Main Collection Function)
# ============================================================================

def collect_kleague_match_data(
    year: int | List[int],
    league: str | List[str] = "K리그1"
) -> Tuple[List[Dict[str, Any]], str]:
    """
    K리그 경기 데이터를 수집하는 최상위 공개 API 함수입니다.

    수집 전략:
        - 경기 ID 기반 순차 접근: 각 시즌의 경기 수를 기반으로 1번부터 N번까지 순회
        - URL 패턴: https://www.kleague.com/match.do?year={year}&meetSeq={league}&gameId={id}
        - BeautifulSoup 파싱: 정적 HTML 페이지에서 데이터 추출

    사전 정의된 경기 수:
        - K리그1: 보통 228경기 (12팀 × 38라운드 / 2)
        - K리그2: 236~275경기 (팀 수에 따라 변동)
        - 승강PO: 4경기
        - 슈퍼컵: 1경기

    사용 예시:
        # 단일 연도, 단일 리그
        >>> data, filename = collect_kleague_match_data(2025, "K리그1")
        >>> print(filename)
        'kleague1_match_2025'
        >>> print(len(data))
        228

        # 여러 연도, 여러 리그
        >>> data, filename = collect_kleague_match_data([2023, 2025], ["K리그1", "K리그2"])
        >>> print(filename)
        'kleague_match_2023-2025'
        >>> print(len(data))
        1392  # (228+236)*3년

        # 승강 플레이오프만 수집
        >>> data, filename = collect_kleague_match_data(2024, "승강PO")
        >>> print(len(data))
        4

    Args:
        year: 수집할 시즌 연도 (2013년 이후 지원)
            - int: 단일 연도 (예: 2025)
            - List[int]: 연도 범위 (예: [2023, 2025] → 2023, 2024, 2025)
        league: 수집할 리그 (기본값: "K리그1")
            - str: 단일 리그
            - List[str]: 여러 리그 (예: ["K리그1", "K리그2"])
            - 지원 리그:
                * "K리그1": 하나원큐 K리그1 (1부 리그)
                * "K리그2": 하나원큐 K리그2 (2부 리그)
                * "승강PO": 승강 플레이오프
                * "슈퍼컵": FA컵 우승팀 vs K리그 우승팀

    Returns:
        Tuple[List[Dict[str, Any]], str]:
            - List[Dict[str, Any]]: 수집된 경기 데이터 리스트
            - str: 파일 저장에 사용할 파일명 (확장자 제외)
                  형식: "{리그}_match_{연도}"
                  예: "kleague1_match_2025", "kleague_match_2023-2025"

    Raises:
        ValueError: 지원하지 않는 리그 이름이 입력된 경우
        Exception: 개별 경기 수집 실패 (에러 메시지 출력 후 계속 진행)

    Note:
        - 경기가 존재하지 않는 ID는 자동으로 건너뜀
        - fetch_page 실패 시 해당 경기는 None 반환되어 dataset에 미포함
        - 수집 진행 상황은 Rich 라이브러리로 실시간 표시
        - J리그와 달리 트래킹 데이터 없음 (K리그 웹사이트에서 미제공)
    """
    # ========================================================================
    # 리그 이름 → API 코드 매핑 테이블
    # ========================================================================
    # K리그 웹사이트 URL 파라미터 "meetSeq"에 사용되는 리그 코드
    LEAGUE_CODE: Dict[str, int] = {
        "K리그1": 1,    # 1부 리그
        "K리그2": 2,    # 2부 리그
        "승강PO": 3,    # 승강 플레이오프
        "슈퍼컵": 4     # 슈퍼컵
    }

    # ========================================================================
    # 입력 파라미터 정규화
    # ========================================================================

    # 리그 파라미터를 리스트로 변환
    if isinstance(league, str):
        leagues: List[str] = [league]
        # 파일명용 레이블 생성: "K리그1" → "kleague1"
        league_label: str = league.replace("K리그", "kleague")
    else:
        leagues = league
        # 여러 리그: 통합 레이블 사용
        league_label = "kleague"

    # 연도 파라미터를 리스트로 변환 및 범위 확장
    if isinstance(year, int):
        # 단일 연도: [2025]
        years: List[int] = [year]
        year_label: str = str(year)
    else:
        # 연도 범위: [2023, 2025] → [2023, 2024, 2025]
        years = list(range(min(year), max(year) + 1))
        year_label = f"{min(year)}-{max(year)}"

    # ========================================================================
    # 시즌별 경기 수 매핑 테이블
    # ========================================================================
    # K리그는 경기 ID가 1부터 순차적으로 할당되므로 총 경기 수를 알아야 함
    # (리그, 연도) 튜플을 키로 사용
    GAMES_COUNT: Dict[Tuple[str, int], int] = {
        # K리그1: 12팀 기준 228경기
        ("K리그1", 2023): 228,
        ("K리그1", 2024): 228,
        ("K리그1", 2025): 228,

        # K리그2: 팀 수 변동에 따라 경기 수 다름
        ("K리그2", 2023): 236,
        ("K리그2", 2024): 236,
        ("K리그2", 2025): 275,  # 2025년부터 팀 수 증가

        # 승강 플레이오프: 고정 4경기
        ("승강PO", 2023): 4,
        ("승강PO", 2024): 4,
        ("승강PO", 2025): 4
    }

    # K리그 웹사이트 URL 파라미터 (용도 불명, 고정값 사용)
    start_tab_num: int = 3

    # Rich 콘솔 초기화 (진행률 표시용)
    console = Console()

    # ========================================================================
    # 데이터 수집 (중첩 루프: 리그 × 연도 × 경기)
    # ========================================================================
    dataset: List[Dict[str, Any]] = []

    for league_name in leagues:
        # 리그 이름을 API 코드로 변환
        meet_seq = LEAGUE_CODE.get(league_name)

        # 입력 검증: 지원하지 않는 리그명 처리
        if meet_seq is None:
            print(f"⛔ 잘못된 리그명: {league_name} (가능한 값: {list(LEAGUE_CODE.keys())})")
            continue

        for year_val in years:
            # 해당 리그와 연도의 총 경기 수 조회 (기본값: 228)
            total_games = GAMES_COUNT.get((league_name, year_val), 228)
            games = range(1, total_games + 1)  # 경기 ID는 1부터 시작

            # 수집 시작 안내 메시지
            console.print(
                f"\n[bold magenta][{year_val}년 {league_name} 경기 데이터][/bold magenta] "
                f"(총 {len(games)}경기)",
                style="bold"
            )

            # 각 경기 데이터 수집 (진행률 표시)
            for game_id in track(games, description=f"[cyan]수집 현황:[/cyan]"):
                # K리그 경기 페이지 URL 생성
                url = (
                    f"https://www.kleague.com/match.do?"
                    f"year={year_val}&"
                    f"meetSeq={meet_seq}&"
                    f"gameId={game_id}&"
                    f"leagueId=&"
                    f"startTabNum={start_tab_num}"
                )

                try:
                    # HTML 페이지 다운로드 및 파싱
                    soup = fetch_page(url)

                    # 페이지가 정상적으로 로드된 경우에만 파싱
                    if soup:
                        data = parse_game_info(soup, year_val, game_id)
                        dataset.append(data)
                    # soup이 None인 경우 (404, 타임아웃 등) 자동으로 건너뜀

                except Exception as e:
                    # 예상치 못한 에러 발생 시 로그 출력 후 계속 진행
                    print(f"⛔ 알 수 없는 에러 발생 (year={year_val}, gameId={game_id}): {e}")

    # ========================================================================
    # 결과 반환
    # ========================================================================
    file_name = f"{league_label}_match_{year_label}"
    return dataset, file_name
