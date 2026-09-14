class LedgerError(Exception):
    """Base class for domain errors. Mapped to HTTP responses in app.main."""

    status_code = 400


class UnbalancedEntryError(LedgerError):
    """Debits and credits do not sum to zero."""


class InvalidEntryError(LedgerError):
    """Structurally invalid entry: too few legs, zero amount, or mixed currency."""


class AccountNotFoundError(LedgerError):
    status_code = 404


class IdempotencyConflictError(LedgerError):
    """Same Idempotency-Key replayed with a different request body."""

    status_code = 409
