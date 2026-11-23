from flask import Blueprint, jsonify, request

from app.services import (
    authenticate_user,
    get_game_owner,
    get_game_statistics,
    get_general_statistics,
)

statistics_bp = Blueprint( 'statistics', __name__, url_prefix='/statistics')

@statistics_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'message': 'Microservicio de statistic funcionando'
    }), 200

# Devuelve el id y rol del usuario
def get_request_user():

    access_token = request.headers.get("Authorization", "")

    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    # Autenticar al usuario y recuperar su rol
    user, error = authenticate_user(access_token)

    if error:
        return None, (jsonify({
            'error': error
        }), 401)

    return user, None

# Estadísticas de una partida
@statistics_bp.route('/game/<game_id>', methods=['GET'])
def game_statistics(game_id):

    # Autenticar al usuario
    user, error_response = get_request_user()

    if error_response:
        return error_response

    # Recuperar los datos de la partida
    game, error = get_game_owner(game_id)

    if error:
        if error == 'El recurso solicitado no existe':
            return jsonify({'error': 'La partida no existe'}), 404

        return jsonify({'error': error}), 502

    # Comprobar los permisos
    if user['role'] != 'admin' and game['user_id'] != user['user_id']:
        return jsonify({
            'error': 'No tienes permiso para consultar esta partida'
        }), 403

    # Calcular las estadísticas
    statistics, error = get_game_statistics(game_id, game)

    if error:
        return jsonify({'error': error}), 502

    return jsonify(statistics), 200


# Estadísticas totales
@statistics_bp.route('/user/<user_id>', methods=['GET'])
def general_statistics(user_id):

    # Autenticar al usuario
    user, error_response = get_request_user()

    if error_response:
        return error_response

    # Comprobar los permisos
    if user['role'] != 'admin' and user['user_id'] != user_id:
        return jsonify({
            'error': 'No tienes permiso para consultar estas estadísticas'
        }), 403

    # Calcular las estadísticas generales
    statistics, error = get_general_statistics(user_id)

    if error:
        return jsonify({'error': error}), 502

    return jsonify(statistics), 200