"""
LLM提示词模板
"""
GRAPH_QA_PROMPT = """You are a knowledgeable assistant that answers questions based on a knowledge graph.

Knowledge Graph Context:
{context}

User Question: {question}

Previous Conversation History:
{history}

Instructions:
1. Answer the question based only on the knowledge graph context provided.
2. If the information is not in the context, say "I don't have information about that in the knowledge graph."
3. Be concise but informative.
4. If relevant, mention specific entities and relationships from the graph.
5. Format your answer clearly with bullet points if appropriate.

Answer:"""

INTENT_RECOGNITION_PROMPT = """Analyze the user's question and identify:
1. Main entities mentioned (people, organizations, locations, etc.)
2. Relationships or actions inquired about
3. Question type (entity query, relationship query, comparison, etc.)
4. Whether this requires querying a knowledge graph or can be answered with general knowledge

Question: {question}

Return your analysis as a JSON object with keys: entities, relationships, question_type, requires_graph_query."""

ENTITY_EXTRACTION_PROMPT = """Extract entities from the following text:

Text: {text}

Extract all entities mentioned, including:
- People (names, titles, roles)
- Organizations (companies, institutions, teams)
- Locations (cities, countries, addresses)
- Dates and times
- Key concepts or topics

Return as a JSON list of entities with fields: name, type, confidence, context."""

RELATIONSHIP_EXTRACTION_PROMPT = """Extract relationships between entities from the following text:

Text: {text}
Entities: {entities}

Identify relationships between the entities mentioned, such as:
- PERSON works_at ORGANIZATION
- PERSON located_in LOCATION
- ORGANIZATION based_in LOCATION
- CONCEPT related_to CONCEPT
- EVENT involves PERSON/ORGANIZATION

Return as a JSON list of relationships with fields: source, target, relationship_type, confidence."""

CYPHER_GENERATION_PROMPT = """Generate a Neo4j Cypher query based on the user question and identified entities/relationships.

Question: {question}
Entities: {entities}
Relationships: {relationships}
Question Type: {question_type}

Instructions:
1. Generate a Cypher query that answers the question.
2. Use appropriate labels and properties.
3. Include RETURN clause with relevant data.
4. If filtering by document is needed, add WHERE clause with source_document property.

Cypher Query:"""