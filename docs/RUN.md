# 考研助手 · 运行手册

## 容器化部署（推荐，一键）

### 服务器首次部署

```bash
# 服务器上（需已配置 GitHub 私钥）
cd /data && git clone git@github.com:996Code/kaoyan-copilot.git kaoyan-copilot/src
cd kaoyan-copilot/src

# 写 backend/.env（数据库指向现成 PG 容器；按实际改账号密码/地址）
cat > backend/.env <<'EOF'
DATABASE_URL=postgresql+psycopg://llm:<pass>@postgres:5432/kaoyan
AUTH_USERNAME=admin
AUTH_PASSWORD=<你的密码>
EXAM_DATE=2026-12-19
WORDS_PER_DAY=50
EOF

# 一键部署（容器加入 PG 所在的 docker 网络，挂载原卷切片）
HOST_ASSETS_DIR=/data/kaoyan-copilot/data/assets \
NETWORK=llm-modeler_default PORT=28080 bash deploy.sh
```

### 日常更新

```bash
cd /data/kaoyan-copilot/src && git pull && \
HOST_ASSETS_DIR=/data/kaoyan-copilot/data/assets NETWORK=llm-modeler_default PORT=28080 bash deploy.sh
```

部署流程：停掉旧容器 → 构建镜像（npm 淘宝源/pip 清华源）→ 启动新容器 → 健康检查。
数据库连接读 backend/.env（localhost 自动转 host.docker.internal；容器网络内直接写容器名）。

### 子路径反代（nginx /kaoyan/ 前缀）

系统原生支持部署子路径：backend/.env 加 `APP_PREFIX=/kaoyan`，部署时传 `APP_PREFIX=/kaoyan VITE_BASE=/kaoyan/`，
nginx 99 端口 conf 增加（保留前缀透传 + SSE 支持）：

```nginx
location ^~ /kaoyan/ {
    proxy_pass http://127.0.0.1:28080/kaoyan/;
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_buffering off;
    proxy_read_timeout 300s;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
}
```

线上：https://code.996code.top:99/kaoyan/ 。注意部署时 APP_PREFIX/VITE_BASE 必须成对传（deploy.sh 会把空 APP_PREFIX 注入容器覆盖镜像默认值）。
真题数据迁移：本地 `docker exec chatbi-postgres pg_dump -U root -d kaoyan --no-owner > dump.sql`，服务器 `docker exec -i <pg容器> psql -U <user> -d kaoyan < dump.sql`。

### 服务器 PG 归一（2026-11-09）

服务器只有一个 PG：容器 `postgres`（pgvector/pgvector:pg16，双网络 base_996_network + llm-modeler_default，端口 5432，数据卷 /data/postgres/data）。承载全部库：new_api / accounting_assistant / sub2api / llm_modeler / kaoyan。角色：postgres（new-api 等）、llm（llm_modeler + kaoyan，密码见 llm-modeler 原配置）。旧的 postgres:15-alpine 与 llm-modeler-postgres 已删除（备份 dump 在 /data/postgres-migration-backup/）。

数据库连接优先级：环境变量 `DATABASE_URL` > `backend/.env` 的 `DATABASE_URL`（线上 PG 配这里）> 兜底 `host.docker.internal:5432`。`.env` 里写 `localhost` 会自动转换为 `host.docker.internal`（容器内 localhost 指向容器自身）。

```bash
PORT=3000 ./deploy.sh                 # 换宿主机端口
DATABASE_URL=postgres://... ./deploy.sh  # 临时覆盖数据库
docker logs -f kaoyan-copilot         # 看日志
```

说明：`data/assets`（原卷切片/图表）不入镜像，部署脚本检测到目录会自动只读挂载进容器。

## 本地启动（开发模式）

```bash
# 1. 后端（同时服务 API 与前端构建产物；--host 0.0.0.0 支持局域网访问）
cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. 打开 http://localhost:8000 （局域网 http://<本机IP>:8000）
#    多用户：页面自行注册账号；初始管理员 admin/kaoyan2026（.env 的 AUTH_USERNAME/AUTH_PASSWORD）
```

## 系统管理（仅 admin 可见）

登录 admin 账号后顶栏出现「系统管理」：

- **用户管理**：每用户的模考场次/作答数/正确率/待巩固错题/记忆卡/已学词/最近活跃；重置密码；删除用户（**级联清理其全部个人数据**，题库等公共数据不动，管理员账号不可删）
- **LLM 配置**：接口地址 / API Key（打码显示，留空不改）/ 模型名，保存后**立即生效无需重启**，附带「测试连接」；AI 讲解与主观题批改共用此配置，讲解结果按题缓存多用户共享
- **系统统计**：用户/试卷/题目/词汇/模考/作答/记忆卡/AI 缓存总量

## 开发模式（改前端代码时）

```bash
# 后端
cd backend && .venv/bin/uvicorn app.main:app --port 8000 --reload

# 前端热更新（另开终端，自动代理 /api 与 /paper-assets 到 8000）
cd frontend && npm run dev
# 访问 http://localhost:5173
```

## 重建数据（幂等）

```bash
cd backend
.venv/bin/python -I scripts/create_tables.py        # 建缺失表（不动已有数据）
.venv/bin/python -I scripts/reset_tables.py         # ⚠️ 清空重建全部表
.venv/bin/python -I scripts/import_english2.py      # 英二 17 套（增量单套：传参如 2026-2）
.venv/bin/python -I scripts/import_guanzong.py      # 管综 18 套
.venv/bin/python -I scripts/import_vocab.py         # 词汇 5530
.venv/bin/python -I scripts/apply_answer_verdict.py # 答案裁决修正（26 处）
.venv/bin/python -I scripts/verify_data.py          # 数据对账校验
.venv/bin/python -I scripts/crosscheck_gz_answers.py# 管综答案交叉校验
.venv/bin/python -I scripts/fix_en2_2026_dup.py     # 清理历史重复导入的英二题目（幂等）
.venv/bin/python -I scripts/migrate_timezone.py     # 库会话时区设为 Asia/Shanghai（新环境必跑）
```

注意：`reset_tables.py` 后需按顺序重跑全部导入；日常只跑 `verify_data.py` 即可。

## 备份与恢复（生产必配）

```bash
# 备份（服务器默认参数：postgres 容器 / postgres 用户；本地用 PGUSER=root）
bash backup_db.sh                      # → ../backups/kaoyan-时间戳.sql.gz，保留最近 14 份
# 建议 crontab（每天 4:00）：
# 0 4 * * * cd /data/kaoyan-copilot/src && bash backup_db.sh >> /data/kaoyan-copilot/backups/backup.log 2>&1

# 恢复（已演练验证：35 卷 / 1842 题完整还原）
gunzip -c kaoyan-时间戳.sql.gz | docker exec -i postgres psql -U postgres -d kaoyan
```


> 注意：`data/raw`（真题快照）与 `data/assets`（原卷切片/图表）不进 git 仓库。clone 后需自备真题数据放入 `data/raw/`，再按下方「重建数据」执行导入（assets 由导入脚本自动生成）。

## 依赖

- PostgreSQL：Docker 容器 `chatbi-postgres`（localhost:5432，root/root），库 `kaoyan`
- 后端：uv + Python 3.12（backend/.venv），FastAPI + SQLAlchemy
- 前端：Vue3 + Vite + Naive UI + KaTeX（frontend/）

## 已知事项

- 管综 37 题答案标 raw.answer_disputed（一题多卷年份无独立源），报告/练习页有「答案存在版本争议」提示
- 2012/2025 英二大作文图表源仓库缺失
- **LLM 配置存在数据库**（系统管理 → LLM 配置，改动即生效）；.env 不再有 LLM 项。历史迁移：scripts/migrate_admin.py 曾把 .env 的配置搬入库
- AI 批改只覆盖主观题：英二翻译/大小作文、管综论证有效性分析/论说文，按官方评分档次 prompt，分数从紧
- 服务器重启后需重新登录（token 存内存，安全优先）

## 迁移脚本

```bash
.venv/bin/python -I scripts/migrate_users.py   # 用户模块迁移（表加 user_id、存量归属 admin）
.venv/bin/python -I scripts/migrate_admin.py   # 系统管理迁移（is_admin、system_settings、LLM 配置入库）
```

## 自动化测试

```bash
cd backend && .venv/bin/python -m pytest tests -q
# 使用独立的 kaoyan_test 库（自动重建），不碰生产数据
# 覆盖：注册/登录/鉴权、模考全流程（答案不泄露/判分/报告）、双用户数据隔离（错题/复习卡/词汇/看板）
```

## 手机端

PWA 方案：手机浏览器打开 `http://<电脑IP>:8000` →「添加到主屏幕」即可全屏使用（无需应用商店）。
- Service Worker 缓存静态资源（离线可开壳），API 始终走网络
- 模考页移动端：答题卡变底部抽屉（浮钮呼出）、上一题/下一题固定底栏

## 复习引擎（FSRS）说明

- 一切答题行为自动驱动记忆卡：练习/模考**答错** → 建卡 + Again；**答对** → 已有卡自动推迟（"不间断测试即复习"）
- 单词卡在「背单词」页标记熟悉度（生/模糊/熟 → Hard/Good/Easy）时创建
- 今日看板（首页）全部动态计算：FSRS 到期量、薄弱模块（正确率最低优先）、词汇进度、模考建议（各科最新未考真题）——每天打开即得当天计划
- 考试日期与每日词汇量在 .env：`EXAM_DATE=2026-12-19`、`WORDS_PER_DAY=50`

