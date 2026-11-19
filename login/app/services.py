import os
import hmac
import hashlib
import base64
import boto3
from dotenv import load_dotenv
import requests

# Cargar las variables del archivo .env
load_dotenv()

AWS_REGION= os.getenv("AWS_DEFAULT_REGION")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
PROFILE_SERVICE_URL = os.getenv("PROFILE_SERVICE_URL")


# Comprobar que existen las variables necesarias
required_variables= {
    "AWS_DEFAULT_REGION": AWS_REGION,
    "COGNITO_USER_POOL_ID": USER_POOL_ID,
    "COGNITO_CLIENT_ID": CLIENT_ID,
    "COGNITO_CLIENT_SECRET": CLIENT_SECRET,
    "PROFILE_SERVICE_URL": PROFILE_SERVICE_URL
}

missing_variables= [
    name for name, value in required_variables.items()
    if not value
]

if missing_variables:
    raise RuntimeError(
        f"Faltan variables de retorno: {', '.join(missing_variables)}"
    )


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

        except Exception as rollback_error:
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

    #Guardamos los datos del perfil por si la eliminación en Cognito falla
    profile_response= requests.get(
        f"{PROFILE_SERVICE_URL}/profile/{user_id}",
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
                    json=profile,
                    timeout=5
                ).raise_for_status()    

            except Exception as rollback_error:
                print(
                    "ERROR al restaurar el perfil:",
                    type(rollback_error).__name__
                )

        raise
