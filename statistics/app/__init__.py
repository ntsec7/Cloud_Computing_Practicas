from flask import Flask

def create_app():
    app = Flask(__name__)

    from app.routes import statistics_bp
    app.register_blueprint(statistics_bp)

    return app