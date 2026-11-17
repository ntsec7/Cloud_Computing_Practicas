from flask import Blueprint, jsonify, request
from botocore.exceptions import ClientError


from app.services import (
    create_profile,
    get_profile,
    update_profile,
    delete_profile
)


# Crea un Blueprint de Flask, sirve para organizar las rutas de una aplicación en módulos independientes
profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


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