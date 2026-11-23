import os

import boto3
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración del microservicio game
GAME_SERVICE_URL = os.getenv('GAME_SERVICE_URL')
INTERNAL_SERVICE_TOKEN = os.getenv('INTERNAL_SERVICE_TOKEN')

# Configuración del microservicio profile
PROFILE_SERVICE_URL = os.getenv('PROFILE_SERVICE_URL')

PROFILE_HEADERS = {
    'X-Internal-Token': INTERNAL_SERVICE_TOKEN
}

# Cliente de Cognito
cognito = boto3.client(
    'cognito-idp',
    region_name=os.getenv('COGNITO_REGION')
)

# Valida la autenticación del usuario y devuelve su user_id
def get_authenticated_user(access_token):

    try:
        # Validar el token y recuperar los datos del usuario
        response = cognito.get_user(
            AccessToken=access_token
        )

        # Obtener el identificador del usuario
        user_id = next(
            attribute['Value']
            for attribute in response['UserAttributes']
            if attribute['Name'] == 'sub'
        )

        return user_id, None

    except StopIteration:
        return None, 'No se ha podido identificar al usuario'

    except ClientError:
        return None, 'El token no es válido o ha caducado'

# Comprobamos si el usuario es admin
def get_user_role(user_id):

    try:
        response = requests.get(
            f'{PROFILE_SERVICE_URL}/profile/{user_id}',
            headers=PROFILE_HEADERS,
            timeout=5
        )

        response.raise_for_status()

        profile = response.json()

        # Si el perfil devuelve role, comprobar si es administrador
        if profile.get('role') == 'admin':
            return 'admin', None

        return 'client', None #Si no tiene role es client

    except requests.exceptions.RequestException:
        return None, 'Error al consultar el perfil del usuario'

    except ValueError:
        return None, 'La respuesta de profile no contiene un JSON válido'


# Devuelve el id y rol del usuario
def authenticate_user(access_token):

    # Identificar al usuario mediante Cognito
    user_id, error = get_authenticated_user(access_token)

    if error:
        return None, error

    # Consultar su rol en profile
    role, error = get_user_role(user_id)

    if error:
        return None, error

    return {
        'user_id': user_id,
        'role': role
    }, None


def calculate_statistics(responses):

    # Número total de preguntas respondidas
    total_questions = len(responses)

    # Si no hay respuestas, devolver estadísticas a cero
    if total_questions == 0:
        return {
            'total_questions': 0,
            'correct_answers': 0,
            'incorrect_answers': 0,
            'accuracy': 0,
            'average_response_time': 0
        }

    # Contar respuestas correctas
    correct_answers = sum(
        1 for response in responses
        if response['is_correct']
    )

    # Calcular respuestas incorrectas
    incorrect_answers = total_questions - correct_answers

    # Calcular porcentaje de aciertos
    accuracy = round(
        (correct_answers / total_questions) * 100,
        2
    )

    # Calcular tiempo medio de respuesta (dividido entre 1000 para que este en segundos)
    average_response_time = round(
        sum(response['response_time_ms'] for response in responses)
        / total_questions / 1000,
        2
    )

    return {
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'accuracy': accuracy,
        'average_response_time': average_response_time
    }


# Estadísticas de una partida
def calculate_game_statistics(game, responses):

    statistics = calculate_statistics(responses)

    return {
        'game_id': game['game_id'],
        'category': game.get('category'),
        'difficulty': game.get('difficulty'),
        **statistics
    }

# Estadísticas medias de un jugador
def calculate_general_statistics(user_id, responses):

    statistics = calculate_statistics(responses)

    return {
        'user_id': user_id,
        **statistics
    }

# Función general que reutiliza la autenticación interna y gestión de errores
def call_game_service(endpoint):

    # Preparar cabeceras de la petición
    headers = {
        'X-Internal-Token': INTERNAL_SERVICE_TOKEN
    }

    try:
        response = requests.get(
            f'{GAME_SERVICE_URL}{endpoint}',
            headers=headers,
            timeout=5
        )

        # Comprobar si la petición ha fallado
        response.raise_for_status()

        return response.json(), None

    except requests.exceptions.HTTPError as error:
        if error.response.status_code == 404:
            return None, 'El recurso solicitado no existe'

        return None, 'Error al consultar el microservicio game'

    except requests.exceptions.RequestException:
        return None, 'No se ha podido conectar con el microservicio game'

    except ValueError:
        return None, 'La respuesta de game no contiene un JSON válido'


# Datos de una partida
def get_game_data(game_id):

    return call_game_service(
        f'/game/internal/games/{game_id}'
    )

# Respuestas de una partida
def get_game_responses(game_id):

    return call_game_service(
        f'/game/internal/games/{game_id}/responses'
    )

# Todas las respuestas de un usuario
def get_user_responses(user_id):

    return call_game_service(
        f'/game/internal/users/{user_id}/responses'
    )

# Devuelve el usuario de una partida
def get_game_owner(game_id):

    return call_game_service(
        f'/game/internal/games/{game_id}'
    )

# Estadísticas de una partida
def get_game_statistics(game_id, game):

    # Recuperar las respuestas de la partida
    data, error = get_game_responses(game_id)

    if error:
        return None, error

    # Calcular las estadísticas
    statistics = calculate_game_statistics(
        game,
        data['responses']
    )

    return statistics, None

# Estadísticas de un usuario
def get_general_statistics(user_id):

    # Recuperar todas las respuestas del usuario
    data, error = get_user_responses(user_id)

    if error:
        return None, error

    # Calcular las estadísticas generales
    statistics = calculate_general_statistics(
        user_id,
        data['responses']
    )

    return statistics, None