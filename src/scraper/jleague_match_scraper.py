"""J리그 경기 데이터 스크래퍼 (JLeague Match Data Scraper)

이 모듈은 J리그 공식 웹사이트(www.jleague.jp)에서 경기 정보를 자동으로 수집합니다.

아키텍처 개요:
    ┌──────────────────┐
    │  URL 수집 단계   │  Step 1: 월별 경기 목록 URL 수집
    │  (월별 순회)     │         - 1~12월 경기 리스트 크롤링
    └────────┬─────────┘         - 경기 상세 페이지 URL 추출
             │
             ↓
    ┌──────────────────┐
    │  데이터 추출 단계 │  Step 2: 개별 경기 페이지 스크래핑
    │  (경기별 순회)   │         - 메타데이터 (라운드, 날짜, 팀명)
    └────────┬─────────┘         - 경기장 정보 (관중, 날씨)
             │                   - 트래킹 데이터 (주행거리, 스프린트)
             ↓
    ┌──────────────────┐
    │  데이터 정제 단계 │  Step 3: 데이터 타입 변환 및 검증
    │  (파싱 및 변환)  │         - 문자열 → 숫자 변환
    └────────┬─────────┘         - 날씨 정보 한글 번역
             │                   - 날짜 포맷 정규화
             ↓
    ┌──────────────────┐
    │  통합 데이터셋    │  Step 4: 최종 데이터 반환
    │  (리스트 반환)   │         - Dict[str, Any] 리스트
    └──────────────────┘

수집 데이터 스키마:
    - 경기 메타데이터: Meet_Year, LEAGUE_NAME, Round, Game_Datetime, Day
    - 팀 정보: HomeTeam, AwayTeam
    - 경기장 정보: Audience_Qty, Weather, Temperature, Humidity
    - 트래킹 데이터: HomeDistance, AwayDistance, HomeSprint, AwaySprint

성능 특성:
    - 순차 모드: 안정적, 메모리 효율적 (단일 WebDriver 재사용)
    - 병렬 모드: 4~8배 고속 수집 (멀티스레딩, 독립 WebDriver)

주요 의존성:
    - Selenium: 동적 JavaScript 페이지 렌더링 및 상호작용
    - Rich: 콘솔 진행률 시각화 및 사용자 피드백
    - BeautifulSoup: HTML 파싱 (scraper 모듈 내부에서 사용)

사용 예시:
    >>> from src.scraper.jleague_match_scraper import collect_jleague_match_data
    >>>
    >>> # 단일 시즌 수집 (병렬 모드)
    >>> data, filename = collect_jleague_match_data(
    ...     year=2025,
    ...     league="J리그1",
    ...     parallel=True,
    ...     max_workers=4
    ... )
    >>> print(f"수집 경기 수: {len(data)}, 파일명: {filename}")
    수집 경기 수: 306, 파일명: j1_match_2025
    >>>
    >>> # 여러 시즌, 여러 리그 수집
    >>> data, filename = collect_jleague_match_data(
    ...     year=[2023, 2024, 2025],
    ...     league=["J리그1", "J리그2"]
    ... )
    >>> print(f"총 수집 경기: {len(data)}")
    총 수집 경기: 1836

작성자: Jaebin Kim
작성일: 2026-01-26
"""
from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Any, Callable, Dict, Final, List, NamedTuple, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, track
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    SessionNotCreatedException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .scraper import setup_chrome_driver


# ============================================================================
# 로깅 설정 (Logging Configuration)
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# 시스템 설정 상수 (System Configuration Constants)
# ============================================================================


class TimeoutConfig:
    """Selenium WebDriver 대기 시간 설정 (단위: 초)

    각 작업별 타임아웃은 네트워크 지연과 페이지 렌더링 시간을 고려하여 설정됨.
    타임아웃 초과 시 TimeoutException 발생.
    """
    MATCH_DETAIL_PAGE: Final[int] = 10  # 경기 상세 페이지 로딩
    MATCH_LIST_PAGE: Final[int] = 5      # 월별 경기 목록 페이지 로딩
    TRACKING_TAB: Final[int] = 3         # 트래킹 데이터 탭 활성화


class ElementCount:
    """HTML 요소 개수 관련 상수

    데이터 무결성 검증을 위한 예상 요소 개수 정의.
    """
    TABLE_CELL_PAIR: Final[int] = 2                # 테이블 (레이블, 값) 쌍
    TRACKING_DATA_FULL: Final[int] = 4             # 완전한 트래킹 데이터 (주행거리 2 + 스프린트 2)
    TRACKING_DATA_PARTIAL: Final[int] = 2          # 부분 트래킹 데이터 (주행거리만)
    WEATHER_FIELDS: Final[int] = 3                 # 날씨 필드 (날씨, 온도, 습도)
    MIN_TEAM_ELEMENTS: Final[int] = 2              # 최소 팀 요소 (홈, 어웨이)


class URLConfig:
    """J리그 웹사이트 URL 템플릿"""
    BASE_URL: Final[str] = "https://www.jleague.jp"
    MATCH_SEARCH: Final[str] = f"{BASE_URL}/match/search/?category[]={{league}}&year={{year}}&month={{month}}"


# ============================================================================
# 리그 카테고리 열거형 (League Category Enum)
# ============================================================================


class LeagueCategory(Enum):
    """J리그 카테고리 및 URL 파라미터 매핑

    각 Enum 값은 (한글명, URL_카테고리_코드) 튜플로 구성됨.
    """
    J1 = ("J리그1", "j1")
    J2 = ("J리그2", "j2")
    J3 = ("J리그3", "j3")
    J1_PLAYOFF = ("J리그1PO", "playoff")
    J2_PLAYOFF = ("J리그2PO", "2playoff")

    @property
    def display_name(self) -> str:
        """사용자에게 표시할 한글 리그명"""
        return self.value[0]

    @property
    def url_category(self) -> str:
        """URL 쿼리 파라미터에 사용할 리그 코드"""
        return self.value[1]

    @classmethod
    def from_display_name(cls, name: str) -> 'LeagueCategory':
        """한글 리그명으로 Enum 인스턴스 검색

        Args:
            name: 한글 리그명 (예: "J리그1")

        Returns:
            LeagueCategory: 해당하는 Enum 인스턴스

        Raises:
            ValueError: 존재하지 않는 리그명
        """
        for league in cls:
            if league.display_name == name:
                return league
        raise ValueError(f"지원하지 않는 리그: {name}")


# ============================================================================
# 데이터 필드 매핑 (Data Field Mapping)
# ============================================================================


class JapaneseFieldNames:
    """J리그 웹사이트 일본어 필드명 상수"""
    ATTENDANCE: Final[str] = "入場者数"              # 관중 수
    WEATHER_INFO: Final[str] = "天候 / 気温 / 湿度"  # 날씨 / 온도 / 습도


# 일본어 필드명 → 영어 키 변환 테이블
TARGET_FIELDS: Final[Dict[str, str]] = {
    JapaneseFieldNames.ATTENDANCE: "Attendance",
    JapaneseFieldNames.WEATHER_INFO: "Weather_Info",
}


# ============================================================================
# 번역 매핑 테이블 (Translation Mappings)
# ============================================================================

# 일본어 날씨 표현 → 한글 번역
WEATHER_TRANSLATION: Final[Dict[str, str]] = {
    # 기본 날씨
    "晴": "맑음",
    "曇": "흐림",
    "雨": "비",
    "雪": "눈",
    "霧": "안개",
    "屋内": "실내",

    # 복합 날씨 패턴: 晴 (맑음)
    "晴一時雨": "맑다가 일시 비",
    "晴一時曇": "맑다가 일시 흐림",
    "晴時々曇": "맑음 때때로 흐림",
    "晴のち雨のち曇": "맑음 후 비 후 흐림",
    "晴のち雨": "맑음 후 비",
    "晴のち曇時々雨": "맑음 후 흐림 때때로 비",
    "晴のち曇": "맑음 후 흐림",

    # 복합 날씨 패턴: 雨 (비)
    "雨一時曇": "비 일시 흐림",
    "雨時々曇": "비 때때로 흐림",
    "雨のち曇時々雨": "비 후 흐림 때때로 비",
    "雨のち曇のち雨": "비 후 흐림 후 비",
    "雨のち曇": "비 후 흐림",

    # 복합 날씨 패턴: 曇 (흐림)
    "曇一時晴": "흐림 일시 맑음",
    "曇一時雨のち晴": "흐림 일시 비 후 맑음",
    "曇一時雨": "흐림 일시 비",
    "曇一時雷雨": "흐림 일시 뇌우",
    "曇時々晴時々雪": "흐림 때때로 맑음 때때로 눈",
    "曇時々晴": "흐림 때때로 맑음",
    "曇時々雨": "흐림 때때로 비",
    "曇のち晴": "흐림 후 맑음",
    "曇のち雨のち曇": "흐림 후 비 후 흐림",
    "曇のち雨": "흐림 후 비",
    "曇のち雷雨のち雨": "흐림 후 뇌우 후 비",
}

# 일본어 요일 → 한글 변환
DAY_TRANSLATION: Final[Dict[str, str]] = {
    '月': '월',  # Monday
    '火': '화',  # Tuesday
    '水': '수',  # Wednesday
    '木': '목',  # Thursday
    '金': '금',  # Friday
    '土': '토',  # Saturday
    '日': '일',  # Sunday
}


# ============================================================================
# 웹 요소 선택자 (Web Element Selectors)
# ============================================================================


class CSSSelectors:
    """CSS 선택자 패턴 모음"""
    MATCH_LIST_CONTAINER: Final[str] = "section.matchlistWrap"
    MATCH_LINK: Final[str] = "section.matchlistWrap td.match a[href*='/live/']"


class XPathSelectors:
    """XPath 선택자 패턴 모음"""
    STADIUM_TABLE: Final[str] = "//td[contains(text(), 'スタジアム')]/ancestor::table"
    TRACKING_TAB_LINK: Final[str] = "//a[contains(@href, '#trackingdata')]"


class CSSClassNames:
    """CSS 클래스명 상수"""
    LIVE_TOP_TABLE: Final[str] = "liveTopTable"
    MATCH_VS_TITLE_LEAGUE: Final[str] = "matchVsTitle__league"
    MATCH_VS_TITLE_DATE: Final[str] = "matchVsTitle__date"
    LEAGUE_ACC_TEAM_CLUB_NAME: Final[str] = "leagAccTeam__clubName"
    TOTAL_KM: Final[str] = "total_km"


# ============================================================================
# 정규표현식 패턴 (Regex Patterns)
# ============================================================================


class RegexPatterns:
    """정규표현식 패턴 모음"""
    # 라운드 번호 추출: "第10節" → 10
    ROUND: Final[str] = r'第(\d+)節'

    # 날짜/시간 파싱: "2025年3月15日(土) 14:00" → (year, month, day, 요일, hour, minute)
    DATETIME: Final[str] = r'(\d{4})[年/.-](\d{1,2})[月/.-](\d{1,2}).*?([月火水木金土日]).*?(\d{1,2}):(\d{2})'


# ============================================================================
# 데이터 구조 (Data Structures)
# ============================================================================


class WeatherData(NamedTuple):
    """파싱된 날씨 데이터 구조"""
    weather: str      # 날씨 (한글)
    temperature: str  # 온도 (℃)
    humidity: str     # 습도 (%)


class MatchDataKeys:
    """최종 경기 데이터 딕셔너리의 키 상수"""
    MEET_YEAR = "Meet_Year"           # 시즌 연도
    LEAGUE_NAME = "LEAGUE_NAME"       # 리그명
    ROUND = "Round"                   # 라운드 번호
    GAME_DATETIME = "Game_Datetime"   # 경기 일시
    DAY = "Day"                       # 요일
    HOME_TEAM = "HomeTeam"            # 홈팀명
    AWAY_TEAM = "AwayTeam"            # 어웨이팀명
    HOME_DISTANCE = "HomeDistance"    # 홈팀 주행거리
    AWAY_DISTANCE = "AwayDistance"    # 어웨이팀 주행거리
    HOME_SPRINT = "HomeSprint"        # 홈팀 스프린트 횟수
    AWAY_SPRINT = "AwaySprint"        # 어웨이팀 스프린트 횟수
    AUDIENCE_QTY = "Audience_Qty"     # 관중 수
    WEATHER = "Weather"               # 날씨
    TEMPERATURE = "Temperature"       # 온도
    HUMIDITY = "Humidity"             # 습도


# ============================================================================
# 유틸리티 함수 (Utility Functions)
# ============================================================================


def safe_extract(
    extraction_func: Callable[[], Dict[str, Any]],
    error_context: str
) -> Dict[str, Any]:
    """예외를 안전하게 처리하며 데이터를 추출하는 래퍼 함수

    데이터 파이프라인의 견고성을 위해 예외 발생 시에도 프로세스가 중단되지 않도록
    에러를 캡처하고 빈 딕셔너리를 반환합니다.

    Args:
        extraction_func: 데이터 추출 콜백 함수 (반환 타입: Dict[str, Any])
        error_context: 로그 메시지에 포함할 컨텍스트 정보

    Returns:
        추출된 데이터 딕셔너리 (실패 시 빈 딕셔너리)

    Example:
        >>> def extract_data():
        ...     return {"value": 100}
        >>> result = safe_extract(extract_data, "테스트 데이터 추출")
        >>> print(result)
        {'value': 100}
    """
    try:
        return extraction_func()
    except Exception as e:
        logger.warning(f"{error_context} 실패: {type(e).__name__} - {e}")
        return {}


def clean_attendance_data(raw_attendance: str) -> int:
    """관중 수 원본 데이터를 정수로 변환

    데이터 정제 파이프라인:
        1. 천 단위 구분자(,) 제거
        2. 일본어 단위('人') 제거
        3. 공백 제거 및 숫자 검증
        4. 정수형 변환

    Args:
        raw_attendance: 원본 관중 수 문자열 (예: "10,000人", "45,123人")

    Returns:
        정제된 관중 수 (양의 정수, 실패 시 0)

    Example:
        >>> clean_attendance_data("10,000人")
        10000
        >>> clean_attendance_data("Invalid")
        0
    """
    if not raw_attendance:
        return 0

    # 특수문자 및 단위 제거
    cleaned = raw_attendance.replace(",", "").replace("人", "").strip()

    # 숫자 검증 및 변환
    if cleaned.isdigit():
        return int(cleaned)

    logger.warning(f"유효하지 않은 관중 수 데이터: '{raw_attendance}'")
    return 0


def parse_weather_info(weather_info: str) -> Dict[str, str]:
    """복합 날씨 정보 문자열을 개별 필드로 파싱

    입력 형식: "날씨 / 온도℃ / 습도%"
    출력 형식: {"Weather": "맑음", "Temperature": "25", "Humidity": "60"}

    Args:
        weather_info: 슬래시(/)로 구분된 날씨 정보 문자열

    Returns:
        파싱된 날씨 데이터 딕셔너리 (실패 시 빈 딕셔너리)

    Example:
        >>> parse_weather_info("晴 / 25℃ / 60%")
        {'Weather': '맑음', 'Temperature': '25', 'Humidity': '60'}
    """
    if not weather_info:
        return {}

    # 슬래시 기준 분리
    parts = [part.strip() for part in weather_info.split("/")]

    # 데이터 무결성 검증
    if len(parts) < ElementCount.WEATHER_FIELDS:
        logger.warning(
            f"날씨 정보 필드 부족: '{weather_info}' "
            f"(예상: {ElementCount.WEATHER_FIELDS}개, 실제: {len(parts)}개)"
        )
        return {}

    # 각 필드에서 단위 제거
    weather_raw = parts[0]
    temperature = parts[1].replace("℃", "").strip()
    humidity = parts[2].replace("%", "").strip()

    # 날씨를 한국어로 번역 (매핑 없으면 원본 유지)
    weather_korean = WEATHER_TRANSLATION.get(weather_raw, weather_raw)
    if weather_korean == weather_raw and weather_raw not in WEATHER_TRANSLATION.values():
        logger.info(f"번역되지 않은 날씨 표현: '{weather_raw}'")

    return {
        "Weather": weather_korean,
        "Temperature": temperature,
        "Humidity": humidity
    }


# ============================================================================
# 데이터 추출 함수 (Data Extraction Functions)
# ============================================================================


def extract_table_data(driver: webdriver.Chrome) -> Dict[str, Any]:
    """경기 상세 페이지의 스타디움 정보 테이블 추출

    HTML 구조:
        <table>
            <tr>
                <td>スタジアム</td><td>경기장명</td>
                <td>入場者数</td><td>10,000人</td>
            </tr>
            <tr>
                <td>天候 / 気温 / 湿度</td><td>晴 / 25℃ / 60%</td>
            </tr>
        </table>

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        추출된 경기 데이터 (예: {"Attendance": "10,000人", "Weather_Info": "晴 / 25℃ / 60%"})

    Raises:
        NoSuchElementException: 스타디움 테이블이 존재하지 않는 경우
    """
    # 스타디움 정보 테이블 검색
    table = driver.find_element(By.XPATH, XPathSelectors.STADIUM_TABLE)
    cells = table.find_elements(By.TAG_NAME, "td")

    data = {}

    # 테이블 셀을 (레이블, 값) 쌍으로 순회
    for i in range(0, len(cells), ElementCount.TABLE_CELL_PAIR):
        if i + 1 >= len(cells):
            logger.debug(f"테이블 셀 개수가 홀수: {len(cells)}개")
            break

        label = cells[i].text.strip()
        value = cells[i + 1].text.strip()

        # TARGET_FIELDS에 정의된 필드만 추출
        if label in TARGET_FIELDS:
            data[TARGET_FIELDS[label]] = value
            logger.debug(f"필드 추출 성공: {label} = {value}")

    return data


def process_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """추출된 원본 데이터를 분석 가능한 형태로 변환

    데이터 변환 파이프라인:
        1. 관중 수: "10,000人" → 10000 (int)
        2. 날씨 정보: "晴 / 25℃ / 60%" → 개별 필드로 분해

    Args:
        data: 원본 데이터 딕셔너리

    Returns:
        정제 및 타입 변환된 데이터 딕셔너리

    Note:
        원본 딕셔너리를 in-place로 수정합니다.
    """
    # 관중 수 변환: 문자열 → 정수
    if "Attendance" in data:
        data["Attendance"] = clean_attendance_data(data["Attendance"])

    # 날씨 정보 분해: 복합 문자열 → 개별 필드
    if "Weather_Info" in data:
        weather_data = parse_weather_info(data.pop("Weather_Info"))
        if weather_data:
            data.update(weather_data)
        else:
            logger.warning("날씨 정보 파싱 실패")

    return data


def extract_round_info(driver: webdriver.Chrome) -> Dict[str, Optional[int]]:
    """경기 라운드 정보 추출

    예시:
        - "明治安田J1リーグ 第10節" → {"Round": 10}
        - "J1리그 第25節" → {"Round": 25}
        - "YBCルヴァンカップ 準決勝" → {"Round": None} (패턴 없음)

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        라운드 정보 딕셔너리 ({"Round": 번호 또는 None})
    """
    def _extract():
        league_element = driver.find_element(By.CLASS_NAME, CSSClassNames.MATCH_VS_TITLE_LEAGUE)
        league_text = league_element.text.strip()

        # 정규표현식으로 라운드 번호 추출
        round_match = re.search(RegexPatterns.ROUND, league_text)
        if round_match:
            round_num = int(round_match.group(1))
            logger.debug(f"라운드 추출 성공: {league_text} → {round_num}")
            return {"Round": round_num}

        logger.info(f"라운드 패턴 없음: {league_text}")
        return {"Round": None}

    return safe_extract(_extract, "라운드 정보 추출")


def extract_datetime_info(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """경기 날짜, 시간, 요일 정보 추출 및 ISO 8601 형식 변환

    지원 입력 형식:
        - "2025年3月15日(土) 14:00"
        - "2025/03/15(土)14:00"
        - "2025.3.15 (토) 2:30"

    출력 형식:
        {"Datetime": "2025-03-15 14:00:00", "Day": "토"}

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        날짜/시간/요일 정보 딕셔너리 (실패 시 모든 값 None)
    """
    def _extract():
        date_element = driver.find_element(By.CLASS_NAME, CSSClassNames.MATCH_VS_TITLE_DATE)
        raw_date_text = date_element.text.strip()

        # 정규표현식으로 날짜/시간 파싱
        match = re.search(RegexPatterns.DATETIME, raw_date_text)
        if not match:
            logger.warning(f"날짜 형식 파싱 실패: '{raw_date_text}'")
            return {"Datetime": None, "Day": None}

        year, month, day, day_char, hour, minute = match.groups()

        # 요일 한글 변환
        korean_day = DAY_TRANSLATION.get(day_char, day_char)

        # ISO 8601 형식 생성 (제로패딩 적용)
        formatted_datetime = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}:00"

        logger.debug(f"날짜 추출 성공: {raw_date_text} → {formatted_datetime} ({korean_day})")
        return {"Datetime": formatted_datetime, "Day": korean_day}

    return safe_extract(_extract, "날짜 정보 추출")


def extract_team_names(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """홈팀 및 어웨이팀 이름 추출

    HTML 구조:
        <div class="leagAccTeam__clubName">
            <span>浦和レッズ</span>  <!-- 홈팀 -->
        </div>
        <div class="leagAccTeam__clubName">
            <span>鹿島アントラーズ</span>  <!-- 어웨이팀 -->
        </div>

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        팀명 딕셔너리 ({"HomeTeam": 홈팀명, "AwayTeam": 어웨이팀명})
    """
    def _extract():
        team_elements = driver.find_elements(By.CLASS_NAME, CSSClassNames.LEAGUE_ACC_TEAM_CLUB_NAME)

        # 데이터 무결성 검증
        if len(team_elements) < ElementCount.MIN_TEAM_ELEMENTS:
            logger.warning(
                f"팀명 요소 부족: {len(team_elements)}개 "
                f"(필요: {ElementCount.MIN_TEAM_ELEMENTS}개)"
            )
            return {"HomeTeam": None, "AwayTeam": None}

        # 각 요소에서 <span> 태그의 텍스트 추출
        home_team = team_elements[0].find_element(By.TAG_NAME, "span").text.strip()
        away_team = team_elements[1].find_element(By.TAG_NAME, "span").text.strip()

        logger.debug(f"팀명 추출 성공: {home_team} vs {away_team}")
        return {"HomeTeam": home_team, "AwayTeam": away_team}

    return safe_extract(_extract, "팀명 추출")


def activate_tracking_tab(driver: webdriver.Chrome) -> None:
    """트래킹 데이터 탭 활성화

    JavaScript 클릭을 통해 강제로 탭을 활성화하고,
    "total_km" 요소가 나타날 때까지 대기합니다.

    Args:
        driver: Selenium WebDriver 인스턴스

    Note:
        - 트래킹 탭이 없는 경기도 존재 (과거 경기, 데이터 미제공)
        - 예외 발생 시 무시하여 전체 프로세스 중단 방지
    """
    try:
        tracking_tab = driver.find_element(By.XPATH, XPathSelectors.TRACKING_TAB_LINK)
        driver.execute_script("arguments[0].click();", tracking_tab)

        # 탭 내용 로드 대기
        WebDriverWait(driver, TimeoutConfig.TRACKING_TAB).until(
            EC.presence_of_element_located((By.CLASS_NAME, CSSClassNames.TOTAL_KM))
        )
        logger.debug("트래킹 탭 활성화 성공")

    except TimeoutException:
        logger.debug("트래킹 데이터 로딩 시간 초과")
    except NoSuchElementException:
        logger.debug("트래킹 탭 없음")
    except Exception as e:
        logger.debug(f"트래킹 탭 활성화 예외: {type(e).__name__}")


def extract_tracking_data(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """선수 트래킹 데이터 추출 (주행거리, 스프린트)

    HTML 구조:
        <td class="total_km">115.2 <span>km</span></td>  <!-- 홈팀 주행거리 -->
        <td class="total_km">112.8 <span>km</span></td>  <!-- 어웨이팀 주행거리 -->
        <td class="total_km">45 <span>回</span></td>     <!-- 홈팀 스프린트 -->
        <td class="total_km">38 <span>回</span></td>     <!-- 어웨이팀 스프린트 -->

    데이터 추출 로직:
        - 4개 이상: 주행거리 + 스프린트 (완전한 데이터)
        - 2~3개: 주행거리만 (스프린트는 None)
        - 2개 미만: 모든 값 None

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        트래킹 데이터 딕셔너리
        {
            "HomeDistance": "115.2",
            "AwayDistance": "112.8",
            "HomeSprint": "45",
            "AwaySprint": "38"
        }
    """
    def _extract():
        stat_elements = driver.find_elements(By.CLASS_NAME, CSSClassNames.TOTAL_KM)

        # 기본 구조 초기화
        result = {
            "HomeDistance": None,
            "AwayDistance": None,
            "HomeSprint": None,
            "AwaySprint": None
        }

        # Case 1: 완전한 트래킹 데이터 (주행거리 + 스프린트)
        if len(stat_elements) >= ElementCount.TRACKING_DATA_FULL:
            result["HomeDistance"] = stat_elements[0].text.lower().replace("km", "").strip()
            result["AwayDistance"] = stat_elements[1].text.lower().replace("km", "").strip()
            result["HomeSprint"] = stat_elements[2].text.replace("回", "").strip()
            result["AwaySprint"] = stat_elements[3].text.replace("回", "").strip()

            logger.debug(
                f"완전한 트래킹 데이터: "
                f"주행거리({result['HomeDistance']} vs {result['AwayDistance']}km), "
                f"스프린트({result['HomeSprint']} vs {result['AwaySprint']}회)"
            )

        # Case 2: 부분 데이터 (주행거리만)
        elif len(stat_elements) >= ElementCount.TRACKING_DATA_PARTIAL:
            result["HomeDistance"] = stat_elements[0].text.lower().replace("km", "").strip()
            result["AwayDistance"] = stat_elements[1].text.lower().replace("km", "").strip()

            logger.info(
                f"부분 트래킹 데이터: "
                f"주행거리({result['HomeDistance']} vs {result['AwayDistance']}km), "
                f"스프린트 없음"
            )

        # Case 3: 트래킹 데이터 없음
        else:
            logger.debug(f"트래킹 데이터 없음 (요소 {len(stat_elements)}개)")

        return result

    return safe_extract(_extract, "트래킹 데이터 추출")


# ============================================================================
# URL 수집 함수 (URL Collection Functions)
# ============================================================================


def _collect_monthly_match_urls(
    driver: webdriver.Chrome,
    league_category: str,
    year: int,
    month: int
) -> List[str]:
    """특정 월의 모든 경기 URL 수집

    Args:
        driver: Selenium WebDriver 인스턴스
        league_category: 리그 카테고리 코드 (j1, j2, j3, playoff, 2playoff)
        year: 시즌 연도
        month: 월 (1~12)

    Returns:
        경기 상세 페이지 URL 리스트 (경기 없으면 빈 리스트)

    Note:
        URL만 사전 추출하여 StaleElementReferenceException 방지
    """
    url = URLConfig.MATCH_SEARCH.format(league=league_category, year=year, month=month)
    driver.get(url)

    try:
        # 경기 목록 컨테이너 로딩 대기
        WebDriverWait(driver, TimeoutConfig.MATCH_LIST_PAGE).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CSSSelectors.MATCH_LIST_CONTAINER))
        )

        # 모든 경기 링크 추출
        match_link_elements = driver.find_elements(By.CSS_SELECTOR, CSSSelectors.MATCH_LINK)
        match_urls = [
            link.get_attribute("href")
            for link in match_link_elements
            if link.get_attribute("href")
        ]

        logger.debug(f"{year}년 {month}월: {len(match_urls)}경기 URL 수집")
        return match_urls

    except TimeoutException:
        logger.debug(f"{year}년 {month}월: 페이지 로딩 시간 초과")
        return []
    except Exception as e:
        logger.warning(f"{year}년 {month}월: URL 수집 실패 - {type(e).__name__}")
        return []


# ============================================================================
# 경기 데이터 수집 함수 (Match Data Collection Functions)
# ============================================================================


def _scrape_single_match_with_driver(
    driver: webdriver.Chrome,
    url: str,
    year: int,
    league_name: str,
    include_tracking: bool = True
) -> Optional[Dict[str, Any]]:
    """기존 WebDriver를 재사용하여 단일 경기 데이터 수집

    데이터 수집 파이프라인:
        1. 페이지 로드 및 대기
        2. 스타디움 테이블에서 관중/날씨 추출
        3. 데이터 정제 (타입 변환, 파싱)
        4. 메타데이터 추출 (라운드, 날짜, 팀명)
        5. 트래킹 데이터 추출 (주행거리, 스프린트) - 선택적
        6. 모든 데이터를 하나의 딕셔너리로 통합

    Args:
        driver: 재사용할 WebDriver 인스턴스
        url: 경기 상세 페이지 URL
        year: 시즌 연도
        league_name: 리그명
        include_tracking: 트래킹 데이터 포함 여부 (기본: True)

    Returns:
        통합 경기 데이터 딕셔너리 (실패 시 None)
    """
    try:
        driver.get(url)

        # Step 1: 페이지 로딩 대기
        try:
            WebDriverWait(driver, TimeoutConfig.MATCH_DETAIL_PAGE).until(
                EC.presence_of_element_located((By.CLASS_NAME, CSSClassNames.LIVE_TOP_TABLE))
            )
        except TimeoutException:
            logger.warning(f"페이지 로딩 시간 초과: {url}")
            return None

        # Step 2: 기본 테이블 데이터 추출
        try:
            data = extract_table_data(driver)
        except NoSuchElementException:
            logger.error(f"스타디움 테이블 없음: {url}")
            return None

        # Step 3: 데이터 정제
        processed_data = process_extracted_data(data)

        # Step 4: 메타데이터 추출 및 병합
        processed_data.update(extract_round_info(driver))
        processed_data.update(extract_datetime_info(driver))
        processed_data.update(extract_team_names(driver))

        # Step 5: 트래킹 데이터 추출 (선택적)
        if include_tracking:
            activate_tracking_tab(driver)
            processed_data.update(extract_tracking_data(driver))

        # Step 6: 최종 데이터 구조 생성
        final_data = {
            MatchDataKeys.MEET_YEAR: year,
            MatchDataKeys.LEAGUE_NAME: league_name,
            MatchDataKeys.ROUND: processed_data.get("Round"),
            MatchDataKeys.GAME_DATETIME: processed_data.get("Datetime"),
            MatchDataKeys.DAY: processed_data.get("Day"),
            MatchDataKeys.HOME_TEAM: processed_data.get("HomeTeam"),
            MatchDataKeys.AWAY_TEAM: processed_data.get("AwayTeam"),
            MatchDataKeys.AUDIENCE_QTY: processed_data.get("Attendance"),
            MatchDataKeys.WEATHER: processed_data.get("Weather"),
            MatchDataKeys.TEMPERATURE: processed_data.get("Temperature"),
            MatchDataKeys.HUMIDITY: processed_data.get("Humidity")
        }

        # 트래킹 데이터는 include_tracking=True일 때만 추가
        if include_tracking:
            final_data.update({
                MatchDataKeys.HOME_DISTANCE: processed_data.get("HomeDistance"),
                MatchDataKeys.AWAY_DISTANCE: processed_data.get("AwayDistance"),
                MatchDataKeys.HOME_SPRINT: processed_data.get("HomeSprint"),
                MatchDataKeys.AWAY_SPRINT: processed_data.get("AwaySprint")
            })

        logger.debug(
            f"경기 수집 완료: {final_data.get('HomeTeam')} vs {final_data.get('AwayTeam')}"
        )
        return final_data

    except Exception as e:
        logger.error(f"경기 수집 예외: {type(e).__name__} - {e}")
        return None


def scrape_single_match(
    url: str,
    year: int,
    league_name: str,
    include_tracking: bool = True
) -> Optional[Dict[str, Any]]:
    """단일 경기 데이터 수집 (독립 WebDriver 사용)

    독립적인 WebDriver 인스턴스를 생성하여 하나의 경기만 수집합니다.
    (하위 호환성 유지용 래퍼 함수)

    Args:
        url: 경기 상세 페이지 URL
        year: 시즌 연도
        league_name: 리그명
        include_tracking: 트래킹 데이터 포함 여부

    Returns:
        통합 경기 데이터 딕셔너리 (실패 시 None)

    Note:
        WebDriver는 함수 종료 시 자동 종료됨.
        대량 수집 시 scrape_season_matches() 권장.
    """
    driver = setup_chrome_driver()
    try:
        return _scrape_single_match_with_driver(driver, url, year, league_name, include_tracking)
    finally:
        driver.quit()


def scrape_monthly_matches(
    driver: webdriver.Chrome,
    league_category: str,
    year: int,
    month: int,
    league_display_name: str,
    include_tracking: bool = True
) -> List[Dict[str, Any]]:
    """특정 월의 모든 경기 데이터 수집

    작업 흐름:
        1. 월별 경기 목록 페이지에서 URL 수집
        2. 각 URL에 대해 데이터 추출
        3. 수집된 데이터를 리스트로 반환

    Args:
        driver: 재사용 가능한 WebDriver 인스턴스
        league_category: 리그 카테고리 코드
        year: 시즌 연도
        month: 월 (1~12)
        league_display_name: 사용자용 리그명
        include_tracking: 트래킹 데이터 포함 여부

    Returns:
        해당 월의 모든 경기 데이터 리스트
    """
    match_urls = _collect_monthly_match_urls(driver, league_category, year, month)

    if not match_urls:
        return []

    monthly_data = []
    for match_url in track(match_urls, description=f"[cyan]{month}월 경기 수집:[/cyan]"):
        match_data = scrape_single_match(match_url, year, league_display_name, include_tracking)
        if match_data:
            monthly_data.append(match_data)

    return monthly_data


def scrape_season_matches(
    league_category: str,
    year: int,
    league_display_name: str,
    include_tracking: bool = True
) -> List[Dict[str, Any]]:
    """전체 시즌(1~12월) 경기 데이터 순차 수집

    2단계 수집 전략:
        [1단계] URL 수집: 1~12월 모든 경기 URL 수집
        [2단계] 데이터 수집: 수집된 URL로부터 상세 데이터 추출

    장점:
        - 총 경기 수 사전 파악 가능
        - 단일 진행률 바로 전체 진행 상황 표시

    Args:
        league_category: 리그 카테고리 코드
        year: 시즌 연도
        league_display_name: 사용자용 리그명
        include_tracking: 트래킹 데이터 포함 여부

    Returns:
        시즌 전체 경기 데이터 리스트
    """
    driver = setup_chrome_driver(optimized=True)
    season_data = []

    try:
        # [1단계] 전체 시즌 URL 수집
        all_match_urls = []
        for month in range(1, 13):
            month_urls = _collect_monthly_match_urls(driver, league_category, year, month)
            all_match_urls.extend(month_urls)

        # 수집 시작 안내
        console = Console()
        console.print(
            f"\n[bold magenta][{year}년 {league_display_name} 경기 데이터][/bold magenta] "
            f"(총 {len(all_match_urls)}경기)",
            style="bold"
        )

        # [2단계] 경기 상세 데이터 수집 (드라이버 재사용)
        for match_url in track(all_match_urls, description=f"[cyan]수집 현황:[/cyan]"):
            match_data = _scrape_single_match_with_driver(
                driver, match_url, year, league_display_name, include_tracking
            )
            if match_data:
                season_data.append(match_data)

    finally:
        driver.quit()

    return season_data


# ============================================================================
# 병렬 처리 함수 (Parallel Processing Functions)
# ============================================================================


def _scrape_match_worker(
    args: Tuple[str, int, str, bool],
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """병렬 처리용 워커 함수 (재시도 로직 포함)

    각 스레드에서 독립적으로 WebDriver를 생성하여 경기 데이터를 수집합니다.

    Args:
        args: (match_url, year, league_display_name, include_tracking) 튜플
        max_retries: ChromeDriver 생성 실패 시 최대 재시도 횟수

    Returns:
        수집된 경기 데이터 또는 None

    Note:
        각 워커는 독립적인 WebDriver 인스턴스 사용.
        ChromeDriver 생성 실패 시 최대 3회 재시도.
    """
    match_url, year, league_display_name, include_tracking = args

    for attempt in range(max_retries):
        driver = None
        try:
            driver = setup_chrome_driver(optimized=True)
            result = _scrape_single_match_with_driver(
                driver, match_url, year, league_display_name, include_tracking
            )
            return result
        except SessionNotCreatedException as e:
            logger.warning(f"ChromeDriver 생성 실패 (시도 {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                raise
        finally:
            if driver:
                driver.quit()

    return None


def scrape_season_matches_parallel(
    league_category: str,
    year: int,
    league_display_name: str,
    max_workers: int = 4,
    include_tracking: bool = True
) -> List[Dict[str, Any]]:
    """전체 시즌(1~12월) 경기 데이터 병렬 수집

    3단계 수집 전략:
        [1단계] URL 수집: 1~12월 모든 경기 URL 수집
        [2단계] 병렬 수집: 여러 스레드로 동시 수집
        [3단계] 재수집: 실패한 경기 재시도

    Args:
        league_category: 리그 카테고리 코드
        year: 시즌 연도
        league_display_name: 사용자용 리그명
        max_workers: 동시 실행 스레드 수 (권장: 4~6)
        include_tracking: 트래킹 데이터 포함 여부

    Returns:
        시즌 전체 경기 데이터 리스트

    Note:
        순차 모드 대비 4~8배 빠른 속도.
        각 스레드가 독립 WebDriver 사용.
    """
    # [1단계] URL 수집
    driver = setup_chrome_driver(optimized=True)
    try:
        all_match_urls = []
        for month in range(1, 13):
            month_urls = _collect_monthly_match_urls(driver, league_category, year, month)
            all_match_urls.extend(month_urls)
    finally:
        driver.quit()

    # [2단계] 병렬 수집
    console = Console()
    console.print(
        f"\n[bold magenta][{year}년 {league_display_name} 경기 데이터][/bold magenta] "
        f"(총 {len(all_match_urls)}경기)",
        style="bold"
    )

    task_args = [(url, year, league_display_name, include_tracking) for url in all_match_urls]
    season_data = []
    failed_tasks = []

    with Progress() as progress:
        task = progress.add_task("[cyan]수집 현황:[/cyan]", total=len(task_args))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_args = {
                executor.submit(_scrape_match_worker, args): args
                for args in task_args
            }

            for future in as_completed(future_to_args):
                args = future_to_args[future]
                try:
                    match_data = future.result()
                    if match_data:
                        season_data.append(match_data)
                    else:
                        failed_tasks.append(args)
                        logger.warning(f"데이터 수집 실패 (재시도 예정): {args[0]}")
                except Exception as e:
                    failed_tasks.append(args)
                    logger.error(f"워커 예외 (재시도 예정): {type(e).__name__} - {e}")

                progress.update(task, advance=1)

    # [3단계] 실패 경기 재수집
    if failed_tasks:
        console.print(
            f"\n[bold yellow]실패한 {len(failed_tasks)}경기 재수집 시작...[/bold yellow]"
        )

        retry_data = []
        for args in track(failed_tasks, description=f"[yellow]재수집 현황:[/yellow]"):
            match_url, year_val, league_name, include_tracking_flag = args
            match_data = scrape_single_match(match_url, year_val, league_name, include_tracking_flag)
            if match_data:
                retry_data.append(match_data)
                logger.info(f"재수집 성공: {match_url}")
            else:
                logger.error(f"재수집 실패: {match_url}")

        season_data.extend(retry_data)
        console.print(
            f"[bold green]재수집 완료: {len(retry_data)}/{len(failed_tasks)}건 성공[/bold green]"
        )

    return season_data


# ============================================================================
# 공개 API 함수 (Public API Function)
# ============================================================================


def collect_jleague_match_data(
    year: int | List[int],
    league: str | List[str] = "J리그1",
    parallel: bool = True,
    max_workers: int = 4
) -> Tuple[List[Dict[str, Any]], str]:
    """J리그 경기 데이터 수집 (최상위 공개 API)

    사용 예시:
        # 단일 연도, 단일 리그
        >>> data, filename = collect_jleague_match_data(2025, "J리그1")
        >>> print(filename)
        'j1_match_2025'

        # 여러 연도, 여러 리그
        >>> data, filename = collect_jleague_match_data(
        ...     year=[2023, 2025],
        ...     league=["J리그1", "J리그2"]
        ... )
        >>> print(filename)
        'jleague_match_2023-2025'

        # 병렬 처리로 빠르게 수집
        >>> data, filename = collect_jleague_match_data(
        ...     year=2024,
        ...     league="J리그1",
        ...     parallel=True,
        ...     max_workers=4
        ... )

    Args:
        year: 수집 시즌 연도
            - int: 단일 연도 (예: 2025)
            - List[int]: 연도 범위 (예: [2023, 2025] → 2023, 2024, 2025)
        league: 수집 리그 (기본값: "J리그1")
            - str: 단일 리그
            - List[str]: 여러 리그 (예: ["J리그1", "J리그2"])
            - 지원: "J리그1", "J리그2", "J리그3", "J리그1PO", "J리그2PO"
        parallel: 병렬 처리 사용 여부 (기본값: True)
        max_workers: 병렬 스레드 수 (기본값: 4, 권장: 2~8)

    Returns:
        Tuple[List[Dict[str, Any]], str]:
            - 수집된 경기 데이터 리스트
            - 파일 저장용 파일명 (확장자 제외)

    Raises:
        ValueError: 지원하지 않는 리그명

    Note:
        - 개별 시즌 수집 실패 시 로깅 후 계속 진행
        - parallel=True 사용 시 웹사이트 부하 주의
        - J리그1만 수집 시 트래킹 데이터 포함
    """
    # 리그 이름 → URL 카테고리 매핑
    LEAGUE_TO_CATEGORY: Final[Dict[str, str]] = {
        "J리그1": "j1",
        "J리그2": "j2",
        "J리그3": "j3",
        "J리그1PO": "playoff",
        "J리그2PO": "2playoff"
    }

    # 입력 파라미터 정규화
    league_list: List[str] = [league] if isinstance(league, str) else list(league)

    # 리그 검증
    for league_name in league_list:
        if league_name not in LEAGUE_TO_CATEGORY:
            raise ValueError(
                f"지원하지 않는 리그: '{league_name}'\n"
                f"지원 리그: {list(LEAGUE_TO_CATEGORY.keys())}"
            )

    # 연도 파라미터 정규화
    if isinstance(year, int):
        years: List[int] = [year]
        year_label: str = str(year)
    else:
        years = list(range(min(year), max(year) + 1))
        year_label = f"{min(year)}-{max(year)}"

    # 파일명 생성
    if len(league_list) == 1:
        league_label: str = LEAGUE_TO_CATEGORY[league_list[0]]
    elif set(league_list) == {"J리그1", "J리그2", "J리그3"}:
        league_label = "jleague"
    else:
        league_numbers = []
        for league_name in sorted(league_list, key=lambda x: league_list.index(x)):
            if league_name == "J리그1":
                league_numbers.append("1")
            elif league_name == "J리그2":
                league_numbers.append("2")
            elif league_name == "J리그3":
                league_numbers.append("3")
            elif league_name == "J리그1PO":
                league_numbers.append("1po")
            elif league_name == "J리그2PO":
                league_numbers.append("2po")
        league_label = "jleague" + ",".join(league_numbers)

    # 트래킹 데이터 포함 여부 (J리그1만 수집 시)
    include_tracking = (league_list == ["J리그1"])

    # 데이터 수집 (리그 × 연도)
    dataset: List[Dict[str, Any]] = []

    for league_name in league_list:
        league_category = LEAGUE_TO_CATEGORY[league_name]

        for year_val in years:
            try:
                if parallel:
                    season_data = scrape_season_matches_parallel(
                        league_category,
                        year_val,
                        league_name,
                        max_workers,
                        include_tracking
                    )
                else:
                    season_data = scrape_season_matches(
                        league_category,
                        year_val,
                        league_name,
                        include_tracking
                    )
                dataset.extend(season_data)

            except Exception as e:
                logger.error(
                    f"{year_val}년 {league_name} 수집 실패: {type(e).__name__} - {e}"
                )

    # 결과 반환
    file_name = f"{league_label}_match_{year_label}"
    logger.info(f"데이터 수집 완료: {len(dataset)}경기, 파일명: {file_name}")
    return dataset, file_name
