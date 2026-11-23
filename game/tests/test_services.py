
from unittest.mock import patch

from botocore.exceptions import ClientError

from app import services

# --------------------------------------------------
# FUNCIONES AUXILIARES
# --------------------------------------------------

def make_client_error(code="InternalServerError"):
    return ClientError(
        {
            "Error": {
                "Code": code,
                "Message": "Error de prueba"
            }
        },
        "TestOperation"
    )


def make_questions():
    return [
        {
            "question_id": str(i + 1),
            "question": f"Pregunta {i + 1}",
            "answers": ["A", "B", "C", "D"],
            "correct_answer_index": 0,
            "category": "Science",
            "difficulty": "easy"
        }
        for i in range(services.QUESTION_COUNT)
    ]


def make_game():
    return {
        "game_id": "game-123",
        "user_id": "user-123",
        "category": 18,
        "difficulty": "easy",
        "questions": make_questions(),
        "current_question_index": 0,
        "current_question_started_at": "2026-11-23T10:00:00+00:00"
    }


# --------------------------------------------------
# GET AUTHENTICATED USER
# --------------------------------------------------

@patch("app.services.cognito")
def test_get_authenticated_user_success(mock_cognito):
    mock_cognito.get_user.return_value = {
        "UserAttributes": [
            {"Name": "email", "Value": "user@test.com"},
            {"Name": "sub", "Value": "user-123"}
        ]
    }

    user_id, error = services.get_authenticated_user("valid-token")

    assert user_id == "user-123"
    assert error is None

    mock_cognito.get_user.assert_called_once_with(
        AccessToken="valid-token"
    )


@patch("app.services.cognito")
def test_get_authenticated_user_without_sub(mock_cognito):
    mock_cognito.get_user.return_value = {
        "UserAttributes": [
            {"Name": "email", "Value": "user@test.com"}
        ]
    }

    user_id, error = services.get_authenticated_user("valid-token")

    assert user_id is None
    assert error == "No se ha podido identificar al usuario"


@patch("app.services.cognito")
def test_get_authenticated_user_invalid_token(mock_cognito):
    mock_cognito.exceptions.NotAuthorizedException = type(
        "NotAuthorizedException",
        (Exception,),
        {}
    )

    mock_cognito.get_user.side_effect = (
        mock_cognito.exceptions.NotAuthorizedException()
    )

    user_id, error = services.get_authenticated_user("invalid-token")

    assert user_id is None
    assert error == "Token inválido o caducado"



@patch("app.services.cognito")
def test_get_authenticated_user_client_error(mock_cognito):
    from botocore.exceptions import ClientError

    mock_cognito.exceptions.NotAuthorizedException = type(
        "NotAuthorizedException",
        (Exception,),
        {}
    )

    mock_cognito.get_user.side_effect = ClientError(
        {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Error de prueba"
            }
        },
        "GetUser"
    )

    user_id, error = services.get_authenticated_user("token")

    assert user_id is None
    assert error == "Error al validar el usuario con Cognito"



# --------------------------------------------------
# GET QUESTIONS
# --------------------------------------------------

@patch("app.services.random.shuffle")
@patch("app.services.requests.get")
def test_get_questions_success(mock_get, mock_shuffle):
    mock_get.return_value.json.return_value = {
        "response_code": 0,
        "results": [
            {
                "question": "What is the capital of Spain?",
                "correct_answer": "Madrid",
                "incorrect_answers": [
                    "Paris",
                    "Rome",
                    "Berlin"
                ],
                "category": "Geography",
                "difficulty": "easy"
            }
            for _ in range(services.QUESTION_COUNT)
        ]
    }

    questions, error = services.get_questions(22, "easy")

    assert error is None
    assert len(questions) == services.QUESTION_COUNT

    first_question = questions[0]

    assert first_question["question_id"] == "1"
    assert first_question["question"] == "What is the capital of Spain?"
    assert len(first_question["answers"]) == 4
    assert (first_question["answers"][first_question["correct_answer_index"]] == "Madrid")
    assert first_question["category"] == "Geography"
    assert first_question["difficulty"] == "easy"

    mock_get.assert_called_once_with(
        services.OPENTDB_URL,
        params={
            "amount": services.QUESTION_COUNT,
            "type": "multiple",
            "category": 22,
            "difficulty": "easy"
        },
        timeout=10
    )


@patch("app.services.random.shuffle")
@patch("app.services.requests.get")
def test_get_questions_without_filters(mock_get, mock_shuffle):
    mock_get.return_value.json.return_value = {
        "response_code": 0,
        "results": []
    }

    questions, error = services.get_questions(None, None)

    assert questions == []
    assert error is None

    mock_get.assert_called_once_with(
        services.OPENTDB_URL,
        params={
            "amount": services.QUESTION_COUNT,
            "type": "multiple"
        },
        timeout=10
    )


@patch("app.services.requests.get")
def test_get_questions_api_error_code(mock_get):
    mock_get.return_value.json.return_value = {
        "response_code": 1,
        "results": []
    }

    questions, error = services.get_questions(None, None)

    assert questions is None
    assert error == "No se han podido obtener las preguntas"


@patch("app.services.requests.get")
def test_get_questions_connection_error(mock_get):
    mock_get.side_effect = services.requests.exceptions.Timeout()

    questions, error = services.get_questions(None, None)

    assert questions is None
    assert error == "Error al conectar con OpenTDB"


@patch("app.services.requests.get")
def test_get_questions_http_error(mock_get):
    mock_get.return_value.raise_for_status.side_effect = (
        services.requests.exceptions.HTTPError()
    )

    questions, error = services.get_questions(None, None)

    assert questions is None
    assert error == "Error al conectar con OpenTDB"


# --------------------------------------------------
# CREATE GAME
# --------------------------------------------------

@patch("app.services.games_table")
@patch("app.services.get_questions")
@patch("app.services.uuid.uuid4")
def test_create_game_success(mock_uuid, mock_get_questions, mock_table):
    mock_uuid.return_value = "game-123"
    mock_get_questions.return_value = (make_questions(), None)

    result, error = services.create_game(
        "user-123",
        18,
        "easy"
    )

    assert error is None
    assert result["game_id"] == "game-123"
    assert result["question"]["question_id"] == "1"
    assert result["question"]["question"] == "Pregunta 1"
    assert result["question"]["answers"] == ["A", "B", "C", "D"]

    mock_table.put_item.assert_called_once()

    saved_game = mock_table.put_item.call_args.kwargs["Item"]

    assert saved_game["user_id"] == "user-123"
    assert saved_game["category"] == 18
    assert saved_game["difficulty"] == "easy"
    assert saved_game["current_question_index"] == 0
    assert len(saved_game["questions"]) == services.QUESTION_COUNT

    assert mock_table.put_item.call_args.kwargs[
        "ConditionExpression"
    ] == "attribute_not_exists(game_id)"


@patch("app.services.get_questions")
def test_create_game_questions_error(mock_get_questions):
    mock_get_questions.return_value = (
        None,
        "Error al conectar con OpenTDB"
    )

    result, error = services.create_game("user-123", None, None)

    assert result is None
    assert error == "Error al conectar con OpenTDB"


@patch("app.services.games_table")
@patch("app.services.get_questions")
def test_create_game_not_enough_questions(mock_get_questions, mock_table):
    mock_get_questions.return_value = (
        make_questions()[:5],
        None
    )

    result, error = services.create_game("user-123", None, None)

    assert result is None
    assert error == "No se han recibido suficientes preguntas"

    mock_table.put_item.assert_not_called()


@patch("app.services.games_table")
@patch("app.services.get_questions")
def test_create_game_dynamodb_error(mock_get_questions, mock_table):
    mock_get_questions.return_value = (make_questions(), None)
    mock_table.put_item.side_effect = make_client_error()

    result, error = services.create_game("user-123", None, None)

    assert result is None
    assert error == "Error al guardar la partida"


# --------------------------------------------------
# GET GAME
# --------------------------------------------------

@patch("app.services.games_table")
def test_get_game_success(mock_table):
    game = make_game()
    mock_table.get_item.return_value = {"Item": game}

    result, error = services.get_game("game-123", "user-123")

    assert error is None
    assert result == game

    mock_table.get_item.assert_called_once_with(
        Key={"game_id": "game-123"},
        ConsistentRead=True
    )


@patch("app.services.games_table")
def test_get_game_not_found(mock_table):
    mock_table.get_item.return_value = {}

    result, error = services.get_game("game-123", "user-123")

    assert result is None
    assert error == "La partida no existe"


@patch("app.services.games_table")
def test_get_game_forbidden(mock_table):
    mock_table.get_item.return_value = {
        "Item": make_game()
    }

    result, error = services.get_game("game-123", "other-user")

    assert result is None
    assert error == "No tienes permiso para acceder a esta partida"


@patch("app.services.games_table")
def test_get_game_dynamodb_error(mock_table):
    mock_table.get_item.side_effect = make_client_error()

    result, error = services.get_game("game-123", "user-123")

    assert result is None
    assert error == "Error al consultar la partida"


# --------------------------------------------------
# SAVE RESPONSE
# --------------------------------------------------

@patch("app.services.dynamodb_client")
@patch("app.services.get_game")
def test_save_response_success(mock_get_game, mock_dynamodb_client):
    game = make_game()
    mock_get_game.return_value = (game, None)

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        0
    )

    assert error is None
    assert result["question_id"] == "1"
    assert result["is_correct"] is True
    assert result["correct_answer"] == "A"
    assert result["completed"] is False
    assert "next_question" in result
    assert result["next_question"]["question_id"] == "2"

    mock_dynamodb_client.transact_write_items.assert_called_once()

    transaction = (
        mock_dynamodb_client.transact_write_items.call_args.kwargs[
            "TransactItems"
        ]
    )

    assert len(transaction) == 2
    assert "Put" in transaction[0]
    assert "Update" in transaction[1]


@patch("app.services.dynamodb_client")
@patch("app.services.get_game")
def test_save_response_incorrect_answer(mock_get_game, mock_dynamodb_client):
    mock_get_game.return_value = (make_game(), None)

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        2
    )

    assert error is None
    assert result["is_correct"] is False
    assert result["correct_answer"] == "A"


@patch("app.services.get_game")
def test_save_response_game_error(mock_get_game):
    mock_get_game.return_value = (
        None,
        "La partida no existe"
    )

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        0
    )

    assert result is None
    assert error == "La partida no existe"


@patch("app.services.get_game")
def test_save_response_game_completed(mock_get_game):
    game = make_game()
    game["current_question_index"] = services.QUESTION_COUNT

    mock_get_game.return_value = (game, None)

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        0
    )

    assert result is None
    assert error == "La partida ya ha terminado"


@patch("app.services.get_game")
def test_save_response_wrong_question(mock_get_game):
    mock_get_game.return_value = (make_game(), None)

    result, error = services.save_response(
        "game-123",
        "user-123",
        "2",
        0
    )

    assert result is None
    assert error == "La pregunta no corresponde a la partida actual"


@patch("app.services.get_game")
def test_save_response_invalid_answer(mock_get_game):
    mock_get_game.return_value = (make_game(), None)

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        5
    )

    assert result is None
    assert error == "La respuesta enviada no es válida"


@patch("app.services.get_game")
def test_save_response_boolean_answer_invalid(mock_get_game):
    mock_get_game.return_value = (make_game(), None)

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        True
    )

    assert result is None
    assert error == "La respuesta enviada no es válida"


@patch("app.services.get_game")
def test_save_response_without_start_time(mock_get_game):
    game = make_game()
    game["current_question_started_at"] = None

    mock_get_game.return_value = (game, None)

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        0
    )

    assert result is None
    assert error == "No se ha podido calcular el tiempo de respuesta"


@patch("app.services.dynamodb_client")
@patch("app.services.get_game")
def test_save_response_transaction_canceled(
    mock_get_game,
    mock_dynamodb_client
):
    mock_get_game.return_value = (make_game(), None)

    mock_dynamodb_client.transact_write_items.side_effect = (
        make_client_error("TransactionCanceledException")
    )

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        0
    )

    assert result is None
    assert error == (
        "No se ha podido registrar la respuesta "
        "porque la partida ha cambiado o la respuesta ya existe"
    )


@patch("app.services.dynamodb_client")
@patch("app.services.get_game")
def test_save_response_transaction_error(
    mock_get_game,
    mock_dynamodb_client
):
    mock_get_game.return_value = (make_game(), None)
    mock_dynamodb_client.transact_write_items.side_effect = (
        make_client_error()
    )

    result, error = services.save_response(
        "game-123",
        "user-123",
        "1",
        0
    )

    assert result is None
    assert error == "Error al guardar la respuesta"


@patch("app.services.dynamodb_client")
@patch("app.services.get_game")
def test_save_response_last_question(
    mock_get_game,
    mock_dynamodb_client
):
    game = make_game()
    game["current_question_index"] = services.QUESTION_COUNT - 1

    mock_get_game.return_value = (game, None)

    result, error = services.save_response(
        "game-123",
        "user-123",
        "10",
        0
    )

    assert error is None
    assert result["completed"] is True
    assert "next_question" not in result


# --------------------------------------------------
# GET GAME FOR STATISTICS
# --------------------------------------------------

@patch("app.services.games_table")
def test_get_game_for_statistics_success(mock_table):
    game = make_game()
    mock_table.get_item.return_value = {"Item": game}

    result, error = services.get_game_for_statistics("game-123")

    assert error is None
    assert result == {
        "game_id": "game-123",
        "user_id": "user-123",
        "category": 18,
        "difficulty": "easy"
    }

    mock_table.get_item.assert_called_once_with(
        Key={"game_id": "game-123"},
        ConsistentRead=True
    )


@patch("app.services.games_table")
def test_get_game_for_statistics_not_found(mock_table):
    mock_table.get_item.return_value = {}

    result, error = services.get_game_for_statistics("game-123")

    assert result is None
    assert error == "La partida no existe"


@patch("app.services.games_table")
def test_get_game_for_statistics_dynamodb_error(mock_table):
    mock_table.get_item.side_effect = make_client_error()

    result, error = services.get_game_for_statistics("game-123")

    assert result is None
    assert error == "Error al consultar la partida"


# --------------------------------------------------
# GET GAME RESPONSES FOR STATISTICS
# --------------------------------------------------

@patch("app.services.responses_table")
def test_get_game_responses_for_statistics_success(mock_table):
    mock_table.query.return_value = {
        "Items": [
            {
                "game_id": "game-123",
                "question_id": "1",
                "is_correct": True,
                "response_time_ms": "1500"
            },
            {
                "game_id": "game-123",
                "question_id": "2",
                "is_correct": False,
                "response_time_ms": "2500"
            }
        ]
    }

    result, error = services.get_game_responses_for_statistics(
        "game-123",
        "user-123"
    )

    assert error is None
    assert len(result) == 2
    assert result[0]["response_time_ms"] == 1500
    assert result[1]["response_time_ms"] == 2500

    mock_table.query.assert_called_once()


@patch("app.services.responses_table")
def test_get_game_responses_for_statistics_pagination(mock_table):
    mock_table.query.side_effect = [
        {
            "Items": [
                {
                    "game_id": "game-123",
                    "question_id": "1",
                    "is_correct": True,
                    "response_time_ms": "1500"
                }
            ],
            "LastEvaluatedKey": {
                "user_id": "user-123",
                "response_id": "game-123#1"
            }
        },
        {
            "Items": [
                {
                    "game_id": "game-123",
                    "question_id": "2",
                    "is_correct": False,
                    "response_time_ms": "2500"
                }
            ]
        }
    ]

    result, error = services.get_game_responses_for_statistics(
        "game-123",
        "user-123"
    )

    assert error is None
    assert len(result) == 2
    assert result[0]["response_time_ms"] == 1500
    assert result[1]["response_time_ms"] == 2500
    assert mock_table.query.call_count == 2

    second_call = mock_table.query.call_args_list[1].kwargs

    assert second_call["ExclusiveStartKey"] == {
        "user_id": "user-123",
        "response_id": "game-123#1"
    }


@patch("app.services.responses_table")
def test_get_game_responses_for_statistics_error(mock_table):
    mock_table.query.side_effect = make_client_error()

    result, error = services.get_game_responses_for_statistics(
        "game-123",
        "user-123"
    )

    assert result is None
    assert error == "Error al consultar las respuestas de la partida"


# --------------------------------------------------
# GET USER RESPONSES FOR STATISTICS
# --------------------------------------------------

@patch("app.services.responses_table")
def test_get_user_responses_for_statistics_success(mock_table):
    mock_table.query.return_value = {
        "Items": [
            {
                "game_id": "game-123",
                "question_id": "1",
                "is_correct": True,
                "response_time_ms": "1500"
            },
            {
                "game_id": "game-456",
                "question_id": "1",
                "is_correct": False,
                "response_time_ms": "3000"
            }
        ]
    }

    result, error = services.get_user_responses_for_statistics("user-123")

    assert error is None
    assert len(result) == 2
    assert result[0]["response_time_ms"] == 1500
    assert result[1]["response_time_ms"] == 3000

    mock_table.query.assert_called_once()


@patch("app.services.responses_table")
def test_get_user_responses_for_statistics_pagination(mock_table):
    mock_table.query.side_effect = [
        {
            "Items": [
                {
                    "game_id": "game-123",
                    "question_id": "1",
                    "is_correct": True,
                    "response_time_ms": "1500"
                }
            ],
            "LastEvaluatedKey": {
                "user_id": "user-123",
                "response_id": "game-123#1"
            }
        },
        {
            "Items": [
                {
                    "game_id": "game-456",
                    "question_id": "1",
                    "is_correct": False,
                    "response_time_ms": "3000"
                }
            ]
        }
    ]

    result, error = services.get_user_responses_for_statistics("user-123")

    assert error is None
    assert len(result) == 2
    assert result[0]["response_time_ms"] == 1500
    assert result[1]["response_time_ms"] == 3000
    assert mock_table.query.call_count == 2

    second_call = mock_table.query.call_args_list[1].kwargs

    assert second_call["ExclusiveStartKey"] == {
        "user_id": "user-123",
        "response_id": "game-123#1"
    }


@patch("app.services.responses_table")
def test_get_user_responses_for_statistics_error(mock_table):
    mock_table.query.side_effect = make_client_error()

    result, error = services.get_user_responses_for_statistics("user-123")

    assert result is None
    assert error == "Error al consultar las respuestas del jugador"
