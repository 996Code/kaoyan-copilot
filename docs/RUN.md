# 考研助手 · 运行手册

## 启动（生产模式，推荐日常使用）

```bash
# 1. 后端（同时服务 API 与前端构建产物；--host 0.0.0.0 支持局域网访问）
cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. 打开 http://localhost:8000 （局域网 http://<本机IP>:8000）
#    多用户：页面自行注册账号；首个账号 owner 在 .env（AUTH_USERNAME/AUTH_PASSWORD），历史数据归属 owner
```

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
.venv/bin/python -I scripts/import_english2.py      # 英二 16 套
.venv/bin/python -I scripts/import_guanzong.py      # 管综 18 套
.venv/bin/python -I scripts/import_vocab.py         # 词汇 5530
.venv/bin/python -I scripts/apply_answer_verdict.py # 答案裁决修正（26 处）
.venv/bin/python -I scripts/verify_data.py          # 数据对账校验
.venv/bin/python -I scripts/crosscheck_gz_answers.py# 管综答案交叉校验
```

注意：`reset_tables.py` 后需按顺序重跑全部导入；日常只跑 `verify_data.py` 即可。

> 注意：`data/raw`（真题快照）与 `data/assets`（原卷切片/图表）不进 git 仓库。clone 后需自备真题数据放入 `data/raw/`，再按下方「重建数据」执行导入（assets 由导入脚本自动生成）。

## 依赖

- PostgreSQL：Docker 容器 `chatbi-postgres`（localhost:5432，root/root），库 `kaoyan`
- 后端：uv + Python 3.12（backend/.venv），FastAPI + SQLAlchemy
- 前端：Vue3 + Vite + Naive UI + KaTeX（frontend/）

## 已知事项

- 管综 37 题答案标 raw.answer_disputed（一题多卷年份无独立源），报告/练习页有「答案存在版本争议」提示
- 2012/2025 英二大作文图表源仓库缺失
- AI 讲解/批改走 .env 里的 LLM 配置（OpenAI 兼容接口，qwen3.7-plus）；结果按「题目+上下文」缓存进 ai_cache 表，同题不重复计费
- AI 批改只覆盖主观题：英二翻译/大小作文、管综论证有效性分析/论说文，按官方评分档次 prompt，分数从紧
- 服务器重启后需重新登录（token 存内存，安全优先）

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

