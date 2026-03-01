"""
知识图谱问答引擎
支持两种问答模式：图查询和向量检索
"""
import logging
from typing import Dict, List, Optional, Tuple
from src.knowledge_graph.query_interface import QueryInterface
from src.nlp.llm_extractor import LLMExtractor
from config.settings import Config

logger = logging.getLogger(__name__)

class KGQAEngine:
    """知识图谱问答引擎"""

    def __init__(self):
        self.query_interface = QueryInterface()
        self.llm_extractor = LLMExtractor()
        self.config = Config

    def ask_question(self, question: str, document_id: Optional[str] = None,
                     chat_history: List[Dict] = None) -> Tuple[str, List[Dict]]:
        """
        回答用户问题

        Args:
            question: 用户问题
            document_id: 可选文档ID限制查询范围
            chat_history: 聊天历史上下文

        Returns:
            (答案文本, 来源信息列表)
        """
        try:
            # 1. 问题解析和意图识别
            intent = self._parse_question_intent(question, chat_history)

            # 2. 根据意图选择问答模式
            if intent.get('requires_graph_query', True):
                # 模式A: 图查询
                answer, sources = self._answer_via_graph_query(question, document_id, intent)
            else:
                # 模式B: 向量检索 (可选实现)
                answer, sources = self._answer_via_vector_search(question, document_id, intent)

            # 3. 如果有来源信息，添加到答案中
            if sources and len(sources) > 0:
                source_text = "\n\nSources: "
                source_list = []
                for i, source in enumerate(sources[:3]):  # 最多显示3个来源
                    doc_name = source.get('document', 'Unknown document')
                    confidence = source.get('confidence', 0)
                    source_list.append(f"{doc_name} (confidence: {confidence:.1f})")

                if source_list:
                    answer += source_text + ", ".join(source_list)

            return answer, sources

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return f"I encountered an error while processing your question: {str(e)}", []

    def _parse_question_intent(self, question: str, chat_history: List[Dict] = None) -> Dict:
        """解析问题意图"""
        # 使用规则方法识别问题类型
        # 返回意图字典，包含：query_type, entities, relations, requires_graph_query等

        question_lower = question.lower()
        words = question_lower.split()

        # 初始化意图
        intent = {
            'query_type': 'general',
            'entities': [],
            'relations': [],
            'requires_graph_query': True,
            'keywords': words,
            'is_comparison': False,
            'is_list_query': False,
            'is_factual': True
        }

        # 识别问题类型
        question_words = {'who', 'what', 'where', 'when', 'which', 'whom', 'whose'}
        explanation_words = {'how', 'why'}
        relationship_words = {'relation', 'relationship', 'related', 'connected', 'connection', 'link', 'association'}
        comparison_words = {'compare', 'difference', 'similar', 'versus', 'vs', 'better', 'best', 'worst'}
        list_words = {'list', 'all', 'every', 'each', 'many'}

        # 检查问题类型
        if any(word in question_words for word in words):
            intent['query_type'] = 'entity_query'
        elif any(word in explanation_words for word in words):
            intent['query_type'] = 'explanation_query'
        elif any(word in relationship_words for word in words):
            intent['query_type'] = 'relationship_query'
        elif any(word in comparison_words for word in words):
            intent['query_type'] = 'comparison_query'
            intent['is_comparison'] = True
        elif any(word in list_words for word in words):
            intent['query_type'] = 'list_query'
            intent['is_list_query'] = True

        # 尝试提取实体（简单规则）
        # 假设大写单词或引号内的内容可能是实体
        import re
        # 查找大写单词（可能为专有名词）
        uppercase_words = re.findall(r'\b[A-Z][a-z]+\b', question)
        if uppercase_words:
            intent['entities'].extend([{'name': word, 'type': 'PROPER_NOUN'} for word in uppercase_words])

        # 查找引号内容
        quoted_entities = re.findall(r'"([^"]+)"|\'([^\']+)\'', question)
        for match in quoted_entities:
            entity = match[0] or match[1]
            if entity:
                intent['entities'].append({'name': entity, 'type': 'QUOTED_ENTITY'})

        # 简单关系提取
        relation_patterns = [
            ('works at', 'employment'),
            ('works for', 'employment'),
            ('located in', 'location'),
            ('based in', 'location'),
            ('part of', 'membership'),
            ('member of', 'membership'),
            ('related to', 'association'),
            ('friend of', 'social'),
            ('colleague of', 'professional'),
        ]

        for pattern, rel_type in relation_patterns:
            if pattern in question_lower:
                intent['relations'].append({
                    'type': rel_type,
                    'pattern': pattern
                })

        return intent

    def _answer_via_graph_query(self, question: str, document_id: Optional[str],
                                intent: Dict) -> Tuple[str, List[Dict]]:
        """通过图查询回答问题"""
        try:
            # 1. 尝试生成Cypher查询
            cypher_query = self._generate_cypher_query(question, intent, document_id)

            # 2. 执行查询
            query_results = []
            if cypher_query:
                query_results = self.query_interface.execute_custom_query(cypher_query)
            else:
                # 如果没有生成Cypher查询，使用自然语言查询
                query_results = self.query_interface.query_by_natural_language(question, document_id)

            # 3. 使用LLM生成自然语言答案
            answer = self._generate_natural_language_answer(question, query_results, intent)

            # 4. 收集来源信息
            sources = self._extract_source_info(query_results)

            return answer, sources

        except Exception as e:
            logger.error(f"Error in graph query: {e}")
            # 回退到简单回答
            return f"I tried to query the knowledge graph but encountered an error: {str(e)}. Please try a different question or check if the document has been parsed.", []

    def _answer_via_vector_search(self, question: str, document_id: Optional[str],
                                 intent: Dict) -> Tuple[str, List[Dict]]:
        """通过向量检索回答问题（可选实现）"""
        # 如果实现向量检索
        return "Vector search is not implemented yet. Please use graph query mode.", []

    def _generate_cypher_query(self, question: str, intent: Dict,
                              document_id: Optional[str]) -> str:
        """生成Cypher查询"""
        # 基于意图和问题生成Neo4j Cypher查询
        # 简单实现：返回空字符串，让自然语言查询处理
        return ""

    def _generate_natural_language_answer(self, question: str, query_results: List,
                                         intent: Dict) -> str:
        """使用LLM生成自然语言答案"""
        # 如果查询结果为空
        if not query_results:
            if intent.get('entities'):
                entity_names = [e['name'] for e in intent['entities']]
                return f"I couldn't find information about {', '.join(entity_names[:3])} in the knowledge graph. The document might not contain these entities or needs to be parsed."
            else:
                return f"I couldn't find any information about '{question}' in the knowledge graph. The document might not contain this information or needs to be parsed."

        # 结果摘要
        result_summary = f"Found {len(query_results)} relevant result(s) in the knowledge graph."

        # 根据查询类型生成不同回答
        query_type = intent.get('query_type', 'general')

        if query_type == 'entity_query':
            if intent.get('entities'):
                entity_names = [e['name'] for e in intent['entities'][:2]]
                entities_str = ', '.join(entity_names)
                return f"Based on the knowledge graph, {result_summary} Information about {entities_str} is available."
            else:
                return f"Based on the knowledge graph, {result_summary} The knowledge graph contains information related to your question."

        elif query_type == 'relationship_query':
            if intent.get('relations'):
                rel_types = [r['type'] for r in intent['relations'][:2]]
                rels_str = ', '.join(rel_types)
                return f"Based on the knowledge graph, {result_summary} Information about {rels_str} relationships is available."
            else:
                return f"Based on the knowledge graph, {result_summary} Relationship information is available in the graph."

        elif query_type == 'comparison_query':
            return f"Based on the knowledge graph, {result_summary} Comparison data is available for analysis."

        elif query_type == 'list_query':
            return f"Based on the knowledge graph, {result_summary} Here are the relevant items:"

        elif query_type == 'explanation_query':
            return f"Based on the knowledge graph, {result_summary} Here's an explanation based on the available data:"

        else:
            return f"Based on the knowledge graph, {result_summary} Here's what I found regarding your question."

    def _extract_source_info(self, query_results: List) -> List[Dict]:
        """从查询结果中提取来源信息"""
        sources = []
        if not query_results:
            return sources

        # 确保query_results是列表
        results = query_results if isinstance(query_results, list) else [query_results]

        # 提取唯一文档来源
        seen_documents = set()

        for result in results[:10]:  # 限制检查前10个结果
            try:
                if isinstance(result, dict):
                    # 检查不同可能的文档字段名
                    doc_fields = ['source_document', 'document', 'source', 'filename', 'file']
                    document = None

                    for field in doc_fields:
                        if field in result and result[field]:
                            document = result[field]
                            break

                    # 如果没有找到文档字段，尝试其他结构
                    if not document and 'properties' in result and isinstance(result['properties'], dict):
                        for field in doc_fields:
                            if field in result['properties'] and result['properties'][field]:
                                document = result['properties'][field]
                                break

                    if document and document not in seen_documents:
                        seen_documents.add(document)
                        sources.append({
                            'type': 'knowledge_graph',
                            'document': document,
                            'confidence': result.get('confidence', result.get('score', 0.5)),
                            'entity_count': 1  # 可以扩展为计数
                        })

                # 如果是实体对象（具有属性的对象）
                elif hasattr(result, 'source_document'):
                    document = result.source_document
                    if document and document not in seen_documents:
                        seen_documents.add(document)
                        sources.append({
                            'type': 'knowledge_graph',
                            'document': document,
                            'confidence': getattr(result, 'confidence', 0.5),
                            'entity_count': 1
                        })

            except Exception as e:
                logger.debug(f"Error extracting source from result: {e}")
                continue

        return sources