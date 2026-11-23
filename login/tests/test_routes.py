
from unittest.mock import patch

# ==================================================
# REGISTER
# ==================================================

@patch("app.routes.register_user")
def test_register_success(mock_register, client):
    mock_register.return_value = "user123"

    response = client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "Password123!",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1"
    })

    assert response.status_code == 201
    assert response.json["user_id"] == "user123"
    mock_register.assert_called_once()


def test_register_without_json(client):
    response = client.post("/auth/register")

    assert response.status_code == 400


def test_register_empty_json(client):
    response = client.post("/auth/register", json={})

    assert response.status_code == 400


def test_register_missing_fields(client):
    response = client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "Password123!"
    })

    assert response.status_code == 400


@patch("app.routes.register_user")
def test_register_service_error(mock_register, client):
    mock_register.side_effect = Exception("Error de Cognito")

    response = client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "Password123!",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1"
    })

    assert response.status_code == 500
    assert "error" in response.json


# ==================================================
# LOGIN
# ==================================================

@patch("app.routes.login_user")
def test_login_success(mock_login, client):
    mock_login.return_value = {
        "access_token": "access",
        "id_token": "id",
        "refresh_token": "refresh"
    }

    response = client.post("/auth/login", json={
        "email": "user@example.com",
        "password": "Password123!"
    })

    assert response.status_code == 200
    assert response.json["tokens"]["access_token"] == "access"


def test_login_without_json(client):
    response = client.post("/auth/login")

    assert response.status_code == 400


def test_login_missing_credentials(client):
    response = client.post("/auth/login", json={
        "email": "user@example.com"
    })

    assert response.status_code == 400


@patch("app.routes.login_user")
def test_login_service_error(mock_login, client):
    mock_login.side_effect = Exception("Credenciales incorrectas")

    response = client.post("/auth/login", json={
        "email": "user@example.com",
        "password": "incorrecta"
    })

    assert response.status_code == 401


# ==================================================
# GET MY DATA
# ==================================================

@patch("app.routes.get_my_data")
def test_get_my_data_success(mock_get, client):
    mock_get.return_value = {
        "user_id": "user123",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1",
        "email": "user@example.com"
    }

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer access"}
    )

    assert response.status_code == 200
    assert response.json["user_id"] == "user123"
    mock_get.assert_called_once_with("access")


def test_get_my_data_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_get_my_data_invalid_authorization(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Basic access"}
    )

    assert response.status_code == 401


@patch("app.routes.get_my_data")
def test_get_my_data_service_error(mock_get, client):
    mock_get.side_effect = Exception("Token inválido")

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer access"}
    )

    assert response.status_code == 401


# ==================================================
# UPDATE MY DATA
# ==================================================

@patch("app.routes.update_my_data")
def test_update_my_data_success(mock_update, client):
    response = client.patch(
        "/auth/me",
        headers={"Authorization": "Bearer access"},
        json={
            "username": "nuevo",
            "name": "Nuevo nombre"
        }
    )

    assert response.status_code == 200
    mock_update.assert_called_once_with(
        "access",
        {
            "username": "nuevo",
            "name": "Nuevo nombre"
        }
    )


def test_update_my_data_without_token(client):
    response = client.patch(
        "/auth/me",
        json={"username": "nuevo"}
    )

    assert response.status_code == 401


def test_update_my_data_empty_json(client):
    response = client.patch(
        "/auth/me",
        headers={"Authorization": "Bearer access"},
        json={}
    )

    assert response.status_code == 400


@patch("app.routes.update_my_data")
def test_update_my_data_ignores_forbidden_fields(mock_update, client):
    response = client.patch(
        "/auth/me",
        headers={"Authorization": "Bearer access"},
        json={
            "username": "nuevo",
            "role": "admin"
        }
    )

    assert response.status_code == 200

    mock_update.assert_called_once_with(
        "access",
        {"username": "nuevo"}
    )


@patch("app.routes.update_my_data")
def test_update_my_data_service_error(mock_update, client):
    mock_update.side_effect = Exception("Error actualizando")

    response = client.patch(
        "/auth/me",
        headers={"Authorization": "Bearer access"},
        json={"username": "nuevo"}
    )

    assert response.status_code == 400


# ==================================================
# CHANGE PASSWORD
# ==================================================

@patch("app.routes.change_password")
def test_change_password_success(mock_change, client):
    response = client.post(
        "/auth/change-password",
        headers={"Authorization": "Bearer access"},
        json={
            "previous_password": "OldPassword123!",
            "proposed_password": "NewPassword123!"
        }
    )

    assert response.status_code == 200
    mock_change.assert_called_once_with(
        "access",
        "OldPassword123!",
        "NewPassword123!"
    )


def test_change_password_without_token(client):
    response = client.post(
        "/auth/change-password",
        json={
            "previous_password": "old",
            "proposed_password": "new"
        }
    )

    assert response.status_code == 401


def test_change_password_without_json(client):
    response = client.post(
        "/auth/change-password",
        headers={"Authorization": "Bearer access"}
    )

    assert response.status_code == 400


def test_change_password_missing_fields(client):
    response = client.post(
        "/auth/change-password",
        headers={"Authorization": "Bearer access"},
        json={"previous_password": "old"}
    )

    assert response.status_code == 400


@patch("app.routes.change_password")
def test_change_password_service_error(mock_change, client):
    mock_change.side_effect = Exception("Contraseña incorrecta")

    response = client.post(
        "/auth/change-password",
        headers={"Authorization": "Bearer access"},
        json={
            "previous_password": "old",
            "proposed_password": "new"
        }
    )

    assert response.status_code == 400


# ==================================================
# LOGOUT
# ==================================================

@patch("app.routes.logout_user")
def test_logout_success(mock_logout, client):
    response = client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer access"}
    )

    assert response.status_code == 200
    mock_logout.assert_called_once_with("access")


def test_logout_without_token(client):
    response = client.post("/auth/logout")

    assert response.status_code == 401


@patch("app.routes.logout_user")
def test_logout_service_error(mock_logout, client):
    mock_logout.side_effect = Exception("Error cerrando sesión")

    response = client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer access"}
    )

    assert response.status_code == 401


# ==================================================
# DELETE OWN ACCOUNT
# ==================================================

@patch("app.routes.delete_account")
def test_delete_account_success(mock_delete, client):
    response = client.delete(
        "/auth/account",
        headers={"Authorization": "Bearer access"}
    )

    assert response.status_code == 200
    mock_delete.assert_called_once_with("access")


def test_delete_account_without_token(client):
    response = client.delete("/auth/account")

    assert response.status_code == 401


@patch("app.routes.delete_account")
def test_delete_account_service_error(mock_delete, client):
    mock_delete.side_effect = Exception("Error eliminando cuenta")

    response = client.delete(
        "/auth/account",
        headers={"Authorization": "Bearer access"}
    )

    assert response.status_code == 500


# ==================================================
# ADMIN: GET USER
# ==================================================

@patch("app.routes.get_admin_user_data")
def test_admin_get_user_success(mock_get, client):
    mock_get.return_value = {
        "user_id": "user123",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1",
        "email": "user@example.com",
        "role": "client"
    }

    response = client.get(
        "/admin/users/user123",
        headers={"Authorization": "Bearer admin-token"}
    )

    assert response.status_code == 200
    assert response.json["user_id"] == "user123"

    mock_get.assert_called_once_with("admin-token", "user123")


def test_admin_get_user_without_token(client):
    response = client.get("/admin/users/user123")

    assert response.status_code == 401


@patch("app.routes.get_admin_user_data")
def test_admin_get_user_forbidden(mock_get, client):
    mock_get.side_effect = PermissionError()

    response = client.get(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 403


@patch("app.routes.get_admin_user_data")
def test_admin_get_user_not_found(mock_get, client):
    mock_get.return_value = None

    response = client.get(
        "/admin/users/missing",
        headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 404


@patch("app.routes.get_admin_user_data")
def test_admin_get_user_error(mock_get, client):
    mock_get.side_effect = Exception("Error")

    response = client.get(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 500


# ==================================================
# ADMIN: UPDATE USER
# ==================================================

@patch("app.routes.update_admin_user_data")
def test_admin_update_user_success(mock_update, client):
    mock_update.return_value = True

    response = client.patch(
        "/admin/users/user123",
        headers={"Authorization": "Bearer admin-token"},
        json={"username": "nuevo"}
    )

    assert response.status_code == 200

    mock_update.assert_called_once_with(
        "admin-token",
        "user123",
        {"username": "nuevo"}
    )


def test_admin_update_user_without_token(client):
    response = client.patch(
        "/admin/users/user123",
        json={"username": "nuevo"}
    )

    assert response.status_code == 401


def test_admin_update_user_empty_json(client):
    response = client.patch(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"},
        json={}
    )

    assert response.status_code == 400


@patch("app.routes.update_admin_user_data")
def test_admin_update_user_not_found(mock_update, client):
    mock_update.return_value = False

    response = client.patch(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"},
        json={"username": "nuevo"}
    )

    assert response.status_code == 404


@patch("app.routes.update_admin_user_data")
def test_admin_update_user_forbidden(mock_update, client):
    mock_update.side_effect = PermissionError()

    response = client.patch(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"},
        json={"username": "nuevo"}
    )

    assert response.status_code == 403


@patch("app.routes.update_admin_user_data")
def test_admin_update_user_invalid_data(mock_update, client):
    mock_update.side_effect = ValueError("Campo no permitido")

    response = client.patch(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"},
        json={"password": "new"}
    )

    assert response.status_code == 400


@patch("app.routes.update_admin_user_data")
def test_admin_update_user_error(mock_update, client):
    mock_update.side_effect = Exception("Error")

    response = client.patch(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"},
        json={"username": "nuevo"}
    )

    assert response.status_code == 500


# ==================================================
# ADMIN: CHANGE USER PASSWORD
# ==================================================

@patch("app.routes.change_admin_user_password")
def test_admin_change_password_success(mock_change, client):
    response = client.patch(
        "/admin/users/user123/password",
        headers={"Authorization": "Bearer admin-token"},
        json={"new_password": "NewPassword123!"}
    )

    assert response.status_code == 200

    mock_change.assert_called_once_with(
        "admin-token",
        "user123",
        "NewPassword123!"
    )


def test_admin_change_password_without_token(client):
    response = client.patch(
        "/admin/users/user123/password",
        json={"new_password": "NewPassword123!"}
    )

    assert response.status_code == 401


def test_admin_change_password_invalid_json(client):
    response = client.patch(
        "/admin/users/user123/password",
        headers={"Authorization": "Bearer token"},
        json={}
    )

    assert response.status_code == 400


@patch("app.routes.change_admin_user_password")
def test_admin_change_password_forbidden(mock_change, client):
    mock_change.side_effect = PermissionError("No autorizado")

    response = client.patch(
        "/admin/users/user123/password",
        headers={"Authorization": "Bearer token"},
        json={"new_password": "NewPassword123!"}
    )

    assert response.status_code == 403


@patch("app.routes.change_admin_user_password")
def test_admin_change_password_invalid_value(mock_change, client):
    mock_change.side_effect = ValueError("Contraseña no válida")

    response = client.patch(
        "/admin/users/user123/password",
        headers={"Authorization": "Bearer token"},
        json={"new_password": "NewPassword123!"}
    )

    assert response.status_code == 400


@patch("app.routes.change_admin_user_password")
def test_admin_change_password_error(mock_change, client):
    mock_change.side_effect = Exception("Error")

    response = client.patch(
        "/admin/users/user123/password",
        headers={"Authorization": "Bearer token"},
        json={"new_password": "NewPassword123!"}
    )

    assert response.status_code == 500


# ==================================================
# ADMIN: DELETE USER
# ==================================================

@patch("app.routes.delete_admin_user")
def test_admin_delete_user_success(mock_delete, client):
    mock_delete.return_value = True

    response = client.delete(
        "/admin/users/user123",
        headers={"Authorization": "Bearer admin-token"}
    )

    assert response.status_code == 200
    mock_delete.assert_called_once_with("admin-token", "user123")


def test_admin_delete_user_without_token(client):
    response = client.delete("/admin/users/user123")

    assert response.status_code == 401


@patch("app.routes.delete_admin_user")
def test_admin_delete_user_not_found(mock_delete, client):
    mock_delete.return_value = False

    response = client.delete(
        "/admin/users/missing",
        headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 404


@patch("app.routes.delete_admin_user")
def test_admin_delete_user_forbidden(mock_delete, client):
    mock_delete.side_effect = PermissionError()

    response = client.delete(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 403


@patch("app.routes.delete_admin_user")
def test_admin_delete_user_invalid_value(mock_delete, client):
    mock_delete.side_effect = ValueError("No puedes eliminarte")

    response = client.delete(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 400


@patch("app.routes.delete_admin_user")
def test_admin_delete_user_error(mock_delete, client):
    mock_delete.side_effect = Exception("Error")

    response = client.delete(
        "/admin/users/user123",
        headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 500
