"""실습 과제: 고객 리뷰 감성분석 & 답변 초안 자동생성 챗봇

읽기(Reading, 리뷰 분석)와 작성(Writing, 답변 초안)을 결합한 실습.
리뷰 5개를 감성 분류(긍정/부정/중립) + 한 줄 요약 + 답변 초안(JSON)으로 처리하고,
결과를 표로 출력한 뒤 총 사용 토큰 수와 부정 리뷰 경고를 확인한다.
"""

import json

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # .env 파일을 읽어 OPENAI_API_KEY를 환경변수로 등록

client = OpenAI()  # OPENAI_API_KEY 환경변수 사용

reviews = [
    "배송이 너무 빨라서 놀랐어요! 포장도 꼼꼼하고 좋았습니다.",
    "제품에 흠집이 나 있었어요. 교환 문의했는데 답이 없네요.",
    "가격 대비 무난한 제품입니다. 특별히 나쁘지도 좋지도 않아요.",
    "고객센터 응대가 정말 불친절했습니다. 다시는 안 살 것 같아요.",
    "디자인이 예쁘고 실용적이에요. 재구매 의사 있습니다.",
]

SYSTEM_PROMPT = """당신은 친절하고 전문적인 고객 응대 담당자입니다.
아래 고객 리뷰를 분석하여 반드시 다음 JSON 형식으로만 응답하세요.
{"sentiment": "긍정|부정|중립", "summary": "한 줄 요약", "reply_draft": "고객에게 보낼 2~3문장 답변 초안"}
"""


def analyze_review(review_text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"리뷰: {review_text}"},
        ],
        temperature=0.3,  # 분류 단계이므로 낮게 설정 -> 응답 일관성 확보
        max_completion_tokens=300,
        response_format={"type": "json_object"},  # JSON 파싱 실패 방지
    )
    content = response.choices[0].message.content
    tokens_used = response.usage.total_tokens
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {"sentiment": "파싱오류", "summary": content, "reply_draft": ""}
    result["tokens_used"] = tokens_used
    return result


# 리뷰 5개를 모두 analyze_review()로 처리하여 results 리스트에 저장
results = []
for review in reviews:
    results.append(analyze_review(review))

# 결과를 표 형태로 출력
df = pd.DataFrame(results)
df.insert(0, "review", reviews)
print(df.to_string(index=False))

total_tokens = df["tokens_used"].sum()
print(f"\n총 사용 토큰: {total_tokens}")

# (심화) 부정 리뷰가 3건 이상이면 경고 메시지 출력 - '판단(Decide)' 단계 흉내
negative_count = (df["sentiment"] == "부정").sum()
if negative_count >= 3:
    print("[경고] 부정 리뷰 비율이 높습니다 - 긴급 검토가 필요합니다.")
