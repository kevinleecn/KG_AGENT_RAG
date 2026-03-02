# Vibe Coding 最佳实践

> 基于 KG-Agent Demo 项目开发经验总结（50+ commits 分析）

## 目录

- [一、整体数据概览](#一整体数据概览)
- [二、高效模块分析](#二高效模块分析)
- [三、低效模块分析](#三低效模块分析)
- [四、效率对比](#四效率对比)
- [五、最佳实践清单](#五最佳实践清单)
- [六、推荐工作流](#六推荐工作流)
- [七、检查清单模板](#七检查清单模板)

---

## 一、整体数据概览

| 指标 | 数据 |
|------|------|
| 总提交数 | 50+ commits |
| fix 类型 | 29 (58%) |
| feat 类型 | 10 (20%) |
| chore/test/docs | 9 (18%) |
| refactor | 1 (2%) |
| 修改最频繁文件 | `static/js/main.js` (16 次) |
| 第二大频繁文件 | `src/parsing_manager.py` (15 次) |

### 提交类型分布

```
fix 类型：████████████████████████████████████████████████████ 58%
feat 类型：████████████████████ 20%
chore/test/docs：██████████████████ 18%
refactor：██ 2%
```

---

## 二、高效模块分析

### 🏆 案例 1：KG-LLM 融合问答引擎

**文件**：`src/qa/fusion_qa_engine.py`

**效率表现**：
- ✅ 仅用 **4 次提交**完成核心功能
- ✅ 一次设计文档 + 一次实现 + 一次测试 + 一次优化
- ✅ 代码结构清晰，约 500 行

**提交历史**：
```
63f6814 docs: add KG-LLM 融合设计 v2.md
9739483 feat: 实现真正的 KG-LLM 融合问答引擎
1ad1562 test: 添加融合问答引擎测试
b0feba7 fix: 改进问题分类，支持"哪个大模型"等助手身份询问
```

**高效原因分析**：

| 因素 | 说明 |
|------|------|
| ✅ **设计先行** | 先写设计文档明确架构 |
| ✅ **问题驱动** | 明确解决"你是谁"无法回答的问题 |
| ✅ **模式清晰** | 问题分类器采用规则匹配，简单直接 |
| ✅ **测试及时** | 实现后立即添加测试验证 |
| ✅ **单一职责** | 每个方法只负责一种回答策略 |

**代码特征（值得学习）**：

```python
# 1. 清晰的枚举定义
class QuestionType:
    LLM_ONLY = "llm_only"
    KG_ONLY = "kg_only"
    KG_LLM_FUSION = "kg_llm_fusion"
    CHAT = "chat"

# 2. 直观的分类逻辑
def _classify_question(self, question: str) -> str:
    q = question.lower().strip()

    # LLM_ONLY 类型 - 通用知识/助手相关
    if "你是谁" in q or "什么模型" in q:
        return QuestionType.LLM_ONLY

    # CHAT 类型 - 闲聊
    if "你好" in q or "谢谢" in q:
        return QuestionType.CHAT

    # KG_LLM_FUSION 类型 - 需要推理
    if "关系" in q or "如果" in q:
        return QuestionType.KG_LLM_FUSION

    # 默认 KG_ONLY
    return QuestionType.KG_ONLY

# 3. 清晰的策略路由
def ask_question(self, question: str, ...) -> Dict:
    question_type = self._classify_question(question)

    if question_type == QuestionType.LLM_ONLY:
        return self._answer_with_llm_only(question, ...)
    elif question_type == QuestionType.KG_ONLY:
        return self._answer_with_kg_only(question, ...)
    # ...
```

---

### 🏆 案例 2：文件删除功能

**效率表现**：
- ✅ 3 次提交完成：`feat` → `fix` → `docs`
- ✅ 功能完整：后端 API + 前端 UI + 文档

**提交历史**：
```
de412bf feat: 添加文件删除功能
9b2bac2 fix: 修复删除按钮点击后文件项未移除的问题
f5a1d98 docs: 添加文件删除功能说明文档
```

**高效原因**：
- 需求明确单一
- 复用现有架构（ParsingManager 模式）
- 测试验证快速

---

## 三、低效模块分析

### ⚠️ 案例 1：解析取消功能

**文件**：`src/parsing_manager.py` + `src/document_parser/pdf_parser.py` + `static/js/`

**效率表现**：
- 🔴 **13 次相关提交**，历时多次修复
- 🔴 涉及文件多，修复链长

**提交历史**：
```
fd537de fix: 实现立即响应的解析取消功能
84cdafb fix: 修复解析取消功能和中文翻译
b5c7b25 fix: 取消任务时正确跳过失败处理
f5acab4 fix: 确保取消任务状态正确更新为 CANCELLED
1a8cbe8 fix: 修复 parse_with_progress 取消时返回部分结果
b37a1c7 fix: 在 PDF 解析器中实现取消检查功能
f24e1ef fix: 正确设置取消事件而不是创建新事件
3b6ee17 feat: 添加取消功能调试日志
c71458e fix: 更新 JS 版本号强制浏览器刷新并添加取消日志
5dce620 fix: 修复 main.js 中取消按钮缺少 onclick 处理程序
956572d fix: 修复取消按钮缺少 onclick 处理词的问题
7e0f1b6 chore: 将取消按钮和确认对话框改为中文
8ef7dec fix: 修复 _is_task_cancelled 方法名错误
```

**低效原因分析**：

| 问题 | 根因 | 影响 |
|------|------|------|
| 🔴 **跨多层级** | 前端→后端→解析器→PDF 库，链路过长 | 每次修复需理解全链路 |
| 🔴 **状态管理复杂** | 取消事件、任务状态、进度状态分散 | 容易出现状态不一致 |
| 🔴 **缺少设计文档** | 没有先写取消功能的设计方案 | 边写边改，反复试错 |
| 🔴 **测试滞后** | 没有先写取消功能的测试用例 | 问题在集成后才发现 |
| 🔴 **命名不一致** | `_is_task_cancelled` vs `_is_cancelled` | 低级错误浪费时间 |
| 🔴 **浏览器缓存** | JS 修改后浏览器不刷新 | 多次提交才发现是缓存问题 |

**改进建议**：

```python
# 1. 应该先写设计文档
# docs/cancel-feature-design.md

# 2. 统一命名规范
class ParsingManager:
    def _is_cancelled(self, task_id: str) -> bool:  # 统一使用这个名称
        ...

    def cancel_parsing(self, task_id: str) -> bool:
        ...

# 3. 先写测试
def test_cancel_parsing():
    task_id = parsing_manager.parse_file_async("test.pdf")
    result = parsing_manager.cancel_parsing(task_id)
    assert result == True
    assert parsing_manager.get_task_status(task_id) == "CANCELLED"
```

---

### ⚠️ 案例 2：文件上传提取方法传递

**效率表现**：
- 🔴 **4 次相关提交**才完成
- 🔴 问题根因：前后端数据流未对齐

**提交历史**：
```
f5ea1fb fix: 在/files API 中返回 extraction_method 字段
c1f940b fix: 文件上传时传递并保存提取方法 (LLM/Spacy)
```

**低效原因分析**：

| 问题 | 根因 |
|------|------|
| 🔴 **数据流断裂** | 前端 FormData → 后端 request.form → 解析函数 → 状态保存，4 个环节 |
| 🔴 **缺少端到端测试** | 没有测试验证整个数据流 |
| 🔴 **Flask 服务器缓存** | 修改后未重启服务器，误以为代码有问题 |
| 🔴 **调试日志不足** | 问题定位困难 |

**改进建议**：

```python
# 1. 添加端到端测试
def test_upload_with_extraction_method():
    # 前端发送
    response = requests.post('/upload',
        files={'files': ('test.txt', b'content')},
        data={'extraction_method': 'llm'}
    )

    # 后端接收
    files_response = requests.get('/files')
    file = files_response.json()['files'][0]

    # 验证数据流完整
    assert file['extraction_method'] == 'llm'
    assert file['parsing_metadata']['extraction_method'] == 'llm'

# 2. 添加调试日志
@app.route('/upload', methods=['POST'])
def upload_file():
    extraction_method = request.form.get('extraction_method', 'spacy')
    logger.info(f"[UPLOAD] Received extraction_method: {extraction_method}")  # 关键日志
    # ...
```

---

### ⚠️ 案例 3：知识图谱可视化

**效率表现**：
- 🔴 初始提交：`13736 insertions(+)` (一次性导入大量代码)
- 🔴 后续多次修复显示问题

**低效原因**：
- 一次性导入过多代码，难以理解和维护
- 没有增量开发和测试

**改进建议**：

```
❌ 不好的做法：
- 一次性导入 13000+ 行代码
- 然后逐个修复问题

✅ 好的做法：
- 先实现节点显示（500 行）
- 测试验证
- 再实现连线显示（500 行）
- 测试验证
- 再实现交互功能（500 行）
- 测试验证
```

---

## 四、效率对比

| 维度 | 高效模块 (KG-LLM) | 低效模块 (取消功能) |
|------|------------------|--------------------|
| **设计文档** | ✅ 有明确设计文档 | ❌ 无设计文档 |
| **问题定义** | ✅ 单一明确问题 | ❌ 多问题交织 |
| **测试策略** | ✅ 测试先行 | ❌ 测试滞后 |
| **代码结构** | ✅ 职责单一 | ❌ 跨越多层 |
| **修改次数** | 4 次 | 13 次 |
| **单次提交大小** | 小 (<50 行) | 变化大 |
| **调试时间** | <30 分钟 | >4 小时 |

---

## 五、最佳实践清单

### 📋 实践 1：设计先行原则

**规则**：启动任何功能开发前，先花 10-20 分钟写设计文档。

**设计文档模板**：

```markdown
# [功能名称] 设计文档

## 问题描述
用一句话说清楚要解决什么问题。

## 用户故事
作为 [用户类型]，我想要 [功能]，以便 [价值]。

## 技术方案
### 架构设计
[简单的流程图或伪代码]

### 接口设计
- 前端接口：[端点/参数]
- 后端接口：[端点/参数]

### 数据结构
[关键字段定义]

## 测试用例
- [ ] 测试用例 1
- [ ] 测试用例 2

## 风险评估
[可能遇到的问题和解决方案]
```

**适用场景**：
- ✅ 新功能开发（feat）
- ✅ 跨模块修改
- ✅ 涉及前后端交互
- ❌ 简单 bug 修复（<5 行代码）

---

### 📋 实践 2：单一职责检查

**规则**：在开始编码前，确保功能可以拆分成独立的小模块。

**检查清单**：
```
[ ] 这个功能可以拆分成更小的独立功能吗？
[ ] 这个修改只影响一个文件/模块吗？
[ ] 这个方法的代码少于 50 行吗？
[ ] 这个文件少于 400 行吗？
[ ] 这个类只做一件事吗？
```

**违反后果**：
- 取消功能违反了单一职责（前端 + 后端 + 解析器 + PDF 库）
- 导致 13 次提交才完成

---

### 📋 实践 3：测试先行策略

**规则**：先写测试，再写实现。

**TDD 流程**：

```python
# 第一步：写测试（预期失败）
def test_llm_only_question_classification():
    engine = FusionKGQAEngine()
    result = engine._classify_question("你是谁？")
    assert result == "llm_only"

def test_user_intent_llm_answer():
    """测试用户明确要求 LLM 回答"""
    engine = FusionKGQAEngine()
    result = engine._classify_question("不要用知识图谱，用 LLM 回答")
    assert result == "llm_only"

# 第二步：运行测试（应该失败）
# $ pytest test_fusion_qa.py -v
# FAILED: 'llm_only' != 'kg_only'

# 第三步：实现功能
def _classify_question(self, question: str) -> str:
    # ... 添加意图识别逻辑

# 第四步：验证测试通过
# $ pytest test_fusion_qa.py -v
# PASSED
```

**适用场景**：
- ✅ 新功能开发
- ✅ Bug 修复
- ✅ 重构

---

### 📋 实践 4：端到端数据流验证

**规则**：对于涉及前后端的数据传递，必须验证整个数据流。

**验证步骤**：

```
1. 前端发送 → 检查 FormData/请求体
   console.log('FormData:', formData.get('extraction_method'))

2. 后端接收 → 添加日志打印接收到的参数
   logger.info(f"[UPLOAD] Received extraction_method: {extraction_method}")

3. 业务处理 → 添加日志打印处理的参数
   logger.info(f"[UPLOAD] Starting parsing with method: {extraction_method}")

4. 状态保存 → 添加日志打印保存的数据
   logger.info(f"[STATE] Saved extraction_method: {extraction_method}")

5. 前端显示 → 检查渲染的数据
   console.log('File data:', file.extraction_method)
```

**调试日志模板**：

```python
# 关键节点必须添加日志
@app.route('/upload', methods=['POST'])
def upload_file():
    extraction_method = request.form.get('extraction_method', 'spacy')
    logger.info(f"[UPLOAD] Step 1 - Received extraction_method: {extraction_method}")

    # ... 处理逻辑

    task_id = parsing_manager.parse_file_async(filename, extraction_method=extraction_method)
    logger.info(f"[UPLOAD] Step 2 - Started parsing with method: {extraction_method}")

    return jsonify({...})
```

---

### 📋 实践 5：服务器重启检查清单

**规则**：修改后如果功能不生效，按顺序检查以下项目。

**检查清单**：

```
[ ] Flask 服务器是否重新加载代码？
    → 查看控制台是否有 "Detected file change, reloading" 日志

[ ] 浏览器是否清除了缓存？
    → 按 Ctrl+F5 强制刷新（Windows）
    → 按 Cmd+Shift+R 强制刷新（Mac）

[ ] JavaScript 版本号是否更新？
    → 在 JS 文件中添加版本号注释 /* v1.2.3 */
    → 或使用缓存破坏：script.js?v=1.2.3

[ ] 是否有多个 Flask 进程在运行？
    → Windows: taskkill /F /IM python.exe
    → Mac/Linux: killall python

[ ] 端口是否被占用？
    → netstat -ano | findstr :5000
    → 杀掉占用端口的进程
```

---

### 📋 实践 6：命名一致性检查

**规则**：在提交前使用 grep 检查命名一致性。

**检查命令**：

```bash
# 检查方法名是否一致
grep -rn "_is_cancelled\|_is_task_cancelled" src/**/*.py

# 检查变量名风格
grep -rn "extraction_method\|extract_method" src/**/*.py

# 检查常量命名
grep -rn "^LLM_\|^KG_\|^FUSION_" src/**/*.py
```

**命名规范**：

```python
# ✅ 好的命名
class QuestionType:
    LLM_ONLY = "llm_only"
    KG_ONLY = "kg_only"

def _is_cancelled(self, task_id: str) -> bool:
    """检查任务是否被取消"""

def _serialize_neo4j_result(self, item) -> Any:
    """序列化 Neo4j 结果"""

# ❌ 不好的命名
def checkIfTaskWasCancelledOrNot(self):  # 太长
def chk_cancel(self):  # 太短
def _is_task_cancelled(self):  # 与 _is_cancelled 不一致
```

---

### 📋 实践 7：提交原子化原则

**规则**：每次提交只做一件事。

**好的提交示例**：

```
commit f5ea1fb
fix: 在/files API 中返回 extraction_method 字段

- 只修改了 app.py 一个文件
- 只添加了 3 行代码
- 提交信息清晰说明修改内容
```

**不好的提交示例**：

```
commit xxxxxxx
fix: 修复取消功能和翻译以及一些其他问题

- 修改了 8 个文件
- 包含功能修复、翻译、日志、UI 调整
- 提交信息模糊
```

**提交信息模板**：

```
<type>: <简短描述>

<详细描述（可选）>

<影响范围（可选）>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

**Type 类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 重构
- `chore`: 构建/工具/配置

---

### 📋 实践 8：错误预防检查

**规则**：在提交前检查常见错误。

**检查清单**：

```python
# 1. 方法调用检查
grep -rn "self\._.*(" src/**/*.py | grep -v "def "

# 2. 参数传递检查
grep -rn "extraction_method=" src/**/*.py

# 3. 返回值检查
grep -rn "return {" src/**/*.py | head -20

# 4. 异常处理检查
grep -rn "except.*as e:" src/**/*.py
```

---

## 六、推荐工作流

```
┌─────────────────────────────────────────────────────┐
│  1. 需求分析 (5-10 分钟)                             │
│     □ 明确要解决的具体问题（一句话）                │
│     □ 写下用户故事                                  │
│     □ 画出简单的流程图                              │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  2. 设计文档 (10-20 分钟)                            │
│     □ 创建或更新设计文档                            │
│     □ 定义接口和数据结构                          │
│     □ 列出测试用例                                  │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  3. 测试先行 (5-10 分钟)                             │
│     □ 编写测试用例                                  │
│     □ 运行测试（预期失败）                          │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  4. 增量实现 (迭代进行)                              │
│     □ 每次只实现一个小功能                          │
│     □ 立即运行测试验证                              │
│     □ 提交代码（原子化提交）                        │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  5. 集成验证                                        │
│     □ 端到端测试整个功能                            │
│     □ 检查前后端数据流                              │
│     □ 验证 UI 显示正确                              │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  6. 文档更新                                        │
│     □ 更新设计文档                                  │
│     □ 添加使用说明                                  │
│     □ 记录已知问题                                  │
└─────────────────────────────────────────────────────┘
```

---

## 七、检查清单模板

### 功能开发完成后自检

```markdown
## 效率自检清单

### 设计阶段
- [ ] 是否有明确的问题定义？（一句话）
- [ ] 是否有设计文档或流程图？
- [ ] 是否识别了所有受影响的模块？

### 实现阶段
- [ ] 是否先写测试？
- [ ] 每次提交是否足够小（<100 行）？
- [ ] 提交信息是否清晰？
- [ ] 命名是否一致？（grep 检查）

### 验证阶段
- [ ] 是否进行了端到端测试？
- [ ] 是否检查了浏览器缓存问题？
- [ ] 是否验证了前后端数据流？
- [ ] 调试日志是否充分？

### 复盘阶段
- [ ] 哪些地方可以做得更好？
- [ ] 哪些错误可以避免？
- [ ] 哪些模式可以复用？
```

### Bug 修复专用清单

```markdown
## Bug 修复清单

### 问题分析
- [ ] 是否复现了 Bug？
- [ ] 是否定位了根因？
- [ ] 是否分析了影响范围？

### 修复验证
- [ ] 是否添加了回归测试？
- [ ] 是否验证了相关功能？
- [ ] 是否更新了文档？

### 预防措施
- [ ] 是否有办法避免类似问题？
- [ ] 是否需要添加检查清单？
```

---

## 八、经验教训总结

### ✅ 保持的做法

1. **设计文档先行** - KG-LLM 融合功能证明了这一点
2. **测试及时跟进** - 避免回归问题
3. **小步提交** - 便于定位和回滚
4. **清晰的代码结构** - 枚举、策略模式

### ❌ 避免的做法

1. **一次性导入大量代码** - 图谱可视化导入 13000 行
2. **跨多层级修改无设计** - 取消功能 13 次提交
3. **忽略浏览器缓存** - JS 修改后不生效
4. **命名不一致** - `_is_cancelled` vs `_is_task_cancelled`
5. **缺少端到端测试** - 数据流断裂问题

### 📊 效率对比数据

| 指标 | 高效模式 | 低效模式 | 提升倍数 |
|------|---------|---------|---------|
| 提交次数 | 4 次 | 13 次 | 3.25x |
| 调试时间 | <30 分钟 | >4 小时 | 8x+ |
| 代码行数/提交 | <50 行 | 变动大 | - |
| 返工次数 | 1 次 | 5+ 次 | 5x+ |

---

## 九、快速参考卡片

### 开发前问自己

```
❓ 我要解决什么具体问题？
❓ 这个功能影响哪些文件？
❓ 我写测试了吗？
❓ 我写设计文档了吗？
❓ 这个提交够小吗？
```

### 调试时检查

```
🔍 Flask 服务器重新加载了吗？
🔍 浏览器缓存清除了吗？（Ctrl+F5）
🔍 有多个 Flask 进程吗？
🔍 日志输出了什么？
🔍 数据流哪里断了？
```

### 提交前检查

```
✓ 命名一致吗？（grep 检查）
✓ 提交信息清晰吗？
✓ 测试通过了吗？
✓ 日志充分吗？
```

---

## 十、持续改进

本文档会随着项目开发持续更新。每次遇到问题并解决后，请更新以下部分：

1. **新增低效案例** - 记录新遇到的问题
2. **更新检查清单** - 添加新的检查项
3. **优化工作流** - 改进推荐的工作流程

---

*最后更新：2026-03-02*
*基于 50+ commits 分析*
