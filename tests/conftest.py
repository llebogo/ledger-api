"""Shared fixtures.

Tests that need a database use the `db` fixture, which runs each test inside a
transaction and rolls it back afterwards, so tests never see each other's data.
Pure rule tests need none of this and import the service functions directly.
"""

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://ledger:ledger@localhost:5432/ledger_test"
)


@pytest.fixture(scope="session")
def engine() -> Generator[object, None, None]:
    eng = create_engine(TEST_DATABASE_URL, future=True)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine: object) -> Generator[Session, None, None]:
    connection = engine.connect()  # type: ignore[attr-defined]
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
