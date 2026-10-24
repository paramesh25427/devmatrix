import os
import shutil
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project

# 1. Setup isolated temporary storage
_test_storage_dir = tempfile.mkdtemp(prefix="devmatrix_test_storage_")
settings.storage_dir = _test_storage_dir

# 2. Setup isolated temporary SQLite database
_temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_temp_db_file.close()
_test_db_url = f"sqlite:///{_temp_db_file.name.replace(os.sep, '/')}"

test_engine = create_engine(_test_db_url, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Initializes tables and seeds initial test tenants and users into isolated test DB."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        # Tenant A
        tenant_a = Tenant(
            id="tenant-default",
            name="Default Organization",
            slug="default-org",
            currency="USD",
        )
        db.add(tenant_a)

        # Tenant B
        tenant_b = Tenant(
            id="tenant-beta",
            name="Beta Enterprise",
            slug="beta-enterprise",
            currency="EUR",
        )
        db.add(tenant_b)

        # Users for Tenant A
        user_mgr_a = User(
            id="user-mgr-a",
            tenant_id="tenant-default",
            email="manager@devmatrix.local",
            full_name="Delivery Manager A",
            hashed_password=hash_password("DevMatrix2026!"),
            role="delivery_manager",
            is_active=True,
        )
        user_dev_a = User(
            id="user-dev-a",
            tenant_id="tenant-default",
            email="contributor@devmatrix.local",
            full_name="Developer A",
            hashed_password=hash_password("DevMatrix2026!"),
            role="contributor",
            is_active=True,
        )
        db.add(user_mgr_a)
        db.add(user_dev_a)

        # Users for Tenant B
        user_mgr_b = User(
            id="user-mgr-b",
            tenant_id="tenant-beta",
            email="manager@beta.local",
            full_name="Delivery Manager B",
            hashed_password=hash_password("Beta2026!"),
            role="delivery_manager",
            is_active=True,
        )
        user_dev_b = User(
            id="user-dev-b",
            tenant_id="tenant-beta",
            email="contributor@beta.local",
            full_name="Developer B",
            hashed_password=hash_password("Beta2026!"),
            role="contributor",
            is_active=True,
        )
        db.add(user_mgr_b)
        db.add(user_dev_b)

        # Default Projects
        proj_a = Project(
            id="proj-default",
            tenant_id="tenant-default",
            name="Alpha Project",
            status="intake",
            created_by_id="user-mgr-a",
        )
        proj_b = Project(
            id="proj-beta",
            tenant_id="tenant-beta",
            name="Beta Project",
            status="intake",
            created_by_id="user-mgr-b",
        )
        db.add(proj_a)
        db.add(proj_b)

        db.commit()
    finally:
        db.close()

    yield

    # Teardown
    app.dependency_overrides.clear()
    shutil.rmtree(_test_storage_dir, ignore_errors=True)
    try:
        os.remove(_temp_db_file.name)
    except OSError:
        pass


@pytest.fixture
def token_manager_a() -> str:
    return create_access_token(
        user_id="user-mgr-a",
        email="manager@devmatrix.local",
        role="delivery_manager",
        tenant_id="tenant-default",
    )


@pytest.fixture
def auth_headers_tenant_a(token_manager_a: str) -> dict:
    return {"Authorization": f"Bearer {token_manager_a}"}


@pytest.fixture
def token_contributor_a() -> str:
    return create_access_token(
        user_id="user-dev-a",
        email="contributor@devmatrix.local",
        role="contributor",
        tenant_id="tenant-default",
    )


@pytest.fixture
def auth_headers_contributor_a(token_contributor_a: str) -> dict:
    return {"Authorization": f"Bearer {token_contributor_a}"}


@pytest.fixture
def token_manager_b() -> str:
    return create_access_token(
        user_id="user-mgr-b",
        email="manager@beta.local",
        role="delivery_manager",
        tenant_id="tenant-beta",
    )


@pytest.fixture
def auth_headers_tenant_b(token_manager_b: str) -> dict:
    return {"Authorization": f"Bearer {token_manager_b}"}
