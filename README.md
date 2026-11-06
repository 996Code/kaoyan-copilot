# 考研助手 kaoyan-copilot

自部署的考研冲刺学习平台：**199 管理类联考 + 英语二**，面向「40 天过国家线」的短期冲刺场景（管综 120 / 英二 55）。网页端 + 手机 PWA，多用户数据隔离，AI 讲解与作文批改。

## 功能全景

| 模块 | 能力 |
|---|---|
| 📝 整卷模考 | 管综 18 套（2009-2026）+ 英二 16 套（2010-2025）真题；服务端校准倒计时、分区答题卡、键盘操作流（A-E 选题/←→ 切题）、断点续答（刷新/退出不丢答案）、客观题自动判分、成绩报告（分区统计/错题红绿标记/KaTeX 公式解析） |
| ✏️ 专项练习 | 按科目/模块/年份抽题，即答即判，正确率统计 |
| 🔁 FSRS 复习引擎 | 间隔重复调度错题卡+单词卡；**一切答题自动驱动记忆**（答错建卡、答对推迟），无需刻意维护复习清单 |
| 📕 错题本 | 答错自动归集、错次累计、再错自动复活、「已消灭」标记、模块统计 |
| ✨ AI 能力 | 错题/题目流式讲解（SSE 打字机）；主观题批改——英二翻译/大小作文、管综论证有效性分析/论说文，按官方评分档次从紧给分，分维度点评+改进建议；结果缓存同题不重复计费 |
| 📅 今日看板 | 动态计算（非固定课表）：考试倒计时、FSRS 到期量、薄弱模块（正确率最低优先）、词汇进度、模考建议、近 7 天趋势 |
| 📖 背单词 | 5530 大纲词按真题词频排序（高频先背），生/模糊/熟三档首评直接进 FSRS 队列 |
| 👥 用户体系 | 注册/登录，模考/作答/错题/复习卡全部按用户隔离；系统管理（仅 admin）：用户管理（统计/重置密码/级联删除）、LLM 配置（在线改、即改即生效、连接测试）、系统统计 |
| 📱 移动端 | PWA（添加到主屏幕全屏使用）；底部 Tab 栏、模考答题卡抽屉、固定底栏 |

## 技术栈

- **后端**：Python 3.12 + FastAPI + SQLAlchemy 2 + PostgreSQL（pg16）；`fsrs`（间隔重复）；LLM 走 OpenAI 兼容接口（配置存库，管理页可改）
- **前端**：Vue 3 + Vite + Pinia + Naive UI + KaTeX（LaTeX 公式渲染）+ markdown-it；PWA（manifest + Service Worker）
- **测试**：pytest（13 用例：认证/模考全流程/**双用户数据隔离**/管理员权限与级联删除），独立测试库自动重建

```
Vue3 SPA ──REST/SSE──▶ FastAPI 单体
                        ├─ 题库/模考/判分（CRUD + 规则引擎）
                        ├─ FSRS 引擎（错题卡 + 单词卡统一调度）
                        ├─ 计划引擎（今日看板动态计算）
                        ├─ AI 层（讲解 SSE / 批改，结果缓存）
                        └─ 管理层（用户/配置/统计）
                     PostgreSQL kaoyan 库 ＋ LLM 网关
```

## 快速开始

```bash
# 1. 准备 PostgreSQL，建库 kaoyan
# 2. 后端
cd backend
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env          # 按需改数据库连接与初始管理员
.venv/bin/python -I scripts/create_tables.py
# 导入真题数据（需要自备数据快照放 data/raw，见 docs/RUN.md）
.venv/bin/python -I scripts/import_english2.py
.venv/bin/python -I scripts/import_guanzong.py
.venv/bin/python -I scripts/import_vocab.py
.venv/bin/python -I scripts/apply_answer_verdict.py
.venv/bin/python -I scripts/verify_data.py
# 3. 前端
cd ../frontend && npm install && npm run build
# 4. 启动（局域网可访问）
cd ../backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# 打开 http://localhost:8000 ，初始管理员 admin / kaoyan2026（.env 可改）
```

> 详细运行手册（含数据重建、迁移、测试、移动端）见 [docs/RUN.md](docs/RUN.md)，技术方案见 [docs/tech-design.md](docs/tech-design.md)。

## 数据说明

- 管综真题来自开源结构化仓库（Markdown+LaTeX），**答案经三方独立来源裁决**：149 处争议逐题比对人民网/研招网/希赛/跨考等，修正 26 处、37 处标注「答案存在版本争议」（界面上有提示）
- 英语二真题为结构化 JSON（含解析/翻译/范文）
- 词汇为考研大纲 5530 词按 200 套真题词频重排
- ⚠️ 真题受命题机构版权保护：`data/raw`、`data/assets` 均不入库，仅限个人学习自用、不分发

## 目录结构

```
backend/
  app/api/        # 路由：auth/papers/exams/practice/wrongbook/ai/review/vocab/plan/admin
  app/core/       # db/auth(用户认证)/srs(FSRS)/llm/settings_store(运行时配置)
  app/models/     # 14 张表（题目/题组/试卷/作答/错题/复习卡/用户/配置…）
  scripts/        # 建表/导入/校验/迁移（全部幂等）
  tests/          # pytest
frontend/
  src/views/      # 登录/首页看板/试卷/模考/报告/练习/错题本/复习/背单词/系统管理
  src/components/ # 富文本(KaTeX)/题组材料/题目/AI面板
docs/             # RUN.md 运行手册 / tech-design.md 技术方案 / data-quality 答案裁决
```
