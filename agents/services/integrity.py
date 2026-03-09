from __future__ import annotations

"""Integrity service — SHA-256 hashing for AgentAction audit trail.

Every AgentAction payload is hashed before persistence.
Verification catches tampering in the database.
"""

import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def compute_hash(payload: dict) -> str:
    """Return the SHA-256 hex digest of the canonical JSON serialisation of payload.

    Keys are sorted for determinism. Non-serialisable values raise TypeError.
    """
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_action(action: object) -> bool:
    """Return True if action.integrity_hash matches a fresh hash of action.payload.

    Logs a warning and returns False on mismatch — the caller decides how to
    handle the discrepancy (alerting, quarantine, etc.).
    """
    expected = compute_hash(action.payload)
    if action.integrity_hash == expected:
        return True

    logger.warning(
        "Integrity check FAILED for AgentAction pk=%s: "
        "stored=%s computed=%s",
        getattr(action, "pk", "?"),
        action.integrity_hash,
        expected,
    )
    return False
