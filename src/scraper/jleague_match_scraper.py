"""J리그 경기 데이터 스크래퍼 (JLeague Match Data Scraper).

J리그 공식 웹사이트(www.jleague.jp)에서 경기 정보를 추출하는 웹 스크래핑 모듈입니다.

Architecture:
    ┌─────────────────┐
    │  월별 경기 목록   │ ─┐
    │   URL 수집      │  │ 1단계: URL 수집
    └─────────────────┘ ─┘
           ↓
    ┌─────────────────┐
    │  개별 경기 페이지 │ ─┐
    │  데이터 추출     │  │ 2단계: 데이터 추출
    └─────────────────┘  │ - 경기 메타데이터
           ↓             │ - 경기장 정보
    ┌─────────────────┐  │ - 트래킹 데이터
    │   데이터 정제    │  │
    │   타입 변환     │  │ 3단계: 데이터 정제
    └─────────────────┘ ─┘
           ↓
    ┌─────────────────┐
    │  통합 데이터셋   │
    └─────────────────┘

Data Schema:
    - 경기 메타데이터: 라운드, 날짜, 시간, 요일, 팀명
    - 경기장 정보: 관중 수, 날씨, 온도, 습도
    - 트래킹 데이터: 팀별 주행거리, 스프린트 횟수

Performance:
    - 순차 모드: 안정적, 리소스 효율적
    - 병렬 모드: 4~8배 빠른 수집 속도, 멀티스레딩 활용

Dependencies:
    - Selenium: 동적 웹 페이지 렌더링 및 데이터 추출
    - Rich: 진행률 표시 및 콘솔 출력 시각화
"""
from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Dict, Optional, Any, Callable, List, Tuple, Final, NamedTuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, SessionNotCreatedException

from rich.console import Console
from rich.progress import track, Progress

from .scraper import setup_chrome_driver


# ============================================================================
# 로깅 설정 (Logging Configuration)
# ============================================================================
logger = logging.getLogger(__name__)


# ============================================================================
# 상수 정의 (Configuration Constants)
# ============================================================================

class TimeoutConfig:
    """Selenium WebDriver 대기 시간 설정 (단위: 초).

    Attributes:
        MATCH_DETAIL_PAGE: 경기 상세 페이지 로딩 대기 시간
        MATCH_LIST_PAGE: 월별 경기 목록 페이지 로딩 대기 시간
        TRACKING_TAB: 트래킹 데이터 탭 활성화 대기 시간
    """
    MATCH_DETAIL_PAGE: Final[int] = 10
    MATCH_LIST_PAGE: Final[int] = 5
    TRACKING_TAB: Final[int] = 3


class ElementCount:
    """HTML 요소 개수 관련 상수.

    Attributes:
        TABLE_CELL_PAIR: 테이블 셀 레이블-값 쌍의 크기
        TRACKING_DATA_FULL: 완전한 트래킹 데이터 요소 개수 (주행거리 2개 + 스프린트 2개)
        TRACKING_DATA_PARTIAL: 부분 트래킹 데이터 요소 개수 (주행거리 2개만)
        WEATHER_FIELDS: 날씨 정보 필드 개수 (날씨/온도/습도)
        MIN_TEAM_ELEMENTS: 최소 필요 팀 요소 개수
    """
    TABLE_CELL_PAIR: Final[int] = 2
    TRACKING_DATA_FULL: Final[int] = 4
    TRACKING_DATA_PARTIAL: Final[int] = 2
    WEATHER_FIELDS: Final[int] = 3
    MIN_TEAM_ELEMENTS: Final[int] = 2

class LeagueCategory(Enum):
    """J리그 카테고리 URL 파라미터 매핑."""
    J1 = ("J리그1", "j1")
    J2 = ("J리그2", "j2")
    J3 = ("J리그3", "j3")
    J1_PLAYOFF = ("J리그1PO", "playoff")
    J2_PLAYOFF = ("J리그2PO", "2playoff")

    @property
    def display_name(self) -> str:
        """사용자에게 표시할 리그 이름."""
        return self.value[0]

    @property
    def url_category(self) -> str:
        """URL 쿼리 파라미터로 사용할 카테고리 코드."""
        return self.value[1]

    @classmethod
    def from_display_name(cls, name: str) -> 'LeagueCategory':
        """표시 이름으로 Enum 검색."""
        for league in cls:
            if league.display_name == name:
                return league
        raise ValueError(f"지원하지 않는 리그 이름: {name}")


# ----------------------------------------------------------------------------
# 데이터 필드 매핑 (Data Field Mapping)
# ----------------------------------------------------------------------------
class JapaneseFieldNames:
    """J리그 웹사이트의 일본어 필드명 상수."""
    ATTENDANCE: Final[str] = "入場者数"
    WEATHER_INFO: Final[str] = "天候 / 気温 / 湿度"


# J리그 웹사이트의 일본어 필드명을 영어 키로 변환
TARGET_FIELDS: Final[Dict[str, str]] = {
    JapaneseFieldNames.ATTENDANCE: "Attendance",
    JapaneseFieldNames.WEATHER_INFO: "Weather_Info",
}

# ----------------------------------------------------------------------------
# 번역 매핑 테이블 (Translation Mappings)
# ----------------------------------------------------------------------------
# 일본어 날씨 표현을 한국어로 번역
WEATHER_TRANSLATION: Final[Dict[str, str]] = {
    "晴": "맑음",
    "曇": "흐림",
    "雨": "비",
    "雪": "눈",
    "晴一時雨": "맑다가 일시 비",
    "晴一時曇": "맑다가 일시 흐림",
    "晴時々曇": "맑음 때때로 흐림",
    "晴のち雨のち曇": "맑음 후 비 후 흐림",
    "晴のち雨": "맑음 후 비",
    "晴のち曇時々雨": "맑음 후 흐림 때때로 비",
    "晴のち曇": "맑음 후 흐림",
    "雨一時曇": "비 일시 흐림",
    "雨時々曇": "비 때때로 흐림",
    "雨のち曇時々雨": "비 후 흐림 때때로 비",
    "雨のち曇のち雨": "비 후 흐림 후 비",
    "雨のち曇": "비 후 흐림",
    "屋内": "실내",
    "霧": "안개",
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
    "曇のち雷雨のち雨": "흐림 후 뇌우 후 비"
}

# 일본어 요일을 한국어로 변환
DAY_TRANSLATION: Final[Dict[str, str]] = {
    '月': '월',  # 월요일
    '火': '화',  # 화요일
    '水': '수',  # 수요일
    '木': '목',  # 목요일
    '金': '금',  # 금요일
    '土': '토',  # 토요일
    '日': '일'   # 일요일
}


# ----------------------------------------------------------------------------
# 웹 요소 선택자 (Web Element Selectors)
# ----------------------------------------------------------------------------
class CSSSelectors:
    """CSS 선택자 모음."""
    MATCH_LIST_CONTAINER: Final[str] = "section.matchlistWrap"
    MATCH_LINK: Final[str] = "section.matchlistWrap td.match a[href*='/live/']"


class XPathSelectors:
    """XPath 선택자 모음."""
    STADIUM_TABLE: Final[str] = "//td[contains(text(), 'スタジアム')]/ancestor::table"
    TRACKING_TAB_LINK: Final[str] = "//a[contains(@href, '#trackingdata')]"


class CSSClassNames:
    """CSS 클래스명 상수."""
    LIVE_TOP_TABLE: Final[str] = "liveTopTable"
    MATCH_VS_TITLE_LEAGUE: Final[str] = "matchVsTitle__league"
    MATCH_VS_TITLE_DATE: Final[str] = "matchVsTitle__date"
    LEAGUE_ACC_TEAM_CLUB_NAME: Final[str] = "leagAccTeam__clubName"
    TOTAL_KM: Final[str] = "total_km"


# ----------------------------------------------------------------------------
# 정규표현식 패턴 (Regex Patterns)
# ----------------------------------------------------------------------------
class RegexPatterns:
    """정규표현식 패턴 모음."""
    # 라운드 번호 추출: "第10節" → 10
    ROUND: Final[str] = r'第(\d+)節'

    # 날짜/시간 파싱: "2025年3月15日(土) 14:00" → (2025, 3, 15, 土, 14, 00)
    DATETIME: Final[str] = r'(\d{4})[年/.-](\d{1,2})[月/.-](\d{1,2}).*?([月火水木金土日]).*?(\d{1,2}):(\d{2})'


# ----------------------------------------------------------------------------
# API 엔드포인트 (API Endpoints)
# ----------------------------------------------------------------------------
# J리그 경기 검색 URL 템플릿
JLEAGUE_SEARCH_URL: Final[str] = "https://www.jleague.jp/match/search/?category[]={league}&year={year}&month={month}"


# ============================================================================
# 헬퍼 함수 (Helper Functions)
# ============================================================================

def safe_extract(
    extraction_func: Callable[[], Dict[str, Any]],
    error_context: str
) -> Dict[str, Any]:
    """안전하게 데이터를 추출하고 예외를 처리합니다.

    데이터 파이프라인의 견고성을 위해 예외 발생 시에도 프로세스가 중단되지 않도록
    에러를 캡처하고 빈 딕셔너리를 반환합니다.

    Args:
        extraction_func: 데이터를 추출하는 콜백 함수 (반환값: Dict[str, Any])
        error_context: 예외 발생 시 로그에 기록할 컨텍스트 정보

    Returns:
        Dict[str, Any]: 추출 성공 시 데이터 딕셔너리, 실패 시 빈 딕셔너리

    Example:
        >>> def extract_data():
        ...     return {"value": 100}
        >>> safe_extract(extract_data, "테스트 데이터 추출")
        {'value': 100}

    Note:
        - 모든 예외를 캡처하여 파이프라인의 중단을 방지
        - 예외 발생 시 로깅 후 빈 딕셔너리 반환
    """
    try:
        return extraction_func()
    except Exception as e:
        logger.warning(f"{error_context} 실패: {type(e).__name__} - {e}")
        return {}


def clean_attendance_data(raw_attendance: str) -> int:
    """관중 수 원본 데이터를 정제하여 정수형으로 변환합니다.

    데이터 정제 파이프라인:
        1. 천 단위 구분 쉼표(,) 제거
        2. 일본어 단위 문자 '人' 제거
        3. 공백 제거 및 숫자 검증
        4. 정수형으로 타입 변환

    Args:
        raw_attendance: 원본 관중 수 문자열
            예시: "10,000人", "45,123人", "32,456人"

    Returns:
        int: 정제된 관중 수 (양의 정수)
            변환 실패 시 0 반환

    Example:
        >>> clean_attendance_data("10,000人")
        10000
        >>> clean_attendance_data("45,123人")
        45123
        >>> clean_attendance_data("Invalid Data")
        0

    Note:
        - 음수 값은 허용하지 않음 (0 반환)
        - 빈 문자열이나 None은 0으로 처리
    """
    if not raw_attendance:
        return 0

    # 특수문자 및 일본어 단위 제거
    cleaned = raw_attendance.replace(",", "").replace("人", "").strip()

    # 숫자 검증 및 변환
    if cleaned.isdigit():
        return int(cleaned)

    logger.warning(f"유효하지 않은 관중 수 데이터: '{raw_attendance}'")
    return 0


class WeatherData(NamedTuple):
    """파싱된 날씨 데이터 구조."""
    weather: str
    temperature: str
    humidity: str


def parse_weather_info(weather_info: str) -> Dict[str, str]:
    """복합 날씨 정보 문자열을 개별 필드로 파싱합니다.

    입력 형식:
        "날씨 / 온도℃ / 습도%"
        예시: "晴 / 25℃ / 60%", "曇 / 18℃ / 75%"

    출력 구조:
        {
            "Weather": "맑음",      # 한글로 번역된 날씨
            "Temperature": "25",    # 숫자만 추출된 온도
            "Humidity": "60"        # 숫자만 추출된 습도
        }

    Args:
        weather_info: 슬래시(/)로 구분된 날씨 정보 문자열

    Returns:
        Dict[str, str]: 파싱된 날씨 데이터 딕셔너리
            형식이 잘못된 경우 빈 딕셔너리 반환

    Example:
        >>> parse_weather_info("晴 / 25℃ / 60%")
        {'Weather': '맑음', 'Temperature': '25', 'Humidity': '60'}
        >>> parse_weather_info("曇 / 18℃ / 75%")
        {'Weather': '흐림', 'Temperature': '18', 'Humidity': '75'}

    Note:
        - 번역 테이블에 없는 날씨 표현은 원문 유지
        - 필드 부족 시 빈 딕셔너리 반환 (데이터 무결성 보장)
    """
    if not weather_info:
        return {}

    # 슬래시 기준으로 분리
    parts = [part.strip() for part in weather_info.split("/")]

    # 데이터 무결성 검증: 3개 필드 필요
    if len(parts) < ElementCount.WEATHER_FIELDS:
        logger.warning(f"날씨 정보 필드 부족: '{weather_info}' (예상: 3개, 실제: {len(parts)}개)")
        return {}

    # 각 필드에서 단위 제거
    weather_raw = parts[0]
    temperature = parts[1].replace("℃", "").strip()
    humidity = parts[2].replace("%", "").strip()

    # 날씨를 한국어로 번역 (매핑에 없으면 원본 유지)
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
    """경기 상세 페이지에서 스타디움 정보 테이블을 추출합니다.

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

    추출 알고리즘:
        1. XPath로 스타디움 테이블 검색
        2. <td> 요소를 레이블-값 쌍으로 순회
        3. TARGET_FIELDS에 정의된 필드만 선택적 추출

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Any]: 추출된 경기 데이터
            예시: {
                "Attendance": "10,000人",
                "Weather_Info": "晴 / 25℃ / 60%"
            }

    Raises:
        NoSuchElementException: 스타디움 테이블이 페이지에 존재하지 않는 경우
    """
    # 스타디움 정보 테이블 검색
    table = driver.find_element(By.XPATH, XPathSelectors.STADIUM_TABLE)
    cells = table.find_elements(By.TAG_NAME, "td")

    data = {}

    # 테이블 셀을 레이블-값 쌍으로 순회 (2개씩 처리)
    for i in range(0, len(cells), ElementCount.TABLE_CELL_PAIR):
        # 홀수 개 셀인 경우 마지막 셀 무시
        if i + 1 >= len(cells):
            logger.debug(f"테이블 셀 개수가 홀수입니다: {len(cells)}개")
            break

        label = cells[i].text.strip()
        value = cells[i + 1].text.strip()

        # TARGET_FIELDS에 정의된 필드만 추출
        if label in TARGET_FIELDS:
            data[TARGET_FIELDS[label]] = value
            logger.debug(f"필드 추출: {label} = {value}")

    return data


def process_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """추출된 원본 데이터를 분석 가능한 형태로 정제 및 변환합니다.

    데이터 변환 파이프라인:
        1. 관중 수: "10,000人" → 10000 (int)
        2. 날씨 정보: "晴 / 25℃ / 60%" → 개별 필드로 분해

    변환 전:
        {
            "Attendance": "10,000人",
            "Weather_Info": "晴 / 25℃ / 60%"
        }

    변환 후:
        {
            "Attendance": 10000,
            "Weather": "맑음",
            "Temperature": "25",
            "Humidity": "60"
        }

    Args:
        data: 원본 데이터 딕셔너리 (문자열 형태)

    Returns:
        Dict[str, Any]: 정제 및 타입 변환된 데이터 딕셔너리

    Note:
        - in-place 연산으로 원본 딕셔너리 수정
        - Weather_Info 키는 개별 필드로 분해 후 제거됨
    """
    # 관중 수: 문자열 → 정수 변환
    if "Attendance" in data:
        data["Attendance"] = clean_attendance_data(data["Attendance"])

    # 날씨 정보: 복합 문자열 → 개별 필드로 분해
    if "Weather_Info" in data:
        weather_data = parse_weather_info(data.pop("Weather_Info"))
        if weather_data:
            data.update(weather_data)
        else:
            logger.warning("날씨 정보 파싱 실패")

    return data


def extract_round_info(driver: webdriver.Chrome) -> Dict[str, Optional[int]]:
    """경기 라운드(절차) 정보를 추출합니다.

    추출 위치:
        CSS 클래스 "matchVsTitle__league"에서 "第N節" 패턴 검색

    예시:
        - "明治安田J1リーグ 第10節" → {"Round": 10}
        - "YBCルヴァンカップ 準決勝" → {"Round": None}  # 패턴 없음
        - "J1리그 第25節" → {"Round": 25}

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Optional[int]]: {"Round": 라운드 번호 또는 None}

    Note:
        - 플레이오프나 컵 대회의 경우 라운드 정보가 없을 수 있음
        - 정규표현식 패턴 매칭 실패 시 None 반환
    """
    def _extract():
        # 리그 정보 요소에서 텍스트 추출
        league_element = driver.find_element(By.CLASS_NAME, CSSClassNames.MATCH_VS_TITLE_LEAGUE)
        league_text = league_element.text.strip()

        # 정규표현식으로 라운드 번호 추출 (第10節 → 10)
        round_match = re.search(RegexPatterns.ROUND, league_text)
        if round_match:
            round_num = int(round_match.group(1))
            logger.debug(f"라운드 정보 추출 성공: {league_text} → {round_num}")
            return {"Round": round_num}

        logger.info(f"라운드 패턴(第N節) 없음: {league_text}")
        return {"Round": None}

    return safe_extract(_extract, "라운드 정보 추출")


def extract_datetime_info(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """경기 날짜, 시간, 요일 정보를 추출하여 표준 형식으로 변환합니다.

    지원하는 입력 형식:
        - "2025年3月15日(土) 14:00"
        - "2025/03/15(土)14:00"
        - "2025.3.15 (토) 2:30"

    출력 형식:
        {
            "Datetime": "2025-03-15 14:00:00",  # ISO 8601 형식
            "Day": "토"                          # 한글 요일
        }

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Optional[str]]: 날짜/시간/요일 정보
            파싱 실패 시 모든 값이 None

    Note:
        - 정규표현식으로 다양한 날짜 구분자 지원 (年/月/日, /, ., -)
        - 월/일/시/분은 자동으로 2자리 제로패딩 (3 → 03)
    """
    def _extract():
        # 날짜 정보 요소에서 텍스트 추출
        date_element = driver.find_element(By.CLASS_NAME, CSSClassNames.MATCH_VS_TITLE_DATE)
        raw_date_text = date_element.text.strip()

        # 정규표현식으로 날짜/시간 파싱
        match = re.search(RegexPatterns.DATETIME, raw_date_text)
        if not match:
            logger.warning(f"날짜 형식 파싱 실패: '{raw_date_text}'")
            return {"Datetime": None, "Day": None}

        # 그룹 추출: (년, 월, 일, 요일, 시, 분)
        year, month, day, day_char, hour, minute = match.groups()

        # 요일을 한국어로 번역
        korean_day = DAY_TRANSLATION.get(day_char, day_char)

        # ISO 8601 형식으로 포맷팅 (제로패딩 적용)
        formatted_datetime = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}:00"

        logger.debug(f"날짜 정보 추출 성공: {raw_date_text} → {formatted_datetime} ({korean_day})")
        return {"Datetime": formatted_datetime, "Day": korean_day}

    return safe_extract(_extract, "날짜 정보 추출")


def extract_team_names(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """경기에 참여하는 홈팀과 어웨이팀의 이름을 추출합니다.

    HTML 구조:
        <div class="leagAccTeam__clubName">
            <span>浦和レッズ</span>  <!-- 홈팀 -->
        </div>
        <div class="leagAccTeam__clubName">
            <span>鹿島アントラーズ</span>  <!-- 어웨이팀 -->
        </div>

    추출 순서:
        1. "leagAccTeam__clubName" 클래스를 가진 모든 요소 검색
        2. 첫 번째 요소 = 홈팀, 두 번째 요소 = 어웨이팀
        3. 각 요소 내부의 <span> 태그에서 팀명 텍스트 추출

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Optional[str]]: {"HomeTeam": 홈팀명, "AwayTeam": 어웨이팀명}
            요소 부족 시 모든 값이 None

    Note:
        - 최소 2개의 팀명 요소 필요 (데이터 무결성 검증)
        - 요소 부족 시 경고 로그 출력 후 None 반환
    """
    def _extract():
        # 팀명 요소 검색
        team_elements = driver.find_elements(By.CLASS_NAME, CSSClassNames.LEAGUE_ACC_TEAM_CLUB_NAME)

        # 데이터 무결성 검증: 최소 2개의 팀 정보 필요
        if len(team_elements) < ElementCount.MIN_TEAM_ELEMENTS:
            logger.warning(f"팀명 요소 부족: {len(team_elements)}개 (필요: {ElementCount.MIN_TEAM_ELEMENTS}개)")
            return {"HomeTeam": None, "AwayTeam": None}

        # 각 요소에서 <span> 태그의 텍스트 추출
        home_team = team_elements[0].find_element(By.TAG_NAME, "span").text.strip()
        away_team = team_elements[1].find_element(By.TAG_NAME, "span").text.strip()

        logger.debug(f"팀명 추출 성공: {home_team} vs {away_team}")
        return {"HomeTeam": home_team, "AwayTeam": away_team}

    return safe_extract(_extract, "팀명 추출")


def activate_tracking_tab(driver: webdriver.Chrome) -> None:
    """트래킹 데이터 탭을 JavaScript 클릭으로 활성화합니다.

    동작 방식:
        1. XPath로 트래킹 탭 링크 검색
        2. JavaScript를 통한 강제 클릭 (visibility 무관)
        3. "total_km" 클래스 요소가 나타날 때까지 대기

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        None

    Note:
        - 트래킹 탭이 없는 경기 존재 가능 (예: 과거 경기, 데이터 미제공 경기)
        - 예외 발생 시 무시하여 전체 스크래핑 프로세스 중단 방지
        - 탭이 이미 활성화되어 있어도 안전하게 처리됨
    """
    try:
        # 트래킹 데이터 탭 검색
        tracking_tab = driver.find_element(By.XPATH, XPathSelectors.TRACKING_TAB_LINK)

        # JavaScript를 통한 클릭 (일반 click()보다 안정적)
        driver.execute_script("arguments[0].click();", tracking_tab)

        # 탭 내용 로드 대기
        WebDriverWait(driver, TimeoutConfig.TRACKING_TAB).until(
            EC.presence_of_element_located((By.CLASS_NAME, CSSClassNames.TOTAL_KM))
        )
        logger.debug("트래킹 데이터 탭 활성화 성공")

    except TimeoutException:
        logger.debug("트래킹 데이터 로딩 시간 초과 (탭은 활성화됨)")
    except NoSuchElementException:
        logger.debug("트래킹 데이터 탭 없음 (과거 경기 또는 데이터 미제공)")
    except Exception as e:
        logger.debug(f"트래킹 탭 활성화 예외: {type(e).__name__}")


def extract_tracking_data(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """선수들의 총 주행거리 및 스프린트 횟수를 추출합니다.

    HTML 구조:
        <td class="total_km" colspan="2">115.2 <span>km</span></td>  <!-- 홈팀 주행거리 -->
        <td class="total_km" colspan="2">112.8 <span>km</span></td>  <!-- 어웨이팀 주행거리 -->
        <td class="total_km" colspan="2">45 <span>回</span></td>     <!-- 홈팀 스프린트 -->
        <td class="total_km" colspan="2">38 <span>回</span></td>     <!-- 어웨이팀 스프린트 -->

    데이터 추출 로직 (요소 개수에 따라 분기):
        - 4개 이상: 주행거리 2개 + 스프린트 2개 (완전한 데이터)
        - 2~3개: 주행거리만 추출 (스프린트는 None)
        - 2개 미만: 모든 값 None 반환

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Optional[str]]: 트래킹 데이터 딕셔너리
            {
                "HomeDistance": "115.2",    # 홈팀 주행거리(km)
                "AwayDistance": "112.8",    # 어웨이팀 주행거리(km)
                "HomeSprint": "45",         # 홈팀 스프린트 횟수
                "AwaySprint": "38"          # 어웨이팀 스프린트 횟수
            }

    Note:
        - 과거 경기는 트래킹 데이터가 없을 수 있음
        - 단위(km, 回)는 제거하고 숫자만 반환
        - 부분 데이터도 허용하여 데이터 손실 최소화
    """
    def _extract():
        # "total_km" 클래스를 가진 모든 요소 검색
        stat_elements = driver.find_elements(By.CLASS_NAME, CSSClassNames.TOTAL_KM)

        # 기본 구조: 모든 값을 None으로 초기화
        result = {
            "HomeDistance": None,
            "AwayDistance": None,
            "HomeSprint": None,
            "AwaySprint": None
        }

        # Case 1: 완전한 트래킹 데이터 (주행거리 + 스프린트)
        if len(stat_elements) >= ElementCount.TRACKING_DATA_FULL:
            # 주행거리 추출 (인덱스 0, 1)
            result["HomeDistance"] = stat_elements[0].text.lower().replace("km", "").strip()
            result["AwayDistance"] = stat_elements[1].text.lower().replace("km", "").strip()

            # 스프린트 횟수 추출 (인덱스 2, 3)
            result["HomeSprint"] = stat_elements[2].text.replace("回", "").strip()
            result["AwaySprint"] = stat_elements[3].text.replace("回", "").strip()

            logger.debug(
                f"트래킹 데이터 추출 완료: 주행거리({result['HomeDistance']} vs {result['AwayDistance']}km), "
                f"스프린트({result['HomeSprint']} vs {result['AwaySprint']}회)"
            )

        # Case 2: 부분 데이터 (주행거리만)
        elif len(stat_elements) >= ElementCount.TRACKING_DATA_PARTIAL:
            result["HomeDistance"] = stat_elements[0].text.lower().replace("km", "").strip()
            result["AwayDistance"] = stat_elements[1].text.lower().replace("km", "").strip()

            logger.info(
                f"트래킹 데이터 부분 추출: 주행거리만 ({result['HomeDistance']} vs {result['AwayDistance']}km), "
                f"스프린트 데이터 없음"
            )

        # Case 3: 트래킹 데이터 없음
        else:
            logger.debug(f"트래킹 데이터 없음 (요소 {len(stat_elements)}개)")

        return result

    return safe_extract(_extract, "트래킹 데이터 추출")


# ============================================================================
# 메인 수집 함수 (Main Scraping Functions)
# ============================================================================

def _collect_monthly_match_urls(
    driver: webdriver.Chrome,
    league_category: str,
    year: int,
    month: int
) -> List[str]:
    """특정 월의 모든 경기 URL을 수집합니다.

    Args:
        driver: Selenium WebDriver 인스턴스
        league_category: 리그 카테고리 코드 (j1, j2, j3, playoff, 2playoff)
        year: 시즌 연도
        month: 월 (1~12)

    Returns:
        List[str]: 경기 상세 페이지 URL 리스트
            경기가 없거나 로딩 실패 시 빈 리스트 반환

    Note:
        - URL만 수집하여 StaleElementReferenceException 방지
        - 페이지 로드 실패 시 빈 리스트 반환
    """
    # 월별 경기 목록 URL 생성
    url = JLEAGUE_SEARCH_URL.format(league=league_category, year=year, month=month)
    driver.get(url)

    try:
        # 경기 목록 컨테이너 로딩 대기
        WebDriverWait(driver, TimeoutConfig.MATCH_LIST_PAGE).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CSSSelectors.MATCH_LIST_CONTAINER))
        )

        # 모든 경기 링크 요소 검색
        match_link_elements = driver.find_elements(By.CSS_SELECTOR, CSSSelectors.MATCH_LINK)

        # URL 사전 추출 (StaleElementReferenceException 방지)
        match_urls = [
            link.get_attribute("href")
            for link in match_link_elements
            if link.get_attribute("href")
        ]

        logger.debug(f"{year}년 {month}월: {len(match_urls)}경기 URL 수집 완료")
        return match_urls

    except TimeoutException:
        logger.debug(f"{year}년 {month}월: 페이지 로딩 시간 초과 (경기 없음)")
        return []
    except Exception as e:
        logger.warning(f"{year}년 {month}월: URL 수집 실패 - {type(e).__name__}")
        return []


class MatchDataKeys:
    """최종 경기 데이터 딕셔너리의 키 상수."""
    MEET_YEAR = "Meet_Year"
    LEAGUE_NAME = "LEAGUE_NAME"
    ROUND = "Round"
    GAME_DATETIME = "Game_Datetime"
    DAY = "Day"
    HOME_TEAM = "HomeTeam"
    AWAY_TEAM = "AwayTeam"
    HOME_DISTANCE = "HomeDistance"
    AWAY_DISTANCE = "AwayDistance"
    HOME_SPRINT = "HomeSprint"
    AWAY_SPRINT = "AwaySprint"
    AUDIENCE_QTY = "Audience_Qty"
    WEATHER = "Weather"
    TEMPERATURE = "Temperature"
    HUMIDITY = "Humidity"


def _scrape_single_match_with_driver(
    driver: webdriver.Chrome,
    url: str,
    year: int,
    league_name: str
) -> Optional[Dict[str, Any]]:
    """기존 WebDriver를 재사용하여 단일 경기의 모든 데이터를 수집합니다.

    데이터 수집 파이프라인:
        1. 페이지 로드 및 대기
        2. 스타디움 테이블에서 관중/날씨 정보 추출
        3. 데이터 정제 (타입 변환, 파싱)
        4. 메타데이터 추출 (라운드, 날짜, 팀명)
        5. 트래킹 데이터 추출 (주행거리, 스프린트)
        6. 모든 데이터를 하나의 딕셔너리로 통합

    Args:
        driver: 재사용할 Selenium WebDriver 인스턴스
        url: J리그 경기 상세 페이지 URL
        year: 시즌 연도
        league_name: 리그 이름

    Returns:
        Optional[Dict[str, Any]]: 통합된 경기 데이터 딕셔너리
            페이지 로드 실패 또는 필수 데이터 없을 시 None

    Note:
        - 성능 최적화: 드라이버 재사용으로 인스턴스 생성 오버헤드 제거
        - 부분 데이터 허용: 일부 필드 누락 시에도 수집 가능
    """
    try:
        # 경기 페이지 로드
        driver.get(url)

        # Step 1: 페이지 로딩 완료 대기
        try:
            WebDriverWait(driver, TimeoutConfig.MATCH_DETAIL_PAGE).until(
                EC.presence_of_element_located((By.CLASS_NAME, CSSClassNames.LIVE_TOP_TABLE))
            )
        except TimeoutException:
            logger.warning(f"페이지 로딩 시간 초과 ({TimeoutConfig.MATCH_DETAIL_PAGE}초): {url}")
            return None

        # Step 2: 기본 테이블 데이터 추출 (관중, 날씨 등)
        try:
            data = extract_table_data(driver)
        except NoSuchElementException:
            logger.error(f"스타디움 정보 테이블 없음: {url}")
            return None

        # Step 3: 원본 데이터 정제 (문자열 → 숫자, 복합 필드 분해)
        processed_data = process_extracted_data(data)

        # Step 4: 추가 메타데이터 추출 및 병합
        processed_data.update(extract_round_info(driver))      # 라운드 번호
        processed_data.update(extract_datetime_info(driver))   # 날짜/시간
        processed_data.update(extract_team_names(driver))      # 팀명

        # Step 5: 트래킹 데이터 추출
        activate_tracking_tab(driver)                          # 탭 활성화
        processed_data.update(extract_tracking_data(driver))   # 주행거리/스프린트

        # Step 6: 최종 데이터 구조 생성
        final_data = {
            MatchDataKeys.MEET_YEAR: year,
            MatchDataKeys.LEAGUE_NAME: league_name,
            MatchDataKeys.ROUND: processed_data.get("Round"),
            MatchDataKeys.GAME_DATETIME: processed_data.get("Datetime"),
            MatchDataKeys.DAY: processed_data.get("Day"),
            MatchDataKeys.HOME_TEAM: processed_data.get("HomeTeam"),
            MatchDataKeys.AWAY_TEAM: processed_data.get("AwayTeam"),
            MatchDataKeys.HOME_DISTANCE: processed_data.get("HomeDistance"),
            MatchDataKeys.AWAY_DISTANCE: processed_data.get("AwayDistance"),
            MatchDataKeys.HOME_SPRINT: processed_data.get("HomeSprint"),
            MatchDataKeys.AWAY_SPRINT: processed_data.get("AwaySprint"),
            MatchDataKeys.AUDIENCE_QTY: processed_data.get("Attendance"),
            MatchDataKeys.WEATHER: processed_data.get("Weather"),
            MatchDataKeys.TEMPERATURE: processed_data.get("Temperature"),
            MatchDataKeys.HUMIDITY: processed_data.get("Humidity")
        }

        logger.debug(f"경기 데이터 수집 완료: {final_data.get('HomeTeam')} vs {final_data.get('AwayTeam')}")
        return final_data

    except Exception as e:
        logger.error(f"경기 데이터 수집 중 예외 발생: {type(e).__name__} - {e}")
        return None


def scrape_single_match(url: str, year: int, league_name: str) -> Optional[Dict[str, Any]]:
    """단일 경기 페이지에서 모든 경기 데이터를 수집합니다.

    독립적인 WebDriver 인스턴스를 생성하여 하나의 경기 데이터만 수집합니다.
    (하위 호환성 유지용 래퍼 함수)

    출력 데이터 구조 예시:
        {
            "Meet_Year": 2025,
            "LEAGUE_NAME": "J리그1",
            "Round": 10,
            "Game_Datetime": "2025-03-15 14:00:00",
            "Day": "토",
            "HomeTeam": "浦和レッズ",
            "AwayTeam": "鹿島アントラーズ",
            "HomeDistance": "115.2",
            "AwayDistance": "112.8",
            "HomeSprint": "45",
            "AwaySprint": "38",
            "Audience_Qty": 45123,
            "Weather": "맑음",
            "Temperature": "25",
            "Humidity": "60"
        }

    Args:
        url: J리그 경기 상세 페이지 URL
            예시: https://www.jleague.jp/match/j1/2025/031500/live/
        year: 시즌 연도
        league_name: 리그 이름

    Returns:
        Optional[Dict[str, Any]]: 통합된 경기 데이터 딕셔너리
            페이지 로드 실패 또는 필수 데이터 없을 시 None

    Note:
        - WebDriver는 함수 종료 시 자동으로 종료됨 (finally 블록)
        - 부분 데이터 누락 허용 (None 값으로 표시)
        - 대량 수집 시에는 scrape_season_matches() 사용 권장
    """
    driver = setup_chrome_driver()

    try:
        return _scrape_single_match_with_driver(driver, url, year, league_name)
    finally:
        driver.quit()


def scrape_monthly_matches(
    driver: webdriver.Chrome,
    league_category: str,
    year: int,
    month: int,
    league_display_name: str
) -> List[Dict[str, Any]]:
    """특정 월의 모든 경기를 스크래핑합니다.

    작업 흐름:
        1. 월별 경기 목록 페이지에서 URL 수집
        2. 각 경기 URL에 대해 scrape_single_match() 호출
        3. 수집된 데이터를 리스트로 반환

    Args:
        driver: 재사용 가능한 Selenium WebDriver 인스턴스
        league_category: 리그 카테고리 코드 (j1, j2, j3, playoff, 2playoff)
        year: 시즌 연도 (예: 2025)
        month: 월 (1~12)
        league_display_name: 사용자에게 표시할 리그 이름

    Returns:
        List[Dict[str, Any]]: 해당 월의 모든 경기 데이터 리스트
            경기가 없거나 실패 시 빈 리스트 반환

    Note:
        - URL 사전 추출로 StaleElementReferenceException 방지
        - 개별 경기 실패 시에도 다른 경기는 계속 수집
        - 진행률은 Rich 라이브러리의 track()으로 표시
    """
    # 월별 경기 URL 수집
    match_urls = _collect_monthly_match_urls(driver, league_category, year, month)

    if not match_urls:
        return []

    # 각 경기 데이터 수집 (진행률 표시)
    monthly_data = []
    for match_url in track(match_urls, description=f"[cyan]{month}월 경기 수집:[/cyan]"):
        match_data = scrape_single_match(match_url, year, league_display_name)
        if match_data:
            monthly_data.append(match_data)

    return monthly_data


def scrape_season_matches(
    league_category: str,
    year: int,
    league_display_name: str
) -> List[Dict[str, Any]]:
    """전체 시즌(1~12월)의 모든 경기를 순차적으로 스크래핑합니다.

    2단계 스크래핑 전략:
        [1단계] URL 수집: 1~12월의 모든 경기 URL 수집
            - 빠른 탐색으로 전체 경기 수 사전 파악
            - 월별로 순회하며 URL만 추출

        [2단계] 데이터 수집: 수집된 URL로부터 상세 데이터 추출
            - 단일 진행률 바로 전체 진행 상황 표시
            - 각 경기 페이지 접속 및 데이터 파싱

    장점:
        - 사용자에게 총 경기 수 사전 제공
        - 전체 진행률을 하나의 바로 표시 (UX 개선)
        - 월별 구분 없이 연속적인 수집 가능

    Args:
        league_category: 리그 카테고리 코드 (j1, j2, j3, playoff, 2playoff)
        year: 시즌 연도
        league_display_name: 사용자에게 표시할 리그 이름
            예시: "J리그1", "J리그2", "J리그1PO"

    Returns:
        List[Dict[str, Any]]: 시즌 전체 경기 데이터 리스트

    Note:
        - WebDriver는 함수 종료 시 자동 종료 (finally 블록)
        - 월별 페이지 로드 실패는 무시하고 계속 진행
        - 개별 경기 수집 실패 시에도 다른 경기는 계속 수집
    """
    driver = setup_chrome_driver(optimized=True)
    season_data = []

    try:
        # ====================================================================
        # [1단계] 전체 시즌 URL 수집
        # ====================================================================
        all_match_urls = []

        for month in range(1, 13):  # 1월 ~ 12월
            month_urls = _collect_monthly_match_urls(driver, league_category, year, month)
            all_match_urls.extend(month_urls)

        # 수집 시작 안내 메시지 출력
        console = Console()
        console.print(
            f"\n[bold magenta][{year}년 {league_display_name} 경기 데이터] "
            f"(총 {len(all_match_urls)}경기)[/bold magenta]",
            style="bold"
        )

        # ====================================================================
        # [2단계] 경기 상세 데이터 수집 (드라이버 재사용으로 성능 개선)
        # ====================================================================
        for match_url in track(all_match_urls, description=f"[cyan]수집 현황:[/cyan]"):
            match_data = _scrape_single_match_with_driver(driver, match_url, year, league_display_name)
            if match_data:
                season_data.append(match_data)

    finally:
        driver.quit()

    return season_data


def _scrape_match_worker(args: Tuple[str, int, str], max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """병렬 처리를 위한 워커 함수 (재시도 로직 포함).

    각 스레드에서 독립적으로 WebDriver를 생성하여 경기 데이터를 수집합니다.
    SessionNotCreatedException 발생 시 자동으로 재시도합니다.

    Args:
        args: (match_url, year, league_display_name) 튜플
        max_retries: ChromeDriver 생성 실패 시 최대 재시도 횟수 (기본값: 3)

    Returns:
        Optional[Dict[str, Any]]: 수집된 경기 데이터 또는 None

    Note:
        - 각 워커는 독립적인 WebDriver 인스턴스 사용
        - ChromeDriver 생성 실패 시 최대 3회 재시도
        - 워커 종료 시 자동으로 드라이버 종료 (리소스 관리)
    """
    match_url, year, league_display_name = args

    for attempt in range(max_retries):
        driver = None
        try:
            driver = setup_chrome_driver(optimized=True)
            result = _scrape_single_match_with_driver(driver, match_url, year, league_display_name)
            return result
        except SessionNotCreatedException as e:
            logger.warning(
                f"ChromeDriver 생성 실패 (시도 {attempt + 1}/{max_retries})"
            )
            if attempt == max_retries - 1:
                # 모든 재시도 실패 시 예외를 다시 발생시켜 상위에서 처리
                raise
        finally:
            if driver:
                driver.quit()

    return None


def scrape_season_matches_parallel(
    league_category: str,
    year: int,
    league_display_name: str,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """전체 시즌(1~12월)의 모든 경기를 병렬로 스크래핑합니다.

    3단계 스크래핑 전략:
        [1단계] URL 수집: 1~12월의 모든 경기 URL 수집
        [2단계] 병렬 데이터 수집: 여러 스레드로 동시에 경기 데이터 추출
        [3단계] 실패 URL 재수집: 1차 수집 실패한 경기를 재시도

    Args:
        league_category: 리그 카테고리 코드 (j1, j2, j3, playoff, 2playoff)
        year: 시즌 연도
        league_display_name: 사용자에게 표시할 리그 이름
        max_workers: 동시 실행할 스레드 수 (기본값: 4)
            권장 범위: 2~8 (너무 많으면 웹사이트에 부하)

    Returns:
        List[Dict[str, Any]]: 시즌 전체 경기 데이터 리스트

    Note:
        - 각 스레드가 독립적인 WebDriver 인스턴스 사용
        - 웹사이트 정책을 고려하여 max_workers는 4~6 권장
        - 실패한 경기는 자동으로 재수집하여 데이터 손실 최소화
        - 순차 모드 대비 4~8배 빠른 속도
    """
    # URL 수집용 드라이버 (한 번만 사용)
    driver = setup_chrome_driver(optimized=True)

    try:
        # ====================================================================
        # [1단계] 전체 시즌 URL 수집
        # ====================================================================
        all_match_urls = []

        for month in range(1, 13):  # 1월 ~ 12월
            month_urls = _collect_monthly_match_urls(driver, league_category, year, month)
            all_match_urls.extend(month_urls)

    finally:
        driver.quit()

    # ====================================================================
    # [2단계] 병렬 경기 데이터 수집
    # ====================================================================
    console = Console()
    console.print(
        f"\n[bold magenta][{year}년 {league_display_name} 경기 데이터][/bold magenta] "
        f"(총 {len(all_match_urls)}경기)",
        style="bold"
    )

    # 워커 함수에 전달할 인자 준비
    task_args = [(url, year, league_display_name) for url in all_match_urls]

    # 병렬 처리 with 진행률 표시
    season_data = []
    failed_tasks = []  # 실패한 작업 추적

    with Progress() as progress:
        task = progress.add_task("[cyan]수집 현황:[/cyan]", total=len(task_args))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            future_to_args = {
                executor.submit(_scrape_match_worker, args): args
                for args in task_args
            }

            # 완료된 작업부터 처리
            for future in as_completed(future_to_args):
                args = future_to_args[future]
                try:
                    match_data = future.result()
                    if match_data:
                        season_data.append(match_data)
                    else:
                        # 데이터가 None인 경우 (페이지 로드 실패 등)
                        failed_tasks.append(args)
                        logger.warning(f"데이터 수집 실패 (재시도 예정): {args[0]}")
                except Exception as e:
                    # 예외 발생 시 실패 목록에 추가
                    failed_tasks.append(args)
                    logger.error(f"워커 스레드 예외 (재시도 예정): {type(e).__name__} - {e}")

                progress.update(task, advance=1)

    # ====================================================================
    # [3단계] 실패한 경기 재수집
    # ====================================================================
    if failed_tasks:
        console.print(
            f"\n[bold yellow]실패한 {len(failed_tasks)}경기 재수집 시작...[/bold yellow]"
        )

        retry_data = []
        for args in track(failed_tasks, description=f"[yellow]재수집 현황:[/yellow]"):
            match_url, year_val, league_name = args
            # 재시도는 순차적으로 수행 (안정성 우선)
            match_data = scrape_single_match(match_url, year_val, league_name)
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


def collect_jleague_match_data(
    year: int | List[int],
    league: str | List[str] = "J리그1",
    parallel: bool = False,
    max_workers: int = 4
) -> Tuple[List[Dict[str, Any]], str]:
    """J리그 경기 데이터를 수집하는 최상위 공개 API 함수입니다.

    사용 예시:
        # 단일 연도, 단일 리그
        >>> data, filename = collect_jleague_match_data(2025, "J리그1")
        >>> print(filename)
        'j1_match_2025'

        # 여러 연도, 여러 리그
        >>> data, filename = collect_jleague_match_data([2023, 2025], ["J리그1", "J리그2"])
        >>> print(filename)
        'jleague_match_2023-2025'
        >>> print(len(data))
        750

        # 플레이오프만 수집
        >>> data, filename = collect_jleague_match_data(2024, "J리그1PO")

        # 병렬 처리로 빠르게 수집 (4~8배 속도 향상)
        >>> data, filename = collect_jleague_match_data(2024, "J리그1", parallel=True, max_workers=4)

    Args:
        year: 수집할 시즌 연도
            - int: 단일 연도 (예: 2025)
            - List[int]: 연도 범위 (예: [2023, 2025] → 2023, 2024, 2025)
        league: 수집할 리그 (기본값: "J리그1")
            - str: 단일 리그
            - List[str]: 여러 리그 (예: ["J리그1", "J리그2"])
            - 지원 리그:
                * "J리그1": J1 리그
                * "J리그2": J2 리그
                * "J리그3": J3 리그
                * "J리그1PO": J1 플레이오프
                * "J리그2PO": J2 플레이오프
        parallel: 병렬 처리 사용 여부 (기본값: False)
            True 설정 시 멀티스레딩으로 빠른 수집
        max_workers: 병렬 처리 시 동시 스레드 수 (기본값: 4)
            권장 범위: 2~8

    Returns:
        Tuple[List[Dict[str, Any]], str]:
            - List[Dict[str, Any]]: 수집된 경기 데이터 리스트
            - str: 파일 저장용 파일명 (확장자 제외)
                형식: "{리그}_{타입}_{연도}"
                예시: "j1_match_2025", "jleague_match_2023-2025"

    Raises:
        ValueError: 지원하지 않는 리그 이름이 입력된 경우

    Note:
        - 개별 시즌 수집 실패 시 에러 로깅 후 계속 진행
        - 수집 진행 상황은 콘솔에 실시간으로 표시됨
        - 빈 데이터가 반환될 수 있음 (모든 수집 실패 시)
        - parallel=True 사용 시 웹사이트에 과부하 주의 (max_workers ≤ 6 권장)
    """
    # ========================================================================
    # 리그 이름 → URL 카테고리 매핑 테이블
    # ========================================================================
    LEAGUE_TO_CATEGORY: Final[Dict[str, str]] = {
        "J리그1": "j1",
        "J리그2": "j2",
        "J리그3": "j3",
        "J리그1PO": "playoff",
        "J리그2PO": "2playoff"
    }

    # ========================================================================
    # 입력 파라미터 정규화
    # ========================================================================

    # 리그 파라미터를 리스트로 변환
    league_list: List[str] = [league] if isinstance(league, str) else list(league)

    # 지원하지 않는 리그 검증
    for league_name in league_list:
        if league_name not in LEAGUE_TO_CATEGORY:
            raise ValueError(
                f"지원하지 않는 리그: '{league_name}'\n"
                f"지원 리그: {list(LEAGUE_TO_CATEGORY.keys())}"
            )

    # 연도 파라미터를 리스트로 변환 및 범위 확장
    if isinstance(year, int):
        years: List[int] = [year]
        year_label: str = str(year)
    else:
        years = list(range(min(year), max(year) + 1))
        year_label = f"{min(year)}-{max(year)}"

    # ========================================================================
    # 파일명 생성
    # ========================================================================
    if len(league_list) == 1:
        league_label: str = LEAGUE_TO_CATEGORY[league_list[0]]
    else:
        league_label = "jleague"

    # ========================================================================
    # 데이터 수집 (중첩 루프: 리그 × 연도)
    # ========================================================================
    dataset: List[Dict[str, Any]] = []

    for league_name in league_list:
        league_category = LEAGUE_TO_CATEGORY[league_name]

        for year_val in years:
            try:
                # 시즌 데이터 수집 (병렬/순차 선택)
                if parallel:
                    season_data = scrape_season_matches_parallel(
                        league_category,
                        year_val,
                        league_name,
                        max_workers
                    )
                else:
                    season_data = scrape_season_matches(
                        league_category,
                        year_val,
                        league_name
                    )
                dataset.extend(season_data)

            except Exception as e:
                logger.error(f"{year_val}년 {league_name} 수집 실패: {type(e).__name__} - {e}")

    # ========================================================================
    # 결과 반환
    # ========================================================================
    file_name = f"{league_label}_match_{year_label}"
    logger.info(f"데이터 수집 완료: {len(dataset)}경기, 파일명: {file_name}")
    return dataset, file_name
