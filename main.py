import sys
import os
import re
import json
import argparse
from datetime import datetime

import requests
from dotenv import load_dotenv
from google import genai


# 1. 환경변수 로드
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")


# 2. 날짜 형식 검증 함수
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


# 3. Gemini로 여행지 추천받기
def get_travel_recommendation(date):
    """Gemini에게 여행지를 추천받아 스키마에 맞는 dict 반환 (실패 시 1회 재시도)"""
    client = genai.Client(api_key=GEMINI_API_KEY)

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

    # 최대 2번 시도 (첫 시도 + 재시도 1회)
    last_error = None
    for attempt in range(2):
        try:
            # 재시도일 때는 프롬프트를 더 강하게
            current_prompt = prompt
            if attempt > 0:
                current_prompt = prompt + "\n\n⚠️ 반드시 순수 JSON만! 마크다운(```)이나 설명 없이!"
                print("   🔄 JSON 파싱 실패, 재요청 중...")

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=current_prompt,
            )

            text = response.text.strip()
            # ```json ... ``` 감싸져 있으면 제거
            text = re.sub(r"^```json\s*|\s*```$", "", text).strip()

            return json.loads(text)  # 성공하면 바로 반환

        except json.JSONDecodeError as e:
            last_error = e
            continue  # 다음 시도로

    # 2번 다 실패하면 예외 발생
    raise ValueError(f"JSON 파싱 2회 실패: {last_error}")


# 4. Kakao로 맛집 검색하기
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


# 5. 결과를 JSON 파일로 저장
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

def check_api_keys():
    """API 키가 설정됐는지 확인. 없으면 안내 후 종료"""
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not KAKAO_API_KEY:
        missing.append("KAKAO_API_KEY")

    if missing:
        print("❌ API 키가 설정되지 않았어요!")
        print(f"   누락된 키: {', '.join(missing)}")
        print("\n📝 설정 방법:")
        print("   1. 프로젝트 폴더에 .env 파일을 만드세요")
        print("   2. 아래 내용을 추가하세요:")
        print("      GEMINI_API_KEY=your_gemini_key")
        print("      KAKAO_API_KEY=your_kakao_key")
        sys.exit(1)  # 프로그램 즉시 종료 (에러 코드 1)
        
        
def generate_final_report(recommendation, restaurants, date, errors):
    """1차 추천 + 맛집 목록으로 최종 Markdown 리포트 생성"""
    client = genai.Client(api_key=GEMINI_API_KEY)

    # 맛집 목록을 텍스트로 정리 (0건이면 "데이터 없음")
    if restaurants:
        restaurant_text = "\n".join(
            f"- {r['name']} ({r['address']})"   # ← name, address 사용!
            for r in restaurants
        )
    else:
        restaurant_text = "데이터 없음"

    prompt = f"""
아래 여행 정보를 바탕으로 '{date}' 여행 리포트를 Markdown으로 작성해줘.

[추천 지역] {recommendation['recommended_city']}
[추천 이유] {recommendation['reason']}
[날씨] {recommendation['weather']}
[행사/축제] {', '.join(recommendation['events'])}
[맛집 목록]
{restaurant_text}

반드시 아래 구조의 Markdown으로 작성해줘:

# 🧳 {date} {recommendation['recommended_city']} 여행 리포트

## 📍 추천 지역 & 이유
## 🌤️ 날씨 요약
## 🎉 행사 / 축제
## 🍽️ 맛집 리스트
## 🗓️ 1일 일정 제안
### 오전 / 오후 / 저녁

맛집이 "데이터 없음"이면 그대로 "데이터 없음"이라고 표기해줘.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        report = response.text
    except Exception as e:
        errors.append(f"리포트 생성 실패: {e}")
        report = "# 리포트 생성 실패\n\n리포트를 생성하지 못했습니다."

    # errors 섹션 추가
    if errors:
        report += "\n\n## ⚠️ 처리 중 발생한 오류\n"
        report += "\n".join(f"- {e}" for e in errors)

    return report

def save_report(report, date):
    """Markdown 리포트를 .md 파일로 저장"""
    filename = f"travel_report_{date}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 리포트 저장 완료: {filename}")
    
# 6. 메인 실행 흐름
def main():
    check_api_keys()
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

    gemini_result = None  # ← 리포트 생성 여부 판단용

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

    # 4) JSON 결과 저장 (기존 그대로)
    save_results(date, results)

    # 5) 최종 Markdown 리포트 생성 ← 추가!
    if gemini_result is not None:
        print("\n📝 최종 리포트 생성 중...")
        report = generate_final_report(
            gemini_result,
            results.get("restaurants", []),
            date,
            results["errors"],
        )
        save_report(report, date)
        print("\n" + report)  # 화면에도 출력
    else:
        print("⚠️  추천 실패로 리포트를 생성하지 못했어요.")

    print("\n🎉 완료!")

if __name__ == "__main__":
    main()