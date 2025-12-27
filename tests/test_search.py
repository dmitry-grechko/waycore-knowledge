"""
Tests for search functionality.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest


class TestSQLiteSchema:
    """Tests for SQLite database schema."""
    
    def test_create_tables(self):
        """Test that database tables are created correctly."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        try:
            conn = sqlite3.connect(db_path)
            
            # Create main entries table
            conn.execute("""
                CREATE TABLE entries (
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
            
            # Create FTS5 table
            conn.execute("""
                CREATE VIRTUAL TABLE entries_fts USING fts5(
                    id, title, content, tags,
                    content='entries'
                )
            """)
            
            conn.commit()
            
            # Verify tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            
            assert "entries" in tables
            assert "entries_fts" in tables
            
            conn.close()
        finally:
            db_path.unlink()
    
    def test_insert_and_query(self):
        """Test inserting and querying entries."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        try:
            conn = sqlite3.connect(db_path)
            
            conn.execute("""
                CREATE TABLE entries (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    safety_level TEXT DEFAULT 'safe'
                )
            """)
            
            # Insert test entry
            conn.execute(
                "INSERT INTO entries (id, title, content, category) VALUES (?, ?, ?, ?)",
                ("test-1", "Fire Starting", "How to start a fire without matches", "survival")
            )
            conn.commit()
            
            # Query
            cursor = conn.execute(
                "SELECT title, category FROM entries WHERE category = ?",
                ("survival",)
            )
            row = cursor.fetchone()
            
            assert row is not None
            assert row[0] == "Fire Starting"
            assert row[1] == "survival"
            
            conn.close()
        finally:
            db_path.unlink()
    
    def test_fts_search(self):
        """Test full-text search functionality."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        try:
            conn = sqlite3.connect(db_path)
            
            # Create tables with FTS
            conn.execute("""
                CREATE TABLE entries (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE VIRTUAL TABLE entries_fts USING fts5(
                    id, title, content,
                    content='entries'
                )
            """)
            
            # Create trigger
            conn.execute("""
                CREATE TRIGGER entries_ai AFTER INSERT ON entries BEGIN
                    INSERT INTO entries_fts(rowid, id, title, content)
                    VALUES (new.rowid, new.id, new.title, new.content);
                END
            """)
            
            # Insert entries
            entries = [
                ("1", "Fire Starting", "Learn how to start a fire using flint and steel", "survival"),
                ("2", "Water Purification", "Methods to purify water in the wilderness", "survival"),
                ("3", "Map Reading", "How to read topographic maps for navigation", "navigation"),
            ]
            
            for entry in entries:
                conn.execute(
                    "INSERT INTO entries (id, title, content, category) VALUES (?, ?, ?, ?)",
                    entry
                )
            conn.commit()
            
            # FTS search for "fire"
            cursor = conn.execute(
                "SELECT id, title FROM entries_fts WHERE entries_fts MATCH 'fire'"
            )
            results = cursor.fetchall()
            
            assert len(results) == 1
            assert results[0][1] == "Fire Starting"
            
            # FTS search for "wilderness"
            cursor = conn.execute(
                "SELECT id, title FROM entries_fts WHERE entries_fts MATCH 'wilderness'"
            )
            results = cursor.fetchall()
            
            assert len(results) == 1
            assert results[0][1] == "Water Purification"
            
            conn.close()
        finally:
            db_path.unlink()


class TestCategorySearch:
    """Tests for category-based search."""
    
    def test_filter_by_category(self):
        """Test filtering entries by category."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        try:
            conn = sqlite3.connect(db_path)
            
            conn.execute("""
                CREATE TABLE entries (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL
                )
            """)
            
            conn.execute("CREATE INDEX idx_category ON entries(category)")
            
            # Insert entries from different categories
            entries = [
                ("1", "Shelter Building", "How to build emergency shelter", "survival"),
                ("2", "Fire Starting", "Fire making techniques", "survival"),
                ("3", "Compass Use", "Using a compass for navigation", "navigation"),
                ("4", "First Aid Basics", "Basic first aid techniques", "first_aid"),
            ]
            
            for entry in entries:
                conn.execute(
                    "INSERT INTO entries (id, title, content, category) VALUES (?, ?, ?, ?)",
                    entry
                )
            conn.commit()
            
            # Get survival entries
            cursor = conn.execute(
                "SELECT COUNT(*) FROM entries WHERE category = ?",
                ("survival",)
            )
            count = cursor.fetchone()[0]
            assert count == 2
            
            # Get all categories
            cursor = conn.execute(
                "SELECT DISTINCT category FROM entries ORDER BY category"
            )
            categories = [row[0] for row in cursor.fetchall()]
            assert categories == ["first_aid", "navigation", "survival"]
            
            conn.close()
        finally:
            db_path.unlink()


class TestSafetyLevels:
    """Tests for safety level filtering."""
    
    def test_filter_by_safety(self):
        """Test filtering entries by safety level."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        try:
            conn = sqlite3.connect(db_path)
            
            conn.execute("""
                CREATE TABLE entries (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    safety_level TEXT DEFAULT 'safe'
                )
            """)
            
            entries = [
                ("1", "Navigation Basics", "Basic navigation info", "navigation", "safe"),
                ("2", "Fire Starting", "Fire techniques", "survival", "caution"),
                ("3", "Wound Care", "Emergency wound care", "first_aid", "warning"),
                ("4", "Plant ID", "Plant identification", "plants", "danger"),
                ("5", "Mushroom ID", "Mushroom identification", "plants", "lethal"),
            ]
            
            for entry in entries:
                conn.execute(
                    "INSERT INTO entries (id, title, content, category, safety_level) VALUES (?, ?, ?, ?, ?)",
                    entry
                )
            conn.commit()
            
            # Get dangerous or lethal entries
            cursor = conn.execute(
                "SELECT COUNT(*) FROM entries WHERE safety_level IN ('danger', 'lethal')"
            )
            count = cursor.fetchone()[0]
            assert count == 2
            
            # Get safe entries only
            cursor = conn.execute(
                "SELECT title FROM entries WHERE safety_level = 'safe'"
            )
            safe = cursor.fetchall()
            assert len(safe) == 1
            assert safe[0][0] == "Navigation Basics"
            
            conn.close()
        finally:
            db_path.unlink()

