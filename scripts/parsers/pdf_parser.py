"""
PDF Parser
==========

Extracts text content from PDF documents using PyMuPDF.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


@dataclass
class TextChunk:
    """A chunk of text extracted from a PDF."""
    text: str
    page_number: int
    source_file: str


@dataclass
class PDFMetadata:
    """Metadata extracted from a PDF."""
    title: str | None
    author: str | None
    subject: str | None
    page_count: int
    file_size: int


class PDFParser:
    """Parser for PDF documents."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_size: int = 100,
    ):
        if fitz is None:
            raise ImportError("PyMuPDF (fitz) is required. Install with: pip install pymupdf")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def get_metadata(self, pdf_path: Path) -> PDFMetadata:
        """Extract metadata from a PDF."""
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        
        result = PDFMetadata(
            title=metadata.get("title") or None,
            author=metadata.get("author") or None,
            subject=metadata.get("subject") or None,
            page_count=len(doc),
            file_size=pdf_path.stat().st_size,
        )
        
        doc.close()
        return result
    
    def extract_text(self, pdf_path: Path) -> Iterator[TextChunk]:
        """Extract text from each page of a PDF."""
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text = self._clean_text(text)
            
            if text:
                yield TextChunk(
                    text=text,
                    page_number=page_num + 1,
                    source_file=pdf_path.name,
                )
        
        doc.close()
    
    def extract_chunks(self, pdf_path: Path) -> Iterator[TextChunk]:
        """Extract and chunk text from a PDF."""
        doc = fitz.open(pdf_path)
        all_text = ""
        page_positions = []  # (text_position, page_number)
        
        # Combine all text, tracking page positions
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            page_positions.append((len(all_text), page_num + 1))
            all_text += f"\n\n{text}"
        
        doc.close()
        
        # Clean and chunk
        all_text = self._clean_text(all_text)
        
        for chunk in self._chunk_text(all_text):
            # Find which page this chunk is from
            chunk_start = all_text.find(chunk[:50])
            page_number = 1
            for pos, page in page_positions:
                if chunk_start >= pos:
                    page_number = page
            
            yield TextChunk(
                text=chunk,
                page_number=page_number,
                source_file=pdf_path.name,
            )
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Replace multiple whitespace with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Normalize line endings
        text = re.sub(r'\r\n?', '\n', text)
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Strip
        text = text.strip()
        return text
    
    def _chunk_text(self, text: str) -> Iterator[str]:
        """Split text into overlapping chunks."""
        if len(text) < self.min_chunk_size:
            return
        
        # Split on paragraph boundaries
        paragraphs = re.split(r'\n\n+', text)
        
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph exceeds chunk size, yield current
            if len(current_chunk) + len(para) + 2 > self.chunk_size:
                if len(current_chunk) >= self.min_chunk_size:
                    yield current_chunk
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    current_chunk = current_chunk[-self.chunk_overlap:] + " " + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Yield remaining
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            yield current_chunk

