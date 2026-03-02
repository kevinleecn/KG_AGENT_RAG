"""
知识图谱问答引擎 - 增强版
使用 LLM (DeepSeek V3.2) 进行推理和回答生成
"""
import logging
from typing import Dict, List, Optional, Tuple

from src.knowledge_graph.query_interface import QueryInterface
from src.nlp.llm_extractor import LLMExtractor
from src.qa.llm_reasoner import LLMReasoner
from config.settings import Config

logger = logging.getLogger(__name__)


class KGQAEngine:
    """增强版知识图谱问答引擎"""

    def __init__(self):
        self.query_interface = QueryInterface()
        self.llm_extractor = LLMExtractor()
        self.config = Config

        # Initialize LLM reasoner for advanced reasoning
        self.llm_reasoner = LLMReasoner(
            api_key=Config.OPENAI_API_KEY,
            model=Config.LLM_MODEL,
            backend=Config.LLM_BACKEND,
            base_url=getattr(Config, 'OPENAI_BASE_URL', None)
        )

        # Track if LLM reasoning is available
        self.llm_available = self.llm_reasoner.llm_client is not None

        if self.llm_available:
            logger.info("LLM reasoning enabled with model: {}".format(Config.LLM_MODEL))
        else:
            logger.warning("LLM reasoning disabled - will use basic responses")

    def ask_question(self, question: str, document_id: Optional[str] = None,
                     chat_history: List[Dict] = None) -> Tuple[str, List[Dict]]:
        """
        回答用户问题

        Args:
            question: 用户问题
            document_id: 可选文档 ID 限制查询范围
            chat_history: 聊天历史上下文

        Returns:
            (答案文本，来源信息列表)
        """
        try:
            # 1. 问题解析和意图识别
            intent = self._parse_question_intent(question, chat_history)

            # 2. 根据意图选择问答模式
            if intent.get('requires_graph_query', True):
                # 模式 A: 图查询（增强版）
                answer, sources = self._answer_via_graph_query_enhanced(question, document_id, intent, chat_history)
            else:
                # 模式 B: 向量检索 (可选实现)
                answer, sources = self._answer_via_vector_search(question, document_id, intent)

            # 3. 如果有来源信息，添加到答案中
            if sources and len(sources) > 0:
                source_text = "\n\n来源："
                source_list = []
                for i, source in enumerate(sources[:3]):  # 最多显示 3 个来源
                    doc_name = source.get('document', '未知文档')
                    confidence = source.get('confidence', 0)
                    source_list.append(f"{doc_name} (置信度：{confidence:.1f})")

                if source_list:
                    answer += source_text + ", ".join(source_list)

            return answer, sources

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return f"处理您的问题时发生错误：{str(e)}", []

    def _parse_question_intent(self, question: str, chat_history: List[Dict] = None) -> Dict:
        """解析问题意图 - 增强版"""
        # 使用规则方法识别问题类型
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
            'is_factual': True,
            'entity_names': []  # 提取的实体名称（中文支持）
        }

        # 识别问题类型（中英文）
        question_words = {'who', 'what', 'where', 'when', 'which', 'whom', 'whose',
                         '谁', '什么', '哪里', '何时', '哪个', '哪些'}
        explanation_words = {'how', 'why', '怎么', '为什么', '如何'}
        relationship_words = {'relation', 'relationship', 'related', 'connected', 'connection', 'link', 'association',
                             '关系', '关联', '联系', '连接'}
        comparison_words = {'compare', 'difference', 'similar', 'versus', 'vs', 'better', 'best', 'worst',
                           '比较', '区别', '相似', '对比', '更好', '最好', '最差'}
        list_words = {'list', 'all', 'every', 'each', 'many', '列出', '所有', '每个', '多少'}

        # 检查问题类型
        if any(word in question_lower for word in question_words):
            intent['query_type'] = 'entity_query'
        elif any(word in question_lower for word in explanation_words):
            intent['query_type'] = 'explanation_query'
        elif any(word in question_lower for word in relationship_words):
            intent['query_type'] = 'relationship_query'
        elif any(word in question_lower for word in comparison_words):
            intent['query_type'] = 'comparison_query'
            intent['is_comparison'] = True
        elif any(word in question_lower for word in list_words):
            intent['query_type'] = 'list_query'
            intent['is_list_query'] = True

        # 提取实体 - 改进中文支持
        import re

        # 查找可能的实体（大写单词、引号内容、专有名词）
        uppercase_words = re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', question)
        if uppercase_words:
            intent['entities'].extend([{'name': word, 'type': 'PROPER_NOUN'} for word in uppercase_words])
            intent['entity_names'].extend(uppercase_words)

        # 查找引号内容（支持中英文引号）
        quoted_entities = re.findall(r'"([^"]+)"|\'([^\']+)\'|\'([^\']+)\'', question)
        for match in quoted_entities:
            entity = ''.join([m for m in match if m])  # Join non-empty groups
            if entity:
                intent['entities'].append({'name': entity, 'type': 'QUOTED_ENTITY'})
                intent['entity_names'].append(entity)

        # 简单关系提取（中英文）
        relation_patterns = [
            ('works at', 'employment'), ('works for', 'employment'),
            ('located in', 'location'), ('based in', 'location'),
            ('part of', 'membership'), ('member of', 'membership'),
            ('related to', 'association'), ('friend of', 'social'),
            ('colleague of', 'professional'),
            ('工作在', 'employment'), ('任职于', 'employment'),
            ('位于', 'location'), ('在', 'location'),
            ('属于', 'membership'), ('成员', 'membership'),
            ('关联', 'association'), ('朋友', 'social'),
            ('同事', 'professional'), ('创建', 'founder'),
            ('创立', 'founder'), (' CEO', 'executive'),
        ]

        for pattern, rel_type in relation_patterns:
            if pattern in question_lower:
                intent['relations'].append({
                    'type': rel_type,
                    'pattern': pattern
                })

        return intent

    def _answer_via_graph_query_enhanced(self, question: str, document_id: Optional[str],
                                          intent: Dict, chat_history: List[Dict] = None) -> Tuple[str, List[Dict]]:
        """通过图查询回答问题 - 增强版（使用 LLM 推理）"""
        try:
            query_results = []

            # 1. 如果有实体名称，尝试使用 LLM 生成 Cypher 查询
            if self.llm_available and intent.get('entity_names'):
                logger.info("Using LLM to generate Cypher query...")
                cypher_query = self.llm_reasoner.generate_cypher_query(
                    question,
                    entity_types=intent.get('entity_types', []),
                    relationship_types=intent.get('relationship_types', [])
                )

                if cypher_query:
                    logger.info(f"Executing LLM-generated Cypher query: {cypher_query[:100]}...")
                    query_results = self.query_interface.execute_custom_query(cypher_query)

            # 2. 如果没有生成 Cypher 查询或结果为空，使用自然语言查询
            if not query_results:
                logger.info("Falling back to natural language query...")
                query_results = self.query_interface.query_by_natural_language(question, document_id)

            # 3. 如果仍然没有结果，尝试扩展搜索
            if not query_results and intent.get('entity_names'):
                logger.info("Trying subgraph expansion...")
                subgraph_query = self.llm_reasoner.expand_subgraph(
                    seed_entities=intent['entity_names'][:5],
                    max_depth=2,
                    max_nodes=30
                )
                if subgraph_query:
                    query_results = self.query_interface.execute_custom_query(subgraph_query)

            # 4. 使用 LLM 生成深度回答
            if query_results:
                logger.info(f"Got {len(query_results)} results, generating answer with LLM...")
                answer = self.llm_reasoner.generate_answer(
                    question=question,
                    query_results=query_results,
                    chat_history=chat_history
                )
            else:
                # 没有结果时使用友好提示
                answer = self._generate_no_results_response(question, intent)

            # 5. 收集来源信息
            sources = self._extract_source_info(query_results)

            return answer, sources

        except Exception as e:
            logger.error(f"Error in enhanced graph query: {e}")
            return f"我在查询知识图谱时遇到错误：{str(e)}。请尝试不同的问题或检查文档是否已解析。", []

    def _answer_via_graph_query(self, question: str, document_id: Optional[str],
                                intent: Dict) -> Tuple[str, List[Dict]]:
        """通过图查询回答问题 - 基础版（回退方法）"""
        try:
            # 1. 尝试生成 Cypher 查询
            cypher_query = self._generate_cypher_query(question, intent, document_id)

            # 2. 执行查询
            query_results = []
            if cypher_query:
                query_results = self.query_interface.execute_custom_query(cypher_query)
            else:
                # 如果没有生成 Cypher 查询，使用自然语言查询
                query_results = self.query_interface.query_by_natural_language(question, document_id)

            # 3. 使用基础方法生成自然语言答案
            answer = self._generate_natural_language_answer(question, query_results, intent)

            # 4. 收集来源信息
            sources = self._extract_source_info(query_results)

            return answer, sources

        except Exception as e:
            logger.error(f"Error in graph query: {e}")
            return f"我在查询知识图谱时遇到错误：{str(e)}。请尝试不同的问题或检查文档是否已解析。", []

    def _answer_via_vector_search(self, question: str, document_id: Optional[str],
                                 intent: Dict) -> Tuple[str, List[Dict]]:
        """通过向量检索回答问题（可选实现）"""
        # 如果实现向量检索
        return "向量检索功能尚未实现。请使用图查询模式。", []

    def _generate_cypher_query(self, question: str, intent: Dict,
                              document_id: Optional[str]) -> str:
        """生成 Cypher 查询 - 基础版"""
        # 基于意图和问题生成 Neo4j Cypher 查询
        # 简单实现：返回空字符串，让自然语言查询处理
        return ""

    def _generate_natural_language_answer(self, question: str, query_results: List,
                                         intent: Dict) -> str:
        """使用基础方法生成自然语言答案（回退）"""
        # 如果查询结果为空
        if not query_results:
            if intent.get('entity_names'):
                entity_names = intent['entity_names'][:3]
                return f"我在知识图谱中找不到关于 {', '.join(entity_names)} 的信息。文档可能不包含这些实体或需要解析。"
            else:
                return f"我在知识图谱中找不到关于'{question}'的信息。文档可能不包含此信息或需要解析。"

        # 结果摘要
        result_summary = f"在知识图谱中找到 {len(query_results)} 个相关结果。"

        # 根据查询类型生成不同回答
        query_type = intent.get('query_type', 'general')

        if query_type == 'entity_query':
            if intent.get('entity_names'):
                entity_names = intent['entity_names'][:2]
                entities_str = ', '.join(entity_names)
                return f"根据知识图谱，{result_summary} 关于 {entities_str} 的信息可用。"
            else:
                return f"根据知识图谱，{result_summary} 知识图谱包含与您问题相关的信息。"

        elif query_type == 'relationship_query':
            if intent.get('relations'):
                rel_types = [r['type'] for r in intent['relations'][:2]]
                rels_str = ', '.join(rel_types)
                return f"根据知识图谱，{result_summary} 关于 {rels_str} 关系的信息可用。"
            else:
                return f"根据知识图谱，{result_summary} 图谱中包含关系信息。"

        elif query_type == 'comparison_query':
            return f"根据知识图谱，{result_summary} 可用于比较分析的数据。"

        elif query_type == 'list_query':
            return f"根据知识图谱，{result_summary} 以下是相关项目："

        elif query_type == 'explanation_query':
            return f"根据知识图谱，{result_summary} 以下是基于可用数据的解释："

        else:
            return f"根据知识图谱，{result_summary} 以下是我关于您问题找到的内容。"

    def _generate_no_results_response(self, question: str, intent: Dict) -> str:
        """生成无结果时的友好回复"""
        if intent.get('entity_names'):
            entities_str = ', '.join(intent['entity_names'][:3])
            return f"抱歉，在知识图谱中没有找到关于 \"{entities_str}\" 的相关信息。这可能是因为：\n\n1. 文档尚未解析 - 请确保已上传并解析了相关文档\n2. 实体名称不完全匹配 - 尝试使用不同的表述方式\n3. 知识库中暂无此信息 - 可以上传更多相关文档"
        else:
            return f"抱歉，在知识图谱中没有找到与您的问题 \"{question}\" 相关的信息。\n\n建议：\n1. 确认文档已上传并解析\n2. 尝试用不同的方式提问\n3. 使用更具体的关键词"

    def _extract_source_info(self, query_results: List) -> List[Dict]:
        """从查询结果中提取来源信息"""
        sources = []
        if not query_results:
            return sources

        # 确保 query_results 是列表
        results = query_results if isinstance(query_results, list) else [query_results]

        # 提取唯一文档来源
        seen_documents = set()

        for result in results[:10]:  # 限制检查前 10 个结果
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
                            'entity_count': 1
                        })

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
