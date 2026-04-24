import subprocess
import json
import sys

requests = [
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
    },
    {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
    {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "get_metadata", "arguments": {}},
    },
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "search_documents", "arguments": {"query": "what is RAG?"}},
    },
]

input_data = "\n".join(json.dumps(r) for r in requests) + "\n"

result = subprocess.run(
    [sys.executable, "-m", "mcp_server.server"],
    input=input_data,
    capture_output=True,
    text=True,
)
print(result.stdout)
print(result.stderr)
