#!/usr/bin/env python3
"""
Document Indexer for Open WebUI via Qdrant

Indexes markdown and text files into Qdrant vector database.
Uses the same embedding model as Open WebUI (all-MiniLM-L6-v2).

Usage:
    # Index once
    python index_docs.py /path/to/docs --collection linuxinfrastructure

    # Watch for changes
    python index_docs.py /path/to/docs --collection linuxinfrastructure --watch
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# File extensions to index
SUPPORTED_EXTENSIONS = {".md", ".txt", ".markdown", ".rst"}


class DocumentIndexer:
    def __init__(self, collection_name: str, qdrant_host: str = QDRANT_HOST, qdrant_port: int = QDRANT_PORT):
        self.collection_name = f"open_webui_{collection_name}"
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.vector_size = self.model.get_sentence_embedding_dimension()
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"Created collection: {self.collection_name}")
        else:
            print(f"Using existing collection: {self.collection_name}")

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - CHUNK_OVERLAP
        return chunks

    def _file_hash(self, filepath: Path) -> str:
        """Generate hash of file content for change detection"""
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_indexed_files(self) -> Dict[str, str]:
        """Get dict of {filepath: hash} for already indexed files"""
        indexed = {}
        try:
            # Scroll through all points to get metadata
            offset = None
            while True:
                results, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                for point in results:
                    if point.payload:
                        filepath = point.payload.get("filepath")
                        filehash = point.payload.get("filehash")
                        if filepath and filehash:
                            indexed[filepath] = filehash
                if offset is None:
                    break
        except Exception as e:
            print(f"Warning: Could not fetch indexed files: {e}")
        return indexed

    def _delete_file_points(self, filepath: str):
        """Delete all points for a given file"""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="filepath",
                        match=MatchValue(value=filepath)
                    )
                ]
            )
        )

    def index_file(self, filepath: Path, force: bool = False) -> bool:
        """Index a single file, returns True if indexed"""
        filepath_str = str(filepath.absolute())

        # Check if file needs indexing
        current_hash = self._file_hash(filepath)
        indexed_files = self._get_indexed_files()

        if not force and filepath_str in indexed_files:
            if indexed_files[filepath_str] == current_hash:
                print(f"  Skipping (unchanged): {filepath.name}")
                return False
            else:
                print(f"  Updating (changed): {filepath.name}")
                self._delete_file_points(filepath_str)
        else:
            print(f"  Indexing (new): {filepath.name}")

        # Read and chunk the file
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"  Error reading {filepath}: {e}")
            return False

        chunks = self._chunk_text(content)
        if not chunks:
            print(f"  Skipping (empty): {filepath.name}")
            return False

        # Generate embeddings
        embeddings = self.model.encode(chunks, show_progress_bar=False)

        # Create points
        points = []
        base_id = int(hashlib.sha256(filepath_str.encode()).hexdigest()[:8], 16)

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = base_id + i
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload={
                        "filepath": filepath_str,
                        "filename": filepath.name,
                        "filehash": current_hash,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "content": chunk,
                        "collection": self.collection_name,
                    }
                )
            )

        # Upsert to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"  Indexed {len(chunks)} chunks from {filepath.name}")
        return True

    def index_directory(self, directory: Path, force: bool = False) -> int:
        """Index all supported files in directory, returns count of indexed files"""
        indexed_count = 0

        for filepath in directory.rglob("*"):
            if filepath.is_file() and filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
                if self.index_file(filepath, force=force):
                    indexed_count += 1

        return indexed_count

    def remove_deleted_files(self, directory: Path):
        """Remove indexed files that no longer exist on disk"""
        indexed_files = self._get_indexed_files()
        directory_str = str(directory.absolute())

        for filepath_str in indexed_files:
            if filepath_str.startswith(directory_str):
                if not Path(filepath_str).exists():
                    print(f"  Removing (deleted): {Path(filepath_str).name}")
                    self._delete_file_points(filepath_str)

    def get_stats(self) -> dict:
        """Get collection statistics"""
        info = self.client.get_collection(self.collection_name)
        return {
            "collection": self.collection_name,
            "points_count": info.points_count,
        }


def watch_directory(indexer: DocumentIndexer, directory: Path, interval: int = 30):
    """Watch directory for changes and re-index"""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class IndexHandler(FileSystemEventHandler):
        def __init__(self):
            self.pending_files = set()
            self.last_process = 0

        def _should_process(self, path: str) -> bool:
            return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

        def on_created(self, event):
            if not event.is_directory and self._should_process(event.src_path):
                self.pending_files.add(event.src_path)

        def on_modified(self, event):
            if not event.is_directory and self._should_process(event.src_path):
                self.pending_files.add(event.src_path)

        def on_deleted(self, event):
            if not event.is_directory and self._should_process(event.src_path):
                print(f"  Removing: {Path(event.src_path).name}")
                indexer._delete_file_points(event.src_path)

    handler = IndexHandler()
    observer = Observer()
    observer.schedule(handler, str(directory), recursive=True)
    observer.start()

    print(f"\nWatching {directory} for changes (Ctrl+C to stop)...")

    try:
        while True:
            time.sleep(interval)
            if handler.pending_files:
                print(f"\nProcessing {len(handler.pending_files)} changed files...")
                for filepath_str in list(handler.pending_files):
                    filepath = Path(filepath_str)
                    if filepath.exists():
                        indexer.index_file(filepath, force=True)
                handler.pending_files.clear()
                stats = indexer.get_stats()
                print(f"Total indexed: {stats['points_count']} chunks")
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    parser = argparse.ArgumentParser(description="Index documents into Qdrant for Open WebUI")
    parser.add_argument("directory", type=Path, help="Directory containing documents to index")
    parser.add_argument("--collection", "-c", required=True, help="Collection name (e.g., linuxinfrastructure)")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch for file changes")
    parser.add_argument("--force", "-f", action="store_true", help="Force re-index all files")
    parser.add_argument("--host", default=QDRANT_HOST, help=f"Qdrant host (default: {QDRANT_HOST})")
    parser.add_argument("--port", type=int, default=QDRANT_PORT, help=f"Qdrant port (default: {QDRANT_PORT})")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval in seconds (default: 30)")

    args = parser.parse_args()

    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}")
        sys.exit(1)

    print(f"Document Indexer for Open WebUI")
    print(f"================================")
    print(f"Directory: {args.directory}")
    print(f"Collection: open_webui_{args.collection}")
    print(f"Qdrant: {args.host}:{args.port}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print()

    indexer = DocumentIndexer(
        collection_name=args.collection,
        qdrant_host=args.host,
        qdrant_port=args.port
    )

    # Initial indexing
    print("Scanning directory...")
    indexed = indexer.index_directory(args.directory, force=args.force)
    indexer.remove_deleted_files(args.directory)

    stats = indexer.get_stats()
    print(f"\nIndexing complete: {indexed} files, {stats['points_count']} total chunks")

    if args.watch:
        watch_directory(indexer, args.directory, interval=args.interval)


if __name__ == "__main__":
    main()
