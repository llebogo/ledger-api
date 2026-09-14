"""Rules that hold with no database in sight.

These are the cheapest tests in the suite and the ones that catch real bugs:
every way an entry can be illegal is covered here, in milliseconds.
"""

import uuid

import pytest

from app.errors import InvalidEntryError, UnbalancedEntryError
from app.services.ledger import Line, validate_balanced


def line(amount: int, currency: str = "ZAR") -> Line:
    return Line(account_id=uuid.uuid4(), amount_minor=amount, currency=currency)


def test_equal_debit_and_credit_is_balanced() -> None:
    validate_balanced([line(15000), line(-15000)])


def test_three_legs_balance_when_they_sum_to_zero() -> None:
    validate_balanced([line(15000), line(-10000), line(-5000)])


def test_unbalanced_entry_is_rejected() -> None:
    with pytest.raises(UnbalancedEntryError, match="differ by 1"):
        validate_balanced([line(15001), line(-15000)])


def test_single_leg_is_rejected() -> None:
    with pytest.raises(InvalidEntryError, match="at least two"):
        validate_balanced([line(15000)])


def test_zero_amount_leg_is_rejected() -> None:
    with pytest.raises(InvalidEntryError, match="zero"):
        validate_balanced([line(15000), line(-15000), line(0)])


def test_mixed_currency_entry_is_rejected() -> None:
    with pytest.raises(InvalidEntryError, match="Mixed currencies"):
        validate_balanced([line(15000, "ZAR"), line(-15000, "USD")])


def test_currency_comparison_ignores_case() -> None:
    validate_balanced([line(15000, "zar"), line(-15000, "ZAR")])
