# 55. Agent工具组 -- 诊断与学生

> 前置条件：完成文档53《Agent架构》
> 对应设计文档：[29-Agent对话系统设计](../4.产品设计/29-Agent对话系统设计.md) §3.3（工具定义与元数据）
> 关键依赖设计：[26-错题诊断与障碍分类系统设计](../4.产品设计/26-错题诊断与障碍分类系统设计.md)（三维障碍模型、规则引擎、LLM诊断流程）
> 关键依赖设计：[27-自适应练习引擎设计](../4.产品设计/27-自适应练习引擎设计.md)（ZPD模型、barrier-question策略矩阵）
> 评测框架依据：[31-评测体系设计](../4.产品设计/31-评测体系设计.md)（三级金字塔、场景推导方法论）
> 并行性：本文档与文档53、54可并行开发
> 本阶段目标：诊断与学生组的7个工具，每个独立Evals验证通过

---

## 概述

本文档实现Agent系统的第二批工具——诊断与学生组的7个工具。领域模型（三维障碍模型、ZPD模型、诊断流程、置信度体系）已在设计文档中完整建立，因此跳过 `/grill-with-docs`。工具遵循既有架构模式，跳过 `/plan-eng-review`。整体采用OpenSpec标准工作流：

```
/opsx:explore -> /opsx:propose -> /opsx:apply（TDD全部工具+Evals） -> /code-review -> /opsx:archive -> 合并+打标签
```

工具完整定义和元数据见 `29-Agent对话系统设计.md` §3.3；三维障碍模型见 `26-错题诊断与障碍分类系统设计.md`；ZPD模型见 `27-自适应练习引擎设计.md`；评测方法论见 `31-评测体系设计.md`。

---

## 前置检查

在Claude Code中输入：

```
帮我确认一下前置条件：
1. 确认在chemai-backend项目根目录
2. 确认当前分支正确，且文档53创建的核心模块文件都存在
3. 跑pytest确认Agent核心测试都过了
```

---

## OpenSpec工作流

> 工具组遵循标准工作流——领域模型已建立，无需 `/grill-with-docs`；工具遵循既有架构模式，无需 `/plan-eng-review`。

### Step 1: `/opsx:explore`

探索当前Agent架构的代码结构和已有工具的实现模式，确认诊断相关设计文档中的模型与现有代码的对齐状态。

在Claude Code中输入：

```
/opsx:explore 探索诊断与学生Agent工具组，设计文档：../4.产品设计/26-错题诊断与障碍分类系统设计、../4.产品设计/27-自适应练习引擎设计、../4.产品设计/29-Agent对话系统设计
```

### Step 2: `/opsx:propose`

创建诊断与学生工具组的OpenSpec变更提案。

在Claude Code中输入：

```
/opsx:propose "实现诊断与学生Agent工具组：diagnose_barrier、show_diagnosis、show_students、weekly_report、assign_adaptive_practice、generate_learning_plan、send_learning_plan"
```

### Step 3: `/opsx:apply`（按tasks.md TDD实现所有工具 + Evals）

按照tasks.md一次性实现7个工具的全部代码和Evals。Claude将从设计文档中自行提取每个工具的规格定义、质量风险和Eval场景，按TDD流程先写测试再实现。

**每个工具的设计规格来源**：

| 工具 | 设计文档参考 | 关键验证点 |
|------|------------|-----------|
| diagnose_barrier | 27（三维障碍模型）, 30-§3.3 | 三维障碍分类正确；置信度计算；规则引擎+LLM诊断双路 |
| show_diagnosis | 30-§21.3 | 诊断面板渲染规范；数据结构符合_route格式 |
| show_students | 30-§3.3 | 查询模式；班级名模糊匹配；分页 |
| weekly_report | 30-§4.2, 27 | Persona语言风格约束；数据聚合逻辑；LLM-as-Judge |
| assign_adaptive_practice | 28, 30-§5 | ZPD模型；barrier-question策略矩阵；审批门控 |
| generate_learning_plan | 27-§13, 30-§21.4 | 学习计划生命周期；页面桥接协议 |
| send_learning_plan | 27-§13, 30-§15 | 上下文传递；API端点调用；错误响应处理 |

在Claude Code中输入：

```
/opsx:apply
```

### Step 4: `/code-review`

实现完成后运行Matt Pocock风格的代码审查，重点关注：三维障碍模型贯穿诊断-练习全链路、ZPD策略矩阵的正确实现、LLM报告的语言风格验证、审批门控完整性。

在Claude Code中输入：

```
/code-review
```

### Step 5: `/opsx:archive`

归档已完成的诊断与学生工具组变更。

在Claude Code中输入：

```
/opsx:archive
```

### Step 6: 合并 + 打标签

在Claude Code中输入：

```
帮我把所有诊断和学生工具的测试一起跑一遍确认全部通过。通过后打标签标注评测全部通过，然后merge到Agent分支并跑全量Evals确认无劣化。
```

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] 7个工具全部pytest通过
- [ ] 三维障碍模型贯穿诊断-练习全链路
- [ ] ZPD模型和barrier-question策略矩阵正确工作
- [ ] LLM报告通过语言风格验证
- [ ] 审批门控工具已正确配置
- [ ] 合并后全量Evals无劣化

---

> **下一份文档**：[56-Agent工具组-辅导OCR与记忆](./56-Agent工具组-辅导OCR与记忆.md)
