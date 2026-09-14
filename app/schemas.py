import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import AccountType


class AccountCreate(BaseModel):
    code: str = Field(max_length=32)
    name: str = Field(max_length=128)
    type: AccountType
    currency: str = Field(min_length=3, max_length=3)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    type: AccountType
    currency: str


class BalanceOut(BaseModel):
    account_id: uuid.UUID
    code: str
    currency: str
    balance_minor: int


class PostingIn(BaseModel):
    account_code: str
    amount_minor: int = Field(description="Signed minor units. Debit > 0, credit < 0.")


class PostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: uuid.UUID
    amount_minor: int
    currency: str


class EntryCreate(BaseModel):
    description: str = Field(max_length=256)
    external_id: str | None = None
    postings: list[PostingIn] = Field(min_length=2)


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    external_id: str | None
    occurred_at: datetime
    postings: list[PostingOut]


class PaymentCreate(BaseModel):
    debit_account_code: str
    credit_account_code: str
    amount_minor: int = Field(gt=0, description="Positive minor units, e.g. 15000 = R150.00")
    currency: str = Field(min_length=3, max_length=3)
    reference: str = Field(max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
