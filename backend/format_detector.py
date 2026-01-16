"""
Format detection utilities to identify JSON, TOON, CSV, and YAML formats
"""
import json
import csv
import io
import yaml
import re


def detect_format(content: str) -> str:
    """
    Detect the format of the given content.
    
    Returns:
        'json', 'toon', 'csv', 'yaml', or 'unknown'
    """
    if not content or not content.strip():
        return 'unknown'
    
    content = content.strip()
    
    # Try JSON detection
    if is_json(content):
        return 'json'
    
    # Try TOON detection
    if is_toon(content):
        return 'toon'
    
    # Try CSV detection
    if is_csv(content):
        return 'csv'
    
    # Try YAML detection
    if is_yaml(content):
        return 'yaml'
    
    return 'unknown'


def is_json(content: str) -> bool:
    """Check if content is JSON"""
    try:
        json.loads(content)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def is_toon(content: str) -> bool:
    """Check if content is TOON format"""
    lines = content.strip().split('\n')
    if not lines:
        return False
    
    first_line = lines[0].strip()
    
    # Check for array-of-objects format: [count]{keys}:
    if first_line.startswith('[') and ']{' in first_line and first_line.endswith(':'):
        return True
    
    # Check for path notation: key:value or key.path:value
    if ':' in first_line and not first_line.startswith('-'):
        # Check if it has TOON-style path notation (dots, brackets)
        if '.' in first_line or '[' in first_line:
            return True
        # Check for TOON compact format: key:value (no space after colon)
        if ':' in first_line:
            parts = first_line.split(':', 1)
            if len(parts) == 2 and not parts[1].startswith(' '):
                # No space after colon is TOON format
                if len(lines) > 1:
                    second_line = lines[1].strip()
                    # TOON typically has no indentation
                    if not second_line.startswith('  ') and not second_line.startswith('-'):
                        return True
    
    return False


def is_csv(content: str) -> bool:
    """Check if content is CSV format"""
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    if len(lines) < 2:
        return False
    
    # Check if first line looks like headers (comma-separated)
    first_line = lines[0]
    if ',' not in first_line:
        return False
    
    # Count commas in first line
    comma_count = first_line.count(',')
    if comma_count == 0:
        return False
    
    # Check if at least one other line has similar comma count
    for line in lines[1:3]:  # Check next 2 lines
        if line.count(',') == comma_count:
            return True
    
    return False


def is_yaml(content: str) -> bool:
    """Check if content is YAML format"""
    try:
        yaml.safe_load(content)
        # Additional checks to distinguish from TOON
        lines = content.strip().split('\n')
        if not lines:
            return False
        
        first_line = lines[0].strip()
        
        # YAML often starts with --- or has list items with -
        if first_line.startswith('---') or first_line.startswith('-'):
            return True
        
        # Check for YAML-style key: value (with space after colon)
        if ':' in first_line:
            parts = first_line.split(':', 1)
            if len(parts) == 2 and parts[1].startswith(' '):
                # Has space after colon - likely YAML
                if len(lines) > 1:
                    second_line = lines[1]
                    # YAML typically has indentation
                    if second_line.startswith('  ') or second_line.startswith('\t'):
                        return True
                    # Or it's a simple YAML with space after colon
                    return True
        
        # YAML typically has indentation
        if len(lines) > 1:
            second_line = lines[1]
            if second_line.startswith('  ') or second_line.startswith('\t'):
                # Check if it's not TOON array format
                if not first_line.startswith('[') or ']{' not in first_line:
                    return True
        
        return False
    except yaml.YAMLError:
        return False
