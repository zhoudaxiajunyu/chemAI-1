# 53. Agent架构 —— Gateway、ReAct、SSE、记忆、审计、Provider回退

> 前置条件：完成文档52《Evals评测体系》、文档43《数据模型与认证体系》
> 核心设计文档：[29-Agent对话系统设计](../../4.产品设计/29-Agent对话系统设计.md) —— 完整定义 v1->v2 架构、工具目录、Persona 配置、GuardState 四层护栏、Gateway 意图分类器、Planner、ContextManager、记忆系统、审计日志、错误处理层次、MCP 工具服务器、SSE 事件协议
> 技术选型参考：[37-技术选型与工具链](../../4.产品设计/37-技术选型与工具链.md) —— LangGraph 选型理由、Provider 实测数据与 Fallback 路由
> SSE 渲染参考：[39-Agent输出界面前端SSE渲染策略](../../4.产品设计/39-Agent输出界面前端SSE渲染策略.md) —— 渲染架构、事件类型的生命周期与渲染策略
> 你将拥有：Gateway -> ReAct循环 -> SSE流 -> 对话管理 -> 上下文窗口 -> 记忆系统 -> 审计日志 -> Provider故障切换

---

## 前置检查

- [ ] OpenSpec 项目已初始化：在终端执行 `ls openspec/` 确认 `openspec/config.yaml` 存在（specs/、changes/ 随使用生成）。如不存在，回到文档42 Step 3 执行 `openspec init`

---

## 概述

本文档将构建 ChemAI 的 Agent 核心架构。请求通过 Gateway 路由进来，经过认证和限流，进入 ReAct 推理循环（Thought -> Action -> Observation），结果通过 SSE 实时推送到前端。系统还包含对话管理、上下文窗口组装、记忆系统和审计日志。

Agent架构是关键决策——涉及多组件协作、数据流设计、Provider回退策略和性能瓶颈评估。因此本变更的OpenSpec工作流过架构审查门禁。

---

## 架构总览

```
前端请求
      |
      v
┌────────── Gateway ───────────┐
│  认证 -> 限流 -> 路由         │
└──────────────┬───────────────┘
               |
               v
┌────────── ReAct Agent Engine ───────────┐
│                                           │
│  ┌──────────┐   ┌──────────┐   ┌──────┐  │
│  │ Thought   │->│  Action   │->│ Obs  │  │
│  │ (LLM推理) │<-│ (工具调用) │<-│(解析)│  │
│  └──────────┘   └──────────┘   └──────┘  │
│                                           │
│  依赖: ToolRegistry | LLMClient | ContextMgr │
└──────────────┬────────────────────────────┘
               |
               v SSE事件流
         ┌──────────┐
         │  前端渲染  │
         └──────────┘
```

**数据流关键路径**：前端请求 -> Gateway 认证限流 -> 对话服务创建/加载对话 -> 上下文管理组装上下文 -> ReAct循环 -> LLM调用 -> 工具执行 -> 审计记录 -> SSE 推送到前端。

**组件职责概览**（具体规格见设计文档 29 号各对应章节）：

| 组件 | 职责 | 设计文档参考 |
|------|------|-------------|
| Gateway | JWT认证 + Token Bucket限流 | 29 号第六章 |
| ReActAgent | ReAct循环控制 + SSE事件生成 | 29 号第二章 |
| ToolRegistry | 工具注册/描述/执行 | 29 号第三章 |
| LLMClient | 多Provider调用 + 健康检查 + 故障切换 | 37 号第二章 |
| ConversationService | 对话CRUD + 消息管理 | 29 号第十九章 |
| ContextManager | 滑动窗口 + token预算分配 | 29 号第八章 |
| MemorySystem | 三层记忆架构 | 29 号第九章 |
| SqliteStore | 本地键值存储 | 29 号第九章 |
| AuditLogger | JSON结构化审计日志 | 29 号第十章 |
| ProviderHealthChecker | 健康检查 + 熔断器 | 37 号第二章 |

---

## OpenSpec工作流

> 本变更包含关键架构决策，需要通过 `/plan-eng-review` 架构审查门禁。

### Step 0: 创建分支

在开始 OpenSpec 工作流之前，先创建 Phase 6 的开发分支。

**在 Claude Code 中输入**：

```
帮我从 main 切出 phase-6/agent 分支。
```

### Step 1: `/opsx:explore`

探索当前项目结构，了解已有后端模块和Agent相关基础设施状态。

在Claude Code中输入：

```
/opsx:explore 探索Agent架构，设计文档：D:\pm\课程资料\全套资料\4.产品设计\29-Agent对话系统设计、D:\pm\课程资料\全套资料\4.产品设计\39-Agent输出界面前端SSE渲染策略
```

### Step 2: `/grill-with-docs` 对齐Agent架构需求（产出 ADR）

让Claude深度阅读设计文档并对齐理解，更新CONTEXT.md。需要阅读的文档：

- `D:\pm\课程资料\全套资料\4.产品设计\29-Agent对话系统设计.md` —— Gateway、ReAct、SSE、记忆、审计的完整架构
- `D:\pm\课程资料\全套资料\4.产品设计\37-技术选型与工具链.md` —— LangGraph 选型理由和 Provider Fallback 策略
- `D:\pm\课程资料\全套资料\4.产品设计\39-Agent输出界面前端SSE渲染策略.md` —— SSE 事件类型与渲染映射

在Claude Code中输入：

```
/grill-with-docs 对齐Agent架构的需求
```

### Step 3: `/opsx:propose`

创建Agent核心架构的OpenSpec变更提案。

在Claude Code中输入：

```
/opsx:propose "实现Agent核心架构：Gateway->ReAct->SSE->记忆->审计->Provider回退"
```

### Step 4: `/plan-eng-review`（架构审查）

Agent架构是关键决策——涉及多组件数据流、Provider回退链、记忆系统分层、上下文窗口策略。必须通过架构审查。

在Claude Code中输入：

```
/plan-eng-review "Agent架构：Gateway->ReAct->SSE->记忆->审计的数据流设计"

帮我审查一下这个Agent架构的数据流和各个组件的边界，看看哪里有潜在的瓶颈或者耦合太紧的地方。核心组件包括：
- Gateway 层：JWT 认证 + Token Bucket 限流
- ReActAgent：Thought -> Action -> Observation 循环，有步数上限保护
- SSE 事件流：按设计文档 39 号定义的事件协议
- 对话管理：对话和消息模型，上下文用滑动窗口
- 记忆系统：三层记忆架构
- 审计日志：JSON 结构化日志
- Provider 切换：多级降级 + 熔断器
```

### Step 5: `/opsx:apply`

按照tasks.md一次性实现Agent核心架构的全部组件。Claude将从设计文档中自行提取规格参数，生成以下组件的完整代码和测试：

**Gateway**：
- 规格来源：设计文档 29 号第六章。意图分类架构、路由逻辑、认证和限流参数。

**ReActAgent**：
- 规格来源：设计文档 29 号第二章 + 设计文档 37 号第三章。Agent 模式、循环上限、checkpointer 配置方式，以及 Provider 选择策略。

**SSE端点**：
- 规格来源：设计文档 29 号第十三章 + 设计文档 39 号的事件->渲染映射。事件类型定义、数据结构和流式配置。

**ConversationService + ContextManager**：
- 规格来源：设计文档 29 号第十九章（对话管理 CRUD）和第八章（上下文管理）。三层裁剪策略、token 预算分配逻辑。

**MemorySystem + SqliteStore + AuditLogger**：
- 规格来源：设计文档 29 号第九章（记忆管理）和第十章（审计日志）。三层记忆架构、JSONL 格式日志、环形缓冲区、敏感字段脱敏、best-effort 写入策略。

**LLMService + Provider切换**：
- 规格来源：设计文档 37 号第二章（LLM Provider 选型）和设计文档 29 号第十四章（Provider 多路回退）。兼容 API 调用、优先级链自动故障切换、指数退避重试策略。

在Claude Code中输入：

```
/opsx:apply
```

### Step 6: `/code-review`

实现完成后运行Matt Pocock风格的代码审查，检查数据流正确性、错误处理覆盖、边界条件处理。

在Claude Code中输入：

```
/code-review
```

### Step 7: `/opsx:archive`

归档已完成的Agent核心架构变更。

在Claude Code中输入：

```
/opsx:archive
```

### Step 8: 合并 + 打标签

在Claude Code中输入：

```
帮我做Agent核心架构的收尾：
1. 跑 run_evals --tier l1,l2 确认Agent架构的L1/L2测试全部通过
2. curl 测一下完整SSE链路，确认事件流格式符合设计文档 39 号的定义
3. 检查审计日志是否正确记录
4. 全部通过后提交、打标签、merge到主分支
```

标签应概括本轮Agent核心架构的交付内容。

---

## 架构审查常见问题

| 错误 | 原因 | 解决 |
|------|------|------|
| `fatal: not a git repository` | 当前目录不是 Git 仓库 | 确认当前在项目根目录；检查是否已执行 git init |
| `/plan-eng-review` 命令不可用 | Gstack 未安装或未正确配置 | 确认 `~/.claude/skills/gstack/` 目录存在；重新运行 `./setup` 安装 |
| OpenSpec 提案创建失败 | openspec CLI 未安装 | 执行 `npm install -g @fission-ai/openspec@latest` |

## 实现常见问题

| 错误 | 原因 | 解决 |
|------|------|------|
| JWT 认证失败 | token 验证逻辑有问题，或 Authorization header 格式错误 | 检查 import 路径；确认 header 格式，参考设计文档 29 号 §6 和 43 号 JWT 部分 |
| 限流器始终拒绝请求 | 限流参数配置过小，或测试共享了限流 key | 检查设计文档 29 号中限流参数的规格；每个测试用独立标识 |
| ReAct 循环不退出 | 步数上限未设置或为 0，或退出判断逻辑错误 | 确认递归上限已正确配置；打印步数调试 |
| SSE 事件顺序错乱 | yield 顺序与设计文档 39 号定义的生命周期不一致 | 对照设计文档 39 号的事件状态机 |
| SSE 连接立即断开 | 流式响应配置或 CORS 有问题 | 确认 media_type 设置；添加 CORS 头 |
| 工具调用后响应为空 | 消息追加策略有问题 | 确认 assistant 消息和 tool 消息都被正确追加 |
| 对话列表返回了其他用户的数据 | list 查询未按 user_id 过滤 | 确认 SQL 含 user_id 过滤条件 |
| 消息计数未更新 | 事务未提交或 UPDATE 未执行 | 确认方法中执行了 UPDATE 并 commit |
| 软删除后对话仍出现 | 查询未排除已删除状态 | 添加状态过滤条件 |
| 中文对话 token 估算偏小 | 中文字符/token 比例过低 | 参考设计文档 29 号 §8 中的估算策略 |
| 上下文窗口 token 超限 | 按消息条数而非实际 token 数计算 | 改为按每条消息的实际 token 累计 |
| SqliteStore 初始化失败 | 数据库路径不正确或无写权限 | 确认初始化时数据库路径指向正确位置 |
| 检查点未持久化 | checkpointer 未正确连接 Agent graph | 确认创建 Agent 时的 checkpointer 参数传入了共享实例 |
| ChromaDB 连接失败 | 持久化目录不存在或无写权限 | 创建对应数据目录 |
| SQLite `database is locked` | 多线程并发写入冲突 | LangGraph 内置连接池管理，确保使用单例 |
| JSON 审计日志序列化失败 | 数据含不可序列化对象 | 使用 `json.dumps(record, default=str)` |
| audit.log 文件未生成 | logs/ 目录不存在或无写权限 | 确保目录存在 |
| 所有 Provider 都失败 | API Key 未设置或网络无法访问 | 检查 `.env` 文件中各 Provider 的 API Key 配置；用 curl 测试 API 连通性 |
| Provider 返回认证错误 | API Key 无效或已过期 | 登录对应平台验证 Key 状态 |
| 返回 mock 内容 | 所有 Provider Key 均未配置 | 设置至少一个 API Key |
| 健康检查消耗过多配额 | 检查频率过高 | 仅在调用失败时触发健康检查（lazy checking） |
| 所有 Provider 不可用 | 网络全局故障 | 检查网络连接；确认重试次数和退避间隔符合设计文档规格 |
| Evals 劣化 > 5% | 变更引入了回归 | /investigate 定位 bad commit -> fix 或 revert |
| curl 接收不到 SSE 事件 | 后端 buffering 或流式响应配置问题 | 确认 media_type 和 Cache-Control header |
| 审计日志无工具调用记录 | 审计调用未集成到 ReAct 循环中 | 检查 ReAct 循环中 run 方法是否在工具调用前后调用了审计方法 |
| 服务启动端口冲突 | 上次进程未退出 | `lsof -i :8000` 然后 `kill <PID>` |
| 出题返回占位内容 | 工具的 handler 仍是 stub | 预期行为 -- 真实工具实现见文档 54 |

---

## 完成

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

恭喜！你已构建了完整的 Agent 系统核心架构。

**工具注册表当前注册的占位工具**（handler 均为 stub，具体实现在后续文档中完成）：

| 工具名 | 后续文档 |
|--------|---------|
| 出题工具 | 文档54 |
| 诊断工具 | 文档55 |
| 搜索工具 | 文档54 |
| 健康检查工具 | (内置) |

**下一步**：进入文档 54-57，为 Agent 实现真正的工具（出题、诊断、辅导等），每份文档可并行开发（都只依赖文档 53 的 Agent 框架）。

---

> **下一份文档**：[54-Agent工具组-出题与题库](./54-Agent工具组-出题与题库.md) —— 出题工具的 Evals 先行实现
