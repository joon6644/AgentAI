"""CrewAI 버전: 리서처 + 작가 2-에이전트 Q&A 봇

[같은 구조] langgraph_agent.py 와 완전히 같은 시나리오를 구현한다.
  - 툴      : web_search(일반) / news_search(뉴스) / scholar_search(논문) — Serper API.
              리서처가 질문을 보고 알맞은 툴을 스스로 고른다.
  - 에이전트: researcher(툴 사용) -> writer(툴 없음, 답변 작성)
  - 단기메모리: 한 세션 동안 이전 대화를 기억해 "그거", "아까 그" 같은 후속 질문을 이해

[CrewAI 다운 점]
  - 에이전트 = role / goal / backstory 를 가진 "사람" 객체로 선언한다.
  - 툴 호출 루프는 Agent 내부에 숨어 있다. tools=[...] 만 넘기면 알아서 반복한다.
  - 에이전트 간 데이터 전달 = Task(context=[이전 Task]) 로 선언만 하면 된다.
  - 단기메모리 = Crew(memory=Memory(...)).
    Task 결과를 LLM 이 요약·임베딩해 벡터DB에 저장하고, 다음 Task 실행 전에
    질문과 "의미상 관련 있는" 기억만 골라 프롬프트에 자동으로 넣어준다.
    => 대화 원문이 아니라 "검색으로 떠올리는 기억" 방식.
    여기서는 임시 폴더에 저장하고 종료 시 지워서 세션 한정(단기)으로 만든다.

실행: uv run python study/crewai_agent.py
"""

import os
import tempfile
from datetime import date

import httpx
from crewai import LLM, Agent, Crew, Process, Task
from crewai.memory import Memory
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o-mini"
SEARCH_RESULTS = 5  # 검색 1회당 가져올 결과 수
MAX_SEARCH_ROUNDS = 2  # 리서처가 툴을 부를 수 있는 최대 횟수(라운드)


# ── 1. 툴 ─────────────────────────────────────────────────────────────
def _serper(endpoint: str, query: str) -> str:
    """Serper API 공통 호출. 실패해도 예외 대신 '검색 실패' 문자열을 돌려준다.
    (예외가 나면 에이전트가 결과 없이 답을 지어내기 쉽다)"""
    print(f"  [웹 리서처 → {endpoint} 검색] {query}")
    try:
        resp = httpx.post(
            f"https://google.serper.dev/{endpoint}",
            headers={"X-API-KEY": os.environ["SERPER_API_KEY"]},
            json={"q": query, "num": SEARCH_RESULTS, "hl": "ko"},
            timeout=20,
        )
        resp.raise_for_status()
    except (httpx.HTTPError, KeyError) as e:
        return f"검색 실패({type(e).__name__}: {e}). 이 검색으로는 아무 정보도 얻지 못했다."
    items = resp.json().get("news" if endpoint == "news" else "organic", [])
    items = items[:SEARCH_RESULTS]  # scholar / news 는 num 을 무시하고 10개 이상 준다
    if not items:
        return "검색 결과 없음."
    lines = []
    for i in items:
        # 학술은 publicationInfo(저자/학회/연도), 뉴스는 source/date(언론사/게재 시점)가 추가로 온다
        meta = i.get("publicationInfo") or " · ".join(
            filter(None, [i.get("source"), i.get("date")])
        )
        lines.append(
            "\n  ".join(filter(None, [f"- {i['title']}", meta, i.get("snippet"), i["link"]]))
        )
    return "\n\n".join(lines)


@tool("web_search")
def web_search(query: str) -> str:
    """일반 웹 검색(구글). 시세, 제품, 버전, 사용법 등 일반적인 사실 확인에 쓴다."""
    return _serper("search", query)


@tool("news_search")
def news_search(query: str) -> str:
    """뉴스 검색(구글 뉴스). 기업·시장·사건의 최근 소식을 찾을 때 쓴다. 언론사·게재 시점 포함."""
    return _serper("news", query)


@tool("scholar_search")
def scholar_search(query: str) -> str:
    """학술 검색(구글 스칼라). 논문·연구·학술자료를 찾을 때 쓴다. 저자/학회/연도가 함께 온다."""
    return _serper("scholar", query)


# ── 2. 에이전트 ───────────────────────────────────────────────────────
researcher = Agent(
    role="웹 리서처",
    goal="사용자 질문에 필요한 사실을 웹에서 찾아 출처와 함께 정리한다",
    backstory="검색어를 잘 고르고, 이전 대화 맥락에서 '그거'가 무엇인지 정확히 짚어낸다.",
    # 어떤 툴을 쓸지는 에이전트가 docstring 을 보고 결정
    tools=[web_search, news_search, scholar_search],
    max_iter=MAX_SEARCH_ROUNDS,  # 이 횟수를 넘기면 CrewAI 가 툴 없이 최종 답을 강제
    llm=LLM(model=MODEL, temperature=0),
    verbose=False,
)
writer = Agent(
    role="테크 라이터",
    goal="조사 결과를 바탕으로 간결하고 정확한 한국어 답변을 쓴다",
    backstory="어려운 기술 내용을 초보자도 이해하게 풀어 쓰는 작가.",
    llm=LLM(model=MODEL, temperature=0.3),
    verbose=False,
)


# ── 3. 태스크 ─────────────────────────────────────────────────────────
research_task = Task(
    description=(
        "오늘 날짜: {today}\n사용자 질문: {question}\n"
        "이전 대화 기억이 있으면 참고해 질문이 가리키는 대상을 파악하세요. "
        "논문·연구는 scholar_search, 뉴스·최근 소식은 news_search, "
        "그 외에는 web_search 로 사실을 확인하세요. "
        "검색 결과는 질문의 핵심 대상과 조건을 모두 만족할 때만 관련 있다고 보고, "
        "대상이 다르면(비슷한 주제라도) 버리세요. "
        "주가·수치·뉴스처럼 시점에 따라 바뀌는 정보는 기준 날짜(또는 게재 시점)를 함께 적으세요. "
        "관련 결과가 없거나 검색에 실패했다면 '관련 자료를 찾지 못함'이라고 명시하세요."
    ),
    expected_output="질문과 직접 관련된 사실·출처 링크 bullet 목록 (없으면 '자료를 찾지 못함')",
    agent=researcher,
)
write_task = Task(
    description=(
        "오늘 날짜: {today}\n사용자 질문: {question}\n"
        "리서처의 조사 결과를 근거로 답변을 작성하세요. "
        "질문이 요구한 항목은 빠짐없이 다루되 간결하게 쓰세요.\n"
        "- 사실(수치·사건·논문·링크)은 조사 결과에 있는 것만 쓰고 절대 만들지 마세요. "
        "시점이 있는 수치는 기준 날짜를 함께 적으세요.\n"
        "- 분석·전망·시나리오를 요청받으면 조사 결과의 사실을 근거로 추론해도 됩니다. "
        "단, '분석'임을 밝히고 각 시나리오마다 근거가 된 사실을 적으세요. "
        "'가능성이 높다' 같은 확률 판단은 하지 마세요.\n"
        "- 자료가 질문과 일부만 관련 있으면 그 한계를 밝히고, "
        "관련 자료를 찾지 못했다면 솔직히 찾지 못했다고 답하세요."
    ),
    expected_output="질문의 모든 항목을 다룬 간결한 한국어 답변 + 마지막 줄에 출처 링크",
    agent=writer,
    context=[research_task],  # 리서처 결과를 작가에게 넘긴다
)


# ── 4. 크루 + 대화 루프 ───────────────────────────────────────────────
def main() -> None:
    with tempfile.TemporaryDirectory() as memory_dir:  # 종료 시 기억 삭제 -> 단기메모리
        crew = Crew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            process=Process.sequential,
            memory=Memory(storage=memory_dir, llm=MODEL),
        )
        print("CrewAI 2-에이전트 봇 (빈 줄 입력 시 종료)")
        while question := input("\n질문> ").strip():
            # inputs 의 값이 Task description 의 {question}, {today} 자리에 채워진다
            today = date.today().isoformat()
            result = crew.kickoff(inputs={"question": question, "today": today})
            # 실행이 모두 끝난 뒤, 태스크 순서대로 각 에이전트의 결과를 꺼낸다
            for task_output in result.tasks_output:
                print(f"\n[{task_output.agent}]\n{task_output.raw}")
            print(f"  (토큰 사용: {result.token_usage.total_tokens})")


if __name__ == "__main__":
    main()
