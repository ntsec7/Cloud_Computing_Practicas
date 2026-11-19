from flask import Blueprint, request, jsonify
from app.services import register_user, login_user, change_password, logout_user, delete_account

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

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

    except Exception as e:
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

    except Exception as e:
        print(f"ERROR EN LOGIN: {type(e).__name__}: {e}")

        return jsonify({
            "error": "No se ha podido iniciar sesión"
        }), 401


@auth_bp.route("/change-password", methods=["POST"])
def change_user_password():
    data= request.get_json(silent=True)

    if not data:
        return jsonify({"error":"Se requiere un cuerpo JSON"}),400

    access_token= data.get("access_token")
    previous_password= data.get("previous_password")
    proposed_password= data.get("proposed_password")

    if not all([access_token, previous_password, proposed_password]):
        return jsonify({"error":"Faltan campos obligatorios"}), 400

    try:
        change_password(access_token,previous_password,proposed_password)

        return jsonify({
            "message": "Contraseña actualizada correctamente"
        }), 200

    except Exception as e:
        print(f"ERROR EN CAMBIO DE CONTRASEÑA: {type(e).__name__}: {e}")

        return jsonify({
            "error": "No se ha podido cambiar la contraseña"
        }), 400    

@auth_bp.route("/logout", methods=["POST"])
def logout():
    data= request.get_json(silent=True)

    if not data:
        return jsonify({
            "error":"Se requiere un cuerpo JSON"
        }), 400

    access_token= data.get("access_token")

    if not access_token:
        return jsonify({"error":"Se requiere acceso al token"}), 400

    try:
        logout_user(access_token)

        return jsonify({
            "message":"Sesión cerrada correctamente"
        }), 200
    
    except Exception as e:
        print(f"ERROR EN LOGOUT: {type(e).__name__}: {e}")

        return jsonify({
            "error": "No se ha podido cerrar la sesión"
        }), 401

@auth_bp.route("/account", methods=["DELETE"])
def delete_account_route():
    data= request.get_json(silent=True) or {}   #El {} porque si fuese None daría error

    access_token= data.get("access_token")

    if not access_token:
        return jsonify({
            "error":"Falta el token de acceso"
        }), 400    

    try:
        delete_account(access_token)

        return jsonify({
            "message":"Cuenta eliminada correctamente"
        }), 200

    except Exception as error:
        print(
            "ERROR AL ELIMINAR CUENTA:",
            type(error).__name__,
            error
        )

        return jsonify({
            "error": "No se pudo eliminar la cuenta"
        }), 500