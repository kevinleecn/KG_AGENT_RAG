# Knowledge Graph Agent Demo

> 基于 LLM + 知识图谱的智能问答系统

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目简介

Knowledge Graph Agent Demo 是一个智能问答系统，结合了大型语言模型（LLM）和知识图谱（Neo4j）的优势。用户可以上传文档（PDF、DOCX、PPTX、TXT），系统自动提取知识构建图谱，并通过 Web 界面提供配置管理和智能问答服务。

**项目负责人**: Kevin Lee

## 核心功能

### 1. 文档上传与解析
- 支持多种格式：PDF、DOCX、PPTX、TXT
- 自动文本提取和预处理
- 支持批量上传和进度追踪
- 支持取消正在进行的解析任务

### 2. 知识图谱构建
- **双模式提取**: 支持 spaCy（快速）和 LLM（高精度）两种知识提取方法
- 实体识别与关系抽取
- 自动构建 Neo4j 知识图谱
- 可视化图谱浏览

### 3. 智能问答系统
- **四种问答模式**:
  - `llm_only` - 纯 LLM 回答（通用知识、助手身份问题）
  - `kg_only` - 纯知识图谱查询（简单事实检索）
  - `kg_llm_fusion` - KG-LLM 融合推理（复杂推理问题）
  - `chat` - 闲聊模式
- **意图识别**: 自动识别用户意图，选择最优回答策略
- **用户控制**: 支持用户明确要求"不要用知识图谱，用 LLM 回答"

### 4. 配置管理
- **Web 界面配置**: 通过/settings 页面配置 LLM API 和 Neo4j
- **加密存储**: 敏感信息（API Key、密码）使用 AES 加密存储
- **连接测试**: 一键测试 LLM API 和 Neo4j 连接

## 工作原理

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户上传文档                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    文档解析层 (Parser)                           │
│           PDF/DOCX/PPTX/TXT → 纯文本                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  知识提取层 (Extractor)                          │
│     ┌─────────────┐         ┌─────────────┐                     │
│     │   spaCy     │         │  LLM API    │                     │
│     │  (快速模式) │         │  (高精度)   │                     │
│     └─────────────┘         └─────────────┘                     │
│              ↓                    ↓                             │
│        实体识别 + 关系抽取                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│               知识图谱存储 (Neo4j)                               │
│         节点 (实体) + 边 (关系) → 图结构                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  智能问答引擎 (QA Engine)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 问题分类器                                │  │
│  │  "你是谁？" → llm_only                                   │  │
│  │  "阿里巴巴 CEO 是谁？" → kg_only                          │  │
│  │  "A 和 B 有什么关系？" → kg_llm_fusion                    │  │
│  │  "你好" → chat                                           │  │
│  │  "不要用知识图谱..." → llm_only                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │  LLM Only   │  │  KG Only    │  │  KG-LLM Fusion      │    │
│  │  直接回答   │  │  图谱查询   │  │  查询 + 推理增强      │    │
│  └─────────────┘  └─────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        返回答案                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 问题分类策略

| 问题类型 | 识别模式 | 回答策略 |
|---------|---------|---------|
| **LLM_ONLY** | "你是谁"、"不要用知识图谱"、通用知识 | 直接使用 LLM 回答 |
| **KG_ONLY** | "X 的 Y 是什么"、简单事实查询 | 仅查询知识图谱 |
| **KG_LLM_FUSION** | "关系"、"如果"、"比较"、复杂推理 | 图谱查询 + LLM 推理增强 |
| **CHAT** | "你好"、"谢谢"、闲聊 | 闲聊回复 |

## 系统架构

```
kg_agent_demo/
├── app.py                          # Flask 主应用
├── config/
│   ├── settings.py                 # 系统配置
│   └── config_manager.py           # 配置管理器（加密存储）
├── src/
│   ├── qa/
│   │   └── fusion_qa_engine.py    # 融合问答引擎
│   ├── nlp/
│   │   ├── knowledge_extractor.py  # 知识提取器
│   │   ├── spacy_extractor.py      # spaCy 提取器
│   │   └── llm_extractor.py        # LLM 提取器
│   ├── knowledge_graph/
│   │   └── neo4j_adapter.py        # Neo4j 适配器
│   ├── document_parser/
│   │   ├── pdf_parser.py           # PDF 解析器
│   │   ├── docx_parser.py          # Word 解析器
│   │   └── ...                     # 其他解析器
│   └── parsing_manager.py          # 解析管理器
├── static/
│   ├── js/
│   │   ├── main.js                 # 主前端逻辑
│   │   └── progress.js             # 进度追踪
│   └── css/
│       └── style.css               # 样式
├── templates/
│   ├── base.html                   # 基础模板
│   ├── index.html                  # 主页面（上传）
│   ├── chat.html                   # 聊天页面
│   ├── graph.html                  # 图谱可视化
│   └── settings.html               # 配置页面
├── docs/                           # 设计文档
├── .env.example                    # 环境变量模板
└── requirements.txt                # 依赖
```

## 安装说明

### 环境要求

- Python 3.8 或更高版本
- Neo4j 4.4+ (本地或云端)
- LLM API Key (DeepSeek/OpenAI/Ollama 等)

### 1. 克隆项目

```bash
git clone <repository-url>
cd kg_agent_demo
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**如果需要中文 spaCy 模型**:
```bash
python -m spacy download zh_core_web_sm
```

### 4. 配置应用

有两种配置方式（任选其一）：

#### 方式一：Web 界面配置（推荐）

1. 启动应用后访问 http://localhost:5000/settings
2. 填写 LLM API 和 Neo4j 配置
3. 点击"保存配置"
4. 点击"测试连接"验证配置

#### 方式二：环境变量配置

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置：

```bash
# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password

# LLM API 配置 (以 DeepSeek 为例)
LLM_BACKEND=openai
LLM_MODEL=deepseek-chat
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.deepseek.com
```

### 5. 启动应用

```bash
python app.py
```

访问 http://localhost:5000

## 配置说明

### Web 界面配置

访问 **/settings** 页面配置以下参数：

| 配置项 | 说明 | 示例 |
|-------|------|------|
| **后端类型** | LLM 后端类型 | OpenAI / Ollama / Anthropic |
| **API Base URL** | LLM API 地址 | https://api.deepseek.com |
| **API Key** | LLM API 密钥（加密存储） | sk-... |
| **模型名称** | 使用的模型 | deepseek-chat |
| **Neo4j URI** | Neo4j 连接地址 | bolt://localhost:7687 |
| **Neo4j 用户名** | Neo4j 用户名 | neo4j |
| **Neo4j 密码** | Neo4j 密码（加密存储） | your-password |

### 获取 LLM API Key

#### DeepSeek (推荐)
1. 访问 https://platform.deepseek.com
2. 注册/登录账号
3. 在控制台创建 API Key
4. Base URL: `https://api.deepseek.com`

#### OpenAI
1. 访问 https://platform.openai.com
2. 创建 API Key
3. Base URL: `https://api.openai.com/v1`

#### Ollama (本地部署)
1. 访问 https://ollama.ai 下载安装
2. 拉取模型：`ollama pull llama2`
3. Base URL: `http://localhost:11434`
4. API Key: 任意值（本地部署不需要）

### Neo4j 配置

#### 本地安装
1. 访问 https://neo4j.com/download 下载
2. 安装后启动服务
3. 默认端口：7687 (Bolt), 7474 (Browser)
4. 初始密码：neo4j/neo4j（首次登录需修改）

#### Neo4j Aura (云端)
1. 访问 https://aura.neo4j.com
2. 创建免费实例
3. 获取连接字符串和密码

## 使用指南

### 1. 首次配置

1. 访问 http://localhost:5000/settings
2. 填写 LLM API 和 Neo4j 配置
3. 点击"测试连接"验证
4. 点击"保存配置"

### 2. 上传文档

1. 点击"上传文件"按钮
2. 选择文件（支持多选）
3. 选择知识提取方法：
   - **spaCy**: 快速，适合大批量
   - **LLM API**: 高精度，适合复杂文档
4. 等待解析完成

### 3. 浏览知识图谱

1. 点击"图谱视图"
2. 查看实体和关系网络
3. 支持缩放、拖拽、搜索

### 4. 智能问答

在聊天窗口输入问题，系统自动识别类型并回答：

**示例问题**:
- "你是谁？" → 自动使用 LLM 回答
- "阿里巴巴的 CEO 是谁？" → 自动查询知识图谱
- "张三和李四有什么关系？" → KG-LLM 融合推理
- "不要用知识图谱，用你自己的知识回答" → 强制使用 LLM

## API 端点

### 页面路由

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/` | GET | 主页面（上传） |
| `/chat` | GET | 聊天页面 |
| `/graph` | GET | 图谱页面 |
| `/settings` | GET | 配置页面 |

### 配置管理 API

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/config` | GET | 获取当前配置 |
| `/api/config` | POST | 保存配置 |
| `/api/config/validate` | POST | 验证配置（测试连接） |
| `/api/config/reset` | POST | 恢复默认配置 |

### 文件管理

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/upload` | POST | 上传文件 |
| `/files` | GET | 获取文件列表 |
| `/files/<filename>` | DELETE | 删除文件 |

### 解析任务

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/parse/async/<filename>` | POST | 异步解析 |
| `/progress/<task_id>` | GET | 获取进度 |
| `/parse/cancel/<task_id>` | POST | 取消任务 |

### 问答

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/chat/ask-enhanced` | POST | 融合问答 |

## 安全说明

### 敏感信息保护

1. **加密存储**: API Key 和密码使用 AES 加密存储
2. **文件保护**: 配置文件和加密密钥已加入 `.gitignore`
3. **不要提交**: 请勿将 `.env`、`config/user_config.json`、`config/.encryption_key` 提交到代码仓库

### 生产环境部署

1. **设置强 SECRET_KEY**:
   ```bash
   export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```

2. **启用 HTTPS**

3. **配置 CORS**:
   ```python
   app.config['CORS_ORIGINS'] = ['https://yourdomain.com']
   ```

4. **使用环境变量**:
   - 不要硬编码敏感信息
   - 使用 `.env` 文件并加入 `.gitignore`

## 常见问题

### 1. 配置保存后不生效

**解决**: 重启应用或刷新配置页面

### 2. 上传文件失败

**检查**:
- 文件大小不超过 16MB
- 文件格式支持（.txt, .docx, .pdf, .pptx）
- 查看服务器日志

### 3. Neo4j 连接失败

**检查**:
- Neo4j 服务是否运行
- URI、用户名、密码是否正确
- 防火墙设置

### 4. LLM API 调用失败

**检查**:
- API Key 是否正确
- 网络连接
- API 余额/配额

### 5. 中文乱码

**解决**:
- 确保安装中文 spaCy 模型
- 检查文件编码（推荐 UTF-8）

## 开发说明

### 运行测试

```bash
pytest
pytest --cov=src  # 带覆盖率
```

### 代码风格

- 遵循 PEP 8 规范
- 使用类型提示
- 函数不超过 50 行
- 文件不超过 800 行

## 更新日志

### v1.0.0 (2026-03-03)
- ✅ 基础文件上传功能
- ✅ 多格式文档解析
- ✅ 双模式知识提取（spaCy/LLM）
- ✅ KG-LLM 融合问答引擎
- ✅ 意图识别（支持用户强制 LLM 回答）
- ✅ 异步任务处理与取消
- ✅ 知识图谱可视化
- ✅ 文件删除功能
- ✅ Web 配置管理（加密存储）

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- **项目负责人**: Kevin Lee
- **Email**: [your-email@example.com]
- **GitHub**: [your-github-username]

## 致谢

- Flask 团队
- Neo4j 团队
- spaCy 团队
- DeepSeek/OpenAI
- 所有开源贡献者

---

<div align="center">

**Knowledge Graph Agent Demo** | Made with ❤️ by Kevin Lee

</div>
