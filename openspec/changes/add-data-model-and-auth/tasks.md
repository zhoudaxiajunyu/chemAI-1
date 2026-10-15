# Tasks

## 1. 依赖与测试基建

- [x] 1.1 安装 `python-jose[cryptography]` 与 `passlib[bcrypt]` 到 venv，追加到根 requirements.txt，验证 `venv\Scripts\python.exe -c "import jose, passlib; print('OK')"` 输出 OK
- [x] 1.2 创建完整后端包骨架：`backend/__init__.py`、`backend/app/__init__.py`、`backend/app/models/__init__.py`、`backend/app/core/__init__.py`、`backend/app/api/__init__.py`、`backend/tests/__init__.py`（否则后续 `from backend.app.models...` import 链失败），以及 `backend/tests/conftest.py`：SQLite 内存引擎（`sqlite:///:memory:`，统一引擎工厂供应用与测试共用，保证 JSON 自动反序列化）+ `Base.metadata.create_all` + `db_session` fixture（事务回滚）；验证一个空测试 `pytest backend/tests/ -v` 可被发现并通过
- [x] 1.3 创建 `backend/app/models/base.py`（统一 `declarative_base()`）与 `backend/app/models/enums.py`（全部 str 枚举：ExamType/QuestionSource/AuditStatus/Difficulty/BarrierType/TeacherStatus/StudentStatus/TeacherRole/BindingStatus/NotificationType/WarningType/WarningLevel/UploadSessionStatus/OCRTaskStatus/ReviewTaskStatus），验证 `python -c "from backend.app.models.enums import *"` 无错

## 2. 核心组织与身份模型（8 个，Parent 因 Account 三选一外键前置）

- [x] 2.1 写 `tests/test_models_org.py` 先红：School→Grade→Class 组织链创建/外键拒绝孤儿/可回溯三场景，外加删除保护场景（删除仍有下级年级的学校 → 拒绝或外键置空，按实现选一并断言下级数据未被级联删除）；实现 `backend/app/models/organization.py`（School/Grade/Class），验证测试转绿
- [x] 2.2 追加测试：Teacher 默认 status=pending、role 英文 code 枚举约束（非法值在应用层赋枚举时 ValueError，裸 SQL 绕过时 DB CHECK 抛 IntegrityError，两层都断言）、status 枚举约束；实现 Teacher 模型（枚举列 `Enum(..., native_enum=False, create_constraint=True)`），验证转绿
- [x] 2.3 追加测试：Student 默认 status=approved、绑定码字段、障碍画像 JSON 读写为 dict；实现 Student 模型（含 `Column(JSON)`），验证转绿
- [x] 2.4 追加测试：Parent 基本信息（姓名/手机号/邮箱/密码）与唯一手机号；实现 Parent 模型（从原家校组前置——Account.parent_id 外键依赖它），验证转绿
- [x] 2.5 追加测试：Account 三选一约束全场景（关联教师成功/关联学生成功/关联家长成功/双关联拒绝/零关联拒绝）、用户名唯一约束；实现 Account 模型（三 nullable FK + `CheckConstraint` SQL 文本 `(teacher_id IS NOT NULL) + (student_id IS NOT NULL) + (parent_id IS NOT NULL) = 1`），验证转绿
- [x] 2.6 追加测试：TeacherClassSubject 任课关系（一师多班、班主任标注、teacher/class 外键）；实现 TeacherClassSubject 关联表，验证转绿

## 3. 考试与作答模型（3 个）

- [x] 3.1 写 `tests/test_models_teaching.py` 先红：ExamRecord 归属班级、exam_type 枚举约束（应用层 ValueError + 裸 SQL 绕过时 IntegrityError）、错题统计 JSON 往返（逐题错误数据/高错误率知识点排行/班级平均分结构，读出为 dict）；实现 ExamRecord，验证转绿
- [x] 3.2 追加测试：Question 枚举（source/audit_status/difficulty）双层约束、四维审核报告 JSON 往返、选项列表 JSON；实现 Question，验证转绿
- [x] 3.3 追加测试：StudentAnswer 三元关联（student+question+exam_record）、barrier_type 枚举、连续错误/正确计数器字段；实现 StudentAnswer，验证转绿

## 4. 诊断与学习模型（4 个）

- [x] 4.1 写 `tests/test_models_diagnosis.py` 先红：BarrierConfig 默认值（3/2/3/3/auto_sync=False）、teacher 外键；实现 BarrierConfig，验证转绿
- [x] 4.2 追加测试：KnowledgePoint 字段（名称/分类/PubChem 编号/关联题目数/动态错误率）；实现 KnowledgePoint，验证转绿
- [x] 4.3 追加测试：ReviewTask 级别 0-5、状态枚举（待复习/超期/已掌握）、复习历史 JSON、student+question 外键；实现 ReviewTask，验证转绿
- [x] 4.4 追加测试：WarningLog 四种类型枚举、三通知状态布尔标记、student 外键；实现 WarningLog，验证转绿

## 5. 家校绑定与通知（2 个，Parent 已在 2.4 前置）

- [x] 5.1 写 `tests/test_models_family.py` 先红：StudentParentBinding 绑定状态枚举（active/inactive）、亲属关系字段、student+parent 外键、凭 6 位绑定码建联场景；实现 StudentParentBinding，验证转绿
- [x] 5.2 追加测试：ParentNotification 类型枚举（学习报告/预警提醒/教师消息）、已读状态默认 False、发送时间、parent 外键；实现 ParentNotification，验证转绿

## 6. OCR 批改模型（3 个）

- [x] 6.1 写 `tests/test_models_ocr.py` 先红：UploadSession 状态机枚举（含"降级处理中"，DB CHECK 约束）、非法回退拒绝（应用层状态转移校验）；实现 UploadSession，验证转绿
- [x] 6.2 追加测试：OCRTask 状态枚举、OCR 原始结果与批改结果 JSON、session 外键；实现 OCRTask，验证转绿
- [x] 6.3 追加测试：StudentSubmission 关联 student+exam_record、原始/批改图片字段、答案列表 JSON、总分与批改完成时间；实现 StudentSubmission，验证转绿

## 7. 题库模型（4 个）

- [x] 7.1 写 `tests/test_models_bank.py` 先红：QuestionSet 字段（名称/来源地区/年份/来源说明）；实现 QuestionSet，验证转绿
- [x] 7.2 追加测试：QuestionSetItem 多对多关联、一题入多集各自排序值；实现 QuestionSetItem，验证转绿
- [x] 7.3 追加测试：HistoricalExam 与 HistoricalQuestion 字段完整（来源/年份/题号/知识点标签/难度/区分度/正文/答案/解析）；实现两模型，验证转绿

## 8. JWT 与安全模块

- [x] 8.1 写 `tests/test_security.py` 先红：bcrypt 哈希与校验（正确通过/错误拒绝）；实现 `backend/app/core/security.py`（passlib CryptContext），验证转绿
- [x] 8.2 追加测试四场景：JWT 编码解码往返、签名篡改拒绝、过期令牌拒绝、payload 必备声明（user_id/role/school_id/type/iat/exp，家长无 school_id）；实现 `backend/app/core/jwt.py`（python-jose HS256，access 24h / refresh 7d，密钥读 `JWT_SECRET_KEY`），验证转绿

## 9. RBAC 权限矩阵与中间件

- [x] 9.1 写 `tests/test_permissions.py`：参数化断言 ROLE_PERMISSIONS 全矩阵（6 角色 × 17 资源 × 各操作，从矩阵自动生成用例，含"未声明即拒绝"）；实现 `backend/app/core/permissions.py`（ROLE_PERMISSIONS 常量按 specs/authorization 逐行录入 + PermissionChecker + require_permission），验证转绿
- [x] 9.2 追加测试：PermissionChecker 通过时返回含 user_id/role/school_id 的上下文、越权返回 403 语义；实现校验器上下文返回，验证转绿
- [x] 9.3 写 `tests/test_middleware.py` 五场景：白名单放行（/health 无 token 200）、`/api/parent/login` 精确路径无 token 不被中间件拦截（非 401，进入端点逻辑）、`/api/parent/children` 等家长业务路径无 token 401、受保护路径无 token/过期 token/篡改 token 401；实现 `backend/app/core/middleware.py`（JWT 认证中间件 + 前缀/精确两类白名单匹配），验证转绿

## 10. 认证端点（login / refresh / parent login）

- [x] 10.1 写 `tests/test_auth_api.py` 先红：正确登录 200 含 token/refresh_token/user_id/name/role、错误密码 401、pending 教师 401；实现 `POST /api/auth/login`（bcrypt 校验 + 双 token 签发，登录失败输出 warning 日志且日志不含密码/完整令牌），以 FastAPI TestClient 验证转绿
- [x] 10.2 追加测试：有效 refresh_token 换新 access_token 200、过期/伪造 refresh_token 401、用 access_token（type=access）调 refresh 返回 401；实现 `POST /api/auth/refresh`（强制校验 type=refresh），验证转绿
- [x] 10.3 追加测试：家长以手机号+密码登录 `/api/parent/login` 成功，令牌 role=parent 且无 school_id；错误密码 401；实现家长独立登录通道（复用 JWT 签发，凭证字段 phone+password，非 username），验证转绿
- [x] 10.4 创建 `backend/app/main.py`：挂载 auth 与 parent 登录路由 + 注册认证中间件，验证 `/docs` 可访问、无 token 访问受保护路径 401、登录后凭 token 访问受保护路径 200（TestClient 集成断言）

## 11. Alembic 迁移

- [x] 11.1 初始化 `backend/alembic/`（`alembic init` 后改 env.py：`target_metadata = Base.metadata`，数据库 URL 读环境变量），验证 `alembic current` 无错
- [x] 11.2 autogenerate 生成首个迁移并人工审查（删不期望的 default/nullable 变更；确认全部枚举 CHECK 与 Account 三选一 CheckConstraint 落库；对高频 FK 列 student_id/class_id/exam_record_id/teacher_id/parent_id 显式 `index=True`；确认索引命名），验证全新 SQLite 文件上 `alembic upgrade head` 建出 24 张表（`sqlite_master` 计数断言；33 号"26 张表"中另 2 张为 Agent 检查点/长期记忆，属文档 53 不建）
- [x] 11.3 追加迁移测试：upgrade head 后 `alembic downgrade base` 再 upgrade 往返无错；裸 SQL 向枚举列插非法值被 CHECK 拒绝；验证通过

## 12. 集成验收

- [x] 12.1 全量 `pytest backend/tests/ -v` 绿色，统计覆盖 43 号完成标准 1-5（模型/JWT 四场景/auth 端点四场景/矩阵逐行/中间件场景）
- [x] 12.2 `alembic upgrade head` 在干净库文件复跑无错，确认 24 表结构、枚举 CHECK、索引齐全

## Workflow follow-up

- [ ] /plan-eng-review 架构审查（43 号 Step 4）——已执行并回写 P0/P1 修补
- [ ] 配置 git hooks：pre-commit 跑 `pytest tests/ --tb=short -x`，commit-msg 校验 Conventional Commits（43 号 Step 4 一次性配置）
- [ ] 创建 scripts/run_evals.py 轻量运行器 v1（43 号 Step 5.5）
- [ ] /code-review 代码审查（43 号 Step 6）
- [ ] /opsx:archive 归档（43 号 Step 7）
- [ ] --no-ff 合并回 main + 打 v0.2.0 标签 + push no-mistakes main --tags（43 号 Step 8）
- [ ] 新约定沉淀到 CLAUDE.md；如有架构级决策补 ADR 到 docs/adr/
- [ ] 家长绑定端点上线阶段必须补：绑定尝试次数限制、绑定码轮换（design.md 风险表 F10）
