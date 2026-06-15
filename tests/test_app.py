import copy
from unittest.mock import patch
import pytest

import app


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    original_db = copy.deepcopy(app.db_data)
    original_status = copy.deepcopy(app.system_status)

    # Prevent tests from writing to disk or launching external processes.
    monkeypatch.setattr(app, "save_database", lambda: None)
    monkeypatch.setattr(app, "load_database", lambda: None)
    monkeypatch.setattr(app, "add_log", lambda message: None)
    monkeypatch.setattr(app, "add_record", lambda category, message, metadata=None: None)

    yield

    app.db_data.clear()
    app.db_data.update(original_db)
    app.system_status.clear()
    app.system_status.update(original_status)


@pytest.fixture
def client():
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        yield client


def test_status_route(client):
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["locked"] is False
    assert "logs" in payload


def test_set_lock_mode_route(client):
    response = client.post("/set_lock_mode", json={"lock_mode": "windows", "lock_timeout": 5})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert app.system_status["lock_mode"] == "windows"
    assert app.system_status["lock_timeout"] == 5.0


def test_trigger_unlock_route_with_invalid_password(client):
    app.system_status["owner_detected"] = False
    response = client.post("/trigger_unlock", json={"password": "invalid"})
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["success"] is False
    assert "Invalid Passcode" in payload["error"]


@patch("app.webbrowser.open")
def test_open_application_youtube(mock_webbrowser_open):
    result = app.open_application("youtube")
    assert "opening youtube" in result.lower()
    mock_webbrowser_open.assert_called_once_with("https://youtube.com")


@patch("app.subprocess.Popen")
@patch("app.webbrowser.open")
def test_open_application_google(mock_webbrowser_open, mock_popen):
    result = app.open_application("google")
    assert "opening google" in result.lower()
    mock_webbrowser_open.assert_called_once_with("https://google.com")


def test_add_task_route(client):
    response = client.post("/tasks", json={"text": "test task from api"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["task"]["text"] == "test task from api"


def test_add_rule_route(client):
    response = client.post("/rules", json={"process": "cmd", "description": "test rule"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["rule"]["process"] == "cmd.exe"
