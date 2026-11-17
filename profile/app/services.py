# Gestiona las operaciones sobre DynamoDB
import os
import boto3
from botocore.exceptions import ClientError

def get_profile_table():
    """Obtiene la tabla de perfiles de DynamoDB."""

    dynamodb= boto3.resource(
        'dynamodb',
        endpoint_url= os.getenv(
            'DYNAMODB_ENDPOINT',
            'http://localhost:8002'
        ),
        region_name= os.getenv(
            'AWS_DEFAULT_REGION',
            'eu-south-2' #zaragoza
        ),
        aws_access_key_id=os.getenv(
            'AWS_ACCESS_KEY_ID',
            'local'
        ),
        aws_secret_access_key=os.getenv(
            'AWS_SECRET_ACCESS_KEY',
            'local'
        )
    )

    table_name = os.getenv(
        'PROFILE_TABLE',
        'Profiles'
    )

    return dynamodb.Table(table_name)


# Crear perfil
def create_profile(user_id, username, name, avatar_id):
    """Crea un perfil de usuario."""

    table= get_profile_table()

    table.put_item(
        Item={
            'user_id': user_id,
            'username': username,
            'name': name,
            'avatar_id': avatar_id
        },
        ConditionExpression= 'attribute_not_exists(user_id)'
    )


# Consultar perfil
def get_profile(user_id):
    """Consultar un perfil por su identificador."""

    table= get_profile_table()

    response= table.get_item(
        Key={'user_id':user_id}
    )

    return response.get('Item')


# Actualizar perfil
def update_profile(user_id, data):
    """Actualiza los datos permitidos de un perfil"""

    table= get_profile_table()

    allowed_fields= {
        'username',
        'name',
        'avatar_id'
    }

    update_data= {  #se queda solo con los datos que cumplen allowed_fields
        key:value
        for key, value in data.items()
        if key in allowed_fields
    }

    if not update_data: #si no hay datos para actualizar se sale
        return False

    update_expression = 'SET ' + ', '.join(
        f'#{key} = :{key}'
        for key in update_data
    )

    expression_names = {    #relaciona los marcadores con los nombres reales de los atributos
        f'#{key}': key
        for key in update_data
    }

    expression_values = {
        f':{key}': value
        for key, value in update_data.items()
    }

    try:
        table.update_item(
            Key={'user_id':user_id},
            UpdateExpression=update_expression, #los atributos que queremos actualizar
            ExpressionAttributeNames=expression_names, #relaciona marcadores con nombres reales
            ExpressionAttributeValues=expression_values, #relaciona marcadores con los nuevos valores
            ConditionExpression='attribute_exists(user_id)' #comprueba que el perfil ya existe
        )
        return True

    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return False
        raise


#Borrar perfil
def delete_profile(user_id):
    """Elimina un perfil"""

    table= get_profile_table()

    try:
        table.delete_item(
            Key={'user_id': user_id},
            ConditionExpression='attribute_exists(user_id)'
        )

        return True

    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return False
        raise