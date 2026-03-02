"""
LLM-enhanced knowledge extractor for entity and relationship extraction.
Uses OpenAI API or other LLM backends for advanced knowledge extraction.
"""

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from config.settings import Config

logger = logging.getLogger(__name__)


class LLMExtractor:
    """LLM-based knowledge extractor for advanced entity and relationship extraction."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 backend: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize LLM extractor.

        Args:
            api_key: LLM API key (default: from config)
            model: LLM model name (default: from config)
            backend: LLM backend (openai, ollama, anthropic) (default: from config)
            base_url: Custom base URL for OpenAI-compatible API (default: from config)
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.LLM_MODEL
        self.backend = backend or Config.LLM_BACKEND
        self.base_url = base_url or getattr(Config, 'OPENAI_BASE_URL', None)

        # Initialize LLM client based on backend
        self.llm_client = self._init_llm_client()

        # Extraction settings
        self.extraction_prompts = self._load_extraction_prompts()
        self.max_tokens = 4000  # Max tokens for LLM response
        self.temperature = 0.1  # Low temperature for consistent extraction
        self.max_retries = 3

        logger.info(f"Initialized LLMExtractor with backend: {self.backend}, model: {self.model}")

    def _init_llm_client(self):
        """Initialize LLM client based on configured backend."""
        if not self.api_key and self.backend == "openai":
            logger.warning("OPENAI_API_KEY not configured. LLM extraction will be disabled.")
            return None

        try:
            if self.backend == "openai":
                from openai import OpenAI
                # Use custom base URL if provided (for OpenAI-compatible APIs)
                if self.base_url:
                    logger.info(f"Using custom OpenAI-compatible API: {self.base_url}")
                    return OpenAI(api_key=self.api_key, base_url=self.base_url)
                else:
                    return OpenAI(api_key=self.api_key)
            elif self.backend == "ollama":
                # Ollama local setup
                try:
                    from openai import OpenAI
                    # Ollama compatible OpenAI client with longer timeout for large models
                    client = OpenAI(
                        base_url="http://localhost:11434/v1",
                        api_key="ollama",  # Ollama doesn't require a key
                        timeout=300.0  # 5 minute timeout for Ollama
                    )
                    # Test connection
                    try:
                        client.models.list()
                        logger.info("Ollama OpenAI-compatible client initialized successfully")
                    except Exception as e:
                        logger.warning(f"Ollama connection test failed: {e}. Will retry on first call.")
                    return client
                except ImportError:
                    logger.warning("Ollama backend requested but OpenAI client not available.")
                    return None
            elif self.backend == "anthropic":
                # Anthropic Claude
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

    def _load_extraction_prompts(self) -> Dict[str, str]:
        """Load extraction prompts for different tasks."""
        return {
            "entity_extraction": """Extract all entities from the following text and categorize them.

Text: {text}

Instructions:
1. Identify all named entities (people, organizations, locations, dates, etc.)
2. For each entity, provide:
   - Entity text (exact phrase from text)
   - Entity type (PERSON, ORGANIZATION, LOCATION, DATE, TIME, MONEY, PRODUCT, EVENT, or OTHER)
   - Confidence score (0.0 to 1.0)

Return the entities as a JSON list:
[
  {{"text": "entity name", "type": "ENTITY_TYPE", "confidence": 0.9}}
]

Only return valid JSON, no other text.""",

            "relationship_extraction": """Extract relationships between entities from the following text.

Text: {text}

Instructions:
1. Identify relationships between entities mentioned in the text
2. For each relationship, provide:
   - Subject entity (exact text)
   - Predicate (relationship type like: works_at, located_in, based_in, part_of, founder_of, ceo_of, etc.)
   - Object entity (exact text)
   - Confidence score (0.0 to 1.0)

Common relationship types:
- works_at: Person works at organization
- located_in: Entity located in location
- based_in: Organization based in location
- part_of: Entity part of larger entity
- founder_of: Person founded organization
- ceo_of: Person is CEO of organization
- director_of: Person is director of organization
- member_of: Person is member of organization
- related_to: Generic relationship

Return the relationships as a JSON list:
[
  {{
    "subject": "subject entity text",
    "predicate": "relationship_type",
    "object": "object entity text",
    "confidence": 0.8
  }}
]

Only return valid JSON, no other text.""",

            "triplet_extraction": """Extract knowledge triplets (subject-predicate-object) from the following text.

Text: {text}

Instructions:
1. Extract factual triplets from the text
2. Each triplet should be a factual statement that can be made from the text
3. For each triplet, provide:
   - Subject: The main entity
   - Predicate: The relationship or action
   - Object: The target entity or value
   - Confidence: How certain you are (0.0 to 1.0)

Example triplets:
- Subject: "John Smith", Predicate: "works_at", Object: "Acme Corp"
- Subject: "Acme Corp", Predicate: "based_in", Object: "New York"
- Subject: "Project X", Predicate: "started_on", Object: "2023-01-15"

Return the triplets as a JSON list:
[
  {{
    "subject": {{"name": "subject name", "type": "subject type"}},
    "predicate": "predicate",
    "object": {{"name": "object name", "type": "object type"}},
    "confidence": 0.85
  }}
]

Only return valid JSON, no other text."""
        }

    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for LLM processing."""
        if not text:
            return ""

        import re
        # Remove null characters and excessive whitespace
        text = re.sub(r'\x00', '', text)  # Remove null bytes
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()

        # Limit text length for LLM constraints
        max_text_length = 8000  # Conservative limit for LLM context
        if len(text) > max_text_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_text_length}")
            text = text[:max_text_length]

        return text

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

        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                if self.backend == "openai":
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

                elif self.backend == "ollama":
                    # Use Ollama native API via requests (more reliable than OpenAI compat)
                    import requests

                    messages = []
                    if system_message:
                        messages.append({"role": "system", "content": system_message})
                    messages.append({"role": "user", "content": prompt})

                    try:
                        response = requests.post(
                            "http://localhost:11434/api/chat",
                            json={
                                "model": self.model,
                                "messages": messages,
                                "stream": False
                            },
                            timeout=300.0
                        )
                        response.raise_for_status()
                        result = response.json()
                        return result.get("message", {}).get("content", "")
                    except requests.exceptions.RequestException as e:
                        # Fallback to OpenAI compatible client
                        logger.warning(f"Ollama native API failed: {e}, trying OpenAI compat...")
                        client_response = self.llm_client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                            timeout=300.0
                        )
                        return client_response.choices[0].message.content

                elif self.backend == "anthropic":
                    if system_message:
                        prompt_with_system = f"{system_message}\n\n{prompt}"
                    else:
                        prompt_with_system = prompt

                    response = self.llm_client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        messages=[{"role": "user", "content": prompt_with_system}]
                    )
                    return response.content[0].text

                else:
                    raise ValueError(f"Unsupported backend: {self.backend}")

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"LLM call failed after {max_retries} attempts: {e}")
                    raise

    def _parse_json_response(self, response_text: str, task_name: str) -> List[Dict[str, Any]]:
        """
        Parse JSON response from LLM with error handling.

        Args:
            response_text: LLM response text
            task_name: Name of extraction task for logging

        Returns:
            Parsed JSON data as list of dictionaries
        """
        if not response_text:
            logger.warning(f"Empty response for {task_name}")
            return []

        # Try to extract JSON from response (LLM might add extra text)
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1

        if json_start == -1 or json_end == 0:
            # Try to find JSON object instead of array
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            logger.error(f"No JSON found in LLM response for {task_name}: {response_text[:100]}...")
            return []

        json_str = response_text[json_start:json_end]

        try:
            parsed_data = json.loads(json_str)
            if not isinstance(parsed_data, list):
                # If it's a single object, wrap in list
                parsed_data = [parsed_data]
            return parsed_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {task_name}: {e}\nJSON string: {json_str}")
            return []

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text using LLM.

        Args:
            text: Input text

        Returns:
            List of extracted entities in standardized format
        """
        if not text or not text.strip():
            return []

        text = self._clean_text(text)
        if not text:
            return []

        # Prepare prompt
        prompt = self.extraction_prompts["entity_extraction"].format(text=text)
        system_message = "You are a knowledge extraction expert. Extract entities accurately and return only JSON."

        try:
            response = self._call_llm(prompt, system_message)
            raw_entities = self._parse_json_response(response, "entity_extraction")

            # Convert to standardized format
            entities = []
            for item in raw_entities:
                entity = {
                    "text": item.get("text", "").strip(),
                    "type": item.get("type", "OTHER").upper(),
                    "confidence": float(item.get("confidence", 0.5)),
                    "metadata": {
                        "source": "llm",
                        "extraction_method": "llm_entity_extraction",
                        "timestamp": datetime.now().isoformat()
                    }
                }

                # Validate entity
                if entity["text"] and entity["type"]:
                    entities.append(entity)

            logger.debug(f"LLM extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities with LLM: {e}")
            return []

    def extract_relationships(self, text: str, entities: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Extract relationships from text using LLM.

        Args:
            text: Input text
            entities: Optional pre-extracted entities (not used in LLM extraction but kept for API consistency)

        Returns:
            List of extracted relationships
        """
        if not text or not text.strip():
            return []

        text = self._clean_text(text)
        if not text:
            return []

        # Prepare prompt
        prompt = self.extraction_prompts["relationship_extraction"].format(text=text)
        system_message = "You are a relationship extraction expert. Extract relationships accurately and return only JSON."

        try:
            response = self._call_llm(prompt, system_message)
            raw_relationships = self._parse_json_response(response, "relationship_extraction")

            # Convert to standardized format
            relationships = []
            for item in raw_relationships:
                relationship = {
                    "subject": {
                        "text": item.get("subject", "").strip(),
                        "type": "ENTITY",  # LLM doesn't provide subject type
                        "confidence": 0.8  # Default confidence for LLM-extracted entities
                    },
                    "predicate": item.get("predicate", "related_to").lower(),
                    "object": {
                        "text": item.get("object", "").strip(),
                        "type": "ENTITY",  # LLM doesn't provide object type
                        "confidence": 0.8
                    },
                    "confidence": float(item.get("confidence", 0.5)),
                    "context": "",  # LLM doesn't provide context
                    "metadata": {
                        "source": "llm",
                        "extraction_method": "llm_relationship_extraction",
                        "timestamp": datetime.now().isoformat()
                    }
                }

                # Validate relationship
                if relationship["subject"]["text"] and relationship["object"]["text"]:
                    relationships.append(relationship)

            logger.debug(f"LLM extracted {len(relationships)} relationships")
            return relationships

        except Exception as e:
            logger.error(f"Error extracting relationships with LLM: {e}")
            return []

    def extract_triplets(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract triplets directly from text using LLM.

        Args:
            text: Input text

        Returns:
            List of extracted triplets in standardized format
        """
        if not text or not text.strip():
            return []

        text = self._clean_text(text)
        if not text:
            return []

        # Prepare prompt
        prompt = self.extraction_prompts["triplet_extraction"].format(text=text)
        system_message = "You are a knowledge extraction expert. Extract factual triplets accurately and return only JSON."

        try:
            response = self._call_llm(prompt, system_message)
            raw_triplets = self._parse_json_response(response, "triplet_extraction")

            # Convert to standardized format
            triplets = []
            for item in raw_triplets:
                # Handle different response formats
                subject = item.get("subject", {})
                if isinstance(subject, str):
                    subject = {"name": subject, "type": "ENTITY"}

                obj = item.get("object", {})
                if isinstance(obj, str):
                    obj = {"name": obj, "type": "ENTITY"}

                triplet = {
                    "subject": {
                        "name": subject.get("name", subject.get("text", "")).strip(),
                        "type": subject.get("type", "ENTITY"),
                        "properties": {}
                    },
                    "predicate": item.get("predicate", "related_to").lower(),
                    "object": {
                        "name": obj.get("name", obj.get("text", "")).strip(),
                        "type": obj.get("type", "ENTITY"),
                        "properties": {}
                    },
                    "confidence": float(item.get("confidence", 0.5)),
                    "metadata": {
                        "source": "llm",
                        "extraction_method": "llm_triplet_extraction",
                        "timestamp": datetime.now().isoformat()
                    }
                }

                # Validate triplet
                if triplet["subject"]["name"] and triplet["object"]["name"]:
                    triplets.append(triplet)

            logger.debug(f"LLM extracted {len(triplets)} triplets")
            return triplets

        except Exception as e:
            logger.error(f"Error extracting triplets with LLM: {e}")
            return []

    def process_document(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a document and extract knowledge using LLM.

        Args:
            text: Document text
            document_id: Optional document identifier

        Returns:
            Dictionary with extraction results
        """
        start_time = datetime.now()

        # Extract using LLM
        entities = self.extract_entities(text)
        relationships = self.extract_relationships(text, entities)
        triplets = self.extract_triplets(text)

        # Calculate statistics
        entity_types = {}
        for entity in entities:
            entity_type = entity["type"]
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

        relationship_types = {}
        for rel in relationships:
            rel_type = rel["predicate"]
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1

        processing_time = (datetime.now() - start_time).total_seconds()

        result = {
            "document_id": document_id,
            "entities": entities,
            "relationships": relationships,
            "triplets": triplets,
            "statistics": {
                "total_entities": len(entities),
                "total_relationships": len(relationships),
                "total_triplets": len(triplets),
                "entity_types": entity_types,
                "relationship_types": relationship_types,
                "processing_time_seconds": processing_time,
                "text_length": len(text),
                "word_count": len(text.split())
            },
            "timestamp": datetime.now().isoformat(),
            "method": "llm",
            "backend": self.backend,
            "model": self.model
        }

        logger.info(f"LLM processed document {document_id or 'unknown'}: "
                   f"{len(entities)} entities, {len(relationships)} relationships, "
                   f"{len(triplets)} triplets in {processing_time:.2f}s")

        return result

    def batch_process(self, texts: List[str], document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Process multiple texts in batch.

        Args:
            texts: List of texts to process
            document_ids: Optional list of document identifiers

        Returns:
            List of processing results
        """
        results = []
        for i, text in enumerate(texts):
            doc_id = document_ids[i] if document_ids and i < len(document_ids) else f"doc_{i}"
            try:
                result = self.process_document(text, doc_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing document {doc_id} with LLM: {e}")
                # Return empty result with error
                results.append({
                    "document_id": doc_id,
                    "error": str(e),
                    "entities": [],
                    "relationships": [],
                    "triplets": [],
                    "statistics": {
                        "total_entities": 0,
                        "total_relationships": 0,
                        "total_triplets": 0,
                        "entity_types": {},
                        "relationship_types": {},
                        "processing_time_seconds": 0,
                        "text_length": len(text),
                        "word_count": len(text.split())
                    },
                    "timestamp": datetime.now().isoformat(),
                    "method": "llm"
                })

        return results

    def is_available(self) -> bool:
        """Check if LLM extraction is available (API key configured and client initialized)."""
        if not self.llm_client:
            logger.warning("LLM client not initialized")
            return False

        # Try a simple test call if possible
        try:
            if self.backend == "openai" and self.api_key:
                # Actually test the API key with a minimal call
                import openai
                try:
                    response = self.llm_client.chat.completions.create(
                        model=self.model,
                        messages=[{'role': 'user', 'content': 'Hi'}],
                        max_tokens=5,
                        temperature=0
                    )
                    logger.info("LLM API key validation successful")
                    return True
                except openai.AuthenticationError as e:
                    logger.error(f"LLM API key authentication failed: {e}")
                    return False
                except openai.APIError as e:
                    logger.warning(f"LLM API error during validation: {e}")
                    # Other API errors might be transient, still consider available
                    return True
                except Exception as e:
                    logger.warning(f"LLM API validation failed: {e}")
                    return True  # Consider available even if test fails
            elif self.backend == "ollama":
                # Ollama is local, actually check if service is running
                import requests
                try:
                    response = requests.get('http://localhost:11434/api/tags', timeout=2)
                    if response.status_code == 200:
                        logger.info("Ollama service is available")
                        return True
                    else:
                        logger.warning(f"Ollama service returned status {response.status_code}")
                        return False
                except requests.exceptions.ConnectionError:
                    logger.warning("Ollama service is not running (localhost:11434)")
                    return False
                except Exception as e:
                    logger.warning(f"Ollama service check failed: {e}")
                    return False
            elif self.backend == "anthropic" and self.api_key:
                return True
            else:
                return False
        except Exception:
            return False