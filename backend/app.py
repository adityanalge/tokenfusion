from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from multi_converter import convert_format
from token_counter import count_tokens_for_formats, get_recommended_format
from format_detector import detect_format
from bedrock_analyzer import load_file_content, invoke_bedrock

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

@app.route('/api/convert', methods=['POST'])
def convert_formats():
    """
    Convert content from one format to all other formats.
    Accepts: { "content": "...", "from_format": "json|toon|csv|yaml" }
    Returns: { 
        "success": true, 
        "json": "...", 
        "toon": "...", 
        "csv": "...", 
        "yaml": "...",
        "tokens": {
            "json": 123,
            "toon": 120,
            "csv": 125,
            "yaml": 122
        },
        "recommendation": {
            "recommended": "TOON",
            "min_tokens": 120,
            "all_counts": {...}
        },
        "format_warning": {
            "detected_format": "json",
            "expected_format": "csv",
            "message": "Detected JSON format. Did you mean to paste this in the JSON box?"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        content = data.get('content', '').strip()
        from_format = data.get('from_format', 'json').lower()
        
        if not content:
            return jsonify({'error': 'No content provided'}), 400
        
        if from_format not in ['json', 'toon', 'csv', 'yaml']:
            return jsonify({'error': f'Invalid format: {from_format}. Must be json, toon, csv, or yaml'}), 400
        
        # Detect the actual format of the content FIRST
        detected_format = detect_format(content)
        format_warning = None
        format_labels = {
            'json': 'JSON',
            'toon': 'TOON',
            'csv': 'CSV',
            'yaml': 'YAML'
        }
        
        # If detected format doesn't match expected format, create warning
        if detected_format != 'unknown' and detected_format != from_format:
            format_warning = {
                'detected_format': detected_format,
                'expected_format': from_format,
                'message': f'Detected {format_labels.get(detected_format, detected_format.upper())} format. Did you mean to paste this in the {format_labels.get(detected_format, detected_format.upper())} box?'
            }
            
            # Try to convert using the detected format instead
            # This allows conversion to work even if pasted in wrong box
            try:
                results = convert_format(content, detected_format, 'all')
            except Exception as e:
                # If detected format conversion fails, try original format
                try:
                    results = convert_format(content, from_format, 'all')
                except Exception:
                    # If both fail, raise the original error but include warning
                    raise ValueError(f'Could not convert content. {str(e)}')
        else:
            # Convert to all formats using the specified format
            results = convert_format(content, from_format, 'all')
        
        # Count tokens for all formats
        token_counts = count_tokens_for_formats(results)
        
        # Get recommendation
        recommendation = get_recommended_format(token_counts)
        
        response = {
            'success': True,
            **results,
            'tokens': token_counts,
            'recommendation': recommendation
        }
        
        if format_warning:
            response['format_warning'] = format_warning
        
        return jsonify(response)
    
    except ValueError as e:
        # If we have a format warning, include it even in error response
        error_response = {'error': str(e)}
        if 'format_warning' in locals() and format_warning:
            error_response['format_warning'] = format_warning
        return jsonify(error_response), 400
    except Exception as e:
        # If we have a format warning, include it even in error response
        error_response = {'error': f'Conversion error: {str(e)}'}
        if 'format_warning' in locals() and format_warning:
            error_response['format_warning'] = format_warning
        return jsonify(error_response), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_file():
    """
    Analyze a file with a prompt using AWS Bedrock.
    Accepts: multipart/form-data with 'file' and 'prompt'
    Returns: Analysis result from Bedrock
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        prompt = request.form.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file content
        file_content = file.read().decode('utf-8')
        filename = file.filename
        
        # Load file (returns parsed_data, format, raw_content)
        parsed_data, file_format, raw_content = load_file_content(file_content, filename)
        
        # Get AWS credentials from request (optional, can use environment/default)
        aws_key = request.form.get('aws_key') or os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret = request.form.get('aws_secret') or os.getenv('AWS_SECRET_ACCESS_KEY')
        
        # Invoke Bedrock
        result = invoke_bedrock(prompt, raw_content, file_format, aws_key, aws_secret)
        
        # Format response for frontend
        response_text = ""
        for content_block in result.get('content', []):
            if content_block.get('type') == 'text':
                response_text += content_block.get('text', '')
        
        return jsonify({
            'success': True,
            'response': response_text,
            'estimated_tokens': result.get('estimated_tokens'),
            'file_format': result.get('file_format'),
            'item_count': len(parsed_data) if isinstance(parsed_data, list) else 1
        })
    
    except ValueError as e:
        return jsonify({'error': str(e), 'type': 'validation'}), 400
    except RuntimeError as e:
        return jsonify({'error': str(e), 'type': 'bedrock'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}', 'type': 'unknown'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

@app.route('/analyze')
def analyze_page():
    """Serve the analyze page"""
    return send_from_directory(os.path.dirname(os.path.dirname(__file__)), 'analyze.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
