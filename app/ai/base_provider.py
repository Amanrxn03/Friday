"""Base AI Provider Interface for Project FRIDAY.

Defines the contract for all local and cloud language model integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator, Generator


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class AIResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    provider_name: str = "unknown"
    model_name: str = "unknown"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"
    error: Optional[str] = None


class BaseAIProvider(ABC):
    """Abstract base class for AI reasoning engines."""

    def __init__(self, name: str, default_model: str, timeout: int = 60):
        self.name = name
        self.default_model = default_model
        self.timeout = timeout

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider endpoint is reachable and credentials (if required) are valid."""
        pass

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Synchronously generate a response with optional function calling."""
        pass

    @abstractmethod
    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, AIResponse]:
        """Stream response tokens as they arrive, yielding string tokens and returning final AIResponse."""
        pass
