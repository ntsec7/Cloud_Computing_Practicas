
from unittest.mock import patch

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def make_questions():
    return [
        {
            "question_id": str(i + 1),
            "question": f"Pregunta {i + 1}",
            "answers": ["A", "B", "C", "D"],
            "correct_answer_index": 0,
            "category": "18",
            "difficulty": "easy"
        }
        for i in range(10)
    ]


def make_game_result():
    return {
        "game_id": "game-123",
        "question": {
            "question_id": "1",
            "question": "Pregunta 1",
            "answers": ["A", "B", "C", "D"]
        }
    }


def make_response_result():
    return {
        "question_id": "1",
        "is_correct": True,
        "correct_answer": "A",
        "response_time_ms": 1500,
        "completed": False,
        "next_question": {
            "question_id": "2",
            "question": "Pregunta 2",
            "answers": ["A", "B", "C", "D"]
        }
    }


# --------------------------------------------------
# AUTENTICACIÓN
# --------------------------------------------------

@patch("app.routes.get_authenticated_user")
def test_start_game_without_token(mock_auth, client):
    response = client.post(
        "/game/",
        json={}
    )

    assert response.status_code == 401
    assert response.json["error"] == "Falta el token de autenticación"
    mock_auth.assert_not_called()


@patch("app.routes.get_authenticated_user")
def test_start_game_invalid_token(mock_auth, client):
    mock_auth.return_value = (None, "Token inválido o caducado")

    response = client.post(
        "/game/",
        json={},
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401
    assert response.json["error"] == "Token inválido o caducado"


@patch("app.routes.get_authenticated_user")
def test_start_game_invalid_authorization_scheme(mock_auth, client):
    response = client.post(
        "/game/",
        json={},
        headers={"Authorization": "Basic token"}
    )

    assert response.status_code == 401
    assert response.json["error"] == "Falta el token de autenticación"
    mock_auth.assert_not_called()


# --------------------------------------------------
# CREAR PARTIDA
# --------------------------------------------------

@patch("app.routes.create_game")
@patch("app.routes.get_authenticated_user")
def test_start_game_success(mock_auth, mock_create_game, client):
    mock_auth.return_value = ("user-123", None)
    mock_create_game.return_value = (make_game_result(), None)

    response = client.post(
        "/game/",
        json={
            "category": 18,
            "difficulty": "easy"
        },
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 201
    assert response.json == make_game_result()

    mock_create_game.assert_called_once_with(
        "user-123",
        18,
        "easy"
    )


@patch("app.routes.get_authenticated_user")
def test_start_game_without_json(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/",
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Se deben enviar los datos en formato JSON"
    )


@patch("app.routes.get_authenticated_user")
def test_start_game_invalid_category(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/",
        json={"category": "18"},
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "La categoría debe ser un número entero"
    )


@patch("app.routes.get_authenticated_user")
def test_start_game_boolean_category_invalid(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/",
        json={"category": True},
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "La categoría debe ser un número entero"
    )


@patch("app.routes.get_authenticated_user")
def test_start_game_invalid_difficulty(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/",
        json={"difficulty": "extreme"},
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == "La dificultad no es válida"


@patch("app.routes.create_game")
@patch("app.routes.get_authenticated_user")
def test_start_game_service_error(mock_auth, mock_create_game, client):
    mock_auth.return_value = ("user-123", None)
    mock_create_game.return_value = (
        None,
        "Error al conectar con OpenTDB"
    )

    response = client.post(
        "/game/",
        json={},
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 502
    assert response.json["error"] == "Error al conectar con OpenTDB"


@patch("app.routes.create_game")
@patch("app.routes.get_authenticated_user")
def test_start_game_without_filters(
    mock_auth,
    mock_create_game,
    client
):
    mock_auth.return_value = ("user-123", None)
    mock_create_game.return_value = (make_game_result(), None)

    response = client.post(
        "/game/",
        json={},
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 201

    mock_create_game.assert_called_once_with(
        "user-123",
        None,
        None
    )


# --------------------------------------------------
# ENVIAR RESPUESTA
# --------------------------------------------------

@patch("app.routes.get_authenticated_user")
def test_answer_question_without_token(mock_auth, client):
    response = client.post(
        "/game/game-123/answer",
        json={
            "question_id": "1",
            "answer": 0
        }
    )

    assert response.status_code == 401
    assert response.json["error"] == "Falta el token de autenticación"
    mock_auth.assert_not_called()


@patch("app.routes.get_authenticated_user")
def test_answer_question_invalid_token(mock_auth, client):
    mock_auth.return_value = (None, "Token inválido o caducado")

    response = client.post(
        "/game/game-123/answer",
        json={
            "question_id": "1",
            "answer": 0
        },
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401
    assert response.json["error"] == "Token inválido o caducado"


@patch("app.routes.save_response")
@patch("app.routes.get_authenticated_user")
def test_answer_question_success(
    mock_auth,
    mock_save_response,
    client
):
    mock_auth.return_value = ("user-123", None)
    mock_save_response.return_value = (make_response_result(), None)

    response = client.post(
        "/game/game-123/answer",
        json={
            "question_id": "1",
            "answer": 0
        },
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 200
    assert response.json == make_response_result()

    mock_save_response.assert_called_once_with(
        "game-123",
        "user-123",
        "1",
        0
    )


@patch("app.routes.get_authenticated_user")
def test_answer_question_without_json(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/game-123/answer",
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Se deben enviar datos en formato JSON"
    )


@patch("app.routes.get_authenticated_user")
def test_answer_question_empty_json(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/game-123/answer",
        json={},
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Se deben enviar datos en formato JSON"
    )


@patch("app.routes.get_authenticated_user")
def test_answer_question_missing_question_id(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/game-123/answer",
        json={"answer": 0},
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == "Faltan campos obligatorios"


@patch("app.routes.get_authenticated_user")
def test_answer_question_missing_answer(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/game-123/answer",
        json={"question_id": "1"},
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == "Faltan campos obligatorios"


@patch("app.routes.get_authenticated_user")
def test_answer_question_invalid_question_id(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/game-123/answer",
        json={
            "question_id": 1,
            "answer": 0
        },
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "El identificador de pregunta no es válido"
    )


@patch("app.routes.get_authenticated_user")
def test_answer_question_invalid_answer_type(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/game-123/answer",
        json={
            "question_id": "1",
            "answer": "0"
        },
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "La respuesta debe ser un número entero"
    )


@patch("app.routes.get_authenticated_user")
def test_answer_question_boolean_answer_invalid(mock_auth, client):
    mock_auth.return_value = ("user-123", None)

    response = client.post(
        "/game/game-123/answer",
        json={
            "question_id": "1",
            "answer": True
        },
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "La respuesta debe ser un número entero"
    )


@patch("app.routes.save_response")
@patch("app.routes.get_authenticated_user")
def test_answer_question_service_error(
    mock_auth,
    mock_save_response,
    client
):
    mock_auth.return_value = ("user-123", None)
    mock_save_response.return_value = (
        None,
        "La partida no existe"
    )

    response = client.post(
        "/game/game-123/answer",
        json={
            "question_id": "1",
            "answer": 0
        },
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 400
    assert response.json["error"] == "La partida no existe"


# --------------------------------------------------
# AUTENTICACIÓN INTERNA
# --------------------------------------------------

def test_internal_route_without_token(client):
    response = client.get(
        "/game/internal/games/game-123"
    )

    assert response.status_code == 403
    assert response.json["error"] == "Petición no autorizada"


def test_internal_route_invalid_token(client):
    response = client.get(
        "/game/internal/games/game-123",
        headers={"X-Internal-Token": "wrong-token"}
    )

    assert response.status_code == 403
    assert response.json["error"] == "Petición no autorizada"


# --------------------------------------------------
# OBTENER PARTIDA PARA ESTADÍSTICAS
# --------------------------------------------------

@patch("app.routes.get_game_for_statistics")
def test_get_internal_game_success(mock_get_game, client):
    game = {
        "game_id": "game-123",
        "user_id": "user-123",
        "category": 18,
        "difficulty": "easy"
    }

    mock_get_game.return_value = (game, None)

    response = client.get(
        "/game/internal/games/game-123",
        headers={"X-Internal-Token": "test-internal-token"}
    )

    assert response.status_code == 200
    assert response.json == game

    mock_get_game.assert_called_once_with("game-123")


@patch("app.routes.get_game_for_statistics")
def test_get_internal_game_not_found(mock_get_game, client):
    mock_get_game.return_value = (
        None,
        "La partida no existe"
    )

    response = client.get(
        "/game/internal/games/game-123",
        headers={"X-Internal-Token": "test-internal-token"}
    )

    assert response.status_code == 404
    assert response.json["error"] == "La partida no existe"


@patch("app.routes.get_game_for_statistics")
def test_get_internal_game_service_error(mock_get_game, client):
    mock_get_game.return_value = (
        None,
        "Error al consultar la partida"
    )

    response = client.get(
        "/game/internal/games/game-123",
        headers={"X-Internal-Token": "test-internal-token"}
    )

    assert response.status_code == 500
    assert response.json["error"] == "Error al consultar la partida"


# --------------------------------------------------
# OBTENER RESPUESTAS DE UNA PARTIDA
# --------------------------------------------------

@patch("app.routes.get_game_responses_for_statistics")
@patch("app.routes.get_game_for_statistics")
def test_get_internal_game_responses_success(
    mock_get_game,
    mock_get_responses,
    client
):
    game = {
        "game_id": "game-123",
        "user_id": "user-123",
        "category": 18,
        "difficulty": "easy"
    }

    responses = [
        {
            "game_id": "game-123",
            "question_id": "1",
            "is_correct": True,
            "response_time_ms": 1500
        }
    ]

    mock_get_game.return_value = (game, None)
    mock_get_responses.return_value = (responses, None)

    response = client.get(
        "/game/internal/games/game-123/responses",
        headers={"X-Internal-Token": "test-internal-token"}
    )

    assert response.status_code == 200
    assert response.json == {
        "game_id": "game-123",
        "responses": responses
    }

    mock_get_game.assert_called_once_with("game-123")
    mock_get_responses.assert_called_once_with(
        "game-123",
        "user-123"
    )


@patch("app.routes.get_game_for_statistics")
def test_get_internal_game_responses_game_not_found(
    mock_get_game,
    client
):
    mock_get_game.return_value = (
        None,
        "La partida no existe"
    )

    response = client.get(
        "/game/internal/games/game-123/responses",
        headers={"X-Internal-Token": "test-internal-token"}
    )

    assert response.status_code == 404
    assert response.json["error"] == "La partida no existe"


@patch("app.routes.get_game_responses_for_statistics")
@patch("app.routes.get_game_for_statistics")
def test_get_internal_game_responses_service_error(
    mock_get_game,
    mock_get_responses,
    client
):
    mock_get_game.return_value = (
        {
            "game_id": "game-123",
            "user_id": "user-123"
        },
        None
    )

    mock_get_responses.return_value = (
        None,
        "Error al consultar las respuestas de la partida"
    )

    response = client.get(
        "/game/internal/games/game-123/responses",
        headers={"X-Internal-Token": "test-internal-token"}
    )

    assert response.status_code == 500
    assert response.json["error"] == (
        "Error al consultar las respuestas de la partida"
    )


# --------------------------------------------------
# OBTENER RESPUESTAS GLOBALES DE UN USUARIO
# --------------------------------------------------

@patch("app.routes.get_user_responses_for_statistics")
def test_get_internal_user_responses_success(
    mock_get_responses,
    client
):
    responses = [
        {
            "game_id": "game-123",
            "question_id": "1",
            "is_correct": True,
            "response_time_ms": 1500
        },
        {
            "game_id": "game-456",
            "question_id": "1",
            "is_correct": False,
            "response_time_ms": 2500
        }
    ]

    mock_get_responses.return_value = (responses, None)

    response = client.get(
        "/game/internal/users/user-123/responses",
        headers={"X-Internal-Token": "test-internal-token"}
    )

    assert response.status_code == 200
    assert response.json == {
        "user_id": "user-123",
        "responses": responses
    }

    mock_get_responses.assert_called_once_with("user-123")


@patch("app.routes.get_user_responses_for_statistics")
def test_get_internal_user_responses_service_error(
    mock_get_responses,
    client
):
    mock_get_responses.return_value = (
        None,
        "Error al consultar las respuestas del jugador"
    )

    response = client.get(
        "/game/internal/users/user-123/responses",
        headers={"X-Internal-Token": "test-internal-token"}
    )

    assert response.status_code == 500
    assert response.json["error"] == (
        "Error al consultar las respuestas del jugador"
    )
