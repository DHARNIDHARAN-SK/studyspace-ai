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
async def test_revision_checklist_lifecycle_and_progress_stats():
    token_a = create_test_token("user-stud-101", "student.a@studyspace.ai")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create a project
        proj_res = await client.post(
            "/api/v1/projects",
            headers=headers_a,
            json={"name": "Cloud Systems", "subject": "CS 400"},
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        # 2. Initially empty checklist
        list_res = await client.get(f"/api/v1/projects/{project_id}/revision", headers=headers_a)
        assert list_res.status_code == 200
        data = list_res.json()
        assert data["stats"]["total_items"] == 0
        assert data["stats"]["completion_percentage"] == 0.0

        # 3. Create 3 revision items
        item1_res = await client.post(
            f"/api/v1/projects/{project_id}/revision",
            headers=headers_a,
            json={"title": "Cloud Service Models (IaaS, PaaS, SaaS)", "status": "not_started"},
        )
        assert item1_res.status_code == 201
        item1 = item1_res.json()
        assert item1["status"] == "not_started"

        item2_res = await client.post(
            f"/api/v1/projects/{project_id}/revision",
            headers=headers_a,
            json={"title": "Hypervisors & Virtualization", "status": "learning"},
        )
        assert item2_res.status_code == 201
        item2 = item2_res.json()
        assert item2["status"] == "learning"

        item3_res = await client.post(
            f"/api/v1/projects/{project_id}/revision",
            headers=headers_a,
            json={"title": "Shared Responsibility Model", "status": "revised"},
        )
        assert item3_res.status_code == 201

        # 4. Check progress calculations
        list_res = await client.get(f"/api/v1/projects/{project_id}/revision", headers=headers_a)
        assert list_res.status_code == 200
        stats = list_res.json()["stats"]
        assert stats["total_items"] == 3
        assert stats["not_started"] == 1
        assert stats["learning"] == 1
        assert stats["revised"] == 1
        assert stats["completion_percentage"] == 33.3

        # 5. Link item 1 to a source document
        doc_uuid = str(uuid.uuid4())
        link_res = await client.post(
            f"/api/v1/projects/{project_id}/revision/{item1['id']}/links",
            headers=headers_a,
            json={"target_type": "document", "target_id": doc_uuid, "metadata": {"page": 12}},
        )
        assert link_res.status_code == 201
        assert link_res.json()["target_type"] == "document"
        assert link_res.json()["target_id"] == doc_uuid

        # 6. Update item 1 from not_started to revised
        patch_res = await client.patch(
            f"/api/v1/projects/{project_id}/revision/{item1['id']}",
            headers=headers_a,
            json={"status": "revised", "notes": "Reviewed lecture slides 1-25"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "revised"
        assert patch_res.json()["notes"] == "Reviewed lecture slides 1-25"

        # 7. Check updated progress (2 revised out of 3 -> 66.7%)
        list_res = await client.get(f"/api/v1/projects/{project_id}/revision", headers=headers_a)
        stats = list_res.json()["stats"]
        assert stats["revised"] == 2
        assert stats["completion_percentage"] == 66.7

        # 8. Delete item 2
        del_res = await client.delete(f"/api/v1/projects/{project_id}/revision/{item2['id']}", headers=headers_a)
        assert del_res.status_code == 204

        # 9. Verify deletion and stats update (2 total, 2 revised -> 100%)
        list_res = await client.get(f"/api/v1/projects/{project_id}/revision", headers=headers_a)
        stats = list_res.json()["stats"]
        assert stats["total_items"] == 2
        assert stats["revised"] == 2
        assert stats["completion_percentage"] == 100.0


@pytest.mark.asyncio
async def test_study_guide_generation_and_retrieval():
    token = create_test_token("user-stud-102", "student.b@studyspace.ai")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        proj = (await client.post("/api/v1/projects", headers=headers, json={"name": "Operating Systems"})).json()
        project_id = proj["id"]

        # Generate study guide
        guide_res = await client.post(
            f"/api/v1/projects/{project_id}/guides",
            headers=headers,
            json={
                "topic": "Process Scheduling and Deadlocks",
                "guide_type": "summary",
                "focus_areas": ["Round Robin", "Banker's Algorithm", "Mutex Locks"],
            },
        )
        assert guide_res.status_code == 201
        guide = guide_res.json()
        assert "Process Scheduling and Deadlocks" in guide["title"]
        assert "Study Guide" in guide["content"]
        assert "Executive Summary" in guide["content"]
        guide_id = guide["id"]

        # List study guides
        list_res = await client.get(f"/api/v1/projects/{project_id}/guides", headers=headers)
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1
        assert list_res.json()["guides"][0]["id"] == guide_id

        # Get individual study guide
        get_res = await client.get(f"/api/v1/projects/{project_id}/guides/{guide_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == guide_id


@pytest.mark.asyncio
async def test_quiz_generation_answers_hidden_and_submission_grading():
    token = create_test_token("user-stud-103", "student.c@studyspace.ai")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        proj = (await client.post("/api/v1/projects", headers=headers, json={"name": "Distributed Systems"})).json()
        project_id = proj["id"]

        # Generate quiz
        quiz_res = await client.post(
            f"/api/v1/projects/{project_id}/quizzes",
            headers=headers,
            json={
                "title": "CAP Theorem & Consensus",
                "topic": "CAP Theorem, Paxos, and Raft",
                "num_questions": 3,
                "difficulty": "medium",
                "question_types": ["mcq", "short_answer", "difficult"],
            },
        )
        assert quiz_res.status_code == 201
        quiz = quiz_res.json()
        quiz_id = quiz["id"]
        assert len(quiz["questions"]) >= 1

        # CRITICAL TEST: Answers & explanations MUST BE HIDDEN before submission
        first_q = quiz["questions"][0]
        assert "expected_answer" not in first_q
        assert "explanation" not in first_q

        # Verify public get quiz also hides answers
        pub_quiz = (await client.get(f"/api/v1/projects/{project_id}/quizzes/{quiz_id}", headers=headers)).json()
        for q in pub_quiz["questions"]:
            assert "expected_answer" not in q
            assert "explanation" not in q

        # Submit attempt
        submit_res = await client.post(
            f"/api/v1/projects/{project_id}/quizzes/{quiz_id}/attempt",
            headers=headers,
            json={
                "responses": [
                    {"question_id": q["id"], "submitted_answer": "A"}
                    for q in pub_quiz["questions"]
                ]
            },
        )
        assert submit_res.status_code == 200
        attempt = submit_res.json()
        assert "score" in attempt
        assert "percentage" in attempt
        assert attempt["total_questions"] == len(pub_quiz["questions"])

        # CRITICAL TEST: Attempt result REVEALS expected answers and explanations
        for r in attempt["results"]:
            assert "expected_answer" in r
            assert "explanation" in r
            assert "feedback" in r
            assert "is_correct" in r


@pytest.mark.asyncio
async def test_project_content_export():
    token = create_test_token("user-stud-104", "student.d@studyspace.ai")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        proj = (await client.post("/api/v1/projects", headers=headers, json={"name": "Software Engineering"})).json()
        project_id = proj["id"]

        # Create revision item
        await client.post(
            f"/api/v1/projects/{project_id}/revision",
            headers=headers,
            json={"title": "Design Patterns", "status": "revised"},
        )

        # Export revision checklist
        exp_res = await client.post(
            f"/api/v1/projects/{project_id}/export",
            headers=headers,
            json={"source_type": "revision", "source_id": project_id, "format": "markdown"},
        )
        assert exp_res.status_code == 200
        exp = exp_res.json()
        assert exp["status"] == "completed"
        assert exp["filename"].endswith(".md")
        assert "# Revision Checklist" in exp["content"]
        assert "Design Patterns" in exp["content"]
