# Proposal

## Why

chemAI-1 目前处于 bootstrap 阶段，仓库中没有任何后端代码。按照 43 号实施文档（数据模型与认证体系），本阶段需要搭建整个系统的地基：24 个 SQLAlchemy 数据模型（本阶段 24 张表，Agent 2 表随文档 53 另建）、JWT 认证体系、RBAC 权限矩阵和 Alembic 迁移。这是后续所有业务阶段（出题工作台 44、题库与考试 45、障碍诊断 46、自适应练习 47、学情面板 48、OCR 批改 49）的前置依赖，没有数据模型和认证授权骨架，任何业务端点都无法落地。

## What Changes

- 新增 24 个 SQLAlchemy 模型（本阶段映射 24 张表；33 号"26 张表"中另 2 张为 Agent 对话检查点与长期记忆，随文档 53 由 LangGraph 提供，不在本阶段），按依赖链分 6 组：核心组织（School/Grade/Class/Teacher/TeacherClassSubject/Student/Account）、考试与作答（ExamRecord/Question/StudentAnswer）、诊断与学习（BarrierConfig/KnowledgePoint/ReviewTask/WarningLog）、家校互通（Parent/StudentParentBinding/ParentNotification）、OCR 批改（UploadSession/OCRTask/StudentSubmission）、题库（QuestionSet/QuestionSetItem/HistoricalExam/HistoricalQuestion）
- 新增 JWT 认证体系：python-jose HS256 签发/校验 access_token（24h）与 refresh_token（7d），实现 `POST /api/auth/login` 与 `POST /api/auth/refresh` 两个端点
- 新增 RBAC 权限矩阵：按 22 号文档 §2.1 实现 ROLE_PERMISSIONS（6 角色 × 17 资源 × 操作级），含 PermissionChecker 与 `require_permission` 装饰器
- 新增 HTTP 认证中间件：白名单（`/api/auth/`、`/docs`、`/redoc`、`/openapi.json`、`/health`）跳过校验，其余 `/api/*` 一律校验 JWT
- 新增 Alembic 迁移：初始化迁移覆盖本阶段全部 24 张表（含枚举 CHECK 与 JSON 字段）
- 新增测试基建：`tests/conftest.py`（SQLite 内存引擎 + create_all + session fixture）与全套 TDD 测试

明确不在本阶段 scope（后续阶段处理）：

- 业务端点（exam/question/ocr/diagnosis 等 250 个端点）——仅实现 auth 两个端点
- Agent 对话检查点与长期记忆 2 张表——由文档 53 的 LangGraph checkpointer 提供
- 行级数据范围过滤（admin 全校/教务同校/teacher 任教班级）——本阶段只做角色×资源×操作校验
- Token 黑名单/吊销——按 22 号 §9.3 接受无状态 JWT 权衡

## Capabilities

### New Capabilities

- `data-model`: 系统 24 实体 26 表的持久化结构定义，含组织链、教学链、家校链、身份链四条核心数据链的表结构、外键关系、枚举约束与 JSON 字段 schema
- `authentication`: 统一账户体系的登录认证行为，含 JWT 签发/刷新/校验、login/refresh 端点契约、认证中间件的白名单与 401 语义
- `authorization`: 基于角色的访问控制行为，含 ROLE_PERMISSIONS 矩阵语义、PermissionChecker 资源级校验、require_permission 装饰器的 403 语义与角色-数据范围约定

### Modified Capabilities

（无——项目主 specs 目前为空，本次全部为新建）

## Impact

- **新代码**：`backend/app/models/`（24 个模型文件）、`backend/app/core/`（security/jwt/permissions/middleware）、`backend/app/api/auth.py`、`backend/alembic/`（env.py + 首个迁移版本）、`backend/tests/`（conftest + 模型/认证/权限/中间件测试）
- **依赖**：新增 `python-jose[cryptography]`（JWT）、`passlib[bcrypt]`（密码哈希）；沿用已装的 sqlalchemy 2.0.54、alembic 1.20.0、fastapi 0.143.0、pytest 9.1.1、httpx 0.28.1
- **数据库**：SQLite（开发），通过 Alembic 初始化迁移建 26 张表；JSON 字段在 SQLite 以 TEXT 存储（SQLAlchemy JSON type）
- **设计决策**（详见 design.md）：
  1. JWT 库采用 python-jose（43 号文档口径），而非 22 号文档的"纯 Python 手写"——以更新的实施文档为准
  2. 教师角色字段在 DB 存英文 code（`admin`/`academic_admin`/`subject_leader`/`teacher`），中文名（系统管理员/教务管理员/学科组长/普通教师）仅作显示层映射——偏离 22 号字面（中文枚举），换取工程健壮性
  3. Account 与 Teacher/Student/Parent 的 1:1 三选一关联用 SQL CHECK + 应用层双保险
- **Git**：在 `phase-2/data-model` 分支实现，完成后 `--no-ff` 合并回 main 并打 `v0.2.0` 标签
