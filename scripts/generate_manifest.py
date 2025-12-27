#!/usr/bin/env python3
"""
Manifest Generator
==================

Generates manifest.json with:
- Version number
- Build timestamp
- Source hash
- Entry counts per category
- File hashes for verification

Usage:
    python scripts/generate_manifest.py --output generated/manifest.json --version 1.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_category_counts(db_path: Path) -> dict[str, int]:
    """Get entry counts per category from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT category, COUNT(*) FROM entries GROUP BY category ORDER BY category"
    )
    counts = dict(cursor.fetchall())
    conn.close()
    return counts


def get_total_entries(db_path: Path) -> int:
    """Get total entry count from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def generate_manifest(
    output_path: Path,
    version: str,
    source_hash: str,
    model: str,
    generated_dir: Path,
) -> dict:
    """Generate manifest.json."""
    db_path = generated_dir / "knowledge.db"
    vectors_path = generated_dir / "vectors.idx"
    
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)
    
    if not vectors_path.exists():
        print(f"ERROR: Vector index not found: {vectors_path}")
        sys.exit(1)
    
    manifest = {
        "version": version,
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_hash": source_hash,
        "embedding_model": model,
        "embedding_dimensions": 384,
        "total_entries": get_total_entries(db_path),
        "categories": get_category_counts(db_path),
        "files": {
            "knowledge.db": {
                "size_bytes": db_path.stat().st_size,
                "sha256": calculate_file_hash(db_path),
            },
            "vectors.idx": {
                "size_bytes": vectors_path.stat().st_size,
                "sha256": calculate_file_hash(vectors_path),
            },
        },
        "schema_version": "1.0",
        "hnswlib_space": "cosine",
    }
    
    # Write manifest
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Generated manifest: {output_path}")
    print(f"  Version: {manifest['version']}")
    print(f"  Total entries: {manifest['total_entries']}")
    print(f"  Categories: {len(manifest['categories'])}")
    
    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate manifest.json for RAG index",
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("generated/manifest.json"),
        help="Output path for manifest.json",
    )
    
    parser.add_argument(
        "--version",
        type=str,
        default="1.0.0",
        help="Version string",
    )
    
    parser.add_argument(
        "--source-hash",
        type=str,
        default="unknown",
        help="Hash of source files",
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Embedding model used",
    )
    
    args = parser.parse_args()
    
    generated_dir = args.output.parent
    
    generate_manifest(
        args.output,
        args.version,
        args.source_hash,
        args.model,
        generated_dir,
    )


if __name__ == "__main__":
    main()


