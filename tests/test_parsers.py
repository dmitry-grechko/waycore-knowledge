"""
Tests for document parsers.
"""

import json
import tempfile
from pathlib import Path

import pytest

# Import parsers - handle both direct run and pytest scenarios
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from parsers.json_parser import JSONParser, DataEntry
from parsers.plant_parser import PlantParser, PlantEntry


class TestJSONParser:
    """Tests for JSON parser."""
    
    def test_parse_simple_list(self):
        """Test parsing a simple list of objects."""
        data = [
            {
                "name": "Test Item",
                "description": "This is a test description that is long enough to be included.",
            },
            {
                "name": "Another Item",
                "description": "Another description that contains enough content to pass the minimum threshold.",
            },
        ]
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        
        try:
            parser = JSONParser()
            entries = list(parser.parse_file(temp_path))
            
            assert len(entries) == 2
            assert entries[0].title == "Test Item"
            assert "test description" in entries[0].content.lower()
        finally:
            temp_path.unlink()
    
    def test_parse_nested_structure(self):
        """Test parsing nested JSON structures."""
        data = {
            "items": [
                {
                    "title": "Nested Item",
                    "content": "This content is nested within the items array and should be extracted properly.",
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        
        try:
            parser = JSONParser()
            entries = list(parser.parse_file(temp_path))
            
            assert len(entries) == 1
            assert entries[0].title == "Nested Item"
        finally:
            temp_path.unlink()
    
    def test_skip_short_content(self):
        """Test that short content is skipped."""
        data = [{"name": "Short", "description": "Too short."}]
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        
        try:
            parser = JSONParser(min_content_length=50)
            entries = list(parser.parse_file(temp_path))
            
            assert len(entries) == 0
        finally:
            temp_path.unlink()


class TestPlantParser:
    """Tests for plant database parser."""
    
    def test_parse_plant_entry(self):
        """Test parsing a plant database entry."""
        data = [
            {
                "common_name": "Dandelion",
                "scientific_name": "Taraxacum officinale",
                "family": "Asteraceae",
                "description": "A common perennial plant with yellow flowers and deeply toothed leaves.",
                "edibility": "Young leaves are edible raw or cooked. Roots can be roasted.",
                "edibility_rating": 5,
                "habitat": "Found in lawns, meadows, and disturbed areas worldwide.",
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        
        try:
            parser = PlantParser()
            entries = list(parser.parse_file(temp_path))
            
            assert len(entries) == 1
            entry = entries[0]
            
            assert entry.common_name == "Dandelion"
            assert entry.scientific_name == "Taraxacum officinale"
            assert entry.family == "Asteraceae"
            assert entry.edibility_rating == 5
            assert entry.safety_level == "caution"
            assert "SAFETY WARNING" in entry.safety_notes
        finally:
            temp_path.unlink()
    
    def test_unknown_edibility_is_dangerous(self):
        """Test that plants with unknown edibility are marked as dangerous."""
        data = [
            {
                "common_name": "Unknown Plant",
                "description": "A mysterious plant with no known edibility information provided.",
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        
        try:
            parser = PlantParser()
            entries = list(parser.parse_file(temp_path))
            
            assert len(entries) == 1
            assert entries[0].safety_level == "danger"
        finally:
            temp_path.unlink()
    
    def test_toxic_plant_is_lethal(self):
        """Test that toxic plants are marked as lethal."""
        data = [
            {
                "common_name": "Deadly Nightshade",
                "scientific_name": "Atropa belladonna",
                "description": "An extremely toxic plant. All parts are poisonous.",
                "edibility_rating": 1,
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        
        try:
            parser = PlantParser()
            entries = list(parser.parse_file(temp_path))
            
            assert len(entries) == 1
            assert entries[0].safety_level == "lethal"
        finally:
            temp_path.unlink()


class TestDataEntry:
    """Tests for DataEntry structure."""
    
    def test_data_entry_fields(self):
        """Test DataEntry has all required fields."""
        entry = DataEntry(
            title="Test",
            content="Test content",
            metadata={"key": "value"},
            source_file="test.json",
        )
        
        assert entry.title == "Test"
        assert entry.content == "Test content"
        assert entry.metadata == {"key": "value"}
        assert entry.source_file == "test.json"


class TestPlantEntry:
    """Tests for PlantEntry structure."""
    
    def test_plant_entry_fields(self):
        """Test PlantEntry has all required fields."""
        entry = PlantEntry(
            common_name="Test Plant",
            scientific_name="Testus plantus",
            family="Testaceae",
            description="A test plant",
            edibility="Edible",
            edibility_rating=4,
            medicinal_uses="None",
            habitat="Everywhere",
            safety_level="caution",
            safety_notes="Be careful",
            source_file="test.json",
            metadata={},
        )
        
        assert entry.common_name == "Test Plant"
        assert entry.scientific_name == "Testus plantus"
        assert entry.safety_level == "caution"

