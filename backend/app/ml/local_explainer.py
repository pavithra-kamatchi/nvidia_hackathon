import asyncio
import json
import urllib.request
from urllib.parse import urlparse

from app.config import settings

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _request_explanation(fallback: str, facts: dict) -> str:
    endpoint = settings.nemotron_url
    prompt = (
        "Rewrite the resource-allocation explanation in at most two sentences. "
        "Use only the supplied deterministic facts; do not select, add, remove, "
        "or claim availability of any resource. Facts: " + json.dumps(facts)
    )
    body = json.dumps({
        "model": settings.nemotron_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 160,
    }).encode("utf-8")
    request = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=settings.nemotron_timeout_seconds) as response:
        result = json.load(response)
    content = result["choices"][0]["message"]["content"].strip()
    return content or fallback


async def explain_allocation(fallback: str, facts: dict) -> str:
    """Use local Nemotron for wording only, with deterministic fallback."""
    parsed = urlparse(settings.nemotron_url)
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
        raise ValueError("NEMOTRON_URL must be a local loopback HTTP endpoint")
    try:
        return await asyncio.to_thread(_request_explanation, fallback, facts)
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return fallback
