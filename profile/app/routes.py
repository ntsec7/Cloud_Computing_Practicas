import hmac
import os

from botocore.exceptions import ClientError
from flask import Blueprint, jsonify, request

from app.services import create_profile, delete_profile, get_profile, update_profile

# Crea un Blueprint de Flask, sirve para organizar las rutas de una aplicación en módulos independientes
profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


# Comprobar que la petición viene de login. Lo ejecuta antes de entrar en cualquier ruta
@profile_bp.before_request
def verify_internal_token():
    """Comprueba que la petición procede de un servicio autorizado."""

    # La ruta de salud no necesita autenticación interna.
    if request.endpoint == "profile.health":
        return None

    received_token = request.headers.get("X-Internal-Token", "")
    expected_token = os.getenv("INTERNAL_SERVICE_TOKEN", "")

    if not expected_token or not hmac.compare_digest( #compara los valores
        received_token,
        expected_token
    ):
        return jsonify({
            "error": "Petición no autorizada"
        }), 403


@profile_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'message': 'Microservicio de profile funcionando'
    }), 200


#Crear la cuenta
@profile_bp.route('', methods=['POST'])
def create_profile_route():
    data= request.get_json(silent=True) #silent=True es que si no se puede interpretar el contenido como JSON, no lanza una excepción

    required_fields={
        'user_id',
        'username',
        'name',
        'avatar_id'
    }

    if not isinstance(data, dict):
        return jsonify({'error': 'JSON inválido'}), 400

    if not required_fields.issubset(data):
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    data = {    #Eliminamos campos no permitidos
        key: value
        for key, value in data.items()
        if key in required_fields
    }

    try:
        create_profile(
            data['user_id'],
            data['username'],
            data['name'],
            data['avatar_id']
        )

        return jsonify({
            'message':'Perfil creado correctamente'
        }), 201

    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return jsonify({'error': 'El perfil ya existe'}), 409
        raise


# GET profile
@profile_bp.route('/<user_id>', methods=['GET'])
def get_profile_route(user_id):

    profile = get_profile(user_id)

    if profile is None:
        return jsonify({'error': 'Perfil no encontrado'}), 404

    return jsonify(profile), 200


# PATCH profile
@profile_bp.route('/<user_id>', methods=['PATCH'])
def update_profile_route(user_id):

    data=request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'JSON inválido o vacío'}), 400

    allowed_fields = {'username', 'name', 'avatar_id'}

    if not set(data).issubset(allowed_fields):
        return jsonify({'error':'Hay campos no permitidos'}), 400

    try:
        updated= update_profile(user_id,data)

        if not updated:
            return jsonify({'error':'Perfil no encontrado o sin campos válidos'}), 404

        return jsonify({
            'message':'Perfil actualizado correctamente'
        }), 200

    except ClientError:
        return jsonify({'error': 'No se pudo actualizar el perfil'}), 500


# DELETE user_id
@profile_bp.route('/<user_id>', methods=['DELETE'])
def delete_profile_route(user_id):
    try:
        deleted = delete_profile(user_id)

        if not deleted:
            return jsonify({'error':'Perfil no encontrado'}), 404

        return jsonify({
            'message':'Perfil eliminado correctamente'
        }), 200

    except ClientError:
        return jsonify({'error': 'No se pudo eliminar el perfil'}), 500


# Actualizar perfil siendo admin
@profile_bp.route('/<user_id>/admin', methods=['PATCH'])
def admin_update_profile_route(user_id):
    """Actualiza un perfil incluyendo su rol."""

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'JSON inválido o vacío'}), 400

    allowed_fields = {
        'username',
        'name',
        'avatar_id',
        'role'
    }

    data = {    #Eliminamos campos no permitidos
        key: value
        for key, value in data.items()
        if key in allowed_fields
    }

    if 'role' in data and data['role'] not in {'client', 'admin'}:
        return jsonify({'error': 'Rol no válido'}), 400

    try:
        updated = update_profile(user_id, data, admin=True)

        if not updated:
            return jsonify({'error': 'Perfil no encontrado'}), 404

        return jsonify({
            'message': 'Perfil actualizado correctamente'
        }), 200

    except ClientError:
        return jsonify({
            'error': 'No se pudo actualizar el perfil'
        }), 500    