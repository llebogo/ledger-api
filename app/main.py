from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api import accounts, entries, payments, webhooks
from app.auth import create_access_token
from app.config import get_settings
from app.errors import LedgerError
from app.schemas import TokenOut

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

app = FastAPI(
    title="ledger-api",
    version="0.1.0",
    description=(
        "A double-entry ledger. Balances are derived from postings, never stored, so they "
        "cannot drift. Payments are idempotent and webhook deliveries are de-duplicated."
    ),
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
# slowapi's handler is typed against its own exception, not the base Exception
# signature Starlette declares. The cast is safe: it only ever sees RateLimitExceeded.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.exception_handler(LedgerError)
def handle_ledger_error(request: Request, exc: LedgerError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/demo-token", response_model=TokenOut, tags=["meta"])
def demo_token(role: str = "admin") -> TokenOut:
    """Hand out a token so the Swagger page is explorable. Demo only - remove in production."""
    return TokenOut(access_token=create_access_token(subject="demo", role=role))


app.include_router(accounts.router)
app.include_router(entries.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
