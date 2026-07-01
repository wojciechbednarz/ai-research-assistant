import logging
from pathlib import Path

import chromadb
from chromadb.api import Collection

from config import get_settings
from helpers import chunk_text, get_markdown_content

logger = logging.getLogger(__name__)


class ChromaDB:
    """Handles interactions with the ChromaDB vector database."""

    def __init__(self, collection_name: str) -> None:
        self.chroma_client = chromadb.HttpClient(
            host=get_settings().CHROMA_HOST, port=get_settings().CHROMA_PORT
        )
        self.collection = self.chroma_client.get_or_create_collection(name=collection_name)

    def count_collection(self, collection_name: str) -> int:
        collection = self.chroma_client.get_collection(name=collection_name)
        return collection.count()

    def ingest_data(self, collection: Collection, file: Path, chunks: list[str]) -> None:
        logger.debug("Ingesting %s (%d chunks)", file.stem, len(chunks))
        collection.upsert(
            ids=[f"{file.stem}_chunk{i}" for i in range(len(chunks))], documents=chunks
        )
        logger.debug("Ingested %s", file.stem)

    def load_document(self, file_path: Path) -> None:
        content = get_markdown_content(file_path)
        logger.debug("Loaded %s: %d chars", file_path.name, len(content))

    def load_and_ingest(self, file_path: list[Path], collection: Collection) -> None:
        for file in file_path:
            logger.debug("Processing %s", file.name)
            content = get_markdown_content(file)
            logger.debug("Loaded %d chars from %s", len(content), file.name)
            chunks = chunk_text(content)
            if not chunks:
                continue
            self.ingest_data(collection, file, chunks)
