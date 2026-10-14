# 34. API 设计

> 产品设计文档 | ChemAI 智辅化学
> API 模块: 后端服务模块 (26 个路由模块)
> Agent 通道: Agent工具模块 (SSE 端点)

---

## 一、API 设计原则

### RESTful 风格

- URL 名词复数 (`/api/classes`, `/api/questions`)
- HTTP 方法语义化: GET(查询)、POST(创建)、PUT(更新)、DELETE(删除)
- 资源嵌套: `/api/classes/{class_id}/students`

### 统一响应格式

成功响应格式包含三个顶级字段：`success`（布尔值 true）、`message`（字符串如"操作成功"）、`data`（任意类型数据对象）。错误响应 FastAPI 标准格式，包含 `detail` 字符串字段描述错误信息。

HTTP 状态码：200 成功、201 创建成功、400 参数校验失败、401 未认证、403 权限不足、404 资源不存在、422 Pydantic 请求体验证失败、500 服务器内部错误。

### 版本策略

设计版本: v1.0（URL 路径中暂未携带版本号, 计划在 v2 中改为 `/api/v2/...`）

---

## 二、端点全景矩阵

31 个 Router 模块按 11 个业务域分组:

### 1. 认证与用户管理

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| auth | `/api/auth` | POST /login, POST /register | 后端服务模块 |
| user | `/api/users` | GET /me, PUT /profile | 后端服务模块 |
| teacher_application | `/api/teacher-applications` | POST /, GET / | 后端服务模块 |

### 2. 组织架构

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| school | `/api/school` | GET /, PUT / | 后端服务模块 |
| grade | `/api/grades` | GET /, POST /, DELETE / | 后端服务模块 |
| class_api | `/api/classes` | GET /, POST /, PUT / | 后端服务模块 |

### 3. OCR 与文档解析

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| ocr | `/api/ocr` | POST /recognize, POST /recognize/batch, POST /stats | 后端服务模块 |
| ocr_sheets | `/api/ocr` | POST /tasks/batch, GET /tasks/{id} | 后端服务模块 |

### 4. 考试与批改

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| exam | `/api/exam` | POST /create, GET /list, DELETE /{id} | 后端服务模块 |
| grading | `/api/grading` | POST /run, GET /results/{id} | 后端服务模块 |

### 5. 题目与题库

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| question | `/api/question` | POST /generate, POST /manual/select, GET /historical | 后端服务模块 |
| exam_bank | `/api/exam-bank` | GET /questions, POST /create-set | 后端服务模块 |
| knowledge | `/api/knowledge` | GET /cards, GET /graph | 后端服务模块 |

### 6. 诊断与学习

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| diagnosis | `/api/diagnosis` | GET /barrier/{class_id}/{exam_id}, PUT /config/{teacher_id} | 后端服务模块 |
| practice | `/api/practice` | POST /assign, POST /submit, GET /stats | 后端服务模块 |
| practice_wrong | `/api/practice` | GET /wrong/list, POST /wrong/{question_id}/master | 后端服务模块 |
| review | `/api/review` | GET /tasks, POST /complete | 后端服务模块 |

### 7. 报告与面板

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| report | `/api/report` | GET /teacher/{id}, GET /student/{id}, POST /send-to-students | 后端服务模块 |
| panel | `/api/panel` | GET /class/{id}, GET /knowledge/{kp}, GET /trend | 后端服务模块 |
| analytics | `/api/analytics` | GET /dashboard, GET /export | 后端服务模块 |

### 8. 家长与通知

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| parent | `/api/parent` | POST /login, GET /children, GET /notifications | 后端服务模块 |
| notification | `/api/notification` | POST /send, GET /list | 后端服务模块 |

### 9. 预警与日志

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| warning | `/api/warning` | GET /list, POST /resolve | 后端服务模块 |
| log | `/api/logs` | GET / | 后端服务模块 |

### 10. AI Agent

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| agent (LangGraph) | `/api/agent` | POST /chat/langgraph/stream, POST /chat/langgraph, POST /chat/langgraph/resume, POST /upload | Agent工具模块 |
| conversation | `/api/agent/chat` | GET /conversations, POST /new, GET /history/{thread_id}, DELETE /conversations/{thread_id} | Agent工具模块 |

### 11. 集成与 MCP

| Router | 前缀 | 核心端点 | 文件 |
|--------|------|----------|------|
| integration | `/api/integration` | GET /lms/config, POST /lms/test, POST /webhooks | 后端服务模块 |
| mcp | (无前缀) | MCP 工具注册端点 | 后端服务模块 |
| memory | `/api/memory` | GET /student/{id} | 后端服务模块 |

---

## 三、关键 API 详述

### POST /api/auth/login — 用户登录

**请求体**包含三个字段：`username`（字符串，如"teacher_wang"）、`password`（字符串）、`role`（字符串，如"teacher"）。

**成功响应**包含：`success`（true）、`token`（access_token JWT 字符串）、`refresh_token`（长期刷新令牌）、`user_id`（用户唯一标识）、`name`（显示名称）、`role`（角色名）。认证方式为 JWT Bearer Token（HS256 算法），Token 有效期：短期 access_token 24 小时，长期 refresh_token 7 天。

### POST /api/agent/chat/langgraph/stream — Agent SSE 流式对话

**请求体**包含：`message`（用户消息字符串如"出3道氧化还原选择题"）、`thread_id`（对话线程ID如"conv_abc123"）、`context`（上下文对象，含 user_id 和 role）。

**响应**为 SSE 事件流，依次包含以下帧：
- `event: thinking` → data 含 content 描述当前思考状态
- `event: tool_call` → data 含 tool 工具名和 args 参数对象
- `event: token` → data 含 content 逐字输出内容（可能有多个token帧）
- `event: done` → data 含 thread_id 和 tool_calls 汇总数组

### POST /api/question/generate — AI 出题

**请求体**包含：`knowledge_points`（知识点字符串数组如["氧化还原反应", "电化学"]）、`difficulty`（难度如"medium"）、`quantity`（整数3，题库数量，与 24 号文档 §3.1.2 一致）、`question_types`（题型数组如["选择题"]）、`teacher_id`（教师ID）。

**成功响应**包含：`success`（true）、`questions`（题目数组）、`generated_count`（已生成数量）、`total_available`（题库总可用量）。每道题目包含 question_id、content（题文）、options（选项数组）、answer（正确答案）、analysis（解析）、knowledge_points（知识点标签）、difficulty（难度）、audit_status（审核状态 passed/warning/blocked 之一）、audit_report（审核报告含四个维度的 status 和 overall_status）。

审核维度为：(1) 系数配平、(2) 反应条件、(3) 产物正确性、(4) 分子结构。阻断规则：任一维度 blocked 则题目标记为"不可用"。

### POST /api/ocr/tasks/batch — 批量答题卡上传

**请求**为 multipart/form-data 格式，包含：`images`（文件数组，jpg格式）、`teacher_id`（教师ID）、`class_id`（班级ID）、`exam_name`（考试名称如"高一期末模拟考"）。

**成功响应**包含：`success`（true）、`batch_id`（批次唯一标识）、`total`（总图片数）、`tasks`（任务数组，每项含 task_id、student_name、status）。

处理流程：OCR 识别答案 → 与标准答案对比 → 计算得分 → 统计班级错题分布。

### POST /api/grading/run — 触发 LLM 批改

**请求体**包含：`exam_id`（考试ID如"exam_abc"）、`class_id`（班级ID）。**成功响应**包含：`success`（true）、`grading_job_id`（批改任务标识）、`total_submissions`（总提交数）、`status`（处理状态如"processing"）。

### GET /api/diagnosis/barrier/{class_id}/{exam_id} — 班级障碍诊断

**响应**包含：`success`（true）、`class_id`、`exam_id`、`class_summary`（含 concept_rate/reading_rate/expression_rate 三个障碍类型占比率和 top_weak_kps 薄弱知识点数组）、`students`（学生数组，每项含 student_id、student_name、barrier_type 主导障碍类型、confidence 置信度、weak_kps 薄弱知识点、recommended_intervention 干预建议文本）。

### POST /api/practice/assign — 自适应练习布置

**请求体**包含：`student_id`（学生ID）、`question_count`（整数10）、`target_barrier`（目标障碍类型如"reading"）、`knowledge_points`（知识点数组如["盐类水解"]）。**响应**包含：`success`（true）、`practice_session_id`（练习会话标识）、`questions`（题目数组）、`estimated_time_minutes`（预估完成时间分钟数）。

### POST /api/report/send-to-students/{exam_record_id} — 一键发送报告

**响应**包含：`success`（true）、`sent_count`（已发送数量）、`failed_count`（失败数量）、`parent_notifications_sent`（家长通知已发送数量）。同时触发家长通知推送（对于已绑定家长的学生）。

---

## 四、SSE 事件协议

Agent SSE 流式输出的完整事件类型定义:

| event | data payload | 说明 |
|-------|-------------|------|
| `phase` | phase 值（thinking/executing/planning/reply/awaiting_approval，与 39 号文档一致） | Agent 状态切换 |
| `tool_call` | toolCallId + name 工具名 | 工具调用开始 |
| `tool_args` | toolCallId + delta（JSON 片段） | 工具参数流式传入（39 号文档定义） |
| `tool_result` | name 工具名 + success 布尔 + result 结果 | 工具调用结束 |
| `text` | content 字符串 | LLM 流式文本输出 |
| `component` | component 组件名 + params 参数 | 内联面板渲染指令 |
| `navigate` | page 目标页 + params 参数 | 页面跳转指令 |
| `populate` | target 目标组件 + data 数据 | 数据填充指令 |
| `action` | action 动作类型 + payload 载荷 | 前端行为触发 |
| `exam_images` | q_index 题目索引 + urls 图片列表 | 真题图片推送 |
| `plan_summary` / `plan_progress` | goal + steps / step 进度 | 复杂任务规划与步骤进度 |
| `context` | used_tokens + 占用百分比 | 上下文占用指示器数据 |
| `error` | message + recoverable | 异常信息 |
| `done` | thread_id + tool_calls 汇总 | 对话结束 |

前端通过 fetch + ReadableStream 流式读取 SSE 响应，按事件类型分发渲染：text 追加到聊天区、tool_call 显示调用指示器、component 内联渲染面板、navigate 触发页面跳转、done 关闭流。

---

## 五、认证体系

### JWT 流程

1. `POST /api/auth/login` → 签发 access_token (24h) + refresh_token (7d)
2. 所有 API 请求携带: `Authorization: Bearer {access_token}`
3. access_token 过期 → `POST /api/auth/refresh` → 签发新 access_token

### 认证实现

认证基于 JWT Bearer Token（HS256），access_token 有效期 24 小时，refresh_token 有效期 7 天。认证中间件的白名单路径、Token 校验逻辑和角色权限体系的完整设计详见 [22-权限分级与访问控制系统设计](./22-权限分级与访问控制系统设计.md)。

### 角色权限矩阵

| API 域 | admin | teacher | student | parent |
|--------|-------|---------|---------|--------|
| Auth | R/W | R/W | R/W | R/W |
| School/Grade | R/W | R | - | - |
| Class | R/W | R/W | R | - |
| Exam | R | R/W | R | - |
| Question | R | R/W | - | - |
| OCR | R | R/W | - | - |
| Grading | R | R/W | - | - |
| Diagnosis | R | R/W | R(自身) | - |
| Practice | R | R/W | R/W | - |
| Report | R | R/W | R(自身) | R(子女) |
| Panel | R | R/W | - | - |
| Parent | - | - | R | R/W |
| Notification | R | R/W | R | R |
| Warning | R | R/W | - | - |

图例: R = Read, W = Write, - = 不可访问

---

## 六、分页/排序/筛选

### 通用查询参数

`GET /api/exam/list?limit=20&offset=0&sort_by=exam_date&order=desc`

| 参数 | 类型 | 
|------|------|--------|------|
| `limit` | int | 20 | 每页数量 (最大 100) |
| `offset` | int | 0 | 偏移量 |
| `sort_by` | string | created_at | 排序字段 |
| `order` | string | desc | asc / desc |
| `keyword` | string | - | 关键词搜索 |
| `status` | string | - | 状态过滤 |
| `from_date` | date | - | 开始日期 |
| `to_date` | date | - | 结束日期 |

### 筛选示例

- 搜索全国卷2024年的中等难度题目: `GET /api/question/historical?source=全国卷&year=2024&difficulty=medium`
- 获取某班级最近考试记录: `GET /api/exam/list?class_id=class_abc&sort_by=exam_date&order=desc`
- 获取教师通知（分页）: `GET /api/parent/notifications?parent_id=p_abc&limit=20&offset=0`

---

## 七、错误码体系

### 标准错误响应格式

包含三个字段：`detail`（具体错误描述如"请检查 student_id 是否正确"）、`error_code`（标准错误码如"RESOURCE_NOT_FOUND"）、`suggestion`（修复建议文本）。当前版本以 `detail` 单字段返回实际错误，`error_code` 与 `suggestion` 作为错误码体系预留，随版本逐步启用。

### 错误码定义

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| `VALIDATION_ERROR` | 422 | Pydantic 请求体验证失败 |
| `AUTHENTICATION_REQUIRED` | 401 | 未携带有效 token |
| `TOKEN_EXPIRED` | 401 | Token 已过期, 请刷新 |
| `PERMISSION_DENIED` | 403 | 无此资源访问权限 |
| `RESOURCE_NOT_FOUND` | 404 | 请求的资源不存在 |
| `DUPLICATE_RESOURCE` | 400 | 重复创建 (如重复绑定) |
| `BUSINESS_RULE_VIOLATION` | 400 | 业务规则冲突 (如绑定码错误) |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `LLM_SERVICE_UNAVAILABLE` | 503 | LLM 服务暂时不可用 |
| `OCR_SERVICE_UNAVAILABLE` | 503 | OCR 服务暂时不可用 |

### 业务错误示例

绑定学生失败返回："detail: 绑定码错误", "error_code: BUSINESS_RULE_VIOLATION", "suggestion: 请确认绑定码与学生端显示的一致"。解除绑定失败返回："detail: 绑定关系不存在", "error_code: RESOURCE_NOT_FOUND", "suggestion: 该绑定可能已经解除或不存在"。

---

## 八、速率限制

- 默认限制：每 IP 每分钟 60 次请求，超出返回 HTTP 429 + Retry-After header
- 响应头：X-RateLimit-Limit（限制上限）、X-RateLimit-Remaining（剩余次数）、X-RateLimit-Reset（重置时间戳）
- 关键端点差异化限制：
  - POST /api/question/generate — 10 次/min
  - POST /api/diagnosis/run-llm — 30 次/min
  - POST /api/ocr/tasks/batch — 20 次/min
- 429 响应格式：`{"error": "rate_limit_exceeded", "message": "请求过于频繁，请稍后重试", "retry_after": 30}`

> 通用 API 限流为设计规范预留；当前版本在 LLM 服务内部实现调用频率限制（30 次/分钟内存限流），通用网关限流随部署形态逐步启用。

---

*API 端点总数: 31 个 Router 模块, 约 250 个端点*
*认证方式: JWT Bearer Token (HS256)*
*API 基础路径: `http://localhost:8000/api/` (开发) / `https://chemai.example.com/api/` (生产)*
*文档: FastAPI 自动生成 Swagger UI (`/docs`) 和 ReDoc (`/redoc`)*
