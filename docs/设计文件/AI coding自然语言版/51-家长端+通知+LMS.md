# 51. 家长端 + 通知 + LMS

> 第五部分 - AI Coding工程实践 | ChemAI 智辅化学
> 对应 Part 4 文档：[32-家长端与通知系统设计](../4.产品设计/32-家长端与通知系统设计.md)、[22-权限分级与访问控制系统设计](../4.产品设计/22-权限分级与访问控制系统设计.md)、[35-设计系统](../4.产品设计/35-设计系统.md)
> Scope: parent | Git分支: phase-4/business

---

### 本阶段目标
- 产出：家长端登录 + 3Tab主面板 + 浮动AI助手 + 学生-家长绑定 + 周报生成 + 多通道通知 + LMS集成 + 数据权限隔离
- Git分支：phase-4/business

### 前置检查
- 确认前面文档（尤其是文档50的学生端6页面）已完成
- 确认已在phase-4/business分支上
- [ ] OpenSpec 项目已初始化：在终端执行 `ls openspec/` 确认 `openspec/config.yaml` 存在（specs/、changes/ 随使用生成）。如不存在，回到文档42 Step 3 执行 `openspec init`

---

## Phase A: 后端（周报+通知+LMS+数据权限）

### Step A1: /opsx:explore（探索变更）

**操作**（在Claude Code中输入）：

```
/opsx:explore 探索家长端后端服务，设计文档：../4.产品设计/32-家长端与通知系统设计
```

**你应该看到**：Claude 输出探索报告，涵盖变更范围（学生-家长绑定API、周报生成引擎、多通道通知服务、LMS集成签名协议、数据权限守卫）、受影响的现有模块（auth模块、学生端绑定码生成）、风险点（如JWT签名算法兼容性、外部服务签名验证、化学术语转换的覆盖率）。

---

### Step A2: /grill-with-docs（对齐需求，更新 CONTEXT.md + ADR）

**操作**（在Claude Code中输入）：

```
/grill-with-docs 对齐家长端后端服务的需求
```

**你应该看到**：Claude 对照设计文档逐项"烤问"需求细节，包括家长登录认证模型与角色区分、绑定码生成与失效机制、周报文本的术语通俗化规则、多通道通知的回退机制、LMS 集成的签名协议、数据权限的守卫策略。任何模糊点都在此阶段澄清，并更新 CONTEXT.md。

**验证**：确认 Claude 正确理解：
- 家长 token 与学生端 token 的身份标识区分
- 绑定码每次生成都会重新生成（旧码失效）
- 化学术语按设计文档32的转换表通俗化
- 数据权限守卫在所有相关端点中调用（不遗漏）

---

### Step A3: /opsx:propose（生成后端 spec）

**操作**（在Claude Code中输入）：

```
/opsx:propose "实现家长端后端服务：周报生成、多通道通知、LMS集成与数据权限隔离"
```

**你应该看到**：OpenSpec 生成变更提案，包含 spec.md、design.md 和 tasks.md。

**验证**：确认提案 scope 为 parent，tasks 拆分为家长认证+绑定、周报+通知、LMS+数据权限。

**提交**（在Claude Code中输入）：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
```

---

### Step A4: /opsx:apply（TDD 实现后端）

**操作**（在Claude Code中输入）：

```
/opsx:apply
```

**你应该看到**：Claude Code 按照 tasks.md 的顺序，以 TDD 方式实现所有后端功能：先写测试（全红）→ 生成实现代码 → 迭代修复 → 全部通过。Apply 会处理家长登录+绑定、周报生成、多通道通知、LMS集成、数据权限隔离的全部后端实现。

**验证**：
- 确认家长 token 与学生端 token 区分
- 确认绑定码每次生成都会重新生成（旧码失效）
- 确认多个家长可以绑定同一学生
- 确认守卫检查在所有相关端点中调用（不遗漏）
- 确认周报文本中不含专业术语和排名信息
- 确认通知通道回退机制正常工作
- 确认外部服务签名格式正确
- 确认数据过滤正确生效

**如果出错**：

| 错误方向 | 排查思路 |
|----------|----------|
| 手机号格式验证问题 | 检查正则表达式的宽松度，确认仅验证基本格式 |
| 解绑后仍能访问数据 | 确认绑定关系查询条件中包含了状态过滤 |
| 外部服务签名验证失败 | 检查签名字符串的参数排序规则和拼接格式 |
| JWT签名失败 | 检查算法配置和密钥格式 |
| 周报中仍出现专业术语 | 检查LLM是否忠实执行术语转换，代码层增加正则替换兜底 |
| 权限检查被绕过 | 排查所有相关端点的第一行是否都调用了守卫函数 |
| 越权数据可见 | 检查数据过滤函数是否正确移除了不可见字段 |

**提交**（在Claude Code中输入）：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
```

---

### Step A5: /code-review（后端代码审查）

**操作**（在Claude Code中输入）：

```
/code-review
```

**你应该看到**：Claude 以 Matt Pocock 风格进行全面代码审查，输出审查报告。

**关键检查项**：
- 家长认证与数据权限的隔离是否完备（不可越权看到其他学生数据）
- 周报文本的化学术语转换是否全覆盖
- 通知通道回退机制的错误处理是否健壮
- LMS 集成的签名验证是否正确

---

### Step A6: /opsx:archive（归档后端规格）

**操作**（在Claude Code中输入）：

```
/opsx:archive
```

**你应该看到**：OpenSpec 将已完成的后端变更提案归档。

**验证**：确认 `openspec/changes/` 中该提案已移除，`openspec/archive/` 中出现对应的归档记录。

---

> **前置检查**：确认本阶段对应的原型页面已生成。原型位于 `frontend/` 目录（教师端 `frontend/legacy/teacher/pages/`、学生端/家长端 `frontend/m/`，由 41-原型验证.md 生成）。如目录不存在或缺少对应页面，先完成 41-原型验证.md 的原型生成再进入 Phase B。

## Phase B: 前端（家长端页面）

> 后端 API 就绪后开始前端开发。

### Step B1: /opsx:explore（探索前端页面设计）

**操作**（在Claude Code中输入）：

```
/opsx:explore 探索家长端前端页面，设计文档：../4.产品设计/32-家长端与通知系统设计、../4.产品设计/35-设计系统、../4.产品设计/38-前端页面设计规格，遵守项目根目录的 DESIGN.md（42号文档创建的前端视觉规范），参考原型：frontend/m/parent-login.html、frontend/m/parent.html
```

**你应该看到**：Claude 输出探索报告，涵盖变更范围（家长登录+绑定、3Tab主面板、浮动AI助手）、受影响的现有模块（auth模块、学生端页面）、风险点（如浮动按钮被父元素overflow裁剪）。

---

### Step B2: /opsx:propose（生成前端 spec）

**操作**（在Claude Code中输入）：

```
/opsx:propose "实现家长端前端页面：登录、3Tab主面板与浮动AI助手"
```

**你应该看到**：OpenSpec 生成变更提案，包含 spec.md、design.md 和 tasks.md。

**验证**：确认提案 tasks 拆分为登录+绑定机制、3Tab主面板+浮动AI。

**提交**（在Claude Code中输入）：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
```

---

### Step B3: /opsx:apply（TDD 实现前端）

**操作**（在Claude Code中输入）：

```
/opsx:apply
```

**你应该看到**：Claude Code 按照 tasks.md 的顺序，以 TDD 方式实现前端页面。

**验证**：
- 确认化学术语已在报告 Tab 中按设计文档32的术语转换表被通俗化
- 确认学习特点文本不含焦虑词汇
- 确认 AI 解读使用 parent persona
- 确认浮动按钮不被父元素 overflow 裁剪

**如果出错**：

| 错误方向 | 排查思路 |
|----------|----------|
| 登录后注册触发逻辑问题 | 检查HTTP状态码的判断条件是否合理覆盖了各种后端响应 |
| 术语转换未生效 | 检查术语映射表是否在渲染前被执行，确认映射表覆盖了设计文档中的全部术语对 |
| 浮动按钮位置偏移或被裁剪 | 检查CSS定位是否被overflow:hidden父元素影响，确认定位和z-index层级 |
| AI解读内容过长 | 检查parent persona的系统提示词中是否包含了长度约束，代码层增加兜底截断 |
| 子女下拉选择器为空 | 确认数据库中该家长存在活跃绑定记录，检查子女列表API是否返回非空 |

**提交**（在Claude Code中输入）：

```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
```

---

### Step B4: /code-review（前端代码审查）

**操作**（在Claude Code中输入）：

```
/code-review
```

**你应该看到**：Claude 以 Matt Pocock 风格进行全面代码审查。

**关键检查项**：
- 浮动AI助手的 parent persona 是否忠实执行
- 化学术语转换的前端兜底处理

---

### Step B5: 联调（前后端集成验证）

在 Claude Code 中输入：

帮我把前后端都启动起来，跑一遍核心用户流程确认前后端联通正常。有问题就修，修完再跑一遍。

**验证**：核心用户流程（家长登录 → 绑定学生 → 3Tab切换 → 浮动AI → 通知列表）前后端联通正常，无接口报错。

---

### Step B6: /qa（浏览器验收）

**操作**（在Claude Code中输入）：

```
/qa
```

**你应该看到**：Claude 启动浏览器，自动走查家长端完整流程：手机号登录 → 绑定学生 → 3Tab切换（概览/报告/AI助手）→ 通知列表 → 浮动AI对话。发现问题自动修复（gstack）。

**关键检查点**：
- 隐私隔离必须生效
- 化学术语全部按设计文档32转换表处理
- AI解读不制造焦虑
- 通知列表状态正确切换
- 浮动AI助手动画正常

**如果出错**：如果绑定码曾被覆盖（旧码失效），让学生端重新生成绑定码。如果同时测试多角色，使用不同的浏览器或隐身模式避免token混淆。

**Windows注意**：如果同时测试多个角色（学生/教师/家长），建议使用不同浏览器或隐身模式窗口，避免localStorage的token混淆。

---

### Step B7: /opsx:archive（归档前端规格）

**操作**（在Claude Code中输入）：

```
/opsx:archive
```

**你应该看到**：OpenSpec 将已完成的前端变更提案归档。

**验证**：确认 `openspec/changes/` 中该提案已移除，`openspec/archive/` 中出现对应的归档记录。

---

### Step B8: 合并分支 + 打标签（本文档执行）

> 这是 Phase 4 的最后一份文档，收尾步骤在此执行。

全部5份文档(47-51)完成后，执行以下收尾步骤：

**操作**（在Claude Code中输入）：

```
请帮我执行Phase 4的收尾工作：
1. /opsx:archive 确认所有变更提案已归档
2. /review 检查 phase-4/business 分支上的所有变更
3. 切换到 main 分支然后合并：git checkout main && git merge --no-ff phase-4/business
4. 打版本标签：git tag v0.4.0
5. 跑一遍全量 Evals 确认合并后一切正常
6. 推送到远程（过 no-mistakes 门禁）：git push no-mistakes main --tags
```

**你应该看到**：archive 确认归档完成，/review 输出审查报告，merge 成功，tag 创建，Evals 全部通过。

**验证**：确认 git log 显示 phase-4/business 的所有 commit 已合并到 main。确认标签指向合并 commit。

**如果出错**：如果 merge 有冲突，检查 main 分支上是否有 phase-4/business 之外的新 commit。如果 Evals 劣化>5%，按00-总体开发方案的劣化处理决策树操作（/investigate 定位 bad commit → 修复或 revert）。

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] 家长登录 + 绑定机制测试通过
- [ ] 3Tab主面板正常渲染
- [ ] 浮动AI助手正常交互
- [ ] 通知系统测试通过
- [ ] LMS集成测试通过
- [ ] 数据权限测试通过
- [ ] 前后端联调通过（登录 → 绑定 → 3Tab → 浮动AI → 通知全流程联通）
- [ ] 家长端完整流程在浏览器验证通过
- [ ] Code review 通过，无严重问题
- [ ] /qa 浏览器验收通过

---

## 工具分布

| OpenSpec | Gstack | TDD | Evals | Git |
|:--:|:--:|:--:|:--:|:--:|
| explore + grill + propose + apply + archive | /code-review /qa + 联调 | apply 自动按 tasks.md TDD | L1+L2 | squash merge / --no-ff merge |

---

### Phase 4 产出总览

| 文档 | Scope | 页面 |
|------|-------|------|
| 49-自适应练习 | practice | /student/practice, /student/review |
| 50-学情面板 | analytics | /teacher/analytics |
| 51-OCR批改 | ocr | /teacher/ocr-grading |
| 50-学生端6页面 | ui (student) | /student/* |
| 53-家长端+LMS | parent | /parent/* |
| **合计** | **5个scope** | **10+页面** |
