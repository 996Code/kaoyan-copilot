<script setup>
import { ref } from 'vue'
import { NTabs, NTabPane } from 'naive-ui'
import { renderRich } from '../markdown'

const tab = ref('lunxiao')

const SECTIONS = {
  lunxiao: {
    name: '论证有效性分析',
    score: '30 分 · 600 字',
    blocks: [
      {
        title: '全文框架（万能四段式）',
        md: `**第一段·引入**：上述材料通过一系列似是而非的论证，得出「____」的结论。该论证存在诸多逻辑缺陷，分析如下。

**第二~五段·缺陷段**（每段一个缺陷，结构＝引材料＋指缺陷＋析原因）：
- 首先，材料由「____」推出「____」，有以偏概全之嫌……
- 其次，材料默认「____」，该假设未必成立……
- 再次，「____」与「____」未必存在必然因果……
- 最后，由前述有限论据便断言「必将____」，结论明显过强……

**结尾段**：综上所述，材料的论证存在诸多不严谨之处，其结论有待进一步商榷。`,
      },
      {
        title: '高频缺陷攻击句式（背 6 句走天下）',
        md: `1. **以偏概全**：材料仅以「__」（个别情况/有限样本）便概括出「__」（普遍结论），样本代表性存疑。
2. **不当假设**：论证默认「__」，然而这一前提未经证实，若__则结论难以必然成立。
3. **强加因果**：「__」与「__」之间未必存在因果联系，二者可能均为「__」的结果，或另有他因__。
4. **类比不当**：将「__」（甲）的经验径直套用于「__」（乙），忽视二者在__方面的差异。
5. **概念模糊**：「__」一词前后所指不一，存在偷换概念之嫌。
6. **结论过强**：即便前述论据成立，也只能说明「可能__」，「必将__」的断言言过其实。`,
      },
      {
        title: '时间分配与检查清单',
        md: `- 审题+找缺陷 **8 分钟**（先找结论，倒推论证链，挑 4 个最好写的）
- 成文 **22 分钟**（每缺陷段 130 字左右）
- 检查：是否引了材料原词？是否每个缺陷都「析了原因」而不是只贴标签？字数是否 550+？`,
      },
    ],
  },
  lunshuo: {
    name: '论说文',
    score: '35 分 · 700 字',
    blocks: [
      {
        title: '审题立意三问',
        md: `1. 材料的**核心话题**是什么（通常是转折/评述句所在）？
2. 命题人**态度**偏向哪边？
3. 能否用一个**判断句**表达立意？（正例：「发散思维是创新之源」；反例：「论创新」——太泛）`,
      },
      {
        title: '全文框架（递进式）',
        md: `**第一段·引材料+亮观点**：材料中「____」的事例/论述，揭示了「____」的道理。我认为，____。

**第二段·是什么**：__指的是__（界定核心概念）。

**第三段·为什么（核心段）**：之所以说__，一者__；二者__。（理论+事例各一，事例优选：任正非/屠呦呦/张桂梅/苏炳添/王阳明/勾践——一材多用）

**第四段·怎么办**：要__，个人当__；企业/社会当__。

**第五段·收束**：唯有__，方能__。（回扣观点，忌喊口号）`,
      },
      {
        title: '万能事例（一材多用）',
        md: `- **任正非/华为**：创新、危机意识、长期主义、人才投入
- **屠呦呦**：坚持、科学精神、试错、传统与现代结合
- **苏炳添**：突破极限、科学训练（改起跑脚）、细节
- **王阳明**：知行合一、实践、立志
- **诺基亚/柯达**：拒绝改变、路径依赖（反面）`,
      },
    ],
  },
  small: {
    name: '英二·小作文',
    score: '10 分 · 100 词',
    blocks: [
      {
        title: '书信万能三段式',
        md: `**Dear Sir or Madam,**

¶1 目的：I am writing to **[建议: offer some suggestions / 邀请: extend an invitation / 感谢: express my gratitude]** regarding __.

¶2 要点：**First and foremost**, __. **In addition**, __. **Last but not least**, __.

¶3 收尾：I would appreciate it if you could take my suggestions into consideration. / I am looking forward to your reply.

**Yours sincerely,**
**Li Ming**`,
      },
      {
        title: '格式分必拿（2 分）',
        md: `- 称呼顶格 + 逗号；落款右下：Yours sincerely, / Li Ming 分两行
- 三段清楚，连接词显性化（First / Moreover / Finally）
- 100 词左右，**别抄题目原句**——改写才得分`,
      },
    ],
  },
  big: {
    name: '英二·大作文',
    score: '15 分 · 150 词',
    blocks: [
      {
        title: '图表作文三段式（万能模板）',
        md: `**¶1 描述图表（3 句）**
What is clearly presented in the [chart/graph/table] is that __（总述趋势）. In [2010], the [number/proportion] of __ was __, while it [rose/declined] to __ by [2020]. [Notably, __ （最值/倍数点）.]

**¶2 分析原因（3 句）**
Several factors may account for this [trend/phenomenon]. **First**, __. **Moreover**, __. **Last**, __.

**¶3 预测/评论（2 句）**
[Given the analysis above, this trend is likely to continue in the years to come. / It is high time that we paid due attention to __.]`,
      },
      {
        title: '数据描述替换词（避免重复）',
        md: `- 上升：increase / climb / witness a growth / show an upward trend / nearly double
- 下降：decline / drop / decrease steadily / fall to its lowest point
- 占比：account for (45%) / make up / constitute / the figure stands at
- 波动：fluctuate between __ and __ / remain stable at __`,
      },
    ],
  },
}
</script>

<template>
  <div class="page">
    <div class="kb-head">
      <h1>写作模板库</h1>
      <span class="sub">管综两篇 + 英二两篇：框架 · 句式 · 素材（配合「AI 批改」使用：看模板 → 练真题 → AI 评分）</span>
    </div>

    <n-tabs v-model:value="tab" type="line" animated>
      <n-tab-pane v-for="(s, key) in SECTIONS" :key="key" :name="key" :tab="`${s.name} ${s.score}`">
        <div v-for="b in s.blocks" :key="b.title" class="wblock panel">
          <div class="section-title" style="font-size:14px">{{ b.title }}</div>
          <div class="rich" v-html="renderRich(b.md)"></div>
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<style scoped>
.kb-head { display:flex; align-items:baseline; gap:12px; margin:6px 0 14px; }
.kb-head h1 { font-size:20px; font-weight:700; margin:0; }
.kb-head .sub { color:var(--t3); font-size:13px; }
.wblock { padding:16px 20px; margin-bottom:12px; border-radius:var(--r-card); }
</style>
