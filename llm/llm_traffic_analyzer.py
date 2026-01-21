import argparse
import ast
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI


def _split_top_level_csv(line: str) -> List[str]:
    """
    Split a line on commas, but only at top level (not inside {...}, [...], (...), or quotes).
    This is enough for our TOON mock where some columns are Python-literal dict/list strings.
    """
    parts: List[str] = []
    buf: List[str] = []
    depth_curly = 0
    depth_square = 0
    depth_paren = 0
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
            elif ch == "(":
                depth_paren += 1
            elif ch == ")":
                depth_paren = max(0, depth_paren - 1)

        if (
            ch == ","
            and not in_single
            and not in_double
            and depth_curly == 0
            and depth_square == 0
            and depth_paren == 0
        ):
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)

    if buf:
        parts.append("".join(buf).strip())
    return parts


def _load_server_metrics_toon(path: str) -> List[Dict[str, Any]]:
    """
    Parse the mock TOON file format that looks like:
      [1000]{field1,field2,...}:
        v1,v2,...,{...},[...],...
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]

    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        raise ValueError("TOON file is empty.")

    header = lines[0].strip()
    # Example: [1000]{server_id,hostname,...}:
    if "{" not in header or "}" not in header:
        raise ValueError("Unrecognized TOON header format.")
    fields_blob = header.split("{", 1)[1].rsplit("}", 1)[0]
    fields = [f.strip() for f in fields_blob.split(",") if f.strip()]
    if not fields:
        raise ValueError("No fields found in TOON header.")

    rows: List[Dict[str, Any]] = []
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

        obj: Dict[str, Any] = {}
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


def _load_input(path: str) -> Any:
    """
    Load either JSON (.json) or our mock TOON (.toon).
    """
    if path.lower().endswith(".toon"):
        return _load_server_metrics_toon(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _coerce_payload(payload: Any) -> Dict[str, Any]:
    """
    Accept either:
      - server_metrics.json format (list of servers with metrics.network_traffic), or
      - tokenfusion-style payload (dict with server_configs + traffic_samples).
    """
    if isinstance(payload, list):
        return {"format": "server_metrics_v1", "servers": payload}
    if isinstance(payload, dict):
        return payload
    raise ValueError("Unsupported JSON root type. Expected object or array.")


def _summarize_traffic(payload: Dict[str, Any], *, metric: str, candidates: int) -> Dict[str, Any]:
    """
    Build a compact summary to keep prompt size down while preserving what we need.
    Supports:
      - server_metrics.json (array of servers with metrics.network_traffic), or
      - a dict payload with server_configs + traffic_samples.
    """
    # server_metrics.json style
    if payload.get("format") == "server_metrics_v1" and isinstance(payload.get("servers"), list):
        rows = payload["servers"]
        normalized: List[Dict[str, Any]] = []
        for s in rows:
            nt = ((s or {}).get("metrics") or {}).get("network_traffic") or {}
            incoming = nt.get("incoming_mbps", 0.0) or 0.0
            outgoing = nt.get("outgoing_mbps", 0.0) or 0.0
            active_connections = nt.get("active_connections", 0) or 0
            total_mbps = float(incoming) + float(outgoing)
            normalized.append(
                {
                    "server_id": s.get("server_id"),
                    "hostname": s.get("hostname"),
                    "status": s.get("status"),
                    "tags": s.get("tags", []),
                    "traffic": {
                        "incoming_mbps": float(incoming),
                        "outgoing_mbps": float(outgoing),
                        "total_mbps": total_mbps,
                        "active_connections": int(active_connections),
                    },
                }
            )

        if metric == "total_mbps":
            normalized.sort(key=lambda x: x["traffic"]["total_mbps"], reverse=True)
        elif metric == "outgoing_mbps":
            normalized.sort(key=lambda x: x["traffic"]["outgoing_mbps"], reverse=True)
        elif metric == "incoming_mbps":
            normalized.sort(key=lambda x: x["traffic"]["incoming_mbps"], reverse=True)
        elif metric == "active_connections":
            normalized.sort(key=lambda x: x["traffic"]["active_connections"], reverse=True)
        else:
            raise ValueError(f"Unsupported metric: {metric}")

        return {
            "source_format": "server_metrics.json",
            "metric_definition": {
                "metric": metric,
                "meaning": "Rank servers by the selected network_traffic metric.",
            },
            "candidates": normalized[: max(1, int(candidates))],
        }

    # tokenfusion-style payload
    configs = payload.get("server_configs", []) or []
    samples = payload.get("traffic_samples", []) or []

    by_server: Dict[str, Dict[str, Any]] = {}
    for cfg in configs:
        sid = cfg.get("server_id")
        if not sid:
            continue
        by_server.setdefault(
            sid,
            {
                "server_id": sid,
                "hostname": cfg.get("hostname"),
                "role": cfg.get("role"),
                "region": cfg.get("region"),
                "capacity_rps": cfg.get("capacity_rps"),
                "tags": cfg.get("tags", []),
                "rps_samples": [],
            },
        )

    for s in samples:
        sid = s.get("server_id")
        rps = s.get("rps")
        if not sid or rps is None:
            continue
        by_server.setdefault(
            sid,
            {
                "server_id": sid,
                "hostname": None,
                "role": None,
                "region": None,
                "capacity_rps": None,
                "tags": [],
                "rps_samples": [],
            },
        )
        by_server[sid]["rps_samples"].append(float(rps))

    def stats(vals: List[float]) -> Dict[str, Any]:
        if not vals:
            return {"samples": 0, "avg_rps": 0.0, "peak_rps": 0.0, "total_rps_sum": 0.0}
        total = float(sum(vals))
        return {
            "samples": len(vals),
            "avg_rps": total / len(vals),
            "peak_rps": max(vals),
            "total_rps_sum": total,
        }

    servers_summary: List[Dict[str, Any]] = []
    for sid, info in by_server.items():
        rps_vals = info.get("rps_samples", [])
        s = stats(rps_vals)
        servers_summary.append(
            {
                "server_id": sid,
                "hostname": info.get("hostname"),
                "role": info.get("role"),
                "region": info.get("region"),
                "capacity_rps": info.get("capacity_rps"),
                "tags": info.get("tags"),
                "traffic": s,
            }
        )

    # Sort by total traffic (sum of rps samples) descending as a sensible default metric.
    servers_summary.sort(key=lambda x: x["traffic"]["total_rps_sum"], reverse=True)

    return {
        "window": payload.get("window"),
        "generated_at": payload.get("generated_at"),
        "metric_definition": {
            "max_traffic": "ranked by total_rps_sum over the provided samples; ties broken by peak_rps",
            "fields": ["total_rps_sum", "avg_rps", "peak_rps", "samples"],
        },
        "candidates": servers_summary[: max(1, int(candidates))],
    }


def _shrink_summary_to_fit(summary: Dict[str, Any], *, max_chars: int) -> Tuple[Dict[str, Any], int]:
    """
    Ensure the JSON we send to the LLM stays under a char budget.
    We shrink by reducing the number of candidates until it fits.
    Returns (new_summary, final_candidate_count).
    """
    if max_chars <= 0:
        return summary, len(summary.get("candidates", []) or [])

    candidates = list(summary.get("candidates", []) or [])
    if not candidates:
        return summary, 0

    lo = 1
    hi = len(candidates)
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        trial = dict(summary)
        trial["candidates"] = candidates[:mid]
        blob = json.dumps(trial, ensure_ascii=False, separators=(",", ":"))
        if len(blob) <= max_chars:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    shrunk = dict(summary)
    shrunk["candidates"] = candidates[:best]
    return shrunk, best


def _top_locally(summary: Dict[str, Any], *, top_n: int, metric: str) -> Dict[str, Any]:
    """
    Return top servers purely from the summary candidates (no LLM call).
    """
    cands = list(summary.get("candidates", []) or [])
    top_n = max(1, int(top_n))

    def metric_value(c: Dict[str, Any]) -> float:
        t = c.get("traffic") or {}
        if metric in ("incoming_mbps", "outgoing_mbps", "total_mbps", "active_connections"):
            return float(t.get(metric, 0.0) or 0.0)
        return float(t.get("total_rps_sum", 0.0) or 0.0)

    cands.sort(key=metric_value, reverse=True)
    out = []
    for c in cands[:top_n]:
        out.append(
            {
                "server_id": c.get("server_id") or "",
                "hostname": c.get("hostname") or "",
                "metric_value": metric_value(c),
                "why": "Ranked locally from candidates (no LLM call).",
            }
        )

    return {"metric_used": metric, "top_servers": out}


def _call_llm_for_top_servers(
    *,
    client: OpenAI,
    model: str,
    summary: Dict[str, Any],
    top_n: int,
    metric: str,
) -> Dict[str, Any]:
    schema = {
        "name": "top_traffic_servers",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "metric_used": {"type": "string"},
                "top_servers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "server_id": {"type": "string"},
                            "hostname": {"type": "string"},
                            "metric_value": {"type": "number"},
                            "why": {"type": "string"},
                        },
                        "required": [
                            "server_id",
                            "hostname",
                            "metric_value",
                            "why",
                        ],
                    },
                },
            },
            "required": ["metric_used", "top_servers"],
        },
    }

    prompt = f"""
You are a traffic analyst.

Given the JSON summary below, identify the {top_n} servers that serve the maximum traffic.
Use the metric definition provided. For this run, the selected metric is: {metric}.

Return ONLY valid JSON that conforms to the given JSON schema.
"""

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "You return strict JSON only."},
            {"role": "user", "content": prompt.strip()},
            {"role": "user", "content": json.dumps(summary, ensure_ascii=False)},
        ],
        response_format={"type": "json_schema", "json_schema": schema},
    )

    # responses.create returns structured output as a JSON string in output_text for json_schema
    text = (resp.output_text or "").strip()
    if not text:
        raise RuntimeError("OpenAI response was empty.")
    return json.loads(text)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load a JSON file of server configs + traffic and ask an OpenAI LLM for top traffic servers."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input JSON file (e.g., server_metrics.json)",
    )
    parser.add_argument("--top", type=int, default=3, help="How many top servers to return.")
    parser.add_argument(
        "--metric",
        default="total_mbps",
        choices=["total_mbps", "incoming_mbps", "outgoing_mbps", "active_connections"],
        help="Traffic metric to rank by (server_metrics.json format).",
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=50,
        help="How many top candidates to include in the prompt (reduces token usage).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=45000,
        help="Hard cap for the JSON we send to the LLM (auto-shrinks candidates to fit).",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Don't call OpenAI; print top servers computed locally from candidates.",
    )
    parser.add_argument(
        "--allow-large-json",
        action="store_true",
        help="Allow ingesting large .json files (by default, large JSON is rejected to encourage TOON).",
    )
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=200_000,
        help="Maximum allowed size (in bytes) for .json inputs before throwing a 'too large for context' error.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name (or set OPENAI_MODEL).",
    )
    args = parser.parse_args(argv)

    # Intentionally fail fast for large JSON: encourage TOON for leaner payloads.
    # This is by design (mirrors the real-world 'context window' limitation).
    if (
        isinstance(args.input, str)
        and args.input.lower().endswith(".json")
        and not args.allow_large_json
    ):
        try:
            size = os.path.getsize(args.input)
        except OSError:
            size = None
        if size is not None and size > int(args.max_json_bytes):
            raise SystemExit(
                f"Input JSON is too large for the context window (size={size} bytes > max={int(args.max_json_bytes)}). "
                "Convert to a leaner format like TOON and retry, or pass --allow-large-json to override."
            )

    raw = _load_input(args.input)
    payload = _coerce_payload(raw)
    summary = _summarize_traffic(payload, metric=args.metric, candidates=args.candidates)
    summary, _final_candidates = _shrink_summary_to_fit(summary, max_chars=args.max_chars)

    if args.no_llm:
        print(json.dumps(_top_locally(summary, top_n=args.top, metric=args.metric), indent=2, ensure_ascii=False))
        return 0

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY environment variable. (Or pass --no-llm)")

    client = OpenAI(api_key=api_key)
    result = _call_llm_for_top_servers(
        client=client, model=args.model, summary=summary, top_n=args.top, metric=args.metric
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

