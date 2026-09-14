from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import Principal, require_role
from app.db import get_db
from app.models import WebhookEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{provider}")
def receive(
    provider: str,
    event: dict[str, object],
    db: Session = Depends(get_db),
    _: Principal = Depends(require_role("service", "admin")),
) -> dict[str, object]:
    """Accept a provider callback at most once.

    Providers retry on any non-2xx, and sometimes on a 2xx they never saw. A duplicate
    delivery is acknowledged with 200 and no side effects, so retries stay safe.
    """
    event_id = str(event.get("id", "")).strip()
    if not event_id:
        return {"status": "ignored", "reason": "event has no id"}

    seen = db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.provider == provider, WebhookEvent.event_id == event_id
        )
    )
    if seen is not None:
        return {"status": "duplicate", "event_id": event_id}

    db.add(WebhookEvent(provider=provider, event_id=event_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate", "event_id": event_id}

    # Real processing goes here, inside the same transaction as the dedup row.
    return {"status": "accepted", "event_id": event_id}
