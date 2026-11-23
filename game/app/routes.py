
import hmac
import os

from flask import Blueprint, jsonify, request

from app.services import (
    create_game,
    get_authenticated_user,
    get_game_for_statistics,
    get_game_responses_for_statistics,
    get_user_responses_for_statistics,
    save_response,
)

game_bp = Blueprint( 'game', __name__, url_prefix='/game')

@game_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'message': 'Microservicio de statistic funcionando'
    }), 200

# Comprobar que la petición viene de un microservicio autorizado
@game_bp.before_request
def verify_internal_token():

    # Las rutas públicas no necesitan autenticación interna
    if not request.path.startswith('/game/internal/'):
        return None

    received_token = request.headers.get('X-Internal-Token', '')
    expected_token = os.getenv('INTERNAL_SERVICE_TOKEN', '')

    if not expected_token or not hmac.compare_digest(
        received_token,
        expected_token
    ):
        return jsonify({
            'error': 'Petición no autorizada'
        }), 403

def get_user_from_request():

    # Obtener la cabecera Authorization
    authorization = request.headers.get('Authorization')

    # Comprobar que existe y utiliza Bearer
    if not authorization or not authorization.startswith('Bearer '):
        return None, 'Falta el token de autenticación'

    # Extraer el Access Token
    access_token = authorization.split(' ', 1)[1]

    # Validar el token con Cognito
    user_id, error = get_authenticated_user(access_token)

    if error:
        return None, error

    return user_id, None


# Crear una partida
@game_bp.route('/', methods=['POST'])
def start_game():

    # Identificar al usuario
    user_id, error= get_user_from_request()

    if error:
        return jsonify({'error':error}), 401

    # Obtener los datos
    data= request.get_json(silent= True)

    if data is None:
        return jsonify({
            'error':'Se deben enviar los datos en formato JSON'
        }), 400


    category=data.get("category")
    difficulty=data.get("difficulty")
    
    # Comprobar que la categoría es un número entero si se ha enviado
    if category is not None and type(category) is not int:
        return jsonify({
            'error':'La categoría debe ser un número entero'
        }), 400

    
    # Comprobar la dificultad
    if difficulty is not None and difficulty not in ['easy', 'medium', 'hard']:
        return jsonify({
            'error': 'La dificultad no es válida'
        }), 400


    # Crear la partida
    game,error= create_game( user_id, category, difficulty)

    if error:
        return jsonify({'error': error}), 502

    return jsonify(game), 201


# Enviar respuesta
@game_bp.route('/<game_id>/answer', methods=['POST'])
def answer_question(game_id):

    # Identificar al usuario
    user_id, error = get_user_from_request()

    if error:
        return jsonify({'error': error}), 401

    # Obtener los datos
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            'error': 'Se deben enviar datos en formato JSON'
        }), 400

    question_id=data.get('question_id')
    answer=data.get('answer')

    
    # Comprobar que se han enviado los datos necesarios
    if question_id is None or answer is None:
        return jsonify({
            'error':'Faltan campos obligatorios'
        }), 400

    
    # Comprobar el tipo de identificador de pregunta
    if not isinstance(question_id, str):
        return jsonify({
            'error': 'El identificador de pregunta no es válido'
        }), 400

    # Comprobar que la respuesta es un índice entero
    if type(answer) is not int:
        return jsonify({
            'error': 'La respuesta debe ser un número entero'
        }), 400

    # Guardar la respuesta
    result, error= save_response(
        game_id,
        user_id,
        question_id,
        answer
    )

    if error:
        return jsonify({'error': error}), 400

    return jsonify(result), 200

# Recuperar los datos de una partida para estadísticas
@game_bp.route('/internal/games/<game_id>', methods=['GET'])
def get_internal_game(game_id):

    game, error = get_game_for_statistics(game_id)

    if error:
        if error == 'La partida no existe':
            return jsonify({'error': error}), 404

        return jsonify({'error': error}), 500

    return jsonify(game), 200


# Recuperar las respuestas de una partida para estadísticas
@game_bp.route('/internal/games/<game_id>/responses', methods=['GET'])
def get_internal_game_responses(game_id):

    # Recuperar la partida para obtener el user_id
    game, error = get_game_for_statistics(game_id)

    if error:
        if error == 'La partida no existe':
            return jsonify({'error': error}), 404

        return jsonify({'error': error}), 500

    # Recuperar las respuestas de esa partida
    responses, error = get_game_responses_for_statistics(
        game_id,
        game['user_id']
    )

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'game_id': game_id,
        'responses': responses
    }), 200

# Recuperar todas las respuestas de un usuario para estadísticas
@game_bp.route('/internal/users/<user_id>/responses', methods=['GET'])
def get_internal_user_responses(user_id):

    responses, error = get_user_responses_for_statistics(user_id)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({
        'user_id': user_id,
        'responses': responses
    }), 200