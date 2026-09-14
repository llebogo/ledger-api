from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import Principal, require_role
from app.db import get_db
from app.models import JournalEntry
from app.schemas import EntryCreate, EntryOut
from app.services import ledger

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: EntryCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_role("admin", "service")),
) -> JournalEntry:
    lines = []
    for posting in payload.postings:
        account = ledger.resolve_account(db, posting.account_code)
        lines.append(
            ledger.Line(
                account_id=account.id,
                amount_minor=posting.amount_minor,
                currency=account.currency,
            )
        )

    entry = ledger.post_entry(
        db,
        description=payload.description,
        lines=lines,
        external_id=payload.external_id,
    )
    db.commit()
    db.refresh(entry)
    return entry
