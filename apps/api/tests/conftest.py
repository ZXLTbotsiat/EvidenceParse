from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from evidence_parse.main import create_app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    app = create_app("sqlite+pysqlite:///:memory:", auto_create_schema=True)
    with TestClient(app) as test_client:
        yield test_client
