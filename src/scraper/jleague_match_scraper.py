"""
J리그 경기 데이터 스크래퍼 (JLeague Match Data Scraper)

J리그 공식 웹사이트(www.jleague.jp)에서 경기 정보를 추출하는 웹 스크래핑 모듈입니다.

주요 수집 데이터:
    - 경기 메타데이터: 라운드, 날짜, 시간, 요일, 팀명
    - 경기장 정보: 관중 수, 날씨, 온도, 습도
    - 트래킹 데이터: 팀별 주행거리, 스프린트 횟수

데이터 흐름:
    1. URL 수집: 월별 경기 목록에서 개별 경기 URL 추출
    2. 데이터 추출: 각 경기 페이지에서 구조화된 데이터 수집
    3. 데이터 정제: 문자열 파싱, 타입 변환, 한글 번역
    4. 데이터 통합: 모든 경기 데이터를 리스트로 반환

기술 스택:
    - Selenium: 동적 웹 페이지 렌더링 및 데이터 추출
    - Rich: 진행률 표시 및 콘솔 출력 시각화
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Any, Callable, List, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from rich.console import Console
from rich.progress import track

from .scraper import setup_chrome_driver


# ============================================================================
# 상수 정의 (Configuration Constants)
# ============================================================================

# ----------------------------------------------------------------------------
# Selenium 대기 시간 설정 (Timeout Configuration)
# ----------------------------------------------------------------------------
# 페이지 요소 로딩을 위한 최대 대기 시간 (초 단위)
WAIT_TIMEOUT: int = 10                    # 경기 상세 페이지 로딩 대기 시간
MATCH_LIST_WAIT_TIMEOUT: int = 5          # 월별 경기 목록 로딩 대기 시간
TRACKING_TAB_WAIT_TIMEOUT: int = 3        # 트래킹 탭 활성화 대기 시간

# ----------------------------------------------------------------------------
# 데이터 필드 매핑 (Data Field Mapping)
# ----------------------------------------------------------------------------
# J리그 웹사이트의 일본어 필드명을 영어 키로 변환
TARGET_FIELDS: Dict[str, str] = {
    "入場者数": "Attendance",                 # 관중 수
    "天候 / 気温 / 湿度": "Weather_Info",      # 날씨/온도/습도 통합 정보
}

# ----------------------------------------------------------------------------
# 번역 매핑 테이블 (Translation Mappings)
# ----------------------------------------------------------------------------
# 일본어 날씨 표현을 한국어로 번역
WEATHER_TRANSLATION: Dict[str, str] = {
    "晴": "맑음",    # 맑음
    "曇": "흐림",    # 흐림
    "雨": "비",      # 비
    "雪": "눈"       # 눈
}

# 일본어 요일을 한국어로 변환
DAY_TRANSLATION: Dict[str, str] = {
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
# XPath: 경기장(スタジアム) 정보를 포함한 테이블 찾기
STADIUM_TABLE_XPATH: str = "//td[contains(text(), 'スタジアム')]/ancestor::table"

# XPath: 트래킹 데이터 탭 링크 찾기
TRACKING_TAB_XPATH: str = "//a[contains(@href, '#trackingdata')]"

# CSS Selector: 월별 경기 목록에서 개별 경기 링크 추출
MATCH_LIST_SELECTOR: str = "section.matchlistWrap td.match a[href*='/live/']"

# ----------------------------------------------------------------------------
# 정규표현식 패턴 (Regex Patterns)
# ----------------------------------------------------------------------------
# 라운드 번호 추출: "第10節" → 10
ROUND_PATTERN: str = r'第(\d+)節'

# 날짜/시간 파싱: "2025年3月15日(土) 14:00" → (2025, 3, 15, 土, 14, 00)
DATETIME_PATTERN: str = r'(\d{4})[年/.-](\d{1,2})[月/.-](\d{1,2}).*?([月火水木金土日]).*?(\d{1,2}):(\d{2})'

# ----------------------------------------------------------------------------
# API 엔드포인트 (API Endpoints)
# ----------------------------------------------------------------------------
# J리그 경기 검색 URL 템플릿
JLEAGUE_SEARCH_URL: str = "https://www.jleague.jp/match/search/?category[]={league}&year={year}&month={month}"

# ----------------------------------------------------------------------------
# 데이터 검증 상수 (Data Validation Constants)
# ----------------------------------------------------------------------------
# 트래킹 데이터의 예상 HTML 요소 개수 (주행거리 2개 + 스프린트 2개)
EXPECTED_TRACKING_ELEMENTS: int = 4


# ============================================================================
# 헬퍼 함수 (Helper Functions)
# ============================================================================

def safe_extract(
    extraction_func: Callable[[], Dict[str, Any]],
    error_message: str
) -> Dict[str, Any]:
    """
    안전하게 데이터를 추출하고 예외를 처리합니다.

    데이터 파이프라인의 견고성을 위해 예외 발생 시에도 프로세스가 중단되지 않도록
    에러를 캡처하고 빈 딕셔너리를 반환합니다.

    Args:
        extraction_func: 데이터를 추출하는 콜백 함수
                        반환값은 Dict[str, Any] 형식이어야 함
        error_message: 예외 발생 시 사용자에게 표시할 에러 메시지

    Returns:
        Dict[str, Any]: 추출 성공 시 데이터 딕셔너리, 실패 시 빈 딕셔너리

    Example:
        >>> def extract_data():
        ...     return {"value": 100}
        >>> safe_extract(extract_data, "데이터 추출 실패")
        {'value': 100}
    """
    try:
        return extraction_func()
    except Exception as e:
        print(f"⚠️ {error_message}: {e}")
        return {}


def clean_attendance_data(raw_attendance: str) -> int:
    """
    관중 수 원본 데이터를 정제하여 정수형으로 변환합니다.

    데이터 정제 과정:
        1. 천 단위 구분 쉼표(,) 제거
        2. 일본어 단위 문자 '人' 제거
        3. 숫자 문자열을 정수로 변환
        4. 변환 실패 시 0 반환 (데이터 품질 보장)

    Args:
        raw_attendance: 원본 관중 수 문자열
                       예: "10,000人", "45,123人"

    Returns:
        int: 정제된 관중 수 (정수형)
             변환 실패 또는 유효하지 않은 입력 시 0 반환

    Example:
        >>> clean_attendance_data("10,000人")
        10000
        >>> clean_attendance_data("45,123人")
        45123
        >>> clean_attendance_data("Invalid")
        0
    """
    # 특수문자 및 일본어 제거
    clean_num = raw_attendance.replace(",", "").replace("人", "").strip()

    # 숫자 검증 후 변환 (데이터 품질 검증)
    return int(clean_num) if clean_num.isdigit() else 0


def parse_weather_info(weather_info: str) -> Dict[str, str]:
    """
    복합 날씨 정보 문자열을 개별 필드로 파싱합니다.

    입력 형식:
        "날씨 / 온도℃ / 습도%"
        예: "晴 / 25℃ / 60%"

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
                       형식이 잘못되었을 경우 빈 딕셔너리 반환

    Example:
        >>> parse_weather_info("晴 / 25℃ / 60%")
        {'Weather': '맑음', 'Temperature': '25', 'Humidity': '60'}
    """
    # 슬래시 기준으로 분리
    parts = weather_info.split("/")

    # 데이터 무결성 검증: 3개 필드 미만일 경우 파싱 불가
    if len(parts) < 3:
        return {}

    # 각 필드에서 단위 제거 및 공백 정리
    weather_raw = parts[0].strip()
    temperature = parts[1].replace("℃", "").strip()
    humidity = parts[2].replace("%", "").strip()

    # 날씨를 한국어로 번역 (매핑에 없으면 원본 유지)
    return {
        "Weather": WEATHER_TRANSLATION.get(weather_raw, weather_raw),
        "Temperature": temperature,
        "Humidity": humidity
    }


# ============================================================================
# 데이터 추출 함수 (Data Extraction Functions)
# ============================================================================

def extract_table_data(driver: webdriver.Chrome) -> Dict[str, Any]:
    """
    경기 상세 페이지에서 스타디움 정보 테이블을 추출합니다.

    HTML 구조:
        <table>
            <tr>
                <td>스타디움</td><td>경기장명</td>
                <td>入場者数</td><td>10,000人</td>
            </tr>
            <tr>
                <td>天候 / 気温 / 湿度</td><td>晴 / 25℃ / 60%</td>
            </tr>
        </table>

    추출 알고리즘:
        1. XPath로 스타디움 정보를 포함한 테이블 찾기
        2. 모든 <td> 요소를 순차적으로 탐색 (짝수: 레이블, 홀수: 값)
        3. TARGET_FIELDS에 정의된 필드만 추출

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Any]: 추출된 경기 데이터
                       예: {"Attendance": "10,000人", "Weather_Info": "晴 / 25℃ / 60%"}

    Raises:
        NoSuchElementException: 스타디움 테이블을 찾을 수 없는 경우
    """
    # 스타디움 정보 테이블 찾기
    table = driver.find_element(By.XPATH, STADIUM_TABLE_XPATH)
    cells = table.find_elements(By.TAG_NAME, "td")

    data = {}

    # 테이블 셀을 2개씩 묶어서 처리 (레이블-값 쌍)
    for i in range(0, len(cells), 2):
        # 홀수 개의 셀인 경우 마지막 셀 무시 (데이터 무결성 보장)
        if i + 1 >= len(cells):
            break

        label = cells[i].text.strip()
        value = cells[i + 1].text.strip()

        # 관심 필드만 추출 (필터링)
        if label in TARGET_FIELDS:
            data[TARGET_FIELDS[label]] = value

    return data


def process_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    추출된 원본 데이터를 분석 가능한 형태로 정제 및 변환합니다.

    데이터 변환 파이프라인:
        1. 관중 수: "10,000人" → 10000 (int)
        2. 날씨 정보: "晴 / 25℃ / 60%" → {"Weather": "맑음", "Temperature": "25", "Humidity": "60"}

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
        data: 원본 데이터 딕셔너리 (문자열 형태의 데이터)

    Returns:
        Dict[str, Any]: 정제 및 타입 변환된 데이터 딕셔너리

    Note:
        - 딕셔너리를 직접 수정하는 in-place 연산 수행
        - Weather_Info는 개별 필드로 분해되어 제거됨
    """
    # 관중 수: 문자열 → 정수 변환
    if "Attendance" in data:
        data["Attendance"] = clean_attendance_data(data["Attendance"])

    # 날씨 정보: 복합 문자열 → 개별 필드로 분해
    if "Weather_Info" in data:
        weather_data = parse_weather_info(data.pop("Weather_Info"))
        data.update(weather_data)

    return data


def extract_round_info(driver: webdriver.Chrome) -> Dict[str, Optional[int]]:
    """
    경기 라운드(절차) 정보를 추출합니다.

    추출 위치:
        CSS 클래스 "matchVsTitle__league"에서 "第N節" 패턴 검색

    예시:
        "明治安田J1リーグ 第10節" → {"Round": 10}
        "YBCルヴァンカップ 準決勝" → {"Round": None}  # 패턴 없음

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Optional[int]]: {"Round": 라운드번호 또는 None}

    Note:
        - 플레이오프나 컵 대회의 경우 라운드 정보가 없을 수 있음
        - 정규표현식 패턴 매칭 실패 시 None 반환
    """
    def _extract():
        # 리그 정보 요소에서 텍스트 추출
        league_element = driver.find_element(By.CLASS_NAME, "matchVsTitle__league")
        league_text = league_element.text.strip()

        # 정규표현식으로 라운드 번호 추출 (第10節 → 10)
        round_match = re.search(ROUND_PATTERN, league_text)
        if round_match:
            round_num = int(round_match.group(1))
            return {"Round": round_num}
        else:
            print(f"⚠️ 라운드 패턴(第N節)을 찾을 수 없습니다: {league_text}")
            return {"Round": None}

    return safe_extract(_extract, "라운드 정보 추출 중 에러 발생")


def extract_datetime_info(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """
    경기 날짜, 시간, 요일 정보를 추출하여 표준 형식으로 변환합니다.

    입력 형식 예시:
        - "2025年3月15日(土) 14:00"
        - "2025/03/15(土)14:00"
        - "2025.3.15 (토) 2:30"

    출력 형식:
        {
            "Datetime": "2025-03-15 14:00:00",  # ISO 형식 (YYYY-MM-DD HH:MM:SS)
            "Day": "토"                          # 한글 요일
        }

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Optional[str]]: 날짜/시간/요일 정보 딕셔너리
                                 파싱 실패 시 모든 값이 None

    Note:
        - 정규표현식으로 다양한 날짜 형식 지원
        - 월/일/시/분은 자동으로 2자리 제로패딩 (3 → 03)
    """
    def _extract():
        # 날짜 정보 요소에서 텍스트 추출
        date_element = driver.find_element(By.CLASS_NAME, "matchVsTitle__date")
        raw_date_text = date_element.text.strip()

        # 정규표현식으로 날짜/시간 파싱
        match = re.search(DATETIME_PATTERN, raw_date_text)
        if not match:
            print(f"⚠️ 날짜 형식을 파싱할 수 없습니다. 원본: {raw_date_text}")
            return {"Datetime": None, "Day": None}

        # 그룹 추출: (년, 월, 일, 요일, 시, 분)
        year, month, day, day_char, hour, minute = match.groups()

        # 요일을 한국어로 번역
        korean_day = DAY_TRANSLATION.get(day_char, day_char)

        # ISO 8601 형식으로 포맷팅 (제로패딩 적용)
        formatted_datetime = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}:00"

        return {"Datetime": formatted_datetime, "Day": korean_day}

    return safe_extract(_extract, "날짜 정보를 추출하는 중 오류 발생")


def extract_team_names(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """
    경기에 참여하는 홈팀과 어웨이팀의 이름을 추출합니다.

    HTML 구조:
        <div class="leagAccTeam__clubName">
            <span>浦和レッズ</span>  <!-- 홈팀 -->
        </div>
        <div class="leagAccTeam__clubName">
            <span>鹿島アントラーズ</span>  <!-- 어웨이팀 -->
        </div>

    추출 순서:
        1. "leagAccTeam__clubName" 클래스를 가진 모든 요소 탐색
        2. 첫 번째 요소 = 홈팀, 두 번째 요소 = 어웨이팀
        3. 각 요소 내부의 <span> 태그에서 팀명 추출

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        Dict[str, Optional[str]]: {"HomeTeam": 홈팀명, "AwayTeam": 어웨이팀명}
                                 요소가 부족할 경우 None 반환

    Note:
        - 최소 2개의 팀명 요소가 필요 (데이터 무결성 검증)
        - 요소 부족 시 경고 메시지 출력 후 None 반환
    """
    def _extract():
        # 팀명 요소 모두 찾기
        team_elements = driver.find_elements(By.CLASS_NAME, "leagAccTeam__clubName")

        # 데이터 무결성 검증: 최소 2개의 팀 정보 필요
        if len(team_elements) < 2:
            print("⚠️ 팀 이름 요소를 충분히 찾지 못했습니다.")
            return {"HomeTeam": None, "AwayTeam": None}

        # 각 요소에서 <span> 태그의 텍스트 추출
        home_team = team_elements[0].find_element(By.TAG_NAME, "span").text.strip()
        away_team = team_elements[1].find_element(By.TAG_NAME, "span").text.strip()

        return {"HomeTeam": home_team, "AwayTeam": away_team}

    return safe_extract(_extract, "팀 이름을 추출하는 중 오류 발생")


def activate_tracking_tab(driver: webdriver.Chrome) -> None:
    """
    트래킹 데이터 탭을 JavaScript 클릭으로 활성화합니다.

    동작 방식:
        1. XPath로 트래킹 탭 링크 찾기
        2. JavaScript를 통한 강제 클릭 (일반 클릭보다 안정적)
        3. "total_km" 클래스 요소가 나타날 때까지 대기

    Args:
        driver: Selenium WebDriver 인스턴스

    Returns:
        None

    Note:
        - 트래킹 탭이 없는 경기도 존재할 수 있음 (예: 과거 경기)
        - 예외 발생 시 무시하여 전체 스크래핑 프로세스 중단 방지
        - 탭이 이미 활성화되어 있어도 문제없이 처리됨
    """
    try:
        # 트래킹 데이터 탭 찾기
        tracking_tab = driver.find_element(By.XPATH, TRACKING_TAB_XPATH)

        # JavaScript를 통한 클릭 (일반 click()보다 안정적)
        driver.execute_script("arguments[0].click();", tracking_tab)

        # 탭 내용이 로드될 때까지 대기
        WebDriverWait(driver, TRACKING_TAB_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CLASS_NAME, "total_km"))
        )
    except Exception:
        # 트래킹 탭이 없거나 이미 열려있는 경우 에러 무시
        pass


def extract_tracking_data(driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
    """
    선수들의 총 주행거리 및 스프린트 횟수를 추출합니다.

    HTML 구조:
        <td class="total_km" colspan="2">
            115.2
            <span>km</span>
        </td>
        <td class="total_km" colspan="2">
            112.8
            <span>km</span>
        </td>
        <td class="total_km" colspan="2">
            45
            <span>回</span>
        </td>
        <td class="total_km" colspan="2">
            38
            <span>回</span>
        </td>

    데이터 추출 로직:
        - 요소 4개: 주행거리 2개 + 스프린트 2개 추출
        - 요소 2개: 주행거리만 추출 (스프린트는 None)
        - 요소 부족: 모든 값 None 반환

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
        - 과거 경기의 경우 트래킹 데이터가 없을 수 있음
        - 단위(km, 回)는 제거하고 숫자만 반환
    """
    def _extract():
        # "total_km" 클래스를 가진 모든 요소 찾기
        stat_elements = driver.find_elements(By.CLASS_NAME, "total_km")

        # 기본 구조: 모든 값을 None으로 초기화
        result = {
            "HomeDistance": None,
            "AwayDistance": None,
            "HomeSprint": None,
            "AwaySprint": None
        }

        # Case 1: 완전한 트래킹 데이터 (주행거리 + 스프린트)
        if len(stat_elements) >= EXPECTED_TRACKING_ELEMENTS:
            # 주행거리 추출 (인덱스 0, 1)
            result["HomeDistance"] = stat_elements[0].text.lower().replace("km", "").strip()
            result["AwayDistance"] = stat_elements[1].text.lower().replace("km", "").strip()

            # 스프린트 횟수 추출 (인덱스 2, 3)
            result["HomeSprint"] = stat_elements[2].text.replace("回", "").strip()
            result["AwaySprint"] = stat_elements[3].text.replace("回", "").strip()

        # Case 2: 부분 데이터 (주행거리만 있는 경우)
        elif len(stat_elements) >= 2:
            result["HomeDistance"] = stat_elements[0].text.lower().replace("km", "").strip()
            result["AwayDistance"] = stat_elements[1].text.lower().replace("km", "").strip()
            print(f"⚠️ 스프린트 데이터 부족 (주행거리만 추출): {result['HomeDistance']} vs {result['AwayDistance']}")

        # Case 3: 트래킹 데이터 없음
        else:
            print("⚠️ 트래킹 데이터(주행거리/스프린트)를 찾을 수 없습니다.")

        return result

    return safe_extract(_extract, "트래킹 데이터 추출 중 에러 발생")


# ============================================================================
# 메인 수집 함수 (Main Scraping Functions)
# ============================================================================

def scrape_single_match(url: str, year: int, league_name: str) -> Optional[Dict[str, Any]]:
    """
    단일 경기 페이지에서 모든 경기 데이터를 수집합니다.

    데이터 수집 파이프라인:
        1. 페이지 로드 및 대기
        2. 스타디움 테이블에서 관중/날씨 정보 추출
        3. 데이터 정제 (타입 변환, 파싱)
        4. 메타데이터 추출 (라운드, 날짜, 팀명)
        5. 트래킹 데이터 추출 (주행거리, 스프린트)
        6. 모든 데이터를 하나의 딕셔너리로 통합

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
            예: https://www.jleague.jp/match/j1/2025/031500/live/
        year: 시즌 연도
        league_name: 리그 이름

    Returns:
        Optional[Dict[str, Any]]: 통합된 경기 데이터 딕셔너리
                                 페이지 로드 실패 또는 필수 데이터 없을 시 None

    Note:
        - WebDriver는 함수 종료 시 자동으로 종료됨 (finally 블록)
        - 부분적인 데이터 누락은 허용 (None 값으로 표시)
        - 페이지 로드 실패나 필수 테이블 부재 시에만 None 반환
    """
    # Chrome WebDriver 초기화
    driver = setup_chrome_driver()

    try:
        # 경기 페이지 로드
        driver.get(url)

        # Step 1: 페이지 로딩 완료 대기
        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "liveTopTable"))
            )
        except TimeoutException:
            print(f"⚠️ 시간 초과: {WAIT_TIMEOUT}초 내에 테이블을 찾을 수 없습니다.")
            return None

        # Step 2: 기본 테이블 데이터 추출 (관중, 날씨 등)
        try:
            data = extract_table_data(driver)
        except NoSuchElementException:
            print("❌ 'スタジアム' 정보를 포함한 테이블을 찾을 수 없습니다.")
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

        # Step 6: 필드명 변경 및 새 필드 추가
        final_data = {
            "Meet_Year": year,
            "LEAGUE_NAME": league_name,
            "Round": processed_data.get("Round"),
            "Game_Datetime": processed_data.get("Datetime"),
            "Day": processed_data.get("Day"),
            "HomeTeam": processed_data.get("HomeTeam"),
            "AwayTeam": processed_data.get("AwayTeam"),
            "HomeDistance": processed_data.get("HomeDistance"),
            "AwayDistance": processed_data.get("AwayDistance"),
            "HomeSprint": processed_data.get("HomeSprint"),
            "AwaySprint": processed_data.get("AwaySprint"),
            "Audience_Qty": processed_data.get("Attendance"),
            "Weather": processed_data.get("Weather"),
            "Temperature": processed_data.get("Temperature"),
            "Humidity": processed_data.get("Humidity")
        }

        return final_data

    finally:
        # 리소스 정리: WebDriver 종료
        driver.quit()


def scrape_monthly_matches(
    driver: webdriver.Chrome,
    league_category: str,
    year: int,
    month: int,
    league_display_name: str
) -> List[Dict[str, Any]]:
    """
    특정 월의 모든 경기를 스크래핑합니다.

    작업 흐름:
        1. 월별 경기 목록 페이지 접속
        2. 경기 링크 요소들을 찾아 URL 추출
        3. 각 경기 URL에 대해 scrape_single_match() 호출
        4. 수집된 데이터를 리스트로 반환

    Args:
        driver: 재사용 가능한 Selenium WebDriver 인스턴스
        league_category: 리그 카테고리 코드
                        - "j1": J리그1
                        - "j2": J리그2
                        - "j3": J리그3
                        - "playoff": J리그1 플레이오프
                        - "2playoff": J리그2 플레이오프
        year: 시즌 연도 (예: 2025)
        month: 월 (1~12)
        league_display_name: 사용자에게 표시할 리그 이름

    Returns:
        List[Dict[str, Any]]: 해당 월의 모든 경기 데이터 리스트
                             경기가 없거나 실패 시 빈 리스트 반환

    Note:
        - StaleElementReferenceException 방지를 위해 URL을 먼저 추출
        - 개별 경기 실패 시에도 다른 경기는 계속 수집
        - 진행률은 Rich 라이브러리의 track()으로 표시
    """
    # 월별 경기 목록 URL 생성
    url = JLEAGUE_SEARCH_URL.format(league=league_category, year=year, month=month)
    driver.get(url)

    monthly_data = []

    try:
        # 경기 목록 컨테이너 로딩 대기
        WebDriverWait(driver, MATCH_LIST_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "section.matchlistWrap"))
        )

        # 모든 경기 링크 요소 찾기
        match_link_elements = driver.find_elements(By.CSS_SELECTOR, MATCH_LIST_SELECTOR)

        # 경기가 없는 경우 조기 반환
        if not match_link_elements:
            return monthly_data

        # URL 사전 추출 (StaleElementReferenceException 방지)
        # 페이지를 떠나면 요소 참조가 무효화되므로 URL만 먼저 추출
        match_urls = [
            link.get_attribute("href")
            for link in match_link_elements
            if link.get_attribute("href")
        ]

        # 각 경기 데이터 수집 (진행률 표시)
        for match_url in track(match_urls, description=f"[cyan]{month}월 경기 수집:[/cyan]"):
            match_data = scrape_single_match(match_url, year, league_display_name)
            if match_data:
                monthly_data.append(match_data)

    except TimeoutException:
        print(f"⚠️ {month}월 페이지 로딩 시간 초과 또는 데이터 영역을 찾을 수 없습니다.")

    except Exception as e:
        print(f"❌ {month}월 처리 중 예기치 않은 오류: {e}")

    return monthly_data


def scrape_season_matches(
    league_category: str,
    year: int,
    league_display_name: str
) -> List[Dict[str, Any]]:
    """
    전체 시즌(1~12월)의 모든 경기를 스크래핑합니다.

    2단계 스크래핑 전략:
        [1단계] URL 수집: 1~12월의 모든 경기 URL을 먼저 수집
                        - 빠른 탐색으로 전체 경기 수 파악
                        - 월별로 순회하며 URL만 추출
        [2단계] 데이터 수집: 수집된 URL로부터 상세 데이터 추출
                           - 단일 진행률 바로 진행 상황 표시
                           - 각 경기 페이지 접속 및 데이터 파싱

    이 전략의 장점:
        - 사용자에게 총 경기 수를 사전에 알려줌
        - 전체 진행률을 하나의 바로 표시 (UX 개선)
        - 월별 구분 없이 연속적인 수집 가능

    Args:
        league_category: 리그 카테고리 코드 (j1, j2, j3, playoff, 2playoff)
        year: 시즌 연도
        league_display_name: 사용자에게 표시할 리그 이름
                            예: "J리그1", "J리그2", "J리그1PO"

    Returns:
        List[Dict[str, Any]]: 시즌 전체 경기 데이터 리스트

    Note:
        - WebDriver는 함수 종료 시 자동 종료 (finally 블록)
        - 월별 페이지 로드 실패는 무시하고 계속 진행
        - 개별 경기 수집 실패 시에도 다른 경기는 계속 수집
    """
    driver = setup_chrome_driver()
    season_data = []

    try:
        # ====================================================================
        # [1단계] 전체 시즌 URL 수집
        # ====================================================================
        all_match_urls = []

        for month in range(1, 13):  # 1월 ~ 12월
            # 월별 경기 목록 URL 생성
            url = JLEAGUE_SEARCH_URL.format(
                league=league_category,
                year=year,
                month=month
            )
            driver.get(url)

            try:
                # 경기 목록 로딩 대기
                WebDriverWait(driver, MATCH_LIST_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "section.matchlistWrap"))
                )

                # 경기 링크 요소 찾기
                match_link_elements = driver.find_elements(By.CSS_SELECTOR, MATCH_LIST_SELECTOR)

                # URL 추출
                month_urls = [
                    link.get_attribute("href")
                    for link in match_link_elements
                    if link.get_attribute("href")
                ]

                # 전체 URL 리스트에 추가
                all_match_urls.extend(month_urls)

            except TimeoutException:
                # 해당 월에 경기가 없거나 로딩 실패 시 건너뛰기
                continue
            except Exception:
                # 기타 오류 발생 시에도 계속 진행
                continue

        # 수집 시작 안내 메시지 출력
        console = Console()
        console.print(
            f"\n[bold magenta][{year}년 {league_display_name} 경기 데이터] "
            f"(총 {len(all_match_urls)}경기)[/bold magenta]",
            style="bold"
        )

        # ====================================================================
        # [2단계] 경기 상세 데이터 수집
        # ====================================================================
        for match_url in track(all_match_urls, description=f"[cyan]수집 현황:[/cyan]"):
            match_data = scrape_single_match(match_url, year, league_display_name)
            if match_data:
                season_data.append(match_data)

    finally:
        # 리소스 정리: WebDriver 종료
        driver.quit()

    return season_data


def collect_jleague_match_data(
    year: int | List[int],
    league: str | List[str] = "J리그1"
) -> Tuple[List[Dict[str, Any]], str]:
    """
    J리그 경기 데이터를 수집하는 최상위 공개 API 함수입니다.

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

    Returns:
        Tuple[List[Dict[str, Any]], str]:
            - List[Dict[str, Any]]: 수집된 경기 데이터 리스트
            - str: 파일 저장에 사용할 파일명 (확장자 제외)
                  형식: "{리그}_{타입}_{연도}"
                  예: "j1_match_2025", "jleague_match_2023-2025"

    Raises:
        KeyError: 지원하지 않는 리그 이름이 입력된 경우
        ValueError: 잘못된 연도 범위가 입력된 경우

    Note:
        - 개별 시즌 수집 실패 시 에러 메시지 출력 후 계속 진행
        - 수집 진행 상황은 콘솔에 실시간으로 표시됨
        - 빈 데이터가 반환될 수 있음 (모든 수집 실패 시)
    """
    # ========================================================================
    # 리그 이름 → URL 카테고리 매핑 테이블
    # ========================================================================
    LEAGUE_TO_CATEGORY: Dict[str, str] = {
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
    # 파일명 생성
    # ========================================================================
    # 단일 리그: 리그 코드 사용 (예: "j1")
    # 여러 리그: 통합 레이블 사용 (예: "jleague")
    if len(league_list) == 1:
        league_label: str = LEAGUE_TO_CATEGORY[league_list[0]]
    else:
        league_label = "jleague"

    # ========================================================================
    # 데이터 수집 (중첩 루프: 리그 × 연도)
    # ========================================================================
    dataset: List[Dict[str, Any]] = []

    for league_name in league_list:
        # 리그 이름을 URL 카테고리로 변환
        league_category = LEAGUE_TO_CATEGORY[league_name]

        for year_val in years:
            try:
                # 시즌 데이터 수집
                season_data = scrape_season_matches(
                    league_category,
                    year_val,
                    league_name
                )
                dataset.extend(season_data)

            except Exception as e:
                # 개별 시즌 실패 시 에러 로그 출력 후 계속 진행
                print(f"⛔ {year_val}년 {league_name} 수집 중 에러 발생: {e}")

    # ========================================================================
    # 결과 반환
    # ========================================================================
    file_name = f"{league_label}_match_{year_label}"
    return dataset, file_name
