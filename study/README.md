# 개인 공부: CrewAI vs LangGraph

같은 시나리오를 두 프레임워크로 구현해 차이를 비교한다.

- **툴 3개**: `web_search`(일반) / `news_search`(뉴스) / `scholar_search`(논문) — Serper API.
  리서처가 질문에 맞는 툴을 스스로 고른다. 두 파일의 함수 본문이 똑같다.
- **에이전트 2개**: `researcher`(툴 사용) → `writer`(답변 작성)
- **단기메모리**: 한 세션 안에서 후속 질문("그거 언제 나왔어?")을 이해한다.

```bash
uv run python study/crewai_agent.py
uv run python study/langgraph_agent.py
```

`.env` 에 `OPENAI_API_KEY`, `SERPER_API_KEY` 가 필요하다.

## 구현 차이

| 요소 | CrewAI | LangGraph |
| --- | --- | --- |
| 에이전트 정의 | `Agent(role, goal, backstory)` 선언 | 노드 함수 + 시스템 프롬프트 |
| 툴 연결 | `tools=[web_search]` 만 넘기면 됨 | `bind_tools` + `tools` 노드 직접 작성 |
| 툴 호출 루프 | Agent 내부에 숨어 있음 | `researcher ⇄ tools` 엣지로 직접 배선 |
| 검색 한도 | `Agent(max_iter=...)` 옵션 하나 | 툴 호출 횟수를 세서 한도 도달 시 툴 없는 LLM 사용 |
| 에이전트 간 전달 | `Task(context=[research_task])` | 공유 `State` 의 `notes` 키 |
| 실행 순서 | `Process.sequential` | `add_edge` / `add_conditional_edges` |
| 단기메모리 | `Crew(memory=Memory(...))` | `compile(checkpointer=InMemorySaver())` + `thread_id` |
| 메모리 방식 | LLM 이 요약 → 임베딩 → **관련된 기억만 검색**해 주입 | State 의 `messages` 에 **대화 원문을 그대로 누적** |
| 단기로 만드는 법 | 임시 폴더에 저장하고 종료 시 삭제 | 프로세스 메모리라 종료 시 자동 소멸 |

한 줄 요약: CrewAI 는 "누가 무엇을 하는지"를 **선언**하면 흐름이 따라오고,
LangGraph 는 "무엇이 어디로 흐르는지"를 **배선**하면 에이전트가 생긴다.
