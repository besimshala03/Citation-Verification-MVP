from fastapi.testclient import TestClient

from backend.app import app


client = TestClient(app)


def test_project_name_empty_rejected():
    response = client.post("/projects", json={"name": "   "})
    assert response.status_code == 400


def test_project_name_too_long_rejected():
    response = client.post("/projects", json={"name": "x" * 121})
    assert response.status_code == 422 or response.status_code == 400
