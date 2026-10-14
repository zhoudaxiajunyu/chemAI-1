# 49. OCR批改管线

> 第五部分 - AI Coding工程实践 | ChemAI 智辅化学
> 参考设计文档: [23-答题卡OCR批改系统设计](../../4.产品设计/23-答题卡OCR批改系统设计.md), [37-技术选型与工具链](../../4.产品设计/37-技术选型与工具链.md)
> Scope: ocr | Git分支: phase-4/business

---

### 本阶段目标

- 产出: 10步批改管线(上传->预处理->区域识别->OCR->答案比对->自动评分->人工复核->批量批改) + UploadSession状态机 + 多引擎路由（图片 PP-OCRv6→百度→VLM；PDF MinerU→转图降级） + LLM批改 + OCRTask调度 + 前端拖拽上传页面
- Git分支: phase-4/business
- 并行提示: 本文档可与47/48/50/51并行开发

### 前置检查

- 确认phase-3完成
- 确认已在phase-4/business分支上
- 如果有百度OCR账号，确认相关密钥已配置在.env中；如果暂时没有，测试使用mock数据
- [ ] OpenSpec 项目已初始化: 在终端执行 `ls openspec/` 确认 `openspec/config.yaml` 存在（specs/、changes/ 随使用生成）。如不存在，回到文档42 Step 3 执行 `openspec init`

---

## Phase A: 后端（OCR批改管线）

### Step A1: /opsx:explore（探索变更）

**操作**(在Claude Code中输入):

```
/opsx:explore 探索OCR批改管线后端，设计文档：D:\pm\课程资料\全套资料\4.产品设计\23-答题卡OCR批改系统设计
```

**你应该看到**: Claude 输出探索报告，涵盖变更范围（UploadSession状态机、多引擎路由、LLM批改引擎、OCRTask调度）、受影响的现有模块、风险点（如 PP-OCRv6 本地模型依赖、百度OCR API依赖、MinerU安装要求、Token安全边际处理）。

---

### Step A2: /grill-with-docs（对齐需求，更新 CONTEXT.md + ADR）

**操作**(在Claude Code中输入):

```
/grill-with-docs 对齐OCR批改管线后端的需求
```

**你应该看到**: Claude 对照设计文档逐项"烤问"需求细节，包括10步批改管线的完整流程、UploadSession 终态守卫逻辑、Token 安全边际策略、多引擎降级链顺序（图片：PP-OCRv6→百度→VLM；PDF：MinerU→转图降级）、LLM批改自判模式、OCRTask 重试机制。任何模糊点都在此阶段澄清，并更新 CONTEXT.md。

**验证**: 确认 Claude 正确理解:
- UploadSession 终态做状态变更应抛出异常
- Token 距到期时间较短触发刷新，距到期时间较长使用缓存
- 引擎降级链每层失败才进入下一层
- LLM 无法确定答案时标记需人工复核
- OCRTask 重试时状态重置为 pending，错误信息清空

---

### Step A3: /opsx:propose（生成后端 spec）

**操作**(在Claude Code中输入):

```
/opsx:propose "实现OCR批改管线后端、UploadSession状态机、多引擎路由与OCRTask调度"
```

**你应该看到**: OpenSpec生成变更提案，包含 spec.md、design.md 和 tasks.md。

**验证**: 确认提案scope为ocr，tasks合理拆分多个阶段（OCR后端管线、引擎集成）。

**如果出错**: 如果百度OCR API密钥未配置，OpenSpec提案中应标注"所有OCR测试使用mock数据"。

**提交**(在Claude Code中输入):
```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
```

---

### Step A4: /plan-eng-review（架构审查）

**目的**：OCR 批改管线涉及异步任务调度（APScheduler）、三引擎降级链、状态机，实现前先过一遍架构审查。

在 Claude Code 中输入：

```
/plan-eng-review

请审查以下架构要点：
1. UploadSession / OCRTask 状态机与设计文档 23 号第三章、第六章的映射
2. 多引擎降级链（图片：PP-OCRv6 → 百度 OCR → VLM；PDF：MinerU → 转图 → 图片降级链）与 23 号第四章的映射
3. APScheduler 轮询架构与并发控制
```

**验证**：审查报告列出风险点和改进建议。所有问题解决后进入实现阶段。

---

### Step A5: /opsx:apply（TDD 实现后端）

**操作**(在Claude Code中输入):

```
/opsx:apply
```

**你应该看到**: Claude Code 按照 tasks.md 的顺序，以 TDD 方式实现所有后端功能：先写测试（全红）→ 生成实现代码 → 迭代修复 → 全部通过。Apply 会处理 UploadSession 状态机、百度Auth Token管理、多引擎路由与降级链、LLM批改引擎、OCRTask调度的全部实现。

**验证**: 关键验证点(以设计文档第3.2节和第七章为准):
- UploadSession终态守卫逻辑正确 —— 对终态做状态变更应抛出异常
- Token安全边际逻辑正确 —— 距到期时间较短触发刷新，距到期时间较长使用缓存
- 引擎降级链顺序正确 —— 每层失败才进入下一层
- LLM批改自判模式正确处理 —— 无法确定答案时标记需人工复核
- OCRTask重试逻辑正确 —— 状态重置为pending，错误信息清空
- Agent工具在保存结果后自动触发障碍诊断

**如果出错**:

| 症状 | 常见原因 | 排查方向 |
|------|---------|---------|
| MinerU导入失败 | mineru包未安装或模型未下载 | 实现try-except导入，check_available()返回False，测试全mock |
| PP-OCRv6引擎不可用 | paddleocr未安装或模型未下载 | 实现check_available()检查，不可用时直接降级百度OCR（与23号文档降级链一致），测试全mock |
| 百度API返回401 | Token过期或凭据无效 | 检查.env中密钥配置，确认Token管理逻辑 |
| 异步任务轮询超时 | 轮询间隔或超时阈值不合理 | 检查轮询逻辑的参数设置 |
| 坐标计算错误 | 角点坐标到矩形框的转换有误 | 检查bbox转换公式: 左上角=最小值，宽高=最大值-最小值 |

**Windows注意**: PP-OCRv6 与 MinerU 都需要 Python 3.10+ 和本地模型存储空间（PP-OCRv6 为 onnx 模型，MinerU 较大）。如果磁盘空间不足，可仅保留 PP-OCRv6 并标记 MinerU 为不可用，使用 PP-OCRv6+百度OCR+VLM 降级链。

**提交**(在Claude Code中输入):
```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
```

---

### Step A5: /code-review（后端代码审查）

**操作**(在Claude Code中输入):

```
/code-review
```

**你应该看到**: Claude 以 Matt Pocock 风格进行全面代码审查，输出审查报告。

**关键检查项**:
- UploadSession 状态机的终态守卫是否完备
- Token 安全边际逻辑是否正确
- 引擎降级链的错误处理是否健壮
- LLM 批改的自判模式是否覆盖边界情况
- OCRTask 重试逻辑是否幂等

---

### Step A6: /opsx:archive（归档后端规格）

**操作**(在Claude Code中输入):

```
/opsx:archive
```

**你应该看到**: OpenSpec 将已完成的后端变更提案归档。

**验证**: 确认 `openspec/changes/` 中该提案已移除，`openspec/archive/` 中出现对应的归档记录。

---

> **前置检查**：确认本阶段对应的原型页面已生成。原型位于 `frontend/` 目录（教师端 `frontend/legacy/teacher/pages/`、学生端/家长端 `frontend/m/`，由 41-原型验证.md 生成）。如目录不存在或缺少对应页面，先完成 41-原型验证.md 的原型生成再进入 Phase B。

## Phase B: 前端（上传/预览/批改 UI）

> 后端 API 就绪后开始前端开发。

### Step B1: /opsx:explore（探索前端页面设计）

**操作**(在Claude Code中输入):

```
/opsx:explore 探索OCR批改前端页面，设计文档：D:\pm\课程资料\全套资料\4.产品设计\23-答题卡OCR批改系统设计、D:\pm\课程资料\全套资料\4.产品设计\35-设计系统、D:\pm\课程资料\全套资料\4.产品设计\38-前端页面设计规格，遵守项目根目录的 DESIGN.md（42号文档创建的前端视觉规范），参考原型：frontend/legacy/teacher/pages/ocr.html
```

**你应该看到**: Claude 输出探索报告，涵盖变更范围（拖拽上传交互、批量处理界面、OCR识别结果展示、批改结果预览、状态徽章颜色更新）。

---

### Step B2: /opsx:propose（生成前端 spec）

**操作**(在Claude Code中输入):

```
/opsx:propose "实现OCR批改前端上传与批改预览页面"
```

**你应该看到**: OpenSpec生成变更提案，包含 spec.md、design.md 和 tasks.md。

**验证**: 确认提案中 tasks 拆分为ocr.html（拖拽上传+OCR识别）和ocr-sheets.html（批改结果展示）。

**提交**(在Claude Code中输入):
```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
```

---

### Step B3: /opsx:apply（TDD 实现前端）

**操作**(在Claude Code中输入):

```
/opsx:apply
```

**你应该看到**: Claude Code 按照 tasks.md 的顺序，以 TDD 方式实现前端拖拽上传页面和批改预览页面。

**验证**:
- 确认拖拽上传交互正常（拖曳事件阻止默认行为）
- 确认批量上传超限有报错提示
- 确认前端轮询在全部完成后自动停止

**如果出错**:

| 症状 | 常见原因 | 排查方向 |
|------|---------|---------|
| 拖曳上传无响应 | 拖曳事件未阻止默认行为 | 在事件处理函数中调用preventDefault()和stopPropagation() |
| 批量上传超限未报错 | 前端限制逻辑遗漏 | 检查文件数量限制的判断逻辑 |
| 状态徽章颜色不更新 | 轮询返回的数据中状态未变化 | 确认后端任务状态更新逻辑；检查前端渲染时status与样式的映射 |

**提交**(在Claude Code中输入):
```
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
```

---

### Step B4: /code-review（前端代码审查）

**操作**(在Claude Code中输入):

```
/code-review
```

**你应该看到**: Claude 以 Matt Pocock 风格进行全面代码审查。

**关键检查项**:
- 拖拽上传交互的边界情况处理
- 轮询逻辑的资源清理

---

### Step B5: 联调（前后端集成验证）

在 Claude Code 中输入：

帮我把前后端都启动起来，跑一遍核心用户流程确认前后端联通正常。有问题就修，修完再跑一遍。

**验证**：核心用户流程（拖拽上传 → OCR识别 → 批改结果 → 状态更新）前后端联通正常，无接口报错。

---

### Step B6: /qa（浏览器验收）

**操作**(在Claude Code中输入):

```
/qa
```

**你应该看到**: Claude 启动浏览器，自动走查答题卡识别页和答题卡批改页。验证拖拽上传、批量处理、OCR识别结果展示、批改结果展示、状态徽章颜色更新。发现问题自动修复（gstack）。

**关键检查点**:
- OCR识别准确率(手写中文是否正确提取学号和姓名)
- 批改结果正确性(答案比较逻辑: 标准化处理规则见设计文档第七章)
- 保存时student_id校验(不在students表中的记录被跳过)
- 障碍诊断自动触发(save_grading_results中联动触发)

**如果出错**: 如果后端未启动或百度API不可用，可以使用mock模式验证前端页面功能。检查uvicorn端口未被占用。

---

### Step B7: /opsx:archive（归档前端规格）

**操作**(在Claude Code中输入):

```
/opsx:archive
```

**你应该看到**: OpenSpec 将已完成的前端变更提案归档。

**验证**: 确认 `openspec/changes/` 中该提案已移除，`openspec/archive/` 中出现对应的归档记录。

---

### Step B8: 合并分支 + 打标签

> 注意：此步骤在全部5份文档(47-51)完成后统一执行，不在本文档单独操作。

在文档51的收尾阶段统一执行：`git checkout main && git merge --no-ff phase-4/business && git tag v0.4.0`

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] UploadSession状态机测试通过(状态转移 + 终态守卫 + 版本递增)
- [ ] 百度Auth Token管理测试通过(缓存 + 安全边际 + 凭据缺失报错)
- [ ] 百度OCR集成测试通过(识别提取 + 异步轮询 + 超时处理)
- [ ] 多引擎路由测试通过(PP-OCRv6图片路由 + 百度降级 + VLM兜底 + PDF走MinerU)
- [ ] LLM批改引擎测试通过(答案来源 + 安全模式 + 答案标准化比较)
- [ ] OCRTask调度测试通过(状态流转 + 轮询 + 重试)
- [ ] 前后端联调通过（拖拽上传 → OCR识别 → 批改结果 → 状态更新全流程联通）
- [ ] 前端ocr.html和ocr-sheets.html正常交互
- [ ] Code review 通过，无严重问题
- [ ] /qa 浏览器验收通过

---

> **本阶段收尾不在此文档执行。** 全部5份文档(47-51)完成后，在文档51中执行:
> `/opsx:archive` → `git checkout main && git merge --no-ff phase-4/business` → `git tag v0.4.0`
