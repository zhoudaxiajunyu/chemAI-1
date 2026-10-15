# Design

## Context

chemAI-1 仓库目前无任何后端代码（bootstrap 完成于文档 42）。本变更按 43 号实施文档在 `phase-2/data-model` 分支落地数据与认证地基。动机与 scope 见 proposal.md；行为契约见 specs/ 下三份 spec delta。

关键约束：

- Python 3.13.14（本机唯一版本），SQLite 开发库，FastAPI 0.143 + SQLAlchemy 2.0.54 + Alembic 1.20.0 已装
- 设计文档口径冲突已裁决：JWT 用 python-jose（43 号）；角色字段 DB 存英文 code（偏离 22 号中文字面）
- 目录布局采用 monorepo：后端全部收在 `backend/`（`backend/app/`、`backend/alembic/`、`backend/tests/`）

## Goals / Non-Goals

**Goals**

- 24 个 SQLAlchemy 模型一次建全，外键/枚举/CHECK 约束完整，`alembic upgrade head` 可建 26 张表（含 2 张关联表）
- python-jose HS256 JWT：login/refresh 两端点可用，中间件保护 `/api/*`
- ROLE_PERMISSIONS 矩阵 + PermissionChecker + require_permission 装饰器三层授权
- 全套 TDD：模型 CRUD、认证四场景（编码/签名/过期/篡改）、矩阵逐行断言、中间件四场景

**Non-Goals**

- 业务端点（exam/question/ocr 等约 250 个）——仅 auth 两端点
- 行级数据范围过滤（admin 全校/教务同校/teacher 任教班级）——后续业务阶段
- Token 黑名单、Alembic 增量迁移策略、生产数据库（PostgreSQL）适配

## Decisions

### D1: JWT 库选 python-jose 而非纯 Python 手写

- **选择**：`python-jose[cryptography]` 签发/校验 HS256 JWT
- **理由**：22 号文档写"纯 Python 实现不依赖外部库"，43 号实施文档明确写 python-jose。手写 JWT 的 base64url/签名/过期校验是经典安全漏洞温床；python-jose 成熟且 API 稳定
- **替代**：PyJWT（同等可用，jose 与 FastAPI 生态文档更贴合）；手写（拒绝，安全理由）

### D2: 角色字段存英文 code + 显示层映射

- **选择**：Teacher.role 与 Account.role 存 `admin`/`academic_admin`/`subject_leader`/`teacher`；`ROLE_DISPLAY_NAMES` 常量做中文映射
- **理由**：22 号字面用中文枚举（`教务管理员`/`学科组长`），但中文字符串作为代码标识符易引入全角/半角、编码、大小写类 bug；JWT payload 与矩阵键用英文更稳健
- **代价**：偏离 22 号字面，需在 CONTEXT.md 与代码注释中记录映射关系

### D3: Account 三选一关联用 SQL CHECK + 应用层双保险

- **选择**：Account 表三个 nullable 外键（teacher_id/student_id/parent_id）+ `CHECK ((teacher_id IS NOT NULL)::int + (student_id IS NOT NULL)::int + (parent_id IS NOT NULL)::int = 1)`；应用层 Pydantic validator 前置校验
- **理由**：SQLite 支持 CHECK 约束（含布尔转 int 写法）；单靠应用层校验可被裸 SQL 绕过
- **替代**：单表继承/Joined Table Inheritance（过度设计）；泛型关联（丧失外键完整性）

### D4: 统一声明式 Base + 单 metadata

- **选择**：所有模型继承同一 `Base = declarative_base()`，集中在 `backend/app/models/`，Alembic `target_metadata = Base.metadata`
- **理由**：autogenerate 需要单一 metadata 源；分组文件（organization/teaching/diagnosis/family/ocr/bank/identity）仅作代码组织，不影响表结构

### D5: 枚举用 Python Enum + SQLAlchemy Enum type（DB CHECK 双保险）

- **选择**：5 个业务枚举（ExamType/QuestionSource/AuditStatus/Difficulty/BarrierType）+ 各状态枚举定义为 Python `str, Enum`，列类型用 `sqlalchemy.Enum(..., native_enum=False, create_constraint=True)`。关键陷阱：SQLAlchemy 1.4+ 中 `native_enum=False` 默认 `create_constraint=False`，只落为纯 VARCHAR **不生成 CHECK**，必须显式开 `create_constraint=True` 才会在 SQLite 建 CHECK 约束
- **理由**：`str` 混入让枚举值可直接 JSON 序列化；DB CHECK（裸 SQL 写入非法值也拒绝）+ 应用层 ValueError（赋非法枚举值即抛）双保险，与 D3 Account CHECK 哲学一致；枚举非法值测试断言 DB 层 `IntegrityError`，并辅以应用层赋值 ValueError 断言

### D6: JSON 字段用 SQLAlchemy JSON type

- **选择**：障碍画像、错题统计、复习历史、审核报告四类字段用 `Column(JSON)`（学习计划 JSON 因无归属模型本阶段不做），SQLite 落为 TEXT 自动序列化/反序列化
- **风险**：SQLite 不原生支持 JSON 查询操作符——本阶段无需 JSON 内查询，可接受

### D7: 中间件用 FastAPI 依赖注入而非纯 ASGI 中间件

- **选择**：白名单判定 + JWT 校验实现为 FastAPI middleware（`BaseHTTPMiddleware`），权限校验实现为依赖（`Depends(PermissionChecker(resource, action))`）与装饰器（`require_permission`）
- **理由**：43 号完成标准要求"白名单、有效 token、过期 token、权限拒绝"四场景可测；middleware 处理 401、依赖/装饰器处理 403，职责分离清晰
- **白名单匹配规则**：`/api/auth/` 用前缀匹配；`/api/parent/login` 用精确匹配（否则前缀放行会把整个家长端业务面暴露）；其余按精确路径。22 号文档"家长端不在白名单"与"家长走 /api/parent/login 登录"存在死锁，本设计以"精确放行登录端点"解决

### D8: 测试用 SQLite 内存引擎 + 每测试独立建表

- **选择**：`conftest.py` 提供 `db_session` fixture：`create_engine("sqlite:///:memory:")` + `Base.metadata.create_all` + 事务回滚
- **理由**：隔离性最强、速度最快；避免测试间污染。JSON/枚举行为在内存库与文件库一致

### D9: Alembic 首个迁移手写而非 autogenerate 直出

- **选择**：先跑 autogenerate 生成初稿，人工审查修订后入库
- **理由**：43 号错误速查表预警 autogenerate 会产生不期望的 default/nullable 变更；CHECK 约束与索引命名需人工确认

## Risks / Trade-offs

- [SQLite CHECK 约束写法差异（布尔运算）] → D3 的 `::int` 转换写法在 SQLite 需改写为 `(teacher_id IS NOT NULL) + (student_id IS NOT NULL) + (parent_id IS NOT NULL) = 1`；Alembic 迁移时用 `sa.CheckConstraint` 显式 SQL 文本，并用迁移测试验证
- [python-jose 与 Python 3.13 兼容性] → 安装后立即跑编码/解码/过期/篡改四场景测试；若失败降级 PyJWT（API 几乎同构，改动集中在 security 模块）
- [JSON 字段在 SQLite 读出为字符串] → 引擎创建时显式配置，测试断言读出为 dict/list；conftest 引擎与应用引擎共用同一配置函数
- [矩阵逐行断言量大（6 角色 × 17 资源）] → 参数化测试（`@pytest.mark.parametrize`）从 ROLE_PERMISSIONS 直接生成用例，矩阵即测试数据源，杜绝"测试与实现不一致"
- [无状态 JWT 无法即时吊销] → 接受（22 号 §9.3 已权衡）；文档化应急预案：更换 SECRET_KEY 重启
- [6 位家长绑定码可暴力枚举（约 10^6 空间）] → 本阶段仅落数据模型、绑定端点未上线，风险暂不暴露；家长绑定端点落地的阶段必须加尝试次数限制与绑定码轮换
- [高频外键列无索引导致后续业务阶段查询退化为全表扫描] → 首个 Alembic 迁移人工审查时对 student_id/class_id/exam_record_id/teacher_id/parent_id 等 FK 列显式 `index=True`
- [登录失败与 JWT 校验失败无审计痕迹] → login/refresh 与中间件的 401 路径输出 warning 级日志（含原因，禁止记录密码或完整令牌），成本极低且满足安全可观测性基线

## Migration Plan

1. 新增依赖：`pip install "python-jose[cryptography]" "passlib[bcrypt]"`，更新根 `requirements.txt`
2. 代码落地顺序按依赖链（见 tasks.md）：测试基建 → 核心组织 7 模型 → 考试 3 → 诊断 4 → 家长 3 → OCR 3 → 题库 4 → JWT/安全 → 矩阵/中间件 → auth 端点 → Alembic
3. 迁移执行：`alembic upgrade head` 在全新 SQLite 文件建 26 表；回滚策略 = 删除数据库文件 + 重建（开发期无数据）
4. 环境变量：`JWT_SECRET_KEY` 入 `.env`（`.gitignore` 已排除），测试用固定测试密钥注入

## Open Questions

- 生产环境 PostgreSQL 迁移时 `native_enum` 与 JSON 字段的方言差异——推迟到部署阶段（本阶段 SQLite 优先）
- refresh token 是否落库以支持"踢人下线"——22 号明确无状态，若未来需求变更再议
