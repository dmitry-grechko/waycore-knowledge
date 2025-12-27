# waycore-knowledge

> 🌲 Open-source survival & outdoor knowledge base for AI-powered field devices

[![Build RAG Index](https://github.com/dmitry-grechko/waycore-knowledge/actions/workflows/build.yml/badge.svg)](https://github.com/dmitry-grechko/waycore-knowledge/actions/workflows/build.yml)
[![License: CC0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](https://creativecommons.org/publicdomain/zero/1.0/)
[![Sources](https://img.shields.io/badge/Sources-88_Documents-blue.svg)](#included-sources)

A curated collection of **public domain** survival, tactical, medical, and
outdoor knowledge, pre-processed for RAG (Retrieval-Augmented Generation)
systems. Built for the [Waycore](https://github.com/dmitry-grechko/waycore)
tactical field device, but useful for any AI-powered outdoor application.

## 🎯 Purpose

This repository solves a common problem: **AI models need domain-specific
knowledge to be useful in the field**. Instead of every project independently
collecting, parsing, and indexing survival manuals, we provide:

1. **Curated Sources** - 88 documents covering survival, tactical, medical,
   navigation, NBC preparedness, and more
2. **Pre-built Index** - SQLite + vector embeddings ready for semantic search
3. **Automated Pipeline** - GitHub Actions rebuilds the index when sources
   change
4. **Easy Integration** - Download two files and start searching

## 📥 Quick Start

### For Projects (Recommended)

Download the pre-built index from
[Releases](https://github.com/dmitry-grechko/waycore-knowledge/releases):

```bash
# Download latest release
curl -LO https://github.com/dmitry-grechko/waycore-knowledge/releases/latest/download/knowledge.db
curl -LO https://github.com/dmitry-grechko/waycore-knowledge/releases/latest/download/vectors.idx
curl -LO https://github.com/dmitry-grechko/waycore-knowledge/releases/latest/download/manifest.json
```

### For Docker Builds

```dockerfile
# Multi-stage: download index
FROM curlimages/curl:latest as rag-index
WORKDIR /data
RUN curl -LO https://github.com/dmitry-grechko/waycore-knowledge/releases/latest/download/knowledge.db && \
    curl -LO https://github.com/dmitry-grechko/waycore-knowledge/releases/latest/download/vectors.idx

# Your application
FROM python:3.11-slim
COPY --from=rag-index /data/*.db /data/*.idx /app/data/
```

### Using the Index

```python
import sqlite3
import hnswlib
import numpy as np
from sentence_transformers import SentenceTransformer

# Load the index
conn = sqlite3.connect('knowledge.db')
index = hnswlib.Index(space='cosine', dim=384)
index.load_index('vectors.idx')

# Load embedding model (same one used to build index)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Search
query = "how to start a fire without matches"
query_embedding = model.encode(query)
labels, distances = index.knn_query([query_embedding], k=5)

# Get results from SQLite
for label in labels[0]:
    cursor = conn.execute(
        "SELECT title, content, category, safety_level FROM entries WHERE rowid = ?",
        (int(label),)
    )
    row = cursor.fetchone()
    print(f"[{row[2]}] {row[0]}")
    print(f"  Safety: {row[3]}")
    print(f"  {row[1][:200]}...")
```

## 📚 Included Sources

### Summary

| Category             | Docs   | Topics                                         |
| -------------------- | ------ | ---------------------------------------------- |
| 🪖 Survival          | 2      | Shelter, water, food, psychology, mountain ops |
| 🎯 Tactical          | 3      | Ranger tactics, infantry, camouflage           |
| 🔫 Firearms          | 2      | Rifle marksmanship, crew-served weapons        |
| 🧭 Navigation        | 3      | Map reading, topo symbols, land navigation     |
| 🏥 First Aid         | 6      | Wilderness medicine, water disinfection        |
| 🩺 Medical           | 7      | TCCC, prolonged care, wound closure, diseases  |
| 🪢 Knots & Rigging   | 6      | Essential knots, rigging, mountaineering       |
| 🌦️ Weather            | 3      | Cloud ID, forecasting, hurricanes              |
| 🥶 Cold Weather      | 4      | Cold ops, avalanche, frostbite, hypothermia    |
| 🥵 Hot Weather       | 3      | Heat illness, prevention, first aid            |
| 🌊 Water Survival    | 2      | Sea survival, boat crew rescue                 |
| 📡 Signaling         | 3      | Visual signals, ground-to-air, EPIRB/PLB       |
| 📻 Communications    | 4      | Morse code, ARES, emergency comms              |
| 🌿 Plants & Wildlife | 5      | Edible plants, animal tracks                   |
| 🦎 Wildlife Threats  | 5      | Snakes, scorpions, spiders, crocodilians       |
| 🏕️ Shelter            | 1      | Shelter building techniques                    |
| 🎣 Hunting           | 1      | Trapping techniques                            |
| 🔧 Primitive Skills  | 5      | Flintknapping, cordage, blacksmithing, traps   |
| 🍖 Food Preservation | 6      | Canning, drying, fermenting, smoking           |
| 🚨 Emergency Prep    | 8      | FEMA guides, evacuation, disaster supplies     |
| 🧠 Psychology        | 4      | PFA, combat stress, leadership                 |
| ☢️ NBC Preparedness   | 5      | Nuclear survival, CBRN decon, radiological     |
| **Total**            | **88** |                                                |

### Key Documents

<details>
<summary><b>🪖 Survival & Tactical</b> (click to expand)</summary>

| Document                          | Description                       | License       |
| --------------------------------- | --------------------------------- | ------------- |
| **FM 21-76 Survival Manual**      | Definitive US Army survival guide | Public Domain |
| **FM 3-97.6 Mountain Operations** | High altitude survival            | Public Domain |
| **SH 21-76 Ranger Handbook**      | Legendary tactical reference      | Public Domain |
| **FM 3-21.8 Infantry Platoon**    | Updated infantry doctrine         | Public Domain |
| **ATTP 3-34.39 Camouflage**       | Concealment, decoys, CCD          | Public Domain |

</details>

<details>
<summary><b>🏥 First Aid & Medical</b> (click to expand)</summary>

| Document                             | Description                       | License       |
| ------------------------------------ | --------------------------------- | ------------- |
| **BSA Wilderness First Aid**         | 16-hour WFA curriculum            | Educational   |
| **TCCC Guidelines 2024**             | Tactical Combat Casualty Care     | Public Domain |
| **Prolonged Casualty Care**          | Extended pre-hospital care        | Public Domain |
| **EPA Emergency Water Disinfection** | Water purification methods        | Public Domain |
| **Aerie Backcountry Medicine**       | Comprehensive wilderness medicine | Educational   |
| **Ethicon Wound Closure Manual**     | Professional suturing guide       | Educational   |
| **MSF Obstetric & Newborn Care**     | Field obstetric emergencies       | CC BY-NC-SA   |

</details>

<details>
<summary><b>🧭 Navigation & Signaling</b> (click to expand)</summary>

| Document                         | Description                           | License       |
| -------------------------------- | ------------------------------------- | ------------- |
| **FM 3-25.26 Map Reading**       | Comprehensive military navigation     | Public Domain |
| **USGS Topographic Map Symbols** | Official topo map reference           | Public Domain |
| **FM 21-60 Visual Signals**      | Arm-hand, flag, ground-to-air signals | Public Domain |
| **NOAA EPIRB/PLB Fact Sheet**    | Emergency beacon operation            | Public Domain |

</details>

<details>
<summary><b>🪢 Knots, Rigging & Primitive Skills</b> (click to expand)</summary>

| Document                               | Description                     | License       |
| -------------------------------------- | ------------------------------- | ------------- |
| **FM 5-125 Rigging Techniques**        | Army rigging manual             | Public Domain |
| **FM 3-97.61 Military Mountaineering** | Rope management, climbing       | Public Domain |
| **FEMA Lifting & Rigging**             | US&R rescue rigging             | Public Domain |
| **Flintknapping Guide**                | Stone tool making (350 pages)   | Educational   |
| **Basic Blacksmithing**                | Toolmaking with local materials | Educational   |
| **Deadfalls and Snares**               | Historic trap construction      | Public Domain |

</details>

<details>
<summary><b>🌦️ Weather & Climate Survival</b> (click to expand)</summary>

| Document                            | Description                     | License       |
| ----------------------------------- | ------------------------------- | ------------- |
| **NWS Weather Guide**               | Complete weather forecasting    | Public Domain |
| **TC 21-3 Cold Weather Operations** | Army cold weather handbook      | Public Domain |
| **Ortovox Avalanche Safety**        | Avalanche mechanics and safety  | Educational   |
| **CDC Heat-Related Illnesses**      | Heat stroke, exhaustion, cramps | Public Domain |
| **NOAA Mariner's Tropical Cyclone** | Hurricane preparation           | Public Domain |

</details>

<details>
<summary><b>🦎 Wildlife & Animal Threats</b> (click to expand)</summary>

| Document                          | Description                     | License       |
| --------------------------------- | ------------------------------- | ------------- |
| **DoD Venomous Snake Cards**      | 12 common venomous snakes       | Public Domain |
| **Arizona Scorpions Guide**       | Bark scorpion identification    | Educational   |
| **UWyo Widow & Recluse Spiders**  | Venomous spider identification  | Educational   |
| **UF Crocodile/Alligator Safety** | Crocodilian behavior and safety | Educational   |
| **MN DNR Animal Tracks**          | Animal track identification     | Public Domain |

</details>

<details>
<summary><b>☢️ NBC & Emergency Preparedness</b> (click to expand)</summary>

| Document                           | Description                        | License       |
| ---------------------------------- | ---------------------------------- | ------------- |
| **Nuclear War Survival Skills**    | Definitive civilian nuclear guide  | Public Domain |
| **FEMA Nuclear 72 Hours**          | First 72 hours post-detonation     | Public Domain |
| **FM 3-11.5 CBRN Decontamination** | Multiservice decon manual          | Public Domain |
| **FEMA Are You Ready?**            | Comprehensive citizen preparedness | Public Domain |
| **FEMA Full Hazard Sheets**        | Complete hazard collection         | Public Domain |

</details>

<details>
<summary><b>🍖 Food & Preservation</b> (click to expand)</summary>

| Document                            | Description                     | License       |
| ----------------------------------- | ------------------------------- | ------------- |
| **USDA Home Canning Guide**         | Definitive 7-part canning guide | Public Domain |
| **PNW Drying Fruits & Vegetables**  | Comprehensive dehydration       | Educational   |
| **VA Tech Vegetable Fermentation**  | Sauerkraut, pickles, kimchi     | Educational   |
| **UC Davis Smoking & Canning Fish** | Fish preservation               | Educational   |
| **NY Trapping Manual**              | Comprehensive trapping guide    | Public Domain |

</details>

See [SOURCES.md](SOURCES.md) for complete attribution and licensing details.

## 🔨 Building Locally

If you want to rebuild the index yourself:

```bash
# Clone repository
git clone https://github.com/dmitry-grechko/waycore-knowledge.git
cd waycore-knowledge

# Install dependencies
pip install -r scripts/requirements.txt

# Build index (takes ~5-10 minutes)
python scripts/build_index.py

# Output files in generated/
ls -la generated/
```

## 📊 Index Schema

### SQLite Tables

```sql
-- Main entries table
CREATE TABLE entries (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    safety_level TEXT DEFAULT 'safe', -- safe, caution, warning, danger, lethal
    safety_notes TEXT,
    source_file TEXT,
    source_page INTEGER,
    source_url TEXT,
    license TEXT,
    tags TEXT,                        -- JSON array
    created_at TEXT
);

-- FTS5 full-text search
CREATE VIRTUAL TABLE entries_fts USING fts5(
    id, title, content, tags,
    content='entries'
);
```

### Vector Index

- **Model**: `all-MiniLM-L6-v2` (22MB, 384 dimensions)
- **Format**: Hnswlib with cosine similarity
- **Size**: ~80MB for 7,000 entries

## ⚠️ Safety System

All entries include safety classifications:

| Level     | Color | Meaning                   | Example                  |
| --------- | ----- | ------------------------- | ------------------------ |
| `safe`    | 🟢    | General information       | Navigation basics        |
| `caution` | 🟡    | Requires care             | Fire starting techniques |
| `warning` | 🟠    | Significant risk          | First aid procedures     |
| `danger`  | 🔴    | High risk                 | Plant identification     |
| `lethal`  | ⛔    | Life-threatening if wrong | Mushroom identification  |

**Important**: All plant and mushroom entries default to `danger` or `lethal`
with mandatory verification disclaimers. Never rely solely on this database for
plant identification.

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding Sources

1. Ensure the source is **public domain** or **appropriately licensed**
2. Add the PDF/JSON to `sources/{category}/`
3. Update `SOURCES.md` with full attribution
4. Submit a pull request
5. GitHub Actions will validate and rebuild

### Improving Parsing

1. Fork the repository
2. Modify parsers in `scripts/parsers/`
3. Run `python scripts/build_index.py` to test
4. Submit a pull request with before/after comparison

## 📜 License

- **Repository structure & scripts**:
  [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (Public Domain)
- **Source documents**: Various (see [SOURCES.md](SOURCES.md))
- **Generated index**: CC0 (derived from public domain works)

## 🔗 Related Projects

- [Waycore](https://github.com/dmitry-grechko/waycore) - Tactical field device
  using this knowledge base

## 📈 Stats

- **Total documents**: 88
- **Categories**: 22
- **Build time**: ~5-10 minutes
- **Query latency**: <100ms

---

_Built with ❤️ for the outdoor community_
