"""Replay protection for unsafe endpoints.

The contract: the same Idempotency-Key with the same body returns the first
response, byte for byte, without doing the work twice. The same key with a
different body is a client bug and returns 409.
"""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import IdempotencyConflictError
from app.models import IdempotencyRecord


def fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def find_replay(db: Session, key: str, request_fingerprint: str) -> IdempotencyRecord | None:
    record = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == key))
    if record is None:
        return None
    if record.request_fingerprint != request_fingerprint:
        raise IdempotencyConflictError(
            "This Idempotency-Key was already used with a different request body."
        )
    return record


def remember(
    db: Session,
    *,
    key: str,
    request_fingerprint: str,
    status_code: int,
    response_body: dict[str, object],
) -> IdempotencyRecord:
    """Store the response. If a concurrent request won the race, return its record."""
    record = IdempotencyRecord(
        key=key,
        request_fingerprint=request_fingerprint,
        status_code=status_code,
        response_body=response_body,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        winner = find_replay(db, key, request_fingerprint)
        if winner is None:
            raise
        return winner
    return record
