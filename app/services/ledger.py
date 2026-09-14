"""Core ledger rules.

Two things are deliberate here:

1. `validate_balanced` is a pure function with no database access, so every rule
   about what makes an entry legal can be tested without Postgres.
2. Balances are derived with SUM(postings) on read. No cached balance column
   exists, so a balance cannot drift out of sync with the entries behind it.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AccountNotFoundError, InvalidEntryError, UnbalancedEntryError
from app.models import Account, JournalEntry, Posting


@dataclass(frozen=True)
class Line:
    account_id: uuid.UUID
    amount_minor: int
    currency: str


def validate_balanced(lines: Sequence[Line]) -> None:
    """Raise if the lines do not form a legal double-entry transaction."""
    if len(lines) < 2:
        raise InvalidEntryError("An entry needs at least two postings.")
    if any(line.amount_minor == 0 for line in lines):
        raise InvalidEntryError("A posting of zero has no meaning.")
    currencies = {line.currency.upper() for line in lines}
    if len(currencies) > 1:
        raise InvalidEntryError(f"Mixed currencies in one entry: {sorted(currencies)}.")
    total = sum(line.amount_minor for line in lines)
    if total != 0:
        raise UnbalancedEntryError(f"Debits and credits differ by {total} minor units.")


def resolve_account(db: Session, code: str) -> Account:
    account = db.scalar(select(Account).where(Account.code == code))
    if account is None:
        raise AccountNotFoundError(f"No account with code {code!r}.")
    return account


def post_entry(
    db: Session,
    *,
    description: str,
    lines: Sequence[Line],
    external_id: str | None = None,
) -> JournalEntry:
    """Write one balanced entry inside the caller's transaction.

    Accounts are locked in a stable order (sorted by id) so that two concurrent
    transactions touching the same pair of accounts can never deadlock each other.
    """
    validate_balanced(lines)

    account_ids = sorted({line.account_id for line in lines})
    locked = db.scalars(
        select(Account).where(Account.id.in_(account_ids)).order_by(Account.id).with_for_update()
    ).all()
    if len(locked) != len(account_ids):
        raise AccountNotFoundError("One or more accounts in this entry do not exist.")

    entry = JournalEntry(description=description, external_id=external_id)
    entry.postings = [
        Posting(
            account_id=line.account_id,
            amount_minor=line.amount_minor,
            currency=line.currency.upper(),
        )
        for line in lines
    ]
    db.add(entry)
    db.flush()
    return entry


def account_balance(db: Session, account_id: uuid.UUID) -> int:
    """Derive the balance. Never read from a stored column, because there isn't one."""
    total = db.scalar(
        select(func.coalesce(func.sum(Posting.amount_minor), 0)).where(
            Posting.account_id == account_id
        )
    )
    return int(total or 0)


def trial_balance(db: Session) -> int:
    """Sum of every posting in the system. Must always be zero."""
    total = db.scalar(select(func.coalesce(func.sum(Posting.amount_minor), 0)))
    return int(total or 0)
