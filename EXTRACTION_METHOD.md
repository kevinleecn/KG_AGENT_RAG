# 知识图谱解析工具选择功能

## 功能概述

现在用户可以在 Web 界面上选择两种知识提取方法之一来解析文档：

### 1. spaCy（默认）
- **原理**: 使用 Python spaCy NLP 库进行本地实体识别和关系提取
- **优点**:
  - 快速（无需网络请求）
  - 本地运行（无 API 费用）
  - 适合大量文档快速处理
- **缺点**:
  - 实体识别准确性受限于预训练模型
  - 关系提取基于简单规则

### 2. LLM API (DeepSeek-V3.2)
- **原理**: 使用 DeepSeek-V3.2 大语言模型进行智能知识提取
- **优点**:
  - 更高的实体识别准确性
  - 能理解复杂语义关系
  - 支持更多领域的专业实体
- **缺点**:
  - 需要网络连接
  - 处理速度较慢
  - 需要 API Key（有调用成本）

## 配置信息

```python
# config/settings.py
OPENAI_API_KEY = 'sk-0b0a00b2d4cc4d7d8dce645d5db1b739'
LLM_BACKEND = 'openai'
LLM_MODEL = 'deepseek-chat'  # DeepSeek-V3.2
OPENAI_BASE_URL = 'https://api.deepseek.com'
```

## 使用方法

1. **启动应用**
   ```bash
   python app.py
   ```

2. **访问界面**
   打开浏览器访问：http://localhost:5000

3. **选择提取方法**
   在"Uploaded Files"卡片顶部，使用下拉选择器选择：
   - **spaCy** (默认) - 快速本地提取
   - **LLM API** - 高精度云端提取

4. **解析文档**
   - 上传文档后，点击"Parse"按钮开始解析
   - 系统会使用当前选择的方法进行知识提取
   - 选择的提取方法会保存在浏览器本地存储中，下次访问时自动恢复

## 技术实现

### 前端修改

**templates/index.html**
- 添加提取方法选择器下拉框
- 支持 localStorage 保存用户偏好
- 解析请求时传递选择的提取方法

**static/js/main.js**
- 添加 `currentExtractionMethod` 变量跟踪当前选择
- 修改 parse-file-btn 点击事件，发送选择的提取方法

### 后端修改

**app.py**
- `/parse/async/<filename>` 支持 `extraction_method` 参数
- `/graph/extract/<filename>` 支持 `extraction_method` 参数

**src/parsing_manager.py**
- `parse_file_async()` 添加 `extraction_method` 参数
- `_parse_file_worker()` 传递提取方法
- `extract_knowledge()` 根据参数动态创建 KnowledgeExtractor

## 对比测试结果

测试文本：`"华为是一家中国科技公司，成立于 1987 年，总部位于深圳"`

| 方法 | 实体数 | 识别结果 |
|------|--------|----------|
| spaCy | 3 | 中国科技公司 (ORG), 1987 年 (DATE), 深圳 (LOC) |
| LLM API | 5 | 华为 (ORG), 中国 (LOC), 科技公司 (ORG), 1987 年 (DATE), 深圳 (LOC) |

**结论**: LLM API 能识别更多实体，准确性更高。

## 文件清单

修改的文件：
- `config/settings.py` - LLM 配置
- `app.py` - API 端点支持提取方法参数
- `src/parsing_manager.py` - 解析管理器支持提取方法
- `src/nlp/llm_extractor.py` - LLM 提取器支持自定义 base_url
- `templates/index.html` - UI 选择器
- `static/js/main.js` - 前端逻辑
