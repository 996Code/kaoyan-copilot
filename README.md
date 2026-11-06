# 考研助手 kaoyan-copilot

自部署的考研冲刺学习平台：**199 管理类联考 + 英语二**，面向「40 天过国家线」的短期冲刺场景（管综 120 / 英二 55）。网页端 + 手机 PWA，多用户数据隔离，AI 讲解与作文批改。

## 功能全景

| 模块 | 能力 |
|---|---|
| 📝 整卷模考 | 管综 18 套（2009-2026）+ 英二 17 套（2010-2026）；服务端校准倒计时、答题卡、键盘操作流、断点续答、客观题自动判分、成绩报告 |
| 📚 题库 | 35 套真题（含答案三方裁决）、逐题解析、KaTeX 公式、答案版本争议标记 |
| ✏️ 专项练习 | 按科目/模块/年份/题型（条充/求解/完形/阅读）抽题，即答即判 |
| 🔁 FSRS 复习引擎 | 错题卡+单词卡+知识卡三类统一调度；一切答题自动驱动记忆 |
| 📕 错题本 | 答错自动归集、消灭标记、一页一题+答题卡导航流 |
| ✨ AI 能力 | 错题/题目流式讲解、主观题按官方评分档次批改、LLM 网关管理页在线改即生效 |
| 📅 今日看板 | 考试倒计时、到期量、薄弱模块、词汇进度、模考建议、**趋势+过线概率预测** |
| 📖 背单词 | 5530 大纲词按真题词频排序、三档首评进 FSRS、**点词查义+一键加词本** |
| 💡 知识速成卡 | 134 张（数学公式52/逻辑技法35/论效论说18/英语句型29），翻卡学习直接进 FSRS |
| ✍️ 写作模板库 | 管综论效/论说 + 英二大小作文：框架·句式·素材 |
| 👥 用户体系 | 注册/登录、数据全隔离、系统管理（用户/LLM 配置/统计，仅 admin） |
| 📱 移动端 | PWA、底部 Tab 栏+更多菜单、顶栏页面标题复用、各页面 Tab 化紧凑布局 |

## 技术栈

- **后端**：Python 3.12 + FastAPI + SQLAlchemy 2 + PostgreSQL；fsrs 6（间隔重复）；LLM 走 OpenAI 兼容接口（配置存库）
- **前端**：Vue 3 + Vite + Pinia + Naive UI + KaTeX + markdown-it；PWA（manifest+SW）；design-tokens 单一设计源
- **测试**：pytest 13 用例（认证/模考全流程/双用户隔离/管理员权限）；独立 kaoyan_test 库
- **部署**：deploy.sh 一键容器化（Docker 多阶段构建，npm 淘宝/pip 清华源，单容器 28080 端口，DB 连 .env）

## 快速开始

```bash
# 1. 准备 PostgreSQL + 自备真题数据放 data/raw/（见 docs/RUN.md）
# 2. 后端
cd backend
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env
.venv/bin/python -I scripts/create_tables.py
.venv/bin/python -I scripts/seed_knowledge.py
# 导入真题数据（幂等）：import_guanzong / import_english2 / import_vocab
# 3. 前端 + 启动
cd ../frontend && npm install && npm run build
cd ../backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# 打开 http://localhost:8000 ，初始管理员 admin / kaoyan2026
```

容器化部署：`./deploy.sh`（停旧容器→构建→启动→健康检查，端口 28080）

> 详细运行手册见 [docs/RUN.md](docs/RUN.md)，技术方案 [docs/tech-design.md](docs/tech-design.md)，答案裁决 [docs/data-quality/](docs/data-quality/)。

## 数据说明

- 管综 18 套来自开源结构化仓库（Markdown+LaTeX），答案经三方独立来源裁决：149 处争议逐题比对，修正 26 处、37 处标注「答案存在版本争议」
- 英二 17 套（含 2026）为结构化 JSON，答案至少双源一致
- 知识卡 134 张为自研编写（数学公式/逻辑技法/论效句式/英语句型）
- ⚠️ 真题受版权保护：`data/raw`、`data/assets` 不入 git，仅限个人学习自用

## 目录结构

```
backend/
  app/api/        # 路由：auth/papers/exams/practice/wrongbook/ai/review/vocab/plan/admin/knowledge
  app/core/       # db/auth(用户认证)/srs(FSRS)/llm/settings_store
  app/models/     # 16 张表
  scripts/        # 建表/导入/校验/迁移/知识卡种子（幂等）
  tests/          # pytest
frontend/
  src/styles/tokens.css  # 设计变量单一来源
  src/views/      # 12 个页面
  src/components/ # 富文本/题组材料/题目/AI面板/图标
deploy.sh         # 一键容器化部署
docs/             # RUN.md / tech-design.md / data-quality/
```
