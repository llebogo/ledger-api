import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Principal, get_principal, require_role
from app.db import get_db
from app.errors import AccountNotFoundError
from app.models import Account
from app.schemas import AccountCreate, AccountOut, BalanceOut
from app.services import ledger

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_role("admin")),
) -> Account:
    account = Account(
        code=payload.code,
        name=payload.name,
        type=payload.type,
        currency=payload.currency.upper(),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("", response_model=list[AccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.code)).all())


@router.get("/{account_id}/balance", response_model=BalanceOut)
def get_balance(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
) -> BalanceOut:
    account = db.get(Account, account_id)
    if account is None:
        raise AccountNotFoundError(f"No account with id {account_id}.")
    return BalanceOut(
        account_id=account.id,
        code=account.code,
        currency=account.currency,
        balance_minor=ledger.account_balance(db, account.id),
    )
