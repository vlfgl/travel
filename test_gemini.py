import os
from dotenv import load_dotenv
import google.generativeai as genai

# ① .env 파일에서 API 키 불러오기
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# ② Gemini에 키 등록
genai.configure(api_key=api_key)

# ③ 사용할 모델 선택
model = genai.GenerativeModel("gemini-3.6-flash")

# ④ 질문(프롬프트) 보내기
prompt = "부산으로 여행 가려고 해. 가볼 만한 곳 3군데만 추천해줘."
response = model.generate_content(prompt)

# ⑤ 결과 출력
print(response.text)