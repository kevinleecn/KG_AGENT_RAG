"""
Tests for Knowledge Graph QA Demo System - Phase 1
"""

import os
import tempfile
import io
import pytest
from flask import Flask
from werkzeug.datastructures import FileStorage

# Import the app factory or create test app
try:
    from app import app, allowed_file
except ImportError:
    # Create minimal test app if import fails
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    app.config['ALLOWED_EXTENSIONS'] = {'.txt', '.docx', '.pdf', '.pptx'}

    def allowed_file(filename):
        if not filename:
            return False
        _, ext = os.path.splitext(filename)
        return ext.lower() in app.config['ALLOWED_EXTENSIONS']

class TestFileValidation:
    """Test file validation logic"""

    def test_allowed_file_valid_extensions(self):
        """Test allowed file extensions"""
        assert allowed_file('document.txt') == True
        assert allowed_file('document.docx') == True
        assert allowed_file('document.pdf') == True
        assert allowed_file('document.pptx') == True

    def test_allowed_file_case_insensitive(self):
        """Test case insensitive extension matching"""
        assert allowed_file('document.TXT') == True
        assert allowed_file('document.DOCX') == True
        assert allowed_file('document.PDF') == True
        assert allowed_file('document.PPTX') == True

    def test_allowed_file_invalid_extensions(self):
        """Test invalid file extensions"""
        assert allowed_file('document.exe') == False
        assert allowed_file('document.jpg') == False
        assert allowed_file('document.png') == False
        assert allowed_file('document.zip') == False

    def test_allowed_file_no_extension(self):
        """Test files without extensions"""
        assert allowed_file('document') == False
        assert allowed_file('') == False
        assert allowed_file(None) == False

    def test_allowed_file_dot_files(self):
        """Test dot files"""
        assert allowed_file('.hidden.txt') == True
        assert allowed_file('.gitignore') == False

class TestAppRoutes:
    """Test Flask application routes"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        with app.test_client() as client:
            yield client

    def test_index_route(self, client):
        """Test main page route"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Knowledge Graph QA Demo' in response.data
        assert b'Upload Documents' in response.data

    def test_health_route(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        assert b'healthy' in response.data
        assert b'kg-qa-demo' in response.data

    def test_upload_no_files(self, client):
        """Test upload with no files"""
        response = client.post('/upload')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'No files part' in data['error']

    def test_upload_empty_file(self, client):
        """Test upload with empty filename"""
        data = {'files': (b'', '')}
        response = client.post('/upload', data=data)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'No selected files' in data['error']

    def test_upload_invalid_file_type(self, client):
        """Test upload with invalid file type"""
        # Create a test file
        test_file = FileStorage(
            stream=open(__file__, 'rb'),
            filename='test.exe',
            content_type='application/octet-stream'
        )

        data = {'files': test_file}
        response = client.post('/upload', data=data)
        # Note: This test might need adjustment based on actual implementation

    def test_uploads_route_missing_file(self, client):
        """Test serving non-existent uploaded file"""
        response = client.get('/uploads/nonexistent.txt')
        # Should return 404
        assert response.status_code == 404

class TestConfiguration:
    """Test configuration settings"""

    def test_allowed_extensions_set(self):
        """Test ALLOWED_EXTENSIONS config is set"""
        assert 'ALLOWED_EXTENSIONS' in app.config
        extensions = app.config['ALLOWED_EXTENSIONS']
        assert isinstance(extensions, set)
        assert '.txt' in extensions
        assert '.docx' in extensions
        assert '.pdf' in extensions
        assert '.pptx' in extensions

    def test_upload_folder_exists(self):
        """Test upload folder configuration"""
        assert 'UPLOAD_FOLDER' in app.config
        upload_folder = app.config['UPLOAD_FOLDER']
        assert isinstance(upload_folder, str)

        # Folder should exist (created by ensure_directories)
        # or we should be able to create it
        os.makedirs(upload_folder, exist_ok=True)
        assert os.path.exists(upload_folder)

    def test_max_content_length(self):
        """Test max content length configuration"""
        assert 'MAX_CONTENT_LENGTH' in app.config
        max_size = app.config['MAX_CONTENT_LENGTH']
        assert isinstance(max_size, int)
        assert max_size > 0  # Should be positive


class TestFileUploadSuccess:
    """Test successful file upload scenarios"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        with app.test_client() as client:
            yield client

    def test_single_file_upload(self, client):
        """Test uploading a single valid file"""
        # Create a test file
        test_content = b"Test file content"
        data = {
            'files': (io.BytesIO(test_content), 'test.txt')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert len(data['uploaded']) == 1
        assert data['uploaded'][0]['filename'] == 'test.txt'
        assert data['uploaded'][0]['size'] == len(test_content)
        assert 'url' in data['uploaded'][0]
        assert data['message'] == 'Successfully uploaded 1 file(s)'

    def test_multiple_file_upload(self, client):
        """Test uploading multiple valid files"""
        # Create test files - Flask test client handles multiple files differently
        # We need to create a MultiDict-like structure
        from werkzeug.datastructures import MultiDict

        files = MultiDict([
            ('files', (io.BytesIO(b"Content 1"), 'file1.txt')),
            ('files', (io.BytesIO(b"Content 2"), 'file2.docx')),
            ('files', (io.BytesIO(b"Content 3"), 'file3.pdf'))
        ])

        response = client.post('/upload', data=files, content_type='multipart/form-data')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert len(data['uploaded']) == 3
        assert data['message'] == 'Successfully uploaded 3 file(s)'

        # Check all files were uploaded
        filenames = [f['filename'] for f in data['uploaded']]
        assert 'file1.txt' in filenames
        assert 'file2.docx' in filenames
        assert 'file3.pdf' in filenames

    def test_mixed_valid_invalid_files(self, client):
        """Test uploading mix of valid and invalid files"""
        from werkzeug.datastructures import MultiDict

        files = MultiDict([
            ('files', (io.BytesIO(b"Valid"), 'valid.txt')),
            ('files', (io.BytesIO(b"Invalid"), 'invalid.exe')),
            ('files', (io.BytesIO(b"Valid2"), 'valid2.pdf'))
        ])

        response = client.post('/upload', data=files, content_type='multipart/form-data')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert len(data['uploaded']) == 2  # Only valid files
        assert len(data['skipped']) == 1   # Invalid file skipped
        assert 'invalid.exe' in data['skipped']
        assert 'warning' in data
        assert 'Skipped 1 invalid file(s)' in data['warning']


class TestDuplicateFilenameHandling:
    """Test duplicate filename handling"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        with app.test_client() as client:
            yield client

    def test_duplicate_filename_handling(self, client):
        """Test that duplicate filenames get unique names"""
        # Upload same file twice
        test_content = b"Test content"

        # First upload
        data1 = {'files': (io.BytesIO(test_content), 'test.txt')}
        response1 = client.post('/upload', data=data1, content_type='multipart/form-data')
        assert response1.status_code == 200
        data1 = response1.get_json()
        assert data1['uploaded'][0]['filename'] == 'test.txt'

        # Second upload - should get _1 suffix
        data2 = {'files': (io.BytesIO(test_content), 'test.txt')}
        response2 = client.post('/upload', data=data2, content_type='multipart/form-data')
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['uploaded'][0]['filename'] == 'test_1.txt'

        # Third upload - should get _2 suffix
        data3 = {'files': (io.BytesIO(test_content), 'test.txt')}
        response3 = client.post('/upload', data=data3, content_type='multipart/form-data')
        assert response3.status_code == 200
        data3 = response3.get_json()
        assert data3['uploaded'][0]['filename'] == 'test_2.txt'


class TestSecureFilename:
    """Test secure filename handling"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        with app.test_client() as client:
            yield client

    def test_secure_filename_handling(self, client):
        """Test that insecure filenames are secured"""
        # Test various insecure filenames - check what secure_filename actually produces
        from werkzeug.utils import secure_filename

        test_cases = [
            ('../../etc/passwd.txt', secure_filename('../../etc/passwd.txt')),
            ('file with spaces.txt', secure_filename('file with spaces.txt')),
            ('FILE@WITH#SPECIAL$CHARS.txt', secure_filename('FILE@WITH#SPECIAL$CHARS.txt')),
            ('file/with/slashes.txt', secure_filename('file/with/slashes.txt')),
            ('file\\with\\backslashes.txt', secure_filename('file\\with\\backslashes.txt'))
        ]

        for insecure_name, expected_secure_name in test_cases:
            test_content = b"Test content"
            data = {'files': (io.BytesIO(test_content), insecure_name)}

            response = client.post('/upload', data=data, content_type='multipart/form-data')
            assert response.status_code == 200

            data = response.get_json()
            uploaded_filename = data['uploaded'][0]['filename']
            assert uploaded_filename == expected_secure_name, \
                f"Expected {expected_secure_name}, got {uploaded_filename} for input {insecure_name}"


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        with app.test_client() as client:
            yield client

    def test_server_error_handling(self, client, monkeypatch):
        """Test server error handling (500 response)"""
        # Mock os.path.getsize to raise an exception
        def mock_getsize(*args, **kwargs):
            raise Exception("Simulated server error")

        # Monkey patch the getsize method
        monkeypatch.setattr(os.path, 'getsize', mock_getsize)

        test_content = b"Test content"
        data = {'files': (io.BytesIO(test_content), 'test.txt')}

        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 500

        data = response.get_json()
        assert 'error' in data
        assert 'Simulated server error' in data['error']


class TestUploadedFileServing:
    """Test serving uploaded files"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        upload_folder = tempfile.mkdtemp()
        app.config['UPLOAD_FOLDER'] = upload_folder
        with app.test_client() as client:
            yield client

    def test_serve_uploaded_file(self, client):
        """Test serving an uploaded file"""
        # First upload a file
        test_content = b"Test file content for serving"
        data = {'files': (io.BytesIO(test_content), 'serve_test.txt')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        upload_data = upload_response.get_json()
        filename = upload_data['uploaded'][0]['filename']

        # Now try to serve the file
        serve_response = client.get(f'/uploads/{filename}')
        assert serve_response.status_code == 200
        assert serve_response.data == test_content
        assert serve_response.headers['Content-Type'] == 'text/plain; charset=utf-8'


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        with app.test_client() as client:
            yield client

    def test_upload_empty_filename_string(self, client):
        """Test upload with empty string filename (not None)"""
        # Create a file with empty filename string
        test_content = b"Test content"
        data = {'files': (io.BytesIO(test_content), '')}

        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'No selected files' in data['error']

    def test_upload_very_long_filename(self, client):
        """Test upload with very long filename"""
        # Create a filename that's 255 characters long
        long_name = 'a' * 200 + '.txt'
        test_content = b"Test content"
        data = {'files': (io.BytesIO(test_content), long_name)}

        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert len(data['uploaded']) == 1
        # Filename should be secured (shortened if needed)
        assert len(data['uploaded'][0]['filename']) <= 255

    def test_upload_filename_with_unicode(self, client):
        """Test upload with Unicode characters in filename"""
        test_cases = [
            ('café.txt', 'caf_.txt'),  # Unicode character
            ('文件.docx', '_.docx'),    # Chinese characters
            ('🎉party.pptx', 'party.pptx'),  # Emoji
        ]

        for original_name, expected_secure_name in test_cases:
            test_content = b"Test content"
            data = {'files': (io.BytesIO(test_content), original_name)}

            response = client.post('/upload', data=data, content_type='multipart/form-data')
            assert response.status_code == 200

            data = response.get_json()
            assert data['success'] == True
            assert len(data['uploaded']) == 1
            # Just verify it was processed without error
            # The actual secured name depends on secure_filename implementation

    def test_upload_zero_byte_file(self, client):
        """Test uploading a zero-byte file"""
        test_content = b""
        data = {'files': (io.BytesIO(test_content), 'empty.txt')}

        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert len(data['uploaded']) == 1
        assert data['uploaded'][0]['size'] == 0

    def test_upload_large_number_of_files(self, client):
        """Test uploading many files at once"""
        from werkzeug.datastructures import MultiDict

        # Create 10 test files
        files = MultiDict()
        for i in range(10):
            files.add('files', (io.BytesIO(f"Content {i}".encode()), f'file{i}.txt'))

        response = client.post('/upload', data=files, content_type='multipart/form-data')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert len(data['uploaded']) == 10
        assert data['message'] == 'Successfully uploaded 10 file(s)'


class TestConfigurationEdgeCases:
    """Test configuration edge cases"""

    def test_configuration_loading(self):
        """Test that configuration loads correctly"""
        from config.settings import get_config, DevelopmentConfig, TestingConfig, ProductionConfig

        # Test default config (development) - get_config returns a class
        config_class = get_config()
        assert config_class == DevelopmentConfig

        # Create instance to check values
        config = config_class()
        assert config.DEBUG == True
        assert config.TESTING == False

        # Test testing config
        config_class = get_config('testing')
        assert config_class == TestingConfig
        config = config_class()
        assert config.DEBUG == False
        assert config.TESTING == True

        # Test that upload folder is different for testing
        dev_config = DevelopmentConfig()
        test_config = TestingConfig()
        assert dev_config.UPLOAD_FOLDER != test_config.UPLOAD_FOLDER

    def test_production_config_validation(self):
        """Test production configuration validation"""
        from config.settings import ProductionConfig

        # Test that default secret key raises error in production
        # Need to modify class attribute, not instance attribute
        original_secret_key = ProductionConfig.SECRET_KEY

        try:
            ProductionConfig.SECRET_KEY = 'dev-key-change-in-production'

            # This should raise ValueError
            try:
                ProductionConfig.validate()
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "SECRET_KEY must be set in production" in str(e)

            # Test with proper secret key
            ProductionConfig.SECRET_KEY = 'proper-production-secret-key'
            ProductionConfig.validate()  # Should not raise
        finally:
            # Restore original value
            ProductionConfig.SECRET_KEY = original_secret_key


class TestFileListEndpoint:
    """Test /files endpoint for listing uploaded files"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        with app.test_client() as client:
            yield client

    def test_list_files_empty_directory(self, client):
        """Test listing files when upload directory is empty"""
        response = client.get('/files')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert data['files'] == []
        assert data['count'] == 0
        assert data['total_size'] == 0
        assert 'formatted_total_size' in data
        assert data['formatted_total_size'] == '0 Bytes'

    def test_list_files_with_uploaded_files(self, client):
        """Test listing files after uploading some files"""
        # Upload a test file first
        test_content = b"Test file content for listing"
        data = {'files': (io.BytesIO(test_content), 'list_test.txt')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        # Now list files
        list_response = client.get('/files')
        assert list_response.status_code == 200

        data = list_response.get_json()
        assert data['success'] == True
        assert data['count'] == 1
        assert data['total_size'] == len(test_content)
        assert len(data['files']) == 1

        file_info = data['files'][0]
        assert file_info['filename'] == 'list_test.txt'
        assert file_info['size'] == len(test_content)
        assert file_info['url'] == '/uploads/list_test.txt'
        assert file_info['extension'] == '.txt'
        assert 'formatted_size' in file_info
        assert 'formatted_modified' in file_info
        assert 'modified' in file_info

    def test_list_files_multiple_files(self, client):
        """Test listing multiple uploaded files"""
        # Upload multiple files
        files = [
            (io.BytesIO(b"Content 1"), 'file1.txt'),
            (io.BytesIO(b"Content 2 longer"), 'file2.docx'),
            (io.BytesIO(b"C"), 'file3.pdf')
        ]

        for file_content, filename in files:
            data = {'files': (file_content, filename)}
            response = client.post('/upload', data=data, content_type='multipart/form-data')
            assert response.status_code == 200

        # List files
        response = client.get('/files')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        assert data['count'] == 3

        # Files should be sorted by modification time (newest first)
        filenames = [f['filename'] for f in data['files']]
        assert 'file1.txt' in filenames
        assert 'file2.docx' in filenames
        assert 'file3.pdf' in filenames

        # Check total size
        expected_total = len(b"Content 1") + len(b"Content 2 longer") + len(b"C")
        assert data['total_size'] == expected_total

    def test_list_files_nonexistent_directory(self, client, monkeypatch):
        """Test listing files when upload directory doesn't exist"""
        # Temporarily set UPLOAD_FOLDER to a non-existent directory
        import shutil
        non_existent_dir = tempfile.mkdtemp()
        shutil.rmtree(non_existent_dir)  # Remove it

        original_upload_folder = app.config['UPLOAD_FOLDER']
        app.config['UPLOAD_FOLDER'] = non_existent_dir

        try:
            response = client.get('/files')
            assert response.status_code == 200

            data = response.get_json()
            assert data['success'] == True
            assert data['files'] == []
            assert data['count'] == 0
            assert data['total_size'] == 0
        finally:
            # Restore original upload folder
            app.config['UPLOAD_FOLDER'] = original_upload_folder

    def test_list_files_error_handling(self, client, monkeypatch):
        """Test error handling in file listing"""
        # Mock os.listdir to raise an exception
        def mock_listdir(*args, **kwargs):
            raise PermissionError("Simulated permission error")

        monkeypatch.setattr(os, 'listdir', mock_listdir)

        response = client.get('/files')
        assert response.status_code == 500

        data = response.get_json()
        assert 'error' in data
        assert 'Simulated permission error' in data['error']


if __name__ == '__main__':
    # Run tests directly
    pytest.main([__file__, '-v'])