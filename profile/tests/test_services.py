
from unittest.mock import patch, Mock

from botocore.exceptions import ClientError

from app.services import (
    create_profile,
    get_profile,
    update_profile,
    delete_profile
)


# Simula un error de DynamoDB
def dynamodb_error(error_code):
    return ClientError(
        {'Error': {'Code': error_code}},
        'DynamoDB operation'
    )


# TEST 1: Crear perfil correctamente
@patch('app.services.get_profile_table')
def test_create_profile_success(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    create_profile('user123', 'juan', 'Juan', 1)

    mock_table.put_item.assert_called_once_with(
        Item={
            'user_id': 'user123',
            'username': 'juan',
            'name': 'Juan',
            'avatar_id': 1,
            'role': 'client'
        },
        ConditionExpression='attribute_not_exists(user_id)'
    )


# TEST 2: No se puede crear un perfil duplicado
@patch('app.services.get_profile_table')
def test_create_profile_already_exists(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    mock_table.put_item.side_effect = dynamodb_error(
        'ConditionalCheckFailedException'
    )

    try:
        create_profile('user123', 'juan', 'Juan', 1)
        assert False, 'Debería haberse lanzado ClientError'
    except ClientError as error:
        assert error.response['Error']['Code'] == 'ConditionalCheckFailedException'


# TEST 3: Recuperar perfil existente
@patch('app.services.get_profile_table')
def test_get_profile_success(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    expected_profile = {
        'user_id': 'user123',
        'username': 'juan',
        'name': 'Juan',
        'avatar_id': 1,
        'role': 'client'
    }

    mock_table.get_item.return_value = {
        'Item': expected_profile
    }

    result = get_profile('user123')

    assert result == expected_profile

    mock_table.get_item.assert_called_once_with(
        Key={'user_id': 'user123'}
    )


# TEST 4: Recuperar perfil inexistente
@patch('app.services.get_profile_table')
def test_get_profile_not_found(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    mock_table.get_item.return_value = {}

    result = get_profile('unknown')

    assert result is None


# TEST 5: Actualizar perfil correctamente
@patch('app.services.get_profile_table')
def test_update_profile_success(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    result = update_profile(
        'user123',
        {'username': 'nuevo_nombre'}
    )

    assert result is True

    mock_table.update_item.assert_called_once_with(
        Key={'user_id': 'user123'},
        UpdateExpression='SET #username = :username',
        ExpressionAttributeNames={
            '#username': 'username'
        },
        ExpressionAttributeValues={
            ':username': 'nuevo_nombre'
        },
        ConditionExpression='attribute_exists(user_id)'
    )


# TEST 6: Actualizar varios campos
@patch('app.services.get_profile_table')
def test_update_profile_multiple_fields(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    result = update_profile(
        'user123',
        {
            'username': 'nuevo',
            'name': 'Nuevo nombre'
        }
    )

    assert result is True

    arguments = mock_table.update_item.call_args.kwargs

    assert arguments['ExpressionAttributeNames'] == {
        '#username': 'username',
        '#name': 'name'
    }

    assert arguments['ExpressionAttributeValues'] == {
        ':username': 'nuevo',
        ':name': 'Nuevo nombre'
    }


# TEST 7: No hay campos válidos para actualizar
@patch('app.services.get_profile_table')
def test_update_profile_no_valid_fields(mock_get_table):

    result = update_profile(
        'user123',
        {'role': 'admin'}
    )

    assert result is False

    mock_get_table.assert_not_called()


# TEST 8: Un cliente no puede modificar su rol
@patch('app.services.get_profile_table')
def test_update_profile_client_cannot_change_role(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    result = update_profile(
        'user123',
        {'role': 'admin'},
        admin=False
    )

    assert result is False

    mock_table.update_item.assert_not_called()


# TEST 9: Un administrador puede modificar el rol
@patch('app.services.get_profile_table')
def test_update_profile_admin_can_change_role(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    result = update_profile(
        'user123',
        {'role': 'admin'},
        admin=True
    )

    assert result is True

    arguments = mock_table.update_item.call_args.kwargs

    assert arguments['ExpressionAttributeNames'] == {
        '#role': 'role'
    }

    assert arguments['ExpressionAttributeValues'] == {
        ':role': 'admin'
    }


# TEST 10: Perfil inexistente al actualizar
@patch('app.services.get_profile_table')
def test_update_profile_not_found(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    mock_table.update_item.side_effect = dynamodb_error(
        'ConditionalCheckFailedException'
    )

    result = update_profile(
        'unknown',
        {'username': 'nuevo'}
    )

    assert result is False


# TEST 11: Error inesperado al actualizar
@patch('app.services.get_profile_table')
def test_update_profile_unexpected_error(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    mock_table.update_item.side_effect = dynamodb_error(
        'InternalServerError'
    )

    try:
        update_profile('user123', {'username': 'nuevo'})
        assert False, 'Debería haberse lanzado ClientError'
    except ClientError as error:
        assert error.response['Error']['Code'] == 'InternalServerError'


# TEST 12: Eliminar perfil correctamente
@patch('app.services.get_profile_table')
def test_delete_profile_success(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    result = delete_profile('user123')

    assert result is True

    mock_table.delete_item.assert_called_once_with(
        Key={'user_id': 'user123'},
        ConditionExpression='attribute_exists(user_id)'
    )


# TEST 13: Eliminar perfil inexistente
@patch('app.services.get_profile_table')
def test_delete_profile_not_found(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    mock_table.delete_item.side_effect = dynamodb_error(
        'ConditionalCheckFailedException'
    )

    result = delete_profile('unknown')

    assert result is False


# TEST 14: Error inesperado al eliminar
@patch('app.services.get_profile_table')
def test_delete_profile_unexpected_error(mock_get_table):

    mock_table = Mock()
    mock_get_table.return_value = mock_table

    mock_table.delete_item.side_effect = dynamodb_error(
        'InternalServerError'
    )

    try:
        delete_profile('user123')
        assert False, 'Debería haberse lanzado ClientError'
    except ClientError as error:
        assert error.response['Error']['Code'] == 'InternalServerError'
