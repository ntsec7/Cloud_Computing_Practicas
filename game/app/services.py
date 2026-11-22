
import os
import boto3
import requests
import html
import uuid # genera los ids
import random # permite mezclar las respuestas de una pregunta
from datetime import datetime, timezone # para guardar cuando comenzo una partida

from dotenv import load_dotenv
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeSerializer

# Cargar las variables de entorno
load_dotenv()

# Conexión con DynamoDB local. Cliente de alto nivel para trabajar con games_table y responses_table (convierte los valores al formato que entiende DynamoDB)
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=os.getenv('DYNAMODB_ENDPOINT_URL'),
    region_name=os.getenv('AWS_DEFAULT_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# Cliente de bajo nivel de DynamoDB para las transacciones (tú conviertes los valores al formato de DynamoDB)
dynamodb_client = boto3.client(
    'dynamodb',
    endpoint_url=os.getenv('DYNAMODB_ENDPOINT_URL'),
    region_name=os.getenv('AWS_DEFAULT_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# Acceso a las tablas
games_table = dynamodb.Table('Games')
responses_table = dynamodb.Table('GameResponses')

serializer = TypeSerializer()

# URL de OpenTDB
OPENTDB_URL = 'https://opentdb.com/api.php'


# Número de preguntas por partida
QUESTION_COUNT = 10


# Cliente de Amazon Cognito
cognito = boto3.client(
    'cognito-idp',
    region_name=os.getenv('COGNITO_REGION')
)


def get_authenticated_user(access_token):

    try:
        # Validar el Access Token mediante Cognito
        response = cognito.get_user(
            AccessToken=access_token
        )

        # Obtener los atributos del usuario
        attributes = response['UserAttributes']

        # Buscar el identificador único del usuario
        user_id = next(
            (
                attribute['Value']
                for attribute in attributes
                if attribute['Name'] == 'sub'
            ),
            None
        )

        if not user_id:
            return None, 'No se ha podido identificar al usuario'

        return user_id, None

    except cognito.exceptions.NotAuthorizedException:
        return None, 'Token inválido o caducado'

    except ClientError:
        return None, 'Error al validar el usuario con Cognito'


def get_questions(category, difficulty):

    # Parámetros a enviar a OpenTDB
    params = {
        'amount': QUESTION_COUNT,
        'type': 'multiple'
    }

    if category is not None:
        params['category'] = category

    if difficulty is not None:
        params['difficulty'] = difficulty

    # Hacer petición a OpenTDB
    try:

        response= requests.get(
            OPENTDB_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status() #Comprobar si ha habido algún error HTTP

        data = response.json() #Convertir la respuesta a JSON

        # Comprobar el código de respuesta de OpenTDB
        if data['response_code'] != 0:
            return None, 'No se han podido obtener las preguntas'

        questions= []

        # Recorrer las preguntas recibidas
        for index, question in enumerate(data['results']):

            #Decodificar los caracteres HTML
            correct_answer = html.unescape(question['correct_answer'])

            incorrect_answers = [
                html.unescape(answer)
                for answer in question['incorrect_answers']
            ]

            answers = incorrect_answers + [correct_answer]

            # Mezclar aleatoriamente las cuatro respuestas
            random.shuffle(answers)

            # Obtener la posición de la respuesta correcta
            correct_answer_index = answers.index(correct_answer)

            questions.append({
                'question_id': str(index+1),
                'question': html.unescape(question['question']),
                'answers' : answers,
                'correct_answer_index' : correct_answer_index,
                'category': html.unescape(question['category']),
                'difficulty' : question['difficulty'] 
            })

        
        return questions, None

    except requests.exceptions.RequestException:
        return None, 'Error al conectar con OpenTDB'


# Crea la partida
def create_game(user_id, category, difficulty):

    # Obtener las preguntas de OpenTDB
    questions, error = get_questions(category, difficulty)

    if error:
        return None, error

    # Comprobar que hemos recibido las 10 preguntas
    if len(questions) != QUESTION_COUNT:
        return None, 'No se han recibido suficientes preguntas'


    # Generar identificador único para la partida
    game_id = str(uuid.uuid4())

    # Preparar los datos de la partida
    game = {
        'game_id': game_id,
        'user_id': user_id,
        'category': category,
        'difficulty': difficulty,
        'questions': questions,
        'current_question_index': 0,
        'current_question_started_at': datetime.now(timezone.utc).isoformat()
    }

    try:
        # Guardar partida en DynamoDB
        games_table.put_item(
            Item=game,
            ConditionExpression='attribute_not_exists(game_id)'
        )

        # Preparar primera pregunta 
        first_question = {
            'question_id': questions[0]['question_id'],
            'question': questions[0]['question'],
            'answers': questions[0]['answers']
        }

        return {
            'game_id': game_id,
            'question': first_question
        }, None

    except ClientError:
        return None, 'Error al guardar la partida'


# Comprueba que el usuario está respondiendo a una pregunta que le corresponde a él
def get_game(game_id, user_id):

    try:
        response= games_table.get_item(
            Key={
                'game_id': game_id
            },
            ConsistentRead=True
        )

        game= response.get('Item')

        # Comprobar si existe la partida
        if not game:
            return None, 'La partida no existe'


        # Comprobar que pertenece al usuario
        if game['user_id'] != user_id:
            return None, 'No tienes permiso para acceder a esta partida'

        return game, None
    
    except ClientError:
        return None, 'Error al consultar la partida'


def save_response(game_id, user_id, question_id, answer):

    # Recuperar la partida y comprobar que pertenece al usuario
    game, error = get_game(game_id, user_id)

    if error:
        return None, error

    # Obtener índice de la pregunta actual
    current_index = int(game['current_question_index']) #para que se guarde como un entero

    # Comprobar que la partida no ha terminado
    if current_index >= len(game['questions']):
        return None, 'La partida ya ha terminado'

    # Obtener la pregunta que corresponde contestar
    question = game['questions'][current_index]

    expected_question_id= question['question_id']

    # Comprobar que el usuario responde a la pregunta actual
    if question_id != expected_question_id:
        return None, 'La pregunta no corresponde a la partida actual'

    # Comprobar que la respuesta enviada es valida
    if type(answer) is not int or answer < 0 or answer >= len(question['answers']):
        return None, 'La respuesta enviada no es válida'

    # Comprobar que tenemos la fecha de inicio de la pregunta
    started_at = game.get('current_question_started_at')

    if not started_at:
        return None, 'No se ha podido calcular el tiempo de respuesta'

    # Calcular el tiempo transcurrido
    start_time = datetime.fromisoformat(started_at)
    end_time = datetime.now(timezone.utc)

    response_time_ms = int(
        (end_time - start_time).total_seconds() * 1000
    )

    # Evitar valores negativos
    response_time_ms = max(0, response_time_ms)

    # Comprobar si la respuesta es correcta
    is_correct = answer == question['correct_answer_index']

    # Obtener el texto de la respuesta correcta
    correct_answer = question['answers'][int(question['correct_answer_index'])]

    # Identificador único de la respuesta dentro de la partida
    response_id = f"{game_id}#{question_id}"

    # Preparar el elemento que se guardará en GameResponses
    response_item = {
        'user_id': user_id,
        'response_id': response_id,
        'game_id': game_id,
        'question_id': question_id,
        'is_correct': is_correct,
        'response_time_ms': response_time_ms
    }

    # Calcular el índice de la siguiente pregunta
    next_index = current_index + 1

    # Comprobar si la partida ha terminado
    completed = next_index >= len(game['questions'])

    # Preparar la fecha de inicio de la siguiente pregunta
    next_started_at = datetime.now(timezone.utc).isoformat()

    # Ejecutar ambas operaciones en una única transacción de manera atómica con transact_write_items
    try:

        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    'Put': {
                        'TableName': 'GameResponses',
                        'Item': {
                            key: serializer.serialize(value)
                            for key, value in response_item.items()
                        },
                        'ConditionExpression': (
                            'attribute_not_exists(response_id)'
                        )
                    }
                },
                {
                    'Update': {
                        'TableName': 'Games',
                        'Key': {
                            'game_id': serializer.serialize(game_id)
                        },
                        'UpdateExpression': (
                            'SET current_question_index = :next_index, '
                            'current_question_started_at = :started_at'
                        ),
                        'ConditionExpression': (
                            'current_question_index = :current_index '
                            'AND user_id = :user_id'
                        ),
                        'ExpressionAttributeValues': {
                            ':next_index': serializer.serialize(next_index),
                            ':started_at': serializer.serialize(next_started_at),
                            ':current_index': serializer.serialize(current_index),
                            ':user_id': serializer.serialize(user_id)
                        }
                    }
                }
            ]
        )

    except ClientError as error:

        print("ERROR EN LA TRANSACCIÓN:")
        print(error.response)

        error_code = error.response['Error']['Code']

        if error_code == 'TransactionCanceledException':
            return None, (
                'No se ha podido registrar la respuesta '
                'porque la partida ha cambiado o la respuesta ya existe'
            )

        return None, 'Error al guardar la respuesta'

    # Preparar la información que se va a devolver
    result = {
        'question_id': question_id,
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'response_time_ms': response_time_ms,
        'completed': completed
    }

    # Si quedan preguntas, devolver la siguiente
    if not completed:
        next_question = game['questions'][next_index]

        result['next_question'] = {
            'question_id': next_question['question_id'],
            'question': next_question['question'],
            'answers': next_question['answers']
        }

    return result, None # si no quedan preguntas responde result sin next_question


