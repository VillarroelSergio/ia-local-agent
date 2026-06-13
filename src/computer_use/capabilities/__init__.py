"""Semantic capabilities exposed by the Computer Use Runtime."""

from .registry import (
    CAPABILITIES,
    HIGH_RISK_CAPABILITIES,
    SEMANTIC_CAPABILITIES,
    Capability,
    ConfirmationGrant,
    ConfirmationStore,
    is_high_risk,
    require_capability,
)

__all__ = [
    "CAPABILITIES",
    "HIGH_RISK_CAPABILITIES",
    "SEMANTIC_CAPABILITIES",
    "Capability",
    "ConfirmationGrant",
    "ConfirmationStore",
    "is_high_risk",
    "require_capability",
]
