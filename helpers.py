from pathlib import Path
import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def get_file_content(file_path: Path) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def get_markdown_content(file_path: Path) -> str:
    """Extracts content between the second and third '---' YAML front-matter delimiters."""
    content = get_file_content(file_path)
    parts = content.split("---")
    if len(parts) >= 3:
        return parts[2].strip()
    return content.strip()


def get_all_files_from_dir(directory: Path) -> list[Path]:
    return [file for file in directory.iterdir() if file.is_file()]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
        )
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def parse_message(message: dict) -> dict:
    parsed = {}
    if "jsonrpc" not in message:
        raise ValueError("Missing 'jsonrpc' field in the message.")
    if message["jsonrpc"] != "2.0":
        raise ValueError("Unsupported JSON-RPC version. Expected '2.0'.")
    parsed["id"] = message.get("id")
    if "method" not in message:
        raise ValueError("Missing 'method' field in the message.")
    if not isinstance(message["method"], str):
        raise ValueError("'method' field must be a string.")
    parsed["method"] = message["method"]
    parsed["is_notification"] = "id" not in message
    if "params" in message:
        parsed["params"] = message["params"]
    return parsed


def estimate_tokens(text: str) -> int:
    return len(_enc.encode(text))


def truncate_to_budget(docs: list[str], max_tokens: int) -> str:
    result = []
    total = 0
    for doc in docs:
        tokens = estimate_tokens(doc)
        if total + tokens > max_tokens:
            break
        result.append(doc)
        total += tokens
    return "\n\n---\n\n".join(result)
