from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from app.auth import Principal, require_role
from app.db import get_db
from app.idempotency import find_replay, fingerprint, remember
from app.schemas import PaymentCreate
from app.services import ledger

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _: Principal = Depends(require_role("admin", "service")),
) -> dict[str, object]:
    """Move money between two accounts exactly once.

    Send an Idempotency-Key header. Retrying the same request returns the original
    result instead of moving the money a second time.
    """
    request_fingerprint = fingerprint(payload.model_dump())

    if idempotency_key:
        replay = find_replay(db, idempotency_key, request_fingerprint)
        if replay is not None:
            response.status_code = replay.status_code
            response.headers["Idempotent-Replay"] = "true"
            return replay.response_body

    debit = ledger.resolve_account(db, payload.debit_account_code)
    credit = ledger.resolve_account(db, payload.credit_account_code)

    entry = ledger.post_entry(
        db,
        description=payload.reference,
        lines=[
            ledger.Line(debit.id, payload.amount_minor, payload.currency),
            ledger.Line(credit.id, -payload.amount_minor, payload.currency),
        ],
    )

    body: dict[str, object] = {
        "entry_id": str(entry.id),
        "reference": payload.reference,
        "amount_minor": payload.amount_minor,
        "currency": payload.currency.upper(),
        "debit_account": debit.code,
        "credit_account": credit.code,
    }

    if idempotency_key:
        remember(
            db,
            key=idempotency_key,
            request_fingerprint=request_fingerprint,
            status_code=status.HTTP_201_CREATED,
            response_body=body,
        )

    db.commit()
    return body
