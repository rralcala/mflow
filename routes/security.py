from apiflask import HTTPTokenAuth
from flask_login import current_user


class FlaskLoginAuth(HTTPTokenAuth):
    """Bearer-token auth scheme backed by Flask-Login.

    Flask-Login already resolves the caller from either the session cookie
    (set by /auth/rlogin and /auth/login) or an "Authorization: Bearer <jwt>"
    header (request_loader in routes/auth.py). Flask-HTTPAuth would skip its
    verify callback for cookie-only requests, so authenticate() is overridden
    to defer to Flask-Login. The class still provides the APIFlask integration
    (OpenAPI security metadata and 401 handling).
    """

    def authenticate(self, auth, stored_password):
        return current_user if current_user.is_authenticated else None


auth = FlaskLoginAuth(scheme="Bearer", security_scheme_name="BearerAuth")
auth.description = (
    "JWT from GET /auth/jwt as a Bearer token. Requests carrying the session "
    "cookie set by POST /auth/rlogin are accepted as well."
)


@auth.error_processor
def auth_error(error):
    # Same body the Flask-Login unauthorized handler used to return.
    return {"message": "Unauthorized"}, error.status_code
