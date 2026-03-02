"""
真正的 KG-LLM 融合问答引擎

核心理念：
1. 智能识别问题类型 - 图谱内/图谱外/融合
2. 图谱外问题 - 直接用 LLM 回答（不查图谱）
3. 图谱内问题 - 用图谱数据增强 LLM 回答
4. 融合问题 - 结合图谱检索和 LLM 推理
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.knowledge_graph.query_interface import QueryInterface
from src.nlp.llm_extractor import LLMExtractor
from src.qa.llm_reasoner import LLMReasoner
from config.settings import Config

logger = logging.getLogger(__name__)


class QuestionType:
    """问题类型枚举"""
    LLM_ONLY = "llm_only"           # 仅需 LLM（通用知识、助手身份等）
    KG_ONLY = "kg_only"             # 仅需图谱（简单事实检索）
    KG_LLM_FUSION = "kg_llm_fusion"  # 需要融合（复杂推理、假设性问题）
    CHAT = "chat"                   # 闲聊/对话


class FusionKGQAEngine:
    """
    融合知识图谱问答引擎

    相比 HybridKGQAEngine 的改进:
    1. 正确识别图谱外问题，直接用 LLM 回答
    2. 实现真正的 KG+LLM 融合推理
    3. 支持多轮对话上下文
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
        self.kg_available = self.query_interface.graph_db.connected if self.query_interface.graph_db else False

        # 助手身份信息
        self.assistant_identity = {
            "name": "知识图谱智能助手",
            "model": Config.LLM_MODEL or "DeepSeek-V3",
            "base_url": getattr(Config, 'OPENAI_BASE_URL', 'DeepSeek API'),
            "capabilities": [
                "知识图谱查询",
                "文档内容问答",
                "实体关系分析",
                "多跳推理",
                "假设性分析"
            ]
        }

        logger.info(f"FusionKGQAEngine initialized - LLM: {self.llm_available}, KG: {self.kg_available}")

    def ask_question(self, question: str, document_id: Optional[str] = None,
                     chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        统一问答接口

        Args:
            question: 用户问题
            document_id: 可选文档 ID
            chat_history: 聊天历史

        Returns:
            完整响应
        """
        start_time = datetime.now()

        try:
            # 步骤 1: 问题分类 - 决定使用哪种回答策略
            question_type = self._classify_question(question, chat_history)
            logger.info(f"问题分类：{question_type}")

            # 步骤 2: 根据问题类型选择回答策略
            if question_type == QuestionType.LLM_ONLY:
                response = self._answer_with_llm_only(question, chat_history)
            elif question_type == QuestionType.KG_ONLY:
                response = self._answer_with_kg_only(question, document_id)
            elif question_type == QuestionType.KG_LLM_FUSION:
                response = self._answer_with_fusion(question, document_id, chat_history)
            else:  # CHAT
                response = self._answer_with_chat(question, chat_history)

            # 添加元数据
            processing_time = (datetime.now() - start_time).total_seconds()
            response["metadata"] = {
                "processing_time_seconds": processing_time,
                "question_type": question_type,
                "llm_used": self.llm_available,
                "kg_used": self.kg_available and question_type != QuestionType.LLM_ONLY
            }

            return response

        except Exception as e:
            logger.error(f"Error in FusionKGQAEngine: {e}", exc_info=True)
            return {
                "success": False,
                "answer": f"处理问题时发生错误：{str(e)}",
                "error": str(e),
                "metadata": {"processing_time_seconds": 0, "question_type": "error"}
            }

    def _classify_question(self, question: str, chat_history: List[Dict] = None) -> str:
        """
        问题分类 - 核心逻辑

        识别问题属于哪种类型:
        - LLM_ONLY: 通用知识、助手身份、不需要图谱
        - KG_ONLY: 简单图谱检索
        - KG_LLM_FUSION: 需要推理
        - CHAT: 闲聊
        """
        q = question.lower().strip()

        # === LLM_ONLY 类型 - 通用知识/助手相关 ===
        llm_only_patterns = [
            # 助手身份
            "你是谁", "你是哪个模型", "你叫什么", "who are you", "what model",
            # 能力询问
            "你能做什么", "你有什么功能", "help me", "capabilities",
            # 通用知识
            "解释", "什么是", "what is", "how does", "why is",
            "说明", "介绍一下", "介绍下",
            # 创意/生成任务
            "写一个", "创作", "生成", "translate", "summarize",
        ]

        for pattern in llm_only_patterns:
            if pattern in q:
                return QuestionType.LLM_ONLY

        # === CHAT 类型 - 闲聊 ===
        chat_patterns = [
            "你好", "hello", "hi ", "hey", "早上好", "下午好", "晚上好",
            "谢谢", "thank", "再见", "bye", "goodbye",
            "好的", "ok", "嗯嗯", "哈哈", "嘻嘻",
        ]

        for pattern in chat_patterns:
            if pattern in q:
                return QuestionType.CHAT

        # === KG_LLM_FUSION 类型 - 需要推理 ===
        fusion_patterns = [
            # 多跳推理
            "关系", "关联", "联系", "path", "connection", "how related",
            # 假设性
            "如果", "假如", "what if", "假设",
            # 比较
            "比较", "对比", "区别", "difference", "vs ", "versus",
            # 复杂推理
            "意味着", "说明什么", "implies", "suggest", "为什么", "why",
        ]

        for pattern in fusion_patterns:
            if pattern in q:
                return QuestionType.KG_LLM_FUSION

        # === 默认 KG_ONLY - 简单图谱检索 ===
        return QuestionType.KG_ONLY

    def _answer_with_llm_only(self, question: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        仅用 LLM 回答 - 不查图谱

        适用于：通用知识、助手身份、创意任务等
        """
        if not self.llm_available:
            return {
                "success": False,
                "answer": "LLM 服务不可用，无法回答此问题。",
                "confidence": 0.0
            }

        try:
            # 构建系统提示
            system_prompt = f"""你是{self.assistant_identity['name']}，使用{self.assistant_identity['model']}模型。

你的能力:
{chr(10).join('- ' + cap for cap in self.assistant_identity['capabilities'])}

请用友好、专业的语气回答用户问题。"""

            # 添加对话历史
            history_context = ""
            if chat_history and len(chat_history) > 0:
                recent = chat_history[-5:]
                history_lines = []
                for msg in recent:
                    role = "用户" if msg.get('role') == 'user' else "助手"
                    content = msg.get('content', '')[:200]
                    history_lines.append(f"{role}: {content}")
                history_context = "\n对话历史:\n" + "\n".join(history_lines)

            prompt = f"""{history_context}

用户问题：{question}

请用中文回答:"""

            answer = self.llm_reasoner._call_llm(prompt, system_prompt)

            return {
                "success": True,
                "answer": answer,
                "answer_type": "llm_only",
                "confidence": 0.9,
                "evidence": {
                    "source_type": "llm_knowledge",
                    "graph_results": [],
                    "reasoning_chain": []
                }
            }

        except Exception as e:
            logger.error(f"LLM-only answer failed: {e}")
            return {
                "success": False,
                "answer": f"LLM 回答失败：{str(e)}",
                "confidence": 0.0
            }

    def _answer_with_kg_only(self, question: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        仅用图谱检索回答 - 简单事实查询

        适用于：实体查询、关系查询等
        """
        try:
            # 使用 LLM 生成 Cypher 查询
            cypher = None
            if self.llm_available:
                cypher = self.llm_reasoner.generate_cypher_query(question)

            # 执行查询
            if cypher:
                results = self.query_interface.execute_custom_query(cypher)
            else:
                results = self.query_interface.query_by_natural_language(question, document_id)

            if not results:
                # 图谱中没有数据，回退到 LLM
                logger.info("KG 无结果，回退到 LLM")
                return self._answer_with_llm_fallback(question, "知识图谱中没有找到相关信息")

            # 使用 LLM 生成自然语言答案
            if self.llm_available:
                answer = self.llm_reasoner.generate_answer(question, results)
                confidence = 0.8
            else:
                answer = f"找到 {len(results)} 个相关结果。"
                confidence = 0.5

            return {
                "success": True,
                "answer": answer,
                "answer_type": "kg_only",
                "confidence": confidence,
                "evidence": {
                    "source_type": "knowledge_graph",
                    "graph_results": results,
                    "reasoning_chain": []
                }
            }

        except Exception as e:
            logger.error(f"KG-only answer failed: {e}")
            return self._answer_with_llm_fallback(question, f"图谱查询出错：{str(e)}")

    def _answer_with_fusion(self, question: str, document_id: Optional[str] = None,
                            chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        KG + LLM 融合推理

        适用于：多跳推理、假设性问题、实体比较等
        """
        try:
            # 1. 从图谱检索相关信息
            kg_results = []
            if self.kg_available:
                cypher = self.llm_reasoner.generate_cypher_query(question) if self.llm_available else None
                if cypher:
                    try:
                        kg_results = self.query_interface.execute_custom_query(cypher)
                    except:
                        pass

                if not kg_results:
                    kg_results = self.query_interface.query_by_natural_language(question, document_id)

            # 2. 使用 LLM 进行融合推理
            if self.llm_available:
                answer = self._generate_fusion_answer(question, kg_results, chat_history)
                confidence = 0.85 if kg_results else 0.6
                answer_type = "fusion" if kg_results else "llm_with_kg_context"
            else:
                answer = f"基于知识图谱找到 {len(kg_results)} 个相关信息。"
                confidence = 0.5
                answer_type = "kg_only"

            return {
                "success": True,
                "answer": answer,
                "answer_type": answer_type,
                "confidence": confidence,
                "evidence": {
                    "source_type": "fusion",
                    "graph_results": kg_results,
                    "reasoning_chain": self._extract_reasoning_chain(answer, kg_results)
                }
            }

        except Exception as e:
            logger.error(f"Fusion answer failed: {e}")
            return {
                "success": False,
                "answer": f"融合推理失败：{str(e)}",
                "confidence": 0.0
            }

    def _answer_with_chat(self, question: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        闲聊对话
        """
        chat_responses = {
            "你好": "您好！我是知识图谱智能助手，很高兴为您服务。有什么问题我可以帮您解答吗？",
            "hello": "Hello! I'm the Knowledge Graph Assistant. How can I help you today?",
            "谢谢": "不客气！如果您还有其他问题，随时可以问我。",
            "再见": "再见！祝您有愉快的一天！",
        }

        # 尝试匹配预设回复
        q = question.lower().strip()
        for key, value in chat_responses.items():
            if key in q:
                return {
                    "success": True,
                    "answer": value,
                    "answer_type": "chat",
                    "confidence": 0.95,
                    "evidence": {"source_type": "chat_response", "graph_results": [], "reasoning_chain": []}
                }

        # 默认闲聊回复
        return {
            "success": True,
            "answer": "我听到了您的问题。我是知识图谱助手，主要擅长回答基于文档内容的问题。如果您有关于上传文档的问题，我很乐意为您解答！",
            "answer_type": "chat",
            "confidence": 0.7,
            "evidence": {"source_type": "chat_fallback", "graph_results": [], "reasoning_chain": []}
        }

    def _answer_with_llm_fallback(self, question: str, kg_error: str) -> Dict[str, Any]:
        """
        KG 失败时用 LLM 回答
        """
        if not self.llm_available:
            return {
                "success": False,
                "answer": kg_error,
                "confidence": 0.0
            }

        try:
            system_prompt = """你是知识图谱智能助手。当知识图谱中没有相关信息时，你可以使用自己的知识来回答用户问题，但要说明信息来源。"""

            prompt = f"""{kg_error}

请用你自己的知识来回答这个问题：{question}

注意：说明你的答案是基于你自己的知识，而非知识图谱。

回答:"""

            answer = self.llm_reasoner._call_llm(prompt, system_prompt)

            return {
                "success": True,
                "answer": answer,
                "answer_type": "llm_fallback",
                "confidence": 0.7,
                "evidence": {
                    "source_type": "llm_knowledge",
                    "graph_results": [],
                    "reasoning_chain": []
                }
            }

        except Exception as e:
            return {
                "success": False,
                "answer": f"{kg_error}。LLM 回答也失败：{str(e)}",
                "confidence": 0.0
            }

    def _generate_fusion_answer(self, question: str, kg_results: List,
                                 chat_history: List[Dict] = None) -> str:
        """
        生成融合答案 - 结合 KG 数据和 LLM 推理
        """
        if not self.llm_available:
            return f"基于知识图谱找到 {len(kg_results)} 个相关信息。"

        system_prompt = """你是知识图谱智能助手。请结合知识图谱数据和自己的推理能力回答用户问题。

回答要求:
1. 如果图谱有数据，优先基于图谱信息回答
2. 如果图谱数据不足，可以补充自己的知识
3. 明确说明哪些信息来自图谱，哪些是你的推理
4. 提供推理过程和依据
5. 使用中文回答
"""

        # 格式化图谱数据
        kg_context = ""
        if kg_results:
            kg_context = self.llm_reasoner._format_query_results(kg_results)

        # 添加对话历史
        history_context = ""
        if chat_history and len(chat_history) > 0:
            recent = chat_history[-3:]
            history_lines = []
            for msg in recent:
                role = "用户" if msg.get('role') == 'user' else "助手"
                content = msg.get('content', '')[:150]
                history_lines.append(f"{role}: {content}")
            history_context = "对话历史:\n" + "\n".join(history_lines) + "\n\n"

        prompt = f"""{history_context}用户问题：{question}

知识图谱数据:
{kg_context if kg_context else '(无相关图谱数据)'}

请结合图谱数据和你的推理能力，用中文回答:"""

        return self.llm_reasoner._call_llm(prompt, system_prompt)

    def _extract_reasoning_chain(self, answer: str, kg_results: List) -> List[str]:
        """从答案中提取推理链（简化版）"""
        # 实际实现可以使用 LLM 来提取
        if not kg_results:
            return ["基于 LLM 知识直接回答"]
        return [f"基于知识图谱的 {len(kg_results)} 个结果进行推理"]

    def get_assistant_info(self) -> Dict[str, Any]:
        """获取助手信息"""
        return {
            "name": self.assistant_identity["name"],
            "model": self.assistant_identity["model"],
            "capabilities": self.assistant_identity["capabilities"],
            "llm_available": self.llm_available,
            "kg_available": self.kg_available
        }