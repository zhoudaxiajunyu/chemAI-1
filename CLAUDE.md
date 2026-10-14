# CLAUDE.md — ChemAI 智辅化学

本文件是 AI 编程助手的项目行为准则。**本项目使用 Trae（非 Claude Code）开发**，所有命令与技能均按 Trae 环境适配。

---

## 一、通用行为准则

> 以下四条是跨项目通用的 LLM 编码准则，偏保守、防跑偏。琐碎任务可酌情从简。

### 1. Think Before Coding

**不要假设。不要隐藏困惑。主动暴露取舍。**

实现前：
- 显式陈述你的假设；不确定就问。
- 存在多种解读时列出，不要默默选一个。
- 有更简单的方案就说出来；必要时反对。
- 不清楚就停下，指出困惑点，发问。

### 2. Simplicity First

**只写解决问题的最小代码，不做投机性设计。**

- 不做没被要求的功能。
- 不为一次性代码造抽象。
- 不写没要求的"灵活性""可配置性"。
- 不为不可能发生的场景写错误处理。
- 写了 200 行、其实 50 行能搞定 → 重写。

自问："资深工程师会觉得这过度设计了吗？" 会 → 简化。

### 3. Surgical Changes

**只改必须改的，只清理自己造成的混乱。**

改动既有代码时：
- 不"顺手优化"相邻代码、注释、格式。
- 不重构没坏的东西。
- 跟随既有风格，即使你有别的偏好。
- 发现无关死代码 → 提一句，别删。

你的改动产生孤儿时：
- 删除**你的改动**导致失效的 import/变量/函数。
- 不删既有的死代码（除非被要求）。

检验标准：每一行改动都能直接追溯到用户的要求。

### 4. Goal-Driven Execution

**先定义成功标准，循环到验证通过。**

把任务转成可验证的目标：
- "加校验" → "为非法输入写测试，然后让它们通过"。
- "修 bug" → "写一个复现它的测试，然后让它通过"。
- "重构 X" → "确保重构前后测试都通过"。

多步任务先给简短计划：
```
1. [步骤] → verify: [检查]
2. [步骤] → verify: [检查]
3. [步骤] → verify: [检查]
```

强成功标准能让你独立循环；弱标准（"让它跑起来"）会不断需要澄清。

---

## 二、项目概述

**ChemAI 智辅化学**：面向高中化学的 AI 教学辅助平台，教师端 + 学生端 + 家长端三端。

核心能力：
- **错题诊断**：从"知道谁错了"进化到"知道为什么错"——三维障碍分类（概念理解型 / 审题障碍型 / 表述障碍型）。
- **AI 出题与题库**：AI 生成 / 手动录入 / OCR 导入三条出题路径，四维化学方程式安全审核。
- **答题卡 OCR 批改**：三引擎降级链（PP-OCRv6 → 百度 OCR → VLM），10 步批改管线。
- **Agent 对话系统**：单 Agent ReAct + 42 领域工具 + 4 Persona + 四层 Guard 护栏。
- **自适应练习**：基于 ZPD 窗口的个性化练习推荐；艾宾浩斯间隔复习。

领域术语以 `CONTEXT.md` 为权威口径；前端视觉以 `DESIGN.md` 为权威口径；架构决策记录在 `docs/adr/`。

---

## 三、技术栈

### 后端
| 项 | 选择 |
|------|------|
| Web 框架 | FastAPI 0.109.2 + Uvicorn 0.27.1（原生 async、SSE 流式） |
| ORM + 迁移 | SQLAlchemy 2.0.25 + Alembic 1.13.1（24 实体 / 26 表 / 5 枚举） |
| 数据库 | SQLite + WAL（开发）；MySQL 可选（生产，改连接串即可） |
| 向量库 | ChromaDB 0.4.22（嵌入式）+ DashScope text-embedding-v3（1024 维） |
| Agent 框架 | LangGraph `create_react_agent`（单 Agent，v2 主版本；v1 多 Agent 保留回退） |
| 检查点/记忆 | AsyncSqliteStore + AsyncSqliteSaver |
| 调度 | APScheduler 3.10.4（每日练习 08 UTC / 预警 00 UTC / OCR 轮询 5s） |
| 化学配平 | 自定义系数平衡算法 + RDKit 2024.3.1（确定性，非 LLM） |
| 浏览器工具 | Playwright >=1.40 |
| 测试 | Pytest 8.0.0（单元 / 集成 / 评测） |
| 容器 | Docker + Compose（python:3.11-slim） |
| 桌面打包 | pywebview + PyInstaller 6.x（三端 .exe） |

### 前端（教师端）
React 19 + Vite 8 + Tailwind CSS 4 + antd 6 + ECharts 6 + KaTeX 0.17（+ mhchem）+ Marked 18。
学生端 / 家长端为移动优先轻量页面，不引入框架构建步骤。

### LLM Provider（三级 Fallback）
`qwen-turbo`（主，延迟最低/可用率最高/提供 Embedding）→ `deepseek-chat`（备，化学满分/成本最低）→ `MiMo-V2.5`（兜底，唯一支持视觉 + 联网）。图片 / OCR / 文档解析走视觉模型（qwen-vl-ocr / glm-4v）。每级 3 次重试 + 指数退避。

### OCR 三引擎降级链
答题卡图片：PP-OCRv6（默认）→ 百度 OCR → VLM；PDF：MinerU → 百度 OCR → VLM；混合文档：MinerU + 百度 OCR 并行合并 → VLM。统一配置项 `OCR_SHEET_PROVIDER`（默认 `paddle`）。

---

## 四、开发工具链（Trae 适配）

九层工具链，原方案基于 Claude Code / Gstack，**本项目按 Trae 环境映射**：

| 层 | 原方案 | Trae 环境落地 |
|----|--------|--------------|
| 思考层 | `/office-hours` `/plan-ceo-review` `/plan-eng-review` | 已装技能：`/plan-ceo-review`、`/plan-eng-review` |
| 对齐层 | `/grill-with-docs` → CONTEXT.md + ADR | 已装技能：`/grilling`；产出物为本项目 `CONTEXT.md` + `docs/adr/` |
| 规格层 | `/opsx:propose` → `/opsx:apply` → `/opsx:archive` | OpenSpec v1.14.1：`/opsx-propose` → `/opsx-apply-change` → `/opsx-archive-change`（另有 `/opsx-explore`、`/opsx-update-change`、`/opsx-sync-specs`） |
| 实现层 | 写测试(RED) → 生成(GREEN) → 重构 | 已装技能：`/tdd` |
| 质量层 | L1 单元 → L2 集成 → L3 Golden → 基线对比 | 自建 `scripts/run_evals.py`（后端）+ GitHub Actions CI |
| 流程层 | `/review` `/code-review` `/cso` `/qa` `/ship` `/retro` | 已装技能：`/code-review`、`/gstack-review`、`/gstack-qa`、`/gstack-qa-only`、`/gstack-land-and-deploy`、`/retro`；排障用 `/diagnosing-bugs` |
| 门禁层 | `/no-mistakes` + git hooks + CI | **no-mistakes 未安装** → 改用 git hooks（pre-commit / commit-msg）+ GitHub Actions CI（文档 52 起生效） |
| 骨架层 | branch / commit / tag / merge / revert / push | Git（**仓库尚未 `git init`**，文档 42 Step 9 创建远程仓库） |
| 原生层 | Plan 模式 / Checkpoint / Hooks / Subagents | Trae 原生：Plan 模式、Checkpoint、Hooks、Subagents |

**何时用什么**：

| 场景 | 用什么 |
|------|--------|
| 设计文档已明确定义功能 | `/opsx-propose` → `/opsx-apply-change`（跳过思考层） |
| 需求边界模糊需对齐 | `/grilling` → 更新 `CONTEXT.md` + ADR |
| 架构级决策（数据模型 / 诊断引擎 / Agent 架构） | `/plan-eng-review` |
| 每个模型/组件完成 | `git commit`（原子化，不攒批） |
| 代码审查 | `/code-review`（双轴）或 `/gstack-review` |
| 阶段收尾 | `/code-review` → `merge --no-ff` → `git tag v0.N.0` |
| 前端验收 | `/gstack-qa <URL>`（浏览器）或 `/gstack-qa-only`（只报告不修） |
| 发布 | `/gstack-land-and-deploy` → CHANGELOG → `git tag v1.0.0` |
| 复盘 | `/retro` |

> 注：OpenSpec 在 PowerShell 下因执行策略禁用 `.ps1`，需用 `openspec.cmd` / `npm.cmd` 调用。

---

## 五、开发流程：七阶段

| 阶段 | 文档 | 内容 | 版本 |
|:--:|:--:|------|------|
| 一 | 42 | 环境搭建（工具链安装、项目骨架） | v0.1.0 |
| 二 | 43 | 数据模型 + 认证体系（24 模型、JWT、RBAC 权限矩阵） | v0.2.0 |
| 三 | 44-46 | 核心功能（出题工作台、题库管理、障碍诊断引擎） | v0.3.0 |
| 四 | 47-51 | 业务功能（自适应练习、学情面板、OCR、学生端、家长端） | v0.4.0 |
| 五 | 52 | Evals 评测体系（100 条 Golden、三层金字塔、基线、CI） | v0.5.0 |
| 六 | 53-57 | Agent 系统（Agent 架构、42 工具、Persona、Guard、MCP） | v0.6.0 |
| 七 | 58-59 | 验收与发布（全链路验收、灰度发布、复盘） | v1.0.0-rc.1 → v1.0.0 |

**依赖关系**：42 → 43 → （44→45→46 串行）；（47/48 依赖 46；49 与 46 可并行）→ 52 → 53（必须最先）→ 54/55/56 可并行 → 57 → 58 → 59。

**每个阶段的标准流程**：
```
1. git checkout -b phase-N/xxx
2. /opsx-propose "实现XXX功能"
3. /opsx-apply-change
     └── TDD 循环：写测试 → 生成实现 → pytest
     └── Evals 检查：run_evals → 通过/tag，劣化则排障
4. /code-review（双轴审查）
5. /gstack-qa <URL>（如有 UI）
6. git push（门禁 → 远程）
7. git checkout main && git merge --no-ff phase-N/xxx && git tag -a v0.N.0
8. /opsx-archive-change
```

**合并策略**：日常阶段（43-58）本地 `merge --no-ff` + tag；发布阶段（59）走 PR 仪式。

---

## 六、质量体系

### TDD（实现正确性）
模型测试（CRUD + 约束 + 默认值）、API 测试（端点行为 + 认证 + 错误处理）、逻辑测试（状态机 / 融合算法 / JWT 签名）。用户写测试规格 → AI 生成实现 → pytest 验证。

### Evals（质量稳定性）
| 层级 | 内容 | 通过标准 | 运行时机 |
|------|------|:--:|------|
| L1 单元 | 纯函数逻辑（规则引擎、置信度、状态机） | ≥95% | pre-commit hook |
| L2 集成 | API 端点行为（结构、状态码、认证） | ≥90% | 每个工具组完成 |
| L3 质量 | AI 内容质量（科学性、诊断准确率、辅导安全性） | ≥70% | 每日收工、push 前 |

`run_evals` 在文档 43 建**轻量版 v1**（按 tier 跑全量 pytest），文档 52 升级**完整版**（Golden 分层 + 基线对比 + CI）。

### 劣化处理决策树
```
run_evals --compare baseline.json
  ├── 无劣化      → git tag evals-ok-YYYYMMDD → 继续
  ├── 劣化 ≤3%    → 记录 devlog → 继续
  ├── 劣化 3-5%   → 排障 → 定位 golden 样本 → fix commit → 重跑
  └── 劣化 >5%    → 排障定位 bad commit → revert 或修复 → 重跑确认
```

---

## 七、Git 与提交规范

**Conventional Commits**：`<type>(<scope>): <subject>`

- type：`feat` / `fix` / `test` / `refactor` / `docs` / `chore` / `perf`
- scope：`model` / `auth` / `review` / `exam` / `diagnosis` / `ocr` / `agent` / `eval` / `persona` / `guard` / `ui` / `golden-NNN`

示例：`feat(model): add School with pytest tests`

**门禁**：
```
pre-commit  →  pytest tests/ --tb=short -x    (L1 单元，<5 秒)
commit-msg  →  校验 Conventional Commits 格式
pre-push    →  轻量版：pytest；52 后：run_evals --tier all --compare baseline.json（劣化>5% 阻断）
```

**版本节奏**：见「五、开发流程」。

---

## 八、目录结构与约定

```
chemAI-1/
├── backend/app/          后端应用（FastAPI）
│   ├── api/v1/           路由层
│   ├── core/             配置、安全、日志
│   ├── db/               会话、基类
│   ├── models/           SQLAlchemy 模型（24 实体）
│   ├── schemas/          Pydantic Schema
│   ├── services/         业务服务（诊断、出题、OCR、统计…）
│   ├── agent/            Agent 系统
│   │   ├── graph/        ReAct 图（v1/v2）
│   │   ├── personas/     4 套 Persona YAML
│   │   ├── guard/        四层护栏
│   │   ├── gateway/      意图分类器
│   │   ├── planner/      Planner（PlanStep/Plan）
│   │   ├── context/      上下文裁剪 + 依赖注入容器
│   │   ├── memory/       三层记忆
│   │   ├── tools/        42 领域工具 + 5 浏览器工具 + 元数据注册表
│   │   └── sse/          SSE 事件适配器
│   ├── chem_skills/      10 个化学技能底层实现 + _templates
│   └── mcp/              MCP 工具服务器（16 工具）
├── backend/alembic/      迁移（versions/）
├── backend/tests/        unit / integration / evals
├── frontend/teacher/     教师端 React SPA（src/{pages,components,api,styles}）
├── frontend/student/     学生端（移动优先）
├── frontend/parent/      家长端（移动优先）
├── frontend/shared/      前端共享资源
├── desktop/              pywebview + PyInstaller 打包
├── data/                 audit（审计 JSONL）/ chroma（向量库）/ uploads（上传文件）
├── scripts/              run_evals.py 等
└── docs/adr/             架构决策记录
```

**关键约定**：
- 目录划分严格对应设计文档模块（33 数据模型 / 29 Agent / 23 OCR / 37 技术选型），不新增文档未出现的模块。
- Agent 工具元数据注册表（`TOOL_META`）在启动时做**编译期完整性断言**：每个已注册工具必有元数据、每条元数据必对应已注册工具。
- `chem_skills/<skill>/` 统一结构：`engine/`（业务逻辑）+ `prompts/`（LLM 模板）+ `requirements.txt`。
- 三个数据库文件：主库 / Agent 检查点库 / Agent 长期记忆库。

---

## 九、文档体系（对齐与决策）

| 文件 | 作用 | 维护时机 |
|------|------|---------|
| `CONTEXT.md` | 领域术语权威口径（中英文 + 一句话定义，分类分组） | 出现新术语或术语含义变化时 |
| `DESIGN.md` | 前端视觉设计约束（"必须/禁止"句式，AI 可执行） | 设计系统变更时 |
| `docs/adr/YYYY-MM-DD-<主题>.md` | 架构决策记录 | 出现架构级决策时（用了 eng-review / 需求对齐 / 重大取舍） |

**ADR 格式**：背景（为什么需要）→ 决策（选了什么，一句话）→ 理由（对比至少一个替代方案）→ 结果（预期影响与风险）。

在 Trae 中：`帮我为[决策主题]写一份 ADR，保存到 docs/adr/ 下`。

**CLAUDE.md 演进**：每个阶段收尾时，把本阶段沉淀的新约定（命名规范、模式惯例、踩坑教训）追加进本文件，让后续阶段和 AI 自动继承。

**Issue tracker**：功能规格与工单以 markdown 存于 `.scratch/<feature-slug>/`。规格为 `spec.md`，工单为 `issues/NN-<slug>.md`（从 `01` 编号）。详见 `docs/agents/issue-tracker.md`。

---

## 十、Trae 使用要点

- **Plan 模式先行**：非平凡改动先出计划、取得确认再动手。
- **Checkpoint 兜底**：结构性改动前存检查点，便于回退。
- **Hooks**：用 git hooks 落实 pre-commit（pytest）与 commit-msg（格式校验）。
- **Subagents**：并行独立探索 / 实现任务可下发子代理，保护主上下文。
- **Skill 调用**：需要审查 / QA / 复盘时，优先调用已装技能而非手工重造流程。
- **环境注意**：Windows + PowerShell 5，执行策略禁用 `.ps1`（每次 shell 输出可能带 `PSecurityException` 噪音，可忽略）；调用 CLI 用 `.cmd` 变体。

---

**These guidelines are working if:** diffs 里无关改动更少、因过度设计导致的重写更少、澄清问题出现在实现之前而非出错之后。
