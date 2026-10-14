# 57. Persona系统 + GuardState护栏 + MCP服务器

> 前置条件：完成文档53-56（Agent架构 + 三组Agent工具）
> 对应 Part 4 文档：[29-Agent对话系统设计](../../4.产品设计/29-Agent对话系统设计.md) 第4-12章（Persona、Guard、Planner、Context、Memory、Audit、MCP）
> 本阶段目标：4角色Persona YAML配置 + GuardState四层运行时护栏 + MCP工具服务器

---

## 概述

前三章完成了Agent工具的编码实现。现在需要三层基础设施来保证这些工具被正确、安全地调用：

- **Persona系统**：控制工具可见范围
- **GuardState护栏**：运行时安全校验
- **MCP服务器**：外部系统调用入口

这三层为全部Agent工具提供安全和访问控制能力。领域模型（Persona配置Schema、GuardState四层架构、MCP工具分工）已在设计文档中完整建立，因此跳过 `/grill-with-docs`。架构遵循既有模式，跳过 `/plan-eng-review`。整体采用OpenSpec标准工作流：

```
/opsx:explore -> /opsx:propose -> /opsx:apply（TDD全部实现+Evals） -> /code-review -> /opsx:archive -> 合并+打标签
```

---

## 你需要读的设计文档

在开始之前，让Claude Code阅读以下设计文档章节。本文档只给结构，具体规格让Claude从设计文档中自己提取：

| 设计文档 | 章节 | 需要提取的内容 |
|---------|------|---------------|
| `29-Agent对话系统设计.md` | 第4章 | Persona YAML Schema、角色定义、system_prompt核心原则、工具白名单 |
| `29-Agent对话系统设计.md` | 第5章 | GuardState四层防护架构、各层数据结构、审批门控规则、特殊字段剥离机制 |
| `29-Agent对话系统设计.md` | 第12章 | MCP vs Agent工具分工、MCP工具清单、MCP端点定义、错误响应格式 |
| `22-权限分级与访问控制系统设计.md` | 第2章、第4章 | ROLE_PERMISSIONS矩阵、家长端数据权限模型 |
| `25-四维安全审核引擎设计.md` | 第7章、§11.3 | 审核服务接口、安全红线保障机制 |

> 不要手动复制设计文档内容到prompt里。直接让Claude `Read` 这些文件，它自己能提取结构和语义。

---

## 前置检查

在Claude Code中输入：

```
帮我检查一下前置条件：
1. 确认在chemai-backend项目根目录
2. 确认当前分支正确，前序文档创建的核心模块文件都存在
3. 跑pytest确认Agent核心测试通过
```

---

## OpenSpec工作流

> 工具组遵循标准工作流——领域模型已建立，无需 `/grill-with-docs`；架构遵循既有模式，无需 `/plan-eng-review`。

### Step 1: `/opsx:explore`

探索当前Agent架构中Persona、GuardState和MCP相关的基础设施状态，确认工具注册表和各层接口的现有情况。

在Claude Code中输入：

```
/opsx:explore 探索Persona系统+GuardState+MCP服务器，设计文档：D:\pm\课程资料\全套资料\4.产品设计\29-Agent对话系统设计
```

### Step 2: `/opsx:propose`

创建Persona系统、GuardState护栏和MCP服务器的OpenSpec变更提案。

在Claude Code中输入：

```
/opsx:propose "实现Persona系统+GuardState护栏+MCP服务器：4角色YAML配置、四层运行时护栏、MCP工具服务器"
```

### Step 3: `/opsx:apply`（按tasks.md TDD实现所有组件 + Evals）

按照tasks.md一次性实现三大部分的全部代码和Evals。Claude将从设计文档中自行提取规格定义，按TDD流程先写测试再实现。

**实现清单**：

**Part 1: Persona系统**
| 组件 | 设计文档参考 | 关键验证点 |
|------|------------|-----------|
| 4个Persona YAML文件 | 29-第4章 | Schema校验；工具白名单正确性；system_prompt完整性 |
| Persona YAML加载器 | 29-第4章 | 加载失败时的fallback行为；Schema验证 |
| 两层工具过滤逻辑 | 29-第4章 | 角色白名单+Persona白名单交集；Browser Tools自动附加；跨角色工具泄漏检测 |
| Persona评测 | 31 | YAML加载评测；过滤正确性评测；跨角色泄漏率为0% |

**Part 2: GuardState护栏**
| 组件 | 设计文档参考 | 关键验证点 |
|------|------------|-----------|
| Layer 1: 前置条件检查 | 29-第5章 | 会话状态校验；认证上下文检查 |
| Layer 2: 调用限流 | 29-第5章 | Token Bucket算法；并发调用限制 |
| Layer 3: 去重检查 | 29-第5章 | 连续相同调用拦截；超时后去重窗口失效 |
| Layer 4: 审批门控 | 29-第5章 | 审批集合注册；审批流程生命周期 |
| 特殊字段剥离 | 29-第5章 | _component剥离；_route剥离；SSE适配器转换 |
| GuardState评测 | 31 | 四层各自独立评测；边界条件覆盖 |

**Part 3: MCP工具服务器**
| 组件 | 设计文档参考 | 关键验证点 |
|------|------------|-----------|
| MCP工具注册 | 29-第12章 | 工具清单完整性；Agent/MCP分工边界 |
| MCP API端点 | 29-第12章 | 端点定义；认证集成 |
| 错误响应格式 | 29-第12章 | 标准错误格式；错误码枚举 |
| MCP评测 | 31 | 端点可调用性；错误处理；工具列表查询 |

在Claude Code中输入：

```
/opsx:apply
```

### Step 4: `/code-review`

实现完成后运行Matt Pocock风格的代码审查，重点关注：跨角色工具泄漏检测、GuardState四层的执行顺序和拦截逻辑、MCP与Agent工具的分工边界、特殊字段剥离的正确性。

在Claude Code中输入：

```
/code-review
```

### Step 5: `/opsx:archive`

归档已完成的Persona+GuardState+MCP变更。

在Claude Code中输入：

```
/opsx:archive
```

### Step 6: 合并 + 打 v0.6.0 标签

在Claude Code中输入：

```
帮我把Phase 6收尾的事做了：
1. 安全审计：Prompt注入、Persona越权、工具滥用
2. 跑全量Evals确认无劣化
3. 跑Persona+GuardState+MCP全部评测确认通过
4. 全部通过后，把当前分支用 squash 方式合并到 phase-6/agent
5. 切到 main，把 phase-6/agent 用 --no-ff 合并到 main
6. 打上 v0.6.0 标签，标注写：Phase 6 complete -- Agent architecture + tools + Persona + GuardState + MCP server
7. 推送到远程（过 no-mistakes 门禁）：git push no-mistakes main --tags
合完再跑全量Evals确认无劣化。
```

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] 4个Persona YAML配置加载正确，工具数量符合设计文档
- [ ] 两层工具过滤已实现，跨角色工具泄漏率为0%
- [ ] GuardState四层防护全部通过评测
- [ ] _component 和 _route 剥离机制正确工作
- [ ] MCP工具全部注册，端点可调用
- [ ] Agent/MCP工具责任分工验证通过
- [ ] 安全审计通过
- [ ] 全量Evals通过

---

> **下一份文档**：[58-全链路验收与审查](./58-全链路验收与审查.md)
