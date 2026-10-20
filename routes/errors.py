from http import HTTPStatus

from apiflask import APIFlask, HTTPError
from flask import current_app


def validation_message(detail: dict) -> str:
    """One "field: problem" line per invalid field, from a validation error's detail.

    The detail is keyed by location (json, query, files) and then by field;
    nested fields are joined with dots, e.g. "transactions.0.amount".
    """
    problems = []

    def walk(messages, path):
        if isinstance(messages, dict):
            for key, value in messages.items():
                walk(value, path if key == "_schema" else [*path, str(key)])
        else:
            if isinstance(messages, list):
                messages = " ".join(str(message) for message in messages)
            problems.append(f"{'.'.join(path)}: {messages}" if path else messages)

    for messages in detail.values():
        walk(messages, [])
    return "; ".join(problems)


def error_body(error: HTTPError):
    """APIFlask's default error body, but a validation error's message names the
    fields, since react-admin shows only the message."""
    message = error.message
    if error.detail and message == current_app.config["VALIDATION_ERROR_DESCRIPTION"]:
        message = validation_message(error.detail)
    body = {"detail": error.detail, "message": message, **error.extra_data}
    return body, error.status_code, error.headers


def configure_errors(app: APIFlask) -> None:
    # 400, like the routes' own input checks, rather than APIFlask's 422.
    app.config["VALIDATION_ERROR_STATUS_CODE"] = HTTPStatus.BAD_REQUEST.value
    app.error_processor(error_body)
