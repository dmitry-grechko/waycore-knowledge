#!/usr/bin/env python3
"""
RAG Index Builder
=================

Main build script that:
- Parses all PDFs in sources/
- Chunks text into searchable entries
- Generates embeddings using sentence-transformers
- Builds SQLite + FTS5 index
- Builds Hnswlib vector index

Usage:
    python scripts/build_index.py [--sources-dir DIR] [--output-dir DIR] [--model MODEL] [--verbose]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

try:
    import fitz  # PyMuPDF
    import hnswlib
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Run: pip install -r scripts/requirements.txt")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Chunk configuration
CHUNK_SIZE = 512  # Target chunk size in characters
CHUNK_OVERLAP = 64  # Overlap between chunks
MIN_CHUNK_SIZE = 100  # Minimum chunk size

# Safety levels for categories
CATEGORY_SAFETY = {
    "survival": "caution",
    "navigation": "safe",
    "first_aid": "warning",
    "plants": "danger",
    "knots": "safe",
    "weather": "safe",
    "comms": "safe",
    "equipment": "caution",
}

# Embedding model dimensions
EMBEDDING_DIM = 384


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class Entry:
    """A single searchable entry in the knowledge base."""
    
    def __init__(
        self,
        title: str,
        content: str,
        category: str,
        subcategory: str | None = None,
        safety_level: str = "safe",
        safety_notes: str | None = None,
        source_file: str | None = None,
        source_page: int | None = None,
        source_url: str | None = None,
        license: str | None = None,
        tags: list[str] | None = None,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.title = title
        self.content = content
        self.category = category
        self.subcategory = subcategory
        self.safety_level = safety_level
        self.safety_notes = safety_notes
        self.source_file = source_file
        self.source_page = source_page
        self.source_url = source_url
        self.license = license
        self.tags = tags or []
        self.created_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "subcategory": self.subcategory,
            "safety_level": self.safety_level,
            "safety_notes": self.safety_notes,
            "source_file": self.source_file,
            "source_page": self.source_page,
            "source_url": self.source_url,
            "license": self.license,
            "tags": json.dumps(self.tags),
            "created_at": self.created_at,
        }


# =============================================================================
# TEXT PROCESSING
# =============================================================================

def clean_text(text: str) -> str:
    """Clean extracted text."""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> Iterator[str]:
    """Split text into overlapping chunks."""
    text = clean_text(text)
    
    if len(text) < MIN_CHUNK_SIZE:
        return
    
    # Split on paragraph boundaries first
    paragraphs = re.split(r'\n\n+', text)
    
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If adding this paragraph exceeds chunk size, yield current and start new
        if len(current_chunk) + len(para) + 2 > chunk_size and len(current_chunk) >= MIN_CHUNK_SIZE:
            yield current_chunk
            # Keep overlap from end of current chunk
            current_chunk = current_chunk[-overlap:] + " " + para if overlap > 0 else para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Yield remaining text
    if current_chunk and len(current_chunk) >= MIN_CHUNK_SIZE:
        yield current_chunk


def extract_title_from_text(text: str, max_length: int = 100) -> str:
    """Extract a title from the first meaningful line of text."""
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        # Skip empty lines and very short lines
        if len(line) < 10:
            continue
        # Skip lines that look like page numbers or headers
        if re.match(r'^(page\s+)?\d+$', line.lower()):
            continue
        # Truncate if too long
        if len(line) > max_length:
            return line[:max_length-3] + "..."
        return line
    return "Untitled Entry"


# =============================================================================
# PDF PARSING
# =============================================================================

def parse_pdf(pdf_path: Path, category: str, verbose: bool = False) -> Iterator[Entry]:
    """Parse a PDF file and yield entries."""
    if verbose:
        print(f"  Parsing: {pdf_path.name}")
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  ERROR: Could not open {pdf_path.name}: {e}")
        return
    
    # Determine safety level based on category
    safety_level = CATEGORY_SAFETY.get(category, "safe")
    
    # Add extra caution for plant-related content
    safety_notes = None
    if category == "plants":
        safety_notes = "WARNING: Never consume plants based solely on this information. Always verify with multiple authoritative sources."
    elif category == "first_aid":
        safety_notes = "This information is for educational purposes. Seek professional medical help when possible."
    
    # Extract text from each page and chunk
    all_text = ""
    page_breaks = []  # Track where pages start in the combined text
    
    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        page_breaks.append((len(all_text), page_num + 1))
        all_text += f"\n\n{page_text}"
    
    doc.close()
    
    # Chunk the combined text
    chunk_num = 0
    for chunk in chunk_text(all_text):
        chunk_num += 1
        
        # Determine which page this chunk is from
        chunk_start = all_text.find(chunk[:50])  # Find approximate position
        source_page = 1
        for text_pos, page_num in page_breaks:
            if chunk_start >= text_pos:
                source_page = page_num
        
        # Generate title from chunk content
        title = extract_title_from_text(chunk)
        
        yield Entry(
            title=title,
            content=chunk,
            category=category,
            subcategory=None,
            safety_level=safety_level,
            safety_notes=safety_notes,
            source_file=pdf_path.name,
            source_page=source_page,
            license="public_domain",  # Default for most sources
            tags=[category, pdf_path.stem],
        )
    
    if verbose:
        print(f"    Generated {chunk_num} entries")


def parse_json(json_path: Path, category: str, verbose: bool = False) -> Iterator[Entry]:
    """Parse a JSON file and yield entries."""
    if verbose:
        print(f"  Parsing: {json_path.name}")
    
    try:
        with open(json_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ERROR: Could not parse {json_path.name}: {e}")
        return
    
    # Handle different JSON structures
    entries_count = 0
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield from parse_json_item(item, category, json_path.name)
                entries_count += 1
    elif isinstance(data, dict):
        # Check for nested arrays
        for key, value in data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        yield from parse_json_item(item, category, json_path.name)
                        entries_count += 1
    
    if verbose:
        print(f"    Generated {entries_count} entries")


def parse_json_item(item: dict, category: str, source_file: str) -> Iterator[Entry]:
    """Parse a single JSON item into an entry."""
    # Try to extract meaningful fields
    title = item.get("name") or item.get("title") or item.get("common_name") or "Unknown"
    
    # Build content from available fields
    content_parts = []
    for key, value in item.items():
        if key.lower() in ("name", "title", "id"):
            continue
        if isinstance(value, str) and len(value) > 10:
            content_parts.append(f"{key}: {value}")
    
    content = "\n".join(content_parts) if content_parts else json.dumps(item, indent=2)
    
    if len(content) < MIN_CHUNK_SIZE:
        return
    
    # Plants are always dangerous to identify
    safety_level = "danger" if category == "plants" else CATEGORY_SAFETY.get(category, "safe")
    safety_notes = "WARNING: Never consume plants based solely on this information." if category == "plants" else None
    
    yield Entry(
        title=str(title),
        content=content,
        category=category,
        subcategory=None,
        safety_level=safety_level,
        safety_notes=safety_notes,
        source_file=source_file,
        license="public_domain",
        tags=[category],
    )


# =============================================================================
# DATABASE
# =============================================================================

def create_database(db_path: Path) -> sqlite3.Connection:
    """Create SQLite database with schema."""
    conn = sqlite3.connect(db_path)
    
    # Create main entries table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            safety_level TEXT DEFAULT 'safe',
            safety_notes TEXT,
            source_file TEXT,
            source_page INTEGER,
            source_url TEXT,
            license TEXT,
            tags TEXT,
            created_at TEXT
        )
    """)
    
    # Create FTS5 virtual table for full-text search
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            id,
            title,
            content,
            tags,
            content='entries',
            content_rowid='rowid'
        )
    """)
    
    # Create triggers to keep FTS in sync
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(rowid, id, title, content, tags)
            VALUES (new.rowid, new.id, new.title, new.content, new.tags);
        END
    """)
    
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, id, title, content, tags)
            VALUES('delete', old.rowid, old.id, old.title, old.content, old.tags);
        END
    """)
    
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, id, title, content, tags)
            VALUES('delete', old.rowid, old.id, old.title, old.content, old.tags);
            INSERT INTO entries_fts(rowid, id, title, content, tags)
            VALUES (new.rowid, new.id, new.title, new.content, new.tags);
        END
    """)
    
    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON entries(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_safety ON entries(safety_level)")
    
    conn.commit()
    return conn


def insert_entry(conn: sqlite3.Connection, entry: Entry) -> int:
    """Insert an entry and return its rowid."""
    data = entry.to_dict()
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    
    cursor = conn.execute(
        f"INSERT INTO entries ({columns}) VALUES ({placeholders})",
        list(data.values())
    )
    return cursor.lastrowid


# =============================================================================
# VECTOR INDEX
# =============================================================================

def build_vector_index(
    conn: sqlite3.Connection,
    index_path: Path,
    model: SentenceTransformer,
    verbose: bool = False,
) -> hnswlib.Index:
    """Build Hnswlib vector index from entries."""
    # Get all entries
    cursor = conn.execute("SELECT rowid, content FROM entries ORDER BY rowid")
    rows = cursor.fetchall()
    
    if not rows:
        raise ValueError("No entries in database")
    
    if verbose:
        print(f"Building vector index for {len(rows)} entries...")
    
    # Generate embeddings in batches
    batch_size = 100
    all_embeddings = []
    all_ids = []
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        ids = [row[0] for row in batch]
        texts = [row[1] for row in batch]
        
        embeddings = model.encode(texts, show_progress_bar=verbose)
        all_embeddings.extend(embeddings)
        all_ids.extend(ids)
        
        if verbose:
            print(f"  Processed {min(i + batch_size, len(rows))}/{len(rows)} entries")
    
    # Build index
    index = hnswlib.Index(space='cosine', dim=EMBEDDING_DIM)
    index.init_index(max_elements=len(all_ids), ef_construction=200, M=16)
    index.add_items(all_embeddings, all_ids)
    index.set_ef(50)  # Set search efficiency
    
    # Save index
    index.save_index(str(index_path))
    
    if verbose:
        print(f"Saved vector index to {index_path}")
    
    return index


# =============================================================================
# MAIN BUILD PROCESS
# =============================================================================

def build_index(
    sources_dir: Path,
    output_dir: Path,
    model_name: str,
    verbose: bool = False,
) -> dict:
    """Main build process."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = output_dir / "knowledge.db"
    vectors_path = output_dir / "vectors.idx"
    
    # Remove existing files
    if db_path.exists():
        db_path.unlink()
    if vectors_path.exists():
        vectors_path.unlink()
    
    print("=" * 60)
    print("Waycore RAG Knowledge - Index Builder")
    print("=" * 60)
    print(f"\nSources: {sources_dir}")
    print(f"Output: {output_dir}")
    print(f"Model: {model_name}")
    print()
    
    # Load embedding model
    if verbose:
        print("Loading embedding model...")
    model = SentenceTransformer(model_name)
    
    # Create database
    if verbose:
        print("Creating database...")
    conn = create_database(db_path)
    
    # Process all source files
    stats = {"categories": {}, "total_entries": 0, "files_processed": 0}
    
    for category_dir in sorted(sources_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        
        category = category_dir.name
        if category.startswith("."):
            continue
        
        print(f"\n📁 Processing category: {category}")
        stats["categories"][category] = 0
        
        # Process PDFs
        for pdf_file in sorted(category_dir.glob("*.pdf")):
            for entry in parse_pdf(pdf_file, category, verbose):
                insert_entry(conn, entry)
                stats["categories"][category] += 1
                stats["total_entries"] += 1
            stats["files_processed"] += 1
        
        # Process JSON files
        for json_file in sorted(category_dir.glob("*.json")):
            for entry in parse_json(json_file, category, verbose):
                insert_entry(conn, entry)
                stats["categories"][category] += 1
                stats["total_entries"] += 1
            stats["files_processed"] += 1
    
    conn.commit()
    print(f"\n✅ Inserted {stats['total_entries']} entries into database")
    
    # Build vector index
    print("\n🔢 Building vector index...")
    build_vector_index(conn, vectors_path, model, verbose)
    
    # Close database
    conn.close()
    
    # Print summary
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"\nFiles processed: {stats['files_processed']}")
    print(f"Total entries: {stats['total_entries']}")
    print("\nEntries by category:")
    for cat, count in stats["categories"].items():
        print(f"  {cat}: {count}")
    
    print(f"\nOutput files:")
    print(f"  {db_path} ({db_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  {vectors_path} ({vectors_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
    return stats


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Build RAG index from source documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--sources-dir",
        type=Path,
        default=Path("sources"),
        help="Directory containing source documents (default: sources/)",
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("generated"),
        help="Directory for output files (default: generated/)",
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Sentence transformer model to use (default: all-MiniLM-L6-v2)",
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    if not args.sources_dir.exists():
        print(f"ERROR: Sources directory not found: {args.sources_dir}")
        sys.exit(1)
    
    build_index(args.sources_dir, args.output_dir, args.model, args.verbose)


if __name__ == "__main__":
    main()

