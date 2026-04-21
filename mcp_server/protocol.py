from typing import Any


ERROR_PARSE = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INTERNAL = -32603


def make_result(id: str, result: Any) -> dict:
    """
    Helper function to create a JSON-RPC response.
    :id: The ID of the request this is responding to.
    :result: The result of the request.
    :returns: A dict representing the JSON-RPC response.
    """
    return {"jsonrpc": "2.0", "id": id, "result": result}


def make_error(id: str, code: int, message: str) -> dict:
    """Helper function to create a JSON-RPC error response.
    :id: The ID of the request this is responding to.
    :code: The error code (e.g. -32700 for parse error).
    :message: A human-readable error message.
    :returns: A dict representing the JSON-RPC error response.
    """
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}
