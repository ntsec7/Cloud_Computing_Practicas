
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from flask import Flask

from app.routes import profile_bp


@pytest.fixture
def client(monkeypatch):

    monkeypatch.setenv('INTERNAL_SERVICE_TOKEN', 'test-secret')

    app = Flask(__name__)
    app.register_blueprint(profile_bp)
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


@pytest.fixture
def headers():

    return {
        'X-Internal-Token': 'test-secret'
    }


def dynamodb_error(error_code):

    return ClientError(
        {'Error': {'Code': error_code}},
        'DynamoDB operation'
    )


# TEST 1: Ruta de salud
def test_health(client):

    response = client.get('/profile/health')

    assert response.status_code == 200
    assert response.json == {
        'message': 'Microservicio de profile funcionando'
    }


# TEST 2: Petición sin token interno
def test_missing_internal_token(client):

    response = client.get('/profile/user123')

    assert response.status_code == 403
    assert response.json['error'] == 'Petición no autorizada'


# TEST 3: Token interno incorrecto
def test_invalid_internal_token(client):

    response = client.get(
        '/profile/user123',
        headers={'X-Internal-Token': 'wrong-token'}
    )

    assert response.status_code == 403


# TEST 4: Token interno no configurado
def test_missing_expected_internal_token(client, monkeypatch):

    monkeypatch.setenv('INTERNAL_SERVICE_TOKEN', '')

    response = client.get(
        '/profile/user123',
        headers={'X-Internal-Token': 'test-secret'}
    )

    assert response.status_code == 403


# TEST 5: Crear perfil correctamente
@patch('app.routes.create_profile')
def test_create_profile_success(mock_create, client, headers):

    response = client.post(
        '/profile',
        headers=headers,
        json={
            'user_id': 'user123',
            'username': 'juan',
            'name': 'Juan',
            'avatar_id': 1
        }
    )

    assert response.status_code == 201
    assert response.json['message'] == 'Perfil creado correctamente'

    mock_create.assert_called_once_with(
        'user123',
        'juan',
        'Juan',
        1
    )


# TEST 6: Crear perfil descartando campos no permitidos
@patch('app.routes.create_profile')
def test_create_profile_ignores_extra_fields(
    mock_create, client, headers
):

    response = client.post(
        '/profile',
        headers=headers,
        json={
            'user_id': 'user123',
            'username': 'juan',
            'name': 'Juan',
            'avatar_id': 1,
            'role': 'admin'
        }
    )

    assert response.status_code == 201

    mock_create.assert_called_once_with(
        'user123',
        'juan',
        'Juan',
        1
    )


# TEST 7: Crear perfil con JSON inválido
def test_create_profile_invalid_json(client, headers):

    response = client.post(
        '/profile',
        headers=headers,
        data='esto no es JSON',
        content_type='application/json'
    )

    assert response.status_code == 400
    assert response.json['error'] == 'JSON inválido'


# TEST 8: Crear perfil con campos obligatorios ausentes
def test_create_profile_missing_fields(client, headers):

    response = client.post(
        '/profile',
        headers=headers,
        json={
            'user_id': 'user123',
            'username': 'juan'
        }
    )

    assert response.status_code == 400
    assert response.json['error'] == 'Faltan campos obligatorios'


# TEST 9: Crear perfil duplicado
@patch('app.routes.create_profile')
def test_create_profile_already_exists(
    mock_create, client, headers
):

    mock_create.side_effect = dynamodb_error(
        'ConditionalCheckFailedException'
    )

    response = client.post(
        '/profile',
        headers=headers,
        json={
            'user_id': 'user123',
            'username': 'juan',
            'name': 'Juan',
            'avatar_id': 1
        }
    )

    assert response.status_code == 409
    assert response.json['error'] == 'El perfil ya existe'


# TEST 10: Consultar perfil existente
@patch('app.routes.get_profile')
def test_get_profile_success(mock_get, client, headers):

    mock_get.return_value = {
        'user_id': 'user123',
        'username': 'juan',
        'name': 'Juan',
        'avatar_id': 1,
        'role': 'client'
    }

    response = client.get(
        '/profile/user123',
        headers=headers
    )

    assert response.status_code == 200
    assert response.json['user_id'] == 'user123'
    assert response.json['username'] == 'juan'


# TEST 11: Consultar perfil inexistente
@patch('app.routes.get_profile')
def test_get_profile_not_found(mock_get, client, headers):

    mock_get.return_value = None

    response = client.get(
        '/profile/unknown',
        headers=headers
    )

    assert response.status_code == 404
    assert response.json['error'] == 'Perfil no encontrado'


# TEST 12: Actualizar perfil correctamente
@patch('app.routes.update_profile')
def test_update_profile_success(mock_update, client, headers):

    mock_update.return_value = True

    response = client.patch(
        '/profile/user123',
        headers=headers,
        json={'username': 'nuevo'}
    )

    assert response.status_code == 200
    assert response.json['message'] == 'Perfil actualizado correctamente'

    mock_update.assert_called_once_with(
        'user123',
        {'username': 'nuevo'}
    )


# TEST 13: Actualizar perfil con JSON vacío
def test_update_profile_empty_json(client, headers):

    response = client.patch(
        '/profile/user123',
        headers=headers,
        json={}
    )

    assert response.status_code == 400
    assert response.json['error'] == 'JSON inválido o vacío'


# TEST 14: Actualizar perfil con campos no permitidos
def test_update_profile_forbidden_fields(client, headers):

    response = client.patch(
        '/profile/user123',
        headers=headers,
        json={'role': 'admin'}
    )

    assert response.status_code == 400
    assert response.json['error'] == 'Hay campos no permitidos'


# TEST 15: Actualizar perfil inexistente
@patch('app.routes.update_profile')
def test_update_profile_not_found(mock_update, client, headers):

    mock_update.return_value = False

    response = client.patch(
        '/profile/user123',
        headers=headers,
        json={'username': 'nuevo'}
    )

    assert response.status_code == 404


# TEST 16: Error al actualizar perfil
@patch('app.routes.update_profile')
def test_update_profile_error(mock_update, client, headers):

    mock_update.side_effect = dynamodb_error('InternalServerError')

    response = client.patch(
        '/profile/user123',
        headers=headers,
        json={'username': 'nuevo'}
    )

    assert response.status_code == 500
    assert response.json['error'] == 'No se pudo actualizar el perfil'


# TEST 17: Eliminar perfil correctamente
@patch('app.routes.delete_profile')
def test_delete_profile_success(mock_delete, client, headers):

    mock_delete.return_value = True

    response = client.delete(
        '/profile/user123',
        headers=headers
    )

    assert response.status_code == 200
    assert response.json['message'] == 'Perfil eliminado correctamente'


# TEST 18: Eliminar perfil inexistente
@patch('app.routes.delete_profile')
def test_delete_profile_not_found(mock_delete, client, headers):

    mock_delete.return_value = False

    response = client.delete(
        '/profile/user123',
        headers=headers
    )

    assert response.status_code == 404
    assert response.json['error'] == 'Perfil no encontrado'


# TEST 19: Error al eliminar perfil
@patch('app.routes.delete_profile')
def test_delete_profile_error(mock_delete, client, headers):

    mock_delete.side_effect = dynamodb_error('InternalServerError')

    response = client.delete(
        '/profile/user123',
        headers=headers
    )

    assert response.status_code == 500
    assert response.json['error'] == 'No se pudo eliminar el perfil'


# TEST 20: Actualización de perfil por administrador
@patch('app.routes.update_profile')
def test_admin_update_profile_success(mock_update, client, headers):

    mock_update.return_value = True

    response = client.patch(
        '/profile/user123/admin',
        headers=headers,
        json={
            'username': 'nuevo',
            'role': 'admin'
        }
    )

    assert response.status_code == 200

    mock_update.assert_called_once_with(
        'user123',
        {
            'username': 'nuevo',
            'role': 'admin'
        },
        admin=True
    )


# TEST 21: Rol no válido
def test_admin_update_profile_invalid_role(client, headers):

    response = client.patch(
        '/profile/user123/admin',
        headers=headers,
        json={'role': 'superadmin'}
    )

    assert response.status_code == 400
    assert response.json['error'] == 'Rol no válido'


# TEST 22: Administrador actualiza perfil inexistente
@patch('app.routes.update_profile')
def test_admin_update_profile_not_found(
    mock_update, client, headers
):

    mock_update.return_value = False

    response = client.patch(
        '/profile/user123/admin',
        headers=headers,
        json={'role': 'admin'}
    )

    assert response.status_code == 404


# TEST 23: Error al actualizar como administrador
@patch('app.routes.update_profile')
def test_admin_update_profile_error(
    mock_update, client, headers
):

    mock_update.side_effect = dynamodb_error('InternalServerError')

    response = client.patch(
        '/profile/user123/admin',
        headers=headers,
        json={'role': 'admin'}
    )

    assert response.status_code == 500
    assert response.json['error'] == 'No se pudo actualizar el perfil'
