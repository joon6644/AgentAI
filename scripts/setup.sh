#!/usr/bin/env bash
# AgentAI 개발 환경 구축 (macOS / Linux / Git Bash)
# 사용법:  bash scripts/setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[1/3] uv 확인 중..."
if ! command -v uv >/dev/null 2>&1; then
    echo "uv 가 없어 설치합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    # pyproject.toml 의 required-version 을 못 맞추면 Python 3.12.14 를 받을 수 없음
    uv self update || true
fi

echo "[2/3] Python 및 의존성 설치 중..."
uv sync

echo "[3/3] 환경 검증 중..."
uv run pytest -q

if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env 파일을 생성했습니다. API 키를 채워주세요."
fi

echo
echo "환경 구축 완료. 활성화: source .venv/bin/activate"
