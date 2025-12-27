"""
JSON Parser
===========

Parses JSON and CSV data files into structured entries.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass
class DataEntry:
    """A structured data entry."""
    title: str
    content: str
    metadata: dict[str, Any]
    source_file: str


class JSONParser:
    """Parser for JSON data files."""
    
    def __init__(
        self,
        title_fields: list[str] | None = None,
        content_fields: list[str] | None = None,
        min_content_length: int = 50,
    ):
        self.title_fields = title_fields or [
            "name", "title", "common_name", "label", "heading"
        ]
        self.content_fields = content_fields or [
            "description", "content", "text", "body", "summary", "notes"
        ]
        self.min_content_length = min_content_length
    
    def parse_file(self, json_path: Path) -> Iterator[DataEntry]:
        """Parse a JSON file and yield entries."""
        with open(json_path) as f:
            data = json.load(f)
        
        yield from self._parse_data(data, json_path.name)
    
    def parse_csv(self, csv_path: Path) -> Iterator[DataEntry]:
        """Parse a CSV file and yield entries."""
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = self._parse_item(dict(row), csv_path.name)
                if entry:
                    yield entry
    
    def _parse_data(self, data: Any, source_file: str) -> Iterator[DataEntry]:
        """Recursively parse JSON data."""
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    entry = self._parse_item(item, source_file)
                    if entry:
                        yield entry
        elif isinstance(data, dict):
            # Check if it's a single entry or container
            if self._looks_like_entry(data):
                entry = self._parse_item(data, source_file)
                if entry:
                    yield entry
            else:
                # Recurse into nested structures
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        yield from self._parse_data(value, source_file)
    
    def _looks_like_entry(self, item: dict) -> bool:
        """Check if a dict looks like a data entry."""
        # Has at least one title field
        has_title = any(f in item for f in self.title_fields)
        # Has at least one content field or multiple string fields
        has_content = any(f in item for f in self.content_fields)
        string_fields = sum(1 for v in item.values() if isinstance(v, str) and len(v) > 20)
        
        return has_title or has_content or string_fields >= 2
    
    def _parse_item(self, item: dict, source_file: str) -> DataEntry | None:
        """Parse a single item into a DataEntry."""
        # Extract title
        title = None
        for field in self.title_fields:
            if field in item and item[field]:
                title = str(item[field])
                break
        
        if not title:
            title = "Untitled Entry"
        
        # Build content from available fields
        content_parts = []
        metadata = {}
        
        for key, value in item.items():
            if key in self.title_fields:
                continue
            
            if isinstance(value, str):
                if len(value) > 20:
                    content_parts.append(f"**{key.replace('_', ' ').title()}**: {value}")
                else:
                    metadata[key] = value
            elif isinstance(value, (int, float, bool)):
                metadata[key] = value
            elif isinstance(value, list) and all(isinstance(x, str) for x in value):
                content_parts.append(f"**{key.replace('_', ' ').title()}**: {', '.join(value)}")
        
        content = "\n\n".join(content_parts)
        
        if len(content) < self.min_content_length:
            return None
        
        return DataEntry(
            title=title,
            content=content,
            metadata=metadata,
            source_file=source_file,
        )


