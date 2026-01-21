import argparse
import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _coerce_payload(payload: Any) -> Dict[str, Any]:
    """
    Accept either:
      - tokenfusion-style traffic payloads (dict with server_configs + traffic_samples), or
      - server_metrics.json format (list of servers with metrics.network_traffic)

    Normalize into a dict so the rest of the script can work consistently.
    """
    if isinstance(payload, list):
        # server_metrics.json: list of server objects
        return {"format": "server_metrics_v1", "servers": payload}
    if isinstance(payload, dict):
        return payload
    raise ValueError("Unsupported JSON root type. Expected object or array.")


def _summarize_traffic(payload: Dict[str, Any], *, metric: str, candidates: int) -> Dict[str, Any]:
    """
    Build a compact summary to keep prompt size down while preserving what we need.
    Supports:
      - server_metrics.json (array of servers with metrics.network_traffic), or
      - a dict payload with server_configs + traffic_samples (legacy).
    """
    # --- Case 1: server_metrics.json style ---
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

    # --- Case 2: legacy payload (server_configs + traffic_samples) ---
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
        "source_format": "server_configs + traffic_samples",
        "window": payload.get("window"),
        "generated_at": payload.get("generated_at"),
        "metric_definition": {
            "max_traffic": "ranked by total_rps_sum over the provided samples; ties broken by peak_rps",
            "fields": ["total_rps_sum", "avg_rps", "peak_rps", "samples"],
        },
        "candidates": servers_summary[: max(1, int(candidates))],
    }


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
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name (or set OPENAI_MODEL).",
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY environment variable.")

    raw = _load_json(args.input)
    payload = _coerce_payload(raw)
    summary = _summarize_traffic(payload, metric=args.metric, candidates=args.candidates)

    client = OpenAI(api_key=api_key)
    result = _call_llm_for_top_servers(
        client=client, model=args.model, summary=summary, top_n=args.top, metric=args.metric
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

