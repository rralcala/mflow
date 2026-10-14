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


BEARER_SCHEME = "BearerAuth"
COOKIE_SCHEME = "CookieAuth"

auth = FlaskLoginAuth(scheme="Bearer", security_scheme_name=BEARER_SCHEME)
auth.description = "JWT from GET /auth/jwt as a Bearer token."


def security_schemes(cookie_name: str) -> dict:
    """Extra OpenAPI security schemes, for the SECURITY_SCHEMES config key.

    The cookie is never checked by an APIFlask auth object (Flask-Login reads
    it), so APIFlask can't infer this scheme and it is declared here instead.
    """
    return {
        COOKIE_SCHEME: {
            "type": "apiKey",
            "in": "cookie",
            "name": cookie_name,
            "description": "Session cookie set by POST /auth/rlogin or "
            "/auth/login. A remember_token cookie restores it once it expires.",
        }
    }


def add_cookie_security(spec: dict) -> dict:
    """Spec processor: accept CookieAuth wherever BearerAuth is accepted.

    Each entry of an operation's security list is an alternative, so adding
    CookieAuth as its own entry means either one authenticates the request.
    """
    for path_item in spec.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):  # e.g. path-level "parameters"
                continue
            security = operation.get("security", [])
            if any(BEARER_SCHEME in requirement for requirement in security):
                if {COOKIE_SCHEME: []} not in security:
                    security.append({COOKIE_SCHEME: []})
    return spec


@auth.error_processor
def auth_error(error):
    # Same body the Flask-Login unauthorized handler used to return.
    return {"message": "Unauthorized"}, error.status_code
