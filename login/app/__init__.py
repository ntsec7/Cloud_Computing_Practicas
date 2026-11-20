from flask import Flask

def create_app():
    app = Flask(__name__)

    from app.routes import auth_bp, admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app