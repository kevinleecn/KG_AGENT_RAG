# Knowledge Graph Document QA Demo System

A web-based demo system that allows users to upload documents, automatically extracts text to build a knowledge graph, and provides conversational Q&A interface leveraging the graph.

## Project Status

**Current Phase**: Phase 1 - Basic Interface & File Upload ✅

## Features

### Phase 1: Basic Interface & File Upload (Completed)
- ✅ Web interface built with Flask and Bootstrap 5
- ✅ File upload area with drag & drop support
- ✅ Support for multiple file formats: `.txt`, `.docx`, `.pdf`, `.pptx`
- ✅ File validation and size limits (16MB per file)
- ✅ Upload progress indication and success/error feedback
- ✅ Clean, responsive UI with file type indicators

### Planned Features
- Phase 2: Document parsing for all supported formats
- Phase 3: Knowledge graph construction using spaCy and NetworkX
- Phase 4: Conversational Q&A agent with OpenAI/local models
- Phase 5: Optimization, error handling, and polish

## Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd kg_agent_demo
   ```

2. **Create and activate virtual environment (recommended)**
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   *Note: Some dependencies may require system libraries. If you encounter issues:*
   - **Windows**: Install Visual C++ Build Tools
   - **macOS**: `xcode-select --install`
   - **Linux**: Install build-essential and python3-dev

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   - Navigate to `http://localhost:5000`
   - The file upload interface should be displayed

## Usage Guide

### Uploading Documents
1. Click the "Browse Files" button or drag & drop files onto the upload area
2. Select one or more files (TXT, DOCX, PDF, PPTX formats supported)
3. Review the selected files in the list
4. Click "Upload Files" to upload to the server
5. Wait for upload completion confirmation

### Features
- **Drag & Drop**: Drag files directly onto the upload area
- **Multi-select**: Select multiple files at once
- **File Validation**: Only allowed file types are accepted
- **Size Limit**: Maximum 16MB per file
- **Duplicate Prevention**: Automatic filename adjustment to avoid overwrites
- **Progress Feedback**: Visual indicators during upload

### Navigation
- **Upload**: Current page for document upload
- **Graph View**: Disabled (Phase 3 feature)
- **Chat**: Disabled (Phase 4 feature)

## Project Structure

```
kg_agent_demo/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── static/                         # Static assets
│   ├── css/
│   │   └── style.css              # Custom styles
│   ├── js/
│   │   └── main.js                # Frontend JavaScript
│   └── uploads/                    # Uploaded file storage
├── templates/                      # HTML templates
│   ├── base.html                  # Base template
│   └── index.html                 # Main upload interface
└── data/                          # Data storage (future use)
```

## API Endpoints

### Phase 1 Endpoints
- `GET /` - Main page with file upload interface
- `POST /upload` - File upload endpoint
- `GET /uploads/<filename>` - Serve uploaded files
- `GET /health` - Health check endpoint

### Upload Response Format
```json
{
  "success": true,
  "uploaded": [
    {
      "filename": "document.pdf",
      "size": 1234567,
      "url": "/uploads/document.pdf"
    }
  ],
  "skipped": [],
  "message": "Successfully uploaded 1 file(s)"
}
```

## Development

### Running in Development Mode
```bash
python app.py
```

The application runs in debug mode on `http://localhost:5000` with auto-reload on code changes.

### Testing
To run tests (Phase 1 tests will be added):
```bash
pytest
```

### Adding New Features
Follow the phase-based development approach:
1. Phase 1: Basic interface (✅ Complete)
2. Phase 2: Document parsing
3. Phase 3: Knowledge graph construction
4. Phase 4: Q&A agent
5. Phase 5: Optimization and polish

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt` again

2. **File upload fails**
   - Check file size (max 16MB)
   - Ensure file type is supported (.txt, .docx, .pdf, .pptx)
   - Check server logs for specific errors

3. **Server won't start**
   - Ensure port 5000 is not in use
   - Check Python version (3.8+ required)
   - Verify all dependencies are installed

### Logs
- Check console output for detailed error messages
- Application logs are printed to console with DEBUG level

## Next Steps

### Phase 2: Document Parsing
- Implement parsers for each file format
- Extract plain text from documents
- Handle encoding and formatting issues

### Phase 3: Knowledge Graph Construction
- Integrate spaCy for entity recognition
- Extract entity-relationship triplets
- Build NetworkX knowledge graph
- Add graph visualization

### Phase 4: Q&A Agent
- Implement graph-based retrieval
- Add vector similarity search
- Integrate OpenAI/local LLM
- Create chat interface

## License
This project is developed as a demonstration system. For production use, additional security and optimization measures are required.

## Acknowledgments
- Flask team for the excellent web framework
- Bootstrap team for the responsive UI components
- Font Awesome for the icon set
- All open-source libraries used in this project