"""환경 구축이 올바르게 되었는지 확인하는 스모크 테스트."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_python_version_matches_pin() -> None:
    """실행 중인 파이썬이 .python-version 에 고정한 버전과 일치해야 한다."""
    pinned = (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip()
    actual = ".".join(str(part) for part in sys.version_info[:3])
    assert actual == pinned, f"pinned={pinned}, actual={actual}"


def test_dotenv_importable() -> None:
    import dotenv

    assert hasattr(dotenv, "load_dotenv")


def test_crewai_importable() -> None:
    """CrewAI 핵심 클래스가 임포트되어야 한다."""
    from crewai import Agent, Crew, Task

    assert all(isinstance(cls, type) for cls in (Agent, Crew, Task))


def test_langgraph_runs_a_graph() -> None:
    """LangGraph 그래프가 실제로 컴파일되고 실행되어야 한다 (LLM 호출 없음)."""
    from typing import TypedDict

    from langgraph.graph import END, START, StateGraph

    class State(TypedDict):
        value: int

    def double(state: State) -> State:
        return {"value": state["value"] * 2}

    graph = StateGraph(State)
    graph.add_node("double", double)
    graph.add_edge(START, "double")
    graph.add_edge("double", END)

    assert graph.compile().invoke({"value": 21}) == {"value": 42}
