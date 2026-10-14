# CONTEXT.md — ChemAI 领域术语表

本文件是 ChemAI 智辅化学的**领域术语权威口径**。AI 在写代码、写文档、做诊断时必须使用此处定义的中文名与英文名，不得自造同义词。每个术语给出中英文名称与一句话定义。

> 更新时机：出现新术语或术语含义变化。来源以产品设计文档 29 / 33 / 26 / 24 / 23 / 37 号为准。

---

## 一、核心实体（Core Entities）

| 中文 | 英文 | 定义 |
|------|------|------|
| 学校 | School | 系统顶层容器，包含多个年级；所有数据查询沿"学校→年级→班级"向下展开，确保跨校隔离。 |
| 年级 | Grade | 学校下的一级划分（如"高一"），包含多个班级。 |
| 班级 | Class | 数据隔离的核心边界，隶属于某年级，包含多名学生；归属关系向上可追溯到年级与学校。 |
| 教师 | Teacher | 归属某所学校的教学主体，含账号状态（待审核/已通过/已拒绝）与角色（系统管理员/教务管理员/学科组长/普通教师）。 |
| 学生 | Student | 系统核心实体，归属某班级，携带障碍画像、练习追踪、家长绑定码三类关键数据。 |
| 家长 | Parent | 通过 6 位绑定码与学生建立亲子关联的监护人，一个家长可绑定多个子女。 |
| 统一账户 | Account | 所有用户的统一登录入口，通过角色字段区分身份，一对一关联教师/学生/家长之一。 |
| 任课关系 | TeacherClassSubject | 教师与班级之间的多对多关联表，标注该教师是否为班主任。 |

---

## 二、组织与权限（Org & Access）

| 中文 | 英文 | 定义 |
|------|------|------|
| 数据隔离 | Data Isolation | 通过"学校→年级→班级"层级链路实现的多租户隔离：教师只见本校/任教班级数据，家长只见绑定子女数据，学生只见自己数据。 |
| 权限矩阵 | RBAC Permission Matrix | 由教师角色（系统管理员/教务管理员/学科组长/普通教师）决定的功能权限范围（详见 22 号文档）。 |
| 绑定码 | Binding Code | 学生"我的"页面中展示的 6 位字母数字码（不含 0/O/1/I），家长在家长端输入以建立亲子关联。 |
| 亲子绑定 | StudentParentBinding | 通过绑定码关联学生与家长的记录，含绑定状态与关系类型（父亲/母亲/其他监护人）。 |

---

## 三、学习概念（Learning Concepts）

| 中文 | 英文 | 定义 |
|------|------|------|
| 知识点 | KnowledgePoint | 化学知识图谱中的一个节点（如"盐类水解"），含所属分类、PubChem 编号、关联题目数、动态错误率。 |
| 掌握度 / 掌握标准 | Mastery | 同一知识点连续答对 N 次（教师默认 3）视为已掌握。 |
| 障碍画像 | Barrier Profile | 学生三维障碍类型分布，JSON 存储，形如 `{"concept":0.30,"reading":0.50,"expression":0.20}`，三值之和为 1.0。 |
| 近侧发展区窗口 | ZPD Window (Zone of Proximal Development) | 自适应练习的难度匹配窗口（30 题），映射 easy/medium/hard 三档；competition 不自动分配。 |
| 间隔复习 | Spaced Repetition | 按艾宾浩斯遗忘曲线安排错题复习，级别 Level 0-5（1/3/7/14/30 天 / 不再安排）。 |
| 复习任务 | ReviewTask | 每道错题自动创建的复习任务，状态为：待复习 / 超期 / 已掌握。 |
| 复习级别 | Review Level | 复习任务所处的遗忘曲线档位（0-5），答对升级、答错降级。 |
| 学习计划 | Learning Plan | 教师为学生制定的个性化计划，含标题、创建日期、每日任务列表（天数序号 + 主题 + 练习题数量）。 |
| 学情预警 | Warning | 系统自动触发的学习状态告警，四类：连续未登录（警告）/ 成绩下滑（严重）/ 高错误率（警告）/ 新障碍出现（提示）。 |

---

## 四、诊断概念（Diagnosis）

| 中文 | 英文 | 定义 |
|------|------|------|
| 障碍类型 | Barrier Type | 对错误作答的根因分类枚举：`concept`（概念理解型）/ `reading`（审题障碍型）/ `expression`（表述障碍型）。 |
| 概念理解型 | Concept Barrier | 不理解底层化学概念与原理——选错基本原理、混淆相似概念、无法解释推理过程。 |
| 审题障碍型 | Reading Barrier | 读题不完整或落入陷阱——遗漏题干关键词、答非所问，但概念本身掌握。 |
| 表述障碍型 | Expression Barrier | 理解正确但表达不规范——方程式书写错误、漏写单位/有效数字、配平或条件写漏。 |
| 主导障碍 | Dominant Barrier | 学生三维障碍分布中占比最高的那一类。 |
| 障碍诊断 | Barrier Diagnosis | 三段式流程：规则引擎初筛 → LLM 深度分析 → 综合判定，写回作答记录的障碍类型并聚合学生画像。 |
| 诊断置信度 | Diagnosis Confidence | LLM 诊断结果的可信度（0.0-1.0），三级体系：≥0.8 高（自动采纳）/ 0.7-0.8 中（采纳但标注"需关注"）/ <0.7 低（建议人工复核）。 |
| 障碍诊断配置 | BarrierConfig | 教师可自定义的阈值配置：concept=3 / reading=2 / expression=3 / mastery=3，另含"自动同步学生端"开关（默认关闭）。 |
| 教师覆盖 | Teacher Override | 教师手动推翻 AI 判定：指定类型占 90%、其余各 5%，记录覆盖原因到操作日志；后续新作答会逐步稀释覆盖权重。 |
| 干预建议 | Recommended Intervention | 按障碍类型给出的教学建议（concept→基础概念复习 / reading→审题技巧 / expression→规范表述训练）。 |
| 薄弱知识点 | Weak Knowledge Point | 某学生在其主导障碍上反复出错的知识点标签集合。 |

---

## 五、题目与考试（Question & Exam）

| 中文 | 英文 | 定义 |
|------|------|------|
| 题目类型 | Question Type | 题型枚举：`choice`（选择）/ `fill`（填空）/ `calc`（计算）/ `experiment`（实验）/ `inference`（推断）。 |
| 题目难度 | Difficulty | 难度枚举：`easy` / `medium` / `hard` / `competition`；竞赛级仅支持手动录入，不自动分配。 |
| 题目来源 | Question Source | 来源枚举：`ai`（AI 生成）/ `manual`（手动录入）/ `daily_practice`（日常练习）/ `ocr`（OCR 导入）。 |
| 审核状态 | Audit Status | 四维安全审核结果枚举：`passed`（通过）/ `warning`（警告可用）/ `blocked`（阻断不可用，不下发学生）。 |
| 四维安全审核 | Four-Dimension Safety Audit | 对化学方程式的四维校验：系数配平 / 反应条件 / 产物稳定性 / 分子结构。 |
| 审核报告 | Audit Report | 每道 AI 题经审核后生成的报告，含四维结果 + 综合判定 + 审核耗时。 |
| 出题工作台 | Exam Workbench | 教师端四 Tab 单页应用（出题工作台 / 题库管理 / 历史真题库 / 考试列表）。 |
| 题库文件夹 | QuestionSet | 题目的组织单元，含名称与题目列表（通过 QuestionSetItem 多对多关联，含排序字段）。 |
| 考试类型 | Exam Type | 枚举：`monthly`（月考）/ `practice`（练习）/ `homework`（作业）；决定统计口径（月考影响学情报告，练习影响 ZPD）。 |
| 考试记录 | ExamRecord | 归属于某班级的一次考试/练习，含类型、日期、参考人数、平均分、错题统计。 |
| 考试状态 | Exam State | 考试生命周期：创建 → 发布 → 进行中 → 阅卷 → 完成 → 归档。 |
| 学生作答 | StudentAnswer | 关联学生、题目、考试的一条作答记录，含作答内容、是否正确、障碍类型、连续错误/正确计数器。 |
| 历年真题库 | Historical Exam Bank | 系统预置的高考真题与模拟题集合，是 RAG 的知识底座，含来源、年份、题号、区分度、答案。 |
| 真题集 | Historical Exam Set | 对历年真题的组织归类单元，含名称、来源地区、年份、来源说明。 |
| 变体题 | Variant Question | 基于某道真题（蓝本题）经 RAG 生成的同知识点/同难度变体。 |
| 蓝本题 | Variant Source Question | 生成变体题时指定的参考原题（`variant_qid` + `variant_source="historical"`）。 |
| 陷阱提示 | Trap Hint | 按题目知识点自动生成的教学提示（如"盐类水解"→"注意区分水解与电离"）。 |

---

## 六、Agent 概念（Agent）

| 中文 | 英文 | 定义 |
|------|------|------|
| 智能体 | Agent | 平台的智能核心，把自然语言输入转换为工具调用链，经 SSE 实时推送执行过程与结果。 |
| 单智能体架构 | Single-Agent Architecture (v2) | 当前主版本：单一 ReAct Agent 全量注入 42 领域工具，由 LLM 通过工具描述自选。 |
| 多智能体架构 | Multi-Agent Architecture (v1) | 回退版本：Coordinator + Router + 6 Sub-Agent，路由准确率约 75%。 |
| ReAct 循环 | ReAct Loop | Agent 的"思考 → 选工具 → 执行 → 观察"迭代循环。 |
| 角色设定 | Persona | Agent 的行为配置（YAML），含 system_prompt 与 available_skills 工具白名单。 |
| 教研助手 | Teacher Persona | 面向教师的 AI 教学分析助手，近全量工具（约 35 个）。 |
| 化学助教（学生端） | Student Persona | 面向学生的 AI 辅导老师，绝对不直接给答案，苏格拉底式提问，10 个工具。 |
| 化学助教（通用） | Tutor Persona | 默认 Persona，兼具辅导与出题能力，约 21 个工具。 |
| 家长助手 | Parent Persona | 面向家长的学情报告助手，通俗语言、不制造焦虑，4 个工具 + data_access 可见性约束。 |
| 护栏 | Guard | 请求级安全基础设施，四层顺序检查：前置条件 → 调用限制 → 去重 → 审批门控。 |
| 护栏状态 | GuardState | 每次 Agent 调用创建的实例，跟踪去重、限制、审批状态。 |
| 审批门控 | Approval Gate | 破坏性操作（如布置练习、删除题库）需教师确认后才执行；支持"确认/同意/可以"自然语言确认。 |
| 意图分类器 | Gateway | 请求进入 Agent 前的预分类器，双路径（LLM 优先 + 关键词兜底），输出 chat 或 navigate。 |
| 规划器 | Planner | 将复杂教学任务拆解为结构化执行步骤（最多 6 步）的组件。 |
| 计划步骤 | PlanStep | 计划中的一步，含 step / skill / args / depends_on / description / status。 |
| 执行计划 | Plan | 一个目标及其 PlanStep 列表（最多 6 步），支持 `${step_N.field}` 变量引用注入。 |
| 工作记忆 | Working Memory | 内存滑动窗口，保留最近 20 条消息，生命周期为单次请求。 |
| 情景记忆 | Episodic Memory | 内存字典，存本次对话产生的关键事件（诊断结果、考试记录），随请求销毁。 |
| 学生档案 | Student Profile Memory | 跨请求持久化的学生画像（姓名、障碍类型、练习完成数），以 System Message 注入消息列表最前。 |
| 上下文裁剪 | Context Trimming | 消息超 30 条时的三层保留策略：最近 6 条无条件保留 + 教学关键词消息 + LLM 摘要（≤200 字）。 |
| 工具元数据注册表 | TOOL_META | 以工具函数为键，注册可用 persona 列表与每轮 call_limit 的注册表，启动时做完整性断言。 |
| MCP 工具服务器 | MCP Server | 面向外部系统/定时任务的 Model Context Protocol 工具服务器，16 个工具，端点前缀 `/api/mcp`。 |

**SSE 事件类型（Agent → 前端）**：

| 中文 | 英文 | 定义 |
|------|------|------|
| 阶段事件 | `phase` | 状态切换：thinking（分析中）/ executing（执行中）/ planning（规划中）/ reply（回复中）/ awaiting_approval（等待审批）。 |
| 工具调用 | `tool_call` | 工具调用开始，含 toolCallId / name / tool 分类。 |
| 工具参数 | `tool_args` | 工具参数流式片段（delta）。 |
| 工具结果 | `tool_result` | 工具调用结束，含 success 与 result。 |
| 流式文本 | `text` | LLM 逐 token 生成的文本。 |
| 内联面板 | `component` | 渲染内联组件（如 exam-workbench）。 |
| 页面跳转 | `navigate` | 触发前端跳转（含 page 与 params）。 |
| 数据填充 | `populate` | 向目标组件填充数据。 |
| 前端行为 | `action` | 触发前端动作（如 openTab）。 |
| 真题图片 | `exam_images` | 真题配图列表（q_index / title / urls）。 |
| 计划总览/进度 | `plan_summary` / `plan_progress` | 复杂任务拆解后的计划总览与逐步骤进度。 |
| 上下文占用 | `context` | 已用/剩余/占用百分比，供"上下文占用"指示器。 |
| 错误 | `error` | 含 message 与 recoverable。 |
| 结束 | `done` | 对话结束标记。 |

---

## 七、OCR 概念（OCR）

| 中文 | 英文 | 定义 |
|------|------|------|
| 答题卡 | Answer Sheet | 教师拍照/上传的试卷或答题卡，OCR 批改系统的入口。 |
| 上传会话 | UploadSession | 记录一次文件上传全生命周期的会话实体。 |
| 上传状态机 | UploadSession State Machine | UPLOADED → PREVIEWING → READY → IMPORTING/GRADING → IMPORTED；终态 DISCARDED / ERROR。 |
| 批改任务 | OCRTask | 单张答题卡的识别与批改任务，状态 pending → processing → done / failed（支持重试）。 |
| 批改管线 | Grading Pipeline | 10 步流程：批量上传 → OCR 识别 → 学生信息提取 → 答案来源选择 → LLM 批改 → 教师确认 → 保存 → 触发诊断 → 班级统计 → 报告生成。 |
| OCR 引擎 | OCR Engine | 三条降级链的候选引擎：PP-OCRv6（本地默认）/ 百度 AI 教育 OCR（在线）/ MinerU（PDF 解析）/ VLM（视觉兜底）。 |
| 降级链 | Degradation Chain | 引擎失败时逐级切换的策略；命中降级时标记 `fallback_used=true`。 |
| 试卷切题 | Paper Cut | `paper_cut_edu` 接口，仅返回题目的边界框（题目分割）。 |
| 学生信息提取 | Student Info Extraction | OCR 完成后用正则从识别文本中提取学号与姓名。 |
| 低置信度标记 | Low-confidence Flag | 识别置信度低于阈值时标记"建议人工复核"，目标占比 < 10%。 |

---

## 八、前端与设计（UI & Design）

| 中文 | 英文 | 定义 |
|------|------|------|
| 设计系统 | Design System | 隐喻 "Academic Catalyst（学术催化剂）"，三支柱：学术严谨 / 现代学术 / 清晰分层。 |
| 设计令牌 | Design Token | 颜色/字体/间距的集中定义（Tailwind 类名 + antd 主题），保证跨页面视觉一致。 |
| 系统声音 | Oxford Blue `#002147` | 主色，用于主按钮、侧边栏、标题强调——代表"系统"。 |
| AI 声音 | Teal `#0d7377` | 辅助主色，用于 AI 对话气泡、辅助按钮、化学元素强调——代表"AI"。 |
| 纸的声音 | Cool Background `#f7f9fc` | 页面主背景色——代表"纸"。 |
| 化学式渲染 | Chemistry Formula Rendering | 前端经 KaTeX + mhchem 渲染 `\ce{}` 语法；后端响应阶段把纯文本化学式转为带上下标格式。 |
| 页面桥接 | Page Bridging | Agent 经 `_route`/`_component` → SSE 事件 → 前端桥接存储 → 目标页面读取并自动配置状态的机制。 |

> 前端视觉细节（色值、字号、间距、圆角、阴影、组件样式、断点）以 `DESIGN.md` 为准。

---

## 九、枚举速查（Enum Quick Reference）

| 概念 | 取值 |
|------|------|
| 障碍类型 BarrierType | `concept` / `reading` / `expression` |
| 考试类型 ExamType | `monthly` / `practice` / `homework` |
| 题目来源 QuestionSource | `ai` / `manual` / `daily_practice` / `ocr` |
| 审核状态 AuditStatus | `passed` / `warning` / `blocked` |
| 题目难度 Difficulty | `easy` / `medium` / `hard` / `competition` |
| 题目类型 QuestionType | `choice` / `fill` / `calc` / `experiment` / `inference` |
| 教师角色 TeacherRole | 系统管理员 / 教务管理员 / 学科组长 / 普通教师 |
| 复习状态 ReviewStatus | 待复习 / 超期 / 已掌握 |
| 复习级别 ReviewLevel | Level 0-5（1/3/7/14/30 天 / 不再安排） |
| 批改任务状态 OCRTaskStatus | `pending` / `processing` / `done` / `failed` |
| 上传会话状态 UploadSessionStatus | `UPLOADED` / `PREVIEWING` / `READY` / `IMPORTING` / `IMPORTED` / `GRADING` / `DISCARDED` / `ERROR` |
