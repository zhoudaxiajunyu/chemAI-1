# QA 报告 — chemAI-1 API 面

- **日期**：2026-10-15
- **分支**：`phase-2/data-model`（基线 commit `ccd7f42` + 未提交的复审修复）
- **目标**：`http://127.0.0.1:8000`（uvicorn 实测运行）
- **深度**：Standard（关键/高 + 中等）
- **模式**：diff-aware（功能分支无 Web UI，自动进入）

## 方法说明（TRAE / 本项目适配）

本阶段交付物是 **FastAPI 后端 API**，`frontend/` 仅有占位 `.gitkeep`，无浏览器界面。
gstack-qa 的"不适用场景"排除了纯后端 API 测试，故按 skill 工作流做等价适配：

| skill 原动作 | 本项目等价动作 |
|---|---|
| 点击/填写表单 | 真实 HTTP 请求（httpx，78 个用例） |
| 控制台错误检查 | 服务端 uvicorn 日志扫描（Traceback / 500 / Exception） |
| 截图证据 | 请求→状态码→响应体结构化记录 |
| 链接可达性 | 路由可达性 + 白名单行为 |
| 响应式检查 | 内容协商（JSON / text/plain / form / 畸形 JSON / 超长载荷） |
| 可访问性 | 协议合规性（RFC 7235 scheme + WWW-Authenticate） |

未使用浏览器工具：无 Web UI 可测，Swagger UI（`/docs`）以 HTTP 探测其资源与 OpenAPI 内容代替。

## 健康评分

| 类别 | 权重 | 修复前 | 修复后 |
|---|---|---|---|
| Console（服务端异常） | 15% | 100 | 100 |
| Links（端点可达性） | 10% | 100 | 100 |
| Visual（文档呈现） | 10% | 70 | 95 |
| Functional（功能正确性） | 20% | 85 | 95 |
| UX（API 可用性/一致性） | 15% | 78 | 88 |
| Performance | 10% | 95 | 95 |
| Content（文案） | 5% | 95 | 95 |
| Accessibility（协议合规） | 15% | 62 | 85 |
| **加权总分** | | **84 / 100** | **94 / 100** |

正向面：96 个请求（修复前）+ 78 个请求（修复后）**零 500、零未捕获异常**；全部 401/403/404/405/422 语义正确。

## Top 3 Things to Fix（剩余项）

1. **401 响应缺 `WWW-Authenticate: Bearer`**（低）— RFC 7235 建议携带，客户端无法据此触发重新认证流程。
2. **refresh_token 无轮换/撤销**（已知裁剪）— 7 天内同一 refresh 可反复换取 access；泄露后无法失效。
3. **RBAC 越权 403 与家长绑定前置 403 无端到端证据**（范围缺口）— 业务端点未在本阶段实现，所有受保护路径均返回 404。

---

## 发现清单

### ISSUE-001 — Authorization scheme 大小写敏感（中等，已修复 ✅）

- **现象**：`Authorization: bearer <有效token>` 被判 401；`Bearer <有效token>` 正常。
- **合规依据**：RFC 7235 §2.1 — auth-scheme 大小写不敏感。
- **证据**：修复前 `M|401|GET /api/classes + 小写 bearer 前缀` → 修复后 `M|404|...`（中间件已放行，路由不存在故 404，证明 token 解析成功）。
- **根因**：`backend/app/core/middleware.py` 用 `header.startswith("Bearer ")` 做精确前缀匹配。
- **修复**：改为按空格切分后 `scheme.lower() != "bearer"` 比较，并容忍多空格；scheme-only（无 token）仍 401。
- **回归测试**：`test_lowercase_bearer_scheme_accepted`、`test_scheme_only_or_whitespace_tolerant`。

### ISSUE-002 — OpenAPI 未声明 Bearer 安全方案（中等，已修复 ✅）

- **现象**：`components.securitySchemes` 与全局 `security` 均缺失；`/docs` 无 **Authorize** 按钮，所有 "Try it out" 必然 401。
- **影响**：任何按 `/docs` 自测的开发者/前端联调会被误导。
- **证据**：修复前 `D|openapi securitySchemes|"MISSING"` → 修复后 `{"BearerAuth": {"type":"http","scheme":"bearer","bearerFormat":"JWT"}}`。
- **根因**：认证由**中间件**而非路由依赖实现，OpenAPI 无法自动推导。
- **修复**：`backend/app/main.py` 增加自定义 `app.openapi`；与 `is_whitelisted` 同源，仅真正受保护的路径标记 `security`（登录/刷新/家长登录保持无 security，语义正确）。
- **回归测试**：`test_openapi_declares_bearer_security_scheme`。

### ISSUE-003 — 请求体无上界 + 未知字段静默忽略（中等，已修复 ✅）

- **现象 A**：`username`/`password` 仅 `min_length=1`，无 `max_length`；10 万字符输入被接受并进入 DB 查询（返回 401，无崩溃，但构成无界输入）。
- **现象 B**：未知字段被静默忽略 — 提交 `{"is_admin": true}` 仍返回 200，前端拼写错误会静默失效。
- **证据**：修复前 `L|200|教师登录 额外字段`、`L|401|10 万字符密码` → 修复后 `L|422|额外字段`、`L|422|10 万字符密码`。
- **修复**：`backend/app/schemas/auth.py` 全部请求模型加 `ConfigDict(extra="forbid")` 与合理上界（username ≤150、password ≤128、phone ≤20、refresh_token ≤4096）。
- **回归测试**：`test_login_rejects_unknown_fields_and_oversized_input`。

### ISSUE-004 — 401 缺 `WWW-Authenticate` 头（低，未修）

- **证据**：`E|是否有 WWW-Authenticate 头|"MISSING"`。
- **说明**：Standard 深度不含低严重性项，记录待办。

### ISSUE-005 — 家长"账号未通过审核"文案（已核实**非**问题）

- 该分支位于密码校验**之后**，攻击者需先提供正确密码才能看到该文案，**不构成账号状态枚举**。错误密码与不存在用户的 detail 完全一致（`true`），无枚举面。

### ISSUE-006 — refresh_token 无轮换/撤销（低，已知裁剪）

- **证据**：`R|200|refresh 幂等复用同一 refresh` — 同一 refresh 7 天内可无限次换取 access。
- **说明**：proposal/design 已明确"Token 黑名单不做"，属已接受的范围裁剪，非缺陷；泄露场景无撤销手段，建议后续阶段加轮换。

### ISSUE-007 — RBAC/绑定校验无端到端证据（信息，范围缺口）

- **证据**：`P|404|GET /api/parent/children 用教师 token(越权)` — 中间件放行，因无路由返回 404。
- **说明**：越权 403 仅由单元测试覆盖；家长 `active` 绑定前置 403 在实现中无承载（proposal 已裁剪业务端点）。

---

## 已验证正确的行为（正向证据）

**认证与令牌**
- 登录成功 200，返回 `success/token/refresh_token/user_id/name/role` 六字段。
- access 声明 `sub/user_id/role/school_id/type=access/iat/exp`；`exp-iat = 86400`（24h）。
- refresh 声明 `type=refresh`；`exp-iat = 604800`（7d）。
- 学生 token `school_id=1` 正确经 `class→grade→school` 回溯。
- 家长 token `role=parent` 且 **不含 school_id**。

**失败路径（全部 401，无 500）**
- 错误密码 / 不存在用户 / pending 教师 / rejected 教师 / 角色不匹配 / SQL 注入式用户名 / 中文用户名 / 4 字节 emoji 密码 / 篡改末位 token / 伪造 token / 非 Bearer 头 / scheme-only。

**刷新端点**
- refresh_token 换新 access 200；**access_token 调 refresh → 401**（type 校验生效）；垃圾串 401；空串与缺字段 422。

**中间件白名单**
- `/health` 携带伪造 Bearer 仍 200（白名单）。
- `/api/parent/children` 无 token → 401（**未被 `/api/parent/` 前缀误放行**，精确白名单生效）。
- 有效 token 访问不存在的受保护路径 → 404（中间件不越权拦截）。

**输入健壮性（全部 422，无 500）**
- 无 body / text/plain / 非法 JSON / JSON 数组 / 字段类型错 / form 表单 / null 字段 / 缺字段 / 超长载荷。

**一致性与性能**
- 401 与 404 错误体同形状（`detail`），Content-Type `application/json`。
- 登录（含 bcrypt）5 次耗时 185–203 ms（cost 12，符合预期）；`/health` 2–21 ms。

**迁移**
- `alembic upgrade head` 建 24 表；`alembic check` 无 drift（沿用上一轮证据）。

---

## 验证命令

```
# 全量回归
.\venv\Scripts\python.exe -m pytest backend/tests/ -q      # 250 passed

# 起服务（QA 用）
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## 修复状态汇总

| 编号 | 严重性 | 状态 | 提交 |
|---|---|---|---|
| ISSUE-001 | 中等 | verified | 待提交（工作树） |
| ISSUE-002 | 中等 | verified | 待提交（工作树） |
| ISSUE-003 | 中等 | verified | 待提交（工作树） |
| ISSUE-004 | 低 | deferred | — |
| ISSUE-006 | 低 | accepted-scope | — |
| ISSUE-007 | 信息 | scope-gap | — |

> 修复文件：`backend/app/core/middleware.py`、`backend/app/main.py`、`backend/app/schemas/auth.py`、
> `backend/tests/test_middleware.py`、`backend/tests/test_auth_api.py`
