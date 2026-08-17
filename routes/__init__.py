from .assets import rest_assets, rest_certificates, rest_recurrents
from .auth import auth_bp
from .blueprints import assets_bp
from .rest_reports import reports_bp


def register_api_routes(app):
    """
    Helper function to register all blueprints to the Flask app.
    """
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(assets_bp, url_prefix="/assets")
    app.register_blueprint(auth_bp, url_prefix="/auth")
