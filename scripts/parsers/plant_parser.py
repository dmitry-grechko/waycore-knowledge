"""
Plant Parser
============

Specialized parser for plant databases (USDA, PFAF, etc.).
Adds safety warnings and edibility information.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


# Safety levels based on edibility ratings
SAFETY_LEVELS = {
    5: "caution",   # Edible - still requires verification
    4: "caution",   # Edible with preparation
    3: "warning",   # Limited edibility
    2: "danger",    # Potentially toxic
    1: "lethal",    # Highly toxic
    0: "danger",    # Unknown - assume dangerous
}

# Standard safety disclaimer
PLANT_SAFETY_WARNING = """
⚠️ SAFETY WARNING: Never consume any plant based solely on this information.
Always verify identification with multiple authoritative sources.
Many plants have toxic look-alikes. When in doubt, do NOT eat it.
Consult local experts and field guides specific to your region.
"""


@dataclass
class PlantEntry:
    """A plant database entry with safety information."""
    common_name: str
    scientific_name: str | None
    family: str | None
    description: str
    edibility: str | None
    edibility_rating: int | None
    medicinal_uses: str | None
    habitat: str | None
    safety_level: str
    safety_notes: str
    source_file: str
    metadata: dict[str, Any]


class PlantParser:
    """Parser for plant database files."""
    
    def __init__(self):
        self.min_content_length = 100
    
    def parse_file(self, json_path: Path) -> Iterator[PlantEntry]:
        """Parse a plant database JSON file."""
        with open(json_path) as f:
            data = json.load(f)
        
        if isinstance(data, list):
            for item in data:
                entry = self._parse_plant(item, json_path.name)
                if entry:
                    yield entry
        elif isinstance(data, dict):
            # Handle nested structures
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        entry = self._parse_plant(item, json_path.name)
                        if entry:
                            yield entry
    
    def _parse_plant(self, item: dict, source_file: str) -> PlantEntry | None:
        """Parse a single plant record."""
        if not isinstance(item, dict):
            return None
        
        # Extract common name
        common_name = (
            item.get("common_name") or
            item.get("CommonName") or
            item.get("name") or
            item.get("vernacular_name") or
            "Unknown Plant"
        )
        
        # Extract scientific name
        scientific_name = (
            item.get("scientific_name") or
            item.get("ScientificName") or
            item.get("latin_name") or
            item.get("binomial")
        )
        
        # Extract family
        family = (
            item.get("family") or
            item.get("Family") or
            item.get("plant_family")
        )
        
        # Build description
        description_parts = []
        
        if scientific_name:
            description_parts.append(f"**Scientific Name**: {scientific_name}")
        
        if family:
            description_parts.append(f"**Family**: {family}")
        
        # Add various description fields
        for field in ["description", "physical_characteristics", "growth_habit", "leaves", "flowers", "fruit"]:
            if field in item and item[field]:
                description_parts.append(f"**{field.replace('_', ' ').title()}**: {item[field]}")
        
        # Edibility information
        edibility = item.get("edibility") or item.get("edible_parts") or item.get("uses_edible")
        edibility_rating = None
        
        if "edibility_rating" in item:
            try:
                edibility_rating = int(item["edibility_rating"])
            except (ValueError, TypeError):
                pass
        
        if edibility:
            description_parts.append(f"**Edibility**: {edibility}")
        
        # Medicinal uses
        medicinal_uses = (
            item.get("medicinal_uses") or
            item.get("medicinal") or
            item.get("uses_medicinal")
        )
        
        if medicinal_uses:
            description_parts.append(f"**Medicinal Uses**: {medicinal_uses}")
        
        # Habitat
        habitat = (
            item.get("habitat") or
            item.get("native_range") or
            item.get("distribution")
        )
        
        if habitat:
            description_parts.append(f"**Habitat**: {habitat}")
        
        # Determine safety level
        if edibility_rating is not None:
            safety_level = SAFETY_LEVELS.get(edibility_rating, "danger")
        else:
            safety_level = "danger"  # Default to dangerous if unknown
        
        # Build full description
        description = "\n\n".join(description_parts)
        
        if len(description) < self.min_content_length:
            return None
        
        # Extract remaining metadata
        metadata = {}
        skip_fields = {
            "common_name", "scientific_name", "family", "description",
            "edibility", "edibility_rating", "medicinal_uses", "habitat"
        }
        
        for key, value in item.items():
            if key.lower() not in skip_fields:
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value
        
        return PlantEntry(
            common_name=str(common_name),
            scientific_name=scientific_name,
            family=family,
            description=description,
            edibility=edibility,
            edibility_rating=edibility_rating,
            medicinal_uses=medicinal_uses,
            habitat=habitat,
            safety_level=safety_level,
            safety_notes=PLANT_SAFETY_WARNING,
            source_file=source_file,
            metadata=metadata,
        )
    
    def to_content(self, entry: PlantEntry) -> str:
        """Convert a PlantEntry to searchable content."""
        parts = [
            f"# {entry.common_name}",
            "",
            entry.description,
            "",
            "---",
            "",
            entry.safety_notes,
        ]
        
        return "\n".join(parts)


