import pytest
from httpx import AsyncClient
from app.utils.security import verify_password, get_password_hash, decode_access_token, create_access_token
from app.models.user import User


@pytest.mark.asyncio
async def test_password_hashing():
    pwd = "EnterprisePassword2026!"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


@pytest.mark.asyncio
async def test_token_creation_and_decoding():
    data = {"sub": "user-uuid-1234", "username": "analyst1", "role": "SOC Analyst"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-uuid-1234"
    assert decoded["username"] == "analyst1"
    assert decoded["role"] == "SOC Analyst"


@pytest.mark.asyncio
async def test_login_success_and_cookie(client: AsyncClient, admin_user: User):
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin_test", "password": "AdminPass123!"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["username"] == "admin_test"
    assert body["user"]["role"] == "Administrator"
    assert "ai_verdict_session" in resp.cookies


@pytest.mark.asyncio
async def test_login_failure(client: AsyncClient, admin_user: User):
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin_test", "password": "IncorrectPassword"}
    )
    assert resp.status_code == 401
    assert "Incorrect username or password" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_me(client: AsyncClient, analyst_token: str):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "analyst_test"
    assert resp.json()["role"] == "SOC Analyst"


@pytest.mark.asyncio
async def test_rbac_admin_route_forbidden_for_analyst(client: AsyncClient, analyst_token: str):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    resp = await client.get("/api/users", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_admin_route_allowed_for_admin(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.get("/api/users", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

