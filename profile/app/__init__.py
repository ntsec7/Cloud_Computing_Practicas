from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.routes import profile_bp
    app.register_blueprint(profile_bp)

    return app