# AgentAI

CrewAI / LangGraph 기반 AI Agent 프로젝트 워크스페이스입니다.

## 🛠️ 개발 환경

| 항목 | 값 |
| --- | --- |
| Python | 3.12.10 (`.python-version` 으로 고정) |
| 패키지 관리 | [uv](https://docs.astral.sh/uv/) (`uv.lock` 으로 버전 고정) |
| 가상환경 | `.venv` |
| 주요 라이브러리 | `crewai`, `langgraph` |

Python 버전과 모든 의존성 버전이 `.python-version` + `uv.lock` 에 고정되어 있어,
어떤 PC에서 클론하더라도 완전히 동일한 환경이 재현됩니다.

<details>
<summary>왜 3.12.10 인가</summary>

3.12 는 이미 보안 수정 전용 단계라, **3.12.10 이 공식 바이너리 설치 파일이 제공되는 마지막 릴리스**입니다.
(3.12.11 이후는 소스 tarball 만 배포됩니다.)

- uv 경로: 어느 3.12.x 든 상관없이 동작합니다.
- pip 경로: 설치 파일이 있어야 현실적으로 버전을 맞출 수 있습니다.

즉 3.12.10 은 **두 경로가 모두 성립하는 가장 높은 버전**입니다.
더 낮은 패치(예: 3.12.7)는 버그·보안 수정이 빠질 뿐 얻는 것이 없습니다.

</details>

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

`uv sync` 가 `.python-version` 을 읽어 **Python 3.12.10 을 자동으로 내려받고**,
`uv.lock` 에 고정된 버전 그대로 `.venv` 에 설치합니다.
시스템에 설치된 Python 버전과 무관하게 동작하므로, Python을 미리 깔 필요가 없습니다.

### 방법 2. uv 없이 pip 사용

```bash
python -m venv .venv

# 활성화
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
source .venv/bin/activate         # macOS / Linux

pip install -r requirements.txt -r requirements-dev.txt
```

`requirements*.txt` 는 `uv.lock` 에서 생성된 파일이라 패키지 버전이 동일하게 고정됩니다.
Python 자체는 [3.12.10 공식 설치 파일](https://www.python.org/downloads/release/python-31210/)을
받아 맞추면 되고, 다른 3.12.x 를 쓰더라도 휠 ABI 태그가 `cp312` 로 같아 설치에는 문제가 없습니다.

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
├── .python-version          # Python 버전 고정 (3.12.10)
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
