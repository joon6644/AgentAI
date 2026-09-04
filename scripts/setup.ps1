# AgentAI 개발 환경 구축 (Windows PowerShell)
# 사용법:  .\scripts\setup.ps1
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "[1/3] uv 확인 중..." -ForegroundColor Cyan
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv 가 없어 설치합니다..." -ForegroundColor Yellow
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
} else {
    # 최신 uv 를 권장하지만 필수는 아니므로, 실패해도 설치를 계속 진행
    try { uv self update } catch { Write-Host "uv 업데이트를 건너뜁니다." -ForegroundColor DarkGray }
}

Write-Host "[2/3] Python 및 의존성 설치 중..." -ForegroundColor Cyan
uv sync

Write-Host "[3/3] 환경 검증 중..." -ForegroundColor Cyan
uv run pytest -q

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env 파일을 생성했습니다. API 키를 채워주세요." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "환경 구축 완료. 활성화: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
