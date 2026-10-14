# 56. Agent工具组 -- 辅导、OCR与记忆（16个工具Evals先行循环）

> 前置条件：完成文档53《Agent架构》
> 对应 Part 4 文档：[29-Agent对话系统设计](../../4.产品设计/29-Agent对话系统设计.md) §3.4~§3.7（Tutoring 8 + OCR 3 + Memory 2 + Parent 2 + Browser 5 个工具）
> 本阶段目标：16个辅导/OCR/记忆/家长报告工具，每个独立Evals验证
> 并行性：本文档与文档53、54、55可并行开发（都只依赖文档53）
> 提交策略：工具数量多(16个)，分4组提交

---

## 概述

本文档是工具实现三章中规模最大的一章，包含四个功能组的16个工具。所有辅导工具（6个专题辅导）使用 `_make_tutor_tool` 工厂函数创建，消除重复代码。

**16个工具分四组**：

| 组别 | 工具数 | 内容 |
|------|:--:|------|
| Group A -- 辅导(Commit 1) | 9 | 6个专题辅导 + 通用辅导 + 实验模拟 + 方程式配平 |
| Group B -- OCR(Commit 2) | 3 | 进度查询 + 批量批改 + 结果保存 |
| Group C -- 记忆(Commit 3) | 2 | 学生记忆读取 + 教师记忆读取 |
| Group D -- 家长报告(Commit 4) | 2 | 报告生成 + 报告发送 |

**开发流程**：

```
_commit 1: 辅导工厂 + 6个专题辅导 → pytest(24个Evals) → commit_
_commit 2: 通用辅导 + 实验 + 配平 → pytest(8个Evals) → commit_
_commit 3: OCR组 → pytest(7个Evals) → commit_
_commit 4: 记忆组 + 家长报告组 → pytest(6个Evals) → commit_
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
   - backend/app/services/tool_registry.py + tools/__init__.py
   - backend/app/services/sqlite_store.py
   - backend/app/services/memory.py
   - backend/agent/guard.py
4. 执行 pytest tests/ --tb=short -x 确认Agent核心测试通过
```

---

## Step 1: 创建分支 + OpenSpec提案

**操作**：在Claude Code中输入：

```
请执行以下操作：
1. git checkout -b feat/agent-tools-tutor phase-6/agent
2. /opsx:propose "实现辅导/OCR/记忆/家长报告16个Agent工具：辅导组9工具(_make_tutor_tool工厂+6专题辅导+通用辅导+实验模拟+配平审核) + OCR组3工具(进度查询+批量批改+结果保存) + 记忆组2工具(学生/教师记忆读取) + 家长报告组2工具(报告生成+API发送)"
```

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: docs(agent): add tutoring/OCR/memory/parent tools OpenSpec proposal

---

## 提交1: 辅导工厂 + 6个专题辅导工具

### 工厂函数: _make_tutor_tool

**苏格拉底式四步教学法**，6个专题辅导工具（ionic_equation_tutor, stoichiometry_tutor, redox_tutor, equilibrium_tutor, periodic_law_tutor, organic_tutor）共享同一工厂函数。

**工厂函数规格**：

```
_make_tutor_tool(tutor_name: str, display_name: str, steps: List[Dict]) → callable
```

内部状态：模块级字典 `_tutor_states = {}`，key为 `f"{tutor_name}:{student_id}"`。每个状态含 `{current_step, history, equation, problem}`。

**四步循环逻辑**：
1. equation和problem都为空 → 返回intro引导语，初始化step=1
2. student_input为空(首次/下一步) → 返回当前步骤的guidance_template引导问题
3. student_input有值 → 评估回答(关键词匹配)：
   - 正确：current_step += 1，如果current_step > len(steps)，返回完成确认；否则返回下一步引导问题
   - 错误：返回hint提示(保持current_step不变)

**返回格式每轮**：`{step(编号), title(步骤标题), input(学生输入回显), guidance(引导问题)}`

**所有辅导工具**：personas=["student"]，call_limit=5。

### 工具1-6: 6个专题辅导

每个工具通过 `_make_tutor_tool` 工厂创建，区别仅在于 steps 定义不同：

| 工具 | 知识点 | 四步教学法 |
|------|--------|----------|
| `ionic_equation_tutor` | 离子方程式 | 判断可拆物质 → 写成离子形式 → 删除不变离子 → 检查守恒 |
| `stoichiometry_tutor` | 化学计量 | 提取已知量 → 选择公式 → 列比例关系式 → 分步计算 |
| `redox_tutor` | 氧化还原 | 标化合价 → 找升降 → 电子守恒配平 → 检查守恒 |
| `equilibrium_tutor` | 化学平衡 | 分析平衡体系 → 勒夏特列原理判断 → 三段式计算 → 验证结论 |
| `periodic_law_tutor` | 元素周期律 | 确定元素位置 → 分析原子结构 → 推断性质递变 → 总结规律 |
| `organic_tutor` | 有机推断 | 逆合成分析 → 官能团转化路径 → 中间产物确定 → 完整合成路线 |

#### Eval场景

在Claude Code中输入：

```
请为6个专题辅导工具各编写4个评测：
- evals/baseline/tool_call/test_ionic_equation_tutor.py (4场景: 初始化→step2→空参数intro→完成确认)
- evals/baseline/tool_call/test_stoichiometry_tutor.py (4场景: 同上模式)
- evals/baseline/tool_call/test_redox_tutor.py (4场景: 同上模式)
- evals/baseline/tool_call/test_equilibrium_tutor.py (4场景: 同上模式)
- evals/baseline/tool_call/test_periodic_law_tutor.py (4场景: 同上模式)
- evals/baseline/tool_call/test_organic_tutor.py (4场景: 同上模式)

每个测试使用相同的mock策略：mock _tutor_states全局字典，避免工具间状态污染。
验证返回结构：step编号、title标题、input回显、guidance引导问题。

针对ionic_equation_tutor：验证完整离子方程式正确拆解流程
(Ba(OH)2 + H2SO4 = BaSO4↓ + 2H2O → Ba²⁺ + 2OH⁻ + 2H⁺ + SO₄²⁻ = BaSO₄↓ + 2H₂O)
```

#### 实现

在Claude Code中输入：

```
/opsx:apply
```

实现 `_make_tutor_tool` 工厂函数 + 6个工具的steps定义(每个约35行steps配置)。

#### 验证

```bash
pytest evals/baseline/tool_call/test_ionic_equation_tutor.py \
      evals/baseline/tool_call/test_stoichiometry_tutor.py \
      evals/baseline/tool_call/test_redox_tutor.py \
      evals/baseline/tool_call/test_equilibrium_tutor.py \
      evals/baseline/tool_call/test_periodic_law_tutor.py \
      evals/baseline/tool_call/test_organic_tutor.py -v
# 预期: 24 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add 6 topic tutoring tools with factory
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| _tutor_states全局字典线程不安全 | 多用户/多线程并发写同一字典 | MVP可接受(单用户场景)；后续迁移到 AsyncSqliteStore 或 Redis（生产环境） |
| 学生回答评估过于简单 | 仅关键词匹配无法判断化学正确性 | 设计上的刻意简化——辅导工具目的是引导思考而非批改 |
| _tutor_states在服务重启后丢失 | 内存字典不持久化 | 开发阶段可接受；生产环境可迁移到 Redis |
| 工具间状态污染 | _tutor_states key前缀不统一 | 确认每个工具使用 `tutor_name` 作为key前缀 |

---

## 提交2: 通用辅导 + 实验模拟 + 方程式配平

### 工具7: chemistry_tutor（通用化学辅导）

**参数**：`question`(必填), `student_level`(可选), `persona`(可选)
**可调用角色**：student, tutor, teacher
**call_limit**：3

**角色分流逻辑**：
- 教师模式(persona="teacher")：800字教研分析，含考点分布、教学策略、学生常见误区
- 学生模式(persona="student"或默认)：500字苏格拉底式引导，不直接给答案，先反问"你觉得这个问题的关键在哪里？"

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_chemistry_tutor.py。

3个场景：
CT-001: 学生模式 question="氧化还原反应的本质是什么？" persona="student"，验证不直接给答案
CT-002: 教师模式 question="高一年级盐类水解教学策略" persona="teacher"，验证含教研分析结构
CT-003: 无persona参数默认student模式，验证苏格拉底式提问
```

#### 实现要点

- **温度参数差异**：教师模式temperature=0.3(专业稳定)，学生模式temperature=0.5(引导灵活性)
- **返回格式**：`{answer(LLM回复), model(模型名称)}`

### 工具8: simulate_experiment（实验模拟）

**参数**：`experiment_name`(必填)
**可调用角色**：student, tutor
**call_limit**：2

调用DeepSeek(temperature=0.2)生成结构化实验报告JSON，含9个字段：objectives、equipment、steps[{step, action, note}]、expected_phenomena、equations(LaTeX格式)、principles、safety(具体安全提醒)、exam_tips(高考考点)、reflection_questions。

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_simulate_experiment.py。

2个场景：
SIM-001: experiment_name="酸碱中和滴定"，验证9个字段全部存在，JSON可解析
SIM-002: experiment_name=""，验证返回"请提供实验名称"
```

### 工具9: balance_equation（方程式配平审核）

**参数**：`equation`(必填)
**可调用角色**：tutor, teacher
**call_limit**：3

审核引擎封装：调用 `_normalize_chem_formulas(equation)` 标准化 → 调用 `audit_chemical_equation(normalized_equation)` 四维审核 → 返回balanced状态+左右原子数统计+维度结果。

#### Eval场景

在Claude Code中输入：

```
请在 evals/baseline/tool_call/ 目录下创建 test_balance_equation.py。

3个场景：
BAL-001: 正确配平 equation="2H2 + O2 = 2H2O"，验证balanced=true，左右原子数相等
BAL-002: 未配平 equation="Fe + O2 = Fe2O3"，验证balanced=false，原子数不相等
BAL-003: equation=""，验证返回"请提供需要审核的化学方程式"
```

#### 验证(提交2全部)

```bash
pytest evals/baseline/tool_call/test_chemistry_tutor.py \
      evals/baseline/tool_call/test_simulate_experiment.py \
      evals/baseline/tool_call/test_balance_equation.py -v
# 预期: 8 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add general tutor + experiment simulator + equation balancer
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| `chemistry_tutor` 角色分流逻辑错误（教师模式下仍返回苏格拉底式提问） | `persona` 参数未正确传递到 LLM 调用，或 prompt 模板中未根据 persona 分支 | 检查工具函数中 `persona` 参数的默认值和传递链路：`chemistry_tutor(question, persona="teacher")` → prompt 构建 → LLM 调用；在 prompt 模板中加显式分支：`if persona == "teacher": ... elif persona == "student": ...` |
| `simulate_experiment` JSON 输出缺少必填字段（如 `safety` 或 `exam_tips` 为空） | LLM 返回的 JSON 结构不完整，9 个字段中缺少部分字段 | 在解析 LLM 返回后添加字段验证：`required_fields = ["objectives", "equipment", "steps", "expected_phenomena", "equations", "principles", "safety", "exam_tips", "reflection_questions"]` → 缺失字段填充默认值 `"数据暂缺"` 并记录 warning 日志 |
| `balance_equation` 审核引擎导入路径错误（`ImportError: cannot import name 'audit_chemical_equation'`） | 四维审核引擎的实际导入路径与工具中 import 语句不一致 | 确认文档25中审核引擎的文件位置：`backend/app/services/audit_engine.py` 中的函数名；在工具文件中改为正确的 import：`from app.services.audit_engine import audit_chemical_equation` |
| `_normalize_chem_formulas` 白名单不完整（复杂化学式如 `KAl(SO4)2` 未被识别） | 正则表达式或白名单仅覆盖了常见二元化合物，未处理含结晶水、复盐等复杂形式 | 扩展 `_normalize_chem_formulas` 的正则，增加对 `()` 嵌套、结晶水 `·nH2O`、复盐等模式的支持；或回退到使用 ChemPy 库的 `Substance.from_formula()` 做标准化 |

---

## 提交3: OCR组（3个工具）

**可调用角色**：teacher（全部3个工具）

### 工具10: query_ocr_progress（OCR进度查询）

**参数**：`teacher_id`(必填), `batch_id`(可选)
**call_limit**：3

查询ocr_tasks表，按batch_id分组聚合进度(done/failed/pending百分比)。生成next_action建议：全部done→建议开始批改；还有pending→建议继续等待。

### 工具11: grade_answer_sheets（批量LLM批改）

**参数**：`teacher_id`(必填), `batch_id`(必填), `exam_id`(必填)
**call_limit**：2

状态检查(全部done) → 获取OCR结果+参考答案 → 批量DeepSeek批改(temperature=0.1) → 并发控制(asyncio.gather + semaphore=5) → 聚合结果写入ocr_tasks表。

### 工具12: save_grading_results（保存批改结果）

**参数**：`teacher_id`(必填), `batch_id`(必填)
**call_limit**：2

读取ocr_tasks表的grading_result → 逐条写入StudentAnswer表 → 更新exercises_completed计数 → 异步触发障碍诊断(不阻塞保存返回)。

#### Eval场景

在Claude Code中输入：

```
请为3个OCR工具编写评测：
- test_query_ocr_progress.py (2场景: 正常查询进度 vs 全部完成)
- test_grade_answer_sheets.py (3场景: 正常批改 vs OCR未完成 vs 批次不存在)
- test_save_grading_results.py (2场景: 正常保存 vs 部分保存失败)
```

#### 验证

```bash
pytest evals/baseline/tool_call/test_query_ocr_progress.py \
      evals/baseline/tool_call/test_grade_answer_sheets.py \
      evals/baseline/tool_call/test_save_grading_results.py -v
# 预期: 7 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add 3 OCR pipeline tools
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| `query_ocr_progress` 传入的 `batch_id` 在 `ocr_tasks` 表中不存在 | 前端传入了错误的 batch_id 或该批次的 OCR 任务已被清理 | 返回明确的错误消息：`{"error": "批次不存在", "batch_id": "<id>"}`；同时在工具函数内先执行 `SELECT COUNT(*) FROM ocr_tasks WHERE batch_id = ?` 预检查 |
| `grade_answer_sheets` 调用时 OCR 结果未就绪（`status != "done"`） | 当前批次部分图片的 OCR 尚未完成（status 为 `pending` 或 `processing`） | 工具入口处添加状态检查：查询该 `batch_id` 下所有 task 的 status → 如有非 `done` 状态，返回 `{"status": "not_ready", "done_count": X, "total_count": Y}` 并建议等待后重试 |
| `save_grading_results` 写入 `StudentAnswer` 表时 `student_id` 验证失败（`IntegrityError`） | OCR 识别出的学生姓名与 `Student` 表中记录不匹配，导致 `student_id` 映射失败 | 添加学生姓名→ID 的模糊匹配逻辑（如 `Student.name.like(f"%{ocr_name}%")`）；匹配失败时记录到 `error_message` 字段并跳过该条，不阻断整体保存流程 |
| 并发控制 `semaphore` 设置不当导致 rate limit（批量批改时 DeepSeek API 返回 429） | `asyncio.Semaphore(5)` 太小导致请求堆积，或太大触发 API 限流 | 默认 `semaphore=3`（DeepSeek 免费版并发限制）；在工具函数中捕获 `HTTP 429` 错误并自动退避重试（指数退避 1s/2s/4s，最多 3 次） |

---

## 提交4: 记忆组 + 家长报告组（4个工具）

### 工具13: memory_student_get（学生记忆读取）

**参数**：`student_id`(必填), `memory_type`(可选)
**可调用角色**：student, tutor, teacher, parent
**call_limit**：1

从SqliteStore搜索命名空间 `("student", student_id, "diagnosis")` 获取最近5条诊断记录，搜索 `("student", student_id, "learning_plan")` 获取学习方案。

### 工具14: memory_teacher_get（教师记忆读取）

**参数**：`teacher_id`(必填)
**可调用角色**：teacher
**call_limit**：1

从SqliteStore搜索命名空间 `("teacher", teacher_id, "preferences")`。无记录则返回默认偏好(teaching_style="standard", default_difficulty="medium")。

### 工具15: generate_parent_report（家长报告生成）

**参数**：`student_name`(必填), `student_id`(必填)
**可调用角色**：teacher
**call_limit**：5

数据聚合(调用memory_student_get + 查询StudentAnswer表30天数据) → 内容过滤(移除排名/比较/失败率等焦虑内容) → DeepSeek生成Markdown报告(temperature=0.3)。严格要求：鼓励为主、先说亮点、用"成长空间"代替"问题"、绝对不排名、给出2-3条家长可配合建议。

### 工具16: send_report_to_parent（报告发送）

**参数**：`student_id`(必填), `report_data`(必填, 字典)
**可调用角色**：teacher
**call_limit**：3

HTTP POST到 `/api/parent/send-report/{student_id}`。后端内部：查找StudentParentBinding确认绑定关系(active=true) → 创建ParentNotification记录(type='weekly_report')。多家长绑定同一学生时向每个家长发送。

#### Eval场景

在Claude Code中输入：

```
请为4个记忆/家长报告工具编写评测：
- test_memory_student_get.py (2场景: 正常读取 vs 无历史记录)
- test_memory_teacher_get.py (1场景: 读取教师偏好/默认值)
- test_generate_parent_report.py (2场景: 正常生成 vs 敏感内容过滤)
- test_send_report_to_parent.py (1场景: 成功发送)
```

#### 验证

```bash
pytest evals/baseline/tool_call/test_memory_student_get.py \
      evals/baseline/tool_call/test_memory_teacher_get.py \
      evals/baseline/tool_call/test_generate_parent_report.py \
      evals/baseline/tool_call/test_send_report_to_parent.py -v
# 预期: 6 passed
```

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add 2 memory + 2 parent report tools
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| `memory_student_get` 查询命名空间不存在（返回空列表） | `SqliteStore` 中 `("student", student_id, "diagnosis")` 命名空间尚未有任何记录写入 | 返回空列表属于正常情况，但工具应返回友好提示而非报错：`{"records": [], "message": "该学生暂无诊断记录"}`；测试中先通过 `sqlite_store.set()` 写入一条 seed 数据 |
| `memory_teacher_get` 无记录时默认偏好生成逻辑错误（返回了 `None` 而非默认值） | `SqliteStore.get()` 无记录时返回 `None`，代码中未做 `None` 检查直接用 `.get("teaching_style")` | 在工具函数中添加 fallback 逻辑：`prefs = result or {}` → `teaching_style = prefs.get("teaching_style", "standard")` → `default_difficulty = prefs.get("default_difficulty", "medium")` |
| `generate_parent_report` 内容过滤遗漏敏感词（报告中仍出现"排名""落后""不及格"等字样） | 敏感词过滤列表不完整，或过滤逻辑仅检查了标题而未检查正文 | 扩展 `SENSITIVE_WORDS` 列表：`["排名", "落后", "不及格", "差生", "退步", "失败率", "倒数"]`；对 LLM 生成的全文（包括 Markdown 各级标题和正文）执行 `re.sub()` 替换为 `"***"` |
| `send_report_to_parent` API 端点返回 404（`POST /api/parent/send-report/{student_id}`） | 家长端路由文件 `app/routers/parent.py` 未注册到 `app/main.py` 或路由路径不匹配 | 确认 `app/main.py` 中包含 `app.include_router(parent.router, prefix="/api/parent")`；确认 `parent.py` 中路由装饰器为 `@router.post("/send-report/{student_id}")` |
| `StudentParentBinding` 查询时 `status != "active"`（绑定已失效但仍尝试发送） | 家长解除了与学生的绑定但工具未检查 `status` 字段 | 在 `send_report_to_parent` 工具中添加绑定状态过滤：`SELECT * FROM student_parent_bindings WHERE student_id = ? AND status = 'active'`；无活跃绑定时返回明确提示：`{"status": "no_active_binding", "student_id": ...}` |

---

## 全量验证 + 合并

**操作**：在Claude Code中输入：

```
请帮我执行以下操作：
1. pytest evals/baseline/tool_call/ -v
   确认全部45个测试通过(24+8+7+6=45)
```

**打标签**（在Claude Code中输入）：

```
请帮我打 tag evals-tools-tutor-pass，标注：All 45 tutoring/OCR/memory/parent tool tests passed。确认相关测试全部通过后再打。
```

**代码审查**（在Claude Code中输入）：

```
/code-review
```

双轴代码审查（规范轴 + 规格轴），审查通过后合并。

**合并**（在Claude Code中输入）：

```
请帮我将 feat/agent-tools-tutor squash merge 到 phase-6/agent，commit message 为 "feat(agent): add 16 tutoring/OCR/memory/parent tools"。合并后运行 run_evals 确认无劣化。
```

**你应该看到**：45个测试全部通过，L3无劣化。

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] 16个工具全部pytest通过（45个评测场景）
- [ ] `_make_tutor_tool`工厂函数消除6个辅导工具的重复代码
- [ ] OCR管道状态机通过Agent工具封装为对话式操作
- [ ] 家长报告的内容过滤机制已验证(不制造焦虑、不包含排名)
- [ ] 记忆工具的跨会话持久化读取已验证
- [ ] 合并后L3无劣化

## 工具总览

| 分组 | 工具数 | 行数 | 评测数 | 关键技术点 |
|------|:--:|:--:|:--:|------|
| Group A 辅导(提交1) | 6 | ~250 | 24 | _make_tutor_tool工厂、苏格拉底四步法 |
| Group A 辅导(提交2) | 3 | ~200 | 8 | 角色分流、JSON结构化输出、审核引擎封装 |
| Group B OCR | 3 | ~190 | 7 | 状态机检查、批量LLM批改、异步诊断触发 |
| Group C 记忆 | 2 | ~75 | 3 | SqliteStore命名空间管理 |
| Group D 家长报告 | 2 | ~100 | 3 | 内容过滤、敏感词移除、API推送 |
| **合计** | **16** | **~815** | **45** | |

**三章累计**（文档54+55+56）：30个Agent工具全部实现，94个评测场景全部通过。

---

> **下一份文档**：[57-Persona系统+GuardState护栏+MCP服务器](./57-Persona系统+GuardState护栏+MCP服务器.md) -- Persona YAML配置 + GuardState四层护栏 + MCP 16个工具服务器
