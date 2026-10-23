"""Ollama Local Model Provider for Project FRIDAY.

Runs fully private, local inference on GPU/CPU without transmitting prompt data to the cloud.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Generator
import requests

from app.ai.base_provider import BaseAIProvider, AIResponse, ToolCall
from app.config import config

logger = logging.getLogger(__name__)


class LocalOllamaProvider(BaseAIProvider):
    """Integrates with a locally running Ollama instance."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: int = 60,
    ):
        base = base_url or config.ai.ollama_base_url
        model = default_model or config.ai.ollama_default_model
        super().__init__(name="ollama", default_model=model, timeout=timeout)
        self.base_url = base.rstrip("/")

    def is_available(self) -> bool:
        """Check whether local Ollama daemon is active and has at least one model ready."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return len(models) > 0
            return False
        except Exception:
            return False

    def list_installed_models(self) -> List[str]:
        """Return list of local models installed in Ollama."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning("Failed to list Ollama models: %s", e)
        return []

    def get_effective_model(self, requested_model: Optional[str] = None) -> str:
        if requested_model:
            return requested_model
        installed = self.list_installed_models()
        if not installed:
            return self.default_model
        for m in installed:
            if self.default_model in m or m in self.default_model:
                return m
        return installed[0]

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AIResponse:
        target_model = self.get_effective_model(model)
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return AIResponse(
                    content="",
                    provider_name=self.name,
                    model_name=target_model,
                    error=f"Ollama returned HTTP {resp.status_code}: {resp.text}",
                )

            data = resp.json()
            msg = data.get("message", {})
            content = msg.get("content", "")

            tool_calls = []
            if "tool_calls" in msg and msg["tool_calls"]:
                for idx, tc in enumerate(msg["tool_calls"]):
                    fn = tc.get("function", {})
                    tool_calls.append(
                        ToolCall(
                            id=f"ollama_tc_{idx}",
                            name=fn.get("name", ""),
                            arguments=fn.get("arguments", {}),
                        )
                    )

            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)

            return AIResponse(
                content=content,
                tool_calls=tool_calls,
                provider_name=self.name,
                model_name=target_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                finish_reason="stop" if not tool_calls else "tool_calls",
            )

        except requests.Timeout:
            return AIResponse(
                content="",
                provider_name=self.name,
                model_name=target_model,
                error=f"Ollama request timed out after {self.timeout}s",
            )
        except Exception as e:
            return AIResponse(
                content="",
                provider_name=self.name,
                model_name=target_model,
                error=f"Ollama connection error: {str(e)}",
            )

    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, AIResponse]:
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = tools

        full_content = []
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self.timeout,
            ) as resp:
                if resp.status_code != 200:
                    err_msg = f"Ollama error {resp.status_code}"
                    yield err_msg
                    return AIResponse(
                        content="", provider_name=self.name, model_name=target_model, error=err_msg
                    )

                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        text_piece = chunk.get("message", {}).get("content", "")
                        if text_piece:
                            full_content.append(text_piece)
                            yield text_piece

            final_text = "".join(full_content)
            return AIResponse(
                content=final_text,
                provider_name=self.name,
                model_name=target_model,
                finish_reason="stop",
            )
        except Exception as e:
            err = f"Streaming error: {e}"
            yield err
            return AIResponse(
                content="".join(full_content),
                provider_name=self.name,
                model_name=target_model,
                error=err,
            )
