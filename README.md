# AgentAI

CrewAI / LangGraph 기반 AI Agent 프로젝트 워크스페이스입니다.

## 🛠️ 개발 환경

| 항목 | 값 |
| --- | --- |
| Python | 3.12.14 (`.python-version` 으로 고정) |
| 패키지 관리 | [uv](https://docs.astral.sh/uv/) (`uv.lock` 으로 버전 고정) |
| 가상환경 | `.venv` |
| 주요 라이브러리 | `crewai`, `langgraph` |

Python 버전과 모든 의존성 버전이 `.python-version` + `uv.lock` 에 고정되어 있어,
어떤 PC에서 클론하더라도 완전히 동일한 환경이 재현됩니다.

## 🚀 빠른 시작

클론 후 아래 한 줄이면 Python 설치 → 가상환경 생성 → 의존성 설치 → 검증까지 끝납니다.
(uv 가 없으면 자동으로 설치합니다.)

```powershell
# Windows PowerShell
.\scripts\setup.ps1
```

```bash
# macOS / Linux / Git Bash
bash scripts/setup.sh
```

## 📦 수동 설치

### 방법 1. uv 사용 (권장)

```bash
# uv 설치 (최초 1회)
#   Windows : irm https://astral.sh/uv/install.ps1 | iex
#   macOS/Linux : curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync
```

`uv sync` 가 `.python-version` 을 읽어 **Python 3.12.14 를 자동으로 내려받고**,
`uv.lock` 에 고정된 버전 그대로 `.venv` 에 설치합니다. 별도로 Python을 미리 깔 필요가 없습니다.

> ⚠️ Python 3.12.14 다운로드는 uv 0.12.9 이상에서만 지원됩니다.
> 구버전이라면 `uv self update` 를 먼저 실행하세요. (`pyproject.toml` 에 최소 버전이 명시되어 있습니다.)

### 방법 2. uv 없이 pip 사용

```bash
python -m venv .venv

# 활성화
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
source .venv/bin/activate         # macOS / Linux

pip install -r requirements.txt -r requirements-dev.txt
```

`requirements*.txt` 는 `uv.lock` 에서 생성된 파일이라 버전이 동일하게 고정되어 있습니다.
다만 Python 자체 버전(3.12.14)은 직접 맞춰야 합니다.

## 🔑 환경 변수

```bash
cp .env.example .env    # Windows: copy .env.example .env
```

`.env` 에 사용하는 LLM 제공자의 API 키를 채워 넣으세요. `.env` 는 커밋되지 않습니다.

## ✅ 환경 검증

```bash
uv run pytest
```

`tests/test_environment.py` 가 Python 버전 고정 여부, CrewAI 임포트,
LangGraph 그래프 실행까지 확인합니다.

## 🧹 린트 / 포맷

```bash
uv run ruff check .     # 검사
uv run ruff format .    # 포맷
```

## ➕ 의존성 추가

```bash
uv add <패키지>              # 런타임 의존성
uv add --dev <패키지>        # 개발 의존성
```

추가 후에는 `requirements*.txt` 도 함께 갱신해 주세요.

```bash
uv export --no-hashes --no-emit-project --no-dev --format requirements.txt -o requirements.txt
uv export --no-hashes --no-emit-project --only-group dev --format requirements.txt -o requirements-dev.txt
```

## 📁 프로젝트 구조

```
AgentAI/
├── .python-version          # Python 버전 고정 (3.12.14)
├── pyproject.toml           # 프로젝트 메타데이터 및 의존성 정의
├── uv.lock                  # 전체 의존성 버전 잠금 (커밋 대상)
├── requirements.txt         # pip 사용자용 런타임 의존성
├── requirements-dev.txt     # pip 사용자용 개발 의존성
├── .env.example             # 환경 변수 템플릿
├── scripts/
│   ├── setup.ps1            # Windows 환경 구축 스크립트
│   └── setup.sh             # macOS/Linux 환경 구축 스크립트
└── tests/
    └── test_environment.py  # 환경 검증 스모크 테스트
```
