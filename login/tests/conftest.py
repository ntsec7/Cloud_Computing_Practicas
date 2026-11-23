
import os

# Variables de entorno de prueba.
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-south-2")
os.environ.setdefault("COGNITO_USER_POOL_ID", "test-pool")
os.environ.setdefault("COGNITO_CLIENT_ID", "test-client")
os.environ.setdefault("COGNITO_CLIENT_SECRET", "test-secret")
os.environ.setdefault("PROFILE_SERVICE_URL", "http://profile:5002")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-internal-token")

os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

import pytest
from flask import Flask

from app.routes import auth_bp, admin_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    with app.test_client() as client:
        yield client
