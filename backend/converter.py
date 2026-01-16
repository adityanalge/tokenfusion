"""
JSON to TOON converter module
"""

def json_to_toon(json_data):
    """
    Convert JSON data to TOON format.
    TOON format: A simple text-based representation of JSON structure
    
    Args:
        json_data: The JSON data to convert (dict, list, or primitive)
    
    Returns:
        str: The TOON formatted string representation
    """
    def convert_value(value, indent=0):
        """Recursively convert JSON values to TOON format"""
        indent_str = "  " * indent
        
        if isinstance(value, dict):
            lines = []
            for key, val in value.items():
                if isinstance(val, (dict, list)):
                    lines.append(f"{indent_str}{key}:")
                    lines.append(convert_value(val, indent + 1))
                else:
                    lines.append(f"{indent_str}{key}: {val}")
            return "\n".join(lines)
        
        elif isinstance(value, list):
            lines = []
            for i, item in enumerate(value):
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent_str}[{i}]:")
                    lines.append(convert_value(item, indent + 1))
                else:
                    lines.append(f"{indent_str}[{i}]: {item}")
            return "\n".join(lines)
        
        else:
            return f"{indent_str}{value}"
    
    return convert_value(json_data)
