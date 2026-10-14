# 57. Persona + GuardState + MCP

> 前置条件：完成文档53《Agent架构》及文档54/55/56中至少一项（需要已注册的工具供 Persona 引用）
> 对应 Part 4 文档：[29-Agent对话系统设计](../../4.产品设计/29-Agent对话系统设计.md) §4~§12（Persona、Guard、Planner、Context、Memory、Audit、MCP）
> 本阶段目标：Persona YAML配置(4角色) + GuardState四层护栏 + MCP服务器(16工具+3端点)

---

## 概述

前三章完成了30个Agent工具的实现。但工具本身只是"能力"，还需要三层基础设施来保证工具被正确、安全地使用：

- **Persona系统**：决定"谁能用什么工具"（角色-工具映射，两层过滤交集）
- **GuardState护栏**：决定"什么时候能用、能用几次"（四层运行时安全检查）
- **MCP服务器**：决定"外部系统如何调用工具"（16工具+3端点，与Agent工具责任分工）

---

## 前置检查

- [ ] OpenSpec 项目已初始化：在终端执行 `ls openspec/` 确认 `openspec/config.yaml` 存在（specs/、changes/ 随使用生成）。如不存在，回到文档42 Step 3 执行 `openspec init`

**操作**：在Claude Code中输入：

```
请帮我检查前置条件：
1. 确认在 chemai-backend 项目根目录
2. 确认当前在 phase-6/agent 分支
3. 确认以下文件存在：
   - backend/app/services/tool_registry.py (含TOOL_META字典，注册>=20个工具)
   - backend/agent/guard.py (GuardState类基架)
4. 执行 pytest tests/ --tb=short -x 确认Agent核心测试通过
```

**关于三角依赖**：文档54-56中的工具在TOOL_META中引用了Persona，本文档中的Persona YAML引用了工具名。如果前面文档中用了占位Persona，在本文档完成后需要回到前面文档调整TOOL_META中的Persona引用为本文档定义的精确值。这是正常的——先写完所有代码再回头调整引用。

---

## Step 1: OpenSpec提案 + 创建分支

**操作**：在Claude Code中输入：

```
请执行以下操作：
1. git checkout -b feat/agent-persona phase-6/agent
2. /opsx:propose "实现Persona系统(4角色YAML+两层工具过滤+跨角色泄漏检测) + GuardState四层护栏(去重/限流/审批/脱敏) + MCP服务器(16工具+3端点)"
```

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: docs(persona): add Persona + GuardState + MCP OpenSpec proposal

---

## Part 1: Persona系统

### Persona配置总览

| Persona | 显示名称 | 工具数 | 定位 |
|---------|---------|:--:|------|
| teacher | 教研助手 | 18 | 班级管理、学情分析、考试准备 |
| student | 化学助教-学生端 | 7 | 苏格拉底式辅导、绝对不直接给答案 |
| tutor | 化学助教-通用 | 6 | 默认角色，兼具辅导和出题 |
| parent | 家长助手 | 2 | 学情报告、通俗语言、不制造焦虑 |

### Step P1: 实现四个Persona YAML文件

**操作**：在Claude Code中输入：

```
/opsx:apply
```

Claude Code将在 `backend/agent/personas/` 目录下创建4个YAML文件：

**teacher.yaml**：available_skills 18个工具(搜索/出题/题库管理/诊断/学生管理/周报/自适应练习/学习方案/家长报告/OCR管理/记忆/方程式审核)。system_prompt强调数据驱动、高效务实、尊重专业判断、保护隐私。

**student.yaml**：available_skills 7个工具(6个专题辅导+通用辅导+实验模拟+联网搜索+记忆读取)。system_prompt核心原则：苏格拉底式提问、绝不直接给答案、分步引导、鼓励探索。包含6条禁止行为（不帮计算、不帮写方程式、不帮查公式）。

**tutor.yaml**：available_skills 6个工具(通用辅导+搜索/出题/题库+实验模拟+方程式审核+记忆)。system_prompt根据对话对象自适应风格。

**parent.yaml**：available_skills 2个工具(周报+诊断+记忆)。system_prompt核心原则：通俗语言（禁用教育学术语）、以鼓励为主、保护隐私（不透露其他学生数据）、不制造焦虑。含 `data_access` 字段（can_see: own_child_scores/barriers/practice，cannot_see: other_students/class_stats/teacher_notes）。

所有system_prompt使用YAML的 `|` (literal block scalar)语法保留多行文本。available_skills中的工具名必须与tools_core.py中注册的函数名完全一致。

### Step P2: 编写Persona YAML加载评测

在Claude Code中输入：

```
请创建 evals/baseline/persona/test_persona_loading.py，编写以下评测：
1. 四个YAML文件存在且可正确解析
2. YAML必填字段完整性(name/description/system_prompt/available_skills)
3. 工具数量验证(teacher=18/student=7/tutor=6/parent=2)
4. available_skills中所有工具都在TOOL_META中注册了对应persona
5. browser tools自动附加验证(所有角色默认5个browser工具)
```

验证：`pytest evals/baseline/persona/test_persona_loading.py -v`

### Step P3: 实现两层工具过滤

**操作**：在Claude Code中输入：

```
/opsx:apply
```

实现 `load_persona_config(persona_name)` 函数和两层过滤逻辑：

**两层交集机制**：
```
最终工具集 = YAML白名单(available_skills) ∩ TOOL_META注册(personas含当前角色)
          + 5个Browser Tools(所有角色默认附加)
```

**关键API签名**：

```
load_persona_config(persona_name: str) → dict:
    # 读取 agent/personas/{persona_name}.yaml
    # 返回 {name, description, system_prompt, available_skills}
    # 不存在或解析失败 → fallback到tutor Persona

filter_tools_by_persona(persona_name: str) → List[Callable]:
    # Step 1: 获取YAML白名单 → set(persona_config["available_skills"])
    # Step 2: 遍历TOOL_META，筛选personas含当前角色的工具 → auto_skills set
    # Step 3: 计算交集 → persona_tool_names = yaml_skills & auto_skills
    # Step 4: 根据persona_tool_names找到工具函数对象
    # Step 5: 附加5个Browser Tools
    # 返回: domain_tools列表 + 5个browser_tools
```

**边界情况**：persona_name不在["teacher","student","tutor","parent"]中 → fallback到"tutor"；交集为空 → 返回tutor的工具集；system_prompt为空 → fallback prompt。

### Step P4: 编写工具过滤 + 跨角色泄漏检测评测

在Claude Code中输入：

```
请创建 evals/baseline/persona/：

test_tool_filtering.py (过滤评测)：
- Teacher过滤后 web_search在交集中，ionic_equation_tutor不在交集中
- Student过滤后 6个tutoring工具在交集中，show_exam_workbench不在
- Parent过滤后 仅2个核心工具(weekly_report, diagnose_barrier)在交集中
- 模拟YAML中nonexistent_tool，验证该工具不会被加入(交集为空正确排除)
- Browser tools自动附加验证

test_cross_role_isolation.py (泄漏检测)：
6个禁止调用场景：
LEAK-001: Student尝试调用show_exam_workbench → blocked
LEAK-002: Student尝试调用assign_adaptive_practice → blocked
LEAK-003: Parent尝试调用show_students → blocked
LEAK-004: Parent尝试调用send_report_to_parent → blocked
LEAK-005: Student尝试调用balance_equation → 验证是否意外泄露
LEAK-006: Tutor尝试调用diagnose_barrier → blocked

目标：6个场景全部blocked，0%泄漏率
```

验证：`pytest evals/baseline/persona/ -v`

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(persona): add 4-role Persona system
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| YAML解析失败 | 缩进混用Tab/空格，或`|`符号后换行缩进不对 | 统一使用空格缩进，检查literal block scalar格式 |
| 工具名不匹配 | YAML中的名称与TOOL_META中的函数名不一致 | 对照tools_core.py修正YAML中的工具名 |
| 某个角色工具数为0 | YAML白名单与TOOL_META注册的交集为空 | 检查TOOL_META中各工具的personas列表是否包含了该角色 |
| LEAK-005显示Student可访问balance_equation | tutor.yaml的available_skills含balance_equation，且Student可能错误获得了tutor的权限 | 检查Student Persona的工具过滤逻辑，确认没有错误地混入tutor的工具 |

---

## Part 2: GuardState护栏

### 护栏架构总览

GuardState是请求级安全基础设施(`backend/agent/guard.py`)，每位Agent调用创建一个新实例。四层防护：

```
工具调用请求
   │
   ▼
Layer 1: 前置条件检查 (check_prerequisites)
   → 必填参数非空、keyword长度>2、_at_least_one等
   │
   ▼
Layer 2: 调用次数限制 (check_limit)
   → 基于TOOL_META.call_limit，超限拦截
   │
   ▼
Layer 3: 去重检查 (check_dedup)
   → 相同工具+相同参数(排序后)不重复调用
   │
   ▼
Layer 4: 审批门控 (requires_approval)
   → 破坏性操作(delete_bank, assign_adaptive_practice)需用户确认
   │
   ▼
_component/_route 剥离
   → 从返回数据中弹出UI层字段，LLM只看到业务数据
```

### Step G1: 实现 _PREREQS 字典 + check_prerequisites (Layer 1)

**操作**：在Claude Code中输入：

```
/opsx:apply
```

实现 `_PREREQS` 字典（约40行）和 `check_prerequisites(tool_name, kwargs) → Tuple[bool, Optional[str]]` 方法。

**_PREREQS 结构**（定义每个工具的必填参数及校验规则）：

| 工具 | 必填条件 |
|------|---------|
| search_exam_bank | keyword: v非空且len>2 |
| diagnose_barrier | _at_least_one: [student_id, student_name, class_id, class_name] |
| delete_bank | set_id: v非空 |
| grade_answer_sheets / save_grading_results | teacher_id非空 AND batch_id非空 |
| assign_adaptive_practice | class_id非空 |
| save_to_bank | questions为非空列表 AND set_name非空 |
| weekly_report | _at_least_one: [student_id, student_name, class_name] |
| generate_questions | knowledge_points为非空列表 |

所有其他工具无前置条件，默认通过。

**关键API签名**：

```
check_prerequisites(tool_name: str, kwargs: dict) → Tuple[bool, Optional[str]]:
    # 返回 (True, None) 表示通过
    # 返回 (False, "缺少必要参数: {...}") 表示拦截
```

### Step G2: 实现 check_limit + check_dedup + 审批门控 (Layer 2-4)

**操作**：在Claude Code中输入：

```
/opsx:apply
```

实现Layer 2-4：

**Layer 2 - check_limit**：

```
GuardState._call_counts: Dict[str, int]  # 每个工具的调用计数

check_limit(tool_name: str) → Tuple[bool, Optional[str]]:
    call_limit = TOOL_META[tool_fn].call_limit
    if _call_counts.get(tool_name, 0) + 1 > call_limit:
        return (False, "调用次数已达上限({call_limit}次)")
    _call_counts[tool_name] = _call_counts.get(tool_name, 0) + 1
    return (True, None)
```

**Layer 3 - check_dedup**：

```
GuardState._seen_calls: Set[str]  # 去重集合

check_dedup(tool_name: str, kwargs: dict) → Tuple[bool, Optional[str]]:
    dedup_key = f"{tool_name}:{json.dumps(sorted(kwargs.items()))}"
    if dedup_key in _seen_calls:
        return (True, "重复调用，已跳过")  # True=是重复的
    _seen_calls.add(dedup_key)
    return (False, None)
```

**Layer 4 - 审批门控**：

```
TOOL_APPROVAL_REQUIRED = {delete_bank, assign_adaptive_practice}  # 模块级集合

GuardState.approved_tools: Set[str]  # 已审批的工具名集合

# 在_make_guarded_tool中Layer 4检查:
if tool_fn in TOOL_APPROVAL_REQUIRED and tool_name not in approved_tools:
    return {"error": "requires_approval_blocked",
            "message": "此操作需要您确认", "tool": tool_name}
```

**_component/_route剥离**：

```
# 在_make_guarded_tool包装函数中，工具执行完成后:
if isinstance(data, dict):
    if "_route" in data: guard_state.last_route = data.pop("_route")
    if "_component" in data: guard_state.last_component = data.pop("_component")
return json.dumps(data)  # 不含特殊字段的纯净数据
```

SSE适配器在每轮工具调用结束后检查 `last_component` 和 `last_route`，有值则推送相应的SSE事件，然后清零。

### Step G3: 编写GuardState全部评测

在Claude Code中输入：

```
请创建 evals/baseline/guard/ 目录并编写评测：

test_guard_layer1_prerequisites.py (6场景):
L1-001: search_exam_bank空keyword → 拦截
L1-002: keyword="盐"(len<=2) → 拦截
L1-003: keyword="盐类水解"(len>2) → 通过
L1-004: diagnose_barrier全空参数 → 拦截
L1-005: diagnose_barrier student_id="2024001" → 通过
L1-006: 无前置条件工具(如list_banks) → 始终通过

test_guard_layer2_limit.py (4场景):
L2-001: 首次调用 → 通过
L2-002: 第四次调用(call_limit=3) → 超限
L2-003: 第二次调用(call_limit=1) → 超限
L2-004: 第三次调用(call_limit=3) → 刚好通过

test_guard_layer3_dedup.py (5场景):
L3-001: 相同工具+相同参数两次 → 第二次判定重复
L3-002: 相同工具+不同keyword → 不算重复
L3-003: 不同工具+相同参数 → 不算重复
L3-004: 参数顺序不同语义相同 → 排序后判定重复
L3-005: 无参数工具两次调用 → 第二次判定重复

test_guard_layer4_approval.py (6场景):
L4-001: delete_bank未经审批 → blocked
L4-002: request_approval调用后 → approved_tools包含该工具
L4-003: 审批通过后 → 正常执行
L4-004: assign_adaptive_practice未经审批 → blocked
L4-005: 非审批工具(list_banks)直接通过
L4-006: 审批是一次性的(per-tool) → 不同工具需分别审批

test_guard_strip_component_route.py (4场景):
STRIP-001: 工具返回含_component → 剥离，LLM看不到，guard_state.last_component有值
STRIP-002: 工具返回含_route → 剥离，guard_state.last_route有值
STRIP-003: 同时含两者 → 两者都剥离
STRIP-004: 不含特殊字段 → 直接透传
```

验证：`pytest evals/baseline/guard/ -v`（预期25 passed）

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(guard): add 4-layer GuardState with cross-role leak detection
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| _PREREQS中工具名与实际不匹配 | tool_func.__name__与_KEY不一致 | 确认_PREREQS的key使用 `tool.__name__` 获取的名称 |
| lambda校验空值逻辑错误 | `"" and len(str("")) > 2` 返回""而非False | 在lambda中先判非空：`lambda v: v and len(str(v)) > 2` |
| 去重时参数顺序影响结果 | kwargs未排序导致不同顺序被判定为不同调用 | 使用 `sorted(kwargs.items())` 排序后序列化 |
| 审批状态跨工具不共享 | GuardState实例未在单次Agent调用中保持同一引用 | 确认Agent的run方法中创建的GuardState实例在整个调用期间不被替换 |

---

## Part 3: MCP工具服务器

### MCP vs Agent工具分工

| 维度 | Agent工具 | MCP工具 |
|------|----------|---------|
| 调用方 | LLM在ReAct循环中自选 | 外部系统通过API调用 |
| 端点 | `/api/agent/chat` (SSE) | `/api/mcp/call`, `/api/mcp/tools/{name}` |
| 注册方式 | TOOLS列表 + TOOL_META字典 | `@tool(...)` 装饰器 |
| 典型用途 | LLM驱动的对话式工具执行 | 系统集成、定时任务、外部API调用 |

### MCP工具清单（16个）

| 分组 | 工具 | 用途 |
|------|------|------|
| OCR和内容(4) | `ocr_recognize` | 识别答题卡图片 |
| | `generate_questions` | 简化版出题(仅LLM生成，不含RAG和审核) |
| | `generate_variant` | 基于原题ID生成变式题 |
| | `get_wrong_questions` | 查询学生错题列表 |
| 训练和复习(4) | `create_training` | 创建错题强化训练任务 |
| | `submit_training` | 提交训练结果 |
| | `get_review_tasks` | 查询待复习任务(艾宾浩斯遗忘曲线) |
| | `complete_review` | 完成一条复习任务 |
| 数据统计(4) | `get_class_overview` | 班级维度统计数据 |
| | `get_student_stats` | 单个学生详细统计 |
| | `get_knowledge_heatmap` | 班级知识点掌握热力图数据 |
| | `get_barrier_distribution` | 障碍类型分布统计 |
| 预警和通知(3) | `trigger_warning_check` | 触发学情预警检查 |
| | `get_pending_warnings` | 查询待处理预警 |
| | `send_notification` | 发送通知(微信/短信/App推送) |
| 诊断(1) | `diagnose_question` | 单题级别微观诊断(规则引擎+LLM) |

### MCP端点（3个）

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/mcp/tools` | GET | 返回所有已注册MCP工具的元数据列表(含name/description/parameters JSON Schema) |
| `/api/mcp/call` | POST | 请求体 `{"tool": "工具名", "arguments": {...}}`，调用并返回结果 |
| `/api/mcp/tools/{name}` | POST | 请求体 `{"arguments": {...}}`，RESTful调用方式 |

错误响应统一格式：404 `{"error": "tool_not_found"}` / 400 `{"error": "invalid_arguments"}` / 500 `{"error": "execution_error"}`

安全措施：JWT认证(所有端点) + 角色权限矩阵复用(ROLE_PERMISSIONS) + 速率限制扩展点(每IP每分钟60次)。

### Step M1: 实现MCP服务器

**操作**：在Claude Code中输入：

```
/opsx:apply
```

Claude Code将创建 `backend/app/mcp/server.py`（预计300-500行），包含16个工具定义（使用@tool装饰器）和3个端点（FastAPI路由）。

**关键API签名**：

```
# 工具注册示例
@tool(name="ocr_recognize", description="识别图片中的答题内容")
async def ocr_recognize(image_data: str) -> dict:
    # image_data: base64编码的图片数据
    # 调用 OCRService.recognize_answer_sheet()

# 端点注册
router = APIRouter(prefix="/api/mcp")

@router.get("/tools")
async def list_tools() → {"tools": List[ToolMeta], "total": int}

@router.post("/call")
async def call_tool(request: ToolCallRequest) → dict

@router.post("/tools/{name}")
async def call_tool_by_name(name: str, request: ToolArgumentsRequest) → dict
```

### Step M2: 编写MCP评测

在Claude Code中输入：

```
请创建 evals/baseline/mcp/ 目录并编写评测：

test_mcp_registration.py:
- 16个MCP工具全部注册
- 每个工具有正确的参数Schema(ocr_recognize有image_data, generate_questions有knowledge_points+quantity, send_notification有target_type+target_id+content)
- MCP工具与Agent工具不重复(search_exam_bank/show_exam_workbench等纯Agent工具不在MCP中)
- 三个端点可访问(使用FastAPI TestClient)

test_tool_division.py:
- 核心业务功能覆盖检查(OCR/出题/变式/错题/训练/复习/统计/预警/通知/诊断 -- 每项至少一个工具覆盖)
- 功能重叠检查(Agent和MCP共享工具不超过3个，且参数和行为有明确差异)
- 独有功能合理性检查(对话式交互工具归Agent，系统级操作归MCP)
```

验证：`pytest evals/baseline/mcp/ -v`

提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add MCP tool server
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| @tool装饰器未定义 | 自定义装饰器未实现 | 在server.py中先定义tool函数(接收name/description，返回装饰器) |
| 参数Schema自动提取失败 | 类型注解与JSON Schema映射不完整 | 手动为每个工具指定parameters_schema |
| JWT中间件冲突 | MCP端点与主应用共享认证中间件配置不一致 | 确认MCP路由也apply了相同的认证依赖 |
| 功能重叠过高(>3个工具) | 部分工具在Agent和MCP中都实现了完整逻辑 | 对于共享工具，MCP版实现简化版(去掉RAG和审核)，Agent版实现完整版 |

---

## Step 5: 全量验证 + Phase收尾

**操作**：在Claude Code中输入：

```
请帮我执行Phase收尾操作：

1. /cso
   安全审计：Prompt注入、Persona越权、工具滥用

2. run_evals --tier all --compare baseline.json
   确认全量Evals通过，无劣化>5%

3. pytest evals/baseline/persona/ evals/baseline/guard/ evals/baseline/mcp/ -v
   确认Persona+GuardState+MCP全部评测通过

4. /code-review
   双轴代码审查（规范轴 + 规格轴）

**合并**（在Claude Code中输入）：
请帮我将 phase-6/agent merge 到 main（使用 --no-ff），commit message 为 "merge: phase-6/agent (文档53-57) -- Agent系统完成"。合并后运行 run_evals 确认无劣化，然后推送到远程（过 no-mistakes 门禁）：git push no-mistakes main --tags。

**打标签**（在Claude Code中输入）：
请帮我打 tag v0.6.0，标注：Phase 6: Agent系统完成 -- 30工具 + 4 Persona + 4层护栏 + MCP16工具。确认相关测试全部通过后再打。
```

**你应该看到**：
- 安全审计通过(无Prompt注入漏洞、无跨角色工具泄漏)
- Evals无劣化
- Persona+Guard+MCP评测全部通过（约55个测试）
- 代码审查通过
- Agent Phase正式合入main，tag v0.6.0

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] 4个Persona YAML配置加载正确，工具数量符合设计
- [ ] 两层工具过滤(`TOOL_META ∩ YAML`)已实现，跨角色工具泄漏率0%
- [ ] GuardState四层防护全部通过评测
- [ ] _component和_route剥离机制正确工作
- [ ] MCP 16个工具注册，3个端点可调用
- [ ] Agent/MCP工具责任分工验证通过
- [ ] 安全审计(`/cso`)通过
- [ ] `run_evals --tier all` 通过，tag v0.6.0

## 组件总览

| 部分 | 核心文件 | 代码量 | 评测数 | 关键成果 |
|------|---------|:--:|:--:|------|
| Persona系统 | 4 YAML + langgraph_agent_v2.py | ~200行YAML + ~60行Python | ~18 | 四角色工具隔离，0%泄漏 |
| GuardState护栏 | agent/guard.py | ~150行新增 | 25 | 四层防护完整，审批门控就绪 |
| MCP服务器 | app/mcp/server.py | ~400行 | ~10 | 16工具+3端点，Agent/MCP分工清晰 |

**Phase 6 累计成果**（文档53-57）：
- 30个Agent工具全部实现
- Gateway + ReAct + SSE + 对话管理 + 三级记忆 + 审计日志 + Provider切换
- 4个Persona YAML配置
- GuardState四层安全护栏
- MCP 16个工具服务器
- 累计约150个评测场景全部通过

---

> **下一份文档**：[58-全链路验收与审查](./58-全链路验收与审查.md) -- 三端全链路验收、30个Agent工具逐个触发、三级审查、/ship发布、/retro复盘
