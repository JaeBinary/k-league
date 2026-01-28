import requests
import json
import re
from typing import Optional, Dict, Any

# --- 1. 상수 및 설정 (Configuration) ---
MATCH_API_URL = "https://www.kleague.com/api/ddf/match/matchRecord.do"
POSSESSION_API_URL = "https://www.kleague.com/api/ddf/match/possession.do"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.kleague.com/match.do",
    "Origin": "https://www.kleague.com",
    "X-Requested-With": "XMLHttpRequest"
}

# matchRecord.do에서 가져올 필드들
TARGET_FIELDS = [
    "possession", "attempts", "onTarget", "fouls", 
    "yellowCards", "redCards", "doubleYellowCards", 
    "corners", "freeKicks", "offsides"
]

# possession.do에서 가져올 필드들
POSSESSION_FIELDS = [
    "first_15", "first_30", "first_45",
    "second_15", "second_30", "second_45"
]

# --- 2. 유틸리티 함수 ---
def to_snake_case(name: str) -> str:
    """카멜케이스(camelCase)를 스네이크케이스(snake_case)로 변환합니다."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

# --- 3. 개별 데이터 수집 함수들 ---

def get_match_record(year: int | str, meet_seq: int | str, game_id: int | str) -> Optional[Dict[str, Any]]:
    """K-League 경기 기본 기록(슈팅, 파울 등)을 가져옵니다."""
    payload = {"year": str(year), "meetSeq": str(meet_seq), "gameId": str(game_id)}

    try:
        response = requests.post(MATCH_API_URL, data=payload, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        data = response.json()

        if data.get("resultCode") != "200" or "data" not in data:
            return None

        records = data["data"]
        match_stats = {} # 여기서는 데이터만 반환 (식별자는 통합 함수에서 관리)

        for team_type in ["home", "away"]:
            team_data = records.get(team_type, {})
            for field in TARGET_FIELDS:
                value = team_data.get(field, 0)
                key_name = f"{team_type}_{to_snake_case(field)}"
                match_stats[key_name] = value

        return match_stats

    except Exception as e:
        print(f"❌ [기본 기록] 요청 에러: {e}")
        return None

def get_possession(year: int | str, meet_seq: int | str, game_id: int | str) -> Optional[Dict[str, float]]:
    """K-League 경기 시간대별 점유율을 가져옵니다."""
    payload = {"year": str(year), "meetSeq": str(meet_seq), "gameId": str(game_id)}

    try:
        response = requests.post(POSSESSION_API_URL, data=payload, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        data = response.json()

        if data.get("resultCode") != "200" or "data" not in data:
            return None

        possession_data = data["data"]
        possession_stats = {}

        for team_type in ["home", "away"]:
            team_stats = possession_data.get(team_type, {})
            for field in POSSESSION_FIELDS:
                raw_value = team_stats.get(field, "0")
                if not raw_value: raw_value = "0"
                
                # 키 이름 충돌 방지를 위해 _possession 접미사 추가
                key_name = f"{team_type}_{field}_possession"
                possession_stats[key_name] = float(raw_value)

        return possession_stats

    except Exception as e:
        print(f"❌ [점유율] 요청 에러: {e}")
        return None

# --- 4. 통합 함수 (Main Wrapper) ---

def get_full_match_data(year: int, meet_seq: int, game_id: int) -> Optional[Dict[str, Any]]:
    """
    모든 경기 데이터를 수집하여 하나의 딕셔너리로 병합합니다.
    """
    # 1. 기본 식별자 생성
    full_data = {
        "year": year,
        "meet_seq": meet_seq,
        "game_id": game_id
    }

    # 2. 기본 기록 수집
    basic_records = get_match_record(year, meet_seq, game_id)
    if basic_records:
        full_data.update(basic_records)
    else:
        # 기본 기록조차 없으면 유효하지 않은 경기로 판단
        return None

    # 3. 점유율 데이터 수집 (선택사항: 실패해도 기본 기록은 살림)
    possession_records = get_possession(year, meet_seq, game_id)
    if possession_records:
        full_data.update(possession_records)
    else:
        print(f"⚠️ Warning: {year}-{game_id} 경기의 상세 점유율 데이터가 없습니다.")

    return full_data

# --- 5. 실행부 ---
if __name__ == "__main__":
    # 테스트: 2025년 1번 경기
    print("🔄 데이터 수집 중...")
    match_result = get_full_match_data(2025, 1, 1)

    if match_result:
        print(f"\n✅ 통합 데이터 수집 완료! (총 컬럼 수: {len(match_result)}개)")
        print("-" * 50)
        print(json.dumps(match_result, indent=4, ensure_ascii=False))
    else:
        print("\n❌ 데이터를 가져오지 못했습니다.")

"""출력 예시:
🔄 데이터 수집 중...

✅ 통합 데이터 수집 완료! (총 컬럼 수: 35개)
--------------------------------------------------
{
    "year": 2025,
    "meet_seq": 1,
    "game_id": 1,
    "home_possession": 65,
    "home_attempts": 15,
    "home_on_target": 4,
    "home_fouls": 3,
    "home_yellow_cards": 0,
    "home_red_cards": 0,
    "home_double_yellow_cards": 0,
    "home_corners": 7,
    "home_free_kicks": 4,
    "home_offsides": 1,
    "away_possession": 35,
    "away_attempts": 6,
    "away_on_target": 4,
    "away_fouls": 13,
    "away_yellow_cards": 3,
    "away_red_cards": 0,
    "away_double_yellow_cards": 0,
    "away_corners": 2,
    "away_free_kicks": 13,
    "away_offsides": 0,
    "home_first_15_possession": 59.21,
    "home_first_30_possession": 61.93,
    "home_first_45_possession": 64.25,
    "home_second_15_possession": 63.72,
    "home_second_30_possession": 68.26,
    "home_second_45_possession": 66.25,
    "away_first_15_possession": 40.79,
    "away_first_30_possession": 38.07,
    "away_first_45_possession": 35.75,
    "away_second_15_possession": 36.28,
    "away_second_30_possession": 31.74,
    "away_second_45_possession": 33.75
}
"""
