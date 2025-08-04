from .auth import auth_bp
from .rest_assets import assets_bp
from .rest_reports import reports_bp


def register_api_routes(app):
    """
    Helper function to register all blueprints to the Flask app.
    """
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(assets_bp, url_prefix="/assets")
    app.register_blueprint(auth_bp, url_prefix="/auth")
