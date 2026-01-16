from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from multi_converter import convert_format
from token_counter import count_tokens_for_formats, get_recommended_format
from format_detector import detect_format

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

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
