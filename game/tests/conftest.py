
import os

# Variables necesarias para inicializar los clientes de AWS
os.environ.setdefault("DYNAMODB_ENDPOINT_URL", "http://localhost:8004")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-south-2")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("COGNITO_REGION", "eu-south-2")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-internal-token")

import pytest
from flask import Flask

from app.routes import game_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True

    app.register_blueprint(game_bp)

    with app.test_client() as client:
        yield client
