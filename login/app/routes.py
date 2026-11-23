from flask import Blueprint, jsonify, request

from app.services import (
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

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

health_bp = Blueprint("health", __name__)

@health_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'message': 'Microservicio de login funcionando'
    }), 200

@auth_bp.route("/register", methods=["POST"])
def register():
    """Registra un nuevo usuario."""

    data= request.get_json(silent=True) #cogemos los datos

    if not data:
        return jsonify({
            "error":"Se requiere un cuerpo JSON"
        }), 400

    email= data.get("email")
    password= data.get("password")
    username= data.get("username")
    name = data.get("name")
    avatar_id = data.get("avatar_id")

    if not all([email, password, username, name, avatar_id]):
        return jsonify({
            "error": "Faltan campos obligatorios"
        }),400

    #Registrar
    try:
        user_id= register_user(email, password, username, name, avatar_id)

        return jsonify({
            "message": "Usuario registrado correctamente",
            "user_id": user_id
        }),201

    except Exception as e: # noqa: BLE001
        print(f"ERROR EN REGISTRO: {type(e).__name__}: {e}")

        return jsonify({
            "error": "No se ha podido completar el registro"
        }), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    data= request.get_json(silent=True)

    if not data:
        return jsonify({"error":"Se requiere un cuerpo JSON"}),400

    email = data.get("email")
    password= data.get("password")

    if not email or not password:
        return jsonify({"error":"Email y contraseña son obligatorios"}), 400

    try:
        tokens = login_user(email,password)

        return jsonify({
            "message": "Inicio de sesión correcto",
            "tokens": tokens
        }), 200

    except Exception as e: # noqa: BLE001
        print(f"ERROR EN LOGIN: {type(e).__name__}: {e}")

        return jsonify({
            "error": "No se ha podido iniciar sesión"
        }), 401


@auth_bp.route("/me", methods=["GET"])
def get_my_data_route():
    """Consulta los datos del usuario autenticado."""

    access_token = request.headers.get("Authorization", "")

    # Comprobar que se ha enviado el token Bearer.
    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    try:
        data = get_my_data(access_token)

        return jsonify(data), 200

    except Exception as error: # noqa: BLE001
        print(
            "ERROR AL CONSULTAR LOS DATOS:",
            type(error).__name__,
            error
        )

        return jsonify({
            "error": "No se pudieron consultar los datos"
        }), 401


@auth_bp.route("/me", methods=["PATCH"])
def update_my_data_route():
    """Actualiza los datos del usuario autenticado."""

    access_token = request.headers.get("Authorization", "")

    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "error": "JSON inválido o vacío"
        }), 400
    

    allowed_fields = {
        "username",
        "name",
        "avatar_id",
        "email"
    }

    data = {    #Eliminamos campos no permitidos
        key: value
        for key, value in data.items()
        if key in allowed_fields
    }

    try:
        update_my_data(access_token, data)

        return jsonify({
            "message": "Datos actualizados correctamente"
        }), 200

    except Exception as error: # noqa: BLE001
        print(
            "ERROR AL ACTUALIZAR LOS DATOS:",
            type(error).__name__,
            error
        )

        return jsonify({
            "error": "No se pudieron actualizar los datos"
        }), 400

@auth_bp.route("/change-password", methods=["POST"])
def change_user_password():

    access_token = request.headers.get("Authorization", "")

    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    if not access_token:
        return jsonify({"error":"Se requiere acceso al token"}), 400

    data= request.get_json(silent=True)

    if not data:
        return jsonify({"error":"Se requiere un cuerpo JSON"}),400

    previous_password= data.get("previous_password")
    proposed_password= data.get("proposed_password")

    if not all([access_token, previous_password, proposed_password]):
        return jsonify({"error":"Faltan campos obligatorios"}), 400

    try:
        change_password(access_token,previous_password,proposed_password)

        return jsonify({
            "message": "Contraseña actualizada correctamente"
        }), 200

    except Exception as e: # noqa: BLE001
        print(f"ERROR EN CAMBIO DE CONTRASEÑA: {type(e).__name__}: {e}")

        return jsonify({
            "error": "No se ha podido cambiar la contraseña"
        }), 400    

@auth_bp.route("/logout", methods=["POST"])
def logout():
    
    access_token = request.headers.get("Authorization", "")

    # Comprobar que se ha enviado el token Bearer.
    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    if not access_token:
        return jsonify({"error":"Se requiere acceso al token"}), 400

    try:
        logout_user(access_token)

        return jsonify({
            "message":"Sesión cerrada correctamente"
        }), 200
    
    except Exception as e: # noqa: BLE001
        print(f"ERROR EN LOGOUT: {type(e).__name__}: {e}")

        return jsonify({
            "error": "No se ha podido cerrar la sesión"
        }), 401

@auth_bp.route("/account", methods=["DELETE"])
def delete_account_route():

    access_token = request.headers.get("Authorization", "")

    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    if not access_token:
        return jsonify({"error":"Se requiere acceso al token"}), 400

    try:
        delete_account(access_token)

        return jsonify({
            "message":"Cuenta eliminada correctamente"
        }), 200

    except Exception as error: # noqa: BLE001
        print(
            "ERROR AL ELIMINAR CUENTA:",
            type(error).__name__,
            error
        )

        return jsonify({
            "error": "No se pudo eliminar la cuenta"
        }), 500


# RUTAS DE ADMIN
@admin_bp.route("/users/<user_id>", methods=["GET"])
def get_admin_user_data_route(user_id):
    """Permite a un administrador consultar una cuenta."""

    access_token = request.headers.get("Authorization", "")

    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    try:
        data = get_admin_user_data(
            access_token,
            user_id
        )

        if data is None:
            return jsonify({
                "error": "Usuario no encontrado"
            }), 404

        return jsonify(data), 200

    except PermissionError: 
        return jsonify({
            "error": "No tienes permisos de administrador"
        }), 403

    except Exception as error: # noqa: BLE001
        print(
            "ERROR AL CONSULTAR USUARIO:",
            type(error).__name__,
            error
        )

        return jsonify({
            "error": "No se pudo consultar el usuario"
        }), 500
    

@admin_bp.route("/users/<user_id>", methods=["PATCH"])
def update_admin_user_data_route(user_id):
    """Permite a un administrador modificar una cuenta."""

    access_token = request.headers.get("Authorization", "")

    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "error": "JSON inválido o vacío"
        }), 400

    try:
        updated = update_admin_user_data(
            access_token,
            user_id,
            data
        )

        if not updated:
            return jsonify({
                "error": "Usuario no encontrado"
            }), 404

        return jsonify({
            "message": "Usuario actualizado correctamente"
        }), 200

    except PermissionError:
        return jsonify({
            "error": "No tienes permisos de administrador"
        }), 403

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except Exception as error: # noqa: BLE001
        print(
            "ERROR AL ACTUALIZAR USUARIO:",
            type(error).__name__,
            error
        )

        return jsonify({
            "error": "No se pudo actualizar el usuario"
        }), 500    


@admin_bp.route('/users/<user_id>/password', methods=['PATCH'])
def change_admin_user_password_route(user_id):

    # Obtener el token del administrador
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return jsonify({
            "error": "Token de autenticación no proporcionado"
        }), 401

    access_token = authorization.split(" ", 1)[1]

    # Obtener los datos enviados
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON inválido"
        }), 400

    new_password = data.get("new_password")

    if not isinstance(new_password, str) or not new_password:
        return jsonify({
            "error": "Debes proporcionar una nueva contraseña"
        }), 400

    try:
        change_admin_user_password(
            access_token,
            user_id,
            new_password
        )

        return jsonify({
            "message": "Contraseña modificada correctamente"
        }), 200

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception: # noqa: BLE001
        return jsonify({
            "error": "No se pudo modificar la contraseña"
        }), 500


@admin_bp.route("/users/<user_id>", methods=["DELETE"])
def delete_admin_user_route(user_id):
    """Permite a un administrador eliminar cualquier cuenta."""

    access_token = request.headers.get("Authorization", "")

    if not access_token.startswith("Bearer "):
        return jsonify({
            "error": "Falta el token de acceso"
        }), 401

    access_token = access_token.replace("Bearer ", "", 1)

    try:
        deleted = delete_admin_user(
            access_token,
            user_id
        )

        if not deleted:
            return jsonify({
                "error": "Usuario no encontrado"
            }), 404

        return jsonify({
            "message": "Usuario eliminado correctamente"
        }), 200

    except PermissionError:
        return jsonify({
            "error": "No tienes permisos de administrador"
        }), 403

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except Exception as error: # noqa: BLE001
        print(
            "ERROR AL ELIMINAR USUARIO:",
            type(error).__name__,
            error
        )

        return jsonify({
            "error": "No se pudo eliminar el usuario"
        }), 500