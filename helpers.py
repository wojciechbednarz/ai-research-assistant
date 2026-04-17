from pathlib import Path


def get_file_content(file_path: Path) -> str:
    """Reads the content of a file and returns it as a string."""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def get_markdown_content(file_path: Path) -> str:
    """
    Reads a markdown file and extracts the main content.
    Assumes the content is between the second and third '---' delimiters.
    """
    content = get_file_content(file_path)
    parts = content.split("---")
    if len(parts) >= 3:
        return parts[2].strip()
    return content.strip()


def get_all_files_from_dir(directory: Path) -> list[Path]:
    """Returns a list of all files in the given directory."""
    return [file for file in directory.iterdir() if file.is_file()]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """
    Splits the input text into chunks of a specified size with optional overlap.
    :text: The input text to be chunked.
    :chunk_size: The maximum size of each chunk.
    :overlap: The number of characters to overlap between chunks.
    :return: A list of text chunks.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
