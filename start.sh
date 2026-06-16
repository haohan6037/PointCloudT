#!/bin/bash
# ============================================================================
# GardenOS Mowing Platform — 启动脚本
# 用法: ./start.sh
# ============================================================================
set -euo pipefail

# 进入项目根目录
cd "$(dirname "$0")"

# ── 加载环境变量 ─────────────────────────────────────────────
if [ -f "mowing-platform/.env" ]; then
    echo "📄 加载 mowing-platform/.env"
    set -a
    source <(grep -v '^#' mowing-platform/.env | grep -v '^$')
    set +a
elif [ -f ".env" ]; then
    echo "📄 加载 .env"
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
fi

# ── 默认 PostgreSQL 配置 ─────────────────────────────────────
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5433}"
export PGDATABASE="${PGDATABASE:-MyGardenOSManagementSyetem}"
export PGUSER="${PGUSER:-happyfamily}"

# ── 检查 PostgreSQL 连接 ─────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        GardenOS 割草服务平台 v0.1.0                      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  数据库: postgresql://${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE}"
echo "║  服务地址: http://127.0.0.1:8011"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if command -v psql &> /dev/null; then
    if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "SELECT 1" > /dev/null 2>&1; then
        echo "✅ PostgreSQL 连接成功"
    else
        echo "⚠️  PostgreSQL 连接失败 — 将使用内存存储模式"
        echo "   请检查 PostgreSQL 是否运行：brew services start postgresql@16"
    fi
else
    echo "⚠️  未检测到 psql 命令行工具 — 跳过数据库连接检查"
fi

echo ""
echo "🚀 启动服务..."

# ── 安装依赖（如需） ─────────────────────────────────────────
if [ ! -d "mowing-platform/.venv" ] && command -v uv &> /dev/null; then
    echo "📦 安装 Python 依赖..."
    cd mowing-platform
    uv sync
    cd ..
fi

# ── 启动 uvicorn ────────────────────────────────────────────
exec python3 -m uvicorn app:app \
    --app-dir mowing-platform \
    --host 127.0.0.1 \
    --port 8011 \
    --log-level info
