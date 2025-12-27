# waycore-rag-knowledge

> 🌲 Open-source survival & outdoor knowledge base for AI-powered field devices

[![Build RAG Index](https://github.com/waycore/waycore-rag-knowledge/actions/workflows/build.yml/badge.svg)](https://github.com/waycore/waycore-rag-knowledge/actions/workflows/build.yml)
[![License: CC0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](https://creativecommons.org/publicdomain/zero/1.0/)
[![Sources](https://img.shields.io/badge/Sources-58_Documents-blue.svg)](#included-sources)

A curated collection of **public domain** survival, navigation, first aid, and outdoor knowledge, pre-processed for RAG (Retrieval-Augmented Generation) systems. Built for the [Waycore](https://github.com/waycore/waycore) tactical field device, but useful for any AI-powered outdoor application.

## 🎯 Purpose

This repository solves a common problem: **AI models need domain-specific knowledge to be useful in the field**. Instead of every project independently collecting, parsing, and indexing survival manuals, we provide:

1. **Curated Sources** - 58 public domain documents covering survival, navigation, first aid, plants, knots, and weather
2. **Pre-built Index** - SQLite + vector embeddings ready for semantic search
3. **Automated Pipeline** - GitHub Actions rebuilds the index when sources change
4. **Easy Integration** - Download two files and start searching

## 📥 Quick Start

### For Projects (Recommended)

Download the pre-built index from [Releases](https://github.com/waycore/waycore-rag-knowledge/releases):

```bash
# Download latest release
curl -LO https://github.com/waycore/waycore-rag-knowledge/releases/latest/download/knowledge.db
curl -LO https://github.com/waycore/waycore-rag-knowledge/releases/latest/download/vectors.idx
curl -LO https://github.com/waycore/waycore-rag-knowledge/releases/latest/download/manifest.json
```

### For Docker Builds

```dockerfile
# Multi-stage: download index
FROM curlimages/curl:latest as rag-index
WORKDIR /data
RUN curl -LO https://github.com/waycore/waycore-rag-knowledge/releases/latest/download/knowledge.db && \
    curl -LO https://github.com/waycore/waycore-rag-knowledge/releases/latest/download/vectors.idx

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

| Category | Documents | Entries | Size | Topics |
|----------|-----------|---------|------|--------|
| 🪖 Survival | 12 | ~800 | 85 MB | Shelter, water, food, psychology, climate survival |
| 🧭 Navigation | 6 | ~400 | 25 MB | Map reading, compass, celestial navigation |
| 🏥 First Aid | 8 | ~500 | 20 MB | Wilderness medicine, emergency care, injuries |
| 🌿 Plants | 4 | ~5,000 | 15 MB | Edible plants, medicinal uses, identification |
| 🪢 Knots | 5 | ~150 | 10 MB | Essential knots, rigging, rope work |
| 🌦️ Weather | 5 | ~200 | 5 MB | Cloud identification, forecasting, storms |
| **Total** | **40** | **~7,000** | **~160 MB** | |

### Key Documents

<details>
<summary><b>🪖 Survival Manuals</b> (click to expand)</summary>

| Document | Description | License |
|----------|-------------|---------|
| **FM 21-76 Survival Manual** | The definitive US Army survival guide covering psychology, planning, medicine, shelter, water, fire, food, plants, and navigation | Public Domain |
| **FM 21-76-1 Survival, Evasion & Recovery** | Multi-service guide for survival and evasion in hostile environments | Public Domain |
| **FM 3-05.70 Survival** | Updated 2002 special operations survival manual | Public Domain |
| **Ranger Handbook SH 21-76** | US Army Ranger tactical and survival reference | Public Domain |

</details>

<details>
<summary><b>🧭 Navigation</b> (click to expand)</summary>

| Document | Description | License |
|----------|-------------|---------|
| **FM 3-25.26 Map Reading & Land Navigation** | Comprehensive military map reading and navigation | Public Domain |
| **USGS Topographic Map Symbols** | Official guide to reading topographic maps | Public Domain |

</details>

<details>
<summary><b>🏥 First Aid</b> (click to expand)</summary>

| Document | Description | License |
|----------|-------------|---------|
| **FM 4-25.11 First Aid** | US Army first aid and emergency care manual | Public Domain |
| **BSA Wilderness First Aid** | 16-hour wilderness first aid curriculum | Educational Use |
| **ICRC First Aid In Brief** | International Red Cross quick reference | CC BY-NC-ND |

</details>

<details>
<summary><b>🌿 Plants</b> (click to expand)</summary>

| Document | Description | License |
|----------|-------------|---------|
| **USDA Plants Database** | Comprehensive plant data for North America | Public Domain |
| **Plants For A Future (PFAF)** | 7,000+ plants with edibility ratings | CC BY-NC-SA |

</details>

See [SOURCES.md](SOURCES.md) for complete attribution and licensing details.

## 🔨 Building Locally

If you want to rebuild the index yourself:

```bash
# Clone repository
git clone https://github.com/waycore/waycore-rag-knowledge.git
cd waycore-rag-knowledge

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
    category TEXT NOT NULL,          -- survival, navigation, first_aid, plants, knots, weather
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

| Level | Color | Meaning | Example |
|-------|-------|---------|---------|
| `safe` | 🟢 | General information | Navigation basics |
| `caution` | 🟡 | Requires care | Fire starting techniques |
| `warning` | 🟠 | Significant risk | First aid procedures |
| `danger` | 🔴 | High risk | Plant identification |
| `lethal` | ⛔ | Life-threatening if wrong | Mushroom identification |

**Important**: All plant and mushroom entries default to `danger` or `lethal` with mandatory verification disclaimers. Never rely solely on this database for plant identification.

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

- **Repository structure & scripts**: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (Public Domain)
- **Source documents**: Various (see [SOURCES.md](SOURCES.md))
- **Generated index**: CC0 (derived from public domain works)

## 🔗 Related Projects

- [Waycore](https://github.com/dmitry-grechko/waycore) - Tactical field device using this knowledge base

## 📈 Stats

- **Total entries**: ~7,000
- **Index size**: ~180 MB (knowledge.db + vectors.idx)
- **Build time**: ~5-10 minutes
- **Query latency**: <100ms

---

*Built with ❤️ for the outdoor community*

