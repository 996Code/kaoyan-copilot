"""知识速成卡内容种子：管综数学公式 / 逻辑技法 / 论效缺陷 / 英二写作句型。

用法：cd backend && .venv/bin/python -I scripts/seed_knowledge.py（幂等，重跑覆盖）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

M, L, W, E = "数学", "逻辑推理", "写作", "英语写作"

# (subject, module, category, title, back)
CARDS = [
    # ---------------- 管综数学：公式与结论（30） ----------------
    ("gz199", M, "数列", "等差数列三大公式",
     "通项：$a_n = a_1 + (n-1)d$\n\n前 $n$ 项和：$S_n = \\dfrac{n(a_1+a_n)}{2} = na_1 + \\dfrac{n(n-1)}{2}d$\n\n**性质**：$a_m + a_n = a_p + a_q \\iff m+n = p+q$；中项 $a_\\frac{m+n}{2} = \\dfrac{a_m+a_n}{2}$"),
    ("gz199", M, "数列", "等比数列三大公式",
     "通项：$a_n = a_1 q^{n-1}$\n\n前 $n$ 项和（$q\\neq 1$）：$S_n = \\dfrac{a_1(1-q^n)}{1-q}$\n\n**性质**：等比中项 $G^2 = a_m \\cdot a_n$（同号项才有实数中项）"),
    ("gz199", M, "数列", "$S_n$ 与 $a_n$ 的关系",
     "$a_n = \\begin{cases} S_1, & n=1 \\\\ S_n - S_{n-1}, & n \\ge 2 \\end{cases}$\n\n**别忘验证 $n=1$**，这是数列题最常见陷阱。"),
    ("gz199", M, "代数", "均值不等式链",
     "$\\sqrt{ab} \\le \\dfrac{a+b}{2} \\le \\sqrt{\\dfrac{a^2+b^2}{2}}$（$a,b>0$）\n\n**口诀**：几何 ≤ 算术 ≤ 平方。取等条件：$a=b$。\n\n经典应用：$x + \\dfrac{1}{x} \\ge 2$（$x>0$）"),
    ("gz199", M, "代数", "均值不等式求最值口诀",
     "**一正二定三相等**：各项为正、积或和为定值、验证取等条件。\n\n和定积最大：$a+b=P \\Rightarrow ab \\le (P/2)^2$；积定和最小：$ab=S \\Rightarrow a+b \\ge 2\\sqrt{S}$。"),
    ("gz199", M, "代数", "绝对值不等式",
     "$|a| \\ge a$；$|a| \\le b \\iff -b \\le a \\le b$（$b>0$）\n\n三角不等式：$\\big||a|-|b|\\big| \\le |a\\pm b| \\le |a|+|b|$"),
    ("gz199", M, "代数", "韦达定理",
     "$x_1+x_2 = -\\dfrac{b}{a}$，$x_1 x_2 = \\dfrac{c}{a}$（$ax^2+bx+c=0$）\n\n**衍生**：$x_1^2+x_2^2 = (x_1+x_2)^2-2x_1x_2$；$\\dfrac{1}{x_1}+\\dfrac{1}{x_2} = \\dfrac{x_1+x_2}{x_1x_2}$；$|x_1-x_2| = \\dfrac{\\sqrt{\\Delta}}{|a|}$"),
    ("gz199", M, "代数", "一元二次判别式与根分布",
     "$\\Delta = b^2-4ac$：$\\Delta>0$ 两不等实根、$=0$ 两相等、$<0$ 无实根。\n\n两正根 $\\iff \\Delta\\ge0,\\ x_1+x_2>0,\\ x_1x_2>0$（还要 $a$ 与 $b$ 异号、与 $c$ 同号）；根的区间分布用**数形结合**画抛物线看。"),
    ("gz199", M, "代数", "立方公式三件套",
     "$(a\\pm b)^3 = a^3 \\pm 3a^2b + 3ab^2 \\pm b^3$\n\n$a^3 \\pm b^3 = (a\\pm b)(a^2 \\mp ab + b^2)$"),
    ("gz199", M, "代数", "比例性质",
     "$\\dfrac{a}{b} = \\dfrac{c}{d} \\Rightarrow \\dfrac{a+b}{b} = \\dfrac{c+d}{d}$（合比）\n\n$\\Rightarrow \\dfrac{a-b}{b} = \\dfrac{c-d}{d}$（分比）；$\\Rightarrow \\dfrac{a+b}{a-b} = \\dfrac{c+d}{c-d}$（合分比）"),
    ("gz199", M, "排列组合", "排列与组合公式",
     "$A_n^m = \\dfrac{n!}{(n-m)!}$（有序）；$C_n^m = \\dfrac{n!}{m!(n-m)!}$（无序）\n\n**恒等式**：$C_n^m = C_n^{n-m}$；$C_n^m = C_{n-1}^{m-1} + C_{n-1}^m$；$C_n^0 = C_n^n = 1$"),
    ("gz199", M, "排列组合", "隔板法（相同物分组）",
     "$n$ 个相同元素分给 $m$ 组、每组至少 1 个：$C_{n-1}^{m-1}$ 种。\n\n允许为空则每组先垫 1 个：$C_{n+m-1}^{m-1}$。"),
    ("gz199", M, "排列组合", "错排与定序",
     "定序（$m$ 个元素相对顺序固定）：总数 $\\div m!$。\n\n环排：$n$ 人围圆桌 $(n-1)!$ 种。"),
    ("gz199", M, "概率", "古典概型与对立事件",
     "$P = \\dfrac{\\text{有利}}{\\text{总数}}$；**正难则反**：$P(A) = 1 - P(\\bar A)$。"),
    ("gz199", M, "概率", "独立重复试验（伯努利）",
     "$n$ 次独立试验恰好发生 $k$ 次：$P = C_n^k p^k (1-p)^{n-k}$\n\n**至少一次**：$1-(1-p)^n$"),
    ("gz199", M, "概率", "条件概率与独立性",
     "$P(B|A) = \\dfrac{P(AB)}{P(A)}$；独立：$P(AB)=P(A)P(B)$\n\n互斥 $\\neq$ 独立（互斥是 $P(AB)=0$）"),
    ("gz199", M, "几何", "直线方程五种形式",
     "点斜式 $y-y_0=k(x-x_0)$；斜截式 $y=kx+b$；两点式；截距式 $\\dfrac{x}{a}+\\dfrac{y}{b}=1$；一般式 $Ax+By+C=0$。\n\n**垂直直线不存在斜率**，用一般式最稳。"),
    ("gz199", M, "几何", "距离公式三件套",
     "两点：$d=\\sqrt{(x_1-x_2)^2+(y_1-y_2)^2}$\n\n点到直线：$d=\\dfrac{|Ax_0+By_0+C|}{\\sqrt{A^2+B^2}}$；平行线间：$d=\\dfrac{|C_1-C_2|}{\\sqrt{A^2+B^2}}$"),
    ("gz199", M, "几何", "平行与垂直的斜率关系",
     "平行：$k_1 = k_2$（注意重合排除）；垂直：$k_1 k_2 = -1$。"),
    ("gz199", M, "几何", "圆的方程与位置关系",
     "标准式 $(x-a)^2+(y-b)^2=r^2$。圆心到直线距离 $d$ 与 $r$ 比：相离 $d>r$、相切 $d=r$、相交 $d<r$。弦长 $= 2\\sqrt{r^2-d^2}$。"),
    ("gz199", M, "几何", "三角形必背结论",
     "面积 $S=\\dfrac{1}{2}ah=\\dfrac{1}{2}ab\\sin C$；内角和 $180°$。\n\n**重心**分中线 2:1；**直角三角形**：$a^2+b^2=c^2$、斜边中线 = 斜边一半；等边三角形高 $h=\\dfrac{\\sqrt3}{2}a$、面积 $\\dfrac{\\sqrt3}{4}a^2$。"),
    ("gz199", M, "几何", "扇形与弧长",
     "弧长 $l = r\\theta$（$\\theta$ 为弧度）；扇形面积 $S = \\dfrac{1}{2}lr = \\dfrac{1}{2}r^2\\theta$\n\n$180° = \\pi$ 弧度，$1° = \\dfrac{\\pi}{180}$"),
    ("gz199", M, "应用题", "增长率与利润率",
     "增长：$a(1+r)^n$；下降：$a(1-r)^n$。\n\n利润率 $= \\dfrac{\\text{利润}}{\\text{成本}} \\times 100\\%$；折扣：售价 $=$ 标价 $\\times$ 折扣。先降 $p\\%$ 再升 $p\\%$，总体 $(1-p\\%)(1+p\\%) = 1 - p^2\\%^2 < 1$（**不对称**）。"),
    ("gz199", M, "应用题", "浓度问题（交叉法）",
     "混合前后**溶质守恒**。十字交叉：浓度 $a$、$b$ 混成 $r$，质量比 $\\dfrac{m_a}{m_b} = \\dfrac{r-b}{a-r}$（$a>r>b$）。\n\n倒出加满型：每次倒出 $x$ 再加满，浓度变为原来的 $(1-\\dfrac{x}{V})$ 倍。"),
    ("gz199", M, "应用题", "行程问题",
     "相遇：路程和 $= (v_1+v_2)t$；追及：路程差 $= (v_1-v_2)t$。\n\n顺水 $v=v_{船}+v_{水}$、逆水 $v=v_{船}-v_{水}$；往返平均速度 $\\neq$ 速度平均，用 $\\dfrac{2v_1v_2}{v_1+v_2}$。"),
    ("gz199", M, "应用题", "工程问题（设 1 法）",
     "总量设为 1：效率 $=\\dfrac{1}{天}$。合作效率 = 各效率之和。\n\n交替施工按**周期**分析，注意最后一轮的余量谁来做。"),
    ("gz199", M, "应用题", "集合容斥",
     "两集合：$|A\\cup B| = |A|+|B|-|A\\cap B|$\n\n三集合：$|A\\cup B\\cup C| = |A|+|B|+|C| - |A\\cap B| - |A\\cap C| - |B\\cap C| + |A\\cap B\\cap C|$；**至少一个**用正难则反。"),
    ("gz199", M, "代数", "最值问题三板斧",
     "① 均值不等式（一正二定三相等）；② 二次函数配方法（注意定义域）；③ 线性规划（画可行域，最值在顶点/边界）。\n\n遇到 $x+\\dfrac{k}{x}$ 型想均值，遇到约束想规划。"),
    ("gz199", M, "代数", "不定方程技巧",
     "整系数不定方程看**奇偶性、尾数、整除**：如 $3x+5y=31$，由尾数 $5y$ 尾 0/5 → $3x$ 尾 1/6 → 枚举 $x$。"),
    ("gz199", M, "条件充分性判断", "条充题五种选项含义",
     "**A** 条件(1)充分，(2)不充分；**B** (2)充分，(1)不充分；**C** 联合充分，单独都不充分；**D** 各自都充分；**E** 联合也不充分。\n\n口诀：**一对一否选 A/B，都行选 D，合才行选 C，合都不行选 E**。"),
    ("gz199", M, "条件充分性判断", "条充题解题流程",
     "① 从**结论**出发确定需要什么；② 单独验(1)、单独验(2)；③ 都不充分时**联合**验证。\n\n**陷阱**：条件是结论的子集也可能充分；两个条件等价时选 D；别把「需要两个都给」误判为 C，先各自试！"),
    # ---------------- 逻辑推理：技法（20） ----------------
    ("gz199", L, "形式逻辑", "逆否命题等价",
     "$A \\to B \\iff \\neg B \\to \\neg A$\n\n**推理规则**：肯前推肯后（$A\\to B$，$A$ 真 → $B$ 真）；否后推否前（$B$ 假 → $A$ 假）；**否前、肯后都推不出必然结论**。"),
    ("gz199", L, "形式逻辑", "假言命题真值与矛盾",
     "$A \\to B$ 只有一种情况为假：**前真后假**。\n\n矛盾命题：$A\\to B$ 的矛盾是 $A \\wedge \\neg B$（不是 $\\neg A \\to \\neg B$）。\n\n$\\neg(A\\to B) = A \\wedge \\neg B$。"),
    ("gz199", L, "形式逻辑", "德摩根律",
     "$\\neg(A \\wedge B) = \\neg A \\vee \\neg B$\n\n$\\neg(A \\vee B) = \\neg A \\wedge \\neg B$\n\n**口诀**：负号进去，并且变或者。"),
    ("gz199", L, "形式逻辑", "联言与选言推理",
     "联言 $A\\wedge B$：一假则假（否定一支即可否定整体）。\n\n相容选言 $A\\vee B$：一真则真；**否定一支才能肯定另一支**。不相容选言：恰有一真。"),
    ("gz199", L, "形式逻辑", "三段论规则",
     "中项至少周延一次；前提中不周延的项结论中不得周延；两否定前提推不出结论。\n\n有效式举例：所有 M 是 P，所有 S 是 M → 所有 S 是 P。"),
    ("gz199", L, "形式逻辑", "换位推理",
     "全称肯定 $SAP$：只能换位为 $PIS$（限制换位）；全称否定 $SEP \\iff PES$；特称肯定 $SIP \\iff PIS$；特称否定不能换位。\n\n「所有 S 都是 P」≠「所有 P 都是 S」。"),
    ("gz199", L, "论证逻辑", "削弱题型套路",
     "找**结论与论据之间的联系**下手：\n\n① 因果论证：另有他因 / 因果倒置 / 割断联系；② 类比论证：指出不可比；③ 例证法：质疑样本代表性。\n\n**最强削弱通常是否定论证的前提或因果倒置**，力度：割断联系 > 他因。"),
    ("gz199", L, "论证逻辑", "加强题型套路",
     "① 搭桥：在论据与结论间补前提；② 排除他因（没有别的因素影响）；③ 因果方向确认；④ 补充 supportive 例证/数据。\n\n**搭桥（建立联系）通常是最强加强**。"),
    ("gz199", L, "论证逻辑", "假设题型（论证成立的必要前提）",
     "问法：「以下哪项是上述论证成立的假设？」\n\n方法：**搭桥法**（论据关键词与结论关键词之间补联系）或**否定代入法**——否定选项后论证垮掉的就是假设。"),
    ("gz199", L, "论证逻辑", "解释题型",
     "给一个矛盾/反常现象找原因。正确项必须**同时触及矛盾双方**，只解释一方必错。"),
    ("gz199", L, "论证逻辑", "结论推出题",
     "只依据题干信息能推出什么：**不引入外部信息、不过度推理**。谨防「偷换概念、范围扩大、条件强化」三个陷阱。"),
    ("gz199", L, "分析推理", "分析推理：列表法",
     "元素对应/匹配题：画**表格**，题干确定的先打勾，否定的打叉，行列排除推进。\n\n信息多时用「**最多/最少**」「**只有一人说真话**」类条件作突破口。"),
    ("gz199", L, "分析推理", "分析推理：排序法",
     "位置排序题：画一排格子，把「确定位置」先放，「相邻」「不在两端」「左边几个」等条件逐步夹逼。"),
    ("gz199", L, "分析推理", "分析推理：代入排除",
     "选项具体（如「谁是冠军」）时**直接代入验证**；问「可能为真」的选项，排除所有必然假的。\n\n复杂题先排除两三个选项再精验，省时一半。"),
    ("gz199", L, "分析推理", "真假话问题套路",
     "先找**矛盾对**（两句互相矛盾必一真一假）→ 唯一真话/假话锁定在矛盾对中 → 其余句子真假确定 → 推出结论。"),
    ("gz199", L, "数字陷阱", "平均数与百分比陷阱",
     "① 平均数涨不代表每个个体涨；② 百分比大 ≠ 绝对数大（基数不同）；③ 增长率下降 ≠ 数量下降；④ 相关 ≠ 因果。"),
    ("gz199", L, "常见谬误", "以偏概全",
     "用**少数/特殊样本**推全体结论。标志词：「我认识的人…」「某公司…因此所有企业…」。削弱即指出**样本无代表性**。"),
    ("gz199", L, "常见谬误", "不当类比",
     "两事物有相似处 ≠ 在目标属性上也相似。「A 国改革成功，我国照搬也会成功」——忽略**基础条件差异**。"),
    ("gz199", L, "常见谬误", "因果倒置与强加因果",
     "相关关系当因果关系；或把果当因。「成功人士都早起 → 早起导致成功」可能实为「野心导致早起与成功」（**因果倒置**）。"),
    ("gz199", L, "常见谬误", "偷换概念与循环论证",
     "偷换概念：同一个词前后含义变了（「好人」→「好员工」）。\n\n循环论证：用结论证明结论（「他不会骗人，因为他是诚实的人」）。"),
    # ---------------- 论证有效性分析：常见缺陷（10） ----------------
    ("gz199", W, "论效缺陷", "论效写作：核心方法",
     "**四步**：① 找结论（通常在结尾）；② 梳理论证链（论据→结论）；③ 挑 4 个最明显缺陷；④ 每段结构=**引材料 + 指缺陷 + 析原因**。\n\n常用结构：开头段（概括+质疑）+ 4 个缺陷段 + 结尾段。600 字左右。"),
    ("gz199", W, "论效缺陷", "缺陷一：以偏概全",
     "标志：由个别/部分推整体。攻击句式：「材料由……（个别情况）便推出……（普遍结论），该论证有以偏概全之嫌，样本是否具有代表性值得商榷。」"),
    ("gz199", W, "论效缺陷", "缺陷二：不当假设",
     "标志：论证暗含未经验证的前提。攻击句式：「上述论证默认……，然而这一假设未必成立，若……则结论难以必然得出。」"),
    ("gz199", W, "论效缺陷", "缺陷三：因果谬误",
     "含强加因果、因果倒置、单因论。攻击句式：「……与……之间未必存在必然的因果关系，还可能存在其他影响因素，如……」"),
    ("gz199", W, "论效缺陷", "缺陷四：类比不当",
     "攻击句式：「将……（甲领域）的经验直接套用到……（乙领域），忽视了二者在……方面的本质差异，此类比难以成立。」"),
    ("gz199", W, "论效缺陷", "缺陷五：概念不清/偷换",
     "攻击句式：「材料中『……』一词前后含义不一致/界定模糊，由……推至……存在偷换概念之嫌。」"),
    ("gz199", W, "论效缺陷", "缺陷六：数字陷阱",
     "含平均数、百分比、基数不明。攻击句式：「平均数掩盖了个体差异……」「百分比缺乏基数支持，无法说明……」"),
    ("gz199", W, "论效缺陷", "缺陷七：条件关系误用",
     "把必要条件当充分条件、或然当必然。攻击句式：「……只是达到……的必要条件之一，材料将其视为充分条件，显然不妥。」"),
    ("gz199", W, "论效缺陷", "缺陷八：结论过强",
     "标志：由有限前提得出「必然/一定/必将」。攻击句式：「即便前述论证成立，也只能说明……可能……，『必将』的结论显然言过其实。」"),
    ("gz199", W, "论说文", "论说文：审题立意三问",
     "① 材料核心话题是什么？② 命题人态度偏向？③ 能否用一个**判断句**表达立意（如「发散思维是创新之源」）？\n\n**立意忌**：跑题、含糊、多中心。可从「是什么—为什么—怎么办」搭框架：开头亮观点 + 2-3 个分论点段（每段=观点+理论+例子+回扣）+ 结尾。700 字。"),
    # ---------------- 英语二：写作句型（14） ----------------
    ("en2", E, "小作文", "书信通用框架",
     "**Dear Sir or Madam, / Dear Mr. Smith,**\n\n第一段：自我介绍 + 写信目的（I am writing to …）\n\n第二段：要点展开（First… / Second… / Finally…）\n\n第三段：期待回复或感谢（I would appreciate it if you could … / Thank you for your time.）\n\n**Yours sincerely, Li Ming**"),
    ("en2", E, "小作文", "建议信高频句型",
     "① I am writing to offer some suggestions regarding…\n\n② It would be beneficial if you could take the following suggestions into consideration.\n\n③ First and foremost, it is advisable to…\n\n④ I hope you will find these suggestions helpful and practical."),
    ("en2", E, "小作文", "通知/邀请信句型",
     "通知：An activity themed \"…\" is scheduled to be held in … (place) at … (time). Those interested please sign up before…\n\n邀请：On behalf of…, I would like to invite you to participate in… It would be our great honor if you could attend."),
    ("en2", E, "大作文", "图表作文三段框架",
     "**首段·描述图表**：What is clearly presented in the chart is that…（总述）+ 具体数据（In 2010, the number/proportion of … was …, while it rose/declined to … in 2020.）\n\n**中段·分析原因**：Several factors contribute to this trend. First… Second… Last…\n\n**尾段·预测/评论**：Given the analysis above, it can be predicted that this trend will continue in the foreseeable future. / It is high time that we paid attention to…"),
    ("en2", E, "大作文", "上升趋势表达",
     "① increase / rise / grow / climb (from … to …)\n\n② experience a dramatic/sharp/steady/gradual increase\n\n③ the figure nearly doubled / tripled\n\n④ show an upward trend / remain on the rise"),
    ("en2", E, "大作文", "下降与占比表达",
     "下降：decrease / decline / drop / fall to…; suffer a sharp drop; show a downward trend\n\n占比：account for 45%; make up / constitute …; the proportion of A is twice that of B; A ranks first, followed by B and C"),
    ("en2", E, "大作文", "对比与倍数句型",
     "① By contrast / In contrast, …\n\n② Compared with A, B witnessed a much faster growth.\n\n③ The number of A is almost three times as large as that of B.\n\n④ while / whereas A increased, B declined slightly."),
    ("en2", E, "大作文", "原因分析万能句",
     "① This phenomenon can be attributed to several factors.\n\n② The rapid development of the economy has made it possible for…\n\n③ With the improvement of living standards, people are paying more attention to…\n\n④ Changes in … also play a part in this trend."),
    ("en2", E, "翻译", "翻译评分要点",
     "**忠实 + 通顺**。采分点：关键句式（定语从句/被动/比较）和核心词义。\n\n技巧：① 定语从句长则拆成两句；② 被动常译为主动（is believed → 人们认为）；③ 增译主语（英语无主 → 汉语补「人们/我们」）；④ 词性转换（名词 → 动词）。"),
    ("en2", E, "阅读", "阅读正确选项特征",
     "① **同义改写**（原文关键词的替换表达）而非原词照抄；\n\n② 语气适度（may / some / tend to），慎选绝对词（only / never / all / must）；\n\n③ 细节题答案能在原文**定位**；主旨题看首尾段+高频词。"),
    ("en2", E, "阅读", "阅读干扰项特征",
     "① 偷换概念（换词不换形）；② 以偏概全（个别→全部）；③ 无中生有（原文未提）；④ 因果倒置；⑤ 答非所问（内容真但不是本题答案）；⑥ 原词堆砌（照抄原文词但逻辑错）。"),
    ("en2", E, "完形", "完形填空技巧",
     "① 先通读首句抓主题（首句不设空）；② 逻辑关系题看前后连接词（however/therefore/while）；③ 固定搭配优先（考纲高频：take…into account, be concerned about…）；④ 复现原则——全文同义替换链提示答案。"),
    ("en2", E, "词汇", "猜词技巧",
     "① 构词法：前缀 dis-/in-/un-（否），后缀 -tion/-ment（名词）；② 同位语/定语从句解释；③ 上下文转折（but 后）或并列（and 前后）线索；④ 举例信号 for example 后常是同义复现。"),
    ("en2", E, "词汇", "熟词僻义高频榜",
     "address $v.$ 处理；school $n.$ 学派；novel $adj.$ 新颖的；bear $v.$ 承担/生育；code $n.$ 准则；even $adj.$ 均匀的；game $n.$ 猎物；subject…to 使遭受；branch $n.$ 分支；capital $n.$ 首都/资本/大写"),
]


def main() -> None:
    from sqlalchemy import delete

    from app.core.db import SessionLocal
    from app.models.knowledge import KnowledgeCard

    with SessionLocal() as s:
        s.execute(delete(KnowledgeCard))
        for i, (sub, mod, cat, title, back) in enumerate(CARDS, 1):
            s.add(KnowledgeCard(
                subject_code=sub, module_name=mod, category=cat,
                title=title, back=back, sort=i,
            ))
        s.commit()
        print(f"已写入 {len(CARDS)} 张知识卡：数学{sum(1 for c in CARDS if c[1]==M)}、"
              f"逻辑{sum(1 for c in CARDS if c[1]==L)}、论效/论说{sum(1 for c in CARDS if c[1]==W)}、"
              f"英语{sum(1 for c in CARDS if c[0]=='en2')}")


if __name__ == "__main__":
    main()
