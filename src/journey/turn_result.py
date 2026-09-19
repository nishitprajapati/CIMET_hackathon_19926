from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnResult:
    action: str
    response: str
    extracted: dict[str, Any] = field(default_factory=dict)
    next_field: str | None = None
    escalation_reason: str | None = None
    confidence: float = 1.0
