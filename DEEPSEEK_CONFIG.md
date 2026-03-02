# DeepSeek V3.2 配置说明

## LLM 配置信息

| 配置项 | 值 |
|--------|-----|
| **API Provider** | DeepSeek (深度求索) |
| **模型** | DeepSeek-V3.2 |
| **API Key** | `sk-0b0a00b2d4cc4d7d8dce645d5db1b739` |
| **Base URL** | `https://api.deepseek.com` |
| **模型名称** | `deepseek-chat` |

## 配置文件修改

### 1. `config/settings.py`
```python
OPENAI_API_KEY = 'sk-0b0a00b2d4cc4d7d8dce645d5db1b739'
LLM_BACKEND = 'openai'
LLM_MODEL = 'deepseek-chat'
OPENAI_BASE_URL = 'https://api.deepseek.com'
```

### 2. `app.py`
已添加环境变量设置：
```python
os.environ["OPENAI_API_KEY"] = "sk-0b0a00b2d4cc4d7d8dce645d5db1b739"
os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL"] = "deepseek-chat"
```

## 启动应用

```bash
python app.py
```

## 测试 API 连接

```bash
python -c "
from src.nlp.llm_extractor import LLMExtractor
llm = LLMExtractor()
print(f'LLM 可用：{llm.is_available()}')
entities = llm.extract_entities('华为是一家中国科技公司')
print(f'实体：{[e[\"text\"] for e in entities]}')
"
```

## 功能说明

配置完成后，系统将使用 DeepSeek-V3.2 大模型进行：
- 中文命名实体识别（NER）
- 实体关系提取
- 知识三元组生成
- 增强知识图谱构建

相比纯 spaCy 提取，LLM 增强提取可以：
- 识别更多领域的专业实体
- 提取更复杂的语义关系
- 提高实体类型分类准确性
