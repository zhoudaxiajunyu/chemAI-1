# 49. OCR批改管线

> 第五部分 - AI Coding工程实践 | ChemAI 智辅化学
> 对应 Part 4 文档：[23-答题卡OCR批改系统设计](../../4.产品设计/23-答题卡OCR批改系统设计.md)
> Scope: ocr | Git分支: phase-4/business | 提交: 3个commit

---

### 本阶段目标
- 产出：10步批改管线(上传→预处理→区域识别→OCR→答案比对→自动评分→人工复核→批量批改) + UploadSession 10状态机 + 双引擎路由 + LLM批改 + OCRTask调度 + 前端拖拽上传页面
- Git分支：phase-4/business
- 并行提示：本文档可与28/29并行开发

### 前置检查
- 确认phase-3完成
- 确认已在phase-4/business分支上
- 如果有百度OCR账号，确认BAIDU_OCR_API_KEY和BAIDU_OCR_SECRET_KEY已配置在.env中；如果暂时没有，测试使用mock数据
- [ ] OpenSpec 项目已初始化：在终端执行 `ls openspec/` 确认 `openspec/config.yaml` 存在（specs/、changes/ 随使用生成）。如不存在，回到文档42 Step 3 执行 `openspec init`

---

## 开发流程

### Step 1: /opsx:propose "实现OCR批改管线：10步答题卡批改流程(上传→预处理→区域识别→OCR→答案比对→自动评分→人工复核→批量批改) + 百度OCR/MinerU双引擎 + UploadSession状态机"

**操作**（在Claude Code中输入）：

```
/opsx:propose "实现OCR批改管线。核心需求：
1. UploadSession 7状态机：uploaded→previewing→ready→grading/importing→graded/imported→done/discarded，每个状态转换有守卫逻辑
2. 百度OCR集成：doc_analysis(通用识别, handprint_mix模式) + correct_edu(答题卡批改, 3s轮询120s超时) + paper_cut_edu(试卷切题边界框)
3. 百度Auth Token管理：30天有效期+300秒安全边际自动刷新
4. MinerU集成：PDF解析+化学式LaTeX提取，不可用时回退到百度OCR
5. 双引擎路由：PDF→MinerU优先(失败降级百度)、图片→百度OCR优先(失败降级Vision LLM)、混合→并行
6. LLM批改引擎：3种答案来源(题库匹配/教师录入/LLM自判)，答案标准化比较(case-insensitive, trim)
7. OCRTask批量调度：APScheduler 5s轮询处理pending任务，支持重试
8. 3个Agent工具：query_ocr_progress / grade_answer_sheets / save_grading_results
9. 前端ocr.html(拖曳上传+进度条+结果表格) + ocr-sheets.html(批量上传+预览网格+历史批次+状态徽章)
目标页面：/teacher/ocr-grading"
```

**你应该看到**：OpenSpec生成变更提案。

**验证**：确认提案scope为ocr，tasks拆分为3个阶段（OCR后端管线、百度OCR集成、前端上传+预览）。

**如果出错**：如果百度OCR API密钥未配置，OpenSpec提案中应标注"所有OCR测试使用mock数据，POC对比为可选步骤"。

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: docs(spec): add ocr-grading OpenSpec proposal

### Step 2: /opsx:apply → OCR后端管线TDD实现（Stage 1）

**操作**（在Claude Code中输入）：

```
/opsx:apply
只实现本阶段（Stage 1）的任务，全部完成后暂停，等我确认再进入下一阶段。
实现OCR批改管线全部后端逻辑，按TDD流程：
1. 先写测试：
   - tests/test_upload_session.py (12个测试)：UploadSession 7状态机+乐观锁
   - tests/test_baidu_auth.py (8个测试)：Token缓存+300s安全边际+凭据验证
   - tests/test_baidu_ocr.py (10个测试)：doc_analysis + correct_edu异步轮询
   - tests/test_mineru.py (6个测试)：PDF解析+化学式提取+不可用检测
   - tests/test_engine_routing.py (9个测试)：双引擎路由+降级链验证
   - tests/test_paper_cut.py (6个测试)：试卷切题边界框提取
   - tests/test_llm_grading.py (11个测试)：3种答案来源+答案比较+批改汇总
   - tests/test_ocr_task_scheduler.py (10个测试)：OCRTask模型+5s轮询调度+重试

2. 实现文件：
   - app/models/database.py：UploadSession模型+状态转换方法
   - app/services/baidu_auth.py：Token管理(模块级缓存_token和_expires_at)
   - app/services/ocr_service.py：百度doc_analysis(correct_edu可选)
   - app/services/ocr_mineru.py：MinerU Provider+工厂函数
   - app/services/document_parse_service.py：三引擎统一调度路由
   - app/services/paper_cut_client.py：试卷切题
   - app/services/llm_grading.py：LLM批改(答案来源选择+答案比较+汇总)
   - app/models/ocr_task.py：OCRTask模型
   - app/scheduler/ocr_scheduler.py：5s轮询器

3. 运行pytest确认72个测试全部通过
```

**你应该看到**：72个测试从全红到全绿——这是5份文档中测试数量最多的Step。

**验证**：关键验证点：
- UploadSession.discard()在done/discarded状态抛出ValueError("Cannot discard terminal state")
- Token缓存的300s安全边际：距到期200s触发刷新，400s使用缓存
- 双引擎降级链：MinerU→百度OCR→Vision LLM，每层失败才进入下一层
- LLM批改AUTO模式：所有答案is_correct=False，reason="需教师人工复核"
- OCRTask重试：failed→pending，error_message清空

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| MinerU导入失败 | mineru包未安装 | 实现try-except导入，check_available()返回False，测试全mock |
| 百度API 401 | Token过期或凭据无效 | 检查.env中BAIDU_OCR_API_KEY和BAIDU_OCR_SECRET_KEY是否正确 |
| correct_edu轮询超时 | 轮询间隔太长或图片复杂 | 确认轮询间隔3s，超时120s；超时的任务标记为failed |
| bbox坐标计算错误 | 角点→(left,top,width,height)转换 | left_x = min(xs), top_y = min(ys), width = max(xs)-min(xs), height = max(ys)-min(ys) |

**Windows注意**：MinerU需要Python 3.10+和约2-3GB模型存储。如果磁盘空间不足，标记MinerU为不可用，仅使用百度OCR+Vision降级。

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(ocr): add 10-step grading pipeline with dual-engine routing and LLM grading

### Step 3: /opsx:apply → Agent工具 + 前端页面（Stage 2）

**操作**（在Claude Code中输入）：

```
/opsx:apply
只实现本阶段（Stage 2）的任务，全部完成后暂停，等我确认再进入下一阶段。
实现3个OCR Agent工具和前端页面：
1. agent/tools/ocr_grading.py：
   - query_ocr_progress：按batch_id查询进度汇总(完成数/失败数/待处理数)
   - grade_answer_sheets：触发批改(支持答题卡识别结果+题库答案匹配)
   - save_grading_results：保存批改结果到StudentAnswer表+触发障碍诊断

2. frontend/pages/ocr.html：
   - 左侧232px侧边栏 + 右侧主内容区
   - 班级选择器 + 拖曳上传区(400x280px, dragenter/dragover/drop事件)
   - 进度条 + 识别结果表格(学号/姓名/答案摘要/状态)
   - 5s间隔轮询 + contenteditable手动修正

3. frontend/pages/ocr-sheets.html：
   - 批量上传(每批最多10张) + 2列预览网格
   - "开始识别"按钮 + 历史批次列表
   - 状态徽章：done绿色#2c6e49 / processing黄色#d97706 / failed红色#b43c28 / pending灰色#888
   - 重试按钮(调用POST /api/ocr/tasks/{task_id}/retry)

写前端测试验证关键交互。
```

**你应该看到**：Claude Code创建/更新文件，前端测试通过。

**验证**：确认Agent工具save_grading_results在保存后自动触发run_llm_barrier_diagnosis（障碍诊断联动）。确认前端轮询在全部完成后自动停止。

**如果出错**：

| 错误 | 原因 | 解决 |
|------|------|------|
| 拖曳上传无响应 | dragenter/dragover未阻止默认行为 | 在事件处理函数中调用e.preventDefault()和e.stopPropagation() |
| 批量上传超过10张未报错 | 前端限制逻辑遗漏 | 在选择文件后检查files.length > 10，弹出提示"每批最多上传10张答题卡" |
| 状态徽章颜色不更新 | 轮询返回的数据中status未变化 | 确认后端OCRTask的status更新逻辑正确；检查前端渲染函数中status与CSS类名的映射关系 |

**提交**（在Claude Code中输入）：
请帮我提交当前的更改。先 git status 确认变更范围，选择属于同一个逻辑变更的文件，使用 Conventional Commits 格式提交。
commit message: feat(ocr): add Agent grading tools and frontend upload/preview pages

### Step 4: 验证

**操作**（在Claude Code中输入）：

```
请运行测试验证：
1. python -m pytest tests/test_upload_session.py tests/test_baidu_auth.py tests/test_baidu_ocr.py tests/test_mineru.py tests/test_engine_routing.py tests/test_paper_cut.py tests/test_llm_grading.py tests/test_ocr_task_scheduler.py -v
2. run_evals --tier l2
3. /qa http://localhost:5173/pages/ocr.html
4. /qa http://localhost:5173/pages/ocr-sheets.html
```

**你应该看到**：全部72个测试通过，L2 Evals通过。

**验证**：关键检查点：
- OCR识别准确率（手写中文是否正确提取学号和姓名）
- 批改结果正确性（答案比较逻辑：大小写不敏感、空白trim、AUTO模式标记需人工复核）
- 保存时student_id验证（不在students表中的被跳过，不抛异常）
- 障碍诊断自动触发（save_grading_results中调用run_llm_barrier_diagnosis）

**如果出错**：如果后端未启动或百度API不可用，可以使用mock模式验证前端页面功能。检查uvicorn端口8000未被占用。

**Windows注意**：如果上传大文件超时，检查uvicorn的文件大小限制。启动时添加`--limit-max-requests 1000`防止内存泄漏。检查Windows防火墙是否允许8000端口入站。

---

## 完成标准

> **沉淀**：本阶段完成后，把新约定（命名规范、模式惯例、踩坑教训）追加到 CLAUDE.md，让后续阶段自动继承；本阶段如有架构级决策，补一份 ADR 到 `docs/adr/`（格式见 00-总体开发方案 6.4 节）。

- [ ] UploadSession 7状态机12个测试通过（状态转移+终态守卫+版本递增）
- [ ] 百度Auth Token管理8个测试通过（缓存命中+300s安全边际+凭据缺失报错）
- [ ] 百度OCR集成10个测试通过（doc_analysis提取+correct_edu轮询+超时处理）
- [ ] 双引擎路由9个测试通过（PDF→MinerU, 图片→百度, 失败→Vision降级链）
- [ ] LLM批改引擎11个测试通过（3种答案来源+AUTO安全模式+答案标准化比较）
- [ ] OCRTask调度10个测试通过（pending→processing→done/failed+5s轮询+重试）
- [ ] 前端ocr.html和ocr-sheets.html正常交互

---

> **本阶段收尾不在此文档执行。** 全部5份文档(47-51)完成后，在文档51中执行：
> /code-review（双轴审查通过）→ git checkout main && git merge --no-ff phase-4/business → git tag v0.4.0
