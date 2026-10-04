import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.db.repository import store
from app.main import app
from tests.test_auth import create_test_token


@pytest.fixture(autouse=True)
def clean_store():
    store.clear()
    yield
    store.clear()


@pytest.mark.asyncio
async def test_project_crud_and_multi_tenant_isolation():
    u_suffix = uuid.uuid4().hex[:8]
    token_a = create_test_token(f"user-a-{u_suffix}", f"user.a.{u_suffix}@studyspace.ai")
    token_b = create_test_token(f"user-b-{u_suffix}", f"user.b.{u_suffix}@studyspace.ai")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Unauthenticated requests to /api/v1/projects are rejected
        unauth_res = await client.get("/api/v1/projects")
        assert unauth_res.status_code == 401
        assert unauth_res.json()["error"]["code"] == "UNAUTHORIZED"

        # 2. User A creates Project A
        res_a = await client.post(
            "/api/v1/projects",
            headers=headers_a,
            json={"name": "Physics 101", "description": "Mechanics", "subject": "PHYS"}
        )
        assert res_a.status_code == 201
        project_a = res_a.json()
        assert project_a["name"] == "Physics 101"
        project_a_id = project_a["id"]

        # 3. User B creates Project B
        res_b = await client.post(
            "/api/v1/projects",
            headers=headers_b,
            json={"name": "Computer Architecture", "description": "RISC-V", "subject": "CS"}
        )
        assert res_b.status_code == 201
        project_b = res_b.json()
        assert project_b["name"] == "Computer Architecture"
        project_b_id = project_b["id"]

        # 4. User A lists projects -> sees ONLY Project A
        list_a = await client.get("/api/v1/projects", headers=headers_a)
        assert list_a.status_code == 200
        data_a = list_a.json()
        assert data_a["total"] == 1
        assert data_a["projects"][0]["id"] == project_a_id

        # 5. User B lists projects -> sees ONLY Project B
        list_b = await client.get("/api/v1/projects", headers=headers_b)
        assert list_b.status_code == 200
        data_b = list_b.json()
        assert data_b["total"] == 1
        assert data_b["projects"][0]["id"] == project_b_id

        # 6. User A retrieves Project A -> 200 OK
        get_a = await client.get(f"/api/v1/projects/{project_a_id}", headers=headers_a)
        assert get_a.status_code == 200
        assert get_a.json()["id"] == project_a_id

        # 7. ISOLATION: User A attempts to retrieve User B's Project B -> 404 NOT FOUND
        idor_get = await client.get(f"/api/v1/projects/{project_b_id}", headers=headers_a)
        assert idor_get.status_code == 404
        assert idor_get.json()["error"]["code"] == "PROJECT_NOT_FOUND"

        # 8. ISOLATION: User A attempts to update User B's Project B -> 404 NOT FOUND
        idor_update = await client.patch(
            f"/api/v1/projects/{project_b_id}",
            headers=headers_a,
            json={"name": "Malicious Modification"}
        )
        assert idor_update.status_code == 404
        assert idor_update.json()["error"]["code"] == "PROJECT_NOT_FOUND"

        # 9. ISOLATION: User A attempts to delete User B's Project B -> 404 NOT FOUND
        idor_del = await client.delete(f"/api/v1/projects/{project_b_id}", headers=headers_a)
        assert idor_del.status_code == 404
        assert idor_del.json()["error"]["code"] == "PROJECT_NOT_FOUND"

        # Verify User B's Project B was not modified or deleted
        verify_b = await client.get(f"/api/v1/projects/{project_b_id}", headers=headers_b)
        assert verify_b.status_code == 200
        assert verify_b.json()["name"] == "Computer Architecture"

        # 10. User A updates Project A successfully
        upd_a = await client.patch(
            f"/api/v1/projects/{project_a_id}",
            headers=headers_a,
            json={"description": "Quantum Mechanics & Waves"}
        )
        assert upd_a.status_code == 200
        assert upd_a.json()["description"] == "Quantum Mechanics & Waves"

        # 11. User A deletes Project A successfully
        del_a = await client.delete(f"/api/v1/projects/{project_a_id}", headers=headers_a)
        assert del_a.status_code == 204

        # Confirm Project A is deleted
        get_deleted = await client.get(f"/api/v1/projects/{project_a_id}", headers=headers_a)
        assert get_deleted.status_code == 404
