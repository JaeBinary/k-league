import re
from bs4 import BeautifulSoup

from rich.console import Console
from rich.progress import track

from .scraper import fetch_page 

def parse_game_info(row, year: int, league: str) -> dict:
    """
    단일 뉴스 row를 파싱하여 상세 페이지의 본문(Content)까지 수집합니다.
    """
    base_url = "https://www.kleague.com"

    data = {
        "Meet_Yeer": year,
        "LEAGUE_NAME": league,
        "Round": 0,
        "Title": None,
        "Date": None,
        "View": None,
        "Content": None
    }

    # td 태그들 가져오기
    cols = row.select('td')
    if not cols:
        return None

    # --- [1] 목록에서 기본 정보 추출 (효율성) ---
    # Title (카테고리 제거 로직 포함)
    title_td = cols[1]
    if title_td.find('span'):
        category = title_td.find('span').text
        data["Title"] = title_td.text.replace(category, '').strip().replace("'", "")
    else:
        data["Title"] = title_td.text.strip().replace("'", "")

    # Round (Title에서 "라운드" 앞의 숫자 추출)
    if "라운드" in data["Title"]:
        match = re.search(r'([\d.]+)\s*라운드', data["Title"])
        if match:
            data["Round"] = int(float(match.group(1)))

    # Date, View
    data["Date"] = cols[2].text.strip().replace(".", "-")
    data["View"] = cols[3].text.strip()

    # --- [2] 상세 페이지 접속 및 본문 추출 ---
    if 'onclick' in row.attrs:
        # URL 추출
        relative_url = row['onclick'].split("'")[1]
        url = f"{base_url}{relative_url}"

        # ⭐️ 상세 페이지 요청 (변수명 주의: soup -> detail_soup)
        # 너무 빠른 요청 방지를 위해 약간의 딜레이 권장
        # time.sleep(0.1)
        detail_soup = fetch_page(url)

        if detail_soup:
            # 이미지(image_7e9554.png)에 따른 본문 클래스: div.board-con
            content_div = detail_soup.select_one('div.board-con')

            if content_div:
                # 텍스트만 깔끔하게 추출
                data["Content"] = content_div.text.strip()
            else:
                data["Content"] = "" # 본문 없음

    return data


def collect_kleague_preview_data(year: int | list[int], league: str = "K리그1") -> tuple[str, list]:
    """
    K리그 프리뷰 뉴스 데이터를 수집합니다.

    Args:
        year (int | list[int]): 시즌 연도 또는 년도 범위 리스트
                                예: 2025 → 2025년만 수집
                                    [2023, 2025] → 2023~2025년 모두 수집
        league (str): 리그명 ("K리그1", "K리그2") (기본값: "K리그1")

    Returns:
        str: 년도 레이블 (예: "2025" 또는 "2023-2025")
        list: 수집된 뉴스 정보 리스트
    """

    # 리그 키워드 매핑 (연도별로 다름)
    def get_league_keyword(year_val: int, league: str) -> str:
        if year_val == 2023:
            return "하나원큐%20K리그1" if league == "K리그1" else "하나원큐%20K리그2"
        else:
            return "하나은행%20K리그1" if league == "K리그1" else "하나은행%20K리그2"

    # 년도 처리: int → [int], list → 범위 확장
    if isinstance(year, int):
        years = [year]
        year_label = str(year)
    else:
        years = list(range(min(year), max(year) + 1))
        year_label = f"{min(year)}-{max(year)}"

    # 예시: 1페이지만 수집 (필요 시 반복문으로 확장 가능)
    pages = [1, 2, 3]

    dataset = []  # 모든 페이지의 뉴스를 저장할 리스트
    console = Console()

    for year_val in years:
        keyword = get_league_keyword(year_val, league)
        search_keyword = f"{keyword}%20{year_val}"

        # 먼저 모든 페이지에서 rows를 수집
        all_rows = []
        for page in pages:
            url = f"https://www.kleague.com/news_list.do?search={search_keyword}&category=league&orderBy=seq&page={page}&viewOption=list"
            try:
                soup = fetch_page(url)
                rows = soup.select('div.table-wrap.board-list.list table tbody tr')
                all_rows.extend([(row, year_val, league) for row in rows])
            except Exception as e:
                print(f"⛔ 페이지 로딩 실패 (year={year_val}, page={page}): {e}")

        # 총 기사 수 출력
        console.print(f"\n[bold magenta][{year_val}년 {league} 프리뷰 데이터][/bold magenta] (총 {len(all_rows)}개 라운드)", style="bold")

        # 모든 rows를 하나의 진행 표시줄로 처리
        for row, year_v, league_v in track(all_rows, description=f"[cyan]수집 현황: [/cyan]"):
            try:
                data = parse_game_info(row, year_v, league_v)
                if data:
                    dataset.append(data)
            except Exception as e:
                print(f"⚠️ 파싱 중 에러 발생: {e}")
                continue

    file_name = f"kleague_preview_{year_label}"

    return dataset, file_name
