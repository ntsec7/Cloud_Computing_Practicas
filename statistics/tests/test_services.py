from unittest.mock import patch, Mock

from botocore.exceptions import ClientError
import requests


from app.services import (
    calculate_statistics,
    calculate_game_statistics,
    calculate_general_statistics,
    get_authenticated_user,
    get_user_role,
    authenticate_user,
    call_game_service,
    get_game_data,
    get_game_responses,
    get_user_responses,
    get_game_owner,
    get_game_statistics,
    get_general_statistics
)


# TEST 1: No hay respuestas
def test_calculate_statistics_empty():

    result = calculate_statistics([])

    assert result == {
        'total_questions': 0,
        'correct_answers': 0,
        'incorrect_answers': 0,
        'accuracy': 0,
        'average_response_time': 0
    }


# TEST 2: Todas las respuestas son correctas
def test_calculate_statistics_all_correct():

    responses = [
        {'is_correct': True, 'response_time_ms': 1000},
        {'is_correct': True, 'response_time_ms': 2000}
    ]

    result = calculate_statistics(responses)

    assert result['total_questions'] == 2
    assert result['correct_answers'] == 2
    assert result['incorrect_answers'] == 0
    assert result['accuracy'] == 100
    assert result['average_response_time'] == 1.5


# TEST 3: Todas las respuestas son incorrectas
def test_calculate_statistics_all_incorrect():

    responses = [
        {'is_correct': False, 'response_time_ms': 1000},
        {'is_correct': False, 'response_time_ms': 3000}
    ]

    result = calculate_statistics(responses)

    assert result['total_questions'] == 2
    assert result['correct_answers'] == 0
    assert result['incorrect_answers'] == 2
    assert result['accuracy'] == 0
    assert result['average_response_time'] == 2


# TEST 4: Mezcla de respuestas correctas e incorrectas
def test_calculate_statistics_mixed():

    responses = [
        {'is_correct': True, 'response_time_ms': 1000},
        {'is_correct': False, 'response_time_ms': 2000},
        {'is_correct': True, 'response_time_ms': 3500}
    ]

    result = calculate_statistics(responses)

    assert result['total_questions'] == 3
    assert result['correct_answers'] == 2
    assert result['incorrect_answers'] == 1
    assert result['accuracy'] == 66.67
    assert result['average_response_time'] == 2.17


# TEST 5: Estadísticas de una partida
def test_calculate_game_statistics():

    game = {
        'game_id': 'game123',
        'category': '22',
        'difficulty': 'easy'
    }

    responses = [
        {'is_correct': True, 'response_time_ms': 1000},
        {'is_correct': False, 'response_time_ms': 3000}
    ]

    result = calculate_game_statistics(game, responses)

    assert result['game_id'] == 'game123'
    assert result['category'] == '22'
    assert result['difficulty'] == 'easy'
    assert result['total_questions'] == 2
    assert result['correct_answers'] == 1
    assert result['incorrect_answers'] == 1
    assert result['accuracy'] == 50
    assert result['average_response_time'] == 2


# TEST 6: Estadísticas generales de un usuario
def test_calculate_general_statistics():

    user_id = 'user123'

    responses = [
        {'is_correct': True, 'response_time_ms': 2000},
        {'is_correct': True, 'response_time_ms': 4000},
        {'is_correct': False, 'response_time_ms': 3000}
    ]

    result = calculate_general_statistics(user_id, responses)

    assert result['user_id'] == user_id
    assert result['total_questions'] == 3
    assert result['correct_answers'] == 2
    assert result['incorrect_answers'] == 1
    assert result['accuracy'] == 66.67
    assert result['average_response_time'] == 3


# Autenticación correcta con cognito
@patch('app.services.cognito.get_user')
def test_get_authenticated_user_success(mock_get_user):

    mock_get_user.return_value = {
        'UserAttributes': [
            {'Name': 'sub', 'Value': 'user123'}
        ]
    }

    user_id, error = get_authenticated_user('valid-token')

    assert user_id == 'user123'
    assert error is None


# Cognito no devuelve el identificador
@patch('app.services.cognito.get_user')
def test_get_authenticated_user_without_sub(mock_get_user):

    mock_get_user.return_value = {
        'UserAttributes': []
    }

    user_id, error = get_authenticated_user('valid-token')

    assert user_id is None
    assert error == 'No se ha podido identificar al usuario'


# Token inválido
@patch('app.services.cognito.get_user')
def test_get_authenticated_user_invalid_token(mock_get_user):

    mock_get_user.side_effect = ClientError(
        {'Error': {'Code': 'NotAuthorizedException'}},
        'GetUser'
    )

    user_id, error = get_authenticated_user('invalid-token')

    assert user_id is None
    assert error == 'El token no es válido o ha caducado'


# Usuario administrador
@patch('app.services.requests.get')
def test_get_user_role_admin(mock_get):

    mock_response = Mock()
    mock_response.json.return_value = {'role': 'admin'}
    mock_response.raise_for_status.return_value = None

    mock_get.return_value = mock_response

    role, error = get_user_role('user123')

    assert role == 'admin'
    assert error is None


# Usuario cliente
@patch('app.services.requests.get')
def test_get_user_role_client(mock_get):

    mock_response = Mock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status.return_value = None

    mock_get.return_value = mock_response

    role, error = get_user_role('user123')

    assert role == 'client'
    assert error is None


# Error al consultar profile
@patch('app.services.requests.get')
def test_get_user_role_connection_error(mock_get):

    mock_get.side_effect = requests.exceptions.ConnectionError()

    role, error = get_user_role('user123')

    assert role is None
    assert error == 'Error al consultar el perfil del usuario'


# Autenticación completa
@patch('app.services.get_user_role')
@patch('app.services.get_authenticated_user')
def test_authenticate_user_success(mock_get_user, mock_get_role):

    mock_get_user.return_value = ('user123', None)
    mock_get_role.return_value = ('client', None)

    user, error = authenticate_user('valid-token')

    assert user == {
        'user_id': 'user123',
        'role': 'client'
    }
    assert error is None

# COMUNICACIÓN CON GAME
# Consulta correcta a Game
@patch('app.services.requests.get')
def test_call_game_service_success(mock_get):

    mock_response = Mock()
    mock_response.json.return_value = {'game_id': 'game123'}
    mock_response.raise_for_status.return_value = None

    mock_get.return_value = mock_response

    data, error = call_game_service('/game/internal/games/game123')

    assert data == {'game_id': 'game123'}
    assert error is None    

# Partida inexistente
@patch('app.services.requests.get')
def test_call_game_service_not_found(mock_get):

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=Mock(status_code=404)
    )

    mock_get.return_value = mock_response

    data, error = call_game_service('/game/internal/games/unknown')

    assert data is None
    assert error == 'El recurso solicitado no existe'

# Error de conexión con Game
@patch('app.services.requests.get')
def test_call_game_service_connection_error(mock_get):

    mock_get.side_effect = requests.exceptions.ConnectionError()

    data, error = call_game_service('/game/internal/games/game123')

    assert data is None
    assert error == 'No se ha podido conectar con el microservicio game'

# ESTADÍSTICAS CON GAME
# Estadísticas de una partida
@patch('app.services.get_game_responses')
def test_get_game_statistics_success(mock_get_responses):

    mock_get_responses.return_value = ({
        'responses': [
            {'is_correct': True, 'response_time_ms': 1000},
            {'is_correct': False, 'response_time_ms': 3000}
        ]
    }, None)

    game = {
        'game_id': 'game123',
        'category': '22',
        'difficulty': 'easy'
    }

    result, error = get_game_statistics('game123', game)

    assert error is None
    assert result['game_id'] == 'game123'
    assert result['total_questions'] == 2
    assert result['accuracy'] == 50
    assert result['average_response_time'] == 2

# Error al recuperar las respuestas de una partida
@patch('app.services.get_game_responses')
def test_get_game_statistics_error(mock_get_responses):

    mock_get_responses.return_value = (
        None,
        'El recurso solicitado no existe'
    )

    result, error = get_game_statistics('game123', {})

    assert result is None
    assert error == 'El recurso solicitado no existe'

# Estadísticas generales de un usuario
@patch('app.services.get_user_responses')
def test_get_general_statistics_success(mock_get_responses):

    mock_get_responses.return_value = ({
        'responses': [
            {'is_correct': True, 'response_time_ms': 2000},
            {'is_correct': True, 'response_time_ms': 4000},
            {'is_correct': False, 'response_time_ms': 3000}
        ]
    }, None)

    result, error = get_general_statistics('user123')

    assert error is None
    assert result['user_id'] == 'user123'
    assert result['total_questions'] == 3
    assert result['accuracy'] == 66.67
    assert result['average_response_time'] == 3

# Error al recuperar las respuestas de un usuario
@patch('app.services.get_user_responses')
def test_get_general_statistics_error(mock_get_responses):

    mock_get_responses.return_value = (
        None,
        'Error al consultar el microservicio game'
    )

    result, error = get_general_statistics('user123')

    assert result is None
    assert error == 'Error al consultar el microservicio game'