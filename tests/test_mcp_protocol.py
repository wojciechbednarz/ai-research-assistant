from mcp_server.protocol import (
    make_result,
    make_error,
    ERROR_PARSE,
    ERROR_METHOD_NOT_FOUND,
)


def test_make_result_structure():
    r = make_result(id="1", result={"tools": []})
    assert r["jsonrpc"] == "2.0"
    assert r["id"] == "1"
    assert r["result"] == {"tools": []}


def test_make_error_structure():
    r = make_error(id="2", code=ERROR_PARSE, message="parse error")
    assert r["jsonrpc"] == "2.0"
    assert r["id"] == "2"
    assert r["error"]["code"] == ERROR_PARSE
    assert r["error"]["message"] == "parse error"


def test_make_error_codes():
    assert ERROR_PARSE == -32700
    assert ERROR_METHOD_NOT_FOUND == -32601
