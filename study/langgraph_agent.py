"""LangGraph 버전: 리서처 + 작가 2-에이전트 Q&A 봇

[같은 구조] crewai_agent.py 와 완전히 같은 시나리오를 구현한다.
  - 툴      : web_search(일반) / news_search(뉴스) / scholar_search(논문) — Serper API.
              리서처가 질문을 보고 알맞은 툴을 스스로 고른다.
  - 에이전트: researcher(툴 사용) -> writer(툴 없음, 답변 작성)
  - 단기메모리: 한 세션 동안 이전 대화를 기억해 "그거", "아까 그" 같은 후속 질문을 이해

[LangGraph 다운 점]
  - 에이전트 = 그래프의 "노드(함수)". 역할/목표 같은 개념은 프롬프트에 직접 쓴다.
  - 툴 호출 루프(researcher -> tools -> researcher ...)를 엣지로 직접 배선한다.
  - 에이전트 간 데이터 전달 = 공유 State 의 키(notes)에 쓰고 읽기.
  - 단기메모리 = 체크포인터(InMemorySaver) + thread_id.
    매 턴 끝의 State 가 저장되고, 같은 thread_id 로 다시 호출하면 이어서 시작한다.
    => 대화 원문(messages)이 그대로 누적되는 "정확한 기록" 방식.

실행: uv run python study/langgraph_agent.py
"""

import os
from datetime import date
from typing import Annotated, TypedDict

import httpx
from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES, add_messages

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


@tool
def web_search(query: str) -> str:
    """일반 웹 검색(구글). 시세, 제품, 버전, 사용법 등 일반적인 사실 확인에 쓴다."""
    return _serper("search", query)


@tool
def news_search(query: str) -> str:
    """뉴스 검색(구글 뉴스). 기업·시장·사건의 최근 소식을 찾을 때 쓴다. 언론사·게재 시점 포함."""
    return _serper("news", query)


@tool
def scholar_search(query: str) -> str:
    """학술 검색(구글 스칼라). 논문·연구·학술자료를 찾을 때 쓴다. 저자/학회/연도가 함께 온다."""
    return _serper("scholar", query)


TOOLS = {t.name: t for t in (web_search, news_search, scholar_search)}


# ── 2. 공유 State ──────────────────────────────────────────────────────
class State(TypedDict):
    # 사용자 질문 + 최종 답변. add_messages 리듀서로 턴마다 "누적" -> 이것이 단기메모리의 본체
    messages: Annotated[list[AnyMessage], add_messages]
    # 리서처의 이번 턴 작업 공간(툴 호출/결과). 턴 시작마다 비운다.
    scratch: Annotated[list[AnyMessage], add_messages]
    # 리서처 -> 작가로 넘기는 조사 메모
    notes: str


# ── 3. 에이전트(노드) ─────────────────────────────────────────────────
base_llm = ChatOpenAI(model=MODEL, temperature=0)
researcher_llm = base_llm.bind_tools(list(TOOLS.values()))
writer_llm = ChatOpenAI(model=MODEL, temperature=0.3)

RESEARCHER_PROMPT = (
    "당신은 웹 리서처입니다. 오늘 날짜: {today}\n"
    "이전 대화를 참고해 사용자의 최신 질문이 무엇을 가리키는지 파악하세요. "
    "논문·연구는 scholar_search, 뉴스·최근 소식은 news_search, "
    "그 외에는 web_search 로 사실을 확인하세요. "
    "검색 결과는 질문의 핵심 대상과 조건을 모두 만족할 때만 관련 있다고 보고, "
    "대상이 다르면(비슷한 주제라도) 버린 뒤, "
    "핵심 사실과 출처 링크를 bullet 로 정리하세요. "
    "주가·수치·뉴스처럼 시점에 따라 바뀌는 정보는 기준 날짜(또는 게재 시점)를 함께 적으세요. "
    "관련 결과가 없거나 검색에 실패했다면 '관련 자료를 찾지 못함'이라고 명시하세요."
)
WRITER_PROMPT = (
    "당신은 테크 라이터입니다. 오늘 날짜: {today}\n"
    "이전 대화 맥락과 리서처의 조사 메모를 근거로 사용자의 최신 질문에 한국어로 답하세요. "
    "질문이 요구한 항목은 빠짐없이 다루되 간결하게 쓰고, 마지막 줄에 출처 링크를 적으세요.\n"
    "- 사실(수치·사건·논문·링크)은 메모에 있는 것만 쓰고 절대 만들지 마세요. "
    "시점이 있는 수치는 기준 날짜를 함께 적으세요.\n"
    "- 분석·전망·시나리오를 요청받으면 메모의 사실을 근거로 추론해도 됩니다. "
    "단, '분석'임을 밝히고 각 시나리오마다 근거가 된 사실을 적으세요. "
    "'가능성이 높다' 같은 확률 판단은 하지 마세요.\n"
    "- 자료가 질문과 일부만 관련 있으면 그 한계를 밝히고, "
    "관련 자료를 찾지 못했다면 솔직히 찾지 못했다고 답하세요."
)


def researcher(state: State) -> dict:
    # 대화 기록 전체(messages) + 이번 턴 작업(scratch)을 보고 판단
    system = SystemMessage(RESEARCHER_PROMPT.format(today=date.today().isoformat()))
    prompt = [system, *state["messages"], *state["scratch"]]
    # 검색 한도: CrewAI 의 max_iter 를 직접 구현. 한도에 도달하면 툴을 떼고 결론을 내게 한다
    rounds = sum(1 for m in state["scratch"] if isinstance(m, AIMessage) and m.tool_calls)
    llm = researcher_llm if rounds < MAX_SEARCH_ROUNDS else base_llm
    reply = llm.invoke(prompt)
    if reply.tool_calls:
        return {"scratch": [reply]}  # 툴을 부르겠다 -> tools 노드로
    return {"scratch": [reply], "notes": reply.content}  # 조사 끝 -> writer 로


def tools(state: State) -> dict:
    # 마지막 AI 메시지의 tool_calls 를 직접 실행 (prebuilt ToolNode 가 하는 일)
    results = []
    for call in state["scratch"][-1].tool_calls:
        output = TOOLS[call["name"]].invoke(call["args"])
        results.append(ToolMessage(output, tool_call_id=call["id"]))
    return {"scratch": results}


def writer(state: State) -> dict:
    prompt = [
        SystemMessage(WRITER_PROMPT.format(today=date.today().isoformat())),
        *state["messages"],
        HumanMessage(f"[리서처 조사 메모]\n{state['notes']}"),
    ]
    answer = writer_llm.invoke(prompt)
    return {"messages": [AIMessage(answer.content)]}  # 최종 답만 대화 기록에 남긴다


def route_after_researcher(state: State) -> str:
    return "tools" if state["scratch"][-1].tool_calls else "writer"


# ── 4. 그래프 배선 ────────────────────────────────────────────────────
builder = StateGraph(State)
builder.add_node("researcher", researcher)
builder.add_node("tools", tools)
builder.add_node("writer", writer)
builder.add_edge(START, "researcher")
builder.add_conditional_edges("researcher", route_after_researcher, ["tools", "writer"])
builder.add_edge("tools", "researcher")  # 툴 결과를 들고 다시 리서처에게 (ReAct 루프)
builder.add_edge("writer", END)

# 단기메모리: 프로세스 메모리에 체크포인트 저장 -> 프로그램 종료 시 사라짐
graph = builder.compile(checkpointer=InMemorySaver())


# ── 5. 대화 루프 ──────────────────────────────────────────────────────
ROLES = {"researcher": "웹 리서처", "writer": "테크 라이터"}  # 출력용 에이전트 이름


def main() -> None:
    config = {"configurable": {"thread_id": "study-session"}}  # 같은 thread = 같은 기억
    print("LangGraph 2-에이전트 봇 (빈 줄 입력 시 종료)")
    while question := input("\n질문> ").strip():
        inputs = {
            "messages": [HumanMessage(question)],
            "scratch": [RemoveMessage(id=REMOVE_ALL_MESSAGES)],  # 작업 공간만 초기화
        }
        # stream: 노드가 하나 끝날 때마다 그 노드가 State 에 쓴 내용을 실시간으로 받는다
        for update in graph.stream(inputs, config, stream_mode="updates"):
            for node, out in update.items():
                if node == "researcher" and "notes" in out:
                    print(f"\n[{ROLES[node]}]\n{out['notes']}")
                elif node == "writer":
                    print(f"\n[{ROLES[node]}]\n{out['messages'][-1].content}")
        n = len(graph.get_state(config).values["messages"])
        print(f"  (메모리: 대화 메시지 {n}개 보관 중)")


if __name__ == "__main__":
    main()
