"""
Token counting utilities using tiktoken for LLM token estimation
"""
import tiktoken


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken.
    
    Args:
        text: The text to count tokens for
        model: The model to use for tokenization (default: gpt-4)
    
    Returns:
        Number of tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to cl100k_base encoding (used by GPT-4 and GPT-3.5)
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))


def count_tokens_for_formats(formats_dict: dict, model: str = "gpt-4") -> dict:
    """
    Count tokens for all formats.
    
    Args:
        formats_dict: Dictionary with format names as keys and content as values
        model: The model to use for tokenization
    
    Returns:
        Dictionary with token counts for each format
    """
    token_counts = {}
    for format_name, content in formats_dict.items():
        if content:
            token_counts[format_name] = count_tokens(content, model)
        else:
            token_counts[format_name] = 0
    
    return token_counts


def get_recommended_format(token_counts: dict) -> dict:
    """
    Get the format with the least tokens and recommendation.
    
    Args:
        token_counts: Dictionary with format names and their token counts
    
    Returns:
        Dictionary with recommended format and all counts
    """
    # Filter out formats with 0 tokens
    valid_counts = {k: v for k, v in token_counts.items() if v > 0}
    
    if not valid_counts:
        return {
            'recommended': None,
            'min_tokens': 0,
            'all_counts': token_counts
        }
    
    # Find format with minimum tokens
    recommended_format = min(valid_counts, key=valid_counts.get)
    min_tokens = valid_counts[recommended_format]
    
    return {
        'recommended': recommended_format.upper(),
        'min_tokens': min_tokens,
        'all_counts': token_counts,
        'savings': {}
    }
