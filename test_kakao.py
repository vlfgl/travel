import os
import requests
from dotenv import load_dotenv

# 1) .env 파일에서 환경변수 불러오기
load_dotenv()
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# 2) 카카오 로컬 검색 API 주소
url = "https://dapi.kakao.com/v2/local/search/keyword.json"

# 3) 인증 헤더 (카카오는 이 형식이 필수!)
headers = {
    "Authorization": f"KakaoAK {KAKAO_API_KEY}"
}

# 4) 검색 조건 (파라미터)
params = {
    "query": "광안리 맛집",  # 검색할 키워드
    "size": 5               # 결과 개수 (최대 15)
}

# 5) API 요청 보내기
response = requests.get(url, headers=headers, params=params)
data = response.json()

# 6) 결과 출력
print(data)   # ← 이 줄 추가! 카카오가 뭐라고 답했는지 확인
print()

for place in data["documents"]:
    print("🍽️", place["place_name"])
    print("   📍", place["address_name"])
    print("   📞", place["phone"])
    print()