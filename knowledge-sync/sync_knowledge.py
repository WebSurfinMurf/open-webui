#!/usr/bin/env python3
"""
Knowledge Sync for Open WebUI

Reads .md definition files from a knowledge directory and syncs
referenced documents to Open WebUI Knowledge collections via API.

Each .md file becomes a Knowledge collection (filename = collection name).
Inside each .md, list file paths or folder paths to include.

Usage:
    python sync_knowledge.py                    # One-time sync
    python sync_knowledge.py --watch            # Watch for changes
    python sync_knowledge.py --force            # Force re-upload all
    python sync_knowledge.py --dry-run          # Show what would happen
"""

import argparse
import fnmatch
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

# Configuration
OPEN_WEBUI_URL = os.getenv("OPEN_WEBUI_URL", "http://localhost:8000")
API_KEY = os.getenv("OPEN_WEBUI_API_KEY", "")
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "/home/administrator/projects/open-webui/docs/knowledge")
CACHE_FILE = os.getenv("CACHE_FILE", "/home/administrator/projects/open-webui/knowledge-sync/.sync_cache.json")
CONFIG_FILE = "config.md"

# Defaults if config.md doesn't exist
DEFAULT_EXTENSIONS = {".md", ".txt", ".rst", ".yaml", ".yml", ".json"}
DEFAULT_EXCLUDES = ["**/node_modules/**", "**/.git/**", "**/__pycache__/**"]


class KnowledgeSync:
    def __init__(self, knowledge_dir: str, api_url: str, api_key: str, cache_file: str):
        self.knowledge_dir = Path(knowledge_dir)
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.cache_file = Path(cache_file)
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.extensions: Set[str] = set()
        self.excludes: List[str] = []
        self.cache: Dict = {}
        self._load_config()
        self._load_cache()

    def _load_config(self):
        """Load config.md for extensions and exclude patterns."""
        config_path = self.knowledge_dir / CONFIG_FILE
        if not config_path.exists():
            print(f"No config.md found, using defaults")
            self.extensions = DEFAULT_EXTENSIONS
            self.excludes = DEFAULT_EXCLUDES
            return

        content = config_path.read_text()
        section = None
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("## Extensions"):
                section = "extensions"
            elif line.startswith("## Exclude"):
                section = "excludes"
            elif line.startswith("#") or not line:
                continue
            elif section == "extensions" and line.startswith("."):
                self.extensions.add(line)
            elif section == "excludes":
                self.excludes.append(line)

        if not self.extensions:
            self.extensions = DEFAULT_EXTENSIONS
        if not self.excludes:
            self.excludes = DEFAULT_EXCLUDES

        print(f"Config: {len(self.extensions)} extensions, {len(self.excludes)} exclude patterns")

    def _load_cache(self):
        """Load sync cache from disk."""
        if self.cache_file.exists():
            try:
                self.cache = json.loads(self.cache_file.read_text())
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self):
        """Save sync cache to disk."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache, indent=2))

    def _file_hash(self, path: Path) -> str:
        """Generate hash of file content."""
        try:
            content = path.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return ""

    def _is_excluded(self, path: Path) -> bool:
        """Check if path matches any exclude pattern."""
        path_str = str(path)
        for pattern in self.excludes:
            if fnmatch.fnmatch(path_str, pattern):
                return True
        return False

    def _translate_path(self, path_str: str) -> str:
        """Translate path using PATH_PREFIX_MAP env var if set."""
        prefix_map = os.getenv("PATH_PREFIX_MAP", "")
        if prefix_map and ":" in prefix_map:
            from_prefix, to_prefix = prefix_map.split(":", 1)
            if path_str.startswith(from_prefix):
                return path_str.replace(from_prefix, to_prefix, 1)
        return path_str

    def _resolve_path(self, path_str: str) -> List[Path]:
        """Resolve a path (file, folder, or symlink) to list of files."""
        # Apply path translation (for host vs container differences)
        translated = self._translate_path(path_str.strip())
        path = Path(translated)

        # Resolve symlinks
        if path.is_symlink():
            path = path.resolve()

        if not path.exists():
            print(f"  Warning: Path does not exist: {path_str}")
            return []

        files = []
        if path.is_file():
            if path.suffix.lower() in self.extensions and not self._is_excluded(path):
                files.append(path)
        elif path.is_dir():
            for item in path.rglob("*"):
                if item.is_file() and item.suffix.lower() in self.extensions:
                    if not self._is_excluded(item):
                        files.append(item)

        return files

    def _parse_definition(self, md_path: Path) -> List[Path]:
        """Parse a .md definition file and return list of files to index."""
        files = []
        content = md_path.read_text()

        for line in content.splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Resolve the path
            resolved = self._resolve_path(line)
            files.extend(resolved)

        return files

    def _get_knowledge_bases(self) -> Dict[str, str]:
        """Get existing knowledge bases {name: id}."""
        try:
            resp = requests.get(f"{self.api_url}/api/v1/knowledge/", headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            # API returns {"items": [...], "total": N}
            items = data.get("items", []) if isinstance(data, dict) else data
            return {kb["name"]: kb["id"] for kb in items}
        except Exception as e:
            print(f"Error fetching knowledge bases: {e}")
            return {}

    def _create_knowledge_base(self, name: str, description: str = "") -> Optional[str]:
        """Create a new knowledge base, return its ID."""
        try:
            resp = requests.post(
                f"{self.api_url}/api/v1/knowledge/create",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"name": name, "description": description}
            )
            resp.raise_for_status()
            return resp.json()["id"]
        except Exception as e:
            print(f"Error creating knowledge base '{name}': {e}")
            return None

    def _get_knowledge_files(self, kb_id: str) -> Dict[str, str]:
        """Get files in a knowledge base {filename: file_id}."""
        try:
            # Use the /files endpoint which actually returns file data
            resp = requests.get(f"{self.api_url}/api/v1/knowledge/{kb_id}/files", headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", []) or []
            return {f["filename"]: f["id"] for f in items if f.get("filename")}
        except Exception as e:
            print(f"Error fetching knowledge files: {e}")
            return {}

    def _upload_file(self, file_path: Path) -> Optional[str]:
        """Upload a file to Open WebUI, return file ID."""
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f)}
                resp = requests.post(
                    f"{self.api_url}/api/v1/files/",
                    headers=self.headers,
                    files=files
                )
                resp.raise_for_status()
                return resp.json()["id"]
        except Exception as e:
            print(f"  Error uploading {file_path.name}: {e}")
            return None

    def _clear_qdrant_duplicates(self, file_hash: str) -> bool:
        """Clear duplicate vectors from Qdrant knowledge collection by hash.

        This is a workaround for Open WebUI bug where duplicate content detection
        prevents adding files even after deletion. The vectors remain in Qdrant.
        See: https://github.com/open-webui/open-webui/issues/20853
        """
        qdrant_url = os.getenv("QDRANT_URI", "http://localhost:6333")
        collections = ["open-webui_knowledge", "open-webui_files"]

        for collection in collections:
            try:
                resp = requests.post(
                    f"{qdrant_url}/collections/{collection}/points/delete",
                    json={"filter": {"must": [{"key": "metadata.hash", "match": {"value": file_hash}}]}}
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("status") == "ok":
                        continue
            except Exception:
                pass  # Collection might not exist
        return True

    def _add_file_to_knowledge(self, kb_id: str, file_id: str, file_hash: str = None) -> bool:
        """Add an uploaded file to a knowledge base."""
        try:
            resp = requests.post(
                f"{self.api_url}/api/v1/knowledge/{kb_id}/file/add",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"file_id": file_id}
            )
            resp.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            # Check if it's a duplicate content error
            if resp.status_code == 400 and "Duplicate content" in resp.text:
                if file_hash:
                    # Try to clear duplicates from Qdrant and retry
                    print(f"  Clearing duplicate vectors...")
                    self._clear_qdrant_duplicates(file_hash)
                    try:
                        resp = requests.post(
                            f"{self.api_url}/api/v1/knowledge/{kb_id}/file/add",
                            headers={**self.headers, "Content-Type": "application/json"},
                            json={"file_id": file_id}
                        )
                        resp.raise_for_status()
                        return True
                    except Exception:
                        pass
                print(f"  Warning: Duplicate content - may already exist in knowledge")
                return False
            print(f"  Error adding file to knowledge: {e} - {resp.text}")
            return False
        except Exception as e:
            print(f"  Error adding file to knowledge: {e}")
            return False

    def _update_knowledge_files(self, kb_id: str, name: str, file_ids: List[str]) -> bool:
        """Update knowledge base with file_ids using the update endpoint."""
        try:
            resp = requests.post(
                f"{self.api_url}/api/v1/knowledge/{kb_id}/update",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"name": name, "description": "", "file_ids": file_ids}
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"  Error updating knowledge files: {e}")
            return False

    def _remove_file_from_knowledge(self, kb_id: str, file_id: str) -> bool:
        """Remove a file from a knowledge base."""
        try:
            resp = requests.post(
                f"{self.api_url}/api/v1/knowledge/{kb_id}/file/remove",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"file_id": file_id}
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"  Error removing file from knowledge: {e}")
            return False

    def sync_collection(self, md_path: Path, force: bool = False, dry_run: bool = False) -> Tuple[int, int, int]:
        """Sync a single knowledge collection. Returns (added, updated, removed)."""
        collection_name = md_path.stem  # Filename without .md
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Syncing: {collection_name}")

        # Parse the definition file
        files_to_sync = self._parse_definition(md_path)
        print(f"  Found {len(files_to_sync)} files to sync")

        if not files_to_sync:
            return (0, 0, 0)

        # Get or create knowledge base
        knowledge_bases = self._get_knowledge_bases()
        kb_id = knowledge_bases.get(collection_name)

        if not kb_id:
            print(f"  Creating knowledge base: {collection_name}")
            if not dry_run:
                kb_id = self._create_knowledge_base(collection_name)
                if not kb_id:
                    return (0, 0, 0)
            else:
                kb_id = "dry-run-id"

        # Get existing files in the knowledge base
        existing_files = {} if dry_run else self._get_knowledge_files(kb_id)

        # Track what we're syncing
        cache_key = collection_name
        if cache_key not in self.cache:
            self.cache[cache_key] = {}
        collection_cache = self.cache[cache_key]

        added, updated, removed = 0, 0, 0
        synced_filenames = set()

        # Process each file
        for file_path in files_to_sync:
            filename = file_path.name
            file_hash = self._file_hash(file_path)
            synced_filenames.add(filename)

            cached_hash = collection_cache.get(filename, {}).get("hash")
            cached_file_id = collection_cache.get(filename, {}).get("file_id")

            # If file unchanged and we have a cached file_id, skip
            if not force and cached_hash == file_hash and cached_file_id and filename in existing_files:
                continue

            action = "Adding" if filename not in existing_files else "Updating"
            print(f"  {action}: {filename}")

            if not dry_run:
                # Get file content hash for dedup clearing
                content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

                # Clear any duplicate vectors before upload
                self._clear_qdrant_duplicates(content_hash)

                # Upload file
                file_id = self._upload_file(file_path)
                if not file_id:
                    continue

                # Wait briefly for processing
                time.sleep(0.5)

                # Add to knowledge base
                if self._add_file_to_knowledge(kb_id, file_id, content_hash):
                    collection_cache[filename] = {"hash": file_hash, "file_id": file_id}
                    if filename in existing_files:
                        updated += 1
                    else:
                        added += 1
                else:
                    print(f"    Failed to add {filename} to knowledge")
            else:
                if filename in existing_files:
                    updated += 1
                else:
                    added += 1

        # Count and remove files no longer in definition
        for filename, file_id in existing_files.items():
            if filename not in synced_filenames:
                print(f"  Removing: {filename}")
                if not dry_run:
                    self._remove_file_from_knowledge(kb_id, file_id)
                if filename in collection_cache:
                    del collection_cache[filename]
                removed += 1

        if not dry_run:
            self._save_cache()

        return (added, updated, removed)

    def sync_all(self, force: bool = False, dry_run: bool = False):
        """Sync all knowledge collections."""
        print(f"Knowledge Sync for Open WebUI")
        print(f"==============================")
        print(f"Knowledge dir: {self.knowledge_dir}")
        print(f"API URL: {self.api_url}")

        if not self.api_key:
            print("\nError: OPEN_WEBUI_API_KEY environment variable not set")
            print("Create an API key in Open WebUI: Settings → Account → API Keys")
            sys.exit(1)

        # Find all .md definition files (except config.md)
        md_files = [
            f for f in self.knowledge_dir.glob("*.md")
            if f.name.lower() != CONFIG_FILE.lower()
        ]

        if not md_files:
            print(f"\nNo knowledge definition files found in {self.knowledge_dir}")
            return

        print(f"Found {len(md_files)} knowledge collections")

        total_added, total_updated, total_removed = 0, 0, 0
        for md_file in md_files:
            added, updated, removed = self.sync_collection(md_file, force=force, dry_run=dry_run)
            total_added += added
            total_updated += updated
            total_removed += removed

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Summary: {total_added} added, {total_updated} updated, {total_removed} removed")

    def watch(self, interval: int = 60):
        """Watch for changes and sync periodically."""
        print(f"\nWatching for changes every {interval} seconds (Ctrl+C to stop)...")

        last_check = {}

        while True:
            try:
                # Check each .md file for changes
                md_files = [
                    f for f in self.knowledge_dir.glob("*.md")
                    if f.name.lower() != CONFIG_FILE.lower()
                ]

                for md_file in md_files:
                    # Check if definition file changed
                    current_mtime = md_file.stat().st_mtime
                    if md_file.name in last_check:
                        if current_mtime > last_check[md_file.name]:
                            print(f"\n[{time.strftime('%H:%M:%S')}] Definition changed: {md_file.name}")
                            self.sync_collection(md_file)
                    else:
                        # First run, sync all
                        self.sync_collection(md_file)

                    last_check[md_file.name] = current_mtime

                    # Also check source files
                    files_to_sync = self._parse_definition(md_file)
                    collection_name = md_file.stem
                    collection_cache = self.cache.get(collection_name, {})

                    for file_path in files_to_sync:
                        current_hash = self._file_hash(file_path)
                        cached_hash = collection_cache.get(file_path.name, {}).get("hash")

                        if cached_hash and current_hash != cached_hash:
                            print(f"\n[{time.strftime('%H:%M:%S')}] Source changed: {file_path.name}")
                            self.sync_collection(md_file)
                            break

                time.sleep(interval)

            except KeyboardInterrupt:
                print("\nStopping watch...")
                break


def main():
    parser = argparse.ArgumentParser(description="Sync knowledge to Open WebUI")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch for changes")
    parser.add_argument("--interval", "-i", type=int, default=60, help="Watch interval in seconds")
    parser.add_argument("--force", "-f", action="store_true", help="Force re-upload all files")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would happen")
    parser.add_argument("--dir", "-d", default=KNOWLEDGE_DIR, help="Knowledge directory")
    parser.add_argument("--url", "-u", default=OPEN_WEBUI_URL, help="Open WebUI URL")

    args = parser.parse_args()

    api_key = os.getenv("OPEN_WEBUI_API_KEY", "")

    syncer = KnowledgeSync(
        knowledge_dir=args.dir,
        api_url=args.url,
        api_key=api_key,
        cache_file=CACHE_FILE
    )

    if args.watch:
        syncer.sync_all(force=args.force, dry_run=args.dry_run)
        syncer.watch(interval=args.interval)
    else:
        syncer.sync_all(force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
