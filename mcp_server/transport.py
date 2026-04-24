import sys
import json
from typing import Callable
from .protocol import make_error, ERROR_PARSE, ERROR_INVALID_REQUEST, ERROR_INTERNAL
from helpers import parse_message


def run_server(handler_fn: Callable) -> None:
    """JSON-RPC stdin/stdout server loop. Validates message shape before dispatching."""
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(
                json.dumps(make_error(None, ERROR_PARSE, "Parse error")) + "\n"
            )
            sys.stdout.flush()
            continue
        try:
            parse_message(request)
        except ValueError as err:
            sys.stdout.write(
                json.dumps(
                    make_error(request.get("id"), ERROR_INVALID_REQUEST, str(err))
                )
                + "\n"
            )
            sys.stdout.flush()
            continue
        try:
            response = handler_fn(request)
        except Exception as err:
            sys.stdout.write(
                json.dumps(make_error(request.get("id"), ERROR_INTERNAL, str(err)))
                + "\n"
            )
            sys.stdout.flush()
            continue
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
