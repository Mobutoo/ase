from __future__ import annotations

"""Agent services package.

Services are pure functions / stateless classes — they do NOT import
Django models at module level to keep them testable without the ORM.
All database writes go through AgentAction so every proposal is audited.
"""
