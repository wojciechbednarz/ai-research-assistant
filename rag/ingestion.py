from config import settings
import chromadb
from chromadb.api import Collection
from display import print_header, print_success, print_info
from helpers import get_markdown_content, chunk_text
from pathlib import Path


class ChromaDB:
    """Handles interactions with the ChromaDB vector database."""

    def __init__(self, collection_name: str) -> None:
        """Initializes the ChromaDB client and collection."""
        self.chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST, port=settings.CHROMA_PORT
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name
        )

    def count_collection(self, collection_name: str) -> int:
        """Returns the number of documents in the collection."""
        collection = self.chroma_client.get_collection(name=collection_name)
        return collection.count()

    def ingest_data(
        self, collection: Collection, file: Path, chunks: list[str]
    ) -> None:
        """Ingests data into the ChromaDB collection."""
        print_header("Ingesting")
        collection.upsert(
            ids=[f"{file.stem}_chunk{i}" for i in range(len(chunks))], documents=chunks
        )
        print_success("Done")

    def load_document(self, file_path: Path) -> None:
        print_header("Loading Document")
        content = get_markdown_content(file_path)
        print_info(f"Loaded {len(content)} chars")
        print_info(f"Content preview:\n{content[:200]}...")

    def load_and_ingest(self, file_path: list[Path], collection: Collection) -> None:
        for file in file_path:
            print_header(f"Processing {file.name}")
            content = get_markdown_content(file)
            print_info(f"Loaded {len(content)} chars")
            print_info(f"Content preview:\n{content[:200]}...")
            chunks = chunk_text(content)
            self.ingest_data(collection, file, chunks)
