import datetime
from http import HTTPStatus

import jwt
from apiflask import APIBlueprint, abort
from flask import jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from init import login_manager
from lib.config import Config
from lib.logger import get_logger
from lib.passwords import (
    PasswordStoreError,
    hash_password,
    password_problem,
    set_password_hash,
)
from lib.user_config import UserStore
from models.models import authenticate, find_user_by_id
from routes.schemas import (
    JwtTokenQuery,
    LoginIn,
    LoginOut,
    MessageOut,
    PasswordChangeIn,
    ProfileOut,
)
from routes.security import auth

auth_bp = APIBlueprint("auth", __name__, tag="auth")

Logger = get_logger()


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"message": "Unauthorized"}), HTTPStatus.UNAUTHORIZED


@auth_bp.route("/jwt", methods=["GET"])
@auth_bp.auth_required(auth)
@auth_bp.input(JwtTokenQuery, location="query")
@auth_bp.doc(
    responses={
        HTTPStatus.OK: {
            "description": "A JWT to send as a Bearer token.",
            "content": {"text/plain": {"schema": {"type": "string"}}},
        }
    }
)
def jwt_token(query_data):

    expiration_hours = float(
        query_data.get("expiration_hours", Config.TOKEN_EXPIRATION_HOURS)
    )
    if expiration_hours > 200:
        abort(HTTPStatus.BAD_REQUEST, "Expiration hours cannot exceed 200.")
    payload = {
        "sub": current_user.id,  # Subject (User ID)
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=expiration_hours),  # Expiration
        "iat": datetime.datetime.now(datetime.timezone.utc),  # Issued At
    }
    return (
        jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.SECRET_ALGORITHM),
        HTTPStatus.OK,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


@login_manager.request_loader
def load_user_from_request(request):

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(
            token, Config.SECRET_KEY, algorithms=[Config.SECRET_ALGORITHM]
        )
    except jwt.InvalidTokenError:
        return None

    return load_user(payload.get("sub"))


@auth_bp.route("/rlogin", methods=["POST"])
@auth_bp.input(LoginIn)
@auth_bp.output(LoginOut)
def rlogin(json_data):
    """Log in and set the session cookie."""
    req_user = json_data["username"]
    req_password = json_data["password"]
    if (
        not req_user.isalnum()
        or not req_password
        or not req_user
        or len(req_password) > 30
        or len(req_user) > 30
    ):
        abort(HTTPStatus.BAD_REQUEST, "Invalid username/password")
    user = authenticate(req_user, req_password)
    if user:
        login_user(user, remember=True)
        return {"id": user.id, "fullName": user.username}
    abort(HTTPStatus.UNAUTHORIZED, "Invalid credentials")


@auth_bp.route("/profile", methods=["GET"])
@auth_bp.auth_required(auth)
@auth_bp.output(ProfileOut)
def profile():
    """The logged-in user's identity and their (read-only) UserConfig."""
    user_config = UserStore.get_user_config(current_user.id)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "name": current_user.name,
        "email": current_user.email,
        "config": user_config.to_public_dict(),
    }


@auth_bp.route("/password", methods=["POST"])
@auth_bp.auth_required(auth)
@auth_bp.input(PasswordChangeIn)
@auth_bp.output(MessageOut)
def change_password(json_data):
    """Change the logged-in user's own password.

    There is no user id in the request: the only account that can be changed
    is the caller's. The current password is required too, so a stolen
    session cookie or Bearer token isn't enough to take over the account.
    """
    if not current_user.check_password(json_data["currentPassword"]):
        abort(HTTPStatus.FORBIDDEN, "Current password is incorrect.")
    new_password = json_data["newPassword"]
    problem = password_problem(new_password)
    if problem:
        abort(HTTPStatus.BAD_REQUEST, problem)
    if new_password == json_data["currentPassword"]:
        abort(HTTPStatus.BAD_REQUEST, "New password must differ from the current one.")
    try:
        set_password_hash(current_user.id, hash_password(new_password))
    except PasswordStoreError as e:
        Logger.error("Password change for user %s failed: %s", current_user.id, e)
        abort(HTTPStatus.INTERNAL_SERVER_ERROR, "Couldn't save the new password.")
    Logger.info("User %s changed their password", current_user.id)
    return {"message": "Password changed"}


@auth_bp.route("/rlogout", methods=["GET"])
@auth_bp.auth_required(auth)
@auth_bp.output(MessageOut)
def rlogout():
    logout_user()
    return {"message": "Logged out"}


@login_manager.user_loader
def load_user(user_id):
    return find_user_by_id(user_id)


@auth_bp.route("/login", methods=["GET", "POST"])
@auth_bp.doc(hide=True)
def login():
    if request.method == "POST":
        req_user = request.form.get("username", "")
        req_password = request.form.get("password", "")
        if (
            not req_user.isalnum()
            or not req_password
            or not req_user
            or len(req_password) > 30
            or len(req_user) > 30
        ):
            return (
                jsonify({"message": "Invalid username/password"}),
                HTTPStatus.BAD_REQUEST,
            )

        user = authenticate(req_user, req_password)
        if user:
            login_user(user)
            return render_template(
                "custom_report.html", report_data={"contents": "success"}
            )
        else:
            return (
                jsonify({"error": "Invalid username or password"}),
                HTTPStatus.UNAUTHORIZED,
            )
    return render_template("login.html")


@auth_bp.route("/logout")
@auth_bp.doc(hide=True)
@auth_bp.auth_required(auth)
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
