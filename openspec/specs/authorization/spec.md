# authorization Specification

## Purpose

定义基于角色的访问控制（RBAC）行为契约：ROLE_PERMISSIONS 矩阵的完整语义、PermissionChecker 的资源级校验行为、require_permission 装饰器的 403 语义，以及六类角色对 17 类资源的操作级权限边界。

## Requirements

### Requirement: 权限矩阵权威定义

系统 SHALL 以单一 ROLE_PERMISSIONS 矩阵作为全部后端权限校验的权威数据源。矩阵键为角色（admin / academic_admin / subject_leader / teacher / student / parent），覆盖资源：school、grade、class、teacher、student、analysis、exam、question、ocr、grading、diagnosis、practice、report、panel、parent、notification、warning。每个单元格声明该角色对资源的操作集合（create/read/update/delete/bind/send/write 之一或多个）。

#### Scenario: 矩阵完备可查询

- **WHEN** 对任意（角色, 资源, 操作）三元组查询矩阵
- **THEN** 返回明确的允许/拒绝结论，未声明的组合一律视为拒绝

### Requirement: 管理员全权

角色 `admin` SHALL 对全部 17 类资源拥有全部操作权限。

#### Scenario: admin 无障碍

- **WHEN** admin 对任意资源发起任意操作校验
- **THEN** 校验通过

### Requirement: 教务管理员权限边界

角色 `academic_admin` SHALL 拥有：school 仅 read；grade create/read/update；class 完整 CRUD；teacher read/update；student 完整 CRUD；analysis 仅 read。其余资源与操作 MUST 拒绝。

#### Scenario: 教务管理员建班

- **WHEN** academic_admin 校验 class:create
- **THEN** 通过

#### Scenario: 教务管理员禁删校

- **WHEN** academic_admin 校验 school:delete
- **THEN** 拒绝

### Requirement: 学科组长只读

角色 `subject_leader` SHALL 仅拥有 read 权限，任何写操作 MUST 拒绝。

#### Scenario: 学科组长只读

- **WHEN** subject_leader 校验 exam:read 与 exam:create
- **THEN** read 通过、create 拒绝

### Requirement: 教师教学写权限

角色 `teacher` SHALL 拥有：school/grade/class/teacher/student 仅 read；exam、question、ocr、grading 的 create/read；analysis read；diagnosis read/update；practice read/create；report read/send；panel read/create；notification read/write；warning read/write。

#### Scenario: 教师可出题不可管校

- **WHEN** teacher 校验 question:create 与 school:update
- **THEN** 前者通过、后者拒绝

### Requirement: 学生仅自身数据

角色 `student` SHALL 仅拥有：diagnosis read（自身）、practice read/create（本人/提交作答）、report read（自身）、parent read 与 bind（生成绑定码）、notification read/write（自身，标记已读）、warning read（自身）、grade read。

#### Scenario: 学生提交作答

- **WHEN** student 校验 practice:create
- **THEN** 通过

#### Scenario: 学生禁看题库

- **WHEN** student 校验 question:read
- **THEN** 拒绝

### Requirement: 家长最小可见

角色 `parent` SHALL 仅拥有：student read（子女）、analysis read（子女）、report read（子女）、parent read 与 bind（绑定/解绑）、notification read/write（子女，标记已读）、warning read（子女）。家长 MUST NOT 访问：其他学生数据、班级统计信息、排名信息、教师内部备注、学校整体学情分析。

#### Scenario: 家长读子女报告

- **WHEN** parent 校验 report:read
- **THEN** 通过（且仅对其绑定子女数据生效）

#### Scenario: 家长禁看面板

- **WHEN** parent 校验 panel:read
- **THEN** 拒绝

### Requirement: 资源级权限检查器

系统 SHALL 提供资源级权限检查能力：从有效 JWT 提取角色，在矩阵中判定其对指定资源与操作的权限；通过后 MUST 返回含 user_id、role、school_id 的用户上下文供业务层使用；失败 MUST 以 HTTP 403 拒绝。

#### Scenario: 校验通过返上下文

- **WHEN** teacher 持有效令牌访问需 exam:create 的端点
- **THEN** 校验通过且业务层可获得其 user_id 与 school_id

#### Scenario: 越权 403

- **WHEN** student 持有效令牌访问需 exam:create 的端点
- **THEN** 返回 403（而非 401——身份合法但权限不足）

### Requirement: 端点权限声明强制

所有教学业务端点 MUST 声明权限装饰器做端点级角色校验，不允许仅依赖 JWT 中间件放行。未声明权限的教学业务端点视为安全缺陷。

#### Scenario: 装饰器拦截越权

- **WHEN** 端点声明 `require_permission("student", "read")`，teacher 角色令牌访问
- **THEN** 返回 403

#### Scenario: 装饰器放行合规

- **WHEN** 端点声明 `require_permission("student", "read")`，admin 或 academic_admin 令牌访问
- **THEN** 校验通过进入业务逻辑

### Requirement: 亲子绑定前置校验

家长端数据查询端点（`/api/parent/child/{student_id}/*`）SHALL 在处理前验证该家长与目标学生存在 active 绑定关系；无绑定或绑定已解除 MUST 返回 403。

#### Scenario: 无绑定拒绝

- **WHEN** 家长 P 请求未绑定学生的数据
- **THEN** 返回 403

#### Scenario: 有绑定放行

- **WHEN** 家长 P 请求已绑定子女的数据
- **THEN** 校验通过
