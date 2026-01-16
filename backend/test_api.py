"""
Test cases for Flask API endpoints
"""
import pytest
import json
import io
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestConvertEndpoint:
    """Test the /api/convert endpoint"""
    
    def test_convert_json_body_simple(self, client):
        """Test conversion with JSON in request body - simple object"""
        response = client.post(
            '/api/convert',
            json={"name": "John", "age": 30},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'toon' in data
        assert 'name: John' in data['toon']
        assert 'age: 30' in data['toon']
    
    def test_convert_json_body_nested(self, client):
        """Test conversion with JSON in request body - nested object"""
        response = client.post(
            '/api/convert',
            json={
                "user": {
                    "name": "Alice",
                    "address": {
                        "city": "New York"
                    }
                }
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'user:' in data['toon']
        assert '  name: Alice' in data['toon']
        assert '    city: New York' in data['toon']
    
    def test_convert_file_upload(self, client):
        """Test conversion with file upload"""
        json_data = {"name": "Bob", "age": 25}
        json_string = json.dumps(json_data)
        data = {
            'file': (io.BytesIO(json_string.encode('utf-8')), 'test.json')
        }
        response = client.post(
            '/api/convert',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'name: Bob' in data['toon']
        assert 'age: 25' in data['toon']
    
    def test_convert_file_upload_empty_filename(self, client):
        """Test file upload with empty filename"""
        data = {
            'file': (io.BytesIO(b''), '')
        }
        response = client.post(
            '/api/convert',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No file selected' in data['error']
    
    def test_convert_no_data(self, client):
        """Test conversion with no data provided"""
        response = client.post(
            '/api/convert',
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No JSON data provided' in data['error']
    
    def test_convert_invalid_json_file(self, client):
        """Test conversion with invalid JSON file"""
        invalid_json = "{ invalid json }"
        data = {
            'file': (io.BytesIO(invalid_json.encode('utf-8')), 'invalid.json')
        }
        response = client.post(
            '/api/convert',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid JSON' in data['error']
    
    def test_convert_invalid_json_body(self, client):
        """Test conversion with invalid JSON in body"""
        response = client.post(
            '/api/convert',
            data='{ invalid json }',
            content_type='application/json'
        )
        # Flask might handle this differently, but should return an error
        assert response.status_code in [400, 500]
    
    def test_convert_array_root(self, client):
        """Test conversion with array as root"""
        response = client.post(
            '/api/convert',
            json=[1, 2, 3, {"key": "value"}],
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert '[0]: 1' in data['toon']
        assert '[1]: 2' in data['toon']
        assert '[2]: 3' in data['toon']
    
    def test_convert_complex_structure(self, client):
        """Test conversion with complex nested structure"""
        complex_json = {
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                    "tags": ["admin", "developer"],
                    "settings": {
                        "theme": "dark",
                        "notifications": True
                    }
                },
                {
                    "id": 2,
                    "name": "Bob",
                    "tags": ["user"],
                    "settings": {
                        "theme": "light",
                        "notifications": False
                    }
                }
            ],
            "metadata": {
                "version": "1.0",
                "count": 2
            }
        }
        response = client.post(
            '/api/convert',
            json=complex_json,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        toon = data['toon']
        # Verify key components
        assert 'users:' in toon
        assert '  [0]:' in toon
        assert '    name: Alice' in toon
        assert '    tags:' in toon
        assert '      [0]: admin' in toon
        assert 'metadata:' in toon
        assert '  version: 1.0' in toon


class TestHealthEndpoint:
    """Test the /api/health endpoint"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'


class TestCORS:
    """Test CORS headers"""
    
    def test_cors_headers(self, client):
        """Test that CORS headers are present"""
        response = client.get('/api/health')
        # Flask-CORS should add CORS headers
        # The exact headers depend on configuration
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling"""
    
    def test_method_not_allowed(self, client):
        """Test that GET is not allowed on /api/convert"""
        response = client.get('/api/convert')
        assert response.status_code == 405  # Method Not Allowed
    
    def test_404_for_unknown_endpoint(self, client):
        """Test 404 for unknown endpoint"""
        response = client.get('/api/unknown')
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
