"""Backward-compatible facade for the event validator."""

from backend.domain.validator import decode_event_message, validate_event_payload

__all__ = ["decode_event_message", "validate_event_payload"]
