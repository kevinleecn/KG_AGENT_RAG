"""
Parsing Manager for Knowledge Graph QA Demo System
Handles document parsing state and result storage.
"""

import os
import json
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from src.document_parser.parser_factory import ParserFactory
from src.nlp.knowledge_extractor import KnowledgeExtractor
from src.nlp.triplet_extractor import TripletExtractor
from src.progress_manager import ProgressManager, TaskType, TaskStatus
from config.settings import Config

logger = logging.getLogger(__name__)


class ParsingManager:
    """Manages document parsing state and results"""

    # 全局取消标志存储
    _cancel_events: Dict[str, threading.Event] = {}

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

        # Progress manager for tracking parsing progress
        progress_data_folder = os.path.join(self.parsed_data_folder, 'progress')
        self.progress_manager = ProgressManager(progress_data_folder)

        # Async parsing thread management
        self._parse_threads: Dict[str, threading.Thread] = {}

        # Cancellation events for immediate task termination
        self._cancel_events: Dict[str, threading.Event] = {}

    def _set_cancel_event(self, task_id: str) -> None:
        """Set cancellation event for a task."""
        self._cancel_events[task_id] = threading.Event()

    def _clear_cancel_event(self, task_id: str) -> None:
        """Clear cancellation event for a task."""
        if task_id in self._cancel_events:
            del self._cancel_events[task_id]

    def _is_cancelled(self, task_id: str) -> bool:
        """Check if task has been cancelled."""
        cancel_event = self._cancel_events.get(task_id)
        if cancel_event and cancel_event.is_set():
            logger.info(f"Task {task_id} cancellation detected via event")
            return True
        # Also check progress manager state
        state = self.progress_manager.get_task_state(task_id)
        if state and state.status.name == 'CANCELLED':
            logger.info(f"Task {task_id} cancellation detected via status")
            return True
        return False

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

            # Check if parsed text is empty or contains only whitespace
            if not parsed_text or not parsed_text.strip():
                error_msg = f"No text content extracted from file: {filename}. The file may be empty, contain only images, or have an unsupported format."
                logger.error(error_msg)
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

    def extract_knowledge(self, filename: str, extraction_method: str = 'spacy') -> Dict[str, Any]:
        """
        Extract knowledge from parsed text of a file.

        Args:
            filename: Name of the file
            extraction_method: Knowledge extraction method ('spacy' or 'llm')

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
            logger.info(f"Extracting knowledge from: {filename} using {extraction_method}")

            # Initialize knowledge extractor with selected method
            from src.nlp.knowledge_extractor import KnowledgeExtractor
            spacy_model = Config.SPACY_MODEL
            use_llm = (extraction_method == 'llm')

            # Create extractor with selected method
            knowledge_extractor = KnowledgeExtractor(spacy_model=spacy_model, use_llm=use_llm)

            # Extract knowledge using NLP
            extraction_result = knowledge_extractor.extract_from_text(
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
                'extraction_method': extraction_method,
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
                triplet_count=len(graph_triplets),
                extraction_method=extraction_method
            )

            logger.info(f"Successfully extracted knowledge from {filename} using {extraction_method}: "
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

    def get_graph_path(self, filename: str) -> str:
        """
        Get path for graph data file (alias for get_graph_building_path).

        Args:
            filename: Name of the file

        Returns:
            Path to graph data file
        """
        return self.get_graph_building_path(filename)

    def get_parsing_state_path(self, filename: str) -> str:
        """
        Get path for parsing state file.

        Args:
            filename: Name of the file

        Returns:
            Path to parsing state file
        """
        # Create a safe filename for state
        base_name = os.path.splitext(filename)[0]
        safe_name = ''.join(c if c.isalnum() else '_' for c in base_name)
        state_dir = os.path.join(self.parsed_data_folder, 'parsing_states')
        os.makedirs(state_dir, exist_ok=True)
        return os.path.join(state_dir, f"{safe_name}_state.json")

    # Progress tracking methods
    def parse_file_async(self, filename: str, progress_callback: Optional[Callable] = None,
                        extraction_method: str = 'spacy') -> str:
        """
        Parse a document file asynchronously with progress tracking.

        Args:
            filename: Name of the file to parse
            progress_callback: Optional callback function for progress updates
            extraction_method: Knowledge extraction method ('spacy' or 'llm')

        Returns:
            Task ID for tracking progress
        """
        file_path = os.path.join(self.upload_folder, filename)

        # Check if file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {filename}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Create progress task
        task_id = self.progress_manager.create_task(
            filename=filename,
            task_type=TaskType.PARSE,
            total_steps=100,  # Will be updated with actual page count
            metadata={'file_path': file_path, 'extraction_method': extraction_method}
        )

        # Create cancellation event for this task
        self._set_cancel_event(task_id)
        logger.info(f"Created cancellation event for task {task_id}")

        # Start parsing in background thread
        thread = threading.Thread(
            target=self._parse_file_worker,
            args=(filename, task_id, progress_callback, extraction_method),
            daemon=True
        )
        self._parse_threads[task_id] = thread
        thread.start()

        logger.info(f"Started async parsing for {filename} with task ID: {task_id}, method: {extraction_method}")
        return task_id

    def _parse_file_worker(self, filename: str, task_id: str,
                          progress_callback: Optional[Callable] = None,
                          extraction_method: str = 'spacy') -> None:
        """
        Worker function for async parsing.

        Args:
            filename: Name of the file to parse
            task_id: Progress task ID
            progress_callback: Optional callback function for progress updates
            extraction_method: Knowledge extraction method ('spacy' or 'llm')
        """
        file_path = os.path.join(self.upload_folder, filename)
        parsed_text_path = self.get_parsed_text_path(filename)

        try:
            # Get appropriate parser
            parser = self.parser_factory.get_parser(file_path)

            # Validate file
            if not parser.validate(file_path):
                error_msg = f"Invalid or unsupported file format: {filename}"
                self.progress_manager.fail_task(task_id, error_msg)
                return

            # Update progress: validation passed
            self.progress_manager.update_progress(
                task_id,
                current_step=5,
                step_description="File validated",
                message=f"Validated file format for {filename}"
            )

            # Parse the file with progress updates if parser supports it
            logger.info(f"Async parsing file: {filename}")

            # Check if parser supports progress callback
            if hasattr(parser, 'parse_with_progress'):
                # Use progress-aware parsing with cancellation check
                logger.info(f"Using parse_with_progress for {filename}, task_id: {task_id}")
                result = parser.parse_with_progress(
                    file_path,
                    progress_callback=lambda step, total, desc, msg: self._handle_progress_update_with_check(
                        task_id, step, total, desc, msg, progress_callback
                    ),
                    cancel_check=lambda: self._is_cancelled(task_id)
                )
            else:
                # Fall back to regular parsing with simulated progress
                self.progress_manager.update_progress(
                    task_id,
                    current_step=10,
                    step_description="Starting parsing",
                    message=f"Parsing {filename}..."
                )

                result = parser.parse(file_path)

                # Simulate progress for parsers without progress support
                if result.get('success', False):
                    metadata = result.get('metadata', {})
                    page_count = metadata.get('page_count', 1)

                    # Simulate progress based on page count with cancellation check
                    for page_num in range(page_count):
                        # Check for cancellation before each page
                        if self._is_cancelled(task_id):
                            logger.info(f"Parsing cancelled for {filename} at page {page_num + 1}/{page_count}")
                            return

                        progress = 10 + int((page_num + 1) * 80 / page_count)
                        self.progress_manager.update_progress(
                            task_id,
                            current_step=progress,
                            step_description=f"Parsing page {page_num + 1}/{page_count}",
                            message=f"Extracting text from page {page_num + 1}"
                        )
                        # Simulate delay for progress visualization
                        import time
                        time.sleep(0.1)

            # Check if task was cancelled before checking result
            if self._is_cancelled(task_id):
                logger.info(f"Task {task_id} cancelled during parsing, skipping result check for {filename}")
                return

            # Check if parsing was successful
            if not result.get('success', False):
                error_msg = result.get('error', 'Unknown parsing error')
                self.progress_manager.fail_task(task_id, error_msg)
                return

            # Update progress: parsing completed
            self.progress_manager.update_progress(
                task_id,
                current_step=90,
                step_description="Parsing completed",
                message=f"Text extraction completed for {filename}"
            )

            # Check if task was cancelled before saving results
            if self._is_task_cancelled(task_id):
                logger.info(f"Task {task_id} cancelled after parsing, skipping save for {filename}")
                return

            # Save parsed text
            parsed_text = result.get('content', '')
            if not parsed_text or not parsed_text.strip():
                error_msg = f"No text content extracted from file: {filename}"
                self.progress_manager.fail_task(task_id, error_msg)
                return

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

            # Update progress: saving results
            self.progress_manager.update_progress(
                task_id,
                current_step=95,
                step_description="Saving parsed text",
                message=f"Saving {text_length} characters to disk"
            )

            # Mark task as completed
            result_data = {
                'filename': filename,
                'text_length': text_length,
                'word_count': word_count,
                'metadata': result.get('metadata', {}),
                'parsed_at': datetime.now().isoformat()
            }

            logger.info(f"Async parsing completed for {filename}")

            # ================================
            # Step 2: Knowledge Extraction (LLM or spaCy)
            # ================================
            logger.info(f"Starting knowledge extraction for {filename} using {extraction_method}")

            # Update progress for knowledge extraction
            self.progress_manager.update_progress(
                task_id,
                current_step=96,
                step_description="Knowledge extraction",
                message=f"Extracting knowledge using {extraction_method.upper()}..."
            )

            try:
                # Call extract_knowledge to perform the actual extraction
                extraction_result = self.extract_knowledge(filename, extraction_method=extraction_method)

                if extraction_result.get('success', False):
                    entity_count = extraction_result.get('extraction_result', {}).get('entity_count', 0)
                    relation_count = extraction_result.get('extraction_result', {}).get('relationship_count', 0)
                    logger.info(f"Knowledge extraction successful for {filename}: {entity_count} entities, {relation_count} relations")

                    # Update progress for graph building
                    self.progress_manager.update_progress(
                        task_id,
                        current_step=98,
                        step_description="Building knowledge graph",
                        message="Building knowledge graph from extracted triplets..."
                    )

                    # Build the graph
                    build_result = self.build_graph_from_extraction(filename)

                    if build_result.get('success', False):
                        nodes_created = build_result.get('nodes_created', 0)
                        relationships_created = build_result.get('relationships_created', 0)
                        logger.info(f"Graph building successful for {filename}: {nodes_created} nodes, {relationships_created} relationships")

                        # Add extraction results to final result_data
                        result_data['extraction_method'] = extraction_method
                        result_data['entity_count'] = entity_count
                        result_data['relationship_count'] = relation_count
                        result_data['nodes_created'] = nodes_created
                        result_data['relationships_created'] = relationships_created
                    else:
                        logger.warning(f"Graph building failed for {filename}: {build_result.get('error', 'Unknown error')}")
                        result_data['graph_build_warning'] = build_result.get('error', 'Graph building failed')
                else:
                    extraction_error = extraction_result.get('error', 'Unknown extraction error')
                    logger.warning(f"Knowledge extraction failed for {filename}: {extraction_error}")
                    result_data['extraction_warning'] = extraction_error

            except Exception as extraction_error:
                logger.error(f"Error during knowledge extraction for {filename}: {str(extraction_error)}")
                result_data['extraction_error'] = str(extraction_error)

            # Finalize task completion with all results
            self.progress_manager.complete_task(
                task_id,
                result_data,
                message=f"Successfully parsed {filename} ({text_length} chars, {word_count} words)"
            )

            logger.info(f"Full pipeline completed for {filename}")

        except Exception as e:
            # Check if task was cancelled before failing
            if self._is_cancelled(task_id):
                logger.info(f"Task {task_id} was cancelled, skipping error handling for {filename}")
                return

            error_msg = f"Error parsing file {filename}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.progress_manager.fail_task(task_id, error_msg)

    def _handle_progress_update_with_check(self, task_id: str, step: int, total: int,
                               description: str, message: str,
                               external_callback: Optional[Callable] = None) -> None:
        """
        Handle progress update from parser with cancellation check.

        Args:
            task_id: Progress task ID
            step: Current step number
            total: Total steps
            description: Step description
            message: Progress message
            external_callback: Optional external callback function
        """
        # Check for cancellation before updating progress
        if self._is_cancelled(task_id):
            logger.info(f"Task {task_id} cancelled, stopping progress updates")
            return

        # Update progress manager
        self.progress_manager.update_progress(
            task_id,
            current_step=step,
            step_description=description,
            message=message,
            metadata_updates={'total_steps': total} if total > 0 else None
        )

        # Call external callback if provided
        if external_callback:
            try:
                external_callback(step, total, description, message)
            except Exception as e:
                logger.warning(f"Error in external progress callback: {e}")

    def _handle_progress_update(self, task_id: str, step: int, total: int,
                               description: str, message: str,
                               external_callback: Optional[Callable] = None) -> None:
        """
        Handle progress update from parser.

        Args:
            task_id: Progress task ID
            step: Current step number
            total: Total steps
            description: Step description
            message: Progress message
            external_callback: Optional external callback function
        """
        # Update progress manager
        self.progress_manager.update_progress(
            task_id,
            current_step=step,
            step_description=description,
            message=message,
            metadata_updates={'total_steps': total} if total > 0 else None
        )

        # Call external callback if provided
        if external_callback:
            try:
                external_callback(step, total, description, message)
            except Exception as e:
                logger.warning(f"Error in external progress callback: {e}")

    def get_parsing_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get parsing progress for a task.

        Args:
            task_id: Task ID

        Returns:
            Progress state dictionary or None if not found
        """
        state = self.progress_manager.get_task_state(task_id)
        if not state:
            return None

        return state.to_dict()

    def cancel_parsing(self, task_id: str) -> bool:
        """
        Cancel a parsing task.

        Args:
            task_id: Task ID

        Returns:
            True if successful, False otherwise
        """
        # Set cancellation event for immediate response
        # Get existing event and set it (don't create a new one!)
        cancel_event = self._cancel_events.get(task_id)
        if cancel_event:
            cancel_event.set()  # Signal cancellation
            logger.info(f"Set cancellation event for task {task_id}")
        else:
            logger.warning(f"No cancellation event found for task {task_id}")

        # Update task status
        result = self.progress_manager.cancel_task(
            task_id,
            message="Parsing cancelled by user"
        )

        # Wait for thread to finish (with timeout)
        thread = self._parse_threads.get(task_id)
        if thread and thread.is_alive():
            thread.join(timeout=2.0)  # Wait up to 2 seconds

        # Clean up
        self._clear_cancel_event(task_id)

        return result

    def get_all_parsing_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all parsing tasks.

        Returns:
            List of task state dictionaries
        """
        tasks = self.progress_manager.get_all_tasks()
        return [task.to_dict() for task in tasks]

    def get_tasks_for_file(self, filename: str) -> List[Dict[str, Any]]:
        """
        Get all tasks for a specific file.

        Args:
            filename: Name of the file

        Returns:
            List of task state dictionaries for the file
        """
        tasks = self.progress_manager.get_tasks_by_filename(filename)
        return [task.to_dict() for task in tasks]