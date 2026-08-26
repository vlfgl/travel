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
    """Gemini에게 여행지를 추천받아 지역명 리스트 반환"""
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
{date}에 여행하기 좋은 한국 국내 여행지 3곳을 추천해줘.
반드시 아래 JSON 형식으로만 답해줘. 다른 설명은 하지 마.

{{
  "recommendations": [
    {{"region": "지역명", "reason": "추천 이유"}},
    {{"region": "지역명", "reason": "추천 이유"}},
    {{"region": "지역명", "reason": "추천 이유"}}
  ]
}}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    text = response.text.strip()

    # 혹시 ```json ... ``` 감싸져 있으면 제거
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


# ─────────────────────────────────────
# 6. 메인 실행 흐름
# ─────────────────────────────────────
def main():
    # argparse 설정
    parser = argparse.ArgumentParser(description="여행지 + 맛집 추천 프로그램")
    parser.add_argument(
        "--date",
        type=validate_date,
        required=True,
        help="여행 날짜 (YYYY-MM-DD 형식)",
    )
    args = parser.parse_args()
    date = args.date

    print(f"🗓️  {date} 여행 정보를 준비하고 있어요...\n")

    # 최종 저장할 데이터 구조
    results = {
        "date": date,
        "recommendations": [],
        "errors": [],
    }

    try:
        # 1) Gemini로 여행지 추천
        print("🤖 Gemini에게 여행지 추천받는 중...")
        gemini_result = get_travel_recommendation(date)
        results["raw_gemini_response"] = gemini_result  # 원본 저장

        # 2) 각 여행지마다 맛집 검색
        for rec in gemini_result["recommendations"]:
            region = rec["region"]
            print(f"🍴 '{region}' 맛집 검색 중...")

            entry = {
                "region": region,
                "reason": rec["reason"],
                "restaurants": [],
            }

            try:
                entry["restaurants"] = search_restaurants(region)
            except Exception as e:
                # 맛집 검색 실패해도 전체는 계속 진행
                error_msg = f"[{region}] 맛집 검색 실패: {e}"
                print(f"⚠️  {error_msg}")
                results["errors"].append(error_msg)

            results["recommendations"].append(entry)

    except Exception as e:
        error_msg = f"Gemini 추천 실패: {e}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)

    # 3) 결과 저장
    save_results(date, results)
    print("\n🎉 완료!")


if __name__ == "__main__":
    main()