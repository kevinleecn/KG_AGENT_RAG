"""
混合知识图谱问答引擎 - KG-RAG 融合增强版
结合知识图谱结构化检索与 LLM 深度推理能力
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from src.knowledge_graph.query_interface import QueryInterface
from src.nlp.llm_extractor import LLMExtractor
from src.qa.llm_reasoner import LLMReasoner
from config.settings import Config

logger = logging.getLogger(__name__)


class HybridKGQAEngine:
    """
    混合知识图谱问答引擎

    核心能力:
    1. 混合检索 - 结合知识图谱、向量、全文检索
    2. 神经符号推理 - LLM 驱动的图谱推理
    3. 可解释生成 - 基于证据链的答案生成
    """

    def __init__(self):
        self.query_interface = QueryInterface()
        self.llm_extractor = LLMExtractor()
        self.config = Config

        # 初始化 LLM 推理器
        self.llm_reasoner = LLMReasoner(
            api_key=Config.OPENAI_API_KEY,
            model=Config.LLM_MODEL,
            backend=Config.LLM_BACKEND,
            base_url=getattr(Config, 'OPENAI_BASE_URL', None)
        )

        self.llm_available = self.llm_reasoner.llm_client is not None

        if self.llm_available:
            logger.info(f"HybridKGQAEngine initialized with LLM: {Config.LLM_MODEL}")
        else:
            logger.warning("LLM reasoning disabled - falling back to basic KG query")

    def ask_question(self, question: str, document_id: Optional[str] = None,
                     chat_history: List[Dict] = None,
                     reasoning_depth: str = "standard") -> Dict[str, Any]:
        """
        回答用户问题 - 增强版

        Args:
            question: 用户问题
            document_id: 可选文档 ID 限制查询范围
            chat_history: 聊天历史上下文
            reasoning_depth: 推理深度 ("fast", "standard", "deep")

        Returns:
            包含答案、证据、推理链的完整响应
        """
        start_time = datetime.now()

        try:
            # 1. 深度意图理解（使用 LLM）
            intent_analysis = self._deep_intent_analysis(question, chat_history)
            logger.info(f"Intent analysis: {intent_analysis}")

            # 2. 混合检索策略
            retrieval_results = self._hybrid_retrieval(
                question=question,
                intent=intent_analysis,
                document_id=document_id,
                depth=reasoning_depth
            )

            # 3. LLM 神经符号推理
            reasoning_result = self._neuro_symbolic_reasoning(
                question=question,
                retrieval_results=retrieval_results,
                intent=intent_analysis,
                chat_history=chat_history
            )

            # 4. 生成可解释答案
            answer = self._generate_explainable_answer(
                question=question,
                reasoning_result=reasoning_result,
                retrieval_results=retrieval_results,
                intent=intent_analysis
            )

            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "answer": answer["answer_text"],
                "answer_type": answer["answer_type"],
                "confidence": answer["confidence"],
                "evidence": {
                    "graph_results": retrieval_results.get("graph_results", []),
                    "reasoning_chain": reasoning_result.get("reasoning_chain", []),
                    "sources": answer["sources"]
                },
                "metadata": {
                    "processing_time_seconds": processing_time,
                    "reasoning_depth": reasoning_depth,
                    "llm_used": self.llm_available,
                    "entities_found": len(intent_analysis.get("entities", [])),
                    "graph_results_count": len(retrieval_results.get("graph_results", []))
                }
            }

        except Exception as e:
            logger.error(f"Error in HybridKGQAEngine: {e}", exc_info=True)
            return {
                "success": False,
                "answer": f"处理问题时发生错误：{str(e)}",
                "error": str(e),
                "metadata": {"processing_time_seconds": 0}
            }

    def _deep_intent_analysis(self, question: str, chat_history: List[Dict] = None) -> Dict:
        """
        使用 LLM 进行深度意图分析

        相比基础版本，这个方法:
        1. 识别隐含的推理需求
        2. 检测多跳推理场景
        3. 识别假设性问题
        """
        intent = {
            'query_type': 'general',
            'entities': [],
            'entity_names': [],
            'relations': [],
            'requires_multi_hop': False,
            'requires_comparison': False,
            'requires_aggregation': False,
            'is_hypothetical': False,
            'reasoning_complexity': 'low',  # low, medium, high
            'suggested_approach': 'direct_lookup'
        }

        if not self.llm_available:
            # 回退到规则方法
            return self._rule_based_intent_analysis(question)

        try:
            system_prompt = """你是知识图谱问答的意图分析专家。分析用户问题并识别:

1. **实体**: 问题中提到的所有实体 (人名、组织、地点、概念等)
2. **关系意图**: 用户想了解的关系类型
3. **推理需求**:
   - direct_lookup: 直接查找单个事实
   - multi_hop: 需要多跳推理 (通过中间实体连接)
   - comparison: 需要比较多个实体
   - aggregation: 需要聚合统计
   - hypothetical: 假设性问题 (如果...会怎样)
4. **复杂度**: low/medium/high
5. **推荐方法**: 如何回答这个问题

以 JSON 格式返回，包含以下键:
- entities: 实体列表 [{name, type}]
- entity_names: 实体名称列表
- relations: 关系列表
- reasoning_type: direct_lookup|multi_hop|comparison|aggregation|hypothetical
- complexity: low|medium|high
- suggested_approach: 文字描述
"""

            prompt = f"""分析以下问题:

问题：{question}

{self._format_chat_history_for_context(chat_history) if chat_history else ''}

返回 JSON 分析:"""

            response = self.llm_reasoner._call_llm(prompt, system_prompt)

            # 解析 JSON 响应
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                llm_intent = json.loads(json_match.group())
                intent.update(llm_intent)

            # 标准化字段名
            if 'reasoning_type' in intent:
                if intent['reasoning_type'] == 'multi_hop':
                    intent['requires_multi_hop'] = True
                elif intent['reasoning_type'] == 'comparison':
                    intent['requires_comparison'] = True
                elif intent['reasoning_type'] == 'aggregation':
                    intent['requires_aggregation'] = True
                elif intent['reasoning_type'] == 'hypothetical':
                    intent['is_hypothetical'] = True

        except Exception as e:
            logger.warning(f"LLM intent analysis failed: {e}, falling back to rule-based")
            return self._rule_based_intent_analysis(question)

        return intent

    def _rule_based_intent_analysis(self, question: str) -> Dict:
        """规则式意图分析（回退方法）"""
        question_lower = question.lower()

        intent = {
            'query_type': 'general',
            'entities': [],
            'entity_names': [],
            'relations': [],
            'requires_multi_hop': False,
            'requires_comparison': False,
            'requires_aggregation': False,
            'is_hypothetical': False,
            'reasoning_complexity': 'low',
            'suggested_approach': 'direct_lookup'
        }

        # 检测假设性问题
        if any(word in question_lower for word in ['if ', 'what if', '假如', '如果', '假设']):
            intent['is_hypothetical'] = True
            intent['reasoning_complexity'] = 'high'

        # 检测比较性问题
        if any(word in question_lower for word in ['compare', 'vs', 'difference', '比较', '对比', '区别']):
            intent['requires_comparison'] = True

        # 检测多跳问题
        if any(word in question_lower for word in ['path', 'connection', 'how related', '关系', '关联', '路径']):
            intent['requires_multi_hop'] = True

        return intent

    def _hybrid_retrieval(self, question: str, intent: Dict,
                          document_id: Optional[str] = None,
                          depth: str = "standard") -> Dict:
        """
        混合检索策略

        根据意图分析结果选择最优检索策略:
        1. 直接查找 - 简单实体查询
        2. 子图检索 - 多跳推理准备
        3. 比较检索 - 为比较问题检索多个实体
        4. 聚合检索 - 为统计问题检索大量数据
        """
        results = {
            "graph_results": [],
            "subgraph": [],
            "comparison_data": [],
            "retrieval_strategy": "unknown"
        }

        try:
            # 策略 1: 假设性问题 - 检索相关背景知识
            if intent.get('is_hypothetical'):
                results["retrieval_strategy"] = "hypothetical_context"
                results["graph_results"] = self._retrieve_hypothetical_context(question, intent, document_id)

            # 策略 2: 多跳推理 - 检索子图
            elif intent.get('requires_multi_hop'):
                results["retrieval_strategy"] = "subgraph_expansion"
                results["graph_results"] = self._retrieve_for_multihop(question, intent, document_id)

            # 策略 3: 比较问题 - 检索对比实体
            elif intent.get('requires_comparison'):
                results["retrieval_strategy"] = "comparison"
                results["graph_results"] = self._retrieve_for_comparison(question, intent, document_id)

            # 策略 4: 直接查找 - 标准查询
            else:
                results["retrieval_strategy"] = "direct_lookup"
                results["graph_results"] = self._retrieve_direct(question, intent, document_id)

        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            # 回退到自然语言查询
            results["graph_results"] = self.query_interface.query_by_natural_language(question, document_id)
            results["retrieval_strategy"] = "fallback_natural_language"

        return results

    def _retrieve_direct(self, question: str, intent: Dict, document_id: Optional[str]) -> List:
        """直接查找检索"""
        # 使用 LLM 生成 Cypher 查询
        if self.llm_available and intent.get('entity_names'):
            cypher = self.llm_reasoner.generate_cypher_query(
                question,
                entity_types=intent.get('entity_types', []),
                relationship_types=intent.get('relationship_types', [])
            )
            if cypher:
                try:
                    results = self.query_interface.execute_custom_query(cypher)
                    if results:
                        return results
                except Exception as e:
                    logger.warning(f"LLM-generated Cypher failed: {e}")

        # 回退到自然语言查询
        return self.query_interface.query_by_natural_language(question, document_id)

    def _retrieve_for_multihop(self, question: str, intent: Dict, document_id: Optional[str]) -> List:
        """为多跳推理检索子图"""
        entity_names = intent.get('entity_names', [])[:5]

        if not entity_names:
            return self.query_interface.query_by_natural_language(question, document_id)

        # 生成子图扩展查询
        subgraph_query = self.llm_reasoner.expand_subgraph(
            seed_entities=entity_names,
            max_depth=2 if intent.get('reasoning_complexity') == 'low' else 3,
            max_nodes=50
        )

        if subgraph_query:
            try:
                return self.query_interface.execute_custom_query(subgraph_query)
            except Exception as e:
                logger.warning(f"Subgraph query failed: {e}")

        return self.query_interface.query_by_natural_language(question, document_id)

    def _retrieve_for_comparison(self, question: str, intent: Dict, document_id: Optional[str]) -> List:
        """为比较问题检索数据"""
        # 检索所有相关实体及其属性
        entity_names = intent.get('entity_names', [])
        results = []

        for entity in entity_names[:5]:  # 限制比较的实体数量
            entity_query = f"""
            MATCH (e:Entity WHERE e.name CONTAINS '{entity}')
            OPTIONAL MATCH (e)-[r]-(related:Entity)
            RETURN e, r, related
            LIMIT 20
            """
            try:
                entity_results = self.query_interface.execute_custom_query(entity_query)
                results.extend(entity_results)
            except Exception as e:
                logger.warning(f"Comparison query for '{entity}' failed: {e}")

        return results if results else self.query_interface.query_by_natural_language(question, document_id)

    def _retrieve_hypothetical_context(self, question: str, intent: Dict, document_id: Optional[str]) -> List:
        """为假设性问题检索背景知识"""
        # 检索相关的一般性知识，用于 LLM 进行假设推理
        return self.query_interface.query_by_natural_language(question, document_id)

    def _neuro_symbolic_reasoning(self, question: str, retrieval_results: Dict,
                                   intent: Dict, chat_history: List[Dict] = None) -> Dict:
        """
        神经符号推理 - LLM 驱动的知识图谱推理

        核心能力:
        1. 从检索结果中识别推理链
        2. 进行多跳推理
        3. 识别隐含关系
        """
        reasoning_result = {
            "reasoning_chain": [],
            "inferred_facts": [],
            "confidence": 0.0,
            "reasoning_type": "none"
        }

        graph_results = retrieval_results.get("graph_results", [])

        if not graph_results or not self.llm_available:
            return reasoning_result

        try:
            # 构建推理上下文
            context = self._build_reasoning_context(graph_results, intent)

            system_prompt = """你是知识图谱推理专家。基于检索到的图谱信息进行推理:

1. **识别推理链**: 找出实体之间的逻辑连接
2. **多跳推理**: 如果涉及多跳，明确指出推理路径
3. **隐含关系**: 识别未直接陈述但可推导的关系
4. **置信度**: 评估推理的置信度 (0-1)

输出格式:
{
    "reasoning_chain": ["步骤 1", "步骤 2", ...],
    "inferred_facts": [{"fact": "...", "confidence": 0.x}, ...],
    "reasoning_type": "direct|multi_hop|comparison|aggregation",
    "confidence": 0.x
}
"""

            prompt = f"""基于以下知识图谱信息进行推理:

{context}

用户问题：{question}

推理结果 (JSON 格式):"""

            response = self.llm_reasoner._call_llm(prompt, system_prompt)

            # 解析推理结果
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                reasoning = json.loads(json_match.group())
                reasoning_result.update(reasoning)

        except Exception as e:
            logger.warning(f"Neuro-symbolic reasoning failed: {e}")

        return reasoning_result

    def _build_reasoning_context(self, graph_results: List, intent: Dict) -> str:
        """构建推理上下文"""
        if not graph_results:
            return "(无图谱数据)"

        context_parts = []

        # 整理实体信息
        entities = []
        relations = []

        for result in graph_results[:20]:  # 限制上下文大小
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, dict):
                        if 'properties' in value:
                            props = value.get('properties', {})
                            if 'name' in props:
                                entities.append(f"- {props['name']} (类型：{props.get('type', '未知')})")
                        if 'type' in value and 'start' in value:
                            rel_type = value.get('type', 'RELATIONSHIP')
                            relations.append(f"- 关系：{rel_type}")

        if entities:
            context_parts.append("实体:\n" + "\n".join(entities[:15]))
        if relations:
            context_parts.append("关系:\n" + "\n".join(relations[:15]))

        return "\n\n".join(context_parts) if context_parts else "(无法解析图谱数据)"

    def _generate_explainable_answer(self, question: str, reasoning_result: Dict,
                                      retrieval_results: Dict, intent: Dict) -> Dict:
        """生成可解释的答案"""

        if not self.llm_available:
            return self._generate_simple_answer(question, retrieval_results)

        try:
            system_prompt = """你是知识图谱智能助手。基于图谱数据和推理结果回答问题。

回答要求:
1. **准确性**: 严格基于图谱信息回答
2. **可解释性**: 说明推理过程和依据
3. **结构化**: 使用清晰的格式 (分点、列表)
4. **诚实**: 信息不足时明确说明
5. **中文**: 始终使用中文回答
"""

            # 准备上下文
            context = self._build_answer_context(retrieval_results, reasoning_result)

            prompt = f"""{system_prompt}

问题：{question}

图谱信息:
{context}

推理链:
{chr(10).join(reasoning_result.get('reasoning_chain', ['无显式推理链']))}

请给出准确、有依据的答案:"""

            answer_text = self.llm_reasoner._call_llm(prompt, system_prompt)

            # 评估答案置信度
            confidence = reasoning_result.get('confidence', 0.5)
            if not retrieval_results.get('graph_results'):
                confidence = 0.3
                answer_text = "抱歉，知识图谱中没有足够的信息回答这个问题。" + answer_text

            # 提取来源
            sources = self._extract_sources(retrieval_results.get('graph_results', []))

            return {
                "answer_text": answer_text,
                "answer_type": reasoning_result.get('reasoning_type', 'direct'),
                "confidence": confidence,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                "answer_text": f"生成答案时出错：{str(e)}",
                "answer_type": "error",
                "confidence": 0.0,
                "sources": []
            }

    def _generate_simple_answer(self, question: str, retrieval_results: Dict) -> Dict:
        """简单答案生成（LLM 不可用时）"""
        graph_results = retrieval_results.get('graph_results', [])

        if not graph_results:
            return {
                "answer_text": f"抱歉，知识图谱中没有找到与'{question}'相关的信息。",
                "answer_type": "no_data",
                "confidence": 0.0,
                "sources": []
            }

        count = len(graph_results)
        return {
            "answer_text": f"在知识图谱中找到 {count} 个相关结果。",
            "answer_type": "direct",
            "confidence": 0.5,
            "sources": self._extract_sources(graph_results)
        }

    def _build_answer_context(self, retrieval_results: Dict, reasoning_result: Dict) -> str:
        """构建答案生成的上下文"""
        parts = []

        # 图谱数据
        graph_results = retrieval_results.get('graph_results', [])
        if graph_results:
            formatted = self.llm_reasoner._format_query_results(graph_results)
            parts.append(f"知识图谱数据:\n{formatted}")

        # 推理结果
        inferred = reasoning_result.get('inferred_facts', [])
        if inferred:
            inferred_text = "\n".join([f"- {f['fact']} (置信度：{f['confidence']})" for f in inferred[:5]])
            parts.append(f"推理结果:\n{inferred_text}")

        return "\n\n".join(parts) if parts else "(无相关图谱数据)"

    def _extract_sources(self, graph_results: List) -> List[Dict]:
        """从图谱结果中提取来源"""
        sources = []
        seen_docs = set()

        for result in graph_results[:10]:
            if isinstance(result, dict):
                doc = result.get('source_document') or result.get('document') or result.get('source')
                if doc and doc not in seen_docs:
                    seen_docs.add(doc)
                    sources.append({
                        'type': 'knowledge_graph',
                        'document': doc,
                        'confidence': result.get('confidence', 0.5)
                    })

        return sources

    def _format_chat_history_for_context(self, chat_history: List[Dict]) -> str:
        """格式化聊天历史为上下文"""
        if not chat_history:
            return ""

        recent = chat_history[-3:]  # 最近 3 轮
        lines = []
        for msg in recent:
            role = "用户" if msg.get('role') == 'user' else "助手"
            content = msg.get('content', '')[:100]
            lines.append(f"{role}: {content}")

        return f"\n对话历史:\n{chr(10).join(lines)}"
