import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@patch("app.api.auth.get_supabase")
def test_signup_success(mock_get_supabase):
    mock_sb = MagicMock()
    mock_res = MagicMock()
    mock_res.user.id = "user-123"
    mock_res.user.model_dump.return_value = {"id": "user-123"}
    mock_res.session.model_dump.return_value = {"access_token": "token"}
    mock_sb.auth.sign_up.return_value = mock_res
    mock_get_supabase.return_value = mock_sb
    
    response = client.post("/api/auth/signup", json={"email": "test@test.com", "password": "pass"})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == "user-123"
    assert response.json()["session"]["access_token"] == "token"
    mock_sb.table.assert_called_with("profiles")

@patch("app.api.auth.get_supabase")
def test_signin_success(mock_get_supabase):
    mock_sb = MagicMock()
    mock_res = MagicMock()
    mock_res.user.id = "user-123"
    mock_res.user.model_dump.return_value = {"id": "user-123"}
    mock_res.session.model_dump.return_value = {"access_token": "token"}
    mock_sb.auth.sign_in_with_password.return_value = mock_res
    mock_get_supabase.return_value = mock_sb
    
    response = client.post("/api/auth/signin", json={"email": "test@test.com", "password": "pass"})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == "user-123"

@patch("app.api.auth.get_supabase")
def test_reset_password_success(mock_get_supabase):
    mock_sb = MagicMock()
    mock_get_supabase.return_value = mock_sb
    
    response = client.post("/api/auth/reset-password", json={"email": "test@test.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "Email sent"
    mock_sb.auth.reset_password_email.assert_called_with("test@test.com")

@patch("app.api.auth.get_supabase")
def test_get_profile_success(mock_get_supabase):
    mock_sb = MagicMock()
    mock_auth_res = MagicMock()
    mock_auth_res.user.id = "user-123"
    mock_auth_res.user.model_dump.return_value = {"id": "user-123"}
    mock_sb.auth.get_user.return_value = mock_auth_res
    
    mock_table_res = MagicMock()
    mock_table_res.data = [{"full_name": "Test User", "username": "test"}]
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_table_res
    mock_get_supabase.return_value = mock_sb
    
    response = client.get("/api/auth/profile", headers={"Authorization": "Bearer token123"})
    assert response.status_code == 200
    assert response.json()["profile"]["full_name"] == "Test User"
    
@patch("app.api.auth.get_supabase")
def test_update_profile_success(mock_get_supabase):
    mock_sb = MagicMock()
    mock_auth_res = MagicMock()
    mock_auth_res.user.id = "user-123"
    mock_sb.auth.get_user.return_value = mock_auth_res
    mock_get_supabase.return_value = mock_sb
    
    response = client.put("/api/auth/profile", json={"full_name": "New Name", "username": "new-user"}, headers={"Authorization": "Bearer token123"})
    assert response.status_code == 200
    assert response.json()["message"] == "Profile updated"
