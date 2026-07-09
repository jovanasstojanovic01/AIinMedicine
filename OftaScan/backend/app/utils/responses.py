from flask import jsonify


def ok(data=None, message="Success", status=200):
    payload = {"status": "success", "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def created(data=None, message="Created"):
    return ok(data, message, 201)


def error(message="An error occurred", status=400, details=None):
    payload = {"status": "error", "message": message}
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status


def not_found(resource="Resource"):
    return error(f"{resource} not found.", 404)


def conflict(message="Conflict."):
    return error(message, 409)


def server_error(message="Internal server error.", details=None):
    return error(message, 500, details)