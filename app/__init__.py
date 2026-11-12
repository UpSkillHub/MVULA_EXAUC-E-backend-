from flask import Flask, render_template
from app.config import Config
from app.extensions import db, migrate, jwt
from app.routes.organization_routes import organization_bp
from app.routes.user_routes import user_bp
from app.routes.document_routes import document_bp
from app.routes.permission_routes import permission_bp
from app.routes.auth_routes import auth_bp
from app import models

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(organization_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(permission_bp)
    app.register_blueprint(auth_bp)

    @app.route("/")
    def home():
        return render_template("index.html")

    return app