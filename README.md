# 🌍 여행지 추천 프로그램

Gemini AI와 카카오 API를 활용해 날짜를 입력하면
여행지, 날씨, 이벤트, 맛집을 추천해주는 CLI 프로그램입니다.

## 📖 개요
- **Gemini API**: 추천 도시 / 날씨 / 이벤트 / 추천 이유 제공
- **카카오 로컬 API**: 추천 도시의 맛집 검색
- 결과를 **JSON**과 **Markdown 리포트**로 저장

## 🛠️ 설치 방법
```bash
# 1. 저장소 클론
git clone <저장소 URL>
cd <프로젝트 폴더>

# 2. 라이브러리 설치
pip install -r requirements.txt
```

## 🔑 API 키 설정
프로젝트 루트에 `.env` 파일을 만들고 아래처럼 입력하세요:

```
GEMINI_API_KEY=여기에_본인_키
KAKAO_API_KEY=여기에_본인_키
```

- Gemini 키 발급: https://ai.google.dev/
- 카카오 키 발급: https://developers.kakao.com/

## ▶️ 실행 방법
```bash
python main.py --date 2026-01-01
```
- `--date`: 여행 날짜 (형식: `YYYY-MM-DD`)

## 📂 결과물 확인
실행 후 `results/` 폴더에 저장됩니다:
- `travel_2026-01-01.json` : 원본 데이터
- `travel_2026-01-01.md` : 읽기 좋은 리포트

## ⚠️ 주의사항 (API 키 보안)
- **`.env` 파일은 절대 깃허브에 올리지 마세요!**
- `.gitignore`에 `.env`를 반드시 추가하세요.
- API 키가 코드에 직접 노출되지 않도록 주의하세요.
- 키가 유출되면 즉시 재발급하세요.