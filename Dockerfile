# ---------- 阶段 1：构建前端 ----------
FROM node:20-alpine AS frontend
WORKDIR /build
# 国内镜像源（淘宝 npm）
RUN npm config set registry https://registry.npmmirror.com
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG VITE_BASE=/
ENV VITE_BASE=$VITE_BASE
RUN npm run build

# ---------- 阶段 2：运行镜像（后端 + 前端产物，单容器） ----------
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./
# 国内镜像源（清华 pypi）
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY backend/app ./app
COPY backend/scripts ./scripts
COPY --from=frontend /build/dist ./frontend/dist

# 数据库连接由运行时环境变量注入（deploy.sh 自动读 backend/.env，也可 -e 覆盖）
ENV DATABASE_URL=postgresql+psycopg://root:root@host.docker.internal:5432/kaoyan
# 反代子路径（nginx /kaoyan/ -> 本服务时设为 /kaoyan）
ENV APP_PREFIX=/kaoyan
# 原卷切片/图表体积大且涉版权，不入镜像；部署时用 -v 挂载到 /app/data/assets

EXPOSE 28080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:28080/api/health', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "28080"]
