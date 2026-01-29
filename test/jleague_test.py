import csv
import re
import time
from curl_cffi import requests
from bs4 import BeautifulSoup

# --- 설정값 ---
OUTPUT_FILENAME = "jleague_all_matches.csv"
DELAY_SECONDS = 0.1  # 너무 빠르면 서버에서 차단할 수 있으므로 약간의 딜레이

# 수집할 시즌 및 ID 범위 설정
SEASONS = [
    {"year": 2023, "start": 360094, "end": 360555},
    {"year": 2024, "start": 382848, "end": 383227},
    {"year": 2025, "start": 401456, "end": 401835},
]

# CSV 헤더 순서 정의 (파일 컬럼 순서)
CSV_HEADERS = [
    "season", "game_id", "date", "day", "stadium",          # 메타 정보
    "home_team", "home_score", "away_team", "away_score",   # 스코어
    "home_shoot_total", "home_shoot_ontarget",              # 홈 슈팅
    "away_shoot_total", "away_shoot_ontarget",              # 원정 슈팅
    "home_corner", "away_corner",                           # 코너킥
    "home_offside", "away_offside",                         # 오프사이드
    "home_possession", "away_possession",                   # 점유율
    "home_foul", "away_foul",                               # 파울
    "home_yellow", "away_yellow",                           # 경고
    "home_red", "away_red"                                  # 퇴장
]

def clean_value(value):
    """데이터 정제: 공백 제거, '-'는 '0'으로 변환"""
    if not value: return "0"
    value = value.strip()
    return "0" if value == "-" else value

def get_match_data(game_id, year):
    url = f"https://spodb.spojoy.com/?game_id={game_id}"
    
    try:
        response = requests.get(url, impersonate="chrome110", timeout=10)
        if response.status_code != 200:
            print(f"  [Error] {game_id} 접속 실패: {response.status_code}")
            return None
        
        response.encoding = 'cp949'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 데이터가 없는 페이지(빈 페이지) 체크
        if not soup.body or not soup.body.get_text().strip():
            print(f"  [Skip] {game_id} 데이터 없음")
            return None

        # 결과 저장소 초기화 (모든 키를 미리 0 또는 빈값으로 세팅하여 CSV 오류 방지)
        row = {header: "0" for header in CSV_HEADERS}
        row['season'] = year
        row['game_id'] = game_id
        row['stadium'] = "-"
        row['date'] = "-"
        row['day'] = "-"
        row['home_team'] = ""
        row['away_team'] = ""

        # --- [1] 메타 정보 ---
        full_text = soup.get_text()
        
        # 경기장
        stadium_match = re.search(r'경기장\s*:\s*([^\n\r]+)', full_text)
        if stadium_match:
            row['stadium'] = stadium_match.group(1).strip()

        # 날짜 및 요일 파싱 (YYYY.MM.DD(요) HH:MM)
        date_match = re.search(r'경기일시\s*:\s*([^\n\r]+)', full_text)
        if date_match:
            raw_date = date_match.group(1).strip()
            # 정규식으로 년,월,일,요일,시간 추출
            dp = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})\((.)\)\s*(\d{1,2}:\d{2})', raw_date)
            if dp:
                row['date'] = f"{dp.group(1)}-{dp.group(2).zfill(2)}-{dp.group(3).zfill(2)} {dp.group(5)}:00"
                row['day'] = dp.group(4)
            else:
                row['date'] = raw_date # 파싱 실패시 원본 저장

        # --- [2] 테이블 찾기 ---
        tables = soup.find_all('table')
        score_table = None
        stats_table = None

        for t in tables:
            txt = t.get_text()
            if "최종점수" in txt: score_table = t
            elif "슈팅(유효슈팅)" in txt: stats_table = t

        # --- [3] 스코어 파싱 ---
        if score_table:
            rows = score_table.find_all('tr')
            if len(rows) >= 3:
                h_cols = rows[1].find_all('td')
                a_cols = rows[2].find_all('td')
                
                row['home_team'] = h_cols[0].get_text(strip=True)
                row['home_score'] = clean_value(h_cols[-1].get_text(strip=True))
                row['away_team'] = a_cols[0].get_text(strip=True)
                row['away_score'] = clean_value(a_cols[-1].get_text(strip=True))

        # --- [4] 상세 기록 파싱 ---
        if stats_table:
            stat_rows = stats_table.find_all('tr')
            
            # 맵핑: 텍스트 라벨 -> CSV 컬럼 접미사
            stat_map = {
                "슈팅(유효슈팅)": "shoot",
                "코너킥": "corner", "오프사이드": "offside",
                "볼점유율": "possession", "파울": "foul",
                "경고": "yellow", "퇴장": "red"
            }

            for tr in stat_rows:
                cols = tr.find_all('td')
                if len(cols) != 3: continue
                
                label = cols[1].get_text(strip=True)
                
                if label in stat_map:
                    suffix = stat_map[label]
                    h_val = cols[0].get_text(strip=True)
                    a_val = cols[2].get_text(strip=True)

                    # 슈팅 분리 로직
                    if suffix == "shoot":
                        # Home
                        h_hit = re.search(r'(\d+)\((\d+)\)', h_val)
                        if h_hit:
                            row['home_shoot_total'] = h_hit.group(1)
                            row['home_shoot_ontarget'] = h_hit.group(2)
                        else:
                            row['home_shoot_total'] = clean_value(h_val)
                        
                        # Away
                        a_hit = re.search(r'(\d+)\((\d+)\)', a_val)
                        if a_hit:
                            row['away_shoot_total'] = a_hit.group(1)
                            row['away_shoot_ontarget'] = a_hit.group(2)
                        else:
                            row['away_shoot_total'] = clean_value(a_val)
                    
                    # 일반 데이터 로직
                    else:
                        if suffix == "possession":
                            h_val = h_val.replace('%', '')
                            a_val = a_val.replace('%', '')
                        
                        row[f"home_{suffix}"] = clean_value(h_val)
                        row[f"away_{suffix}"] = clean_value(a_val)
        
        return row

    except Exception as e:
        print(f"  [Error] {game_id} 예외 발생: {e}")
        return None

# --- 메인 실행부 ---
if __name__ == "__main__":
    print(f"🚀 데이터 수집을 시작합니다. 파일명: {OUTPUT_FILENAME}")
    
    # 파일을 쓰기 모드로 열고 헤더 먼저 작성
    with open(OUTPUT_FILENAME, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        
        total_count = 0
        
        for season_info in SEASONS:
            year = season_info['year']
            start_id = season_info['start']
            end_id = season_info['end']
            
            print(f"\n📅 {year} 시즌 데이터 수집 시작 ({start_id} ~ {end_id})")
            
            for game_id in range(start_id, end_id + 1):
                # 진행 상황 출력 (한 줄로 덮어쓰기)
                print(f"   Processing... {year} 시즌 | ID: {game_id}", end='\r')
                
                match_data = get_match_data(game_id, year)
                
                if match_data:
                    # 빈 데이터(팀명이 없는 경우 등) 제외하고 저장
                    if match_data['home_team']:
                        writer.writerow(match_data)
                        total_count += 1
                
                # 서버 부하 방지 딜레이
                time.sleep(DELAY_SECONDS)

    print(f"\n\n✅ 모든 작업 완료! 총 {total_count}개의 경기 데이터가 저장되었습니다.")
