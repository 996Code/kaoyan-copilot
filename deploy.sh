#!/usr/bin/env bash
# 考研助手 · 一键容器化部署（单容器：后端 + 前端产物；数据库用现成的 PG）
#
# 数据库连接读取顺序：
#   1) 环境变量 DATABASE_URL（本次执行时显式传入）
#   2) backend/.env 里的 DATABASE_URL（推荐：线上 PG 信息就配在那里）
#   3) 兜底默认 host.docker.internal:5432（连宿主机发布的 PG）
#
# 用法：
#   ./deploy.sh                      # 常规部署，端口 28080
#   PORT=3000 ./deploy.sh            # 换宿主机端口
#   DATABASE_URL=postgres://... ./deploy.sh   # 临时覆盖数据库
set -e
cd "$(dirname "$0")"

NAME=kaoyan-copilot
PORT="${PORT:-28080}"

# 从 backend/.env 提取配置（存在则用）
ENV_FILE="backend/.env"
DB_URL="${DATABASE_URL:-}"
if [ -z "$DB_URL" ] && [ -f "$ENV_FILE" ]; then
  DB_URL=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' || true)
  echo "==> 使用 $ENV_FILE 中的数据库配置"
fi
[ -z "$DB_URL" ] && DB_URL="postgresql+psycopg://root:root@host.docker.internal:5432/kaoyan" && echo "==> 未找到数据库配置，默认连宿主机 host.docker.internal:5432"

# 容器视角修正：localhost/127.0.0.1 在容器内指向容器自身，须换成宿主机地址
# （线上 .env 配真实 PG 地址时不受影响）
case "$DB_URL" in
  *"@localhost:"*|*"@127.0.0.1:"*)
    DB_URL=$(echo "$DB_URL" | sed -E 's/@(localhost|127\.0\.0\.1):/@host.docker.internal:/')
    echo "==> 已把 localhost 转为 host.docker.internal（容器内无法访问宿主机的 localhost）"
    ;;
esac

VITE_BASE="${VITE_BASE:-/}"
echo "==> 构建镜像 $NAME（国内源：npm 淘宝 / pip 清华，base=$VITE_BASE）"
docker build --build-arg VITE_BASE="$VITE_BASE" -t "$NAME" .

echo "==> 停掉旧容器（若有）"
docker rm -f "$NAME" >/dev/null 2>&1 || true

VOL_ARGS=()
HOST_ASSETS="${HOST_ASSETS_DIR:-$(pwd)/data/assets}"
if [ -d "$HOST_ASSETS" ]; then
  VOL_ARGS+=(-v "$HOST_ASSETS:/app/data/assets:ro")
  echo "==> 挂载原卷切片/图表: $HOST_ASSETS"
else
  echo "==> 提示：$HOST_ASSETS 不存在，原卷切片/图表将不可用（不影响答题判分）"
fi

# 管理员凭据：从 .env 读取并注入容器（避免使用仓库默认值建号）
AUTH_U="${AUTH_USERNAME:-}"
AUTH_P="${AUTH_PASSWORD:-}"
if [ -z "$AUTH_U" ] && [ -f "$ENV_FILE" ]; then
  AUTH_U=$(grep -E '^AUTH_USERNAME=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' || true)
  AUTH_P=$(grep -E '^AUTH_PASSWORD=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' || true)
fi
if [ -z "$AUTH_U" ] || [ -z "$AUTH_P" ]; then
  echo "错误：缺少 AUTH_USERNAME/AUTH_PASSWORD（backend/.env 或环境变量），拒绝以默认凭据部署" >&2
  exit 1
fi

NETWORK="${NETWORK:-}"
NET_ARGS=()
if [ -n "$NETWORK" ]; then
  NET_ARGS+=(--network "$NETWORK")
  echo "==> 加入 Docker 网络: $NETWORK"
fi

echo "==> 启动容器（端口 $PORT）"
docker run -d --name "$NAME" \
  "${NET_ARGS[@]}" \
  -p "${PORT}:28080" \
  -e DATABASE_URL="$DB_URL" \
  -e AUTH_USERNAME="$AUTH_U" \
  -e AUTH_PASSWORD="$AUTH_P" \
  -e APP_PREFIX="${APP_PREFIX:-}" \
  --add-host=host.docker.internal:host-gateway \
  "${VOL_ARGS[@]}" \
  --restart unless-stopped \
  "$NAME" >/dev/null

echo -n "==> 等待健康检查"
for i in $(seq 1 30); do
  if curl -sf "http://localhost:${PORT}/api/health" >/dev/null 2>&1; then
    echo " OK"
    echo ""
    echo "部署完成 ✅  http://localhost:${PORT}   （局域网：http://<本机IP>:${PORT}）"
    echo "数据库：$DB_URL"
    echo "查看日志：docker logs -f $NAME"
    exit 0
  fi
  echo -n "."
  sleep 1
done
echo " 超时！查看日志：docker logs $NAME" >&2
exit 1
