
from flask import Blueprint, jsonify, request

from app.services import (
    get_authenticated_user,
    create_game,
    save_response
)

game_bp = Blueprint( 'game', __name__, url_prefix='/game')

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

    if not data:
        return jsonify({
            'error':'Se deben enviar los datos en formato JSON'
        }), 400


    category=data.get("category")
    difficulty=data.get("difficulty")

    # Comprobar que están todos los datos necesarios
    if category is None or difficulty is None:
        return jsonify({
            'error':'Faltan campos obligatorios'
        }), 400

    
    # Comprobar que la categoría es un número entero
    if type(category) is not int:
        return jsonify({
            'error':'La categoría debe ser un número entero'
        }), 400

    
    # Comprobar la dificultad
    if difficulty not in ['easy', 'medium', 'hard']:
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