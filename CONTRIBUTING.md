# Contributing to waycore-rag-knowledge

Thank you for your interest in contributing! This document provides guidelines
for adding new sources or improving the build process.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) before
contributing.

## Adding New Sources

### Requirements

1. **License**: Source must be one of:
   - Public Domain (US Government works)
   - CC0 (Creative Commons Zero)
   - CC BY (Attribution)
   - CC BY-SA (Attribution-ShareAlike)
   - Educational use (with attribution)

2. **Relevance**: Content should relate to:
   - Survival skills
   - Navigation / orienteering
   - First aid / wilderness medicine
   - Plant identification / foraging
   - Knots / rope work
   - Weather / climate

3. **Quality**: High-quality, authoritative sources preferred

### Process

1. Fork the repository
2. Add source file to appropriate `sources/{category}/` directory
3. Update `SOURCES.md` with full attribution
4. Submit pull request with:
   - Source name and description
   - License information
   - Why this source is valuable

### Example PR Description

```markdown
## New Source: [Document Name]

**Category**: survival **License**: Public Domain (US Government) **Source
URL**: https://example.gov/document.pdf

### Description

Brief description of the content and why it's valuable.

### Checklist

- [ ] File added to `sources/{category}/`
- [ ] Attribution added to `SOURCES.md`
- [ ] File size under 100MB
- [ ] PDF is valid and readable
```

## Improving Parsers

1. Fork and create a feature branch
2. Modify files in `scripts/parsers/`
3. Test locally with `python scripts/build_index.py`
4. Submit PR with before/after comparison

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/waycore-rag-knowledge.git
cd waycore-rag-knowledge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r scripts/requirements.txt

# Run tests
pytest tests/
```

## Pull Request Guidelines

1. **One feature per PR** - Keep changes focused
2. **Update documentation** - If adding sources, update SOURCES.md
3. **Test locally** - Run the build script before submitting
4. **Descriptive commits** - Use clear commit messages

## Reporting Issues

When reporting issues, please include:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)

## Questions?

Open an issue for discussion before starting work on major changes.

---

Thank you for contributing to waycore-rag-knowledge! 🌲

