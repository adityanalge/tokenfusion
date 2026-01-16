"""
Multi-format converter: JSON, TOON, CSV, YAML
"""
import json
import csv
import io
import yaml
from typing import Any, Dict, List


def json_to_toon(json_data):
    """
    Convert JSON data to TOON format - compact format with minimal whitespace.
    Special optimized format for arrays of objects: [count]{keys}:\n  values...
    Uses dot notation for nesting and bracket notation for arrays otherwise.
    """
    def is_array_of_objects(obj):
        """Check if list contains only dicts with same keys"""
        if not isinstance(obj, list) or not obj:
            return False
        if not all(isinstance(item, dict) for item in obj):
            return False
        # Check if all objects have the same keys
        if len(obj) == 0:
            return False
        first_keys = set(obj[0].keys())
        return all(set(item.keys()) == first_keys for item in obj)
    
    def format_value(val):
        """Format a value for TOON output"""
        if val is None:
            return "null"
        elif isinstance(val, bool):
            return "true" if val else "false"
        else:
            return str(val)
    
    # Handle root-level primitives
    if not isinstance(json_data, (dict, list)):
        return str(json_data)
    
    # Special case: array of objects with same structure
    if is_array_of_objects(json_data):
        count = len(json_data)
        if count == 0:
            return "[0]{}:"
        
        # Get keys from first object
        keys = list(json_data[0].keys())
        keys_str = ",".join(keys)
        
        # Build header
        lines = [f"[{count}]{{{keys_str}}}:"]
        
        # Add rows with comma-separated values
        for item in json_data:
            values = [format_value(item[key]) for key in keys]
            lines.append(f"  {','.join(values)}")
        
        return "\n".join(lines)
    
    # General case: use path notation
    def flatten_to_paths(obj, prefix=""):
        """Flatten nested structure to path-value pairs"""
        items = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    items.extend(flatten_to_paths(value, current_path))
                else:
                    items.append((current_path, value))
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{prefix}[{i}]" if prefix else f"[{i}]"
                if isinstance(item, (dict, list)):
                    items.extend(flatten_to_paths(item, current_path))
                else:
                    items.append((current_path, item))
        
        else:
            # Primitive value at root
            items.append(("", obj))
        
        return items
    
    # Flatten to path-value pairs
    paths = flatten_to_paths(json_data)
    
    # Format as compact TOON
    lines = []
    for path, value in paths:
        if path:
            lines.append(f"{path}:{format_value(value)}")
        else:
            lines.append(format_value(value))
    
    return "\n".join(lines)


def toon_to_json(toon_text: str) -> Any:
    """
    Convert TOON format to JSON.
    Parses compact TOON format with dot notation, bracket notation, and array-of-objects format.
    """
    lines = [line.rstrip() for line in toon_text.strip().split('\n') if line.strip()]
    if not lines:
        return {}
    
    def parse_value(value_str):
        """Parse a simple value string"""
        if not value_str:
            return None
        value_str = value_str.strip()
        # Try to parse as number
        try:
            # Check if it's a float (has decimal point and is numeric)
            if '.' in value_str and value_str.replace('.', '').replace('-', '').isdigit():
                return float(value_str)
            # Check if it's an integer
            if value_str.replace('-', '').isdigit():
                return int(value_str)
        except ValueError:
            pass
        # Try boolean
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        # Try null
        if value_str.lower() == 'none' or value_str.lower() == 'null':
            return None
        # Return as string
        return value_str
    
    # Check for array-of-objects format: [count]{keys}:
    first_line = lines[0].strip()
    if first_line.startswith('[') and ']{' in first_line and first_line.endswith(':'):
        # Parse header: [count]{key1,key2,...}:
        count_end = first_line.index(']')
        count = int(first_line[1:count_end])
        keys_start = first_line.index('{') + 1
        keys_end = first_line.index('}')
        keys = [k.strip() for k in first_line[keys_start:keys_end].split(',')]
        
        # Parse data rows (they start with spaces or are just comma-separated values)
        result = []
        for line in lines[1:]:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('['):  # Skip other format lines
                # Remove leading spaces if present, then split by comma
                values = [v.strip() for v in line_stripped.split(',')]
                if len(values) == len(keys):  # Only process if we have the right number of values
                    obj = {}
                    for i, key in enumerate(keys):
                        if i < len(values):
                            obj[key] = parse_value(values[i])
                    result.append(obj)
        
        return result
    
    def set_nested_value(obj, path, value):
        """Set a value in nested structure using path notation"""
        parts = []
        i = 0
        
        # Parse path (handle dots and brackets)
        while i < len(path):
            if path[i] == '[':
                # Array index
                i += 1
                idx_end = path.index(']', i)
                idx = int(path[i:idx_end])
                parts.append(('array', idx))
                i = idx_end + 1
            elif path[i] == '.':
                i += 1
            else:
                # Key name
                key_end = i
                while key_end < len(path) and path[key_end] not in '.[':
                    key_end += 1
                key = path[i:key_end]
                if key:
                    parts.append(('key', key))
                i = key_end
        
        # Navigate/create structure
        current = obj
        for i, (part_type, part_value) in enumerate(parts[:-1]):
            if part_type == 'key':
                if part_value not in current:
                    # Check if next part is array
                    if i + 1 < len(parts) and parts[i + 1][0] == 'array':
                        current[part_value] = []
                    else:
                        current[part_value] = {}
                current = current[part_value]
            elif part_type == 'array':
                idx = part_value
                while len(current) <= idx:
                    # Check if next part is array
                    if i + 1 < len(parts) and parts[i + 1][0] == 'array':
                        current.append([])
                    else:
                        current.append({})
                current = current[idx]
        
        # Set the value
        if parts:
            last_type, last_value = parts[-1]
            if last_type == 'key':
                current[last_value] = value
            elif last_type == 'array':
                idx = last_value
                while len(current) <= idx:
                    current.append(None)
                current[idx] = value
        else:
            # Root level - return the value directly
            return value
    
    # Check if it's a simple root value (no colon)
    if len(lines) == 1 and ':' not in lines[0]:
        return parse_value(lines[0])
    
    # Build structure from path-value pairs
    result = {}
    is_array_root = False
    
    for line in lines:
        if ':' not in line:
            # Root value without path
            return parse_value(line)
        
        path, value_str = line.split(':', 1)
        value = parse_value(value_str)
        
        # Check if root is array
        if path.startswith('['):
            is_array_root = True
            if not isinstance(result, list):
                result = []
        
        if is_array_root and path.startswith('['):
            # Root-level array
            idx_end = path.index(']')
            idx = int(path[1:idx_end])
            remaining_path = path[idx_end + 1:]
            
            while len(result) <= idx:
                result.append({} if remaining_path or isinstance(value, (dict, list)) else None)
            
            if remaining_path:
                set_nested_value(result[idx], remaining_path, value)
            else:
                result[idx] = value
        else:
            # Object structure
            set_nested_value(result, path, value)
    
    return result


def json_to_csv(json_data: Any) -> str:
    """Convert JSON to CSV format"""
    output = io.StringIO()
    
    # Handle different JSON structures
    if isinstance(json_data, list):
        if not json_data:
            return ""
        
        # If list of objects, use keys as headers
        if isinstance(json_data[0], dict):
            fieldnames = json_data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in json_data:
                writer.writerow(row)
        else:
            # Simple list - single column
            writer = csv.writer(output)
            writer.writerow(['value'])
            for item in json_data:
                writer.writerow([item])
    elif isinstance(json_data, dict):
        # Single object - use keys as headers
        writer = csv.DictWriter(output, fieldnames=json_data.keys())
        writer.writeheader()
        writer.writerow(json_data)
    else:
        # Primitive value
        writer = csv.writer(output)
        writer.writerow(['value'])
        writer.writerow([json_data])
    
    return output.getvalue()


def csv_to_json(csv_text: str) -> Any:
    """Convert CSV to JSON"""
    if not csv_text.strip():
        return {}
    
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    
    if not rows:
        return {}
    
    # If only one row, return as object
    if len(rows) == 1:
        # Convert values appropriately
        result = {}
        for key, value in rows[0].items():
            result[key] = parse_csv_value(value)
        return result
    
    # Multiple rows - return as array of objects
    result = []
    for row in rows:
        obj = {}
        for key, value in row.items():
            obj[key] = parse_csv_value(value)
        result.append(obj)
    
    return result


def parse_csv_value(value: str) -> Any:
    """Parse CSV value to appropriate type"""
    if not value:
        return None
    # Try number
    try:
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    # Try boolean
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    return value


def json_to_yaml(json_data: Any) -> str:
    """Convert JSON to YAML format"""
    return yaml.dump(json_data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def yaml_to_json(yaml_text: str) -> Any:
    """Convert YAML to JSON"""
    if not yaml_text.strip():
        return {}
    return yaml.safe_load(yaml_text)


def convert_format(content: str, from_format: str, to_format: str) -> Dict[str, str]:
    """
    Convert content from one format to all other formats
    
    Args:
        content: The content to convert
        from_format: Source format ('json', 'toon', 'csv', 'yaml')
        to_format: Target format ('json', 'toon', 'csv', 'yaml') or 'all'
    
    Returns:
        Dictionary with all format conversions
    """
    # First, convert to JSON (intermediate format)
    try:
        if from_format == 'json':
            json_data = json.loads(content)
        elif from_format == 'toon':
            json_data = toon_to_json(content)
        elif from_format == 'csv':
            json_data = csv_to_json(content)
        elif from_format == 'yaml':
            json_data = yaml_to_json(content)
        else:
            raise ValueError(f"Unknown source format: {from_format}")
        
        # Convert to all target formats
        results = {}
        
        if to_format == 'all' or to_format == 'json':
            results['json'] = json.dumps(json_data, indent=2, ensure_ascii=False)
        
        if to_format == 'all' or to_format == 'toon':
            results['toon'] = json_to_toon(json_data)
        
        if to_format == 'all' or to_format == 'csv':
            results['csv'] = json_to_csv(json_data)
        
        if to_format == 'all' or to_format == 'yaml':
            results['yaml'] = json_to_yaml(json_data)
        
        return results
    
    except Exception as e:
        raise ValueError(f"Conversion error: {str(e)}")
