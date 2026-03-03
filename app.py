"""
Knowledge Graph Document QA Demo System - Main Application
Phase 2: Document Parsing System

Configuration is now managed through the web interface and stored securely:
- LLM API settings (Base URL, API Key) are encrypted
- Neo4j connection settings (URI, Username, Password) are encrypted
- Configuration file: config/user_config.json
- Encryption key: config/.encryption_key

DO NOT hardcode sensitive credentials in this file!
"""

# Initialize configuration manager first
config_manager = get_config_manager()

# Load configuration and set environment variables
llm_config = config_manager.get_llm_config()
neo4j_config = config_manager.get_neo4j_config()

os.environ["NEO4J_URI"] = neo4j_config.get('uri', 'bolt://localhost:7687')
os.environ["NEO4J_USER"] = neo4j_config.get('username', 'neo4j')
os.environ["NEO4J_PASSWORD"] = neo4j_config.get('password', '')

os.environ["OPENAI_API_KEY"] = llm_config.get('api_key', '')
os.environ["OPENAI_BASE_URL"] = llm_config.get('base_url', 'https://api.deepseek.com')
os.environ["LLM_BACKEND"] = llm_config.get('backend', 'openai')
os.environ["LLM_MODEL"] = llm_config.get('model', 'deepseek-chat')

logger.info(f"[Config] Neo4j URI: {os.environ.get('NEO4J_URI')}")
logger.info(f"[Config] Neo4j User: {os.environ.get('NEO4J_USER')}")
logger.info(f"[Config] LLM Backend: {os.environ.get('LLM_BACKEND')}")
logger.info(f"[Config] LLM Model: {os.environ.get('LLM_MODEL')}")

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import logging
from config.settings import get_config
from config.config_manager import get_config_manager
from src.parsing_manager import ParsingManager
from src.knowledge_graph.graph_builder import GraphBuilder
from src.qa.kg_qa_engine import KGQAEngine

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app with configuration
app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# Ensure directories exist
config.ensure_directories()

# Initialize parsing manager
parsing_manager = ParsingManager(
    upload_folder=app.config['UPLOAD_FOLDER'],
    parsed_data_folder=app.config['PARSED_DATA_FOLDER']
)

def allowed_file(filename):
    """Check if file has allowed extension"""
    if not filename:
        return False
    _, ext = os.path.splitext(filename)
    return ext.lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Render main page with file upload"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    try:
        # Check if files are present
        if 'files' not in request.files:
            return jsonify({'error': 'No files part'}), 400

        files = request.files.getlist('files')

        # 获取提取方法参数（默认为 spacy）
        extraction_method = request.form.get('extraction_method', 'spacy')
        if extraction_method not in ['spacy', 'llm']:
            extraction_method = 'spacy'

        # Check if at least one file is selected
        if not files or files[0].filename == '':
            return jsonify({'error': 'No selected files'}), 400

        uploaded_files = []
        skipped_files = []
        parsing_tasks = []

        for file in files:
            if file and allowed_file(file.filename):
                # Secure filename and save
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                # Avoid overwriting existing files
                counter = 1
                name, ext = os.path.splitext(filename)
                while os.path.exists(filepath):
                    filename = f"{name}_{counter}{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    counter += 1

                file.save(filepath)
                uploaded_files.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'url': f"/uploads/{filename}"
                })
                logger.info(f"Uploaded file: {filename}")

                # Start async parsing automatically after upload with extraction method
                try:
                    task_id = parsing_manager.parse_file_async(filename, extraction_method=extraction_method)
                    parsing_tasks.append({
                        'filename': filename,
                        'task_id': task_id,
                        'progress_url': f'/progress/{task_id}'
                    })
                    logger.info(f"Started async parsing for {filename} with task ID: {task_id}, method: {extraction_method}")
                except Exception as parse_error:
                    logger.error(f"Error starting async parsing for {filename}: {str(parse_error)}")
                    # Fall back to sync parsing if async fails
                    try:
                        parse_result = parsing_manager.parse_file(filename)
                        if parse_result.get('success', False):
                            logger.info(f"Fallback sync parsing succeeded for {filename}")
                        else:
                            logger.warning(f"Fallback sync parsing failed for {filename}")
                    except Exception as sync_error:
                        logger.error(f"Fallback sync parsing also failed for {filename}: {str(sync_error)}")
            else:
                skipped_files.append(file.filename)
                logger.warning(f"Skipped invalid file: {file.filename}")

        response = {
            'success': True,
            'uploaded': uploaded_files,
            'skipped': skipped_files,
            'message': f'Successfully uploaded {len(uploaded_files)} file(s)'
        }

        if skipped_files:
            response['warning'] = f'Skipped {len(skipped_files)} invalid file(s)'

        if parsing_tasks:
            response['parsing_tasks'] = parsing_tasks
            response['parsing_started'] = len(parsing_tasks)
            response['parsing_message'] = f'Started parsing for {len(parsing_tasks)} file(s) in background'

        return jsonify(response)

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'kg-qa-demo'})


# ==================== Configuration Management API ====================

@app.route('/api/config', methods=['GET'])
def get_configuration():
    """
    Get current configuration (with masked sensitive fields).

    Returns:
        JSON response with configuration summary
    """
    try:
        config_manager = get_config_manager()
        summary = config_manager.get_config_summary()

        return jsonify({
            'success': True,
            'config': summary,
            'validation': config_manager.validate_config()
        })
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def save_configuration():
    """
    Save user configuration.

    Request JSON:
    {
        "llm": {
            "base_url": "https://api.deepseek.com",
            "api_key": "sk-xxx",
            "model": "deepseek-chat",
            "backend": "openai"
        },
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password123",
            "database": "neo4j"
        }
    }

    Returns:
        JSON response with success status
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        config_manager = get_config_manager()

        # Update configuration
        config_manager.update_config(data)

        # Reload environment variables for immediate effect
        llm_config = config_manager.get_llm_config()
        neo4j_config = config_manager.get_neo4j_config()

        os.environ["NEO4J_URI"] = neo4j_config.get('uri', 'bolt://localhost:7687')
        os.environ["NEO4J_USER"] = neo4j_config.get('username', 'neo4j')
        os.environ["NEO4J_PASSWORD"] = neo4j_config.get('password', '')
        os.environ["OPENAI_API_KEY"] = llm_config.get('api_key', '')
        os.environ["OPENAI_BASE_URL"] = llm_config.get('base_url', 'https://api.deepseek.com')
        os.environ["LLM_BACKEND"] = llm_config.get('backend', 'openai')
        os.environ["LLM_MODEL"] = llm_config.get('model', 'deepseek-chat')

        logger.info("Configuration updated successfully")

        return jsonify({
            'success': True,
            'message': 'Configuration saved successfully',
            'config': config_manager.get_config_summary()
        })
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config/validate', methods=['POST'])
def validate_configuration():
    """
    Validate and test configuration by attempting connections.

    Request JSON (optional test data):
    {
        "test_llm": true,
        "test_neo4j": true
    }

    Returns:
        JSON response with validation results
    """
    try:
        data = request.get_json() or {}
        config_manager = get_config_manager()
        config = config_manager.get_config()

        results = {
            'llm': {'configured': False, 'reachable': False, 'error': None},
            'neo4j': {'configured': False, 'reachable': False, 'error': None}
        }

        # Validate LLM configuration
        llm_config = config.get('llm', {})
        if llm_config.get('api_key'):
            results['llm']['configured'] = True

            if data.get('test_llm', True):
                try:
                    from openai import OpenAI
                    client = OpenAI(
                        api_key=llm_config['api_key'],
                        base_url=llm_config.get('base_url', 'https://api.deepseek.com')
                    )
                    # Simple API call to test connection
                    client.models.list()
                    results['llm']['reachable'] = True
                except Exception as e:
                    results['llm']['error'] = str(e)
                    logger.warning(f"LLM connection test failed: {e}")

        # Validate Neo4j configuration
        neo4j_config = config.get('neo4j', {})
        if neo4j_config.get('password'):
            results['neo4j']['configured'] = True

            if data.get('test_neo4j', True):
                try:
                    from src.knowledge_graph.neo4j_adapter import Neo4jAdapter
                    adapter = Neo4jAdapter(
                        uri=neo4j_config.get('uri', 'bolt://localhost:7687'),
                        user=neo4j_config.get('username', 'neo4j'),
                        password=neo4j_config.get('password', ''),
                        database=neo4j_config.get('database', 'neo4j')
                    )
                    # Test connection with a simple query
                    adapter.query("RETURN 1")
                    results['neo4j']['reachable'] = True
                except Exception as e:
                    results['neo4j']['error'] = str(e)
                    logger.warning(f"Neo4j connection test failed: {e}")

        all_passed = (
            results['llm']['configured'] and
            results['llm']['reachable'] and
            results['neo4j']['configured'] and
            results['neo4j']['reachable']
        )

        return jsonify({
            'success': True,
            'validation': results,
            'all_passed': all_passed
        })
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config/reset', methods=['POST'])
def reset_configuration():
    """
    Reset configuration to defaults.

    Returns:
        JSON response with success status
    """
    try:
        config_manager = get_config_manager()
        config_manager.reset_to_defaults()

        logger.info("Configuration reset to defaults")

        return jsonify({
            'success': True,
            'message': 'Configuration reset to defaults'
        })
    except Exception as e:
        logger.error(f"Failed to reset configuration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/files')
def list_files():
    """List all uploaded files"""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']

        # Ensure the upload folder exists
        if not os.path.exists(upload_folder):
            return jsonify({
                'success': True,
                'files': [],
                'count': 0,
                'total_size': 0,
                'formatted_total_size': '0 Bytes'
            })

        files = []
        total_size = 0

        # Scan the upload directory
        for filename in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, filename)

            # Skip directories, only include files
            if os.path.isfile(filepath):
                # Get file info
                stat = os.stat(filepath)
                size = stat.st_size
                modified_time = stat.st_mtime

                # Get file extension
                _, ext = os.path.splitext(filename)
                ext = ext.lower()

                # Get parsing state
                parsing_state = parsing_manager.get_file_state(filename)

                files.append({
                    'filename': filename,
                    'name': filename,  # For frontend compatibility
                    'size': size,
                    'url': f"/uploads/{filename}",
                    'modified': modified_time,
                    'extension': ext,
                    'formatted_size': _format_file_size(size),
                    'formatted_modified': _format_timestamp(modified_time),
                    # Parsing state fields
                    'parsed': parsing_state.get('parsed', False),
                    'parsed_at': parsing_state.get('parsed_at'),
                    'parsing_error': parsing_state.get('error'),
                    'text_length': parsing_state.get('text_length', 0),
                    'word_count': parsing_state.get('word_count', 0),
                    'parsing_metadata': parsing_state.get('metadata', {}),
                    # Extract extraction_method from metadata for easy access
                    'extraction_method': parsing_state.get('metadata', {}).get('extraction_method', 'spacy')
                })

                total_size += size

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)

        return jsonify({
            'success': True,
            'files': files,
            'count': len(files),
            'total_size': total_size,
            'formatted_total_size': _format_file_size(total_size)
        })

    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete an uploaded file and all associated data"""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)

        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': f'File not found: {filename}'
            }), 404

        # Verify it's a file, not a directory
        if not os.path.isfile(filepath):
            return jsonify({
                'success': False,
                'error': f'Not a file: {filename}'
            }), 400

        # Delete associated parsed data
        try:
            parsed_text_path = parsing_manager.get_parsed_text_path(filename)
            if os.path.exists(parsed_text_path):
                os.remove(parsed_text_path)
                logger.info(f"Deleted parsed text: {parsed_text_path}")
        except Exception as e:
            logger.warning(f"Failed to delete parsed text: {e}")

        # Delete associated knowledge extraction data
        try:
            extraction_path = parsing_manager.get_knowledge_extraction_path(filename)
            if os.path.exists(extraction_path):
                os.remove(extraction_path)
                logger.info(f"Deleted knowledge extraction: {extraction_path}")
        except Exception as e:
            logger.warning(f"Failed to delete knowledge extraction: {e}")

        # Delete associated graph data
        try:
            graph_path = parsing_manager.get_graph_path(filename)
            if os.path.exists(graph_path):
                os.remove(graph_path)
                logger.info(f"Deleted graph data: {graph_path}")
        except Exception as e:
            logger.warning(f"Failed to delete graph data: {e}")

        # Delete parsing state file
        try:
            state_path = parsing_manager.get_parsing_state_path(filename)
            if os.path.exists(state_path):
                os.remove(state_path)
                logger.info(f"Deleted parsing state: {state_path}")
        except Exception as e:
            logger.warning(f"Failed to delete parsing state: {e}")

        # Delete the uploaded file
        os.remove(filepath)
        logger.info(f"Deleted uploaded file: {filepath}")

        # Delete from Neo4j (optional - if graph was built)
        try:
            parsing_manager.graph_db.delete_document_graph(filename)
            logger.info(f"Deleted Neo4j entities for document: {filename}")
        except Exception as e:
            logger.warning(f"Failed to delete Neo4j entities: {e}")

        return jsonify({
            'success': True,
            'message': f'File "{filename}" and all associated data deleted successfully',
            'filename': filename
        })

    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to delete file: {str(e)}'
        }), 500


def _format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 Bytes"

    units = ['Bytes', 'KB', 'MB', 'GB']
    unit_index = 0

    while size_bytes >= 1024 and unit_index < len(units) - 1:
        size_bytes /= 1024
        unit_index += 1

    return f"{size_bytes:.2f} {units[unit_index]}"


def _format_timestamp(timestamp):
    """Format timestamp to readable date"""
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


@app.route('/parse/<filename>', methods=['POST'])
def parse_file(filename):
    """Parse a single file"""
    try:
        # Check if file exists
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': f'File not found: {filename}'
            }), 404

        # Parse the file
        result = parsing_manager.parse_file(filename)

        if result.get('success', False):
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error parsing file {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/parse/all', methods=['POST'])
def parse_all_files():
    """Parse all uploaded files"""
    try:
        result = parsing_manager.parse_all_files()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error parsing all files: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/parsed/<filename>', methods=['GET'])
def get_parsed_text(filename):
    """Get parsed text for a file"""
    try:
        # Check if file exists
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': f'File not found: {filename}'
            }), 404

        # Get parsing state
        parsing_state = parsing_manager.get_file_state(filename)

        if not parsing_state.get('parsed', False):
            return jsonify({
                'success': False,
                'error': f'File not parsed: {filename}',
                'parsed': False
            }), 404

        # Get parsed text
        parsed_text = parsing_manager.get_parsed_text(filename)

        if parsed_text is None:
            return jsonify({
                'success': False,
                'error': f'Parsed text not found for: {filename}',
                'parsed': True
            }), 404

        return jsonify({
            'success': True,
            'filename': filename,
            'parsed_text': parsed_text,
            'text_length': len(parsed_text),
            'word_count': len(parsed_text.split()),
            'parsed_at': parsing_state.get('parsed_at'),
            'metadata': parsing_state.get('metadata', {})
        })

    except Exception as e:
        logger.error(f"Error getting parsed text for {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/parsing/status', methods=['GET'])
def get_parsing_status():
    """Get parsing status for all files"""
    try:
        files_state = parsing_manager.get_all_files_state()

        # Calculate statistics
        total_files = len(files_state)
        parsed_files = sum(1 for f in files_state if f.get('parsed', False))
        failed_files = sum(1 for f in files_state if f.get('error') and not f.get('parsed', False))

        return jsonify({
            'success': True,
            'total_files': total_files,
            'parsed_files': parsed_files,
            'failed_files': failed_files,
            'pending_files': total_files - parsed_files - failed_files,
            'files': files_state
        })

    except Exception as e:
        logger.error(f"Error getting parsing status: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


# Progress tracking endpoints
@app.route('/parse/async/<filename>', methods=['POST'])
def parse_file_async(filename):
    """Start asynchronous parsing of a file with progress tracking"""
    try:
        # Check if file exists
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': f'File not found: {filename}'
            }), 404

        # Get extraction method from request
        data = request.get_json() or {}
        extraction_method = data.get('extraction_method', 'spacy')  # Default to spacy

        # Start async parsing with extraction method
        task_id = parsing_manager.parse_file_async(filename, extraction_method=extraction_method)

        return jsonify({
            'success': True,
            'task_id': task_id,
            'filename': filename,
            'extraction_method': extraction_method,
            'message': f'Started asynchronous parsing for {filename} using {extraction_method}',
            'progress_url': f'/progress/{task_id}'
        })

    except FileNotFoundError as e:
        logger.error(f"File not found for async parsing {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404

    except Exception as e:
        logger.error(f"Error starting async parsing for {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """Get progress status for a task"""
    try:
        progress = parsing_manager.get_parsing_progress(task_id)

        if not progress:
            return jsonify({
                'success': False,
                'error': f'Task not found: {task_id}'
            }), 404

        return jsonify({
            'success': True,
            'progress': progress
        })

    except Exception as e:
        logger.error(f"Error getting progress for task {task_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/progress/all', methods=['GET'])
def get_all_progress():
    """Get progress status for all tasks"""
    try:
        tasks = parsing_manager.get_all_parsing_tasks()

        return jsonify({
            'success': True,
            'total_tasks': len(tasks),
            'tasks': tasks
        })

    except Exception as e:
        logger.error(f"Error getting all progress: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/progress/cancel/<task_id>', methods=['POST'])
def cancel_progress(task_id):
    """Cancel a parsing task"""
    try:
        logger.info(f"Cancel request received for task {task_id}")
        success = parsing_manager.cancel_parsing(task_id)
        logger.info(f"Cancel result for task {task_id}: {success}")

        if not success:
            return jsonify({
                'success': False,
                'error': f'Task not found or cannot be cancelled: {task_id}'
            }), 404

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Task {task_id} cancelled successfully'
        })

    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/progress/file/<filename>', methods=['GET'])
def get_progress_for_file(filename):
    """Get progress status for all tasks of a file"""
    try:
        # Check if file exists
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': f'File not found: {filename}'
            }), 404

        tasks = parsing_manager.get_tasks_for_file(filename)

        return jsonify({
            'success': True,
            'filename': filename,
            'total_tasks': len(tasks),
            'tasks': tasks
        })

    except Exception as e:
        logger.error(f"Error getting progress for file {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


# Graph visualization endpoints
@app.route('/graph')
def graph_view():
    """Render graph visualization page."""
    return render_template('graph.html')


@app.route('/settings')
def settings_page():
    """Render settings page."""
    return render_template('settings.html')


@app.route('/chat')
def chat_page():
    """Render chat page."""
    return render_template('chat.html')


@app.route('/graph/data')
def get_graph_data():
    """Get graph data for visualization."""
    try:
        print(f"[APP DEBUG] Getting graph data, document_id param: {request.args.get('document_id')}")
        logger.debug(f"Getting graph data, document_id param: {request.args.get('document_id')}")

        # Initialize graph builder
        graph_builder = GraphBuilder()
        print(f"[APP DEBUG] GraphBuilder initialized, connected: {graph_builder.graph_db.connected}")
        logger.debug(f"GraphBuilder initialized, connected: {graph_builder.graph_db.connected}")

        # Get graph data for visualization
        document_id = request.args.get('document_id', None)
        print(f"[APP DEBUG] Calling get_graph_for_visualization with document_id: {document_id}")
        logger.debug(f"Calling get_graph_for_visualization with document_id: {document_id}")
        graph_data = graph_builder.get_graph_for_visualization(document_id)

        print(f"[APP DEBUG] Graph data returned: {len(graph_data.get('nodes', []))} nodes, {len(graph_data.get('links', []))} links")
        logger.debug(f"Graph data returned: {len(graph_data.get('nodes', []))} nodes, {len(graph_data.get('links', []))} links")

        return jsonify({
            'success': True,
            'graph_data': graph_data,
            'document_id': document_id
        })
    except Exception as e:
        logger.error(f"Error getting graph data: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/graph/build/<filename>')
def build_graph_for_file(filename):
    """Build graph for a specific file."""
    try:
        # Build graph from file extraction
        result = parsing_manager.build_graph_from_extraction(filename)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error building graph for {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/graph/extract/<filename>', methods=['POST'])
def extract_knowledge_for_file(filename):
    """Extract knowledge and build graph for a file."""
    try:
        # Get extraction method from request
        data = request.get_json() or {}
        extraction_method = data.get('extraction_method', 'spacy')

        # Extract knowledge with selected method
        extraction_result = parsing_manager.extract_knowledge(filename, extraction_method=extraction_method)

        if not extraction_result.get('success', False):
            return jsonify(extraction_result)

        # Build graph from extraction
        build_result = parsing_manager.build_graph_from_extraction(filename)

        return jsonify({
            'success': True,
            'filename': filename,
            'extraction_method': extraction_method,
            'extraction_result': extraction_result,
            'build_result': build_result
        })
    except Exception as e:
        logger.error(f"Error extracting and building graph for {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


# Chat endpoints
@app.route('/chat/ask', methods=['POST'])
def chat_ask():
    """处理聊天问题（基础版）"""
    try:
        data = request.get_json()
        question = data.get('question')
        document_id = data.get('document_id')
        chat_history = data.get('chat_history', [])

        if not question:
            return jsonify({'success': False, 'error': 'No question provided'}), 400

        # 初始化问答引擎
        qa_engine = KGQAEngine()

        # 获取答案
        answer, sources = qa_engine.ask_question(
            question=question,
            document_id=document_id,
            chat_history=chat_history
        )

        return jsonify({
            'success': True,
            'answer': answer,
            'sources': sources,
            'question': question
        })

    except Exception as e:
        logger.error(f"Error in chat_ask: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/chat/ask-enhanced', methods=['POST'])
def chat_ask_enhanced():
    """
    融合问答接口 - 真正的 KG-LLM 融合推理

    功能:
    - 智能问题分类（图谱内/外/融合）
    - 图谱外问题直接用 LLM 回答
    - 图谱内问题用图谱数据增强
    - 融合问题结合图谱检索和 LLM 推理

    参数:
    - question: 用户问题
    - document_id: 可选文档 ID
    - chat_history: 聊天历史
    """
    try:
        data = request.get_json()
        question = data.get('question')
        document_id = data.get('document_id')
        chat_history = data.get('chat_history', [])

        if not question:
            return jsonify({'success': False, 'error': 'No question provided'}), 400

        # 初始化融合问答引擎
        from src.qa.fusion_qa_engine import FusionKGQAEngine
        qa_engine = FusionKGQAEngine()

        # 获取完整响应
        response = qa_engine.ask_question(
            question=question,
            document_id=document_id,
            chat_history=chat_history
        )

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in chat_ask_enhanced: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'answer': f'处理问题时发生错误：{str(e)}',
            'error': str(e)
        }), 500


@app.route('/chat/assistant-info', methods=['GET'])
def chat_assistant_info():
    """获取助手信息（模型、能力等）"""
    try:
        from src.qa.fusion_qa_engine import FusionKGQAEngine
        engine = FusionKGQAEngine()
        info = engine.get_assistant_info()
        return jsonify({
            'success': True,
            'assistant': info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/chat/reason', methods=['POST'])
def chat_reason():
    """
    深度推理接口 - 支持特殊推理任务

    支持的推理类型:
    - multihop: 多跳推理（查找实体间关联）
    - hypothetical: 假设性推理（What-if 分析）
    - comparison: 实体比较

    参数:
    - type: 推理类型
    - question: 问题
    - entities: 实体列表（多跳/比较需要）
    - context: 上下文数据
    """
    try:
        data = request.get_json()
        reason_type = data.get('type', 'multihop')
        question = data.get('question')
        entities = data.get('entities', [])
        context = data.get('context', {})

        if not question:
            return jsonify({'success': False, 'error': 'No question provided'}), 400

        # 初始化 LLM 推理器
        from src.qa.llm_reasoner import LLMReasoner
        from config.settings import Config

        reasoner = LLMReasoner(
            api_key=Config.OPENAI_API_KEY,
            model=Config.LLM_MODEL,
            backend=Config.LLM_BACKEND,
            base_url=getattr(Config, 'OPENAI_BASE_URL', None)
        )

        # 根据类型执行不同推理
        if reason_type == 'multihop':
            result = reasoner.perform_multihop_reasoning(question, entities, max_hops=3)
        elif reason_type == 'hypothetical':
            result = reasoner.answer_hypothetical_question(question, context)
        elif reason_type == 'comparison':
            aspects = data.get('aspects', [])
            result = reasoner.compare_entities(entities, aspects, context)
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown reason type: {reason_type}'
            }), 400

        return jsonify({
            'success': True,
            'result': result,
            'type': reason_type
        })

    except Exception as e:
        logger.error(f"Error in chat_reason: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/chat/history', methods=['GET'])
def get_chat_history():
    """获取聊天历史（占位符）"""
    return jsonify({
        'success': True,
        'history': [],
        'message': 'Chat history endpoint - to be implemented'
    })

@app.route('/chat/clear', methods=['POST'])
def clear_chat_history():
    """清除聊天历史（占位符）"""
    return jsonify({
        'success': True,
        'message': 'Chat history cleared (placeholder)'
    })

if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000)