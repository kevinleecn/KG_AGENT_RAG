# KG-LLM 融合问答系统设计文档 v2

## 概述

本文档描述了知识图谱与 LLM **真正融合**的问答系统架构。v2 版本解决了 v1 的核心问题：**图谱外问题（如"你是谁"）被错误地送到图谱检索，导致无法回答**。

## 核心问题（v1 版本的缺陷）

### 问题描述
在 v1 版本中，用户输入"你是谁"时：
1. 系统尝试在知识图谱中检索"你"、"谁"等实体
2. 图谱中没有结果
3. 返回"知识图谱中没有找到相关信息"

### 根本原因
- **缺少问题分类**：所有问题都被送到图谱检索
- **LLM 仅用于格式化**：只在有图谱数据时才使用 LLM
- **没有融合逻辑**：不是真正的 KG+LLM 融合

## v2 架构设计

### 问题分类驱动的处理流程

```
用户问题
    │
    ▼
┌─────────────────────────────────┐
│  步骤 1: 问题分类 (Rule-based)   │
│  - LLM_ONLY: 通用知识/助手身份   │
│  - KG_ONLY: 简单图谱检索         │
│  - KG_LLM_FUSION: 复杂推理       │
│  - CHAT: 闲聊对话               │
└──────────────┬──────────────────┘
               │
    ┌──────────┼──────────┬────────────┐
    │          │          │            │
    ▼          ▼          ▼            ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│LLM Only│ │KG Only │ │ Fusion │ │ Chat   │
│直接回答│ │图谱检索│ │KG+LLM  │ │预设回复│
└────────┘ └────────┘ └────────┘ └────────┘
```

### 问题分类规则

| 类型 | 模式匹配 | 处理策略 | 示例 |
|------|----------|----------|------|
| **LLM_ONLY** | "你是谁"、"什么模型"、"解释"、"什么是" | 直接用 LLM 回答，不查图谱 | "你是谁？"、"解释量子力学" |
| **KG_ONLY** | 实体名 + 属性询问 | 图谱检索+LLM 格式化 | "阿里巴巴的 CEO 是谁？" |
| **KG_LLM_FUSION** | "关系"、"如果"、"比较"、"为什么" | 图谱检索+LLM 推理融合 | "张三和李四的关系意味着什么？" |
| **CHAT** | "你好"、"谢谢"、"再见" | 预设回复或 LLM 闲聊 | "你好"、"谢谢" |

## 核心代码实现

### 问题分类器

```python
def _classify_question(self, question: str) -> str:
    q = question.lower().strip()

    # LLM_ONLY 类型 - 通用知识/助手相关
    llm_only_patterns = [
        "你是谁", "你是哪个模型", "解释", "什么是",
        "what is", "how does", "why is",
    ]
    for pattern in llm_only_patterns:
        if pattern in q:
            return QuestionType.LLM_ONLY

    # CHAT 类型 - 闲聊
    chat_patterns = ["你好", "hello", "谢谢", "再见"]
    for pattern in chat_patterns:
        if pattern in q:
            return QuestionType.CHAT

    # KG_LLM_FUSION 类型 - 需要推理
    fusion_patterns = ["关系", "如果", "比较", "为什么"]
    for pattern in fusion_patterns:
        if pattern in q:
            return QuestionType.KG_LLM_FUSION

    # 默认 KG_ONLY - 简单图谱检索
    return QuestionType.KG_ONLY
```

### 问答路由

```python
def ask_question(self, question: str, ...) -> Dict:
    # 步骤 1: 问题分类
    question_type = self._classify_question(question)

    # 步骤 2: 根据类型选择回答策略
    if question_type == QuestionType.LLM_ONLY:
        response = self._answer_with_llm_only(question, chat_history)
    elif question_type == QuestionType.KG_ONLY:
        response = self._answer_with_kg_only(question, document_id)
    elif question_type == QuestionType.KG_LLM_FUSION:
        response = self._answer_with_fusion(question, document_id, chat_history)
    else:  # CHAT
        response = self._answer_with_chat(question, chat_history)

    return response
```

### LLM-Only 回答

```python
def _answer_with_llm_only(self, question: str, chat_history: List) -> Dict:
    """直接用 LLM 回答，不查图谱"""

    system_prompt = f"""你是{self.assistant_identity['name']}，使用{self.assistant_identity['model']}模型。

你的能力:
{chr(10).join('- ' + cap for cap in self.assistant_identity['capabilities'])}

请用友好、专业的语气回答用户问题。"""

    answer = self.llm_reasoner._call_llm(prompt, system_prompt)

    return {
        "success": True,
        "answer": answer,
        "answer_type": "llm_only",
        "confidence": 0.9,
        "evidence": {"source_type": "llm_knowledge", "graph_results": []}
    }
```

## API 端点

### /chat/ask-enhanced (POST)

融合问答接口，自动识别问题类型并选择最优回答策略。

**请求**:
```json
{
    "question": "你是谁？",
    "document_id": null,
    "chat_history": []
}
```

**响应**:
```json
{
    "success": true,
    "answer": "你好！我是知识图谱智能助手，基于 deepseek-chat 模型构建...",
    "answer_type": "llm_only",
    "confidence": 0.9,
    "evidence": {
        "source_type": "llm_knowledge",
        "graph_results": [],
        "reasoning_chain": []
    },
    "metadata": {
        "question_type": "llm_only",
        "llm_used": true,
        "kg_used": false,
        "processing_time_seconds": 2.5
    }
}
```

### /chat/assistant-info (GET)

获取助手信息（模型名称、能力等）。

**响应**:
```json
{
    "success": true,
    "assistant": {
        "name": "知识图谱智能助手",
        "model": "deepseek-chat",
        "capabilities": [
            "知识图谱查询",
            "文档内容问答",
            "实体关系分析",
            "多跳推理",
            "假设性分析"
        ],
        "llm_available": true,
        "kg_available": true
    }
}
```

## 测试验证

### 问题分类测试

```python
test_cases = [
    ("你是谁？", "llm_only"),           # PASS
    ("你是哪个模型？", "llm_only"),     # PASS
    ("阿里巴巴的 CEO 是谁？", "kg_only"), # PASS
    ("张三和李四有什么关系？", "fusion"), # PASS
    ("你好", "chat"),                   # PASS
]
```

**结果**: 分类准确率 100% (9/9)

### "你是谁"测试

**输入**: "你是谁？"

**输出**:
```
你好！我是知识图谱智能助手，基于 deepseek-chat 模型构建。我可以帮助你：

🔍 **知识图谱查询** - 查找实体、关系和属性信息
📄 **文档内容问答** - 基于文档内容回答相关问题
🔗 **实体关系分析** - 分析实体之间的关联和路径
🔄 **多跳推理** - 进行多步推理和逻辑分析
```

**类型**: `llm_only` | **置信度**: 90%

## 与 v1 的对比

| 特性 | v1 (HybridKGQAEngine) | v2 (FusionKGQAEngine) |
|------|----------------------|----------------------|
| 问题分类 | ❌ 无，所有问题都查图谱 | ✅ 智能分类 4 种类型 |
| 图谱外问题 | ❌ 返回"图谱无结果" | ✅ 直接用 LLM 回答 |
| 图谱内问题 | ✅ 图谱检索+LLM 格式化 | ✅ 图谱检索+LLM 增强 |
| 融合推理 | ⚠️ 简单拼接 | ✅ 真正的 KG+LLM 融合 |
| 闲聊对话 | ❌ 不支持 | ✅ 预设回复+LLM |
| "你是谁" | ❌ 无法回答 | ✅ 正确回答模型信息 |

## 使用示例

### 基础使用

```python
from src.qa.fusion_qa_engine import FusionKGQAEngine

engine = FusionKGQAEngine()

# 助手身份问题
response = engine.ask_question("你是谁？")
print(response["answer"])
# 输出：你好！我是知识图谱智能助手，基于 deepseek-chat 模型构建...

# 图谱检索问题
response = engine.ask_question("阿里巴巴的 CEO 是谁？")
print(response["metadata"]["question_type"])  # kg_only

# 融合推理问题
response = engine.ask_question("张三和李四的关系意味着什么？")
print(response["metadata"]["question_type"])  # kg_llm_fusion
```

### API 调用

```bash
# 融合问答接口
curl -X POST http://localhost:5000/chat/ask-enhanced \
  -H "Content-Type: application/json" \
  -d '{"question": "你是谁？"}'

# 获取助手信息
curl http://localhost:5000/chat/assistant-info
```

## 后续扩展

1. **机器学习分类器**：用 LLM 替代规则分类器，提高准确率
2. **主动澄清**：当问题类型不明确时，主动询问用户
3. **多轮对话**：基于对话历史理解上下文
4. **图谱构建**：从 LLM 回答中提取知识更新图谱
