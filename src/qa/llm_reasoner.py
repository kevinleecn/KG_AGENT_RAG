"""
LLM-driven knowledge graph reasoning engine.
Uses DeepSeek V3.2 or other LLMs to:
1. Generate Cypher queries from natural language questions
2. Perform multi-hop reasoning over knowledge graph
3. Generate comprehensive answers based on graph query results
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from config.settings import Config

logger = logging.getLogger(__name__)


class LLMReasoner:
    """LLM-based reasoner for knowledge graph QA."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 backend: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize LLM reasoner.

        Args:
            api_key: LLM API key
            model: LLM model name
            backend: LLM backend (openai, ollama, anthropic)
            base_url: Custom base URL for OpenAI-compatible API
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.LLM_MODEL
        self.backend = backend or Config.LLM_BACKEND
        self.base_url = base_url or getattr(Config, 'OPENAI_BASE_URL', None)

        # Initialize LLM client
        self.llm_client = self._init_llm_client()

        # Reasoning settings
        self.max_tokens = 4000
        self.temperature = 0.3  # Slightly higher for creative reasoning
        self.max_retries = 3

        # Knowledge graph schema (will be populated dynamically)
        self.entity_types = []
        self.relationship_types = []

        logger.info(f"Initialized LLMReasoner with backend: {self.backend}, model: {self.model}")

    def _init_llm_client(self):
        """Initialize LLM client based on configured backend."""
        if not self.api_key and self.backend == "openai":
            logger.warning("OPENAI_API_KEY not configured. LLM reasoning will be disabled.")
            return None

        try:
            if self.backend == "openai":
                from openai import OpenAI
                if self.base_url:
                    logger.info(f"Using custom OpenAI-compatible API: {self.base_url}")
                    return OpenAI(api_key=self.api_key, base_url=self.base_url)
                else:
                    return OpenAI(api_key=self.api_key)
            elif self.backend == "ollama":
                try:
                    from openai import OpenAI
                    client = OpenAI(
                        base_url="http://localhost:11434/v1",
                        api_key="ollama",
                        timeout=300.0
                    )
                    return client
                except ImportError:
                    logger.warning("Ollama backend requested but OpenAI library not available.")
                    return None
            elif self.backend == "anthropic":
                try:
                    from anthropic import Anthropic
                    return Anthropic(api_key=self.api_key)
                except ImportError:
                    logger.warning("Anthropic backend requested but anthropic library not available.")
                    return None
            else:
                logger.warning(f"Unsupported LLM backend: {self.backend}")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize LLM client for backend {self.backend}: {e}")
            return None

    def _call_llm(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Call LLM with prompt and return response.

        Args:
            prompt: User prompt
            system_message: Optional system message

        Returns:
            LLM response text
        """
        if not self.llm_client:
            raise ValueError("LLM client not initialized. Check API key and backend configuration.")

        for attempt in range(self.max_retries):
            try:
                if self.backend == "openai" or self.backend == "ollama":
                    messages = []
                    if system_message:
                        messages.append({"role": "system", "content": system_message})
                    messages.append({"role": "user", "content": prompt})

                    response = self.llm_client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                    return response.choices[0].message.content

                elif self.backend == "anthropic":
                    messages = []
                    if system_message:
                        messages.append({"role": "system", "content": system_message})
                    messages.append({"role": "user", "content": prompt})

                    response = self.llm_client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        messages=messages
                    )
                    return response.content[0].text

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

        raise ValueError("LLM call failed after all retries")

    def generate_cypher_query(self, question: str,
                              entity_types: Optional[List[str]] = None,
                              relationship_types: Optional[List[str]] = None) -> Optional[str]:
        """
        Generate Cypher query from natural language question.

        Args:
            question: Natural language question
            entity_types: Available entity types in the knowledge graph
            relationship_types: Available relationship types

        Returns:
            Generated Cypher query or None
        """
        schema_info = ""
        if entity_types:
            schema_info += f"Available entity types: {', '.join(entity_types)}\n"
        if relationship_types:
            schema_info += f"Available relationship types: {', '.join(relationship_types)}\n"

        system_message = """你是一个知识图谱 Cypher 查询生成专家。你的任务是将自然语言问题转换为 Neo4j Cypher 查询。

知识库结构：
- 实体节点标签：Entity
- 关系类型：RELATIONSHIP
- 实体属性：name, type, source_document, confidence
- 关系属性：type, source_document, confidence

请遵循以下规则：
1. 只生成 Cypher 查询，不要其他说明
2. 使用 MATCH 语句查询实体和关系
3. 使用 WHERE 子句过滤条件
4. 使用 RETURN 返回结果
5. 限制结果数量（LIMIT 50）
6. 如果问题涉及两个实体之间的关系，使用路径查询
7. 如果需要查找相关内容，使用 CONTAINS 进行模糊匹配

示例查询：
- 查找名为"X"的实体：MATCH (e:Entity {name: "X"}) RETURN e
- 查找包含"X"的实体：MATCH (e:Entity WHERE e.name CONTAINS "X") RETURN e LIMIT 20
- 查找两个实体之间的关系：MATCH p=(e1:Entity)-[r]-(e2:Entity) WHERE e1.name CONTAINS "X" AND e2.name CONTAINS "Y" RETURN p
- 查找某实体的所有关系：MATCH (e:Entity {name: "X"})-[r]-(other:Entity) RETURN r, other"""

        prompt = f"""请为以下问题生成 Cypher 查询：

问题：{question}

{schema_info if schema_info else ''}

Cypher 查询："""

        try:
            response = self._call_llm(prompt, system_message)
            # Extract Cypher query from response
            cypher_query = self._extract_cypher_query(response)
            logger.info(f"Generated Cypher query: {cypher_query}")
            return cypher_query
        except Exception as e:
            logger.error(f"Failed to generate Cypher query: {e}")
            return None

    def _extract_cypher_query(self, response: str) -> Optional[str]:
        """Extract Cypher query from LLM response."""
        # Remove markdown code blocks if present
        import re

        # Try to find content within ```cypher ... ``` or ``` ... ```
        code_block_match = re.search(r'```(?:cypher)?\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            return code_block_match.group(1).strip()

        # If no code block, try to find a line that looks like Cypher
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.upper().startswith(('MATCH', 'RETURN', 'WITH', 'CREATE', 'MERGE')):
                return line

        # Return entire response as fallback
        return response.strip() if response.strip() else None

    def generate_answer(self, question: str, query_results: List[Any],
                        chat_history: Optional[List[Dict]] = None) -> str:
        """
        Generate natural language answer based on query results.

        Args:
            question: Original question
            query_results: Results from knowledge graph query
            chat_history: Optional chat history

        Returns:
            Natural language answer
        """
        # Format query results for LLM
        formatted_results = self._format_query_results(query_results)

        system_message = """你是知识图谱智能助手。基于知识图谱查询结果，用中文回答用户问题。

请遵循以下规则：
1. 基于查询结果提供准确、具体的答案
2. 明确指出找到的实体、关系和路径
3. 如果结果为空，说明知识库中没有相关信息
4. 如果有多个结果，进行归纳总结
5. 引用具体的实体名称和关系类型
6. 答案应该自然流畅，不要机械地罗列数据
7. 如果信息不足，说明需要更多上下文
8. 始终使用中文回答"""

        history_context = ""
        if chat_history and len(chat_history) > 0:
            recent_history = chat_history[-3:]  # Last 3 exchanges
            history_context = "\n对话历史：\n"
            for msg in recent_history:
                role = "用户" if msg.get('role') == 'user' else "助手"
                content = msg.get('content', '')[:100]  # Truncate long messages
                history_context += f"{role}: {content}\n"

        prompt = f"""{history_context}
用户问题：{question}

知识图谱查询结果：
{formatted_results}

请基于以上查询结果，用中文回答用户问题。如果结果为空或没有相关信息，请礼貌地告知用户。

回答："""

        try:
            response = self._call_llm(prompt, system_message)
            logger.info(f"Generated answer: {response[:200]}...")
            return response
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return f"抱歉，生成答案时遇到错误：{str(e)}"

    def _format_query_results(self, query_results: List[Any]) -> str:
        """Format query results for LLM context."""
        if not query_results:
            return "（无查询结果）"

        formatted = []
        for i, result in enumerate(query_results[:20]):  # Limit to 20 results
            if isinstance(result, dict):
                # Format as key-value pairs
                items = []
                for key, value in result.items():
                    if value is not None:
                        items.append(f"  {key}: {self._format_value(value)}")
                if items:
                    formatted.append(f"结果 {i+1}:\n" + "\n".join(items))
            else:
                formatted.append(f"结果 {i+1}: {self._format_value(result)}")

        if len(query_results) > 20:
            formatted.append(f"... 还有 {len(query_results) - 20} 个结果")

        return "\n\n".join(formatted) if formatted else "（无查询结果）"

    def _format_value(self, value: Any) -> str:
        """Format a single value for display."""
        if value is None:
            return "null"
        elif isinstance(value, dict):
            # Neo4j node/relationship object
            if 'labels' in value and 'properties' in value:
                props = value.get('properties', {})
                labels = value.get('labels', [])
                return f"节点 ({', '.join(labels)}): {props}"
            elif 'type' in value and 'properties' in value:
                props = value.get('properties', {})
                rel_type = value.get('type', 'RELATIONSHIP')
                return f"关系 ({rel_type}): {props}"
            else:
                return str(value)
        elif hasattr(value, '_properties'):
            # Neo4j Node or Relationship object
            props = dict(value._properties)
            if hasattr(value, 'labels'):
                return f"节点 {value.labels}: {props}"
            else:
                return f"关系: {props}"
        else:
            return str(value)

    def find_relationship_path(self, entity1: str, entity2: str,
                               max_hops: int = 3) -> Optional[str]:
        """
        Find relationship path between two entities.

        Args:
            entity1: First entity name
            entity2: Second entity name
            max_hops: Maximum number of hops

        Returns:
            Cypher query to find path
        """
        # Generate variable-length path query
        var_pattern = f"*1..{max_hops}"

        cypher = f"""
        MATCH (e1:Entity WHERE e1.name CONTAINS '{entity1}')
        MATCH (e2:Entity WHERE e2.name CONTAINS '{entity2}')
        MATCH p=(e1)-[r:RELATIONSHIP{var_pattern}]-(e2)
        RETURN p, length(p) as hops
        ORDER BY hops ASC
        LIMIT 5
        """
        return cypher

    def expand_subgraph(self, seed_entities: List[str],
                        max_depth: int = 2,
                        max_nodes: int = 50) -> Optional[str]:
        """
        Generate query to expand subgraph around seed entities.

        Args:
            seed_entities: List of seed entity names
            max_depth: Maximum depth to expand
            max_nodes: Maximum nodes to return

        Returns:
            Cypher query to expand subgraph
        """
        if not seed_entities:
            return None

        # Build OR condition for seed entities
        conditions = " OR ".join([f"e.name CONTAINS '{e}'" for e in seed_entities])

        cypher = f"""
        MATCH (e:Entity)
        WHERE {conditions}
        WITH e
        MATCH p=(e)-[r:RELATIONSHIP*1..{max_depth}]-(related:Entity)
        RETURN p
        LIMIT {max_nodes}
        """
        return cypher

    def analyze_graph_structure(self, query_results: List[Any]) -> Dict[str, Any]:
        """
        Analyze the structure of query results.

        Args:
            query_results: Results from graph query

        Returns:
            Analysis including entity count, relationship types, etc.
        """
        analysis = {
            'entity_count': 0,
            'relationship_count': 0,
            'entity_types': set(),
            'relationship_types': set(),
            'documents': set(),
            'has_connections': False
        }

        for result in query_results:
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, dict):
                        if 'labels' in value:
                            analysis['entity_count'] += 1
                            for label in value.get('labels', []):
                                analysis['entity_types'].add(label)
                        if 'type' in value and 'start' in value:
                            analysis['relationship_count'] += 1
                            analysis['relationship_types'].add(value.get('type'))

                        props = value.get('properties', {})
                        if 'source_document' in props:
                            analysis['documents'].add(props['source_document'])

        analysis['has_connections'] = analysis['relationship_count'] > 0

        # Convert sets to lists for JSON serialization
        analysis['entity_types'] = list(analysis['entity_types'])
        analysis['relationship_types'] = list(analysis['relationship_types'])
        analysis['documents'] = list(analysis['documents'])

        return analysis
