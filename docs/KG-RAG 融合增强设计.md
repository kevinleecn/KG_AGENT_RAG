# KG-RAG 融合增强问答系统设计文档

## 概述

本文档描述了知识图谱与 LLM 融合的增强问答系统架构，实现从"基于图谱检索"到"神经符号推理"的升级。

## 架构设计

### 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户问题                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 混合检索层 (Hybrid Retrieval)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │
│  │ 图谱检索    │  │ 向量检索    │  │ 全文检索        │     │
│  │ Neo4j       │  │ Embedding   │  │ BM25            │     │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘     │
│         └────────────────┴──────────────────┘               │
│                    检索结果融合                              │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: LLM 推理层 (Neuro-Symbolic Reasoning)              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ 子图推理        │  │ 多跳推理        │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           └──────────┬─────────┘                           │
│              LLM 结构化推理输出                              │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: 答案生成层 (Augmented Generation)                 │
│  RAG Generator (LLM + 检索证据 + 推理链)                     │
└─────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. HybridKGQAEngine (`src/qa/hybrid_qa_engine.py`)

主问答引擎，提供以下能力：

| 方法 | 功能 |
|------|------|
| `ask_question()` | 统一入口，返回完整响应 |
| `_deep_intent_analysis()` | LLM 深度意图分析 |
| `_hybrid_retrieval()` | 混合检索策略 |
| `_neuro_symbolic_reasoning()` | 神经符号推理 |
| `_generate_explainable_answer()` | 可解释答案生成 |

### 2. LLMReasoner 增强 (`src/qa/llm_reasoner.py`)

新增推理能力：

| 方法 | 功能 |
|------|------|
| `perform_multihop_reasoning()` | 多跳推理 |
| `answer_hypothetical_question()` | 假设性推理 |
| `compare_entities()` | 实体比较分析 |
| `_analyze_paths_with_llm()` | 路径分析 |

## 使用示例

### 基础问答

```python
from src.qa.hybrid_qa_engine import HybridKGQAEngine

engine = HybridKGQAEngine()

# 简单问题
response = engine.ask_question(
    question="阿里巴巴的 CEO 是谁？",
    document_id=None,
    reasoning_depth="standard"
)

print(response["answer"])
print(f"置信度：{response['confidence']}")
print(f"来源：{response['evidence']['sources']}")
```

### 多跳推理

```python
# 需要多跳推理的问题
response = engine.ask_question(
    question="张三和李四之间有什么关联？",
    reasoning_depth="deep"  # 使用深度推理
)

# 响应包含推理链
print(response["evidence"]["reasoning_chain"])
# 输出：["张三工作在阿里巴巴", "李四创建于阿里巴巴", ...]
```

### 假设性问题

```python
# 假设性问题
response = engine.ask_question(
    question="如果阿里巴巴收购了腾讯，会有什么影响？",
    reasoning_depth="deep"
)

print(response["answer"])
# 输出包含直接影响、间接影响、不确定性分析
```

### 实体比较

```python
from src.qa.llm_reasoner import LLMReasoner

reasoner = LLMReasoner()

# 比较两个实体
result = reasoner.compare_entities(
    entities=["阿里巴巴", "腾讯"],
    comparison_aspects=["成立时间", "总部地点", "主营业务"],
    context={}  # 可选的图谱上下文
)

print(result["comparison_table"])
print(result["key_differences"])
```

## 推理深度配置

| depth | 适用场景 | 响应时间 |
|-------|----------|----------|
| `fast` | 简单事实查询 | <1s |
| `standard` | 一般问题 | 1-3s |
| `deep` | 复杂推理、多跳、假设性 | 3-10s |

## 响应格式

```json
{
  "success": true,
  "answer": "答案文本",
  "answer_type": "multi_hop",
  "confidence": 0.85,
  "evidence": {
    "graph_results": [...],
    "reasoning_chain": ["步骤 1", "步骤 2"],
    "sources": [{"document": "...", "confidence": 0.9}]
  },
  "metadata": {
    "processing_time_seconds": 2.5,
    "reasoning_depth": "standard",
    "llm_used": true,
    "entities_found": 3,
    "graph_results_count": 5
  }
}
```

## 集成到 Flask 应用

在 `app.py` 中添加新的 API 端点：

```python
from src.qa.hybrid_qa_engine import HybridKGQAEngine

hybrid_qa_engine = HybridKGQAEngine()

@app.route('/chat/ask-enhanced', methods=['POST'])
def chat_ask_enhanced():
    """增强版问答接口（支持深度推理）"""
    data = request.get_json()
    question = data.get('question')
    document_id = data.get('document_id')
    chat_history = data.get('chat_history', [])
    reasoning_depth = data.get('reasoning_depth', 'standard')

    response = hybrid_qa_engine.ask_question(
        question=question,
        document_id=document_id,
        chat_history=chat_history,
        reasoning_depth=reasoning_depth
    )

    return jsonify(response)
```

## 性能优化建议

1. **缓存推理结果**: 对相同问题的推理结果进行缓存
2. **异步处理**: 对 `deep` 深度的推理使用异步处理
3. **批处理**: 批量执行图谱查询减少往返次数
4. **上下文截断**: 限制 LLM 上下文大小避免 token 超限

## 后续扩展

- [ ] 向量检索集成 (FAISS/Chroma)
- [ ] 对话状态追踪
- [ ] 多文档跨文档推理
- [ ] 图谱动态更新与增量学习
