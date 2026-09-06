"""Environment-configured hosted transport; no dataset or gate decisions."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

COLLECTION_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-(?:am|pm)$")

# Load only the repository-local file. Existing shell variables take priority.
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
BASE_URL = os.environ.get("MODEL_BASE_URL", "").rstrip("/")
MODEL = os.environ.get("MODEL_NAME", "").strip()
PROVIDER_NAME = os.environ.get("MODEL_PROVIDER_NAME", "").strip()
PROVIDER_ENDPOINT = os.environ.get("MODEL_PROVIDER_ENDPOINT", "").strip()
REASONING_EFFORT = os.environ.get("MODEL_REASONING_EFFORT", "").strip()
MODEL_DIRECTORY = MODEL.rsplit("/", 1)[-1] if MODEL else ""


def configured_base_url():
    if not BASE_URL or not MODEL or not PROVIDER_NAME or not PROVIDER_ENDPOINT:
        raise ValueError(
            "MODEL_BASE_URL, MODEL_NAME, MODEL_PROVIDER_NAME, and "
            "MODEL_PROVIDER_ENDPOINT must be set in .env"
        )
    return BASE_URL


def configured_extra_body():
    try:
        value = json.loads(os.environ.get("MODEL_EXTRA_BODY_JSON", "{}"))
    except json.JSONDecodeError as error:
        raise ValueError("MODEL_EXTRA_BODY_JSON must be valid JSON") from error
    if not isinstance(value, dict):
        raise ValueError("MODEL_EXTRA_BODY_JSON must be a JSON object")
    return value


@dataclass(frozen=True)
class HostedConfig:
    max_completion_tokens: int
    timeout_seconds: float = 300

    def __post_init__(self):
        if self.max_completion_tokens < 1 or self.max_completion_tokens > 65536:
            raise ValueError("max completion tokens must be between 1 and 65536")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("request timeout must be finite and positive")
        configured_base_url()

    def contract(self):
        # argparse parses --request-timeout as float. Normalize integral values
        # so the executed contract hashes to the reviewed JSON value (300), not
        # a representation-only variant (300.0).
        timeout_seconds = (
            int(self.timeout_seconds)
            if float(self.timeout_seconds).is_integer()
            else self.timeout_seconds
        )
        return {
            "max_completion_tokens": self.max_completion_tokens,
            "timeout_seconds": timeout_seconds,
            "model_provider": PROVIDER_NAME, "model": MODEL,
            "base_url": configured_base_url(), "stream": False, "seed_supported": False,
            "provider_endpoint": PROVIDER_ENDPOINT,
            "reasoning_effort": REASONING_EFFORT,
            "extra_body": configured_extra_body(),
            "temperature": None, "allow_fallbacks": False,
            "require_parameters": True, "max_retries": 0,
            "token_metric": "provider_prompt_plus_completion_including_reasoning",
            "weight_digest_available": False,
        }

    def identity(self):
        return {
            "kind": "hosted", "provider": PROVIDER_NAME, "model": MODEL,
            "endpoint": PROVIDER_ENDPOINT, "weight_digest": None,
            "configuration_sha256": hashlib.sha256(json.dumps(
                self.contract(), sort_keys=True, separators=(",", ":")
            ).encode()).hexdigest(),
        }


def validate_output_path(output: Path):
    """Keep hosted results inside their model and timestamp namespace."""
    parts = output.resolve().parts
    if MODEL_DIRECTORY not in parts:
        raise ValueError(
            f"hosted output must be inside {MODEL_DIRECTORY}/<date-time>/<dataset>/results/"
        )
    tail = parts[parts.index(MODEL_DIRECTORY) + 1:]
    if (len(tail) < 4 or not COLLECTION_ID.fullmatch(tail[0])
            or tail[1] not in {"ledgar", "cfpb", "spamassassin"} or tail[2] != "results"):
        raise ValueError(
            "expected <model>/YYYY-MM-DD-HH-MM-am|pm/<ledgar|cfpb|spamassassin>/results/<run>.json"
        )


def normalize_usage(usage):
    """Completion includes reasoning; never add its breakdown a second time."""
    if not isinstance(usage, dict):
        raise ValueError("missing hosted-model usage")
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if type(value) is not int or value < 0:
            raise ValueError(f"invalid or missing hosted-model {key}")
    if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
        raise ValueError("inconsistent hosted-model total_tokens")
    reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    for name, value, maximum in (("reasoning", reasoning, usage["completion_tokens"]),
                                 ("cached", cached, usage["prompt_tokens"])):
        if value is not None and (type(value) is not int or not 0 <= value <= maximum):
            raise ValueError(f"invalid hosted-model {name} token count")
    cost = usage.get("cost")
    if cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0):
        raise ValueError("invalid hosted-model cost")
    return {"input_tokens": usage["prompt_tokens"], "output_tokens": usage["completion_tokens"],
            "total_tokens": usage["total_tokens"], "reasoning_tokens": reasoning,
            "cached_input_tokens": cached, "service_cost_usd": cost}


def client_class():
    # Lazy import keeps offline preflight independent of the client package.
    from langchain_openai import ChatOpenAI

    class HostedChatOpenAI(ChatOpenAI):
        """Preserve provider extensions that stock ChatOpenAI discards."""

        def _create_chat_result(self, response, generation_info=None):
            raw = response if isinstance(response, dict) else response.model_dump()
            result = super()._create_chat_result(response, generation_info)
            for generation, choice in zip(result.generations, raw.get("choices", []), strict=True):
                message = generation.message
                details = choice.get("message", {}).get("reasoning_details")
                if details is not None:
                    message.additional_kwargs["reasoning_details"] = copy.deepcopy(details)
                message.response_metadata["hosted"] = copy.deepcopy({
                    "id": raw.get("id"), "model": raw.get("model"),
                    "provider": raw.get("provider"), "created": raw.get("created"),
                    "system_fingerprint": raw.get("system_fingerprint"),
                    "usage": raw.get("usage"), "finish_reason": choice.get("finish_reason"),
                    "refusal": choice.get("message", {}).get("refusal"),
                })
            return result

        def _get_request_payload(self, input_, *, stop=None, **kwargs):
            messages = self._convert_input(input_).to_messages()
            payload = super()._get_request_payload(messages, stop=stop, **kwargs)
            # OpenAI-compatible Chat Completions services commonly use max_tokens.
            if "max_completion_tokens" in payload:
                payload["max_tokens"] = payload.pop("max_completion_tokens")
            for original, serialized in zip(messages, payload["messages"], strict=True):
                details = original.additional_kwargs.get("reasoning_details")
                if original.type == "ai" and details is not None:
                    serialized["reasoning_details"] = copy.deepcopy(details)
            return payload

    return HostedChatOpenAI


def build_model(config: HostedConfig, labels, **test_clients):
    key = os.environ.get("MODEL_API_KEY")
    if not key:
        raise ValueError("Set MODEL_API_KEY in .env; never store it in the plan")
    schema = {"type": "object", "properties": {"label": {"type": "string", "enum": list(labels)}},
              "required": ["label"], "additionalProperties": False}
    return client_class()(
        model=MODEL, api_key=key, base_url=configured_base_url(), temperature=None,
        max_tokens=config.max_completion_tokens, timeout=config.timeout_seconds,
        max_retries=0, streaming=False, disable_streaming=True, use_responses_api=False,
        model_kwargs={"response_format": {"type": "json_schema", "json_schema": {
            "name": "classification", "strict": True, "schema": schema}}},
        extra_body=configured_extra_body(),
        **test_clients,
    )


def optional_sum(values):
    return None if any(value is None for value in values) else sum(values)


def normalize_messages(messages):
    receipts = [m.response_metadata.get("hosted", {}) for m in messages]
    if not receipts or any(not r.get("id") or not r.get("provider") or not r.get("model") for r in receipts):
        raise ValueError("missing hosted request/provider/model receipt")
    if any(r["model"] != MODEL for r in receipts):
        raise ValueError("hosted service returned an unexpected model")
    usage = [normalize_usage(r.get("usage")) for r in receipts]
    return {
        "prompt_eval_count": sum(u["input_tokens"] for u in usage),
        "eval_count": sum(u["output_tokens"] for u in usage),
        "reasoning_tokens": optional_sum([u["reasoning_tokens"] for u in usage]),
        "cached_input_tokens": optional_sum([u["cached_input_tokens"] for u in usage]),
        "service_cost_usd": optional_sum([u["service_cost_usd"] for u in usage]),
        "request_receipts": receipts,
        "done_reason": receipts[-1]["finish_reason"],
        "refusal": any(r.get("refusal") for r in receipts),
    }
