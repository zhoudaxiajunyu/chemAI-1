# 55. Agent工具组 -- 诊断与学生（7个工具逐个Evals循环）

> 前置条件：完成文档53《Agent架构》
> 对应 Part 4 文档：[29-Agent对话系统设计](../../4.产品设计/29-Agent对话系统设计.md) §3.3（Diagnosis & Students 7个工具）
> 本阶段目标：7个诊断与学生工具，每个独立Evals验证
> 并行性：本文档与文档53、54可并行开发（都只依赖文档53）

---

## 概述

本文档实现Agent系统的第二批工具——诊断与学生组的7个工具。这批工具是ChemAI核心差异化能力的体现：从"知道谁错了"进化到"知道为什么错"，并基于诊断结果驱动自适应练习。

**7个工具**：

| 工具 | 功能 | 关键特性 |
|------|------|---------|
| `diagnose_barrier` | 障碍诊断 | 个体/班级双模式 + 智能名称解析(SQLite模糊匹配) |
| `show_diagnosis` | 诊断面板渲染 | _component包装，调用diagnose_barrier后添加图表渲染指令 |
| `show_students` | 学生查询 | 三模式(班级概览/班级学生名单/按障碍类型筛选) + 三层fallback班级名匹配 |
| `weekly_report` | LLM周报 | 数据聚合 → DeepSeek生成200字报告 → 通俗语言不制造焦虑 |
| `assign_adaptive_practice` | 自适应练习 | ZPD模型 + barrier→question策略矩阵 + 审批门控(Layer 4) |
| `generate_learning_plan` | 学习方案跳转 | _route页面导航(不实际生成方案) |
| `send_learning_plan` | 方案持久化发送 | HTTP POST /api/teacher/class/learning-plan/{student_id} |

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
请帮我检查前置条件：
1. 确认在 chemai-backend 项目根目录
2. 确认当前在 phase-6/agent 分支
3. 确认以下文件存在：
   - backend/app/services/tool_registry.py (工具注册表)
   - backend/app/services/sqlite_store.py (本地键值存储，文档53 Step 4创建)
   - backend/app/services/memory.py (记忆系统，文档53 Step 4创建)
   - backend/app/diagnosis/rule_engine.py (规则引擎，文档55创建)
4. 执行 pytest tests/ --tb=short -x 确认Agent核心测试通过
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| sqlite_store.py 不存在 | 文档53 Step 4未完成 | 回到文档53完成记忆系统+SqliteStore |
| rule_engine.py 不存在 | 文档46的规则引擎未实现 | 回到文档46补全规则引擎 |
| Agent核心测试失败 | 分支代码有回归 | 先修复测试再继续 |

---

## Step 1: 创建分支 + OpenSpec提案

**操作**：在Claude Code中输入：

```
请执行以下操作：
1. git checkout -b feat/agent-tools-diag phase-6/agent
2. /opsx:propose "实现诊断与学生7个Agent工具：diagnose_barrier(个体/班级双模式+智能名称解析) + show_diagnosis(诊断面板渲染) + show_students(三模式查询+三层fallback) + weekly_report(LLM周报) + assign_adaptive_practice(ZPD模型+审批门控) + generate_learning_plan(页面跳转) + send_learning_plan(API持久化)"
```

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: docs(agent): add diagnosis & student tools OpenSpec proposal

---

## Step 2-8: 逐个工具 -- Evals先行循环

### 工具1: diagnose_barrier（个体/班级两级障碍诊断）

**参数**：`student_id`(可选), `student_name`(可选), `class_id`(可选), `class_name`(可选)
**可调用角色**：teacher, parent
**call_limit**：2

**两种模式**：
- 个体模式：传入student_id或student_name → 返回该学生的障碍分布(concept/reading/expression三元组)和主导障碍类型
- 班级模式：传入class_id → 返回全班学生的障碍聚合统计 + _component诊断面板

**智能名称解析**：支持纯数字ID和中文姓名两种输入。中文姓名通过 `LIKE '%name%'` 模糊匹配 → 返回0条提示未找到、1条自动转ID继续诊断、多条返回candidates列表让用户选择。

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_diagnose_barrier.py。

6个场景：
DIAG-001: 个体诊断 -- student_id="2024001"，验证返回barrier_distribution+dominant_barrier+_route
DIAG-002: 班级诊断 -- class_id="C001"，模拟40名学生，验证total_students=40+_component="diagnosis"
DIAG-003: 智能名称解析 -- student_name="张三"，LIKE查询返回唯一匹配，自动转ID
DIAG-004: 空参数 -- 全为空，验证GuardState Layer 1拦截，返回missing_prerequisites
DIAG-005: 模糊匹配多结果 -- student_name="张"，返回3条candidates，提示用户选择
DIAG-006: Parent角色数据过滤 -- 验证不返回其他学生数据，仅返回绑定子女的信息
```

#### 实现要点

- **个体模式**：查询StudentAnswer表 → 按barrier_type分组统计 → 计算barrier_distribution(三元组总和=1.0) → 判定dominant_barrier → SqliteStore写回(best-effort)
- **班级模式**：查询班级所有学生 → 聚合所有StudentAnswer → 班级级barrier_distribution → top_barriers排序
- **返回格式(个体)**：`{student_id, student_name, barrier_distribution, dominant_barrier, diagnosis_time, _route: {navigate: "diagnosis", params: {student_id}}}`
- **返回格式(班级)**：`{class_id, total_students, barrier_distribution, top_barriers, students[{student_id, student_name, dominant_barrier, error_count}], _component: {component: "diagnosis", params: {...}}}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_diagnose_barrier.py -v
# 预期: 6 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add diagnose_barrier tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| 姓名模糊匹配效率低 | name字段无索引 | 创建索引：`CREATE INDEX idx_students_name ON students(name)` |
| barrier_distribution合计不为1.0 | 浮点精度问题 | 使用 `round(value, 2)` 并调整最后一项使总和=1.0 |
| Parent角色看到多余数据 | Persona过滤未检查data_access.cannot_see | 检查过滤逻辑中是否应用了Persona的data_access配置 |

---

### 工具2: show_diagnosis（诊断面板组件包装）

**参数**：`student_id`(可选), `student_name`(可选), `class_id`(可选)
**可调用角色**：teacher
**call_limit**：1

**区别于diagnose_barrier**：diagnose_barrier返回结构化数据，show_diagnosis额外包装一层_component让诊断结果以图表形式在聊天中渲染。

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_show_diagnosis.py。

3个场景：
SHOWDIAG-001: 个体诊断面板 student_id="2024001"，验证返回message+_component(component="diagnosis")
SHOWDIAG-002: 班级诊断面板 class_id="C001"，验证_component.params含aggregated=true
SHOWDIAG-003: 内部diagnose_barrier失败，验证不崩溃，降级为纯文本错误提示
```

#### 实现要点

- **逻辑**：调用diagnose_barrier → 解析返回JSON → 如果错误则透传 → 如果成功则构建message中文文案 + _component(component="diagnosis"，params从diagnose_barrier结果提取关键字段)
- **返回格式**：`{message(中文提示), _component: {component: "diagnosis", params: {...}}}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_show_diagnosis.py -v
# 预期: 3 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add show_diagnosis tool
```

---

### 工具3: show_students（三模式学生查询）

**参数**：`class_id`(可选), `class_name`(可选), `filter_barrier`(可选)
**可调用角色**：teacher
**call_limit**：1

**三种模式**：
- 模式1(无班级参数)：列出所有班级概览
- 模式2(有班级)：列出该班级所有学生卡片(含障碍类型/分数)
- 模式3(有filter_barrier)：在模式2基础上按障碍类型筛选

**班级名三层fallback**：精确匹配 → LIKE模糊匹配 → 中文数字规范化匹配("高一一班"="高一(1)班"="高一（一）班")

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_show_students.py。

5个场景：
STU-001: 无参数 -- 列出所有班级概览，验证_component="class-overview"
STU-002: class_name="高一(1)班" -- 精确匹配，验证_component="student-list"
STU-003: class_id="C001" filter_barrier="concept" -- 验证仅返回concept障碍的学生
STU-004: class_name="高一一班" -- 测试三层fallback中文数字规范化
STU-005: class_name="不存在的班级" -- 验证返回"未找到班级"
```

#### 实现要点

- **三层fallback**：中文数字翻译表(一→1, 二→2...十→10)，提取年级前缀+数字+班级后缀，规范化后精确匹配
- **返回格式(模式2)**：`{result, student_count, students[{student_id, student_name, barrier_type, last_score, practice_count}], top_barriers(Top 3), _component: "student-list"}`
- **filter_barrier校验**：必须是concept/reading/expression之一

#### 验证

```bash
pytest evals/baseline/tool_call/test_show_students.py -v
# 预期: 5 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add show_students tool
```

---

### 工具4: weekly_report（LLM自然语言周报）

**参数**：`student_id`(可选), `student_name`(可选), `class_name`(可选)
**可调用角色**：teacher, parent
**call_limit**：2

**核心逻辑**：聚合练习数据 + 障碍诊断 + 知识点掌握 → DeepSeek生成150-250字中文报告。严格要求：通俗语言、以鼓励为主、不制造焦虑、用"成长空间"替代"问题"、禁止教育学术语。

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_weekly_report.py。

4个场景：
WR-001: 正常生成学生周报 student_id="2024001"，验证report文本长度100-300字
WR-002: Parent角色周报，验证报告中不出现教育学术语，用"孩子"而非"学生"
WR-003: 无数据可报告 exam_count=0，验证LLM生成"本周暂无练习数据"而非报错
WR-004: 数据异常 exam_count=20(过高)，验证LLM包含合理提醒但不制造焦虑
```

#### 实现要点

- **数据聚合**：查询StudentAnswer表(最近7天) → 统计exam_count、correct_rate、各知识点正确率 → 读取barrier_distribution
- **Prompt约束**：严禁教育学术语("最近发展区""元认知""支架式教学")、用"成长空间"代替"问题"、给出1-2条具体可操作建议
- **Parent角色适配**：额外注入student_context模板变量，语气更亲切
- **返回格式**：`{student_name, report(文本), exam_count, correct_rate, generated_at(ISO时间戳)}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_weekly_report.py -v
# 预期: 4 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add weekly_report tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| LLM生成超时 | max_tokens过大或模型响应慢 | 使用更小的max_tokens(512)，或切换更快的模型 |
| 报告包含教育学术语 | prompt约束不够强 | 增加禁用词示例列表，降低temperature到0.3 |
| student_context注入失败 | SqliteStore中无该学生画像 | 检查_aggregate_data中的存储逻辑 |

---

### 工具5: assign_adaptive_practice（ZPD自适应练习分配）

**参数**：`class_id`(必填), `knowledge_points`(可选, 列表), `question_count`(默认5)
**可调用角色**：teacher
**call_limit**：1

**审批门控**：破坏性操作(创建练习并推送给学生)，在TOOL_APPROVAL_REQUIRED集合中。

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_assign_adaptive_practice.py。

5个场景：
ADP-001: 正常分配 class_id="C001" 3个学生，验证assigned_count=3，每个学生ZPD难度不同
ADP-002: 审批门控 -- 未经审批调用，验证requires_approval_blocked: true
ADP-003: 审批门控 -- 审批通过后调用，验证正常执行
ADP-004: 指定知识点范围 knowledge_points=["盐类水解"]，验证题目仅覆盖指定范围
ADP-005: 指定数量 question_count=10，验证每个学生分配约10道题
```

#### 实现要点

- **ZPD模型**：dominant_barrier="concept" → ZPD难度easy或medium-low(基础概念巩固)；"reading" → medium(提升审题能力)；"expression" → medium或medium-high(强化规范表达)
- **barrier→question策略矩阵**：concept类型障碍→优先"概念辨析""原理解释"类题目；reading→优先"综合应用""多知识点联动"类；expression→优先"方程式书写""计算过程"类
- **优先级链**：知识点weak_kps匹配 > ZPD难度匹配 > 随机补充
- **审批门控**：工具本身不处理审批，由GuardState Layer 4自动检查

#### 验证

```bash
pytest evals/baseline/tool_call/test_assign_adaptive_practice.py -v
# 预期: 5 passed (特别确认ADP-002和ADP-003审批门控)
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add assign_adaptive_practice tool
```

---

### 工具6: generate_learning_plan（页面跳转）

**参数**：`student_id`(必填), `student_name`(可选)
**可调用角色**：teacher
**call_limit**：5

**特殊行为**：纯页面跳转工具。不实际生成学习方案，只通过_route触发前端导航到学生管理页面并打开抽屉。

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_generate_learning_plan.py。

2个场景：
LP-001: 正常跳转 student_id="2024001" student_name="张三"，验证_route(navigate="students", actions含"openStudentDrawer"和"triggerGenPlan")
LP-002: 缺少student_name，验证工具从数据库查询补全姓名
```

#### 实现要点

- **逻辑**：如果student_name为空从DB查询补全 → 构建message文本 → 构建_route(`{navigate: "students", populate: {target: "studentDrawer", data: {student_id, student_name}}, actions: ["openStudentDrawer", "triggerGenPlan"]}`)
- **返回格式**：`{message(中文提示), _route: {...}}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_generate_learning_plan.py -v
# 预期: 2 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add generate_learning_plan tool
```

---

### 工具7: send_learning_plan（API持久化发送）

**参数**：`student_id`(必填), `plan_data`(必填, 字典)
**可调用角色**：teacher
**call_limit**：2

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_send_learning_plan.py。

2个场景：
SLP-001: 成功发送，模拟POST /api/teacher/class/learning-plan/{student_id}返回200，验证success=true
SLP-002: API返回500，验证success=false，message包含错误描述，不抛出异常
```

#### 实现要点

- **逻辑**：构建请求体 → POST到 `/api/teacher/class/learning-plan/{student_id}` → 请求头含JWT Bearer token(从上下文获取) → 解析响应
- **返回格式**：`{success(布尔值), message(操作描述)}`

#### 验证

```bash
pytest evals/baseline/tool_call/test_send_learning_plan.py -v
# 预期: 2 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add send_learning_plan tool
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| JWT令牌获取失败 | 工具内获取当前用户上下文的逻辑错误 | 检查RunContext.deps或全局context的访问方式 |
| API端点404 | 后端路由未注册 | 确认 `/api/teacher/class/learning-plan/{student_id}` 已注册 |

---

## Step 9: 合并回Agent分支

**操作**：在Claude Code中输入：

```
请帮我执行以下操作：
1. pytest evals/baseline/tool_call/test_diagnose_barrier.py evals/baseline/tool_call/test_show_diagnosis.py evals/baseline/tool_call/test_show_students.py evals/baseline/tool_call/test_weekly_report.py evals/baseline/tool_call/test_assign_adaptive_practice.py evals/baseline/tool_call/test_generate_learning_plan.py evals/baseline/tool_call/test_send_learning_plan.py -v
   确认27个测试全部通过
```

**打标签**（在Claude Code中输入）：

```
请帮我打 tag evals-tools-diag-pass，标注：All 27 diagnosis & student tool tests passed。确认相关测试全部通过后再打。
```

**代码审查**（在Claude Code中输入）：

```
/code-review
```

双轴代码审查（规范轴 + 规格轴），审查通过后合并。

**合并**（在Claude Code中输入）：

```
请帮我将 feat/agent-tools-diag squash merge 到 phase-6/agent，commit message 为 "feat(agent): add 7 diagnosis & student tools"。合并后运行 run_evals 确认无劣化。
```

**你应该看到**：27个测试全部通过，L3无劣化。

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] 7个工具全部pytest通过（27个评测场景）
- [ ] `diagnose_barrier`的三维障碍模型(concept/reading/expression)贯穿诊断-练习全链路
- [ ] `assign_adaptive_practice`的ZPD模型和barrier→question策略矩阵正确工作
- [ ] `weekly_report`的LLM报告通过语言风格和隐私保护验证
- [ ] 审批门控工具(assign_adaptive_practice)已正确配置GuardState Layer 4
- [ ] 合并后L3无劣化

## 工具总览

| 工具 | 行数 | 评测 | 关键技术 |
|------|:--:|:--:|------|
| diagnose_barrier | ~120 | 6 | 个体/班级双模式、智能名称解析、SqliteStore写回 |
| show_diagnosis | ~50 | 3 | _component组件包装、内部调用透传 |
| show_students | ~110 | 5 | 三模式查询、三层fallback班级名匹配 |
| weekly_report | ~85 | 4 | LLM自然语言生成、语言风格约束、Parent适配 |
| assign_adaptive_practice | ~120 | 5 | ZPD模型、barrier→question策略矩阵、审批门控 |
| generate_learning_plan | ~40 | 2 | _route页面跳转、前端动作触发 |
| send_learning_plan | ~50 | 2 | HTTP API调用、错误处理 |
| **合计** | **~575** | **27** | |

---

> **下一份文档**：[56-Agent工具组-辅导OCR与记忆](./56-Agent工具组-辅导OCR与记忆.md) -- 16个辅导/OCR/记忆/家长报告工具的Evals先行实现；可与本文档并行开发
