import sys
import json
from typing import Callable
from .protocol import make_error, ERROR_PARSE


# stdin looks like:
# {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "search_documents", "arguments": {"query": "weather"}}}


def run_server(handler_fn: Callable) -> None:
    """Runs a simple JSON-RPC server that reads requests from stdin and writes responses to stdout.
    :handler_fn: A callable that takes a JSON-RPC request and returns a JSON-RPC response.
    :returns: None
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            break
        try:
            request = json.loads(line)
        except json.JSONDecodeError as err:
            error_response = make_error(None, ERROR_PARSE, "Parse error")
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
            continue
        response = handler_fn(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
