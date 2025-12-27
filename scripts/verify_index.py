#!/usr/bin/env python3
"""
Index Verification Script
=========================

Validates the built index:
- SQLite integrity check
- Vector index loads correctly
- Sample searches return results
- Entry counts match expected

Usage:
    python scripts/verify_index.py generated/
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

try:
    import hnswlib
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Run: pip install sentence-transformers hnswlib")
    sys.exit(1)


# Test queries with expected categories
TEST_QUERIES = [
    ("how to start a fire without matches", "survival"),
    ("reading a topographic map", "navigation"),
    ("treating a bleeding wound", "first_aid"),
    ("tying a bowline knot", "knots"),
    ("identifying cloud types", "weather"),
]


def verify_database(db_path: Path) -> tuple[bool, str]:
    """Verify SQLite database integrity."""
    try:
        conn = sqlite3.connect(db_path)
        
        # Integrity check
        cursor = conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        if result != "ok":
            return False, f"Integrity check failed: {result}"
        
        # Check table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entries'"
        )
        if not cursor.fetchone():
            return False, "Table 'entries' not found"
        
        # Check FTS table
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entries_fts'"
        )
        if not cursor.fetchone():
            return False, "FTS table 'entries_fts' not found"
        
        # Check entry count
        cursor = conn.execute("SELECT COUNT(*) FROM entries")
        count = cursor.fetchone()[0]
        if count == 0:
            return False, "No entries in database"
        
        conn.close()
        return True, f"Database OK: {count} entries"
        
    except Exception as e:
        return False, f"Database error: {e}"


def verify_vector_index(vectors_path: Path, expected_dim: int = 384) -> tuple[bool, str]:
    """Verify Hnswlib vector index."""
    try:
        index = hnswlib.Index(space='cosine', dim=expected_dim)
        index.load_index(str(vectors_path))
        
        count = index.get_current_count()
        if count == 0:
            return False, "Vector index is empty"
        
        return True, f"Vector index OK: {count} vectors"
        
    except Exception as e:
        return False, f"Vector index error: {e}"


def verify_search(
    db_path: Path,
    vectors_path: Path,
    model_name: str = "all-MiniLM-L6-v2",
) -> tuple[bool, list[str]]:
    """Verify search functionality with test queries."""
    results = []
    all_passed = True
    
    try:
        # Load components
        conn = sqlite3.connect(db_path)
        index = hnswlib.Index(space='cosine', dim=384)
        index.load_index(str(vectors_path))
        model = SentenceTransformer(model_name)
        
        for query, expected_category in TEST_QUERIES:
            embedding = model.encode(query)
            labels, _ = index.knn_query([embedding], k=1)
            
            if len(labels) == 0 or len(labels[0]) == 0:
                results.append(f"❌ '{query}' - No results")
                all_passed = False
                continue
            
            cursor = conn.execute(
                "SELECT category FROM entries WHERE rowid = ?",
                (int(labels[0][0]),)
            )
            row = cursor.fetchone()
            
            if not row:
                results.append(f"❌ '{query}' - Entry not found for rowid {labels[0][0]}")
                all_passed = False
                continue
            
            actual = row[0]
            if actual == expected_category:
                results.append(f"✅ '{query}' -> {actual}")
            else:
                results.append(f"⚠️ '{query}' -> {actual} (expected: {expected_category})")
                # Don't fail for category mismatch, just warn
        
        conn.close()
        return all_passed, results
        
    except Exception as e:
        return False, [f"Search error: {e}"]


def verify_manifest(manifest_path: Path, db_path: Path) -> tuple[bool, str]:
    """Verify manifest.json consistency."""
    try:
        if not manifest_path.exists():
            return False, "Manifest not found"
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Check required fields
        required = ["version", "total_entries", "categories", "files"]
        for field in required:
            if field not in manifest:
                return False, f"Missing field: {field}"
        
        # Verify entry count matches database
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM entries")
        actual_count = cursor.fetchone()[0]
        conn.close()
        
        if manifest["total_entries"] != actual_count:
            return False, f"Entry count mismatch: manifest={manifest['total_entries']}, db={actual_count}"
        
        return True, f"Manifest OK: v{manifest['version']}"
        
    except Exception as e:
        return False, f"Manifest error: {e}"


def verify_index(generated_dir: Path, verbose: bool = False) -> bool:
    """Run all verification checks."""
    db_path = generated_dir / "knowledge.db"
    vectors_path = generated_dir / "vectors.idx"
    manifest_path = generated_dir / "manifest.json"
    
    print("=" * 60)
    print("Waycore RAG Knowledge - Index Verification")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # Check database
    print("📊 Checking database...")
    passed, message = verify_database(db_path)
    print(f"  {'✅' if passed else '❌'} {message}")
    all_passed &= passed
    
    # Check vector index
    print("\n🔢 Checking vector index...")
    passed, message = verify_vector_index(vectors_path)
    print(f"  {'✅' if passed else '❌'} {message}")
    all_passed &= passed
    
    # Check manifest
    print("\n📋 Checking manifest...")
    passed, message = verify_manifest(manifest_path, db_path)
    print(f"  {'✅' if passed else '❌'} {message}")
    all_passed &= passed
    
    # Run search tests
    print("\n🔍 Running search tests...")
    passed, results = verify_search(db_path, vectors_path)
    for result in results:
        print(f"  {result}")
    all_passed &= passed
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All verification checks passed!")
    else:
        print("❌ Some verification checks failed!")
    print("=" * 60)
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Verify built RAG index",
    )
    
    parser.add_argument(
        "generated_dir",
        type=Path,
        nargs="?",
        default=Path("generated"),
        help="Directory containing generated files (default: generated/)",
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    if not args.generated_dir.exists():
        print(f"ERROR: Directory not found: {args.generated_dir}")
        sys.exit(1)
    
    success = verify_index(args.generated_dir, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

