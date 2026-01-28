"""K리그 경기 데이터 스크래퍼 (KLeague Match Data Scraper)

이 모듈은 K리그 공식 웹사이트(www.kleague.com)에서 경기 정보를 자동으로 수집합니다.

아키텍처 개요:
    ┌──────────────────┐
    │  URL 생성 단계   │  Step 1: 경기 ID 기반 URL 생성
    │  (ID 순회)       │         - 1번부터 N번까지 순차 생성
    └────────┬─────────┘         - 시즌별 경기 수 기반
             │
             ↓
    ┌──────────────────┐
    │  HTML 다운로드    │  Step 2: HTTP 요청 및 페이지 파싱
    │  (HTTP GET)      │         - BeautifulSoup HTML 파싱
    └────────┬─────────┘         - 404/타임아웃 처리
             │
             ↓
    ┌──────────────────┐
    │  데이터 추출 단계 │  Step 3: CSS Selector 기반 추출
    │  (파싱)          │         - 메타데이터 (리그, 라운드, 날짜)
    └────────┬─────────┘         - 팀 정보 (이름, 순위)
             │                   - 경기장 정보 (관중, 날씨)
             ↓
    ┌──────────────────┐
    │  데이터 정제 단계 │  Step 4: 데이터 타입 변환 및 검증
    │  (변환)          │         - 날짜 포맷 정규화
    └────────┬─────────┘         - 관중 수 정수 변환
             │                   - 순위 정보 추출
             ↓
    ┌──────────────────┐
    │  통합 데이터셋    │  Step 5: 최종 데이터 반환
    │  (리스트 반환)   │         - Dict[str, Any] 리스트
    └──────────────────┘

수집 데이터 스키마:
    - 경기 메타데이터: Meet_Year, LEAGUE_NAME, Round, Game_id, Game_Datetime, Day
    - 팀 정보: HomeTeam, AwayTeam, HomeRank, AwayRank
    - 경기장 정보: Field_Name, Audience_Qty, Weather, Temperature, Humidity

성능 특성:
    - 순차 처리: 경기 ID 기반 단순 순회
    - BeautifulSoup 파싱: 가볍고 빠른 정적 HTML 처리
    - 메모리 효율: 스트리밍 방식, 경기당 독립 처리

주요 의존성:
    - BeautifulSoup4: HTML 파싱 및 CSS Selector 기반 추출
    - Rich: 콘솔 진행률 시각화 및 사용자 피드백
    - Requests: HTTP 요청 (scraper.fetch_page 내부)

사용 예시:
    >>> from src.scraper.kleague_match_scraper import collect_kleague_match_data
    >>>
    >>> # 단일 시즌 수집
    >>> data, filename = collect_kleague_match_data(
    ...     year=2025,
    ...     league="K리그1"
    ... )
    >>> print(f"수집 경기 수: {len(data)}, 파일명: {filename}")
    수집 경기 수: 228, 파일명: kleague1_match_2025
    >>>
    >>> # 여러 시즌, 여러 리그 수집
    >>> data, filename = collect_kleague_match_data(
    ...     year=[2023, 2024, 2025],
    ...     league=["K리그1", "K리그2"]
    ... )
    >>> print(f"총 수집 경기: {len(data)}")
    총 수집 경기: 1392

작성자: Jaebin Kim
작성일: 2026-01-26
"""
from __future__ import annotations

import re
from typing import Any, Dict, Final, List, Tuple

from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import track

from .scraper import fetch_page


# ============================================================================
# 시스템 설정 상수 (System Configuration Constants)
# ============================================================================


class URLConfig:
    """K리그 웹사이트 URL 템플릿"""
    BASE_URL: Final[str] = "https://www.kleague.com"
    MATCH_DETAIL: Final[str] = (
        f"{BASE_URL}/match.do?"
        "year={year}&"
        "meetSeq={meet_seq}&"
        "gameId={game_id}&"
        "leagueId=&"
        "startTabNum={start_tab_num}"
    )


class LeagueCode:
    """K리그 API 파라미터 코드 매핑"""
    K_LEAGUE_1: Final[int] = 1      # K리그1 (1부 리그)
    K_LEAGUE_2: Final[int] = 2      # K리그2 (2부 리그)
    PLAYOFF: Final[int] = 3         # 승강 플레이오프
    SUPER_CUP: Final[int] = 4       # 슈퍼컵


class DefaultConfig:
    """기본 설정 값"""
    START_TAB_NUM: Final[int] = 3   # K리그 웹사이트 URL 파라미터 (고정값)


# ============================================================================
# 데이터 필드 매핑 (Data Field Mapping)
# ============================================================================


class MatchDataKeys:
    """최종 경기 데이터 딕셔너리의 키 상수"""
    MEET_YEAR = "Meet_Year"           # 시즌 연도
    LEAGUE_NAME = "LEAGUE_NAME"       # 리그명
    ROUND = "Round"                   # 라운드
    GAME_ID = "Game_id"               # 경기 ID
    GAME_DATETIME = "Game_Datetime"   # 경기 일시
    DAY = "Day"                       # 요일
    HOME_TEAM = "HomeTeam"            # 홈팀명
    AWAY_TEAM = "AwayTeam"            # 어웨이팀명
    HOME_RANK = "HomeRank"            # 홈팀 순위
    AWAY_RANK = "AwayRank"            # 어웨이팀 순위
    HOME_POINTS = "HomePoints"        # 홈팀 승점
    AWAY_POINTS = "AwayPoints"        # 어웨이팀 승점
    FIELD_NAME = "Field_Name"         # 경기장명
    AUDIENCE_QTY = "Audience_Qty"     # 관중 수
    WEATHER = "Weather"               # 날씨
    TEMPERATURE = "Temperature"       # 온도
    HUMIDITY = "Humidity"             # 습도


# ============================================================================
# 시즌별 경기 수 데이터 (Season Match Count Data)
# ============================================================================

# (리그명, 연도) → 총 경기 수 매핑
# K리그는 경기 ID가 1부터 순차 할당되므로 총 경기 수를 알아야 함
SEASON_MATCH_COUNT: Final[Dict[Tuple[str, int], int]] = {
    # K리그1: 12팀 기준 228경기
    ("K리그1", 2015): 228,
    ("K리그1", 2016): 228,
    ("K리그1", 2017): 228,
    ("K리그1", 2018): 228,
    ("K리그1", 2019): 228,
    ("K리그1", 2020): 162,
    ("K리그1", 2021): 228,
    ("K리그1", 2022): 228,
    ("K리그1", 2023): 228,
    ("K리그1", 2024): 228,
    ("K리그1", 2025): 228,

    # K리그2: 팀 수 변동에 따라 경기 수 다름
    ("K리그2", 2015): 222,
    ("K리그2", 2016): 222,
    ("K리그2", 2017): 182,
    ("K리그2", 2018): 182,
    ("K리그2", 2019): 182,
    ("K리그2", 2020): 137,
    ("K리그2", 2021): 182,
    ("K리그2", 2022): 222,
    ("K리그2", 2023): 236,
    ("K리그2", 2024): 236,
    ("K리그2", 2025): 275,  # 2025년부터 팀 수 증가

    # 승강 플레이오프: 고정 4경기
    ("승강PO", 2023): 4,
    ("승강PO", 2024): 4,
    ("승강PO", 2025): 4,
}

# 리그명 → API 코드 변환 테이블
LEAGUE_NAME_TO_CODE: Final[Dict[str, int]] = {
    "K리그1": LeagueCode.K_LEAGUE_1,
    "K리그2": LeagueCode.K_LEAGUE_2,
    "승강PO": LeagueCode.PLAYOFF,
    "슈퍼컵": LeagueCode.SUPER_CUP,
}


# ============================================================================
# CSS 선택자 (CSS Selectors)
# ============================================================================


class CSSSelectors:
    """BeautifulSoup CSS 선택자 패턴"""
    # 리그 및 라운드 정보
    LEAGUE_NAME: Final[str] = "#meetSeq option[selected]"
    ROUND: Final[str] = "#roundId option[selected]"

    # 경기 일시
    MATCH_DATETIME: Final[str] = "div.versus p"

    # 팀 정보
    TEAM_INFO: Final[str] = "#gameId option[selected]"
    TEAM_RANK: Final[str] = "#tab03 ul.compare > li"
    TEAM_RANK_SPANS: Final[str] = "span.font-red"

    # 경기장 및 환경 정보
    STADIUM_INFO: Final[str] = "ul.game-sub-info.sort-box li"


# ============================================================================
# 유틸리티 함수 (Utility Functions)
# ============================================================================


def extract_value(text: str, remove_char: str = "") -> str:
    """레이블-값 형식의 문자열에서 값을 추출하고 정제

    K리그 웹사이트는 "항목 : 값" 형식으로 정보를 제공합니다.
    이 함수는 콜론 뒤의 값을 추출하고 불필요한 단위를 제거합니다.

    처리 파이프라인:
        1. 콜론(:) 기준 문자열 분리
        2. 마지막 부분(값) 선택
        3. 지정된 문자(단위) 제거
        4. 앞뒤 공백 제거

    Args:
        text: '항목 : 값' 형태의 원본 문자열
            예: "관중수 : 10,519", "온도 : 25°C"
        remove_char: 값에서 제거할 단위 문자
            예: "%", "°C", ","

    Returns:
        정제된 값 문자열

    Example:
        >>> extract_value("관중수 : 10,519", ",")
        '10519'
        >>> extract_value("온도 : 25°C", "°C")
        '25'
        >>> extract_value("습도 : 60%", "%")
        '60'
    """
    # 콜론 기준 분리 후 마지막 값 선택
    value = text.split(':')[-1]

    # 지정된 문자 제거
    if remove_char:
        value = value.replace(remove_char, '')

    # 앞뒤 공백 제거
    return value.strip()


def calculate_points_from_record(text: str) -> int:
    """'0승 0무 0패' 텍스트에서 승점을 계산 (승*3 + 무*1)
    
    Args:
        text: 전적 정보가 포함된 원본 텍스트 (예: "3위 2승 1무 0패")
        
    Returns:
        int: 계산된 승점
    """
    # 정규표현식으로 숫자 추출: (\d+)승, (\d+)무
    match = re.search(r'(\d+)승\s*(\d+)무\s*(\d+)패', text)
    
    if match:
        wins = int(match.group(1))
        draws = int(match.group(2))
        # losses = int(match.group(3)) # 패배는 승점에 영향 없음
        
        return (wins * 3) + (draws * 1)
            
    return 0  # 패턴을 찾지 못한 경우 0점 반환


# ============================================================================
# 데이터 파싱 함수 (Data Parsing Functions)
# ============================================================================


def parse_game_info(soup: BeautifulSoup, year: int, game_id: int) -> Dict[str, Any]:
    """BeautifulSoup 객체에서 K리그 경기 정보를 파싱

    HTML 구조 기반 데이터 추출:
        - 리그/라운드: <select> 태그의 선택된 <option>
        - 경기 일시: <div class="versus"> 내부 <p> 태그
        - 팀 정보: <select id="gameId"> 선택된 <option>
        - 순위 정보: <ul class="compare"> 내부 <span class="font-red">
        - 경기장/날씨: <ul class="game-sub-info"> 내부 <li> 리스트

    데이터 추출 전략:
        1. 기본 구조 초기화 (모든 필드 기본값 설정)
        2. CSS Selector로 각 요소 탐색
        3. 요소 존재 여부 검증
        4. 텍스트 정제 및 타입 변환
        5. 누락 데이터 처리

    Args:
        soup: BeautifulSoup으로 파싱된 HTML 객체
        year: 시즌 연도 (예: 2025)
        game_id: K리그 경기 ID (1부터 시작)

    Returns:
        추출된 경기 정보 딕셔너리 (필드 누락 시 해당 값은 None)

    Example:
        >>> from bs4 import BeautifulSoup
        >>> html = fetch_page(url)
        >>> data = parse_game_info(html, 2025, 1)
        >>> print(data['HomeTeam'], 'vs', data['AwayTeam'])
        울산 vs 포항
    """
    # ========================================================================
    # 데이터 구조 초기화
    # ========================================================================
    data: Dict[str, Any] = {
        MatchDataKeys.MEET_YEAR: year,
        MatchDataKeys.LEAGUE_NAME: None,
        MatchDataKeys.ROUND: None,
        MatchDataKeys.GAME_ID: game_id,
        MatchDataKeys.GAME_DATETIME: None,
        MatchDataKeys.DAY: None,
        MatchDataKeys.HOME_TEAM: None,
        MatchDataKeys.AWAY_TEAM: None,
        MatchDataKeys.HOME_RANK: 0,
        MatchDataKeys.AWAY_RANK: 0,
        MatchDataKeys.HOME_POINTS: 0,
        MatchDataKeys.AWAY_POINTS: 0,
        MatchDataKeys.FIELD_NAME: None,
        MatchDataKeys.AUDIENCE_QTY: None,
        MatchDataKeys.WEATHER: None,
        MatchDataKeys.TEMPERATURE: None,
        MatchDataKeys.HUMIDITY: None,
    }

    # ========================================================================
    # 리그명 추출
    # ========================================================================
    tag = soup.select_one(CSSSelectors.LEAGUE_NAME)
    if tag:
        data[MatchDataKeys.LEAGUE_NAME] = tag.text.strip()
    else:
        print("❌ 리그명 정보를 찾을 수 없습니다.")

    # ========================================================================
    # 라운드 추출
    # ========================================================================
    tag = soup.select_one(CSSSelectors.ROUND)
    if tag:
        data[MatchDataKeys.ROUND] = tag.text.strip()
    else:
        print("❌ 라운드 정보를 찾을 수 없습니다.")

    # ========================================================================
    # 경기 일시 및 요일 추출
    # ========================================================================
    # 입력 형식: "2025/03/01 (토) 14:00"
    # 출력 형식: "2025-03-01 14:00:00" (ISO 8601)
    tag = soup.select_one(CSSSelectors.MATCH_DATETIME)
    if tag:
        parts = tag.text.split()

        # 날짜와 시간 조합 후 ISO 형식 변환
        # "2025/03/01 14:00" → "2025-03-01 14:00:00"
        data[MatchDataKeys.GAME_DATETIME] = f"{parts[0]} {parts[-1]}:00".replace("/", "-")

        # 요일 추출: "(토)" → "토"
        data[MatchDataKeys.DAY] = parts[1].strip("()")
    else:
        print("❌ 일시 정보를 찾을 수 없습니다.")

    # ========================================================================
    # 홈팀 vs 어웨이팀 추출
    # ========================================================================
    # 입력 형식: "울산vs포항 (14:00)"
    # 파싱: "울산vs포항" → ["울산", "포항"]
    tag = soup.select_one(CSSSelectors.TEAM_INFO)
    if tag:
        # 첫 번째 공백 전까지가 팀 정보 (시간 제거)
        teams = tag.text.split(' ')[0].strip()

        # "vs"로 분리
        if 'vs' in teams:
            data[MatchDataKeys.HOME_TEAM], data[MatchDataKeys.AWAY_TEAM] = teams.split('vs')
    else:
        print("❌ 팀 정보를 찾을 수 없습니다.")

    # ========================================================================
    # 팀 순위 및 승점 추출
    # ========================================================================
    tag = soup.select_one(CSSSelectors.TEAM_RANK)

    if tag:
        # 순위 텍스트를 가진 모든 span 찾기
        tags = tag.select(CSSSelectors.TEAM_RANK_SPANS)

        # 최소 2개의 순위 정보 필요
        if len(tags) >= 2:
            # 홈팀 순위: "1위" → "1" → 1
            home_rank = tags[0].text.replace("위", "").strip()
            if home_rank.isdigit():
                data[MatchDataKeys.HOME_RANK] = int(home_rank)

            # 어웨이팀 순위: "3위" → "3" → 3
            away_rank = tags[1].text.replace("위", "").strip()
            if away_rank.isdigit():
                data[MatchDataKeys.AWAY_RANK] = int(away_rank)

            # 홈팀 텍스트 추출 (첫 번째 순위 정보의 부모 텍스트)
            home_text = tags[0].parent.text
            data[MatchDataKeys.HOME_POINTS] = calculate_points_from_record(home_text)
            
            # 어웨이팀 텍스트 추출 (두 번째 순위 정보의 부모 텍스트)
            away_text = tags[1].parent.text
            data[MatchDataKeys.AWAY_POINTS] = calculate_points_from_record(away_text)
        
        else:
            # 순위 정보가 없는 경우 (시즌 초반 등) 0점 처리
            data[MatchDataKeys.HOME_POINTS] = 0
            data[MatchDataKeys.AWAY_POINTS] = 0

    # ========================================================================
    # 경기장 정보 및 환경 데이터 추출
    # ========================================================================
    tags = soup.select(CSSSelectors.STADIUM_INFO)

    for tag in tags:
        text = tag.text

        # 키워드 매칭으로 데이터 분류
        if "관중수" in text:
            data[MatchDataKeys.AUDIENCE_QTY] = extract_value(text, ',')
        elif "경기장" in text:
            data[MatchDataKeys.FIELD_NAME] = extract_value(text)
        elif "날씨" in text:
            data[MatchDataKeys.WEATHER] = extract_value(text)
        elif "온도" in text:
            data[MatchDataKeys.TEMPERATURE] = extract_value(text, '°C')
        elif "습도" in text:
            data[MatchDataKeys.HUMIDITY] = extract_value(text, '%')
        else:
            # 예상치 못한 정보 발견
            print(f"⚠️ 알 수 없는 정보: {tag.text}")

    return data


# ============================================================================
# 메인 수집 함수 (Main Collection Function)
# ============================================================================


def collect_kleague_match_data(
    year: int | List[int],
    league: str | List[str] = "K리그1"
) -> Tuple[List[Dict[str, Any]], str]:
    """K리그 경기 데이터 수집 (최상위 공개 API)

    경기 ID 기반 순차 접근 방식:
        - K리그는 각 시즌의 경기에 1부터 N까지 순차 ID 할당
        - URL 패턴: www.kleague.com/match.do?year={year}&meetSeq={league}&gameId={id}
        - BeautifulSoup으로 정적 HTML 파싱

    사용 예시:
        # 단일 연도, 단일 리그
        >>> data, filename = collect_kleague_match_data(2025, "K리그1")
        >>> print(filename)
        'kleague1_match_2025'
        >>> print(len(data))
        228

        # 여러 연도, 여러 리그
        >>> data, filename = collect_kleague_match_data(
        ...     year=[2023, 2025],
        ...     league=["K리그1", "K리그2"]
        ... )
        >>> print(filename)
        'kleague_match_2023-2025'

        # 승강 플레이오프만 수집
        >>> data, filename = collect_kleague_match_data(2024, "승강PO")
        >>> print(len(data))
        4

    Args:
        year: 수집 시즌 연도 (2013년 이후 지원)
            - int: 단일 연도 (예: 2025)
            - List[int]: 연도 범위 (예: [2023, 2025] → 2023, 2024, 2025)
        league: 수집 리그 (기본값: "K리그1")
            - str: 단일 리그
            - List[str]: 여러 리그 (예: ["K리그1", "K리그2"])
            - 지원 리그:
                * "K리그1": 하나원큐 K리그1 (1부 리그)
                * "K리그2": 하나원큐 K리그2 (2부 리그)
                * "승강PO": 승강 플레이오프
                * "슈퍼컵": FA컵 우승팀 vs K리그 우승팀

    Returns:
        Tuple[List[Dict[str, Any]], str]:
            - 수집된 경기 데이터 리스트
            - 파일 저장용 파일명 (확장자 제외)
                형식: "{리그}_match_{연도}"
                예: "kleague1_match_2025", "kleague_match_2023-2025"

    Raises:
        ValueError: 지원하지 않는 리그명 (암묵적, 경고 메시지 출력)

    Note:
        - 경기가 존재하지 않는 ID는 자동 건너뜀 (fetch_page가 None 반환)
        - fetch_page 실패 시 해당 경기는 dataset에 미포함
        - 수집 진행률은 Rich 라이브러리로 실시간 표시
        - J리그와 달리 트래킹 데이터 없음 (K리그 미제공)
    """
    # ========================================================================
    # 입력 파라미터 정규화
    # ========================================================================

    # 리그 파라미터를 리스트로 변환
    if isinstance(league, str):
        leagues: List[str] = [league]
        # 파일명용 레이블: "K리그1" → "kleague1"
        league_label: str = league.replace("K리그", "kleague")
    else:
        leagues = league
        # 여러 리그: 통합 레이블
        league_label = "kleague"

    # 연도 파라미터를 리스트로 변환 및 범위 확장
    if isinstance(year, int):
        years: List[int] = [year]
        year_label: str = str(year)
    else:
        # [2023, 2025] → [2023, 2024, 2025]
        years = list(range(min(year), max(year) + 1))
        year_label = f"{min(year)}-{max(year)}"

    # Rich 콘솔 초기화
    console = Console()

    # ========================================================================
    # 데이터 수집 (리그 × 연도 × 경기 ID)
    # ========================================================================
    dataset: List[Dict[str, Any]] = []

    for league_name in leagues:
        # 리그명 → API 코드 변환
        meet_seq = LEAGUE_NAME_TO_CODE.get(league_name)

        # 입력 검증: 지원하지 않는 리그명
        if meet_seq is None:
            print(
                f"⛔ 지원하지 않는 리그: {league_name}\n"
                f"   지원 리그: {list(LEAGUE_NAME_TO_CODE.keys())}"
            )
            continue

        for year_val in years:
            # 해당 리그와 연도의 총 경기 수 조회 (기본값: 228)
            total_games = SEASON_MATCH_COUNT.get((league_name, year_val), 228)
            games = range(1, total_games + 1)

            # 수집 시작 안내
            console.print(
                f"\n[bold magenta][{year_val}년 {league_name} 경기 데이터][/bold magenta] "
                f"(총 {len(games)}경기)",
                style="bold"
            )

            # 각 경기 데이터 수집 (진행률 표시)
            for game_id in track(games, description=f"[cyan]수집 현황:[/cyan]"):
                # K리그 경기 페이지 URL 생성
                url = URLConfig.MATCH_DETAIL.format(
                    year=year_val,
                    meet_seq=meet_seq,
                    game_id=game_id,
                    start_tab_num=DefaultConfig.START_TAB_NUM
                )

                try:
                    # HTML 페이지 다운로드 및 파싱
                    soup = fetch_page(url)

                    # 페이지가 정상 로드된 경우에만 파싱
                    if soup:
                        data = parse_game_info(soup, year_val, game_id)
                        dataset.append(data)
                    # soup이 None인 경우 (404, 타임아웃 등) 자동 건너뜀

                except Exception as e:
                    # 예상치 못한 에러 발생 시 로그 출력 후 계속
                    print(
                        f"⛔ 데이터 수집 실패 (year={year_val}, gameId={game_id}): "
                        f"{type(e).__name__} - {e}"
                    )

    # ========================================================================
    # 결과 반환
    # ========================================================================
    file_name = f"{league_label}_match_{year_label}"
    console.print(
        f"\n[bold green]✅ 수집 완료: {len(dataset)}경기, 파일명: {file_name}[/bold green]"
    )
    return dataset, file_name
