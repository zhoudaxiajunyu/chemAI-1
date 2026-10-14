# Vibe Coding 开发工作流 — ChemAI

> ChemAI 的全部代码由 Claude Code 生成，通过 OpenSpec 驱动结构化变更，用 GStack 浏览器自动化做验收。这不是"让 AI 随便写"——而是一套有护栏、有流程、有验证的生产级 AI 辅助开发体系。

---

## 一、三件套总览

```
┌──────────────────────────────────────────────────────────┐
│                 ChemAI 开发工作流                          │
│                                                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │  Claude Code │    │  OpenSpec   │    │   GStack    │   │
│  │             │    │             │    │             │   │
│  │  代码生成    │───→│  规范驱动    │───→│  浏览器验证  │   │
│  │  执行层      │    │  管理层      │    │  验收层      │   │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘   │
│         │                 │                 │            │
│         │    CLAUDE.md    │   propose.md    │  screenshot│
│         │    行为护栏      │   design.md     │  console   │
│         │    权限白名单    │   tasks.md      │  network   │
│         │    架构速查      │   specs/*.md    │  snapshot  │
│         │                 │                 │            │
└─────────┴─────────────────┴─────────────────┴────────────┘
```

| 工具 | 角色 | 核心职责 |
|------|------|---------|
| **Claude Code** | 代码生成 + 执行 | 理解需求 → 读取代码库 → 写出实现代码 → 运行测试 |
| **OpenSpec** | 规范驱动管理 | 结构化变更（propose → design → tasks → apply → archive） |
| **GStack** | 浏览器验收 | 页面导航、元素交互、截图验证、JS 断言、网络/控制台调试 |

---

## 二、CLAUDE.md — AI 的"上岗说明书"

### 2.1 三层上下文体系

ChemAI 的 CLAUDE.md 不是一个大文件，而是分层设计：

```
D:\化学\CLAUDE.md           ← 根级：通用行为准则（65 行）
  内容：先思考再编码、简洁至上、精准修改、目标驱动执行
  作用范围：整个项目，每次对话自动加载

D:\化学\chemai-backend\CLAUDE.md  ← 项目级：架构速查表（151 行）
  内容：Agent 层（v2 vs v1）、安全护栏、API 端点表、
        测试命令、已知缺陷、工作流场景
  作用范围：chemai-backend 目录下的开发

D:\化学\chemai-backend\CONTEXT.md  ← 领域词汇表
  内容：学生/教师/班级/障碍类型/知识点等核心概念的唯一定义
  作用范围：跨文件术语一致性
```

### 2.2 根级 CLAUDE.md 的实际规则

```markdown
## 1. 先思考再编码
- 陈述假设，不确定就问
- 多种方案时全部列出，不自己选
- 更简单的方案存在时，主动提出

## 2. 简洁至上
- 不写未要求的功能
- 不为单次使用建抽象
- 200 行能干的事不写 50 行？重写

## 3. 精准修改
- 不改相邻代码、注释、格式
- 不重构没坏的东西
- 匹配现有风格

## 4. 目标驱动执行
- 把任务转化为可验证目标
- "改好了"不够，要有"对应评测全部通过"
```

### 2.3 项目级 CLAUDE.md 的架构速查

```markdown
## ChemAI 项目架构

### Agent 层
- v2（推荐）: create_react_agent + Persona 过滤
- v1（回退）: Coordinator + Router + 6 Sub-Agent
- 端点：/api/agent/chat/langgraph/stream (SSE)
- 版本切换：API 参数 ?version=v1|v2

### 安全护栏
- GuardState: recursion_limit=12, 去重, 审批门控
- 破坏性工具: delete_bank, assign_adaptive_practice → 需要 request_approval
- Persona 隔离: 学生不能看到教师工具

### 测试命令
- 确定性评测（无 LLM）: python evals/run_evals.py --unit
- API 评测（需 LLM）: python evals/run_evals.py --agent

### 已知缺陷
- search_exam_bank 只读 JSON，不读 SQLite → HIGH
- LLM 有时跳过 request_approval → MEDIUM
```

**关键设计**：CLAUDE.md 不是"指导 AI 怎么写代码"，而是"告诉 AI 这个项目的上下文和约束"。AI 每次对话从零开始，CLAUDE.md 是它了解项目的唯一窗口。

---

## 三、OpenSpec — 规范驱动的变更管理

### 3.1 四步循环

ChemAI 的所有功能变更都通过 OpenSpec 四步循环管理。这不是"写个需求文档"，而是**一套有严格产出物的结构化流程**：

```
/opsx:explore    →  调研与思考（只读，不写代码）
/opsx:propose    →  创建变更（proposal.md + design.md + tasks.md + specs/）
/opsx:apply      →  逐任务实施（更新 tasks.md 复选框）
/opsx:archive    →  归档（移至 archive/ + 时间戳）
```

### 3.2 实际案例：chemai-architecture-overhaul

这是 ChemAI 最大的一次架构变更——向量搜索集成、长期记忆、智能上下文管理。完整的 OpenSpec 流程如下：

**第一步：`/opsx:propose`**

生成变更目录 `openspec/changes/chemai-architecture-overhaul/`，包含四个工件：

1. **proposal.md** — 回答"为什么做"和"改什么"
```markdown
# 架构升级：向量搜索 + 长期记忆 + 智能上下文

## 动机
当前系统存在三个能力缺口：
1. 题库搜索仅用关键词匹配，无法语义检索
2. Agent 对话状态在 InMemorySaver 中，重启丢失
3. 长对话没有上下文裁剪，token 消耗线性增长

## 变更内容
- 向量化：Dashscope Embedding + ChromaDB 语义检索
- 长期记忆：LangGraph SqliteStore 持久化
- 上下文管理：TrimMessages + LLM 摘要混合策略
```

2. **design.md** — 回答"怎么改"及技术决策
```markdown
## D1: 选择 Dashscope 而非 sentence-transformers
理由：中文文本嵌入质量高、API 成本低、无需 GPU

## D2: 选择 SqliteStore 而非双写
理由：LangGraph 原生支持、零额外运维、与现有 SQLite 统一

## D3: 选择 TrimMessages 而非全量摘要
理由：最后 6 条保留原文（辅导对话需要精确上下文）、
      前 24 条用 LLM 摘要（节省 token 但保留主题连续性）
```

3. **tasks.md** — 可逐项执行的 checklist
```markdown
## Phase 1: 向量搜索集成
- [x] 安装 dashscope SDK
- [x] 实现 embedding 函数
- [x] 创建 ChromaDB collection
- [x] 迁移题库数据到向量库
- [x] 实现语义搜索接口
- [x] 评测：搜索准确率 > 80%

## Phase 2: 长期记忆
- [x] 初始化 SqliteStore
- [x] 实现 memory_student_get / memory_teacher_get
...
```

4. **specs/** — 行为规格（Gherkin 风格场景）
```
specs/vector-search-integration/spec.md
  场景：搜索"氧化还原"应返回相关题目即使不包含这个词
  场景：空搜索应返回空结果而非报错

specs/long-term-memory/spec.md
  场景：同一学生两次对话应共享记忆
  场景：不同学生的记忆应完全隔离
```

**第二步：`/opsx:apply`**

Claude Code 读取 `tasks.md`，逐项实施：
- 读取每个 task → 理解意图 → 读取相关代码 → 生成实现 → 运行评测 → 标记 `[x]`
- 如果卡住或有歧义，暂停并询问——不做假设
- 36 个 tasks 全部在 apply 流程中完成

**第三步：`/opsx:archive`**

变更完成 → 同步 delta spec → 移至 `archive/2026-07-02-chemai-architecture-overhaul/`。

### 3.3 OpenSpec 实战统计

ChemAI 项目在整个开发周期中产生了 **60+ 个 OpenSpec 变更**，覆盖：

| 类别 | 变更数 | 示例 |
|------|:---:|------|
| 基础架构 | 8 | 基础搭建、Provider 层、Channel API |
| Agent 系统 | 12 | pydantic-ai 迁移、Gateway 路由、Multi-Agent 架构、v2 单 Agent、Browser Agent |
| 前端 | 5 | Chat UI、Exam 工作台、Diagnosis 面板、Students 页面、移动端 |
| 功能模块 | 10+ | OCR 管线、出题工作台、诊断引擎、自适应练习、长期记忆 |
| 修复/优化 | 15+ | Exec Loop 修复、安全加固、性能优化、去重、SSE 流式修复 |

---

## 四、GStack — 浏览器自动化验收

### 4.1 GStack 是什么

GStack 是 Claude Code 的一个技能插件（skill），提供无头浏览器自动化能力。在 ChemAI 开发中，它被用作**前端验收工具**——不是人工打开浏览器"看看对不对"，而是用脚本化的方式验证。

### 4.2 实际使用模式（基于 718 条真实日志还原）

ChemAI 的 GStack 使用统计（`chemai-backend/.gstack/browse-audit.jsonl`，718 次操作，2026-05-25 ~ 2026-07-03）：

**模式 1：页面状态验证**

```bash
# 1. 注入 JWT token（跳过登录流程，加速测试）
$B goto http://localhost:8000/login.html
$B js "sessionStorage.setItem('token', '$JWT')"

# 2. 导航到目标页面
$B goto http://localhost:8000/teacher

# 3. 快照检查页面元素
$B snapshot -i    # 交互模式，列出所有可交互元素
$B snapshot -d 3  # 3 层深度，查看 DOM 结构

# 4. 截图存证
$B screenshot
```

**模式 2：交互流程测试**

```bash
# 考试工作台流程验证
$B goto http://localhost:8000/pages/exam-v2.html
$B fill @e14 "盐类水解"      # 填写知识点
$B click @e23                 # 点击"生成题目"
$B js "document.querySelectorAll('.question-card').length"  # 验证题目数量
# → 5  (期望 ≥ 3)
$B click @e45                 # 点击"发布考试"
$B console --errors           # 检查是否有 JS 错误
```

**模式 3：调试与排错**

```bash
# 排查 SSE 流式连接问题
$B console                    # 查看控制台输出
# → "SSE connected" "tool_call: chemistry_tutor" "SSE disconnected"

$B network                    # 查看网络请求
# → GET /api/agent/chat/langgraph/stream 200
# → POST /api/exam/create 500  ← 找到问题

$B js "JSON.parse(document.body.innerText)"  # 解析错误响应
```

### 4.3 GStack 在设计迭代中的作用

ChemAI 的前端经历了三次重大重写（v1 Vue3 → v2 Vanilla JS → v3 精简 5 页），GStack 在每次重写后承担了"自动化回归测试"的角色：

```bash
# 重写后验证：每个页面加载 + 核心流程通过
for page in teacher exam-v2 diagnosis students ocr; do
  $B goto http://localhost:8000/pages/$page.html
  $B console --errors | grep -q "0 errors" || echo "FAIL: $page"
done
```

---

## 五、分层 Prompt 策略

### 5.1 核心原则：先计划，再执行

Claude Code 的"3 次尝试模型"（来自 Sanity Staff Engineer 的 6 周实践报告）：

- **第 1 次**：~95% 的代码是废的——AI 在建立上下文
- **第 2 次**：~50% 可用——理解更深了，但仍有偏差
- **第 3 次**：可工作——进入迭代优化

ChemAI 的实际做法是**在 Prompt 里强制跳过前两次**：

```
❌ 不好的 Prompt：
"帮我做一个考试工作台页面"

✅ 好的 Prompt：
"在做任何事之前，先：
1. 读取现有的 exam-v2.html 理解当前的页面结构
2. 读取 /api/exam 下的端点定义
3. 输出你要创建/修改的文件清单和修改计划
4. 等我确认后再写代码"
```

### 5.2 分层实现策略

每次只改一层，改完验证，再改下一层：

```markdown
Layer 1: 数据层
  Prompt: "在 Student 表增加 barrier_profile 字段（JSON），
   创建对应的 migration。先输出 migration 脚本，不执行。"

Layer 2: API 层
  Prompt: "在 /api/diagnosis 增加 GET /student/{id}/barrier-profile 端点，
   返回 student.barrier_profile 的解析结果。先读现有端点代码了解模式。"

Layer 3: 前端层
  Prompt: "在 diagnosis.html 增加障碍画像展示区域，
   调用新加的 barrier-profile API。先读现有页面了解组件模式。"
```

### 5.3 Prompt 模板（ChemAI 实际使用）

来自课程系统 (`curriculum/`) 的标准 Prompt 格式：

```markdown
## 产出物
- [ ] 文件 1: agent/tools/redox_tutor.py
- [ ] 文件 2: agent/tools/__init__.py（更新注册）

## 前置条件
- 已读取 agent/tools_core.py 了解 TOOL_META 机制
- 已读取 agent/tools/_make_tutor_tool.py 了解工厂模式

## 操作步骤
1. 读取 agent/tools/ionic_equation_tutor.py 作为模板
2. 创建 redox_tutor.py，复用工厂模式
3. 在 __init__.py 注册新工具
4. 在 TOOL_META 声明 personas: ["student", "tutor"]
5. 在 student.yaml 的 available_skills 增加 redox_tutor
6. 运行 python evals/test_tutor_factory.py 验证
```

---

## 六、AI 编码护栏

### 6.1 权限白名单

`D:\化学\.claude\settings.local.json` 中配置了精确的命令白名单：

```json
{
  "permissions": {
    "allow": [
      "Bash(uvicorn:*)",
      "Bash(python:*)",
      "Bash(docker:*)",
      "Bash(git:*)",
      "Bash(openspec:*)",
      "WebSearch(*)",
      "WebFetch(api.deepseek.com)",
      "WebFetch(api.dashscope.aliyuncs.com)"
    ],
    "deny": [
      "Bash(rm:*)",
      "Bash(git push:*)",
      "Bash(git reset --hard:*)",
      "Read(.env)",
      "Read(*credentials*)"
    ]
  }
}
```

### 6.2 不可触碰的红线

- `.env` 文件 — AI 永远不能读取（含 API key）
- `git push` — AI 永远不能推送代码
- `git reset --hard` — AI 永远不能强制重置
- 数据库 migration — AI 可以生成脚本，但不能执行
- 生产环境 — AI 只能操作 localhost

### 6.3 每次提交前的人工检查

```
[ ] git diff 查看所有变更
[ ] 确定性评测 86/86 通过
[ ] 没有修改 .env 或 credentials 文件
[ ] 没有新增未授权的依赖包
[ ] 新增代码有对应的评测场景
```

---

## 七、完整开发流程（一个功能的端到端案例）

以下是一个新功能在 ChemAI 中的完整开发流程——以"增加 tutoring tool"为例：

```
第 1 天上午：OpenSpec 提案
  /opsx:propose add-periodic-law-tutor
  → 生成 proposal.md / design.md / tasks.md / specs/

第 1 天下午：方案评审
  人工审核 proposal.md 和 design.md
  → 确认"新增 periodic_law_tutor"的动机合理
  → 确认使用工厂模式（复用 _make_tutor_tool）

第 2 天上午：实施
  /opsx:apply add-periodic-law-tutor
  → Claude Code 读取 tasks.md，逐项实施：
    1. 读取 ionic_equation_tutor.py 作为模板
    2. 创建 periodic_law_tutor.py（15 行配置）
    3. 在 __init__.py 注册
    4. 更新 TOOL_META
    5. 更新 student.yaml
    6. 写评测场景 + 运行验证

第 2 天下午：GStack 验收
  $B goto localhost:8000/m/
  $B fill @e1 "元素周期律中原子半径的变化规律是什么"
  $B js "document.querySelector('.tutor-title').textContent"
  → "元素周期律"  ← 验证 Agent 调用了正确的 tutoring tool
  $B console --errors

第 2 天晚上：归档
  /opsx:archive add-periodic-law-tutor
  → 变更移至 archive/2026-07-04-add-periodic-law-tutor/
```

**总耗时：2 天。** 如果不使用这套工具链（手工编写 60 行工具代码 + 手工测试），预计耗时 1-1.5 天。工具链的优势在**复杂功能**上更明显——chemai-architecture-overhaul（36 个 tasks，6 个 spec 文件）通过 openspec 的结构化变更管理，避免了在多个文件之间遗漏依赖。

---

## 八、行业对照：ChemAI 的工具链在行业中处于什么位置

| 实践 | 行业标准（2025） | ChemAI 做法 | 对齐 |
|------|---------------|-----------|:--:|
| AI 编码护栏 | CLAUDE.md + 权限白名单 | 三层 CLAUDE.md + 精确 allow/deny | ✅ |
| 规范化变更 | OpenSpec spec-driven | OpenSpec propose→apply→archive（60+ 变更） | ✅ |
| 自动化验收 | Playwright/Cypress | GStack 浏览器自动化（718 次操作） | ✅ |
| 评测门禁 | CI + Eval | 确定性评测 86 个 < 5s + API 评测 36 个 ~2min | ✅ |
| 分层 Prompt | 先计划再执行 | 3 次尝试模型 + 分层实施 + 标准化 Prompt 模板 | ✅ |
| 代码审查 | Human-in-the-loop | 每次 commit 前 git diff + 评测 + 人工检查 | ✅ |

**ChemAI 的多层护栏**（CLAUDE.md → OpenSpec → GStack → Evals → 人工审查）确保了 AI 辅助编码不会以牺牲质量为代价。行业数据表明，AI 生成代码的缺陷密度高于人工代码（CodeRabbit 2025 年报告：1.7x 重大缺陷、2.7x XSS 漏洞），而 ChemAI 通过评测体系 + 权限白名单 + 人工审查三道防线将这些风险控制在可接受范围内。

---

*基于 ChemAI 实际开发工作流逆向整理 | 数据来源：`.claude/settings.local.json`（权限配置）、`curriculum/`（17 个 Session 的 Prompt 模板）、`openspec/changes/archive/`（60+ 变更记录）、`.gstack/browse-audit.jsonl`（718 次浏览器操作）| 最后更新：2026-07-05*
