# 考研助手 · 技术方案

> 2026-11-06 定稿。40 天冲刺平台：199 管综 + 英语二，目标过国家线（英二 55 / 管综 120）。

## 1. 架构

单体 FastAPI + Vue3 SPA，PostgreSQL（Docker `chatbi-postgres`，pg16+pgvector，库 `kaoyan`）。

```
Vue3 SPA（Vite+Pinia+Naive UI+KaTeX） ──REST/SSE──▶ FastAPI 单体
                                                    ├─ 题库/模考/错题（CRUD）
                                                    ├─ 评分引擎（规则 + LLM 主观题）
                                                    ├─ 讲解引擎（LLM 流式）
                                                    ├─ 复习引擎（py-fsrs）
                                                    └─ 计划引擎（40天动态排期）
```

- 服务端时间戳计时：开考时记录 `started_at + duration`，交卷服务端校验超时
- LLM 调用全部落库缓存（prompt、模型版本、结果）
- 单用户私有部署，鉴权从简

## 2. 数据来源（已验证快照于 data/raw，版权自用不分发）

| 数据 | 来源 | 覆盖 | 形态 |
|---|---|---|---|
| 管综真题 | dollarser/kaoyan-199-guanzong-real-exams | 2009–2026 共18套×57题 | Markdown+LaTeX、JSONL、原卷PNG切片、含答案解析 |
| 管综答案校验 | DominicWay/199guanzong-zhenti-trainer | 2010–2026 选择题速查 | HTML |
| 英二真题 | LIziak112/structured-kaoyan-english | 2010–2025 共16套 | 结构化 JSON：题目+答案+解析+译文+范文 |
| 词汇 | exam-data/NETEMVocabulary | 5530 大纲词（真题词频重排） | JSON+SQL；另用16套真题自算英语二专属词频 |

## 3. 数据模型（backend/app/models）

- `subjects` → `modules`（数学/逻辑/写作；完形/阅读/翻译/写作）→ `knowledge_points`（树）
- `question_groups`：**共享材料题组**（阅读文章/完形语段 `{{1}}..{{20}}` 空格标记/翻译段落/写作材料）
- `questions`：单选题/翻译/作文，`options/answer` JSONB，`analysis` 解析，`year`，`raw` 原始数据留档
- `papers` → `paper_sections` → `paper_questions`：整卷模考结构，题组挂 `group_id`
- `words`：词表 + `en2_freq`（英语二语料自算词频回填）

## 4. 四引擎

1. **评分**：客观题规则判分；翻译/作文 LLM 按官方评分档次出结构化 JSON（分数+分项+评语+改进建议）
2. **讲解**：题目/知识点/错题一键 AI 讲解，SSE 流式；错题讲解自动带错误答案对比
3. **复习**：py-fsrs 双队列（错题卡+单词卡），"复习前一天"=FSRS 到期队列
4. **计划**：锚定考试日（2026-12-19 前后）倒排 40 天 → 按目标分拆每日任务 → 每日按「FSRS到期量+知识点正确率+模考成绩」重排。规则引擎，可解释

## 5. 阶段（每阶段结束平台可用）

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 数据快照 → 解析入库 → 校验 | 进行中 |
| P1 | FastAPI 接口 + Vue3：题库浏览、专项练习、真题整卷模考（倒计时+判分+成绩单） | 待开始 |
| P2 | 错题本 + AI 讲解 + 主观题批改 | 待开始 |
| P3 | FSRS 复习队列 + 40 天计划看板 | 待开始 |
| P4 | 词汇背诵 + 学情报告 | 待开始 |

## 6. 前端交互要求（用户明确强调）

模考页：答题卡侧栏（答题状态一目了然）、服务端同步倒计时、阅读双栏（原文/题目）、键盘操作流（1234/ABCD 选择、方向键切题）、断点续答、交卷即时成绩单。
刷题/错题：即时判分反馈、AI 讲解流式面板、错题一键重做。
整体：深浅色适配、移动端可用（在职碎片化学习）。
