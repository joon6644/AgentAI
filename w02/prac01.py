from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # .env 파일을 읽어 OPENAI_API_KEY를 환경변수로 등록

# API 클라이언트 생성 (환경변수 OPENAI_API_KEY를 자동으로 사용)
client = OpenAI()
 
response = client.chat.completions.create( 
    model="gpt-4o-mini", 
    messages=[ 
        {"role": "system", "content": "당신은 친절한 조교입니다."}, 
        {"role": "user", "content": "생성형 AI를 한 문장으로 설명해줘."} 
    ], 
    temperature=0.7, 
    max_completion_tokens=200 
) 
 
print(response.choices[0].message.content)