"""
Parsing Manager for Knowledge Graph QA Demo System
Handles document parsing state and result storage.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.document_parser.parser_factory import ParserFactory
from src.nlp.knowledge_extractor import KnowledgeExtractor
from src.nlp.triplet_extractor import TripletExtractor
from config.settings import Config

logger = logging.getLogger(__name__)


class ParsingManager:
    """Manages document parsing state and results"""

    def __init__(self, upload_folder: str, parsed_data_folder: str):
        """
        Initialize ParsingManager.

        Args:
            upload_folder: Path to uploaded files directory
            parsed_data_folder: Path to store parsed results
        """
        self.upload_folder = upload_folder
        self.parsed_data_folder = parsed_data_folder
        self.parser_factory = ParserFactory()

        # Ensure parsed data directory exists
        os.makedirs(self.parsed_data_folder, exist_ok=True)

        # State file for tracking parsing status
        self.state_file = os.path.join(self.parsed_data_folder, 'parsing_state.json')
        self._load_state()

        # Knowledge extraction components (lazy-loaded)
        self._knowledge_extractor = None
        self._triplet_extractor = None
        self._graph_builder = None

    def _load_state(self) -> None:
        """Load parsing state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load parsing state: {e}")
                self.state = {}
        else:
            self.state = {}

    def _save_state(self) -> None:
        """Save parsing state to file"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save parsing state: {e}")

    def get_file_state(self, filename: str) -> Dict[str, Any]:
        """
        Get parsing state for a file.

        Args:
            filename: Name of the file

        Returns:
            Dictionary with parsing state information
        """
        return self.state.get(filename, {
            'parsed': False,
            'parsed_at': None,
            'error': None,
            'text_length': 0,
            'word_count': 0,
            'metadata': {}
        })

    def update_file_state(self, filename: str, **kwargs) -> None:
        """
        Update parsing state for a file.

        Args:
            filename: Name of the file
            **kwargs: State fields to update
        """
        if filename not in self.state:
            self.state[filename] = {
                'parsed': False,
                'parsed_at': None,
                'error': None,
                'text_length': 0,
                'word_count': 0,
                'metadata': {}
            }

        self.state[filename].update(kwargs)
        self._save_state()

    def get_parsed_text_path(self, filename: str) -> str:
        """
        Get path for storing parsed text.

        Args:
            filename: Name of the file

        Returns:
            Path to parsed text file
        """
        # Create a safe filename for parsed text
        base_name = os.path.splitext(filename)[0]
        safe_name = ''.join(c if c.isalnum() else '_' for c in base_name)
        return os.path.join(self.parsed_data_folder, f"{safe_name}_parsed.txt")

    def parse_file(self, filename: str) -> Dict[str, Any]:
        """
        Parse a document file.

        Args:
            filename: Name of the file to parse

        Returns:
            Dictionary with parsing results
        """
        file_path = os.path.join(self.upload_folder, filename)
        parsed_text_path = self.get_parsed_text_path(filename)

        # Check if file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {filename}"
            logger.error(error_msg)
            self.update_file_state(
                filename,
                parsed=False,
                error=error_msg,
                parsed_at=datetime.now().isoformat()
            )
            return {
                'success': False,
                'error': error_msg,
                'filename': filename
            }

        try:
            # Get appropriate parser
            parser = self.parser_factory.get_parser(file_path)

            # Validate file
            if not parser.validate(file_path):
                error_msg = f"Invalid or unsupported file format: {filename}"
                logger.error(error_msg)
                self.update_file_state(
                    filename,
                    parsed=False,
                    error=error_msg,
                    parsed_at=datetime.now().isoformat()
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'filename': filename
                }

            # Parse the file
            logger.info(f"Parsing file: {filename}")
            result = parser.parse(file_path)

            # Check if parsing was successful
            if not result.get('success', False):
                error_msg = result.get('error', 'Unknown parsing error')
                logger.error(f"Parsing failed for {filename}: {error_msg}")
                self.update_file_state(
                    filename,
                    parsed=False,
                    error=error_msg,
                    parsed_at=datetime.now().isoformat(),
                    metadata=result.get('metadata', {})
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'filename': filename
                }

            # Save parsed text
            parsed_text = result.get('content', '')
            with open(parsed_text_path, 'w', encoding='utf-8') as f:
                f.write(parsed_text)

            # Calculate statistics
            text_length = len(parsed_text)
            word_count = len(parsed_text.split())

            # Update state
            self.update_file_state(
                filename,
                parsed=True,
                parsed_at=datetime.now().isoformat(),
                error=None,
                text_length=text_length,
                word_count=word_count,
                metadata=result.get('metadata', {})
            )

            logger.info(f"Successfully parsed file: {filename} "
                       f"({text_length} chars, {word_count} words)")

            return {
                'success': True,
                'filename': filename,
                'text_length': text_length,
                'word_count': word_count,
                'metadata': result.get('metadata', {}),
                'parsed_at': datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Error parsing file {filename}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.update_file_state(
                filename,
                parsed=False,
                error=error_msg,
                parsed_at=datetime.now().isoformat()
            )
            return {
                'success': False,
                'error': error_msg,
                'filename': filename
            }

    def get_parsed_text(self, filename: str) -> Optional[str]:
        """
        Get parsed text for a file.

        Args:
            filename: Name of the file

        Returns:
            Parsed text or None if not parsed
        """
        parsed_text_path = self.get_parsed_text_path(filename)

        if not os.path.exists(parsed_text_path):
            return None

        try:
            with open(parsed_text_path, 'r', encoding='utf-8') as f:
                return f.read()
        except IOError as e:
            logger.error(f"Error reading parsed text for {filename}: {e}")
            return None

    def get_all_files_state(self) -> List[Dict[str, Any]]:
        """
        Get parsing state for all files.

        Returns:
            List of file state dictionaries
        """
        files_state = []

        # Get all files in upload folder
        if os.path.exists(self.upload_folder):
            for filename in os.listdir(self.upload_folder):
                file_path = os.path.join(self.upload_folder, filename)
                if os.path.isfile(file_path):
                    state = self.get_file_state(filename)
                    state['filename'] = filename

                    # Add file size and modified time
                    try:
                        stat = os.stat(file_path)
                        state['file_size'] = stat.st_size
                        state['file_modified'] = stat.st_mtime
                    except OSError:
                        state['file_size'] = 0
                        state['file_modified'] = 0

                    files_state.append(state)

        return files_state

    def parse_all_files(self) -> Dict[str, Any]:
        """
        Parse all unparsed files in upload folder.

        Returns:
            Dictionary with parsing summary
        """
        if not os.path.exists(self.upload_folder):
            return {
                'success': True,
                'total': 0,
                'parsed': 0,
                'failed': 0,
                'results': []
            }

        results = []
        total = 0
        parsed = 0
        failed = 0

        for filename in os.listdir(self.upload_folder):
            file_path = os.path.join(self.upload_folder, filename)
            if not os.path.isfile(file_path):
                continue

            total += 1

            # Skip already parsed files
            state = self.get_file_state(filename)
            if state.get('parsed', False):
                results.append({
                    'filename': filename,
                    'success': True,
                    'skipped': True,
                    'message': 'Already parsed'
                })
                parsed += 1
                continue

            # Parse the file
            result = self.parse_file(filename)
            results.append(result)

            if result.get('success', False):
                parsed += 1
            else:
                failed += 1

        return {
            'success': True,
            'total': total,
            'parsed': parsed,
            'failed': failed,
            'results': results
        }

    def delete_parsed_data(self, filename: str) -> bool:
        """
        Delete parsed data for a file.

        Args:
            filename: Name of the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove parsed text file
            parsed_text_path = self.get_parsed_text_path(filename)
            if os.path.exists(parsed_text_path):
                os.remove(parsed_text_path)

            # Remove from state
            if filename in self.state:
                del self.state[filename]
                self._save_state()

            logger.info(f"Deleted parsed data for: {filename}")
            return True

        except Exception as e:
            logger.error(f"Error deleting parsed data for {filename}: {e}")
            return False

    # Knowledge extraction methods
    @property
    def knowledge_extractor(self):
        """Lazy-load knowledge extractor."""
        if self._knowledge_extractor is None:
            try:
                # Get spaCy model from config
                spacy_model = Config.SPACY_MODEL

                # Determine if LLM should be enabled
                # Check if API key is configured for the selected backend
                use_llm = False
                llm_backend = Config.LLM_BACKEND

                if llm_backend == "openai":
                    use_llm = bool(Config.OPENAI_API_KEY)
                elif llm_backend == "anthropic":
                    use_llm = bool(Config.OPENAI_API_KEY)  # Assuming same env var for Anthropic
                elif llm_backend == "ollama":
                    # Ollama runs locally, assume available
                    use_llm = True

                logger.info(f"Initializing KnowledgeExtractor with spaCy model: {spacy_model}, LLM enabled: {use_llm}")
                self._knowledge_extractor = KnowledgeExtractor(spacy_model=spacy_model, use_llm=use_llm)
            except Exception as e:
                logger.error(f"Failed to initialize KnowledgeExtractor: {e}")
                # Create a dummy extractor that returns empty results
                class DummyExtractor:
                    def extract_from_text(self, text, document_id=None, extraction_methods=None):
                        return {"entities": [], "relationships": [], "triplets": []}
                self._knowledge_extractor = DummyExtractor()
        return self._knowledge_extractor

    @property
    def triplet_extractor(self):
        """Lazy-load triplet extractor."""
        if self._triplet_extractor is None:
            self._triplet_extractor = TripletExtractor()
        return self._triplet_extractor

    def extract_knowledge(self, filename: str) -> Dict[str, Any]:
        """
        Extract knowledge from parsed text of a file.

        Args:
            filename: Name of the file

        Returns:
            Dictionary with knowledge extraction results
        """
        # Check if file is parsed
        state = self.get_file_state(filename)
        if not state.get('parsed', False):
            return {
                'success': False,
                'error': f"File not parsed: {filename}",
                'filename': filename
            }

        # Get parsed text
        parsed_text = self.get_parsed_text(filename)
        if not parsed_text:
            return {
                'success': False,
                'error': f"No parsed text found for: {filename}",
                'filename': filename
            }

        try:
            logger.info(f"Extracting knowledge from: {filename}")

            # Extract knowledge using NLP
            extraction_result = self.knowledge_extractor.extract_from_text(
                text=parsed_text,
                document_id=filename
            )

            # Convert to triplets for graph building
            triplets = self.triplet_extractor.knowledge_extractor_result_to_triplets(
                extraction_result
            )

            # Prepare triplets for graph builder
            graph_triplets = self.triplet_extractor.create_graph_builder_input(
                triplets=triplets,
                source_document=filename
            )

            # Save extraction results
            extraction_path = self.get_knowledge_extraction_path(filename)
            os.makedirs(os.path.dirname(extraction_path), exist_ok=True)

            extraction_data = {
                'filename': filename,
                'extraction_result': extraction_result,
                'triplets': graph_triplets,
                'extraction_timestamp': datetime.now().isoformat()
            }

            with open(extraction_path, 'w', encoding='utf-8') as f:
                json.dump(extraction_data, f, indent=2, default=str)

            # Update state with extraction info
            self.update_file_state(
                filename,
                knowledge_extracted=True,
                knowledge_extracted_at=datetime.now().isoformat(),
                entity_count=len(extraction_result.get('entities', [])),
                relationship_count=len(extraction_result.get('relationships', [])),
                triplet_count=len(graph_triplets)
            )

            logger.info(f"Successfully extracted knowledge from {filename}: "
                       f"{len(extraction_result.get('entities', []))} entities, "
                       f"{len(extraction_result.get('relationships', []))} relationships, "
                       f"{len(graph_triplets)} triplets")

            return {
                'success': True,
                'filename': filename,
                'extraction_result': extraction_result,
                'triplets': graph_triplets,
                'entity_count': len(extraction_result.get('entities', [])),
                'relationship_count': len(extraction_result.get('relationships', [])),
                'triplet_count': len(graph_triplets),
                'extraction_timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Error extracting knowledge from {filename}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'filename': filename
            }

    def get_knowledge_extraction_path(self, filename: str) -> str:
        """
        Get path for storing knowledge extraction results.

        Args:
            filename: Name of the file

        Returns:
            Path to extraction results file
        """
        # Create a safe filename for extraction results
        base_name = os.path.splitext(filename)[0]
        safe_name = ''.join(c if c.isalnum() else '_' for c in base_name)
        extraction_dir = os.path.join(self.parsed_data_folder, 'knowledge_extractions')
        return os.path.join(extraction_dir, f"{safe_name}_knowledge.json")

    def get_extracted_knowledge(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get extracted knowledge for a file.

        Args:
            filename: Name of the file

        Returns:
            Extraction results or None if not extracted
        """
        extraction_path = self.get_knowledge_extraction_path(filename)

        if not os.path.exists(extraction_path):
            return None

        try:
            with open(extraction_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading extraction results for {filename}: {e}")
            return None

    def build_graph_from_extraction(self, filename: str) -> Dict[str, Any]:
        """
        Build knowledge graph from extracted knowledge.

        Args:
            filename: Name of the file

        Returns:
            Dictionary with graph building results
        """
        # Get extracted knowledge
        extraction_data = self.get_extracted_knowledge(filename)
        if not extraction_data:
            return {
                'success': False,
                'error': f"No extracted knowledge found for: {filename}",
                'filename': filename
            }

        triplets = extraction_data.get('triplets', [])
        if not triplets:
            return {
                'success': False,
                'error': f"No triplets found in extraction for: {filename}",
                'filename': filename,
                'triplet_count': 0
            }

        try:
            # Import here to avoid circular imports
            from src.knowledge_graph.graph_builder import GraphBuilder

            # Initialize graph builder
            graph_builder = GraphBuilder()

            # Build graph from triplets
            build_result = graph_builder.build_graph_from_triplets(
                triplets=triplets,
                source_document=filename
            )

            logger.info(f"Built graph from {filename}: {build_result}")

            # Save graph building results
            graph_path = self.get_graph_building_path(filename)
            os.makedirs(os.path.dirname(graph_path), exist_ok=True)

            graph_data = {
                'filename': filename,
                'build_result': build_result,
                'triplet_count': len(triplets),
                'graph_built_at': datetime.now().isoformat()
            }

            with open(graph_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, default=str)

            return {
                'success': True,
                'filename': filename,
                'build_result': build_result,
                'triplet_count': len(triplets),
                'graph_built_at': datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Error building graph from {filename}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'filename': filename
            }

    def get_graph_building_path(self, filename: str) -> str:
        """
        Get path for storing graph building results.

        Args:
            filename: Name of the file

        Returns:
            Path to graph building results file
        """
        # Create a safe filename for graph results
        base_name = os.path.splitext(filename)[0]
        safe_name = ''.join(c if c.isalnum() else '_' for c in base_name)
        graph_dir = os.path.join(self.parsed_data_folder, 'graph_builds')
        return os.path.join(graph_dir, f"{safe_name}_graph.json")