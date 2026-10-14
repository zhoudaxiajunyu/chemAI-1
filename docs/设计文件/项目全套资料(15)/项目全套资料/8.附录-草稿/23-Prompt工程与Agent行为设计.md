# Prompt 工程与 Agent 行为设计 — ChemAI

> Agent 产品的核心不是代码，是行为设计。代码决定了 Agent"能做什么"，Prompt 和工具设计决定了 Agent"会做什么"和"不会做什么"。本文档记录 ChemAI 在 Prompt 工程、工具 docstring 设计、Persona 系统、护栏机制方面的实践。

---

## 一、Agent 行为设计的四个层次

```
┌──────────────────────────────────────┐
│  第四层：护栏（绝对不会做什么）         │
│  GuardState: 去重/限流/审批/递归限制   │
├──────────────────────────────────────┤
│  第三层：角色边界（作为谁、不能越界）    │
│  Persona YAML: system_prompt + skills │
├──────────────────────────────────────┤
│  第二层：工具选择（什么时候用什么工具）  │
│  TOOL_META + docstring: 何时用/何时不用│
├──────────────────────────────────────┤
│  第一层：基础指令（怎么回答、什么风格）  │
│  system_prompt: 角色定义 + 行为准则     │
└──────────────────────────────────────┘
```

每一层都是一道防线。如果第四层失效（护栏被绕过），第三层仍然阻止越权。如果第三层失效（角色混淆），第二层通过工具过滤兜底。

---

## 二、工具 docstring 设计

### 2.1 设计原则

工具 docstring 是 Agent 选择工具的唯一依据。写得好 = Agent 知道什么时候该用什么。写不好 = Agent 随机选工具。

ChemAI 的 docstring 遵循**四要素**结构：

ChemAI 的 TOOL_META 在 `tools_core.py` 中集中管理，格式如下（实际代码）：

```python
TOOL_META = {
    chemistry_tutor:    {"personas": ["student","tutor","teacher"], "call_limit": 3},
    balance_equation:   {"personas": ["tutor","teacher"],       "call_limit": 3},
    diagnose_barrier:   {"personas": ["teacher","parent"],      "call_limit": 2},
    # ... 共 25 个工具
}
assert set(TOOLS) == set(TOOL_META.keys())  # CI 自动验证完整性
```

每个工具的 Python docstring 是 LLM 选择工具的唯一依据。Agent 通过 LangGraph 的 `create_react_agent` 看到所有工具的 name + docstring，自行判断调用哪个。docstring 的质量直接决定路由准确率。

### 2.2 实际设计原则

分析实际 `tools_core.py` 中 25 个工具的 docstring，可以总结出三个核心设计原则：

1. **名字即意图**：工具名直接表达功能（`balance_equation`、`search_exam_bank`），LLM 不需要猜
2. **描述界定边界**：docstring 明确说清楚"这个工具做什么"，隐含地排除了其他场景
3. **评测兜底**：docstring 写得好不好，不靠感觉——路由准确率评测（32 个场景）用数据说话 |

### 2.3 实际案例：docstring 驱动路由准确率提升

**问题**：学生说"我不会配平 Fe + O2"，Agent 调用了 `chemistry_tutor`（通用辅导），而不是直接配平。学生卡住了，Agent 在讲概念。

**原因**：`chemistry_tutor` 的 docstring 里写了"适用于化学知识辅导"，LLM 认为"配平"也是"辅导"。

**修复**：在 `chemistry_tutor` 的 `NOT for` 部分增加：
```
- 不要用于配平化学方程式（应使用 balance_equation）
- 不要用于离子方程式辅导（应使用 ionic_equation_tutor）
- 不要用于氧化还原反应辅导（应使用 redox_tutor）
```

**效果**：路由准确率从 78% → 85%（在 15 个涉及配平的场景中）。

### 2.4 "NOT for" 模式

`NOT for` 是 ChemAI 工具 docstring 中最重要的部分。它解决了 LLM 的一个核心弱点：**正例易学，反例难辨**。LLM 擅长理解"什么情况下该用"，但容易把边界模糊的场景也归入"该用"。

每个工具的 `NOT for` 至少列 2-3 个明确排除的场景，并指向**应该使用的替代工具**。这样 LLM 不只是知道"不要用这个"，还知道"应该用哪个"。

---

## 三、Persona 系统设计

### 3.1 设计原则

ChemAI 的 4 个角色不仅是"换了个名字"，而是从根本上隔离了可用工具：

| Persona | 角色定位 | 可用工具数 | 核心限制 |
|---------|---------|:-----:|---------|
| **student** | 引导式 AI 助教 | 7 | 不能配平（=不给答案）、不能出题、不能看诊断 |
| **teacher** | 教研助手 | 8 | 可以配平、可以出题、可以诊断、可以看学生数据 |
| **tutor** | 通用化学助教 | 12 | 开发和演示用，工具最全 |
| **parent** | 家长助手 | 4 | 只能看周报和基础诊断，不能操作任何教学功能 |

### 3.2 YAML 结构

每个 Persona 一个 YAML 文件（`agent/personas/{role}.yaml`）：

```yaml
# agent/personas/student.yaml（实际文件内容）
name: 化学助教
description: 面向学生的 AI 化学辅导老师（学生端专用）

system_prompt: |
  你是高中化学AI辅导老师。你的核心原则：引导学生自己推导出答案，绝不直接给出答案。

  ## 你的定位
  - 你面对的是中国高中学生，他们最需要的是：理解课本概念 → 会做题 → 做对题
  - 用苏格拉底式提问引导学生思考
  - 化学方程式、计算过程必须用 LaTeX 格式输出

  ## 工作方式
  - 概念问题：用通俗类比解释，然后追问"试试用你自己的话复述一遍？"
  - 解题问题：分步引导，每步让学生自己先想，卡住了再给提示

  ## 禁止事项
  - 禁止直接给出选择题答案
  - 禁止代替学生完成计算步骤

available_skills:
  - chemistry_tutor
  - simulate_experiment
  - web_search
  - ionic_equation_tutor
  - stoichiometry_tutor
  - redox_tutor
  - equilibrium_tutor
```

### 3.3 Persona 隔离机制

隔离不是靠"prompt 里说不让用"——那太容易被绕过。隔离是靠**代码层硬过滤**：

```python
# Agent 创建时自动过滤工具
def create_chemai_agent(persona_name: str):
    persona = load_persona(persona_name)  # 加载 YAML
    allowed_skills = set(persona["available_skills"])

    # 取 YAML skills 和 TOOL_META personas 的交集
    available_tools = [
        tool for name, tool in ALL_TOOLS.items()
        if name in allowed_skills
        and persona_name in TOOL_META[name]["personas"]
    ]

    return create_react_agent(model, available_tools, ...)
```

评测自动验证隔离效果：

```python
def test_student_cannot_access_teacher_tools():
    """安全层评测：学生角色看不到教师工具"""
    forbidden = {"show_exam_workbench", "balance_equation",
                 "diagnose_barrier", "grade_answer_sheets"}
    student_tools = get_tools_for_persona("student")
    for tool_name in forbidden:
        assert tool_name not in student_tools
```

---

## 四、GuardState 护栏设计

### 4.1 五层护栏

GuardState 在每次工具调用前执行检查。不是一层，是五层：

```
工具调用请求
  │
  ├─ 第 1 层：去重检查
  │   seen_calls 记录 (tool_name, input_hash)
  │   → 如果已经调过同样的工具+输入 → 拒绝
  │
  ├─ 第 2 层：调用限制
  │   TOOL_META[].call_limit 定义每个工具的最大调用次数
  │   → 如果超过限制 → 拒绝
  │
  ├─ 第 3 层：审批门控
  │   TOOL_META[].approval_required = True
  │   → 必须先调 request_approval → 用户确认 → 才放行
  │
  ├─ 第 4 层：递归限制
  │   ReAct 循环最大 12 轮
  │   → 超过 → 强制终止
  │
  └─ 第 5 层：路由剥离
      _route 字段在传给 LLM 前自动剥离
      → 防止内部路由信息泄露给终端用户
```

### 4.2 护栏设计原则

1. **护栏应该让正确行为更容易，让错误行为更困难**——不是"不让 LLM 做"，而是"让 LLM 自然地不做"
2. **护栏失效应该是安全的**——每层独立，单层失效不等于系统失效
3. **护栏应该是可评测的**——每个护栏对应至少 1 个评测场景
4. **审批门控只用于不可逆操作**——不要每个操作都审批，用户会疲劳

### 4.3 需要审批的操作

| 工具 | 为什么需要审批 |
|------|--------------|
| `assign_adaptive_practice` | 给学生布置练习，影响教学计划 |
| `delete_bank` | 删除题库，不可恢复 |
| `save_grading_results` | 保存批改结果，影响学生成绩数据 |

### 4.4 不需要审批的操作

| 工具 | 为什么不需要 |
|------|------------|
| `balance_equation` | 纯计算，无副作用 |
| `search_exam_bank` | 只读操作 |
| `chemistry_tutor` | 只生成对话内容 |

---

## 五、TOOL_META 自动注册

### 5.1 问题

v1 时期加一个工具要改 4 个地方：
- 工具函数文件（写代码）
- Coordinator Prompt（加路由规则）
- Router Prompt（加工具描述）
- Persona 过滤逻辑（声明角色归属）

漏掉任何一步 = 工具"存在但不可用"或"不该有的角色能用"。

### 5.2 方案

每个工具在一个地方声明自己的全部元数据：

```python
TOOL_META = {
    "balance_equation": {
        "personas": ["teacher", "tutor"],   # 哪些角色可以用
        "call_limit": 5,                     # 最多调用次数
        "approval_required": False,          # 是否需要审批
    },
}
```

Agent 创建时自动：
1. 读取 Persona YAML 的 `available_skills`
2. 过滤 TOOL_META 中 `personas` 包含当前角色的工具
3. 取两步的交集 → 最终可用工具集

### 5.3 一致性验证

```python
def test_yaml_skills_all_in_auto():
    """每个 Persona YAML 的 skills 必须在 TOOL_META 中有对应声明"""
    for persona_name, yaml_data in load_all_personas():
        yaml_skills = set(yaml_data["available_skills"])
        meta_skills = {
            name for name, meta in TOOL_META.items()
            if persona_name in meta["personas"]
        }
        assert yaml_skills == meta_skills, \
            f"{persona_name}: YAML 和 TOOL_META 不一致"
```

---

## 六、Tutoring Tool 工厂模式

### 6.1 问题

7 个化学辅导工具（`ionic_equation_tutor`、`stoichiometry_tutor`、`redox_tutor`、`equilibrium_tutor`、`periodic_law_tutor`、`organic_tutor`、`chemistry_tutor`）有**完全相同的三分支结构**：

```
学生有输入 → 分析回答 → 给反馈 + 下一步引导
学生回复了 → 继续引导
学生刚打开 → 给知识点介绍 + 初始问题
```

手写 7 次 = 7 × 60 行 = 420 行几乎相同的代码。改引导逻辑 = 改 7 个地方。

### 6.2 方案

```python
def _make_tutor_tool(
    skill_name: str,
    display_name: str,
    chapter: str,
    intro_template: str,
    feedback_template: str,
) -> Tool:
    """工厂函数：创建标准 tutoring tool"""
    async def tutor_func(input_text: str = "") -> str:
        if not input_text:
            return intro_template
        return analyze_and_feedback(input_text, chapter, feedback_template)

    return Tool(
        name=skill_name,
        description=f"引导式{display_name}辅导。【NOT for】配平、真题搜索、出题",
        func=tutor_func,
    )

# 新增一个 tutoring tool 只需 15 行配置
ionic_tutor = _make_tutor_tool(
    skill_name="ionic_equation_tutor",
    display_name="离子方程式",
    chapter="离子反应",
    intro_template="...",
    feedback_template="...",
)
```

### 6.3 效果

- 代码量：420 行 → 100 行
- 改引导逻辑 = 改工厂一处 → 7 个工具全部受益
- 新增 `periodic_law_tutor` 和 `organic_tutor`：各 10 分钟
- 评测用 `@pytest.mark.parametrize` 一个测试覆盖全部 7 个工具

---

## 七、常见错误与应对

| 错误 | 现象 | 原因 | 应对 |
|------|------|------|------|
| **Docstring 模糊** | Agent 在不该调的时候调了工具 | "用于化学辅导"太泛 | 加 `NOT for` 明确排除场景 |
| **Persona Prompt 太弱** | Agent 在 student 角色下直接给答案 | system_prompt 没说清楚"不给答案"的具体含义 | 用具体行为描述替代抽象原则（"不说你错了"→"说让我们重新看看这一步"） |
| **护栏太松** | LLM 绕过审批直接调破坏性工具 | 只靠 Prompt 约束 | 代码层硬过滤（GuardState 在 LLM 不知道的情况下拦截） |
| **工厂模式太死** | 所有 tutoring tool 行为一模一样 | 抽象过度 | 保留 override 机制（工厂函数接受可选的 `custom_behavior` 参数） |

---

*基于 ChemAI agent/ 实际代码整理 | 详见 `agent/tools_core.py`（TOOL_META）、`agent/personas/*.yaml`（Persona 配置）、`agent/langgraph_agent.py`（GuardState）| 最后更新：2026-07-05*
