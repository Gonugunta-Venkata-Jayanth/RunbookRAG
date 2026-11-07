"""Optional generative step through a local Ollama server (free, self-hosted).

Enabled only when RUNBOOKRAG_OLLAMA_URL is set; otherwise answers stay extractive.
"""

from __future__ import annotations

import json
import os
import urllib.request

from runbookrag.answer import build_prompt


class OllamaGenerator:
    def __init__(self, base_url: str, model: str = "llama3.2:1b", timeout: float = 30.0, opener=None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._open = opener or urllib.request.urlopen

    def generate(self, question: str, hits: list[dict]) -> str:
        payload = json.dumps(
            {"model": self.model, "prompt": build_prompt(question, hits), "stream": False,
             "options": {"temperature": 0}}
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/generate", data=payload, headers={"Content-Type": "application/json"}
        )
        with self._open(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode())
        text = (body.get("response") or "").strip()
        if not text:
            raise RuntimeError("generator returned an empty response")
        return text


def generator_from_env() -> OllamaGenerator | None:
    url = os.getenv("RUNBOOKRAG_OLLAMA_URL")
    if not url:
        return None
    return OllamaGenerator(url, model=os.getenv("RUNBOOKRAG_OLLAMA_MODEL", "llama3.2:1b"))
