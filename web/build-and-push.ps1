# ─────────────────────────────────────────────────────────────────────────────
# Build and push Strix Console images to Docker Hub.
#
#   1. Start Docker Desktop
#   2. docker login            (enter your Docker Hub credentials yourself)
#   3. ./build-and-push.ps1    (optionally: -Namespace ... -Tag ...)
# ─────────────────────────────────────────────────────────────────────────────
param(
    [string]$Namespace = "ahmedbenhamad",
    [string]$Tag       = "0.1.0",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$backend  = "$Namespace/strix-console-backend"
$frontend = "$Namespace/strix-console-frontend"

Write-Host "==> Building backend: $backend" -ForegroundColor Cyan
docker build -t "${backend}:$Tag" -t "${backend}:latest" "$here/backend"

Write-Host "==> Building frontend: $frontend" -ForegroundColor Cyan
docker build -t "${frontend}:$Tag" -t "${frontend}:latest" "$here/frontend"

if ($SkipPush) {
    Write-Host "==> Skipping push (-SkipPush set). Images built locally." -ForegroundColor Yellow
    exit 0
}

Write-Host "==> Pushing images to Docker Hub..." -ForegroundColor Cyan
docker push "${backend}:$Tag";  docker push "${backend}:latest"
docker push "${frontend}:$Tag"; docker push "${frontend}:latest"

Write-Host "==> Done. Launch with: docker compose -f docker-compose.hub.yml up -d" -ForegroundColor Green
