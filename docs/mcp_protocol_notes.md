# MCP Protocol Notes

## Overview

**Model Context Protocol (MCP)** is an open protocol (by Anthropic) that standardizes how LLM-based applications connect to external tools, resources, and data sources. MCP is built **on top of JSON-RPC 2.0** — every MCP message is a valid JSON-RPC 2.0 message.

---

## Transports

MCP supports two official transport types:

| Transport | Description |
|-----------|-------------|
| **stdio** | Client spawns the server as a subprocess; communication over stdin/stdout. Common for local tools. |
| **Streamable HTTP** | Server exposes an HTTP endpoint. Supports both request/response and server-sent events (SSE) for streaming. Used for remote servers. |

---

## Connection Lifecycle

```
Client                         Server
  |-- initialize ------------>  |   (sends client capabilities + protocol version)
  |<-- result (capabilities) -- |
  |-- notifications/initialized>|   (client signals ready)
  |                             |
  |  ... normal operation ...   |
  |                             |
  |-- (close connection) -----> |
```

### `initialize` request

```json
--> {
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {}
    },
    "clientInfo": { "name": "my-client", "version": "1.0.0" }
  }
}

<-- {
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": {},
      "prompts": {}
    },
    "serverInfo": { "name": "my-server", "version": "1.0.0" }
  }
}
```

---

## Core Primitives

### Tools (`tools/list`, `tools/call`)

Server-exposed functions the LLM can invoke.

```json
--> {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
<-- {
  "jsonrpc": "2.0", "id": 2,
  "result": {
    "tools": [{
      "name": "get_weather",
      "description": "Returns current weather for a city.",
      "inputSchema": {
        "type": "object",
        "properties": { "city": { "type": "string" } },
        "required": ["city"]
      }
    }]
  }
}

--> {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_weather", "arguments": {"city": "Warsaw"}}}
<-- {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "15°C, partly cloudy"}], "isError": false}}
```

### Resources (`resources/list`, `resources/read`)

Read-only data the server exposes (files, DB records, API responses).

```json
--> {"jsonrpc": "2.0", "id": 4, "method": "resources/list"}
--> {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": "file:///data/notes.txt"}}
```

### Prompts (`prompts/list`, `prompts/get`)

Reusable prompt templates with optional arguments.

```json
--> {"jsonrpc": "2.0", "id": 6, "method": "prompts/list"}
--> {"jsonrpc": "2.0", "id": 7, "method": "prompts/get", "params": {"name": "summarize", "arguments": {"style": "bullet"}}}
```

---

## Notifications (server → client)

MCP uses JSON-RPC notifications (no `id`) to signal list changes:

```json
{"jsonrpc": "2.0", "method": "notifications/tools/list_changed"}
{"jsonrpc": "2.0", "method": "notifications/resources/list_changed"}
{"jsonrpc": "2.0", "method": "notifications/prompts/list_changed"}
```

---

## MCP Error Codes (in addition to JSON-RPC standard codes)

| Code | Meaning |
|------|---------|
| `-32700` | Parse error (JSON-RPC) |
| `-32600` | Invalid Request (JSON-RPC) |
| `-32601` | Method not found (JSON-RPC) |
| `-32602` | Invalid params (JSON-RPC) |
| `-32603` | Internal error (JSON-RPC) |

> MCP does not define additional numeric error codes beyond JSON-RPC 2.0. Application-level errors are returned inside `result.isError = true` for tool calls, not as JSON-RPC error responses.

---

# JSON-RPC 2.0 Specification (reference)

JSON-RPC is a stateless, light-weight remote procedure call (RPC) protocol. Primarily this specification defines several data structures and the rules around their processing. It is transport agnostic in that the concepts can be used within the same process, over sockets, over http, or in many various message passing environments. It uses JSON (RFC 4627) as data format.


## Request object members

- **jsonrpc** — A String specifying the version of the JSON-RPC protocol. MUST be exactly `"2.0"`.
- **method** — A String containing the name of the method to be invoked. Method names that begin with the word `rpc` followed by a period character (U+002E or ASCII 46) are reserved for rpc-internal methods and extensions and MUST NOT be used for anything else.
- **params** — A Structured value that holds the parameter values to be used during the invocation of the method. This member MAY be omitted.
- **id** — An identifier established by the Client that MUST contain a String, Number, or NULL value.

## Examples

Syntax:

```
--> data sent to Server
<-- data sent to Client
```

### rpc call with positional parameters

```json
--> {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}
<-- {"jsonrpc": "2.0", "result": 19, "id": 1}

--> {"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}
<-- {"jsonrpc": "2.0", "result": -19, "id": 2}
```

### rpc call with named parameters

```json
--> {"jsonrpc": "2.0", "method": "subtract", "params": {"subtrahend": 23, "minuend": 42}, "id": 3}
<-- {"jsonrpc": "2.0", "result": 19, "id": 3}

--> {"jsonrpc": "2.0", "method": "subtract", "params": {"minuend": 42, "subtrahend": 23}, "id": 4}
<-- {"jsonrpc": "2.0", "result": 19, "id": 4}
```

### a Notification

```json
--> {"jsonrpc": "2.0", "method": "update", "params": [1,2,3,4,5]}
--> {"jsonrpc": "2.0", "method": "foobar"}
```

### rpc call of non-existent method

```json
--> {"jsonrpc": "2.0", "method": "foobar", "id": "1"}
<-- {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "1"}
```

### rpc call with invalid JSON

```json
--> {"jsonrpc": "2.0", "method": "foobar, "params": "bar", "baz]
<-- {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": null}
```

### rpc call with invalid Request object

```json
--> {"jsonrpc": "2.0", "method": 1, "params": "bar"}
<-- {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}
```

---

## Building a Raw Stdio MCP Server (No SDK)

Since stdio transport is just newline-delimited JSON-RPC over stdin/stdout, you can implement an MCP server from scratch in any language.

### How stdio transport works

The MCP client (e.g. Claude Code) **spawns your server as a child process** and communicates via pipes:

```
Client  ──stdin──►  Your Server Process
        ◄─stdout──
```

Your server loops over stdin line by line, parses each line as JSON-RPC, and writes responses to stdout.

### Critical rules

- **stdout is the wire** — never write anything to stdout except JSON-RPC responses. All debug/log output must go to stderr.
- **Always flush** stdout after every write.
- **Notifications** (messages with no `id`) require no response.
- **Every request** (has an `id`) must get a response — either `result` or `error`.

### Minimal Python implementation

```python
import sys
import json

def send(msg: dict):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def handle(msg: dict):
    method = msg.get("method")
    id_ = msg.get("id")  # None for notifications

    if method == "initialize":
        send({
            "jsonrpc": "2.0", "id": id_,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "my-server", "version": "0.1.0"}
            }
        })

    elif method == "initialized":
        pass  # notification — no response

    elif method == "tools/list":
        send({
            "jsonrpc": "2.0", "id": id_,
            "result": {"tools": [
                {
                    "name": "hello",
                    "description": "Says hello",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"]
                    }
                }
            ]}
        })

    elif method == "tools/call":
        args = msg["params"]["arguments"]
        send({
            "jsonrpc": "2.0", "id": id_,
            "result": {
                "content": [{"type": "text", "text": f"Hello, {args['name']}!"}],
                "isError": False
            }
        })

    elif id_ is not None:
        # Unknown method with an id — must respond with error
        send({
            "jsonrpc": "2.0", "id": id_,
            "error": {"code": -32601, "message": "Method not found"}
        })

for line in sys.stdin:
    line = line.strip()
    if line:
        try:
            handle(json.loads(line))
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
```

### Wiring it into Claude Code

Add to `.claude/settings.json` (or `settings.local.json`):

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

Claude Code spawns the process on startup and kills it on exit — you never run it manually.

### Application-level tool errors

Tool execution errors (e.g. "city not found") are **not** JSON-RPC errors. Return them inside `result` with `isError: true`:

```json
<-- {
  "jsonrpc": "2.0", "id": 3,
  "result": {
    "content": [{"type": "text", "text": "City not found"}],
    "isError": true
  }
}
```

Only use JSON-RPC `error` responses for protocol-level failures (unknown method, invalid params, parse errors).