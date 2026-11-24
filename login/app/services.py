import base64
import hashlib
import hmac
import os

import boto3
import requests
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

AWS_REGION= os.getenv("AWS_DEFAULT_REGION")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
PROFILE_SERVICE_URL = os.getenv("PROFILE_SERVICE_URL")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")
GAME_SERVICE_URL = os.getenv("GAME_SERVICE_URL")


# Comprobar que existen las variables necesarias
required_variables= {
    "AWS_DEFAULT_REGION": AWS_REGION,
    "COGNITO_USER_POOL_ID": USER_POOL_ID,
    "COGNITO_CLIENT_ID": CLIENT_ID,
    "COGNITO_CLIENT_SECRET": CLIENT_SECRET,
    "PROFILE_SERVICE_URL": PROFILE_SERVICE_URL,
    "GAME_SERVICE_URL": GAME_SERVICE_URL,
    "INTERNAL_SERVICE_TOKEN": INTERNAL_SERVICE_TOKEN
}

missing_variables= [
    name for name, value in required_variables.items()
    if not value
]

if missing_variables:
    raise RuntimeError(
        f"Faltan variables de retorno: {', '.join(missing_variables)}"
    )

PROFILE_HEADERS = {
    "X-Internal-Token": INTERNAL_SERVICE_TOKEN
}

GAME_HEADERS = {
    "X-Internal-Token": INTERNAL_SERVICE_TOKEN
}

# Crear el cliente de Cognito
cognito= boto3.client(
    "cognito-idp",
    region_name=AWS_REGION
)

# Necesario para algunas operaciones de autenticación
def calculate_secret_hash(username):
    """Calcula el SECRET_HASH requerido por Cognito."""

    message = username + CLIENT_ID

    digest = hmac.new(
        CLIENT_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).digest()

    return base64.b64encode(digest).decode()

def register_user(email, password, username, name, avatar_id):
    """Registra un usuario en Amazon Cognito y crea el perfil en profile."""

    # Crear el usuario sin enviar correos
    response= cognito.admin_create_user(
        UserPoolId= USER_POOL_ID,
        Username= email,
        UserAttributes=[
            {
                "Name":"email",
                "Value": email
            },
            {
                "Name":"email_verified",    #marca el email como verificado
                "Value":"true"
            }
        ],
        MessageAction="SUPPRESS"
    )

    # Obtener el nombre interno asignado por Cognito
    cognito_username= response["User"]["Username"]

    try:

        # Establecer contraseña
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username= cognito_username,
            Password= password,
            Permanent= True #para que no tenga que cambiarla en su primer acceso. Pero si podrá cambiarla si quiere
        )

        # Obtener el ID del usuario (sub) recien creado
        user= cognito.admin_get_user(
            UserPoolId= USER_POOL_ID,
            Username= cognito_username
        )

        user_id= next( #me quedo con el valor de sub
            attribute["Value"]
            for attribute in user["UserAttributes"]
            if attribute["Name"] == "sub"
        )

        # Crear el perfil en el microservicio profile
        profile_response= requests.post(
            f"{PROFILE_SERVICE_URL}/profile",
            headers=PROFILE_HEADERS,
            json={
                "user_id": user_id,
                "username": username,
                "name": name,
                "avatar_id": avatar_id
            },
            timeout= 5 #espera 5 seg a que responda el servicio
        )

        # Comprobar que profile ha creado correctamente el perfil
        profile_response.raise_for_status()

        return user_id

    except Exception:

        #Si hay algún fallo, eliminar el usuario de Cognito
        try:
            cognito.admin_delete_user(
                UserPoolId= USER_POOL_ID,
                Username= cognito_username
            )
            print("Registro incompleto: usuario eliminado de Cognito")

        except Exception as rollback_error: # noqa: BLE001
            print(
                "ERROR al deshacer el registro:",
                type(rollback_error).__name__,
                rollback_error
            )

        raise    


def login_user(email, password):
    """Inicia sesión de un usuario mediante Amazon Cognito."""

    response= cognito.admin_initiate_auth(
        UserPoolId= USER_POOL_ID,
        ClientId= CLIENT_ID,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": email,
            "PASSWORD": password,
            "SECRET_HASH": calculate_secret_hash(email)
        }
    )

    authentication= response["AuthenticationResult"]

    return{
        "access_token": authentication["AccessToken"],
        "id_token": authentication["IdToken"],
        "refresh_token" : authentication.get("RefreshToken"),
        "expires_in": authentication["ExpiresIn"],
        "token_type": authentication["TokenType"]
    }

def get_my_data(access_token):
    """Obtiene los datos del usuario que ha iniciado sesión."""

    #Obtener los datos del usuario autenticado en Cognito
    user = cognito.get_user(
        AccessToken=access_token
    )

    user_id = next(
        attribute["Value"]
        for attribute in user["UserAttributes"]
        if attribute["Name"] == "sub"
    )

    email = next(
        attribute["Value"]
        for attribute in user["UserAttributes"]
        if attribute["Name"] == "email"
    )

    profile_response = requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{user_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )

    profile_response.raise_for_status()

    profile = profile_response.json()

    #Combinar los datos de profile y Cognito
    result = {
        "user_id": user_id,
        "username": profile["username"],
        "name": profile["name"],
        "avatar_id": profile["avatar_id"],
        "email": email
    }

    #Incluir el rol si es admin
    if profile.get("role") == "admin":
        result["role"] = "admin"

    return result

def update_my_data(access_token, data):
    """Actualiza los datos del usuario autenticado."""

    # Obtener datos del usuario autenticado.
    user = cognito.get_user(
        AccessToken=access_token
    )

    user_id = next(
        attribute["Value"]
        for attribute in user["UserAttributes"]
        if attribute["Name"] == "sub"
    )

    profile_data = {
        key: value
        for key, value in data.items()
        if key in {"username", "name", "avatar_id"}
    }

    # Actualizar el perfil
    if profile_data:
        profile_response = requests.patch(
            f"{PROFILE_SERVICE_URL}/profile/{user_id}",
            headers=PROFILE_HEADERS,
            json=profile_data,
            timeout=5
        )

        profile_response.raise_for_status()

    # Actualizar el email en Cognito si se ha proporcionado.
    if "email" in data:
       
        cognito_username = user["Username"]

        cognito.admin_update_user_attributes(   #Cambia el email y lo marca como verificado
            UserPoolId=USER_POOL_ID,
            Username=cognito_username,
            UserAttributes=[
                {
                    "Name": "email",
                    "Value": data["email"]
                },
                {
                    "Name": "email_verified",
                    "Value": "true"
                }
            ]
        )

    return True    


def change_password(access_token, previous_password, proposed_password):
    """Cambia la contraseña de un usuario autenticado.""" 

    cognito.change_password(
        AccessToken=access_token,
        PreviousPassword=previous_password,
        ProposedPassword=proposed_password
    )   

def logout_user(access_token):
    """Cierra la sesión del usuario en Amazon Cognito."""    

    cognito.global_sign_out( #Cognito invalida los tokens asociados a la sesión
        AccessToken= access_token
    )

def delete_game_data(user_id):
    """Solicita al microservicio game que elimine los datos del usuario."""

    response = requests.delete(
        f"{GAME_SERVICE_URL}/game/internal/users/{user_id}",
        headers=GAME_HEADERS,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not isinstance(result, dict) or "deleted_games" not in result or "deleted_responses" not in result:
        raise RuntimeError(
            "El microservicio game devolvió una respuesta no válida"
        )

    return result

def delete_account(access_token):        
    """Elimina la cuenta de Cognito y su perfil."""

    #Obtener la identidad del usuario a partir del token
    user= cognito.get_user(
        AccessToken= access_token
    )

    cognito_username= user["Username"]

    user_id= next(
        attribute["Value"]
        for attribute in user["UserAttributes"]
        if attribute["Name"] =="sub"
    )

    # Eliminar las partidas y respuestas del usuario en game
    game_result = delete_game_data(user_id)

    #Guardamos los datos del perfil por si la eliminación en Cognito falla
    profile_response= requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{user_id}",
        headers=PROFILE_HEADERS,
        timeout= 5
    )

    profile = None

    if profile_response.status_code == 200:
        profile = profile_response.json() #lo convertimos en un diccionario de python
    elif profile_response.status_code != 404:
        profile_response.raise_for_status()

    #Eliminar el perfil en profile
    if profile is not None:
        delete_response= requests.delete(
            f"{PROFILE_SERVICE_URL}/profile/{user_id}",
            headers=PROFILE_HEADERS,
            timeout=5
        )
        delete_response.raise_for_status()

    #Eliminar el usuario de Cognito
    try:
        cognito.admin_delete_user(
            UserPoolId= USER_POOL_ID,
            Username= cognito_username
        )       
    except Exception:
        #Si falla Cognito, se intenta restaurar el perfil
        if profile is not None:
            try:
                requests.post(
                    f"{PROFILE_SERVICE_URL}/profile",
                    headers=PROFILE_HEADERS,
                    json=profile,
                    timeout=5
                ).raise_for_status()    

            except Exception as rollback_error: # noqa: BLE001
                print(
                    "ERROR al restaurar el perfil:",
                    type(rollback_error).__name__
                )

        raise


#OPERACIONES DE ADMIN
def get_admin_user_data(access_token, target_user_id):
    """Permite a un administrador consultar los datos de cualquier usuario."""

    # Identificar al admin
    admin = cognito.get_user(
        AccessToken=access_token
    )

    admin_id = next(
        attribute["Value"]
        for attribute in admin["UserAttributes"]
        if attribute["Name"] == "sub"
    )

    # Consultar el perfil del admin para comprobar que su rol
    admin_response = requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{admin_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )

    admin_response.raise_for_status()
    admin_profile = admin_response.json()

    if admin_profile.get("role") != "admin":
        raise PermissionError("El usuario no es administrador")

    # Consultar el perfil del usuario 
    profile_response = requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{target_user_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )

    if profile_response.status_code == 404:
        return None

    profile_response.raise_for_status()
    profile = profile_response.json()

    # Buscar en Cognito la cuenta cuyo sub coincide con el user_id.
    pagination_token = None
    cognito_user = None

    while True:
        params = {
            "UserPoolId": USER_POOL_ID,
            "Limit": 60 #vamos recibiendo los datos de 60 en 60
        }

        if pagination_token:
            params["PaginationToken"] = pagination_token

        response = cognito.list_users(**params) # El ** le pasa los params como diccionario

        for user in response["Users"]:
            user_sub = next(
                (
                    attribute["Value"]
                    for attribute in user["Attributes"]
                    if attribute["Name"] == "sub"
                ),
                None
            )

            if user_sub == target_user_id:
                cognito_user = user
                break

        if cognito_user or "PaginationToken" not in response:   #Si hemos encontrado al usuario o no quedan más usuarios
            break

        pagination_token = response["PaginationToken"]

    if cognito_user is None:
        return None

    # Obtener el email de Cognito.
    email = next(
        (
            attribute["Value"]
            for attribute in cognito_user["Attributes"]
            if attribute["Name"] == "email"
        ),
        None
    )

    # Devolver los datos del usuario.
    return {
        "user_id": target_user_id,
        "username": profile["username"],
        "name": profile["name"],
        "avatar_id": profile["avatar_id"],
        "email": email,
        "role": profile.get("role", "client")
    }


def update_admin_user_data(access_token, target_user_id, data):
    """Permite a un administrador modificar cualquier cuenta."""

    # Comprobar quién realiza la petición.
    admin = cognito.get_user(
        AccessToken=access_token
    )

    admin_id = next(
        attribute["Value"]
        for attribute in admin["UserAttributes"]
        if attribute["Name"] == "sub"
    )

    # Comprobar que realmente es admin
    admin_response = requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{admin_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )

    admin_response.raise_for_status()
    admin_profile = admin_response.json()

    if admin_profile.get("role") != "admin":
        raise PermissionError("El usuario no es administrador")

    # Consultar el perfil que queremos modificar.
    profile_response = requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{target_user_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )

    if profile_response.status_code == 404:
        return False

    profile_response.raise_for_status()

    # Comprobar los campos permitidos.
    allowed_fields = {
        "username",
        "name",
        "avatar_id",
        "email",
        "role"
    }

    if not set(data).issubset(allowed_fields):
        raise ValueError("Hay campos no permitidos")

    if "role" in data and data["role"] not in {"client", "admin"}:
        raise ValueError("El rol indicado no es válido")

    # Actualizar los datos del perfil
    profile_data = {
        key: value
        for key, value in data.items()
        if key in {"username", "name", "avatar_id"}
    }

    if "role" in data:
        profile_data["role"] = data["role"]

    if profile_data:
        profile_response = requests.patch(
            f"{PROFILE_SERVICE_URL}/profile/{target_user_id}/admin",
            headers=PROFILE_HEADERS,
            json=profile_data,
            timeout=5
        )

        if profile_response.status_code == 404:
            return False

        profile_response.raise_for_status()

    # Actualizar el email en Cognito si se ha cambiado
    if "email" in data:

        # Buscar la cuenta de Cognito correspondiente.
        cognito_username = None
        pagination_token = None

        while True:
            params = {
                "UserPoolId": USER_POOL_ID,
                "Limit": 60
            }

            if pagination_token:
                params["PaginationToken"] = pagination_token

            response = cognito.list_users(**params)

            for user in response["Users"]:
                user_sub = next(
                    (
                        attribute["Value"]
                        for attribute in user["Attributes"]
                        if attribute["Name"] == "sub"
                    ),
                    None
                )

                if user_sub == target_user_id:
                    cognito_username = user["Username"]
                    break

            if cognito_username or "PaginationToken" not in response:
                break

            pagination_token = response["PaginationToken"]

        if cognito_username is None:
            raise ValueError("No se encontró la cuenta en Cognito")

        cognito.admin_update_user_attributes(
            UserPoolId=USER_POOL_ID,
            Username=cognito_username,
            UserAttributes=[
                {"Name": "email", "Value": data["email"]},
                {"Name": "email_verified", "Value": "true"}
            ]
        )

    return True


def change_admin_user_password(access_token, target_user_id, new_password):
    """Permite a un administrador cambiar la contraseña de otro usuario."""

    # Obtener el administrador autenticado desde Cognito
    admin = cognito.get_user(
        AccessToken=access_token
    )

    admin_id = next(
        attribute["Value"]
        for attribute in admin["UserAttributes"]
        if attribute["Name"] == "sub"
    )

    # Evitar que utilice esta operación para cambiar su propia contraseña
    if admin_id == target_user_id:
        raise ValueError(
            "Utiliza la operación de cambio de contraseña personal"
        )

    # Comprobar que el usuario autenticado es administrador
    admin_profile_response = requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{admin_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )
    admin_profile_response.raise_for_status()

    admin_profile = admin_profile_response.json()

    if admin_profile.get("role") != "admin":
        raise PermissionError(
            "No tienes permisos de administrador"
        )

    # Buscar en Cognito al usuario cuya contraseña queremos cambiar
    response = cognito.list_users(
        UserPoolId=USER_POOL_ID,
        Filter=f'sub = "{target_user_id}"',
        Limit=1
    )

    users = response.get("Users", [])

    if not users:
        raise ValueError("Usuario no encontrado en Cognito")

    cognito_username = users[0]["Username"]

    # Establecer la nueva contraseña
    cognito.admin_set_user_password(
        UserPoolId=USER_POOL_ID,
        Username=cognito_username,
        Password=new_password,
        Permanent=True
    )

    return True


def delete_admin_user(access_token, target_user_id):
    """Permite a un administrador eliminar cualquier cuenta."""

    # Identificar al administrador.
    admin = cognito.get_user(
        AccessToken=access_token
    )

    admin_id = next(
        attribute["Value"]
        for attribute in admin["UserAttributes"]
        if attribute["Name"] == "sub"
    )

    if admin_id == target_user_id:
        raise ValueError(
            "No puedes eliminar tu propia cuenta desde esta ruta"
        )

    # Comprobar que tiene permisos de administrador.
    admin_response = requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{admin_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )

    admin_response.raise_for_status()
    admin_profile = admin_response.json()

    if admin_profile.get("role") != "admin":
        raise PermissionError("El usuario no es administrador")

    # Buscar el perfil que queremos eliminar.
    profile_response = requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{target_user_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )

    if profile_response.status_code == 404:
        return False

    profile_response.raise_for_status()

    profile = profile_response.json()

    # Buscar la cuenta correspondiente en Cognito.
    cognito_username = None
    pagination_token = None

    while True:
        params = {
            "UserPoolId": USER_POOL_ID,
            "Limit": 60
        }

        if pagination_token:
            params["PaginationToken"] = pagination_token

        response = cognito.list_users(**params)

        for user in response["Users"]:
            user_sub = next(
                (
                    attribute["Value"]
                    for attribute in user["Attributes"]
                    if attribute["Name"] == "sub"
                ),
                None
            )

            if user_sub == target_user_id:
                cognito_username = user["Username"]
                break

        if cognito_username or "PaginationToken" not in response:
            break

        pagination_token = response["PaginationToken"]

    if cognito_username is None:
        return False

    # Eliminar las partidas y respuestas del usuario en game
    game_result = delete_game_data(target_user_id)

    # Eliminar el perfil de DynamoDB.
    delete_response = requests.delete(
        f"{PROFILE_SERVICE_URL}/profile/{target_user_id}",
        headers=PROFILE_HEADERS,
        timeout=5
    )

    delete_response.raise_for_status()

    try:
        # Eliminar la cuenta de Cognito.
        cognito.admin_delete_user(
            UserPoolId=USER_POOL_ID,
            Username=cognito_username
        )

    except Exception:
        # Si falla Cognito, intentar restaurar el perfil.
        try:
            requests.post(
                f"{PROFILE_SERVICE_URL}/profile",
                headers=PROFILE_HEADERS,
                json=profile,
                timeout=5
            ).raise_for_status()

        except Exception as rollback_error: # noqa: BLE001
            print(
                "ERROR AL RESTAURAR EL PERFIL:",
                type(rollback_error).__name__,
                rollback_error
            )

        raise

    return True