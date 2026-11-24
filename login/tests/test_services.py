
import base64
import hashlib
import hmac
from unittest.mock import MagicMock, patch

import pytest
import requests
from botocore.exceptions import ClientError

from app.services import (
    calculate_secret_hash,
    change_admin_user_password,
    change_password,
    delete_account,
    delete_admin_user,
    get_admin_user_data,
    get_my_data,
    login_user,
    logout_user,
    register_user,
    update_admin_user_data,
    update_my_data,
)


def make_cognito_user(user_id="user123", username="user@example.com"):
    return {
        "Username": username,
        "UserAttributes": [
            {"Name": "sub", "Value": user_id},
            {"Name": "email", "Value": "user@example.com"}
        ]
    }


def make_profile_response(data, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = data
    response.raise_for_status.return_value = None
    return response


def make_admin_profile(role="admin"):
    return {
        "username": "admin",
        "name": "Administrador",
        "avatar_id": "1",
        "role": role
    }


def make_client_error(code="SomeError"):
    return ClientError(
        {"Error": {"Code": code, "Message": "Error de prueba"}},
        "TestOperation"
    )


# --------------------------------------------------
# CALCULATE SECRET HASH
# --------------------------------------------------

def test_calculate_secret_hash():
    from app import services

    username = "user@example.com"

    message = username + services.CLIENT_ID

    expected = base64.b64encode(
        hmac.new(
            services.CLIENT_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).digest()
    ).decode()

    assert calculate_secret_hash(username) == expected


# --------------------------------------------------
# REGISTER USER
# --------------------------------------------------

@patch("app.services.requests.post")
@patch("app.services.cognito")
def test_register_user_success(mock_cognito, mock_post):
    mock_cognito.admin_create_user.return_value = {
        "User": {"Username": "cognito-user"}
    }

    mock_cognito.admin_get_user.return_value = {
        "UserAttributes": [
            {"Name": "sub", "Value": "user123"}
        ]
    }

    mock_post.return_value = make_profile_response({})

    result = register_user(
        "user@example.com",
        "Password123!",
        "username",
        "Nombre",
        "1"
    )

    assert result == "user123"

    mock_cognito.admin_create_user.assert_called_once()
    mock_cognito.admin_set_user_password.assert_called_once()
    mock_cognito.admin_get_user.assert_called_once()

    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["json"]["user_id"] == "user123"


@patch("app.services.cognito")
def test_register_user_error_creating_user(mock_cognito):
    mock_cognito.admin_create_user.side_effect = make_client_error()

    with pytest.raises(ClientError):
        register_user(
            "user@example.com",
            "Password123!",
            "username",
            "Nombre",
            "1"
        )

    mock_cognito.admin_set_user_password.assert_not_called()


@patch("app.services.cognito")
def test_register_user_error_setting_password(mock_cognito):
    mock_cognito.admin_create_user.return_value = {
        "User": {"Username": "cognito-user"}
    }

    mock_cognito.admin_set_user_password.side_effect = make_client_error()

    with pytest.raises(ClientError):
        register_user(
            "user@example.com",
            "Password123!",
            "username",
            "Nombre",
            "1"
        )

    mock_cognito.admin_delete_user.assert_called_once()


@patch("app.services.requests.post")
@patch("app.services.cognito")
def test_register_user_error_creating_profile(mock_cognito, mock_post):
    mock_cognito.admin_create_user.return_value = {
        "User": {"Username": "cognito-user"}
    }

    mock_cognito.admin_get_user.return_value = {
        "UserAttributes": [
            {"Name": "sub", "Value": "user123"}
        ]
    }

    mock_post.return_value.raise_for_status.side_effect = requests.HTTPError(
        "Error en profile"
    )

    with pytest.raises(requests.HTTPError):
        register_user(
            "user@example.com",
            "Password123!",
            "username",
            "Nombre",
            "1"
        )

    mock_cognito.admin_delete_user.assert_called_once()


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@patch("app.services.cognito")
def test_login_user_success(mock_cognito):
    mock_cognito.admin_initiate_auth.return_value = {
        "AuthenticationResult": {
            "AccessToken": "access",
            "IdToken": "id",
            "RefreshToken": "refresh",
            "ExpiresIn": 3600,
            "TokenType": "Bearer"
        }
    }

    result = login_user("user@example.com", "Password123!")

    assert result == {
        "access_token": "access",
        "id_token": "id",
        "refresh_token": "refresh",
        "expires_in": 3600,
        "token_type": "Bearer"
    }

    mock_cognito.admin_initiate_auth.assert_called_once()


@patch("app.services.cognito")
def test_login_user_error(mock_cognito):
    mock_cognito.admin_initiate_auth.side_effect = make_client_error()

    with pytest.raises(ClientError):
        login_user("user@example.com", "incorrecta")


# --------------------------------------------------
# GET MY DATA
# --------------------------------------------------

@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_get_my_data_success(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user()

    mock_get.return_value = make_profile_response({
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1",
        "role": "client"
    })

    result = get_my_data("access-token")

    assert result == {
        "user_id": "user123",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1",
        "email": "user@example.com"
    }

    mock_cognito.get_user.assert_called_once_with(
        AccessToken="access-token"
    )


@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_get_my_data_admin_includes_role(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user()

    mock_get.return_value = make_profile_response({
        "username": "admin",
        "name": "Administrador",
        "avatar_id": "1",
        "role": "admin"
    })

    result = get_my_data("access-token")

    assert result["role"] == "admin"


@patch("app.services.cognito")
def test_get_my_data_cognito_error(mock_cognito):
    mock_cognito.get_user.side_effect = make_client_error()

    with pytest.raises(ClientError):
        get_my_data("access-token")


# --------------------------------------------------
# UPDATE MY DATA
# --------------------------------------------------

@patch("app.services.requests.patch")
@patch("app.services.cognito")
def test_update_my_data_profile_fields(mock_cognito, mock_patch):
    mock_cognito.get_user.return_value = make_cognito_user()
    mock_patch.return_value = make_profile_response({})

    result = update_my_data(
        "access-token",
        {"username": "nuevo", "name": "Nuevo nombre"}
    )

    assert result is True
    mock_patch.assert_called_once()

    assert mock_patch.call_args.kwargs["json"] == {
        "username": "nuevo",
        "name": "Nuevo nombre"
    }


@patch("app.services.cognito")
def test_update_my_data_email(mock_cognito):
    mock_cognito.get_user.return_value = make_cognito_user()

    result = update_my_data(
        "access-token",
        {"email": "nuevo@example.com"}
    )

    assert result is True

    mock_cognito.admin_update_user_attributes.assert_called_once()


@patch("app.services.requests.patch")
@patch("app.services.cognito")
def test_update_my_data_error_profile(mock_cognito, mock_patch):
    mock_cognito.get_user.return_value = make_cognito_user()
    mock_patch.return_value.raise_for_status.side_effect = requests.HTTPError(
        "Error en profile"
    )

    with pytest.raises(requests.HTTPError):
        update_my_data(
            "access-token",
            {"username": "nuevo"}
        )


# --------------------------------------------------
# PASSWORD AND LOGOUT
# --------------------------------------------------

@patch("app.services.cognito")
def test_change_password_success(mock_cognito):
    change_password("access", "old-password", "new-password")

    mock_cognito.change_password.assert_called_once_with(
        AccessToken="access",
        PreviousPassword="old-password",
        ProposedPassword="new-password"
    )


@patch("app.services.cognito")
def test_change_password_error(mock_cognito):
    mock_cognito.change_password.side_effect = make_client_error()

    with pytest.raises(ClientError):
        change_password("access", "old", "new")


@patch("app.services.cognito")
def test_logout_user_success(mock_cognito):
    logout_user("access")

    mock_cognito.global_sign_out.assert_called_once_with(
        AccessToken="access"
    )


# --------------------------------------------------
# DELETE ACCOUNT
# --------------------------------------------------

@patch("app.services.delete_game_data")
@patch("app.services.requests.delete")
@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_delete_account_success(mock_cognito, mock_get, mock_delete, mock_delete_game_data):
    mock_cognito.get_user.return_value = make_cognito_user()

    mock_get.return_value = make_profile_response({
        "user_id": "user123",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1"
    })

    mock_delete.return_value = make_profile_response({})

    mock_delete_game_data.return_value = {
        "deleted_games": 1,
        "deleted_responses": 3
    }

    delete_account("access")

    mock_delete.assert_called_once()
    mock_cognito.admin_delete_user.assert_called_once()
    mock_delete_game_data.assert_called_once_with("user123")


@patch("app.services.delete_game_data")
@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_delete_account_without_profile(mock_cognito, mock_get, mock_delete_game_data):
    mock_cognito.get_user.return_value = make_cognito_user()
    mock_get.return_value = make_profile_response({}, 404)

    mock_delete_game_data.return_value = {
        "deleted_games": 1,
        "deleted_responses": 3
    }

    delete_account("access")

    mock_cognito.admin_delete_user.assert_called_once()
    mock_delete_game_data.assert_called_once_with("user123")


@patch("app.services.delete_game_data")
@patch("app.services.requests.post")
@patch("app.services.requests.delete")
@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_delete_account_restores_profile_if_cognito_fails(
    mock_cognito, mock_get, mock_delete, mock_post, mock_delete_game_data
):
    profile = {
        "user_id": "user123",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1"
    }

    mock_cognito.get_user.return_value = make_cognito_user()
    mock_get.return_value = make_profile_response(profile)
    mock_delete.return_value = make_profile_response({})
    mock_cognito.admin_delete_user.side_effect = make_client_error()
    mock_post.return_value = make_profile_response({})
    mock_delete_game_data.return_value = {
        "deleted_games": 1,
        "deleted_responses": 3
    }

    with pytest.raises(ClientError):
        delete_account("access")

    mock_post.assert_called_once()
    mock_delete_game_data.assert_called_once_with("user123")


# --------------------------------------------------
# ADMIN: GET USER DATA
# --------------------------------------------------

@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_get_admin_user_data_success(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    mock_get.side_effect = [
        make_profile_response(make_admin_profile()),
        make_profile_response({
            "username": "usuario",
            "name": "Nombre",
            "avatar_id": "1",
            "role": "client"
        })
    ]

    mock_cognito.list_users.return_value = {
        "Users": [{
            "Username": "user@example.com",
            "Attributes": [
                {"Name": "sub", "Value": "user123"},
                {"Name": "email", "Value": "user@example.com"}
            ]
        }]
    }

    result = get_admin_user_data("admin-token", "user123")

    assert result == {
        "user_id": "user123",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1",
        "email": "user@example.com",
        "role": "client"
    }


@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_get_admin_user_data_forbidden(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user("user123")
    mock_get.return_value = make_profile_response(
        make_admin_profile(role="client")
    )

    with pytest.raises(PermissionError):
        get_admin_user_data("token", "other-user")


@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_get_admin_user_data_not_found(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    mock_get.side_effect = [
        make_profile_response(make_admin_profile()),
        make_profile_response({}, 404)
    ]

    result = get_admin_user_data("admin-token", "missing")

    assert result is None


# --------------------------------------------------
# ADMIN: UPDATE USER DATA
# --------------------------------------------------

@patch("app.services.requests.patch")
@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_update_admin_user_data_success(
    mock_cognito, mock_get, mock_patch
):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    mock_get.side_effect = [
        make_profile_response(make_admin_profile()),
        make_profile_response({"user_id": "user123"})
    ]

    mock_patch.return_value = make_profile_response({})

    result = update_admin_user_data(
        "admin-token",
        "user123",
        {"username": "nuevo"}
    )

    assert result is True
    mock_patch.assert_called_once()


@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_update_admin_user_data_forbidden(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user("user123")
    mock_get.return_value = make_profile_response(
        make_admin_profile(role="client")
    )

    with pytest.raises(PermissionError):
        update_admin_user_data(
            "token",
            "other-user",
            {"username": "nuevo"}
        )


@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_update_admin_user_data_invalid_fields(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    mock_get.side_effect = [
        make_profile_response(make_admin_profile()),
        make_profile_response({"user_id": "user123"})
    ]

    with pytest.raises(ValueError):
        update_admin_user_data(
            "admin-token",
            "user123",
            {"password": "new-password"}
        )


@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_update_admin_user_data_not_found(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    mock_get.side_effect = [
        make_profile_response(make_admin_profile()),
        make_profile_response({}, 404)
    ]

    result = update_admin_user_data(
        "admin-token",
        "missing",
        {"username": "nuevo"}
    )

    assert result is False


# --------------------------------------------------
# ADMIN: CHANGE PASSWORD
# --------------------------------------------------

@patch("app.services.cognito")
def test_change_admin_user_password_success(mock_cognito):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    with patch("app.services.requests.get") as mock_get:
        mock_get.return_value = make_profile_response(
            make_admin_profile()
        )

        mock_cognito.list_users.return_value = {
            "Users": [{"Username": "target@example.com"}]
        }

        result = change_admin_user_password(
            "admin-token",
            "user123",
            "NewPassword123!"
        )

    assert result is True
    mock_cognito.admin_set_user_password.assert_called_once()


@patch("app.services.cognito")
def test_change_admin_user_password_cannot_change_own(mock_cognito):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    with pytest.raises(ValueError):
        change_admin_user_password(
            "admin-token",
            "admin123",
            "NewPassword123!"
        )


@patch("app.services.cognito")
def test_change_admin_user_password_not_admin(mock_cognito):
    mock_cognito.get_user.return_value = make_cognito_user("user123")

    with patch("app.services.requests.get") as mock_get:
        mock_get.return_value = make_profile_response(
            make_admin_profile(role="client")
        )

        with pytest.raises(PermissionError):
            change_admin_user_password(
                "token",
                "other-user",
                "NewPassword123!"
            )


# --------------------------------------------------
# ADMIN: DELETE USER
# --------------------------------------------------

@patch("app.services.delete_game_data")
@patch("app.services.requests.delete")
@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_delete_admin_user_success(mock_cognito, mock_get, mock_delete, mock_delete_game_data):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    profile = {
        "user_id": "user123",
        "username": "usuario",
        "name": "Nombre",
        "avatar_id": "1"
    }

    mock_get.side_effect = [
        make_profile_response(make_admin_profile()),
        make_profile_response(profile)
    ]

    mock_cognito.list_users.return_value = {
        "Users": [{
            "Username": "user@example.com",
            "Attributes": [
                {"Name": "sub", "Value": "user123"}
            ]
        }]
    }

    mock_delete.return_value = make_profile_response({})

    mock_delete_game_data.return_value = {
        "deleted_games": 1,
        "deleted_responses": 3
    }

    result = delete_admin_user("admin-token", "user123")

    assert result is True
    mock_delete.assert_called_once()
    mock_cognito.admin_delete_user.assert_called_once()
    mock_delete_game_data.assert_called_once_with("user123")


@patch("app.services.cognito")
def test_delete_admin_user_cannot_delete_self(mock_cognito):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    with pytest.raises(ValueError):
        delete_admin_user("admin-token", "admin123")


@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_delete_admin_user_forbidden(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user("user123")
    mock_get.return_value = make_profile_response(
        make_admin_profile(role="client")
    )

    with pytest.raises(PermissionError):
        delete_admin_user("token", "other-user")


@patch("app.services.requests.get")
@patch("app.services.cognito")
def test_delete_admin_user_not_found(mock_cognito, mock_get):
    mock_cognito.get_user.return_value = make_cognito_user("admin123")

    mock_get.side_effect = [
        make_profile_response(make_admin_profile()),
        make_profile_response({}, 404)
    ]

    result = delete_admin_user("admin-token", "missing")

    assert result is False
