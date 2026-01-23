"""
Bedrock analysis module - extracted from test.py for use in Flask app
"""
import ast
import json
import boto3
from botocore.exceptions import ClientError
from typing import Tuple, Any, Dict, List

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

# Configuration
REGION = "us-east-2"
MODEL_ID = (
    "arn:aws:bedrock:us-east-2:528214696964:"
    "inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0"
)

# Generation parameters
TEMPERATURE = 0.5
TOP_P = 1.0
MAX_TOKENS = 1000

# Claude 3.5 Haiku context window: ~200,000 tokens
# Using conservative limit to account for prompt overhead
MAX_INPUT_TOKENS = 180000


def _split_top_level_csv(line: str) -> List[str]:
    """Split a line on commas, but only at top level (not inside {...}, [...], or quotes)."""
    parts = []
    buf = []
    depth_curly = 0
    depth_square = 0
    in_single = False
    in_double = False

    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if ch == "{":
                depth_curly += 1
            elif ch == "}":
                depth_curly = max(0, depth_curly - 1)
            elif ch == "[":
                depth_square += 1
            elif ch == "]":
                depth_square = max(0, depth_square - 1)

        if (
            ch == ","
            and not in_single
            and not in_double
            and depth_curly == 0
            and depth_square == 0
        ):
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)

    if buf:
        parts.append("".join(buf).strip())
    return parts


def load_toon_file(path: str) -> List[Dict[str, Any]]:
    """Parse TOON file format."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()
        lines = content.splitlines()

    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        raise ValueError("TOON file is empty.")

    header = lines[0].strip()
    if "{" not in header or "}" not in header:
        raise ValueError("Unrecognized TOON header format.")
    
    fields_blob = header.split("{", 1)[1].rsplit("}", 1)[0]
    fields = [f.strip() for f in fields_blob.split(",") if f.strip()]
    if not fields:
        raise ValueError("No fields found in TOON header.")

    rows = []
    for ln in lines[1:]:
        ln = ln.strip()
        if not ln:
            continue
        if ln.endswith(","):
            ln = ln[:-1]
        
        cols = _split_top_level_csv(ln)
        if len(cols) != len(fields):
            raise ValueError(
                f"TOON row has {len(cols)} columns but header has {len(fields)} fields."
            )

        obj = {}
        for k, v in zip(fields, cols):
            obj[k] = v

        # Convert known structured fields
        if "metrics" in obj and isinstance(obj["metrics"], str):
            obj["metrics"] = ast.literal_eval(obj["metrics"])
        if "tags" in obj and isinstance(obj["tags"], str):
            obj["tags"] = ast.literal_eval(obj["tags"])
        if "uptime_seconds" in obj:
            try:
                obj["uptime_seconds"] = int(obj["uptime_seconds"])
            except Exception:
                pass
        if "health_score" in obj:
            try:
                obj["health_score"] = float(obj["health_score"])
            except Exception:
                pass

        rows.append(obj)

    return rows


def load_file_content(file_content: str, filename: str) -> Tuple[Any, str, str]:
    """
    Load file content (from upload). Returns (parsed_data, format, raw_content).
    """
    if filename.lower().endswith(".toon"):
        # For TOON, use raw content directly
        # Also parse for validation
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toon', delete=False, encoding='utf-8') as f:
            f.write(file_content)
            temp_path = f.name
        try:
            parsed_data = load_toon_file(temp_path)
        finally:
            os.unlink(temp_path)
        return parsed_data, "toon", file_content
    else:
        # For JSON, parse and return raw
        parsed_data = json.loads(file_content)
        return parsed_data, "json", file_content


def estimate_tokens(text: str) -> int:
    """Estimate token count for text."""
    if HAS_TIKTOKEN:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            pass
    
    # Fallback: rough approximation
    return len(text) // 3


def check_input_size(prompt: str, file_content: str, file_format: str) -> int:
    """Check if input exceeds token limits."""
    user_message = f"{prompt}\n\nFile data ({file_format.upper()} format):\n{file_content}"
    estimated_tokens = estimate_tokens(user_message)
    
    if estimated_tokens > MAX_INPUT_TOKENS:
        raise ValueError(
            f"Input exceeds maximum token limit!\n"
            f"  Estimated tokens: {estimated_tokens:,}\n"
            f"  Maximum allowed: {MAX_INPUT_TOKENS:,}\n"
            f"  Over by: {estimated_tokens - MAX_INPUT_TOKENS:,} tokens\n\n"
            f"Consider:\n"
            f"  - Using a TOON file instead of JSON (more compact)\n"
            f"  - Reducing the file size\n"
            f"  - Using a smaller subset of the data"
        )
    
    return estimated_tokens


def invoke_bedrock(prompt: str, file_content: str, file_format: str, aws_key: str = None, aws_secret: str = None) -> Dict[str, Any]:
    """Invoke Bedrock with a prompt and file content."""
    # Pre-flight check
    estimated_tokens = check_input_size(prompt, file_content, file_format)
    
    # Create client with credentials if provided
    client_kwargs = {
        "service_name": "bedrock-runtime",
        "region_name": REGION
    }
    if aws_key and aws_secret:
        client_kwargs["aws_access_key_id"] = aws_key
        client_kwargs["aws_secret_access_key"] = aws_secret
    
    client = boto3.client(**client_kwargs)

    user_message = f"{prompt}\n\nFile data ({file_format.upper()} format):\n{file_content}"

    messages = [{"role": "user", "content": user_message}]

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "top_p": TOP_P
    }

    try:
        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(payload),
            accept="application/json",
            contentType="application/json"
        )

        response_body = json.loads(response["body"].read().decode("utf-8"))
        return {
            "success": True,
            "content": response_body.get("content", []),
            "estimated_tokens": estimated_tokens,
            "file_format": file_format
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        
        # Check for token/size-related errors
        error_lower = error_msg.lower()
        if any(keyword in error_lower for keyword in [
            "too large", "exceed", "context window", "context limit",
            "maximum tokens", "input too long", "request too large"
        ]):
            raise ValueError(
                f"Input file is too large for the model context window!\n\n"
                f"Bedrock Error:\n"
                f"  Code: {error_code}\n"
                f"  Message: {error_msg}\n\n"
                f"Suggestions:\n"
                f"  - Use a TOON file instead of JSON (more compact format)\n"
                f"  - Reduce the file size or use a smaller subset\n"
                f"  - Split the data into multiple requests"
            ) from e
        
        raise RuntimeError(
            f"Bedrock invocation failed [{error_code}]: {error_msg}"
        ) from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error during Bedrock invocation: {e}") from e
