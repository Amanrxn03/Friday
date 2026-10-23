"""Hybrid AI Provider Manager for Project FRIDAY.

Intelligently routes inference between local models (Ollama on GPU/CPU) and cloud models
(OpenAI, Gemini, Anthropic) based on user settings, hardware capacity, privacy policy,
and connectivity.
"""

import logging
from typing import Dict, List, Optional, Any, Generator

from app.ai.base_provider import BaseAIProvider, AIResponse
from app.ai.local_provider import LocalOllamaProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.anthropic_provider import AnthropicProvider
from app.ai.offline_provider import OfflineFallbackProvider
from app.core.event_bus import event_bus, Events
from app.config import config

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manages AI provider routing, discovery, fallbacks, and model recommendations."""

    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {
            "ollama": LocalOllamaProvider(),
            "openai": OpenAIProvider(),
            "gemini": GeminiProvider(),
            "anthropic": AnthropicProvider(),
        }
        self.fallback_provider = OfflineFallbackProvider()
        self.active_provider_name: str = config.ai.default_provider

    def set_active_provider(self, name: str) -> bool:
        """Set the default reasoning engine."""
        clean = name.strip().lower()
        if clean in self.providers:
            self.active_provider_name = clean
            logger.info("Active AI provider changed to '%s'", clean)
            event_bus.publish(Events.PROVIDER_CHANGED, {"provider": clean})
            return True
        return False

    def get_provider(self, name: Optional[str] = None) -> BaseAIProvider:
        """Get the requested or currently active provider."""
        target = (name or self.active_provider_name).strip().lower()
        if target in self.providers:
            return self.providers[target]
        if "ollama" in self.providers:
            return self.providers["ollama"]
        if self.providers:
            return next(iter(self.providers.values()))
        raise RuntimeError("No AI providers configured.")

    def get_active_provider_name(self) -> str:
        return self.active_provider_name

    def list_providers_status(self) -> List[Dict[str, Any]]:
        """Return status, availability, and active model for all configured providers."""
        statuses = []
        for name, provider in self.providers.items():
            available = provider.is_available()
            installed_models = []
            if name == "ollama" and available:
                installed_models = provider.list_installed_models()  # type: ignore

            statuses.append({
                "name": name,
                "is_active": name == self.active_provider_name,
                "is_available": available,
                "default_model": provider.default_model,
                "installed_models": installed_models,
            })
        return statuses

    def test_connectivity(self, name: str) -> Dict[str, Any]:
        """Test API connectivity and authentication for a specific provider."""
        provider = self.providers.get(name.lower())
        if not provider:
            return {"success": False, "error": f"Unknown provider '{name}'"}

        try:
            available = provider.is_available()
            if not available:
                return {
                    "success": False,
                    "error": f"Provider '{name}' credentials not configured or endpoint unreachable.",
                }

            # Run a lightweight test generation
            test_prompt = [{"role": "user", "content": "Respond with 'ONLINE'"}]
            resp = provider.generate(test_prompt, max_tokens=10)
            if resp.error:
                return {"success": False, "error": resp.error}

            return {
                "success": True,
                "model": resp.model_name,
                "content": resp.content.strip(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        provider_name: Optional[str] = None,
        fallback: bool = True,
    ) -> AIResponse:
        """Route request to the target provider with automatic fallback if unreachable."""
        primary = self.get_provider(provider_name)

        if primary.is_available():
            resp = primary.generate(messages, tools=tools)
            if not resp.error:
                return resp
            logger.warning("Primary provider '%s' failed: %s", primary.name, resp.error)

        if not fallback:
            return AIResponse(
                content="",
                provider_name=primary.name,
                error=f"Provider '{primary.name}' is unavailable.",
            )

        # Fallback search: try any other available provider
        logger.info("Attempting fallback provider...")
        for name, provider in self.providers.items():
            if name != primary.name and provider.is_available():
                logger.info("Routing to fallback provider: %s", name)
                resp = provider.generate(messages, tools=tools)
                if not resp.error:
                    return resp

        # Zero-downtime safety net: fall back to built-in local offline engine
        logger.info("Routing to built-in offline desktop engine fallback.")
        return self.fallback_provider.generate(messages, tools=tools)

    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        provider_name: Optional[str] = None,
    ) -> Generator[str, None, AIResponse]:
        """Stream response tokens from active provider."""
        primary = self.get_provider(provider_name)
        if primary.is_available():
            try:
                return primary.stream_generate(messages, tools=tools)
            except Exception as e:
                logger.warning("Primary stream failed: %s", e)

        return self.fallback_provider.stream_generate(messages, tools=tools)

    def get_recommended_local_models(self, vram_gb: float = 8.0) -> List[Dict[str, Any]]:
        """Recommend compact instruction-tuned models tailored to actual GPU VRAM."""
        if vram_gb >= 8.0:
            return [
                {
                    "model": "llama3.2:3b",
                    "description": "Ultra-fast conversational assistant, fits easily into VRAM (~2.5 GB VRAM)",
                    "recommended": True,
                },
                {
                    "model": "qwen2.5-coder:7b",
                    "description": "Superb coding and tool reasoning, fully fits in 8 GB VRAM (~5.5 GB VRAM)",
                    "recommended": True,
                },
                {
                    "model": "mistral:7b",
                    "description": "Balanced general assistant with strong reasoning (~5.2 GB VRAM)",
                    "recommended": False,
                },
            ]
        else:
            return [
                {
                    "model": "llama3.2:1b",
                    "description": "Minimal memory footprint, runs on CPU or low VRAM (~1.2 GB)",
                    "recommended": True,
                },
                {
                    "model": "phi3:mini",
                    "description": "Compact high-efficiency Microsoft model (~2.3 GB)",
                    "recommended": True,
                },
            ]


# Global singleton
provider_manager = ProviderManager()
