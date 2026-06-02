# 智能问答系统 Docker 重建脚本
# 在项目根目录运行: .\docker-rebuild.ps1

$ErrorActionPreference = "Stop"

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  智能问答系统 - Docker 重建脚本        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan

# ── 检查 docker 命令 ──
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未找到 docker 命令，请先安装 Docker Desktop" -ForegroundColor Red
    exit 1
}

# ── 模式选择 ──
Write-Host ""
Write-Host "请选择模式:" -ForegroundColor Yellow
Write-Host "  1) 生产模式 (默认，前端预构建，通过 80 端口访问)"
Write-Host "  2) 开发模式 (前端热重载，通过 5173 端口访问)"
$mode = Read-Host "输入 1 或 2 (默认 1)"
if ($mode -eq "2") {
    $profileArg = "--profile", "dev"
    Write-Host "[信息] 启动开发模式" -ForegroundColor Green
} else {
    $profileArg = @()
    Write-Host "[信息] 启动生产模式" -ForegroundColor Green
}

# ── 重建并启动 ──
Write-Host ""
Write-Host "步骤 1/3: 停止并清除旧容器..." -ForegroundColor Yellow
docker compose -f docker/docker-compose.yml down --remove-orphans @profileArg

Write-Host ""
Write-Host "步骤 2/3: 重建镜像..." -ForegroundColor Yellow
docker compose -f docker/docker-compose.yml build @profileArg

Write-Host ""
Write-Host "步骤 3/3: 启动服务..." -ForegroundColor Yellow
docker compose -f docker/docker-compose.yml up -d @profileArg

# ── 检查状态 ──
Write-Host ""
Write-Host "服务状态:" -ForegroundColor Yellow
docker compose -f docker/docker-compose.yml ps

Write-Host ""
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  启动完成!                             ║" -ForegroundColor Cyan
if ($mode -eq "2") {
    Write-Host "║  前端开发地址: http://localhost:5173     ║" -ForegroundColor Cyan
} else {
    Write-Host "║  访问地址: http://localhost              ║" -ForegroundColor Cyan
}
Write-Host "║  后端 API:  http://localhost:8000/api/v1 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Cyan
Write-Host "  查看日志:  docker compose -f docker/docker-compose.yml logs -f backend"
Write-Host "  查看前端:  docker compose -f docker/docker-compose.yml logs -f frontend"
Write-Host "  停止服务:  docker compose -f docker/docker-compose.yml down"
