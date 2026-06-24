# app/__init__.py
from flask import Flask
from app.config import Config
from app.extensions import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)

    # Import Blueprints using aliases to avoid name collisions (since both are named 'bp')
    from app.routes.patients import bp as patients_bp
    from app.routes.eyes import bp as eyes_bp

    # Register Blueprints
    # (Prefixes are omitted here because they are already defined in your blueprint files)
    app.register_blueprint(patients_bp)
    app.register_blueprint(eyes_bp)

    # Simple health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {
            "status": "healthy", 
            "project": "Glaucoma Detection Platform Backend"
        }, 200

    return app