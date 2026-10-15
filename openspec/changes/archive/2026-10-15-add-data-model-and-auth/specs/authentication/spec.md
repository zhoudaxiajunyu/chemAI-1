# Spec Delta

## Purpose

定义统一账户体系的认证行为契约：JWT 令牌的签发、刷新与校验规则，login/refresh 两个公开端点的请求/响应契约与错误语义，以及认证中间件对白名单与受保护路径的 401 处理。

## ADDED Requirements

### Requirement: 登录签发令牌

系统 SHALL 提供 `POST /api/auth/login` 端点，接收 username、password、role 三字段。凭证校验 MUST 使用 bcrypt 哈希比对。校验通过时 MUST 返回：`success: true`、`token`（access_token）、`refresh_token`、`user_id`、`name`、`role`。密码错误 MUST 返回 HTTP 401。账号状态为 pending 或 rejected 的教师 MUST NOT 签发令牌（返回 401 并提示账号未审核）。

#### Scenario: 正确凭证登录

- **WHEN** 以存在的用户名、正确密码、匹配角色调用 login
- **THEN** 返回 200，含 access_token 与 refresh_token，且 role 与账户一致

#### Scenario: 错误密码

- **WHEN** 以存在的用户名、错误密码调用 login
- **THEN** 返回 401，不签发任何令牌

#### Scenario: 待审核教师拒绝登录

- **WHEN** 状态为 pending 的教师以正确凭证登录
- **THEN** 返回 401，提示账号未通过审核

### Requirement: JWT 令牌结构

系统 SHALL 以 HS256 算法签发 JWT，密钥来自环境变量。Access token 有效期 MUST 为 24 小时，refresh token MUST 为 7 天。Access token 的 payload MUST 包含：`user_id`、`role`、`school_id`（家长角色除外）、`type: "access"`、`iat`、`exp`。家长角色的令牌 MUST 令 `role = "parent"` 且不携带 `school_id`。

#### Scenario: 令牌包含必备声明

- **WHEN** 教师登录成功并解码 access_token
- **THEN** payload 含 user_id、role、school_id、type=access、iat、exp，且 exp-iat 为 24 小时

#### Scenario: 家长令牌无 school_id

- **WHEN** 家长登录成功并解码 access_token
- **THEN** role 为 parent 且 payload 中不存在 school_id

### Requirement: 令牌刷新

系统 SHALL 提供 `POST /api/auth/refresh` 端点，接收有效 refresh_token 并签发新 access_token。过期、伪造或类型不匹配的令牌 MUST 返回 401。

#### Scenario: 刷新成功

- **WHEN** 持未过期 refresh_token 调用 refresh
- **THEN** 返回 200 与新 access_token，新令牌可正常访问受保护端点

#### Scenario: 过期刷新令牌

- **WHEN** 持已过期的 refresh_token 调用 refresh
- **THEN** 返回 401

#### Scenario: 令牌类型不匹配

- **WHEN** 持 access_token（type=access）调用 refresh
- **THEN** 返回 401（端点只接受 type=refresh 的令牌）

### Requirement: 家长独立登录通道

系统 SHALL 提供 `POST /api/parent/login` 家长独立登录端点，凭证为手机号（phone）与密码（password），不走教师/学生的 username 登录通道。校验通过时 MUST 签发 `role = "parent"` 且不含 `school_id` 的 access_token（24h）与 refresh_token（7d）。凭证错误 MUST 返回 401。

#### Scenario: 家长凭手机号登录

- **WHEN** 家长以正确手机号与密码调用 `/api/parent/login`
- **THEN** 返回 200，token 中 role=parent 且无 school_id

#### Scenario: 家长凭证错误

- **WHEN** 以错误密码调用 `/api/parent/login`
- **THEN** 返回 401

### Requirement: 认证中间件白名单

系统 SHALL 对所有 `/api/*` 请求执行 JWT 校验，仅以下路径跳过认证：`/api/auth/`（前缀）、`/api/parent/login`（**精确路径匹配，非前缀**）、`/docs`、`/redoc`、`/openapi.json`、`/health`。`/api/parent/` 前缀 MUST NOT 整体进入白名单——除精确的 login 路径外，其余家长端路径仍需携带有效 parent 令牌（绑定关系另行校验）。其余教学业务路径（`/api/agent/`、`/api/ocr/`、`/api/classes/`、`/api/parser/`、`/api/knowledge/`、`/api/exam-bank/`、`/api/question/` 等）MUST NOT 进入白名单。缺失或无效令牌 MUST 返回 HTTP 401。

#### Scenario: 白名单放行

- **WHEN** 无令牌请求 `/health`
- **THEN** 返回 200（不经过 JWT 校验）

#### Scenario: 家长登录端点无令牌放行

- **WHEN** 无令牌 POST 请求精确路径 `/api/parent/login`
- **THEN** 不返回 401（请求进入登录端点逻辑，由凭证校验决定 200/401）

#### Scenario: 家长业务路径无令牌拒绝

- **WHEN** 无令牌请求 `/api/parent/children`
- **THEN** 返回 401（精确 login 路径之外的 /api/parent/ 路径不豁免）

#### Scenario: 受保护路径无令牌

- **WHEN** 无令牌请求 `/api/classes`
- **THEN** 返回 401

#### Scenario: 过期令牌

- **WHEN** 持已过期 access_token 请求任一受保护路径
- **THEN** 返回 401

#### Scenario: 篡改令牌

- **WHEN** 持签名被篡改的令牌请求受保护路径
- **THEN** 返回 401

### Requirement: 无状态令牌语义

系统 SHALL 采用无状态 JWT：令牌在过期前始终有效，不维护服务端黑名单。登出 MUST 仅由客户端清除本地令牌完成，服务端不提供吊销端点。

#### Scenario: 登出不依赖服务端

- **WHEN** 客户端清除本地令牌后不再携带
- **THEN** 后续请求按"缺失令牌"返回 401，期间不存在任何服务端登出调用
