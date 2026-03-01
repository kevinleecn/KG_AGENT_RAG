"""
Knowledge Graph Document QA Demo System - Main Application
Phase 2: Document Parsing System
"""

import os
# Set environment variables for Neo4j
os.environ["NEO4J_PASSWORD"] = "neo4j168"
os.environ["NEO4J_USER"] = "neo4j"

print(f"[APP DEBUG] Environment NEO4J_USER: {os.environ.get('NEO4J_USER')}")
print(f"[APP DEBUG] Environment NEO4J_PASSWORD: {'*' * len(os.environ.get('NEO4J_PASSWORD', '')) if os.environ.get('NEO4J_PASSWORD') else 'None'}")

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import logging
from config.settings import get_config
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

        # Check if at least one file is selected
        if not files or files[0].filename == '':
            return jsonify({'error': 'No selected files'}), 400

        uploaded_files = []
        skipped_files = []

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
                    'parsing_metadata': parsing_state.get('metadata', {})
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


# Graph visualization endpoints
@app.route('/graph')
def graph_view():
    """Render graph visualization page."""
    return render_template('graph.html')


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


@app.route('/graph/extract/<filename>')
def extract_knowledge_for_file(filename):
    """Extract knowledge and build graph for a file."""
    try:
        # Extract knowledge
        extraction_result = parsing_manager.extract_knowledge(filename)

        if not extraction_result.get('success', False):
            return jsonify(extraction_result)

        # Build graph from extraction
        build_result = parsing_manager.build_graph_from_extraction(filename)

        return jsonify({
            'success': True,
            'filename': filename,
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
    """处理聊天问题"""
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