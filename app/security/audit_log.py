"""Audit Logging and Sensitive Data Redaction for Project FRIDAY.

Ensures that all actions, tool runs, and errors are logged safely without exposing API keys,
passwords, or sensitive user tokens.
"""

import re
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Regex patterns for sensitive credentials (ordered from most specific to general)
SENSITIVE_PATTERNS = [
    (re.compile(r"sk-ant-[a-zA-Z0-9_\-]{15,}", re.IGNORECASE), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}", re.IGNORECASE), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"(api[-_]?key|password|secret|token)\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?", re.IGNORECASE), r"\1: [REDACTED]"),
]


def redact_sensitive_data(text: str) -> str:
    """Scrub sensitive keys, passwords, and tokens from a string."""
    if not isinstance(text, str):
        return text

    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class RedactingFormatter(logging.Formatter):
    """Logging formatter that automatically redacts sensitive tokens."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return redact_sensitive_data(original)


class AuditLogger:
    """Thread-safe centralized logger with automatic rotation and redaction."""

    def __init__(self, log_dir: Optional[Path] = None, log_level: int = logging.INFO):
        self.log_dir = log_dir or (Path(__file__).resolve().parent.parent.parent / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "friday.log"
        self.audit_file = self.log_dir / "audit.log"

        self.logger = logging.getLogger("FridayApp")
        self.logger.setLevel(log_level)
        self.logger.propagate = False

        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Rotating file handler (10 MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Audit dedicated rotating file handler
        audit_handler = RotatingFileHandler(
            self.audit_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        audit_handler.setFormatter(formatter)
        self.audit_logger = logging.getLogger("FridayAudit")
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.addHandler(audit_handler)
        self.audit_logger.propagate = False

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def info(self, msg: str, *args, **kwargs) -> None:
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self.logger.error(msg, *args, **kwargs)

    def record_action(
        self,
        category: str,
        action: str,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        user_confirmed: bool = False
    ) -> None:
        """Record an auditable action for compliance and security traceability."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "action": action,
            "status": status,
            "confirmed_by_user": user_confirmed,
            "details": details or {},
        }
        sanitized_msg = redact_sensitive_data(str(entry))
        self.audit_logger.info(sanitized_msg)


# Global singleton
audit_log = AuditLogger()
