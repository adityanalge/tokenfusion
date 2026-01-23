import argparse
import ast
import json
import boto3
from botocore.exceptions import ClientError

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

AWS_KEY = "YOUR_AWS_ACCESS_KEY"
AWS_SECRET_KEY = "YOUR_AWS_SECRET_KEY"
# Configuration
REGION = "us-east-2"
MODEL_ID = (
    "arn:aws:bedrock:us-east-2:528214696964:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0"
)

# Generation parameters
TEMPERATURE = 0.5
TOP_P = 1.0
MAX_TOKENS = 1000

# Claude 3.5 Haiku context window: ~200,000 tokens
# Using conservative limit to account for prompt overhead
# Pre-check to avoid costly Bedrock API calls
MAX_INPUT_TOKENS = 180000


def _split_top_level_csv(line: str):
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


def load_toon_file(path: str):
    """Load and parse a TOON file into a list of dictionaries."""
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


def load_file(path: str):
    """Load either JSON or TOON file. Returns (parsed_data, format, raw_content)."""
    if path.lower().endswith(".toon"):
        # For TOON, return the raw text to preserve token efficiency
        with open(path, "r", encoding="utf-8", newline="") as f:
            raw_content = f.read()
        # Also parse it for validation
        parsed_data = load_toon_file(path)
        return parsed_data, "toon", raw_content
    else:
        # For JSON, read raw content and parse
        with open(path, "r", encoding="utf-8") as f:
            raw_content = f.read()
        parsed_data = json.loads(raw_content)
        return parsed_data, "json", raw_content


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Uses tiktoken if available, otherwise uses character-based approximation.
    """
    if HAS_TIKTOKEN:
        try:
            # Use cl100k_base encoding (GPT-4/Claude compatible)
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            pass
    
    # Fallback: rough approximation (1 token ≈ 4 characters for English)
    # This is conservative and may overestimate
    return len(text) // 3


def check_input_size(prompt: str, file_content: str, file_format: str):
    """
    Check if the input exceeds token limits and raise an error if it does.
    Pre-flight check to avoid costly Bedrock API calls.
    Uses raw file content to preserve TOON's token efficiency.
    """
    user_message = f"{prompt}\n\nFile data ({file_format.upper()} format):\n{file_content}"
    
    # Estimate tokens
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


def invoke_bedrock(prompt: str, file_content: str, file_format: str):
    """Invoke Bedrock with a prompt and file content (preserves TOON format for token efficiency)."""
    # Pre-flight check to avoid costly API calls
    estimated_tokens = check_input_size(prompt, file_content, file_format)
    print(f"Estimated input tokens: {estimated_tokens:,} ({file_format.upper()} format)")
    
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    # Use raw file content directly - preserves TOON's token efficiency
    user_message = f"{prompt}\n\nFile data ({file_format.upper()} format):\n{file_content}"

    messages = [
        {
            "role": "user",
            "content": user_message
        }
    ]

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
        return response_body.get("content", [])

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
                f"❌ Input file is too large for the model context window!\n\n"
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send a prompt and file (JSON or TOON) to AWS Bedrock"
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="The prompt/question to send to the model"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to JSON or TOON file to analyze"
    )
    
    args = parser.parse_args()
    
    try:
        # Load the file (returns data, format, raw_content)
        print(f"Loading file: {args.file}")
        file_data, file_format, file_content = load_file(args.file)
        print(f"File loaded successfully ({len(file_data) if isinstance(file_data, list) else 'object'} items, {file_format.upper()} format)")
        
        # Invoke Bedrock with raw content to preserve TOON's token efficiency
        print(f"\nSending prompt to Bedrock...")
        result = invoke_bedrock(args.prompt, file_content, file_format)
        
        # Print result
        print("\n=== Bedrock Response ===")
        for content_block in result:
            if content_block.get("type") == "text":
                print(content_block.get("text", ""))
            else:
                print(json.dumps(content_block, indent=2))
    
    except ValueError as e:
        print(f"\n❌ Error: {e}", file=__import__("sys").stderr)
        exit(1)
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=__import__("sys").stderr)
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=__import__("sys").stderr)
        exit(1)
