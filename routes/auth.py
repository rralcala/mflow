import datetime
from http import HTTPStatus

import jwt
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from init import login_manager
from lib.config import Config
from lib.logger import get_logger
from models.models import User, find_user_by_username

auth_bp = Blueprint("auth", __name__)

ALGORITHM = "HS256"
Logger = get_logger()


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"message": "Unauthorized"}), HTTPStatus.UNAUTHORIZED


@auth_bp.route("/jwt", methods=["GET"])
@login_required
def jwt_token():

    payload = {
        "sub": current_user.id,  # Subject (User ID)
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=1),  # Expiration
        "iat": datetime.datetime.now(datetime.timezone.utc),  # Issued At
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=ALGORITHM), HTTPStatus.OK


@login_manager.request_loader
def load_user_from_request(request):

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None

    return load_user(payload.get("sub"))


@auth_bp.route("/rlogin", methods=["POST"])
def rlogin():
    data = request.json
    req_user = data.get("username", "")
    req_password = data.get("password", "")
    if (
        not req_user.isalnum()
        or not req_password
        or not req_user
        or len(req_password) > 30
        or len(req_user) > 30
    ):
        return jsonify({"message": "Invalid username/password"}), HTTPStatus.BAD_REQUEST
    user = find_user_by_username(req_user)
    if user and user.check_password(req_password):
        login_user(user, remember=True)
        return jsonify({"id": user.id, "fullName": user.username}), HTTPStatus.OK
    return jsonify({"message": "Invalid credentials"}), HTTPStatus.UNAUTHORIZED


@auth_bp.route("/rlogout", methods=["GET"])
@login_required
def rlogout():
    logout_user()
    return jsonify({"message": "Logged out"}), HTTPStatus.OK


@login_manager.user_loader
def load_user(user_id):
    user_data = Config.USERS.get(user_id, None)
    if user_data:
        user = User(
            uid=user_id,
            username=user_data.get("username"),
            name=user_data.get("name"),
            password=user_data.get("password"),
            email=user_data.get("email"),
        )
        return user
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
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

        user = find_user_by_username(req_user)
        if user and user.check_password(req_password):
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
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
