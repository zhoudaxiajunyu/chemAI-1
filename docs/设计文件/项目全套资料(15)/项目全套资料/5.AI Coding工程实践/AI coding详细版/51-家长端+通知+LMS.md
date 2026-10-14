# 51. 家长端 + 通知 + LMS

> 第五部分 - AI Coding工程实践 | ChemAI 智辅化学
> 对应 Part 4 文档：[32-家长端与通知系统设计](../../4.产品设计/32-家长端与通知系统设计.md)、[22-权限分级与访问控制系统设计](../../4.产品设计/22-权限分级与访问控制系统设计.md)
> Scope: parent | Git分支: phase-4/business | 提交: 4个commit

---

### 本阶段目标
- 产出：家长端登录+3Tab主面板(概览/学习报告/消息) + 浮动AI助手 + 学生-家长绑定机制 + 周报生成 + 7通道通知系统 + 4种LMS连接器 + 数据权限模型
- Git分支：phase-4/business
### 前置检查
- 确认文档47-50已完成（尤其是文档50的学生端6页面，家长绑定码从学生端report.html生成）
- 确认已在phase-4/business分支上
- [ ] OpenSpec 项目已初始化：在终端执行 `ls openspec/` 确认 `openspec/config.yaml` 存在（specs/、changes/ 随使用生成）。如不存在，回到文档42 Step 3 执行 `openspec init`

---

## 开发流程

### Step 1: /opsx:propose "实现家长端+通知+LMS：手机号+绑定码登录 + 3Tab主面板(概览/学习报告/消息) + 浮动AI助手(parent-role) + 7通道通知 + LMS集成 + 数据隐私隔离"

**操作**（在Claude Code中输入）：

```
/opsx:propose "实现家长端、通知系统和LMS集成。核心需求：
1. 家长登录：手机号+绑定码(6位数字)，独立JWT(chemai_parent_token)，自动区分首次注册/已有账号
2. 3Tab主面板：
   - Tab1概览：4张统计卡片(练习量/正确率/连续天数/累计总量)+学习特点(通俗描述，无负面词汇)+本周学习时间线
   - Tab2学习报告：知识掌握进度条(3级)+术语通俗化转换(6对映射：氧化还原反应→物质与氧气反应等)+家庭配合建议(可操作，无命令式词汇)+AI解读按钮(parent persona SSE流式)
   - Tab3消息：5种通知类型(weekly_report/score_alert/learning_plan/reminder/daily_report)+已读/未读区分+手风琴展开
3. 浮动AI助手：右下角56x56圆形按钮+呼吸灯动画，SSE覆盖层(半透明蒙层)，5个预设提示词，parent-role Agent
4. 学生-家长绑定：6位随机绑定码+去重+多家长绑定同一学生+解绑(status→inactive)
5. 周报生成：家长友好自然语言(无排名/无专业术语/无负面词汇/<=200字)
6. 7通道通知系统：系统DB+钉钉+企业微信+Telegram+LTI 1.3+SFTP+Webhook(7种事件类型)
7. 4种LMS连接器：GenericLMS(HMAC-SHA256)+DingTalk(OAuth2)+WeCom(CorpID/Secret)+LTI13(Deep Linking JWT)
8. 数据权限隔离：_verify_parent_binding守卫+_filter_parent_visible_data白名单(可见：练习量/正确率/通俗薄弱点/学习特点/建议/周总结；不可见：其他学生/排名/原始答题/教师评语)
目标页面：/parent/*"
```

**你应该看到**：OpenSpec生成变更提案。

**验证**：确认提案scope为parent，tasks拆分为4个阶段（登录+绑定、3Tab+AI助手、通知系统、LMS集成）。

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: docs(spec): add parent-portal OpenSpec proposal

### Step 2: /opsx:apply → 家长登录 + 绑定机制 TDD实现（Stage 1）

**操作**（在Claude Code中输入）：

```
/opsx:apply
只实现本阶段（Stage 1）的任务，全部完成后暂停，等我确认再进入下一阶段。
实现家长登录和绑定机制，按TDD流程：
1. 先写测试：
   - tests/test_parent_login.py (5个测试)：手机号格式验证+绑定码格式+自动注册+token存储
   - tests/test_parent_binding.py (11个测试)：绑定码生成+验证+重复绑定+解绑+权限检查

2. 实现：
   - app/api/parent.py：
     * POST /api/parent/send-bind-code/{student_id}：生成6位随机绑定码→存入students.bind_code
     * POST /api/parent/bind：验证绑定码→创建StudentParentBinding(status="active")
     * DELETE /api/parent/bind/{binding_id}：解绑(status→"inactive")
     * GET /api/parent/children/{parent_id}：查询活跃绑定子女列表
   - app/models/database.py：StudentParentBinding模型(binding_id, student_id(FK), parent_id(FK), bind_code, status, relation, created_at)

3. 前端：
   - frontend/m/parent-login.html：手机号(11位)+绑定码(6位)表单，先尝试登录(404→自动注册)，成功存储chemai_parent_token

4. 运行pytest确认16个测试全部通过
```

**你应该看到**：16个测试通过。

**验证**：确认家长JWT token键名为chemai_parent_token（与学生端的chemai_student_token区分）。确认绑定码每次调用send-bind-code都会重新生成（旧码失效）。确认多个家长可以绑定同一学生。

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| 手机号格式验证失败 | 正则表达式过于严格 | 确认正则`/^1\d{10}$/`仅验证11位以1开头的数字 |
| 登录返回404后未自动注册 | 后端注册接口返回的不是404 | 放宽触发条件为`response.status === 404 || response.status === 401` |
| 解绑后仍能访问 | _verify_parent_binding被绕过 | 确认查询条件包含`AND status = 'active'` |

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(parent): add parent phone+bind-code login and student-parent binding mechanism

### Step 3: /opsx:apply → 3Tab主面板 + 浮动AI助手（Stage 2）

**操作**（在Claude Code中输入）：

```
/opsx:apply
只实现本阶段（Stage 2）的任务，全部完成后暂停，等我确认再进入下一阶段。
实现家长主面板3个Tab和浮动AI助手：
1. frontend/m/parent.html（单文件，3个Tab切换）：
   - Tab1概览：
     * 头部功能区(子女姓名下拉选择器+绑定子女/设置/退出)
     * 4张统计卡片(本周练习数量/正确率%/连续学习天数/累计练习总量)
     * 学习特点通俗描述(不使用"障碍""缺陷""差"等负面词汇)
     * 本周学习动态时间线(未学习日期显示灰色"休息")
   - Tab2学习报告：
     * 知识掌握进度条(3级：良好>=80%/加强中40-80%/需要加强<40%)
     * 术语通俗化映射(6对：氧化还原反应→物质与氧气反应 等)
     * 家庭配合建议(不出现"督促""监督""要求"等命令式词汇)
     * "AI解读"按钮→POST /api/parent/child/{id}/report/ai-summary SSE流式
   - Tab3消息：
     * 通知列表(GET /api/parent/notifications?parent_id={pid})
     * 已读/未读区分(未读粗体+蓝色圆点)
     * 手风琴展开详情(展开时自动标记已读)
     * 5种通知类型图标映射+相对时间显示("刚刚""3天前")

2. 浮动AI助手（追加到parent.html）：
   - 右下角fixed定位56x56圆形按钮，黄色呼吸灯脉冲动画
   - 半透明覆盖层面板(占据屏幕下部60%)
   - 5个预设提示词(快捷芯片水平滚动)
   - SSE流式(persona固定"parent"，thread_id前缀"p-")
   - 隐私保护：AI回复不含"排名""对比""其他同学"

3. 写前端测试验证：
   - tests/test_parent_overview.py：4卡片+特点无负面词汇+时间线排序+子女切换
   - tests/test_parent_report.py：进度条3级颜色+术语转换+建议无命令词+SSE解读
   - tests/test_parent_messages.py：未读样式+手风琴+自动已读+图标映射+相对时间
   - tests/test_parent_ai_assistant.py：浮动按钮+预设提示词+SSE渲染+persona参数

4. 后端支撑：
   - GET /api/parent/child/{student_id}/report：返回家长可见数据(已过滤)
   - GET /api/parent/child/{student_id}/weekly：本周学习动态
   - POST /api/parent/child/{student_id}/report/ai-summary：SSE流式解读
   - GET /api/parent/notifications：通知列表(支持type过滤)
   - PUT /api/parent/notifications/{id}/read：标记已读
```

**你应该看到**：Claude Code创建parent.html（含3个Tab和AI助手）和4个前端测试文件。

**验证**：确认化学术语图表在Tab2中全部被通俗化转换。确认学习特点文本不含"障碍""缺陷""差""落后"等焦虑词汇。确认AI解读使用parent persona且不超过150字。确认浮动按钮position:fixed不被父元素overflow裁剪。

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| 术语转换未生效 | 映射表未在渲染前执行 | 确认terminologyMap包含全部6对，且在渲染知识掌握表前对知识点名称执行replace |
| 浮动按钮位置偏移或被裁剪 | CSS定位被overflow:hidden父元素影响 | 确认按钮CSS: position:fixed; bottom:24px; right:24px; z-index:9999 |
| AI解读内容超过150字 | parent persona未限制输出长度 | 在prompt中明确要求"不超过100字"，代码层面对>150字截断 |
| 子女下拉选择器为空 | 数据库中该家长无活跃绑定 | 先通过学生端生成绑定码+家长登录完成绑定，确认GET /api/parent/children返回非空 |

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(parent): add 3-Tab dashboard (overview/report/messages) with floating AI assistant

### Step 4: /opsx:apply → 通知系统 + 周报生成 + LMS集成 + 数据权限 TDD实现（Stage 3）

**操作**（在Claude Code中输入）：

```
/opsx:apply
只实现本阶段（Stage 3）的任务，全部完成后暂停，等我确认再进入下一阶段。
实现通知系统、周报、LMS集成和数据权限，按TDD流程：
1. 先写测试：
   - tests/test_parent_weekly_report.py (6个测试)：通俗语言+无排名+鼓励语气+<=200字+家庭建议+权限
   - tests/test_notification_channels.py (9个测试)：7通道发送+Webhook事件+通道失败回退
   - tests/test_notification_types.py (7个测试)：5种通知类型+类型过滤+优先级排序
   - tests/test_lms_connectors.py (8个测试)：4种连接器+HMAC签名+JWT claims+disabled开关
   - tests/test_parent_permissions.py (8个测试)：可见/不可见字段+绑定验证+无绑定拒绝+排名屏蔽

2. 实现文件：
   - app/services/weekly_report_service.py：周报生成(LLM prompt含术语转换表+后处理验证)
   - app/services/notification_service.py：
     * NotificationService：7通道发送(system/dingtalk/wecom/telegram/webhook)
     * 5种通知类型：send_weekly_report/send_score_alert/send_learning_plan/send_reminder/send_daily_report
     * 通道回退：外部通道失败→写入系统DB
   - app/services/lms_connector.py：
     * GenericLMSConnector：REST API+HMAC-SHA256签名+标准请求头(X-API-Key/X-Timestamp/X-Platform)
     * DingTalkConnector：AppKey+AppSecret→OAuth2
     * WeComConnector：CorpID+CorpSecret
     * LTI13Connector：JWT RS256+Deep Linking claim
     * WebhookService：7种事件类型注册/触发/取消
   - app/api/parent.py：
     * _verify_parent_binding(parent_id, student_id, db)：守卫函数，无活跃绑定→403
     * _filter_parent_visible_data(data)：白名单过滤(allowed_fields=7项)
     * 在所有parent端点开头调用_verify_parent_binding，返回前调用_filter

3. 运行pytest确认38个测试全部通过
```

**你应该看到**：38个测试从全红到全绿。

**验证**：确认_verify_parent_binding在所有parent端点中调用（不遗漏）。确认周报文本中不包含化学专业术语和排名信息。确认notification通道回退：外部通道失败时自动写入系统DB。确认HMAC签名格式：`{sorted_params}&timestamp={timestamp}`。

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| HMAC签名测试失败 | 签名字符串参数排序或拼接有误 | 确认参数按key字母序排列后用&拼接，再追加&timestamp= |
| JWT RS256签名失败 | 算法或私钥格式错误 | 确认algorithm="RS256"而非HS256，私钥PEM格式 |
| 周报中仍出现专业术语 | LLM未忠实执行术语转换 | 在prompt最前面明确要求"必须替换所有术语"，代码层增加正则替换兜底 |
| 权限检查被绕过 | _verify_parent_binding未在某个端点调用 | 检查所有parent端点(GET report/weekly, POST ai-summary)的第一行 |
| 家长可看到排名数据 | _filter_parent_visible_data未移除disallowed字段 | 确认白名单为7个字段，其余全部pop或设为null |

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(parent): add 7-channel notification system, weekly report, 4 LMS connectors, and data privacy isolation

### Step 5: 验证

**操作**（在Claude Code中输入）：

```
请运行测试验证：
1. python -m pytest tests/test_parent_*.py tests/test_notification_*.py tests/test_lms_*.py -v
2. run_evals --tier l2
3. /qa http://localhost:8000/m/parent-login.html
执行完整家长旅程：
- 先到学生端m/report.html→设置→生成绑定码(记录6位数字)
- 打开parent-login.html→输入手机号+绑定码→登录
- Tab1概览：确认4卡片数据+学习特点无负面词汇
- Tab2学习报告：确认术语通俗化+点击AI解读
- Tab3消息：确认通知列表+已读/未读切换
- 浮动AI助手：点击→选择预设提示词→验证回复不含排名信息
- 隐私验证：修改URL中的student_id访问未绑定学生→确认403
```

**你应该看到**：全部测试通过，L2 Evals通过，家长端完整流程正常。

**验证**：关键检查点：
- 隐私隔离必须生效（未绑定学生返回403，排名数据不可见）
- 化学术语在家长端全部被通俗化转换
- AI解读不制造焦虑（不出现"很差""落后""不及格""排名"）
- 通知列表的已读/未读状态正确切换
- 浮动AI助手的呼吸灯动画正常

**如果出错**：如果绑定码曾被覆盖（旧码失效），让学生端重新点击"生成绑定码"。如果同时测试多角色，使用不同的浏览器或隐身模式避免token混淆。

**Windows注意**：如果同时测试多个角色（学生/教师/家长），建议使用不同浏览器或隐身模式窗口，避免localStorage的token混淆。

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] 家长登录(bind-code)+绑定机制16个测试通过（生成码+验证+去重+多家长绑定+解绑）
- [ ] 3Tab主面板正常渲染（概览统计卡片+报告术语转换+消息已读/未读）
- [ ] 浮动AI助手正常交互（SSE流式+parent persona+隐私约束+5个预设提示词）
- [ ] 通知系统16个测试通过（7通道+5种类型+通道回退+优先级排序）
- [ ] LMS连接器8个测试通过（4种连接器+HMAC签名+JWT+disabled开关）
- [ ] 数据权限8个测试通过（可见字段白名单+无绑定403+排名屏蔽+答题详情脱敏）
- [ ] 家长端完整旅程在浏览器验证通过

---

## 本阶段收尾（仅在本文档执行）

全部5份文档(47-51)完成后，执行以下收尾步骤：

**操作**（在Claude Code中输入）：

```
请执行Phase 4收尾：
1. /code-review：双轴代码审查全部phase-4/business的变更（规范轴 + 规格轴）
2. git checkout main && git merge --no-ff phase-4/business -m "merge: phase-4/business (文档47-51: 业务功能)"
3. git tag -a v0.4.0 -m "Phase 4 完成: 自适应练习 + 学情面板 + OCR批改 + 学生端6页面 + 家长端通知LMS"
4. run_evals --tier all --compare baseline.json（合并后最终确认）
```

**你应该看到**：/code-review输出双轴审查报告，merge成功，tag创建，Evals全部通过。

**验证**：确认git log显示phase-4/business的所有commit已合并到main。确认v0.4.0 tag指向合并commit。

**如果出错**：如果merge有冲突，检查main分支上是否有phase-4/business之外的新commit。正常情况下main应只有phase-1~3的merge commit，不会冲突。如果Evals劣化>5%，按00-总体开发方案的劣化处理决策树操作（/investigate定位bad commit→修复或revert）。

---

### Phase 4 产出总览

| 文档 | Scope | 测试数 | 页面 |
|------|-------|:-----:|------|
| 27-自适应练习 | practice | 62 | /student/practice, /student/review |
| 28-学情面板 | analytics | 63 | /teacher/analytics |
| 29-OCR批改 | ocr | 72 | /teacher/ocr-grading |
| 48-学生端6页面 | ui (student) | 前端 | /student/* |
| 31-家长端+LMS | parent | 54 | /parent/* |
| **合计** | **4个scope** | **251+** | **10+页面** |
