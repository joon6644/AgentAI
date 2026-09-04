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
    # 최신 uv 를 권장하지만 필수는 아니므로, 실패해도 설치를 계속 진행
    uv self update || echo "uv 업데이트를 건너뜁니다."
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
