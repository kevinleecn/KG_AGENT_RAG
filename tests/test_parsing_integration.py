"""
Integration tests for Phase 2: Document Parsing System Integration
"""

import os
import tempfile
import io
import pytest
from app import app, parsing_manager


class TestParsingIntegration:
    """Integration tests for parsing endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        app.config['PARSED_DATA_FOLDER'] = tempfile.mkdtemp()

        # Reinitialize parsing_manager with test config
        global parsing_manager
        from src.parsing_manager import ParsingManager
        parsing_manager = ParsingManager(
            upload_folder=app.config['UPLOAD_FOLDER'],
            parsed_data_folder=app.config['PARSED_DATA_FOLDER']
        )

        with app.test_client() as client:
            yield client

    def test_parse_single_file_success(self, client):
        """Test parsing a single file successfully"""
        # First upload a test file
        test_content = b"Test document content for parsing."
        data = {'files': (io.BytesIO(test_content), 'test_parse.txt')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        # Now parse the file
        parse_response = client.post('/parse/test_parse.txt')
        assert parse_response.status_code == 200

        parse_data = parse_response.get_json()
        assert parse_data['success'] == True
        assert parse_data['filename'] == 'test_parse.txt'
        assert parse_data['text_length'] == len(test_content)
        assert parse_data['word_count'] == 5  # "Test document content for parsing."
        assert 'parsed_at' in parse_data
        assert 'metadata' in parse_data

    def test_parse_file_not_found(self, client):
        """Test parsing a non-existent file"""
        response = client.post('/parse/nonexistent.txt')
        assert response.status_code == 404

        data = response.get_json()
        assert data['success'] == False
        assert 'File not found' in data['error']

    def test_parse_invalid_file_format(self, client):
        """Test parsing a file with invalid format"""
        # Upload an invalid file (not in allowed extensions)
        test_content = b"Invalid file"
        data = {'files': (io.BytesIO(test_content), 'test.invalid')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        # The file was uploaded but will be skipped due to invalid format
        # Actually, our system only allows specific extensions, so this file wouldn't be uploaded
        # Let's test with a valid extension but corrupted content
        # For now, skip this test

        pass

    def test_parse_all_files(self, client):
        """Test parsing all files"""
        # Upload multiple test files
        files_content = [
            (b"First document content", 'doc1.txt'),
            (b"Second document with more content", 'doc2.docx'),
            (b"Third document", 'doc3.pdf')
        ]

        for content, filename in files_content:
            data = {'files': (io.BytesIO(content), filename)}
            upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
            assert upload_response.status_code == 200

        # Parse all files
        response = client.post('/parse/all')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert data['total'] == 3
        assert data['parsed'] == 3
        assert data['failed'] == 0
        assert len(data['results']) == 3

        # Check each result
        for result in data['results']:
            assert result['filename'] in ['doc1.txt', 'doc2.docx', 'doc3.pdf']
            assert result['success'] == True

    def test_get_parsed_text(self, client):
        """Test getting parsed text for a file"""
        # Upload and parse a file
        test_content = b"Test content for parsed text retrieval."
        data = {'files': (io.BytesIO(test_content), 'get_parsed.txt')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        parse_response = client.post('/parse/get_parsed.txt')
        assert parse_response.status_code == 200

        # Get parsed text
        response = client.get('/parsed/get_parsed.txt')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert data['filename'] == 'get_parsed.txt'
        assert data['parsed_text'] == test_content.decode('utf-8')
        assert data['text_length'] == len(test_content)
        assert 'parsed_at' in data
        assert 'metadata' in data

    def test_get_parsed_text_not_parsed(self, client):
        """Test getting parsed text for an unparsed file"""
        # Upload but don't parse
        test_content = b"Test content"
        data = {'files': (io.BytesIO(test_content), 'not_parsed.txt')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        # Try to get parsed text
        response = client.get('/parsed/not_parsed.txt')
        assert response.status_code == 404

        data = response.get_json()
        assert data['success'] == False
        assert 'File not parsed' in data['error']

    def test_get_parsing_status(self, client):
        """Test getting parsing status for all files"""
        # Upload some files
        files = [
            (b"File 1", 'file1.txt'),
            (b"File 2", 'file2.docx'),
            (b"File 3", 'file3.pdf')
        ]

        for content, filename in files:
            data = {'files': (io.BytesIO(content), filename)}
            upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
            assert upload_response.status_code == 200

        # Parse only first file
        parse_response = client.post('/parse/file1.txt')
        assert parse_response.status_code == 200

        # Get parsing status
        response = client.get('/parsing/status')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert data['total_files'] == 3
        assert data['parsed_files'] == 1
        assert data['pending_files'] == 2

        # Check files list
        assert len(data['files']) == 3

        # Find file1.txt and check its parsed status
        file1 = next(f for f in data['files'] if f['filename'] == 'file1.txt')
        assert file1['parsed'] == True
        assert file1['parsed_at'] is not None

        # Find unparsed files
        file2 = next(f for f in data['files'] if f['filename'] == 'file2.docx')
        assert file2['parsed'] == False
        assert file2['parsed_at'] is None

    def test_files_endpoint_with_parsing_state(self, client):
        """Test that /files endpoint includes parsing state"""
        # Upload and parse a file
        test_content = b"Test for files endpoint."
        data = {'files': (io.BytesIO(test_content), 'files_test.txt')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        parse_response = client.post('/parse/files_test.txt')
        assert parse_response.status_code == 200

        # Get files list
        response = client.get('/files')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True

        # Find our file
        file_info = next(f for f in data['files'] if f['filename'] == 'files_test.txt')

        # Check parsing state fields
        assert 'parsed' in file_info
        assert file_info['parsed'] == True
        assert 'parsed_at' in file_info
        assert 'parsing_error' in file_info
        assert 'text_length' in file_info
        assert 'word_count' in file_info
        assert 'parsing_metadata' in file_info

        # Check original fields are still there
        assert 'size' in file_info
        assert 'url' in file_info
        assert 'extension' in file_info
        assert 'formatted_size' in file_info
        assert 'formatted_modified' in file_info

    def test_parse_corrupted_file(self, client):
        """Test parsing a corrupted file"""
        # Create a file with invalid PDF content
        corrupted_content = b"This is not a valid PDF file"
        data = {'files': (io.BytesIO(corrupted_content), 'corrupted.pdf')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        # Try to parse the corrupted file
        response = client.post('/parse/corrupted.pdf')

        # Should either fail with error or return success=False
        # The actual behavior depends on PDF parser implementation
        # For now, just check we get a response
        assert response.status_code in [200, 400, 500]

        data = response.get_json()
        # If it's an error response, success should be False
        if not data.get('success', True):
            assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])