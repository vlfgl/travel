import os
import re
import json
import argparse
from datetime import datetime

import requests
from dotenv import load_dotenv
from google import genai  # ✅ 신버전 import

# ─────────────────────────────────────
# 1. 환경변수 로드
# ─────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")


# ─────────────────────────────────────
# 2. 날짜 형식 검증 함수
# ─────────────────────────────────────
def validate_date(date_str):
    """YYYY-MM-DD 형식인지 검증"""
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(pattern, date_str):
        raise argparse.ArgumentTypeError(
            f"날짜 형식이 잘못됐어요: '{date_str}' (예: 2025-01-15)"
        )
    # 실제로 존재하는 날짜인지도 확인
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"존재하지 않는 날짜예요: '{date_str}'")
    return date_str


# ─────────────────────────────────────
# 3. Gemini로 여행지 추천받기
# ─────────────────────────────────────
def get_travel_recommendation(date):
    """Gemini에게 여행지를 추천받아 스키마에 맞는 dict 반환"""
    client = genai.Client(api_key=GEMINI_API_KEY)

    # 요구사항 스키마에 맞춘 프롬프트
    prompt = f"""
{date}에 여행하기 좋은 한국 국내 도시 1곳을 추천해줘.
반드시 아래 JSON 형식으로만 답해줘. 다른 설명은 절대 하지 마.

{{
  "recommended_city": "도시명 (예: 제주, 강릉)",
  "weather": "{date} 시기의 일반적인 날씨 요약",
  "events": ["행사/축제1", "행사/축제2", "행사/축제3"],
  "reason": "추천 근거를 2~4문장으로 작성"
}}

주의사항:
- recommended_city는 문자열 1개
- events는 문자열 배열, 1~3개
- reason은 2~4문장
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",   # ✅ 모델명도 수정!
        contents=prompt,
    )

    text = response.text.strip()

    # ```json ... ``` 감싸져 있으면 제거
    text = re.sub(r"^```json\s*|\s*```$", "", text).strip()

    return json.loads(text)


# ─────────────────────────────────────
# 4. Kakao로 맛집 검색하기
# ─────────────────────────────────────
def search_restaurants(region):
    """카카오 로컬 API로 지역 맛집 검색"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {
        "query": f"{region} 맛집",
        "category_group_code": "FD6",  # 음식점 카테고리
        "size": 5,
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # 오류 시 예외 발생

    data = response.json()
    restaurants = []
    for place in data.get("documents", []):
        restaurants.append({
            "name": place["place_name"],
            "address": place["address_name"],
            "phone": place.get("phone", ""),
            "url": place["place_url"],
        })
    return restaurants


# ─────────────────────────────────────
# 5. 결과를 JSON 파일로 저장
# ─────────────────────────────────────
def save_results(date, results):
    """results/ 폴더에 결과 저장"""
    os.makedirs("results", exist_ok=True)  # 폴더 없으면 생성

    filename = f"results/travel_{date}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ 결과 저장 완료: {filename}")

def validate_schema(data):
    """Gemini 응답이 필수 스키마를 지키는지 검증"""

    # 1) 필수 키 존재 확인
    required_keys = ["recommended_city", "weather", "events", "reason"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"필수 키 누락: '{key}'")

    # 2) 타입 검증
    if not isinstance(data["recommended_city"], str):
        raise ValueError("recommended_city는 string이어야 해요")

    if not isinstance(data["weather"], str):
        raise ValueError("weather는 string이어야 해요")

    if not isinstance(data["events"], list):
        raise ValueError("events는 array여야 해요")

    # events 안의 요소가 모두 string인지 확인
    if not all(isinstance(e, str) for e in data["events"]):
        raise ValueError("events의 요소는 모두 string이어야 해요")

    if not isinstance(data["reason"], str):
        raise ValueError("reason은 string이어야 해요")

    # 3) events 개수 검증 (1~3개)
    if not (1 <= len(data["events"]) <= 3):
        raise ValueError(f"events는 1~3개여야 해요 (현재 {len(data['events'])}개)")

    return True

# ─────────────────────────────────────
# 6. 메인 실행 흐름
# ─────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="여행지 + 맛집 추천 프로그램")
    parser.add_argument("--date", type=validate_date, required=True,
                        help="여행 날짜 (YYYY-MM-DD 형식)")
    args = parser.parse_args()
    date = args.date

    print(f"🗓️  {date} 여행 정보를 준비하고 있어요...\n")

    results = {
        "date": date,
        "errors": [],
    }

    try:
        # 1) Gemini 추천
        print("🤖 Gemini에게 여행지 추천받는 중...")
        gemini_result = get_travel_recommendation(date)

        # 2) 스키마 검증 ← 요구사항 필수!
        validate_schema(gemini_result)
        print("✅ 스키마 검증 통과!")

        # 원본 응답 저장
        results["recommended_city"] = gemini_result["recommended_city"]
        results["weather"] = gemini_result["weather"]
        results["events"] = gemini_result["events"]
        results["reason"] = gemini_result["reason"]

        # 3) 추천 도시 맛집 검색
        city = gemini_result["recommended_city"]
        print(f"🍴 '{city}' 맛집 검색 중...")
        try:
            results["restaurants"] = search_restaurants(city)
        except Exception as e:
            error_msg = f"[{city}] 맛집 검색 실패: {e}"
            print(f"⚠️  {error_msg}")
            results["errors"].append(error_msg)
            results["restaurants"] = []

    except Exception as e:
        error_msg = f"처리 실패: {e}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)

    save_results(date, results)
    print("\n🎉 완료!")

if __name__ == "__main__":
    main()