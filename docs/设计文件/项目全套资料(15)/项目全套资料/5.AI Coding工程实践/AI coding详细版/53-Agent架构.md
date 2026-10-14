# 53. Agent架构 — Gateway、ReAct、SSE、记忆、审计、Provider回退

> 前置条件：完成文档52《Evals评测体系》、文档43《数据模型与认证体系》
> 对应 Part 4 文档：[29-Agent对话系统设计](../../4.产品设计/29-Agent对话系统设计.md)
> 你将拥有：Gateway → ReAct循环 → SSE流 → 对话管理 → 上下文窗口 → 三级记忆系统 → SqliteStore → 审计日志 → Provider故障切换

---

## 前置检查

- [ ] OpenSpec 项目已初始化：在终端执行 `ls openspec/` 确认 `openspec/config.yaml` 存在（specs/、changes/ 随使用生成）。如不存在，回到文档42 Step 3 执行 `openspec init`

---

## 概述

本文档将构建ChemAI的Agent核心架构——整个系统的大脑。请求通过Gateway路由进来，经过JWT认证和Token Bucket限流，进入ReAct推理循环（Thought → Action → Observation），结果通过SSE实时推送到前端。系统还包含对话管理、上下文窗口组装、三级记忆系统和审计日志。

整个过程分为6个Step，遵循总体开发方案的标准流程：创建分支 → OpenSpec提案 → 分批apply → Evals验证 → 打tag。

---

## 架构总览

```
前端请求 (POST /api/agent/chat)
      │
      ▼
┌────────────── Gateway ──────────────┐
│  JWT认证 → Token Bucket限流 → 路由  │
└──────────────┬──────────────────────┘
               │
               ▼
┌────────────── ReAct Agent Engine ──────────────┐
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐ │
│  │ Thought   │───▶│  Action   │───▶│Observation│ │
│  │ (LLM推理) │◀───│ (工具调用) │◀───│ (结果解析) │ │
│  └──────────┘    └──────────┘    └───────────┘ │
│                                                  │
│  依赖: ToolRegistry │ LLMClient │ ContextManager │
└──────────────┬───────────────────────────────────┘
               │
               ▼ SSE事件流 (thinking/tool_call_start/tool_call_result/text_delta/done)
         ┌──────────┐
         │  前端渲染  │
         └──────────┘
```

**数据流关键路径**：前端请求 → Gateway认证限流 → ConversationService创建/加载对话 → ContextManager组装上下文 → ReActAgent.run()开始循环 → LLMClient调用Provider → ToolRegistry.execute()执行工具 → AuditLogger记录 → SSE推送到前端。

**组件清单**：

| 组件 | 文件 | 职责 |
|------|------|------|
| AgentGateway | `services/gateway.py` | JWT认证 + Token Bucket限流 |
| ReActAgent | `services/react_agent.py` | ReAct循环控制 + SSE事件生成 |
| ToolRegistry | `services/tool_registry.py` | 工具注册/描述/执行 |
| LLMClient | `services/llm_client.py` | 多Provider调用 + 健康检查 + 故障切换 |
| ConversationService | `services/conversation_service.py` | 对话CRUD + 消息管理 |
| ContextManager | `services/context_manager.py` | 滑动窗口 + token预算分配 |
| MemorySystem | `services/memory.py` | 短期(AsyncSqliteStore，LangGraph 内置) + 长期(ChromaDB) + 情景摘要 |
| SqliteStore | `services/sqlite_store.py` | 本地键值存储(诊断缓存/辅导状态) |
| AuditLogger | `services/audit.py` | JSON结构化审计日志 |
| ProviderHealthChecker | `services/llm_client.py` 内部类 | 健康检查 + 熔断器 |

---

## Step 1: 创建分支 + 架构审查 + OpenSpec提案

**本步目标**：建立Git分支，完成架构审查，创建OpenSpec变更提案。

**操作**：

在Claude Code中输入：

```
请执行以下Git操作：
1. git checkout -b phase-6/agent main
2. 确认分支已切换到 phase-6/agent
```

然后在Claude Code中输入：

```
/plan-eng-review "Agent架构：Gateway→ReAct→SSE→记忆→审计的数据流设计"

请审阅以下Agent架构的数据流和组件边界，指出潜在瓶颈和耦合点：
- Gateway层：JWT认证 + Token Bucket限流，单例模式
- ReActAgent：Thought→Action→Observation循环，max_steps=10保护
- SSE事件流：thinking/tool_call_start/tool_call_result/text_delta/done 五种事件
- 对话管理：Conversation + Message模型，滑动窗口上下文
- 记忆系统：短期(AsyncSqliteStore，LangGraph 内置) + 长期(ChromaDB) + 情景(SqliteStore)
- 审计日志：每次工具调用和LLM调用记录JSON结构化日志
- Provider切换：MiMo-V2.5→DashScope→DeepSeek 三级降级（通过 OpenAI 兼容 API） + 熔断器
```

架构审查通过后，把关键决策写进 ADR（决策不记录 = 没发生）：

```
帮我为"Agent架构选型与数据流设计"写一份 ADR，保存到 docs/adr/ 下。内容包括：背景（为什么需要Agent系统）、决策（Gateway+ReAct+SSE+三级记忆+审计+Provider降级）、理由（对比了哪些替代方案）、结果（预期影响与风险，如单例并发安全、上下文窗口成本）。
```

最后在Claude Code中输入：

```
/opsx:propose "实现Agent核心架构：Gateway(JWT认证+Token Bucket限流) + ReAct循环(Thought→Action→Observation) + SSE事件流 + 对话管理(CRUD+上下文窗口) + 三级记忆(AsyncSqliteStore + ChromaDB（LangGraph 内置）) + 审计日志 + Provider健康检查与故障切换"
```

**你应该看到**：
- Git分支 `phase-6/agent` 已创建
- 架构审查指出了数据流中的潜在瓶颈（如Gateway单例的并发安全、ReAct循环的step上限保护、记忆系统TTL配置合理性）
- OpenSpec创建了变更提案文件

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: docs(agent): add agent architecture OpenSpec proposal

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| `fatal: not a git repository` | 当前目录不是Git仓库 | 确认当前在chemai-backend项目根目录；检查是否已执行git init |
| `/plan-eng-review` 命令不可用 | Gstack未安装或未正确配置 | 确认 `~/.claude/skills/gstack/` 目录存在；重新运行 `./setup` 安装Gstack |
| OpenSpec提案创建失败 | openspec CLI未安装 | 执行 `npm install -g @fission-ai/openspec@latest` |

---

## Step 2: /opsx:apply → Gateway + ReAct + SSE

**本步目标**：生成Gateway、ReActAgent、SSE聊天端点，pytest验证通过后提交。

**操作**：

在Claude Code中输入：

```
/opsx:apply
```

Claude Code将根据OpenSpec提案生成以下文件：

**Gateway** (`backend/app/services/gateway.py`)：
- `RateLimiter`类：Token Bucket算法，rate=10 tokens/s，burst=20容量，内存字典维护用户bucket状态
- `AgentGateway`类：`authenticate(request)`从Authorization header提取Bearer token并调用verify_token验证；`check_rate_limit(user_id)`调用RateLimiter.is_allowed，超限返回HTTP 429；`handle(request)`完整流程链

**ReActAgent** (`backend/app/services/react_agent.py`)：
- 使用 LangGraph `create_react_agent` 构建 ReAct 循环
- 通过 `langchain_openai.ChatOpenAI` 调用 LLM，默认使用 DeepSeek（`deepseek-chat`，`https://api.deepseek.com/v1`）
- 支持运行时切换 provider：MiMo / DashScope / DeepSeek / 智谱
- 工具通过 ToolRegistry 注册，传给 `create_react_agent` 的 `tools` 参数
- 检查点（checkpoint）使用 LangGraph 内置的 `SqliteSaver`

**SSE端点** (`backend/app/routers/agent.py`，SSE 流式适配通过 `langgraph_sse_v2.py`)：
- `POST /api/agent/chat`：接收 `{conversation_id?, message, persona_id?}`，返回 `StreamingResponse(media_type="text/event-stream")`
- SSE事件格式规范（5种事件类型）：

```
event: thinking
data: {"step": 1}

event: tool_call_start
data: {"tool_name": "search_exam_bank", "args": {"keyword": "化学平衡"}}

event: tool_call_result
data: {"tool_name": "search_exam_bank", "success": true, "summary": "找到3条结果"}

event: text_delta
data: {"content": "好的，我为你找到了..."}

event: done
data: {"steps": 2, "tools_used": ["search_exam_bank"], "total_tokens": 450}
```

**验证**：

```bash
cd backend
pytest tests/test_agent_gateway.py tests/test_react_agent.py tests/test_agent_sse.py -v
```

全部通过后，在Claude Code中输入：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add Gateway + ReAct loop + SSE streaming
```

然后用curl验证SSE端点：

```
curl -N -X POST http://localhost:8000/api/agent/chat \
  -H "Authorization: Bearer [test_token]" \
  -H "Content-Type: application/json" \
  -d '{"message": "请解释化学平衡", "persona_id": "chemistry_teacher"}'
```

观察SSE事件流格式是否正确（event: thinking/tool_call_start/tool_call_result/text_delta/done）。

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| JWT认证失败(HTTP 401) | verify_token函数导入路径不对，或Authorization header格式不是"Bearer xxx" | 检查 `from app.services.auth import verify_token` 导入路径；确认header格式 |
| 限流器始终返回429 | Token bucket参数过小(rate=1)，或测试共享user_id | 调整初始化参数为 `rate=10, burst=20`；每个测试用独立user_id |
| ReAct循环死循环不退出 | max_steps=0或None，或has_tool_calls始终返回True | 确认max_steps>0；打印steps_taken调试 |
| SSE事件顺序错乱 | yield顺序与事件发生顺序不一致 | 确保yield顺序为: thinking → tool_call_start → tool_call_result → text_delta → done |
| SSE连接立即断开 | StreamingResponse media_type未设，或CORS未配置 | 确认 `media_type="text/event-stream"`；添加CORS头 |
| 工具调用后响应content为空 | 只追加了tool消息但assistant消息content为None | 同时追加assistant消息(含tool_calls)和tool消息(含result) |

---

## Step 3: /opsx:apply → 对话管理 + 上下文窗口

**本步目标**：生成ConversationService和ContextManager，提交。

**操作**：

在Claude Code中输入：

```
/opsx:apply
```

**数据模型** (`backend/app/models/conversation.py`)：
- `Conversation`：id, uuid(UUID4), user_id(FK→users), persona_id, title, status(active/archived/deleted), message_count, total_tokens_used, created_at, updated_at
- `Message`：id, conversation_id(FK→conversations), role(user/assistant/system/tool), content, tool_calls(JSON, [{tool_name, input, output, latency}]), token_count, metadata(JSON), sequence_num, created_at

**ConversationService** (`backend/app/services/conversation_service.py`)：
- `create_conversation(user_id, title?, persona_id?) → Conversation`
- `list_conversations(user_id, page, size) → 分页结果`（按updated_at降序，排除deleted）
- `archive_conversation(conversation_id, user_id)` / `delete_conversation(conversation_id, user_id)`（软删除）
- `add_message(conversation_id, role, content, tool_calls?, token_count?, metadata?)`（自动更新message_count和total_tokens_used）
- `get_messages(conversation_id, page, size) → 分页结果`（按sequence_num升序）
- `get_context_window(conversation_id, max_tokens=8000) → List[Message]`（从最新消息往前取，按token预算截断）

**ContextManager** (`backend/app/services/context_manager.py`)：
- `assemble_context(system_prompt, persona, messages, relevant_docs=None) → List[Dict]`：按优先级分配token预算
  - 扣除system_prompt + persona固定消耗
  - 剩余available = max_tokens - reserve_tokens - 基础消耗
  - 注入相关文档(relevant_docs)，每条截断500字符
  - 从新到旧选取消息，超出则停止
  - 截断旧消息时插入 "[早期{count}条消息已省略]"
- `should_summarize(messages, threshold=20) → bool`
- `_estimate_tokens(text) → int`：中文约1.8字符/token，英文约4字符/token

**验证**：

```bash
cd backend
pytest tests/test_conversation_service.py tests/test_context_manager.py -v
```

全部通过后，在Claude Code中输入：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add conversation management + context window
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| 拉取对话列表返回了其他用户的对话 | list_conversations未按user_id过滤 | 确认SQL含 `WHERE user_id = ?` 条件 |
| add_message后message_count未更新 | 事务未提交或更新SQL未执行 | 确认方法中执行了UPDATE并db.commit() |
| 软删除后对话仍出现在列表中 | 查询未排除status='deleted' | 添加 `WHERE status != 'deleted'` 条件 |
| 中文对话token估算严重偏小 | 中文1.5字符/token过于乐观 | 调整为1.8-2字符/token保守比例 |
| context_window返回的token总数远超max_tokens | 按消息条数而非实际token数估算 | 改为按每条消息的实际token_count字段累计 |

---

## Step 4: /opsx:apply → 记忆系统 + SqliteStore + 审计日志

**本步目标**：生成三级记忆系统、SqliteStore和AuditLogger，提交。

**操作**：

在Claude Code中输入：

```
/opsx:apply
```

**MemorySystem** (`backend/app/services/memory.py`)：
- 短期记忆：LangGraph 内置的 `AsyncSqliteStore`（`chemai_store.db`），由 `app/main.py` 中 `get_store()` 管理单例
- 长期记忆：ChromaDB 向量存储（`store_long_term()` / `search_long_term()`），用于题目搜索等语义检索场景
- 对话检查点：LangGraph `SqliteSaver`，持久化对话状态

**SqliteStore**（LangGraph 内置 `AsyncSqliteStore`，位于 `chemai_store.db`）：
- 由 `app/main.py` 在应用启动时通过 `AsyncSqliteStore.from_conn_string()` 懒加载初始化
- 命名空间键值存储，用于 Agent 长期记忆和诊断缓存
- 通过 `get_store()` 获取单例，自动执行 `setup()`

**AuditLogger** (`backend/app/services/audit.py`)：
- `log_agent_request(user_id, conversation_id, message)`：事件类型"agent_request"
- `log_tool_call(user_id, tool_name, args, result, latency_ms)`：事件类型"tool_call"，args/result截断200字符
- `log_llm_call(user_id, model, prompt_tokens, completion_tokens, latency_ms)`：事件类型"llm_call"
- `log_error(user_id, error_type, message, traceback)`：事件类型"error"，traceback截断500字符
- 输出：JSON结构化日志，FileHandler写入 `logs/audit.log`

**验证**：

```bash
cd backend
pytest tests/test_memory.py tests/test_sqlite_store.py tests/test_audit.py -v
```

全部通过后，提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add 3-tier memory system + audit logging
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| `AsyncSqliteStore` 初始化失败 | `chemai_store.db` 路径不正确或无写权限 | 确认 `app/main.py` 中 `get_store()` 的 `db_path` 指向正确的项目根目录 |
| LangGraph 检查点未持久化 | `SqliteSaver` 未正确连接到 Agent graph | 确认 `create_react_agent` 的 `checkpointer` 参数传入了共享的 `SqliteSaver` 实例 |
| ChromaDB 连接失败 | `persist_directory` 不存在或无写权限 | 创建目录：`mkdir -p ./data/chroma` |
| SQLite `database is locked` | 多线程并发写入冲突 | LangGraph `AsyncSqliteStore` 内置连接池管理，确保使用单例 |
| JSON 审计日志序列化失败(TypeError) | 数据含 datetime 对象 | 使用 `json.dumps(record, default=str)` |
| audit.log 文件未生成 | logs/ 目录不存在或无写权限 | `os.makedirs("logs", exist_ok=True)` |

---

## Step 5: /opsx:apply → LLM Client + Provider切换

**本步目标**：生成多Provider LLM客户端和健康检查器，提交。

**操作**：

在Claude Code中输入：

```
/opsx:apply
```

**LLMService** (`backend/app/services/llm_service.py`)：
- 所有 Provider 通过 OpenAI 兼容 API 调用（`base_url` + `api_key`）
- 优先级链：MiMo-V2.5 主力 → DashScope 备选 → DeepSeek 第三后备
- `MiMo API`（`https://api.xiaomimimo.com/v1/chat/completions`，模型 `mimo-v2.5`）：用于出题、审核、诊断、联网搜索
- `DashScope`（`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`）：MiMo 不可用时的备选
- `DeepSeek`（`https://api.deepseek.com/v1/chat/completions`，模型 `deepseek-chat`）：用于 Agent 对话、意图分类
- API Key 从 `.env` 中读取（`MIMO_API_KEY`、`DASHSCOPE_API_KEY`、`DEEPSEEK_API_KEY`）
- `generate_text(prompt, system_prompt, temperature, max_tokens, provider="auto")`：按 provider 优先级链自动故障切换，成功即返回，异常尝试下一个
- 内置请求缓存（TTL=300s）和频率限制（默认30次/分钟）

**验证**：

```bash
cd backend
pytest tests/test_llm_client.py tests/test_provider_health.py -v
```

全部通过后，提交：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(agent): add multi-provider LLM client with health check
```

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| `All LLM providers failed` | 所有 API Key 未设置或网络无法访问 | 检查 `.env` 文件中 `MIMO_API_KEY`、`DASHSCOPE_API_KEY`、`DEEPSEEK_API_KEY`；用 curl 测试 API 连通性 |
| Provider 返回认证错误 | API Key 无效或已过期 | 登录对应平台（小米MiMo/阿里云百炼/DeepSeek）验证 Key 状态 |
| `generate_text` 返回 mock 内容 | 所有 Provider Key 均未配置 | 设置至少一个 API Key 以启用真实 LLM 调用 |
| 健康检查消耗过多 API 配额 | 检查频率过高 | 仅在调用失败时触发健康检查（lazy checking） |
| 所有 Provider 不可用 | 网络全局故障 | 检查网络连接；`generate_text` 内置重试（最多3次，指数退避） |

---

## Step 6: 验证 + Agent Phase基础打tag

**本步目标**：运行全量Evals，curl测试完整SSE链路，打tag标记Phase基础完成。

**操作**：

在Claude Code中输入：

```
请帮我执行以下验证步骤：

1. run_evals --tier l1,l2
   确认Agent架构的所有L1/L2测试通过

2. curl测试完整SSE链路：
   curl -N -X POST http://localhost:8000/api/agent/chat \
     -H "Authorization: Bearer [test_token]" \
     -H "Content-Type: application/json" \
     -d '{"message": "帮我出3道关于氧化还原反应的选择题"}'
   确认SSE事件流包含: thinking → tool_call_start → tool_call_result → text_delta → done

3. 检查审计日志：
   tail -5 logs/audit.log
   确认有agent_request和tool_call事件记录

4. /code-review
   双轴代码审查（规范轴 + 规格轴），审查通过后打标签

**打标签**（在Claude Code中输入）：
请帮我打 tag v0.6.0-core-agent，标注：Phase 6 Agent core: Gateway + ReAct + SSE + Memory + Audit + Provider switch。确认相关测试全部通过后再打。
```

**你应该看到**：
- L1/L2 Evals全部通过
- SSE事件流格式正确，5种事件依次输出
- 审计日志文件存在且包含agent_request、tool_call等事件
- Git tag `v0.6.0-core-agent` 已创建

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| Evals劣化 > 5% | 变更引入了回归 | /investigate定位bad commit → fix或revert |
| curl接收不到SSE事件 | 后端buffering或StreamingResponse配置问题 | 确认 `media_type="text/event-stream"` 和 `Cache-Control: no-cache` |
| 审计日志无tool_call记录 | 审计调用未集成到ReAct循环中 | 检查react_agent.py中run方法是否在工具调用前后插入了audit.log_tool_call() |
| 服务启动端口冲突 | 上次进程未退出 | `lsof -i :8000` 然后 `kill <PID>` |
| "帮我出题"返回占位内容而非真实题目 | 工具的handler仍是stub | 预期行为——真实工具实现见文档54|

---

## 完成

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

恭喜！你已构建了完整的Agent系统核心架构。你现在拥有：

| 组件 | 文件 | 状态 |
|------|------|:--:|
| Gateway (JWT + 限流) | `services/gateway.py` | DONE |
| ReAct Agent循环 | `services/react_agent.py` | DONE |
| SSE事件流端点 | `routers/agent.py` | DONE |
| 对话管理(CRUD) | `services/conversation_service.py` | DONE |
| 上下文窗口管理 | `services/context_manager.py` | DONE |
| 三级记忆系统 | `services/memory.py` | DONE |
| SqliteStore | `services/sqlite_store.py` | DONE |
| 审计日志 | `services/audit.py` | DONE |
| LLM多Provider客户端 | `services/llm_client.py` | DONE |
| Provider健康检查+熔断 | `services/llm_client.py` 内部 | DONE |
| 工具注册表(占位) | `services/tool_registry.py` + `tools/__init__.py` | DONE |

**工具注册表当前注册的占位工具**（handler均为stub，返回 `{"status": "not_implemented"}`）：

| 工具名 | 参数 | 后续文档 |
|--------|------|---------|
| `generate_questions` | knowledge_point, difficulty(1-5), question_type(choice/fill/calculation/experiment), count(默认1) | 文档54 |
| `diagnose_error` | question_text, student_answer | 文档55 |
| `search_knowledge` | query, top_k(默认5) | 文档54 |
| `ping` | 无 | (健康检查) |

**下一步**：进入文档54-57，为Agent实现真正的工具（出题、诊断、辅导等），每份文档可并行开发（都只依赖文档53的Agent框架）。

---

> **下一份文档**：[54-Agent工具组-出题与题库](./54-Agent工具组-出题与题库.md) -- 7个出题工具的Evals先行实现
