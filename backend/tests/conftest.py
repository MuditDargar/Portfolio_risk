import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    from app.config import get_settings
    get_settings.cache_clear()

    from app import database
    database.settings = get_settings()
    database.engine = create_engine(database.settings.database_url, connect_args={"check_same_thread": False})
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    os.close(db_fd)
    os.unlink(db_path)
