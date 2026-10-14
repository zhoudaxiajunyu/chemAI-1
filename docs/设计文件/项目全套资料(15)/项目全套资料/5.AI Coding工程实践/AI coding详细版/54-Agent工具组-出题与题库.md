# 54. Agent工具组 -- 出题与题库（7个工具逐个Evals循环）

> 前置条件：完成文档53《Agent架构》
> 对应 Part 4 文档：[29-Agent对话系统设计](../../4.产品设计/29-Agent对话系统设计.md) §3.2（Exam & Question Bank 7个工具）
> 本阶段目标：7个出题工具，每个独立Evals验证

---

## 概述

本文档实现Agent系统的第一批工具——出题与题库组的7个工具。采用"Evals先行"方法：先写好每个工具的评测场景，然后让Claude Code实现工具代码，运行评测验证通过，再进入下一个工具。

**7个工具**：

| 工具 | 功能 | 关键特性 |
|------|------|---------|
| `search_exam_bank` | 三级搜索 | 关键词匹配 → 向量召回 → 联网补齐 |
| `web_search` | 联网搜索 | MiMo enable_search + Bing兜底 + DeepSeek摘要 |
| `show_exam_workbench` | 内联出题面板 | _component渲染，不执行业务逻辑 |
| `save_to_bank` | 持久化保存 | SQLite写入 + ChromaDB向量同步 + _route页面跳转 |
| `generate_questions` | LLM出题 | RAG上下文检索 + 四维审核 + 化学式标准化 + 重试 |
| `list_banks` | 题库列表 | 只读查询，按created_at倒序 |
| `delete_bank` | 审批删除 | GuardState Layer 4审批门控 + 级联删除 |

**开发流程（Evals先行循环）**：

```
对每个工具：
  1. 编写Eval场景 (pytest, mock依赖)
  2. /opsx:apply → Claude生成工具实现
  3. pytest通过 → git commit
```

---

## 前置检查

- [ ] OpenSpec 项目已初始化：在终端执行 `ls openspec/` 确认 `openspec/config.yaml` 存在（specs/、changes/ 随使用生成）。如不存在，回到文档42 Step 3 执行 `openspec init`

**操作**：在Claude Code中输入：

```
请帮我检查Agent工具开发的前置条件：
1. 确认在 chemai-backend 项目根目录
2. 确认当前在 phase-6/agent 分支
3. 确认 backend/app/services/tool_registry.py 存在
4. 确认 backend/app/utils/vector_search.py 存在（文档53创建）
5. 执行 pytest tests/ --tb=short -x 确认Agent核心测试通过
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| tool_registry.py 不存在 | 文档53的Step 2未完成 | 回到文档53完成Gateway+ReAct+SSE |
| vector_search.py 不存在 | 文档53的向量检索未实现 | 回到文档53补全ChromaDB基础设施 |
| Agent核心测试失败 | phase-6/agent分支代码有回归 | 先修复测试再继续 |

---

## Step 1: 创建分支 + OpenSpec提案

**操作**：在Claude Code中输入：

```
请执行以下操作：
1. git checkout -b feat/agent-tools-gen phase-6/agent
2. /opsx:propose "实现出题与题库7个Agent工具：search_exam_bank(三级搜索) + web_search(MiMo+Bing兜底) + show_exam_workbench(内联面板) + save_to_bank(持久化+向量同步) + generate_questions(LLM出题+四维审核) + list_banks(题库列表) + delete_bank(审批门控)"
```

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: docs(agent): add question-generation tools OpenSpec proposal

---

## Step 2-8: 逐个工具 -- Evals先行循环

每个工具的Step结构相同，以Tool 1（search_exam_bank）为模板。

### 工具1: search_exam_bank（三级搜索）

**参数**：`keyword`(必填), `year`(可选), `difficulty`(可选), `limit`(默认10)
**可调用角色**：tutor, teacher
**call_limit**：3

#### Step 2.1: 编写Eval场景

在Claude Code中输入：

```
请为search_exam_bank工具编写评测场景，在 evals/baseline/tool_call/ 目录下创建 test_search_exam_bank.py。

5个场景：
SEARCH-001: 正常搜索 keyword="2024湖南卷盐类水解"，期望返回结果包含题目
SEARCH-002: keyword="不存在的偏门知识点xyz123456"，期望返回"未找到"或触发web search兜底
SEARCH-003: keyword="" (空字符串)，期望提示用户输入关键词
SEARCH-004: keyword="高考" year=2024，验证年份过滤
SEARCH-005: 模拟本地题库仅2条结果，期望触发web search补齐，结果中提示"AI辅助搜索"

使用mock模拟 exam_bank_service 和 web_search 的返回值。
```

#### Step 2.2: 实现工具

在Claude Code中输入：

```
/opsx:apply
```

Claude Code将生成 `search_exam_bank` 函数：

- **三级搜索策略**：Tier 1 关键词精确匹配 → Tier 2 向量召回补充(use_vector=True) → Tier 3 联网补齐(MiMo enable_search，前两层结果不足3条时触发)
- **返回格式**：`{results: [{qid, content, options, answer, analysis, knowledge_points, year, difficulty, source}], total, keyword, search_tiers_used}`
- **错误处理**：每层try-except包裹，单层失败不影响其他层

#### 验证

```bash
pytest evals/baseline/tool_call/test_search_exam_bank.py -v
# 预期: 5 passed
```

在Claude Code中输入提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add search_exam_bank tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| Tier 1搜索失败 | exam_bank_service导入路径错误 | 确认 `from app.services.exam_bank_service import exam_bank_service` |
| Tier 3联网搜索失败 | MiMo API密钥未设置 | 设置 `export MIMO_API_KEY=your_key` |
| ChromaDB连接失败 | 数据文件路径错误或权限不足 | 检查chroma_db_path配置 |
| 工具注册到TOOL_META时key错误 | 注册时key是字符串而非函数对象 | 确认 `TOOL_META[search_exam_bank] = {...}` |

---

### 工具2: web_search（联网搜索）

**参数**：`query`(必填)
**可调用角色**：student, tutor, teacher, parent
**call_limit**：2

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_web_search.py。

3个场景：
WEB-001: query="高考化学盐类水解知识点"，模拟MiMo正常返回，验证result非空
WEB-002: 模拟MiMo不可用(抛出异常)，验证降级到Bing Web Search API，source标记为"bing"
WEB-003: query="" (空查询)，验证工具提示用户输入搜索词
```

#### 实现要点

- **双路搜索 + 摘要架构**：MiMo enable_search(优先) → Bing Web Search API(降级) → DeepSeek摘要到400字(共享)。第三优先返回错误提示"联网搜索暂时不可用"
- **返回格式**：`{query, result, source("mimo"/"bing"), raw_count}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_web_search.py -v
# 预期: 3 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add web_search tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| MiMo API 401/403 | MIMO_API_KEY无效 | 检查环境变量 |
| Bing API 401 | BING_SEARCH_API_KEY无效或Azure订阅过期 | 验证Azure订阅状态 |
| DeepSeek摘要超时 | max_tokens过大或网络延迟 | 降低max_tokens到512，增加超时时间 |

---

### 工具3: show_exam_workbench（内联出题面板）

**参数**：`knowledge_points`(必填, 列表), `difficulty`(默认"medium"), `question_types`(可选), `variant_source`(可选), `set_name`(可选)
**可调用角色**：tutor, teacher
**call_limit**：3

**特殊行为**：后端不执行业务逻辑，仅在聊天界面渲染出题工作台 React 组件（内联面板）。

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_show_exam_workbench.py。

2个场景：
WB-001: knowledge_points=["盐类水解","化学平衡"] difficulty="medium"，验证_component字段存在，component="exam-workbench"
WB-002: 仅传入 knowledge_points=["氧化还原"]，验证其他参数使用默认值
```

#### 实现要点

- **参数处理**：knowledge_points确保列表类型(string包装为单元素列表)；difficulty校验(easy/medium/hard/competition之一，否则默认medium)；question_types默认["choice","fill","calc"]
- **返回格式**：`{message(中文提示), _component: {component: "exam-workbench", params: {...}}}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_show_exam_workbench.py -v
# 预期: 2 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add show_exam_workbench tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| _component未被GuardState剥离 | 包装函数未处理_component键的弹出 | 检查_make_guarded_tool中的剥离逻辑 |
| 前端面板不渲染 | 前端agent.js中无exam-workbench组件处理 | 确认前端已注册对应组件的SSE事件处理 |

---

### 工具4: save_to_bank（持久化保存到题库）

**参数**：`questions`(必填, 列表), `knowledge_points`(必填, 列表), `set_name`(必填), `description`(可选)
**可调用角色**：tutor, teacher
**call_limit**：1

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_save_to_bank.py。

3个场景：
SAVE-001: 模拟成功保存，验证saved=true，set_id非空，_route字段存在(page="exam-v2")
SAVE-002: 模拟数据库写入失败，验证saved=false，包含error信息，不抛出异常
SAVE-003: questions=[]，验证工具返回"saved=false, 题库中没有题目"
```

#### 实现要点

- **三个动作**：持久化(创建QuestionSet → 逐题写入Question + QuestionSetItem) → 向量同步(增量索引ChromaDB) → 页面跳转(_route → "exam-v2")
- **最终一致性**：如果创建QuestionSet成功但部分题目写入失败，已写入的不回滚
- **返回格式**：`{saved(布尔值), set_id, set_name, count, message, _route: {navigate: "exam-v2", populate: {target: "exam-set", data: set_id}, actions: ["openTab:bank"]}}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_save_to_bank.py -v
# 预期: 3 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add save_to_bank tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| ChromaDB同步失败 | chroma_db_path目录不存在 | 检查配置，创建目录 |
| SQLite UNIQUE constraint | set_id/qid冲突 | uuid4理论上不冲突，检查生成逻辑 |
| _route未生效 | GuardState剥离键名不一致 | 确认键名为"_route"而非"route" |

---

### 工具5: generate_questions（LLM出题 + 四维审核）

**参数**：`knowledge_points`(必填, 列表), `difficulty`(默认"medium"), `quantity`(默认10), `question_types`(可选), `variant_qid`(可选), `variant_source`(可选)
**可调用角色**：tutor, teacher
**call_limit**：5

**核心流程**：RAG上下文检索 → LLM生成 → 化学式标准化 → 四维审核 → 不通过则重试(最多2次) → 返回通过题目

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_generate_questions.py。

5个场景：
GEN-001: 正常生成3道题，模拟LLM返回+审核全通过，验证questions数组长度=3
GEN-002(核心安全): 模拟第2题含错误方程式(配平不通过)，验证触发重试，最终所有题通过，retry_count<=2
GEN-003: 变体模式 variant_qid="q_variant_001"，验证从题库获取蓝本题作为LLM上下文
GEN-004: knowledge_points=[]，验证工具提示至少需要一个知识点
GEN-005: quantity=50(超限)，验证截断到20并给出警告
```

#### 实现要点

- **出题Prompt模板**：注入知识范围、难度、参考题目、LaTeX格式要求
- **化学式标准化(`_normalize_chem_formulas`)**：LaTeX箭头统一(→替换为\rightarrow, ⇌替换为\rightleftharpoons) + 裸化学式检测(60+白名单)包裹为`$...$`格式
- **四维审核(`audit_chemical_equation`)**：维度1系数配平、维度2反应条件、维度3产物稳定性、维度4分子结构
- **重试机制**：审核不通过 → 失败信息追加到prompt → LLM重新生成失败题目 → 最多重试2次；2次后仍不通过的标为"人工审核"
- **返回格式**：`{total, questions[{content, options, answer, analysis, knowledge_points}], audit_summary: {passed_count, failed_count, retry_count}, _component: "exam-workbench"}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_generate_questions.py -v
# 预期: 5 passed (特别确认GEN-002审核阻断场景通过)
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add generate_questions tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| _normalize_chem_formulas误判括号/上标 | 白名单不含边界情况(Ca(OH)2, Fe³⁺) | 扩展白名单，增加括号和上标的正则处理 |
| 审核引擎调用失败 | audit_chemical_equation导入路径错误 | 确认 `from app.services.chemical_balance import audit_chemical_equation` |
| LLM返回非JSON格式 | 格式不稳定 | 增加JSON解析容错(从```json代码块中提取、处理尾部逗号) |
| 审核阻断后LLM仍生成相同错误 | 重试时的feedback不够具体 | 在重试prompt中加入具体的审核失败原因和修改建议 |

---

### 工具6: list_banks（列出题库）

**参数**：无
**可调用角色**：tutor, teacher
**call_limit**：1

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_list_banks.py。

1个场景：
LIST-001: 模拟数据库有3个题库，验证banks数组长度=3，total=3
同时验证call_limit=1的去重逻辑(连续两次调用第二次被拦截)
```

#### 实现要点

- **查询逻辑**：SELECT * FROM question_sets ORDER BY created_at DESC
- **返回格式**：`{banks: [{set_id, name, description, question_count, created_at}], total}`
- **无参数校验**

#### 验证

```bash
pytest evals/baseline/tool_call/test_list_banks.py -v
# 预期: 1 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add list_banks tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| 数据库查询返回空 | question_sets表无测试数据 | 确认表存在且有数据 |
| 去重检查误触发 | GuardState check_dedup的key构建方式有误 | 检查dedup_key的生成逻辑 |

---

### 工具7: delete_bank（审批门控删除）

**参数**：`set_id`(必填)
**可调用角色**：tutor, teacher
**call_limit**：1
**审批门控**：此工具在 `TOOL_APPROVAL_REQUIRED` 集合中

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_delete_bank.py。

3个场景：
DEL-001: 未经审批调用，验证返回 requires_approval_blocked: true，题库未被删除
DEL-002: 审批通过后调用，验证 deleted=true，set_id正确
DEL-003: 审批被拒绝(模拟用户点击"取消")，验证delete_bank未执行
```

#### 实现要点

- **审批门控**：工具本身不处理审批逻辑，由GuardState Layer 4在调用前自动检查。确保在TOOL_APPROVAL_REQUIRED集合中注册此工具
- **删除逻辑(审批通过后)**：查询确认 → 级联删除(question_set_items表 → question_sets表；留questions表原始题目) → 向量库清理(ChromaDB)
- **返回格式**：`{deleted(布尔值), set_id, name, question_count}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_delete_bank.py -v
# 预期: 3 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add delete_bank tool with approval gate
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| 审批拦截不生效 | TOOL_APPROVAL_REQUIRED中未正确添加delete_bank函数对象 | 确认添加了函数对象(非字符串) |
| 级联删除不完整 | 外键约束未设置或未手动删子表 | 确认SQLite PRAGMA foreign_keys=ON或手动先删子表 |
| ChromaDB清理失败 | remove_from_vector_db方法未实现 | 检查exam_bank_service中是否有该方法 |

---

## Step 9: 合并回Agent分支

**操作**：在Claude Code中输入：

```
请帮我执行以下合并操作：
1. pytest evals/baseline/tool_call/test_search_exam_bank.py evals/baseline/tool_call/test_web_search.py evals/baseline/tool_call/test_show_exam_workbench.py evals/baseline/tool_call/test_save_to_bank.py evals/baseline/tool_call/test_generate_questions.py evals/baseline/tool_call/test_list_banks.py evals/baseline/tool_call/test_delete_bank.py -v
   确认22个测试全部通过
```

**打标签**（在Claude Code中输入）：

```
请帮我打 tag evals-tools-gen-pass，标注：All 22 question-generation tool tests passed。确认相关测试全部通过后再打。
```

**代码审查**（在Claude Code中输入）：

```
/code-review
```

双轴代码审查（规范轴 + 规格轴），审查通过后合并。

**合并**（在Claude Code中输入）：

```
请帮我将 feat/agent-tools-gen squash merge 到 phase-6/agent，commit message 为 "feat(agent): add 7 question-generation tools"。合并后运行 run_evals 确认无劣化。
```

**你应该看到**：22个测试全部通过，L3无劣化。

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] 7个工具全部pytest通过（22个评测场景）
- [ ] `generate_questions`的四维审核阻断机制正确工作
- [ ] `search_exam_bank`的三级搜索降级链已验证
- [ ] `delete_bank`的审批门控(GuardState Layer 4)正确工作
- [ ] 所有工具已在TOOL_META中注册，Persona过滤可用
- [ ] 合并后L3无劣化

## 工具总览

| 工具 | 行数 | 评测 | 关键技术 |
|------|:--:|:--:|------|
| search_exam_bank | ~100 | 5 | 三级搜索降级、向量召回、联网补齐 |
| web_search | ~75 | 3 | MiMo enable_search、Bing降级、DeepSeek摘要 |
| show_exam_workbench | ~50 | 2 | _component内联面板、参数规范化 |
| save_to_bank | ~95 | 3 | 持久化+向量同步+_route导航 |
| generate_questions | ~150 | 5 | LLM出题、化学式标准化、四维审核、重试 |
| list_banks | ~35 | 1 | 只读查询、去重验证 |
| delete_bank | ~60 | 3 | 审批门控、级联删除 |
| **合计** | **~565** | **22** | |

---

> **下一份文档**：[55-Agent工具组-诊断与学生](./55-Agent工具组-诊断与学生.md) -- 7个诊断与学生工具的Evals先行实现；可与本文档并行开发
