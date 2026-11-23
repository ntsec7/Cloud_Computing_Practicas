
from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.routes import game_bp
    app.register_blueprint(game_bp)

    return app
